"""A7 合成：把逐镜头配音拼成整轨、生成 srt、与无声视频混流成片。

音频拼接用标准库 wave 手工做（各段都是 24kHz/16bit/mono，格式统一），
不依赖 ffmpeg 的 filter 图，行为完全可预测。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Iterable

from .ir import SHOT_HEAD, num

RATE, WIDTH, CH = 24000, 2, 1

# 换机器/上创空间时靠环境变量顶掉默认值，不把本机路径写死进代码。
FFMPEG_DIR = Path(os.environ.get("MVP_FFMPEG_DIR", r"D:\App\ffmpeg"))
log = logging.getLogger("mux")

# 烧录结果供上层（sidecar.json）读取；每次 mux() 调用后刷新。
last_burn: dict = {"attempted": False, "ok": False, "detail": ""}

# SFX 素材（SubTask #60-E）：audio/sfx.py 程序生成后入库 assets/sfx/，mux 混音时直接当
# ffmpeg 输入（素材即产即用）。增益都是字面倍率（amix 关了 normalize），低音量垫底不压配音。
SFX_DIR = Path(__file__).resolve().parent.parent / "assets" / "sfx"
SFX_SWEEP = SFX_DIR / "sweep.wav"
SFX_DING = SFX_DIR / "ding.wav"
SFX_VOL_SWEEP = 0.15     # 镜头切换点转场音：低增益
SFX_VOL_DING = 0.25      # 片尾提示音：略高，仍低于人声
SFX_DING_FALLBACK_SECONDS = 0.35   # 素材缺失/读不出时长时的兜底（与 audio/sfx.py 口径一致）


def _sfx_enabled(sfx: bool | None) -> bool:
    """None=读环境变量 MVP_SFX（"1"/"true"/"yes"/"on" 视为开），缺省 "0" 关闭。"""
    if sfx is None:
        return os.environ.get("MVP_SFX", "0").strip().lower() in {"1", "true", "yes", "on"}
    return bool(sfx)


def _wav_seconds(path: Path) -> float | None:
    """只读 wav 头拿时长（标准库 wave，不额外调 ffmpeg）；打不开返回 None。"""
    try:
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            return w.getnframes() / rate if rate else None
    except (OSError, wave.Error):
        return None


def _sfx_graph(shot_seconds: Iterable[float] | None,
               track_seconds: float | None) -> tuple[list[Path], str] | None:
    """构造 SFX 混音的额外输入与 filter_complex 图；没有可混内容时返回 None。

    输入布局：0=无声视频、1=配音整轨、2 起=SFX 素材（每个镜头切换点一份 sweep、片尾一份 ding）。
    每个 SFX 输入：volume 调增益 → adelay 按偏移（毫秒，mono 单值）→ 汇总 amix。
    normalize=0：amix 默认按输入数量缩放（ffmpeg≥4.4），关掉它增益才是字面值，
    否则整条配音会被整体压低；duration=first 以配音轨长度为准，越界尾巴交给 -shortest 裁。
    """
    inputs: list[Path] = []
    chains: list[str] = []
    labels: list[str] = ["[1:a]"]
    idx = 2
    offset = 0.0
    for sec in shot_seconds or ():
        offset += float(sec)
        if offset <= 0:
            continue        # t=0 的第一个镜头起点不放转场音
        inputs.append(SFX_SWEEP)
        ms = int(round(offset * 1000))
        chains.append(f"[{idx}:a]volume={SFX_VOL_SWEEP},adelay={ms}[sfx{idx}]")
        labels.append(f"[sfx{idx}]")
        idx += 1
    if track_seconds and track_seconds > 0:
        ding_len = _wav_seconds(SFX_DING) or SFX_DING_FALLBACK_SECONDS
        ding_at = max(0.0, track_seconds - ding_len)     # ding 收尾正好压在片尾
        inputs.append(SFX_DING)
        ms = int(round(ding_at * 1000))
        chains.append(f"[{idx}:a]volume={SFX_VOL_DING},adelay={ms}[sfx{idx}]")
        labels.append(f"[sfx{idx}]")
        idx += 1
    if len(labels) == 1:
        return None
    graph = ";".join(chains) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:duration=first:normalize=0[aout]"
    return inputs, graph


def _sfx_cmd(video: Path, audio: Path, out: Path,
             spec: tuple[list[Path], str]) -> list[str]:
    """按已算好的 SFX 混音图拼整条混流命令（视频流直拷，音频走 filter_complex 一次成型）。"""
    inputs, graph = spec
    cmd = [_ffmpeg_bin(), "-y", "-loglevel", "error"]
    for src in (video, audio, *inputs):
        cmd += ["-i", str(src)]
    cmd += ["-filter_complex", graph,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
            "-shortest", str(out)]
    return cmd


def _ffmpeg_bin() -> str:
    """定位 ffmpeg 可执行文件，并把其目录加进 PATH（本构建无 ffprobe）。"""
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    direct = FFMPEG_DIR / exe
    found = shutil.which("ffmpeg")
    if found:
        return found
    if direct.exists():
        os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")
        return str(direct)
    return "ffmpeg"


def probe_duration(path: Path) -> float | None:
    """读取视频实际时长（秒）。本 ffmpeg 构建不带 ffprobe，只能解析 -i 的 stderr。"""
    r = subprocess.run(
        [_ffmpeg_bin(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", r.stderr or "")
    if not m:
        return None
    h, mi, s, cs = (int(g) for g in m.groups())
    return h * 3600 + mi * 60 + s + cs / 100.0


def speech_onsets(wav: Path, noise_db: float = -45.0, min_silence: float = 0.3) -> list[float]:
    """整轨里每一段"开始说话"的时刻（秒）。用 ffmpeg silencedetect 解析，无 ffprobe 依赖。"""
    r = subprocess.run(
        [_ffmpeg_bin(), "-hide_banner", "-loglevel", "info", "-i", str(wav),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    events = [(k, float(t)) for k, t in
              re.findall(r"silence_(start|end):\s*([0-9.]+)", r.stderr or "")]
    onsets = [] if (events and events[0][0] == "start" and events[0][1] < 0.05) else [0.0]
    onsets += [t for k, t in events if k == "end"]
    return sorted(onsets)


def build_track(shot_wavs: list[tuple[float, Path]], total_seconds: float, out_wav: Path) -> float:
    """shot_wavs: [(镜头起点秒, wav 路径)]，段内音频从起点后 SHOT_HEAD 秒开始（等标题淡入）。
    与 IR 的字幕时间口径一致，字幕与语音才不会逐镜累积错位。"""
    rate = None
    for _, wav in shot_wavs:
        with wave.open(str(wav), "rb") as w:
            if rate and w.getframerate() != rate:
                raise ValueError(f"各镜头配音采样率不一致，无法拼接：{wav}")
            if w.getnchannels() != CH or w.getsampwidth() != WIDTH:
                raise ValueError(
                    f"配音格式不符（期望 {CH} 声道/{WIDTH * 8}bit，实际 {w.getnchannels()}/{w.getsampwidth() * 8}bit）：{wav}"
                )
            rate = w.getframerate()
    rate = rate or RATE
    width, ch = WIDTH, CH
    frames = bytearray(int(total_seconds * rate) * width)

    def put(offset: float, data: bytes) -> None:
        i = int(offset * rate) * width
        if i >= len(frames):        # 越过轨道末尾：丢弃而不是把缓冲区撑大（撑大会让时长失真）
            return
        if i < 0:
            i = 0
        end = min(i + len(data), len(frames))
        frames[i:end] = data[: end - i]

    for start, wav in shot_wavs:
        with wave.open(str(wav), "rb") as w:
            put(start + SHOT_HEAD, w.readframes(w.getnframes()))

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return total_seconds


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(plan: dict, out_srt: Path) -> int:
    out = []
    n = 0
    offset = 0.0
    for shot in plan["shots"]:
        # 兜底（SubTask #60-C）：plan.json 被手改后 cue 可能乱序/重叠，review 闸门又拦不住
        # 直接喂给合成层的这份 dict。写盘前按 start 排序，重叠时把前一条的 end 裁到后一条
        # 的 start（end = max(start, next.start)，不会裁出负时长），顺序不动、不删条——
        # 宁可静音断档，也不能两条字幕叠在屏幕上。只修落盘这份拷贝，不改输入 dict。
        cues = sorted([dict(c) for c in shot.get("subtitles", [])],
                      key=lambda c: num(c.get("start")))
        for a, b in zip(cues, cues[1:]):
            if num(b.get("start")) < num(a.get("end")):
                a["end"] = max(num(a.get("start")), num(b.get("start")))
        for s in cues:
            n += 1
            out.append(f"{n}\n{_ts(offset + s['start'])} --> {_ts(offset + s['end'])}\n{s['text']}\n")
        offset += shot["seconds"]
    out_srt.write_text("\n".join(out), encoding="utf-8")
    return n


def _burn_cmd(video: Path, audio: Path, srt: Path, burned: Path,
              spec: tuple[list[Path], str] | None = None) -> tuple[list[str], str]:
    """构造一次成型的烧录命令：直接从无声视频+配音编码出带内嵌字幕的成品，避免二次有损。

    Windows 路径/转义要点：
    - cwd 设为字幕目录，滤镜里只传相对文件名，绕开盘符冒号被当作滤镜参数分隔符的问题；
    - force_style 的值必须整体用单引号包住，否则样式里的逗号会被当作滤镜参数分隔符，
      ffmpeg 会把 "PrimaryColour=..." 当成下一个滤镜名并报"过滤链解析错误"而静默失败。

    spec 非空时（SFX 已混进 final.mp4）字幕滤镜与音效混音并入同一条 filter_complex——
    烧录版必须和主版本听感一致，不能主版本有转场音、烧录版没有。
    """
    style = ("FontName=Microsoft YaHei,FontSize=15,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H80000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=18")
    vf = f"subtitles=filename='{srt.name}':force_style='{style}'"
    # cwd 会改成字幕目录，所以除 srt 外的路径必须绝对化，否则 ffmpeg 找不到输入。
    if spec is None:
        cmd = [_ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(Path(video).resolve()),
               "-i", str(Path(audio).resolve()),
               "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
               "-shortest", str(Path(burned).resolve())]
        return cmd, vf
    inputs, graph = spec
    cmd = [_ffmpeg_bin(), "-y", "-loglevel", "error"]
    for src in (Path(video).resolve(), Path(audio).resolve(), *[Path(p).resolve() for p in inputs]):
        cmd += ["-i", str(src)]
    cmd += ["-filter_complex", f"[0:v]{vf}[v];{graph}",
            "-map", "[v]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
            "-shortest", str(Path(burned).resolve())]
    return cmd, vf


def mux(video: Path, audio: Path, out: Path, srt: Path | None = None,
        sfx: bool | None = None, shot_seconds: Iterable[float] | None = None) -> Path:
    """混流出 final.mp4；给了 srt 再烧一份内嵌字幕版（手机直看）。

    sfx: None=读环境变量 MVP_SFX（缺省关闭）；开启后在每个镜头切换点（t>0 的 shot 起点）
    混入转场 sweep、片尾混入 ding，用 filter_complex 多输入 + adelay/volume/amix 一次成型。
    shot_seconds: 逐镜头时长（秒），算累计偏移得切换点。SFX 混入失败不致命：退回无音效
    路径并打 warning，音效不能毁掉整片。烧录版与主版本用同一份混音结果（SFX 混入成功才带
    音效，失败则两份都不带），不会出现"画廊版有转场音、手机版没有"。

    烧录从 silent+track 一次成型（不经 final.mp4 二次编码）。烧录失败不静默退回：
    结果写入 last_burn（含 ffmpeg stderr 摘要）并以 warning 级日志输出，供上层记录。
    """
    ffmpeg = _ffmpeg_bin()
    # 交付口径统一到 48kHz 立体声：配音轨是 24kHz 单声道（网关 TTS 与音效素材同规格），
    # 上采样不增信息，但低采样率单声道 AAC 在部分播放器/浏览器上音量与同步表现不稳（批量评审 D16）。
    base = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
            "-shortest", str(out)]
    spec = _sfx_graph(shot_seconds, _wav_seconds(audio)) if _sfx_enabled(sfx) else None
    mixed = False
    if spec is not None:
        try:
            subprocess.run(_sfx_cmd(video, audio, out, spec), check=True)
            mixed = True
        except (subprocess.CalledProcessError, OSError) as e:
            log.warning("SFX 混入失败，退回无音效路径: %s", e)
    if not mixed:
        subprocess.run(base, check=True)

    global last_burn
    last_burn = {"attempted": False, "ok": False, "detail": "无字幕文件，未尝试烧录"}
    if srt and srt.exists():
        burned = out.with_name(out.stem + "_burned" + out.suffix)
        cmd, vf = _burn_cmd(video, audio, srt, burned, spec if mixed else None)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(srt.parent))
        if r.returncode == 0 and burned.exists() and burned.stat().st_size > 0:
            last_burn = {"attempted": True, "ok": True, "detail": str(burned)}
            log.info("字幕烧录成功: %s", burned)
            return burned
        err = (r.stderr or r.stdout or "").strip().splitlines()
        summary = " | ".join(err[-3:]) if err else f"ffmpeg 退出码 {r.returncode}"
        last_burn = {"attempted": True, "ok": False,
                     "detail": f"{summary} (vf={vf})",
                     "stderr": "\n".join(err)}
        log.warning("字幕烧录失败，退回未烧录版本: %s", summary)
    return out


# 交付目录里"过路"的东西：渲染出的无声轨、拼出来的整轨、逐镜 wav、manim 的中间缓存。
# 出片成功后一律删掉——评审 B D43 实测一条 3.5 MiB 的片子旁边躺着 15.6 MiB 的中间产物（占目录 84%），
# 画廊与留档目录看着像"一个知识点四份视频"。失败时不走到这一步，中间产物原样留着查问题。
WORK_FILES = ("silent.mp4", "track.wav", "final.mp4")
WORK_DIRS = ("media", "audio")


def cleanup_work(out_dir: Path, keep: Iterable[Path] = ()) -> int:
    """删掉 out_dir 里的中间产物，返回清掉的字节数。keep 里的路径一律不动。"""
    keep_paths = {Path(k).resolve() for k in keep}
    freed = 0
    for name in WORK_FILES:
        p = out_dir / name
        if not p.exists() or p.resolve() in keep_paths:
            continue
        freed += p.stat().st_size
        p.unlink()
    for name in WORK_DIRS:
        d = out_dir / name
        if not d.is_dir() or d.resolve() in keep_paths:
            continue
        freed += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        shutil.rmtree(d)
    return freed
