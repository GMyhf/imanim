r"""容器内字距重测入口（移植阻断项 ③）：量当前 MVP_TEXT_FONT/MVP_LATIN_FONT 的度量，产出 JSON。

收编自 .local/typo2/probe.py（不渲染像素：manim Text 是 SVG 轮廓，控制点会越出真实曲线，
每条路径按 point_from_proportion 采样取极值）。口径与 scene.py 的 _DELTA_*、review.py 的
UNIT_*、tests/test_typo.py 的复检用例完全同源，量出来的数字可以直接填 font_metrics.CALIBRATED。

用法（Linux 容器 / Windows 本机同一条命令，无 D:\ 依赖、无 MiKTeX 依赖）：
    python mvp/tools_fontmetrics.py                 # JSON 打到 stdout
    python mvp/tools_fontmetrics.py --out metrics.json
步骤：容器内确认 env（fc-match 核对字体已装）→ 跑本命令 → 把输出的 table_entry
填进 mvp/font_metrics.py 的 CALIBRATED → 跑 tests/run_tests.py（test_typo 会复测量值对撞）。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (str(ROOT), str(ROOT / "render")):
    if p not in sys.path:
        sys.path.insert(0, p)

import font_metrics as FM  # noqa: E402
import scene as S  # noqa: E402  会拉起 manim——本脚本只在有 manim 的环境跑（闸门/review 不依赖它）

FS = 54.0            # 下沉量测量字号（与 tests/test_typo.py 同一把尺子）
UNIT_FS = 32.0       # 估宽系数定义字号（_est_width 的口径：width = units × fs / 32）

# 降部/括号样本：与 scene._DESC_RE、scene._PAREN_RE 的覆盖面一致，取最深者（上包络）。
DESC_CHARS = "gjpqyQ"
PAREN_CHARS = "(["
# 汉字/全角标点样本：常见字 + 会沉到基线下的全角标点（）「」、；：，_CJK_RE 覆盖三类码位。
CJK_CHARS = "学术方程数定义轨迹椭圆导力电压内能（）、；：，"
# 估宽样本：小写+空格（正文）、大写+数字（宽上包络）、出处行常见的量式混排。
ASCII_SAMPLES = [
    "the quick brown fox jumps over 13 lazy dogs",
    "0123456789 ABCDEFGHIJKLMNOPQRSTUVWXY",
    "v=s/t a=2.5 m/s F=ma x_0 x^2 (1.3)",
]
DIGIT_CHECK = "0479"   # 必须是等高数字（lining figures）：旧式数字 4/7 会掉到基线下


def paths(mob):
    """每个有点的子物件按弧长采样成折线（同 test_typo.paths）。"""
    out = []
    for sub in mob.get_family():
        pts = getattr(sub, "points", None)
        if pts is None or len(pts) < 2:
            continue
        out.append([sub.point_from_proportion(i / (len(pts) - 1)) for i in range(len(pts))])
    return out


def glyph_boxes(text):
    """排版一次 text，按 x 空隙切成字形框 [(x0,x1,y0,y1)]（同 probe.py：同次排版共享基线）。"""
    boxes = []
    for p in paths(S.T(text, font_size=FS)):
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    boxes.sort()
    merged = []
    for b in boxes:
        if merged and b[0] - merged[-1][1] < 0.02:   # 同一字形的多段轮廓（如括号两笔）
            prev = merged[-1]
            merged[-1] = (min(prev[0], b[0]), max(prev[1], b[1]), min(prev[2], b[2]), max(prev[3], b[3]))
        else:
            merged.append(b)
    return merged


def drop(ch: str) -> float:
    """字形 ch 的墨迹底相对基线（同一行里 H 的墨迹底）的下沉量 × 1/字号。

    样本隔一个空格排版（同 probe.py：H 与 j 贴太近会被 x 空隙阈值粘成同框）；
    多笔字形（全角括号、带点的变音符）取所有后续字形框的最深墨迹底。
    """
    g = glyph_boxes("H " + ch)
    if len(g) < 2:
        raise SystemExit(f"H {ch} 没切出独立字形框：标定方法在当前字体栈上失效，请人工核对 {ch!r}")
    return (g[0][2] - min(b[2] for b in g[1:])) / FS


def char_units(ch: str) -> float:
    """单个字符（重复 10 次）的平均宽度，折算到 fs=32 口径的场景单位。"""
    t = S.T(ch * 10, font_size=UNIT_FS)
    return t.width / 10.0


def ceil_at(x: float, nd: int) -> float:
    """上取整到 nd 位小数：标定值只许偏大不许偏小（偏小会让闸门漏报、拼接越界）。"""
    q = 10 ** nd
    return math.ceil(x * q - 1e-12) / q


def measure() -> dict:
    pair = (S.TEXT_FONT, S.LATIN_FONT)
    raw = {
        "DELTA_DESC": max(drop(c) for c in DESC_CHARS),
        "DELTA_PAREN": max(drop(c) for c in PAREN_CHARS),
        "DELTA_CJK": max(drop(c) for c in CJK_CHARS),
        "UNIT_CJK": char_units("学"),
        # _est_width 里每个 ASCII 字符按 0.5×UNIT_ASCII 计（空格也算字符），所以取
        # 2×平均字符宽；多样本取最大，保持"上包络、只许偏宽"的原口径。
        "UNIT_ASCII": max(2.0 * S.T(s, font_size=UNIT_FS).width / len(s) for s in ASCII_SAMPLES),
    }
    metrics = {
        "DELTA_DESC": ceil_at(raw["DELTA_DESC"], 5),
        "DELTA_PAREN": ceil_at(raw["DELTA_PAREN"], 5),
        "DELTA_CJK": ceil_at(raw["DELTA_CJK"], 5),
        "UNIT_CJK": ceil_at(raw["UNIT_CJK"], 2),
        "UNIT_ASCII": ceil_at(raw["UNIT_ASCII"], 2),
    }
    digits = {c: round(drop(c), 5) for c in DIGIT_CHECK}
    entry = {"text_font": pair[0], "latin_font": pair[1],
             "raw": {k: round(v, 6) for k, v in raw.items()},
             "metrics": metrics,
             "lining_digit_drops": digits,
             "digits_lining_ok": all(abs(v) < 0.0005 for v in digits.values()),
             "already_calibrated": pair in FM.CALIBRATED,
             "pair": list(pair)}
    entry["table_entry"] = (
        f'    ("{pair[0]}", "{pair[1]}"): {{\n'
        + "".join(f'        "{k}": {metrics[k]},\n'
                  for k in ("DELTA_DESC", "DELTA_CJK", "DELTA_PAREN", "UNIT_CJK", "UNIT_ASCII"))
        + "    },")
    if not entry["digits_lining_ok"]:
        entry["warning"] = ("数字出现基线下沉（旧式数字/text figures）：该字体不适合本项目体例，"
                            "见 scene.py 字体族注释，勿直接填表。")
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="量当前字体栈的字距/估宽标定，输出可填表的 JSON")
    ap.add_argument("--out", help="把 JSON 另存到该路径（默认只打 stdout）")
    args = ap.parse_args(argv)
    entry = measure()
    text = json.dumps(entry, ensure_ascii=False, indent=2)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
