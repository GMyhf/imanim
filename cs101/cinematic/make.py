"""3B1B 风格 CS101 短视频的制作脚本：旁白稿 → Edge TTS（句级时间戳）→ 渲染 → 混流。

用法（cwd 任意）：
  python cs101/cinematic/make.py --lesson fib                 # 1080p60 成片
  python cs101/cinematic/make.py --lesson fib --quality draft # 480p15 预览
  python cs101/cinematic/make.py --lesson fib --tts-only      # 只合成配音、写时间轴

时间轴口径：先合成每个 beat 的配音并量出时长，场景按「LEAD + 配音时长 + TAIL」给每个 beat
留时间（动画超长则顺延）；场景把每个 beat 的实际起点写进 marks.json，混流时音频按这份实际
起点摆放，所以动画超时也不会音画错位。字幕由场景按句级时间戳直接排进画面。
依赖：manim==0.22.0、edge-tts、ffmpeg；公式需要 latex + dvisvgm（TinyTeX 补 preview 宏包）。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"                  # cs101/out
PREFIX = "cs101_cine_"                     # 产物目录名前缀；cs201/cinematic/make.py 复用本脚本时改写 HERE/OUT/LESSONS/PREFIX
CINE_DIR = Path(__file__).resolve().parent  # cine.py 所在目录，渲染时放进 PYTHONPATH，别的课程的场景也能 import cine
SR = 24000
LESSONS = {"fib": ("fib.json", "fib_scene.py", "FibLesson"),
           "binary": ("binary.json", "binary_scene.py", "BinaryLesson"),
           "float": ("float.json", "float_scene.py", "FloatLesson"),
           "hanoi": ("hanoi.json", "hanoi_scene.py", "HanoiLesson"),
           "perm": ("perm.json", "perm_scene.py", "PermLesson"),
           "dsu": ("dsu.json", "dsu_scene.py", "DSULesson"),
           "bfs": ("bfs.json", "bfs_scene.py", "BFSLesson"),
           "knap": ("knap.json", "knap_scene.py", "KnapLesson"),
           "sort": ("sort.json", "sort_scene.py", "SortLesson"),
           "dijkstra": ("dijkstra.json", "dijkstra_scene.py", "DijkstraLesson"),
           "bsearch": ("bsearch.json", "bsearch_scene.py", "BSearchLesson"),
           "interval": ("interval.json", "interval_scene.py", "IntervalLesson"),
           "lcs": ("lcs.json", "lcs_scene.py", "LCSLesson"),
           "queens": ("queens.json", "queens_scene.py", "QueensLesson"),
           "lights": ("lights.json", "lights_scene.py", "LightsLesson"),
           "dpintro": ("dpintro.json", "dpintro_scene.py", "DPIntroLesson"),
           "stack": ("stack.json", "stack_scene.py", "StackLesson"),
           "matrix": ("matrix.json", "matrix_scene.py", "MatrixLesson")}
QUALITY = {"draft": ["-ql"], "hd": ["-qh"], "fullhd": ["-r", "1920,1080", "--fps", "60"]}


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg") or str(Path(os.environ.get("MVP_FFMPEG_DIR", "")) / "ffmpeg")
    if not Path(exe).exists():
        raise SystemExit("找不到 ffmpeg：放进 PATH 或设 MVP_FFMPEG_DIR")
    return exe


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        raise SystemExit(f"命令失败：{' '.join(map(str, cmd))}\n{(r.stderr or r.stdout)[-2000:]}")
    return r


async def _tts(text: str, voice: str, rate: str, mp3: Path) -> list[dict]:
    import edge_tts
    cues, audio = [], bytearray()
    async for ch in edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary").stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "SentenceBoundary":
            cues.append({"start": ch["offset"] / 1e7, "end": (ch["offset"] + ch["duration"]) / 1e7,
                         "text": ch["text"]})
    if not audio:
        raise RuntimeError("edge-tts 返回空音频")
    mp3.write_bytes(bytes(audio))
    return cues


# 读音词典：只改送去合成的文本，字幕仍显示旁白稿原文。Edge TTS 的中文音色把句中孤立的单个英文字母
# 读得含糊（ASR 校对里 j 被听成「距」、n 被听成「嗯」），按 Mac 上 Whisper 回听对比的结果选写法，见 README。
# 每条 (正则, 替换)，按顺序作用；替换不能引入或去掉「。？！」，否则句级时间轴对不上原文（会报错）。
# 2026-11 对 51 句含孤立 i/j/n 的旁白做过 A/B（.local/pron/ 有小样）：句首/分句首的 n 原样会被读成「嗯」，写成 en
# 才读成字母；句中的 n 原样最好（写成 en 或 N 反而被听成 m）；i 原样有时整个吞掉，写成 eye 才出声；j 写成 jay 更稳。
# 大写字母、大 O（读「欧」本就是字母名）不动。
PRON: list[tuple[str, str]] = [
    (r"(^|[，。；：？！、])(\s*)n(?![A-Za-z0-9_])", r"\1\2en"),
    (r"(?<![A-Za-z0-9_])i(?![A-Za-z0-9_])", "eye"),
    (r"(?<![A-Za-z0-9_])j(?![A-Za-z0-9_])", "jay"),
]


def speakable(text: str) -> str:
    """旁白稿 → 送 TTS 的文本。"""
    for pat, rep in PRON:
        text = re.sub(pat, rep, text)
    return text


def sentences(text: str) -> list[str]:
    """按「。？！」切句，与 Edge TTS 的 SentenceBoundary 一致（两门课 344 段实测逐句相同）。"""
    return [s.strip() for s in re.split(r"(?<=[。？！])", text) if s.strip()]


def _plain(text: str) -> str:
    """去掉标点和空白，只留文字，用来比较句子时间轴是否覆盖了整段旁白。"""
    return "".join(ch for ch in text if ch.isalnum())


def synth(beat: dict, voice: str, rate: str, cache: Path) -> dict:
    """合成一个 beat；按 (voice, rate, 送 TTS 的文本) 缓存，改稿或改读音词典都自动失效。

    句级时间戳的文字换回旁白稿原句（字幕显示原文，不显示读音词典的写法）。
    """
    spoken = speakable(beat["narration"])
    orig = sentences(beat["narration"])
    if len(sentences(spoken)) != len(orig):
        raise SystemExit(f"读音词典改变了句数（{beat['id']}）：检查 PRON 是否引入或去掉了「。？！」")
    key = hashlib.sha1(f"{voice}|{rate}|{spoken}".encode()).hexdigest()[:12]
    wav, meta = cache / f"{beat['id']}-{key}.wav", cache / f"{beat['id']}-{key}.json"
    if not (wav.exists() and meta.exists()):
        mp3 = wav.with_suffix(".mp3")
        for attempt in range(5):
            try:
                cues = asyncio.run(asyncio.wait_for(_tts(spoken, voice, rate, mp3), timeout=60))
            except Exception as e:  # noqa: BLE001 网络/服务端异常类型不固定
                if attempt == 4:
                    raise SystemExit(f"TTS 失败（{beat['id']}）：{type(e).__name__}: {e}")
                time.sleep(3 * 2 ** attempt)
                continue
            run([ffmpeg(), "-v", "error", "-y", "-i", str(mp3), "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(wav)])
            with wave.open(str(wav)) as w:
                got = w.getnframes() / w.getframerate()
            said = sum(len(_plain(c["text"])) for c in cues)
            want = len(_plain(spoken))
            # 音频流中途断了却没报错，有两种样子：音频比最后一句字幕短；或者音频和句子时间轴一起在半路结束
            # （并查集「应用」段曾少了整整一句）。两样都查。
            if not cues or got + 0.3 < cues[-1]["end"] or said < 0.95 * want:
                wav.unlink()
                if attempt == 4:
                    raise SystemExit(f"TTS 音频残缺（{beat['id']}）：音频 {got:.2f}s，句子覆盖 {said}/{want} 字")
                time.sleep(3 * 2 ** attempt)
                continue
            break
        mp3.unlink()
        meta.write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
    with wave.open(str(wav)) as w:
        dur = w.getnframes() / w.getframerate()
    cues = json.loads(meta.read_text(encoding="utf-8"))
    if len(cues) != len(orig):
        raise SystemExit(f"Edge TTS 切出 {len(cues)} 句、旁白稿 {len(orig)} 句（{beat['id']}），字幕没法换回原文")
    return {"id": beat["id"], "wav": f"audio/{wav.name}", "seconds": round(dur, 3),
            "cues": [{**c, "text": s} for c, s in zip(cues, orig)]}


def build_track(timing: list[dict], marks: dict, lead: float, total: float, out: Path) -> None:
    buf = bytearray(int(total * SR) * 2)
    for t in timing:
        with wave.open(str(out.parent / t["wav"])) as w:
            pcm = w.readframes(w.getnframes())
        at = int((marks[t["id"]] + lead) * SR) * 2
        buf[at:at + len(pcm)] = pcm[: max(0, len(buf) - at)]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(bytes(buf))


def srt(timing: list[dict], marks: dict, lead: float, out: Path) -> int:
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    rows = []
    for t in timing:
        for c in t["cues"]:
            base = marks[t["id"]] + lead
            rows.append(f"{len(rows) + 1}\n{ts(base + c['start'])} --> {ts(base + c['end'])}\n{c['text']}\n")
    out.write_text("\n".join(rows), encoding="utf-8")
    return len(rows)


def endcard(lesson: str) -> dict:
    """片尾卡信息：按本课程 site/films.json 的周次顺序找下一支；没登记的片只显示系列网址。"""
    url = f"infomall.zhengmao.ltd/{PREFIX.split('_')[0]}-anim/"
    try:
        films = [f for w in json.loads((HERE / "site" / "films.json").read_text(encoding="utf-8"))["weeks"]
                 for f in w["films"]]
    except (OSError, KeyError, ValueError):
        return {"next": None, "last": False, "url": url}
    ids = [f["id"] for f in films]
    if lesson not in ids:
        return {"next": None, "last": False, "url": url}
    k = ids.index(lesson)
    if k + 1 == len(ids):
        return {"next": None, "last": True, "url": url}
    nxt = films[k + 1]
    title = nxt["title"]
    if nxt["id"] in LESSONS:                     # 以下一支旁白稿里的标题为准（films.json 的可能是旧写法）
        try:
            title = json.loads((HERE / LESSONS[nxt["id"]][0]).read_text(encoding="utf-8"))["title"]
        except (OSError, KeyError, ValueError):
            pass
    return {"next": title, "last": False, "url": url}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", choices=LESSONS, default="fib")
    ap.add_argument("--quality", choices=QUALITY, default="fullhd")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--tts-only", action="store_true")
    a = ap.parse_args()
    script_name, scene_file, scene_cls = LESSONS[a.lesson]
    script = json.loads((HERE / script_name).read_text(encoding="utf-8"))
    out = (a.out or OUT / f"{PREFIX}{a.lesson}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "audio"
    cache.mkdir(exist_ok=True)
    t0 = time.time()
    timing = [synth(b, script["voice"], script["rate"], cache) for b in script["beats"]]
    (out / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print("配音：", ", ".join(f"{t['id']} {t['seconds']:.1f}s" for t in timing))
    if a.tts_only:
        return 0
    media = out / "media"
    env = dict(os.environ, CINE_TIMING=str(out / "timing.json"), CINE_MARKS=str(out / "marks.json"),
               CINE_AUDIT=str(out / "audit.json"), CINE_ENDCARD=json.dumps(endcard(a.lesson), ensure_ascii=False),
               PYTHONPATH=os.pathsep.join(filter(None, [str(CINE_DIR), os.environ.get("PYTHONPATH")])))
    run([sys.executable, "-m", "manim", *QUALITY[a.quality], "--disable_caching", "--media_dir", str(media),
         "-o", "silent.mp4", str(HERE / scene_file), scene_cls], env=env, cwd=HERE)
    silent = next(media.glob("**/silent.mp4"))
    marks = json.loads((out / "marks.json").read_text(encoding="utf-8"))
    lead, total = marks.pop("_lead"), marks.pop("_total")
    endcard_at = marks.pop("_endcard", None)
    audit = json.loads((out / "audit.json").read_text(encoding="utf-8"))
    for it in audit:
        print(f"[画面检查] {it['t']:7.2f}s {it['beat']:>9} {it['kind']}：{it['detail']}")
    print(f"画面检查：{len(audit)} 处问题" + ("" if audit else "（通过）"))
    track = out / "track.wav"
    build_track(timing, marks, lead, total, track)
    n_subs = srt(timing, marks, lead, out / "subs.srt")
    final = out / f"{script['id']}.mp4"
    run([ffmpeg(), "-v", "error", "-y", "-i", str(silent), "-i", str(track),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", str(final)])
    run([ffmpeg(), "-v", "error", "-y", "-ss", str(round(total * 0.62, 2)), "-i", str(final),
         "-frames:v", "1", str(out / "preview.png")])
    (out / "sidecar.json").write_text(json.dumps({
        "lesson": a.lesson, "title": script["title"], "source": script["source"],
        "voice": script["voice"], "tts": "edge-tts", "quality": a.quality,
        "seconds": round(total, 2), "speech_seconds": round(sum(t["seconds"] for t in timing), 2),
        "beats": {k: round(v, 2) for k, v in marks.items()}, "subtitles": n_subs, "audit_issues": len(audit),
        "endcard": None if endcard_at is None else round(endcard_at, 2),
        "size_mb": round(final.stat().st_size / 2**20, 2), "wall_seconds": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(media, ignore_errors=True)
    track.unlink()
    print(f"成片：{final}（{total:.1f}s）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
