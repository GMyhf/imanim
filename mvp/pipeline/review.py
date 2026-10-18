"""A4 风格监督（静态）：Plan 出片前的确定性闸门。

只打回、不改写（Spec_Workflow 第 1 节）。检查项对应 Spec_Workflow A4 的 ①~⑤。
"""

from __future__ import annotations

import math
import re

from .ir import (ACCEPTABLE_RATE, BUDGET_REF_KIND, FAST_CPS, GRAPHIC_KINDS, MAX_CAP_UNITS, MAX_TTS_RATE,
                 MIN_SHOT_SECONDS, NATURAL_CPS, RATE_FACTOR, SHOT_HEAD, SHOT_TAIL, SPEED_LADDER,
                 VISUAL_KINDS, Plan, Shot, cap_width, num)

# 版面高度模型（Manim 单位，帧高 8）：底部字幕带 1.05，顶部页眉 0.6
FRAME_H = 8.0
SUBTITLE_BAND = 1.05
HEADER_BAND = 0.60
USABLE_H = FRAME_H - SUBTITLE_BAND - HEADER_BAND

MAX_SHOT_SHARE = 0.25

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
UNIT_CJK = 0.44
UNIT_ASCII = 0.50

# 出处折行的断点纪律：与 scene._wrap_ref 同源（改一处要改两处）。句读优先、括号内部禁断、
# 行尾不留开括号或运算符——否则公式被劈开，比缩字号更糟。
REF_SEPS = ("；", "：", "。", "，", "、", "）", " ", "—", "·", "/")
REF_STRONG = ("；", "：", "。", "，", "、")
REF_ATTACH_LEFT = "；：。，、）》」』—·"
REF_OPEN = "（(《「『[［"
REF_CLOSE = "）)》」』]］"
REF_EDGE_BAD = REF_OPEN + "=+_^/·—"


def _est_width(txt: str, fs: float) -> float:
    """分字符宽度估算（纯标准库，不 import scene/manim）：CJK 与 ASCII 各用自己的实测系数。"""
    cjk = sum(1.0 for c in str(txt) if not c.isascii())
    asc = sum(0.5 for c in str(txt) if c.isascii())
    return (cjk * UNIT_CJK + asc * UNIT_ASCII) * fs / 32.0


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


def _flat(v: str) -> str:
    """去掉所有空白：口播里写「a 不等于零」、条目里声明「a不等于零」，应当算说过。"""
    return re.sub(r"\s+", "", v)


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
        else:
            h += 1.0
    return h


def check(plan: Plan, kp: dict | None = None) -> list[dict]:
    findings: list[dict] = []

    def add(shot_id, code, msg):
        findings.append({"shot": shot_id, "code": code, "msg": msg})

    total = _num(plan.total_seconds)
    forbidden = _seq((kp or {}).get("forbidden"))

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
            add(s.index, "DUR_SHARE", f"单镜头占比 {secs / total:.0%} 超过 {MAX_SHOT_SHARE:.0%}，节奏会闷")

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

        if not s.kp_refs:
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

        need = _visual_height(s)
        if need > USABLE_H:
            add(s.index, "SAFE_AREA", f"版面预计高 {need:.2f} 单位 > 可用 {USABLE_H:.2f}，会侵入字幕安全区")

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
        dev = abs(total - tgt) / tgt
        if dev > 0.10:
            add(-1, "TARGET", f"总时长 {total}s 与目标 {tgt}s 偏差 {dev:.0%} > 10%")

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
