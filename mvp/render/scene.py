"""A5 渲染：ManimCE 消费 Plan IR 出无声视频。

渲染层零内容判断（Spec_Workflow 第 1 节）：IR 说画什么就画什么，只额外保证不越界。
不装 LaTeX：全部用 Text/Pango + Unicode（Schedule C7 已实测中文与 Δ 字形正常）。
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# 时长口径唯一来源是 pipeline.ir；渲染层不再自己读 SHOT_HEAD（边界改硬切后 INTRO/OUTRO 归零，
# 见上面那段注释），但字幕窗口仍由 IR 算好下发，这里不留一份副本。
import font_metrics  # noqa: E402  字体度量标定表（阻断项③），纯标准库

from manim import (
    BOLD,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    BLUE_C,
    Arrow,
    DashedLine,
    Dot,
    Rectangle,
    Sector,
    Square,
    Ellipse,
    GOLD,
    GREEN_C,
    GREY_A,
    ORANGE,
    PURE_YELLOW,
    RED_C,
    WHITE,
    FadeIn,
    FadeOut,
    Flash,
    Group,
    Indicate,
    Line,
    NumberPlane,
    Polygon,
    RoundedRectangle,
    Scene,
    ShowPassingFlash,
    Text,
    VMobject,
    VGroup,
    Wiggle,
    config,
    np,
)

PLAN_JSON = os.environ.get("PLAN_JSON", "plan.json")
SUBTITLE_BAND = 1.05          # 底部字幕专用带，任何内容不得进入（竞品缺陷 B3）
HEADER_BAND = 0.6
CONTENT_TOP = 4.0 - HEADER_BAND
CONTENT_BOTTOM = -4.0 + SUBTITLE_BAND
# 边界转场：**硬切**（第四轮 F-2；v6 的 D38 第一次量化，当时判"小修、不构成 G3/G4"于是留着）。
# 留着的代价这两轮终于被看见：整帧淡出到黑在 52/52 个镜头边界上各留下 0.20~0.63s 纯黑
# （实测 ink>60 的像素数为 0），教室一体机上就是"片子卡了一下黑了"。
# 为什么不改成"保留淡化但换个非黑底"：交叉淡化会吃掉每镜 0.4s，破坏
# 「每镜帧数 == round(seconds × fps)」这条音画同轴（G4）的前提——那是刻意不做的取舍，不改。
# 复验口径（原写"blackdetect 边界段归零"是错的，pix_th=0.10/pic_th=0.98 的默认口径会把
# 深色版面的有内容帧也算成黑，见 SubTask 48 ③复验）：pic_th=0.9999 零命中 + 逐帧 ink==0 零帧。
# 淡入淡出的时长归零后，SHOT_HEAD/SHOT_TAIL 两段静音仍在（配音与字幕的窗口不动），
# 只是那两段现在显示的是下一镜/本镜的画面，不再是黑屏。
INTRO = 0.0
OUTRO = 0.0

THEMES = {
    # clean = 白底深字（深色系强调色，保证白底对比度）；board = 深色黑板。
    "clean": {"bg": "#ffffff", "fg": "#1a1a1a", "accent": "#1f5fbf", "warn": "#c0392b", "key": "#b06d00",
              "dim": "#5f6670", "grid": "#e3e6ea", "hi": "#d35400", "emph": "#c0392b"},
    "board": {"bg": "#05070a", "fg": "#f2f2f2", "accent": GREEN_C, "warn": RED_C, "key": GOLD, "dim": GREY_A,
              "grid": "#20242c", "hi": PURE_YELLOW, "emph": GOLD},
}

# 页眉中文化映射（缺陷 2）：未知键回退原文，不引入新依赖。
SUBJECT_ZH = {"physics": "物理", "math": "数学", "chemistry": "化学", "biology": "生物"}
GRADE_ZH = {"G8": "初二", "G9": "初三", "H1": "高一", "H2": "高二", "H3": "高三", "U1": "大一", "U2": "大二"}

SAFE_WIDTH = 12.4              # 画面安全宽（与 _fit 一致）

# ---- callout 排版口径（SubTask #60-D 去框化）----
# 与 pipeline/review.py 的 CALLOUT_FS / CALLOUT_PAD / MIN_LEGIBLE_FS 同一把尺子，改一处必须改两处
# （A1/A2 审计教训：不允许"闸门说放行、渲染挤带"的两套尺子）。去框化去掉的是框线，
# 不改变字号与内宽预算：仍以 CALLOUT_FS 起排，以 SAFE_WIDTH − 2×CALLOUT_PAD 为内宽。
CALLOUT_FS = 32.0              # 单行结论卡字号（= review.CALLOUT_FS）
CALLOUT_SPLIT_FS = 28.0        # 「 · 」断行后每行字号（review 用 32 估宽再等比换算，数学上等价）
CALLOUT_PAD = 0.6              # 内宽预算两侧余量（= review.CALLOUT_PAD；无框后保留，避免两把尺子）

# ---- 强调动效帧预算（P2）----
# 动效只借既有 hold/淡入帧，绝不新增镜头时长；预算不够就压缩 run_time（FX_MAX_SEC 上限）。
FX_MAX_SEC = 0.5               # 单个强调动画最多借用的秒数
# 这些版式是"本镜主角"（图形类）：出场/揭示时挂 Indicate 点名。
FX_GRAPHIC_KINDS = ("figure", "graph_vt", "axis_graph", "particle_box", "microstate",
                    "energy_dist", "stat_chart", "mind_map", "table")
# 角标（首镜 id / 末镜出处）到画框边的距离：让外缘正好落在安全宽边界上。
# 原来写死 0.4，两条角标分别顶到 x=1866 / x=54，超出本项目自己的 123–1797 安全区（评审 A4）。
EDGE_BUFF = config.frame_width / 2 - SAFE_WIDTH / 2

# ---- 底部角标带（首镜 id / 末镜出处）与正文的间距（评审 P2 / phys-A D39）----
# CORNER_BAND：角标底边离字幕带上沿的余量，本轮改造前就写死在这里的 0.15（沿用，不动）。
CORNER_BAND = 0.15
# 正文块与正文块之间的距离就是 stack 的 arrange buff —— 出处行是独立的一块，
# 它与正文的间距不得小于一块到另一块的间距，否则读起来像正文的最后一行。
STACK_BUFF = 0.4
CORNER_CLEAR = STACK_BUFF  # ≈ 54px @1080p：不是试出来的数，= 同屏两块内容之间的既有距离
# 页眉与正文之间同样"按一块到另一块的间距"留空（第四轮 F-7 / 评审 A D4）：
# CONTENT_TOP 只是个静态带顶，页眉（26 pt，实测高 ≈0.45 单位）的墨迹底缘比它低，
# 全库 60 镜实测有 6 镜正文上沿**越过**页眉下沿（+0~+6px 重叠），最紧的 quad 也只剩 46px。
# 净空不再靠 CONTENT_TOP 与字高的巧合，改成从页眉实测绘底缘往下让。
HEADER_CLEAR = STACK_BUFF

# ---- 出处角标的字号与折行（第四轮评审 F-1 / A D5 / B D-01）----
# v7 实测：基准 18 号（未缩时墨迹 33~34px，投影可读），但长引用行被 `scale_to_fit_width(8.5)`
# 压到 12~13px —— 8.5 单位 = 1147px，而安全宽 12.4 单位 = 1674px，白弃 527px 横向空间，
# 逼着唯一承载"可追溯"证据的那几行纵向缩字。改法：横向用满安全宽，放不下先**折行**，
# 折完还超才等比缩，缩到下限以下由 review.py 的 LEGIBLE 闸门拦下（宁可拦下来改文案）。
REF_FS = 18.0
REF_WIDE = SAFE_WIDTH
REF_MIN_FS = 15.0        # 折行后允许缩到的下限；再小就是"一片灰点"，评审 A D5 的读数区
# 断点候选与断点纪律（见 _wrap_ref）：句读优先，括号内部禁断，行尾不留开括号或运算符。
REF_SEPS = ("；", "：", "。", "，", "、", "）", " ", "—", "·", "/")
REF_STRONG = ("；", "：", "。", "，", "、")
ATTACH_LEFT = "；：。，、）》」』—·"          # 这些跟着前一行收尾，不能顶在新行行首
REF_OPEN = "（(《「『[［"
REF_CLOSE = "）)》」』]］"
REF_EDGE_BAD = REF_OPEN + "=+_^/·—"

# ---- 字体族 ----
# 不指定字体时 Pango 的 "Sans" 在本机落到一款**旧式数字**（text figures）的字族上：
# 0 只有 x 高、4 和 7 掉到基线以下，坐标轴刻度与公式里的数字忽高忽低（batch_v4 两位评审各记一次 S5=3）。
# 显式钉死一款等高数字（lining figures）+ 全量 CJK 的字族，并把下面所有排版标定值按它重新量过。
TEXT_FONT = os.environ.get("MVP_TEXT_FONT", "SimSun")                  # 中文：宋体（Spec_Video_Defaults）
LATIN_FONT = os.environ.get("MVP_LATIN_FONT", "Times New Roman")       # 英文/数字：Times New Roman
_LATIN_CHARS = re.compile(r"[A-Za-z0-9.,;:!?'\"()\[\]{}<>=+\-*/%&|^~_#@$ ]")


def T(content, **kw):
    """全片唯一的 Text 出口：统一字体族。中文走 TEXT_FONT，拉丁字母/数字/半角符号逐字走 LATIN_FONT。"""
    kw.setdefault("font", TEXT_FONT)
    if LATIN_FONT and LATIN_FONT != kw["font"] and "t2f" not in kw:
        chars = {c for c in str(content) if _LATIN_CHARS.match(c) and c != " "}
        if chars:
            kw["t2f"] = {c: LATIN_FONT for c in sorted(chars)}
    return Text(content, **kw)


def _find_tex_bin() -> bool:
    """latex + dvisvgm 都能找到才算可用；Windows 上顺手把 MiKTeX 的 bin 补进 PATH。"""
    import shutil
    extra = os.environ.get("MVP_TEX_BIN", r"D:\App\MiKTeX\miktex\bin\x64")
    if shutil.which("latex") is None and os.path.isdir(extra):
        os.environ["PATH"] = extra + os.pathsep + os.environ["PATH"]
    return shutil.which("latex") is not None and shutil.which("dvisvgm") is not None


_TEX_OK = None
_TEX_TEMPLATE = None


def _tex_formula(tex, font_size, color):
    """公式走 LaTeX（Times 系数学字体）；没装 TeX 或编译失败返回 None，由调用方退回 rich()。"""
    global _TEX_OK, _TEX_TEMPLATE
    if _TEX_OK is None:
        _TEX_OK = _find_tex_bin()
    if not _TEX_OK:
        return None
    try:
        from manim import MathTex, TexTemplate
        if _TEX_TEMPLATE is None:
            _TEX_TEMPLATE = TexTemplate()
            _TEX_TEMPLATE.add_to_preamble(r"\usepackage{amsmath,amssymb}\usepackage{mathptmx}")
        m = MathTex(str(tex), font_size=font_size, color=color, tex_template=_TEX_TEMPLATE)
        return m
    except Exception as e:  # noqa: BLE001  TeX 缺包/语法错：退回 Unicode 排版，不让整片渲染失败
        print(f"[tex] fallback to rich(): {type(e).__name__}", file=sys.stderr)
        return None


# 每次 _place_label 的落点残差（分数, 标签文本），进程内累积；tests/test_layout.py 全库回归用。
PLACEMENTS: list = []

# 每次 _v_graph_vt 的刻度避让结果 (外推个数, 去掉个数)，同样进程内累积：刻度是"能让位的那一半"，
# 它动了多少必须看得见，否则避让到底生效没有只能靠肉眼翻帧（评审 P1 的自检口径）。
TICK_ADJUST: list = []

# ---- 上下标排版（评审 P1 第 2 条：v_t / s^2 必须排成真下标/上标）----
# 本机无 LaTeX；实测 Unicode 下标**字母**（ₐₑₜ…）在字体栈里是豆腐块，Unicode 下标数字
# （₀…）会被替换成满号 0（v₀ 看着像 v0），所以只能把字符串切片后分段生成 Text，再按
# 基线手工拼接。下面三个 _DELTA_* 是「该段墨迹底低于基线多少 × 字号」（H 的墨迹底=基线），
# 由 mvp/tools_fontmetrics.py（.local/typo2/probe.py 的收编版）直接读 manim Text 的 SVG 轮廓量出
# ——**换 TEXT_FONT 必须重跑一次**，标定值住在 font_metrics.CALIBRATED 表里、运行时按
# (TEXT_FONT, LATIN_FONT) 查表，未标定的字体对直接抛错（阻断项③，不再静默沿用旧值），
# 否则含降部/汉字/括号的段会整体错位（旧值标在未指定字体的 Sans 上，那一款还是旧式数字）。
#   带降部字母(gjpqyQ)的段，墨迹底在基线下 0.00353×字号；汉字/全角标点段 0.00190×字号；
#   拉丁字母与数字墨迹底≈基线（≤1px 溢出忽略）。上标取该字体栈 ² 的实测抬升为参照。
_MARKUP = re.compile(r"(_\{[^{}]+\}|_[A-Za-z0-9]|\^\{[^{}]+\}|\^[A-Za-z0-9])")
_UNISUB = re.compile(r"[₀₁₂₃₄₅₆₇₈₉]+")
_UNISUB_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
# Unicode 上标（²³…）只有**整段都是上标**时才需要接管：混在长段里时同一次 Text 排版会把它
# 自然抬起，独立成段时 Pango 按墨迹裁剪，²的墨迹底被当成基线对齐 → 落回基线（batch_v6 评审 D27）。
_UNISUP = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ]+")
_UNISUP_MAP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ", "0123456789+-n")
_DESC_RE = re.compile(r"[gjpqyQ]")
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_PAREN_RE = re.compile(r"[()\[\]]")
# 评审 N3/五.3：拉丁单字母「变量符号」用斜体，单位/缩写/数字/CJK 保持正体。
# 判定所需的两个字符集（无内容白名单，纯排版规则）：
#   _UNIT_JOIN：把相邻字母粘成「复合单位」的连接符（m/s、m·s⁻¹）；
#   _REL_OPS：若同一非空白片段里出现这些运算符，则该斜杠是「代数除号」而非「单位 per」。
_UNIT_JOIN = "/·•"
_REL_OPS = "=<>≤≥≈≠+-−"
# 两个字母的全小写 run 默认按「两个变量相乘」斜体，除这些确实成词的单位/缩写。
# 元素符号（Na、Cl）首字母大写，不在小写 run 之列，天然正体。
# lg/ln 是对数算子（正体），两字母全小写的形状和「两个变量相乘」撞车，只能点名豁免；
# 三字母的 log/cos/tan 天然走"多字母 run 一律正体"那条，不必列。
_UPRIGHT_DIGRAPHS = {"kg", "cm", "mm", "km", "dm", "ml", "mg", "ms", "kj", "ev", "hz",
                     "kp", "id", "of", "in", "to", "at", "on", "is", "it", "no", "lg", "ln"}
SUB_SCALE = 0.62               # 下标/上标字号比例
SUB_DROP = 0.0014              # ×正文字号：下标基线相对正文基线下移（收敛下沉，底缘不越主基线）
SUP_LIFT = 0.0040              # ×正文字号：上标基线相对正文基线上移（0.216@54）
# 移植阻断项 ③：下面三个下沉量是**按字体标定**的度量，唯一事实源在 font_metrics.CALIBRATED；
# 这里的 _DELTA_* 只是 SimSun 表项的别名（test_typo.py 与注释沿用原名，数值一字未动）。
# 运行时真正生效的取值走 _font_metrics()，按当前 (TEXT_FONT, LATIN_FONT) 查表。
_SIMSUN_M = font_metrics.CALIBRATED[(font_metrics.DEFAULT_TEXT_FONT, font_metrics.DEFAULT_LATIN_FONT)]
_DELTA_DESC = _SIMSUN_M["DELTA_DESC"]    # ×段内字号：降部段（gjpqy）墨迹底低于基线
_DELTA_CJK = _SIMSUN_M["DELTA_CJK"]      # ×段内字号：汉字/全角标点段墨迹底低于基线
_DELTA_PAREN = _SIMSUN_M["DELTA_PAREN"]  # ×段内字号：括号 ()[] 墨迹底低于基线，令含括号段按基线对齐
_KERN = 0.0005                 # ×正文字号：拼接边界补回被 ink extents 吞掉的侧空
_SUB_KERN = 0.0016             # ×正文字号：下标/上标右侧补空，令 v₀ 与右括号、下标与后续 = 间距均匀

_FONT_METRICS_CACHE: dict[tuple[str, str], dict[str, float]] = {}


def _font_metrics() -> dict[str, float]:
    """当前字体对（TEXT_FONT, LATIN_FONT）的标定值；未标定字体在此硬失败（见 font_metrics）。"""
    pair = (TEXT_FONT, LATIN_FONT)
    m = _FONT_METRICS_CACHE.get(pair)
    if m is None:
        m = font_metrics.metrics_for(pair)
        _FONT_METRICS_CACHE[pair] = m
    return m


def _is_unit_letter(s, i):
    """s[i] 是一个「单字母拉丁 run」中的字母；判断它是单位（正体）还是变量（斜体）。"""
    n = len(s)
    # (1) 斜杠/间隔号两侧的单位。两种写法要分开判，判据就是斜杠旁边有没有空格：
    #     · 无空格 m/s、m·s⁻¹ → 复合单位，两侧都是单位；
    #     · 带空格 "量 / 单位"（轴名的标准写法：t / s、F / N、a / (m·s⁻²)）→ 只有斜杠**右侧**是单位，
    #       左侧是量符号。混为一谈时「a / (m·s⁻²)」的 a 会被读成单位（斜体丢了），而「F / N」的 N
    #       会被读成变量（单位斜了）——评审 D28 就是同一行里两种体例并存。
    #     若该非空白片段含运算符（v=s/t），斜杠是代数除号，整段都不算单位。
    for j in (i - 1, i + 1):
        k = j
        while 0 <= k < n and s[k] == " ":
            k += 1 if j > i else -1
        if not (0 <= k < n) or s[k] not in _UNIT_JOIN:
            continue
        if j > i and k != i + 1:      # 字母在斜杠左侧且中间有空格 → 那是被除的量符号
            continue
        left, right = k - 1, k + 1
        while left >= 0 and s[left] != " " and not _CJK_RE.match(s[left]):
            left -= 1
        while right < n and s[right] != " " and not _CJK_RE.match(s[right]):
            right += 1
        if not any(c in _REL_OPS for c in s[left + 1:right]):
            return True
    # (2) 独立单位：字母被空白与其左边的「纯数字」隔开（10 s、250 m）。
    #     没有空格的紧邻数字是系数不是量纲（「2x」里的 x 是变量，斜体；写成「2 X」才可能是单位）——
    #     这条漏掉时同一表达式里 y 斜体、x 正体，学生读成两个不同的东西（batch_v4 评审 D1）。
    #     数字串左邻若仍是字母（v₀ t 里的下标 0）则不是量纲数字，字母依旧视为变量。
    p = i - 1
    while p >= 0 and s[p] == " ":
        p -= 1
    if p < i - 1 and p >= 0 and s[p].isdigit():
        q = p
        while q >= 0 and s[q].isdigit():
            q -= 1
        if q < 0 or not _LATIN_RE.match(s[q]):
            return True
    return False


def _is_element_symbol(s, b):
    """单字母 run（末位下标 b）若紧跟电荷或计量数字，那是元素符号，不是变量（第四轮 F-6 / 评审 B D-04）。

    IUPAC 体例：元素符号一律正体，只有量符号斜体。v7 的 chem 片里同一个屏上「H 斜、Zn/Cu 正」，
    学生读成两个不同的东西。判据只看 run 右侧紧邻的字符：⁺⁻ 与上下标数字（H⁺、O₂、Fe³⁺）；
    物理里的单字母变量右侧是空格或运算符（F = ma、U_外 走 _ 标记），不会被这条误判。
    """
    n = len(s)
    return s[b].isupper() and b + 1 < n and s[b + 1] in "⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉"


def slant_indices(s):
    """纯函数：返回与 s 等长的布尔表，True 表示该字符应斜体（拉丁单字母变量符号）。

    规则：仅单字母拉丁 run（多字母词如 mol/max 一律正体）；且不是单位（见 _is_unit_letter）；
    且不是元素符号（见 _is_element_symbol）；
    数字、CJK、希腊字母（Δ）均非 [A-Za-z] → 正体。
    """
    s = str(s or "")
    out = [False] * len(s)
    n = len(s)
    for i, ch in enumerate(s):
        if not _LATIN_RE.match(ch):
            continue
        a = i
        while a > 0 and _LATIN_RE.match(s[a - 1]):
            a -= 1
        b = i
        while b + 1 < n and _LATIN_RE.match(s[b + 1]):
            b += 1
        if b - a + 1 != 1:      # 多字母 run：默认正体，除下面这种情形
            run = s[a:b + 1]
            # 两个字母、各自成词又不是单位/函数名 → 是两个变量相乘或两点连线（F = ma、|PF₁|），
            # 教材里各自斜体；整串正体会把它读成一个叫 "ma" 的量（评审 D1 同族）。
            # 大小写两种都收：|PF| 的 P、F 全是大写，而元素符号是 Na/Cl 这种驼峰，天然不在此列；
            # 单位豁免按小写键查，所以 KG 也照样正体。
            if len(run) == 2 and (run.islower() or run.isupper()) \
                    and run.lower() not in _UPRIGHT_DIGRAPHS \
                    and not any(_is_unit_letter(s, j) for j in (a, b)):
                out[a] = out[b] = True
            continue
        if _is_unit_letter(s, i):
            continue
        if _is_element_symbol(s, b):
            continue
        out[i] = True
    return out


def slant_chars(s):
    """s 中应设为斜体的字符集合（供测试与调用方核对，等价于逐字符判定的去重结果）。"""
    s = str(s or "")
    return {c for c, it in zip(s, slant_indices(s)) if it}


def _compose(core, fs, color, kw):
    """按逐字符斜体判定生成 Text：只把拉丁单字母变量交给 t2s 斜体，其余（CJK/单位/数字）正体。

    走 Text 的 t2s（子串→slant），不拆分片段、不改宽度累加，避免破坏既有空格/拼接。
    同一字母在同一片段里既像变量又像单位时（罕见），保守取正体，绝不斜体单位。
    """
    idx = slant_indices(core)
    italic, upright = set(), set()
    for ch, it in zip(core, idx):
        (italic if it else upright).add(ch)
    keys = sorted(italic - upright)          # 冲突字母（既变量又单位）留正体
    if not keys:
        return T(core, font_size=fs, color=color, **kw)
    t2s = {k: "ITALIC" for k in keys}
    return T(core, font_size=fs, color=color, t2s=t2s, **kw)


def _seg_bottom_delta(s, fs):
    """该段墨迹底相对其基线低多少（决定拼接时的垂直落点）。

    取值按当前 (TEXT_FONT, LATIN_FONT) 查 font_metrics 表；字体对未标定时抛
    FontMetricsError——宁可渲染失败，也不许拿 SimSun 的旧值给别的字体排错版（阻断项③）。
    """
    m = _font_metrics()
    d = 0.0
    if _DESC_RE.search(s):
        d = max(d, m["DELTA_DESC"] * fs)
    if _CJK_RE.search(s):
        d = max(d, m["DELTA_CJK"] * fs)
    if _PAREN_RE.search(s):  # 含括号的段按其基线（而非括号下沿）落位，避免把整段抬高、下标反越过括号
        d = max(d, m["DELTA_PAREN"] * fs)
    return d


def rich(text, font_size, color, **kw):
    """IR 文本 → VGroup：_x/_{} 排成下标，^x/^{} 排成上标，其余原样。

    无 _/^ 且无 Unicode 下标数字的文本原样返回单个 Text（行为不变）。
    拼接规则：每段按自身基线落位——普通段基线在 y=0，下标段基线下移
    SUB_DROP×字号，上标段上移 SUP_LIFT×字号；段底 = 基线 − _seg_bottom_delta。
    """
    toks = []  # (kind, s)  kind: "" 普通 / "_" 下标 / "^" 上标
    for p in [q for q in _MARKUP.split(str(text or "")) if q != ""]:
        if p[:1] in ("_", "^") and len(p) > 1:
            toks.append((p[0], p[2:-1] if p[1:2] == "{" else p[1:]))
            continue
        if _UNISUP.fullmatch(p):          # t_{停}² 里的 ² 会被拆成独立一段 → 改走上标道
            toks.append(("^", p.translate(_UNISUP_MAP)))
            continue
        j = 0
        for m in _UNISUB.finditer(p):  # v₀ → v + 下标0（本字体栈里 ₀ 是满号 0）
            prev = p[m.start() - 1] if m.start() > 0 else (toks[-1][1][-1:] if toks and not toks[-1][0] else "")
            if re.match(r"[A-Za-z0-9)\]]", prev or ""):
                if m.start() > j:
                    toks.append(("", p[j:m.start()]))
                toks.append(("_", m.group().translate(_UNISUB_MAP)))
                j = m.end()
        if j < len(p):
            toks.append(("", p[j:]))
    if not toks:
        return T("", font_size=font_size, color=color, **kw)
    if len(toks) == 1 and not toks[0][0]:
        return _compose(toks[0][1], font_size, color, kw)

    # Pango 的 ink extents 不含首尾空白，分段拼接会把段间空格吃掉，
    # 所以空格宽度单独量一次（"一 一" 减 "一一"），再手工按 x 累加排布。
    space = T("一 一", font_size=font_size).width - T("一一", font_size=font_size).width
    kern = _KERN * font_size
    sub_kern = _SUB_KERN * font_size   # 下标/上标右侧补空：令 v₀ 与右括号、下标与后续 = 间距均匀
    fs_small = max(round(font_size * SUB_SCALE), 6)
    pieces = []
    x = 0.0
    prev_core = False
    prev_kind = ""
    for kind, s in toks:
        lead = len(s) - len(s.lstrip(" "))
        trail = len(s) - len(s.rstrip(" "))
        core = s.strip(" ")
        if not core:
            x += (lead + trail) * space
            prev_core = False
            continue
        if prev_core:
            x += kern + (sub_kern if prev_kind else 0.0)
        fs_eff = font_size if not kind else fs_small
        t = _compose(core, fs_eff, color, kw)
        if kind == "_":
            base = -SUB_DROP * font_size
        elif kind == "^":
            base = SUP_LIFT * font_size
        else:
            base = 0.0
        x += lead * space
        t.move_to([x + t.width / 2, base - _seg_bottom_delta(core, fs_eff) + t.height / 2, 0])
        x += t.width + trail * space
        pieces.append(t)
        prev_core = True
        prev_kind = kind
    g = VGroup(*pieces)
    g.shift(LEFT * (x / 2))  # 与单 Text 一致：整体以原点为中心
    return g


def _grid_step(lo: float, hi: float, want: int = 6) -> float:
    """把坐标区间切成约 want 格，步长取 1/2/2.5/5×10ⁿ 里最接近的一档。"""
    raw = max(hi - lo, 1e-6) / want
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= raw:
            return m * mag
    return 10 * mag


def _tick_values(lo: float, hi: float, step: float) -> list[float]:
    out, k = [], math.ceil(lo / step - 1e-9)
    while k * step <= hi + 1e-9:
        out.append(round(k * step, 6))
        k += 1
    return out


def _fmt_tick(v: float) -> str:
    return f"{v:g}"


def _polyline(coords, color, width: int):
    """两点连线 / 三点折线 / 四点以上平滑曲线。

    物理的分段图（3 点）斜率本身就是要讲的内容，不能平滑；数学的采样点画成折线会在顶点
    出现巨型棱角，看着不像函数图（评审 D4「平滑曲线成巨型折线」）。
    """
    if len(coords) == 2:
        return Line(coords[0], coords[1], color=color, stroke_width=width)
    if len(coords) < 4:
        return VMobject(color=color, stroke_width=width).set_points_as_corners(coords)
    curve = VMobject(color=color, stroke_width=width)
    curve.start_new_path(coords[0])
    for i in range(len(coords) - 1):
        p0 = coords[i - 1] if i > 0 else 2 * coords[0] - coords[1]          # 端点虚设邻点（Catmull-Rom）
        p3 = coords[i + 2] if i + 2 < len(coords) else 2 * coords[-1] - coords[-2]
        curve.add_cubic_bezier_curve_to(coords[i] + (coords[i + 1] - p0) / 6,
                                        coords[i + 1] - (p3 - coords[i]) / 6, coords[i + 1])
    return curve


def _box(mob):
    a, b = mob.get_corner(LEFT + DOWN), mob.get_corner(RIGHT + UP)
    return (a[0], a[1], b[0], b[1])


def _overlap(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _sample(mob, n=20):
    """沿图线取 n 个屏幕点。外接框对斜线毫无用处（一条陡线的外接框能盖住半个平面），
    判断「标签有没有压住线」只能逐点看。"""
    try:
        return [mob.point_from_proportion(i / (n - 1)) for i in range(n)]
    except Exception:
        return [np.array(mob.get_center())]


# 硬障碍的净空（manim 单位）。碰撞判定用的是精确外接框（_overlap 不含容差），
# 实测这一批撞点全都停在 0–2px：轴穿过 x² 标签 1px、曲线贴着刻度「−2」0.0px、导引线贴着
# 刻度「−1」2.0px（数学 B 评审 Q3/Q5 + batch_v6 复评同点位）。所以障碍不向外扩就等于没设障碍。
# 取值不是试出来的：0.08 是 _place_label 里标签贴到平面边缘时用的同一个钳位余量。
AXIS_PAD = 0.08
# 刻度外推还允许"离图区边多远"。刻度本来就贴在轴外侧（x 刻度在轴下 0.3u、y 刻度在轴左 0.42u），
# 三档外推 = 0.48u；再往外推数字就和这张图脱开了，宁可不推（宁可去掉那一格）。
TICK_SLACK = 0.8
# 轴名（x_label / y_label）作为障碍时要向外扩的净空。两端都有出处，不是试出来的：
#   下限 = x 刻度那一行的下沿（轴外 0.3u + 20px 字的一半 ≈ 0.394u）到轴名那一行的上沿
#          （0.62u − 22px 字的一半 ≈ 0.517u）之间的缝 ≈ 0.123u —— 小于它就桥不住叠字。
#   上限 = y 轴名左沿（轴右 0.2u）加上 y 刻度数字的宽度（0.42u + 0.094u）≈ 0.714u ——
#          超过它就开始吃 y 轴顶端那些本来该标出来的刻度（0.8 时 newton 的 a 轴丢了 "4"）。
# 取 0.15：刚过下限，离上限很远。1080p 下 1u ≈ 106.7px，两个字号由此换算。
AXIS_LABEL_PAD = 0.15
# 轴名与平面右缘的净距（F-9）：末端刻度数字的半宽最大 ≈0.28u（"125" 三号字），再加避让盒
# AXIS_LABEL_PAD 也要留给刻度，0.5u 让两者在任何刻度宽度下都不同列。
AXIS_NAME_GAP = 0.5


def _pad_box(box, pad):
    return (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)


def graph_obstacles(plane, ticks, pad: float = AXIS_PAD) -> list:
    """图线标签要让开的硬障碍：两条坐标轴（各含 ±AXIS_PAD 净空）+ 全部刻度数字。

    旧写法只装了轴名和刻度，**坐标轴本身不在避让集里** —— 于是 y 轴竖线正好从 x² 标签中间穿过，
    实测间隙 1px（数学 B 评审 Q3）：外接框判定不含容差，1px 就是"没撞"，缩放后成了穿线。
    轴是又长又直的线，用外接框表示正合适（不像斜线那样必须逐点采样）。
    """
    return [
        _pad_box(_box(plane.x_axis), pad),
        _pad_box(_box(plane.y_axis), pad),
        *[_box(t) for t in ticks],
    ]


def _poly_hits(poly, box, margin=0.0) -> bool:
    """这条线的任一采样点是否落进（外扩 margin 的）这个盒。"""
    x0, y0, x1, y1 = box
    return any(x0 - margin <= q[0] <= x1 + margin and y0 - margin <= q[1] <= y1 + margin for q in poly)


def _place_label(lab, line, plane, taken, avoid=()):
    """标签贴着它所指的那条线放，且不压住任何一条图线。

    旧写法 next_to(line, UP) 按外接框定位，斜线的外接框很高，标签被顶到画面上方两个单位，
    学生不知道它在标谁（一次函数「y = 2x − 1」实测）。改成在线上取锚点、沿局部法线让开半个字高：
    线再陡标签也落在它旁边，不会穿过它（加速度 v-t 三种情形，「下斜 → a 与 v 反向」被斜线划过去实测）。
    """
    def place(p):
        lab.move_to(p)
        if lab.get_right()[0] > plane.get_right()[0]:
            lab.set_x(plane.get_right()[0] - lab.width / 2 - 0.08)
        if lab.get_left()[0] < plane.get_left()[0]:
            lab.set_x(plane.get_left()[0] + lab.width / 2 + 0.08)
        if lab.get_top()[1] > plane.get_top()[1]:
            lab.set_y(plane.get_top()[1] - lab.height / 2 - 0.06)
        if lab.get_bottom()[1] < plane.get_bottom()[1]:
            lab.set_y(plane.get_bottom()[1] + lab.height / 2 + 0.06)

    def score():
        x0, y0, x1, y1 = _box(lab)
        on_line = sum(1 for poly in avoid for q in poly
                      if x0 - 0.05 <= q[0] <= x1 + 0.05 and y0 - 0.05 <= q[1] <= y1 + 0.05)
        clash = sum(1 for t in taken if _overlap(_box(lab), t))
        return on_line * 2 + clash * 3

    best = None
    for prop in (0.80, 0.62, 0.45, 0.90):
        try:
            anchor = line.point_from_proportion(prop)
            tangent = line.point_from_proportion(min(prop + 0.04, 1.0)) - line.point_from_proportion(
                max(prop - 0.04, 0.0)
            )
        except Exception:
            continue
        normal = np.array([-tangent[1], tangent[0], 0.0])
        norm = np.linalg.norm(normal)
        if norm < 1e-6:
            continue
        # 让开的距离 = 标签框在该法线方向上的半影（矩形支撑函数）：
        # 只按半个字高让，遇到陡线（法线几乎是水平的）等于没让，标签照样被线穿过。
        n = normal / norm
        reach = abs(n[0]) * lab.width / 2 + abs(n[1]) * lab.height / 2 + 0.16
        tang = np.array([n[1], -n[0], 0.0])       # 单位切向：沿自己的线滑一段，躲开别的线与已放好的标签
        slide = lab.width / 2 + 0.2
        cands = [anchor + s * reach * n + k * slide * tang
                 for s in (1.0, -1.0) for k in (0.0, -1.0, 1.0, -2.0, 2.0)]
        cands += [anchor + 0.26 * UP, anchor - 0.34 * UP]
        for cand in cands:
            place(cand)
            value = score()
            if best is None or value < best[0]:
                best = (value, np.array(lab.get_center()))
            if value == 0:
                break
        if best[0] == 0:
            break
    if best is None:
        best = (0, np.array(line.get_center()) + 0.26 * UP)
    place(best[1])
    taken.append(_box(lab))
    # 落点残差登记：0 = 既不压任何图线也不撞别的标签。tests/test_layout.py 拿它做全库回归，
    # 因为"标签压线"这类缺陷只有渲染出来才看得见，而评审看到的是成片、闸门拦不住——只能反向钉死。
    PLACEMENTS.append((best[0], "".join(m.text for m in lab.get_family() if hasattr(m, "text"))))
    return lab


def reveal_keys(at, n: int) -> list:
    """IR 的 at 提示 → n 个「揭示键」（全片唯一的"哪一块什么时候露"口径）。

    键的两种形态与 graph_vt 的 cases 同源：
      · 字幕里的片段字符串 —— 讲到那句话，这一批才出现；
      · 0~1 的行序比例   —— 按整镜字幕数换算成第几条字幕。
    缺省（**现库 kp 基本没有 at，这一条是主路径**）：n 个单元按行序均匀铺批，第 i 个取 i/n，
    与 _tag_progressive 的既有口径一模一样 —— 于是 compare/callout 的分批节奏与 steps/summary
    同速、天然落在 shot.seconds 之内（键只映射到既有字幕下标，不引入任何新的动画时长）。
    长度对不上、类型不认识、只给一个单元却没给 at —— 一律回落到缺省铺批，绝不因为脏数据而
    让某块内容整镜不出现。
    """
    if n <= 0:
        return []
    if isinstance(at, (list, tuple)) and len(at) == n:
        return list(at)
    if n == 1 and at is not None and not isinstance(at, (list, tuple)):
        return [at]          # 一句 callout 想卡在自己那句话上：直接给标量，不必包成列表
    return [k / n for k in range(n)]


def tag_reveal(mob, key) -> None:
    """打揭示标记。数字键统一转成 float：JSON 里的 0 / 1 读进来是 int，
    落到 _reveal_at 的字符串分支会被当成"匹配不上的片段"而静默变成整镜可见。"""
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        key = float(key)
    mob._reveal_at = key


def reveal_cue_index(key, cues) -> int | None:
    """一个揭示键 → 第几条字幕（换算口径与改造前的内联写法逐字相同）。

    两种键：0~1 的行序比例（int/float，含 tag_reveal 归一的 0 与 1）→ 按字幕条数均匀换算；
    字幕里的片段字符串 → 命中第一条包含它的字幕。**对不上就返回 None**，调用方让那块内容
    从镜头一开始就在画面上——脏数据绝不能让一块内容整镜不出现。
    换算出的下标恒为 0..len(cues)-1，而 cue 的起点都在 shot.seconds 之内，
    所以分批揭示不需要、也不允许引入任何新的时长偏移。
    """
    if isinstance(key, float):
        return min(int(key * len(cues)), max(len(cues) - 1, 0))
    for i, s in enumerate(cues):
        if key and key in str(s["text"]):
            return i
    return None


def collect_reveals(body, cues):
    """把 builder 标了 _reveal_at 的子元素按字幕下标归批，并从各自的直接父节点摘出去。

    摘出去的元素不进本镜的入场动画，等对应字幕淡入时**与字幕同帧**一起淡入 —— 不额外占一帧，
    镜头总时长仍然精确等于 IR 给的 seconds（这是本轮改造的红线：只加揭示，不加时长）。
    返回 (揭示表, 被摘出去的全部元素)；后者用于收尾一起淡出，否则残影会挂进下一镜（评审 D9 同族）。

    两条护栏：
      * Mobject.remove() 只动直接子元素，揭示对象嵌在 builder 返回的 VGroup 深处，
        对 body 调用它等于空操作——所以遍历时记住真正的父节点（评审 D9：steps/summary 一开场就整屏全显）。
      * 一条字幕都没有（Brief.subtitles=False）时整段跳过：揭示靠字幕把人加回来，没有字幕就
        永远没人加回来，画面上等于这些内容整镜不存在。steps/summary 早就踩在这个坑上，
        compare/callout 上了分批之后会铺满全库，所以在这里一次堵死。
    """
    reveals: dict[int, list] = {}
    if not cues:
        return reveals, []

    def _with_parent(mob):
        for child in mob.submobjects:
            yield child, mob
            yield from _with_parent(child)

    pending = [(mob, parent) for mob, parent in _with_parent(body) if getattr(mob, "_reveal_at", None) is not None]
    for mob, parent in pending:
        idx = reveal_cue_index(getattr(mob, "_reveal_at"), cues)
        if idx is None:  # 对不上口播就退回"一开始就在画面上"，绝不能整条不显示
            continue
        if not any(parent is m for m in body.get_family()):  # 父节点已被摘走（揭示套揭示）
            continue
        parent.remove(mob)
        reveals.setdefault(idx, []).append(mob)
    return reveals, [m for idx in sorted(reveals) for m in reveals[idx]]


def content_bottom_for(corners, default: float = CONTENT_BOTTOM) -> float:
    """本镜正文可用高度的底缘：有底部角标带（首镜 id / 末镜出处）就整条把它扣掉。

    扣法不是"给出处行加个 margin"，而是把角标当成正文栏的**最后一块**：正文底缘 = 角标上沿
    + CORNER_CLEAR（= 同屏两块内容之间既有的距离 STACK_BUFF）。这样出处行与正文之间天然隔开
    一块到另一块的间距，投影上不会再被读成正文的最后一行（评审 P2 / phys-A D39 实测 9px）。
    正文本身仍由 _fit 等比缩进 [content_bottom, CONTENT_TOP]，越界的老红线一条不动。
    """
    if not corners:
        return default
    return max(default, min(c.get_top()[1] for c in corners) + CORNER_CLEAR)


def _ref_line(seg, color):
    """一条出处行。走 rich()：出处里也带 IR 的下标标记（v_t = v_0 + a t），
    裸 T() 会把那条原样画上屏（第四轮 F-11 / 评审 A D8、B D-05），与同屏公式的体例不一致。"""
    return rich(seg, REF_FS, color).set_opacity(0.85)


def _wrap_ref(text: str) -> list:
    """一条过长的出处 → 最多两行。

    两条纪律：① 断点只在中文句读上，且**不进括号内部**——v7 那条 `（v_t = v_0 + a t）` 被空格断成
    "（v_t = v_0 + a" / "t）" 就是没这条约束的结果，公式被劈开比缩字号更糟；
    ② 优先选"两行都不必再缩字号"的断点，宁可两行参差一点，也不把字缩回读不见的那一档。
    """
    cands = []
    mid = len(text) / 2
    for i, ch in enumerate(text):
        if i == 0 or ch not in REF_SEPS:
            continue
        depth = sum(1 for c in text[:i] if c in REF_OPEN) - sum(1 for c in text[:i] if c in REF_CLOSE)
        if depth > 0:
            continue  # 括号里的是公式与页码，不是可选断点
        cut = i + 1 if ch in ATTACH_LEFT else i
        left, right = text[:cut].rstrip(), text[cut:].lstrip()
        if not left or not right or left[-1] in REF_EDGE_BAD or right[0] in ATTACH_LEFT:
            continue
        cls = 0 if ch in REF_STRONG else 1
        cands.append((cls, abs(len(left) - mid), left, right))
    if not cands:
        return [text]
    cands.sort()
    fallback = None
    for _, _, left, right in cands:
        wide = max(_ref_line(left, WHITE).width, _ref_line(right, WHITE).width)
        if wide <= REF_WIDE:
            return [left, right]
        if fallback is None or wide < fallback[0]:
            fallback = (wide, left, right)
    return [text] if fallback is None else [fallback[1], fallback[2]]


def _ref_texts(refs, color) -> list:
    """出处行组：先折行，再对仍超宽的等比缩到安全宽内（缩过头由 review.py 的 LEGIBLE 拦）。"""
    out = []
    for s in (str(r) for r in refs):
        segs = [s] if _ref_line(s, WHITE).width <= REF_WIDE else _wrap_ref(s)
        for seg in segs:
            ln = _ref_line(seg, color)
            if ln.width > REF_WIDE:
                ln.scale_to_fit_width(REF_WIDE)
            out.append(ln)
    return out


def _halo_ring(mob, color, buff=0.22, width=8, opacity=0.3):
    """P3 假辉光（halo，调研 1.2 的 ExplosionMarker 做法）：同中心叠一圈粗描边、
    低不透明度、无填充的环，垫在"本镜主角"（关键图形/公式）底下。

    只做静态 halo、不做脉冲动画（省帧预算）；不做真模糊——ManimCE 核心无 blur API（调研已排除）。
    用法：作为 VGroup 的**第一个**子元素加入（先画者在下），并 set_z_index(-1) 双保险。
    环的外接框只比本体大 buff 一圈，不显著放大整块版式（_fit / 安全带纪律不受影响）。
    """
    w, h = mob.width, mob.height
    ring = RoundedRectangle(
        width=w + 2 * buff, height=h + 2 * buff,
        corner_radius=min(0.3, (h + 2 * buff) / 2),
        stroke_color=color, stroke_width=width, stroke_opacity=opacity, fill_opacity=0,
    ).move_to(mob.get_center())
    ring.set_z_index(-1)
    return ring


class Explainer(Scene):
    def construct(self):
        with open(PLAN_JSON, encoding="utf-8") as f:
            plan = json.load(f)
        self._th = THEMES.get(plan["brief"]["style"], THEMES["clean"])
        self.camera.background_color = self._th["bg"]
        shots = plan["shots"]
        for i, shot in enumerate(shots):
            self._render_shot(shot, plan, is_first=(i == 0), is_last=(i == len(shots) - 1))

    # ---------------- 版式原语 ----------------
    def _v_title(self, p, th):
        main = str(p.get("main", ""))
        if main and not _MARKUP.search(main) and not _UNISUB.search(main):
            # P2 艺术字：标题渐变（调研 2.1：Text 自带 gradient 参数，按字数在渐变上采样取色）。
            # 字体栈不变（仍走 T() 的 SimSun/Times 双字体）；含上下标标记时退回 rich()
            # （分段拼接无法做连续渐变）。
            head = T(main, font_size=76, weight=BOLD, gradient=(th["accent"], th["fg"]))
        else:
            head = rich(main, 76, th["fg"], weight=BOLD)
        return VGroup(
            head,
            rich(p.get("sub", ""), 34, th["accent"]),
        ).arrange(DOWN, buff=0.35)

    def _v_formula(self, p, th):
        tex = _tex_formula(p.get("tex"), 54, th["key"]) if p.get("tex") else None
        core = tex if tex is not None else rich(p.get("expr", ""), 54, th["key"])
        g = VGroup(core)
        if p.get("note"):
            g.add(rich(p["note"], 28, th["dim"]))
        g.arrange(DOWN, buff=0.3)
        # P3 halo：公式是"本镜主角"时叠假辉光环（静态、垫底、无脉冲），环随 _fit 一起缩放。
        return VGroup(_halo_ring(core, th["key"]), g)

    def _v_callout(self, p, th):
        """结论/提示卡：**无框排版**（去框化，SubTask #60-D 用户核心抱怨"看不懂的框框"）。

        改动：
          · 不再画 RoundedRectangle 框线与半透明底——文字卡直接裸排；
          · 「 · 」清单**总是**按段拆行，每段一个揭示单元，按口播节奏 FadeIn
            （不再一次性整框出现；单段仍保持原有"一行不拆"行为）；
          · 段内重点字按 IR 的 emph 点名用 Text(t2c={子串: GOLD}) 染色（调研 2.2），
            点名后 key 调整段退回中性色以衬出金字，未点名保持原 tone 色（旧片零回归）；
          · 结论（tone=key）与提醒（tone=warn）打 _reveal_fx 动效标记，由 _render_shot
            在字幕时间轴内播放（借既有帧，不加镜头时长）。
        字号/安全区纪律不变：CALLOUT_FS 起排、内宽 SAFE_WIDTH − 2×CALLOUT_PAD，
        与 pipeline/review.py 的 CALLOUT_FS / CALLOUT_PAD / _est_width 同一把尺子。
        """
        tone = str(p.get("tone", "key"))
        color = {"warn": th["warn"], "key": th["key"]}.get(tone, th["accent"])
        text = str(p.get("text", ""))
        inner_max = SAFE_WIDTH - 2 * CALLOUT_PAD          # == review.py LEGIBLE 的 avail
        emph = [str(e) for e in p.get("emph", []) if str(e)] \
            if isinstance(p.get("emph"), (list, tuple)) else []
        # 染字底：IR 点名重点字后，key 调整段本就要染金，必须退回中性色才衬得出 GOLD 重点字；
        # warn/accent 调保留自身 tone 色（GOLD 重点字压在其上仍然醒目）。
        base = th["fg"] if (emph and tone == "key") else color

        def line(s, fs):
            t2c = {e: th["emph"] for e in emph if e and e in s}
            return rich(s, fs, base, t2c=t2c) if t2c else rich(s, fs, base)

        parts = [s.strip() for s in re.split(r"\s+·\s+", text) if s.strip()]
        if len(parts) >= 2:
            lines = VGroup(*[line(s, CALLOUT_SPLIT_FS) for s in parts]).arrange(
                DOWN, buff=0.24, aligned_edge=LEFT
            )
            if lines.width > inner_max:
                lines.scale_to_fit_width(inner_max)
            units = list(lines)
        else:
            txt = line(text, CALLOUT_FS)
            if txt.width > inner_max:
                txt.scale_to_fit_width(inner_max)
            units = [txt]
        keys = reveal_keys(p.get("at"), len(units))
        for i, (mob, key) in enumerate(zip(units, keys)):
            if len(units) >= 2 or p.get("at") is not None:
                tag_reveal(mob, key)
            # P2 动效点名：结论卡最后一句（或唯一一句）揭晓 → Flash 爆闪；其余结论行 → Indicate；
            # 提醒卡 → Wiggle 轻提示。单行卡若不揭示（F-5 整块接管揭示除外），
            # _render_shot 的 _intro_fx / 块级扫描也能找到这个标记。
            if tone == "key":
                mob._reveal_fx = "flash" if i == len(units) - 1 else "indicate"
            elif tone == "warn":
                mob._reveal_fx = "wiggle"
        return units[0] if len(units) == 1 else VGroup(*units)

    def _tag_progressive(self, group, n: int, at=None) -> None:
        """给逐行内容打"按口播进度揭示"的标记：讲到哪一步，那一行才出现。

        一次全显六行时学生读不完（评审 U3），但 IR 里没有行-字幕对应关系，
        所以按行序在整镜字幕上均匀分布，最后一条留到镜头收尾。
        IR 给了 at（行序比例或字幕片段）就照用；没给时的缺省键与旧写法逐字相同（k/n），
        所以 steps/summary 的既有时序一点都不动——评审 P0 的红线是那三条已经与口播 ±0.5s 对齐。
        """
        if n < 2 or len(group) != n:
            return
        use_at = reveal_keys(at, n)
        for mob, key in zip(group, use_at):
            tag_reveal(mob, key)

    def _v_steps(self, p, th):
        lines = list(p.get("lines", [])[:6])
        body = VGroup(*[rich(l, 30, th["fg"]) for l in lines]).arrange(
            DOWN, aligned_edge=LEFT, buff=0.22
        )
        self._tag_progressive(body, len(lines), p.get("at"))
        # 标题由 IR 给：这一版式既装例题推导，也装拼图与逼近步骤，写死「推导 / 解题步骤」
        # 对「用面积拼一拼」这类镜就是假话（batch_v4 评审）。
        head = T(str(p.get("heading") or "推导 / 解题步骤"), font_size=26, color=th["accent"])
        return VGroup(head, body).arrange(DOWN, aligned_edge=LEFT, buff=0.25)

    def _v_summary(self, p, th):
        pts = list(p.get("points", [])[:6])
        body = VGroup(*[rich("· " + s, 30, th["fg"]) for s in pts]).arrange(
            DOWN, aligned_edge=LEFT, buff=0.24
        )
        self._tag_progressive(body, len(pts), p.get("at"))
        head = T("小结", font_size=26, color=th["accent"])
        return VGroup(head, body).arrange(DOWN, aligned_edge=LEFT, buff=0.25)

    def _v_compare(self, p, th):
        def col(data, color):
            head = rich(data.get("h", ""), 30, color)
            items = VGroup(*[rich(i, 26, th["fg"]) for i in data.get("items", [])[:5]]).arrange(
                DOWN, aligned_edge=LEFT, buff=0.18
            )
            return VGroup(head, items).arrange(DOWN, aligned_edge=LEFT, buff=0.22)

        left, right = col(p.get("left", {"items": []}), th["dim"]), col(p.get("right", {"items": []}), th["accent"])
        bl = RoundedRectangle(width=left.width + 0.6, height=left.height + 0.5, corner_radius=0.1).set_stroke(th["dim"], 2).move_to(left)
        br = RoundedRectangle(width=right.width + 0.6, height=right.height + 0.5, corner_radius=0.1).set_stroke(th["accent"], 2).move_to(right)
        g = VGroup(VGroup(bl, left), VGroup(br, right)).arrange(RIGHT, buff=0.8)
        # 评审 P0：双栏对比此前和 callout 一样在 0.1–0.5s 整屏摊开，之后十几秒纹丝不动，
        # 「刹车陷阱」把正确答案 s = 50 m 提前 9.9s 写在屏上（实测见 .local/rev7_scene/meas）。
        # 揭示单位 = **一行**（左右两栏各自的第 i 条一起出现）：compare 是一张对照表，口播也是
        # 逐行读的（「直接代公式得三十二米，错了」→「车五秒就停下」→「位移应是五十米」），
        # 按行铺既均匀，又不会让一栏抢在另一栏前面；卡片框与两个栏头随第一行走，
        # 免得先挂出两张空卡。rows < 2 时无批可分，行为与原来一致。
        rows = max(len(left[1]), len(right[1]))
        keys = reveal_keys(p.get("at"), rows)
        if rows >= 2 or p.get("at") is not None:
            for box, colv in ((bl, left), (br, right)):
                tag_reveal(box, keys[0])
                tag_reveal(colv[0], keys[0])            # 栏头与第一行同批
                for i, item in enumerate(colv[1]):
                    tag_reveal(item, keys[i])
        return g

    def _v_figure(self, p, th):
        """几何图形原语：把"看得见的那件事"真画出来，而不是只写在字上。

        ellipse（评审 D8：整片讲椭圆却全程无图）/ right_triangle（勾股三边上的正方形）/
        chord（赵爽弦图，"用面积拼一拼"没有图就是空话，batch_v4 评审 U1=2）。
        """
        shape = str(p.get("shape") or "ellipse")
        if shape == "right_triangle":
            return self._f_right_triangle(p, th)
        if shape == "chord":
            return self._f_chord(p, th)
        return self._f_ellipse(p, th)

    def _f_right_triangle(self, p, th):
        """直角三角形 + 三条边朝外的正方形：a²、b² 两块面积合起来正好是 c² 那块。"""
        a = float(p.get("a", 3))
        b = float(p.get("b", 4))
        # 整图（含斜边上那块正方形）不超过 3.3×2.8：这一镜还要和公式卡同屏，_fit 一旦缩放，
        # 30px 的正文会掉到 24px 以下（LEGIBLE 的下限），图形再大就是自找不可读。
        s = min(4.6 / (a + b + max(a, b)), 2.6 / (a + b + min(a, b)))
        A, B, C = [0, 0, 0], [a * s, 0, 0], [0, b * s, 0]     # 直角顶点在原点
        tri = Polygon(*[A, B, C], color=th["key"], stroke_width=5).set_fill(th["key"], 0.28)
        sq_a = Polygon(A, B, [B[0], -B[0], 0], [0, -B[0], 0], color=th["dim"], stroke_width=3)
        sq_b = Polygon(A, C, [-C[1], C[1], 0], [-C[1], 0, 0], color=th["dim"], stroke_width=3)
        # 斜边正方形：BC 的外法向正好是 (b, a)·s，长度等于 |BC|，所以直接平移就是正方形。
        n = np.array([b, a, 0.0]) * s
        sq_c = Polygon(B, C, C + n, B + n, color=th["accent"], stroke_width=4).set_fill(th["accent"], 0.2)
        g = VGroup(tri, sq_a, sq_b, sq_c,
                   rich("a^2", 26, th["fg"]).move_to([a * s / 2, -a * s / 2, 0]),
                   rich("b^2", 26, th["fg"]).move_to([-b * s / 2, b * s / 2, 0]),
                   rich("c^2", 26, th["accent"]).move_to([(a + b) * s / 2, (a + b) * s / 2, 0]))
        if p.get("label"):
            g.add(rich(p["label"], 24, th["key"]).next_to(g, DOWN, buff=0.24))
        # P3 halo：本镜主角叠静态假辉光环（垫底、无脉冲；见 _halo_ring）。
        return VGroup(_halo_ring(g, th["key"], buff=0.18), g)

    def _f_chord(self, p, th):
        """赵爽弦图：四个全等直角三角形的斜边围成边长 c 的大正方形，中间空出边长 b − a 的小正方形。

        与口播严格同构（"拼出一个边长为 c 的大正方形，中间留下一个边长为 b − a 的小正方形"）：
        先前按 a+b 外框画的那版中间是 c²，跟旁白说的正好相反，图与话对不上就是新的 G1 风险。
        """
        a = float(p.get("a", 3))
        b = float(p.get("b", 4))
        c = math.hypot(a, b)
        s = 2.8 / c          # 与 right_triangle 同理：这一镜要和 5 行拼图步骤同屏
        L = c * s
        rot = lambda q: (L - q[1], q[0])                       # noqa: E731  绕正方形中心转 90°
        # 必须逐个 append：写成 v += [rot(v[-1]) for _ in range(3)] 时推导式里读到的 v[-1]
        # 始终是 v[0]（右侧先整体求值），四块三角形会共用同一个内顶点，中间那块"洞"退化成
        # 一个点 —— 弦图当场画成一个正方形加两条对角线。
        v = [(b * b / c * s, a * b / c * s)]
        for _ in range(3):
            v.append(rot(v[-1]))
        corners = [(0, 0), (L, 0), (L, L), (0, L)]
        pts = lambda x, y: [x, y, 0.0]
        # 四块三角形同色同透明度时，整张图读起来就是"正方形加两条对角线"，弦图不见了。
        # 交替两档深浅，拼法（哪四条边是斜边、哪块是洞）才看得出来。
        tris = [Polygon(pts(*corners[i]), pts(*corners[(i + 1) % 4]), pts(*v[i]),
                        color=th["key"], stroke_width=4).set_fill(th["key"], 0.36 if i % 2 else 0.16)
                for i in range(4)]
        hole = Polygon(*[pts(*q) for q in v], color=th["warn"], stroke_width=3).set_fill(th["warn"], 0.6)
        g = VGroup(Polygon(*[pts(*q) for q in corners], color=th["dim"], stroke_width=3), *tris, hole)
        # 旁白点名的就是这块小正方形，可 3-4-5 时它只占大正方形面积的 4%，塞不进字，只能引线到外面。
        hc = np.mean([[x, y, 0.0] for x, y in v], axis=0)
        tip = hc + np.array([1.05, -0.42, 0.0])
        g.add(Line(hc, tip, color=th["warn"], stroke_width=2),
              rich("b − a", 22, th["warn"]).move_to(tip + RIGHT * 0.42))
        # 一条三角形上标清 a、b 两条直角边，斜边标 c：旁白说到哪一块，学生能找到哪一块。
        g.add(rich("b", 24, th["fg"]).move_to([v[0][0] / 2 - 0.16, v[0][1] / 2 + 0.16, 0]),
              rich("a", 24, th["fg"]).move_to([(L + v[0][0]) / 2 + 0.16, v[0][1] / 2, 0]),
              rich("c", 24, th["accent"]).move_to([L / 2, -0.3, 0]))
        if p.get("label"):
            g.add(rich(p["label"], 24, th["key"]).next_to(g, DOWN, buff=0.24))
        # P3 halo：本镜主角叠静态假辉光环（垫底、无脉冲；见 _halo_ring）。
        return VGroup(_halo_ring(g, th["key"], buff=0.18), g)

    def _f_ellipse(self, p, th):
        """椭圆：把"绳长不变"这件事画出来（评审 D8）。"""
        a = float(p.get("a", 5))
        b = float(p.get("b", 3))
        s = min(4.6 / (2 * a), 2.6 / (2 * b))  # 数据单位 → 屏幕单位，整图不超过约 4.6×2.6
        c = math.sqrt(max(a * a - b * b, 0.0))
        curve = Ellipse(width=2 * a * s, height=2 * b * s, color=th["key"], stroke_width=5)
        # P3 halo：椭圆是这一镜的主角，叠一圈同形状、略放大、粗描边低不透明度的假辉光环
        # （静态、无脉冲、垫底；见 _halo_ring 与调研 1.2）。
        halo = Ellipse(width=curve.width * 1.12, height=curve.height * 1.12,
                       stroke_color=th["key"], stroke_width=8, stroke_opacity=0.3, fill_opacity=0)
        halo.move_to(curve.get_center())
        halo.set_z_index(-1)
        ax = Line(LEFT * (a * s + 0.6), RIGHT * (a * s + 0.6), color=th["dim"], stroke_width=2)
        ay = Line(DOWN * (b * s + 0.45), UP * (b * s + 0.45), color=th["dim"], stroke_width=2)
        xlab = T(str(p.get("x_label") or "x"), font_size=22, color=th["dim"]).next_to(ax, RIGHT, buff=0.12)
        ylab = T(str(p.get("y_label") or "y"), font_size=22, color=th["dim"]).next_to(ay, UP, buff=0.08)
        g = VGroup(halo, curve, ax, ay, xlab, ylab)
        if p.get("foci"):
            for sign, name in ((-1, "F_1"), (1, "F_2")):
                f = Dot([sign * c * s, 0, 0], radius=0.06, color=th["warn"])
                g.add(VGroup(f, rich(name, 22, th["warn"]).next_to(f, DOWN, buff=0.1)))
        if p.get("point"):
            t = math.radians(float(p.get("point_angle", 55)))
            pos = [a * math.cos(t) * s, b * math.sin(t) * s, 0]
            dot = Dot(pos, radius=0.06, color=th["accent"])
            g.add(dot, rich("P", 22, th["accent"]).next_to(dot, UP, buff=0.1))
            for sign in (-1, 1):  # 两条焦半径 = 拉紧的绳子
                g.add(DashedLine([sign * c * s, 0, 0], pos, dash_length=0.12,
                                 color=th["accent"], stroke_width=3))
        if p.get("label"):
            # 几何图的标签是**图注**，不是引线标签：椭圆内部被曲线、两轴、两条焦半径占满，
            # 任何落在图内的位置都会压住某条线（test_layout 实测残差 4），教材里这条式子本来也写在图下方。
            g.add(rich(p["label"], 24, th["key"]).next_to(g, DOWN, buff=0.24))
        return g

    def _clear_ticks(self, ticks, lines, boxes, plane) -> tuple[int, int]:
        """刻度数字不得被图线/导引虚线穿过，也不得压住轴名或被推回坐标轴上。

        图线是数据、不能挪；能动的是数字：沿"离开自己那条轴"的方向外推，每档 0.16u≈21.6px
        （= _place_label 给标签的法向余量，同一把尺子），最多三档；原位干净就一律不动。
        三档都不干净就把这一格刻度去掉——少一个数字不影响读图，一条线从数字中间穿过去是坏图
        （数学 B 评审 Q5：抛物线与刻度「−2」实测最小间隙 0.0px）。
        返回 (外推个数, 去掉个数)，同时记进 TICK_ADJUST 供测试读。
        """
        polys = [_sample(m, 80) for m in lines]
        hard = [_pad_box(_box(plane.x_axis), AXIS_PAD), _pad_box(_box(plane.y_axis), AXIS_PAD), *boxes]
        floor = plane.get_bottom()[1] - TICK_SLACK
        wall = plane.get_left()[0] - TICK_SLACK
        dropped = moved = 0
        for t in list(ticks):
            d = np.array(getattr(t, "_tick_dir", DOWN))
            base = np.array(getattr(t, "_tick_anchor", t.get_center()))
            for n in range(4):                      # 0 = 原位
                t.move_to(base + n * 0.16 * d)
                box = _box(t)
                if box[1] < floor or box[0] < wall:  # 脱离图区就不算候选
                    continue
                if any(_poly_hits(poly, box, AXIS_PAD) for poly in polys):
                    continue
                if any(_overlap(box, b) for b in hard):
                    continue
                moved += 1 if n else 0
                break
            else:
                t.move_to(base)                     # 放弃外推：要么原位、要么没有
                ticks.remove(t)
                dropped += 1
        TICK_ADJUST.append((moved, dropped))
        return moved, dropped

    def _v_graph_vt(self, p, th):
        pts = list(p.get("points", [[0, 0], [1, 1]]))
        cases = list(p.get("cases", []))
        # 平面范围 = 主线与所有备选情形的点一起算，且负坐标也要包含在内。
        # 旧写法只按主线正半轴取 max*1.35，含负坐标的二次函数被画到平面外，_fit 再把整组
        # 缩成顶部小块，坐标轴标签糊成 10px（评审 D4）。
        all_pts = pts + [q for c in cases for q in c.get("points", [])]
        xs = [q[0] for q in all_pts if len(q) > 1] + [0]
        ys = [q[1] for q in all_pts if len(q) > 1] + [0]
        x_lo, x_hi = min(xs), max(xs)
        y_lo, y_hi = min(ys), max(ys)
        wx = max(x_hi - x_lo, 1.0)
        wy = max(y_hi - y_lo, 1.0)
        x_lo -= 0.10 * wx if x_lo < 0 else 0.0
        x_hi += 0.14 * wx
        y_lo -= 0.10 * wy if y_lo < 0 else 0.0
        y_hi += 0.18 * wy
        plane = NumberPlane(
            x_range=[x_lo, x_hi, _grid_step(x_lo, x_hi)],
            y_range=[y_lo, y_hi, _grid_step(y_lo, y_hi)],
            x_length=6.4,
            y_length=4.0,
            background_line_style={"stroke_color": th["grid"], "stroke_width": 1},
            axis_config={"stroke_color": th["dim"]},
        )
        # 不用 add_coordinates()：它走 MathTex，需要 LaTeX。刻度用 Text 手搓，保持零 LaTeX 依赖。
        # 刻度贴着自己那条轴排（负半轴时轴在平面中间，不再固定压在底边）。
        # _tick_dir/_tick_anchor：刻度是唯一能让位的东西（图线是数据，不能挪），避让时只能
        # 沿"离开自己那条轴"的方向外推，所以落点与外推方向都要记在数字上。
        def tick(text, pos, shift, escape):
            t = T(text, font_size=20, color=th["dim"]).move_to(pos).shift(shift)
            t._tick_dir = escape
            t._tick_anchor = np.array(t.get_center())
            return t

        step = _grid_step(x_lo, x_hi)
        ystep = _grid_step(y_lo, y_hi)
        ticks = VGroup(
            *[tick(_fmt_tick(v), plane.c2p(v, 0), DOWN * 0.3, DOWN)
              for v in _tick_values(x_lo, x_hi, step) if v != 0],
            *[tick(_fmt_tick(v), plane.c2p(0, v), LEFT * 0.42, LEFT)
              for v in _tick_values(y_lo, y_hi, ystep) if v != 0],
            tick("0", plane.c2p(0, 0), DOWN * 0.3 + LEFT * 0.3, DOWN + LEFT),
        )
        # 轴名来自 IR：数学片写 x/y，物理片不写则沿用 t/s、v/(m·s⁻¹)（评审 D3 的跨学科模板污染）。
        # 走 rich() 而不是裸 Text：轴名里的量符号（t、v、F）必须与同一屏正文里的斜体一致，
        # 单位（s、N、m·s⁻¹）保持正体——否则同一个 t 在图上是正体、在字上是斜体（评审五.3 对全片生效）。
        xlab = rich(str(p.get("x_label") or "t / s"), 22, th["dim"])
        # 轴名**移到平面右缘之外**（第四轮 F-9 / 评审 A D7、B D-10）。此前它停在平面内右下角
        # （x_hi−0.05−宽/2，离轴 0.62u），与末端刻度同处一列：避让为了不让"1"叠在"1 / m"上，
        # 把轴名盒按 AXIS_LABEL_PAD 扩过去，结果**吃掉末端那一格刻度**——全库实测 6 处，
        # 匀变速的 t 轴只标到 8 而面积矩形画到 10、电极电势的 x 轴丢了 1.5 和 2。
        # 轴名是装饰、刻度是数据，谁该让位很清楚：让轴名出界，两端就再没有抢位置的东西。
        xlab.move_to([plane.get_right()[0] + AXIS_NAME_GAP + xlab.width / 2,
                      plane.c2p(x_hi, 0)[1] + 0.16, 0])
        ylab = rich(str(p.get("y_label") or "v / (m·s⁻¹)"), 22, th["dim"])
        ylab.move_to([plane.c2p(0, y_hi)[0] + ylab.width / 2 + 0.2, plane.c2p(0, y_hi)[1] - 0.12, 0])
        coords = [plane.c2p(*q) for q in pts]
        seg = _polyline(coords, th["key"], 5)
        fill = None
        if p.get("area"):  # 面积可视化：图线与横轴之间的填充（匀变速「面积=位移」，评审 D6）
            base = plane.c2p(0, 0)[1]
            outline = list(seg.points) + [[seg.points[-1][0], base, 0], [seg.points[0][0], base, 0]]
            fill = Polygon(*outline, color=th["accent"], stroke_width=0).set_fill(th["accent"], 0.22)
        g = VGroup(plane, *([fill] if fill else []), ticks, xlab, ylab, seg)
        if p.get("dots"):  # 描点法：把取的那几个点真的画成点，否则「描在坐标系里」没有对应画面
            for q in coords:
                g.add(Dot(q, radius=0.07, color=th["accent"]))
        # 斜率辅助三角形：把"陡=大"这件事画出来，而不是只写在字上。
        # 先建好，因为它和图线一样是"刻度数字要让开"的线（一次函数实测：导引虚线贴着 y 刻度
        # 「−1」只有 2.0px，两个都是次要信息，挤在一起就等于都读不到）。
        tri = None
        if p.get("slope_note") and p.get("triangle", True) and not p.get("area") and len(coords) < 4:
            # 采样点≥4 时画的是函数曲线（抛物线），斜率三角形在这里没有物理意义。
            i = max(0, len(coords) // 2 - 1)      # 取中后段，避免贴着坐标轴
            a, b = coords[i], coords[i + 1]
            if len(coords) == 2:                   # 单段线：用中点起三角形，水平边不与横轴重合
                a = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0]
            tri = VGroup(
                DashedLine(a, [b[0], a[1], 0], dash_length=0.12, color=th["dim"], stroke_width=2),
                DashedLine([b[0], a[1], 0], b, dash_length=0.12, color=th["dim"], stroke_width=2),
            )
            g.add(tri)
        # 本镜里**所有**会出现的线（主线 + 各情形线）。
        # 只让开自己那条不够——情形线是后揭示的，一旦穿过先放好的主线标签，
        # 就成了评审在 linear t=78 抓到的「白线正穿过橙色标签的等号」。
        drawn = []
        for c in cases:
            cp = [plane.c2p(*q) for q in c["points"]]
            sub = _polyline(cp, th.get(c.get("tone", "warn"), th["warn"]), 4)
            drawn.append((c, sub))
        # 刻度避让要在标签之前：标签的碰撞盒里装的是刻度的**最终**位置。
        guides = [seg, *(sub for _, sub in drawn), *(list(tri) if tri else [])]
        # 轴名的避让盒要向外扩 AXIS_LABEL_PAD：刻度数字停在轴外 0.3u、轴名停在 0.62u，
        # 两个精确外接框恰好不接触，于是 "1" 与 "1 / m" 上下叠成一列，读起来像 "1/1/m"
        # （batch_v7 newton t=24 实测）。扩到刚好桥住这道缝，末端那一格刻度会被去掉、
        # 轴名留下；再大就会连 y 轴顶端的有效刻度一起吃掉（0.8 时实测少标了 a 轴的 4）。
        label_boxes = [_pad_box(_box(xlab), AXIS_LABEL_PAD), _pad_box(_box(ylab), AXIS_LABEL_PAD)]
        self._clear_ticks(ticks, guides, label_boxes, plane)
        # 图线标签要让开的东西：两条坐标轴 + 刻度数字 + 两个轴名。
        # 轴此前不在避让集里，于是 y 轴竖线正好从 x² 标签中间穿过（数学 B 评审 Q3，实测间隙 1px）。
        taken = [_box(xlab), _box(ylab)] + graph_obstacles(plane, ticks)
        curves = [_sample(seg, 24)]
        for _, sub in drawn:
            curves.append(_sample(sub, 24))
        if p.get("label"):
            g.add(_place_label(rich(p["label"], 24, th["key"]), seg, plane, taken, curves))
        # cases：口播枚举的其它图线情形（更陡/水平/下斜），讲到哪条亮哪条。
        # 没有这一层时画面全程只有一条上升线，字幕说"图线水平"学生却找不到水平线（评审 N1）。
        for c, sub in drawn:
            color = th.get(c.get("tone", "warn"), th["warn"])
            grp = VGroup(sub)
            if c.get("label"):
                grp.add(_place_label(rich(c["label"], 22, color), sub, plane, taken, curves))
            grp._reveal_at = c.get("at", "")
            g.add(grp)
        if p.get("slope_note"):
            g = VGroup(g, rich(p["slope_note"], 26, th["key"])).arrange(DOWN, buff=0.2)
        return g

    # ---------------- 图示类版式（Spec_Video_Defaults 四：所有的都是图表示）----------------
    # 共同约束：只画 IR 给的东西；标注文字 ≥22 号且短；逐项内容带 _reveal_at（无字幕时整体可见）；
    # 整体尺寸控制在正文带内，_fit 只做兜底。
    @staticmethod
    def _norm_guides(items, key):
        out = []
        for it in items or []:
            if isinstance(it, dict) and key in it:
                out.append((float(it[key]), str(it.get("label", ""))))
            elif isinstance(it, (int, float)) and not isinstance(it, bool):
                out.append((float(it), ""))
        return out

    def _v_axis_graph(self, p, th):
        """笛卡尔坐标图：多曲线 + 标记点（带到两轴的引线）+ 水平/垂直辅助线。"""
        curves = [c for c in p.get("curves", []) if isinstance(c, dict) and len(c.get("points", [])) >= 2]
        marks = [m for m in p.get("marks", []) if isinstance(m, dict) and len(m.get("xy", [])) == 2]
        hls = self._norm_guides(p.get("hlines"), "y")
        vls = self._norm_guides(p.get("vlines"), "x")
        xs = [0.0] + [q[0] for c in curves for q in c["points"]] + [m["xy"][0] for m in marks] + [v for v, _ in vls]
        ys = [0.0] + [q[1] for c in curves for q in c["points"]] + [m["xy"][1] for m in marks] + [v for v, _ in hls]
        x_lo, x_hi, y_lo, y_hi = min(xs), max(xs), min(ys), max(ys)
        wx, wy = max(x_hi - x_lo, 1.0), max(y_hi - y_lo, 1.0)
        x_lo -= 0.10 * wx if x_lo < 0 else 0.0
        x_hi += 0.14 * wx
        y_lo -= 0.10 * wy if y_lo < 0 else 0.0
        y_hi += 0.18 * wy
        plane = NumberPlane(
            x_range=[x_lo, x_hi, _grid_step(x_lo, x_hi)], y_range=[y_lo, y_hi, _grid_step(y_lo, y_hi)],
            x_length=6.4, y_length=4.0,
            background_line_style={"stroke_color": th["grid"], "stroke_width": 1},
            axis_config={"stroke_color": th["dim"]},
        )

        def tick(text, pos, shift, escape):
            t = T(text, font_size=20, color=th["dim"]).move_to(pos).shift(shift)
            t._tick_dir = escape
            t._tick_anchor = np.array(t.get_center())
            return t

        ticks = VGroup(
            *[tick(_fmt_tick(v), plane.c2p(v, 0), DOWN * 0.3, DOWN)
              for v in _tick_values(x_lo, x_hi, _grid_step(x_lo, x_hi)) if v != 0],
            *[tick(_fmt_tick(v), plane.c2p(0, v), LEFT * 0.42, LEFT)
              for v in _tick_values(y_lo, y_hi, _grid_step(y_lo, y_hi)) if v != 0],
            tick("0", plane.c2p(0, 0), DOWN * 0.3 + LEFT * 0.3, DOWN + LEFT),
        )
        xlab = rich(str(p.get("x_label") or "x"), 22, th["dim"])
        xlab.move_to([plane.get_right()[0] + AXIS_NAME_GAP + xlab.width / 2, plane.c2p(x_hi, 0)[1] + 0.16, 0])
        ylab = rich(str(p.get("y_label") or "y"), 22, th["dim"])
        ylab.move_to([plane.c2p(0, y_hi)[0] + ylab.width / 2 + 0.2, plane.c2p(0, y_hi)[1] - 0.12, 0])
        g = VGroup(plane, ticks, xlab, ylab)

        guides, notes = [], []
        for v, lab in hls:
            ln = DashedLine(plane.c2p(x_lo, v), plane.c2p(x_hi, v), dash_length=0.12, color=th["dim"], stroke_width=2)
            guides.append(ln)
            if lab:
                notes.append(rich(lab, 22, th["dim"]).next_to(plane.c2p(x_hi, v), UP, buff=0.06).shift(LEFT * 0.5))
        for v, lab in vls:
            ln = DashedLine(plane.c2p(v, y_lo), plane.c2p(v, y_hi), dash_length=0.12, color=th["dim"], stroke_width=2)
            guides.append(ln)
            if lab:
                notes.append(rich(lab, 22, th["dim"]).next_to(plane.c2p(v, y_hi), RIGHT, buff=0.08))
        mark_mobs = []
        for m in marks:
            x, y = m["xy"]
            dot = Dot(plane.c2p(x, y), radius=0.08, color=th["accent"])
            mark_mobs.append(dot)
            if m.get("guides", True):
                for a, b in ((plane.c2p(x, y), plane.c2p(x, 0)), (plane.c2p(x, y), plane.c2p(0, y))):
                    guides.append(DashedLine(a, b, dash_length=0.1, color=th["accent"], stroke_width=2))
            if m.get("label"):
                notes.append(rich(str(m["label"]), 22, th["accent"]).next_to(dot, UP + RIGHT, buff=0.1))
        lines = []
        for c in curves:
            lines.append(_polyline([plane.c2p(*q) for q in c["points"]],
                                   th.get(c.get("tone", "key"), th["key"]), 5))
        self._clear_ticks(ticks, lines + guides, [_pad_box(_box(xlab), AXIS_LABEL_PAD),
                                                  _pad_box(_box(ylab), AXIS_LABEL_PAD)], plane)
        g.add(*guides, *lines, *mark_mobs)
        taken = [_box(xlab), _box(ylab)] + graph_obstacles(plane, ticks) + [_box(n) for n in notes]
        polys = [_sample(ln, 24) for ln in lines]
        for c, ln in zip(curves, lines):
            if c.get("label"):
                color = th.get(c.get("tone", "key"), th["key"])
                g.add(_place_label(rich(str(c["label"]), 24, color), ln, plane, taken, polys))
        g.add(*notes)
        # 曲线逐条出现：有 at 的按口播卡点，没写的按序均匀铺
        if len(lines) >= 2:
            keys = reveal_keys(p.get("at"), len(lines))
            for i, ln in enumerate(lines[1:], start=1):
                tag_reveal(ln, keys[i])
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 26, th["key"])).arrange(DOWN, buff=0.2)
        return g

    def _v_particle_box(self, p, th):
        """粒子盒子：before（隔板左侧挤着）/ after（均匀占满）/ both（前后对照，中间一支箭头）。"""
        import random
        rng = random.Random(int(p.get("seed", 7)))
        n = max(2, min(int(p.get("n", 24)), 60))
        W, H = 3.4, 2.5

        def fill(x0, x1):
            pts = []
            tries = 0
            while len(pts) < n and tries < 4000:
                tries += 1
                q = (rng.uniform(x0 + 0.12, x1 - 0.12), rng.uniform(-H / 2 + 0.12, H / 2 - 0.12))
                if all((q[0] - r[0]) ** 2 + (q[1] - r[1]) ** 2 > 0.07 for r in pts):
                    pts.append(q)
            return pts

        def box(state):
            frame = Rectangle(width=W, height=H, color=th["dim"], stroke_width=3)
            parts = VGroup(frame)
            if state == "before":
                parts.add(DashedLine([0, -H / 2, 0], [0, H / 2, 0], dash_length=0.12, color=th["warn"], stroke_width=3))
                pts = fill(-W / 2, 0.0)
            else:
                pts = fill(-W / 2, W / 2)
            parts.add(*[Dot([x, y, 0], radius=0.07, color=th["accent"]) for x, y in pts])
            return parts

        state = str(p.get("state") or "both")
        cap = {"before": str(p.get("before_label") or ""), "after": str(p.get("after_label") or "")}
        if state == "both":
            def panel(s):
                b = box(s)
                return VGroup(b, rich(cap[s], 24, th["fg"])).arrange(DOWN, buff=0.2) if cap[s] else b
            left, right = panel("before"), panel("after")
            arrow = Arrow(LEFT * 0.5, RIGHT * 0.5, color=th["key"], buff=0, stroke_width=6)
            g = VGroup(left, arrow, right).arrange(RIGHT, buff=0.45)
            tag_reveal(right, 0.5)
            tag_reveal(arrow, 0.5)
        else:
            g = box(state)
            if cap[state]:
                g = VGroup(g, rich(cap[state], 24, th["fg"])).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 26, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _v_microstate(self, p, th):
        """微观态枚举：N 个格子里放 k 个粒子的全部排法（最多 20 种），W 就是图的个数。"""
        cells = max(2, min(int(p.get("cells", 4)), 8))
        k = max(1, min(int(p.get("particles", 2)), cells))
        combos = list(itertools.combinations(range(cells), k))
        total = len(combos)
        combos = combos[:20]
        size = 0.36 if cells <= 6 else 0.3

        def grid(sel):
            sq = VGroup(*[Square(side_length=size, color=th["dim"], stroke_width=2) for _ in range(cells)])
            sq.arrange(RIGHT, buff=0)
            for i in sel:
                sq.add(Dot(sq[i].get_center(), radius=size * 0.32, color=th["accent"]))
            return sq

        grids = VGroup(*[grid(c) for c in combos])
        cols = 4 if len(combos) > 8 else (3 if len(combos) > 4 else len(combos))
        grids.arrange_in_grid(rows=math.ceil(len(combos) / cols), cols=cols, buff=(0.5, 0.35))
        keys = reveal_keys(p.get("at"), len(grids))
        if len(grids) >= 2:
            for gr, key in zip(grids, keys):
                tag_reveal(gr, key)
        w = rich(f"W = {total}", 34, th["key"])
        g = VGroup(grids, w).arrange(DOWN, buff=0.35)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["fg"])).arrange(DOWN, buff=0.25)
        return g

    def _v_energy_dist(self, p, th):
        """能级图 + 玻尔兹曼占据：每个 kT 一幅，点数按 exp(−E/kT) 分配（最大余数法，总数守恒）。"""
        raw_levels = p.get("levels", [0, 1, 2, 3, 4])
        if not isinstance(raw_levels, (list, tuple)):
            raw_levels = [raw_levels]        # KP 数据不规范（如 levels: 7）时兜底，A4 的 KIND 会负责打回
        levels = [float(e) for e in raw_levels][:7]
        if len(levels) < 2:
            levels = [0.0, 1.0]
        temps = [float(t) for t in p.get("kT", [0.5, 1.5])][:3]
        names = list(p.get("names", []))
        n = max(4, min(int(p.get("n", 24)), 60))
        step, width = 0.5, 2.6

        def alloc(kt):
            w = [math.exp(-(e - levels[0]) / kt) for e in levels]
            raw = [n * x / sum(w) for x in w]
            cnt = [int(r) for r in raw]
            for i in sorted(range(len(raw)), key=lambda i: raw[i] - cnt[i], reverse=True)[: n - sum(cnt)]:
                cnt[i] += 1
            return cnt

        panels = []
        for ti, kt in enumerate(temps):
            cnt = alloc(kt)
            g = VGroup()
            for li, c in enumerate(cnt):
                y = li * step
                g.add(Line([0, y, 0], [width, y, 0], color=th["dim"], stroke_width=3))
                per_row = 13
                for j in range(c):
                    g.add(Dot([0.14 + (j % per_row) * 0.19, y + 0.13 + (j // per_row) * 0.14, 0],
                              radius=0.06, color=th["accent"] if ti == 0 else th["warn"]))
            ax = Arrow([-0.25, 0, 0], [-0.25, (len(levels) - 0.3) * step, 0], color=th["dim"], buff=0, stroke_width=3)
            g.add(ax, rich("E", 24, th["dim"]).next_to(ax, LEFT, buff=0.1))
            nm = names[ti] if ti < len(names) else ""
            panels.append(VGroup(g, rich(str(nm), 24, th["fg"])).arrange(DOWN, buff=0.25) if nm else g)
        row = VGroup(*panels).arrange(RIGHT, buff=0.9, aligned_edge=DOWN)
        if len(panels) >= 2:
            for pn, key in zip(panels, reveal_keys(p.get("at"), len(panels))):
                tag_reveal(pn, key)
        if p.get("label"):
            row = VGroup(row, rich(str(p["label"]), 26, th["key"])).arrange(DOWN, buff=0.25)
        return row

    def _v_stat_chart(self, p, th):
        """统计图：bar / hist / pie / scatter。"""
        kind = str(p.get("type") or "bar")
        data = p.get("data", [])
        palette = [th["accent"], th["warn"], th["key"], GREEN_C, BLUE_C, RED_C]
        if kind == "pie":
            items = [(str(d.get("label", "")), float(d.get("value", 0))) for d in data if isinstance(d, dict)]
            tot = sum(v for _, v in items) or 1.0
            pie, legend, ang = VGroup(), VGroup(), 0.0
            for i, (lab, v) in enumerate(items):
                col = palette[i % len(palette)]
                pie.add(Sector(radius=1.35, angle=2 * math.pi * v / tot, start_angle=ang, color=col,
                               fill_opacity=0.55, stroke_width=3))
                ang += 2 * math.pi * v / tot
                legend.add(VGroup(Square(side_length=0.22, color=col).set_fill(col, 0.8),
                                  rich(f"{lab} {v / tot:.0%}", 24, th["fg"])).arrange(RIGHT, buff=0.18))
            legend.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            g = VGroup(pie, legend).arrange(RIGHT, buff=0.7)
            if len(legend) >= 2:
                for sl, lg, key in zip(pie, legend, reveal_keys(p.get("at"), len(legend))):
                    tag_reveal(sl, key)
                    tag_reveal(lg, key)
        elif kind == "scatter":
            pts = [d for d in data if isinstance(d, (list, tuple)) and len(d) == 2]
            xs, ys = [q[0] for q in pts] or [0, 1], [q[1] for q in pts] or [0, 1]
            sx = 4.8 / max(max(xs) - min(xs), 1e-6)
            sy = 2.8 / max(max(ys) - min(ys), 1e-6)
            org = np.array([-2.4 - min(xs) * sx + 0.0, -1.4 - min(ys) * sy, 0.0])
            ax = Line([-2.5, -1.5, 0], [2.7, -1.5, 0], color=th["dim"], stroke_width=3)
            ay = Line([-2.5, -1.5, 0], [-2.5, 1.7, 0], color=th["dim"], stroke_width=3)
            dots = VGroup(*[Dot(org + np.array([x * sx, y * sy, 0.0]), radius=0.07, color=th["accent"]) for x, y in pts])
            g = VGroup(ax, ay, dots,
                       rich(str(p.get("x_label") or "x"), 22, th["dim"]).next_to(ax, RIGHT, buff=0.12),
                       rich(str(p.get("y_label") or "y"), 22, th["dim"]).next_to(ay, UP, buff=0.1))
        else:
            items = [(str(d.get("label", "")), float(d.get("value", 0))) for d in data if isinstance(d, dict)]
            top = max([v for _, v in items] + [1e-6])
            gap = 0.0 if kind == "hist" else 0.25
            bw = 0.62
            bars = VGroup()
            for i, (lab, v) in enumerate(items):
                h = max(2.6 * v / top, 0.04)
                b = Rectangle(width=bw, height=h, color=th["accent"], stroke_width=3).set_fill(th["accent"], 0.45)
                cap = VGroup(b, rich(_fmt_tick(v), 22, th["fg"]).next_to(b, UP, buff=0.06),
                             rich(lab, 22, th["dim"]).next_to(b, DOWN, buff=0.1))
                bars.add(cap)
            for i, c in enumerate(bars):
                c[0].move_to([i * (bw + gap), c[0].height / 2, 0])
                c[1].next_to(c[0], UP, buff=0.06)
                c[2].next_to([i * (bw + gap), 0, 0], DOWN, buff=0.1)
            base = Line([-0.4, 0, 0], [max(len(items) - 1, 0) * (bw + gap) + 0.4, 0, 0], color=th["dim"], stroke_width=3)
            g = VGroup(base, bars)
            if len(bars) >= 2:
                for c, key in zip(bars, reveal_keys(p.get("at"), len(bars))):
                    tag_reveal(c, key)
            if p.get("y_label"):
                g.add(rich(str(p["y_label"]), 22, th["dim"]).next_to(base, LEFT, buff=0.2).shift(UP * 1.2))
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 26, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _v_mind_map(self, p, th):
        """思维导图：中心词 + 左右两侧分支，每个分支带若干子项。分支依次揭示。"""
        branches = [b for b in p.get("branches", []) if isinstance(b, dict)][:6]
        root = VGroup(RoundedRectangle(width=2.3, height=0.9, corner_radius=0.15, color=th["key"], stroke_width=4)
                      .set_fill(th["key"], 0.15), rich(str(p.get("root", "")), 30, th["key"]))
        root[1].move_to(root[0])
        if root[1].width > 2.1:
            root[1].scale_to_fit_width(2.1)
        sides = {1: [], -1: []}
        for i, b in enumerate(branches):
            sides[1 if i % 2 == 0 else -1].append((i, b))
        tags = []
        g = VGroup(root)
        for sgn, lst in sides.items():
            heights = [max(0.8, 0.46 * len(b.get("children", []))) for _, b in lst]
            total = sum(heights) + 0.2 * (len(lst) - 1)
            y = total / 2
            for (i, b), h in zip(lst, heights):
                cy = y - h / 2
                y -= h + 0.2
                col = (th["accent"], th["key"], th["warn"], GREEN_C)[i % 4]
                head = rich(str(b.get("h", "")), 26, col)
                box = RoundedRectangle(width=head.width + 0.4, height=0.62, corner_radius=0.12, color=col, stroke_width=3)
                node = VGroup(box, head)
                node.move_to([sgn * 2.7, cy, 0])
                grp = VGroup(node, Line(root[0].get_edge_center(RIGHT * sgn), node[0].get_edge_center(-RIGHT * sgn),
                                        color=col, stroke_width=2))
                kids = list(b.get("children", []))[:4]
                for j, kid in enumerate(kids):
                    ky = cy + (len(kids) - 1) * 0.23 - j * 0.46
                    t = rich(str(kid), 22, th["fg"])
                    t.move_to([sgn * 4.0 + sgn * t.width / 2, ky, 0])
                    grp.add(t, Line(node[0].get_edge_center(RIGHT * sgn), [sgn * 3.9, ky, 0], color=col, stroke_width=1.5))
                g.add(grp)
                tags.append((i, grp))
        if len(tags) >= 2:
            keys = reveal_keys(p.get("at"), len(branches))
            for i, grp in tags:
                tag_reveal(grp, keys[i])
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _v_table(self, p, th):
        """表格：表头 + 若干行；行依次揭示。"""
        heads = [str(h) for h in p.get("headers", [])]
        rows = [[str(c) for c in r] for r in p.get("rows", []) if isinstance(r, (list, tuple))][:7]
        ncol = max([len(heads)] + [len(r) for r in rows] + [1])
        grid = [heads] + rows if heads else rows
        cells = [[rich(c, 26, th["accent"] if (heads and ri == 0) else th["fg"]) for c in r + [""] * (ncol - len(r))]
                 for ri, r in enumerate(grid)]
        widths = [max(c[ci].width for c in cells) + 0.6 for ci in range(ncol)]
        rh = 0.66
        g = VGroup()
        x = [0.0]
        for w in widths:
            x.append(x[-1] + w)
        tot_w, tot_h = x[-1], rh * len(cells)
        rowgroups = []
        for ri, r in enumerate(cells):
            cy = -ri * rh - rh / 2
            rg = VGroup()
            for ci, c in enumerate(r):
                c.move_to([(x[ci] + x[ci + 1]) / 2, cy, 0])
                rg.add(c)
            rg.add(Line([0, -(ri + 1) * rh, 0], [tot_w, -(ri + 1) * rh, 0], color=th["dim"], stroke_width=2))
            rowgroups.append(rg)
            g.add(rg)
        g.add(Line([0, 0, 0], [tot_w, 0, 0], color=th["dim"], stroke_width=3))
        for xv in x[1:-1]:
            g.add(Line([xv, 0, 0], [xv, -tot_h, 0], color=th["dim"], stroke_width=1.5))
        g.move_to([0, 0, 0])
        if len(rowgroups) >= 2:
            first = 1 if heads else 0
            keys = reveal_keys(p.get("at"), len(rowgroups) - first)
            for rg, key in zip(rowgroups[first:], keys):
                tag_reveal(rg, key)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    BUILDERS = {
        "axis_graph": "_v_axis_graph",
        "particle_box": "_v_particle_box",
        "microstate": "_v_microstate",
        "energy_dist": "_v_energy_dist",
        "stat_chart": "_v_stat_chart",
        "mind_map": "_v_mind_map",
        "table": "_v_table",
        "title": "_v_title",
        "formula": "_v_formula",
        "callout": "_v_callout",
        "steps": "_v_steps",
        "summary": "_v_summary",
        "compare": "_v_compare",
        "graph_vt": "_v_graph_vt",
        "figure": "_v_figure",
    }

    # ---------------- 镜头装配 ----------------
    def _fit(self, mobject, bottom: float = CONTENT_BOTTOM, top: float = CONTENT_TOP):
        """正文既不越安全宽，也不越本镜的内容带 [bottom, top]（末镜的底缘要给出处行让带，见 content_bottom）。"""
        if mobject.width > SAFE_WIDTH:
            mobject.scale_to_fit_width(SAFE_WIDTH)
        if mobject.height > top - bottom:
            mobject.scale_to_fit_height(top - bottom)
        return mobject

    def _corner_tags(self, shot, plan, is_first: bool, is_last: bool, th) -> list:
        """缺陷 3：可追溯出处。首镜右下角知识点 id、末镜左下角出处行，都停在字幕安全区之上。

        原来首镜把 id 放右上角，长 id（kp.physics.uniform_acceleration）会横穿页眉的「物理 · 高一」标签，
        等比缩到 13px 又糊成一团——放到与末镜同一条横带上，两边都不抢位置。
        这一条横带与正文共用，所以角标必须**早于**正文建出来：正文的内容底缘要从它们的上沿往下让
        （评审 P2 / phys-A D39：出处行离正文最后一行只有 9px，投影仪上读成正文的第三行）。

        横向基准（第五轮 F-13 / B D-09 裁定）：角标锚在**页边安全区**（EDGE_BUFF，左缘 123 px），
        正文块居中在**版心**（左缘实测 639 px），两者相差 516 px 是有意的页脚体例——角标属于页面
        元素、与页眉同行同制，正文属于内容元素。改成跟版心对齐会让角标随正文宽度逐镜漂移，
        反而失去"整片同一条基线"，故本轮不动几何，只在语料层统一页码区间体例（全角～）。
        """
        out = []
        if is_first:
            kid = str(plan.get("knowledge_id", ""))
            if kid:
                kp_tag = T(kid, font_size=18, color=th["dim"]).set_opacity(0.85)
                if kp_tag.width > REF_WIDE:
                    kp_tag.scale_to_fit_width(REF_WIDE)
                kp_tag.to_edge(DOWN, buff=SUBTITLE_BAND + CORNER_BAND).to_edge(RIGHT, buff=EDGE_BUFF)
                out.append(kp_tag)
        if is_last:
            refs = shot.get("kp_refs") or [
                f"{r.get('source', '')} {r.get('locator', '')}".strip() for r in plan.get("refs", [])
                if r.get("kind") != "storyboard_budget"
            ]
            if refs:
                # 出处行是"可追溯"这一维唯一的屏上证据，只显 refs[0] 等于把另外几条擦掉
                # （评审 B D41：newton 有三条教材/课标出处，屏上只见一条，且那一条还被砍到 60 字）。
                # 全部列出来；过长的那条折成两行而不是缩字号（第四轮 F-1：ell/ua 的引用行被缩到 12~14px
                # 直接命中 G3 一票否决）。先各自定宽再左对齐排：arrange 之后缩放以中心为锚，长行左沿会错位。
                lines = _ref_texts(refs, th["dim"])
                src_tag = VGroup(*lines).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
                # buff=SUBTITLE_BAND+CORNER_BAND → 整组底边停在字幕带之上 CORNER_BAND 处。
                src_tag.to_edge(DOWN, buff=SUBTITLE_BAND + CORNER_BAND).to_edge(LEFT, buff=EDGE_BUFF)
                out.append(src_tag)
        return out

    def _assemble(self, shot, plan, th, is_first: bool = False, is_last: bool = False):
        """一镜的静态装配（页眉 + 正文栏 + 角标带），不含任何动画：_render_shot 与测试共用这一份几何。"""
        header = rich(shot["title"], 26, th["accent"]).to_edge(UP, buff=0.25)
        # 缺陷 2：页眉学科/学段码中文化，未知值回退原文。
        subject = plan["brief"]["subject"]
        grade = plan["brief"]["grade"]
        tag = T(
            f'{SUBJECT_ZH.get(subject, subject)} · {GRADE_ZH.get(grade, grade)}',
            font_size=18,
            color=th["dim"],
        ).next_to(header, RIGHT, buff=0.5)
        corners = self._corner_tags(shot, plan, is_first, is_last, th)
        content_bottom = content_bottom_for(corners)
        # 内容带上沿：不越过页眉（含右侧学科标签）的最低墨迹，再让开一整块的间距。
        content_top = min(CONTENT_TOP,
                          min(header.get_bottom()[1], tag.get_bottom()[1]) - HEADER_CLEAR)
        blocks = []
        for v in shot["visuals"]:
            m = getattr(self, self.BUILDERS[v["kind"]])(v["props"], th)
            m._kind = v["kind"]    # 渲染动效点名用（P2）：_render_shot 按版式类型挂 Indicate/ShowPassingFlash
            blocks.append(m)
        # 第四轮 F-5（评审 A D3、B 复检1）：不带内部揭示标记的正文块此前随整镜在 t=0
        # 一次铺满——20 个镜次从头到尾画面不变（占比 13%~49%）。steps/summary/callout 早
        # 就按行分批，剩下这些"整块"按镜内进度依次进场，口径与 _tag_progressive 一致
        # （行序比例映射到既有字幕下标，不引入新时长）。已自带逐行揭示的块不接管：
        # 两层揭示会互相屏蔽，反而把逐行降级成逐块。
        plain = [i for i, m in enumerate(blocks)
                 if not any(getattr(x, "_reveal_at", None) is not None for x in m.get_family())]
        if len(plain) >= 2:
            for pos, i in enumerate(plain):
                tag_reveal(blocks[i], pos / len(plain))
        stack = self._fit(
            VGroup(*blocks).arrange(DOWN, buff=STACK_BUFF), content_bottom, content_top
        )
        stack.move_to([0, (content_top + content_bottom) / 2 - 0.1, 0])
        if stack.get_bottom()[1] < content_bottom:  # 红线兜底：正文任何情况下不得进入角标/字幕带
            stack.shift(UP * (content_bottom - stack.get_bottom()[1]))
        return Group(header, tag, stack, *corners), stack, corners

    @staticmethod
    def _first_fx_in(mob) -> str:
        """家族里第一个 _reveal_fx 动效点名（_v_callout 按语气打），没有就返回空串。"""
        for x in mob.get_family():
            tag = getattr(x, "_reveal_fx", None)
            if tag:
                return tag
        return ""

    def _fx_for_reveal(self, mobs, secs: float) -> list:
        """本批揭示单元的强调动效（P2 路由，全部 ManimCE 核心 API）。

        路由（调研 05_visual_style §1.2 / §2）：
          · 公式揭示 → ShowPassingFlash 扫光：打在**黄色副本**上（introducer+remover 自清理），
            本体由同帧 FadeIn 引入、绝不被动画删除；
          · 图形类（FX_GRAPHIC_KINDS）→ Indicate 放大变黄（there_and_back，结束精确还原）；
          · 结论/提醒卡 → _v_callout 点名的 flash（结论揭晓爆闪）/ wiggle（轻提醒）/ indicate。
        run_time 一律由调用方 play(run_time=n/fps) 覆盖；secs 只是上限（镜头不够就压缩动效，
        绝不加长镜头——帧预算纪律见 _render_shot）。
        """
        fx = []
        for m in mobs or ():
            kind = getattr(m, "_kind", "")
            tag = getattr(m, "_reveal_fx", None) or self._first_fx_in(m)
            if tag == "wiggle":
                fx.append(Wiggle(m, scale_value=1.05, n_wiggles=3))
            elif tag == "flash":
                fx.append(Flash(m.get_center(), num_lines=12, line_length=0.35,
                                flash_radius=0.18, line_stroke_width=3,
                                time_width=min(0.3, secs)))
            elif kind == "formula":
                fx.append(ShowPassingFlash(m.copy().set_color(self._th["hi"]),
                                           time_width=min(0.35, secs)))
            elif tag == "indicate" or kind in FX_GRAPHIC_KINDS:
                fx.append(Indicate(m, scale_factor=1.2, color=self._th["hi"]))
        return fx

    def _intro_fx(self, stack, secs: float) -> list:
        """cue 0 时给"开场就在屏上的主角"补一个短动效（P2：重点对象出现后 Indicate）。

        只扫 stack 顶层块；跳过空壳（steps/summary 的行被揭示机制摘走后剩下的空容器——
        点它等于没点）。被揭示机制摘走的块不在这里（collect_reveals 已从父节点移除），
        它们各自的动效由 _fx_for_reveal 在揭示帧播放，互不抢戏。
        """
        fx = []
        for blk in (stack.submobjects if isinstance(stack, VGroup) else []):
            if not blk.family_members_with_points():
                continue
            if getattr(blk, "_kind", "") == "formula":
                fx.append(ShowPassingFlash(blk.copy().set_color(self._th["hi"]),
                                           time_width=min(0.35, secs)))
                continue
            tag = self._first_fx_in(blk)
            if tag == "flash":
                fx.append(Flash(blk.get_center(), num_lines=12, line_length=0.35,
                                flash_radius=0.18, line_stroke_width=3,
                                time_width=min(0.3, secs)))
            elif tag == "wiggle":
                fx.append(Wiggle(blk, scale_value=1.05, n_wiggles=3))
            elif tag == "indicate" or getattr(blk, "_kind", "") in FX_GRAPHIC_KINDS:
                fx.append(Indicate(blk, scale_factor=1.2, color=self._th["hi"]))
        return fx

    def _render_shot(self, shot, plan, is_first=False, is_last=False):
        th = THEMES.get(plan["brief"]["style"], THEMES["clean"])
        body, stack, _corners = self._assemble(shot, plan, th, is_first, is_last)

        # Brief.subtitles=False 时画面不带内嵌字幕（留给外挂 srt / 烧录那一层去做）。
        # 揭示节奏仍按口播字幕时间轴走（否则 steps/compare 整镜全显），subtitles=False 时只是不把字幕画上屏。
        cues = shot.get("subtitles", [])
        show_caps = plan.get("brief", {}).get("subtitles", True)
        reveals, revealed_all = collect_reveals(body, cues)

        # 帧精确记账：manim 会把每个 play() 的 run_time 向上取整到整帧（实测每次 +0.01s，
        # 49 条字幕 × 3 段 + 镜头首尾 ≈ 160 段 → 成片比 Plan 长 0.6s，字幕与配音错开）。
        # 因此这里一律以"整帧数"驱动动画，并把取整误差留在 tail 里吸收，
        # 使每镜实际帧数 == round(seconds × fps)，音画轴与 IR 轴保持重合。
        fps = config.frame_rate
        total_frames = int(round(shot["seconds"] * fps))
        outro_f = min(int(round(OUTRO * fps)), total_frames - 1)
        consumed = 0
        # 强调动效帧预算：最多借 FX_MAX_SEC 的既有 hold/停留帧（并至少留 2 帧给 play），
        # 镜头窗口不够就压缩 run_time——动效从不新增镜头时长。
        fx_cap = max(int(round(FX_MAX_SEC * fps)), 2)

        def frames_at(sec: float) -> int:
            return min(max(int(round(sec * fps)), 0), total_frames - outro_f)

        def hold(n: int) -> None:
            nonlocal consumed
            if n > 0:
                self.wait(n / fps)
                consumed += n

        def anim(mobj, fading_in: bool, n: int, extra=()) -> None:
            nonlocal consumed
            fade = FadeIn if fading_in else FadeOut
            if n <= 0:
                if fading_in:
                    self.add(mobj, *extra)
                else:
                    self.remove(mobj, *extra)
                return
            # 揭示与字幕淡入共用同一段时间，不额外占帧，否则又把 plan 时长撑出去了。
            self.play(fade(mobj), *[fade(e) for e in extra], run_time=n / fps)
            consumed += n

        intro_f = frames_at(INTRO)
        anim(body, True, intro_f)
        want_fi = int(round(0.15 * fps))
        want_fo = int(round(0.12 * fps))
        for i, s in enumerate(cues):
            hold(frames_at(s["start"]) - consumed)
            fx = self._fx_for_reveal(reveals.get(i, ()), FX_MAX_SEC)
            if i == 0:
                fx += self._intro_fx(stack, FX_MAX_SEC)
            if not show_caps:
                # 口播不上屏：揭示按字幕时间轴直接出现（消失-出现），不画字幕。
                if reveals.get(i):
                    self.add(*reveals[i])
                remain = frames_at(s["end"]) - consumed
                fx_n = min(max(remain, 0), fx_cap) if fx else 0
                if fx_n >= 2:
                    # 动效借这段 hold 窗口的帧播，后面的 hold 相应缩短——总帧数不变。
                    self.play(*fx, run_time=fx_n / fps)
                    consumed += fx_n
                hold(max(remain - fx_n, 1))
                continue
            # 字幕也走 rich()：同一句里正文的 y 是斜体、字幕的 y 是正体，读起来像两个东西（五.3 排版规范对全片生效）。
            cap = rich(s["text"], 30, th["fg"]).move_to([0, -4.0 + SUBTITLE_BAND / 2, 0])
            if cap.width > 13.0:
                cap.scale_to_fit_width(13.0)
            span = max(frames_at(s["end"]) - consumed, 1)
            # 淡入/淡出都必须算在字幕窗口之内，且至少留 1 帧淡出，否则残影会挂到下一镜。
            fi = min(want_fi, max(span - 1, 0) // 2)
            fo = min(want_fo, max(span - 1 - fi, 1))
            anim(cap, True, fi, reveals.get(i, ()))
            # 强调动效在揭示淡入**完成之后**、字幕停留窗口内单独 play（与 FadeIn 错开：
            # 同帧两个 Transform 会抢同一 mobject 的插值，后播的会盖掉先播的）。borrow 自 hold 窗口。
            mid = span - fi - fo
            fx_n = min(mid, fx_cap) if fx else 0
            if fx_n >= 2:
                self.play(*fx, run_time=fx_n / fps)
                consumed += fx_n
            hold(mid - fx_n)
            anim(cap, False, fo)

        hold(total_frames - outro_f - consumed)
        # 揭示出来的子元素已经从 body 里摘出去了，收尾必须一起淡出，
        # 否则它们会留在画面上叠进下一镜（实测：上一镜的 5 行步骤整段糊在下一镜的图上）。
        anim(body, False, outro_f, revealed_all)
