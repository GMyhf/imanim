"""3B1B 风格 CS101 短视频的制作脚本：旁白稿 → Edge TTS（句级时间戳）→ 渲染 → 混流。

用法（cwd 任意）：
  python mvp/cs101/cinematic/make.py --lesson fib                 # 1080p60 成片
  python mvp/cs101/cinematic/make.py --lesson fib --quality draft # 480p15 预览
  python mvp/cs101/cinematic/make.py --lesson fib --tts-only      # 只合成配音、写时间轴

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
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
MVP = HERE.parent.parent
SR = 24000
LESSONS = {"fib": ("fib.json", "fib_scene.py", "FibLesson"),
           "hanoi": ("hanoi.json", "hanoi_scene.py", "HanoiLesson"),
           "perm": ("perm.json", "perm_scene.py", "PermLesson"),
           "dsu": ("dsu.json", "dsu_scene.py", "DSULesson"),
           "bfs": ("bfs.json", "bfs_scene.py", "BFSLesson")}
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


def synth(beat: dict, voice: str, rate: str, cache: Path) -> dict:
    """合成一个 beat；按 (voice, rate, text) 缓存，改稿自动失效。"""
    key = hashlib.sha1(f"{voice}|{rate}|{beat['narration']}".encode()).hexdigest()[:12]
    wav, meta = cache / f"{beat['id']}-{key}.wav", cache / f"{beat['id']}-{key}.json"
    if not (wav.exists() and meta.exists()):
        mp3 = wav.with_suffix(".mp3")
        for attempt in range(5):
            try:
                cues = asyncio.run(_tts(beat["narration"], voice, rate, mp3))
                break
            except Exception as e:  # noqa: BLE001 网络/服务端异常类型不固定
                if attempt == 4:
                    raise SystemExit(f"TTS 失败（{beat['id']}）：{type(e).__name__}: {e}")
                time.sleep(3 * 2 ** attempt)
        run([ffmpeg(), "-v", "error", "-y", "-i", str(mp3), "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(wav)])
        mp3.unlink()
        meta.write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
    with wave.open(str(wav)) as w:
        dur = w.getnframes() / w.getframerate()
    return {"id": beat["id"], "wav": f"audio/{wav.name}", "seconds": round(dur, 3),
            "cues": json.loads(meta.read_text(encoding="utf-8"))}


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", choices=LESSONS, default="fib")
    ap.add_argument("--quality", choices=QUALITY, default="fullhd")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--tts-only", action="store_true")
    a = ap.parse_args()
    script_name, scene_file, scene_cls = LESSONS[a.lesson]
    script = json.loads((HERE / script_name).read_text(encoding="utf-8"))
    out = (a.out or MVP / "out" / f"cs101_cine_{a.lesson}").resolve()
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
    env = dict(os.environ, CINE_TIMING=str(out / "timing.json"), CINE_MARKS=str(out / "marks.json"))
    run([sys.executable, "-m", "manim", *QUALITY[a.quality], "--disable_caching", "--media_dir", str(media),
         "-o", "silent.mp4", str(HERE / scene_file), scene_cls], env=env, cwd=HERE)
    silent = next(media.glob("**/silent.mp4"))
    marks = json.loads((out / "marks.json").read_text(encoding="utf-8"))
    lead, total = marks.pop("_lead"), marks.pop("_total")
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
        "beats": {k: round(v, 2) for k, v in marks.items()}, "subtitles": n_subs,
        "size_mb": round(final.stat().st_size / 2**20, 2), "wall_seconds": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(media, ignore_errors=True)
    track.unlink()
    print(f"成片：{final}（{total:.1f}s）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
