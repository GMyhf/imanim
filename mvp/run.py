"""A0 总控：一条命令从 Brief 到成片。

用法（在 mvp/ 目录下）：
  python run.py --subject physics --grade H1 --topic 加速度 --seconds 120 --style clean

中间产物（brief.json / plan.json / review.json / subs.srt / sidecar.json）与成片一起留在
out/<run>/；配音与渲染的过路文件在出片成功后清掉（失败时保留，供查问题）。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from audio import tts  # noqa: E402
from pipeline import (knowledge, kp_draft, llm_client, mux, requirement_llm, review, scoring_llm,  # noqa: E402
                      selfcheck, storyboard, storyboard_llm, visual_review_llm, voiceover)
from pipeline import ir
from pipeline.ir import MAX_SHOT_IDLE, SHOT_HEAD, SHOT_TAIL, Brief  # noqa: E402

FFMPEG_DIR = Path(os.environ.get("MVP_FFMPEG_DIR", r"D:\App\ffmpeg"))
# 语速档位与实测系数住在 pipeline/ir.py（A4 静态闸门用它反推"这支片子要念多快"）。
MAX_TTS_RATE, RATE_FACTOR = ir.MAX_TTS_RATE, ir.RATE_FACTOR
MANIM = str(Path(os.environ.get("MVP_MANIM_BIN") or shutil.which("manim")
                 or r"D:\Dev\Project1\.local\t314\Scripts\manim.exe"))
# manim 0.22：-s=只存最后一帧、-l=实时预览，画质必须用 -q l|m|h|p|k 或显式 -r/--fps
QUALITY = {
    "draft": ["-q", "l"],                   # 854x480 @15，调试用
    "hd": ["-q", "m"],                      # 1280x720 @30
    "fullhd": ["-r", "1920,1080", "--fps", "30"],
}
os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ["PATH"]


def _run(cmd, env=None, cwd=None) -> None:
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=cwd, shell=isinstance(cmd, str),
    )
    if r.returncode != 0:
        raise RuntimeError(f"命令失败：{' '.join(cmd) if isinstance(cmd, list) else cmd}\n{(r.stderr or r.stdout or '')[-1200:]}")


class DurationNotFeasible(RuntimeError):
    """口播太长：自然语速（或最快档）都塞不进目标时长 +10% 以内。

    带上实测数字抛出去：上层（CLI/前端）要能直接告诉用户"这条知识点至少要多少秒"，
    而不是只给一句"偏差 43%"。反方向（成片比目标短）不走这里——那由 run 记 shortfall_note
    如实报，因为"内容就这么多"不是错误，把镜头填到目标秒数反而会造出冻屏。
    """

    def __init__(self, natural: float, fastest: float, target: float, speed_supported: bool = True):
        if speed_supported:
            msg = (f"目标时长 {target:.0f}s 放不下这条口播：自然语速需 {natural:.0f}s，"
                   f"最快可接受语速（rate=+{MAX_TTS_RATE}）仍需 {fastest:.0f}s。"
                   f"请把目标时长放宽到 ≥{fastest * 1.05:.0f}s，或精简口播。")
        else:
            msg = (f"目标时长 {target:.0f}s 放不下这条口播：自然语速需 {natural:.0f}s，"
                   f"当前 TTS 模型不支持提速档，只能按自然语速。"
                   f"请把目标时长放宽到 ≥{natural * 1.05:.0f}s，或精简口播。")
        super().__init__(msg)
        self.natural, self.fastest, self.target = natural, fastest, target


class GenerationError(RuntimeError):
    """生成链路上的失败，按「内容问题 vs 工具问题」分类并带一句可直接照做的建议。

    kind: content —— 分镜/口播本身过不去（改内容能救）；tool —— 渲染/合成/探测这类工具性
    故障（重试后仍不行）。前端据此把结论用人话说出来，而不是只给一句「生成失败」让人猜。
    """

    def __init__(self, kind: str, message: str, suggestion: str, **extra):
        super().__init__(message)
        self.kind = kind
        self.suggestion = suggestion
        self.extra = extra


def _retry(fn, attempts: int = 3, desc: str = ""):
    """机械重试：工具性步骤（渲染/合成）的偶发故障很常见，按固定间隔重试几次，仍不行才归类为 tool。

    TTS 自己内部已经带 4 次退避重试（audio/tts.py），不在这里再套一层；这里只管渲染与合成。
    """
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 这里就是要把一切工具性故障兜住、统一归类
            last = e
            if i < attempts - 1:
                time.sleep(1.5 * (i + 1))
    raise GenerationError(
        "tool", f"{desc or '工具性步骤'} 重试 {attempts} 次后仍失败：{last}",
        "服务端工具偶发故障。请稍后重试；若持续失败，请反馈这条知识点并附上 plan.json。",
        detail=str(last))


# 出片前最后一道闸门的内容缺陷，回灌 A3 最多改这一轮（改完再配音再复查）。再多轮子边际收益低、
# 耗时线性涨，一轮已经是"自愈"与"别让用户等太久"的折中。
FINAL_HEAL_ROUNDS = 1


def _spread_surplus(spoken: list[float], floors: list[float]) -> list[float]:
    """把 A3 的预算富余按**各镜自己的缺口**封顶，而不是堆在个别镜头上（第四轮 F-4 / 评审 A D2、B D-07）。

    旧写法 `seconds = max(spoken, floor)` 把每一镜的预算当成不可动的下限：实测口播比
    NATURAL_CPS 的估算快 20%~25% 时，差额整块留在那一镜的结尾——画面同冻、配音静音，
    一次函数镜4 实测 5.0s、二次函数镜4 实测 4.7s。富余本身是要的（思考时间，也是
    ±10% 时长闸门不被判失败的前提），只是不该集中在一镜：**每镜的缺口各自封顶在
    MAX_SHOT_IDLE**，没有缺口的镜头（spoken 已经≥floor）一秒都不多给——均摊成"每镜一份"
    会把这份富余塞给根本不缺的镜头，等于凭空造出一个新的冻屏。封顶后仍摊不下的那部分
    还给总时长（dev 由 duration 闸门如实报，不再用一镜的冻屏去凑目标秒数）。
    """
    return [round(s + min(MAX_SHOT_IDLE, max(0.0, f - s)), 2) for s, f in zip(spoken, floors)]


def _synthesize(plan, audio_dir: Path, rate: int, floors=None) -> list[tuple[float, Path]]:
    """按给定语速合成全部镜头，并用实测时长反写 shot.seconds（A6 时长对齐回路）。

    `floors` 是 A3 分镜给每一镜的预算秒数：实测口播比预算薄时那截余量是刻意留给学生的
    思考时间，抹掉它总时长就会掉到目标之下（batch_v7 首跑：一次函数/二次函数自然语速
    106/108s），所以富余保留——但由 _spread_surplus 按各镜自己的缺口封顶，不再整块堆在一镜结尾。
    """
    spoken: list[float] = []
    for s in plan.shots:
        wav = audio_dir / f"shot_{s.index:02d}.wav"
        dur = tts.synth(s.voiceover or s.narration, wav, audio_dir, rate=rate)
        s.spoken = round(SHOT_HEAD + dur + SHOT_TAIL, 2)
        spoken.append(s.spoken)
    seconds = _spread_surplus(spoken, list(floors) if floors is not None else [0.0] * len(spoken))
    shot_wavs: list[tuple[float, Path]] = []
    offset = 0.0
    for s, sec in zip(plan.shots, seconds):
        s.seconds = sec
        shot_wavs.append((offset, audio_dir / f"shot_{s.index:02d}.wav"))
        offset += sec
    return shot_wavs


def _pick_rate(natural: float, target: float) -> int:
    """自然语速落在 ±10% 内就不提速；否则按实测语速-时长模型（每档 ×0.897）反解所需档位。"""
    if abs(natural - target) / target <= 0.10:
        return 0
    want = target / natural
    r = round(math.log(max(want, 1e-6)) / math.log(RATE_FACTOR))
    return max(0, min(MAX_TTS_RATE, r))


def _voice_and_align(plan, audio_dir: Path, brief: Brief, log: dict) -> list[tuple[float, Path]]:
    """配音 → 用实测语音反写每镜秒数 → 语速记账。主路径与 A3 自愈路径共用这一份，保证两侧
    的 sidecar 口径一致（别一个记提速、一个记自然）。超长按 DurationNotFeasible 报"至少要多少秒"；
    反向超差不拦出片，只记 shortfall_note（内容就这么长，硬摊只会造冻屏）。"""
    step = time.time()
    # floors 必须在第一遍之前取：_synthesize 会就地改掉 s.seconds，第二遍不能再拿改后的值当下限。
    floors = [float(s.seconds) for s in plan.shots]
    shot_wavs = _synthesize(plan, audio_dir, 0, floors)
    natural = plan.total_seconds
    target = brief.target_seconds
    rate = _pick_rate(natural, target)
    if rate and tts.SPEED_SUPPORTED:
        shot_wavs = _synthesize(plan, audio_dir, rate, floors)
    dev = (plan.total_seconds - target) / target if target else 0
    spoken = sum(len("".join(c["text"] for c in s.subtitles())) for s in plan.shots)
    log["steps"]["narration"] = round(time.time() - step, 2)
    # 字/秒是给老师看的实测数：提速档到底把语速推到哪儿，比"rate=+3"好判断。
    log["tts"] = {"rate": rate, "natural_seconds": round(natural, 2),
                  "actual_seconds": round(plan.total_seconds, 2), "chars": spoken,
                  "natural_chars_per_second": round(spoken / natural, 2) if natural else None,
                  "chars_per_second": round(spoken / plan.total_seconds, 2)}
    if rate:
        if tts.SPEED_SUPPORTED:
            # C13 待判项的产品口径：提速照做，但代价要说给老师听，不能默默把语速推快。
            log["tts"]["note"] = (f'自然语速需 {natural:.0f}s，讲不进 {target}s，已提速到第 {rate} 档'
                                  f'（实测 {log["tts"]["chars_per_second"]} 字/秒）；'
                                  f'想更从容可把时长放宽到 ≥{natural:.0f}s')
        else:
            log["tts"]["note"] = "当前 TTS 模型不支持提速档，按自然语速合成。"
    if dev > 0.10:
        fastest = (plan.total_seconds
                   if rate >= MAX_TTS_RATE or not tts.SPEED_SUPPORTED
                   else natural * RATE_FACTOR ** MAX_TTS_RATE)
        raise DurationNotFeasible(natural, fastest, target, speed_supported=tts.SPEED_SUPPORTED)
    if dev < -0.10:
        # 反向超差不拦出片：内容就这么长，配音又没有提速档可以把它"讲满"，
        # 硬把每镜富余摊到目标秒数只会造出冻屏（第四轮 F-4）——照内容长度交付，
        # 但差额必须说给老师听，不能让人以为 120s 的目标真能讲出 120s 的东西。
        log["tts"]["shortfall_note"] = (
            f"这条知识点的口播按自然语速只需 {plan.total_seconds:.0f}s，比目标 {target:.0f}s 短 "
            f"{-dev * 100:.0f}%，成片按内容长度交付；想讲满目标时长请把目标收紧或补充例题。")
    return shot_wavs


def generate(brief: Brief, out_dir: Path, quality: str = "fullhd", burn: bool = False) -> dict:
    t0 = time.time()
    # 字幕只允许一层：渲染层已在画面内排字幕，再烧 srt 会叠成两行互相打架。
    # 需要外挂/烧录版时关掉内嵌层，由 srt 单独承担。
    if burn:
        brief.subtitles = False
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {"steps": {}}

    errs = brief.validate()
    if errs:
        raise ValueError("Brief 校验失败：" + "；".join(errs))

    # A1/A2 需求分析 + 资料调用：库内命中优先，库里没有的知识点由 K0 起草一条无出处的草稿条目
    # （落进 pipeline/data/kp_auto/ 后，下游每一步读的都是同一份文件，单一真源不变）。
    step = time.time()
    if llm_client.enabled("A1"):
        a1 = requirement_llm.normalize(brief.subject, brief.grade, brief.topic, brief.target_seconds)
        brief.topic = a1["topic"]
        log["requirement"] = {**a1, "model": llm_client.model_for("A1")}
    try:
        kp = knowledge.load(brief.subject, brief.topic, brief.grade)
    except knowledge.KnowledgeNotFound:
        kp = kp_draft.draft(brief.subject, brief.grade, brief.topic,
                            brief.target_seconds, brief.raw_text)
        log["kp_draft"] = {"id": kp["id"], "topic": kp["topic"],
                           "model": llm_client.model_for("K0"),
                           "note": ("知识点库里没有这一条，内容由模型起草，出处来自教材检索命中（未经人工核对）"
                                    if kp.get("refs") else
                                    "知识点库里没有这一条，内容由模型起草，未核对教材出处")}
    log["steps"]["retrieve"] = round(time.time() - step, 2)

    # A3 分镜（先按文本长度估时长）
    step = time.time()
    if llm_client.enabled("A3"):
        plan, log["storyboard_llm"] = storyboard_llm.build(brief, kp)
    else:
        plan = storyboard.build(brief, kp)
    log["steps"]["storyboard"] = round(time.time() - step, 2)

    # 预算态先过一遍闸门：A6 会用实测配音反写每镜秒数，所以只在反写之后检查，
    # 等于用"已经被提速抹平"的时长去验收（流程审计 §1.2）。这里在花钱渲染之前
    # 按分镜自己的账打回，顺便省掉一条注定出不了片的 TTS+渲染。
    # 记账级发现（blocking=False，如 BUDGET_TIGHT）照旧落盘但不拦：它说的是代价，不是违规。
    budget_findings = review.check(plan, kp)
    # 内部调整：确定性分镜被判阻断项时，不直接打回，先把清单回灌给 A3 模型改写一轮
    # （LLM 版 A3 自己已经回灌过，不再重复）。部署侧只要网关可用（开了任一生成环节）就会走这一步。
    if (review.blocking(budget_findings) and "storyboard_llm" not in log
            and (llm_client.enabled("A3") or llm_client.enabled("K0"))):
        step = time.time()
        plan, log["storyboard_adjust"] = storyboard_llm.adjust(brief, kp, plan, review.blocking(budget_findings))
        log["steps"]["storyboard_adjust"] = round(time.time() - step, 2)
        budget_findings = review.check(plan, kp)
    if budget_findings:
        (out_dir / "review.json").write_text(json.dumps(review.report(plan, kp), ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    hard = review.blocking(budget_findings)
    if hard:
        # 内部调整（拆行 + 按句裁 + 回灌 A3）都走完仍剩下的，如果全是"时长装不下这些内容"这一类，
        # 就照实测数字报"这条至少要多少秒"，而不是丢一句闸门打回让人猜。
        acct = storyboard.budget_of(plan)
        if acct and all(f["code"] in ("OVERLOAD", "PACING", "TARGET") for f in hard):
            natural = float(acct.get("natural_seconds") or 0.0)
            fastest = (natural * RATE_FACTOR ** MAX_TTS_RATE if tts.SPEED_SUPPORTED else natural)
            if fastest > brief.target_seconds * 1.10:
                raise DurationNotFeasible(natural, fastest, float(brief.target_seconds),
                                          speed_supported=bool(tts.SPEED_SUPPORTED))
        raise GenerationError(
            "content",
            "静态监督未通过（预算态，尚未配音/渲染）：\n"
            + "\n".join(f"  shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard),
            "分镜在预算阶段就被静态闸门打回：按上面清单精简口播、补限定语或图形原语，再重试。",
            findings=[{"shot": f["shot"], "code": f["code"], "msg": f["msg"]} for f in hard])

    # 配音稿（朗读稿）：把混着公式/化学式的口播改写成朗读员照念的中文。正则分不清
    # 「2-碘辛烷」的定位连字符（不念减）和「a-b」的减号，也认不得化学式，所以交给网关模型
    # 按整镜上下文生成、写进 shot.voiceover 随 plan 落盘；网关关闭/失败则回退 tts.speakable 正则。
    step = time.time()
    log["voiceover"] = voiceover.apply(plan)
    log["steps"]["voiceover"] = round(time.time() - step, 2)

    # A6 配音 → 用实测语音时长反推镜头时长（时长对齐回路）。_voice_and_align 同时负责语速记账：
    # 第一遍按自然语速实测；落在目标 ±10% 内就直接用，超了才按语速-时长模型估一档提速重合成。
    # 提速是否真的会发生由 tts.SPEED_SUPPORTED 决定（网关 TTS 实测不支持 speed，见 audio/tts.py）。
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    shot_wavs = _voice_and_align(plan, audio_dir, brief, log)

    plan.brief.target_seconds = brief.target_seconds

    # A4 静态监督闸门（最后一关，配音之后）：实测时长暴露的内容问题（超字/丢限定/缺图）先回灌
    # A3 自愈一轮（FINAL_HEAL_ROUNDS），改完再重写朗读稿、再配音、再复查；仍不过才打回。
    # 不因为一个镜头的问题让整段生成直接崩掉——能自愈的自愈，自愈不了的给人话清单。
    findings = review.check(plan, kp)
    hard = review.blocking(findings)
    if hard and llm_client.enabled("A3"):
        for _ in range(FINAL_HEAL_ROUNDS):
            plan, info = storyboard_llm.adjust(brief, kp, plan, hard)
            if info["source"] != "llm":
                break
            log["storyboard_heal"] = {"model": info["model"], "attempts": info["attempts"]}
            log["voiceover"] = voiceover.apply(plan)
            shot_wavs = _voice_and_align(plan, audio_dir, brief, log)
            findings = review.check(plan, kp)
            hard = review.blocking(findings)
            if not hard:
                break
    (out_dir / "review.json").write_text(
        json.dumps(review.report(plan, kp), ensure_ascii=False, indent=2), encoding="utf-8")
    if hard:
        raise GenerationError(
            "content",
            "静态监督未通过：\n"
            + "\n".join(f"  shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard),
            "可在下方修改分镜后重出片；或按上面清单精简口播、补限定语、把目标时长放宽。",
            findings=[{"shot": f["shot"], "code": f["code"], "msg": f["msg"]} for f in hard])

    total = plan.total_seconds
    dev = abs(total - brief.target_seconds) / brief.target_seconds
    log["duration"] = {"actual": total, "target": brief.target_seconds, "deviation": round(dev, 3)}

    plan_path = out_dir / "plan.json"
    plan.save(plan_path)
    (out_dir / "brief.json").write_text(json.dumps(brief.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")

    # A5 渲染
    env = dict(os.environ, PATH=str(FFMPEG_DIR) + os.pathsep + os.environ["PATH"], PLAN_JSON=str(plan_path))
    media = out_dir / "media"
    step = time.time()
    # SubTask #79-D1a：flow v2 生产开关（env QX_LLM_FLOW=1 且 subject 命中白名单，缺省 {"physics"}，
    # QX_LLM_FLOW_SUBJECTS 可覆盖）。缺省关=现网行为逐字不变：run.py 只在开关打开时才 import
    # pipeline.flow 任何东西。flow 逐镜回退是第一层（pipeline/flow/produce.render_flow 内），
    # 这里是最后一层：flow 整片塌了（concat/回退渲染都失败）→ 记 log["flow"]["fatal"] 走旧 A3 全片渲染。
    flow_ok = os.environ.get("QX_LLM_FLOW") == "1"
    silent = None
    if flow_ok:
        try:
            from pipeline.flow import produce as flow_produce  # 懒导入：开关关着不碰 flow 包
            # R7 接线：为每个 run 自动生成 .local/<run>/produce.py（bridge R 棒的驱动对象）
            if flow_produce.flow_enabled(brief.subject):
                flow_produce.write_produce_script(out_dir, quality=quality, manim=MANIM)
                silent = flow_produce.render_flow(
                    out_dir, plan.to_dict(), brief.__dict__, log, MANIM, QUALITY[quality], FFMPEG_DIR)
        except Exception as e:  # noqa: BLE001 「一步失败不整段崩」的最后一层（含 flow 包导入失败）
            log["flow"] = {**(log.get("flow") or {}), "enabled": True, "fatal": str(e)[-500:]}
            silent = None
    if silent is None:
        _retry(lambda: _run([MANIM, *QUALITY[quality], "--media_dir", str(media), "-o", "silent.mp4",
                             "--disable_caching", str(ROOT / "render" / "scene.py"), "Explainer"], env=env),
               desc="画面渲染")
        silent = next(iter(sorted(media.glob("**/silent.mp4"))), None)
        if silent is None:
            raise GenerationError(
                "tool", f"渲染未产出 silent.mp4（media 目录：{media}）",
                "manim 渲染异常退出、未产出画面轨。请检查分镜里的版式原语是否受支持，或稍后重试。")
        shutil.move(str(silent), out_dir / "silent.mp4")
    log["steps"]["render"] = round(time.time() - step, 2)

    # G2 时长闸门：成片必须与 Plan 时长一致（±10%），否则渲染层的时间记账又漏了东西。
    rendered = mux.probe_duration(out_dir / "silent.mp4")
    if rendered is None:
        raise GenerationError(
            "tool", "无法读取渲染产物时长（ffmpeg 未返回 Duration）",
            "ffmpeg 无法读取渲染产物时长，环境可能异常。请稍后重试，或联系维护者。")
    drift = abs(rendered - total) / total
    log["rendered"] = {"seconds": rendered, "plan": total, "drift": round(drift, 4)}
    if drift > 0.10:
        raise GenerationError(
            "tool",
            f"渲染时长 {rendered}s 与 Plan {total}s 偏差 {drift:.1%} > 10%（Spec_Scale G2），出片中止",
            "渲染层的时间记账与分镜不一致，成片可能卡顿或冻屏。请反馈这条知识点并附上 plan.json。")

    # A7 合成
    step = time.time()
    plan_dict = json.loads(plan_path.read_text(encoding="utf-8"))
    mux.build_track(shot_wavs, total, out_dir / "track.wav")
    # G4 音画同轴闸门：每镜头语音起点必须落在 SHOT_HEAD 附近（评审 P0 的复发检测）。
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
        raise GenerationError(
            "tool", f"音画时间轴错位（>0.35s）：{bad}",
            "音画时间轴错位，成片会声画不同步。请反馈这条知识点并附上 plan.json。")
    n_subs = mux.write_srt(plan_dict, out_dir / "subs.srt")
    # 音效（SubTask #60-E）：默认关，MVP_SFX=1 才在每个镜头切换点混转场音、片尾混提示音。
    # 切换点用反写后的**实际**镜长累加，不能用预算值——预算和实测差 20% 时音效会错半拍。
    final = _retry(lambda: mux.mux(out_dir / "silent.mp4", out_dir / "track.wav", out_dir / "final.mp4",
                                   out_dir / "subs.srt" if burn else None,
                                   shot_seconds=[float(s["seconds"]) for s in plan_dict["shots"]]),
                   desc="音画合成")
    log["steps"]["mux"] = round(time.time() - step, 2)
    log["sfx"] = os.environ.get("MVP_SFX", "0")
    log["burn"] = dict(mux.last_burn) if burn else {
        "attempted": False, "ok": False,
        "detail": "字幕已由渲染层排在画面内，未做烧录（要外挂/烧录版加 --burn）",
    }

    name = f"{brief.subject}-{brief.grade}-{kp['topic']}-{int(total)}s-{plan.hash}"
    artifact = out_dir / (name + ".mp4")
    if final != artifact:
        shutil.move(str(final), artifact)

    # F-10 自检（SubTask 48⑥）：全片时间轴扫一遍黑/空白帧 + 每镜首末帧拼图，而不是靠评审
    # agent 下一轮再抽样撞运气——batch_v7 两轮独立评审分别抽了 335/148 帧，没有一帧落在
    # 镜头边界的黑段上。扫描失败不拦出片（这是自检，不是闸门），但要如实记进 sidecar。
    step = time.time()
    try:
        scan = selfcheck.scan_boundaries(artifact, plan_dict)
        selfcheck.contact_sheet(artifact, plan_dict, out_dir / "frames" / "contact_sheet.png")
        (out_dir / "boundary_scan.json").write_text(
            json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
        log["boundary_scan"] = {"unexpected": scan["unexpected"], "any_blank": scan["any_blank"]}
    except Exception as e:  # 自检本身的工具性故障（缺 numpy/PIL、ffmpeg 版本差异）不该拖垮出片
        log["boundary_scan"] = {"error": str(e)}
    log["steps"]["selfcheck"] = round(time.time() - step, 2)

    # A8 VLM 回审 + S2.2 模型辅助判分：默认关，只出报告不拦出片，也不改任何内容。
    sheet = out_dir / "frames" / "contact_sheet.png"
    if sheet.exists():
        if llm_client.enabled("A8"):
            log["visual_review"] = visual_review_llm.review(sheet)
            (out_dir / "visual_review.json").write_text(
                json.dumps(log["visual_review"], ensure_ascii=False, indent=2), encoding="utf-8")
        if llm_client.enabled("S22"):
            log["llm_score"] = scoring_llm.score(plan_dict, kp, sheet)
            (out_dir / "llm_score.json").write_text(
                json.dumps(log["llm_score"], ensure_ascii=False, indent=2), encoding="utf-8")

    # 出片成功才走到这一行：中间产物（无声轨、整轨 wav、逐镜 wav、manim 缓存）当场清掉。
    # 评审 B D43 实测 3.5 MiB 的成片旁边躺着 15.6 MiB 过路文件，留档目录看着像"一个知识点四份视频"。
    # 任一步失败会在到达这里之前抛错，中间产物原样留着查问题。
    freed = mux.cleanup_work(out_dir)

    size_mb = round(artifact.stat().st_size / 1e6, 1)
    log.update({
        "artifact": str(artifact),
        "size_mb": size_mb,
        "cleaned_mb": round(freed / 1e6, 1),
        "mb_per_min": round(size_mb / (total / 60), 1),
        "subtitles": n_subs,
        "knowledge_id": kp["id"],
        "kp_origin": kp.get("origin") or "library",   # 画廊/详情页据此如实标「模型起草、未核对出处」
        "refs": kp["refs"],
        # A3 的预算账随片留档：画廊与 sidecar 里要能回答"这条片子是按自然语速讲的还是提速讲的"。
        "budget": storyboard.budget_of(plan),
        "shots": len(plan.shots),
        "wall_seconds": round(time.time() - t0, 1),
    })
    (out_dir / "sidecar.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="physics")
    ap.add_argument("--grade", default="H1")
    ap.add_argument("--topic", default="加速度")
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--style", default="clean", choices=["clean", "board"])
    ap.add_argument("--no-narration", action="store_true")
    ap.add_argument("--no-subtitles", action="store_true", help="画面内不排字幕（只留 subs.srt 外挂）")
    ap.add_argument("--burn", action="store_true", help="用 ffmpeg/libass 烧字幕（自动关闭画面内字幕，避免两层）")
    ap.add_argument("--quality", default="fullhd", choices=list(QUALITY))
    ap.add_argument("--out", default=str(ROOT / "out"))
    a = ap.parse_args()

    brief = Brief(subject=a.subject, grade=a.grade, topic=a.topic, target_seconds=a.seconds,
                  style=a.style, narration=not a.no_narration, subtitles=not a.no_subtitles)
    # 保持 ASCII：PowerShell/ffmpeg 对中文路径不稳。后缀防并发撞车：同一秒跑两条同学科
    # 的任务时，纯时间戳会让两个 manim 写进同一个 media 目录，产出互相踩掉（实测 FileNotFoundError）。
    slug = f"{a.subject}_{time.strftime('%Y%m%d_%H%M%S')}-{os.urandom(2).hex()}"
    log = generate(brief, Path(a.out) / slug, quality=a.quality, burn=a.burn)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
