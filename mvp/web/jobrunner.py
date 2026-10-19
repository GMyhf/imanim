"""澄象 MVP · 任务子进程执行器（被 server.py 以子进程方式调用）

为什么单独一个文件：渲染一条要 30~100s，必须与 HTTP 线程隔离；且 ffmpeg 对中文路径不稳，本执行器只处理纯 ASCII 的任务目录。

两种模式（都不修改 mvp/ 下任何既有代码，只 import 复用）：
  --mode generate  从 Brief 出发跑整条链路。直接调用 mvp/run.py 的 generate()，
                   但用 import 而不是 argparse CLI —— run.py 的命令行没有
                   --prior-knowledge / --raw-text 两个开关（Spec_Product 第 2 节的
                   选填项），走 argparse 会丢掉输入契约的两项。
  --mode render    从「用户改过的 plan.json」出发重出片（Spec 第 4 节：分镜是一等公民）。
                   run.py 没有这个入口（它总是重新 storyboard.build），所以这里复用
                   run.py 的常量与 _run()，按 配音→静态监督→渲染→合成 重跑后半段。

进度：写 <job_dir>/run/progress.json（原子替换），server.py 轮询该文件即可拿到阶段名与耗时。
结果：写 <job_dir>/run/result.json。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
MVP_DIR = WEB_DIR.parent
sys.path.insert(0, str(MVP_DIR))

import run as cli  # noqa: E402  mvp/run.py：复用 QUALITY / MANIM / _run / generate
from audio import tts  # noqa: E402
from pipeline import knowledge, kp_draft, llm_client, mux, review, selfcheck, storyboard  # noqa: E402
from pipeline import storyboard_llm  # noqa: E402
from pipeline import voiceover  # noqa: E402
from pipeline.ir import SHOT_HEAD, SHOT_TAIL, Brief, Plan  # noqa: E402

# 阶段中文名（对应 Spec_Workflow 的 A2~A7，前端按这个顺序画进度条）
STAGES = [
    ("retrieve", "检索知识点库"),
    ("draft", "起草知识点（库外）"),
    ("storyboard", "生成分镜"),
    ("narration", "配音合成"),
    ("review", "静态监督检查"),
    ("render", "画面渲染"),
    ("mux", "音幕合成"),
]


class Progress:
    """阶段进度写盘器。只记开始一次、结束一次，重复调用安全（TTS 每镜头都调）。"""

    def __init__(self, path: Path):
        self.path = path
        self.started_at = time.time()
        self.cur = None
        self.stages = []
        self.note = ""
        self.save()

    def begin(self, key: str) -> None:
        for s in self.stages:
            if s["key"] == key and s["started"] is not None:
                return
        self.cur = key
        self.stages.append({"key": key, "label": dict(STAGES).get(key, key),
                            "started": time.time(), "ended": None})
        self.save()

    def end(self, key: str) -> None:
        for s in self.stages:
            if s["key"] == key and s["ended"] is None:
                s["ended"] = time.time()
        if self.cur == key:
            self.cur = None
        self.save()

    def finish(self, **extra) -> None:
        self.cur = "done"
        self.extra = extra
        self.save()

    def fail(self, msg: str) -> None:
        self.cur = "failed"
        self.note = msg
        self.save()

    def save(self) -> None:
        payload = {
            "stage": self.cur,
            "stages": self.stages,
            "started_at": self.started_at,
            "updated_at": time.time(),
            "elapsed": round(time.time() - self.started_at, 1),
            "note": self.note,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)


def instrument(pg: Progress) -> None:
    """generate() 是一整块黑盒，这里在模块属性上包一层，把它内部的调用点映射到阶段名。

    只包不替：原函数照常执行，run.py 的行为一个字节都没改。
    """
    def wrap(owner, name, key):
        orig = getattr(owner, name)

        def inner(*a, **k):
            pg.begin(key)
            try:
                return orig(*a, **k)
            finally:
                pg.end(key)

        setattr(owner, name, inner)

    def wrap_begin_only(owner, name, key):
        """只标记阶段开始：拼音轨与混流是两个调用，阶段耗时要以最后一个为准。"""
        orig = getattr(owner, name)

        def inner(*a, **k):
            pg.begin(key)
            return orig(*a, **k)

        setattr(owner, name, inner)

    wrap(knowledge, "load", "retrieve")
    wrap(kp_draft, "draft", "draft")
    wrap(storyboard, "build", "storyboard")
    # 配音阶段要包在整段 _synthesize 上，而不是 tts.synth：synth 每镜头都调一次，
    # 而 Progress.begin/end 幂等，包 synth 会让"配音完成"在第一镜结束就被打上，
    # 后面几镜还在合成、前端却显示"画面渲染 待开始"，看起来像卡死（用户实测"经常卡"）。
    wrap(cli, "_synthesize", "narration")
    wrap(review, "check", "review")
    wrap(cli, "_run", "render")
    wrap_begin_only(mux, "build_track", "mux")
    wrap(mux, "mux", "mux")


def ascii_names(out_dir: Path, log: dict) -> dict:
    """主产物文件名带中文（{subject}-{grade}-{知识点}-…），下载/播放不稳，这里补 ASCII 副本。

    final.mp4 恒存在；burned.mp4 仅在字幕烧录成功时存在（mux.last_burn 是进程内状态，
    generate() 刚跑完时读它最准）。
    """
    names = {"plan": "plan.json", "srt": "subs.srt", "sidecar": "sidecar.json"}
    main = Path(log.get("artifact", ""))
    if main.exists():
        names["main"] = main.name
    burned_ok = bool(mux.last_burn.get("ok"))
    if burned_ok and main.exists():
        dst = out_dir / "burned.mp4"
        if not dst.exists():
            shutil.copy2(main, dst)
        names["burned"] = "burned.mp4"
    if not (out_dir / "final.mp4").exists() and main.exists():
        shutil.copy2(main, out_dir / "final.mp4")
    names["final"] = "final.mp4"
    return names


def do_generate(brief_data: dict, out_dir: Path, quality: str, pg: Progress) -> dict:
    fields = {k: v for k, v in brief_data.items() if k in Brief.__dataclass_fields__}
    brief = Brief(**fields)
    errs = brief.validate()
    if errs:
        raise ValueError("Brief 校验失败：" + "；".join(errs))
    # 知识点口径（2026-10-18 改）：库里命中就用库内容；库里没有不再当场拒绝，
    # 由 run.generate 走 K0 起草一条 origin=model_draft、refs 为空的条目再往下走（见 pipeline/kp_draft.py）。
    # 起草自身失败（未开 K0/模型自检不过）会让任务带着人话错误结束，不会出半成品。
    instrument(pg)
    # flow v2 生产开关（SubTask #79-D1a）：QX_LLM_FLOW=1 + subject 白名单的分叉在 cli.generate
    # 内部读 os.environ——server.py 用 Popen 继承环境，这里无需（也不应）额外传参；关闭时现网行为逐字不变。
    log = cli.generate(brief, out_dir, quality=quality)
    return {"ok": True, "mode": "generate", "names": ascii_names(out_dir, log), "sidecar": log}


def do_render(plan_file: Path, out_dir: Path, quality: str, pg: Progress, source_key: str = "") -> dict:
    """分镜改完之后：按新 narration 重测语音时长 → 过闸门 → 重渲 → 重合成。"""
    plan = Plan.load(plan_file)
    # 字幕只允许一层（与 run.py `if burn: brief.subtitles=False` 同源）：重渲/改进这条路径
    # 稍后必然把 subs.srt 烧进成片（mux 固定传 srt 路径），若画面层再画一遍字幕就叠成两行
    # 互相打架（用户实报「字幕重叠」）。关掉画面内字幕后，揭示节奏仍按口播字幕时间轴走，
    # 不受影响——scene._render_shot 在 show_caps=False 时只跳过画字幕、不跳过时间记账。
    plan.brief.subtitles = False
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {"steps": {}, "brief": plan.brief.__dict__}

    # 配音：时长以实测语音时长为唯一真源（与 run.generate/_synthesize 同一口径，81-A2）：
    # spoken 回写实测秒（字幕窗口按真实语音铺，不铺满整镜），秒数用 _spread_surplus 把
    # 用户手写的旧 seconds 只当**缺口封顶到 MAX_SHOT_IDLE** 的下限——旧版 max(user, need)
    # 把过期规划秒整块留在镜尾，语音早讲完、字幕还按全镜铺，正是 regenerate/improve 路径的
    # 音画不同步来源。
    log["voiceover"] = voiceover.apply(plan)
    pg.begin("narration")
    step = time.time()
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    fps = cli.QUALITY_FPS.get(quality, 30)
    needs: list[float] = []
    floors: list[float] = []
    for s in plan.shots:
        wav = audio_dir / f"shot_{s.index:02d}.wav"
        user_secs = round(float(s.seconds), 2)
        floors.append(user_secs)
        if plan.brief.narration:
            dur = tts.synth(s.voiceover or s.narration, wav, audio_dir)
            # 镜头总时长 = 淡入留白 + 实测口播 + 淡出留白；与 run.py / IR 用同一组常量。
            need = round(SHOT_HEAD + dur + SHOT_TAIL, 2)
            s.spoken = need       # 实测秒回写：subtitles()/speak_window 从此按语音铺
        else:
            need = 0.0
        needs.append(need)
    seconds = cli._spread_surplus(needs, floors) if plan.brief.narration else floors
    shot_wavs: list[tuple[float, Path]] = []
    for s, sec, start in zip(plan.shots, seconds, mux.cumulative_offsets(seconds, fps)):
        s.seconds = sec
        shot_wavs.append((start, audio_dir / f"shot_{s.index:02d}.wav"))
    log["steps"]["narration"] = round(time.time() - step, 2)
    pg.end("narration")
    log["audio_floor"] = {str(s.index): s.seconds for s in plan.shots}

    total = plan.total_seconds
    log["duration"] = {"actual": total, "target": plan.brief.target_seconds,
                       "deviation": round(abs(total - plan.brief.target_seconds) / plan.brief.target_seconds, 3)}

    # 静态监督闸门（用户改写过内容，必须重新过一遍；不过就不出片并报原因）
    pg.begin("review")
    step = time.time()
    kp = None
    try:
        # 与 run.py 同一签名：load(subject, topic, grade)，学段不符也当作未命中（不阻塞重渲，仅记一笔）
        kp = knowledge.load(plan.brief.subject, plan.brief.topic, plan.brief.grade)
    except Exception:  # 库里查不到时仍跑通用检查（不阻塞重渲），只在 sidecar 里记一笔
        log["kp_missing"] = True
    findings = review.check(plan, kp)
    (out_dir / "review.json").write_text(json.dumps(review.report(plan, kp), ensure_ascii=False, indent=2), encoding="utf-8")
    log["steps"]["review"] = round(time.time() - step, 2)
    pg.end("review")
    hard = review.blocking(findings)
    if hard:
        raise cli.GenerationError(
            "content",
            "静态监督未通过：\n" + "\n".join(
                f"  shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard),
            "可在下方修改分镜后重出片；或按上面清单精简口播、补限定语、把目标时长放宽。",
            findings=[{"shot": f["shot"], "code": f["code"], "msg": f["msg"]} for f in hard])

    plan_path = out_dir / "plan.json"
    plan.save(plan_path)
    (out_dir / "brief.json").write_text(
        json.dumps(plan.brief.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")

    # 渲染：与 run.py 同一命令，PLAN_JSON 指向改写后的分镜
    pg.begin("render")
    env = dict(os.environ, PATH=str(cli.FFMPEG_DIR) + os.pathsep + os.environ["PATH"],
               PLAN_JSON=str(plan_path))
    media = out_dir / "media"
    step = time.time()
    cli._retry(lambda: cli._run([cli.MANIM, *cli.QUALITY[quality], "--media_dir", str(media), "-o", "silent.mp4",
                                 "--disable_caching", str(cli.ROOT / "render" / "scene.py"), "Explainer"], env=env),
               desc="画面渲染")
    silent = next(iter(sorted(media.glob("**/silent.mp4"))), None)
    if silent is None:
        raise cli.GenerationError(
            "tool", f"渲染未产出 silent.mp4（media 目录：{media}）",
            "manim 渲染异常退出、未产出画面轨。请检查分镜里的版式原语是否受支持，或稍后重试。")
    shutil.move(str(silent), out_dir / "silent.mp4")
    log["steps"]["render"] = round(time.time() - step, 2)
    pg.end("render")

    # G2 时长闸门（与 run.py 一致）：成片时长必须与 Plan 时长 ±10% 内，否则渲染层时间记账漏了东西。
    rendered = mux.probe_duration(out_dir / "silent.mp4")
    if rendered is None:
        raise cli.GenerationError(
            "tool", "无法读取渲染产物时长（ffmpeg 未返回 Duration）",
            "ffmpeg 无法读取渲染产物时长，环境可能异常。请稍后重试，或联系维护者。")
    drift = abs(rendered - total) / total
    log["rendered"] = {"seconds": rendered, "plan": total, "drift": round(drift, 4)}
    if drift > 0.10:
        raise cli.GenerationError(
            "tool",
            f"渲染时长 {rendered}s 与 Plan {total}s 偏差 {drift:.1%} > 10%（Spec_Scale G2），出片中止",
            "渲染层的时间记账与分镜不一致，成片可能卡顿或冻屏。请反馈这条知识点并附上 plan.json。")

    # 合成 + G4 音画同轴闸门（与 run.py 一致）：每镜头语音起点必须落在 SHOT_HEAD 附近。
    pg.begin("mux")
    step = time.time()
    plan_dict = json.loads(plan_path.read_text(encoding="utf-8"))
    sec_list = [float(s["seconds"]) for s in plan_dict["shots"]]
    # 与 run.generate 同一口径：缓冲盖住帧网格量化后的末镜终点，越界部分由 -shortest 裁，
    # 不再截弃片尾语音。
    track_secs = max(total, mux.cumulative_offsets(sec_list + ([0.0] if sec_list else []), fps)[-1])
    mux.build_track(shot_wavs, track_secs, out_dir / "track.wav")
    onsets = mux.speech_onsets(out_dir / "track.wav")
    align = []
    for start, _ in shot_wavs:
        want = round(start + SHOT_HEAD, 2)
        cand = [o for o in onsets if o >= start - 0.05]
        align.append({"shot_start": round(start, 2), "expect": want,
                      "actual": round(cand[0], 2) if cand else None,
                      "delta": round(cand[0] - want, 2) if cand else None})
    log["audio_align"] = align
    bad = [a for a in align if a["delta"] is None or abs(a["delta"]) > 0.35]
    if bad:
        raise cli.GenerationError(
            "tool", f"音画时间轴错位（>0.35s）：{bad}",
            "音画时间轴错位，成片会声画不同步。请反馈这条知识点并附上 plan.json。")
    n_subs = mux.write_srt(plan_dict, out_dir / "subs.srt", fps=fps)
    final = cli._retry(lambda: mux.mux(out_dir / "silent.mp4", out_dir / "track.wav", out_dir / "final.mp4",
                                       out_dir / "subs.srt",
                                       shot_seconds=sec_list, fps=fps),
                       desc="音画合成")
    log["steps"]["mux"] = round(time.time() - step, 2)
    log["sfx"] = os.environ.get("MVP_SFX", "0")
    log["burn"] = dict(mux.last_burn)
    pg.end("mux")

    burned = mux.last_burn.get("ok")
    if burned:
        shutil.move(str(final), out_dir / "burned.mp4")
    artifact = final if not burned else out_dir / "final.mp4"
    if not (out_dir / "final.mp4").exists():
        shutil.copy2(final, out_dir / "final.mp4")
        artifact = out_dir / "final.mp4"

    kp_id = plan.knowledge_id
    name = f"{plan.brief.subject}-{plan.brief.grade}-{plan.brief.topic}-{int(total)}s-{plan.hash}.mp4"
    named = out_dir / name
    if artifact.exists() and named != artifact:
        shutil.copy2(artifact, named)

    # F-10 自检（与 run.py 同一套，保持两条入口的产物/证据同构，见 SubTask 42 的交付目录卫生同理）
    step = time.time()
    try:
        scan = selfcheck.scan_boundaries(named, plan_dict)
        selfcheck.contact_sheet(named, plan_dict, out_dir / "frames" / "contact_sheet.png")
        (out_dir / "boundary_scan.json").write_text(
            json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
        log["boundary_scan"] = {"unexpected": scan["unexpected"], "any_blank": scan["any_blank"]}
    except Exception as e:
        log["boundary_scan"] = {"error": str(e)}
    log["steps"]["selfcheck"] = round(time.time() - step, 2)

    size_mb = round(artifact.stat().st_size / 1e6, 1)
    log.update({
        "artifact": str(named),
        "size_mb": size_mb,
        "mb_per_min": round(size_mb / (total / 60), 1) if total else None,
        "subtitles": n_subs,
        "knowledge_id": kp_id,
        "refs": plan.refs,
        "shots": len(plan.shots),
        "wall_seconds": round(time.time() - t0, 1),
        "burned": burned,
        "regenerated_from": source_key or plan_file.parent.name,
    })
    (out_dir / "sidecar.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    # 交付目录卫生：与 run.py 同一套清理，但画廊按角色解析文件（server.py 只认 final/burned/named），
    # 所以这三个必须留住，其余过路产物一律清掉。
    freed = mux.cleanup_work(out_dir, keep=[named, out_dir / "final.mp4", out_dir / "burned.mp4"])
    if freed:
        log["cleaned_mb"] = round(freed / 1e6, 1)
        (out_dir / "sidecar.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    names = {"plan": "plan.json", "srt": "subs.srt", "sidecar": "sidecar.json",
             "main": named.name, "final": "final.mp4"}
    if burned:
        names["burned"] = "burned.mp4"
    return {"ok": True, "mode": "render", "names": names, "sidecar": log}


def do_improve(plan_file: Path, out_dir: Path, quality: str, pg: Progress, instruction: str,
               source_key: str = "") -> dict:
    """用户在成片下写的改进意见：把上一版分镜连同意见交给 A3 重写，再过一遍后半段。

    改进版照样过闸门；模型不可用或改到过不去，就带着人话原因失败、绝不毁掉已经出来的上一版
    （storyboard_llm.improve 内部 fallback=上一版，这里据 info.source 判断是否继续）。
    """
    if not llm_client.enabled("A3"):
        raise RuntimeError("改进需要开通生成环节（网关不可用或未配置）")
    plan = Plan.load(plan_file)
    brief = plan.brief
    out_dir.mkdir(parents=True, exist_ok=True)
    pg.begin("storyboard")
    try:
        kp = knowledge.load(brief.subject, brief.topic, brief.grade)
    except Exception:
        raise RuntimeError("源任务的知识点已不在库里（自动库被清理？），无法在它的条目上做改进")
    new_plan, info = storyboard_llm.improve(brief, kp, plan, instruction)
    pg.end("storyboard")
    if info["source"] != "llm":
        raise RuntimeError("改进版没能通过静态检查，已保留上一版成片：" + str(info.get("reason") or "模型未改写"))
    improved = out_dir / "plan_improved.json"
    new_plan.save(improved)
    result = do_render(improved, out_dir, quality, pg, source_key)
    result.setdefault("sidecar", {})["improve"] = {
        "instruction": instruction, "model": info["model"], "attempts": info["attempts"]}
    (out_dir / "sidecar.json").write_text(json.dumps(result["sidecar"], ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["generate", "render", "improve"])
    ap.add_argument("--job-dir", required=True)
    ap.add_argument("--quality", default="fullhd", choices=list(cli.QUALITY))
    ap.add_argument("--brief-file")
    ap.add_argument("--plan-file")
    ap.add_argument("--instruction-file")
    ap.add_argument("--source-key", default="")
    a = ap.parse_args()

    job_dir = Path(a.job_dir)
    out_dir = job_dir / "run"
    out_dir.mkdir(parents=True, exist_ok=True)
    pg = Progress(out_dir / "progress.json")
    res_file = job_dir / "result.json"

    try:
        if a.mode == "generate":
            brief_data = json.loads(Path(a.brief_file).read_text(encoding="utf-8"))
            result = do_generate(brief_data, out_dir, a.quality, pg)
        elif a.mode == "improve":
            instruction = Path(a.instruction_file).read_text(encoding="utf-8").strip()
            result = do_improve(Path(a.plan_file), out_dir, a.quality, pg, instruction, a.source_key)
        else:
            result = do_render(Path(a.plan_file), out_dir, a.quality, pg, a.source_key)
        result["elapsed"] = round(time.time() - pg.started_at, 1)
        pg.finish(**result["names"])
    except Exception as e:  # noqa: BLE001 子进程的异常要变成前端可读的结果，不能只留 traceback
        cause = e.__cause__
        detail = f"{type(e).__name__}: {e}"
        if isinstance(e, knowledge.KnowledgeNotFound) or getattr(cause, "candidates", None):
            detail = json.dumps({"error": str(e), "candidates": getattr(cause, "candidates", [])},
                               ensure_ascii=False)
        if isinstance(e, cli.GenerationError):
            # 内容 vs 工具两类失败都带一句可直接照做的建议；内容类额外附闸门清单（前端亮人话清单）。
            body = {"error": str(e), "kind": e.kind, "suggestion": e.suggestion}
            if e.kind == "content":
                body["findings_raw"] = str(e)
                body["findings"] = e.extra.get("findings", [])
            detail = json.dumps(body, ensure_ascii=False)
        if isinstance(e, RuntimeError) and "静态监督" in str(e):
            detail = json.dumps({"error": "静态监督未通过", "findings_raw": str(e)}, ensure_ascii=False)
        if isinstance(e, cli.DurationNotFeasible):
            # 口播放不进目标时长：给前端一组可直接显示的实测数字，而不是只给一句话。
            detail = json.dumps({
                "error": str(e), "kind": "duration_infeasible",
                "natural": e.natural, "fastest": e.fastest, "target": e.target,
                "suggest": int(round(e.fastest * 1.05)),
                "suggestion": (f"这条知识点的口播至少要 {int(round(e.fastest * 1.05))} 秒才讲得完，"
                               f"请把目标时长放宽，或精简口播。"),
            }, ensure_ascii=False)
        pg.fail(str(e)[:500])
        res_file.write_text(json.dumps({"ok": False, "error": detail, "traceback": _tb()},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(detail, file=sys.stderr)
        return 1

    res_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def _tb() -> str:
    import traceback
    return traceback.format_exc()[-3000:]


if __name__ == "__main__":
    sys.exit(main())
