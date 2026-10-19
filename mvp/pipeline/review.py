"""A4 风格监督（静态）：Plan 出片前的确定性闸门。

只打回、不改写（Spec_Workflow 第 1 节）。检查项对应 Spec_Workflow A4 的 ①~⑤。
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import font_metrics as _fm  # noqa: E402  纯标准库：不破坏本文件「不 import scene/manim」的纪律

from .ir import (ACCEPTABLE_RATE, BUDGET_REF_KIND, FAST_CPS, GRAPHIC_KINDS, MAX_CAP_UNITS, MAX_TTS_RATE,
                 MIN_SHOT_SECONDS, NATURAL_CPS, RATE_FACTOR, SHOT_HEAD, SHOT_TAIL, SPEED_LADDER,
                 VISUAL_KINDS, Plan, Shot, cap_width, num)

# 版面高度模型（Manim 单位，帧高 8）：底部字幕带 1.05，顶部页眉 0.6
FRAME_H = 8.0
SUBTITLE_BAND = 1.05
HEADER_BAND = 0.60
USABLE_H = FRAME_H - SUBTITLE_BAND - HEADER_BAND

MAX_SHOT_SHARE = 0.25
MAX_SHOT_SHARE_HARD = 0.35

# 可读性下限：渲染层会把超宽文本整条缩进安全宽，缩到看不清就成了一片细线
# （batch_v4 的先修条实测：60 字挤一行，字号掉到 18px）。
SAFE_WIDTH = 12.4
CALLOUT_PAD = 0.6
CALLOUT_FS = 32.0
MIN_LEGIBLE_FS = 24.0
# 与 render/scene.py 的 CALLOUT_FS / CALLOUT_PAD / SAFE_WIDTH 同一把尺子（SubTask #60-D 去框化注释）：
# scene 的 callout 去掉了框线，但字号与内宽预算不变——闸门说放行、渲染就必须放得进。
# scene 的「 · 」断行用 CALLOUT_SPLIT_FS=28 起排，本文件仍用 CALLOUT_FS 估宽再等比换算（数学等价）。
# 出处角标那一档（第四轮 F-1）：与 scene.py 的 REF_FS / REF_WIDE / REF_MIN_FS 同步，改一处要改两处。
# v7 的两个 G3 命中（ell 出处行 12px、ua 14px）就是从这条漏出去的——原来的 LEGIBLE 只挂在
# callout 分支里，出处行/角标这条路径**根本没有闸门**，所以 8 条 review.json 才会全是 []。
REF_FS = 18.0
REF_WIDE = SAFE_WIDTH
REF_MIN_FS = 15.0
# figure 原语支持的图形；scene._v_figure 一一对应，加一种要两边同步。
FIGURE_SHAPES = {"ellipse", "right_triangle", "chord"}

# 物理图示的方向词与元件类型（与 render/scene.py 的 _FORCE_DIRS / circuit 符号同源）。
_FORCE_DIRS = {"up", "down", "left", "right", "upleft", "upright", "downleft", "downright"}
_FIELD_MODES = {"region", "wire", "magnet"}
_CIRCUIT_TYPES = {"battery", "resistor", "switch", "bulb", "ammeter", "voltmeter"}
_OPTICS_MODES = {"mirror", "refract", "lens", "image"}
_INCLINE_DIRS = {"normal", "into", "along_up", "along_down"}
_TRAJECTORY_MODES = {"projectile", "circle", "cycloid"}

# 检查码清单（第四轮 F-8）：`review.json = []` 在 v7 里同时可能是"全绿"和"根本没跑"，
# 两位评审各记一次（A D14 / B D-03）。交付件改成 {checked:[码], violations:[...]}，
# 空 violations 从此只在"这些码确实跑过"的意义下才算通过。
# 这份清单由 test_review.py 与源码对撞（扫 add(...) 里真实出现的码），加检查忘登记会被测出来。
CODES = (
    "AXIS_LABEL", "COUNT", "DUR_SHARE", "DUR_SHORT", "GLYPH", "KIND", "LEGIBLE",
    "MISSING_QUALIFIER", "NO_FIGURE", "NO_REF", "OVERLOAD", "PACING", "QUALIFIER_LOSS",
    "SAFE_AREA", "SUB_OVERLAP", "SUB_RANGE", "SUB_WIDTH", "TARGET", "TERM",
)

# 32 号字下 1 个 cap_width 单位的场景单位宽，按新字体栈（SimSun + Times New Roman）分字符实测：
#   CJK/全角 =0.44（10 汉字实测 4.3958）；ASCII 上包络 0.50（全库 55 行出处折行实测 ≤0.49，
#   含空格/标点拉低均值）。估算只许偏宽不许偏窄：偏窄会让 A4 漏报，test_refs.py 的实测断言会抓住。
# 移植阻断项 ③：估宽与字体强绑定，唯一事实源在 font_metrics.CALIBRATED；下面两个常量只是
# SimSun 表项别名（本机 Windows 口径不变），_est_width 运行时按 MVP_TEXT_FONT/MVP_LATIN_FONT 查表，
# 未标定字体直接抛 FontMetricsError——闸门不许拿别家字体的旧值估宽。
_UNIT_M = _fm.CALIBRATED[(_fm.DEFAULT_TEXT_FONT, _fm.DEFAULT_LATIN_FONT)]
UNIT_CJK = _UNIT_M["UNIT_CJK"]
UNIT_ASCII = _UNIT_M["UNIT_ASCII"]

# 出处折行的断点纪律：与 scene._wrap_ref 同源（改一处要改两处）。句读优先、括号内部禁断、
# 行尾不留开括号或运算符——否则公式被劈开，比缩字号更糟。
REF_SEPS = ("；", "：", "。", "，", "、", "）", " ", "—", "·", "/")
REF_STRONG = ("；", "：", "。", "，", "、")
REF_ATTACH_LEFT = "；：。，、）》」』—·"
REF_OPEN = "（(《「『[［"
REF_CLOSE = "）)》」』]］"
REF_EDGE_BAD = REF_OPEN + "=+_^/·—"


def _est_width(txt: str, fs: float) -> float:
    """分字符宽度估算（纯标准库，不 import scene/manim）：CJK 与 ASCII 各用自己的实测系数。

    系数按当前字体对查 font_metrics 表（阻断项③）；未标定字体抛 FontMetricsError，
    闸门宁可拒绝出片也不许用错字体的旧值估宽。
    """
    m = _fm.metrics_for()
    cjk = sum(1.0 for c in str(txt) if not c.isascii())
    asc = sum(0.5 for c in str(txt) if c.isascii())
    return (cjk * m["UNIT_CJK"] + asc * m["UNIT_ASCII"]) * fs / 32.0


def _ref_cut(text: str) -> list[str]:
    """一条过长的出处 → 最多两行。断点纪律与 scene._wrap_ref 一致，宽度用估算替代实测。"""
    cands = []
    mid = len(text) / 2
    for i, ch in enumerate(text):
        if i == 0 or ch not in REF_SEPS:
            continue
        depth = sum(1 for c in text[:i] if c in REF_OPEN) - sum(1 for c in text[:i] if c in REF_CLOSE)
        if depth > 0:
            continue
        cut = i + 1 if ch in REF_ATTACH_LEFT else i
        left, right = text[:cut].rstrip(), text[cut:].lstrip()
        if not left or not right or left[-1] in REF_EDGE_BAD or right[0] in REF_ATTACH_LEFT:
            continue
        cands.append((0 if ch in REF_STRONG else 1, abs(len(left) - mid), left, right))
    if not cands:
        return [text]
    cands.sort()
    fallback = None
    for _, _, left, right in cands:
        wide = max(_est_width(left, REF_FS), _est_width(right, REF_FS))
        if wide <= REF_WIDE:
            return [left, right]
        if fallback is None or wide < fallback[0]:
            fallback = (wide, left, right)
    return [text] if fallback is None else [fallback[1], fallback[2]]

# 本机字体栈实测缺字形的字符（Schedule C7 的字形结论）：Unicode 上/下标**字母**。
# 数字下标 ₀₁₂ 与上标 ⁻¹²³、Δ、·、² 都有字形，不在黑名单内。
TOFU = set("ₐₑₔₕᵢⱼₖₗₘₙₚₛₜᵤᵥₓ"
           "ᵃᵇᶜᵈᵉᵍⁱʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ")


def _mag_findings(kind: str, forces: list) -> list[str]:
    """forces[].mag（79-C1b）：可选的相对大小，scene._force_lengths 按它让箭长成比例。
    给了必须是有限正数；同一图要么全给要么全不给（混给时 scene 把缺 mag 的力画成最长，比例就失真了）。"""
    msgs = []
    given = [f for f in forces if f.get("mag") is not None]
    for f in given:
        m = f.get("mag")
        if isinstance(m, bool) or not isinstance(m, (int, float)) or not math.isfinite(m) or m <= 0:
            msgs.append(f"{kind} 的力「{_text(f.get('name'))}」mag 非法（{m!r}），必须是有限正数（力的相对大小）")
    if given and len(given) < len(forces):
        miss = "、".join(_text(f.get("name")) or "?" for f in forces if f.get("mag") is None)
        msgs.append(f"{kind} 的 mag 要么全给要么全不给：{miss} 缺 mag，箭头长度会失去比例")
    return msgs


def _across_finding(e: dict, elems: list) -> str | None:
    """电压表 across（79-C1b）：口径与 scene._voltmeter_target 一致——
    int 为 elements 下标（与 scene 一样只数 dict 元件），str 依次匹配 label 或 type（取第一个命中的非电压表元件）。
    闸门比渲染层更严：被测元件必须存在且不是电表（scene 遇到非法值会静默退回默认跨接）。"""
    acr = e.get("across")
    if acr is None:
        return None
    meters = ("ammeter", "voltmeter")
    if isinstance(acr, int) and not isinstance(acr, bool):
        if not 0 <= acr < len(elems):
            return f"circuit 电压表 across={acr} 越界：本电路只有 {len(elems)} 个元件（下标从 0 起）"
        t = elems[acr]
    elif isinstance(acr, str) and acr.strip():
        t = next((x for x in elems if _text(x.get("type")) != "voltmeter"
                  and (_text(x.get("label")) == acr or _text(x.get("type")) == acr)), None)
        if t is None:
            t = next((x for x in elems if _text(x.get("label")) == acr), None)
        if t is None:
            return f"circuit 电压表 across「{acr}」不是本电路任何元件的 label 或 type"
    else:
        return f"circuit 电压表 across 必须是元件下标（整数）或元件 label，当前 {acr!r}"
    if _text(t.get("type")) in meters:
        return f"circuit 电压表 across 指向了电表（{_text(t.get('type'))}），只能并联在电池/电阻/开关/灯泡两端"
    return None


def _texts(obj, out=None):
    """递归收集 props 里的所有字符串（渲染层会画到画面上的文本）。"""
    out = [] if out is None else out
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _texts(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _texts(v, out)
    return out



def _num(v, default=0.0) -> float:
    """脏 IR（web 表单/手改 plan.json）里可能是 None/字符串：闸门要能打回，不能自己崩。
    归一化口径取自 ir.num —— 与 Plan.total_seconds / Shot.subtitles 同一把尺子。"""
    return num(v, default)


def _seq(v) -> list:
    return list(v) if isinstance(v, (list, tuple)) else ([] if v is None else [str(v)])


def _text(v) -> str:
    return v if isinstance(v, str) else ("" if v is None else str(v))


_KEEP_PUNCT = set("-−–—/%‰^")


def _flat(v: str) -> str:
    """去掉空白与标点再比：「a 不等于零。」与「a不等于零，」应当算说过。
    数学符号（= ≠ + < > 等不属于标点类）和 - / % ^ 保留，免得「a≠0」与「a=0」被压成同一串。"""
    return "".join(c for c in v
                   if not c.isspace() and (c in _KEEP_PUNCT or not unicodedata.category(c).startswith("P")))


_CN_NUM = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
_COUNT_RE = re.compile(r"([两二三四五六])\s*[个条种]")


def _count_claim(title: str):
    """标题里的"三个/两条/几种"。同一个标题里出现两个不同的数就不判（多半不是清单承诺）。"""
    got = {_CN_NUM[m.group(1)] for m in _COUNT_RE.finditer(title)}
    return next(iter(got)) if len(got) == 1 else None


def _item_count(v) -> int | None:
    """这一屏版式实际画了几条：只有清单类版式有答案，其余返回 None 表示无从判断。"""
    props = v.props if isinstance(v.props, dict) else {}
    if v.kind == "compare":
        return sum(1 for side in ("left", "right") if isinstance(props.get(side), dict))
    if v.kind in ("steps", "summary"):
        return len(_seq(props.get("lines", props.get("points"))))
    return None


def _shot_items(shot: Shot):
    """整屏清单条目数（compare 的两侧 + 步骤/小结的行）。没有清单类版式就返回 None。"""
    total, listed = 0, False
    for v in _seq(shot.visuals):
        n = _item_count(v)
        if n is not None:
            total += n
            listed = True
    return total if listed else None


def _visual_height(shot: Shot) -> float:
    h = 0.0
    for v in shot.visuals:
        p = v.props if isinstance(v.props, dict) else {}
        if v.kind == "title":
            h += 1.6
        elif v.kind == "formula":
            h += 1.2 + (0.4 if p.get("note") else 0.0)
        elif v.kind == "callout":
            h += 0.8
        elif v.kind == "compare":
            def items(side):
                d = p.get(side)
                return _seq(d.get("items") if isinstance(d, dict) else [])
            h += 1.0 + 0.5 * max(len(items("left")), len(items("right")))
        elif v.kind == "steps":
            h += 0.8 + 0.55 * len(_seq(p.get("lines")))
        elif v.kind == "summary":
            h += 0.8 + 0.55 * len(_seq(p.get("points")))
        elif v.kind == "graph_vt":
            h += 3.6
        elif v.kind == "figure":
            # 椭圆按 4.6×2.6 画再加图注；直角三角形与弦图被刻意压到 2.4~2.6 高，
            # 因为它们那两镜还要和公式卡 / 五行步骤同屏（scene._f_* 里同一套尺寸约束）。
            h += 3.4 if _text(p.get("shape")) == "ellipse" else 3.0
        elif v.kind == "axis_graph":
            h += 3.6
        elif v.kind in ("particle_box", "energy_dist", "stat_chart"):
            h += 3.2 + (0.5 if p.get("label") else 0.0)
        elif v.kind == "microstate":
            h += 3.4 + (0.5 if p.get("label") else 0.0)
        elif v.kind == "mind_map":
            h += 4.2
        elif v.kind == "table":
            h += 0.66 * (1 + len(_seq(p.get("rows"))))
        elif v.kind == "force_diagram":
            h += 2.8
        elif v.kind == "field":
            h += 3.0
        elif v.kind == "circuit":
            h += 2.4
        elif v.kind == "optics":
            h += 3.2
        elif v.kind == "incline":
            h += 3.4
        elif v.kind == "trajectory":
            h += 3.6
        elif v.kind == "derivation":
            # 每步一行等式 + 可选注释，行距与 scene._v_derivation 的 0.34/0.12 同源。
            steps = _seq(p.get("steps"))
            h += 0.6 + 0.68 * max(len(steps), 1)
            if p.get("symbols"):
                h += 0.45
            if p.get("label"):
                h += 0.45
        else:
            h += 1.0
    return h


def check(plan: Plan, kp: dict | None = None) -> list[dict]:
    findings: list[dict] = []

    def add(shot_id, code, msg):
        findings.append({"shot": shot_id, "code": code, "msg": msg})

    total = _num(plan.total_seconds)
    forbidden = _seq((kp or {}).get("forbidden"))
    # 模型起草的库外条目本来就没有教材出处（sidecar 的 kp_origin 如实标注），不按缺出处打回。
    draft_kp = bool(kp) and kp.get("origin") == "model_draft"

    # 同片"写全了限定"的那几句（结论 emphasis / 屏上正文 / 条目声明的 must_say）。
    # 第四轮 F-3：chem 末镜「一句话记住」把 shot6 的 emphasis「氧化型浓度升高，电极电势增大」压成
    # 「浓度升高，电极电势增大」上了屏——学生背下来的是屏上这条，而它是个会被判错的普适句。
    strongest = {_flat(_text(s.emphasis)) for s in plan.shots} | {
        _flat(t) for s in plan.shots for t in _texts([{"kind": v.kind, "props": v.props} for v in _seq(s.visuals)])
    } | {_flat(_text(m)) for m in _seq((kp or {}).get("must_say"))}
    strongest = {c for c in strongest if len(c) >= 8}

    for s in plan.shots:
        secs = _num(s.seconds)
        if secs < MIN_SHOT_SECONDS:
            add(s.index, "DUR_SHORT", f"镜头时长 {s.seconds}s 低于下限 {MIN_SHOT_SECONDS}s（或不是数字）")
        if total and secs / total > MAX_SHOT_SHARE:
            # 短目标（60s）只有六七个镜头，最重的那镜落在 26%~35% 是常态：节奏偏闷但片子能看，
            # 记账不拦；真正一镜到底（>35%）才打回。
            share = secs / total
            if share > MAX_SHOT_SHARE_HARD:
                add(s.index, "DUR_SHARE", f"单镜头占比 {share:.0%} 超过 {MAX_SHOT_SHARE_HARD:.0%}，节奏会闷，请拆镜")
            else:
                findings.append({"shot": s.index, "code": "DUR_SHARE", "blocking": False,
                                 "msg": f"单镜头占比 {share:.0%} 略超 {MAX_SHOT_SHARE:.0%}，节奏偏闷（未拦）"})

        # 屏上条目是同片某句强表述去掉前缀后的那半截 → 限定词被压掉了，打回让作者补回屏上。
        # 只认"后缀压缩"这一种形状（丢掉开头的限定语），因为它是实测发生的形状（"氧化型"三个字被吞掉）。
        # 被吞的那一截必须是纯汉字才算"丢了限定语"：v7 语料里正常的摘要压缩是丢掉公式
        # （「a = Δv/Δt，矢量」压成「矢量，方向沿Δv」）或丢掉引导标签（「参照：标准氢电极…」），
        # 带数字、运算符或标点的截断是排版取舍，不是丢限定词。
        for v in _seq(s.visuals):
            props = v.props if isinstance(v.props, dict) else {}
            for it in _seq(props.get("points", props.get("lines", []))) + _seq([props.get("text", "")]):
                item = _flat(_text(it))
                if len(item) < 6:
                    continue
                for c in strongest:
                    prefix = "" if c == item else (c[:-len(item)] if c.endswith(item) else "")
                    if prefix and re.fullmatch(r"[\u4e00-\u9fff]{1,6}", prefix):
                        add(s.index, "QUALIFIER_LOSS",
                            f"{v.kind} 条目「{item[:20]}」是「{c[:24]}」去掉前缀的压缩版，"
                            f"限定词「{prefix}」丢了；屏上要写全：{c}")
                        break

        words = len(_text(s.narration))
        # 可说窗口：镜头时长扣掉头尾两段静音（配音只落在 [SHOT_HEAD, seconds-SHOT_TAIL]）。
        window = max(secs - SHOT_HEAD - SHOT_TAIL, 0.01)
        cps = words / window
        if cps > FAST_CPS:
            ceiling = (f"最快可接受语速（{FAST_CPS:.1f} 字每秒）" if SPEED_LADDER
                       else f"配音能念到的最快速度（{FAST_CPS:.1f} 字每秒，含逐镜抖动余量）")
            add(s.index, "OVERLOAD", f"口播 {words} 字，本镜可说窗口只有 {window:.1f}s → {cps:.1f} 字每秒，"
                                     f"{ceiling}也念不完，必须精简或给这一镜更多秒数")

        if not s.kp_refs and not draft_kp:
            add(s.index, "NO_REF", "该镜头没有出处引用，科学性不可追溯")

        for word in forbidden:
            # 屏幕文字与口播同权（第四轮 F-3）：学生抄下来的是屏上那行字。v7 的 chem 末镜
            # 「一句话记住」写着无限定版的"浓度升高，电极电势增大"，而口播那条是对的——
            # 只查 narration 的闸门看不见它。
            on_screen = _texts([{"kind": v.kind, "props": v.props} for v in _seq(s.visuals)])
            if word in _text(s.narration) or any(word in t for t in on_screen):
                add(s.index, "TERM", f"出现库中标记为易错/不规范的表述：{word}")

        for v in _seq(s.visuals):
            props = v.props if isinstance(v.props, dict) else {}
            if v.kind not in VISUAL_KINDS:
                add(s.index, "KIND", f"未知版式原语 {v.kind}")
            if v.kind == "formula" and not _text(props.get("expr")).strip():
                add(s.index, "KIND", "formula 缺 expr")
            if v.kind == "graph_vt" and len(_seq(props.get("points"))) < 2:
                add(s.index, "KIND", "graph_vt 至少需要两个点")
            # 跨学科模板守卫：graph_vt 的轴名默认是物理的 v-t 图。数学/化学的函数图不写轴名就上屏，
            # y=x² 会被标成"速度—时间图像"（批量评审 D3，一票否决级硬伤）。
            if v.kind == "graph_vt" and plan.brief.subject != "physics" \
                    and not (_text(props.get("x_label")).strip() and _text(props.get("y_label")).strip()):
                add(s.index, "AXIS_LABEL",
                    f"{plan.brief.subject} 的 graph_vt 未写 x_label/y_label，会套用物理轴名 t/s、v/(m·s⁻¹)")
            for c in _seq(props.get("cases")):
                if not isinstance(c, dict) or len(_seq(c.get("points"))) < 2:
                    add(s.index, "KIND", "graph_vt 的 case 至少需要两个点")
                elif not _text(c.get("at")).strip():
                    add(s.index, "KIND", "graph_vt 的 case 缺 at（何时揭示这条图线）")
                elif _text(c.get("at")) not in "".join(x["text"] for x in s.subtitles()):
                    add(s.index, "KIND", f"graph_vt 的 case.at「{c['at']}」不在本镜任何一条字幕里，永远不会被揭示")
            if v.kind == "figure":
                shape = _text(props.get("shape")) or "ellipse"
                a, b = _num(props.get("a")), _num(props.get("b"))
                if shape not in FIGURE_SHAPES:
                    add(s.index, "KIND", f"figure 不支持 shape={shape}，渲染层只画 {sorted(FIGURE_SHAPES)}")
                elif shape == "ellipse" and not a > b > 0:
                    add(s.index, "KIND", f"椭圆要求 a > b > 0，当前 a={props.get('a')}、b={props.get('b')}")
                elif shape != "ellipse" and not (a > 0 and b > 0):
                    add(s.index, "KIND", f"{shape} 是两条直角边拼出来的图，要求 a、b 均为正数")
            if v.kind == "axis_graph":
                curves = [c for c in _seq(props.get("curves")) if isinstance(c, dict)]
                if not curves or any(len(_seq(c.get("points"))) < 2 for c in curves):
                    add(s.index, "KIND", "axis_graph 至少要一条 curve，且每条至少两个点")
                if not (_text(props.get("x_label")).strip() and _text(props.get("y_label")).strip()):
                    add(s.index, "AXIS_LABEL", "axis_graph 必须写 x_label 与 y_label")
            if v.kind == "particle_box" and _text(props.get("state") or "both") not in ("before", "after", "both"):
                add(s.index, "KIND", "particle_box 的 state 只能是 before / after / both")
            if v.kind == "microstate":
                cells, parts = _num(props.get("cells")), _num(props.get("particles"))
                if not (1 <= parts <= cells <= 8):
                    add(s.index, "KIND", f"microstate 要求 1 ≤ particles ≤ cells ≤ 8，当前 cells={props.get('cells')}、particles={props.get('particles')}")
            if v.kind == "energy_dist" and len(_seq(props.get("levels"))) < 2:
                add(s.index, "KIND", "energy_dist 至少需要两个能级")
            if v.kind == "stat_chart":
                if _text(props.get("type") or "bar") not in ("bar", "hist", "pie", "scatter"):
                    add(s.index, "KIND", "stat_chart 的 type 只能是 bar / hist / pie / scatter")
                if not _seq(props.get("data")):
                    add(s.index, "KIND", "stat_chart 缺 data")
            if v.kind == "mind_map" and not (_text(props.get("root")).strip() and _seq(props.get("branches"))):
                add(s.index, "KIND", "mind_map 需要 root 与至少一个 branch")
            if v.kind == "table" and not _seq(props.get("rows")):
                add(s.index, "KIND", "table 缺 rows")
            if v.kind == "force_diagram":
                forces = [f for f in _seq(props.get("forces")) if isinstance(f, dict)]
                if not forces:
                    add(s.index, "KIND", "force_diagram 至少要一个力（forces 非空）")
                for f in forces:
                    d = f.get("dir")
                    if d is None or (not isinstance(d, (int, float)) and str(d).strip().lower() not in _FORCE_DIRS):
                        add(s.index, "KIND", f"force_diagram 的力「{_text(f.get('name'))}」dir 非法（{d}），"
                                             f"要用 {sorted(_FORCE_DIRS)} 或角度度数")
                for msg in _mag_findings("force_diagram", forces):
                    add(s.index, "KIND", msg)
            if v.kind == "field":
                mode = _text(props.get("mode") or "region")
                if mode not in _FIELD_MODES:
                    add(s.index, "KIND", f"field 的 mode 只能是 {sorted(_FIELD_MODES)}，当前 {mode}")
                if mode == "wire" and _text(props.get("current") or "") not in ("in", "out"):
                    add(s.index, "KIND", "field(wire) 需要 current=in/out（电流进/出纸面）")
                if mode == "region" and _text(props.get("symbols") or "cross") not in ("cross", "dot", "both"):
                    add(s.index, "KIND", "field(region) 的 symbols 只能是 cross / dot / both")
            if v.kind == "circuit":
                elems = [e for e in _seq(props.get("elements")) if isinstance(e, dict)]
                if not elems:
                    add(s.index, "KIND", "circuit 至少要一个元件")
                for e in elems:
                    if _text(e.get("type")) not in _CIRCUIT_TYPES:
                        add(s.index, "KIND", f"circuit 元件 type 只能是 {sorted(_CIRCUIT_TYPES)}，当前 {_text(e.get('type'))}")
                    if _text(e.get("type")) == "voltmeter":
                        msg = _across_finding(e, elems)
                        if msg:
                            add(s.index, "KIND", msg)
            if v.kind == "optics" and _text(props.get("mode") or "mirror") not in _OPTICS_MODES:
                add(s.index, "KIND", f"optics 的 mode 只能是 {sorted(_OPTICS_MODES)}")
            if v.kind == "incline":
                inc_forces = [x for x in _seq(props.get("forces")) if isinstance(x, dict)]
                for msg in _mag_findings("incline", inc_forces):
                    add(s.index, "KIND", msg)
                for f in inc_forces:
                    d = f.get("dir")
                    ok = isinstance(d, (int, float)) and not isinstance(d, bool) or \
                        str(d).strip().lower() in (_FORCE_DIRS | _INCLINE_DIRS)
                    if d is None or not ok:
                        add(s.index, "KIND", f"incline 的力「{_text(f.get('name'))}」dir 非法（{d}），"
                                             f"要用 {sorted(_FORCE_DIRS | _INCLINE_DIRS)} 或角度度数")
            if v.kind == "trajectory" and _text(props.get("mode") or "projectile") not in _TRAJECTORY_MODES:
                add(s.index, "KIND", f"trajectory 的 mode 只能是 {sorted(_TRAJECTORY_MODES)}")
            if v.kind == "derivation":
                steps = _seq(props.get("steps"))
                if not (1 <= len(steps) <= 8):
                    add(s.index, "KIND", f"derivation 需要 1~8 步，当前 {len(steps)} 步")
                for j, st in enumerate(steps):
                    d = st if isinstance(st, dict) else {"text": st}
                    text = _text(d.get("text")).strip()
                    if not text:
                        add(s.index, "KIND", f"derivation 第 {j + 1} 步缺少 text")
                        continue
                    if len(text) > 90:
                        add(s.index, "KIND", f"derivation 第 {j + 1} 步过长（{len(text)} 字），一屏读不完，请拆步")
                    sub = d.get("sub")
                    if sub is not None and not isinstance(sub, dict):
                        add(s.index, "KIND", f"derivation 第 {j + 1} 步的 sub 必须是 {{字母: 代入值}}")
                    elif isinstance(sub, dict):
                        for k, val in sub.items():
                            if not _text(k).strip() or not _text(val).strip():
                                add(s.index, "KIND", f"derivation 第 {j + 1} 步的 sub 有空字母或空代入值")
                            elif _text(k) not in text:
                                add(s.index, "KIND",
                                    f"derivation 第 {j + 1} 步的代入目标「{_text(k)}」不在等式里，动画会指错位置")
                if props.get("symbols") is not None and not isinstance(props.get("symbols"), dict):
                    add(s.index, "KIND", "derivation 的 symbols 必须是 {字母: 物理含义}")
            if v.kind in ("steps", "summary") and len(_seq(props.get("lines", props.get("points")))) > 6:
                add(s.index, "KIND", "一屏条目超过 6 条，认知负荷过高")
            # 与渲染层 _v_callout 的断行规则一致：能按「 · 」拆开且每行都够大就放行。
            if v.kind == "callout":
                text = _text(props.get("text"))
                avail = SAFE_WIDTH - 2 * CALLOUT_PAD

                def font_after_fit(t):
                    w = _est_width(t, CALLOUT_FS)
                    return CALLOUT_FS * min(1.0, avail / w) if w > avail else CALLOUT_FS

                parts = [x.strip() for x in re.split(r"\s+·\s+", text) if x.strip()]
                rows = parts if len(parts) >= 2 else [text]
                if min(font_after_fit(r) for r in rows) < MIN_LEGIBLE_FS:
                    add(s.index, "LEGIBLE",
                        f"callout 上屏字号会掉到 {min(font_after_fit(r) for r in rows):.0f}px < {MIN_LEGIBLE_FS:.0f}px，"
                        f"投影读不见；按「 · 」分成两条以上或删到 {text[:16]}…")

        # 渲染层 scene._fit 会把超高版面整体等比缩进内容带，不会真的压到字幕；只有缩完字号掉到
        # 投影看不清（< MIN_LEGIBLE_FS）才阻断，轻度超高记一笔放行。
        need = _visual_height(s)
        if need > USABLE_H:
            fs = CALLOUT_FS * USABLE_H / need
            if fs < MIN_LEGIBLE_FS:
                add(s.index, "SAFE_AREA", f"版面预计高 {need:.2f} 单位 > 可用 {USABLE_H:.2f}，"
                                          f"整体缩放后字号约 {fs:.0f}px < {MIN_LEGIBLE_FS:.0f}px，请拆成两镜或删减元素")
            else:
                findings.append({"shot": s.index, "code": "SAFE_AREA", "blocking": False,
                                 "msg": f"版面预计高 {need:.2f} 单位 > 可用 {USABLE_H:.2f}，渲染时整体缩到 "
                                        f"{USABLE_H / need:.0%}（字号约 {fs:.0f}px，仍可读）"})

        # 标题里的计数词是对这一屏的承诺：说"三个"却只画两张卡，学生数不到（v2 N2、批量 D13）。
        said = _count_claim(_text(s.title))
        n = _shot_items(s)
        if said is not None and n is not None and n != said:
            add(s.index, "COUNT", f"标题说「{said}」个/条，这一屏的清单只有 {n} 条")

        # 字形闸门：无 LaTeX 环境下，缺字形字符会上屏成豆腐块（评审 P1 第 2 条）。
        for t in _texts(s.narration) + _texts([{"kind": v.kind, "props": v.props} for v in _seq(s.visuals)]):
            bad = sorted({c for c in t if c in TOFU})
            if bad:
                add(s.index, "GLYPH", f"含本机字体缺字形的上下标字母 {''.join(bad)}，请改写为 _x/^x 记法：{t[:28]}")
            if re.search(r"_(?![A-Za-z0-9{])|\^(?![A-Za-z0-9{])", t):
                add(s.index, "GLYPH", f"上下标记法不合法（_ 或 ^ 后须紧跟字母数字或花括号）：{t[:28]}")

        # 字幕必须落在口播窗口内：早于 SHOT_HEAD 会盖住淡入，晚于 seconds-SHOT_TAIL 会与淡出重叠。
        for c in s.subtitles():
            if c["start"] < SHOT_HEAD - 0.01 or c["end"] > secs - SHOT_TAIL + 0.01:
                add(s.index, "SUB_RANGE",
                    f"字幕 {c['i']} 超出窗口 [{SHOT_HEAD}, {round(secs - SHOT_TAIL, 2)}]：[{c['start']}, {c['end']}]")
            dur = c["end"] - c["start"]
            if dur < 0.35:
                add(s.index, "SUB_RANGE", f"字幕 {c['i']} 仅 {round(dur, 2)}s，来不及读：{c['text'][:16]}")
            if cap_width(c["text"]) > MAX_CAP_UNITS + 2:
                add(s.index, "SUB_WIDTH",
                    f"字幕 {c['i']} 宽 {cap_width(c['text']):.1f} > 上限 {MAX_CAP_UNITS + 2:.1f}，会折行出安全区：{c['text'][:20]}")

        # 字幕不重叠（SubTask #60-C）：subtitles() 正常铺排逐条相接、不会重叠，这条防的是
        # 脏 IR / 手改 plan.json 里相邻 cue 时间打架（两条字幕叠在屏幕上互相压字）。
        # 上界不用在这里重复：SUB_RANGE 已对每条 cue（含最后一条）查 end > seconds-SHOT_TAIL。
        # 0.01s 容差与 SUB_RANGE 同口径：恰好相接（end == start）不判重叠。
        cues = sorted(s.subtitles(), key=lambda c: num(c.get("start")))
        for a, b in zip(cues, cues[1:]):
            if num(b.get("start")) < num(a.get("end")) - 0.01:
                add(s.index, "SUB_OVERLAP",
                    f"字幕 {a.get('i')} 与 {b.get('i')} 重叠："
                    f"{num(a.get('start')):.2f}–{num(a.get('end')):.2f} 与 "
                    f"{num(b.get('start')):.2f}–{num(b.get('end')):.2f}"
                    f"（「{_text(a.get('text'))[:10]}」/「{_text(b.get('text'))[:10]}」），"
                    f"请缩短口播或放宽镜头时长")

    # 出处角标的可读性（第四轮 F-1，唯一的过线结论改变项）：渲染层把过长的那条折成两行、
    # 折完仍超安全宽才等比缩。缩到 REF_MIN_FS 以下就是投影上的一片灰点——v7 的 ell（12px）、
    # ua（14px）两条正是从这里漏出去并命中 G3 一票否决的，而当时这条路径上没有任何闸门。
    # 折行用与 scene._wrap_ref 同源的断点纪律（_ref_cut），宽度用分字符估算（_est_width）——
    # 两者不同源时估算会漏报（熵试跑实测：A4 全绿而 test_refs 抓出 12.6px 行）。
    if plan.shots:
        last = plan.shots[-1]
        ref_lines = _seq(last.kp_refs) or [
            f"{r.get('source', '')} {r.get('locator', '')}".strip()
            for r in _seq(plan.refs) if isinstance(r, dict)
        ]
        for ln in ref_lines:
            txt = str(ln)
            segs = [txt] if _est_width(txt, REF_FS) <= REF_WIDE else _ref_cut(txt)
            for seg in segs:
                wide = _est_width(seg, REF_FS)
                eff = REF_FS if wide <= REF_WIDE else REF_FS * REF_WIDE / wide
                if eff < REF_MIN_FS:
                    add(last.index, "LEGIBLE",
                        f"出处行折成两行后仍要缩到 {eff:.0f} 号 < {REF_MIN_FS:.0f}，投影读不见；"
                        f"把这一条拆成两条 refs 或精简定位语：{seg[:28]}…")

    # 图形原语配额（C15/C16 遗留三维里最后那一维）：讲弦图却没有弦图、讲能斯特关系却没有一条线，
    # 空 Plan 不判：它不是"一部没图的片子"，根本还没分镜，该由 TARGET 那类码去喊。
    if plan.shots and not any(v.kind in GRAPHIC_KINDS
                              for s in plan.shots for v in _seq(s.visuals)):
        add(-1, "NO_FIGURE", "整片没有一张图（figure/graph_vt/axis_graph/粒子盒/微观态/统计图/思维导图等）：几何与函数关系全靠文字念，学生无处可指")

    tgt = _num(plan.brief.target_seconds)
    if tgt <= 0:
        # 脏 brief 不能变成免检通道：偏差与节奏两条闸门都按目标时长算，目标没了就必须显式打回，
        # 而不是 `if tgt:` 一句静默跳过（target_seconds=0 曾经同时旁路 TARGET 与 PACING）。
        add(-1, "TARGET", f"目标时长不可用（target_seconds={plan.brief.target_seconds!r}）："
                          f"时长偏差与整片节奏两条闸门无法判定，先修 Brief 再重跑")
    else:
        # 超长是硬伤（内容讲不进目标时长，得删或提速）；短缺不算违规——内容就这么长，
        # 配音又没有提速档能把它"讲满"，硬摊只会造出冻屏（run.py 的反向超差不拦出片口径）。
        # 这里只把超长记为阻断；短缺照 BUDGET_TIGHT 的路子落一条 blocking=False 记账，
        # 让老师知道差额，但不拦出片（否则 161s vs 180s 这种 10.5% 短缺会在这里被杀掉，
        # 与 run.py 第 225 行"反向超差不拦"自相矛盾——用户实报的 TARGET 误杀）。
        over = (total - tgt) / tgt
        if over > 0.10:
            add(-1, "TARGET", f"总时长 {total}s 超出目标 {tgt}s {over:.0%} > 10%：内容讲不进目标时长")
        elif over < -0.10:
            findings.append({"shot": -1, "code": "TARGET", "blocking": False,
                             "msg": f"总时长 {total}s 比目标 {tgt}s 短 {-over:.0%}（按内容长度交付，差额在 sidecar 记一笔）"})

    # 定义性限定闸门：条目用 must_say 声明"这条知识点必须说出口的那几句"（a ≠ 0、常数须大于焦距、
    # F 是合外力……）。评审 S 维度的失分点全是"少了这个限定就讲错了"，而精简口播时最容易误删它们，
    # 所以这里正向钉住：任何一镜的口播里出现过即可，一句都没有就打回。
    said = _flat("".join(_text(s.narration) for s in plan.shots))
    for phrase in _seq((kp or {}).get("must_say")):
        if _flat(_text(phrase)) not in said:
            add(-1, "MISSING_QUALIFIER", f"条目声明的定义性限定在整片口播里一次都没出现：{phrase}")

    # 整片节奏闸门：Plan 里的镜头时长只是预算，成片时长由 TTS 实测反写（A6 对齐回路），
    # 所以口播写超了的代价不是"说不完"，而是整片被提速、并且比目标时长长出一截。
    # 这一条补的正是 C15 遗留里"A4 对内容层缺陷仍然是瞎的"：渲染之前就能看出这支片子要念多快。
    if tgt:
        # 可说窗按 speak_window 取：预算态它等于镜头秒数扣头尾；A6 反写之后镜头可能被分镜预算
        # 拉长（留白），那截是静音不是语速，拿它当窗口会把赶读算成从容。
        speak = sum(s.speak_window for s in plan.shots)
        chars = sum(len(_text(s.narration)) for s in plan.shots)
        rate = 0 if speak <= 0 else (
            0 if chars / speak <= NATURAL_CPS
            else math.ceil(math.log(chars / speak / NATURAL_CPS) / math.log(1 / RATE_FACTOR)))
        if speak > 0 and rate > ACCEPTABLE_RATE:
            need = chars / speak
            cap = int(NATURAL_CPS * speak / RATE_FACTOR ** ACCEPTABLE_RATE)
            # 两个数都给，因为它们是两种活：过线最小值 = 压到 +2 档就能讲完；+0 档值 = 完全按自然语速讲。
            # 只给后者会让人以为必须放宽那么多（审计 §2 指出这条口径过去是隐性的）。
            floor = round(chars / (NATURAL_CPS / RATE_FACTOR ** ACCEPTABLE_RATE)
                          + len(plan.shots) * (SHOT_HEAD + SHOT_TAIL))
            relaxed = round(chars / NATURAL_CPS + len(plan.shots) * (SHOT_HEAD + SHOT_TAIL))
            if SPEED_LADDER:
                advice = (f"自然语速 {NATURAL_CPS} 字每秒要提速到 +{min(rate, MAX_TTS_RATE)} 档"
                          f"{'（已顶到上限，成片还会超时）' if rate > MAX_TTS_RATE else ''}，听着像赶课。"
                          f"精简到 {cap} 字以内，或把目标时长放宽到 ≥{floor}s（+{ACCEPTABLE_RATE} 档过线最小值）"
                          f"~{relaxed}s（自然语速）")
            else:
                # 配音引擎没有语速档（网关 TTS，见 ir.SPEED_LADDER）：不能给"提几档"这种
                # 执行不了的建议，只给"精简到多少字 / 放宽到多少秒"两条真能做的路。
                advice = (f"当前配音只有一个语速（自然语速 {NATURAL_CPS} 字每秒），快不出来。"
                          f"精简到 {int(NATURAL_CPS * speak)} 字以内，"
                          f"或把目标时长放宽到 ≥{relaxed}s。")
            add(-1, "PACING",
                f"口播共 {chars} 字，{tgt:.0f}s 的可说窗口 {speak:.0f}s 平均只容 {need:.1f} 字每秒：" + advice)

        # A3 预算账的诚实记账：+1/+2 档不违规（PACING 已经放过），但"这条片子是靠提速讲完的"
        # 得让老师和评审看得见 —— batch_v6 闸门全绿却有 6/8 条提速过关，就缺这句话（C18 更正一）。
        # 装不装得下**以 A3 自己的账为准**（fits_natural）：点名段是固定开销、不参与正片预算，
        # 而这里的全片平均语速把它算进去了，两者会在"正片讲得进、片头略赶"的条目上打架（匀变速）。
        # 非阻断：它记录代价，不拦出片（run.py 只对阻断项硬打回）。
        # 只在预算态喊：账本记的是分镜自己的总长，A6 反写秒数后这个等式不再成立，自动静音。
        acct = next((r for r in _seq(plan.refs) if isinstance(r, dict)
                     and r.get("kind") == BUDGET_REF_KIND), None)
        if acct and not acct.get("fits_natural", True) and 0 < rate <= ACCEPTABLE_RATE \
                and abs(_num(acct.get("budgeted_seconds")) - total) <= 0.01:
            how = (f"成片靠提速到 +{rate} 档讲完" if SPEED_LADDER
                   else "配音没有提速档，只能靠删内容或让个别镜头赶")
            findings.append({"shot": -1, "code": "BUDGET_TIGHT", "blocking": False, "msg":
                f"A3 预算账：{acct.get('narration_chars')} 字按自然语速要 {_num(acct.get('natural_seconds')):.0f}s "
                f"才讲得进，现在压进 {tgt:.0f}s（{how}）；"
                f"想零提速就精简到 {int(NATURAL_CPS * speak)} 字以内，"
                f"或把目标时长放宽到 ≥{acct.get('min_seconds_for_natural')}s"})

    return findings


def blocking(findings: list[dict]) -> list[dict]:
    """阻断级发现才拦得住出片。findings 里缺 blocking 键的按传统一律阻断，
    只有闸门显式声明 blocking: False 的（如 BUDGET_TIGHT 这类记账）才放行。"""
    return [f for f in findings if f.get("blocking", True)]


def report(plan: Plan, kp: dict | None = None) -> dict:
    """交付件形态（第四轮 F-8）：跑过哪些码 + 违规清单。

    空清单从此只有一种读法——这些码确实跑过了；不再是"全绿"与"根本没跑"共用一个 []。
    """
    return {"checked": list(CODES), "violations": check(plan, kp)}
