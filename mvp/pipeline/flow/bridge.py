# -*- coding: utf-8 -*-
"""flow v2 核心执行器：拼 prompt → 网关调用 → 校验 → 落盘审计件 → 路由。

审计三件套（Spec 第 10 节第 5 条铁律：prompt 与网关原始响应必须落盘 reports/ 备审）：
  reports/<stage>_prompt_system.md / <stage>_prompt_user.md / <stage>_response*.md / <stage>.md

抗 524（Spec 第 11 节第 2 条 + .local/complex_trial/gateway.py 实战形态）：
  max_tokens 缺省 4000；HTTP 524 或响应截断（JSON 解析坏）→ 按分段策略（Stage.segments）
  逐段调用、逐段落盘 _response_part<i>.md，再机械拼接（text=原文串接；json=逐段抽取合并）。

独立性棒（K2/P/A8/S22）不由 --auto 内联跑：打印
  SPAWN_SUBAGENT: stage=<X> run=<dir> prompt_files=[...]
由主 agent 另起子 agent 上下文执行 `python -m pipeline.flow --run <dir> --stage <X>`
（隔离靠调用上下文，不靠代码；子 agent 里本执行器照常跑该棒）。

确定性棒：A4=review.check 只读调用 + flow 层 physics_gates PHYS_* 六闸门（81-F1 接线：
输入 modelspec/ 目录，无目录=不检保持旧行为；violations 并入 F-8 输出后由
stages.route_a4_fail 按 PHYS_TO_M1/PHYS_TO_M2 路由 M1/M2；闸门在 flow 层，不在 review.py）；
R=TTS+渲染+合成适配层（现阶段 subprocess 调 .local/<run>/produce.py，T0 定稿后收编，见 run_deterministic_R 内 TODO）。

红线：不打印/记录任何 API 密钥（llm_client 的异常消息本身不含密钥）；不 git；不改公共层。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .. import llm_client, review
from ..ir import Plan
from . import handoff
from . import physics_gates as pg
from . import produce as flow_produce
from .stages import ROOT, HERE, STAGES, RunCtx, Stage, _resolve

MAX_ATTEMPTS = 3          # 首次 + 坏格式回喂重试 ≤2 次（每环 ≤3 轮纪律的单棒内层）
MAX_ROUNDS = 3            # O 路由表：每个打回环最多 3 轮，仍不过 → BLOCKED 报用户
SEG_RETRY = 2             # 机械修复（substitution_trial）：单段网关失败（524 等）段内重试次数
TRUNCATE_HINTS = ("524", "超时", "timeout", "Timeout")
M1_WORKERS_ENV = "QX_FLOW_M1_WORKERS"   # M1 按镜并行度上限（81-F1），缺省 3
DEFAULT_SEGMENT_WORKERS = 3
MAX_SEGMENT_WORKERS = 16                # 兜底：env 写错也不至于把网关打爆


# ---------------------------------------------------------------- 工具


def _ctx(run_dir: Path, state: dict) -> RunCtx:
    return RunCtx(run_dir=Path(run_dir), state=state, brief=state.get("brief") or {})


def _note(seq: list, item: str) -> None:
    """审计件登记去重：分段缓存在跨进程续跑时会重新 load handoff，同名响应只记一次。"""
    if item not in seq:
        seq.append(item)


def _response_name(stage_name: str, attempt: int, part: int | None = None) -> str:
    base = f"{stage_name}_response" if attempt == 0 else f"{stage_name}_response_r{attempt + 1}"
    return f"reports/{base}.md" if part is None else f"reports/{base}_part{part}.md"


def _write_report(run_dir: Path, st: Stage, verdict: str, nxt: str, state: dict,
                  inputs: list, errors: list, outputs: list, extra: str = "") -> str:
    """统一报告头（Ref_Handoff_Prompts）：agent/model 原样/task/inputs/verdict/next。"""
    model = llm_client.model_for(st.stage_id) if st.stage_id in llm_client.MODELS else "确定性代码（无模型）"
    slot = handoff.stage(state, st.name)
    rel = f"reports/{st.name}.md"
    lines = [
        f"agent: {st.name}   model: {model}   task: {st.task_line}   inputs: {', '.join(inputs) or '（无）'}",
        f"verdict: {verdict}     next: {nxt}",
        "",
        f"- run: {state.get('run')}   round: {slot.get('round', 0)}   retries: {slot.get('retries', 0)}",
        f"- 产物: {', '.join(outputs) or '（无）'}",
        f"- 审计件: {', '.join(slot.get('responses', [])) or '（无）'}",
    ]
    if errors:
        lines += ["", "## 校验错误清单（确定性）", *[f"- {e}" for e in errors]]
    if extra:
        lines += ["", extra]
    (run_dir / rel).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rel


def _is_truncation(err_text: str) -> bool:
    return any(h in err_text for h in TRUNCATE_HINTS)


def _stitch_json(parts: list[str]) -> str:
    """json 拼接策略：逐段 extract_json，dict 浅合并 / list 串接，再序列化回文本供 validate。"""
    merged: object = {}
    for p in parts:
        obj = llm_client.extract_json(p)
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list) and isinstance(merged, dict) and isinstance(merged.get(k), list):
                    merged[k] = merged[k] + v          # 同名列表字段（shots/specs）机械串接
                else:
                    merged = {**merged, k: v} if isinstance(merged, dict) else obj
        elif isinstance(obj, list):
            merged = (merged if isinstance(merged, list) else []) + obj
        else:
            merged = obj
    return json.dumps(merged, ensure_ascii=False, indent=1)


def _segment_workers(st: Stage) -> int:
    """按镜并行度上限（81-F1）：默认 3，env QX_FLOW_M1_WORKERS 覆盖；非法值回退默认，
    钳到 [1, MAX_SEGMENT_WORKERS]。只在 st.parallel_segments 的棒上生效。"""
    try:
        n = int(str(os.environ.get(M1_WORKERS_ENV, "")).strip())
    except (TypeError, ValueError):
        n = DEFAULT_SEGMENT_WORKERS
    return max(1, min(n, MAX_SEGMENT_WORKERS)) if n > 0 else DEFAULT_SEGMENT_WORKERS


def _call_one_segment(st: Stage, ctx: RunCtx, system: str, attempt: int,
                      i: int, eff: str) -> tuple[str, str | None]:
    """单段调用（_call_segmented 的段体，串行/并行共用，段内重试 SEG_RETRY 次语义不变）。

    命中断点缓存（段 user 逐字一致）→ 直接复用，返回 (text, None) 不重复登记审计件；
    否则调网关、落 _part<i>.md 与 segcache，返回 (text, rel)。失败抛 LLMError。
    线程安全前提：各段读写各自 distinct 路径的文件，共享态（responses/inputs）由主线程登记。"""
    cache_rel = f"reports/{st.name}_segcache_part{i}.md"
    cache_p, user_p = ctx.run_dir / cache_rel, ctx.run_dir / f"reports/{st.name}_segcache_part{i}.user.md"
    if cache_p.exists() and user_p.exists() and cache_p.stat().st_size > 0 and \
            user_p.read_text(encoding="utf-8") == eff:
        return cache_p.read_text(encoding="utf-8"), None   # 断点复用：审计件已在 responses 里
    text, last = None, None
    for _ in range(SEG_RETRY):
        try:
            text = llm_client.chat(st.stage_id, system, eff,
                                   images=st.build_images(ctx) if (st.build_images and i == 0) else None,
                                   max_tokens=st.max_tokens)
            break
        except llm_client.LLMError as e:
            last = e
    if text is None:
        raise last or llm_client.LLMError(f"[{st.name}] 第 {i} 段调用失败")
    rel = _response_name(st.name, attempt, part=i)
    (ctx.run_dir / rel).write_text(text, encoding="utf-8")
    cache_p.write_text(text, encoding="utf-8")
    user_p.write_text(eff, encoding="utf-8")
    return text, rel


def _call_segmented(st: Stage, ctx: RunCtx, system: str, attempt: int,
                    inputs: list, feedback: str = "") -> tuple[str, list[str]]:
    """分段调用（524/截断兜底）：每段独立落盘 _part<i>.md，机械拼接后返回。

    feedback：上一轮合并产物的确定性校验错误清单（机械回喂，与整发路径的 user 附加同构）；
    不带则分段重试是「盲重试」，同一批 prompt 重跑三次收敛不了格式错。

    机械修复（操作员，2026-10，substitution_trial/M2 实战）：
    1) 段级断点缓存 reports/<stage>_segcache_part<i>.md（配 .user.md 校验段输入）：
       后段 524 导致整 attempt 报废时，已成功的先段不再重复调网关——下一 attempt 或
       下一次 --stage 运行直接复用（段 user 逐字一致才复用；回喂 feedback 变化即失效）。
    2) 段内重试 SEG_RETRY 次（524 是窗口超时，隔几秒再发常可过）。

    81-F1（按镜并行）：st.parallel_segments=True 的棒（M1）用 ThreadPoolExecutor 并发跑段，
    并行度 _segment_workers（默认 3，env QX_FLOW_M1_WORKERS 覆盖）。结果**按段号（=镜号）顺序**
    拼接——拼接口径与串行版逐字节一致，与完成顺序无关（顺序确定性）；单段失败沿用段内
    SEG_RETRY 重试语义，重试后仍失败 → 等全部在途段收尾（成功段落盘进 segcache 供下轮复用），
    再抛段号最小的错误（与串行路径「撞到第一个坏段即止」的可观测结果一致）。
    max_tokens 分段口径不动（抗 524）。"""
    segs = st.segments(ctx) if st.segments else None
    if not segs:
        raise llm_client.LLMError(f"[{st.name}] 该棒未注册分段策略，无法从截断中恢复")
    effs = [seg + feedback for seg in segs]
    parts: list[str] = [""] * len(effs)
    rels: list[str | None] = [None] * len(effs)

    try:
        if getattr(st, "parallel_segments", False) and len(effs) > 1:
            errs: dict[int, BaseException] = {}
            with ThreadPoolExecutor(max_workers=min(_segment_workers(st), len(effs))) as ex:
                futs = {ex.submit(_call_one_segment, st, ctx, system, attempt, i, effs[i]): i
                        for i in range(len(effs))}
                for fut in as_completed(futs):
                    i = futs[fut]
                    try:
                        parts[i], rels[i] = fut.result()
                    except Exception as e:            # 含 LLMError；文件 IO 异常照旧外抛语义（下方 raise）
                        errs[i] = e
            if errs:
                raise errs[min(errs)]
        else:
            for i, eff in enumerate(effs):
                parts[i], rels[i] = _call_one_segment(st, ctx, system, attempt, i, eff)
    finally:
        # 审计登记按段号序（并发下仍确定）；坏段出现时已成功段的登记不丢——
        # 下一轮断点复用返回 rel=None，靠这里先登记过才不漏审计件（沿用串行旧语义）。
        for i, rel in enumerate(rels):
            if rel:
                _note(handoff.stage(ctx.state, st.name)["responses"], rel)
                inputs.append(rel)
    joined = "\n\n\n".join(p.strip() for p in parts) if st.stitch == "text" else _stitch_json(parts)
    return joined, []


# ---------------------------------------------------------------- 确定性棒


def _replay_sim_results(specs: list, plan) -> dict:
    """81-E2 T1b（G5 裁定方案）：run_physics_gates 之前用 physics 引擎从 ModelSpec
    **内存重放**填充 sim_result sidecar（不落盘、不覆盖已有 sidecar），让六闸门拿到
    「真实模拟源」而非恒力现算兜底；镜秒来源 = solver.t_end（replay 内部优先）→
    Plan 对应镜 seconds。不支持的模型/引擎不可用一律记 skip，绝不炸 A4
    （恒力现算兜底仍在那儿，重放只是将 skip 变 checked、将近似判据变逐帧比对）。
    shot_no↔plan.index 映射：V0 镜号 1 基（index = shot_no−1），兼容 0 基直用。"""
    out: dict = {"injected": [], "skipped": []}
    try:
        from physics import replay as phys_replay
    except Exception as e:  # noqa: BLE001 环境级故障不是模型的错：记 skip，闸门照常跑旧兜底
        out["error"] = f"physics.replay 不可用，全部 spec 未尝试重放：{type(e).__name__}: {e}"
        return out
    secs: dict = {}
    if plan is not None:
        try:
            secs = {int(s.index): float(s.seconds) for s in plan.shots}
        except (TypeError, ValueError):
            secs = {}
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        t_end = None
        no = spec.get("shot_no")
        if isinstance(no, (int, float)) and not isinstance(no, bool):
            no_i = int(no)
            t_end = secs.get(no_i - 1, secs.get(no_i))
        try:
            rec = phys_replay.replay_spec(spec, t_end=t_end)
        except Exception as e:  # noqa: BLE001 双保险：replay_spec 本体已吞异常
            rec = {"injected": False, "shot": spec.get("shot_no"), "reason": str(e)}
        out["injected" if rec.get("injected") else "skipped"].append(rec)
    return out


def run_deterministic_A4(st: Stage, ctx: RunCtx) -> tuple[dict, list[str]]:
    """A4'：review.check 只读调用（不改 plan/KP/review.py），F-8 契约 {checked, violations}。
    81-F1 接线：check 之后再跑 flow 层 physics_gates.run_physics_gates(modelspec/ 目录)，
    PHYS_* violations（{code, shot, detail}）并入同一 violations/findings 结构，由
    stages.route_a4_fail 按 PHYS_TO_M1/PHYS_TO_M2 路由 M1/M2；闸门在 flow 层，不经 review.py。
    modelspec/ 目录不存在 → 不跑闸门（保持旧行为，PASS 不受影响）；skips=字段缺失不适用，
    不算失败，原样挂 obj["phys_skips"] 供报告查。
    81-E2 T1b（G5）：跑闸门前先对 specs 做 physics 引擎内存重放填 sim_result（见
    _replay_sim_results），记账挂 obj["phys_replay"]；闸门输入改为重放后的 specs 列表
    （load_specs 语义不变，内存对象优先于磁盘文件）。"""
    plan_path = ctx.path("plan.json")
    if not plan_path.exists():
        # R7 接线（SubTask #79-D1a）：plan.json 缺失时先尝试从本 run 的 visual_script.json
        # 机械合成（produce.ensure_plan，逐字搬运不做语义改写）；无可合成物才照旧报 BLOCKED。
        if not flow_produce.ensure_plan(ctx):
            return {"checked": [], "violations": []}, ["plan.json 不存在（且无 visual_script.json 可合成）——报 BLOCKED"]
    plan = Plan.load(plan_path)
    findings = review.check(plan, ctx.load_kp())
    violations = review.blocking(findings)
    checked = sorted({f.get("code", "") for f in findings} | set(getattr(review, "CODES", ()) or ()))
    md_dir = ctx.path("modelspec")
    obj: dict = {"checked": checked, "violations": violations, "findings": findings}
    if md_dir.exists():
        specs = pg.load_specs(md_dir)
        replayed = _replay_sim_results(specs, plan)
        phys = pg.run_physics_gates(specs)
        violations = violations + phys["violations"]
        obj = {"checked": sorted(set(checked) | set(phys["checked"])),
               "violations": violations,
               "findings": findings + phys["violations"],
               "phys_skips": phys["skips"],
               "phys_replay": replayed}
    errors = [f"阻断违规 {f.get('code')}（shot {f.get('shot')}）：{f.get('msg') or f.get('detail') or ''}"
              for f in violations]
    return obj, errors


def run_deterministic_R(st: Stage, ctx: RunCtx) -> tuple[dict, list[str]]:
    """R 棒适配层：TTS + 逐镜渲染 + concat/mux + selfcheck。

    现阶段 = subprocess 调 .local/<run>/produce.py all（T0 链条操作员实战验证过的驱动形态：
    phase_tts→phase_render→phase_concat→phase_selfcheck，断点续跑靠 shot_seconds.json）。
    TODO(T0 定稿后收编进 pipeline，逐项)：
      1. tts 逐镜合成 + 秒数吸附 1/fps 网格（snap）+ shot_seconds.json 记账 → pipeline 化；
      2. manim 逐镜渲染（-q 档位/media_dir/disable_caching 参数形态照 produce.phase_render）；
      3. concat 无声轨 + mux.build_track/mux.mux + write_srt + sidecar.json（models 字段登记网关模型）；
      4. selfcheck：boundary_scan、帧预算 frames==round(sec*fps)、时长偏差 ≤10%、抽帧像素方差探针；
      5. manim/ffmpeg/MiKTeX 的 env PATH 注入（produce.py 头部两行）迁到 pipeline 配置。
    """
    produce = ROOT / ".local" / ctx.run_dir.name / "produce.py"
    if not produce.exists():
        # R7 接线（SubTask #79-D1a）：环境准备自动化——run 有 plan.json 就补一个默认
        # produce.py（驱动 pipeline.flow.produce.drive_r：逐镜渲染+concat，缺场景文件的镜
        # 走旧 A3 原语回退）。仍补不出来（无 plan.json/落盘失败）才照旧 BLOCKED。
        flow_produce.ensure_produce_script(ctx.run_dir)
    if not produce.exists():
        return {"adapter": "missing"}, [
            f".local/{ctx.run_dir.name}/produce.py 不存在：R 适配层无可驱动对象。"
            "T0 定稿前该 run 需先有操作员驱动的 produce.py（报 BLOCKED，不伪造产物）"]
    # 渲染子进程必须能把 mvp/ 当包根：M2 场景按契约写 `from render.scene import …` +
    # `from physics import …`，而 manim 只把**场景文件所在目录**加进 sys.path（实测：cwd=mvp
    # 但不设 PYTHONPATH 时 ModuleNotFoundError: No module named 'render'，见
    # .local/physics_probe/render_A.log；设了 PYTHONPATH=mvp 则 8s 探针镜渲出 mp4）。
    # 各 run 的 produce.py 里那行 PYTHONPATH 属操作员手工兜底，桥不能依赖它——在这里统一注入。
    env = dict(os.environ, PYTHONPATH=str(ROOT / "mvp") + os.pathsep
               + os.environ.get("PYTHONPATH", ""))
    r = subprocess.run([sys.executable, str(produce), "all"], cwd=str(ROOT / "mvp"), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_rel = "reports/R_console.log"
    (ctx.run_dir / log_rel).write_text(
        (r.stdout or "") + "\n=== STDERR ===\n" + (r.stderr or ""), encoding="utf-8")
    _note(handoff.stage(ctx.state, st.name)["responses"], log_rel)
    if r.returncode != 0:
        tail = "\n".join(((r.stderr or r.stdout or "").strip().splitlines())[-30:])
        return {"adapter": str(produce), "returncode": r.returncode}, [f"渲染失败（详见 {log_rel}）:\n{tail}"]
    return {"adapter": str(produce), "returncode": 0, "log": log_rel}, []


_DETERMINISTIC = {"A4": run_deterministic_A4, "R": run_deterministic_R}


# ---------------------------------------------------------------- 主执行器


def run_stage(run_dir, stage_name: str, isolated_ok: bool = False) -> str:
    """执行一棒：拼 prompt→落盘→网关调用→校验→报告→更新 handoff→返回 next（棒名/DONE/BLOCKED）。

    isolated_ok=True 表示调用方就是主 agent 为独立性棒另起的子 agent 上下文
    （CLI --stage 显式点名），允许执行 needs_isolated_context 的棒。"""
    run_dir = Path(run_dir)
    state = handoff.load(run_dir)
    if stage_name not in STAGES:
        raise KeyError(f"未注册的棒：{stage_name}（可选：{', '.join(STAGES)}）")
    st = STAGES[stage_name]
    ctx = _ctx(run_dir, state)
    slot = handoff.stage(state, stage_name)
    if st.needs_isolated_context and not isolated_ok:
        raise PermissionError(f"{stage_name} 是独立性棒，必须由主 agent 另起子 agent 上下文执行"
                              f"（python -m pipeline.flow --run {run_dir} --stage {stage_name}）")
    if slot.get("status") == "blocked" or slot.get("round", 0) > MAX_ROUNDS:
        handoff.mark(state, stage_name, status="blocked", verdict="BLOCKED", route_next="BLOCKED")
        handoff.save(run_dir, state)
        return "BLOCKED"

    slot["status"] = "running"
    handoff.save(run_dir, state)          # 中断可见 running 态（第 10 节纪律 1：产出立即落盘）

    inputs: list[str] = []
    outputs: list[str] = []
    errors: list[str] = []
    obj: object = None
    verdict, nxt = "FAIL", "BLOCKED"

    if st.deterministic:
        obj, errors = _DETERMINISTIC[st.name](st, ctx)
        if st.save_output and isinstance(obj, dict) and "violations" in obj:
            outputs = st.save_output(ctx, obj, "")     # review.json 过与不过都落盘（照 run.py 纪律）
        verdict = "PASS" if not errors else ("BLOCKED" if "BLOCKED" in errors[0] else "FAIL")
    else:
        system = st.system_prompt()
        user = st.build_user(ctx)
        sys_rel, user_rel = f"reports/{st.name}_prompt_system.md", f"reports/{st.name}_prompt_user.md"
        (run_dir / sys_rel).write_text(system, encoding="utf-8")
        (run_dir / user_rel).write_text(user, encoding="utf-8")
        inputs += [sys_rel, user_rel]
        images = st.build_images(ctx) if st.build_images else None

        segmented = False
        for attempt in range(MAX_ATTEMPTS):
            text = None
            if segmented:
                fb = ("\n\n【上一轮合并产物的错误清单，逐条修复后重新输出本轮分段产物，不输出差异】\n- "
                      + "\n- ".join(errors)) if errors else ""
                try:
                    text, _ = _call_segmented(st, ctx, system, attempt, inputs, fb)
                except llm_client.LLMError as e:
                    errors = [f"分段调用仍失败：{e}"]
            else:
                try:
                    text = llm_client.chat(st.stage_id, system, user, images=images,
                                           max_tokens=st.max_tokens)
                except llm_client.LLMError as e:
                    if _is_truncation(str(e)) and st.segments:
                        segmented = True       # 524/超时 → 下一轮起改分段+机械拼接
                        errors = [f"整体调用被截断/超时（{e}），转分段策略"]
                        continue
                    errors = [f"网关调用失败：{e}"]
            if text is None:
                # 网关侧失败（无产物可比对）也占一轮重试额度，否则 retries 恒 0、台账看不出回喂过几次
                if attempt + 1 < MAX_ATTEMPTS:
                    slot["retries"] = int(slot.get("retries", 0)) + 1
                continue
            rel = _response_name(st.name, attempt)
            (run_dir / rel).write_text(text, encoding="utf-8")
            _note(slot["responses"], rel)
            inputs.append(rel)
            obj, errors = st.validate(text, ctx)
            if not errors:
                outputs = st.save_output(ctx, obj, text) if st.save_output else []
                break
            # 编排层/环境级故障（如 physics 引擎导入不了）不是模型的错：
            # 回喂重试只会白烧额度，直接停手报 BLOCKED。
            if any("BLOCKED" in e for e in errors):
                break
            # 截断疑似（JSON 坏）且有分段策略 → 下一轮转分段（Spec 第 11 节第 2 条）
            if st.segments and any("JSON" in e for e in errors):
                segmented = True
            if attempt + 1 < MAX_ATTEMPTS:
                slot["retries"] = int(slot.get("retries", 0)) + 1
                user += ("\n\n【上一轮输出的错误清单，逐条修复后重新输出完整产物，不输出差异】\n- "
                         + "\n- ".join(errors))
                (run_dir / user_rel).write_text(user, encoding="utf-8")

    passed = verdict == "PASS" if st.deterministic else not errors and obj is not None
    if not st.deterministic and passed and isinstance(obj, dict) and obj.get("verdict") in ("PASS", "FAIL", "BLOCKED"):
        passed = obj["verdict"] == "PASS"          # 判定棒（K2/A8/S22）：报告 verdict 才算数
    if passed:
        verdict, nxt = "PASS", _resolve(st.next_on_pass, state, ctx, obj)
        status = "pass"
    else:
        if not errors and isinstance(obj, dict) and obj.get("verdict") in ("FAIL", "BLOCKED"):
            verdict = obj["verdict"]               # 有效判定为 FAIL/BLOCKED（不回喂重试）
        else:
            verdict = "BLOCKED" if any("BLOCKED" in e for e in errors) else "FAIL"
        nxt = "BLOCKED" if verdict == "BLOCKED" else _resolve(st.next_on_fail, state, ctx, obj)
        status = "blocked" if verdict == "BLOCKED" else "fail"
        # 打回轮数纪律：每环 ≤3 轮，第 4 次进同棒 → BLOCKED 报用户
        if nxt in STAGES:
            if slot.get("round", 0) + 1 > 0 and handoff.bump_round(state, nxt) > MAX_ROUNDS:
                nxt, verdict, status = "BLOCKED", "BLOCKED", "blocked"

    extra = ""
    if st.deterministic and st.name == "A4" and isinstance(obj, dict):
        extra = ("## findings（原样，不解释不改写）\n```json\n"
                 + json.dumps(obj.get("findings", obj.get("violations", [])), ensure_ascii=False, indent=1)
                 + "\n```")
    report_rel = _write_report(run_dir, st, verdict, nxt, state, inputs, errors, outputs, extra)
    handoff.mark(state, st.name, status=status, verdict=verdict, report=report_rel, route_next=nxt)
    handoff.save(run_dir, state)
    return nxt


def prepare_isolated(run_dir, stage_name: str) -> list[str]:
    """--auto 遇独立性棒：先把 prompt 文件落盘（供主 agent 派单引用），返回文件相对路径。"""
    run_dir = Path(run_dir)
    state = handoff.load(run_dir)
    st = STAGES[stage_name]
    ctx = _ctx(run_dir, state)
    rels = []
    if not st.deterministic:
        sys_rel, user_rel = f"reports/{st.name}_prompt_system.md", f"reports/{st.name}_prompt_user.md"
        (run_dir / sys_rel).write_text(st.system_prompt(), encoding="utf-8")
        (run_dir / user_rel).write_text(st.build_user(ctx), encoding="utf-8")
        rels = [sys_rel, user_rel]
    rels.append(write_dispatch(run_dir, stage_name))
    return rels


DISPATCH_REL = "reports/{stage}_dispatch.md"


def dispatch_text(run_dir, stage_name: str) -> str:
    """渲染操作员指令书：固定模板 + 机械填充（主 agent 派单一律原文粘贴，不再口头自写）。"""
    run_dir = Path(run_dir)
    state = handoff.load(run_dir)
    st = STAGES[stage_name]
    brief = state.get("brief") or {}
    model = "确定性代码（无模型）" if st.deterministic else llm_client.model_for(st.stage_id)
    text = (HERE / "prompts" / "DISPATCH_TEMPLATE.md").read_text(encoding="utf-8")
    fills = {
        "stage": stage_name,
        "run_dir": str(run_dir.resolve()),
        "task_line": st.task_line or "（见 prompt 文件）",
        "focus": str(brief.get("focus") or "（本题无附加要求，以本棒 prompt 为准）"),
        "style": json.dumps(brief.get("style") or {}, ensure_ascii=False),
        "model": model,
        "cmd": f"cd mvp && python -m pipeline.flow --run {run_dir.resolve()} --stage {stage_name}",
        "prompt_files": (f"reports/{stage_name}_prompt_system.md, reports/{stage_name}_prompt_user.md"
                         if not st.deterministic else "（确定性棒，无 prompt）"),
    }
    for k, v in fills.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def write_dispatch(run_dir, stage_name: str) -> str:
    """落盘 reports/<STAGE>_dispatch.md，返回相对路径。"""
    rel = DISPATCH_REL.format(stage=stage_name)
    run_dir = Path(run_dir)
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    (run_dir / rel).write_text(dispatch_text(run_dir, stage_name), encoding="utf-8")
    return rel


def spawn_line(run_dir, stage_name: str, prompt_files: list[str]) -> str:
    dispatch = DISPATCH_REL.format(stage=stage_name)
    return (f"SPAWN_SUBAGENT: stage={stage_name} run={Path(run_dir).resolve()} "
            f"dispatch_file={dispatch}（把该文件内容原文作为子 agent 派单，不要自写） "
            f"prompt_files=[{', '.join(prompt_files)}] "
            f"cmd=`cd mvp && python -m pipeline.flow --run {Path(run_dir).resolve()} --stage {stage_name}`")


def auto(run_dir) -> int:
    """--auto：从 handoff.route_next 连续推进；遇 独立性棒/FAIL/BLOCKED/DONE 停下并打印路由指令。"""
    run_dir = Path(run_dir)
    while True:
        state = handoff.load(run_dir)
        cur = state.get("route_next") or "BLOCKED"
        if cur in ("DONE", "BLOCKED"):
            print(f"ROUTE: {cur}" + ("（链条走完）" if cur == "DONE" else "（打回环超 3 轮或阻塞——报用户，不再自动重试）"))
            return 0 if cur == "DONE" else 1
        st = STAGES.get(cur)
        if st is None:
            print(f"ROUTE: BLOCKED（route_next={cur} 不是已注册棒名）")
            return 1
        if st.needs_isolated_context:
            files = prepare_isolated(run_dir, cur)
            print(spawn_line(run_dir, cur, files))
            print(f"ROUTE: WAIT_SUBAGENT（{cur} 是独立性棒，主 agent 另起子 agent 上下文执行上面的 cmd）")
            return 0
        nxt = run_stage(run_dir, cur)
        slot = handoff.stage(handoff.load(run_dir), cur)
        if slot.get("verdict") != "PASS":
            print(f"ROUTE: {nxt}（{cur} verdict={slot.get('verdict')}，打回/阻塞——路由指令见 reports/{cur}.md）")
            return 1 if nxt == "BLOCKED" else 0
        print(f"{cur}: PASS -> next={nxt}")
