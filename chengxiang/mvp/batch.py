"""批量出片入口：把语料库里的知识点一次全跑一遍，产出对照表。

评审 C5 指出仓库只有单条命令、没有清单入口，跨片对比只能手工逐条跑；这里补上。
每条知识点独立成 run 目录，失败不影响其它条，最后统一汇总（时长偏差 / 闸门 / 语速）。

用法（在 mvp/ 目录下）：
  python batch.py --out ../.local/batch --jobs 4
  python batch.py --subject physics --quality hd
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline import knowledge  # noqa: E402
from pipeline.ir import SUBJECTS, Brief  # noqa: E402
from run import generate  # noqa: E402


def corpus(subject: str | None, grade: str | None) -> list[dict]:
    out = []
    for f in sorted((ROOT / "pipeline" / "data" / "kp").glob("*/*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if subject and d["subject"] != subject:
            continue
        if grade and d["grade"] != grade:
            continue
        out.append({"file": f.name, **{k: d[k] for k in ("id", "subject", "grade", "topic")}})
    return out


def run_one(entry: dict, out_root: Path, quality: str, seconds: int) -> dict:
    brief = Brief(subject=entry["subject"], grade=entry["grade"], topic=entry["topic"],
                  target_seconds=seconds, style="clean")
    slug = f"{entry['subject']}_{entry['file'][:-5]}_{time.strftime('%H%M%S')}"
    t0 = time.time()
    try:
        log = generate(brief, out_root / slug, quality=quality)
    except Exception as exc:  # 一条失败不能带走整批
        return {"id": entry["id"], "ok": False, "error": f"{type(exc).__name__}: {str(exc)[-300:]}"}
    # 静态监督有任何发现时 generate 直接抛错，所以走到这里的就是"闸门全过"。
    return {
        "id": entry["id"], "ok": True, "video": log["artifact"],
        "seconds": log["duration"]["actual"], "deviation": log["duration"]["deviation"],
        "drift": log["rendered"]["drift"], "shots": log["shots"], "cues": log["subtitles"],
        # rate 与 chars_per_second 必须同栏读：后者是**提速后**的实测语速，单看它会把
        # "该讲 60 秒的内容挤进 45 秒"读成正常语速（C18 更正一：batch_v6 有 6/8 条靠 +1/+2 档过关）。
        "mb_per_min": log["mb_per_min"], "chars_per_second": log["tts"].get("chars_per_second"),
        "rate": log["tts"].get("rate"),
        "wall_seconds": round(time.time() - t0, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out" / "batch"))
    ap.add_argument("--subject", default=None, choices=[*SUBJECTS, None])
    ap.add_argument("--grade", default=None)
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--quality", default="fullhd", choices=["draft", "hd", "fullhd"])
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()

    entries = corpus(a.subject, a.grade)
    if not entries:
        print("语料库里没有匹配的知识点", file=sys.stderr)
        return 1
    out_root = Path(a.out)
    out_root.mkdir(parents=True, exist_ok=True)
    print(f"共 {len(entries)} 条，并发 {a.jobs}，输出 {out_root}", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(lambda e: run_one(e, out_root, a.quality, a.seconds), entries))

    print(f"\n{'知识点':<34}{'时长':>7}{'偏差':>8}{'镜数':>6}{'字幕':>6}{'漂移':>8}"
          f"{'字/秒':>7}{'提速':>6}{'MB/min':>9}")
    for r in results:
        if not r["ok"]:
            print(f"{r['id']:<34} 失败：{r['error']}")
            continue
        boost = f"+{r['rate']}" if r["rate"] else "+0"
        print(f"{r['id']:<34}{r['seconds']:>7.1f}{r['deviation']:>7.1%}{r['shots']:>6}"
              f"{r['cues']:>6}{r['drift']:>8.3f}{r['chars_per_second']:>7.2f}{boost:>6}{r['mb_per_min']:>9.1f}")
    bad = [r for r in results if not r["ok"] or abs(r.get("deviation", 1)) > 0.1]
    print(f"\n{len(results) - len(bad)}/{len(results)} 条出片成功且时长落在 ±10% 内")
    (out_root / "batch_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
