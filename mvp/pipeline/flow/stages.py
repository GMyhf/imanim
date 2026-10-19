# -*- coding: utf-8 -*-
"""flow v2 棒次注册表：每棒的 prompt 来源、user 拼装、确定性校验、路由。

设计口径（Spec_AgentFlow_v2 第 2/8/10/11 节 + Ref_Handoff_Prompts O 路由表）：
- 语义产出全部经 llm_client.chat(stage,...) 由网关钉死模型完成（第 10 节第 5 条铁律），
  本注册表只做机械编排：拼 prompt、校验、落盘、路由。
- validate 是**确定性**校验（JSON 解析 + 字段检查 + 规则核对），不做语义判断；
  V0 的规则从 Spec 第 8 节 V0 围栏块逐条抄录（镜数/单镜占比/时长/must_say/forbidden）。
- needs_isolated_context=True 的棒（K2/P/A8/S22）必须由主 agent 另起子 agent 上下文调用
  （不共享上游推理过程），bridge --auto 遇到时只打印 SPAWN_SUBAGENT 指令并停下。
- next_on_fail 照 Ref_Handoff_Prompts 的 O 打回路由表：K2 FAIL→K1；A4 blocking 按码分派
  M1/M2/V0；每环 ≤3 轮（轮数控制在 bridge，round>3 → BLOCKED 报用户）。
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .. import ir, llm_client, knowledge
from ..storyboard import MIN_SHOTS, max_shots_for  # 81-A1c：镜头密度单一真源在 storyboard（81-A1b 建），
# flow 层不 import scene/manim，storyboard 只依赖 ir/review（纯标准库），无循环导入；
# K0（kp_draft）/A3（storyboard_llm）已接入，V0 校验与 K1 派单 prompt 在此同步同一口径。

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # D:\Dev\Project1
MVP = HERE.parents[1]                       # mvp/（physics 引擎所在）
SPEC_PATH = ROOT / "Projrct_Plan" / "Spec_AgentFlow_v2.md"


def physics_api_errors(code: str) -> list:
    """确定性闸门：场景代码只能 import/引用 physics 引擎里**真实存在**的名字。

    M2 一旦杜撰 API（早期草稿的 frame_points/progressive 之类），代码能编译、review 也过，
    到 R 渲染才 ImportError —— 白白烧掉整轮额度。这里在 M2 出口就用反射拦下。
    """
    try:
        import importlib
        if str(MVP) not in sys.path:
            sys.path.insert(0, str(MVP))
        pkg = importlib.import_module("physics")
        known = set(pkg.__all__)
    except Exception as e:                       # 引擎装不上是编排层问题，不让它伪装成模型 FAIL
        return [f"BLOCKED：physics 引擎导入失败（编排层问题，报操作员）：{e}"]
    errs: set[str] = set()
    for m in re.finditer(r"^[ \t]*from[ \t]+(physics(?:\.[A-Za-z_]\w*)?)[ \t]+import[ \t]+(.+)$",
                         code, re.M):
        mod, raw = m.group(1), m.group(2)
        names = [n.split(" as ")[0].strip() for n in re.split(r"[(),]", raw)
                 if n.strip() and not n.strip().startswith("as ")]
        if mod == "physics":
            bad = [n for n in names if n not in known]
        else:
            try:
                sub = importlib.import_module(mod)
            except Exception as e:
                errs.add(f"{mod} 导入失败：{e}")
                continue
            bad = [n for n in names if not hasattr(sub, n)]
        for n in bad:
            errs.add(f"{mod} 里没有 {n}（可用名字：{', '.join(sorted(known))}）")
    for m in re.finditer(r"(?<![\w.])physics\.([A-Za-z_]\w*)", code):
        attr = m.group(1)
        if attr not in known and attr not in ("integrator", "particle", "graphsync"):
            errs.add(f"physics.{attr} 不存在（可用名字：{', '.join(sorted(known))}）")
    return sorted(errs)

# ---------------------------------------------------------------- run 上下文


@dataclass
class RunCtx:
    """一次 run_stage 调用能看到的全部输入（都是路径/落盘件，不携带上游推理过程）。"""
    run_dir: Path
    state: dict
    brief: dict
    kp: Optional[dict] = None

    def path(self, *parts: str) -> Path:
        return self.run_dir.joinpath(*parts)

    def read_if(self, rel: str) -> str:
        p = self.run_dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def materials(self) -> str:
        """备料摘录（materials/*.md，由 P 棒/入库工具/操作员落盘；生产形态里由备料管线承担）。"""
        d = self.run_dir / "materials"
        if not d.exists():
            return ""
        chunks = []
        for p in sorted(d.glob("*.md")):
            chunks.append(f"===== {p.name} =====\n" + p.read_text(encoding="utf-8"))
        return "\n\n".join(chunks)

    def load_kp(self) -> Optional[dict]:
        """优先 kp_draft.json（本 run K1 产物），其次库内 kp_id 指向的条目。"""
        draft = self.run_dir / "kp_draft.json"
        if draft.exists():
            return json.loads(draft.read_text(encoding="utf-8"))
        kp_id = self.state.get("kp_id") or ""
        if kp_id:
            p = ROOT / "mvp" / "pipeline" / "data" / "kp" / f"{kp_id}.json"
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        return self.kp

    def load_script(self) -> Optional[dict]:
        p = self.run_dir / "visual_script.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def target_seconds(self) -> float:
        return float(self.brief.get("seconds") or 120)


# ---------------------------------------------------------------- Stage 定义


@dataclass
class Stage:
    name: str                                   # 棒名（K1/K2/P/V0/M1/M2/A4/R/A8/S22）
    stage_id: str                               # llm_client.MODELS 键（钉死模型）
    system_file: str                            # flow/prompts/ 下的 system prompt 文件名
    build_user: Optional[Callable[[RunCtx], str]] = None
    build_images: Optional[Callable[[RunCtx], list]] = None
    outputs: list = field(default_factory=list)  # 落盘路径（相对 run_dir）
    validate: Optional[Callable] = None         # (text, ctx) -> (obj, errors)
    save_output: Optional[Callable] = None      # (ctx, obj, text) -> [相对路径]
    needs_isolated_context: bool = False
    deterministic: bool = False                 # True=bridge 直接执行（A4/R），不走网关
    max_tokens: int = 4000                      # 缺省 4000：抗 524（Spec 第 11 节第 2 条）
    segments: Optional[Callable[[RunCtx], list]] = None   # 524/截断时的分段 user 列表
    parallel_segments: bool = False       # True=分段路径按段（按镜）ThreadPool 并行（81-F1，M1）；拼接仍按段号序
    stitch: str = "json"                        # 分段拼接策略：json=逐段抽 JSON 机械合并；text=原文拼接
    next_on_pass: object = "DONE"               # str 或 (state, ctx, obj) -> str
    next_on_fail: object = "BLOCKED"            # 同上
    task_line: str = ""                         # 报告统一头里的一句话 task

    def system_prompt(self) -> str:
        return (HERE / "prompts" / self.system_file).read_text(encoding="utf-8")


def _resolve(nxt, state: dict, ctx: RunCtx, obj) -> str:
    return nxt(state, ctx, obj) if callable(nxt) else str(nxt)


# ---------------------------------------------------------------- 路由（O 表）

PHYS_TO_M1 = {"PHYS_ANALYTIC", "PHYS_UNIT", "PHYS_ENERGY"}          # 模型参数错
PHYS_TO_M2 = {"PHYS_GRAPH_SYNC", "PHYS_FORCE_BALANCE", "PHYS_MB"}   # 实现错


def route_k2_pass(state: dict, ctx: RunCtx, obj) -> str:
    """K2 PASS：KP 登记了教材插图（figure_refs）→ 必派 P；没有 → 直接 V0（Spec 第 8 节 O 路由 1）。"""
    kp = ctx.load_kp() or {}
    return "P" if kp.get("figure_refs") else "V0"


def route_a4_fail(state: dict, ctx: RunCtx, obj) -> str:
    """A4' blocking 按码分类打回（Spec 第 8 节 O 路由 2）：物理参数码→M1，实现码→M2，旧 18 码→V0。"""
    codes = {f.get("code", "") for f in (obj or {}).get("violations", [])}
    if codes & PHYS_TO_M1:
        return "M1"
    if codes & PHYS_TO_M2:
        return "M2"
    return "V0"


def route_a8_fail(state: dict, ctx: RunCtx, obj) -> str:
    """A8' FAIL：MOTION_*（静止假动/方向错/跳变）→ M2；旧视觉码 → V0（Spec 第 8 节 O 路由 3）。"""
    text = json.dumps(obj or {}, ensure_ascii=False)
    return "M2" if "MOTION_" in text else "V0"


def route_r_fail(state: dict, ctx: RunCtx, obj) -> str:
    """渲染报错 → M2（实现错，Spec 第 8 节 O 路由 2 末句）。"""
    return "M2"


def route_s22_fail(state: dict, ctx: RunCtx, obj) -> str:
    """S22 报 G1 → K1+K2（重走链条自然再过 K2）；其余 FAIL 报用户。"""
    text = json.dumps(obj or {}, ensure_ascii=False)
    return "K1" if "G1" in text else "BLOCKED"


# ---------------------------------------------------------------- validate


def v_json_fields(text: str, ctx: RunCtx, required: tuple, list_key: str | None = None):
    """通用：extract_json + 顶层字段/列表元素字段检查。返回 (obj, errors)。"""
    try:
        obj = llm_client.extract_json(text)
    except llm_client.LLMError as e:
        return None, [f"输出不是合法 JSON：{e}"]
    errs = []
    items = obj
    if list_key:
        if not isinstance(obj, dict) or not isinstance(obj.get(list_key), list) or not obj[list_key]:
            return obj, [f"缺少非空列表字段 {list_key}"]
        items = obj[list_key]
    if isinstance(items, dict):
        items = [items]
    for i, it in enumerate(items if isinstance(items, list) else [items]):
        if not isinstance(it, dict):
            errs.append(f"第 {i} 项不是 JSON 对象")
            continue
        for k in required:
            if k not in it:
                errs.append(f"第 {i} 项缺字段 {k}")
    return obj, errs


def validate_k1(text: str, ctx: RunCtx):
    """K1：JSON 解析 + knowledge._check schema 复核（撰写员自跑纪律的代码化）。"""
    try:
        obj = llm_client.extract_json(text)
    except llm_client.LLMError as e:
        return None, [f"输出不是合法 JSON：{e}"]
    if not isinstance(obj, dict):
        return obj, ["KP 条目必须是 JSON 对象"]
    try:
        knowledge._check(obj)
    except Exception as e:                      # knowledge._check 抛 AssertionError/KeyError 等
        return obj, [f"knowledge schema 复核不过：{type(e).__name__}: {e}"]
    return obj, []


_VERDICT_RE = re.compile(r"verdict[:：]?\s*\**\s*(PASS|FAIL|BLOCKED)", re.I)


def validate_verdict(text: str, ctx: RunCtx):
    """K2/A8/S22 类判定棒：从报告文本抽 verdict 行；抽不到视为格式坏（回喂重试）。"""
    m = _VERDICT_RE.search(text)
    if not m:
        return {"text": text}, ["报告里找不到 verdict: PASS|FAIL|BLOCKED 行"]
    return {"verdict": m.group(1).upper(), "text": text}, []


def validate_k2(text: str, ctx: RunCtx):
    obj, errs = validate_verdict(text, ctx)
    if errs:
        return obj, errs
    # 判定码统计（UNSUPPORTED/OVERSTATED/WRONG/GENERALIZED）进 obj 供报告引用
    obj["finding_codes"] = sorted(set(re.findall(
        r"\b(OK|OVERSTATED|UNSUPPORTED|GENERALIZED|WRONG|UNVERIFIED)\b", text)) - {"OK"})
    return obj, []


def validate_v0(text: str, ctx: RunCtx):
    """V0 确定性校验，规则逐条抄自 Spec 第 8 节 V0 围栏块第 1/2 条：
    镜头数下限 MIN_SHOTS、上限随目标时长伸缩（storyboard.max_shots_for，81-A1c 同步 81-A1b 口径；
    时长读不出时 RunCtx.target_seconds 兜底 120s ⇒ 仍是旧上限 10）；单镜 ≤25%；总时长 ≈ 目标（±20%）；
    must_say 逐字进某镜口播；forbidden 零出现；
    口播总字数 ≤ (秒数×NATURAL_CPS − 镜数×1.15s×NATURAL_CPS) 的 110%（宁少勿多，留抖动余量）。"""
    try:
        script = llm_client.extract_json(text)
    except llm_client.LLMError as e:
        return None, [f"输出不是合法 JSON：{e}"]
    errs: list[str] = []
    # 81-A1c：镜数上限取自 storyboard 单一真源——旧「4~10」硬校验会把 1200s 长片（可到 20 镜）打回。
    target = ctx.target_seconds()
    cap = max_shots_for(target)
    shots = script.get("shots") if isinstance(script, dict) else None
    if not isinstance(shots, list) or not (MIN_SHOTS <= len(shots) <= cap):
        n = len(shots) if isinstance(shots, list) else "?"
        return script, [f"shots 必须是 {MIN_SHOTS}~{cap} 镜的数组，实际 {n}"]
    total, narr_all = 0.0, ""
    for i, sh in enumerate(shots):
        for k in ("shot_no", "seconds_budget", "narration"):
            if k not in sh:
                errs.append(f"shot[{i}] 缺字段 {k}")
        sb = sh.get("seconds_budget")
        if isinstance(sb, (int, float)):
            total += sb
            if sb > target * 0.25 + 1e-9:
                errs.append(f"shot[{i}] seconds_budget={sb} 超过总长 25%（{target * 0.25:.1f}s）")
        else:
            errs.append(f"shot[{i}] seconds_budget 不是数值")
        narr_all += str(sh.get("narration", ""))
    # 开场大字标题（Spec_Video_Defaults 第一节「开头」，用户 2026-10-18 复申"仍然必要"）
    topic = str((ctx.brief or {}).get("topic") or "").strip()
    ot = str(shots[0].get("opening_title") or "").strip() if isinstance(shots[0], dict) else ""
    if topic and ot.replace(" ", "") != topic.replace(" ", ""):
        errs.append(f"首镜 opening_title 必须逐字等于 KP topic 原文（期望 {topic!r}，实际 {ot!r}）："
                    "第一帧大字标题是默认设定，不可省")
    if errs:
        return script, errs
    if abs(total - target) > target * 0.20:
        errs.append(f"seconds_budget 合计 {total}s 偏离目标 {target}s 超过 ±20%")
    cap = (target - len(shots) * 1.15) * ir.NATURAL_CPS * 1.10
    if len(narr_all) > cap:
        errs.append(f"口播总字数 {len(narr_all)} 超过预算上限 {cap:.0f}（宁少勿多）")
    kp = ctx.load_kp() or {}
    norm = lambda s: re.sub(r"[\s²=−\-+|√()（）]", "", s)   # noqa: E731
    hay = norm(narr_all)
    for ms in kp.get("must_say", []):
        key = norm(str(ms))
        frag = max((key[:8], key[-8:]))
        if frag and frag not in hay:
            errs.append(f"must_say 未逐字进任何镜口播：{ms}")
    for fb in kp.get("forbidden", []):
        if fb and str(fb) in narr_all:
            errs.append(f"forbidden 词出现：{fb}")
    return script, errs


SIM_TYPES = {"rigid_body_2d", "particle_gas", "coupled_graph",
             "geometry_transform", "wave", "circuit", "analytic"}


def validate_m1(text: str, ctx: RunCtx):
    obj, errs = v_json_fields(text, ctx, ("shot_no", "sim_type", "solver"), list_key="specs")
    if errs or not isinstance(obj, dict):
        return obj, errs
    for i, sp in enumerate(obj["specs"]):
        if sp.get("sim_type") not in SIM_TYPES:
            errs.append(f"spec[{i}] sim_type={sp.get('sim_type')!r} 不在 schema 枚举内")
        if not sp.get("analytic_check") and not (sp.get("solver") or {}).get("events"):
            errs.append(f"spec[{i}] analytic_check 与 solver.events 至少填一个（A4' 抽检依据）")
        gs = sp.get("graph_sync")
        if gs and not gs.get("source"):
            errs.append(f"spec[{i}] graph_sync.source 必须指向真实 body 状态量")
    return obj, errs


def validate_m2(text: str, ctx: RunCtx):
    """M2：抽 ```python 围栏（分段拼接后允许多个围栏）；必须出现 class Shot 场景类。"""
    codes = re.findall(r"```python\n(.*?)\n```", text, re.S)
    code = "\n\n\n".join(c.strip() for c in codes) if codes else text.strip()
    errs = []
    if "class Shot" not in code:
        errs.append("输出里没有 class Shot<N> 场景类")
    try:
        compile(code, "<m2_scene>", "exec")
    except SyntaxError as e:
        errs.append(f"场景代码语法错误：{e}")
    else:
        errs += physics_api_errors(code)
        md = ctx.path("modelspec")
        has_dyn = md.exists() and any(md.glob("shot*.json"))
        if has_dyn and "physics" not in code:
            errs.append("ModelSpec 存在却没引用 physics 引擎：画面运动必须由 integrate()/series() 驱动，"
                        "不得手填关键帧")
        # 镜数完整性（机械修复，2026-10-18 实战）：分段策略下 Shot3+ 连续撞 524，前 2 段已落盘，
        # 原先只验 "class Shot" 出现过 → 6/9 镜也判 PASS，坏产物一路带到 R 才暴露。缺哪镜就回喂哪镜。
        script = ctx.load_script() or {}
        want = [sh.get("shot_no") for sh in (script.get("shots") or []) if sh.get("shot_no") is not None]
        have = {int(m.group(1)) for m in re.finditer(r"\bclass\s+Shot(\d+)\b", code)}
        missing = [k for k in want if k not in have]
        if want and missing:
            errs.append(f"场景代码缺镜：Shot{', Shot'.join(str(k) for k in missing)}"
                        f"（visual_script 要求 {len(want)} 镜，实际 {len(have & set(want))} 镜）——"
                        "补齐缺失的 Shot 类，已写好的镜不要重写")
    return {"code": code}, errs


def validate_a4(obj_in, ctx: RunCtx):
    """A4' 是确定性棒：obj 由 bridge 直接构造（review.check 结果），这里只核 F-8 契约字段。"""
    errs = []
    if not isinstance(obj_in, dict) or "checked" not in obj_in or "violations" not in obj_in:
        errs.append("A4 输出不符合 F-8 契约 {checked, violations}")
    return obj_in, errs


# ---------------------------------------------------------------- save_output


def save_k1(ctx: RunCtx, obj, text: str) -> list:
    p = ctx.path("kp_draft.json")
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return ["kp_draft.json"]


def save_figurespec(ctx: RunCtx, obj, text: str) -> list:
    items = obj if isinstance(obj, list) else (obj.get("figurespecs") or obj.get("specs") or [obj])
    d = ctx.path("figurespec")
    d.mkdir(parents=True, exist_ok=True)
    rel = []
    for i, it in enumerate(items):
        name = f"{Path(str(it.get('pdf', 'fig'))).stem}_p{it.get('page', 0)}_f{it.get('figure_no', i)}.json"
        (d / name).write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
        rel.append(f"figurespec/{name}")
    return rel


def save_v0(ctx: RunCtx, obj, text: str) -> list:
    p = ctx.path("visual_script.json")
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return ["visual_script.json"]


def save_m1(ctx: RunCtx, obj, text: str) -> list:
    d = ctx.path("modelspec")
    d.mkdir(parents=True, exist_ok=True)
    rel = []
    for sp in obj["specs"]:
        n = sp.get("shot_no", 0)
        (d / f"shot{n}.json").write_text(json.dumps(sp, ensure_ascii=False, indent=2), encoding="utf-8")
        rel.append(f"modelspec/shot{n}.json")
    return rel


def save_m2(ctx: RunCtx, obj, text: str) -> list:
    """拼接后的场景代码落 run 目录（生产接线 R7 时由操作员收编进 mvp/render/scenes/，bridge 不直写公共层）。"""
    # 机械修复（主 agent，2026-10-18）：原先直接用 brief.topic 当文件名 → T5 产出
    # 「电容-单杆模型 I=CBLa_scene.py」，中文+空格的文件名在 manim/ subprocess 链路上随时翻车。
    # 文件名只走 ASCII slug：优先 kp_id（<subject>/<id>），退到 run 目录名，两者都是库内 ASCII 标识。
    ident = (ctx.state.get("kp_id") or "").split("/")[-1] or ctx.run_dir.name
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ident).strip("_") or "scene"
    d = ctx.path("generated")
    d.mkdir(parents=True, exist_ok=True)
    rel = f"generated/{slug}_scene.py"
    ctx.path(rel).write_text(obj["code"] + "\n", encoding="utf-8")
    return [rel]


def save_a4(ctx: RunCtx, obj, text: str) -> list:
    ctx.path("review.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return ["review.json"]


# ---------------------------------------------------------------- build_user

_STYLE_LINE = "style 由 brief 指定（见下），缺省沿用全局暗色主题。"


def _brief_line(ctx: RunCtx, focus: bool = True) -> str:
    b = ctx.brief
    line = (f"【本片需求】subject={b.get('subject')}；grade={b.get('grade')}；topic=「{b.get('topic')}」；"
            f"目标总时长 {ctx.target_seconds():g}s；style={json.dumps(b.get('style') or {}, ensure_ascii=False)}。{_STYLE_LINE}")
    # 机械修复（主 agent，2026-10-18）：brief.focus（本题专题/验收点原文）此前只进派单模板，
    # 不进棒 prompt → 操作员只能靠硬编常量补，造成跨题污染。此处逐字透传，M1/M2 另有
    # concretization_rule 在尾部原文附加一遍。
    # 口径纠偏（T1 操作员，2026-10-18）：V0 是**口播编剧**棒，专题要求全是画面/建模验收点，
    # 进 V0 会诱导模型把验收条款念进口播 → V0 不注入（focus=False），只走 M1/M2。
    if focus:
        f = str(b.get("focus") or "").strip()
        if f:
            line += "\n【本题专题要求（brief.focus 原文）】\n" + f
    return line


def _kp_block(ctx: RunCtx) -> str:
    kp = ctx.load_kp()
    if not kp:
        return "（KP 尚未产出——上游棒缺失，如实报 BLOCKED 所需信息不足）"
    return "KP JSON（事实唯一来源，全文如下）：\n" + json.dumps(kp, ensure_ascii=False, indent=1)


def segments_k1(ctx: RunCtx) -> list:
    """K1 分段策略（机械修复，操作员，2026-10）：整条 KP JSON 常超单发 max_tokens=4000 被截断，
    照 T2（periodic_trial）实战形态分两段：段一只出除 sequence 外的顶层字段（sequence 出空数组），
    段二只出 {"sequence":[...]}；_stitch_json 对同名列表机械串接。"""
    b = ctx.brief
    base = build_k1(ctx)
    seg1 = base + ("\n\n【本次为分段输出第 1 段/共 2 段】只输出 KP 条目除分镜序列内容以外的顶层字段"
                   "（id/subject/grade/topic/aliases/refs/figure_refs/prior/forbidden/must_say 等），"
                   "并给出 \"sequence\": []（空数组占位）。只输出这个 JSON 对象。")
    seg2 = (f"# K1 分段输出第 2 段/共 2 段（承接第 1 段同一条目）\n"
            f"为知识点「{b.get('topic')}」（{b.get('subject')}/{b.get('grade')}）输出分镜序列："
            f"只输出一个 JSON 对象 {{\"sequence\":[全部镜头]}}，{MIN_SHOTS}~{max_shots_for(ctx.target_seconds())} 镜，每镜含 "
            f"title/seconds/narration/emphasis/visuals；各镜 seconds 之和落在总时长 "
            f"{ctx.target_seconds():g}s 的 ±10%。事实口径与第 1 段同一资料一致。只输出 JSON。")
    return [seg1, seg2]


def build_k1(ctx: RunCtx) -> str:
    b = ctx.brief
    kp_id = ctx.state.get("kp_id") or f"{b.get('subject')}/{re.sub(r'[^0-9A-Za-z_]+', '_', str(b.get('topic')))}"
    exemplar = ""
    ex_dir = ROOT / "mvp" / "pipeline" / "data" / "kp" / str(b.get("subject") or "")
    if ex_dir.exists():
        ex = sorted(ex_dir.glob("*.json"))[:1]
        if ex:
            exemplar = f"\n\n【同学科现有条目格式范本（只学格式，不抄内容）：{ex[0].name}】\n" + \
                ex[0].read_text(encoding="utf-8")[:4000]
    mats = ctx.materials()
    return (f"# K1 任务：撰写「{b.get('topic')}」KP 条目\n\n"
            f"## 一、任务说明\n"
            f"- 为 {b.get('subject')} / {b.get('grade')} 学段撰写知识点「{b.get('topic')}」的 KP 条目 JSON。\n"
            f"- id 固定为 `kp.{b.get('subject')}.{kp_id.split('/')[-1]}`；全片总时长 {ctx.target_seconds():g}s，"
            f"分镜 sequence {MIN_SHOTS}~{max_shots_for(ctx.target_seconds())} 镜（各镜 seconds 之和落在总时长 ±10%）。\n"
            f"- 事实一律以下方「资料摘录」为准；摘录里没有的数字、结论、人名、年份一律不写。\n"
            f"- 限定词纪律：原文弱表述（倾向/可能/generally）不得强化为绝对断言。\n"
            f"- 翻资料时同步登记教材插图清单 figure_refs（Spec v2 K1 第 7 条，每条 ≤6 张，caption 逐字抄）。\n\n"
            f"## 二、资料摘录（备料件，materials/ 落盘原文）\n\n{mats or '（本 run 无备料摘录——只写你确知的通识并全部标 UNVERIFIED，或报 BLOCKED）'}"
            f"{exemplar}\n\n"
            f"## 三、输出\n只输出一个合法 JSON 对象（KP 条目全文），不要解释文字、不要围栏外的说明。")


def build_k2(ctx: RunCtx) -> str:
    mats = ctx.materials()
    return ("# K2 核对材料\n\n"
            "## 一、待核对 KP JSON 全文\n\n```json\n"
            + json.dumps(ctx.load_kp() or {}, ensure_ascii=False, indent=1)
            + "\n```\n\n## 二、原文摘录（判定依据；给不出摘抄的判定无效，改 UNVERIFIED）\n\n"
            + (mats or "（本 run 无备料摘录——全部条目按 UNVERIFIED 处理并说明）")
            + "\n\n## 三、输出\n逐条判定（OK/OVERSTATED/UNSUPPORTED/GENERALIZED/WRONG/UNVERIFIED，"
              "每条附原文位置+≤30 字摘抄）+ 建议改法，最后一行必须是 `verdict: PASS` 或 `verdict: FAIL`。")


def build_p(ctx: RunCtx) -> str:
    kp = ctx.load_kp() or {}
    return ("# P 图像解读任务\n\n【figure_refs 清单（KP 登记，唯一输入来源）】\n"
            + json.dumps(kp.get("figure_refs", []), ensure_ascii=False, indent=1)
            + "\n\n【对应页文本层摘录】\n" + (ctx.materials() or "（无文本层备料——文字对不上的项一律 UNVERIFIED）")
            + "\n\n页面渲染图随本消息以图片形式给出（figures/*.png，≤1600px）。"
              "每张图输出一个 FigureSpec JSON，全部装进 {\"figurespecs\":[...]}；"
              "confidence<0.6 的单列。只输出 JSON。")


def build_images_p(ctx: RunCtx) -> list:
    d = ctx.path("figures")
    return sorted(d.glob("*.png")) if d.exists() else []


DEFAULTS_NOTE = """
【默认设定（Spec_Video_Defaults.md 摘要，硬约束）】
- 字体：中文宋体、英文 Times New Roman；公式一律 LaTeX（MathTex）渲染。
- 开头：第一镜首帧必须是「内容主题」大字标题（宋体、居中、安全区内），随口播结束淡出——
  这是下面"屏上几乎无字"的唯一开场例外（用户 2026-10-18 复申：第一帧大字标题仍然必要）。
- 图多；文字只在口播，几乎不进画面；禁止把口播原样变成字幕（口播不上屏）。
- 屏上允许的文字只有「把抽象概念落到具象画面」的短标注 + LaTeX 公式。
- 动效默认「消失-出现」（淡出→淡入）。
- style 缺省：全局暗色主题（theme=dark）。
"""


def build_v0(ctx: RunCtx) -> str:
    fs_dir = ctx.path("figurespec")
    fs = ""
    if fs_dir.exists():
        fs = "\n\n【FigureSpec 清单（P 棒产物）】\n" + "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(fs_dir.glob("*.json")))
    return (DEFAULTS_NOTE + "\n" + _brief_line(ctx, focus=False) + "\n\n" + _kp_block(ctx) + fs
            + "\n\n输出 visual_script.json：顶层 {\"style\":{...},\"shots\":[...]}，"
              "每镜字段按你的系统提示词第 1 条（shot_no/seconds_budget/画面叙事/sim_kind/"
              "ModelSpec需求描述/narration/屏上标注/reveal_beats），首镜另加 opening_title（第 8 条）。"
              "只输出 JSON，不要解释文字。")


def _modelspec_schema() -> str:
    """Spec 第 3.1 节 ModelSpec schema 围栏块（运行时抽取，Spec 更新即跟随）。"""
    from .tools_extract_prompts import fence_after
    try:
        return fence_after(SPEC_PATH.read_text(encoding="utf-8"), r"### 3\.1 ModelSpec[^\n]*\n", fence="```jsonc")
    except (OSError, SystemExit):
        return "（schema 抽取失败——按 M1 系统提示词第 1 条字段清单填写）"


# 机械附加（操作员，2026-10，T4 速度选择器）：桥的 M1/M2 user prompt 模板里没有具象化要求原文
# （只有 V0 系统提示词第 4 条带），按任务口径把 Spec 第 8 节 V0 提示词第 4 条（核心 rule「语义
# 具象化原则」）原文附加到 M1/M2 user prompt 尾部。操作员不新增任何语义，只搬运已定稿 rule 原文。
# 主 agent 纠偏（2026-10-18）：各题验收点原先硬编在这段公共常量里 → T4 的验收点被带进 T1/T2/T3/T5
# 的 prompt（跨题污染）。验收点是**每题输入**，改由 brief.acceptance 提供（--init / --acceptance），
# 本函数只透传原文，不带任何一题的内容。
CONCRETIZATION_RULE = """

【核心 rule 原文附加 · 语义具象化原则（Spec_AgentFlow_v2.md 第 8 节 V0 提示词第 4 条，逐字引用）】
4. 语义具象化原则（2026-10-18 用户 rule）：画面动作必须与概念动作同构——概念里的动词
   （取代/选择/切割/充电/配速/扩充…）必须用画面元素的**代替、移动、变换**直接演出来：
   讲「取代反应」就让原子/字符真的被换走、移进移出；公式推导必须有**字母↔物理量对应动画**
   （字母色标、代入位移、数值同步上屏）；方程式/表达式里有内在思维联系的项同理
   （项的移动、守恒量色标、来源去向连线）。禁止"口播讲取代、画面放静态结构式"这种脱钩。
"""


def concretization_rule(ctx: RunCtx) -> str:
    """通用具象化 rule + 本题验收点原文（brief.focus，逐字透传，无则不附加）。"""
    acc = str((ctx.brief or {}).get("focus") or "").strip()
    if not acc:
        return CONCRETIZATION_RULE
    return (CONCRETIZATION_RULE +
            "\n【核心 rule 原文附加 · 本题验收点（brief.focus，主 agent 逐字注入）】\n" + acc + "\n")


def build_m1(ctx: RunCtx) -> str:
    script = ctx.load_script() or {}
    return (_brief_line(ctx) + "\n\n【ModelSpec schema（Spec v2 第 3.1 节原文）】\n```jsonc\n"
            + _modelspec_schema() + "\n```\n\n【visual_script.json 全文】\n"
            + json.dumps(script, ensure_ascii=False, indent=1)
            + "\n\n把每个 sim 镜的 ModelSpec 装进一个 JSON 输出：{\"specs\":[{...,\"shot_no\":N},...]}，"
              "静态版式镜可不出 spec。只输出 JSON。" + concretization_rule(ctx))


def segments_v0(ctx: RunCtx) -> list:
    """机械修复（操作员，2026-10）：V0 未注册分段策略，整片 visual_script（8~10 镜）单发
    max_tokens=4000 常截断且无法恢复（bridge 截断兜底要求 st.segments）。照 segments_m2 形态
    按 KP sequence 镜数分组（每组 ≤4 镜），_stitch_json 对 shots 列表机械串接。"""
    kp = ctx.load_kp() or {}
    n = len(kp.get("sequence") or []) or 8
    target = ctx.target_seconds()
    base = build_v0(ctx)
    segs = []
    for a in range(1, n + 1, 4):
        b = min(a + 3, n)
        segs.append(
            base + f"\n\n【本次为分段输出：只出 shot_no {a}~{b}】全片共 {n} 镜（对应 KP sequence 的 "
            f"{n} 镜，shot_no 1~{n}），其余镜由相邻段输出，本段不得越界。顶层输出 "
            f"{{\"shots\":[]}}（style 头只在含 shot_no=1 的那段给出）。硬约束照旧：单镜 seconds_budget "
            f"≤ {target * 0.25:.0f}s；全片 {n} 镜合计 ≈ {target:g}s（±20%）；全片口播总字数 ≤ "
            f"{(target - n * 1.15) * ir.NATURAL_CPS * 1.10:.0f}（本段按镜数分摊，宁少勿多）；"
            f"must_say 逐字进对应镜 narration（参考 KP sequence 原口播）；forbidden 零出现。只输出 JSON。")
    return segs


PHYSICS_API = """
【physics 引擎 = 画面运动与图线的唯一合法来源（核心 rule：真实物理模型动态渲染，禁止手填关键帧）】
只允许 import/调用下列真实存在的名字，签名照此，不得杜撰其它函数或参数：
- from physics import …，可 import 的名字就这 12 个：integrate, Trajectory, rk4_step, Particle,
  lorentz, series, shared_time_axis, autoscale, bounds, AxisMap, Range, Curve
- integrate(pos=, vel=, mass=1.0, force=fn(t,pos,vel)->合力 或 particle=Particle, t_end=, dt=0.01) -> Trajectory
  force 与 particle 二选一（都给或都不给=报错）；节点数 = round(t_end/dt)+1。
  轨迹字段：tr.t[n]、tr.pos[n,d]、tr.vel[n,d]、tr.acc[n,d]、tr.dt、tr.t_end、tr.mass（numpy 数组，仿真单位）。
- tr.sample(times) -> (pos, vel)：三次 Hermite 插值。逐帧动画必须按渲染帧时间调它取坐标，
  帧数与 dt 解耦（fps 变了轨迹也不用重算）。
- tr.speed() / tr.kinetic_energy() / tr.total_energy(phi=None, charge=0.0) -> 每个节点一个标量。
- tr.crossing(fn(pos)->bool) -> 第一次满足的时刻（二分细化）；tr.speed_below(v) -> 速率首次降到 v 的时刻；
  都不满足返回 None（"何时穿出边界/何时停下"只能这样问引擎，不许自己估）。
- Particle(mass=, charge=, pos=, vel=, e_field=(Ex,Ey[,Ez]), b_field=(0,0,Bz), extra_force=None)：
  二维粒子（纸面内运动）只允许 Bz；extra_force(t,pos,vel) 叠加重力等。p.net_force(t,pos,vel) 是合力，
  p.at(pos,vel) 换状态保留场。lorentz(q, vel, e_field, b_field) -> q(E + v×B)。
- series(traj, y, x="t", name="", width=10.0, origin=(0,0), want=5) -> Curve：横轴只能是共享时间轴 "t"；
  y = "pos"/"speed"/"ek" | ("pos"|"v"|"a", 分量下标) | (图线名, fn(traj)->与节点等长的数组)。
  c.points(n_frames) -> [(x,y)] 逐帧画面坐标（n_frames = round(SECONDS × fps)，线刚好铺满 width）；
  c.upto(t) -> 截至 t 的已画部分（描线动画用）。
- autoscale(values, want=5) -> Range(lo, hi, step)，r.ticks() 给刻度数组；
  AxisMap.of(values, span, want, origin) 把仿真值映射到画面：am.to_screen(v, axis=0/1)
  （**不翻 y**：渲染端 ManimCE 的 y 轴向上，映射再翻一次会把图线画颠倒、把粒子转向做成镜像）；
  shared_time_axis(traj) 取全片共享时间轴。
- 只用 ManimCE 0.22 真有的符号：没有 Polyline（ManimGL 残留名），逐帧折线用
  VMobject().set_points_as_corners(...) 或 Line 段拼接；点/圆用 Dot/Circle。
- 硬约束：粒子、图线、读数三者的数据必须来自**同一个** Trajectory（图-式-体同源）；坐标换算只走
  AxisMap/Curve，不许在场景里写 x = v0*t 这类手算轨迹，也不许给 mobject 直接摆关键帧位置。
"""


M2_BRIEF = """
【scene.py 可复用封装清单（只 import，禁止修改公共层）】
- from render.scene import T, THEMES, SAFE_WIDTH, CONTENT_TOP, CONTENT_BOTTOM, SUBTITLE_BAND, HEADER_BAND
- T(content, **kw)：全片唯一 Text 出口，中文宋体/拉丁 Times New Roman 自动混排；短标注一律用 T()。
- SAFE_WIDTH=12.4；CONTENT_TOP=3.4；CONTENT_BOTTOM=-2.95；底部 SUBTITLE_BAND=1.05 任何内容不得进入。
- 公式用 manim MathTex；style 参数（theme/palette/bg/ink）在本镜场景文件内内联实现，不改 scene.py。

【帧预算铁律】
- 每镜一个 Scene 类（Shot1..ShotN），类常量 SECONDS；construct 内动画总时长必须恰好 SECONDS
  （末尾 self.wait(pad) 补齐），从而帧数 == round(SECONDS × fps)。场景代码不得写死帧数。

""" + PHYSICS_API + """
【输出要求】
- 顶部 import 只用 ManimCE 核心 API + render.scene 封装 + 上面清单里的 physics 名字 + 标准库。
  包名一律写顶层形式（`from render.scene import …` / `from physics import …`）：R 渲染子进程已统一
  注入 PYTHONPATH=mvp，不要写相对路径、不要 sys.path 手拼。
- 整片输出不包 ```python 围栏也可以（桥按纯代码读取）；但必须**一次交齐 visual_script 要求的全部
  Shot 类**，缺任何一镜判 FAIL。
- 口播不上屏：无字幕、无 narration 文本；屏上只留短标注（T()）与 LaTeX 公式（MathTex）。
  唯一开场例外：Shot1 第 0 帧必须是首镜 opening_title 的大字版（宋体、居中、安全区内，随口播淡出）。
- 只输出 ```python 围栏的完整代码，不要解释。
"""




def build_m2(ctx: RunCtx) -> str:
    script = ctx.load_script() or {}
    specs = {}
    d = ctx.path("modelspec")
    if d.exists():
        for p in sorted(d.glob("shot*.json")):
            specs[p.stem] = p.read_text(encoding="utf-8")
    n = len(script.get("shots", []))
    # 机械修复（操作员，2026-10）：原版未把 brief.style 送进 M2 user prompt，
    # theme=light 类风格参数到 M2 断链。按任务要求补 _brief_line（只透传，不解读）。
    return (M2_BRIEF + "\n" + _brief_line(ctx) + "\n"
            + f"【任务】本片共 {n} 镜（类名 Shot1~Shot{n}），单文件多镜头类。"
            + "\n【visual_script.json 全文】\n" + json.dumps(script, ensure_ascii=False, indent=1)
            + "\n【ModelSpec 全文（modelspec/*.json）】\n"
            + "\n".join(f"--- {k} ---\n{v}" for k, v in specs.items()) + concretization_rule(ctx))


def segments_m2(ctx: RunCtx) -> list:
    """524/截断时的分段策略（照 .local/complex_trial/gateway.py run_m2 实战形态）：
    call#0=文件头+共享常量/辅助函数（≤80 行）；call#1..N=每镜一个类（≤140 行）。"""
    script = ctx.load_script() or {}
    shots = {sh.get("shot_no"): sh for sh in script.get("shots", [])}
    n = len(shots)

    def spec_of(k) -> str:
        p = ctx.path("modelspec") / f"shot{k}.json"
        return p.read_text(encoding="utf-8") if p.exists() else "（静态版式镜，无 ModelSpec）"

    # 机械修复（操作员，2026-10）：分段策略各段此前不带 brief.style，风格参数在分段路径断链。
    brief = "\n" + _brief_line(ctx)
    rule = concretization_rule(ctx)   # 每段尾部附加具象化 rule 原文（分段路径同样生效）
    segs = [M2_BRIEF + brief + f"\n【任务】本片共 {n} 镜（类名 Shot1~Shot{n}，逐镜由后续段生成）。你只写文件头："
            "module docstring + 全部 import + 共享常量 + 共享辅助函数。总行数 ≤80，不写任何 Shot 类。"
            f"\n【全片 visual_script.json】\n{json.dumps(script, ensure_ascii=False, indent=1)}" + rule]
    for k in sorted(shots):
        segs.append(M2_BRIEF + brief + f"\n【任务】续写同一文件：只输出 Shot{k} 一个类（不重复 import/文件头/共享常量）。"
                    f"总行数 ≤140，务必紧凑。\n【Shot{k} 的 visual_script 条目】\n"
                    + json.dumps(shots[k], ensure_ascii=False, indent=1)
                    + f"\n【Shot{k} ModelSpec】\n{spec_of(k)}" + rule)
    return segs


def segments_m1(ctx: RunCtx) -> list:
    """机械修复（操作员，2026-10）：M1 未注册分段策略，10 镜 ModelSpec 单发 max_tokens=4000
    常截断无法恢复。按 visual_script 镜数分组，_stitch_json 对 specs 列表机械串接。
    粒度调 1（逐镜分段）：单段 4 镜的 ModelSpec 输出在网关 120s 窗口内必 524
    （substitution_trial 实测两轮 ×3 attempt 全 524），逐镜分段是任务书既定纪律。"""
    script = ctx.load_script() or {}
    shot_nos = [sh.get("shot_no") for sh in script.get("shots", [])]
    base = build_m1(ctx)
    segs = []
    for i in range(0, len(shot_nos), 1):
        grp = shot_nos[i:i + 1]
        segs.append(
            base + f"\n\n【本次为分段输出：只出 shot_no {grp} 的 ModelSpec】其余镜由相邻段输出，"
            f"本段不得越界、不得重复。顶层输出 {{\"specs\":[...]}}（每项含 shot_no）。"
            f"静态版式镜（sim_kind≠sim）跳过不出 spec。只输出 JSON。")
    return segs


def build_a8(ctx: RunCtx) -> str:
    script = ctx.load_script() or {}
    labels = [{"shot": sh.get("shot_no"), "seconds": sh.get("seconds_budget")}
              for sh in script.get("shots", [])]
    return ("# A8' 动态视觉回审材料\n\n【镜头标签清单（不给 KP 和口播，避免评科学性）】\n"
            + json.dumps(labels, ensure_ascii=False, indent=1)
            + "\n\n帧序列拼图（contact sheet，每镜 6~9 帧等间隔连排、带 t 标）随本消息以图片给出"
              "（sheets/*.png）。先自测能否读图：读不了立即报 BLOCKED。"
              "每条 issue 含 shot、sheet 格位、code、现象描述。最后一行必须是 `verdict: PASS` 或 `verdict: FAIL`。")


def build_images_a8(ctx: RunCtx) -> list:
    d = ctx.path("sheets")
    return sorted(d.glob("*.png")) if d.exists() else []


def build_s22(ctx: RunCtx) -> str:
    script = ctx.load_script() or {}
    return ("# S22 独立评分材料\n\n【visual_script.json（旁白+屏上文字）】\n"
            + json.dumps(script, ensure_ascii=False, indent=1)
            + "\n\n【KP JSON】\n" + json.dumps(ctx.load_kp() or {}, ensure_ascii=False, indent=1)
            + "\n\n帧序列拼图随本消息以图片给出（sheets/*.png）。不给上游棒推理过程与 A8 报告。"
              "先过 G1/G3，再给 S1~S5、U1~U5、M 维 M1~M5（每个 <5 的分附 sheet 格位证据）。"
              "最后一行必须是 `verdict: PASS` 或 `verdict: FAIL`。")


# ---------------------------------------------------------------- 注册表

STAGES: dict[str, Stage] = {}


def _reg(st: Stage) -> Stage:
    STAGES[st.name] = st
    return st


_reg(Stage("K1", "K1", "K1_SYSTEM.md", build_user=build_k1,
           segments=segments_k1, stitch="json",
           outputs=["kp_draft.json"], validate=validate_k1, save_output=save_k1,
           next_on_pass="K2", next_on_fail="BLOCKED",
           task_line="把备料摘录写成可入库、可逐句核对的 KP 条目 JSON（含 figure_refs 登记）"))

_reg(Stage("K2", "K2", "K2_SYSTEM.md", build_user=build_k2,
           outputs=["reports/K2.md"], validate=validate_k2,
           needs_isolated_context=True,
           next_on_pass=route_k2_pass, next_on_fail="K1",     # O 表：K2 FAIL→K1，改完重过 K2
           task_line="独立核对 KP 每条数值/公式/结论/refs 是否被原文支持"))

_reg(Stage("P", "P", "P_SYSTEM.md", build_user=build_p, build_images=build_images_p,
           outputs=["figurespec/"], validate=lambda t, c: v_json_fields(
               t, c, ("pdf", "page", "figure_no", "caption", "level", "confidence"),
               list_key="figurespecs"),
           save_output=save_figurespec, needs_isolated_context=True,
           next_on_pass="V0", next_on_fail="K2",              # A 级 confidence<0.6 → 报 K2 复核
           task_line="把教材静态插图转写成结构化 FigureSpec"))

_reg(Stage("V0", "V0", "V0_SYSTEM.md", build_user=build_v0, segments=segments_v0,
           outputs=["visual_script.json"], validate=validate_v0, save_output=save_v0,
           next_on_pass="M1", next_on_fail="BLOCKED",
           task_line="视觉-first 编剧：先定画面叙事再配口播，产出 visual_script.json"))

_reg(Stage("M1", "M1", "M1_SYSTEM.md", build_user=build_m1, segments=segments_m1,
           parallel_segments=True,      # 81-F1：分段路径按镜并行（默认 3，env QX_FLOW_M1_WORKERS 覆盖）
           outputs=["modelspec/"], validate=validate_m1, save_output=save_m1,
           next_on_pass="M2", next_on_fail="BLOCKED",
           task_line="把画面叙事翻译成可被确定性引擎执行的 ModelSpec"))

_reg(Stage("M2", "M2", "M2_SYSTEM.md", build_user=build_m2, segments=segments_m2,
           stitch="text",
           outputs=["generated/"], validate=validate_m2, save_output=save_m2,
           next_on_pass="A4", next_on_fail="BLOCKED",
           task_line="把 ModelSpec 写成 ManimCE 场景代码（physics/ 引擎驱动）"))

_reg(Stage("A4", "A4", "", deterministic=True, validate=validate_a4, save_output=save_a4,
           outputs=["review.json"],
           next_on_pass="R", next_on_fail=route_a4_fail,
           task_line="确定性闸门：review.check（旧 18 码）+ flow 层 physics_gates PHYS_* 六闸门（modelspec/ 输入，违规按码路由 M1/M2）"))

_reg(Stage("R", "R", "", deterministic=True,
           outputs=["final/"],
           next_on_pass="A8", next_on_fail=route_r_fail,
           task_line="TTS + 逐镜渲染 + concat/mux + selfcheck（确定性出片）"))

_reg(Stage("A8", "A8", "A8_SYSTEM.md", build_user=build_a8, build_images=build_images_a8,
           outputs=["reports/A8.md"], validate=validate_verdict,
           needs_isolated_context=True,
           next_on_pass="S22", next_on_fail=route_a8_fail,
           task_line="只看帧序列拼图报视觉/运动缺陷码"))

_reg(Stage("S22", "S22", "S22_SYSTEM.md", build_user=build_s22, build_images=build_images_a8,
           outputs=["reports/S22.md"], validate=validate_verdict,
           needs_isolated_context=True,
           next_on_pass="DONE", next_on_fail=route_s22_fail,
           task_line="独立评分：G1/G3 一票否决 + S/U/M 维"))

ORDER = ("K1", "K2", "P", "V0", "M1", "M2", "A4", "R", "A8", "S22")
