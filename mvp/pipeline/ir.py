"""project1 澄象 · 中间表示（IR）层

对应 Spec_Product.txt 第 2/4 节：Brief 是输入契约，Plan 是分镜 IR。
渲染层与配音层只消费 Plan，不接触知识点原文。
"""

from __future__ import annotations

import hashlib
import math
import json
import re
from dataclasses import dataclass, field, asdict

SUBJECTS = ("math", "physics", "chemistry")
SPEC_VERSION = "S1-2026.10"     # plan.json 里回指规格版本（Spec_Product 第 4 节）
GRADES = ("G8", "G9", "H1", "H2", "H3", "U1", "U2")
STYLES = ("clean", "board")
VISUAL_KINDS = ("title", "formula", "compare", "graph_vt", "figure", "steps", "summary", "callout",
                "axis_graph", "particle_box", "microstate", "energy_dist", "stat_chart", "mind_map", "table",
                "force_diagram", "field", "circuit", "optics", "incline", "trajectory")
# 以「画」为主的版式：整片至少要有一个（review.NO_FIGURE），讲具体对象的图都算。
GRAPHIC_KINDS = ("figure", "graph_vt", "axis_graph", "particle_box", "microstate", "energy_dist",
                 "stat_chart", "mind_map", "force_diagram", "field", "circuit", "optics",
                 "incline", "trajectory")

# A3 分镜预算账本挂在 Plan.refs 末尾的标记（refs[0] 仍是教材出处，片尾卡只读第一条）。
# 常量住在 ir：storyboard 写、review 读，任何一方都不该私有这份字段名。
BUDGET_REF_KIND = "storyboard_budget"

MIN_SECONDS, MAX_SECONDS = 30, 600
MIN_SHOT_SECONDS = 4.0

# 镜头时间轴：每个镜头占 shot.seconds 秒，其中前 SHOT_HEAD 秒留给标题淡入（配音也从这里开始），
# 后 SHOT_TAIL 秒留给收尾静音。渲染、配音、字幕三个环节共用这一组常量，
# 才能保证"成片时长 == Plan 时长"且"字幕与语音对齐"。
# （SHOT_TAIL 原本是"淡出 0.4 + 余量 0.3"；第四轮 F-2 边界改硬切后淡出没了，
#  这 0.7s 纯作收尾静音保留，数值不动——它是音画记账的一部分。）
SHOT_HEAD = 0.45
SHOT_TAIL = 0.70
# 单镜在口播讲完之后最多还能静多久（不含 SHOT_TAIL）。富余是刻意留的思考时间，但第四轮
# 评审实测到一镜冻 5.0s（一次函数镜4）——集中在一镜的富余不是节奏，是卡片。见 run._spread_surplus。
MAX_SHOT_IDLE = 1.5

# 口播节奏尺子。2026-10-18 起以**网关 TTS（qwen3-tts-flash，voice=cherry）**为准：
# 用一次真实出片的 8 镜口播（424 字）逐镜合成实测 = 4.75 字/秒（逐镜 3.99~5.15），
# 另 5 条短句 ×2 遍的独立探针给 4.45~5.17 ⇒ 取 4.7。标定脚本 .local/tts_calib/calib_qwen.py。
# 旧值 3.9 是 Windows SAPI Huihui 的读数（2026-10-17 正向标定 60 次合成，3.86~4.06），
# 配音换引擎后不重标会把分镜预算铺得过宽：120s 目标实测偏差已到 -9.3%，贴着 ±10% 时长闸门。
NATURAL_CPS = 4.7
# 语速档：SAPI 有 -10~10 档（每档 ×0.897），网关 TTS 的 speed 参数实测无效（见 audio/tts.py
# 的探测结论），所以 SPEED_LADDER=False —— 成片只有一个语速，就是自然语速。
SPEED_LADDER = False
RATE_FACTOR = 0.897
MAX_TTS_RATE = 4
# 闸门"最快也念不完"的天花板。带语速档时 = 顶档语速（≈6.0）；没有档可提时，天花板就是
# 自然语速本身，只再留一点逐镜抖动余量（实测 ±12%），否则分镜按 NATURAL_CPS 铺满的片子
# 会因为取整被误判超载。
FAST_CPS = NATURAL_CPS / RATE_FACTOR ** MAX_TTS_RATE if SPEED_LADDER else round(NATURAL_CPS * 1.12, 2)
# 2026-10-17 正向标定复测（.local/tts_calib/calib.py，三条真实口播 × rate 0..4 共 60 次合成）：
# 实测 +1=0.8990 / +2=0.8044 / +3=0.7213 / +4=0.6459，与 0.897^rate 逐档差 ≤0.22%；
# 自然语速读数 3.86~4.06 字/秒 ⇒ 这两个常数不改。流程审计从**成片时长**反推得出的 0.905/0.817
# 混进了逐镜取整与每镜 1.15s 头尾静音，不是语速系数，其"应重标定"的结论作废。
# （该结论只对 SAPI 成立：换网关 TTS 后 NATURAL_CPS 已按上行重标，RATE_FACTOR 只在
#  SPEED_LADDER=True 的引擎下才有意义。）
# 成片需要提到第几档以上，就算"口播写超了"：+2（≈4.9 字/秒）以内听着还是讲课，
# 再往上是在赶时间，伤的是四维评价里的"易懂"，不如精简文本或放宽目标时长。
ACCEPTABLE_RATE = 2

# 先修点名段（片头"开始前先确认…"）不是教学内容：按 NAME_CPS 给时长，且总占比不超过
# NAME_MAX_SHARE。storyboard 与 prereq 两处共用这一把尺子，否则同名两段会算出两种预算。
# NAME_CPS 比 NATURAL_CPS 略低（4.5 vs 4.7）= 给点名段多留一点余量，口径仍是**可说窗**
# （镜头秒数扣掉 SHOT_HEAD+SHOT_TAIL）上的语速，所以派生秒数要把那 1.15s 另加回去——
# 少加一次，点名段实测就被推到 4.9~5.0 字/秒，比这条常数自己声明的还快（batch_v7 复核 §3）。
NAME_CPS = 4.5
NAME_MAX_SHARE = 0.15


_CITE_RE = re.compile(r"（[^（）]*）")


def naming_label(label: str) -> str:
    """先修标签上屏/上口播的形态：去掉库内条目给编辑看的全角括注（出处页码、课标原文）。
    半角括号不动——它们常是公式本身，如 r = mv/(qB)。"""
    prev = None
    while prev != label:
        prev, label = label, _CITE_RE.sub("", label)
    return label.strip(" ，,；;")


def naming_narration(labels: list[str]) -> str:
    """点名段的固定文本。三处（storyboard、prereq 的两个函数）都从这里取：
    同一段点名的措辞一旦各写各的，字数就不同，下面的 naming_shot_seconds 也算不出同一个秒数。"""
    return "开始前先确认一件事：" + "、".join(naming_label(x) for x in labels) + "。这几条熟了，下面才跟得上。"


def fit_naming_labels(labels: list[str], cap_seconds: float) -> list[str]:
    """按原顺序保留能在 cap_seconds 内念完的前几条先修；一条都放不下就返回空（不出点名镜）。"""
    keep = [x for x in (naming_label(x) for x in labels) if x]
    while keep and naming_shot_seconds(naming_narration(keep)) > cap_seconds + 1e-9:
        keep.pop()
    return keep


def naming_shot_seconds(narration: str, min_seconds: float = MIN_SHOT_SECONDS) -> float:
    """点名段的镜头秒数：文本在可说窗上按 NAME_CPS 念完，再加回头尾留白。

    `min_seconds` 封的是**整镜**秒数：prereq 用自己的 NAME_MIN_SECONDS，storyboard 用
    MIN_SHOT_SECONDS。两边算的是同一段文本，就必须走这一个函数（Spec_PreqChain R2）。
    """
    return max(min_seconds, round(len(narration) / NAME_CPS + SHOT_HEAD + SHOT_TAIL, 2))

# 字幕切分：一条字幕的视觉宽度上限（汉字记 1、拉丁字母/数字记 0.5）。
MAX_CAP_UNITS = 18.0
MIN_CAP_UNITS = 5.0            # 短于这个宽度的碎片会和上一条合并，避免"注意"一闪而过
MIN_CUE_SECONDS = 1.0          # 一条字幕至少停留 1s：宽度够但镜头语速快时仍可能只分到 0.9s
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-/_.²³¹%]*")
# 可断点优先级：空格后 > 中西文交界 > 虚词前后 > 汉字之间。绝不在 token（术语/单位/数值）内部下刀。
_BREAK_AFTER = "的了等与和及或而是"
_BREAK_BEFORE = "除并与及或而所把被让从到"
_STOP = "。；！？"


def num(v, default: float = 0.0) -> float:
    """脏 IR 里 seconds / target_seconds 可能是 None 或字符串（web 表单、手改 plan.json）。

    数值口径只在这里定义一次，闸门与字幕时序共用：此前 review 侧有 _num 而数值层照裸值算，
    于是 check 第一行读 plan.total_seconds 就 TypeError 崩掉，一条闸门都没跑完。
    """
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def cap_width(s: str) -> float:
    return sum(0.5 if c.isascii() else 1.0 for c in s)


def disp(s: str) -> str:
    """上屏文本：句末的逗号/顿号/冒号不显示，宽度也按不显示来算。"""
    return s.rstrip("，、：")


def split_narration(text: str) -> list[str]:
    """按标点切句，超长句再按语义单元折行：术语（v-t 图像）、数值单位（20 m/s）不可拦腰截断。

    返回的是**带标点**的原始片段，上屏前由 Shot.subtitles() 去掉句末逗号/顿号/冒号——
    合并规则要拿标点当粘连符，宽度却要按上屏后的样子算。
    """
    chunks: list[str] = []
    for part in re.split(r"(?<=[。；！？，、：])", text or ""):
        p = part.strip()
        if p:
            chunks.extend(_fold(p))
    # ① 碎片并回上一条；但上一条若是完整句尾（。；！？）就不合并，保持与语音停顿一致。
    merged: list[str] = []
    for c in chunks:
        prev = merged[-1] if merged else ""
        if merged and cue_w(c) < MIN_CAP_UNITS and not prev.endswith(tuple(_STOP)) \
                and cue_w(_join(prev, c)) <= MAX_CAP_UNITS + 2:
            merged[-1] = _join(prev, c)
        else:
            merged.append(c)
    # ② 还是太短的碎片就跟**下一条**合成一条：2 个字的 cue 只分到 0.3s，屏幕上是一闪而过的字，
    #    读不到（评审 N4）。两条合起来放不下就重新平切成两条——谁都不闪读，也不折出安全区。
    out: list[str] = []
    i = 0
    while i < len(merged):
        c = merged[i]
        if cue_w(c) >= MIN_CAP_UNITS or i + 1 == len(merged):
            out.append(c)
            i += 1
            continue
        comb = _join(c, merged[i + 1])
        out.extend(_fold(comb) if cue_w(comb) > MAX_CAP_UNITS + 2 else [comb])
        i += 2
    # ③ 收尾的孤立碎片没有下一条可并，只能并回上一条（同样放不下就平切）。
    if len(out) > 1 and cue_w(out[-1]) < MIN_CAP_UNITS:
        comb = _join(out[-2], out[-1])
        out[-2:] = _fold(comb) if cue_w(comb) > MAX_CAP_UNITS + 2 else [comb]
    return [c for c in out if disp(c)]


def cue_w(s: str) -> float:
    """一条字幕上屏后占多少个汉字宽。"""
    return cap_width(disp(s))


def _join(a: str, b: str) -> str:
    """两条接成一条：哪一侧本来就带标点就直接接，两边都没有才补个逗号断句（否则会出现「，，」）。"""
    if not a or a[-1] in "，、：。；！？" or b[:1] in "，、：。；！？":
        return a + b
    return a + "，" + b


def _fold(s: str) -> list[str]:
    """超长文本平切成若干条。目标宽度取"总宽 / 要切几块"，不是"切到装不下为止"：
    贪心折到上限会留下『…5、12、』+『13。』这种 2 个字的尾巴，一秒都给不出。"""
    out: list[str] = []
    while cue_w(s) > MAX_CAP_UNITS + 2:
        blocks = max(2, math.ceil(cue_w(s) / MAX_CAP_UNITS))
        cut = _best_cut(s, cue_w(s) / blocks)
        out.append(s[:cut].strip())
        s = s[cut:].strip()
    if s:
        out.append(s)
    return out


def _best_cut(p: str, balance: float | None = None) -> int:
    """在宽度上限内取最靠平衡点的合法断点。返回切片下标（一定 >0 且 <len(p)）。"""
    target = cap_width(p) / 2 if balance is None else balance
    token_spans = [(m.start(), m.end()) for m in _TOKEN_RE.finditer(p)]
    cum, best, best_score = 0.0, 0, -1e9
    for i in range(1, len(p)):
        cum += 0.5 if p[i - 1].isascii() else 1.0
        if cap_width(p[:i]) > MAX_CAP_UNITS:
            break
        if any(s < i < e for s, e in token_spans):  # token 内部不可断
            continue
        score = 0.5   # 两个汉字中间硬切会把词切断（「直角三角/形」），只能当最后手段
        if p[i - 1] in "，、：；。！？":
            score = 3.5   # 本来就有停顿，切在这里读起来最自然
        elif p[i - 1] == " " or p[i - 1] in "（([":
            score = 3.0
        elif p[i - 1].isascii() != p[i].isascii():
            score = 2.5   # 中西文交界
        elif p[i] in _BREAK_BEFORE or p[i - 1] in _BREAK_AFTER:
            score = 2.0   # 虚词前后
        if p[i - 1].isdigit() or p[i].isdigit():
            score -= 2.0  # 数字两侧下刀会把「5、12、13」拆成「5、12」+「13」
        score -= abs(cum - target) * 0.3  # 同档里再挑最接近平衡点的
        if score > best_score:
            best_score, best = score, i
    return best or min(len(p) - 1, max(1, int(MAX_CAP_UNITS)))



@dataclass
class Brief:
    subject: str
    grade: str
    topic: str
    target_seconds: int = 120
    style: str = "clean"
    narration: bool = True
    prior_knowledge: bool = True
    resolution: str = "1920x1080"
    fps: int = 30
    subtitles: bool = True
    language: str = "zh"
    raw_text: str = ""

    def __post_init__(self) -> None:
        # 表单/JSON 常把数字传成字符串：先归一化，让 validate() 只报真错误而不是抛异常。
        for name in ("target_seconds", "fps"):
            v = getattr(self, name)
            if isinstance(v, str) and v.strip().isdigit():
                setattr(self, name, int(v))

    def validate(self) -> list[str]:
        errs = []
        if self.subject not in SUBJECTS:
            errs.append(f"subject 必须是 {SUBJECTS}")
        if self.grade not in GRADES:
            errs.append(f"grade 必须是 {GRADES}")
        if self.style not in STYLES:
            errs.append(f"style 必须是 {STYLES}")
        if not self.topic.strip():
            errs.append("topic 不能为空")
        if not isinstance(self.target_seconds, int):
            errs.append(f"target_seconds 必须是整数，收到 {self.target_seconds!r}")
        elif not MIN_SECONDS <= self.target_seconds <= MAX_SECONDS:
            errs.append(f"target_seconds 需在 {MIN_SECONDS}~{MAX_SECONDS} 之间")
        if self.language != "zh":
            errs.append("MVP 只出中文字幕（language 固定 zh）")
        w, _, h = self.resolution.partition("x")
        if not (w.isdigit() and h.isdigit()) or int(w) < 1920 or int(h) < 1080:
            errs.append("resolution 不得低于 1920x1080（Spec_Product 第 3 节）")
        return errs


@dataclass
class Visual:
    kind: str
    props: dict = field(default_factory=dict)


@dataclass
class Shot:
    index: int
    title: str
    seconds: float
    narration: str
    visuals: list[Visual]
    kp_refs: list[str] = field(default_factory=list)
    emphasis: str = ""
    # A6 实测到的语音秒数（含头尾留白）。镜头可以比语音长——分镜预算没说完的那截是留给学生的
    # 思考时间——但字幕与揭示只铺在真正有声音的那一段里，否则越到镜头末尾字幕越拖后。
    spoken: float = 0.0
    # 配音稿（朗读稿）：把混着公式/化学式的 narration 改写成朗读员照念的中文，供 TTS 朗读；
    # 字幕仍用 narration 原文。为空时 TTS 回退到 audio/tts.speakable 的正则朗读。
    voiceover: str = ""

    @property
    def speak_window(self) -> float:
        """这一镜真正用来念口播的可说窗：扣掉头尾留白，且以实测语音长度为准。"""
        wall = num(self.spoken) if num(self.spoken) > 0 else num(self.seconds)
        return max(min(wall, num(self.seconds)) - SHOT_HEAD - SHOT_TAIL, 0.0)

    def subtitles(self) -> list[dict]:
        """切句后按各句"朗读宽度"分配时长（不是均分），落在镜头口播窗口 [SHOT_HEAD, seconds-SHOT_TAIL]。

        时间是镜头内的绝对秒，与配音轨（同一镜头的语音也从 SHOT_HEAD 起）对齐。
        镜头被分镜预算拉长时，窗口仍按 speak_window 算——多出来的是静音，不是给字幕慢慢铺的。
        split_narration 只能按字数兜底，这里按**这条 cue 实际分到几秒**再收一次：
        语速快的镜头 4 个字只落 0.9s，屏幕上是一闪而过的字（评审 N4）。
        """
        chunks = split_narration(self.narration)
        if not chunks:
            return []
        span = max(self.speak_window, 0.5)
        pairs = [[c, max(cap_width(disp(c)), 0.5)] for c in chunks]
        while len(pairs) > 1:
            total_w = sum(w for _, w in pairs)
            flash = [i for i, (_, w) in enumerate(pairs) if span * w / total_w < MIN_CUE_SECONDS]
            merged = False
            # 从右往左并，删元素不会挪动还没处理的下一条下标；一条并不动就跳过它去并别条，
            # 整轮一条都没并成才收手（否则永远在处理同一条并不动的）。
            for i in sorted(flash, reverse=True):
                for j in (i + 1, i - 1):
                    if not 0 <= j < len(pairs):
                        continue
                    lo, hi = min(i, j), max(i, j)
                    text = _join(pairs[lo][0], pairs[hi][0])
                    # 并完不能超宽度上限：超了就折行出安全区，比闪读更糟
                    if cue_w(text) > MAX_CAP_UNITS + 2:
                        continue
                    pairs[lo] = [text, max(cue_w(text), 0.5)]
                    del pairs[hi]
                    merged = True
                    break
            if not merged:
                break
        chunks = [disp(c) for c, _ in pairs]
        weights = [w for _, w in pairs]
        total_w = sum(weights)
        out, t = [], SHOT_HEAD
        for i, (c, w) in enumerate(zip(chunks, weights)):
            end = SHOT_HEAD + span if i == len(chunks) - 1 else round(t + span * w / total_w, 2)
            out.append({"i": i, "start": round(t, 2), "end": end, "text": c})
            t = end
        return out


@dataclass
class Plan:
    brief: Brief
    knowledge_id: str
    shots: list[Shot]
    refs: list[dict] = field(default_factory=list)

    @property
    def total_seconds(self) -> float:
        return round(sum(num(s.seconds) for s in self.shots), 2)

    @property
    def hash(self) -> str:
        blob = json.dumps(self.to_dict(include_subtitles=False, with_hash=False),
                          ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]

    def to_dict(self, include_subtitles: bool = True, with_hash: bool = True) -> dict:
        d = {
            "version": SPEC_VERSION,
            "knowledge_id": self.knowledge_id,
            "refs": self.refs,
            "brief": asdict(self.brief),
            "total_seconds": self.total_seconds,
            "shots": [
                {
                    "index": s.index,
                    "title": s.title,
                    "seconds": s.seconds,
                    "spoken": s.spoken,
                    "narration": s.narration,
                    "voiceover": s.voiceover,
                    "emphasis": s.emphasis,
                    "kp_refs": s.kp_refs,
                    "visuals": [{"kind": v.kind, "props": v.props} for v in s.visuals],
                    **({"subtitles": s.subtitles()} if include_subtitles else {}),
                }
                for s in self.shots
            ],
        }
        if with_hash:
            d["hash"] = self.hash
        return d

    def save(self, path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def from_dict(d: dict) -> "Plan":
        shots = [
            Shot(
                index=s["index"],
                title=s["title"],
                seconds=s["seconds"],
                narration=s["narration"],
                visuals=[Visual(v["kind"], v.get("props", {})) for v in s["visuals"]],
                kp_refs=s.get("kp_refs", []),
                emphasis=s.get("emphasis", ""),
                voiceover=s.get("voiceover", ""),
            )
            for s in d["shots"]
        ]
        return Plan(
            brief=Brief(**{k: v for k, v in d["brief"].items() if k in Brief.__dataclass_fields__}),
            knowledge_id=d["knowledge_id"],
            shots=shots,
            refs=d.get("refs", []),
        )

    @staticmethod
    def load(path) -> "Plan":
        return Plan.from_dict(json.loads(path.read_text(encoding="utf-8")))
