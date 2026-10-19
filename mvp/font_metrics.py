"""字体度量标定表（移植阻断项 ③）：把散在 scene.py / review.py 的字距标定值收拢成按字体查的表。

背景：`_DELTA_DESC/_DELTA_CJK/_DELTA_PAREN`（scene.py 分段基线拼接）与
`UNIT_CJK/UNIT_ASCII`（review.py LEGIBLE 闸门估宽）都是**量着具体字体测出来的**，
换字体必须重测——旧版本里它们是模块级硬编码常量，Linux 容器把 MVP_TEXT_FONT 换成
Noto Serif CJK SC 之后，代码仍会静默沿用 SimSun 的旧值，闸门估宽与真实渲染脱钩。

本表是这些值的**唯一事实源**：
- 键 = (MVP_TEXT_FONT, MVP_LATIN_FONT) 字体对；默认对（SimSun + Times New Roman）的
  现值逐字保留，Windows 本机行为不变（红线：不许改动这些数值）。
- 表里没有的字体对 → metrics_for() 抛 FontMetricsError，明确拒绝继续排版/估宽，
  要求先在目标容器里跑 `python mvp/tools_fontmetrics.py` 重测并把结果填进 CALIBRATED。
- 纯标准库：review.py 的「不 import scene/manim」纪律由本模块延续。
"""

from __future__ import annotations

import os

DEFAULT_TEXT_FONT = "SimSun"
DEFAULT_LATIN_FONT = "Times New Roman"

# 已标定字体对。数值口径（与 tests/test_typo.py 的复检用例同一把尺子）：
#   DELTA_*  ×段内字号，字形墨迹底相对基线（=同行 H 的墨迹底）的下沉量，按 1/10 万上取整；
#   UNIT_*   fs=32 场景单位下的估宽系数，只许偏宽不许偏窄（偏窄会让 A4 漏报），按 0.01 上取整。
CALIBRATED: dict[tuple[str, str], dict[str, float]] = {
    (DEFAULT_TEXT_FONT, DEFAULT_LATIN_FONT): {
        "DELTA_DESC": 0.00300,   # 降部段（gjpqyQ）墨迹底下沉
        "DELTA_CJK": 0.00097,    # 汉字/全角标点段墨迹底下沉（上包络：取样本里沉得最深的）
        "DELTA_PAREN": 0.00284,  # 括号 ()[] 段墨迹底下沉
        "UNIT_CJK": 0.44,        # 每 CJK/全角字符估宽（10 汉字实测 4.3958）
        "UNIT_ASCII": 0.50,      # ASCII 估宽上包络（_est_width 按每字符 0.5×本值计）
    },
    # 容器替代字体（Noto Serif CJK SC / TeX Gyre Termes）**故意不预填**：
    # 本机没有 docker，量不了容器里的字体；在容器跑 tools_fontmetrics.py 产出后由人填进来。
}


class FontMetricsError(RuntimeError):
    """当前字体对没有度量标定：禁止静默沿用别家的值（这正是阻断项 ③ 要拦的事）。"""


def current_pair() -> tuple[str, str]:
    """(MVP_TEXT_FONT, MVP_LATIN_FONT)，缺省回 SimSun/Times（与 scene.py 的默认一致）。"""
    return (os.environ.get("MVP_TEXT_FONT", DEFAULT_TEXT_FONT),
            os.environ.get("MVP_LATIN_FONT", DEFAULT_LATIN_FONT))


def metrics_for(pair: tuple[str, str] | None = None) -> dict[str, float]:
    """按字体对取标定值；表里没有就抛 FontMetricsError（带重测命令），绝不回退到别家的值。"""
    p = pair if pair is not None else current_pair()
    m = CALIBRATED.get(p)
    if m is None:
        raise FontMetricsError(
            f"字体对 {p[0]!r} + {p[1]!r} 尚无字距标定（阻断项③）：估宽/基线拼接与字体强绑定，"
            f"不许沿用 {DEFAULT_TEXT_FONT!r} 的旧值。请在目标容器里跑 "
            f"`python mvp/tools_fontmetrics.py`，把输出的 entry 填进 font_metrics.CALIBRATED "
            f"再开生成入口；重测前只当画廊。")
    return m
