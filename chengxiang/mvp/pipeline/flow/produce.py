# -*- coding: utf-8 -*-
"""flow v2 → 生产路径编排层（SubTask #79-D1a：R7 接线 + QX_LLM_FLOW 开关 + 逐镜回退）。

这一层把 bridge/stages 验证过的 M2 契约（LLM 写 manim 场景类 + physics 引擎真渲染）
接进 mvp/run.py 的出片主路径：

  开关：env QX_LLM_FLOW=1 且 subject 命中白名单（缺省 {"physics"}，可用
        QX_LLM_FLOW_SUBJECTS 逗号分隔覆盖）才走 flow；缺省关=现网行为逐字不变。
        run.py 只在开关打开时才 import 本模块——关着时不碰 flow 任何东西。

  逐镜（项目纪律「一步失败不整段崩」）：
    每镜独立：网关生成 ShotN 场景类 → manim 渲染；任何一环失败（网关拒答/代码校验
    不过/渲染崩/时长对不上）→ **该镜**回退旧 A3 原语拼装（scene.py Explainer 吃
    单镜 plan.json，PLAN_JSON 机制与现网同源），不拖垮全片；连回退渲染都失败才抛给
    run.py，由 run.py 兜最后一层（整片改走旧 A5 渲染）。逐镜记账进 log["flow"]。

  R7 接线（SubTask.txt #69 欠账的自动化）：
    - write_produce_script / ensure_produce_script：为每个 run 自动落
      .local/<run>/produce.py（bridge.run_deterministic_R 的驱动对象），R 不再因
      「没有 produce.py」BLOCKED；生成的 produce.py 只做确定性半程（渲染+concat），
      不重复烧网关额度。
    - ensure_plan / plan_from_script：A4 需要的 plan.json 缺失时，从本 run 的
      visual_script.json 机械合成（逐字搬运 narration/seconds，屏上标注→callout 原语），
      不做任何语义改写。渲染端 PYTHONPATH=mvp 注入沿用 bridge.run_deterministic_R
      与现网 run.py 的既有机制（_render_env）。

红线照旧：不打印/记录任何 API 密钥；语义产出（M2 场景代码）一律走网关 llm_client.chat。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .. import ir, llm_client, mux
from .stages import M2_BRIEF, ROOT, MVP, physics_api_errors

FLOW_ENV = "QX_LLM_FLOW"
FLOW_SUBJECTS_ENV = "QX_LLM_FLOW_SUBJECTS"
DEFAULT_SUBJECTS = ("physics",)
GEN_ATTEMPTS = 2          # 单镜 M2：首次 + 带错误清单回喂 1 次，再不行就回退（不烧整片）
MANIM_DEFAULT = str(Path(os.environ.get("MVP_MANIM_BIN") or shutil.which("manim")
                         or (ROOT / ".local" / "t314" / "Scripts" / "manim.exe")))
QUALITY_FLAGS = {   # 与 run.py QUALITY 同形态；独立一份是为了 produce.py 独立可跑
    "draft": ["-q", "l"],
    "hd": ["-q", "m"],
    "fullhd": ["-r", "1920,1080", "--fps", "30"],
}


# ---------------------------------------------------------------- 开关

def whitelist(env: dict | None = None) -> tuple[str, ...]:
    # env is None 才读 os.environ：空 dict 是"显式无变量"（测试/嵌入调用），不能落回进程环境，
    # 否则 QX_LLM_FLOW=1 会穿过一个本该干净的 env 把 flow 偷偷打开。
    raw = (os.environ if env is None else env).get(FLOW_SUBJECTS_ENV, "").strip()
    if not raw:
        return DEFAULT_SUBJECTS
    return tuple(s.strip().lower() for s in raw.split(",") if s.strip())


def flow_enabled(subject: str, env: dict | None = None) -> bool:
    """QX_LLM_FLOW=1 **且** subject 命中白名单才开（缺省关）。语义与 QX_LLM_* 家族一致：
    只有值恰好是 "1" 才算开。白名单比对大小写不敏感。"""
    e = os.environ if env is None else env
    if e.get(FLOW_ENV) != "1":
        return False
    return str(subject or "").strip().lower() in whitelist(e)


# ---------------------------------------------------------------- M2 场景代码（走网关）

_FENCE_RE = re.compile(r"```python\n(.*?)\n```", re.S)


def extract_code(text: str) -> str:
    codes = _FENCE_RE.findall(text or "")
    return "\n\n\n".join(c.strip() for c in codes) if codes else (text or "").strip()


def scene_code_errors(code: str, shot_no: int) -> list[str]:
    """单镜产物的确定性校验（对齐 stages.validate_m2，但对象是生产 plan 的镜号）。"""
    errs: list[str] = []
    if not re.search(rf"\bclass\s+Shot{shot_no}\b", code):
        errs.append(f"输出里没有 class Shot{shot_no} 场景类")
    try:
        compile(code, f"<m2_scene_{shot_no}>", "exec")
    except SyntaxError as e:
        errs.append(f"场景代码语法错误：{e}")
    else:
        errs += physics_api_errors(code)
    return errs


def shot_prompt(shot: dict, brief: dict, n_shots: int, shot_no: int | None = None) -> str:
    """单镜 M2 user prompt：M2_BRIEF 契约 + brief/style 逐字透传 + 该镜 plan 条目。
    生产路径没有 visual_script/modelspec，画面意图取 storyboard 原语（visuals）。

    shot_no 是**本片内的 1-based 镜序**，不是 plan 的 index（plan 的 index 从 0 起）：
    M2_BRIEF 的类名契约是 Shot1..ShotN，两者混用会让首镜被判成 Shot0 而反复校验失败。"""
    no = int(shot_no if shot_no is not None else (shot.get("index") or 0) + 1)
    payload = {k: shot.get(k) for k in ("index", "title", "seconds", "narration", "visuals")}
    return (M2_BRIEF + "\n"
            + "【brief（逐字）】" + json.dumps(
                {k: brief.get(k) for k in ("subject", "grade", "topic", "target_seconds", "style")},
                ensure_ascii=False) + "\n"
            + f"【任务】本片共 {n_shots} 镜；本文件**只含 Shot{no} 一个场景类**，"
              "文件必须自包含（顶部 import 齐全 + 这一个类）。类常量 SECONDS 必须逐字等于 "
              f"payload 的 seconds（{shot.get('seconds')}s），construct 末尾 self.wait 补齐到恰好 SECONDS。\n"
            + f"【该镜 plan 条目】\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n"
            + "【渲染口径】画面内容依据 visuals 原语与 narration 语义自行编排；"
              "口播不上屏；只输出一个 ```python 围栏的完整场景文件，不要解释。")


def gen_shot_scene(shot: dict, brief: dict, n_shots: int,
                   attempts: int = GEN_ATTEMPTS, shot_no: int | None = None) -> tuple[str | None, list[str]]:
    """单镜走网关生成场景代码；全部尝试失败返回 (None, 错误清单)——调用方负责回退。"""
    system = (MVP / "pipeline" / "flow" / "prompts" / "M2_SYSTEM.md").read_text(encoding="utf-8")
    no = int(shot_no if shot_no is not None else (shot.get("index") or 0) + 1)
    user = shot_prompt(shot, brief, n_shots, shot_no=no)
    errs: list[str] = []
    for k in range(attempts):
        prompt = user if k == 0 else user + "\n\n【上一轮输出的错误清单，逐条修复后重新输出完整场景文件】\n- " + "\n- ".join(errs)
        try:
            text = llm_client.chat("M2", system, prompt, max_tokens=8000)
        except llm_client.LLMError as e:
            errs = [f"网关调用失败：{e}"]      # 网关挂了不必回喂——直接回退，省额度
            break
        code = extract_code(text)
        errs = scene_code_errors(code, no)
        if not errs:
            return code, []
    return None, errs


# ---------------------------------------------------------------- 渲染（确定性）

def _render_env(ffmpeg_dir=None) -> dict:
    """渲染子进程环境：PYTHONPATH=mvp（M2 场景 `from render.scene import …` 的前提，
    与 bridge.run_deterministic_R 注入同源）+ ffmpeg 进 PATH。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(MVP) + os.pathsep + env.get("PYTHONPATH", "")
    if ffmpeg_dir:
        env["PATH"] = str(ffmpeg_dir) + os.pathsep + env["PATH"]
    return env


def render_scene_file(scene_file: Path, scene_name: str, media_dir: Path,
                      manim: str, quality_flags: list[str], env: dict,
                      log_dir: Path | None = None) -> Path:
    """manim 渲染一个场景类，返回产出的 mp4 路径；失败抛 RuntimeError（尾日志进消息）。"""
    cmd = [manim, *quality_flags, "--media_dir", str(media_dir), "--disable_caching",
           str(scene_file), scene_name]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(MVP), env=env)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"render_{scene_name}.log").write_text(
            (r.stdout or "") + "\n=== STDERR ===\n" + (r.stderr or ""), encoding="utf-8")
    vid = next(iter(sorted(media_dir.glob(f"**/{scene_name}.mp4"))), None)
    if r.returncode != 0 or vid is None:
        tail = "\n".join(((r.stderr or r.stdout or "").strip().splitlines())[-25:])
        raise RuntimeError(f"{scene_name} 渲染失败（rc={r.returncode}）:\n{tail}")
    return vid


def single_shot_plan_dict(plan_dict: dict, i: int) -> dict:
    """取 plan 的第 i 镜拼成单镜 plan dict（逐镜回退旧 A3 原语用的输入）。"""
    shot = plan_dict["shots"][i]
    d = dict(plan_dict)
    d["shots"] = [shot]
    d["total_seconds"] = shot["seconds"]
    return d


def render_fallback_shot(plan_dict: dict, i: int, out_dir: Path, media_dir: Path,
                         env: dict, manim: str, quality_flags: list[str]) -> Path:
    """逐镜回退 = 旧 A3 路径同款渲染：scene.py Explainer 吃单镜 plan.json（PLAN_JSON）。
    不改 scene.py、不改 storyboard——只把现网渲染的调用形态按镜切一小片。"""
    no = int(plan_dict["shots"][i].get("index") or (i + 1))
    gen = out_dir / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    sub_plan = single_shot_plan_dict(plan_dict, i)
    plan_p = gen / f"fallback_plan_shot{no:02d}.json"
    plan_p.write_text(json.dumps(sub_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    fb_env = dict(env, PLAN_JSON=str(plan_p))
    shot_media = media_dir / f"fallback_shot{no:02d}"
    cmd = [manim, *quality_flags, "--media_dir", str(shot_media), "-o", "silent.mp4",
           "--disable_caching", str(MVP / "render" / "scene.py"), "Explainer"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(MVP), env=fb_env)
    vid = next(iter(sorted(shot_media.glob("**/silent.mp4"))), None)
    if r.returncode != 0 or vid is None:
        tail = "\n".join(((r.stderr or r.stdout or "").strip().splitlines())[-25:])
        raise RuntimeError(f"shot{no} 回退渲染失败（rc={r.returncode}）:\n{tail}")
    return vid


def concat_videos(videos: list[Path], out_path: Path, listfile: Path) -> Path:
    """逐镜 mp4 → silent.mp4（-c copy，同 manim 档位产物同参数，complex_trial 实战形态）。"""
    listfile.parent.mkdir(parents=True, exist_ok=True)
    listfile.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in videos),
                        encoding="utf-8")
    subprocess.run([mux._ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listfile), "-c", "copy", str(out_path)], check=True)
    return out_path


# ---------------------------------------------------------------- 主编排（run.py 调用面）

def render_flow(out_dir: Path, plan_dict: dict, brief_dict: dict, log: dict,
                manim: str, quality_flags: list[str], ffmpeg_dir=None) -> Path:
    """flow 路径的 A5：逐镜（M2 场景类 → manim；失败逐镜回退旧 A3 原语）→ concat。

    返回 out_dir/silent.mp4；每镜的 source/error 落 log["flow"] 与 generated/flow_render.json。
    仅当**回退渲染都失败**（工具性）才抛 RuntimeError，由 run.py 兜整片旧渲染。"""
    t0 = time.time()
    gen = out_dir / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    media = out_dir / "media_flow"
    env = _render_env(ffmpeg_dir)
    brief_flat = {**{k: v for k, v in brief_dict.items() if k in
                     ("subject", "grade", "topic", "target_seconds")},
                  "style": brief_dict.get("style") or "clean"}
    n = len(plan_dict["shots"])
    records: list[dict] = []
    videos: list[Path] = []
    for i, shot in enumerate(plan_dict["shots"]):
        no = int(shot.get("index") if shot.get("index") is not None else (i + 1))
        pos = i + 1                       # 类名 Shot1..ShotN（M2 契约），与 plan index(0 起) 解耦
        rec = {"shot": no, "source": "m2", "error": None}
        try:
            code, errs = gen_shot_scene(shot, brief_flat, n, shot_no=pos)
        except Exception as e:            # noqa: BLE001 网关/提示词/落盘的任何一环失败都只塌这一镜
            code, errs = None, [f"生成异常：{type(e).__name__}: {e}"]
        vid = None
        if code:
            scene_file = gen / f"shot_{pos:02d}_scene.py"
            scene_file.write_text(code + "\n", encoding="utf-8")
            try:
                vid = render_scene_file(scene_file, f"Shot{pos}", media, manim,
                                        quality_flags, env, log_dir=out_dir / "reports")
                want = float(shot.get("seconds") or 0)
                got = mux.probe_duration(vid)
                if want and got and abs(got - want) > max(0.75, 0.10 * want):
                    rec["error"] = f"M2 成片时长 {got:.2f}s 与预算 {want:.2f}s 不符，回退"
                    vid = None
                    # 时长不合格的成片不能留给 R 棒重放（drive_r 只看 shot_XX_scene.py 是否存在，
                    # 留着会让 produce.py all 重新渲出这条坏镜），改名留档 = 该镜在 R 里也回退。
                    scene_file.replace(scene_file.with_suffix(".rejected.py"))
            except Exception as e:        # noqa: BLE001 渲染崩/ffmpeg 探不到时长同样只塌这一镜
                rec["error"] = f"M2 渲染/时长校验失败，回退：{str(e)[-400:]}"
                vid = None
        else:
            rec["error"] = "M2 生成失败，回退：" + "；".join(errs)[:400]
        if vid is None:
            rec["source"] = "a3_fallback"
            vid = render_fallback_shot(plan_dict, i, out_dir, media, env, manim, quality_flags)
        rec["video"] = str(vid.relative_to(out_dir)).replace("\\", "/")
        videos.append(vid)
        records.append(rec)
    silent = out_dir / "silent.mp4"
    concat_videos(videos, silent, gen / "concat_list.txt")
    fallbacks = [r for r in records if r["source"] != "m2"]
    (gen / "flow_render.json").write_text(json.dumps(
        {"model_m2": llm_client.model_for("M2"), "shots": records},
        ensure_ascii=False, indent=2), encoding="utf-8")
    log["flow"] = {**(log.get("flow") or {}),
                   "enabled": True,
                   "model_M2": llm_client.model_for("M2"),
                   "shots": len(records), "fallback_shots": [r["shot"] for r in fallbacks],
                   "fallback_detail": [{"shot": r["shot"], "error": r["error"]} for r in fallbacks],
                   "seconds": round(time.time() - t0, 1)}
    return silent


# ---------------------------------------------------------------- R7：produce.py 自动生成

PRODUCE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""produce.py —— flow R7 接线自动生成的 R 棒驱动（pipeline.flow.produce.write_produce_script）。

bridge.run_deterministic_R 的驱动对象：`python produce.py all` = 逐镜渲染 + concat 出 silent.mp4。
只跑确定性半程（不重烧网关额度）：generated/shot_XX_scene.py 是 M2 已定稿产物，缺文件/渲染崩
的镜自动走旧 A3 原语回退（scene.py Explainer 吃单镜 plan.json）。TTS/mux 由 run.py 主路径负责，
本文件不重复。

用法（cwd=mvp，PYTHONPATH 由 bridge 统一注入）：
  python ../.local/<run>/produce.py render|concat|all
"""
import sys

CFG = {cfg!r}

from pipeline.flow.produce import drive_r  # noqa: E402

if __name__ == "__main__":
    sys.exit(drive_r(CFG, sys.argv[1:] or ["all"]))
'''


def write_produce_script(out_dir: Path, quality: str = "fullhd", manim: str | None = None) -> Path:
    """R7 环境准备自动化：为该 run 落 .local/<run>/produce.py（幂等，覆盖重写）。"""
    cfg = {"run_dir": str(Path(out_dir).resolve()),
           "quality": quality,
           "quality_flags": QUALITY_FLAGS.get(quality, QUALITY_FLAGS["fullhd"]),
           "manim": manim or MANIM_DEFAULT}
    d = ROOT / ".local" / Path(out_dir).name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "produce.py"
    p.write_text(PRODUCE_TEMPLATE.format(cfg=cfg), encoding="utf-8")
    return p


def ensure_produce_script(run_dir: Path) -> Path | None:
    """bridge R 棒入口：run 缺 produce.py 就补一个（#69 欠账的自动化），已有则不动。"""
    run_dir = Path(run_dir)
    target = ROOT / ".local" / run_dir.name / "produce.py"
    if target.exists():
        return target
    plan_p = run_dir / "plan.json"
    if not plan_p.exists():
        return None
    q = "fullhd"
    try:
        write_produce_script(run_dir, quality=q)
    except OSError:
        return None
    return target if target.exists() else None


def drive_r(cfg: dict, phases: list[str]) -> int:
    """生成的 produce.py 的实体：确定性重放 render_flow 的渲染半程（不调网关）。"""
    out_dir = Path(cfg["run_dir"])
    plan_p = out_dir / "plan.json"
    if not plan_p.exists():
        print(f"BLOCKED: {plan_p} 不存在（R 需要 run 的 plan.json）", file=sys.stderr)
        return 1
    plan_dict = json.loads(plan_p.read_text(encoding="utf-8"))
    flags = cfg.get("quality_flags") or QUALITY_FLAGS.get(cfg.get("quality", "fullhd"))
    manim = cfg.get("manim") or MANIM_DEFAULT
    phase = (phases or ["all"])[0]
    media = out_dir / "media_flow"
    gen = out_dir / "generated"
    env = _render_env()
    videos: list[Path] = []
    records: list[dict] = []
    for i, shot in enumerate(plan_dict["shots"]):
        no = int(shot.get("index") if shot.get("index") is not None else (i + 1))
        pos = i + 1                       # 与 render_flow 同口径：类名/文件名按 1-based 镜序
        rec = {"shot": no, "source": "m2", "error": None}
        scene_file = gen / f"shot_{pos:02d}_scene.py"
        vid = None
        if scene_file.exists():
            try:
                vid = render_scene_file(scene_file, f"Shot{pos}", media, manim, flags,
                                        env, log_dir=out_dir / "reports")
            except RuntimeError as e:
                rec["error"] = str(e)[-400:]
                vid = None
        else:
            rec["error"] = "generated 里没有本镜场景文件——回退旧 A3 原语"
        if vid is None:
            rec["source"] = "a3_fallback"
            vid = render_fallback_shot(plan_dict, i, out_dir, media, env, manim, flags)
        rec["video"] = str(vid.relative_to(out_dir)).replace("\\", "/")
        videos.append(vid)
        records.append(rec)
        print(f"shot{no}: {rec['source']} -> {rec['video']}", flush=True)
    if phase == "render":
        return 0
    silent = concat_videos(videos, out_dir / "silent.mp4", gen / "concat_list.txt")
    (gen / "flow_render.json").write_text(json.dumps(records, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(f"silent: {silent} dur={mux.probe_duration(silent)}", flush=True)
    return 0


# ---------------------------------------------------------------- R7：plan.json 机械合成（A4 欠账）

def plan_from_script(script: dict, brief: dict, kp: dict | None) -> dict:
    """visual_script.json → plan.json 形态的机械映射（逐字搬运，零语义改写）：
    narration/seconds_budget/屏上标注 原样进 shots；标注 → callout 原语只为让 A4 的
    图形/字数闸门有账可查，不代表任何渲染承诺。"""
    shots = []
    for sh in script.get("shots") or []:
        no = int(sh.get("shot_no") or (len(shots) + 1))
        notes = [str(t) for t in (sh.get("屏上标注") or []) if str(t).strip()]
        ot = str(sh.get("opening_title") or "")
        visuals = [{"kind": "title", "props": {"text": ot}}] if ot else []
        visuals += [{"kind": "callout", "props": {"text": t}} for t in notes]
        visuals = [v for v in visuals if v]
        shots.append({
            "index": no,
            "title": str(sh.get("opening_title") or (notes[0] if notes else f"Shot{no}")),
            "seconds": float(sh.get("seconds_budget") or 0),
            "spoken": 0.0,
            "narration": str(sh.get("narration") or ""),
            "voiceover": "",
            "emphasis": "",
            "kp_refs": [],
            "visuals": visuals,
            "subtitles": ir.Shot(index=no, title="", seconds=float(sh.get("seconds_budget") or 0),
                                 narration=str(sh.get("narration") or ""),
                                 visuals=[]).subtitles(),
        })
    b = ir.Brief(subject=str(brief.get("subject") or "physics"),
                 grade=str(brief.get("grade") or "H1"),
                 topic=str(brief.get("topic") or ""),
                 target_seconds=int(float(brief.get("seconds") or 120)),
                 style="clean")
    return {"version": ir.SPEC_VERSION,
            "knowledge_id": (kp or {}).get("id") or "kp.flow.synthetic",
            "refs": (kp or {}).get("refs", []),
            "brief": ir.asdict(b),
            "total_seconds": round(sum(s["seconds"] for s in shots), 2),
            "shots": shots}


def ensure_plan(ctx) -> bool:
    """bridge A4 棒入口：run_dir/plan.json 缺失但有 visual_script.json（flow 链条 V0 产物）
    → 机械合成一份落盘（R7 接线）；成功 True，无可合成物 False（调用方照旧报 BLOCKED）。"""
    run_dir = Path(ctx.run_dir)
    plan_p = run_dir / "plan.json"
    if plan_p.exists():
        return True
    script_p = run_dir / "visual_script.json"
    if not script_p.exists():
        return False
    try:
        script = json.loads(script_p.read_text(encoding="utf-8"))
        plan = plan_from_script(script, ctx.brief or {}, ctx.load_kp())
    except (OSError, ValueError, TypeError) as e:
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "reports" / "A4_plan_synthesize_error.md").write_text(str(e), encoding="utf-8")
        return False
    plan_p.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
