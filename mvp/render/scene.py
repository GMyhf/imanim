"""A5 渲染：ManimCE 消费 Plan IR 出无声视频。

渲染层零内容判断（Spec_Workflow 第 1 节）：IR 说画什么就画什么，只额外保证不越界。
公式与推导行走 LaTeX（xelatex + xeCJK，见 texform.py；缺 TeX 时退回 rich）；正文标签与字幕
仍走 Text/Pango + Unicode（Schedule C7 已实测中文与 Δ 字形正常）。
"""

from __future__ import annotations

import difflib
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
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 82-SD1a：运动层与 scene 同目录
import font_metrics  # noqa: E402  字体度量标定表（阻断项③），纯标准库
import mech_anchors as _ma  # noqa: E402  82-SB mechanism 锚点表（纯标准库，与 pipeline/review.py 同一份语义）
import motion as _mo  # noqa: E402  82-SD1a 运动原语层（mvp/render/motion.py，反向 import 本模块的只有 scene）
import texform as _texform  # noqa: E402  82-F1 公式文本 → LaTeX 纯函数层（texform.py）

from manim import (
    BOLD,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    BLUE_C,
    Arrow,
    Circle,
    DashedLine,
    DashedVMobject,
    Dot,
    Rectangle,
    Sector,
    Square,
    Ellipse,
    Arc,
    ArcBetweenPoints,
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
    LaggedStart,
    Line,
    NumberPlane,
    Polygon,
    CubicBezier,
    RoundedRectangle,
    Scene,
    ShowPassingFlash,
    Text,
    Transform,
    TransformFromCopy,
    ValueTracker,
    VMobject,
    VGroup,
    Wiggle,
    Write,
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
FX_MAX_SEC = _mo.FX_MAX_SEC    # 单个强调动画最多借用的秒数。82-SD1a 单源收口（82-M0 §6.5）：
#                                值不变（0.5），事实源改钉在 motion.py；改一处只改 motion.py。
# ---- 82-SD1a 运动播放段口径 ----
# 单镜动效总借帧 ≤ 镜帧数 × MOTION_BUDGET_RATIO（D4 §4.2-3 / 82-M0 §6.1）；超预算按契约
# 降级（先保「揭示/强调」语义最强 beat，压暗类靠后），降级逐条记入 _motion_ledger 可观测，
# 绝不静默全丢。播放一律 motion.snap_run_time 整帧对齐（QUALITY_FPS 15/30 同尺）。
MOTION_BUDGET_RATIO = 0.80     # 单镜运动播放段总借帧上限（占镜帧数比例）。M0 原定 0.35，
#                                实测文字镜只动 0.8s/2.1s cue → 静止帧 51~57% 不过 SD1a/E
#                                验收线；用户口径是「全流程全视频、每一步都要动」，且揭示拍
#                                只借 cue 内 hold 帧、不新增时长，35% 帽无时长保护意义，故放宽。
#                                剩余 20% 仍留给口播停顿与呼吸感（不是每帧都必须有位移）。
REVEAL_RUN_SEC = 1.0           # M6 逐条揭示/强调单拍时长（15帧@15fps；口播读到哪亮到哪）。
#                                0.8s 实测静止帧 55~58% 不过 SD1a ≤50% 验收线：2.1s 的 cue 窗口里
#                                只动 0.8s，剩余 hold 全是静止。1.0s + 回扫 0.8s≈预算 96% 用满。
SWEEP_RUN_SEC = 0.8            # 镜尾回扫单拍（12帧）：与 REVEAL 合计不超过 35% 借帧预算
MOTION_WINDOW_MIN_F = 2        # 一个 beat 至少要有 2 帧可播，否则降级（1 帧无过程可言）
# 这些版式是"本镜主角"（图形类）：出场/揭示时挂 Indicate 点名。
FX_GRAPHIC_KINDS = ("figure", "graph_vt", "axis_graph", "particle_box", "microstate",
                    "energy_dist", "stat_chart", "mind_map", "table",
                    "force_diagram", "field", "circuit", "optics", "incline", "trajectory",
                    "rod_rails", "derivation", "mechanism")
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
    """xelatex + dvisvgm 都能找到才算可用；Windows 上顺手把 MiKTeX 的 bin 补进 PATH。

    82-F1：公式模板固定走 xelatex（要 xeCJK 排中文下标），输出 .xdv 交给 dvisvgm，
    所以 latex 不再是判据——只有 xelatex 时 dvisvgm 无从下手，缺一个就整体退回 rich()。
    """
    import shutil
    extra = os.environ.get("MVP_TEX_BIN", r"D:\App\MiKTeX\miktex\bin\x64")
    if shutil.which("xelatex") is None and os.path.isdir(extra):
        os.environ["PATH"] = extra + os.pathsep + os.environ["PATH"]
    return shutil.which("xelatex") is not None and shutil.which("dvisvgm") is not None


_TEX_OK = None
_TEX_TEMPLATE = None


def _tex_math(*texs, font_size, color=None):
    """MathTex 唯一出口（xelatex + xeCJK 模板，逐 token 的多参数版本也走这里）。

    没装 TeX / 缺宏包 / 编译失败一律返回 None，由调用方退回 rich()——绝不让一条公式
    把整片渲染打断。86 个宏包在 MiKTeX 上首次编译会按需安装，耗时但只发生一次。
    """
    global _TEX_OK, _TEX_TEMPLATE
    if _TEX_OK is None:
        _TEX_OK = _find_tex_bin()
    if not _TEX_OK or not texs:
        return None
    try:
        from manim import MathTex, TexTemplate
        if _TEX_TEMPLATE is None:
            tpl = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
            # 中文下标必须是 \hbox{\fontsize{0.5em}{...}\selectfont 停}（见 texform._SUB_WRAP）：
            # xeCJK 下 \text{停} 在下标里按全字号落在基线上，既不小也不沉。
            tpl.add_to_preamble(
                r"\usepackage{amsmath,amssymb}"
                r"\usepackage{graphicx}"
                r"\usepackage{xeCJK}"
                r"\IfFontExistsTF{SimSun}{\setCJKmainfont{SimSun}}"
                r"{\setCJKmainfont{Noto Serif CJK SC}}"
                r"\usepackage{mathptmx}"
            )
            _TEX_TEMPLATE = tpl
        return MathTex(*[str(t) for t in texs], font_size=font_size, color=color,
                       tex_template=_TEX_TEMPLATE)
    except Exception as e:  # noqa: BLE001  TeX 缺包/语法错：退回 Unicode 排版，不让整片渲染失败
        print(f"[tex] fallback to rich(): {type(e).__name__}", file=sys.stderr)
        return None


def _tex_formula(tex, font_size, color):
    """公式卡片走 LaTeX（Times 系数学字体）；没装 TeX 或编译失败返回 None，由调用方退回 rich()。"""
    return _tex_math(tex, font_size=font_size, color=color)


# 每次 _place_label 的落点残差（分数, 标签文本），进程内累积；tests/test_layout.py 全库回归用。
PLACEMENTS: list = []

# 每次 _v_graph_vt 的刻度避让结果 (外推个数, 去掉个数)，同样进程内累积：刻度是"能让位的那一半"，
# 它动了多少必须看得见，否则避让到底生效没有只能靠肉眼翻帧（评审 P1 的自检口径）。
TICK_ADJUST: list = []

# 81-S4：候选位（含字号微缩/换锚点兜底）全部耗尽后仍然压线或撞字的标签登记在这里（必挂冲突）。
# 与 PLACEMENTS 的区别：PLACEMENTS 是"每次落位的残差"（回归断言读它），UNRESOLVED 是"机器自认
# 救不回来"的清单——非空即说明有标签在成片里注定叠字，收口与排障先看这里。
UNRESOLVED: list = []

# 81-S4：全链复核（_resolve_label_clashes）每次**真的挪了字**记一条 (标签文本, 挪动距离)。
# 测试用它反证复核不是空转：语料里没有挪动记录 = 要么真干净、要么机器没接上。
CLASH_MOVED: list = []

# 82-SB：mechanism 弯箭头端点锚定超差登记 (端点名, 距最近锚点_单位)。渲染装配期由
# _v_mechanism 落笔前自测，run.py 重放链（replay_unresolved）收集后转成 report 级
# MECH_ARROW_DRIFT finding——错位可报告化，与 LABEL_CLASH 同口径记账、不拦出片。
MECH_DRIFT: list = []

# ---- 上下标排版（评审 P1 第 2 条：v_t / s^2 必须排成真下标/上标）----
# 标签级文本不走 LaTeX（82-F1 起只有公式/推导行走 xelatex，标签仍走 Pango）；
# 实测 Unicode 下标**字母**（ₐₑₜ…）在字体栈里是豆腐块，Unicode 下标数字
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

# ---- 81-S5 化学式上下标归一化（渲染层兜底，纯函数便于单测）----
# 根因实测（.local/81S5_smoke 实拍帧）：
#   ① Unicode 上标混排在长段里时只有**纯数字**（²³）能靠字形自身抬升读对；⁺⁻ 在本字体栈
#     落回满号基线（"Cu²⁺" 屏上读成 "Cu²+"，电荷错位）；下标转换把 ² 拆成独立尾段后，
#     Pango 按墨迹裁剪令其底缘贴基线（"SO₄²⁻" 屏上读成 "SO₄₂⁻"，指数掉进下标行=乱码主案）。
#   ② 上下标**字母**（ₐₑₜ… ᵃᶜ…，review.py TOFU 黑名单同源）不经转换直接送字体栈。
#   ③ ASCII 化学式（"H2SO4"）不进任何下标道。
# 对策（全部挂在 rich() 的统一分词入口，不碰 S4/S2 锁定机器）：
#   A. 上标段扩展：Unicode 上标一律改走手工基线 ^ 道（82-SA 撤销 D27「纯数字上标混排不拆段」
#      豁免——容器字体池缺 64/69 白名单字形（.local/82D1_report.md C1），原样送字体层就是
#      .notdef 黑块；本机 Windows 系统回退曾掩盖此事。²³ 也统一 ^ 道，观感由 SUP_LIFT 标定）。
#   B. 下标段扩展到字母，与上标字母一起映射回 ASCII 再进 _/^ 道（82-SA 撤销「前邻判据」：
#      「第₂周期」「（₂）」这类前邻中文/全角括号的下标同样必须转换）。
#   B+. 终兜底 _script_fallback（82-SA P1）：rich_tokens 尾部再扫一遍，任何仍含白名单
#      Unicode 上下标字符的 token（含 _/^ 标记道 payload）一律强制映射进 _/^+ASCII 道——
#      白名单字符在生产渲染中零残留，不再依赖任何字形覆盖，也不依赖主路径判据不出漏网。
#   C. ASCII 化学式（数字紧跟元素符号）按元素白名单 + 「≥2 种元素且带计量数字」双门槛识别，
#      转成 下标数字/上标电荷；"R1""I2""Cu2+""2s" 这类单元素或物理标号一律不转（不误伤）。
#   D. 化学语境（紧跟转换出的下标/上标）的纯元素符号段走正体——元素符号 IUPAC 正体，
#      实拍旧帧里 H₂SO₄ 被斜体判定排成变量体也是本案"乱码"观感的一半。
# 取舍：MathTex/LaTeX 现在服务 _v_formula 卡片与 _v_derivation 推导行（82-F1，缺 TeX 都要退回、
# 字体与全片 SimSun 脱钩、帧预算翻倍）；标签级文本仍走既有「分段 Text + 基线偏移」机器，
# 与 v₀/t_{停}² 同一条道。
_ELEMENTS = frozenset("""
H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge
As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm
Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th
Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og
""".split())
# 下标：数字 + 正负号括号 + 下标字母（含 review.py TOFU 全集）；上标同理。
_SUB_MAP = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7",
            "₈": "8", "₉": "9", "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
            "ₐ": "a", "ₑ": "e", "ₔ": "e", "ₕ": "h", "ᵢ": "i", "ⱼ": "j", "ₖ": "k", "ₗ": "l",
            "ₘ": "m", "ₙ": "n", "ₚ": "p", "ₛ": "s", "ₜ": "t", "ᵤ": "u", "ᵥ": "v", "ₓ": "x"}
_SUP_MAP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
            "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")", "ⁿ": "n",
            "ᵃ": "a", "ᵇ": "b", "ᶜ": "c", "ᵈ": "d", "ᵉ": "e", "ᵍ": "g", "ⁱ": "i", "ʲ": "j",
            "ᵏ": "k", "ˡ": "l", "ᵐ": "m", "ᵒ": "o", "ᵖ": "p", "ʳ": "r", "ˢ": "s", "ᵗ": "t",
            "ᵘ": "u", "ᵛ": "v", "ʷ": "w", "ˣ": "x", "ʸ": "y", "ᶻ": "z"}
_SUB_RUN = re.compile("[" + "".join(_SUB_MAP) + "]+")
_SUP_RUN = re.compile("[" + "".join(_SUP_MAP) + "]+")
# 82-SA 终兜底用：下标∪上标白名单全集（_script_fallback 的扫描尺子）。
_ALL_SCRIPT_RUN = re.compile("[" + "".join(set(_SUB_MAP) | set(_SUP_MAP)) + "]+")
_CHEM_RUN = re.compile(r"[0-9A-Za-z+\-]+")


def _formula_walk(s, i, acc):
    """从元素符号处继续解析：单字母优先（NH3=N+H₃ 不是 Nh+₃），失败回溯两字母（NaCl）。"""
    if i >= len(s):
        return acc if _formula_ok(acc) else None
    for L in (1, 2):
        cand = s[i:i + L]
        if len(cand) == L and cand in _ELEMENTS:
            r = _formula_count(s, i + L, acc + [(cand, "el")])
            if r is not None:
                return r
    return None


def _formula_ok(acc):
    els = {t for t, k in acc if k == "el"}
    return len(els) >= 2 and any(k == "count" for _, k in acc)


def _formula_count(s, i, acc):
    """元素符号之后：可选计量数字（下标），或收尾/电荷尾巴（上标），或下一个元素（H2SO4 的 S）。"""
    if i < len(s) and s[i].isdigit():
        j = i
        while j < len(s) and s[j].isdigit():
            j += 1
        r = _formula_walk(s, j, acc + [(s[i:j], "count")])
        if r is not None:
            return r
    if i == len(s):
        return acc if _formula_ok(acc) else None
    mc = re.match(r"^(\d*)([+\-])$", s[i:]) or re.match(r"^([+\-])(\d*)$", s[i:])
    if mc and _formula_ok(acc):
        return acc + [(s[i:], "charge")]
    if not s[i].isdigit():
        # 不带数字的元素（SO4 的 S、KMnO4 的 KMn…）：继续往后走，收尾仍要过双门槛
        return _formula_walk(s, i, acc)
    return None


def parse_formula(run):
    """纯函数：ASCII 片段 → [(chunk, role)]（role: coef/el/count/charge）或 None。

    文法：[配比系数数字] (元素符号 [计量数字])+ [电荷 数字?± / ±数字?]。
    双门槛防误伤：≥2 种不同元素符号 + ≥1 个紧跟元素的计量数字。
    "H2SO4"→H₂SO₄ ✓；"R1"/"I2"/"Cu2+"/"2s"/"NaCl"（无数字）→ None（维持现行为）。
    """
    s = str(run or "")
    if not s:
        return None
    i = 0
    acc = []
    if s[0].isdigit():
        j = 0
        while j < len(s) and s[j].isdigit():
            j += 1
        acc.append((s[:j], "coef"))
        i = j
    return _formula_walk(s, i, acc)


def _chem_hit(run):
    """_CHEM_RUN 的一个匹配是否为化学式（要求左右邻不是字母数字——最大片段自身已保证）。"""
    return parse_formula(run) is not None


def chem_formula_hit(text):
    """纯函数：文本里是否出现可归一化的 ASCII 化学式片段（供 _v_title 快路径与单测用）。"""
    return any(_chem_hit(m.group()) for m in _CHEM_RUN.finditer(str(text or "")))


def _split_elements(s):
    """s 能否整体拆成元素符号串（单字母优先回溯：NH=N+H；NaCl=N 走不通→Na+Cl）。"""
    if not s:
        return True
    for L in (1, 2):
        if s[:L] in _ELEMENTS and _split_elements(s[L:]):
            return True
    return False


def _upright_element_chunk(s):
    """纯字母数字段（如 H / SO / Ba / 2H）若字母部分能整体拆成元素符号串，判为化学式语境。"""
    letters = re.sub(r"[0-9]", "", s)
    if not letters or not re.fullmatch(r"[A-Za-z]+", letters):
        return False
    return _split_elements(letters)


def rich_tokens(text):
    """纯函数（81-S5 统一分词入口）：IR 文本 → [(kind, s, upright)]。

    kind: "" 普通 / "_" 下标 / "^" 上标；upright=True 表示该普通段处于化学式语境，排正体。
    规则优先级：ASCII _/^ 标记 > Unicode 上下标 > ASCII 化学式；三者都不沾的文本
    原样返回单个 ("", 原文, False)——rich() 据此走单 Text，行为与旧版逐字相同。
    82-SA 终兜底（_script_fallback）：无论主路径判据怎么走，**返回的 token 流里保证不含
    任何 Unicode 上下标白名单字符**（.local/82D1_report.md C1：容器字体池缺其中 64 个字形，
    原样进字体层=.notdef 黑块）。上下标语义不变——仍按 _/^ 道排成基线偏移的小字。
    """
    toks = []
    for p in [q for q in _MARKUP.split(str(text or "")) if q != ""]:
        if p[:1] in ("_", "^") and len(p) > 1:
            toks.append((p[0], p[2:-1] if p[1:2] == "{" else p[1:], False))
            continue
        toks.extend(_plain_tokens(p))
    return _script_fallback(toks)


def _script_fallback(toks):
    """82-SA P1 终兜底：token 流里残留的 Unicode 上下标白名单字符一律清零。

    主路径（_plain_tokens）已无条件转换，这里是最后一道闸：哪怕将来又开「故意不转换」
    的口子、或 _/^ 标记道 payload 里带出白名单字符（如 "_{₂}"），也强制映射进 _/^+ASCII
    自绘道——渲染语义保持（下标仍下标小字、上标仍上标小字），生产渲染零字形依赖。
    """
    out = []
    for kind, s, up in toks:
        if not any(c in _SUB_MAP or c in _SUP_MAP for c in s):
            out.append((kind, s, up))
            continue
        if kind in ("_", "^"):
            # 标记道 payload：同道换 ASCII（₂→"2" 排下标、²→"2" 排上标，非白名单字符原样留）
            out.append((kind, "".join(_SUB_MAP.get(c) or _SUP_MAP.get(c) or c for c in s), up))
            continue
        i = 0
        for m in _ALL_SCRIPT_RUN.finditer(s):
            if m.start() > i:
                out.append(("", s[i:m.start()], up))
            run = m.group()
            k = 0
            while k < len(run):                # 一个连续串里下标/上标类可能交替（"₂²"）
                is_sub = run[k] in _SUB_MAP
                j, buf = k, []
                while j < len(run) and (run[j] in _SUB_MAP) == is_sub:
                    buf.append(_SUB_MAP.get(run[j]) or _SUP_MAP.get(run[j]))
                    j += 1
                out.append(("_" if is_sub else "^", "".join(buf), False))
                k = j
            i = m.end()
        if i < len(s):
            out.append(("", s[i:], up))
    return out


def _plain_tokens(p):
    """把一个非 _/^ 标记的普通段切成 token 流（见 rich_tokens 的规则优先级）。

    82-SA：撤销「下标前邻判据」与「D27 纯数字上标豁免」两条「故意不转换」通道，
    Unicode 上下标白名单字符在本函数出口即无原样残留；_script_fallback 只是终扫保险。
    """
    ev = []                                   # (start, end, kind, payload)
    for m in _CHEM_RUN.finditer(p):
        parsed = parse_formula(m.group())
        if parsed is not None:
            ev.append((m.start(), m.end(), "chem", parsed))
    for m in _SUB_RUN.finditer(p):
        # 82-SA：撤销「前邻 [A-Za-z0-9)\]] 判据」——下标白名单字符无条件转 _ 道
        # （「第₂周期」「（₂）」这类前邻中文/全角括号的，容器字体池同样缺字形，原样送=黑块）。
        ev.append((m.start(), m.end(), "sub", m.group()))
    for m in _SUP_RUN.finditer(p):
        # 82-SA：撤销 D27「纯数字上标混排不拆段」豁免——上标白名单字符无条件转 ^ 道，
        # 屏上与旧 ^ 道完全一致（ASCII 小字号+手工基线抬升，不依赖任何 Unicode 字形）。
        ev.append((m.start(), m.end(), "sup", m.group()))
    if not ev:
        return [("", p, False)]
    ev.sort()
    out, j = [], 0
    prev_conv = False        # 上一个事件是否为转换出的下标/上标（化学语境相邻判据）
    for a, b, kind, payload in ev:
        if a < j:            # chem 段与 Unicode 段理论上不重叠（字符集不相交），保守跳过
            continue
        if a > j:
            seg = p[j:a]
            # ①段尾紧贴转换下标/上标的元素符号串（"… + SO"₂）→ 拆出来排正体
            if kind in ("sub", "sup"):
                m = re.search(r"[A-Za-z]+$", seg)
                if m and _upright_element_chunk(m.group()):
                    if m.start() > 0:
                        out.append(("", seg[:m.start()], False))
                    seg = None
                    out.append(("", m.group(), True))
            if seg is not None:
                # ②段首紧跟转换下标/上标的元素符号串（2H₂"O"、BaSO₄"↓" 前的 O）→ 拆出正体
                m2 = re.match(r"[A-Za-z]+", seg) if prev_conv else None
                if m2 and _upright_element_chunk(m2.group()):
                    out.append(("", m2.group(), True))
                    if m2.end() < len(seg):
                        out.append(("", seg[m2.end():], False))
                else:
                    out.append(("", seg, False))
        if kind == "chem":
            for t, role in payload:
                if role == "count":
                    out.append(("_", t, False))
                elif role == "charge":
                    out.append(("^", t, False))
                else:                         # coef / el：普通道，元素语境正体
                    out.append(("", t, True))
        elif kind == "sub":
            out.append(("_", "".join(_SUB_MAP[c] for c in payload), False))
        else:
            out.append(("^", "".join(_SUP_MAP[c] for c in payload), False))
        prev_conv = kind in ("sub", "sup")
        j = b
    if j < len(p):
        seg = p[j:]
        m2 = re.match(r"[A-Za-z]+", seg) if prev_conv else None
        if m2 and _upright_element_chunk(m2.group()):
            out.append(("", m2.group(), True))
            if m2.end() < len(seg):
                out.append(("", seg[m2.end():], False))
        else:
            out.append(("", seg, False))
    return out


def _has_scripts(s):
    """文本是否会被 rich_tokens 拆出上下标段（_v_title 渐变快路径的绕行判据，81-S5）。

    82-SA 终兜底后：只要文本含任一 Unicode 上下标白名单字符（或 _/^ 标记），rich_tokens 一律
    拆段，_has_scripts 即 True，标题退回 rich() 分段拼接（无连续渐变）——这是「白名单字符零
    残留」的必然结果，观感由 ^/_ 道自绘基线偏移小字承载。纯无上下标的标题仍走渐变艺术字。
    """
    toks = rich_tokens(s)
    return len(toks) != 1 or toks[0][0] != ""

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


def _compose(core, fs, color, kw, upright=False):
    """按逐字符斜体判定生成 Text：只把拉丁单字母变量交给 t2s 斜体，其余（CJK/单位/数字）正体。

    走 Text 的 t2s（子串→slant），不拆分片段、不改宽度累加，避免破坏既有空格/拼接。
    同一字母在同一片段里既像变量又像单位时（罕见），保守取正体，绝不斜体单位。
    upright=True（81-S5）：该段处于化学式语境（元素符号紧跟转换出的下标/上标），
    跳过斜体判定——元素符号 IUPAC 正体，实拍旧帧把 H₂SO₄ 排成变量斜体是乱码观感的一半。
    """
    if upright:
        return T(core, font_size=fs, color=color, **kw)
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
    81-S5：分词规则（Unicode 上下标字母/电荷/ASCII 化学式/元素正体）全部收进纯函数
    rich_tokens()，本函数只管排版——单测对 token 断言，不必拉起 Text 对象。
    """
    toks = rich_tokens(text)
    if not toks:
        return T("", font_size=font_size, color=color, **kw)
    if len(toks) == 1 and not toks[0][0]:
        return _compose(toks[0][1], font_size, color, kw, toks[0][2])

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
    for kind, s, _up in toks:
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
        t = _compose(core, fs_eff, color, kw, _up if not kind else False)
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


# ---- 82-SD1b 推导过程动画的四个薄壳动画 ----
# 推导的每步都是「构建期透明、到 cue 才出现/变形」的 token；Manim 原语在 alpha=0 时
# 要么写不出墨（Write/FadeIn 按当前 alpha 复制），要么会把嵌套 mobject 从父组摘走
# （FadeOut 的 Scene.remove 会拆散顶层 body）。下面四个类只补 begin/finish 两个开关
# 或改走 Transform，不改变场景树——镜尾 remove(body) 仍然一次清干净。
class _LateWrite(Write):
    """到 cue 才书写：begin 先把整行点亮，再交给 Write 描轮廓。

    Write/DrawBorderThenFill 的轮廓副本继承当前 alpha；构建期透明的行直接写会全程不可见。
    """

    def begin(self):
        self.mobject.set_opacity(1)
        super().begin()


class _LateFadeIn(FadeIn):
    """到 cue 才淡入：begin 先点亮，FadeIn 的起始副本才是「从 0 到当前色」而不是「0 到 0」。"""

    def begin(self):
        self.mobject.set_opacity(1)
        super().begin()


class _TokenMorph(Transform):
    """逐 token 原位形变：旧 token 直接变成新 token 的形/色（不换引用）。

    不用 ReplacementTransform：Scene.replace 会把新 token 从新行组摘走、塞进旧行组，
    同一 mobject 出现两个父引用；下一步再 replace 时 BFS 只替换第一处，画面上新旧同屏。
    Transform 不改场景树，行组结构稳定，镜尾整块清理也干净。
    """

    def create_target(self):
        target = self.target_mobject.copy()
        target.set_opacity(1)      # 新行 token 构建期透明，形变目标必须是「落定可见」的
        return target


class _ValueFly(TransformFromCopy):
    """value_flyin 的透明槽薄壳：目标字母先隐身，值从来源飞入、落定后才点亮。

    动画本体仍是 TransformFromCopy（来源→槽位，来源留在原地=复印件语义），只补
    begin/finish 两个开关，满足「先腾出槽位、再点亮字母」的推导口径。
    """

    def begin(self):
        self.mobject.set_opacity(0)
        super().begin()

    def finish(self):
        super().finish()
        self.mobject.set_opacity(1)


class _Dissolve(Transform):
    """嵌套 token 的退场：形变到「同点缩小 + 全透明」的幽灵，不用 FadeOut。

    FadeOut 是 remover，clean_up 的 Scene.remove 会把嵌套 token 从父组摘掉，Scene 的
    restructure 随之把顶层 body 拆散——镜尾 remove(body) 就找不到整块，残影跨镜。
    Transform 只改形态不动场景树；幽灵目标在 begin 时按**当帧**几何生成，_fit 后的
    缩放/位移也跟得上。
    """

    def create_target(self):
        ghost = self.mobject.copy()
        ghost.set_opacity(0)
        ghost.scale(0.05, about_point=self.mobject.get_center())
        return ghost


def _live_update(build):
    """带初值的 always_redraw：装配期先有一份真实几何（_fit 才量得到尺寸），之后每帧重建。

    manim 的 always_redraw 初始是空 Mobject，进 stack 时宽高为 0，会把版面预算算错；
    另外它的重建坐标是装配坐标系，_fit 一缩放就跳回原尺寸。这里的 build 由调用方读
    **静态导轨/标签的当前几何**换算坐标与字号，所以 _fit 的缩放/位移每帧都跟得上。
    """
    mob = build()

    def _sync(m):
        fresh = build()
        m.become(fresh)
        # Text.become 只搬字形点、不改 .text 串：动态读数把真值挂 _live_state 供测试/排障读取。
        if hasattr(fresh, "_live_state"):
            m._live_state = fresh._live_state

    mob.add_updater(_sync)
    return mob


# ---- 82-SD2a1 场图示过程动画小工具 ----
# 共同纪律：beats 在 builder 构造期生成（早于 _assemble 的 _fit），所以这里一律不缓存
# 「装配期屏幕坐标」——缩放/位移每帧从**已变换的参考图元**（导线截面、磁铁本体、转轴圆点）
# 现算；tracker 停住后 updater 直接返回，退场淡出/落定强调不会被抢回不透明度。


def _clamp01(x) -> float:
    x = float(x)
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _wave_reveal(mob, u_of, q: float, *, ramp: float = 0.32, scale_from: float = 0.55,
                 stroke_only: bool = False):
    """成波显形：tracker 0→1 时按波前位置 q∈[0,1]（到源区距离归一化）逐帧算不透明度+缩放。

    q 由布局模型坐标算出（_fit 前，与屏幕尺度无关）；缩放锚点每帧取 mobject **当前**中心
    （已被 _fit 变换），不缓存装配期绝对坐标。u 不变即不写，避免与退场 FadeOut 抢状态。
    ``stroke_only``：同心圆这类「只有描边、无填充」的图元必须只改 stroke——set_opacity 会把
    fill 也点亮，圆环就变成实心盘（82-SD2a1 冒烟首帧实测）。
    """
    st: dict = {"a": -1.0, "k": 1.0}

    def _upd(m):
        a = _clamp01((_clamp01(u_of()) * (1.0 + ramp) - q) / ramp)
        if abs(a - st["a"]) < 1e-9:
            return
        st["a"] = a
        k = scale_from + (1.0 - scale_from) * a
        if abs(k - st["k"]) > 1e-9:
            m.scale(k / st["k"], about_point=m.get_center())
            st["k"] = k
        if stroke_only:
            m.set_stroke(opacity=a)
        else:
            m.set_opacity(a)

    if stroke_only:
        mob.set_stroke(opacity=0.0)
    else:
        mob.set_opacity(0.0)
    mob.add_updater(_upd)
    return mob


def _opacity_gate(mob, u_of, start: float, end: float, *, base: float = 1.0,
                  stroke_only: bool = False):
    """区间显形：tracker 走到 [start,end] 时透明度 0→base（线/箭头/图注共用）。"""
    st: dict = {"a": -1.0}

    def _upd(m):
        a = _clamp01((_clamp01(u_of()) - start) / max(end - start, 1e-9))
        if abs(a - st["a"]) < 1e-9:
            return
        st["a"] = a
        if stroke_only:
            m.set_stroke(opacity=base * a)
        else:
            m.set_opacity(base * a)

    if stroke_only:
        mob.set_stroke(opacity=0.0)
    else:
        mob.set_opacity(0.0)
    mob.add_updater(_upd)
    return mob


def _partial_polyline(pts, frac: float):
    """折线按累计弧长取前 frac 段（frac=1 返回全点）——「描线」不复制对象。"""
    pts = np.asarray(pts, dtype=float)
    frac = _clamp01(frac)
    if frac >= 1.0 or len(pts) < 2:
        return pts
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = float(seg.sum())
    if total <= 1e-12:
        return pts[:1]
    target = frac * total
    out = [pts[0]]
    acc = 0.0
    for k, seg_len in enumerate(seg):
        if acc + seg_len >= target:
            t = (target - acc) / seg_len if seg_len > 1e-12 else 0.0
            out.append(pts[k] + (pts[k + 1] - pts[k]) * t)
            return np.array(out)
        out.append(pts[k + 1])
        acc += seg_len
    return pts


def _draw_on(mob, u_of, start: float, end: float, model_pts, ref_of, color, stroke_width: float = 2.5):
    """按 tracker 进度把折线「描出来」：前缀点列每帧在参考图元当前坐标系里重算。

    ``model_pts`` 是布局模型坐标；``ref_of()`` 返回 (cx, cy, scale)，由静态参考件（磁铁本体）
    现场给出——_fit 缩放/位移后描线仍贴着参考件，且没有 ShowPassingFlash(m.copy()) 的装配期快照。
    """
    st: dict = {"f": -1.0}

    def _upd(m):
        f = _clamp01((_clamp01(u_of()) - start) / max(end - start, 1e-9))
        if abs(f - st["f"]) < 1e-9:
            return
        st["f"] = f
        if f <= 1e-9:
            m.set_stroke(opacity=0.0)
            return
        cx, cy, s = ref_of()
        pp = _partial_polyline(model_pts, f)
        fresh = VMobject()
        fresh.set_points_as_corners([[cx + s * float(x), cy + s * float(y), 0.0] for x, y in pp])
        fresh.set_stroke(color, stroke_width, opacity=1.0)
        m.become(fresh)

    mob.set_stroke(opacity=0.0)
    mob.add_updater(_upd)
    return mob


def _rebuild_on_change(mob, key_of, build):
    """key 变了才重建（become）：tracker 停住后不再每帧重写，退场/强调动画可正常接管。"""
    st: dict = {"key": None}

    def _upd(m):
        k = key_of()
        if st["key"] is not None and k == st["key"]:
            return
        st["key"] = k
        m.become(build())

    mob.add_updater(_upd)
    return mob


# ---- 82-SD2a2 电场/螺线管过程动画小工具 ----
# 与 SD2a1 同一纪律：beats 在 builder 构造期生成，几何全部来自 field.py 的布局模型；
# 这里只给「成波/逐条描出/逐匝 Create」提供统一的归一化时间窗口，不另起动画框架。


def _seq_slot(i: int, n: int, *, span: float = 0.92) -> tuple:
    """第 i/n 个元素的归一化 [起,止] 窗口：按顺序铺开，末元素在 span 处收齐。"""
    n = max(int(n), 1)
    a = float(span) * (i / n)
    b = float(span) * ((i + 1) / n)
    return a, min(max(b, a + 1e-6), 1.0)


def _lag_slot(i: int, n: int, lag: float, *, cover: float = 0.82) -> tuple:
    """LaggedStart(lag_ratio=lag) 里第 i 个元素的 [起,止] 窗口。

    gate 透明度与并行的 Create 按同一把尺对齐：d=1/(1+lag(n−1)) 是单个子动画占总时长的
    比例，第 i 个在 i·lag·d 起跑——否则「线已画完、门还没开」会看到一截空白。
    """
    n = max(int(n), 1)
    den = 1.0 + float(lag) * (n - 1)
    d = 1.0 / den
    a = i * float(lag) * d
    return a, min(1.0, a + d * float(cover))


def _head_on_path(model_pts, u_of, start: float, end: float, ref_of, color,
                  radius: float = 0.075):
    """沿模型折线移动的高对比亮斑（描线笔头 / 方向高亮带）；f 落定即隐身。"""
    head = Dot([0.0, 0.0, 0.0], radius=radius, color=color)

    def _upd(m):
        f = _clamp01((_clamp01(u_of()) - start) / max(end - start, 1e-9))
        if f <= 1e-9 or f >= 1.0 - 1e-9:
            m.set_opacity(0.0)
            return
        pp = _partial_polyline(model_pts, f)
        x, y = pp[-1]
        cx, cy, s = ref_of()
        m.move_to([cx + s * float(x), cy + s * float(y), 0.0])
        m.set_opacity(0.95)

    head.set_opacity(0.0)
    head.add_updater(_upd)
    return head


def _draw_with_head(mob, u_of, start: float, end: float, model_pts, ref_of, color,
                    stroke_width: float = 2.5, *, head_color=None, head_radius: float = 0.075):
    """「描线 + 笔头」：线按前缀点列生长，一个高对比圆点跟着生长端点走。

    帧差验收要的是**逐帧可见的位移**：细线描出本身每帧只改十几个像素，15fps 下会被
    当成静止帧（82-SD2a2 首版实测）；笔头把「正在画到哪里」变成几十像素的移动亮斑，
    既压住静止帧占比，也让观众看得见描线的前沿。f 落定后笔头立即隐身，不留残影。
    """
    _draw_on(mob, u_of, start, end, model_pts, ref_of, color, stroke_width)
    return _head_on_path(model_pts, u_of, start, end, ref_of,
                         head_color or color, head_radius)


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


# ---- 82-SD2b 连续过程动画小工具 ----
# 与 SD2a1/SD2a2 同一纪律：beats 构造期生成，几何每帧从**已变换的静态参考件**现算
# （_fit 缩放/位移后仍贴合），tracker 停住即不再写状态——退场/强调动画不被 updater 抢回。


def _swing_to(mob, u_of, angle_of):
    """把线段绕**当前**起点连续转到 ``angle_of(u)``（绝对角，+x 轴逆时针，弧度）。

    服务的理解：开关闸臂落下 / 表针从 0 偏到读数——转角是过程量，不是两帧定格。
    构造期几何保持终点角（测试锁死终点坐标）；首帧只记一次实角，此后按增量转，
    不在装配期缓存坐标，所以 _fit 缩放/位移后转轴仍在闸刀起点（82-SD2a1 同则）。
    """
    st = {"a": None}

    def _upd(m):
        v = m.get_end() - m.get_start()
        if st["a"] is None:
            st["a"] = math.atan2(float(v[1]), float(v[0]))
        tgt = float(angle_of(_clamp01(u_of())))
        d = tgt - st["a"]
        if abs(d) > 1e-7:
            m.rotate(d, about_point=m.get_start())
            st["a"] = tgt

    mob.add_updater(_upd)
    return mob


def _grow_partial(mob, u_of, start: float = 0.0, end: float = 1.0):
    """按 tracker 把**已有路径**逐段露出（前缀裁剪，Create 语义但可分段续画）。

    首帧才拷一份全点快照（此时 _fit 已定稿）：若在构造期拷，缩放前的点列会把线画歪；
    拷贝后只改点不改样式，退场 FadeOut 照常接管透明度。
    """
    st = {"f": None, "full": None}

    def _upd(m):
        if st["full"] is None:
            st["full"] = m.copy()
        f = _clamp01((_clamp01(u_of()) - start) / max(end - start, 1e-9))
        if st["f"] is not None and abs(f - st["f"]) < 1e-9:
            return
        st["f"] = f
        m.pointwise_become_partial(st["full"], 0.0, f)

    mob.add_updater(_upd)
    return mob


def _dashed_grow(mob, u_of, model_pts, ref_of, color, stroke_width: float = 2.0,
                 num_dashes: int = 30):
    """虚线轨迹随运动体生长：按前缀点列重建 Dash 数随进度增（虚线长度不随生长变密）。"""
    st = {"f": -1.0}

    def _upd(m):
        f = _clamp01(u_of())
        if abs(f - st["f"]) < 1e-9:
            return
        st["f"] = f
        if f <= 1e-6:
            m.set_stroke(opacity=0.0)
            return
        cx, cy, s = ref_of()
        pp = _partial_polyline(model_pts, f)
        base = VMobject()
        base.set_points_as_corners([[cx + s * float(x), cy + s * float(y), 0.0] for x, y in pp])
        # 固定 dash 数：Dash 是子对象，数目变化会让 become 留下旧子对象残影（82-SD2b 实测口径）。
        fresh = DashedVMobject(base, num_dashes=max(2, int(num_dashes)))
        m.become(fresh)
        m.set_stroke(color, stroke_width, opacity=0.92)

    mob.set_stroke(opacity=0.0)
    mob.add_updater(_upd)
    return mob


def _follow_uv(mob, u_of, pt_of):
    """让图元跟着 ``pt_of(u)`` 走（小球/滑块/游标共用；只定位，不改角度与样式）。"""
    st = {"p": None}

    def _upd(m):
        p = pt_of(_clamp01(u_of()))
        q = np.array([float(p[0]), float(p[1]), 0.0])
        if st["p"] is None or float(np.abs(q - st["p"]).sum()) > 1e-9:
            st["p"] = q
            m.move_to(q)

    mob.add_updater(_upd)
    return mob


def _box(mob):
    a, b = mob.get_corner(LEFT + DOWN), mob.get_corner(RIGHT + UP)
    return (a[0], a[1], b[0], b[1])


def _overlap(a, b) -> bool:
    """两个包围盒是否重叠。81-S4 加固：盒有两种形态——
      · 4 元组 (x0,y0,x1,y1)：轴对齐 AABB，判据与旧写法逐字相同（全部既有调用零影响）；
      · 8 元组 (x0,y0,x1,y1 + 4 个角点)：_obb 产出的**旋转后**包围盒（有向矩形）。
    只要有一方是旋转盒就改用分离轴定理（SAT）：磁针、斜闸刀、贴面转过的方块这类旋转图元的
    AABB 会被"撑满"成远超本体的方块，用 AABB 判标签碰撞会把没压住的误报成压住；SAT 用
    旋转后的真实外接矩形判定，既不漏判也不误判。"""
    if len(a) == 4 and len(b) == 4:
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
    return _sat(_corners_of(a), _corners_of(b))


def _corners_of(box) -> list:
    """盒（AABB 或 _obb 的 8 元组）→ 逆时针 4 角点。"""
    if len(box) == 4:
        x0, y0, x1, y1 = box
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(box[4], box[5]), (box[6], box[7]), (box[8], box[9]), (box[10], box[11])]


def _sat(ca, cb) -> bool:
    """两个凸四边形是否重叠：沿两组边法线投影，任一轴上区间分离即不相交。"""
    for poly in (ca, cb):
        for i in range(4):
            nx = poly[i][1] - poly[(i + 1) % 4][1]
            ny = poly[(i + 1) % 4][0] - poly[i][0]
            nn = nx * nx + ny * ny
            if nn < 1e-12:
                continue
            pa = [p[0] * nx + p[1] * ny for p in ca]
            pb = [p[0] * nx + p[1] * ny for p in cb]
            if max(pa) <= min(pb) or max(pb) <= min(pa):
                return False
    return True


def _convex_hull(pts):
    """Andrew 单调链凸包（输入少、够用即可），返回逆时针顶点。"""
    p = sorted({(float(q[0]), float(q[1])) for q in pts})
    if len(p) <= 2:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]


def _obb(mob):
    """旋转图元的**旋转后**最小面积包围盒：8 元组 (x0,y0,x1,y1, 4×2 角点)。
    前 4 位仍是 AABB（_pad_box 等旧代码照常可用），后 8 位是 _overlap/SAT 用的有向角点。
    方向取凸包各边的最小面积矩形（旋转卡钳的单步近似）；点数先降采样，几百点内不成为瓶颈。"""
    b = _box(mob)
    try:
        pts = np.array([[q[0], q[1]] for q in mob.points], dtype=float)
    except Exception:
        return (*b, b[0], b[1], b[2], b[1], b[2], b[3], b[0], b[3])
    if len(pts) == 0:
        return (*b, b[0], b[1], b[2], b[1], b[2], b[3], b[0], b[3])
    if len(pts) > 240:
        pts = pts[:: max(1, len(pts) // 240)]
    hull = _convex_hull(pts)
    if len(hull) < 2:
        return (*b, b[0], b[1], b[2], b[1], b[2], b[3], b[0], b[3])
    best = None
    for i in range(len(hull)):
        ex, ey = hull[(i + 1) % len(hull)][0] - hull[i][0], hull[(i + 1) % len(hull)][1] - hull[i][1]
        ln = math.hypot(ex, ey)
        if ln < 1e-9:
            continue
        ux, uy = ex / ln, ey / ln
        vx, vy = -uy, ux
        pu = pts[:, 0] * ux + pts[:, 1] * uy
        pv = pts[:, 0] * vx + pts[:, 1] * vy
        area = (pu.max() - pu.min()) * (pv.max() - pv.min())
        if best is None or area < best[0]:
            best = (area, pu.min(), pu.max(), pv.min(), pv.max(), ux, uy, vx, vy)
    if best is None:
        return (*b, b[0], b[1], b[2], b[1], b[2], b[3], b[0], b[3])
    _a, u0, u1, v0, v1, ux, uy, vx, vy = best
    cs = [(u0 * ux + v0 * vx, u0 * uy + v0 * vy), (u1 * ux + v0 * vx, u1 * uy + v0 * vy),
          (u1 * ux + v1 * vx, u1 * uy + v1 * vy), (u0 * ux + v1 * vx, u0 * uy + v1 * vy)]
    xs = [c[0] for c in cs]
    ys = [c[1] for c in cs]
    return (min(xs), min(ys), max(xs), max(ys), *(x for c in cs for x in c))


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


def _place_label(lab, line, plane, taken, avoid=(), obstacles=()):
    """标签贴着它所指的那条线放，且不压住任何一条图线。

    旧写法 next_to(line, UP) 按外接框定位，斜线的外接框很高，标签被顶到画面上方两个单位，
    学生不知道它在标谁（一次函数「y = 2x − 1」实测）。改成在线上取锚点、沿局部法线让开半个字高：
    线再陡标签也落在它旁边，不会穿过它（加速度 v-t 三种情形，「下斜 → a 与 v 反向」被斜线划过去实测）。

    81-S4 加固（签名向后兼容，新参都有缺省）：
      · obstacles —— 旋转图元的 _obb 有向盒序列，用 SAT 参与判压（磁针/斜杆的 AABB 会误报）；
      · 避让失败路径逐档兜底：常规候选 → 加密锚点重扫 → 字号微缩（缩到注释文字 22 号下限为止）；
        全部耗尽仍不干净才落最低分位置，残差如实登记非零，并另记入 UNRESOLVED（必挂冲突清单）。
    落位成功的标签打 _placed 标记：装配期的全量复核（_resolve_text_clashes）不再二次挪动它。
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
        x0, y0, x1, y1 = _box(lab)[:4]
        on_line = sum(1 for poly in avoid for q in poly
                      if x0 - CLASH_MARGIN <= q[0] <= x1 + CLASH_MARGIN
                      and y0 - CLASH_MARGIN <= q[1] <= y1 + CLASH_MARGIN)
        clash = sum(1 for t in taken if _overlap(_box(lab), t))
        clash += sum(1 for ob in obstacles if _overlap(_box(lab), ob))
        return on_line * 2 + clash * 3

    def sweep(props):
        nonlocal best
        for prop in props:
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
                    return True
            if best[0] == 0:
                return True
        return best is not None and best[0] == 0

    best = None
    sweep((0.80, 0.62, 0.45, 0.90))
    if best is not None and best[0] > 0:
        # 兜底一：换锚点——常规四档之外再铺六档（两端与各段中点），还是"沿线滑"优先。
        sweep((0.30, 0.15, 0.52, 0.71, 1.0, 0.0))
    if best is not None and best[0] > 0:
        # 兜底二：字号微缩——只允许缩到 22 号下限（G3 可读性红线：注释文字 ≥22），缩了也不许低于它。
        fam = [m for m in lab.get_family() if hasattr(m, "text") and m.font_size > 0]
        min_fs = min((m.font_size for m in fam), default=0)
        if min_fs >= 24:
            k = max(0.8, 22.0 / min_fs)
            w0, h0 = lab.width, lab.height
            lab.scale(k)
            sweep((0.80, 0.62, 0.45, 0.90, 0.30, 0.15))
            if best is not None and best[0] > 0:      # 缩了仍不干净：不缩了也不救回来就别留小字，还原
                lab.scale(1.0 / k)
                place(best[1]) if best[1] is not None else None
                best = (min(best[0], score()), np.array(lab.get_center()))
    if best is None:
        best = (0, np.array(line.get_center()) + 0.26 * UP)
    place(best[1])
    taken.append(_box(lab))
    if best[0] > 0:
        text = "".join(m.text for m in lab.get_family() if hasattr(m, "text"))
        UNRESOLVED.append((best[0], text))       # 必挂冲突登记：机器自认救不回来，成片里它注定叠字
    # 落点残差登记：0 = 既不压任何图线也不撞别的标签。tests/test_layout.py 拿它做全库回归，
    # 因为"标签压线"这类缺陷只有渲染出来才看得见，而评审看到的是成片、闸门拦不住——只能反向钉死。
    # 81-S4 收紧后的语义：非零 = 常规候选 + 换锚点 + 字号微缩全部耗尽仍不干净（并同步进 UNRESOLVED）。
    PLACEMENTS.append((best[0], "".join(m.text for m in lab.get_family() if hasattr(m, "text"))))
    lab._placed = True
    return lab


# ---- 81-S4 全链字重叠复核机器（新增辅助，不触碰任何锁定图元逻辑）----
# 锁定函数（_v_circuit / _v_derivation / _v_force_diagram / _v_incline / _v_optics …）一个字不能改，
# 它们的裸放置标签却正是"字重叠"的案发现场。解法：在装配层的每个版式块**建完之后、排版之前**
# 做一次与图元无关的通用复核——不改画法，只挪字：压线/撞字的标签在原位附近做小步平移（必要时
# 字号微缩到 22 号下限），并把最终残差按 _place_label 同一口径登记进 PLACEMENTS。
TEXT_MIN_FS = 22.0            # G3 可读性红线：允许的最小注释字号（微缩兜底不许跌破它）
CLASH_MARGIN = 0.05           # 采样点落入标签盒的容差（≈3px@854 宽），与 _place_label 同口径：
                              # 笔画中心线离字太近也算压字。P3 实拍抽验（斜面方块 label_in）证明
                              # 0.02 时"挪干净"的字仍会被 3px 外的方块描边啃到边 → 收紧到 0.05。


def _mob_leaf_pts(x) -> bool:
    try:
        return x.points is not None and len(x.points) > 0
    except Exception:
        return False


def _mob_mean(x, name, default: float) -> float:
    v = getattr(x, name, None)
    if v is None:
        return default
    try:
        return float(np.mean(v))
    except (TypeError, ValueError):
        return default


def _is_text_mob(x) -> bool:
    return hasattr(x, "text") and not isinstance(x, VGroup)


def _has_pts_deep(x) -> bool:
    if _mob_leaf_pts(x):
        return True
    try:
        return any(_mob_leaf_pts(y) for y in x.get_family())
    except Exception:
        return False


def _is_pure_text_group(x) -> bool:
    """整棵子树只有字（rich/图例行这类"一条标签的包装组"）：挪就整条一起挪，下标不许撕下来。"""
    if not isinstance(x, VGroup):
        return False
    fam = x.get_family()
    return (any(_is_text_mob(y) and _has_pts_deep(y) for y in fam)
            and all(_is_text_mob(y) or isinstance(y, VGroup) for y in fam))


def _visible_text(x) -> bool:
    """可见性/豁免判定：0 号透明度（推导里等待"飞入点亮"的目标字母）与刻度数字（由 _clear_ticks
    专管）不参与复核，否则会把设计性的"字在图形上/贴轴排布"误判成叠字。"""
    if _mob_mean(x, "fill_opacity", 1.0) < 0.05 and _mob_mean(x, "stroke_opacity", 1.0) < 0.05:
        return False
    return not hasattr(x, "_tick_dir") and not hasattr(x, "_tick_anchor")


def _family_parent_map(block):
    parent = {}
    for x in block.get_family():
        for c in getattr(x, "submobjects", ()):
            parent[id(c)] = x
    return parent


def _text_units(block):
    """标签单元 = 复核时被整体挪动的那一组字：
    · 有 .text 祖先的分段（MathTex 内部）并进祖先——整条公式一起挪；
    · 同一纯文字父组、盒间距 ≤0.25 的兄弟段（rich 的一条标签、推导的一行公式）并进父组——
      下标不能从基字上撕下来；
    · 同父但彼此隔开的（磁针 N/S 两极字）保持独立——它们是两条标签，各挪各的。"""
    fam = block.get_family()
    parent = _family_parent_map(block)

    def outermost(x):
        a = parent.get(id(x))
        while a is not None and a is not block:
            if _is_text_mob(a):
                return False
            a = parent.get(id(a))
        return True

    def under_placed(x):
        """_place_label 落过位的标签不再复核（机器不同、判据已更严），只认别家的裸字。"""
        a = parent.get(id(x))
        while a is not None and a is not block:
            if getattr(a, "_placed", False):
                return True
            a = parent.get(id(a))
        return bool(getattr(x, "_placed", False))

    def under_locked(x):
        """82-SB：锚点锁死的结构式文本不参与挪字复核。mechanism 的原子/基团符号与箭标签
        由锚点表钉死（_v_mechanism 打 _locked_anchor），挪字=错位根源（82D3：A/B 实测原子被
        搬走 20~122px 而键线/弯箭头原地不动）；空间冲突改由结构式布局阶段整体避让（_ma.spread_atoms）。"""
        a = parent.get(id(x))
        while a is not None and a is not block:
            if getattr(a, "_locked_anchor", False):
                return True
            a = parent.get(id(a))
        return bool(getattr(x, "_locked_anchor", False))

    cands = [x for x in fam if _is_text_mob(x) and outermost(x) and _has_pts_deep(x)
             and _visible_text(x) and not under_placed(x) and not under_locked(x)]
    byparent: dict = {}
    for x in cands:
        byparent.setdefault(id(parent.get(id(x))), []).append(x)
    units, taken_ids = [], set()
    for pid, group in byparent.items():
        p = parent.get(pid)
        merged = (p is not None and p is not block and len(group) > 1
                  and all(_is_text_mob(c) or (_is_pure_text_group(c) if isinstance(c, VGroup) else False)
                          for c in p.submobjects))
        if merged:      # 只有"挨在一起的段"才算同一条标签（N/S 那种隔开的仍各自独立）
            boxes = sorted(_box(c) for c in group)
            for a, b in zip(boxes, boxes[1:]):
                gap_h = max(a[0], b[0]) - min(a[2], b[2])      # 水平投影重叠时给负值=相邻
                gap_v = max(a[1], b[1]) - min(a[3], b[3])
                sep = gap_h if gap_h > 0 else gap_v
                if sep > 0.25:
                    merged = False
                    break
        if merged and id(p) not in taken_ids:
            taken_ids.add(id(p))
            units.append(p)
        else:
            units.extend(group)
    return units


def _label_obstacles(block, textids):
    """块内可被字压到的图元：描边足够粗（≥2.4，与图线/导线/箭头同量级；网格线 1、细辅助线
    1.5~2 是背景不是碰撞对象）、描边可见；或实心（fill>0.5）的图形。文字自己的 SVG 轮廓子件
    （笔画）不算图元——字与字的关系由 AABB 撞字判定统一管，否则一个字的笔画会把它自己
    旁边的字全判成"压图元"。"""
    fam = block.get_family()
    parent = _family_parent_map(block)
    obs = []
    for x in fam:
        if isinstance(x, VGroup) or id(x) in textids or not _mob_leaf_pts(x):
            continue
        a = parent.get(id(x))
        under_text = False
        while a is not None and a is not block:
            if _is_text_mob(a) or id(a) in textids:
                under_text = True
                break
            a = parent.get(id(a))
        if under_text:
            continue
        sw = _mob_mean(x, "stroke_width", 0.0)
        so = _mob_mean(x, "stroke_opacity", 1.0)
        fo = _mob_mean(x, "fill_opacity", 0.0)
        stroked = sw >= 2.4 and so >= 0.6
        solid = fo > 0.5
        if not (stroked or solid):
            continue
        try:
            pts = x.points
            closed = len(pts) > 2 and float(np.linalg.norm(pts[0, :2] - pts[-1, :2])) < 1e-3
        except Exception:
            closed = False
        obs.append({
            "box": _box(x), "obb": _obb(x) if solid else None,
            "samples": _sample(x, 32) if stroked else [],
            "segs": _stroke_segs(x, 32) if stroked else [],
            "closed": closed, "solid": solid, "stroked": stroked,
        })
    return obs


def _orient(px, py, qx, qy, rx, ry):
    return (qx - px) * (ry - py) - (qy - py) * (rx - px)


def _crossover(ax, ay, bx, by, cx, cy, dx, dy):
    """线段 AB 与线段 CD 是否跨立相交（含共线重叠）。"""
    o1, o2 = _orient(ax, ay, bx, by, cx, cy), _orient(ax, ay, bx, by, dx, dy)
    o3, o4 = _orient(cx, cy, dx, dy, ax, ay), _orient(cx, cy, dx, dy, bx, by)
    if o1 == o2 == o3 == o4 == 0:
        return not (max(ax, bx) < min(cx, dx) or max(cx, dx) < min(ax, bx)
                    or max(ay, by) < min(cy, dy) or max(cy, dy) < min(ay, by))
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _stroke_segs(mob, n=32):
    """把描边图元沿弧长切成小段，返回 (minx, miny, maxx, maxy, x0, y0, x1, y1) 列表。
    为什么不能只看采样点：一条长直边采 20 个点，点间隔十几 px，贴着字走过的边可能一个采样点
    都不在字盒里（P3 实拍抓到：斜面方块边框中心线离 label_in 只有 0.04u，采样点全落在别处，
    残差报 0 而字仍被啃边）。线段与"外扩后的字盒"相交才算压字，才与像素口径一致。"""
    pts = _sample(mob, n)
    segs = []
    for p, q in zip(pts, pts[1:]):
        try:
            x0, y0 = float(p[0]), float(p[1])
            x1, y1 = float(q[0]), float(q[1])
        except Exception:
            continue
        segs.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), x0, y0, x1, y1))
    return segs


def _segs_hit_box(segs, x0, y0, x1, y1):
    """线段集合与矩形盒（已外扩过）相交数：先比外接框粗筛，再判端点在盒内 / 与四条边跨立。"""
    hit = 0
    for s in segs:
        if s[2] < x0 or s[0] > x1 or s[3] < y0 or s[1] > y1:
            continue
        ax, ay, bx, by = s[4], s[5], s[6], s[7]
        if (x0 <= ax <= x1 and y0 <= ay <= y1) or (x0 <= bx <= x1 and y0 <= by <= y1):
            hit += 1
            continue
        if (_crossover(ax, ay, bx, by, x0, y0, x1, y0) or _crossover(ax, ay, bx, by, x1, y0, x1, y1)
                or _crossover(ax, ay, bx, by, x1, y1, x0, y1) or _crossover(ax, ay, bx, by, x0, y1, x0, y0)):
            hit += 1
    return hit


def _clash_score(tbox, samples, segs, obbs, other_boxes):
    """(压线数, 撞字数)：samples/segs 是描边图元的采样点与线段，obbs 是实心图元的有向盒
    （_overlap 走 SAT，旋转针/斜杆不误报），other_boxes 是其余文本的 AABB。"""
    x0, y0, x1, y1 = tbox[:4]
    mx0, my0, mx1, my1 = x0 - CLASH_MARGIN, y0 - CLASH_MARGIN, x1 + CLASH_MARGIN, y1 + CLASH_MARGIN
    on_line = sum(1 for q in samples if mx0 <= q[0] <= mx1 and my0 <= q[1] <= my1)
    on_line += _segs_hit_box(segs, mx0, my0, mx1, my1)
    clash = 0
    for ob in obbs:
        if _overlap(tbox, ob):
            on_line += 1
    for o in other_boxes:
        if _overlap(tbox, o):
            clash += 1
    return on_line, clash


def _resolve_label_clashes(block):
    """对块内每个标签单元复核落点：先原位打分，脏了才挪——8 方位×递增半径的小平移优先
    （挪字不改图），全向挪不干净再试字号微缩（≥22 号下限，缩不干净就还原字号、落最低分位置）。
    返回 [(残差分, 文本)]，残差 = 压线数 + 2×撞字数；仍脏的同步进 UNRESOLVED。"""
    texts = _text_units(block)
    if not texts:
        return []
    textids = {id(x) for u in texts for x in u.get_family()}
    obs_all = _label_obstacles(block, textids)
    tboxes = {id(x): _box(x) for x in texts}
    records = []
    for t in texts:
        pbox = _box(t)
        # 本标签专属障碍集：只有**实心**图形（fill>0.5 的磁极条、电荷点）把标签整个包住时才豁免
        # ——那是"字写在色块上"的设计。描边轮廓不豁免：转过的斜面方块 bbox 比实体大一圈，
        # 边框线斜着切过贴边的 label_in 实拍就是"字被线划"（P3 抽验 f3 帧抓到过）。
        obs, obbs, segs = [], [], []
        for o in obs_all:
            bx, tb = o["box"], pbox
            enclosed = (o["solid"] and o["closed"]
                        and bx[0] <= tb[0] - 0.02 and bx[1] <= tb[1] - 0.02
                        and bx[2] >= tb[2] + 0.02 and bx[3] >= tb[3] + 0.02)
            if enclosed:
                continue
            obs.extend(o["samples"])
            segs.extend(o["segs"])
            if o["solid"] and o["obb"] is not None:
                obbs.append(o["obb"])

        def score():
            nb = _box(t)
            on_line, clash = _clash_score(nb, obs, segs, obbs, [b for k, b in tboxes.items() if k != id(t)])
            return on_line + 2 * clash

        s0 = score()
        rec_text = "".join(m.text for m in t.get_family() if hasattr(m, "text"))
        if s0 == 0:
            records.append((0, rec_text))
            continue
        c0 = np.array(t.get_center())
        dirs = [np.array(v, dtype=float) for v in
                ((0, 1, 0), (0.707, 0.707, 0), (1, 0, 0), (0.707, -0.707, 0),
                 (0, -1, 0), (-0.707, -0.707, 0), (-1, 0, 0), (-0.707, 0.707, 0))]
        best = (s0, c0, 0.0)
        moved = False
        for dist in (0.08, 0.18, 0.3, 0.44, 0.6, 0.8, 1.0, 1.2):
            for u in dirs:
                t.move_to(c0 + u * dist)
                v = score()
                if v < best[0]:
                    best = (v, np.array(t.get_center()), dist)
                if v == 0:
                    moved = True
                    break
            if moved:
                break
        if not moved and best[0] > 0:
            fam = [m for m in t.get_family() if hasattr(m, "text") and m.font_size > 0]
            min_fs = min((m.font_size for m in fam), default=0)
            if min_fs >= TEXT_MIN_FS + 2:
                k = max(0.8, TEXT_MIN_FS / min_fs)
                t.scale(k)
                for dist in (0.08, 0.18):
                    for u in dirs:
                        t.move_to(c0 + u * dist)
                        v = score()
                        if v < best[0]:
                            best = (v, np.array(t.get_center()), dist)
                        if v == 0:
                            moved = True
                            break
                    if moved:
                        break
                if not moved:
                    t.scale(1.0 / k)                 # 缩了仍不干净：还原字号，落最低分位置（残差照记非零）
                    t.move_to(best[1])
                    best = (min(best[0], score()), np.array(t.get_center()), best[2])
        t.move_to(best[1])
        tboxes[id(t)] = _box(t)
        if best[2] > 0:
            CLASH_MOVED.append((rec_text, best[2]))   # 复核真的挪了字（反空转证据）
        if best[0] > 0:
            UNRESOLVED.append((best[0], rec_text))
        records.append((best[0], rec_text))
    return records


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


def fit_cues(cues, seconds: float) -> list:
    """字幕时间轴超出镜头时长时按比例压回镜头窗口。

    数据里出现「4s 镜配 9.3s 字幕」时，前面几条 cue 的 hold 会吃满整镜，末几条的揭示
    在最后一帧之后才 add——电路图的 R/V 就是这样整镜不出现的。压回后相对顺序不变，
    每块内容都能在本镜内出现；正常数据原样返回（只复制被压缩的项，不改 plan 原对象）。
    """
    if not cues:
        return cues
    last = max(float(c.get("end", 0) or 0) for c in cues)
    if last <= seconds or last <= 0:
        return cues
    k = seconds / last
    return [{**c, "start": float(c.get("start", 0) or 0) * k,
             "end": float(c.get("end", 0) or 0) * k} for c in cues]


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


# ---- 物理图示方向字典（受力分析 / 光路共用）----
# 方向词 → 单位向量；角度度数（0=右、逆时针为正）由 _dir_vec 现算。
_FORCE_DIRS = {
    "up": UP, "down": DOWN, "left": LEFT, "right": RIGHT,
    "upleft": UP + LEFT, "upright": UP + RIGHT,
    "downleft": DOWN + LEFT, "downright": DOWN + RIGHT,
}


def _dir_vec(d) -> np.ndarray:
    """force_diagram 的 dir：方向词 → 单位向量；角度度数 → (cos, sin, 0)。"""
    if isinstance(d, (int, float)) and not isinstance(d, bool):
        a = math.radians(float(d))
        return np.array([math.cos(a), math.sin(a), 0.0])
    return np.array(_FORCE_DIRS.get(str(d).strip().lower(), DOWN))


FORCE_MIN_LEN = 0.45   # 按量值缩放时最短箭长（再短就看不见箭杆）


def _force_lengths(forces, L: float, floor: float = FORCE_MIN_LEN) -> list:
    """力箭长：同图内长度 ∝ mag（规范§5「同一图中力越大线段越长」）。

    最大 mag 的力画成 L（沿用原固定长度），其余按比例缩短，最短 floor。
    没有任何力给出有效 mag（正数）时全部为 L，与旧行为一致；混给时缺 mag 的力按 L 画。
    """
    mags = [_mag_of(f) for f in forces]
    top = max((m for m in mags if m is not None), default=None)
    if top is None:
        return [L] * len(forces)
    return [L if m is None else max(floor, L * m / top) for m in mags]


FORCE_STICK_OUT = 0.3   # 按量值缩短时，箭头至少露出物体边框这么长（否则短力整支藏在方块里）


def _body_force_lengths(forces, dirs, L, half_w, half_h, rot=0.0, edge_ok=None) -> list:
    """从有体积的物体（方块）中心出发的力：给了 mag 时，**露出边框的那段** ∝ mag。

    只按总长缩放会让短力（如 0.45）整支藏在半宽 0.75 的方块里看不见；学生读的是露在外面的
    箭杆，所以让露出段 ∝ mag：最大者露出 L−half_h（竖直方向总长恰为 L，与旧固定长度一致），
    最短露出 FORCE_STICK_OUT。edge_ok[i]=False 的力（起点不在中心，如斜面压力从接触点出发）
    不加边距。全图无有效 mag 时返回 [L]*n，即旧行为。
    """
    if not any(_mag_of(f) for f in forces):
        return [L] * len(forces)
    vis = _force_lengths(forces, L - half_h, FORCE_STICK_OUT)
    out = []
    for i, (f, d, v) in enumerate(zip(forces, dirs, vis)):
        if _mag_of(f) is None:
            out.append(L)
            continue
        inside = True if edge_ok is None else edge_ok[i]
        out.append((_box_edge(d, half_w, half_h, rot) if inside else 0.0) + v)
    return out


def _mag_of(f):
    try:
        v = float(f.get("mag"))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def _box_edge(d, half_w: float, half_h: float, rot: float = 0.0) -> float:
    """从矩形中心沿单位方向 d 走到边框的距离（矩形逆时针转 rot 弧度）。"""
    c, s = math.cos(-rot), math.sin(-rot)
    lx, ly = abs(c * d[0] - s * d[1]), abs(s * d[0] + c * d[1])
    return min(half_w / lx if lx > 1e-9 else math.inf, half_h / ly if ly > 1e-9 else math.inf)


# ---------------- 81-S2 物理图示补齐：接触面刻线 / 平行四边形定则 / 正交分解 / 斜面下滑仿真 ----------------
# 原 #79 C4 范围。画法依据 Ref_Physics_Diagram_Standards.txt：
#   §3 面本体用一小段一段斜线表示（镜面口径，支持面同族）；§6 N 垂直接触面、f 沿接触面；
#   §7 平行四边形定则：对角线=合力，平移/辅助边画虚线以区分真实力。
# 以下全部是**新增**辅助（_force_lengths/_body_force_lengths/_box_edge 等锁定机器只调用、不修改）。

def _surface_hatch(p0, p1, into, n: int = 6, length: float = 0.22) -> list:
    """接触面本体的阴影斜刻线：沿 p0→p1 均布 n 条短线，各自朝**材料侧**斜后画。

    into 是材料侧单位法向（刻线必须落进面背后，不许伸向物体一侧）。
    返回线段端点列表 [((x,y,0),(x,y,0)),...]，纯几何、可单测；颜色/粗细由 builder 决定。
    """
    a = np.array([p0[0], p0[1], 0.0], dtype=float)
    b = np.array([p1[0], p1[1], 0.0], dtype=float)
    t = b - a
    seg = float(np.hypot(t[0], t[1]))
    if seg < 1e-9:
        return []
    u = t / seg
    m = np.array([into[0], into[1], 0.0], dtype=float)
    m = m / (np.linalg.norm(m) or 1.0)
    h = (m - u) / math.sqrt(2.0) * length            # 与面成 45°、朝材料侧（教材斜线观感）
    out = []
    for i in range(n):
        q = a + u * seg * (0.06 + 0.88 * (i + 0.5) / n)
        out.append((tuple(q), tuple(q + h)))
    return out


def surface_layout(kind: str, half_w: float = 0.75, half_h: float = 0.5,
                   span: float = 1.25) -> dict | None:
    """支承面几何（force_diagram props=surface）：面线段端点、材料方向（刻线侧）、接触点。

    对象 = 居中原点、半宽 half_w、半高 half_h 的方块；面与物块棱边**重合共触**
    （接触面表示的第一要义：面是物体碰着的那块，不是装饰）。
    kind: ground 下方支持面 | wall_left 左侧竖墙 | wall_right 右侧竖墙；未知 kind 返回 None（脏数据兜底）。
    """
    if kind == "ground":
        return {"p0": (-span, -half_h), "p1": (span, -half_h), "into": (0.0, -1.0),
                "contact": (0.0, -half_h)}
    if kind == "wall_left":
        return {"p0": (-half_w, -0.8 * span), "p1": (-half_w, 0.8 * span),
                "into": (-1.0, 0.0), "contact": (-half_w, 0.0)}
    if kind == "wall_right":
        return {"p0": (half_w, -0.8 * span), "p1": (half_w, 0.8 * span),
                "into": (1.0, 0.0), "contact": (half_w, 0.0)}
    return None


def compose_layout(f1, f2, L: float = 1.5, floor: float = FORCE_MIN_LEN) -> dict:
    """平行四边形定则几何（规范§7）：两分力箭长走 _force_lengths（与受力图同一把尺子），

    合力 = 对角线 v1+v2；对边是另一个分力向量的**精确平移**（平行且等长由向量加法保证，不是手绘）。
    返回 {"v1","v2","result","lens","cross"}，均为二维 np 向量/标量，原点在共同作用点。
    """
    d1 = _dir_vec(f1.get("dir"))
    d2 = _dir_vec(f2.get("dir"))
    d1 = d1 / (np.linalg.norm(d1) or 1.0)
    d2 = d2 / (np.linalg.norm(d2) or 1.0)
    l1, l2 = _force_lengths([f1, f2], L, floor)
    v1, v2 = d1 * l1, d2 * l2
    r = v1 + v2
    return {"v1": v1, "v2": v2, "result": r, "lens": [l1, l2],
            "cross": float(v1[0] * v2[1] - v1[1] * v2[0])}


def resolve_layout(force, axis_deg: float = 0.0, L: float = 1.5) -> dict:
    """正交分解几何（规范§7 推论）：F 沿两根互相垂直的轴取**精确投影**（画出来的长度由

    fx=F·e1、fy=F·e2 算出，与 |F|·cosθ 恒等），分量之和向量恒等于 F。
    """
    d = _dir_vec(force.get("dir"))
    d = d / (np.linalg.norm(d) or 1.0)
    v = d * L
    ax = math.radians(float(axis_deg or 0.0))
    e1 = np.array([math.cos(ax), math.sin(ax), 0.0])
    e2 = np.array([-math.sin(ax), math.cos(ax), 0.0])
    return {"v": v, "e1": e1, "e2": e2,
            "fx": float(v[0] * e1[0] + v[1] * e1[1]),
            "fy": float(v[0] * e2[0] + v[1] * e2[1]),
            "cos": float((v[0] * e1[0] + v[1] * e1[1]) / L)}


def incline_slide_layout(angle_deg, mu: float = 0.0, g: float = 9.8,
                         T: float = 6.0, n: int = 6) -> dict:
    """斜面下滑仿真采样（81-S2；SIM_DT 口径——数学驱动、与渲染帧率解耦，禁手填关键帧）。

    a = g(sinθ − μcosθ) 恒加速（规范§6：N 垂斜面、f 沿斜面与相对运动反向——箭头由 builder 画，
    这里只管数）；v(t)=at、s(t)=½at²，按 n 等分时间 {t_k=kT/n} 逐点算出。
    μ ≥ tanθ → a=0：从静止释放**不滑**，v≡0（物理正确的"静止"，不是画法失败）。
    斜面三角尺寸沿用 _v_incline 的钳制（base 4.4、h≤2.6），保证与旧图元同一几何语言。
    """
    deg = max(10.0, min(float(angle_deg), 60.0))
    a = math.radians(deg)
    n = max(3, min(int(n), 8))
    T = max(1.0, float(T))
    acc = max(0.0, float(g) * (math.sin(a) - float(mu) * math.cos(a)))
    ts = [k * T / n for k in range(n + 1)]
    vs = [acc * t for t in ts]
    ss = [0.5 * acc * t * t for t in ts]
    base = 4.4
    h = base * math.tan(a)
    if h > 2.6:
        h = 2.6
        base = h / math.tan(a)
    return {"deg": deg, "rad": a, "a": acc, "g": float(g), "mu": float(mu), "T": T, "n": n,
            "ts": ts, "vs": vs, "ss": ss, "vmax": vs[-1], "smax": ss[-1], "base": base, "h": h}


def _equal_ticks(mid, d, k: int = 1, half: float = 0.07, spread: float = 0.09) -> list:
    """等长复制标记：边中点处 k 条垂直于边的小刻度线（同数刻度 = 一对平移复制、等长的边）。

    d 为沿边的单位向量；返回线段端点对列表，供 builder 画 Line（规范§7 辅助线要可辨识）。
    """
    nrm = np.array([-d[1], d[0], 0.0], dtype=float)
    nrm = nrm / (np.linalg.norm(nrm) or 1.0)
    out = []
    for i in range(max(1, int(k))):
        off = (i - (k - 1) / 2.0) * spread
        c = np.array(mid, dtype=float) + np.array(d, dtype=float) * off
        out.append((tuple(c - nrm * half), tuple(c + nrm * half)))
    return out


# ---------------- 电路版式（79-C1） ----------------
CIRCUIT_R = 0.3                      # 灯泡/电流表/电压表圆半径
CIRCUIT_HALF = {"battery": 0.55, "resistor": 0.55, "switch": 0.55,
                "capacitor": 0.18, "inductor": 0.5, "rheostat": 0.55}   # 其余类型（圆形元件）半宽 = CIRCUIT_R
CIRCUIT_TAP = 0.2                    # 电压表支路分接点离被测元件端子的距离
CIRCUIT_VRISE = 1.05                 # 电压表支路高出主回路顶边的距离（让开被测元件的标签）
AMMETER_MAX_DEFLECT = 60.0           # 指针满偏角（度）：示数=满量程时指针偏离竖直 60°，可读且不撞圆框


def ammeter_needle_angle(reading, full_scale=1.0) -> float:
    """电流表指针偏转角（度，竖直向上为 0，正值右偏、负值左偏）：θ = 60°·reading/full_scale，
    钳在 ±60°（超量程打满）。示数字段缺失/非法 → 0°（旧行为：只有圆圈 A，无指针）。
    方向随电流符号翻转是楞次定律刚需（Audit_79A §1.1 circuit 行、规范§16）。"""
    try:
        r = float(reading)
        f = float(full_scale)
    except (TypeError, ValueError):
        return 0.0
    if f <= 0:
        f = 1.0
    return max(-AMMETER_MAX_DEFLECT, min(AMMETER_MAX_DEFLECT, AMMETER_MAX_DEFLECT * r / f))


def _circuit_half(e) -> float:
    return CIRCUIT_HALF.get(str(e.get("type")), CIRCUIT_R)


def _voltmeter_target(e, i, elems, main) -> int | None:
    """电压表跨接的被测元件下标：across=元件下标或 label；缺省取它前面最近的非电池元件，
    再退到后面最近的，再退到电池（测路端电压）。主回路没有元件时返回 None。"""
    if not main:
        return None
    acr = e.get("across")
    if isinstance(acr, int) and not isinstance(acr, bool) and acr in main:
        return acr
    if isinstance(acr, str):
        for j in main:
            if str(elems[j].get("label") or "") == acr or str(elems[j].get("type")) == acr:
                return j
    loads = [j for j in main if str(elems[j].get("type")) != "battery"]
    before = [j for j in loads if j < i]
    after = [j for j in loads if j > i]
    if before:
        return before[-1]
    if after:
        return after[0]
    return main[0]


def circuit_layout(elems: list) -> dict:
    """电路的纯几何布局（不建 Mobject，便于测试）。

    主回路：非电压表、未标 branch 的元件沿顶边等距排开，导线一直接到每个元件的端子（圆形元件即圆周 x±R），
    其余三边是导线；电压表不进主回路，跨接在被测元件两端：从元件两侧的分接点竖直上引，
    电压表居中在上方支路里（规范§2、§16「电压表并联」）。
    并联支路（81-S1，规范§16）：元件带可选字段 branch=k（整数或 "1"/"2" 数字串）即离开主回路，
    按 k 分组、各自挂成一条**竖直支路**（上下端接主回路顶边/底边的分接点，元件沿支路纵向排开），
    同一 k 的多个元件在该支路内首尾顺次串联——两支路并列连接，即并联。
    连接点：只在 ≥3 根导线交汇处（电压表分接点、支路上下脚）画实心点；拐角、元件端子不画。
    电流箭头（81-S1，规范§16「正极→外电路→负极」）：主回路含 battery 时给出 current.arrows——
    顶边两段沿 −x（+ 极在电池左侧，与 symbol 画法制）、左边 −y、右边 +y、底边 +x；
    每条竖直支路一个箭头（电池右侧支路电流自下而上、电池左侧自上而下，KCL 连续）；
    电池不在主回路时 arrows=[]。
    返回 hw/hh（主回路半宽/半高）、wires[(a,b)]、junctions[(x,y)]、pos[元件中心，按 elems 顺序]、
    terminals[(近端,远端)：横放=(左,右)，竖放=(上,下)]、main（串在主回路的元件下标）、parallel{电压表下标: 被测下标}、
    branch_cols[{"x","branch","elems","ys"}]、current{"arrows":[{"p","d"}],"battery"}。
    """
    groups = {}
    for i, e in enumerate(elems):
        b = e.get("branch") if isinstance(e, dict) else None
        if b is None or (isinstance(b, str) and not b.strip()):
            continue
        key = str(b).strip() if isinstance(b, str) else b
        groups.setdefault(key, []).append(i)
    brset = {i for ids in groups.values() for i in ids}
    main = [i for i, e in enumerate(elems)
            if i not in brset and str(e.get("type")) != "voltmeter"]
    volts = [i for i, e in enumerate(elems) if i not in brset and str(e.get("type")) == "voltmeter"]
    parallel = {}
    for i in volts:
        t = _voltmeter_target(elems[i], i, elems, main)
        if t is None:            # 只有电压表、没有可测元件：退回串在顶边（旧行为），保证不报错
            main.append(i)
        else:
            parallel[i] = t
    main.sort()
    n = max(len(main), 1)
    W = max(4.0, 1.7 * n + 0.8)
    H = 1.6
    hw = W / 2
    hh = H / 2
    # 81-S1 修正：支路元件沿支路方向占 2×_circuit_half（框类旋转后长轴沿支路），
    # 均分 ys 会让相邻元件重叠、导线倒插进电容断口（视觉上短路）——先按元件尺寸
    # 估支路所需高度，不够则整体加高主回路，再自上而下顺次排布留足接线段。
    _lead_min = 0.12
    for _ids in groups.values():
        _need = sum(_circuit_half(elems[i]) for i in _ids) + (len(_ids) + 1) * _lead_min
        hh = max(hh, _need)
    wires = [((-hw, hh), (-hw, -hh)), ((-hw, -hh), (hw, -hh)), ((hw, -hh), (hw, hh))]
    pos = [None] * len(elems)
    terminals = [None] * len(elems)
    top_gaps = []                # 顶边上相邻元件之间的空档 (起x, 止x)，给竖直支路挑位
    end_lead = 0.35              # 首尾只留短引线：整格等分会把电源/末端元件外侧空出一大段
    spans = [2 * _circuit_half(elems[i]) for i in main]
    n_el = len(main)
    gap = max(0.0, (W - 2 * end_lead - sum(spans)) / (n_el - 1)) if n_el > 1 else 0.0
    prev = -hw
    cursor = (-hw + end_lead if n_el > 1
              else -hw + (W - spans[0]) / 2 if n_el == 1 else -hw)
    for i in main:
        gw = _circuit_half(elems[i])
        x = cursor + gw
        pos[i] = (x, hh)
        terminals[i] = ((x - gw, hh), (x + gw, hh))
        wires.append(((prev, hh), (x - gw, hh)))
        if (x - gw) - prev >= 0.5:
            top_gaps.append((prev, x - gw))
        prev = x + gw
        cursor = prev + gap
    wires.append(((prev, hh), (hw, hh)))
    if hw - prev >= 0.5:
        top_gaps.append((prev, hw))
    # ---- 并联支路列（81-S1）----
    branch_cols = []
    col_x = []
    keys = sorted(groups.keys(), key=lambda k: groups[k][0])
    xs_pool = [0.5 * (a + b) for a, b in top_gaps]
    if len(keys) <= len(xs_pool):
        step = len(xs_pool) / len(keys) if keys else 1
        col_x = [xs_pool[min(int((j + 0.5) * step), len(xs_pool) - 1)] for j in range(len(keys))]
    elif xs_pool:
        col_x = list(xs_pool) + [-hw + (j + 1) * W / (len(keys) - len(xs_pool) + 1)
                                 for j in range(len(keys) - len(xs_pool))]
    else:
        col_x = [-hw + (j + 1) * W / (len(keys) + 1) for j in range(len(keys))]
    used_x = set()
    for j, kk in enumerate(keys):
        xc = col_x[j]
        while any(abs(xc - ux) < 0.5 for ux in used_x):
            xc += 0.5
        used_x.add(xc)
        ids = groups[kk]
        m = len(ids)
        hvs = [_circuit_half(elems[i]) for i in ids]
        lead = max(_lead_min, (2 * hh - 2 * sum(hvs)) / (m + 1))
        ys, _cur = [], hh
        for hv in hvs:
            _cur -= lead + hv
            ys.append(_cur)
            _cur -= hv
        col_e, col_ys = [], []
        cursor = hh
        for t, i in enumerate(ids):
            hv = _circuit_half(elems[i])
            y = ys[t]
            pos[i] = (xc, y)
            terminals[i] = ((xc, y + hv), (xc, y - hv))
            wires.append(((xc, cursor), (xc, y + hv)))
            cursor = y - hv
            col_e.append(i)
            col_ys.append(y)
        wires.append(((xc, cursor), (xc, -hh)))
        branch_cols.append({"x": xc, "branch": kk, "elems": col_e, "ys": col_ys})
    junctions = []
    stack = {}
    for i, t in parallel.items():
        level = stack.get(t, 0)
        stack[t] = level + 1
        tx = pos[t][0]
        gw = _circuit_half(elems[t])
        lx, rx = tx - gw - CIRCUIT_TAP, tx + gw + CIRCUIT_TAP
        vy = hh + CIRCUIT_VRISE * (level + 1)
        pos[i] = (tx, vy)
        terminals[i] = ((tx - CIRCUIT_R, vy), (tx + CIRCUIT_R, vy))
        wires += [((lx, hh), (lx, vy)), ((lx, vy), (tx - CIRCUIT_R, vy)),
                  ((tx + CIRCUIT_R, vy), (rx, vy)), ((rx, vy), (rx, hh))]
        if level == 0:           # 同一被测元件的第二块表从同一对分接点上引，点不重复
            junctions += [(lx, hh), (rx, hh)]
    for col in branch_cols:      # 支路上下脚都是三线交汇：实心点（规范§2 连接点）
        junctions += [(col["x"], hh), (col["x"], -hh)]
    # ---- 电流方向箭头（81-S1）：电池 + 极（左侧长板）→ 外电路 → − 极 ----
    arrows = []
    batt = next((i for i in main if str(elems[i].get("type")) == "battery"), None)
    if batt is not None:
        bx = pos[batt][0]
        gbh = _circuit_half(elems[batt])
        for a, b in top_gaps:    # 电池两侧顶边各一支，方向都沿 −x
            if abs(b - (bx - gbh)) < 1e-9 or abs(a - (bx + gbh)) < 1e-9:
                arrows.append({"p": (0.5 * (a + b), hh), "d": (-1, 0), "side": "top"})
        arrows.append({"p": (-hw, 0.0), "d": (0, -1), "side": "left"})
        arrows.append({"p": (hw, 0.0), "d": (0, 1), "side": "right"})
        feet = sorted([c["x"] for c in branch_cols])
        segs = list(zip([-hw] + feet, feet + [hw]))
        a0, b0 = max(segs, key=lambda s: s[1] - s[0]) if segs else (-hw, hw)
        arrows.append({"p": (0.5 * (a0 + b0), -hh), "d": (1, 0), "side": "bottom"})
        for col in branch_cols:  # 支路电流：电池右侧自下而上，左侧自上而下（KCL 连续）
            top_y = col["ys"][0] + _circuit_half(elems[col["elems"][0]])
            # 箭头须整支落在母线与首元件之间的接线段内：短支路时自动缩短，
            # 不再压到母线/连接点上（81-S1 冒烟实拍发现箭头骑跨顶栏）。
            half = max(0.06, min(0.2, 0.5 * (hh - top_y) - 0.02))
            arrows.append({"p": (col["x"], 0.5 * (hh + top_y)), "half": half,
                           "d": (0, 1 if col["x"] > bx else -1), "side": "branch"})
    return {"hw": hw, "hh": hh, "wires": wires, "junctions": junctions, "pos": pos,
            "terminals": terminals, "main": main, "parallel": parallel,
            "branch_cols": branch_cols, "current": {"arrows": arrows, "battery": batt}}


# ---------------- 条形磁铁磁感线（79-C1） ----------------
# 模型：均匀磁化条形磁铁 = 两端面均布磁荷（N 面 +σ、S 面 −σ）。在图平面内把每个端面当作
# 均匀带"荷"线段，场用二维解析式（线段积分闭式），不做逐点求和，追踪一条线只要几毫秒。
# 对称性：B_x(−x,y)=B_x(x,y)、B_y(−x,y)=−B_y(x,y)，所以从 N 面 (hx,y0) 出发的线关于 x=0
# 镜像后恰好落回 S 面 (−hx,y0)。只积分右半段（到 x=0）再镜像，闭合与终点由构造保证，
# 不受积分误差影响；内部段是 (−hx,y0)→(hx,y0) 的 S→N 平行直线。

def _magnet_B(x: float, y: float, hx: float, hh: float):
    bx = by = 0.0
    for a, q in ((hx, 1.0), (-hx, -1.0)):
        dx = x - a
        if abs(dx) < 1e-9:
            dx = 1e-9
        bx += q * (math.atan((hh - y) / dx) + math.atan((hh + y) / dx))
        by += q * 0.5 * math.log((dx * dx + (y + hh) ** 2) / (dx * dx + (y - hh) ** 2 + 1e-12))
    return bx, by


def magnet_field_line(y0: float, hx: float = 1.2, hh: float = 0.45, max_steps: int = 1200) -> list:
    """从 N 极面 (hx, y0) 出发的一条外部磁感线，终于 S 极面 (−hx, y0)，返回 [(x, y), ...]。

    RK4、单位化方向场；近极处步长 0.02、远处 0.05。确定性（无随机），只依赖入参。
    """
    def f(px, py):
        bx, by = _magnet_B(px, py, hx, hh)
        n = math.hypot(bx, by) or 1e-12
        return bx / n, by / n

    x, y = hx + 1e-3, y0
    half = [(hx, y0), (x, y)]
    for _ in range(max_steps):
        h = 0.02 if math.hypot(x - hx, y) < 0.6 else 0.05
        k1 = f(x, y)
        k2 = f(x + .5 * h * k1[0], y + .5 * h * k1[1])
        k3 = f(x + .5 * h * k2[0], y + .5 * h * k2[1])
        k4 = f(x + h * k3[0], y + h * k3[1])
        nx = x + h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        ny = y + h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        if nx <= 0.0:
            t = x / (x - nx)
            half.append((0.0, y + (ny - y) * t))
            break
        x, y = nx, ny
        half.append((x, y))
    else:
        raise ValueError(f"magnet field line from y0={y0} did not reach x=0")
    mirror = [(-px, py) for px, py in reversed(half[:-1])]
    return half + mirror


# ---------------- 电场线 / 螺线管 / 小磁针（81-S1，Audit_79A §1.1 field P1 行） ----------------
# 口径全部来自 Ref_Physics_Diagram_Standards：§20 电场线（正→负、不断裂、不相交、疏密示强弱、
# 匀强场平行等距）、§18 螺线管（安培定则二：四指顺电流、拇指=N 极；外 N→S、内 S→N 闭合）、
# §19 小磁针（静止 N 极指向=该点磁场方向，N 端画红）。
# 等量异号电场线与 magnet_field_line 同法：±点电荷解析场（3D 型 q·r̂/r²）RK4 单位化流线，
# 追到中线 x=0 再按 (x,y)→(−x,y) 镜像——中线处 E 恰沿 +x（垂直穿中线），镜像后曲线光滑、
# 起点终点由构造落在两电荷的 r0 圆上（规范§20「出发/终止」）。

EFIELD_D, EFIELD_R0 = 1.0, 0.16       # 电荷半间距 d、电场线起/终半径 r0
EFIELD_PAIR_SEEDS = (30.0, 65.0, 100.0)


def _pair_E(x: float, y: float, d: float = EFIELD_D):
    ex = ey = 0.0
    for a, q in ((-d, 1.0), (d, -1.0)):
        dx, dy = x - a, y
        r3 = (dx * dx + dy * dy) ** 1.5
        ex += q * dx / r3
        ey += q * dy / r3
    return ex, ey


def efield_pair_line(phi_deg: float, d: float = EFIELD_D, r0: float = EFIELD_R0,
                     max_steps: int = 4000) -> list:
    """从 +q(−d,0) 面出发、终于 −q(+d,0) 面的一条电场线（上半平面，phi_deg∈(0,180)）。

    出发点 = 正电荷周围 r0 圆上极角 phi_deg 处；RK4 沿单位化 E 追到中线 x=0（交点插值），
    再 (x,y)→(−x,y) 镜像成完整线。确定性、只依赖入参。返回 [(x,y),...]，首尾分别落在
    距 +q、−q 恰为 r0 的位置，且两端 y 相同（镜像构造保证）。
    """
    phi = math.radians(phi_deg)
    x, y = -d + r0 * math.cos(phi), r0 * math.sin(phi)

    def f(px, py):
        ex, ey = _pair_E(px, py, d)
        n = math.hypot(ex, ey) or 1e-12
        return ex / n, ey / n

    half = [(x, y)]
    reached = False
    for _ in range(max_steps):
        h = 0.02 if (math.hypot(x + d, y) < 0.6 or math.hypot(x - d, y) < 0.6) else 0.05
        k1 = f(x, y)
        k2 = f(x + .5 * h * k1[0], y + .5 * h * k1[1])
        k3 = f(x + .5 * h * k2[0], y + .5 * h * k2[1])
        k4 = f(x + h * k3[0], y + h * k3[1])
        nx = x + h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        ny = y + h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        if abs(nx) > 4 * d or abs(ny) > 4 * d:
            raise ValueError(f"efield line from phi={phi_deg} escaped")
        if nx >= 0.0:
            t = x / (x - nx)
            half.append((0.0, y + (ny - y) * t))
            reached = True
            break
        x, y = nx, ny
        half.append((x, y))
    if not reached:
        raise ValueError(f"efield line from phi={phi_deg} did not reach midplane")
    mirror = [(-px, py) for px, py in reversed(half[:-1])]
    return half + mirror


def efield_point_layout(charge: str = "pos", spokes: int = 8,
                        r0: float = 0.42, r1: float = 1.9) -> dict:
    """点电荷辐射状电场线（规范§20）：sgn=+1 从电荷向外、−1 从无穷会向电荷。

    spokes 条同半径射线段（方向沿 ±r̂，天然互不相交、只有起点/终点与电荷重合）；
    每条线中点放一个箭头，方向 = sgn·r̂（正外负内）。angle 为极角（弧度）。
    返回 {"sgn", "r0", "r1", "lines": [{"angle","p0","p1","arrow":{"pos","d"}}]}。
    """
    sgn = -1 if str(charge).strip().lower() in ("neg", "negative", "-", "−") else 1
    s = max(int(spokes), 1)
    lines = []
    for k in range(s):
        a = 2 * math.pi * k / s
        ca, sa = math.cos(a), math.sin(a)
        mid = (0.5 * (r0 + r1) * ca, 0.5 * (r0 + r1) * sa)
        lines.append({"angle": a, "p0": (r0 * ca, r0 * sa), "p1": (r1 * ca, r1 * sa),
                      "arrow": {"pos": mid, "d": (sgn * ca, sgn * sa)}})
    return {"sgn": sgn, "r0": r0, "r1": r1, "lines": lines}


EFIELD_PLATE_GAP, EFIELD_PLATE_H, EFIELD_PLATE_N, EFIELD_PLATE_FRINGE = 2.2, 1.9, 5, 2


def efield_plate_layout(gap: float = EFIELD_PLATE_GAP, h: float = EFIELD_PLATE_H,
                        n: int = EFIELD_PLATE_N, fringe: int = EFIELD_PLATE_FRINGE,
                        samples: int = 33) -> dict:
    """平行板电容器匀强场 + 边缘 fringe（规范§20「匀强电场画平行等距箭头」）。

    板面在 x=±gap/2、竖直范围 ±h/2；左板 +、右板 −，场内方向恒 +x。
    uniform：n 条横贯板间的直线，y 等间距（匀强→平行等距，间距=0.9h/(n−1)），每条中点箭头 +x；
    fringe：upper/lower 各 fringe 条正弦隆起线 y(t)=yb+b·sin(πt)，两端贴板面、越靠外隆得越高、
    顶点越过板缘（|顶点 y|>h/2 即「边缘略弯」），顶点箭头 +x（t=0.5 切线水平）。
    返回 {"gap","h","uniform":[{"y","p","q","arrow"}],"fringe":[{"pts","apex","arrow"}],"plates"}。
    """
    g = gap / 2
    n = max(int(n), 2)
    sp = 0.9 * h / (n - 1)
    uniform = []
    for i in range(n):
        y = (i - (n - 1) / 2) * sp
        uniform.append({"y": y, "p": (-g, y), "q": (g, y),
                        "arrow": {"pos": (0.0, y), "d": (1.0, 0.0)}})
    fringe_n = max(int(fringe), 0)
    fringe = []
    for j in range(fringe_n):
        b = 0.28 + 0.3 * j
        for sg in (1, -1):
            yb = sg * (h / 2 - 0.12)
            pts = [(-g + 2 * g * t / (samples - 1),
                    yb + sg * b * math.sin(math.pi * t / (samples - 1)))
                   for t in range(samples)]
            apex = (0.0, yb + sg * b)
            fringe.append({"pts": pts, "apex": apex,
                           "arrow": {"pos": apex, "d": (1.0, 0.0)}})
    return {"gap": gap, "h": h, "uniform": uniform, "fringe": fringe,
            "plates": [(-g, -h / 2, -1), (g, -h / 2, 1)]}


SOLENOID_HX, SOLENOID_HH, SOLENOID_TURNS = 1.15, 0.42, 5
SOLENOID_SEEDS = (0.62, 0.8, 0.95)     # 外线种子（占端面半高，同磁铁口径：近极面密）


def solenoid_layout(turns: int = SOLENOID_TURNS, wind: str = "up_front") -> dict:
    """通电螺线管的纯几何（规范§18 安培定则二）。

    wind="up_front"：电流在朝向读者的一侧竖直向上 → 磁矩 m=(1/2)∮r×dl 沿 −x → N 极在 −x 端；
    "down_front" 反向。ns = N 端的 x 符号（−1/1），全部方向由它导出，内外自洽：
    bars：turns 根绕线（前侧可见段，电流 (0, −ns)）；
    inner：内部 3 条平行等距线（S→N，方向 (ns,0)，"内部近匀强"）；
    seeds：外部磁感线种子高度，渲染端用 magnet_field_line(y0, hx, hh) 追踪——
    其镜像构造保证每条外线一端落 (hx,y0)、另一端落 (−hx,y0)：ns=1 时起点即 N 端（外 N→S），
    ns=−1 时整线按 x→−x 镜像，起点即左 N 端、终于右 S 面（安培定则与磁铁等价）。
    返回 {"hx","hh","ns","bars":[{"x","dir"}],"inner":[{"y","dir"}],"seeds"}。
    """
    t = max(int(turns), 3)
    ns = -1 if str(wind).strip().lower() != "down_front" else 1
    hx, hh = SOLENOID_HX, SOLENOID_HH
    xb = hx - 0.12                     # 绕线杆分布范围：留出端面给磁感线收口
    bars = []
    for k in range(t):
        x = -xb + 2 * xb * k / (t - 1) if t > 1 else 0.0
        bars.append({"x": x, "dir": (0.0, float(-ns))})
    inner = [{"y": (i - 1) * 0.66 * hh, "dir": (float(ns), 0.0)} for i in range(3)]
    return {"hx": hx, "hh": hh, "ns": ns, "bars": bars, "inner": inner,
            "seeds": [s * hh for s in SOLENOID_SEEDS]}


COMPASS_LEN, COMPASS_W = 0.95, 0.3


def compass_layout(angle_deg: float = 0.0, length: float = COMPASS_LEN,
                   width: float = COMPASS_W) -> dict:
    """小磁针纯几何（规范§19：静止 N 极指向=该点磁场方向；N 端红）。

    angle_deg：N 端指向（数学角，+x=0°、逆时针为正）。菱形两半：
    n_half=[tip, sideA, sideB]（含指向 tip 的三角，渲染填红）、s_half=[tail, sideA, sideB]。
    返回 {"angle","u","tip","tail","poly","n_half","s_half","pivot"}。
    """
    th = math.radians(float(angle_deg))
    u = (math.cos(th), math.sin(th))
    w = (-math.sin(th), math.cos(th))
    tip = (0.5 * length * u[0], 0.5 * length * u[1])
    tail = (-tip[0], -tip[1])
    sA = (0.5 * width * w[0], 0.5 * width * w[1])
    sB = (-sA[0], -sA[1])
    return {"angle": th, "u": u, "tip": tip, "tail": tail,
            "poly": [tip, sA, tail, sB], "n_half": [tip, sA, sB],
            "s_half": [tail, sA, sB], "pivot": (0.0, 0.0)}


# ---------------- 光学透镜成像 / 通电导线磁场（79-C2a，纯几何，便于测试） ----------------

LENS_F = 1.0    # 默认焦距（场景单位）；f>0 凸透镜、f<0 凹透镜


def lens_layout(u, f: float = LENS_F, oh: float = 0.9) -> dict:
    """透镜成像的纯几何（不建 Mobject）。规范§14、Audit_79A §1.1 optics lens。

    符号口径（实正虚负）：u 物距（>0，物在 x=−u）、f 焦距（凸正凹负）、oh 物高（>0）。
    像距解析解 1/u + 1/v = 1/f ⇒ v = u·f/(u−f)；像高 ih = −oh·v/u。
    v>0 ⇒ 异侧倒立实像（凸透镜 u>f）；v<0 ⇒ 同侧正立虚像（凸透镜 u<f 放大、凹透镜恒缩小）。
    三条特殊光线：①平行主轴→过（凹透镜：反向延长过同侧虚焦点）焦点；②过光心 O 不偏折；
    ③过（或延长线指向）焦点→平行主轴出射。实际光线实线段（出射段带箭头=arrow），
    反向延长线虚线段（dashed），虚线段所在直线都过像点顶点 img。
    返回 {"u","f","oh","v","ih","real","obj_top","img","x_left","x_right","lens_h",
    "focus":[(±|f|,0)], "pt2f":[在轴内的 (±2|f|,0)], "segs":[{"p","q","dashed","arrow"}]}。
    """
    u, f, oh = float(u), float(f), float(oh)
    fm = abs(f)
    if fm <= 1e-12 or u <= 0 or oh <= 0 or abs(u - f) < 1e-9:
        raise ValueError("lens_layout 需要 u>0、f!=0 且 u!=f（u=f 像在无穷远）")
    v = u * f / (u - f)
    ih = -oh * v / u
    top, img = (-u, oh), (v, ih)
    xr = 1.8 * fm                       # 虚像情形出射光线的右端裁剪
    segs = []

    def seg(p, q, dashed=False, arrow=False):
        segs.append({"p": p, "q": q, "dashed": dashed, "arrow": arrow})

    def exit_end(p0, p1, xmax=xr, yabs=2.0 * fm):
        """沿 p0→p1 方向把出射光线画到裁剪框（x≤xmax，|y|≤yabs）内的终点。"""
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        t = float("inf")
        if dx > 1e-12:
            t = (xmax - p0[0]) / dx
        if dy > 1e-12:
            t = min(t, (yabs - p0[1]) / dy)
        if dy < -1e-12:
            t = min(t, (-yabs - p0[1]) / dy)
        if not t > 0:
            t = 0.8
        return (p0[0] + dx * t, p0[1] + dy * t)

    if f > 0 and v > 0:                 # 凸透镜实像：三条光线实线会聚于像点，无反向延长
        seg(top, (0, oh))
        seg((0, oh), img, arrow=True)   # ①平行入射→过焦点折向像点
        seg(top, img, arrow=True)       # ②过光心方向不变
        seg(top, (0, ih))               # ③过物方焦点入射
        seg((0, ih), img, arrow=True)   # ③平行出射（出射高度恰等于像高）
    elif f > 0:                         # 凸透镜 u<f（放大镜）：出射发散，反向延长线交正立放大虚像
        a0 = (0, oh)
        seg(top, a0)
        seg(a0, exit_end(a0, (fm, 0.0)), arrow=True)
        seg(a0, img, dashed=True)
        seg(top, exit_end(top, (0.0, 0.0)), arrow=True)
        seg((0, 0), img, dashed=True)
        seg(top, (0, ih))
        seg((0, ih), (xr, ih), arrow=True)
        seg((0, ih), img, dashed=True)
    else:                               # 凹透镜（发散）：恒成正立缩小虚像；①反向延长过同侧虚焦点
        a0 = (0, oh)
        seg(top, a0)
        seg(a0, exit_end(a0, (fm, 2 * oh)), arrow=True)
        seg((-fm, 0.0), a0, dashed=True)
        seg(top, exit_end(top, (0.0, 0.0)), arrow=True)
        seg(top, (0, ih))
        seg((0, ih), (xr, ih), arrow=True)
        seg((0, ih), img, dashed=True)

    x_left = -(max(u, abs(v), 2 * fm) + 0.45)
    x_right = (max(v, 2 * fm) + 0.45) if v > 0 else (xr + 0.35)
    return {
        "u": u, "f": f, "oh": oh, "v": v, "ih": ih, "real": v > 0,
        "obj_top": top, "img": img,
        "x_left": x_left, "x_right": x_right,
        "lens_h": 2 * max(1.4, oh + 0.35, (abs(ih) + 0.35) if f > 0 else 0.0),
        "focus": [(-fm, 0.0), (fm, 0.0)],
        "pt2f": [(x, 0.0) for x in (-2 * fm, 2 * fm) if x_left + 0.1 <= x <= x_right - 0.1],
        "segs": segs,
    }


WIRE_FIELD_R0, WIRE_FIELD_RATIO, WIRE_FIELD_N = 0.6, 1.55, 4


def wire_field_layout(current: str = "out", r0: float = WIRE_FIELD_R0,
                      ratio: float = WIRE_FIELD_RATIO, n: int = WIRE_FIELD_N) -> dict:
    """通电直导线磁感线同心圆的纯几何（规范§17：越靠近导线越密）。

    B∝1/r ⇒ 半径取等比数列 r0·ratio^k（外圈间距越来越大，近导线侧变密）。
    安培定则：current="out"（·，出纸面）→ 逆时针（ccw=True，切向 (−sinθ, cosθ)）；
    "in"（×，入纸面）→ 顺时针（切向取反）。每条圆上放一个切向小箭头。
    返回 {"radii":[...], "ccw": bool,
    "arrows":[{"r","angle","pos":(x,y),"tangent":(tx,ty)}...]}，tangent 为单位向量，
    cross(pos, tangent) 的 z 分量同号：出纸面 >0（逆时针）、入纸面 <0（顺时针）。
    """
    ccw = str(current or "out").strip().lower() != "in"
    radii = [r0 * ratio ** k for k in range(max(n, 1))]
    angles = (55.0, 150.0, 250.0, 330.0)
    arrows = []
    for k, r in enumerate(radii):
        a = math.radians(angles[k % len(angles)])
        sgn = 1.0 if ccw else -1.0
        arrows.append({"r": r, "angle": angles[k % len(angles)],
                       "pos": (r * math.cos(a), r * math.sin(a)),
                       "tangent": (sgn * -math.sin(a), sgn * math.cos(a))})
    return {"radii": radii, "ccw": ccw, "arrows": arrows}


MECH_BULGE_K = 0.30      # 弯箭头默认鼓度 = 0.30 × 弦长（弯月形一眼可辨，不贴死弦线）
MECH_HEAD_LEN = 0.26     # 箭刺（鱼钩/全头两刺）长度
MECH_BARB_DEG = 26.0     # 箭刺从终点切线反向张开的半角


def mech_arrow_geom(p0, p1, bulge=None, full_head=True,
                    head_len=MECH_HEAD_LEN, barb_deg=MECH_BARB_DEG) -> dict | None:
    """机理弯箭头（电子流向）纯几何：三次贝塞尔控制点 + 顶点 + 终点切向 + 箭刺线段。

    画法口径（IUPAC 推荐符号／有机教材惯例，Projrct_Plan 与语料白名单内无化学机理规范，
    自定并在此钉死）：
      · 弯箭头尾部落在**电子源**（孤对电子或成键电子对）、箭头落在**电子汇**（原子或新键位）；
      · full_head=True（type="cov"，电子对流向／异裂机理）→ 全头：终点两侧对称张开的**双刺**；
      · full_head=False（type="hom"，单电子流向／均裂机理）→ 鱼钩：终点单侧**一刺**，
        弯侧取鼓度同一侧（钩尖朝曲线凹侧，与弯月走向一致，读起来才像"钩着电子走"）；
      · bulge>0 时曲线鼓向行进方向的**左手侧**（弦的 +法向，n=R90°(d̂)），bulge<0 反侧；
        缺省鼓度 MECH_BULGE_K×弦长。弯月弧的顶点（t=0.5）偏离弦线 |bulge|·0.75。
    退化（起终点重合，弦长<1e-9）返回 None——调用方跳过，绝不画零长箭。
    返回 {"ctrl":[p0,c1,c2,p1] 各 (x,y), "apex":(x,y), "head_dir":单位(ux,uy),
          "tail_dir":单位(ux,uy), "barbs":[((x0,y0),(x1,y1)),…1或2条], "bulge": float}。
    """
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return None
    ux, uy = dx / L, dy / L                 # 弦向单位向量
    nx, ny = -uy, ux                       # 行进方向左法向（R90°）
    b = MECH_BULGE_K * L if bulge is None else float(bulge)
    c1 = (x0 + dx / 3.0 + nx * b, y0 + dy / 3.0 + ny * b)
    c2 = (x0 + 2.0 * dx / 3.0 + nx * b, y0 + 2.0 * dy / 3.0 + ny * b)
    apex = ((x0 + 3.0 * c1[0] + 3.0 * c2[0] + x1) / 8.0,
            (y0 + 3.0 * c1[1] + 3.0 * c2[1] + y1) / 8.0)   # B(0.5) 精确式
    tx, ty = x1 - c2[0], y1 - c2[1]        # 终点切向（B'(1)=3(p1−c2)，方向与系数无关）
    tl = math.hypot(tx, ty) or 1.0
    hd = (tx / tl, ty / tl)                # 箭头行进方向（进入终点）
    ang = math.radians(barb_deg)
    ca, sa = math.cos(ang), math.sin(ang)

    def _rot(vx, vy, c, s):                # 逆时针旋 c,s
        return (vx * c - vy * s, vx * s + vy * c)

    back = (-hd[0], -hd[1])                # 从终点回拉的方向
    rb_p = _rot(back[0], back[1], ca, sa)  # +侧（左手侧）
    rb_m = _rot(back[0], back[1], ca, -sa)
    if full_head:
        barbs = [((x1, y1), (x1 + rb_p[0] * head_len, y1 + rb_p[1] * head_len)),
                 ((x1, y1), (x1 + rb_m[0] * head_len, y1 + rb_m[1] * head_len))]
    else:
        r = rb_p if b >= 0 else rb_m       # 鱼钩单刺：钩向曲线凹侧
        barbs = [((x1, y1), (x1 + r[0] * head_len, y1 + r[1] * head_len))]
    tdx, tdy = c1[0] - x0, c1[1] - y0
    td = math.hypot(tdx, tdy) or 1.0
    return {"ctrl": [(x0, y0), c1, c2, (x1, y1)], "apex": apex,
            "head_dir": hd, "tail_dir": (tdx / td, tdy / td),
            "barbs": barbs, "bulge": b}


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
        if main and not _has_scripts(main):
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
        # 82-F1：公式一律走 LaTeX。带 tex 的（行内已写命令）保留命令，其余把 expr 转 LaTeX；
        # TeX 不可用/编译失败才退回 rich()。note 是正文说明文字，仍走 rich。
        if p.get("tex"):
            core = _tex_formula(_texform.to_latex(p["tex"], keep_commands=True), 54, th["key"])
        else:
            core = _tex_formula(_texform.to_latex(p.get("expr", "")), 54, th["key"])
        if core is None:
            core = rich(p.get("expr", ""), 54, th["key"])
        g = VGroup(core)
        if p.get("note"):
            g.add(rich(p["note"], 28, th["dim"]))
        g.arrange(DOWN, buff=0.3)
        # P3 halo：公式是"本镜主角"时叠假辉光环（静态、垫底、无脉冲），环随 _fit 一起缩放。
        return VGroup(_halo_ring(core, th["key"]), g)

    def _v_derivation(self, p, th):
        """逐步等式推导（82-SD1b A 级过程动画）：写第一式 → 每步逐 token 形变/代入 → 落定点名。

        每一拍都是一次 play（经 _motion_steps / play_motion 挂到口播 cue）：
          · 第 1 步：Write 逐符号**书写**（不是淡入）；
          · 第 i 步：difflib 对齐两行 token——未变且未移位的 token 原地不动，变了/移位了
            的 token 走 _TokenMorph 原位形变；sub 代入值从「已知」条用 motion.value_flyin
            的语义飞进目标字母（字母先隐身、落定点亮）；旧注记退场、新注记淡入；
          · 末步：motion.emphasize 点名 result（命中 token）或结果行。

        props（向后兼容）:
          steps:   [{"text": "F = BIL", "note": "安培力", "sub": {"I": "BLv/R"},
                     "transform": 0}, ...]；也接受纯字符串；最多 8 步。
          symbols: {"F": "安培力", ...} 字母 → 物理含义。图例只列前 6 个。
          at:      与 steps 等长的 cue 键（字幕片段或 0~1 行序比例；缺省按行序均匀铺）。
          transform: 可选。整数 k = 本步声明由第 k 步形变而来（0 基；动画仍以屏上
                    当前行为起点）；"replace"/"换行" = 整行逐位换位（不做未变识别）。
          result:  可选。末步结果子串；命中 token 就把它们点名，命中不了点名末行。
        """
        raw = p.get("steps")
        raw_steps = [raw] if isinstance(raw, (str, dict)) else list(raw or [])[:8]
        symbols = p.get("symbols") if isinstance(p.get("symbols"), dict) else {}
        order: list[str] = []
        for st in raw_steps:
            text = st if isinstance(st, str) else str((st or {}).get("text", ""))
            for ch in text:
                if ch in symbols and ch not in order:
                    order.append(ch)
        palette = [th["accent"], th["warn"], th["key"], th["hi"], th["emph"], th["dim"]]
        color_of = {s: palette[i % len(palette)] for i, s in enumerate(order)}

        # 字母级切分：BIL 拆成 B/I/L（各自色标）；CJK 词与数字保持整段。
        # 上/下标只吃「一组」payload（^{...} / _2 / ^n），不再让 ^ 把后面整串吞进一个 token
        # ——否则 B^2L^2v/R 会变成单 token，token 链就退化成整式替换。
        _script = r"(?:\{[^}]*\}|[0-9]+(?:\.[0-9]+)?|[A-Za-z]+)"
        tok_re = re.compile(rf"[A-Za-zΑ-ωΔ](?:[_\^]{_script})?(?:[_\^]{_script})?"
                            r"|\d+(?:\.\d+)?|[\u4e00-\u9fff]+|[^\sA-Za-z0-9]")
        ops = set("=+-−×÷·/()[]{}<>≤≥≠,，。")

        def base_of(tok: str) -> str:
            return re.sub(r"[_^]\{?[^}]*\}?$", "", tok)

        def color_for(tok: str) -> str:
            b = base_of(tok)
            if b in color_of:
                return color_of[b]
            return th["dim"] if b in ops else th["fg"]

        def line_mob(text: str, fs: float = 34):
            # 82-F1：整行一个 MathTex 逐 token 排版（TeX 自己管间距），token 切分仍用 tok_re；
            # 子对象数必须与 token 一一对应才能逐 token 上色/形变，否则整行退回 rich 并留痕。
            toks = [t for t in tok_re.findall(str(text)) if t.strip()]
            math = _tex_math(*[_texform.to_latex(t) for t in toks], font_size=fs)
            mobs = list(math.submobjects) if math is not None else []
            if math is not None and len(mobs) != len(toks):
                print(f"[tex] derivation fallback to rich(): submobjects {len(mobs)} "
                      f"!= tokens {len(toks)}: {text}", file=sys.stderr)
                math = None
            if math is None:
                mobs = [rich(t, fs, color_for(t)) for t in toks]
                return VGroup(*mobs).arrange(RIGHT, buff=0.07), toks, mobs
            for m, t in zip(mobs, toks):
                m.set_color(color_for(t))
            return math, toks, mobs

        steps = []
        for st in raw_steps:
            d = st if isinstance(st, dict) else {"text": str(st)}
            if str(d.get("text", "")).strip():
                steps.append(d)
        if not steps:
            steps = [{"text": str(p.get("label") or "推导")}]

        # 所有步先建成同尺寸的「舞台行」：同一位置、'=' 列对齐，后续步构建期全透明。
        built = [line_mob(str(d["text"])) for d in steps]
        max_w = max(g[0].width for g in built)
        if max_w > SAFE_WIDTH - 1.2:          # 全行等比缩，避免逐步字号跳变
            k = (SAFE_WIDTH - 1.2) / max_w
            for line, _t, _m in built:
                line.scale(k)
        for line, toks, mobs in built:
            eq = next((m for t, m in zip(toks, mobs) if base_of(t) == "="), None)
            line.shift(LEFT * ((eq if eq is not None else line).get_center()[0]))
        all_lines = VGroup(*[g[0] for g in built])
        cx = (all_lines.get_left()[0] + all_lines.get_right()[0]) / 2
        for line, _t, _m in built:
            line.shift(LEFT * cx)             # 舞台整体居中，'=' 列仍共线
        stage = VGroup(*[g[0] for g in built])
        for _line, _toks, mobs in built:
            for m in mobs:
                m.set_opacity(0)              # 首步等 _LateWrite，其余步等形变/飞入

        # 注记叠在同一槽位（不是逐步向下堆行）：旧注记退场，新注记淡入。
        notes = []
        for d in steps:
            txt = str(d.get("note") or "").strip()
            notes.append(rich(txt, 21, th["dim"]).move_to([0, 0, 0]) if txt else None)
        note_slot = VGroup(*[n for n in notes if n is not None]) if any(notes) else None
        if note_slot is not None:
            for n in note_slot:
                n.set_opacity(0)
            if note_slot.width > SAFE_WIDTH - 1.0:
                note_slot.scale_to_fit_width(SAFE_WIDTH - 1.0)

        # 「已知」条：sub 的来源（题面条件先亮出来，讲到哪一步就从哪一条飞进公式）。
        sub_entries = []
        rail_chips = []
        for i, d in enumerate(steps):
            if i == 0:
                continue                      # 首步没有上一行，不做代入
            sub = d.get("sub") if isinstance(d.get("sub"), dict) else {}
            for sym, val in sub.items():
                sym, val = str(sym).strip(), str(val).strip()
                if not sym or not val:
                    continue
                ckey = sym if sym in color_of else base_of(sym)
                color = color_of.get(ckey, th["accent"])
                src = _tex_math(_texform.to_latex(val), font_size=19, color=color)
                if src is None:
                    src = rich(val, 19, color)
                chip = VGroup(rich(f"已知 {sym} =", 18, th["dim"]), src).arrange(
                    RIGHT, buff=0.1)
                rail_chips.append(chip)
                sub_entries.append((i, sym, val, src))
        rail = None
        if rail_chips:
            rail = VGroup(*rail_chips).arrange(RIGHT, buff=0.45)
            if rail.width > SAFE_WIDTH - 1.0:
                rail.scale_to_fit_width(SAFE_WIDTH - 1.0)

        legend = []
        for sym in order[:6]:
            if not str(symbols.get(sym) or "").strip():
                continue
            # 符号 token 走 LaTeX，中文含义仍是正文 rich（82-F1）。
            head = _tex_math(_texform.to_latex(sym), font_size=21, color=color_of[sym])
            if head is None:
                head = rich(sym, 21, color_of[sym])
            legend.append(VGroup(head, rich(str(symbols[sym]), 19, th["dim"]))
                          .arrange(RIGHT, buff=0.12))
        leg = None
        if legend:
            leg = VGroup(*legend).arrange(RIGHT, buff=0.55)
            if leg.width > SAFE_WIDTH - 1.0:
                leg.scale_to_fit_width(SAFE_WIDTH - 1.0)

        out = []
        if p.get("label"):
            lab = T(str(p["label"]), font_size=24, color=th["accent"])
            lab._placed = True
            out.append(lab)
        if rail is not None:
            rail._placed = True
            out.append(rail)
        stage._placed = True                  # 几何已定稿：不参与装配层「挪字」复核
        out.append(stage)
        if note_slot is not None:
            note_slot._placed = True
            out.append(note_slot)
        if leg is not None:
            leg._placed = True
            out.append(leg)
        block = VGroup(*out).arrange(DOWN, aligned_edge=LEFT, buff=0.22)

        # ---- beat 编排：一 step 一拍，cue 走 _cue_key（与 _reveal_at 同一把尺）----
        keys = reveal_keys(p.get("at"), len(built))
        beats = []

        line0, toks0, mobs0 = built[0]
        first = [_LateWrite(line0)]
        if notes[0] is not None:
            first.append(_LateFadeIn(notes[0]))
        b0 = _mo.MotionBeat(first, run_time=1.2, cue=None,
                            note=f"推导第1步：书写初始式（cue {keys[0]}）")
        b0._cue_key = keys[0]
        beats.append(b0)

        live = list(zip(toks0, mobs0))        # 屏上当前行：[(文本, 可视 token)]
        last_note = 0 if notes[0] is not None else None

        for i in range(1, len(built)):
            d = steps[i]
            _new_line, new_texts, new_mobs = built[i]
            old_texts = [t for t, _m in live]
            old_mobs = [m for _t, m in live]

            mode = d.get("transform")
            if isinstance(mode, str) and mode.strip().lower() in ("replace", "换行", "整行"):
                k = min(len(old_mobs), len(new_mobs))
                pairs = list(zip(range(k), range(k)))
                exits = list(range(k, len(old_mobs)))
                enters = list(range(k, len(new_mobs)))
            else:
                pairs, exits, enters = [], [], []
                sm = difflib.SequenceMatcher(None, old_texts, new_texts, autojunk=False)
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == "equal":
                        pairs.extend(zip(range(i1, i2), range(j1, j2)))
                    elif tag == "replace":
                        k = min(i2 - i1, j2 - j1)
                        pairs.extend(zip(range(i1, i1 + k), range(j1, j1 + k)))
                        exits.extend(range(i1 + k, i2))
                        enters.extend(range(j1 + k, j2))
                    elif tag == "delete":
                        exits.extend(range(i1, i2))
                    else:                       # insert
                        enters.extend(range(j1, j2))

            anims = []
            skip_old, skip_new = set(), set()
            sub_desc = []
            for (si, sym, val, src) in sub_entries:
                if si != i:
                    continue
                j = next((jj for jj in range(len(new_texts))
                          if base_of(new_texts[jj]) == base_of(sym)), None)
                if j is None:
                    continue                    # 本步文本里没有该字母：不飞，避免指错位置
                pair = next(((oi, ni) for oi, ni in pairs if ni == j), None)
                if pair is not None:
                    oi, _ni = pair
                    skip_old.add(oi)
                    anims.append(_Dissolve(old_mobs[oi], path_arc=0.1))
                elif j in enters:
                    pass                        # 新字母首次出现：由飞入负责点亮
                else:
                    continue
                skip_new.add(j)
                # 飞入语义走 motion.value_flyin；落点先透明、落定点亮由 _ValueFly 薄壳补。
                fly = _mo.value_flyin([(src, new_mobs[j])], emphasis_on_landing=False,
                                      run_time=0.9)[0]
                anims.extend(_ValueFly(a.target_mobject, a.mobject, path_arc=-np.pi / 2)
                             for a in fly.anims)
                sub_desc.append(f"代入 {sym}={val}")

            n_chain = 0
            for oi, ni in pairs:
                if oi in skip_old or ni in skip_new:
                    continue
                om, nm = old_mobs[oi], new_mobs[ni]
                same = old_texts[oi] == new_texts[ni]
                if same and float(np.linalg.norm(om.get_center() - nm.get_center())) < 1e-3:
                    continue                    # 未变且未移位：原地不动
                anims.append(_TokenMorph(om, nm, path_arc=0.0 if same else 0.15))
                n_chain += 1

            for oi in exits:
                if oi in skip_old:
                    continue
                anims.append(_Dissolve(old_mobs[oi], path_arc=-0.1))
            for nj in enters:
                if nj in skip_new:
                    continue
                anims.append(_LateFadeIn(new_mobs[nj], shift=DOWN * 0.2))

            same_note = (notes[i] is not None and last_note is not None
                         and str(steps[i].get("note", "")) == str(steps[last_note].get("note", "")))
            if notes[i] is not None and not same_note:
                if last_note is not None:
                    anims.append(_Dissolve(notes[last_note]))
                anims.append(_LateFadeIn(notes[i], shift=DOWN * 0.12))
                last_note = i

            if not anims:
                tgt = VGroup(*old_mobs) if len(old_mobs) > 1 else old_mobs[0]
                anims = [Indicate(tgt, scale_factor=1.08, color=th["hi"])]

            one = LaggedStart(*anims, lag_ratio=0.06) if len(anims) > 1 else anims[0]
            desc = sub_desc or (["逐 token 形变"] if n_chain else ["原位点名"])
            beat = _mo.MotionBeat([one], run_time=1.0, cue=None,
                                  note=f"推导第{i + 1}步：{'/'.join(desc)}（cue {keys[i]}）")
            beat._cue_key = keys[i]
            beats.append(beat)

            pair_map = {ni: oi for oi, ni in pairs if ni not in skip_new}
            new_live = []
            for ni in range(len(new_texts)):
                if ni in skip_new:
                    new_live.append((new_texts[ni], new_mobs[ni]))   # 飞入点亮的新 token
                elif ni in pair_map:
                    new_live.append((new_texts[ni], old_mobs[pair_map[ni]]))  # 形变后的旧 token
                else:
                    new_live.append((new_texts[ni], new_mobs[ni]))   # 新 token 已淡入
            live = new_live

        # 末步落定点名：result 命中的 token 一起 Indicate；命中不了点名整行。
        result = str(p.get("result") or "").strip()

        def _norm(s: str) -> str:
            s = str(s).translate(str.maketrans({"²": "2", "³": "3", "¹": "1", "⁰": "0",
                                                "⁻": "-"}))
            return re.sub(r"[\s·×*^_{}]", "", s)

        targets = []
        if live and result:
            texts = [_norm(t) for t, _m in live]
            joined = "".join(texts)
            pos = joined.find(_norm(result))
            if pos >= 0:
                end = pos + len(_norm(result))
                acc = 0
                for idx, nt in enumerate(texts):
                    if nt and acc < end and acc + len(nt) > pos:
                        targets.append(live[idx][1])
                    acc += len(nt)
        if not targets and live:
            targets = [m for _t, m in live]
        if targets:
            grp = VGroup(*targets) if len(targets) > 1 else targets[0]
            eb = _mo.emphasize(grp, kind="indicate", color=th["hi"])
            eb._cue_key = keys[-1]
            eb.note = f"末步落定点名：{result or '结果式'}（cue {keys[-1]}）"
            beats.append(eb)

        _mo.mount_motion(block, beats)
        return block

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
        # 82-SD1a：分段逐条揭示与语气点名（flash/wiggle）已有，按 M6 契约补的是
        # **过往条压暗 0.55**——dim-only beat（emphasis=False），强调仍由 _reveal_fx
        # 家族负责，两层不叠（同帧抢插值红线）。规格挂在返回组上：组不被摘出父链，
        # 逐条 units 虽被 collect_reveals 摘走，beat 只引用对象本身、不依赖父链。
        out = units[0] if len(units) == 1 else VGroup(*units)
        if len(units) >= 2:
            self._mount_text_reveal(out, units, keys, th, emphasis=False)
        return out

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

    def _mount_text_reveal(self, group, units, keys, th, *, emphasis: bool = True,
                           sweep: bool = False) -> None:
        """82-SD1a M6 文本要点接线：给逐条揭示的行挂 motion 规格（不产 beats）。

        为什么挂"规格"而不是直接挂 beats：builder 产物还要过 `_fit` 等比缩放，
        Indicate/TransformFromCopy 在构造时捕获几何——提前产 beat 会点在旧坐标上。
        `_render_shot` 装配定稿后按本规格调 ``motion.reveal(animate_in=False)`` 产 beats：
        出场仍走引擎 _reveal_at 同帧淡入（零帧成本、与字幕同轴——评审 D9 红线），
        beat 只带「当前条 Indicate 强调 + 过往条压暗 0.55」两个内容运动事件——
        服务的理解：观众的视线跟着口播走，讲到哪条哪条亮、讲过的退到背景（D4 M6 契约）。
        ``sweep=True`` 追加镜尾回扫 beat（flow ≤1 圈，cue=None 由引擎兜底段播）：
        全镜读完前把已讲条目按顺序再过一遍，复盘动线。
        行→cue 绑定沿用 tag_reveal 同一把尺（_cue_key 由 _bind_motions 换算）。
        """
        if len(units) < 2:
            return
        group._reveal_motion = {
            "units": list(units), "keys": list(keys),
            "emphasis": emphasis, "color": th["hi"], "run_time": REVEAL_RUN_SEC,
            "sweep": sweep,
        }

    def _v_steps(self, p, th):
        lines = list(p.get("lines", [])[:6])
        body = VGroup(*[rich(l, 30, th["fg"]) for l in lines]).arrange(
            DOWN, aligned_edge=LEFT, buff=0.22
        )
        self._tag_progressive(body, len(lines), p.get("at"))
        # 82-SD1a：逐行淡入（B 级）升级为 reveal 三拍——当前条 Indicate、过往条压暗 0.55、
        # 镜尾回扫；行→cue 沿用 _tag_progressive 同一把尺（讲到哪步哪步亮）。
        self._mount_text_reveal(body, body, reveal_keys(p.get("at"), len(lines)), th, sweep=True)
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
        # 82-SD1a：小结每条结论逐个点亮、讲过的退到背景——回顾有动线不是成品清单（M6 契约）。
        self._mount_text_reveal(body, body, reveal_keys(p.get("at"), len(pts)), th, sweep=True)
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
        """粒子盒子：before（隔板左侧挤着）/ after（均匀占满）/ both（前后对照，中间一支箭头）。

        82-SD2b M5：三态都必须是过程动画——
          · both：前态粒子从边界成波进入；随后右盘粒子**逐颗**从前盘位置滑到新位置
            （LaggedStart 语义的错峰滑移，起点=左盘同位粒子，落点=右盘最终排布），
            观众看到的是「扩散发生」而不是两幅静图；
          · before：粒子从左侧边界成波进入左室并排布到位；
          · after：粒子从左侧半室（隔板刚抽走）成波扩开占满全室。
        粒子最终坐标仍由**原有 rng 调用顺序**的 fill() 生成（同 seed 落定形态不变；
        额外需要的「起始位」全部用几何映射，不再抽随机数）。
        """
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

        def frame():
            return Rectangle(width=W, height=H, color=th["dim"], stroke_width=3)

        def dots_of(pts):
            return VGroup(*[Dot([x, y, 0], radius=0.07, color=th["accent"]) for x, y in pts])

        def panel_pt(fr, local):
            c = fr.get_center()
            k = float(fr.width) / W
            return (float(c[0]) + k * float(local[0]), float(c[1]) + k * float(local[1]), 0.0)

        def glide(fr0, loc0, fr1, loc1, d, a, b, u_of):
            st = {"p": None}

            def _upd(m):
                f = _clamp01((_clamp01(u_of()) - a) / max(b - a, 1e-9))
                p0 = panel_pt(fr0, (loc0[0], loc0[1]))
                p1 = panel_pt(fr1, (loc1[0], loc1[1]))
                p = (p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, 0.0)
                if st["p"] is None or float(abs(p[0] - st["p"][0]) + abs(p[1] - st["p"][1])) > 1e-9:
                    st["p"] = p
                    m.move_to(p)

            d.add_updater(_upd)
            return d

        state = str(p.get("state") or "both")
        cap = {"before": str(p.get("before_label") or ""), "after": str(p.get("after_label") or "")}
        lag = 0.55
        if state == "both":
            f_left = frame()
            left_body = VGroup(f_left,
                               DashedLine([0, -H / 2, 0], [0, H / 2, 0], dash_length=0.12,
                                          color=th["warn"], stroke_width=3),
                               dots_of(fill(-W / 2, 0.0)))          # rng 顺序①：前态
            left = (VGroup(left_body, rich(cap["before"], 24, th["fg"])).arrange(DOWN, buff=0.2)
                    if cap["before"] else left_body)
            f_right = frame()
            right_body = VGroup(f_right, dots_of(fill(-W / 2, W / 2)))   # rng 顺序②：后态
            right = (VGroup(right_body, rich(cap["after"], 24, th["fg"])).arrange(DOWN, buff=0.2)
                     if cap["after"] else right_body)
            arrow = Arrow(LEFT * 0.5, RIGHT * 0.5, color=th["key"], buff=0, stroke_width=6)
            g = VGroup(left, arrow, right).arrange(RIGHT, buff=0.45)
            left_dots = [m for m in left_body.submobjects if isinstance(m, VGroup)][0]
            right_dots = [m for m in right_body.submobjects if isinstance(m, VGroup)][0]
            # 布排定稿后再量偏移（_fit 缩放由 panel_pt 每帧按框宽折算）
            l_loc = [tuple(m.get_center()[:2] - f_left.get_center()[:2]) for m in left_dots]
            r_loc = [tuple(m.get_center()[:2] - f_right.get_center()[:2]) for m in right_dots]
            tr_in = ValueTracker(0.0)
            tr_m = ValueTracker(0.0)
            for k, d in enumerate(left_dots):
                a, b = _lag_slot(k, n, lag)
                glide(f_left, (-W / 2 + 0.10, l_loc[k][1]), f_left, l_loc[k], d, a, b,
                      tr_in.get_value)
                _opacity_gate(d, tr_in.get_value, a, a + 0.10)
            for k, d in enumerate(right_dots):
                a, b = _lag_slot(k, n, lag)
                # 起点=左盘同位粒子（跨盘飞越），落点=右盘最终格位：迁移逐颗发生
                glide(f_left, l_loc[k], f_right, r_loc[k], d, a, b, tr_m.get_value)
                _opacity_gate(d, tr_m.get_value, a, a + 0.12)
            beats = []
            b = _mo.advance_to(tr_in, 1.0, cue=0,
                               note="时钟演化：前态粒子从边界成波进入左室——隔板左边挤着的是「前」")
            b.run_time = 2.6
            beats.append(b)
            b = _mo.advance_to(tr_m, 0.55, cue=1,
                               note="时钟演化：右盘粒子逐颗从前盘同位起点滑向新位置（错峰迁移=扩散过程）")
            b.run_time = 2.6
            beats.append(b)
            b = _mo.advance_to(tr_m, 1.0, cue=2,
                               note="时钟演化：后半批粒子落位，后态均匀占满——两态是同一批粒子的两种排布")
            b.run_time = 2.6
            beats.append(b)
        else:
            fr = frame()
            body = VGroup(fr)
            if state == "before":
                body.add(DashedLine([0, -H / 2, 0], [0, H / 2, 0], dash_length=0.12,
                                    color=th["warn"], stroke_width=3))
                pts = fill(-W / 2, 0.0)                              # rng 顺序：旧口径
            else:
                pts = fill(-W / 2, W / 2)
            ds = dots_of(pts)
            body.add(ds)
            g = (VGroup(body, rich(cap[state], 24, th["fg"])).arrange(DOWN, buff=0.2)
                 if cap[state] else body)
            loc = [tuple(m.get_center()[:2] - fr.get_center()[:2]) for m in ds]
            tr = ValueTracker(0.0)
            for k, d in enumerate(ds):
                a, b = _lag_slot(k, n, lag)
                if state == "before":       # 边界进入：同 y 从左侧壁滑到自己的格位
                    st_l = (-W / 2 + 0.10, loc[k][1])
                else:                       # 隔板抽走：从被压在左半室的位置扩开
                    st_l = (-W / 2 + 0.10 + (loc[k][0] + W / 2) * 0.45, loc[k][1])
                glide(fr, st_l, fr, loc[k], d, a, b, tr.get_value)
                _opacity_gate(d, tr.get_value, a, a + 0.10)
            beats = []
            for k, tgt in enumerate((1.0 / 3.0, 2.0 / 3.0, 1.0)):
                b = _mo.advance_to(
                    tr, tgt, cue=k,
                    note=("时钟演化：粒子从边界成波进入并排布到位（前态不是一张贴图）"
                          if state == "before" else
                          "时钟演化：隔板抽走后粒子成波扩开、均匀占满（后态由同一批粒子走出来）"))
                b.run_time = 2.6
                beats.append(b)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 26, th["key"])).arrange(DOWN, buff=0.25)
        _mo.mount_motion(g, beats)
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
        levels = sorted(float(e) for e in raw_levels)[:7]
        if len(levels) < 2:
            levels = [0.0, 1.0]
        temps = [float(t) for t in p.get("kT", [0.5, 1.5])][:3]
        names = list(p.get("names", []))
        n = max(4, min(int(p.get("n", 24)), 60))
        step, width = 0.5, 2.6
        # 能级纵坐标 = 能量值的线性映射：y = (E−E₀)/(Eₘₐₓ−E₀)·H（79-A 一节 energy_dist）。
        # 总高与旧版一致（最高能级仍在 (len−1)·step），只是中间能级按真实间隔落位。
        e0, emax, top = levels[0], levels[-1], (len(levels) - 1) * step

        def ylev(e):
            return (e - e0) / (emax - e0) * top if emax - e0 > 1e-9 else 0.0

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
                y = ylev(levels[li])
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
        # 行 = 左右一对（分支 0/1 同排、2/3 同排……），每排高度取这对里较高者。
        # 原先左右两列各算各的堆高、各自由 y=0 向上下铺：一列有个高分支就把整列顶偏，
        # 分支 1 会飘到分支 0 上头，视觉顺序和分镜顺序反过来（用户实报「思维导图有时画反的」）。
        heights = [max(0.8, 0.46 * len(b.get("children", []))) for b in branches]
        rows = [max(heights[r:r + 2]) for r in range(0, len(branches), 2)]
        total = sum(rows) + 0.2 * (len(rows) - 1)
        tags = []
        g = VGroup(root)
        y = total / 2
        for r, rh in enumerate(rows):
            cy = y - rh / 2
            y -= rh + 0.2
            for k in (0, 1):
                idx = r * 2 + k
                if idx >= len(branches):
                    continue
                b = branches[idx]
                sgn = 1 if k == 0 else -1
                col = (th["accent"], th["key"], th["warn"], GREEN_C)[idx % 4]
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
                tags.append((idx, grp))
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
            # 82-SD1a：表格是「一行一行读」的——行 i 揭示瞬间当前行 Indicate、上一行压暗，
            # 揭示节奏即阅读节奏（M6 契约；表头行随第一批出场，不参与压暗链）。
            self._mount_text_reveal(g, rowgroups[first:], keys, th)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    # ---------------- 物理图示原语（受力 / 场 / 电路 / 光路） ----------------
    # 画法口径全部取自 Projrct_Plan/Ref_Physics_Diagram_Standards.txt：物理图示用明文规定画，
    # 不用数学语言（角度弧线、网格坐标图）。
    def _v_force_diagram(self, p, th):
        """受力分析：真实力箭头从对象（方块/质点）中心沿方向画出，标签在箭头端，逐条揭示。

        dir 接受方向词（up/down/left/right/upleft/upright/downleft/downright）或角度度数
        （0=右、逆时针为正）。以对象中心为起点，学生看到的是"合外力从哪来、指向哪"。
        可选 mag（相对大小）：同图内箭长 ∝ mag，最大者长 L、最短 FORCE_MIN_LEN；都不给则等长。
        """
        obj = str(p.get("object") or "box")
        forces = [f for f in p.get("forces", []) if isinstance(f, dict)]
        # 81-S2 扩展入口：synthesize/decompose 走平行四边形/正交分解 builder（数据不足则落回旧受力路径，
        # 旧 props 下本分支永不触发——回归锁见 tests/test_new_kinds.py::Test81S2BehaviorLock）。
        if p.get("synthesize") and len(forces) >= 2:
            return self._f_compose_forces(p, th)
        if p.get("decompose") and len(forces) >= 1:
            return self._f_compose_forces(p, th)
        if obj == "point":
            body = VGroup(Dot([0, 0, 0], radius=0.1, color=th["key"]))
        else:
            frame = Rectangle(width=1.5, height=1.0, color=th["key"], stroke_width=4).set_fill(th["key"], 0.12)
            body = VGroup(frame)
            if p.get("label_in"):
                lab = rich(str(p["label_in"]), 30, th["fg"])
                lab.move_to(frame)
                body.add(lab)
        # 81-S2 扩展：surface=ground|wall_left|wall_right 时在物块棱边处画支承面
        # （面线 + 材料侧斜刻线 + 接触点高亮，规范§3/§6）；未给 props 时 surf=None，旧行为逐字不变。
        surf = None
        sk = str(p.get("surface") or "").strip().lower()
        if sk:
            lay = surface_layout(sk, 0.3, 0.12) if obj == "point" else surface_layout(sk)
            if lay is not None:
                sp0, sp1 = lay["p0"], lay["p1"]
                face = Line([sp0[0], sp0[1], 0], [sp1[0], sp1[1], 0], color=th["dim"], stroke_width=3)
                hatch = VGroup(*[Line(np.array(a, dtype=float), np.array(b, dtype=float),
                                      color=th["dim"], stroke_width=2)
                                 for a, b in _surface_hatch(sp0, sp1, lay["into"])])
                contact = Dot(np.array([lay["contact"][0], lay["contact"][1], 0.0]),
                              radius=0.07, color=th["hi"])
                surf = VGroup(face, hatch, contact)
        L = 1.25
        units = []
        raw = [np.array(_dir_vec(f.get("dir")), dtype=float) for f in forces]
        if any(_mag_of(f) for f in forces):
            dirs = [d / (np.linalg.norm(d) or 1.0) for d in raw]
            if obj == "point":
                lengths = _force_lengths(forces, L)
            else:   # 方块 1.5×1.0：露出边框的那段 ∝ mag
                lengths = _body_force_lengths(forces, dirs, L, 0.75, 0.5)
        else:       # 无 mag：与旧版逐字一致（斜向方向词未归一，长 L·√2）
            dirs, lengths = raw, [L] * len(forces)
        for f, d, ln in zip(forces, dirs, lengths):
            color = th.get(str(f.get("tone") or "key"), th["key"])
            arrow = Arrow([0, 0, 0], d * ln, color=color, buff=0, stroke_width=5,
                          max_tip_length_to_length_ratio=0.35)
            unit = VGroup(arrow)
            label = str(f.get("label") or f.get("name") or "")
            if label:
                lab = rich(label, 26, color)
                lab.next_to(arrow.get_end(), d, buff=0.08)
                unit.add(lab)
            units.append(unit)
        if len(units) >= 2:
            for u, key in zip(units, reveal_keys(p.get("at"), len(units))):
                tag_reveal(u, key)
        g = VGroup(body, *units)
        if surf is not None:        # 81-S2：给了 surface 才把支承面并进组；旧路径逐字不变
            g = VGroup(body, surf, *units)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _f_compose_forces(self, p, th):
        """力的合成与分解（81-S2，规范§7）：平行四边形定则 + 正交分解，与受力分析共用一把尺子。

        箭长机器 = _dir_vec + _force_lengths（规范§5 同图长度∝mag）；平行四边形对边是
        分力向量的**精确平移**（对边顶点=v1+v2，向量加法恒等），"平行且等长"由数学保证，不是手绘。
        synthesize：两分力实箭 + 平移边虚线（辅助线，非真实力）+ 对角线合力（加粗）+ 等长刻度标记
          （同数刻度=平移复制的等长边）+ 夹角 θ 写在角平分线上（不画弧：弧线是数学记号）。
        decompose：F 实箭 + 两根互相垂直的轴（淡虚线）+ 精确投影 fx=F·e1、fy=F·e2 的分量箭
          + 分量尖端到 F 尖端的虚矩边 + F 与轴夹角 θ。零分量不画零长箭、共线不画退化平行四边形、
          等大反向不画零合力——脏数据自动降级，绝不画错。
        """
        forces = [f for f in p.get("forces", []) if isinstance(f, dict)]
        O = np.zeros(3)

        def tone(f, dflt="key"):
            return th.get(str(f.get("tone") or dflt), th[dflt])

        def flabel(f, dflt=""):
            return str(f.get("label") or f.get("name") or dflt)

        def farrow(start, end, color, sw, label=""):
            a = np.array(start, dtype=float)
            b = np.array(end, dtype=float)
            ar = Arrow(a, b, color=color, buff=0, stroke_width=sw,
                       max_tip_length_to_length_ratio=0.35)
            u = VGroup(ar)
            if label:
                d = b - a
                d = d / (np.linalg.norm(d) or 1.0)
                u.add(rich(label, 26, color).next_to(b, d, buff=0.08))
            return u

        def ticks_of(mid, d, k, color):
            return VGroup(*[Line(np.array(a, dtype=float), np.array(b, dtype=float),
                                 color=color, stroke_width=2.5)
                            for a, b in _equal_ticks(mid, d, k)])

        body = VGroup(Dot(O, radius=0.08, color=th["key"]))
        L = max(0.8, min(float(p.get("L") or 1.5), 2.2))

        if p.get("synthesize"):
            cl = compose_layout(forces[0], forces[1], L)
            v1, v2, r, (l1, l2) = cl["v1"], cl["v2"], cl["result"], cl["lens"]
            d1u = v1 / max(np.linalg.norm(v1), 1e-9)
            d2u = v2 / max(np.linalg.norm(v2), 1e-9)
            col = abs(cl["cross"]) < 0.05 * l1 * l2      # |sin∠|<0.05：近似共线，平行四边形退化
            units = [farrow(O, v1, tone(forces[0]), 5, flabel(forces[0], "F₁")),
                     farrow(O, v2, tone(forces[1]), 5, flabel(forces[1], "F₂"))]
            if not col:
                aux = VGroup(
                    DashedLine(v1, r, dash_length=0.1, color=th["dim"], stroke_width=2),
                    DashedLine(v2, r, dash_length=0.1, color=th["dim"], stroke_width=2),
                    ticks_of(v1 + v2 / 2, d2u, 1, tone(forces[1])),
                    ticks_of(v2 + v1 / 2, d1u, 2, tone(forces[0])),
                    ticks_of(v2 / 2, d2u, 1, tone(forces[1])),
                    ticks_of(v1 / 2, d1u, 2, tone(forces[0])),
                )
                bis = d1u + d2u
                bn = float(np.linalg.norm(bis))
                if bn > 0.2:                              # 几乎反向：角平分线方向不可靠，θ 不画
                    aux.add(rich(str(p.get("angle_label") or "θ"), 26, th["fg"])
                            .move_to(bis / bn * (0.45 * min(l1, l2) + 0.3)))
                units.append(aux)
            if float(np.linalg.norm(r)) >= 0.15:          # 等大反向：合力为零，不画零长箭
                units.append(farrow(O, r, th["accent"], 6, str(p.get("result_label") or "合力")))
            g = VGroup(body, *units)
            if len(units) >= 2:
                for u, k in zip(units, reveal_keys(p.get("at"), len(units))):
                    tag_reveal(u, k)
            if p.get("label"):
                g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
            return g

        rl = resolve_layout(forces[0], float(p.get("axis_deg") or 0.0), L)
        v, e1, e2, fx, fy = rl["v"], rl["e1"], rl["e2"], rl["fx"], rl["fy"]
        dF = v / max(np.linalg.norm(v), 1e-9)
        axes = VGroup(*[DashedLine(-e * 0.3, e * (L + 0.35), dash_length=0.08,
                                   color=th["dim"], stroke_width=1.5) for e in (e1, e2)])
        px, py = e1 * fx, e2 * fy
        units = [farrow(O, v, tone(forces[0]), 6, flabel(forces[0], "F"))]
        comps = VGroup()
        if abs(fx) >= 0.05:
            comps.add(farrow(O, px, th["accent"], 5, str(p.get("x_label") or "F_x")))
        if abs(fy) >= 0.05:
            comps.add(farrow(O, py, th["accent"], 5, str(p.get("y_label") or "F_y")))
        if comps:
            units.append(axes)
            units.append(comps)
        if abs(fx) >= 0.05 and abs(fy) >= 0.05:
            aux = VGroup(
                DashedLine(px, v, dash_length=0.1, color=th["dim"], stroke_width=2),
                DashedLine(py, v, dash_length=0.1, color=th["dim"], stroke_width=2),
            )
            d1u = (v - py) / max(float(np.linalg.norm(v - py)), 1e-9)
            d2u = (v - px) / max(float(np.linalg.norm(v - px)), 1e-9)
            aux.add(ticks_of(py / 2, d2u, 1, th["accent"]),
                    ticks_of((px + v) / 2, d2u, 1, th["accent"]),
                    ticks_of(px / 2, d1u, 2, th["accent"]),
                    ticks_of((py + v) / 2, d1u, 2, th["accent"]))
            bis = dF + e1
            bn = float(np.linalg.norm(bis))
            if bn > 0.2 and 1.0 - float(np.dot(dF, e1)) > 0.002:   # 与轴重合：没有夹角可标
                aux.add(rich(str(p.get("angle_label") or "θ"), 26, th["fg"])
                        .move_to(bis / bn * (0.42 * L + 0.22)))
            units.append(aux)
        g = VGroup(body, *units)
        if len(units) >= 2:
            for u, k in zip(units, reveal_keys(p.get("at"), len(units))):
                tag_reveal(u, k)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _v_field(self, p, th):
        """场图示：region（垂直纸面向里×/向外·）、wire（通电导线截面+安培定则环绕磁感线）、
        magnet（条形磁铁 N→S 闭合磁感线）；81-S1 新增电场/螺线管/小磁针 mode：
        efield_point / efield_pair / efield_plate / solenoid / compass（缺 mode 仍是 region，旧行为）。"""
        mode = str(p.get("mode") or "region")
        if mode == "wire":
            return self._f_field_wire(p, th)
        if mode == "magnet":
            return self._f_field_magnet(p, th)
        if mode == "efield_point":
            return self._f_field_efield_point(p, th)
        if mode == "efield_pair":
            return self._f_field_efield_pair(p, th)
        if mode == "efield_plate":
            return self._f_field_efield_plate(p, th)
        if mode == "solenoid":
            return self._f_field_solenoid(p, th)
        if mode == "compass":
            return self._f_field_compass(p, th)
        return self._f_field_region(p, th)

    def _f_field_region(self, p, th):
        """垂直纸面方向的均匀场：一屏（或左右各半屏）的 ×（纸面向里）/ ·（纸面向外）。

        82-SD2a1：×/· 不再整块贴出——从 props.origin（缺省版面中心）按到源距离成波铺开，
        每个 mark 的透明度+缩放由 tracker 逐帧现算；波前到齐后图注才出现（六律④→⑤）。
        真实场是充满空间的，所以波「铺满全屏」本身就是场建立的语义。
        """
        sym = str(p.get("symbols") or "cross")
        org = p.get("origin")
        try:
            ox, oy = float(org[0]), float(org[1])
        except (TypeError, ValueError, IndexError, KeyError):
            ox = oy = 0.0
        tr = ValueTracker(0.0)

        def panel(kind):
            cells = [((c - 2) * 0.66, (1.5 - r) * 0.66) for r in range(4) for c in range(5)]
            dist = [math.hypot(x - ox, y - oy) for x, y in cells]
            dmax = max(dist) or 1.0
            marks = VGroup()
            for (x, y), d in zip(cells, dist):
                mk = (T("×", font_size=36, color=th["warn"]).move_to([x, y, 0]) if kind == "cross"
                      else Dot([x, y, 0], radius=0.09, color=th["accent"]))
                _wave_reveal(mk, tr.get_value, d / dmax)
                marks.add(mk)
            box = Rectangle(width=marks.width + 0.8, height=marks.height + 0.8,
                            color=th["dim"], stroke_width=2)
            return VGroup(box, marks)

        if sym == "both":
            g = VGroup(panel("cross"), panel("dot")).arrange(RIGHT, buff=1.0)
        else:
            g = panel("cross" if sym == "cross" else "dot")
        cap = {"cross": "垂直纸面向里 ×", "dot": "垂直纸面向外 ·",
               "both": "左：纸面向里 ×　　右：纸面向外 ·"}.get(sym, "")
        cap_tr = ValueTracker(0.0)
        if cap:
            cap_obj = rich(cap, 24, th["fg"])
            _opacity_gate(cap_obj, cap_tr.get_value, 0.0, 1.0)
            g = VGroup(g, cap_obj).arrange(DOWN, buff=0.25)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(tr, 1.0, cue=0,
                            note="时钟演化：×/· 由源区按到源距离成波铺开——场是从中心一圈圈铺满全屏的")
        b0.run_time = 1.8
        beats.append(b0)
        if cap:
            b1 = _mo.advance_to(cap_tr, 1.0, cue=1,
                                note="揭示图注：波前到齐后点名 —— × 表示场垂直纸面向里、· 表示向外")
            b1.run_time = 0.7
            beats.append(b1)
        g._field_tracker = tr
        _mo.mount_motion(g, beats)
        return g

    def _f_field_wire(self, p, th):
        """通电直导线截面：圆心标电流 ×（进纸面）/ ·（出纸面），同心圆是磁感线，
        半径按几何级数排布（B∝1/r，越靠导线越密，wire_field_layout），切向小箭头按
        安培定则示环绕方向（出=逆时针、进=顺时针，规范§17）。

        82-SD2a1：导线截面+电流符号先可见；磁感线由内向外逐圈显现、切向箭头随圈出现；
        收尾用一条 tracker 调 stroke_opacity 的移动高亮带沿磁感线绕行一周——观众看到的是
        「磁场从导线向外建立、再沿圈环绕」的过程，而不是一张贴好的同心圆图。
        """
        lay = wire_field_layout(str(p.get("current") or "out"))
        into = not lay["ccw"]
        conductor = Circle(radius=0.32, color=th["key"], stroke_width=4).set_fill(th["key"], 0.25)
        cur = T("×" if into else "·", font_size=40,
                color=th["warn"] if into else th["accent"]).move_to([0, 0, 0])
        g = VGroup(conductor, cur)
        tr = ValueTracker(0.0)
        radii = lay["radii"]
        n_r = max(len(radii) - 1, 1)
        for k, r in enumerate(radii):
            ring = Circle(radius=r, color=th["dim"], stroke_width=2)
            _wave_reveal(ring, tr.get_value, k / n_r, ramp=0.34, scale_from=0.82, stroke_only=True)
            g.add(ring)
        for a in lay["arrows"]:
            pos = np.array([a["pos"][0], a["pos"][1], 0.0])
            t = np.array([a["tangent"][0], a["tangent"][1], 0.0])
            arr = Arrow(pos - t * 0.28, pos + t * 0.28, color=th["warn"], buff=0, stroke_width=5)
            k = min(range(len(radii)), key=lambda j: abs(radii[j] - a["r"]))
            q = min(1.0, (k + 0.35) / n_r)
            _wave_reveal(arr, tr.get_value, q, ramp=0.30, scale_from=0.6)
            g.add(arr)
        # 方向游走高亮带：位置每帧由已变换的导线截面现算（_fit 缩放后仍贴着截面）。
        flow = ValueTracker(0.0)
        r_band = radii[len(radii) // 2]
        turn = 1.0 if lay["ccw"] else -1.0

        def band_build():
            v = _clamp01(flow.get_value())
            c = conductor.get_center()
            s = max(float(conductor.width), 1e-9) / 0.64
            a0 = -math.pi / 2.0 + turn * 2.0 * math.pi * v
            env = 0.0 if (v <= 1e-9 or v >= 1.0 - 1e-9) else min(1.0, v * 6.0, (1.0 - v) * 6.0)
            arc = Arc(radius=r_band * s, start_angle=a0, angle=0.95, num_components=24,
                      arc_center=c)
            arc.set_stroke(th["hi"], 6, opacity=0.95 * env)
            return arc

        band = _rebuild_on_change(VMobject(), flow.get_value, band_build)
        g.add(band)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(tr, 1.0, cue=0,
                            note="时钟演化：磁感线由内向外逐圈显现、切向箭头随圈出现——越靠近导线越密（B∝1/r）")
        b0.run_time = 2.2
        beats.append(b0)
        b1 = _mo.advance_to(flow, 1.0, cue=1,
                            note="时钟演化：高亮带沿磁感线绕行一周——出纸面电流(out)的磁场逆时针环绕（安培定则手性）")
        b1.run_time = 1.8
        beats.append(b1)
        beats.append(_mo.MotionBeat(
            [Indicate(cur, scale_factor=1.25, color=th["hi"])], run_time=FX_MAX_SEC, cue=2,
            note="落定强调：点名电流符号 ×/·——它的进出决定磁感线环绕手性（安培定则）"))
        g._field_tracker = tr
        g._field_flow = flow
        _mo.mount_motion(g, beats)
        return g

    MAGNET_HX, MAGNET_HH = 1.2, 0.45
    # N 极面上的种子（占半高的比例）：上半 4 条，下半镜像 4 条，外加轴向直线。
    # 种子在端面上等距，外部线自然"近极密、远处疏"（规范§4 疏密示强弱）。
    MAGNET_SEEDS = (0.62, 0.74, 0.86, 0.95)

    def _f_field_magnet(self, p, th):
        """条形磁铁（左 S 右 N）磁感线：两端面均布磁荷解析场 + RK4 流线追踪（magnet_field_line）。

        外部线从 N 极面多点发出、绕回 S 极面同高处，内部沿 S→N 平行直线回到起点——每条闭合、
        互不相交、不穿磁铁本体；含轴向直线；每条外部线在顶点处有 N→S 箭头，内部轴线箭头 S→N。
        依据：规范§0 磁场行、§4、§19。

        82-SD2a1：磁铁本体先可见；外部磁感线按种子顺序逐条「描出」（前缀点列每帧按磁铁本体
        当前几何重算），顶点箭头随线到顶出现；内部 S→N 线随后出现，图注最后点名——外部 N→S、
        内部 S→N 的闭合回路是被演出来的。
        """
        hx, hh = self.MAGNET_HX, self.MAGNET_HH
        line_c, inner_c = th["accent"], WHITE
        bar = VGroup(
            Rectangle(width=hx, height=2 * hh, color=th["dim"]).set_fill(th["dim"], 0.85).move_to(LEFT * hx / 2),
            Rectangle(width=hx, height=2 * hh, color=th["warn"]).set_fill(th["warn"], 0.85).move_to(RIGHT * hx / 2),
        )
        tr_out = ValueTracker(0.0)
        tr_in = ValueTracker(0.0)
        tr_cap = ValueTracker(0.0)

        def ref():
            """磁铁本体已被 _fit 变换：描线每帧从这里读中心与尺度（不存装配期坐标）。"""
            c = bar.get_center()
            return float(c[0]), float(c[1]), max(float(bar.width), 1e-9) / (2.0 * hx)

        inner = VGroup()
        outer = VGroup()
        arrows = VGroup()
        models = []
        for s in self.MAGNET_SEEDS:
            pts = magnet_field_line(s * hh, hx, hh)
            apex_i = len(pts) // 2
            for sg in (1, -1):
                model = [(float(x), float(sg * y)) for x, y in pts]
                models.append(model)
                ln = VMobject(color=line_c, stroke_width=2.5)
                ln.set_points_as_corners([[x, y, 0] for x, y in model])
                outer.add(ln)
                ay = sg * pts[apex_i][1]
                arrows.add(Arrow([0.22, ay, 0], [-0.22, ay, 0], color=th["warn"], buff=0, stroke_width=4,
                                 max_tip_length_to_length_ratio=0.6))
                inner.add(Line([-hx, sg * s * hh, 0], [hx, sg * s * hh, 0], color=inner_c,
                               stroke_width=1.5, stroke_opacity=0.75))
        # 轴向直线：N 面沿轴向右出去、从左侧沿轴进入 S 面（无穷远闭合），各带一个 N→S 外部方向箭头。
        ax_len = 1.3
        for q0, q1 in (([hx, 0, 0], [hx + ax_len, 0, 0]), ([-hx - ax_len, 0, 0], [-hx, 0, 0])):
            outer.add(Line(q0, q1, color=line_c, stroke_width=2.5))
            models.append([(float(q0[0]), float(q0[1])), (float(q1[0]), float(q1[1]))])
        for x in (hx + ax_len * 0.55, -hx - ax_len * 0.45):
            arrows.add(Arrow([x - 0.22, 0, 0], [x + 0.22, 0, 0], color=th["warn"], buff=0, stroke_width=4,
                             max_tip_length_to_length_ratio=0.6))
        # 内部：轴线中段画 S→N 箭头（S/N 字母让到两侧，不压线）。
        inner.add(Arrow([-0.55, 0, 0], [0.55, 0, 0], color=inner_c, buff=0, stroke_width=4,
                        max_tip_length_to_length_ratio=0.3))
        # 外部线：按种子顺序逐条描出；箭头在线爬到顶点（弧长中段）时随线显现。
        n_out = len(outer)

        def slot(i, n):
            return 0.94 * i / n, min(1.0, 0.94 * (i + 1) / n + 0.06)

        for i, ln in enumerate(outer):
            f0, f1 = slot(i, n_out)
            _draw_on(ln, tr_out.get_value, f0, f1, models[i], ref, line_c, 2.5)
            if i < len(arrows):
                _opacity_gate(arrows[i], tr_out.get_value,
                              f0 + 0.44 * (f1 - f0), f0 + 0.62 * (f1 - f0))
        # 内部 S→N：外部线讲完后再出现；轴线箭头最后长出。
        n_in = len(inner)
        for i, m in enumerate(inner):
            q0 = 0.62 * i / max(n_in - 1, 1)
            _opacity_gate(m, tr_in.get_value, q0, min(1.0, q0 + 0.38),
                          base=1.0 if i == n_in - 1 else 0.75,
                          stroke_only=i != n_in - 1)
        poles = VGroup(T("S", font_size=28, color=WHITE).move_to([-hx + 0.3, 0, 0]),
                       T("N", font_size=28, color=WHITE).move_to([hx - 0.3, 0, 0]))
        g = VGroup(outer, bar, inner, poles, arrows)
        cap_obj = rich("外部 N→S，内部 S→N", 22, th["fg"])
        _opacity_gate(cap_obj, tr_cap.get_value, 0.0, 1.0)
        g = VGroup(g, cap_obj).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(tr_out, 1.0, cue=0,
                            note="时钟演化：外部磁感线从 N 极面按种子顺序逐条描出、绕回 S 极——外部 N→S")
        b0.run_time = 2.4
        beats.append(b0)
        b1 = _mo.advance_to(tr_in, 1.0, cue=1,
                            note="时钟演化：内部磁感线随后出现，由 S 极回到 N 极——磁感线闭合，内部 S→N")
        b1.run_time = 1.3
        beats.append(b1)
        b2 = _mo.advance_to(tr_cap, 1.0, cue=2,
                            note="揭示图注：外部 N→S、内部 S→N——磁感线在磁铁内外闭合成回路、永不中断")
        b2.run_time = 0.7
        beats.append(b2)
        g._field_tracker = tr_out
        _mo.mount_motion(g, beats)
        return g

    def _f_arrow(self, a, th, half=0.22, sw=4):
        """按布局箭头 {"pos","d"} 画一支小方向箭头（场线/电流共用）。"""
        px, py = a["pos"]
        dx, dy = a["d"]
        return Arrow([px - dx * half, py - dy * half, 0], [px + dx * half, py + dy * half, 0],
                     color=th["warn"], buff=0, stroke_width=sw,
                     max_tip_length_to_length_ratio=0.5)

    def _f_field_efield_point(self, p, th):
        """点电荷电场线（规范§20）：spokes 条辐射线，正电荷箭头朝外、负电荷朝内；
        线只从 r0 画到 r1，不到电荷中心（不断裂、不相交，交点只在电荷处与电荷重合）。

        82-SD2a2：电荷圆盘先由中心长出（正负号常显作为场源骨架），随后 spokes 按极角顺序
        从 r0 向 r1 逐条「描出」、箭头随线落位；第二拍用一条沿径向走的高亮带把「正电荷向外 / 负电荷
        向内」再演一趟（只走一次）；图注最后淡入。全部 beats 只借既有 hold 帧。
        """
        lay = efield_point_layout(str(p.get("charge") or "pos"), int(p.get("spokes", 8)))
        pos_c = th["warn"] if lay["sgn"] > 0 else th["accent"]
        charge = Circle(radius=0.24, color=pos_c, stroke_width=4).set_fill(pos_c, 0.9)
        glyph = T("+" if lay["sgn"] > 0 else "−", font_size=34, color=WHITE).move_to([0, 0, 0])
        tr_ch = ValueTracker(0.0)
        tr_lines = ValueTracker(0.0)
        tr_flash = ValueTracker(0.0)
        tr_cap = ValueTracker(0.0)
        # 正负号常显（场源骨架）；圆盘用 _wave_reveal 由小长大，不走 play 动画——
        # 动画会挂起对象 updater，gate 的透明度在动画结束时可能停在 0（首轮冒烟电荷消失）。
        _wave_reveal(charge, tr_ch.get_value, 0.0, ramp=0.30, scale_from=0.05)

        def ref():
            """电荷已被 _fit 变换：描线每帧从电荷当前中心/直径换算模型坐标。"""
            c = charge.get_center()
            return float(c[0]), float(c[1]), max(float(charge.width), 1e-9) / 0.48

        lines = VGroup()
        arrows = VGroup()
        n = max(len(lay["lines"]), 1)
        for k, ln in enumerate(lay["lines"]):
            x0, y0 = ln["p0"]
            x1, y1 = ln["p1"]
            mob = VMobject(color=th["dim"], stroke_width=2.5)
            mob.set_points_as_corners([[x0, y0, 0], [x1, y1, 0]])
            f0, f1 = _seq_slot(k, n, span=0.92)
            head = _draw_with_head(mob, tr_lines.get_value, f0, f1,
                                   [(x0, y0), (x1, y1)], ref, th["dim"], 2.5,
                                   head_color=th["hi"], head_radius=0.07)
            arr = self._f_arrow(ln["arrow"], th)
            _opacity_gate(arr, tr_lines.get_value, f0 + 0.55 * (f1 - f0), f1)
            lines.add(mob)
            lines.add(head)
            arrows.add(arr)
        # 方向高亮带：沿每条 spokes 的径向位置同步推进；正电荷由内向外、负电荷由外向内。
        # 位置每帧由已变换的电荷现算（与 _draw_on 同一 ref），_fit 后仍贴着线。
        flash = VGroup()
        for _ in lay["lines"]:
            fl = Line([0, 0, 0], [0.1, 0, 0], color=th["hi"], stroke_width=7)
            fl.set_stroke(opacity=0.0)
            flash.add(fl)

        def _flash_upd(_m):
            u = _clamp01(tr_flash.get_value())
            env = 0.0 if (u <= 1e-9 or u >= 1.0 - 1e-9) else min(1.0, u * 8.0, (1.0 - u) * 8.0)
            v = u if lay["sgn"] > 0 else 1.0 - u
            cx, cy, s = ref()
            for ln, fl in zip(lay["lines"], flash):
                x0, y0 = ln["p0"]
                x1, y1 = ln["p1"]
                va, vb = v, min(1.0, v + 0.12)
                fl.put_start_and_end_on(
                    [cx + s * (x0 + (x1 - x0) * va), cy + s * (y0 + (y1 - y0) * va), 0],
                    [cx + s * (x0 + (x1 - x0) * vb), cy + s * (y0 + (y1 - y0) * vb), 0])
                fl.set_stroke(th["hi"], 7, opacity=0.9 * env)

        flash.add_updater(_flash_upd)
        cap = "正电荷：电场线向外" if lay["sgn"] > 0 else "负电荷：电场线向内"
        cap_obj = rich(cap, 22, th["fg"])
        _opacity_gate(cap_obj, tr_cap.get_value, 0.0, 1.0)
        g = VGroup(lines, charge, glyph, arrows, flash)
        g = VGroup(g, cap_obj).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(
            tr_ch, 1.0, cue=0,
            note="时钟演化：电荷圆盘先从中心长出（正负号常显作为场源骨架）——场源先立住，后面的场线才有出处")
        b0.run_time = 1.2
        beats.append(b0)
        b1 = _mo.advance_to(
            tr_lines, 1.0, cue=0,
            note="时钟演化：电场线按极角顺序从 r0 向 r1 逐条描出，箭头随线落位——正电荷向外、负电荷向内")
        b1.run_time = 2.0
        beats.append(b1)
        b2 = _mo.advance_to(
            tr_flash, 1.0, cue=1,
            note="方向强调：一条高亮带沿所有 spokes 径向走一趟——把「正电荷向外、负电荷向内」再演一次，只走一次")
        b2.run_time = 2.7
        beats.append(b2)
        b3 = _mo.advance_to(
            tr_cap, 1.0, cue=2,
            extra=[Indicate(VGroup(lines, charge, glyph, arrows), scale_factor=1.06, color=th["hi"])],
            note="揭示图注 + 落定点名：电场线由正电荷发出、向负电荷会入，方向由电荷正负决定")
        b3.run_time = 1.8
        beats.append(b3)
        g._field_tracker = tr_lines
        _mo.mount_motion(g, beats)
        return g

    def _f_field_efield_pair(self, p, th):
        """等量异号点电荷电场线（efield_pair_line 解析场流线，镜像构造保证从 +q 出发、
        终止 −q、上下对称嵌套不相交；中线箭头 +x=正→负，规范§20）。含轴线与两外侧半线。

        82-SD2a2：两个电荷先长出；流线从 +q 一侧向 −q 成对描出（左右镜面同步、按 phi
        由内到外 lag），箭头在流线顶点随线落位；轴线与两外侧半线最后描出，再沿轴线走一趟
        正→负的高亮带；图注最后淡入。
        """
        d, r0 = EFIELD_D, EFIELD_R0
        pos_c, neg_c = th["warn"], th["accent"]
        charges = VGroup(
            Circle(radius=0.2, color=pos_c, stroke_width=4).set_fill(pos_c, 0.9).move_to([-d, 0, 0]),
            Circle(radius=0.2, color=neg_c, stroke_width=4).set_fill(neg_c, 0.9).move_to([d, 0, 0]),
            T("+", font_size=30, color=WHITE).move_to([-d, 0, 0]),
            T("−", font_size=30, color=WHITE).move_to([d, 0, 0]),
        )
        tr_ch = ValueTracker(0.0)
        tr_lines = ValueTracker(0.0)
        tr_axis = ValueTracker(0.0)
        tr_cap = ValueTracker(0.0)
        # 正负号常显（两电荷的骨架/极性先立住）；圆盘用 _wave_reveal 长大（动画会挂起 updater）。
        for m in charges[:2]:
            _wave_reveal(m, tr_ch.get_value, 0.0, ramp=0.30, scale_from=0.05)

        def ref():
            """模型原点 ↔ 两电荷中点：用 +q 圆的当前中心/直径换算（_fit 后仍贴着电荷）。"""
            c = charges[0].get_center()
            s = max(float(charges[0].width), 1e-9) / 0.40
            return float(c[0] + d * s), float(c[1]), s

        lines = VGroup()
        arrows = VGroup()
        n = max(len(EFIELD_PAIR_SEEDS), 1)
        for j, phi in enumerate(EFIELD_PAIR_SEEDS):
            pts = efield_pair_line(phi, d, r0)
            apex_i = len(pts) // 2
            f0, f1 = _seq_slot(j, n, span=0.80)
            for sg in (1, -1):
                model = [(float(x), float(sg * y)) for x, y in pts]
                ln = VMobject(color=th["dim"], stroke_width=2.5)
                ln.set_points_as_corners([[x, y, 0] for x, y in model])
                head = _draw_with_head(ln, tr_lines.get_value, f0, f1, model, ref,
                                       th["dim"], 2.5, head_color=th["hi"], head_radius=0.07)
                lines.add(ln)
                lines.add(head)
                arr = self._f_arrow({"pos": (0.0, sg * pts[apex_i][1]), "d": (1.0, 0.0)}, th)
                _opacity_gate(arr, tr_lines.get_value, f0 + 0.50 * (f1 - f0), f1)
                arrows.add(arr)
        # 轴线 + 两外侧半线最后描出：轴线从 +q 指向 −q（+x），外侧半线的箭头都 −x。
        ax_len = 0.9
        axis_specs = [
            ([(-d + r0, 0.0), (d - r0, 0.0)],
             {"pos": (0.0, 0.0), "d": (1.0, 0.0)}, 0.00, 0.62),
            ([(-d - r0, 0.0), (-d - ax_len, 0.0)],
             {"pos": (-d - 0.5 * (r0 + ax_len), 0.0), "d": (-1.0, 0.0)}, 0.66, 0.80),
            ([(d + ax_len, 0.0), (d + r0, 0.0)],
             {"pos": (d + 0.5 * (r0 + ax_len), 0.0), "d": (-1.0, 0.0)}, 0.84, 1.00),
        ]
        for model, arrow_spec, f0, f1 in axis_specs:
            ln = VMobject(color=th["dim"], stroke_width=2.5)
            ln.set_points_as_corners([[x, y, 0] for x, y in model])
            head = _draw_with_head(ln, tr_axis.get_value, f0, f1, model, ref,
                                   th["dim"], 2.5, head_color=th["hi"], head_radius=0.07)
            lines.add(ln)
            lines.add(head)
            arr = self._f_arrow(arrow_spec, th)
            _opacity_gate(arr, tr_axis.get_value, f0 + 0.45 * (f1 - f0), f1)
            arrows.add(arr)
        # 轴线高亮带（只走一趟）：加粗亮斑从 +q 走到 −q；位置每帧按电荷现算。
        tr_flow = ValueTracker(0.0)
        flow_head = Dot([0.0, 0.0, 0.0], radius=0.105, color=th["hi"])

        def _flow_upd(m):
            u = _clamp01(tr_flow.get_value())
            env = 0.0 if (u <= 1e-9 or u >= 1.0 - 1e-9) else min(1.0, u * 8.0, (1.0 - u) * 8.0)
            cx, cy, s = ref()
            m.move_to([cx + s * (-d + r0 + (2.0 * d - 2.0 * r0) * u), cy, 0.0])
            m.set_opacity(0.95 * env)

        flow_head.set_opacity(0.0)
        flow_head.add_updater(_flow_upd)
        cap_obj = rich("电场线从 + 出发、终止于 −，不相交、不断裂", 22, th["fg"])
        _opacity_gate(cap_obj, tr_cap.get_value, 0.0, 1.0)
        g = VGroup(lines, charges, arrows, flow_head)
        g = VGroup(g, cap_obj).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(
            tr_ch, 1.0, cue=0,
            note="时钟演化：两个电荷圆盘先长出（正负号常显）——正电荷在左、负电荷在右，场线才有两端可落")
        b0.run_time = 1.2
        beats.append(b0)
        b1 = _mo.advance_to(
            tr_lines, 1.0, cue=0,
            note="时钟演化：上下镜像成对、按 phi 由内到外逐条描出——流线从 +q 出发、终止于 −q，顶点箭头随之落位")
        b1.run_time = 1.9
        beats.append(b1)
        b2 = _mo.advance_to(
            tr_axis, 1.0, cue=1,
            note="时钟演化：轴线与两外侧半线最后描出——轴线 +x 由正指向负，外侧半线箭头 −x")
        b2.run_time = 1.2
        beats.append(b2)
        b3 = _mo.advance_to(
            tr_flow, 1.0, cue=1,
            note="方向强调：高亮带沿轴线从 +q 走到 −q 一趟——场线方向正→负，只走一次")
        b3.run_time = 1.5
        beats.append(b3)
        b4 = _mo.advance_to(
            tr_cap, 1.0, cue=2,
            extra=[Indicate(VGroup(lines, charges, arrows), scale_factor=1.05, color=th["hi"])],
            note="揭示图注 + 落定点名：电场线从 + 出发、终止于 −，不相交、不断裂——闭合的是磁感线，电场线有始有终")
        b4.run_time = 1.8
        beats.append(b4)
        g._field_tracker = tr_lines
        _mo.mount_motion(g, beats)
        return g

    def _f_field_efield_plate(self, p, th):
        """平行板电容器：板间匀强场=平行等距带箭头直线，边缘 fringe 略弯外凸（规范§20
        「匀强电场画平行等距箭头」；efield_plate_layout 正弦隆起，顶点越过板缘）。左 + 右 −。

        82-SD2a2：两块极板先自上而下 Create 语义逐帧描出（极性符号常显），板间匀强场线
        从左板向右板逐条描出、箭头随线落位，fringe 线最后描出；末拍一条竖直高亮带从正板
        扫到负板（只扫一次），把「匀强场方向 +x」再演一遍，图注随扫描淡入。
        """
        lay = efield_plate_layout()
        g_half = lay["gap"] / 2
        h = lay["h"]
        tr_pl = ValueTracker(0.0)
        tr_uni = ValueTracker(0.0)
        tr_fr = ValueTracker(0.0)
        tr_flash = ValueTracker(0.0)
        plate_l = Line([-g_half, h / 2, 0], [-g_half, -h / 2, 0],
                       color=th["warn"], stroke_width=9)
        plate_r = Line([g_half, h / 2, 0], [g_half, -h / 2, 0],
                       color=th["accent"], stroke_width=9)
        lab_p = T("+", font_size=30, color=th["warn"]).move_to([-g_half - 0.3, h / 2 + 0.2, 0])
        lab_m = T("−", font_size=30, color=th["accent"]).move_to([g_half + 0.3, h / 2 + 0.2, 0])
        # 极性符号常显（先立极性与左右，板体随后逐帧描出）——也是装配层标签复核的锚点。
        plates = VGroup(plate_l, plate_r, lab_p, lab_m)
        # 不参与动画的静态尺：左板原位。不能用 plate_l 本身——它正被 _draw_on 逐帧改点，
        # 用它会越画越短，ref 跟着缩（首轮冒烟板间线整体缩进板内）。
        plate_anchor = Line([-g_half, h / 2, 0], [-g_half, -h / 2, 0], stroke_opacity=0)
        plates.add(plate_anchor)

        def ref():
            """模型坐标 → 已变换的板面坐标：以静态锚点中心/高度为尺（_fit 后仍贴着极板）。"""
            c = plate_anchor.get_center()
            s = max(float(plate_anchor.height), 1e-9) / h
            return float(c[0] + g_half * s), float(c[1]), s

        # 极板用 Create 语义（按弧长前缀逐帧描出、亮笔头随行）：自上而下，先左后右小幅错峰。
        plates.add(
            _draw_with_head(plate_l, tr_pl.get_value, 0.0, 0.78,
                            [(-g_half, h / 2), (-g_half, -h / 2)], ref,
                            th["warn"], 9, head_color=th["hi"], head_radius=0.1),
            _draw_with_head(plate_r, tr_pl.get_value, 0.25, 1.0,
                            [(g_half, h / 2), (g_half, -h / 2)], ref,
                            th["accent"], 9, head_color=th["hi"], head_radius=0.1),
        )
        lines = VGroup()
        arrows = VGroup()
        n_u = max(len(lay["uniform"]), 1)
        for i, u in enumerate(lay["uniform"]):
            model = [tuple(u["p"]), tuple(u["q"])]
            ln = VMobject(color=th["dim"], stroke_width=2.5)
            ln.set_points_as_corners([[x, y, 0] for x, y in model])
            f0, f1 = _seq_slot(i, n_u, span=0.90)
            head = _draw_with_head(ln, tr_uni.get_value, f0, f1, model, ref,
                                   th["dim"], 2.5, head_color=th["hi"], head_radius=0.07)
            lines.add(ln)
            lines.add(head)
            arr = self._f_arrow(u["arrow"], th, half=0.2)
            _opacity_gate(arr, tr_uni.get_value, f0 + 0.50 * (f1 - f0), f1)
            arrows.add(arr)
        n_f = max(len(lay["fringe"]), 1)
        for i, fr in enumerate(lay["fringe"]):
            model = [tuple(pt) for pt in fr["pts"]]
            ln = VMobject(color=th["dim"], stroke_width=2.5)
            ln.set_points_as_corners([[x, y, 0] for x, y in model])
            f0, f1 = _seq_slot(i, n_f, span=0.88)
            head = _draw_with_head(ln, tr_fr.get_value, f0, f1, model, ref,
                                   th["dim"], 2.5, head_color=th["hi"], head_radius=0.07)
            lines.add(ln)
            lines.add(head)
            arr = self._f_arrow(fr["arrow"], th, half=0.2)
            _opacity_gate(arr, tr_fr.get_value, f0 + 0.42 * (f1 - f0), f1)
            arrows.add(arr)
        # 板间向右的扫描带：竖直高亮线先从正板走到负板（单趟），位置每帧按板面现算。
        band = Line([0, 0, 0], [0, 1, 0], color=th["hi"], stroke_width=9)
        band.set_stroke(opacity=0.0)

        def _band_upd(m):
            u = _clamp01(tr_flash.get_value())
            env = 0.0 if (u <= 1e-9 or u >= 1.0 - 1e-9) else min(1.0, u * 8.0, (1.0 - u) * 8.0)
            cx, cy, s = ref()
            x = -g_half + (2.0 * g_half) * u
            m.put_start_and_end_on(
                [cx + s * x, cy + s * (-h / 2 + 0.12), 0],
                [cx + s * x, cy + s * (h / 2 - 0.12), 0])
            m.set_stroke(th["hi"], 9, opacity=0.85 * env)

        band.add_updater(_band_upd)
        cap_obj = rich("板间平行等距=匀强场；边缘略弯（fringe）", 22, th["fg"])
        _opacity_gate(cap_obj, tr_flash.get_value, 0.10, 0.70)
        g = VGroup(lines, plates, arrows, band)
        g = VGroup(g, cap_obj).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(
            tr_pl, 1.0, cue=0,
            note="时钟演化：两块极板自上而下 Create 语义逐帧描出（亮笔头随行），正负符号先立住——先有板，才有板间场")
        b0.run_time = 1.2
        beats.append(b0)
        b1 = _mo.advance_to(
            tr_uni, 1.0, cue=0,
            note="时钟演化：板间匀强场线从左板向右板逐条描出、箭头随线落位——平行等距即匀强")
        b1.run_time = 1.85
        beats.append(b1)
        b2 = _mo.advance_to(
            tr_fr, 1.0, cue=1,
            note="时钟演化：边缘 fringe 线最后描出，两端贴板、顶点越过板缘——边缘场不再平行")
        b2.run_time = 1.9
        beats.append(b2)
        b3 = _mo.advance_to(
            tr_flash, 1.0, cue=2,
            note="方向强调 + 揭示图注：一条高亮带从正板扫到负板一趟——板间场方向 +x；fringe 略弯")
        b3.run_time = 1.85
        beats.append(b3)
        g._field_tracker = tr_uni
        _mo.mount_motion(g, beats)
        return g

    def _f_field_solenoid(self, p, th):
        """通电螺线管（规范§18）：绕线杆+顶底半圆成线圈，前侧电流箭头与绕向一致；
        外部磁感线复用 magnet_field_line（极面磁荷解析场流线，闭合、N→S），内部 3 条
        平行等距 S→N（近匀强），两端标 N/S。安培定则：电流前侧向上 ⇒ N 在 −x 端。

        82-SD2a2：三段式过程——(1) 线圈逐匝 Create（杆→上弧→下弧按绕向顺序），前侧电流
        箭头随匝出现；(2) 内部 3 条 S→N 平行线渐显；(3) 外部闭合磁感线按种子顺序逐条描出，
        最后点名 N/S 与图注。全部 beats 只借既有 hold 帧。
        """
        lay = solenoid_layout(int(p.get("turns", SOLENOID_TURNS)),
                              str(p.get("wind") or "up_front"))
        hx, hh, ns = lay["hx"], lay["hh"], lay["ns"]
        bars = VGroup()
        arcs = VGroup()
        cur_arrows = VGroup()
        coil_seq = []
        coil_models = []
        coil_widths = []
        for k, b in enumerate(lay["bars"]):
            x = b["x"]
            dy = b["dir"][1]
            bar = Line([x, -hh, 0], [x, hh, 0], color=th["key"], stroke_width=4)
            bars.add(bar)
            coil_seq.append(bar)
            coil_models.append([(float(x), -hh), (float(x), hh)])
            coil_widths.append(4.0)
            cur_arrows.add(self._f_arrow({"pos": (x, 0.0), "d": (0.0, dy)}, th, half=0.2, sw=4))
            if k + 1 < len(lay["bars"]):
                x2 = lay["bars"][k + 1]["x"]
                top = ArcBetweenPoints([x, hh, 0], [x2, hh, 0], angle=0.5,
                                       color=th["key"], stroke_width=3)
                bot = ArcBetweenPoints([x, -hh, 0], [x2, -hh, 0], angle=-0.5,
                                       color=th["key"], stroke_width=3)
                arcs.add(top, bot)
                # Create 等价：按弧长采样成折线，逐帧只画前缀——笔头才能贴着弧走。
                for arc in (top, bot):
                    coil_models.append([tuple(arc.point_from_proportion(t)[:2])
                                        for t in np.linspace(0.0, 1.0, 18)])
                    coil_widths.append(3.0)
                coil_seq.extend([top, bot])
        tr_coil = ValueTracker(0.0)
        n_coil = max(len(coil_seq), 1)

        def ref():
            """模型坐标 → 已变换的线圈坐标：用第一支电流箭头（只调透明度、几何永不变）
            作静态尺，不能用正被 _draw_on 逐帧 become 的绕线杆——杆会越画越短，尺就缩了。"""
            c = cur_arrows[0].get_center()
            s = max(float(cur_arrows[0].height), 1e-9) / 0.4
            return float(c[0] - lay["bars"][0]["x"] * s), float(c[1]), s

        for i, m in enumerate(coil_seq):
            f0, f1 = _seq_slot(i, n_coil, span=0.94)
            head = _draw_with_head(m, tr_coil.get_value, f0, f1, coil_models[i], ref,
                                   th["key"], coil_widths[i],
                                   head_color=th["hi"], head_radius=0.065)
            if i % 3 == 0:
                # 杆与弧的笔头都放进对应的线圈组，随组一起 _fit / 退场。
                (bars if i < len(bars) else arcs).add(head)
            else:
                arcs.add(head)
        for i, arr in enumerate(cur_arrows):
            # 杆 i 在 coil_seq 里的位置：每匝 = 杆 + 上弧 + 下弧（最后一根只有杆）。
            pos = min(3 * i, n_coil - 1)
            f0, f1 = _seq_slot(pos, n_coil, span=0.94)
            _opacity_gate(arr, tr_coil.get_value, f0, f1)

        outer = VGroup()
        inner = VGroup()
        arrows = VGroup()
        outer_models = []
        for s in lay["seeds"]:
            pts = magnet_field_line(s, hx, hh)
            if ns < 0:
                pts = [(-px, py) for px, py in pts]
            apex_i = len(pts) // 2
            for sg in (1, -1):
                model = [(float(x), float(sg * y)) for x, y in pts]
                ln = VMobject(color=th["accent"], stroke_width=2.5)
                ln.set_points_as_corners([[x, y, 0] for x, y in model])
                outer.add(ln)
                outer_models.append(model)
                ay = sg * pts[apex_i][1]
                # 中线顶点处外线方向 = N→S = −ns·x̂
                arrows.add(self._f_arrow({"pos": (0.0, ay), "d": (float(-ns), 0.0)}, th))
        ax_len = 1.1
        for model in ([(ns * hx, 0.0), (ns * (hx + ax_len), 0.0)],
                      [(-ns * (hx + ax_len), 0.0), (-ns * hx, 0.0)]):
            ln = VMobject(color=th["accent"], stroke_width=2.5)
            ln.set_points_as_corners([[x, y, 0] for x, y in model])
            outer.add(ln)
            outer_models.append(model)
        for xm in (ns * (hx + 0.55 * ax_len), -ns * (hx + 0.45 * ax_len)):
            arrows.add(self._f_arrow({"pos": (xm, 0.0), "d": (float(ns), 0.0)}, th))
        tr_out = ValueTracker(0.0)
        n_out = max(len(outer), 1)
        for i, ln in enumerate(outer):
            f0, f1 = _seq_slot(i, n_out, span=0.90)
            _draw_on(ln, tr_out.get_value, f0, f1, outer_models[i], ref, th["accent"], 2.5)
        for i, arr in enumerate(arrows):
            f0, f1 = _seq_slot(i, n_out, span=0.90)
            _opacity_gate(arr, tr_out.get_value, f0 + 0.45 * (f1 - f0), f1)
        # 内部 S→N：平行等距 3 条（近匀强），第二段渐显；箭头与线同窗。
        tr_in = ValueTracker(0.0)
        n_in = max(len(lay["inner"]), 1)
        for i, it in enumerate(lay["inner"]):
            ln = Line([-hx, it["y"], 0], [hx, it["y"], 0], color=th["dim"],
                      stroke_width=2.0, stroke_opacity=0.9)
            inner.add(ln)
            f0, f1 = _seq_slot(i, n_in, span=0.72)
            _opacity_gate(ln, tr_in.get_value, f0, f1, base=0.9, stroke_only=True)
            inner.add(_head_on_path([(-ns * hx, it["y"]), (ns * hx, it["y"])],
                                    tr_in.get_value, f0, f1, ref, th["hi"], 0.075))
            arr = self._f_arrow({"pos": (0.0, it["y"]), "d": it["dir"]}, th)
            arrows.add(arr)
            _opacity_gate(arr, tr_in.get_value, f0 + 0.25 * (f1 - f0), f1)
        poles = VGroup(T("N", font_size=26, color=th["warn"]).move_to([ns * (hx + 0.35), 0.5, 0]),
                       T("S", font_size=26, color=th["dim"]).move_to([-ns * (hx + 0.35), 0.5, 0]))
        # N/S 常显：两端极性是装配骨架（也供标签复核）；线圈/内线/外线仍按三段演出。
        cap_obj = rich("右手握螺线管：四指顺电流、拇指指 N 极；外 N→S、内 S→N", 22, th["fg"])
        _opacity_gate(cap_obj, tr_out.get_value, 0.74, 0.98)
        g = VGroup(arcs, bars, outer, inner, poles, arrows, cur_arrows)
        g = VGroup(g, cap_obj).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        b0 = _mo.advance_to(
            tr_coil, 1.0, cue=0,
            note="时钟演化：线圈逐匝描出——杆、上弧、下弧按绕向顺序；前侧电流箭头随匝出现，方向=绕向")
        b0.run_time = 2.9
        beats.append(b0)
        b1 = _mo.advance_to(
            tr_in, 1.0, cue=1,
            note="时钟演化：内部 3 条平行等距磁场线渐显，方向 S→N——螺线管内部近匀强")
        b1.run_time = 2.6
        beats.append(b1)
        b2 = _mo.advance_to(
            tr_out, 1.0, cue=2,
            note="时钟演化 + 揭示：外部闭合磁感线按种子顺序逐条描出（N→S），最后点名 N/S 与右手定则")
        b2.run_time = 2.0
        beats.append(b2)
        g._field_tracker = tr_coil
        _mo.mount_motion(g, beats)
        return g

    def _f_field_compass(self, p, th):
        """小磁针（规范§19）：菱形指针，N 端填红、S 端填蓝，指向角 angle（度，+x=0 逆时针）；
        静止时 N 极指向即该点磁场方向。

        82-SD2a1：指针从 from_angle（缺省 90°）连续转到 to_angle（缺省取 angle），N/S 标签随之
        转到位；转到位后 ≤0.5s 落定强调。from_angle==to_angle 时做一次 ≤8° 的阻尼摆动再回
        to_angle——演的是「磁针受扰后稳定到磁场方向」的过程，不是一张静止指针图。
        """
        def _deg(key, default):
            try:
                v = float(p.get(key, default))
            except (TypeError, ValueError):
                return float(default)
            return v if math.isfinite(v) else float(default)

        to_deg = _deg("to_angle", _deg("angle", 0.0))
        from_deg = _deg("from_angle", 90.0)
        equal = abs(to_deg - from_deg) < 1e-9
        lay = compass_layout(from_deg)
        A, B, C, D = lay["poly"]
        outline = Polygon([A[0], A[1], 0], [B[0], B[1], 0], [C[0], C[1], 0], [D[0], D[1], 0],
                          color=th["fg"], stroke_width=3)
        nh = Polygon([A[0], A[1], 0], [B[0], B[1], 0], [D[0], D[1], 0],
                     color=th["warn"], stroke_width=2).set_fill(th["warn"], 1.0)
        sh = Polygon([C[0], C[1], 0], [B[0], B[1], 0], [D[0], D[1], 0],
                     color=th["accent"], stroke_width=2).set_fill(th["accent"], 1.0)
        tip = lay["tip"]
        tail = lay["tail"]
        Nlab = T("N", font_size=22, color=th["warn"]).move_to(
            [tip[0] * 1.35 + 0.12, tip[1] * 1.35 + 0.12, 0])
        Slab = T("S", font_size=22, color=th["accent"]).move_to(
            [tail[0] * 1.35 - 0.12, tail[1] * 1.35 - 0.12, 0])
        labs = VGroup(Nlab, Slab)
        hub = Dot([0, 0, 0], radius=0.045, color=th["fg"])
        needle = VGroup(nh, sh, outline)
        tr = ValueTracker(from_deg)
        osc = ValueTracker(0.0)

        def disp_deg():
            if equal:
                v = _clamp01(osc.get_value())
                return to_deg + 8.0 * math.sin(4.0 * math.pi * v) * (1.0 - v) ** 2
            t = (float(tr.get_value()) - from_deg) / (to_deg - from_deg)
            e = 1.0 - (1.0 - _clamp01(t)) ** 3      # 缓出：起转快、到位慢，像被磁场扭过去
            return from_deg + (to_deg - from_deg) * e

        def build_at(deg):
            """按当前（已被 _fit 变换）转轴圆点的中心与尺度重建菱形——不缓存装配期坐标。"""
            c = hub.get_center()
            s = max(float(hub.width), 1e-9) / 0.09     # 转轴圆点直径 2×0.045

            def P(pts, color, fill=None, sw=3):
                poly = Polygon(*[[c[0] + s * float(x), c[1] + s * float(y), 0.0] for x, y in pts],
                               color=color, stroke_width=sw)
                if fill is not None:
                    poly.set_fill(fill, 1.0)
                return poly

            L = compass_layout(deg)
            return L, P(L["poly"], th["fg"], None, 3), \
                P(L["n_half"], th["warn"], th["warn"], 2), \
                P(L["s_half"], th["accent"], th["accent"], 2)

        st = {"deg": None}

        def _needle_upd(_grp):
            deg = disp_deg()
            if st["deg"] is not None and abs(deg - st["deg"]) < 1e-9:
                return
            st["deg"] = deg
            L, po, pn, ps = build_at(deg)
            outline.become(po)
            nh.become(pn)
            sh.become(ps)
            c = hub.get_center()
            s = max(float(hub.width), 1e-9) / 0.09
            tp, tl = L["tip"], L["tail"]
            Nlab.move_to([c[0] + s * (tp[0] * 1.35 + 0.12),
                          c[1] + s * (tp[1] * 1.35 + 0.12), 0])
            Slab.move_to([c[0] + s * (tl[0] * 1.35 - 0.12),
                          c[1] + s * (tl[1] * 1.35 - 0.12), 0])

        needle.add_updater(_needle_upd)
        g = VGroup(needle, hub, labs)
        g = VGroup(g, rich("N 端（红）指向=该点磁场方向", 22, th["fg"])).arrange(DOWN, buff=0.2)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        if equal:
            b0 = _mo.advance_to(osc, 1.0, cue=0,
                                note="时钟演化：磁针在 to_angle 附近做 ≤8° 阻尼摆动后稳定——受扰后回到该点磁场方向")
            b0.run_time = 1.4
        else:
            b0 = _mo.advance_to(tr, to_deg, cue=0,
                                note="时钟演化：磁针从 from_angle 连续转到 to_angle——N 端（红）被磁场扭到该点磁场方向")
            b0.run_time = 1.8
        beats.append(b0)
        beats.append(_mo.emphasize(needle, kind="indicate", cue=1))
        g._compass_tracker = tr
        g._compass_osc = osc
        g._compass_from = from_deg
        g._compass_target = to_deg
        g._compass_hub = hub
        g._compass_n = nh
        _mo.mount_motion(g, beats)
        return g

    def _v_circuit(self, p, th):
        """电路图（GB/T 4728 符号，按 circuit_layout 画）：导线横平竖直拐直角，连接点实心圆点。

        符号：电池=长线正极+短线负极、电阻=矩形、开关=断开斜刃（closed=true 落下成通路）、
        灯泡=圆圈内×、电表=圆圈内 A/V（ammeter 可带 reading 指针）、
        81-S1 新增 capacitor=双板、inductor=半圆线圈、rheostat=框+斜箭头滑片。
        元件带 branch=k 挂成竖直并联支路（规范§16）；current_arrows=true 沿导线画电流箭头。
        """
        elems = [e for e in p.get("elements", []) if isinstance(e, dict)]
        lay = circuit_layout(elems)
        hw, hh = lay["hw"], lay["hh"]
        wire = th["dim"]
        col = th["key"]
        g = VGroup()
        wires = VGroup()
        for a, b in lay["wires"]:
            wires.add(Line([a[0], a[1], 0], [b[0], b[1], 0], color=wire, stroke_width=3))
        g.add(wires)
        jdots = VGroup()
        for jx, jy in lay["junctions"]:
            jdots.add(Dot([jx, jy, 0], radius=0.065, color=wire).set_fill(wire, 1.0))
        g.add(jdots)

        def symbol(e, x, y, vertical=False):
            ty = str(e.get("type"))
            gw = CIRCUIT_HALF[ty] if ty in CIRCUIT_HALF else CIRCUIT_R
            sg = VGroup()
            if ty == "battery":
                # 两极板贴近中线（间距 0.28），端子到极板用引线补足：端子仍在 x±gw，
                # 极板若画在端子上会变成「两根竖线隔一大段空白」的假电池符号。
                px = 0.14
                sg.add(Line([x - gw, y, 0], [x - px, y, 0], color=col, stroke_width=3))
                sg.add(Line([x - px, y - 0.28, 0], [x - px, y + 0.28, 0], color=col, stroke_width=5))
                sg.add(Line([x + px, y - 0.16, 0], [x + px, y + 0.16, 0], color=col, stroke_width=5))
                sg.add(Line([x + px, y, 0], [x + gw, y, 0], color=col, stroke_width=3))
                sg.add(rich("+", 22, col).next_to([x - px, y + 0.28, 0], UP, buff=0.04))
                # 负极用短横线而不是「−」字形：22pt 的减号只有 1.5px 高，贴在短板顶端
                # 会被读成 T 形（79C1_smoke/f_7.6 实测），短线与电池符号同粗才像电极标记。
                sg.add(Line([x + px - 0.12, y + 0.16 + 0.14, 0],
                            [x + px + 0.12, y + 0.16 + 0.14, 0], color=col, stroke_width=3))
            elif ty == "resistor":
                sg.add(Rectangle(width=2 * gw, height=0.5, color=col, stroke_width=3).move_to([x, y, 0]))
            elif ty == "switch":
                if e.get("closed"):     # 闭合态：闸刀落在水平位置（构造期=旧几何，SD2b 从斜角转下）
                    blade = Line([x - gw, y, 0], [x + gw, y, 0], color=col, stroke_width=3)
                    sg.add(blade)
                    sg._blade = blade
                    sg._blade_open = math.atan2(0.5, 2 * gw)   # 合闸前抬起的斜角
                else:                   # 断开态（旧行为）：斜刃只接左端子
                    sg.add(Line([x - gw, y, 0], [x + gw * 0.55, y + 0.5, 0], color=col, stroke_width=3))
            elif ty == "bulb":
                c = Circle(radius=CIRCUIT_R, color=col, stroke_width=3).move_to([x, y, 0])
                d = CIRCUIT_R * 0.7
                sg.add(c, Line([x - d, y - d, 0], [x + d, y + d, 0], color=col, stroke_width=3),
                       Line([x - d, y + d, 0], [x + d, y - d, 0], color=col, stroke_width=3))
            elif ty == "capacitor":     # 两等长竖板、中间断口（GB/T 4728.4，规范§2）
                sg.add(Line([x - gw, y - 0.25, 0], [x - gw, y + 0.25, 0], color=col, stroke_width=4),
                       Line([x + gw, y - 0.25, 0], [x + gw, y + 0.25, 0], color=col, stroke_width=4))
            elif ty == "inductor":      # 四个半圆凸起（线圈，GB/T 4728.4）
                a0 = x - gw
                step = 2 * gw / 4
                for k in range(4):
                    sg.add(ArcBetweenPoints([a0 + k * step, y, 0], [a0 + (k + 1) * step, y, 0],
                                            angle=math.pi, color=col, stroke_width=3))
            elif ty == "rheostat":      # 电阻框+斜箭头滑片（GB/T 4728.7 变阻器，规范§2）
                sg.add(Rectangle(width=2 * gw, height=0.5, color=col, stroke_width=3).move_to([x, y, 0]))
                sg.add(Arrow([x + 0.35, y + 0.8, 0], [x - 0.1, y + 0.28, 0], color=col, buff=0,
                             stroke_width=3, max_tip_length_to_length_ratio=0.4))
            else:  # ammeter / voltmeter / 未知类型按电表圆画
                c = Circle(radius=CIRCUIT_R, color=col, stroke_width=3).move_to([x, y, 0])
                sg.add(c, T("A" if ty == "ammeter" else "V", font_size=26, color=col).move_to(c))
                if e.get("reading") is not None and ty == "ammeter":
                    # 可选读数指针：偏转角 ∝ reading/full_scale（ammeter_needle_angle，楞次刚需）
                    ndeg = ammeter_needle_angle(e.get("reading"), e.get("full_scale", 1.0))
                    rad = math.radians(ndeg)
                    needle = Line([x, y, 0], [x + 0.85 * CIRCUIT_R * math.sin(rad),
                                              y + 0.85 * CIRCUIT_R * math.cos(rad), 0],
                                  color=th["warn"], stroke_width=3)
                    sg.add(needle)
                    sg._needle = needle
                    sg._needle_deg = ndeg
            if e.get("label") and not vertical:
                sg.add(rich(str(e["label"]), 22, col).next_to([x, y, 0], UP, buff=0.34))
            if vertical:                # 竖直支路元件：整体转 90°（字母除外，保持水平可读）
                txts = [m for m in sg if isinstance(m, Text)]
                for m in txts:
                    sg.remove(m)
                sg.rotate(math.pi / 2, about_point=[x, y, 0])
                if e.get("label"):
                    sg.add(rich(str(e["label"]), 22, col).next_to([x, y, 0], LEFT, buff=0.34))
                sg.add(*txts)
            # 82-SD2b：转轴件（闸刀/表针）记下**当前**实角——支路转过 90° 后仍按屏幕方向回摆
            if getattr(sg, "_blade", None) is not None:
                bv = sg._blade.get_end() - sg._blade.get_start()
                sg._blade_base = math.atan2(float(bv[1]), float(bv[0]))
            if getattr(sg, "_needle", None) is not None:
                nv = sg._needle.get_end() - sg._needle.get_start()
                sg._needle_base = math.atan2(float(nv[1]), float(nv[0]))
            return sg

        syms = [symbol(e, x, y, e.get("branch") is not None)
                for e, (x, y) in zip(elems, lay["pos"])]
        # 82-SD2b：带转轴件的符号（闸刀/读数表针）不做分批淡入——它们从第一帧就在屏上，
        # 由 tracker 演「合闸/偏转」；否则被 collect_reveals 摘走，动作播在画面外。
        moving_ids = {id(s) for s in syms
                      if getattr(s, "_blade", None) is not None
                      or getattr(s, "_needle", None) is not None}
        still = [s for s in syms if id(s) not in moving_ids]
        if len(still) >= 2:
            for s, key in zip(still, reveal_keys(p.get("at"), len(still))):
                tag_reveal(s, key)
        for s in syms:
            g.add(s)
        arrows = VGroup()
        if p.get("current_arrows"):     # 沿导线的电流方向小箭头（正极→外电路→负极，串联回路连续）
            for a in lay["current"]["arrows"]:
                px, py = a["p"]
                dx, dy = a["d"]
                hl = a.get("half", 0.2)   # 支路箭头按可用接线段缩短（见 circuit_layout）
                arrows.add(Arrow([px - dx * hl, py - dy * hl, 0], [px + dx * hl, py + dy * hl, 0],
                                 color=th["warn"], buff=0, stroke_width=4,
                                 max_tip_length_to_length_ratio=0.45))
            g.add(arrows)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)

        # ---- 82-SD2b M4：导线逐段描出 → 合闸（电流箭头分时点亮）→ 表针 0→读数偏转 ----
        # 全部由 ValueTracker + updater 现算；beats 只借既有 hold 帧，cue 显式绑定。
        sw_syms = [s for s in syms if getattr(s, "_blade", None) is not None]
        nd_syms = [s for s in syms if getattr(s, "_needle", None) is not None]
        tr_wire = ValueTracker(0.0)
        n_wire = max(len(wires), 1)
        for i, w in enumerate(wires):
            f0, f1 = _seq_slot(i, n_wire, span=0.96)
            _grow_partial(w, tr_wire.get_value, f0, f1)
        for jd in jdots:
            jc = jd.get_center()[:2]
            jf = 0.0
            for i, (a, b) in enumerate(lay["wires"]):
                if (abs(a[0] - jc[0]) < 1e-6 and abs(a[1] - jc[1]) < 1e-6) or \
                        (abs(b[0] - jc[0]) < 1e-6 and abs(b[1] - jc[1]) < 1e-6):
                    jf = max(jf, _seq_slot(i, n_wire, span=0.96)[1])
            _opacity_gate(jd, tr_wire.get_value, max(jf - 0.10, 0.0), min(jf + 0.02, 1.0))
        tr_sw = ValueTracker(0.0)
        for s in sw_syms:
            _swing_to(s._blade, tr_sw.get_value,
                      lambda u, b=s._blade_base, o=s._blade_open: b + o * (1.0 - u))
        tr_nd = ValueTracker(0.0)
        for s in nd_syms:
            _swing_to(s._needle, tr_nd.get_value,
                      lambda u, b=s._needle_base, a=math.radians(float(s._needle_deg)):
                      b + a * (1.0 - u))
        tr_ar = ValueTracker(0.0)
        arr_tracker = tr_sw if sw_syms else tr_ar
        for i, ar in enumerate(arrows):
            f0, f1 = _seq_slot(i, max(len(arrows), 1), span=0.9)
            _opacity_gate(ar, arr_tracker.get_value, f0, f1)

        has_sw, has_ar, has_nd = bool(sw_syms), bool(arrows), bool(nd_syms)
        # 通电后电流箭头沿自身方向轻微往复（包络 sin 在通电段两端归零）：
        # 合闸拍 + 表针拍接力推进「持续流动」的观感，不影响箭头点亮顺序与最终位置。
        for i, ar in enumerate(arrows):
            st_ar = {"c": None}

            def _flow(m, i=i, st=st_ar):
                if st["c"] is None:
                    st["c"] = m.get_center().copy()
                v = m.get_end() - m.get_start()
                nv = float(np.linalg.norm(v))
                if nv < 1e-9:
                    return
                if has_sw or has_nd:
                    u = _clamp01((tr_sw.get_value() + tr_nd.get_value()) / 2.0)
                else:
                    u = _clamp01(tr_ar.get_value())
                off = 0.14 * math.sin(math.pi * u) * math.sin(4.0 * math.pi * u - 0.8 * i)
                m.move_to(st["c"] + v / nv * off)

            ar.add_updater(_flow)
        n_prog = 1 + int(has_sw) + int(has_ar and not has_sw) + int(has_nd)
        rt_w = 2.6
        beats = []
        if n_prog == 1:            # 只有导线可演：分三拍描完，不让任何一条 cue 空转
            for k, tgt in enumerate((1.0 / 3.0, 2.0 / 3.0, 1.0)):
                b = _mo.advance_to(tr_wire, tgt, cue=k,
                                   note="时钟演化：导线沿回路逐段描出（本镜无开关/读数，骨架即过程）")
                b.run_time = rt_w
                beats.append(b)
        elif n_prog == 2:          # 导线分两拍画完，第二个程序收在末拍
            for k, tgt in enumerate((0.55, 1.0)):
                b = _mo.advance_to(tr_wire, tgt, cue=k, note="时钟演化：导线沿回路逐段描出")
                b.run_time = rt_w
                beats.append(b)
        else:
            b = _mo.advance_to(tr_wire, 1.0, cue=0,
                               note="时钟演化：导线沿回路逐段描出（先立回路骨架，再通电）")
            b.run_time = rt_w
            beats.append(b)
        if has_sw:
            # 三拍固定分工：0 导线 / 1 合闸(+电流) / 2 表针；导线要分两拍时合闸收在末拍。
            # （契约里的 close_at 是「合闸拍」语义，这里在既有三 cue 布局内固定为 1/2。）
            cue_sw = 1 if n_prog >= 3 else 2
            b = _mo.advance_to(
                tr_sw, 1.0, cue=cue_sw,
                note=("时钟演化：闸臂从断开斜角落到水平——合闸，电流箭头沿回路分时点亮"
                      if has_ar else "时钟演化：闸臂从断开斜角落到水平——合闸（闭合回路才有电流）"))
            b.run_time = rt_w
            beats.append(b)
        elif has_ar:
            b = _mo.advance_to(
                tr_ar, 1.0, cue=(2 if n_prog == 2 else 1),
                note="时钟演化：电流箭头沿回路顺序点亮（正极→外电路→负极）")
            b.run_time = rt_w
            beats.append(b)
        if has_nd:
            b = _mo.advance_to(
                tr_nd, 1.0, cue=2,
                note="时钟演化：表针从 0 连续偏转到读数角（θ=60°·reading/full_scale）")
            b.run_time = rt_w
            beats.append(b)
        _mo.mount_motion(g, beats)
        return g

    def _v_optics(self, p, th):
        """光路图：法线画虚线、光线画实线带箭头；镜面=线段+背面斜线；折射=界面+折向法线。
        lens/image 见 _optics_imaging：u<f 放大镜虚像、lens="concave"（或 f<0）凹透镜虚像。

        入射角/反射角/折射角都标在光线上（不画角度弧线——那是数学记号，物理用物理图示）。
        """
        mode = str(p.get("mode") or "mirror")
        ang = math.radians(max(1.0, min(float(p.get("angle", 30)), 80.0)))
        r = 2.2
        show_normal = bool(p.get("show_normal", True))
        g = VGroup()
        if mode in ("lens", "image"):
            g = self._optics_imaging(mode, p, th)
        elif mode == "refract":
            # 水平界面 + 竖直法线（虚线）；入射自上左，折射折向法线入下右。
            n2 = float(p.get("n", 1.5))
            ang2 = math.asin(max(-1.0, min(1.0, math.sin(ang) / n2)))
            g.add(Line([-r, 0, 0], [r, 0, 0], color=th["key"], stroke_width=4))
            if show_normal:
                g.add(DashedLine([0, -1.7, 0], [0, 1.7, 0], dash_length=0.12, color=th["dim"], stroke_width=3))
            inc = Arrow([-r * math.sin(ang), r * math.cos(ang), 0], [0, 0, 0], color=th["accent"], buff=0, stroke_width=5)
            ref = Arrow([0, 0, 0], [r * math.sin(ang2), -r * math.cos(ang2), 0], color=th["warn"], buff=0, stroke_width=5)
            g.add(inc, ref)
            g.add(rich("入射光线", 22, th["accent"]).move_to([-r * math.sin(ang) / 2 - 0.1, r * math.cos(ang) / 2 + 0.25, 0]))
            g.add(rich("折射光线", 22, th["warn"]).move_to([r * math.sin(ang2) / 2 + 0.1, -r * math.cos(ang2) / 2 - 0.25, 0]))
            if show_normal:
                g.add(rich("法线", 22, th["dim"]).next_to([0, 1.7, 0], UP, buff=0.08))
            g.add(rich("空气", 22, th["dim"]).move_to([-r + 0.6, 0.55, 0]),
                  rich("玻璃", 22, th["dim"]).move_to([-r + 0.6, -0.55, 0]))
        else:
            # 竖直镜面 + 水平法线（虚线）；背面斜线示镜面；入射上左 → 反射上右（对称）。
            mh = 1.7
            g.add(Line([0, -mh, 0], [0, mh, 0], color=th["key"], stroke_width=5))
            for yy in (-1.2, -0.6, 0.0, 0.6, 1.2):
                g.add(Line([0.14, yy - 0.12, 0], [0.32, yy + 0.12, 0], color=th["dim"], stroke_width=3))
            if show_normal:
                g.add(DashedLine([-1.8, 0, 0], [1.8, 0, 0], dash_length=0.12, color=th["dim"], stroke_width=3))
            inc = Arrow([-r * math.cos(ang), r * math.sin(ang), 0], [0, 0, 0], color=th["accent"], buff=0, stroke_width=5)
            ref = Arrow([0, 0, 0], [r * math.cos(ang), r * math.sin(ang), 0], color=th["warn"], buff=0, stroke_width=5)
            g.add(inc, ref)
            g.add(rich("入射光线", 22, th["accent"]).move_to([-r * math.cos(ang) / 2 - 0.1, r * math.sin(ang) / 2 + 0.28, 0]))
            g.add(rich("反射光线", 22, th["warn"]).move_to([r * math.cos(ang) / 2 + 0.1, r * math.sin(ang) / 2 + 0.28, 0]))
            g.add(rich("i", 24, th["accent"]).move_to([-0.5, 0.32, 0]))
            g.add(rich("r", 24, th["warn"]).move_to([0.5, 0.32, 0]))
            if show_normal:
                g.add(rich("法线", 22, th["dim"]).next_to([1.8, 0, 0], RIGHT, buff=0.08))
            g.add(rich("镜面", 22, th["dim"]).next_to([0.32, -1.6, 0], RIGHT, buff=0.1))
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _optics_imaging(self, mode, p, th):
        """成像作图：实物/实光线画实线，虚像与反向延长线画虚线；物、光线、像依次揭示。"""
        body, units = VGroup(), []

        def dashed(a, b):
            return DashedLine(a, b, dash_length=0.12, color=th["dim"], stroke_width=3)

        if mode == "image":
            # 平面镜成像：物像关于镜面对称、连线垂直镜面；两条反射光线的反向延长线交于虚像。
            d, oh = 1.6, 1.1
            body.add(Line([0, -1.6, 0], [0, 1.6, 0], color=th["key"], stroke_width=5))
            for yy in (-1.2, -0.6, 0.0, 0.6, 1.2):
                body.add(Line([0.14, yy - 0.12, 0], [0.32, yy + 0.12, 0], color=th["dim"], stroke_width=3))
            obj = VGroup(Arrow([-d, -0.6, 0], [-d, -0.6 + oh, 0], color=th["accent"], buff=0, stroke_width=6),
                         rich("物", 22, th["accent"]).next_to([-d, -0.6, 0], DOWN, buff=0.1))
            top, img_top = np.array([-d, -0.6 + oh, 0]), np.array([d, -0.6 + oh, 0])
            rays = VGroup()
            for hy in (1.3, -0.3):
                hit = np.array([0, hy, 0])
                out = hit + (hit - img_top) / np.linalg.norm(hit - img_top) * 1.3
                rays.add(Arrow(top, hit, color=th["warn"], buff=0, stroke_width=4),
                         Arrow(hit, out, color=th["warn"], buff=0, stroke_width=4),
                         dashed(hit, img_top))
            img = VGroup(DashedLine([d, -0.6, 0], img_top, dash_length=0.12, color=th["accent"], stroke_width=5),
                         dashed(top, img_top),
                         rich("像（虚像）", 22, th["accent"]).next_to([d, -0.6, 0], DOWN, buff=0.1))
            units = [obj, rays, img]
        else:
            # 透镜成像（lens_layout 解析几何）：u<f 放大镜成正立放大虚像；凹透镜（lens="concave"
            # 或 f<0）恒成正立缩小虚像；反向延长线/虚像虚线，实际光线实线带箭头；F、2F 标在轴上。
            f_in = float(p.get("f", LENS_F)) or LENS_F
            fmag = abs(f_in)
            concave = str(p.get("lens") or "").strip().lower() == "concave" or f_in < 0
            f = -fmag if concave else fmag
            oh = 0.9
            # u 钳位（像在无穷远/出框的区间画不了）：凸实像 1.5f~3.5f、放大镜 0.3f~0.5f、凹 0.5f~3.5f
            u = float(p.get("u", 2.0 * fmag))
            if concave:
                u = max(0.5 * fmag, min(u, 3.5 * fmag))
            elif u < fmag:
                u = max(0.3 * fmag, min(u, 0.5 * fmag))
            else:
                u = max(1.5 * fmag, min(u, 3.5 * fmag))
            lay = lens_layout(u, f, oh)
            body.add(Line([lay["x_left"], 0, 0], [lay["x_right"], 0, 0], color=th["dim"], stroke_width=2))
            lh = lay["lens_h"] / 2
            if f > 0:
                body.add(Ellipse(width=0.32, height=2 * lh, color=th["key"], stroke_width=4))
            else:   # 凹透镜符号：中间薄（双凹弧线 + 上下端帽；弧中点 x≈∓0.03，中薄边厚）
                w, c = 0.16, 0.01
                body.add(CubicBezier([-w, lh, 0], [c, lh * 0.4, 0], [c, -lh * 0.4, 0], [-w, -lh, 0],
                                     color=th["key"], stroke_width=4),
                         CubicBezier([w, lh, 0], [-c, lh * 0.4, 0], [-c, -lh * 0.4, 0], [w, -lh, 0],
                                     color=th["key"], stroke_width=4),
                         Line([-w, lh, 0], [w, lh, 0], color=th["key"], stroke_width=4),
                         Line([-w, -lh, 0], [w, -lh, 0], color=th["key"], stroke_width=4))
            for x, cap in [(p2[0], "F") for p2 in lay["focus"]] + [(p2[0], "2F") for p2 in lay["pt2f"]]:
                body.add(Dot([x, 0, 0], radius=0.05, color=th["dim"]),
                         rich(cap, 22, th["dim"]).next_to([x, 0, 0], DOWN, buff=0.12))
            body.add(rich("O", 22, th["dim"]).next_to([0, 0, 0], DOWN + RIGHT, buff=0.08))
            top = np.array([lay["obj_top"][0], lay["obj_top"][1], 0.0])
            obj = VGroup(Arrow([lay["obj_top"][0], 0, 0], top, color=th["accent"], buff=0, stroke_width=6),
                         rich("物", 22, th["accent"]).next_to([lay["obj_top"][0], 0, 0], DOWN, buff=0.12))
            rays = VGroup()
            for s in lay["segs"]:
                a = np.array([s["p"][0], s["p"][1], 0.0])
                b = np.array([s["q"][0], s["q"][1], 0.0])
                if s["dashed"]:
                    rays.add(DashedLine(a, b, dash_length=0.12, color=th["warn"], stroke_width=3))
                elif s["arrow"]:
                    rays.add(Arrow(a, b, color=th["warn"], buff=0, stroke_width=4))
                else:
                    rays.add(Line(a, b, color=th["warn"], stroke_width=4))
            vx, ih = lay["v"], lay["ih"]
            if lay["real"]:
                img = VGroup(Arrow([vx, 0, 0], [vx, ih, 0], color=th["accent"], buff=0, stroke_width=6),
                             rich("像（倒立实像）", 22, th["accent"]).next_to([vx, 0, 0], UP, buff=0.12))
            else:
                cap = "像（正立放大虚像）" if f > 0 else "像（正立缩小虚像）"
                img = VGroup(DashedLine([vx, 0, 0], [vx, ih, 0], dash_length=0.12, color=th["accent"], stroke_width=5),
                             rich(cap, 22, th["accent"]).next_to([vx, 0, 0], DOWN, buff=0.5))
            units = [obj, rays, img]
        for un, k in zip(units, reveal_keys(p.get("at"), len(units))):
            tag_reveal(un, k)
        return VGroup(body, *units)

    def _v_incline(self, p, th):
        """斜面滑块：斜面三角 + 贴面方块 + 受力箭头（逐条揭示）。

        力的 dir 除 force_diagram 的绝对方向词/角度外，还认斜面相对方向：
        normal（垂直斜面向外）、into（垂直斜面向里，压力）、along_up / along_down（沿斜面）。
        倾角只在底角写 θ，不画角度弧线（弧线是数学记号）。
        81-S2 扩展（旧 props 下全部不触发，回归锁见 Test81S2BehaviorLock）：
          vt=true → 转入 _f_incline_vt（右侧 v-t 图同步生长）；hatch_face → 斜面表面刻线；
          contact → 接触点高亮圆点（规范§3：面是物块真正碰着的那条线）。
        """
        if p.get("vt"):
            return self._f_incline_vt(p, th)
        deg = max(10.0, min(float(p.get("angle", 30)), 60.0))
        a = math.radians(deg)
        base = 4.4
        h = base * math.tan(a)
        if h > 2.6:
            h = 2.6
            base = h / math.tan(a)
        x0, y0 = -base / 2, -h / 2
        ramp = Polygon([x0, y0, 0], [x0 + base, y0, 0], [x0 + base, y0 + h, 0],
                       color=th["dim"], stroke_width=4).set_fill(th["dim"], 0.12)
        g = VGroup(ramp)
        for i in range(7):
            xx = x0 - 0.3 + i * (base + 0.6) / 6
            g.add(Line([xx, y0, 0], [xx - 0.22, y0 - 0.22, 0], color=th["dim"], stroke_width=2))
        g.add(rich("θ", 26, th["fg"]).move_to([x0 + 0.75, y0 + 0.2, 0]))
        u_along = np.array([math.cos(a), math.sin(a), 0.0])
        u_norm = np.array([-math.sin(a), math.cos(a), 0.0])
        bw, bh = 1.0, 0.66
        foot = np.array([x0, y0, 0.0]) + u_along * (base / math.cos(a)) * 0.55
        center = foot + u_norm * (bh / 2)
        block = Rectangle(width=bw, height=bh, color=th["key"], stroke_width=4).set_fill(th["key"], 0.15)
        block.rotate(a).move_to(center)
        g.add(block)
        if p.get("label_in"):
            g.add(rich(str(p["label_in"]), 26, th["fg"]).move_to(center))
        rel = {"normal": u_norm, "into": -u_norm, "along_up": u_along, "along_down": -u_along}
        L = 1.2
        units = []
        forces = [x for x in p.get("forces", []) if isinstance(x, dict)]
        keys = [str(f.get("dir")).strip().lower() for f in forces]
        dirs = []
        for f, key in zip(forces, keys):
            d = rel[key] if key in rel else _dir_vec(f.get("dir"))
            dirs.append(d / (np.linalg.norm(d) or 1.0))
        # 方块 bw×bh 随斜面转 a：露出边框的那段 ∝ mag；压力 into 从接触点出发，不加边距
        lengths = _body_force_lengths(forces, dirs, L, bw / 2, bh / 2, rot=a,
                                      edge_ok=[k != "into" for k in keys])
        for f, key, d, ln in zip(forces, keys, dirs, lengths):
            start = foot if key == "into" else center
            color = th.get(str(f.get("tone") or "key"), th["key"])
            arrow = Arrow(start, start + d * ln, color=color, buff=0, stroke_width=5,
                          max_tip_length_to_length_ratio=0.35)
            unit = VGroup(arrow)
            label = str(f.get("label") or f.get("name") or "")
            if label:
                unit.add(rich(label, 24, color).next_to(arrow.get_end(), d, buff=0.08))
            units.append(unit)
        if len(units) >= 2:
            for u, k in zip(units, reveal_keys(p.get("at"), len(units))):
                tag_reveal(u, k)
        g.add(*units)
        # 81-S2：斜面表面刻线（朝材料侧、45°斜后画，规范§3）+ 接触点高亮（规范§6 N⊥面的落点）。
        if p.get("hatch_face"):
            hc0 = np.array([x0, y0, 0.0]) + u_along * 0.35
            hc1 = np.array([x0 + base, y0 + h, 0.0]) - u_along * 0.25
            g.add(*[Line(np.array(a, dtype=float), np.array(b, dtype=float),
                         color=th["dim"], stroke_width=2)
                    for a, b in _surface_hatch((hc0[0], hc0[1]), (hc1[0], hc1[1]), -u_norm)])
        if p.get("contact"):
            g.add(Dot(foot, radius=0.07, color=th["hi"]))
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        return g

    def _f_incline_vt(self, p, th):
        """斜面下滑 · v-t 图联动动画（81-S2）：频闪式同步。

        同步口径：左图每个滑块的"位置影"与右图对应的数据点装进**同一个揭示单元**——
        collect_reveals 把同批成员与同一条字幕淡入在同一帧，同步是构造性质，不是对表。
        一切坐标由公式生成（SIM_DT 纪律、禁手填关键帧，见 incline_slide_layout）：
          a = g(sinθ−μcosθ) 恒加速（规范§6：N⊥斜面、f 沿斜面且与相对运动反向——默认箭 G/N/f
          的画法即此，mag 取物理比值 1 : cosθ : μcosθ，同图箭长∝大小，规范§5）；
          v = at、s = ½at²、t_k = kT/n。滑块屏幕行程 = s_k·(D/smax)，等比映射不撒谎。
        μ≥tanθ → a=0：从静止释放**不滑**——影块与行程整组不画，v-t 就是 t 轴上的水平线，
        这是物理正确的静止而不是画法失败。
        props: angle/mu(0)/g(9.8)/T(6)/n(3..8)/show_velocity(True)/forces(可覆盖默认三力)/
               vt_label(默认 "a = … m·s⁻²")/vt_x_label("t/s")/vt_y_label("v/(m·s⁻¹)")/label。
        """
        la = incline_slide_layout(float(p.get("angle", 30)), float(p.get("mu") or 0.0),
                                  float(p.get("g") or 9.8), float(p.get("T") or 6.0),
                                  int(p.get("n") or 6))
        rad, acc, base, h = la["rad"], la["a"], la["base"], la["h"]
        ttot, n, vmax, smax = la["T"], la["n"], la["vmax"], la["smax"]
        ts, vs, ss = la["ts"], la["vs"], la["ss"]
        x0, y0 = -base / 2, -h / 2
        u_along = np.array([math.cos(rad), math.sin(rad), 0.0])
        u_norm = np.array([-math.sin(rad), math.cos(rad), 0.0])
        bw, bh = 1.0, 0.66

        left = VGroup()
        ramp = Polygon([x0, y0, 0], [x0 + base, y0, 0], [x0 + base, y0 + h, 0],
                       color=th["dim"], stroke_width=4).set_fill(th["dim"], 0.12)
        left.add(ramp)
        for i in range(7):            # 地面刻线：与旧斜面逐字同口径
            xx = x0 - 0.3 + i * (base + 0.6) / 6
            left.add(Line([xx, y0, 0], [xx - 0.22, y0 - 0.22, 0], color=th["dim"], stroke_width=2))
        hc0 = np.array([x0, y0, 0.0]) + u_along * 0.35
        hc1 = np.array([x0 + base, y0 + h, 0.0]) - u_along * 0.25
        for a_, b_ in _surface_hatch((hc0[0], hc0[1]), (hc1[0], hc1[1]), -u_norm):
            left.add(Line(np.array(a_, dtype=float), np.array(b_, dtype=float),
                          color=th["dim"], stroke_width=2))
        left.add(rich("θ", 26, th["fg"]).move_to([x0 + 0.75, y0 + 0.2, 0]))

        sl = base / math.cos(rad)
        d_start = min(0.85 * sl, sl - bw / 2 - 0.15)
        D = max(0.0, min(d_start - (bw / 2 + 0.15), 0.62 * sl))
        k_s = D / smax if smax > 1e-9 else 0.0

        def foot_at(d):
            return np.array([x0, y0, 0.0]) + u_along * d

        f0 = foot_at(d_start)
        c0 = f0 + u_norm * (bh / 2)
        block = Rectangle(width=bw, height=bh, color=th["key"], stroke_width=4).set_fill(th["key"], 0.15)
        block.rotate(rad).move_to(c0)
        left.add(block)
        live_dot = Dot(f0, radius=0.07, color=th["hi"])    # 接触点高亮（随滑块下滑）
        left.add(live_dot)

        forces = [f for f in p.get("forces", []) if isinstance(f, dict)]
        if not forces:                                    # 默认三力：箭长取真实物理比值
            forces = [{"dir": "down", "label": "G", "mag": 1.0},
                      {"dir": "normal", "label": "N", "mag": round(math.cos(rad), 4)}]
            if la["mu"] > 1e-9:
                forces.append({"dir": "along_up", "label": "f",
                               "mag": round(la["mu"] * math.cos(rad), 4)})
        rel = {"normal": u_norm, "into": -u_norm, "along_up": u_along, "along_down": -u_along}
        keys = [str(f.get("dir")).strip().lower() for f in forces]
        dirs = []
        for f, key in zip(forces, keys):
            d = rel[key] if key in rel else _dir_vec(f.get("dir"))
            dirs.append(d / (np.linalg.norm(d) or 1.0))
        lengths = _body_force_lengths(forces, dirs, 1.2, bw / 2, bh / 2, rot=rad,
                                      edge_ok=[k != "into" for k in keys])
        for f, key, d, ln in zip(forces, keys, dirs, lengths):
            start = f0 if key == "into" else c0
            color = th.get(str(f.get("tone") or "key"), th["key"])
            arrow = Arrow(start, start + d * ln, color=color, buff=0, stroke_width=5,
                          max_tip_length_to_length_ratio=0.35)
            u = VGroup(arrow)
            label = str(f.get("label") or f.get("name") or "")
            if label:
                u.add(rich(label, 24, color).next_to(arrow.get_end(), d, buff=0.08))
            left.add(u)

        gxl, gyl = 4.6, 3.4
        x_hi = ttot * 1.15
        y_hi = (vmax if vmax > 1e-9 else max(ttot * 0.25, 1.0)) * 1.25
        sx, sy = _grid_step(0.0, x_hi), _grid_step(0.0, y_hi)
        gx = base / 2 + gxl / 2 + 0.55
        plane = NumberPlane(x_range=[0, x_hi, sx], y_range=[0, y_hi, sy],
                            x_length=gxl, y_length=gyl,
                            background_line_style={"stroke_color": th["grid"], "stroke_width": 1},
                            axis_config={"stroke_color": th["dim"]})
        plane.move_to([gx, 0.15, 0])

        def tick(text, pos, shift, escape):
            t = T(text, font_size=20, color=th["dim"]).move_to(pos).shift(shift)
            t._tick_dir = escape
            t._tick_anchor = np.array(t.get_center())
            return t

        ticks = VGroup(
            *[tick(_fmt_tick(v_), plane.c2p(v_, 0), DOWN * 0.3, DOWN)
              for v_ in _tick_values(0, x_hi, sx) if v_ != 0],
            *[tick(_fmt_tick(v_), plane.c2p(0, v_), LEFT * 0.42, LEFT)
              for v_ in _tick_values(0, y_hi, sy) if v_ != 0],
            tick("0", plane.c2p(0, 0), DOWN * 0.3 + LEFT * 0.3, DOWN + LEFT),
        )
        xlab = rich(str(p.get("vt_x_label") or "t/s"), 22, th["dim"])
        xlab.move_to([plane.get_right()[0] + AXIS_NAME_GAP + xlab.width / 2,
                      plane.c2p(x_hi, 0)[1] + 0.16, 0])
        ylab = rich(str(p.get("vt_y_label") or "v/(m·s⁻¹)"), 22, th["dim"])
        ylab.move_to([plane.c2p(0, y_hi)[0] + ylab.width / 2 + 0.2,
                      plane.c2p(0, y_hi)[1] - 0.12, 0])
        graph = VGroup(plane, ticks, xlab, ylab)

        show_v = bool(p.get("show_velocity", True))
        units, segs_list, cursors, dots = [], [], [], []
        for k in range(1, n + 1):
            p_prev = plane.c2p(ts[k - 1], vs[k - 1])
            p_now = plane.c2p(ts[k], vs[k])
            seg = _polyline([p_prev, p_now], th["key"], 5)
            dotk = Dot(p_now, radius=0.08, color=th["accent"])
            u = VGroup()
            if smax > 1e-9:
                d_k = d_start - ss[k] * k_s
                fk = foot_at(d_k)
                ck = fk + u_norm * (bh / 2)
                ghost = Rectangle(width=bw, height=bh, color=th["accent"], stroke_width=3)
                ghost.rotate(rad).move_to(ck)
                u.add(ghost, Dot(fk, radius=0.06, color=th["hi"]))
                if show_v:
                    lv = min(0.7 * vs[k] / max(vmax, 1e-9),
                             max(d_k - bw / 2 - 0.12, 0.0))
                    if lv >= 0.15:
                        s0 = ck - u_along * (bw / 2 + 0.02)
                        u.add(Arrow(s0, s0 - u_along * lv, color=th["hi"], buff=0,
                                    stroke_width=4, max_tip_length_to_length_ratio=0.3))
            if float(np.linalg.norm(p_now - plane.c2p(ts[k], 0))) >= 0.06:
                cur = DashedLine(p_now, plane.c2p(ts[k], 0), dash_length=0.08,
                                 color=th["dim"], stroke_width=2)
                curh = DashedLine(p_now, plane.c2p(0, vs[k]), dash_length=0.08,
                                  color=th["dim"], stroke_width=2)
                u.add(cur, curh)
                cursors.extend([cur, curh])
            u.add(dotk)
            segs_list.append(seg)
            dots.append(dotk)
            units.append(u)
        self._clear_ticks(ticks, segs_list + cursors,
                          [_pad_box(_box(xlab), AXIS_LABEL_PAD),
                           _pad_box(_box(ylab), AXIS_LABEL_PAD)], plane)

        # ---- 82-SD2b M2：连续位移是主运动，频闪影/数据点降为辅助 ----
        # 同一 ValueTracker（单位=秒）驱动：滑块位 → s=½at²（与 incline_slide_layout 同源）、
        # 接触点、v-t 线生长、图上游标。_fit 之后从静态件（斜面三角/坐标面）现算坐标尺。
        tr_t = ValueTracker(0.0)

        def ramp_ref():
            vs = ramp.get_vertices()
            x0v, y0v = float(vs[0][0]), float(vs[0][1])
            x1v, y1v = float(vs[1][0]), float(vs[1][1])
            k = math.hypot(x1v - x0v, y1v - y0v) / max(base, 1e-9)
            return x0v - k * x0, y0v - k * y0, k

        def dist_at(t):
            return 0.5 * acc * t * t

        def block_pt(t):
            d = d_start - dist_at(t) * k_s
            cx, cy, k = ramp_ref()
            return (cx + k * (x0 + d * math.cos(rad) + u_norm[0] * (bh / 2)),
                    cy + k * (y0 + d * math.sin(rad) + u_norm[1] * (bh / 2)), 0.0)

        def foot_pt(t):
            d = d_start - dist_at(t) * k_s
            cx, cy, k = ramp_ref()
            return (cx + k * (x0 + d * math.cos(rad)), cy + k * (y0 + d * math.sin(rad)), 0.0)

        # 82-SD2b 修正：tracker 单位是秒（0..ttot），_follow_uv/_grow_partial 的进度口径是
        # 0..1——先归一化再取点，否则 t>1 后全被 clamp 卡死（首轮冒烟实测滑块只动了 1/6 段）。
        def u_t():
            return tr_t.get_value() / max(ttot, 1e-9)

        _follow_uv(block, u_t, lambda u: block_pt(u * ttot))
        _follow_uv(live_dot, u_t, lambda u: foot_pt(u * ttot))

        line_t = [ttot * i / 48.0 for i in range(49)]
        # 折线按平面坐标现建（与 plane 同组随 _fit 等比缩放），生长用自身前缀裁剪。
        vline = VMobject(color=th["key"], stroke_width=5)
        vline.set_points_as_corners([plane.c2p(t, acc * t) for t in line_t])
        vline.set_stroke(th["key"], 5)
        _grow_partial(vline, u_t)
        live_cur = Dot([0.0, 0.0, 0.0], radius=0.09, color=th["accent"])

        def cur_pt(t):
            q = plane.c2p(t, acc * t)
            return (float(q[0]), float(q[1]), 0.0)

        live_cur.move_to(cur_pt(0.0))
        _follow_uv(live_cur, u_t, lambda u: cur_pt(u * ttot))
        graph.add(vline, live_cur)

        if units:
            ltxt = str(p.get("vt_label") or f"a = {acc:.2f} m·s⁻²")
            taken = ([_box(xlab), _box(ylab)] + graph_obstacles(plane, ticks)
                     + [_box(d) for d in dots])
            units[-1].add(_place_label(rich(ltxt, 24, th["key"]), segs_list[-1],
                                       plane, taken, [_sample(m, 24) for m in segs_list]))
            for u, kkey in zip(units, reveal_keys(p.get("at"), n)):
                tag_reveal(u, kkey)
        g = VGroup(left, graph, *units)
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        # M2 三段同时钟：滑块/接触点/v-t 线/游标一起走；每拍 2.6s（10s 镜 78% 覆盖，预算 80%）。
        # μ≥tanθ（acc=0）时滑块不动是物理正确：同一条拍只让 v-t 游标沿 t 轴走出 v≡0。
        beats = []
        for k, tgt in enumerate((ttot / 3.0, 2.0 * ttot / 3.0, ttot)):
            b = _mo.advance_to(
                tr_t, tgt, cue=k,
                note=("时钟演化：滑块沿斜面连续下滑 s=½at²，接触点与 v-t 线/游标同值源同步"
                      if acc > 1e-9 else
                      "时钟演化：a=0（μ≥tanθ）不滑——v-t 游标沿 t 轴走出 v≡0，静止是物理结论"))
            b.run_time = 2.6
            beats.append(b)
        _mo.mount_motion(g, beats)
        return g

    def _v_rod_rails(self, p, th):
        """单杆+导轨（82-SC）：真实装置图，杆按物理运动连续位移，Φ/E/I/F 同步读数。

        对照 82-D2「只能看到文字卡」的缺陷：这里画的是装置本身——双导轨、粗跨杆、接触点、
        ×/· 匀强场、左侧回路元件（电阻 R / 电容器 C）、电流方向；杆位由**同一个时钟**
        驱动（motion.advance_to），速度/安培力箭头长度 ∝ 物理量，右侧读数每帧从同一时刻
        求值——位移、箭头、读数三者同值源，不是分别对表。

        物理（三种模式都只做课本模型内）：
          capacitor：恒力 F ⇒ a = F/(m+B²L²C) 恒定，v=v0+at，I=CBL·a 恒定、Q=CBLv 累积；
          resistor：无外力自由减速 v=v0·e^(−t/τ)，τ=mR/(B²L²)，I=BLv/R 随 v 衰减；
          plain：按给定 v0/a 的匀变速，仅示动生电动势与（可选）回路电流。
        屏幕位移 = s(t)/s(T) 的等比映射；读数用真实时间 t 与真值，不拿屏幕像素冒充物理量。

        props: mode/capacitor|resistor|plain, B, L(切割长度), m, R, C, F(恒外力), v0, a,
               T(模拟窗口秒), x0(起点占轨长比例), travel(行程占轨长比例), rail(轨长 m),
               field="in"|"out", applied_force, beats(时钟拍数 2~6), at, label
        """
        mode = str(p.get("mode") or "plain").strip().lower()
        if mode not in ("plain", "resistor", "capacitor"):
            mode = "plain"

        def _pos(v, d):
            try:
                x = float(v)
            except (TypeError, ValueError):
                return d
            return x if math.isfinite(x) and x > 0 else d

        def _nonneg(v, d):
            try:
                x = float(v)
            except (TypeError, ValueError):
                return d
            return x if math.isfinite(x) and x >= 0 else d

        B = _pos(p.get("B"), 0.5)
        Lp = _pos(p.get("L"), 0.6)
        m = _pos(p.get("m"), 0.2)
        R = _pos(p.get("R"), 2.0)
        C = _pos(p.get("C"), 0.5)
        F_ext = _nonneg(p.get("F"), 1.0 if mode == "capacitor" else 0.0)
        applied = bool(p.get("applied_force", mode == "capacitor")) and F_ext > 0
        v0 = _nonneg(p.get("v0"), 0.0 if mode == "capacitor" else 4.0)
        tau = max(m * R / (B * B * Lp * Lp), 1e-6) if mode == "resistor" else 1.0
        if mode == "resistor":
            a = 0.0
        else:
            a = _nonneg(p.get("a"), F_ext / max(m + B * B * Lp * Lp * C, 1e-6)
                        if mode == "capacitor" else 0.8)
        if v0 <= 0 and a <= 0:
            a = 0.8
        TW = _pos(p.get("T"), 5.0)
        x0 = min(max(_nonneg(p.get("x0"), 0.10), 0.0), 0.30)
        travel = min(max(_pos(p.get("travel"), 0.78), 0.2), 0.9 - x0)
        rail_m = _pos(p.get("rail"), 2.0)
        field_in = str(p.get("field") or "in").strip().lower() != "out"

        def sim_s(t):
            if mode == "resistor":
                return v0 * tau * (1.0 - math.exp(-t / tau))
            return v0 * t + 0.5 * a * t * t

        def sim_v(t):
            if mode == "resistor":
                return v0 * math.exp(-t / tau)
            return v0 + a * t

        sT = max(sim_s(TW), 1e-9)
        v_peak = max(sim_v(0.0), sim_v(TW), 1e-9)

        def cur_i(v):
            if mode == "capacitor":
                return C * B * Lp * a
            return B * Lp * v / R if R > 0 else 0.0

        def amp_f(v):
            return B * cur_i(v) * Lp

        f_peak = max(amp_f(sim_v(0.0)), amp_f(sim_v(TW)), 1e-9)
        f_ref = max(f_peak, F_ext if applied else 0.0, 1e-9)

        tracker = ValueTracker(0.0)

        def frac(t):
            return x0 + travel * min(max(sim_s(t) / sT, 0.0), 1.0)

        # 静态骨架：导轨同时是动态层的坐标真源（_fit 缩放/位移后从它反算，见 _live_update）。
        X0, X1, YH = -3.75, 0.95, 0.95
        rail_top = Line([X0, YH, 0], [X1, YH, 0], color=th["dim"], stroke_width=4)
        rail_bot = Line([X0, -YH, 0], [X1, -YH, 0], color=th["dim"], stroke_width=4)

        def scale():
            return float(rail_top.get_length()) / (X1 - X0)

        def rod_x(t):
            return rail_top.get_start()[0] + frac(t) * (X1 - X0) * scale()

        g = VGroup()

        def area_build():
            yt = rail_top.get_center()[1]
            yb = rail_bot.get_center()[1]
            xl = rail_top.get_start()[0]
            w = max(rod_x(tracker.get_value()) - xl, 0.02)
            rect = Rectangle(width=w, height=max(yt - yb, 0.02), stroke_width=0)
            rect.set_fill(th["accent"], 0.08)
            rect.move_to([xl + w / 2, (yt + yb) / 2, 0])
            return rect

        g.add(_live_update(area_build))

        # 匀强场：× 向里 / · 向外（画在回路区域，杆与导轨压在上面）
        for r in range(3):
            yy = (1 - r) * 0.55
            for c in range(7):
                xx = X0 + 0.55 + c * (X1 - X0 - 1.0) / 6
                if field_in:
                    mk = T("×", font_size=30, color=th["warn"]).set_opacity(0.5).move_to([xx, yy, 0])
                else:
                    mk = Dot([xx, yy, 0], radius=0.07, color=th["warn"]).set_opacity(0.55)
                g.add(mk)

        g.add(rail_top, rail_bot)
        if mode == "capacitor":
            g.add(Line([X0, -YH, 0], [X0, -0.16, 0], color=th["dim"], stroke_width=4),
                  Line([X0, 0.16, 0], [X0, YH, 0], color=th["dim"], stroke_width=4),
                  Line([X0 - 0.36, 0.16, 0], [X0 + 0.36, 0.16, 0], color=th["key"], stroke_width=5),
                  Line([X0 - 0.36, -0.16, 0], [X0 + 0.36, -0.16, 0], color=th["key"], stroke_width=5))
            for sym, yy in (("+", 0.5 if field_in else -0.5), ("−", -0.5 if field_in else 0.5)):
                pm = rich(sym, 22, th["warn"]).move_to([X0 - 0.62, yy, 0])
                pm._placed = True
                g.add(pm)
        elif mode == "resistor":
            g.add(Line([X0, -YH, 0], [X0, -0.45, 0], color=th["dim"], stroke_width=4),
                  Line([X0, 0.45, 0], [X0, YH, 0], color=th["dim"], stroke_width=4),
                  Rectangle(width=0.4, height=0.9, color=th["key"], stroke_width=3).move_to([X0, 0, 0]))
        else:
            g.add(Line([X0, -YH, 0], [X0, YH, 0], color=th["dim"], stroke_width=4))
        if mode != "plain":
            elab = rich("C" if mode == "capacitor" else "R", 24, th["key"]).move_to([X0 - 0.62, 0, 0])
            elab._placed = True
            g.add(elab)

        # 电流方向：B 向里 ⇒ 杆内正电荷受力向上，电流沿上轨向左；B 向外反之。
        # 箭头挂在「左端元件 → 杆」这段回路的中点并随杆移动（t=0 时回路极窄，先隐藏），
        # 透明度跟随真实电流 I(t)/I_peak——电阻版减速时电流箭头随之变淡。
        top_sign = -1.0 if field_in else 1.0
        i_peak = max(cur_i(sim_v(0.0)), cur_i(sim_v(TW)), 1e-9)

        def current_build():
            s_ = scale()
            xl = rail_top.get_start()[0]
            yt = rail_top.get_center()[1]
            yb = rail_bot.get_center()[1]
            t = tracker.get_value()
            gap = rod_x(t) - xl
            xa = xl + gap / 2
            h = 0.18 * s_
            op = min(max(cur_i(sim_v(t)) / i_peak, 0.0), 1.0)
            grp = VGroup(
                Arrow([xa - h * top_sign, yt, 0], [xa + h * top_sign, yt, 0],
                      color=th["warn"], buff=0, stroke_width=4,
                      max_tip_length_to_length_ratio=0.5),
                Arrow([xa + h * top_sign, yb, 0], [xa - h * top_sign, yb, 0],
                      color=th["warn"], buff=0, stroke_width=4,
                      max_tip_length_to_length_ratio=0.5),
                rich("I", 20, th["warn"]).move_to([xa, yt + 0.26 * s_, 0]))
            grp.set_opacity(0 if gap < 0.55 * s_ or op < 0.04 else op)
            grp._live_state = round(op, 3)
            return grp

        g.add(_live_update(current_build))

        # 读数面板：静态标签/单位随 _fit 缩放；数值由同一个时钟逐帧重写，右对齐到固定列。
        # PX 与杆端 v 箭头尖（≤1.44）留出空隙：放 1.65 时杆到右端会与「实时读数」表头挤字。
        PX, TOP_Y, ROW_GAP = 1.95, 1.48, 0.44
        header = rich("实时读数", 21, th["key"])
        header.move_to([PX + header.width / 2, TOP_Y, 0])
        header._placed = True
        g.add(header)

        def px(dx):
            return header.get_left()[0] + dx * scale()

        def py(dy):
            return header.get_left()[1] - dy * scale()

        if mode == "capacitor":
            rows = [("v", "m·s⁻¹", lambda t: sim_v(t), 1),
                    ("E = BLv", "V", lambda t: B * Lp * sim_v(t), 1),
                    ("Φ = BLx", "Wb", lambda t: B * Lp * rail_m * frac(t), 2),
                    ("I = CBL·a", "A", lambda t: cur_i(sim_v(t)), 1),
                    ("Q = CU", "C", lambda t: C * B * Lp * sim_v(t), 1)]
        else:
            rows = [("v", "m·s⁻¹", lambda t: sim_v(t), 1),
                    ("E = BLv", "V", lambda t: B * Lp * sim_v(t), 1),
                    ("Φ = BLx", "Wb", lambda t: B * Lp * rail_m * frac(t), 2),
                    ("I = E/R", "A", lambda t: cur_i(sim_v(t)), 1),
                    ("F安 = BIL", "N", lambda t: amp_f(sim_v(t)), 1)]

        def num_field(getter, i, dec):
            def build():
                s_ = scale()
                cap = 99.9 if dec == 1 else 9.99
                val = min(max(float(getter(tracker.get_value())), 0.0), cap)
                txt = f"{val:.{dec}f}"
                pad = max(4 - len(txt), 0)
                chars = ("0" * pad) + txt[-4:]
                grp = VGroup(*[T(c, font_size=21 * s_, color=th["hi"]) for c in chars])
                grp.arrange(RIGHT, buff=0.012 * s_)
                grp.move_to([px(2.95) - grp.width / 2, py(0.52 + i * ROW_GAP), 0])
                for gg in grp[:pad]:
                    gg.set_opacity(0)
                grp._live_state = round(val, dec)
                return grp

            mob = _live_update(build)
            mob._placed = True
            return mob

        for i, (lab, unit, getter, dec) in enumerate(rows):
            yy = TOP_Y - 0.52 - i * ROW_GAP
            lm = rich(lab, 21, th["dim"])
            lm.move_to([PX + lm.width / 2, yy, 0])
            lm._placed = True
            um = rich(unit, 18, th["dim"])
            um.move_to([PX + 3.12 + um.width / 2, yy, 0])
            um._placed = True
            g.add(lm, um, num_field(getter, i, dec))

        note = rich(str(p.get("label") or ("磁场垂直纸面向里（×）" if field_in else "磁场垂直纸面向外（·）")),
                    18, th["dim"])
        if note.width > 3.9:
            note.scale_to_fit_width(3.9)
        note.move_to([PX + note.width / 2, TOP_Y - 0.52 - len(rows) * ROW_GAP - 0.08, 0])
        note._placed = True
        g.add(note)

        def rod_build():
            s_ = scale()
            t = tracker.get_value()
            x = rod_x(t)
            yt = rail_top.get_center()[1]
            yb = rail_bot.get_center()[1]
            return VGroup(Line([x, yb, 0], [x, yt, 0], color=th["key"], stroke_width=7),
                          Dot([x, yt, 0], radius=0.07 * s_, color=th["hi"]),
                          Dot([x, yb, 0], radius=0.07 * s_, color=th["hi"]))

        rod = _live_update(rod_build)
        g.add(rod)

        def mk_arrow(base, x_sign, y_off, mag_fn, peak, color):
            def build():
                s_ = scale()
                t = tracker.get_value()
                x = rod_x(t)
                y = base() + y_off * s_
                ln = max(1.05 * s_ * min(max(mag_fn(t) / peak, 0.0), 1.0), 0.05)
                ar = Arrow([x, y, 0], [x + x_sign * ln, y, 0],
                           color=color, buff=0, stroke_width=5,
                           max_tip_length_to_length_ratio=0.32)
                if mag_fn(t) <= 1e-9:
                    ar.set_opacity(0)
                return ar

            return _live_update(build)

        v_arrow = mk_arrow(lambda: rail_top.get_center()[1], 1, 0.40,
                           sim_v, v_peak, th["hi"])
        f_arrow = mk_arrow(lambda: rail_bot.get_center()[1], -1, -0.40,
                           lambda t: amp_f(sim_v(t)), f_peak, th["accent"])
        g.add(v_arrow, f_arrow)
        vlab = rich("v", 22, th["hi"])
        # 标签挂在箭头下方：杆到右端时箭头尖端已贴近右侧读数面板，放 RIGHT 会与表头挤成一行。
        vlab.add_updater(lambda mm: mm.next_to(v_arrow.get_end(), DOWN, buff=0.05))
        vlab._placed = True
        flab = rich("F安", 20, th["accent"])
        flab.add_updater(lambda mm: mm.next_to(f_arrow.get_end(), LEFT, buff=0.06))
        flab._placed = True
        g.add(vlab, flab)
        if applied:
            fapp = mk_arrow(lambda: rail_top.get_center()[1], 1, 0.92,
                            lambda t: F_ext, f_ref, th["warn"])
            g.add(fapp)
            falab = rich("F", 22, th["warn"])
            falab.add_updater(lambda mm: mm.next_to(fapp.get_end(), RIGHT, buff=0.06))
            falab._placed = True
            g.add(falab)

        try:
            n_beats = int(p.get("beats"))
        except (TypeError, ValueError):
            n_beats = 4
        n_beats = min(max(n_beats, 2), 6)
        keys = reveal_keys(p.get("at"), n_beats)
        beat_len = max(TW / n_beats, 1.0 / config.frame_rate)
        beats = []
        for k in range(n_beats):
            t_end = TW * (k + 1) / n_beats
            beat = _mo.advance_to(tracker, t_end,
                                  note=f"单杆时钟演化 → t={t_end:.2f}s（cue {keys[k]}）")
            # advance_to 在构造期读不到运行期当前值（四拍同时构造，cur 都是 0），
            # 显式按「一拍走 T/拍数」给 run_time，预算分配才与物理 1:1 同速。
            beat.run_time = beat_len
            beat._cue_key = keys[k]
            beats.append(beat)
        g._rod_tracker = tracker
        _mo.mount_motion(g, beats)
        return g

    def _v_trajectory(self, p, th):
        """运动轨迹（频闪照片式）：虚线轨迹 + 等时间间隔位置点 + 切向速度箭头，点逐个揭示。

        mode: projectile（抛体，angle=0 即平抛）/ circle（匀速圆周，速度沿切线）/
        cycloid（配速法：静止释放的匀速直线+匀速圆周合成摆线，arches 1~3 拱）。
        不画网格坐标——物理过程用物理模型图，读图象才用 graph_vt/axis_graph。
        """
        mode = str(p.get("mode") or "projectile")
        n = max(3, min(int(p.get("n", 6)), 9))
        show_v = bool(p.get("show_velocity", True))
        g = VGroup()
        if mode == "circle":
            R = 1.9
            g.add(DashedLine([0, 0, 0], [R, 0, 0], dash_length=0.1, color=th["dim"], stroke_width=2))
            circle = Circle(radius=R, color=th["dim"], stroke_width=2)
            g.add(circle)
            g.add(Dot([0, 0, 0], radius=0.06, color=th["dim"]), rich("O", 22, th["dim"]).move_to([-0.22, -0.22, 0]))
            u_pts = [k / n for k in range(n)]
            pts = [(R * math.cos(t), R * math.sin(t), -math.sin(t), math.cos(t))
                   for t in (2 * math.pi * k / n for k in range(n))]

            def pos_u(u, R=R):
                t = 2 * math.pi * u
                return R * math.cos(t), R * math.sin(t)

            def ref():
                c = circle.get_center()
                return float(c[0]), float(c[1]), float(circle.width) / (2.0 * R)
        elif mode == "cycloid":
            # 配速法：静止释放 → 匀速直线(圆心平移) + 匀速圆周 合成摆线；x=R(φ-sinφ)，y=-R(1-cosφ)
            arches = max(1, min(int(p.get("arches", 2)), 3))
            span = 2 * math.pi * arches
            s = 5.6 / span
            R = s
            ox = -span * s / 2
            def at(ph):
                return ox + R * (ph - math.sin(ph)), R * (1 - math.cos(ph)) * -1 + R
            base_line = Line([ox - 0.3, R, 0], [ox + span * s + 0.3, R, 0], color=th["dim"], stroke_width=3)
            g.add(base_line)
            path = VMobject(color=th["dim"], stroke_width=2)
            path.set_points_smoothly([[*at(ph), 0] for ph in np.linspace(0, span, 80)])
            trail = DashedVMobject(path, num_dashes=40)
            g.add(trail)
            u_pts = [k / (n - 1) for k in range(n)]
            pts = [(*at(ph), 1 - math.cos(ph), -math.sin(ph))
                   for ph in (span * k / (n - 1) for k in range(n))]

            def pos_u(u, ox=ox, R=R, span=span):
                ph = span * u
                return ox + R * (ph - math.sin(ph)), R * (1 - math.cos(ph)) * -1 + R

            def ref(ln=base_line, ox=ox, R=R, span=span):
                k = float(ln.get_length()) / max(span * s + 0.6, 1e-9)
                st = ln.get_start()
                return float(st[0]) - k * (ox - 0.3), float(st[1]) - k * R, k
        else:
            ang = math.radians(max(0.0, min(float(p.get("angle", 0)), 75.0)))
            vx, vy, gacc = math.cos(ang), math.sin(ang), 1.0
            T = (2 * vy / gacc) if vy > 0 else 1.6
            raw = [(vx * t, vy * t - 0.5 * gacc * t * t, vx, vy - gacc * t)
                   for t in (T * k / (n - 1) for k in range(n))]
            xs = [q[0] for q in raw]
            ys = [q[1] for q in raw]
            sx = 5.6 / max(max(xs) - min(xs), 1e-6)
            sy = 3.2 / max(max(ys) - min(ys), 1e-6)
            s = min(sx, sy)
            ox, oy = -(max(xs) + min(xs)) / 2 * s, -(max(ys) + min(ys)) / 2 * s
            pts = [(x * s + ox, y * s + oy, vxx, vyy) for x, y, vxx, vyy in raw]
            ground = min(q[1] for q in pts) - 0.1
            ground_line = Line([pts[0][0] - 0.5, ground, 0], [pts[-1][0] + 0.5, ground, 0],
                               color=th["dim"], stroke_width=3)
            g.add(ground_line)
            # 轨迹用同一 T 归一化采样：Create 的“画到哪”与小球位置同尺。
            path = VMobject(color=th["dim"], stroke_width=2)
            path.set_points_smoothly([[vx * t * s + ox, (vy * t - 0.5 * gacc * t * t) * s + oy, 0]
                                      for t in np.linspace(0, T, 40)])
            trail = DashedVMobject(path, num_dashes=30)
            g.add(trail)
            u_pts = [k / (n - 1) for k in range(n)]

            def pos_u(u, vx=vx, vy=vy, gacc=gacc, T=T, s=s, ox=ox, oy=oy):
                t = T * u
                return vx * t * s + ox, (vy * t - 0.5 * gacc * t * t) * s + oy

            def ref(ln=ground_line, x0=pts[0][0] - 0.5, y0=ground, x1=pts[-1][0] + 0.5):
                k = float(ln.get_length()) / max(x1 - x0, 1e-9)
                st = ln.get_start()
                return float(st[0]) - k * x0, float(st[1]) - k * y0, k
        units = []
        for x, y, ux, uy in pts:
            u = VGroup(Dot([x, y, 0], radius=0.11, color=th["key"]))
            sp = math.hypot(ux, uy)
            if show_v and sp > 1e-6:  # 摆线尖点速度为 0：只画点，不画零长箭头
                d = np.array([ux / sp, uy / sp, 0.0]) * (0.45 + 0.4 * sp if mode != "circle" else 0.8)
                u.add(Arrow([x, y, 0], [x + d[0], y + d[1], 0], color=th["warn"], buff=0, stroke_width=4))
            units.append(u)
        for u, k in zip(units, reveal_keys(p.get("at"), len(units))):
            tag_reveal(u, k)
        g.add(*units)

        # ---- 82-SD2b M2：小球沿真实轨迹连续运动；虚线轨迹随尾迹描出；点到即现 ----
        # 位置点/速度箭头保留逐条 reveal（n 与测试锁死），但透明度再按「球到没到」把关：
        # 球还没到就只留轨迹，不抢在运动前面把答案摆满屏。
        tr = ValueTracker(0.0)
        path_pts = [pos_u(i / 80.0) for i in range(81)]

        def scr(u):
            x, y = pos_u(u)
            cx, cy, k = ref()
            return (cx + k * x, cy + k * y, 0.0)

        if mode == "circle":
            trail = VMobject(color=th["accent"], stroke_width=4)
            _draw_on(trail, tr.get_value, 0.0, 1.0, path_pts, ref, th["accent"], 4)
            g.add(trail)
        else:
            _dashed_grow(trail, tr.get_value, path_pts, ref, th["dim"], 2.0,
                         40 if mode == "cycloid" else 30)
        ball = Dot([0.0, 0.0, 0.0], radius=0.12, color=th["accent"])
        ball.move_to(scr(0.0))
        _follow_uv(ball, tr.get_value, scr)
        g.add(ball)
        for uk, u in zip(u_pts, units):
            _opacity_gate(u, tr.get_value, max(uk - 0.05, 0.0), min(uk + 0.02, 1.0))
        if show_v:
            g.add(rich(str(p.get("v_label") or "v"), 24, th["warn"]).next_to(units[0], UP, buff=0.1))
        if p.get("label"):
            g = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
        beats = []
        for k, tgt in enumerate((1.0 / 3.0, 2.0 / 3.0, 1.0)):
            b = _mo.advance_to(
                tr, tgt, cue=k,
                note=("时钟演化：小球沿真实轨迹连续运动，轨迹随球尾迹描出，"
                      "位置点与切向速度箭头在球到达该点时出现"))
            b.run_time = 2.6
            beats.append(b)
        _mo.mount_motion(g, beats)
        return g

    def _v_mechanism(self, p, th):
        """有机化学推电子箭头机理图（81-S3；82-SB 锚点表统一坐标真源）：物种 + 键 + 孤对 + 弯月箭头，逐箭揭示。

        画法口径（mech_arrow_geom 钉死几何、mech_anchors 钉死锚点语义，这里是编排部分）：
          · 坐标真源=锚点表：先落物种字形（实测半宽半高），建原子/键/孤对锚点表 _ma.build_table，
            键线与弯箭头全部从表上取坐标——键线不再中心到中心（按两端字形缘截短，不穿字形、
            不触发挪字）；弯箭头尾在电子源（孤对点/键）、头在电子汇（原子缘/新键位）；
          · arrows/bonds 端点支持锚点引用：{"atom":i,"side"?,"gap"?} / {"bond":j,"frac"?,"offset"?} /
            {"lp":k}；裸 [x,y] 保留为兜底：落进原子字形盒归其中心，距锚点 < _ma.MECH_SNAP_RADIUS
            自动吸附；吸附不上原样保留并把端点距锚长度进 MECH_DRIFT（run.py 重放链转成
            MECH_ARROW_DRIFT finding，错位可报告化）；
          · 物种与箭标签打 _locked_anchor：81-S4 挪字机器对这些文本豁免（82D3 主因：挪字把原子
            从键线/弯箭头上搬走 20~122px）；物种间空间冲突改由布局阶段 _ma.spread_atoms 整体
            推开、越界兜底仍由 _fit 等比缩放负责——挪的是一整张图，不是把字从键上撕下来；
          · type="cov"（默认，电子对流向/异裂）全头双刺；type="hom"（单电子/均裂）鱼钩单刺；
          · 骨架不做完整骨架式渲染器：物种=文本节点（走 rich()，S5 电荷上标归一化自动生效，
            Cu²⁺/SO₄²⁻ 级排版 + TOFU 兜底），键=短线（order 1~3；kind="break" 断=warn 虚线、
            kind="form" 成=accent 虚线），孤对/电子源=成对小圆点 lps；
          · 分批揭示：一支箭头 = 一个揭示单元（曲线+箭刺+随箭出现的物种/键/孤对点，
            由 attach=箭下标绑定），at 数组长度 = 有效箭数（reveal_keys 口径，长度不符回均匀铺批）；
            不带 attach 的物种从 cue0 就在屏上（机理图的"地图"），caption 图注同旧口径追加。
        props: species:[{text, pos:[x,y]（缺省自动排位）, tone?, attach?, size?}]
               bonds:[{from|to: [x,y] | {"atom":i}, order?:1|2|3, kind?:"break"|"form", attach?}]
               lps:[{pos:[x,y], attach?}]
               arrows:[{from|to: {"atom":i,"side"?,"gap"?} | {"bond":j,"frac"?,"offset"?} | {"lp":k} | [x,y],
                        bulge?, type?:"cov"|"hom", label?, tone?}]
               at:[0~1 比例或字幕片段] × 有效箭数, label?: 图注。
        脏 props 兜底：pos 缺失的物种按行均布自动排位；端点解不出/退化的箭头跳过不画但占 attach 下标。
        """
        def _tone(t, fallback):
            return th.get(str(t or "").strip().lower(), th[fallback])

        g = VGroup()
        species = [s for s in (p.get("species") or []) if isinstance(s, dict)]
        bonds = [b for b in (p.get("bonds") or []) if isinstance(b, dict)]
        lps = [l for l in (p.get("lps") or []) if isinstance(l, dict)]
        arrows = [a for a in (p.get("arrows") or []) if isinstance(a, dict)]

        # 布局阶段①：物种字形先落位（实测字形半宽半高进锚点表），重叠原子整体推开；
        # 这些文本此后不再被任何挪字机器碰（_locked_anchor 豁免，82-SB）。
        placed = _ma.species_pos(species)
        sp_mobs, atoms = [], []
        for s, q in zip(species, placed):
            txt = str(s.get("text") or "")
            if not txt.strip() or q is None:
                continue
            mob = rich(txt, int(s.get("size") or 30), _tone(s.get("tone"), "fg"))
            mob.move_to([q[0], q[1], 0.0])
            mob._locked_anchor = True
            sp_mobs.append((mob, s.get("attach")))
            atoms.append({"text": txt, "pos": q, "half_w": mob.width / 2.0, "half_h": mob.height / 2.0})
        if len(atoms) >= 2:
            new_pos = _ma.spread_atoms(atoms)
            for (mob, _at), q in zip(sp_mobs, new_pos):
                mob.move_to([q[0], q[1], 0.0])
            for a, q in zip(atoms, new_pos):
                a["pos"] = q

        # 坐标真源：锚点表（原子=实测字形盒；键端点裸坐标落进原子盒自动归到该原子中心）
        table = _ma.build_table(atoms, bonds, lps)

        # 静态层：键线（从表上取**按字形缘截短后**的画线端点；先收集、仍垫在文本后面）
        bond_mobs = []
        for b, e in zip(bonds, table["bonds"]):
            if not e["valid"]:
                continue
            q0, q1 = e["draw"]
            if q0 is None or q1 is None:
                continue
            kind = str(b.get("kind") or "").strip().lower()
            color = _tone(b.get("tone"), "fg") if kind == "" else \
                th["warn"] if kind == "break" else th["accent"] if kind == "form" else _tone(None, "fg")
            cls = DashedLine if kind in ("break", "form") else Line
            try:
                order = max(1, min(int(b.get("order") or 1), 3))
            except (TypeError, ValueError):
                order = 1
            dx, dy = q1[0] - q0[0], q1[1] - q0[1]
            ln_ = math.hypot(dx, dy)
            if ln_ < 1e-9:
                continue
            nx, ny = -dy / ln_, dx / ln_
            offs = [0.0] if order == 1 else [-0.09, 0.09] if order == 2 else [-0.11, 0.0, 0.11]
            unit = VGroup(*[cls(np.array([q0[0] + nx * o, q0[1] + ny * o, 0.0]),
                                np.array([q1[0] + nx * o, q1[1] + ny * o, 0.0]),
                                color=color, stroke_width=4) for o in offs])
            bond_mobs.append((unit, b.get("attach")))
        lp_mobs = []
        for l, e in zip(lps, table["lps"]):
            q = e["pos"]
            if q is None:
                continue
            pair = VGroup(Dot(np.array([q[0] - 0.085, q[1], 0.0]), radius=0.05, color=th["accent"]),
                          Dot(np.array([q[0] + 0.085, q[1], 0.0]), radius=0.05, color=th["accent"]))
            lp_mobs.append((pair, l.get("attach")))

        # 揭示层：一支箭头一个单元，attach==i 的物种/键/孤对点随第 i 支箭同批淡入
        # （i 按**声明**的 arrows 下标计，退化箭跳过不占单元但占下标，attach 语义不漂移）
        units = []
        unit_by_decl = {}
        arcs_report = []
        for i, a in enumerate(arrows):
            q0, q1, h0, h1 = _ma.resolve_arrow(a, table)
            for key, xy, how in (("from", q0, h0), ("to", q1, h1)):
                if xy is None:
                    continue
                d = _ma.anchor_distance(xy, table)
                if d > _ma.MECH_ANCHOR_THRESH:   # 端点锚定断言：超差=弧要指空，记账给重放链
                    MECH_DRIFT.append((f"arrows[{i}].{key}[{how}]", round(d, 3)))
            geom = mech_arrow_geom(q0, q1, a.get("bulge"),
                                  full_head=str(a.get("type") or "cov").strip().lower() != "hom") \
                if (q0 is not None and q1 is not None) else None
            if geom is None:      # 退化/脏箭头（端点解不出或起终点重合）：跳过不画，零长箭不上屏
                continue
            color = _tone(a.get("tone"), "accent")
            curve = CubicBezier(*[np.array([x, y, 0.0]) for x, y in geom["ctrl"]],
                                stroke_color=color, stroke_width=4)
            u = VGroup(curve)
            for (bx, by), (ex, ey) in geom["barbs"]:
                u.add(Line(np.array([bx, by, 0.0]), np.array([ex, ey, 0.0]),
                           color=color, stroke_width=4))
            lab = str(a.get("label") or "")
            if lab:
                lm = rich(lab, 22, color).move_to([geom["apex"][0], geom["apex"][1] + 0.32, 0.0])
                lm._locked_anchor = True     # 箭标签钉在弧顶，同样不进挪字机器（82-SB）
                u.add(lm)
            arcs_report.append({"arrow": i, "from": q0, "to": q1, "how": [h0, h1]})
            unit_by_decl[i] = u
            units.append(u)
        keys = reveal_keys(p.get("at"), len(units))
        if len(units) >= 2:
            for u, k in zip(units, keys):
                tag_reveal(u, k)
        for mob, at in sp_mobs + bond_mobs + lp_mobs:
            try:
                j = int(at)
            except (TypeError, ValueError):
                j = -1
            if j >= 0 and j in unit_by_decl and len(units) >= 2:
                unit_by_decl[j].add(mob)
            else:
                g.add(mob)
        g.add(*units)
        # 锚点表随块下发：冒烟量测/重放断言与渲染共用同一份真源，不再各处重算坐标
        g._mech_table = {"atoms": [{"text": a["text"], "pos": a["pos"],
                                    "half_w": a["half_w"], "half_h": a["half_h"]} for a in atoms],
                         "bonds": [{"valid": e["valid"], "a": e["a"], "b": e["b"],
                                    "mid": e["mid"], "draw": e["draw"]}
                                   for e in table["bonds"]],
                         "lps": [{"pos": e["pos"]} for e in table["lps"]],
                         "arcs": arcs_report}
        if p.get("label"):
            outer = VGroup(g, rich(str(p["label"]), 24, th["key"])).arrange(DOWN, buff=0.25)
            outer._mech_table = g._mech_table
            g = outer
        return g

    BUILDERS = {
        "axis_graph": "_v_axis_graph",
        "particle_box": "_v_particle_box",
        "microstate": "_v_microstate",
        "energy_dist": "_v_energy_dist",
        "stat_chart": "_v_stat_chart",
        "mind_map": "_v_mind_map",
        "table": "_v_table",
        "force_diagram": "_v_force_diagram",
        "field": "_v_field",
        "circuit": "_v_circuit",
        "optics": "_v_optics",
        "incline": "_v_incline",
        "trajectory": "_v_trajectory",
        "rod_rails": "_v_rod_rails",
        "mechanism": "_v_mechanism",
        "title": "_v_title",
        "formula": "_v_formula",
        "callout": "_v_callout",
        "steps": "_v_steps",
        "summary": "_v_summary",
        "compare": "_v_compare",
        "graph_vt": "_v_graph_vt",
        "figure": "_v_figure",
        "derivation": "_v_derivation",
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
            # 81-S4：锁定图元里的裸放置标签不许动画法，只在装配层做"只挪字"的全量复核；
            # 走 _place_label 的图线标签（_placed）、刻度数字（_tick_*）与 82-SB mechanism 锚锁定文本
            # （_locked_anchor——挪原子=错位根源）已在各自机器里钉死/豁免，复核跳过。
            PLACEMENTS.extend(_resolve_label_clashes(m))
            blocks.append(m)
        # 第四轮 F-5（评审 A D3、B 复检1）：不带内部揭示标记的正文块此前随整镜在 t=0
        # 一次铺满——20 个镜次从头到尾画面不变（占比 13%~49%）。steps/summary/callout 早
        # 就按行分批，剩下这些"整块"按镜内进度依次进场，口径与 _tag_progressive 一致
        # （行序比例映射到既有字幕下标，不引入新时长）。已自带逐行揭示的块不接管：
        # 两层揭示会互相屏蔽，反而把逐行降级成逐块。
        # 82-SD1a（M0 §6.2）：已挂 motion beats 的块同样不接管——整块淡入与过程动画互斥。
        plain = [i for i, m in enumerate(blocks)
                 if not any(getattr(x, "_reveal_at", None) is not None for x in m.get_family())
                 and not getattr(m, "_motion_steps", None)]
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
            # 82-SD1b：推导飞入已完全收进 _motion_steps beats（_ValueFly），
            # 这里不再对 _derivation_fly 补播第二套动画（同一 mobject 同一 cue 只许一套）。
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
            # 82-SD1b：已挂 motion beats 的块自带逐拍编排，不再补整块 Indicate——
            # 否则 cue0 先被借走 ≤0.5s，短 cue 会把「书写第一式」那一拍挤到丢帧。
            if getattr(blk, "_motion_steps", None):
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

    def _bind_motions(self, body, cues):
        """82-SD1a 运动播放段第一步：把 builder 挂来的 beats/spec 换算成 cue→beats 分发表。

        两种挂载（motion.py mount_motion/take_motion 协议）：
          · ``_motion_steps``：builder 直挂的现成 beats（后续棒用，本棒 M6 不走这条）；
          · ``_reveal_motion``：本棒文本要点 kind 挂的"揭示规格"——beats 必须等 _fit
            定稿几何后再由 motion.reveal(animate_in=False) 产出（构造期几何未定，见
            _mount_text_reveal），产完就地销毁 spec，一镜一次。
        cue 绑定（讲到哪动到哪，Plan_82 §3）：beat.cue 是显式字幕下标；``_cue_key`` 沿用
        _reveal_at 同一把尺（reveal_cue_index：0~1 行序比例或字幕片段），对不上口播的
        beats 进 loose 表由镜尾兜底段按序播（82-M0 §6.4 引擎兜底口径）——绝不静默丢。
        返回 ({cue: [beats]}, loose beats)。
        """
        by_cue: dict[int, list] = {}
        loose: list = []
        aux: dict[int, object] = {}   # 运动拍引入的辅助图元（高亮带），镜尾统一清理
        for m in body.get_family():
            spec = getattr(m, "_reveal_motion", None)
            mounted = _mo.take_motion(m)
            if spec is None and not mounted:
                continue
            if spec is not None:
                beats = _mo.reveal(spec["units"], run_time=spec["run_time"],
                                   emphasis=spec["emphasis"], emphasis_color=spec["color"],
                                   cue_from=None, animate_in=False, read_along=True)
                for b, k in zip(beats, spec["keys"]):
                    b._cue_key = k
                    # 「口播多久、色带就走多久」：单拍时长跟随该 cue 的朗读窗口（留 0.25s
                    # 给字幕淡入淡出），而不是固定 1s 让后半句干等。play_motion 仍按真实
                    # 窗口再裁一次，短 cue 自动压缩。
                    idx_k = reveal_cue_index(k, cues) if cues else None
                    if idx_k is not None:
                        cue_sec = cues[idx_k]["end"] - cues[idx_k]["start"]
                        b.run_time = max(0.6, min(cue_sec - 0.25, 2.0))
                if spec.get("sweep"):
                    beats = beats + _mo.draw(VGroup(*spec["units"]), mode="flow",
                                             run_time=SWEEP_RUN_SEC, time_width=0.45,
                                             color=spec["color"], cue=None,
                                             note="镜尾回扫：已讲条目按顺序再过一遍（复盘动线）")
                del m._reveal_motion
                mounted = mounted + beats
            for b in mounted:
                idx = None
                if b.cue is not None:
                    idx = min(max(int(b.cue), 0), max(len(cues) - 1, 0))
                else:
                    key = getattr(b, "_cue_key", None)
                    if key is not None and cues:
                        if isinstance(key, (int, float)) and not isinstance(key, bool):
                            key = float(key)   # 与 tag_reveal 同尺：JSON int → float 行序比例
                        idx = reveal_cue_index(key, cues)
                if idx is None:
                    loose.append(b)
                else:
                    by_cue.setdefault(idx, []).append(b)
                for x in getattr(b, "_aux", ()) or ():
                    aux[id(x)] = x
        return by_cue, loose, list(aux.values())

    def _render_shot(self, shot, plan, is_first=False, is_last=False):
        th = THEMES.get(plan["brief"]["style"], THEMES["clean"])
        body, stack, _corners = self._assemble(shot, plan, th, is_first, is_last)

        # Brief.subtitles=False 时画面不带内嵌字幕（留给外挂 srt / 烧录那一层去做）。
        # 揭示节奏仍按口播字幕时间轴走（否则 steps/compare 整镜全显），subtitles=False 时只是不把字幕画上屏。
        cues = fit_cues(shot.get("subtitles", []), float(shot["seconds"]))
        show_caps = plan.get("brief", {}).get("subtitles", True)
        reveals, revealed_all = collect_reveals(body, cues)
        # 82-SD1a：builder 经 mount_motion/_reveal_motion 挂来的运动 beats 按 cue 落位。
        motions, loose_beats, motion_aux = self._bind_motions(body, cues)

        # 帧精确记账：manim 会把每个 play() 的 run_time 向上取整到整帧（实测每次 +0.01s，
        # 49 条字幕 × 3 段 + 镜头首尾 ≈ 160 段 → 成片比 Plan 长 0.6s，字幕与配音错开）。
        # 因此这里一律以"整帧数"驱动动画，并把取整误差留在 tail 里吸收，
        # 使每镜实际帧数 == round(seconds × fps)，音画轴与 IR 轴保持重合。
        fps = config.frame_rate
        total_frames = int(round(shot["seconds"] * fps))

        def _mrt(n: int) -> float:
            # 82-SD1a 帧精度：manim 用 np.arange(0, run_time, 1/fps) 采样，run_time 恰为
            # 23/15、31/15 这类值时浮点误差会多进 1 帧（实测 3 镜 42s 片长 42.53s）。
            # 动画类 play 一律把 run_time 压到整帧数下方 1e-3 帧；wait 走 freeze 分支的
            # int(duration/dt) 截断，不受影响，故 hold() 保持 n/fps 不动。
            return max(int(n) - 0.001, 0.0) / fps
        outro_f = min(int(round(OUTRO * fps)), total_frames - 1)
        consumed = 0
        # 强调动效帧预算：最多借 FX_MAX_SEC 的既有 hold/停留帧（并至少留 2 帧给 play），
        # 镜头窗口不够就压缩 run_time——动效从不新增镜头时长。
        fx_cap = max(int(round(FX_MAX_SEC * fps)), 2)

        # ---- 82-SD1a 运动播放段记账（借帧纪律与上面同源：只借 hold 帧、整帧对齐） ----
        shot_no = getattr(self, "_shot_seq", -1) + 1
        self._shot_seq = shot_no
        ledger = getattr(self, "_motion_ledger", None)
        if ledger is None:
            ledger = self._motion_ledger = []
        # 单镜动效总借帧 ≤ total_frames×MOTION_BUDGET_RATIO（D4 §4.2-3 / 82-M0 §6.1）；
        # 超预算按契约降级并逐条记账，绝不静默全丢。
        motion_budget = int(round(total_frames * MOTION_BUDGET_RATIO))
        motion_spent = 0

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

        def record(status: str, beat, frames: int, cue) -> None:
            ledger.append({"shot": shot_no, "cue": cue,
                           "note": getattr(beat, "note", "") or "",
                           "status": status, "frames": int(frames)})

        def rescue_targets(beat) -> None:
            """降级兜底：被丢 beat 若是「让内容出现」的引入动画（FadeIn 族），
            直接 add 目标——内容可见性优先于动画，绝不允许某行整镜不出现（评审 D9 同族）。"""
            for a in getattr(beat, "anims", ()):
                if type(a).__name__ in ("FadeIn",) and getattr(a, "mobject", None) is not None:
                    self.add(a.mobject)

        def play_motion(beats, window: int, cue=None) -> int:
            """运动播放段核心：一拍一 play、run_time 走 motion.snap_run_time 整帧对齐
            （QUALITY_FPS 15/30 同一把尺），只借 window 帧内的既有 hold。
            降级契约（任务书 §1）：窗口/预算放不下时——
              · 语义最强 beat 优先（含「揭示」的当前条强调拍 > 纯压暗拍，稳定排序）；
              · 能塞下的先按整帧压缩播（scaled），塞不下的丢（dropped）并 rescue 内容；
              · 每一拍的去留都写 _motion_ledger，镜尾对 stderr 记账告警——不静默全丢。
            返回剩余窗口帧数。"""
            nonlocal consumed, motion_spent
            # 同 cue 多拍分配：时钟演化（物理过程连续性）优先，其次揭示拍，最后压暗拍。
            # 每拍至少给后面的拍留 MOTION_WINDOW_MIN_F 帧——否则先播的揭示/强调拍吃满窗口，
            # 同一 cue 里的时钟拍会整拍丢掉，杆停在原地、读数与口播脱节（SC 冒烟实测）。
            ordered = sorted(beats, key=lambda b: 0 if "时钟演化" in (b.note or "")
                             else 1 if "揭示" in (b.note or "") else 2)
            left = window
            for b in ordered:
                if not b.anims:
                    record("empty", b, 0, cue)
            active = [b for b in ordered if b.anims]
            for pos, b in enumerate(active):
                need = max(MOTION_WINDOW_MIN_F, int(round(_mo.snap_run_time(b.run_time) * fps)))
                room = min(left, motion_budget - motion_spent)
                if room < MOTION_WINDOW_MIN_F:
                    record("dropped", b, 0, cue)
                    rescue_targets(b)
                    continue
                rest = len(active) - pos - 1
                cap = max(room - MOTION_WINDOW_MIN_F * rest, MOTION_WINDOW_MIN_F)
                rt_f = min(need, cap)
                self.play(*b.anims, run_time=_mrt(rt_f))
                consumed += rt_f
                motion_spent += rt_f
                left -= rt_f
                record("played" if rt_f >= need else "scaled", b, rt_f, cue)
            return max(left, 0)

        # ---- 开场：INTRO 硬切升级——上一镜暂存的旧内容在这里 yield_to 新内容 ----
        # 「它不是消失了，它是变成了下一个」（六律⑥）；窗口不够则硬切移除并记账（回退路径）。
        intro_f = frames_at(INTRO)
        pend = getattr(self, "_yield_pending", None)
        self._yield_pending = None
        yielded = False
        if pend is not None and intro_f == 0:
            old_stack, old_revealed = pend
            w0 = frames_at(cues[0]["start"]) if cues else 0
            f = min(w0, fx_cap, max(motion_budget - motion_spent, 0))
            if f >= MOTION_WINDOW_MIN_F and (
                    old_stack.family_members_with_points() or old_revealed):
                body.remove(stack)                     # 新 stack 由 transform 引入
                self.add(body)
                beat = _mo.yield_to(old_stack, stack, run_time=_mrt(f))[0]
                self.play(*beat.anims,
                          *[FadeOut(m, shift=DOWN * 0.6) for m in old_revealed],
                          run_time=_mrt(f))
                consumed += f
                motion_spent += f
                body.add(stack)
                record("yield", beat, f, None)
                yielded = True
            else:
                self.remove(old_stack, *old_revealed)
                record("yield_hard", _mo.MotionBeat([], note="开场窗口不足：旧内容硬切移除（回退记账）"),
                       0, None)
        elif pend is not None:
            # 遗留软边界（INTRO>0）路径不会消费 yield_pending：旧内容必须显式移除，
            # 否则它会永远留在画面上（默认 INTRO=0 走不到，防御分支）。
            self.remove(pend[0], *pend[1])
        if not yielded:
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
                # 运动播放段（无字幕路径同样生效）：预算够时留 1 帧收尾 hold，
                # 但 fx_n 已吃满窗口时不能再借（否则每 cue 多 1 帧、成片比 Plan 长）。
                reserve = 1 if remain - fx_n >= 1 else 0
                left = play_motion(motions.get(i, ()), max(remain - fx_n - reserve, 0), cue=i)
                hold(left + reserve)
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
            # 运动播放段：本 cue 的 beats 在揭示淡入与通用 fx 之后、按剩余 hold 窗口播放；
            # 讲到哪条哪条亮（cue 绑定在 _bind_motions 完成），窗口不足整帧压缩或降级记账。
            mid2 = play_motion(motions.get(i, ()), mid - fx_n, cue=i)
            hold(mid2)
            anim(cap, False, fo)

        # ---- 镜尾：无 cue/对不上口播的 beats 兜底段（82-M0 §6.4），再升级边界硬切 ----
        tail = total_frames - outro_f - consumed
        exit_f = 0
        if outro_f == 0 and tail >= 4:
            # 退场预留：≤FX_MAX_SEC 且至少留 2 帧收尾 hold
            exit_f = min(fx_cap, max(motion_budget - motion_spent, 0), tail - 2)
            if exit_f < MOTION_WINDOW_MIN_F:
                exit_f = 0
        if loose_beats:
            play_motion(loose_beats, max(tail - exit_f - 1, 0), cue=None)
            tail = total_frames - outro_f - consumed
            exit_f = min(exit_f, max(tail - 2, 0))
        if outro_f > 0:
            # 遗留软边界配置：保持整帧淡出行为（默认 OUTRO=0 不走这支）。
            hold(tail)
            anim(body, False, outro_f, revealed_all)
        elif exit_f >= MOTION_WINDOW_MIN_F:
            # 边界硬切升级（任务书 §1）：内容 stack+已揭示行播 exit_stage 方向性退场——
            # 「旧内容把位置让给下一镜」可见（带方向 FadeOut，不留残影）；
            # 页眉/角标属 ELEMENT_EXEMPT 固定件，仍随帧边界硬切。
            beat = _mo.exit_stage([stack, *revealed_all, *motion_aux], direction=DOWN,
                                  run_time=_mrt(exit_f))[0]
            self.play(*beat.anims, run_time=_mrt(exit_f))
            consumed += exit_f
            motion_spent += exit_f
            record("exit", beat, exit_f, None)
            hold(max(tail - exit_f, 0))
            # exit_stage 的 FadeOut(stack) 收尾时会对 stack 调 scene.remove()，manim 会
            # 把含 stack 的 body 就地拆成 [页眉, 学科标签, 角标]——此后 remove(body) 是空操作，
            # 页眉会带进下一镜（82-SD2a1 冒烟实测镜首出现两行页眉叠字）。按家族逐个移除，
            # 拆散与否都能把本镜固定件硬切干净。
            self.remove(*body.get_family())
        elif tail < MOTION_WINDOW_MIN_F + 2 and (
                stack.family_members_with_points() or revealed_all):
            # 尾部放不下退场：旧内容暂存给下一镜开场 yield_to（画面不空切、帧数不越界）。
            hold(max(tail, 0))
            for x in list(body.submobjects):
                if x is not stack:
                    self.remove(x)
            self._yield_pending = (stack, list(revealed_all))
            record("pending_yield", _mo.MotionBeat([], note="镜尾帧预算不足：旧内容暂存待下一镜换位"),
                   0, None)
        else:
            hold(tail)
            self.remove(body, *revealed_all)
        if motion_aux:
            self.remove(*motion_aux)   # 高亮带不跨镜：pending_yield/软边界也一并清掉

        # 降级可观测（任务书 §1「不许静默全丢」）：只要有 dropped/pending 就落一行 stderr。
        degraded = [e for e in ledger if e["shot"] == shot_no
                    and e["status"] in ("dropped", "yield_hard", "pending_yield")]
        if degraded:
            print(f"[motion] 镜{shot_no}: {len(degraded)} 拍降级（窗口/预算不足，"
                  "已记账并保内容可见；时长不变）", file=sys.stderr)
