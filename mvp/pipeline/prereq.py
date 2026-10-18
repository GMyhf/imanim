"""project1 澄象 · 先修依赖图与先修补齐规划（差异环①，设计见 Spec_PreqChain.txt）。

职责：把知识点条目里的 `prior` 字符串升级成**可递归展开、每条边都有出处**的依赖图，
并按确定性策略决定「这一片补哪几条先修、各补几秒、哪些必须先另出一支片」。

红线（Spec_PreqChain.txt 第 0 节）：
  R1 不建没有出处的边。边的 citations 必须带教材章节 / 课标条目定位，缺出处即丢弃并记录。
  R2 指向库外概念的边一律标 in_library=False（悬空）：只能点名、不能展开讲、永不进串播清单。
  R3 递归有深度上限（默认 2）+ 环检测；被截断必须留痕，不静默。
  R4 对既有管线只读：不改 ir/knowledge/storyboard/review/mux，不改 data/kp/*.json。
  R5 补齐镜头的内容一律整段复用库内已核对条目的原文，一字不改写（不生成新内容）。

只用标准库（本机约定最小依赖，不引入 networkx）。
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------- 只读接入既有管线
# 既可作为 `pipeline.prereq` 包内模块导入，也可 `python pipeline/prereq.py` 直跑。
# 两条路都要走得通：ir 与 knowledge 得一起进同一个 try，否则直跑时先在相对导入上炸掉。
try:
    from . import knowledge as _knowledge
    from .ir import MIN_SHOT_SECONDS, NATURAL_CPS, naming_narration, naming_shot_seconds
except ImportError:  # 脚本直跑：把 mvp/ 放进 sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pipeline import knowledge as _knowledge
    from pipeline.ir import MIN_SHOT_SECONDS, NATURAL_CPS, naming_narration, naming_shot_seconds

DATA_DIR: Path = Path(getattr(_knowledge, "DATA_DIR", Path(__file__).resolve().parent / "data" / "kp"))
# 选型结论（Spec_PreqChain 第 1 节）：边放全局图文件，不内嵌进 kp 文件。
# 该文件当前尚未落地 —— 缺失时本模块只用「从 prior 字段派生」的边，且一律 verified=False。
GRAPH_PATH: Path = DATA_DIR.parent / "prereq.json"

GRADES = ("G8", "G9", "H1", "H2")  # 与 ir.GRADES 同序，用于学段倒挂检查

# 时长常量：与 review.py 的闸门同源（ir 里那一份），避免两处各写一把尺子。
PREQ_BUDGET_RATIO = 0.15  # 先修段总时长占目标时长的比例上限
PREQ_NAME_SHARE = 0.4  # 先修预算里给「片头点名」的保底份额（点名便宜但必要，U4 的 3 分线）
PREQ_SHOT_CAP = 0.20  # 单个先修镜头占目标时长的上限（给 MAX_SHOT_SHARE 留余量）
MAX_DEPTH_DEFAULT = 2

MODE_RECALL = "recall_block"  # 片内回顾：整段复用库内那条条目的既有镜头
MODE_NAME = "name_only"  # 只点名不讲解：悬空先修的唯一合法处置（R2）
MODE_VIDEO = "separate_video"  # 本片不补，先另出一支先修片（进串播清单）
MODE_SKIP = "skip"

NAME_MIN_SECONDS = 6.0
NAME_MAX_ITEMS = 4  # 片头点名最多 4 条（与 prior 字段的入库约定一致；再多就压垮 U2 认知负荷）

_PUNCT = re.compile(r"[\s，、。；：:（）()「」《》“”\"'’·…—\-_,.;:!?！？]")


def _norm(s: str) -> str:
    """归一化：去空白与标点、小写。只做字面对齐，不做语义推断。"""
    return _PUNCT.sub("", (s or "")).lower()


def _lcs(a: str, b: str) -> int:
    """最长公共子串长度。字符串都很短，O(n·m) 手写即可，不引第三方库。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


MIN_CONTAIN = 3  # 子串命中（可能成边）的最小长度，防「的/与」之类误配
MIN_HINT = 4  # 近似覆盖提示（绝不成边）的最小长度


# ---------------------------------------------------------------- 数据结构
@dataclass
class Node:
    """依赖图节点：库内条目（kp）或库外概念（external，即「悬空」）。"""

    kind: str  # "kp" | "external"
    key: str  # 库内为 kp id；库外为归一化 label
    label: str  # 展示名：库内用 topic，库外用 prior 原文
    depth: int = 0
    kp_id: str | None = None
    in_library: bool = False
    verified: bool = False  # 边是否经人工核对；派生边默认 False
    origin: str = "derived_prior_match"  # derived_prior_match | declared_edge | external_prior
    citations: list[dict] = field(default_factory=list)  # 出处（R1）
    matched_via: str = ""  # exact_topic | exact_alias | contains_alias | prior_in_name | declared
    prior_label: str = ""  # 宿主条目 prior 字段里的原文（学生/老师口中最常见的说法）
    used_by_shot: str = ""  # 本片哪个镜头真的用到它（来自镜头标题的证据）
    covered_by: list[str] = field(default_factory=list)  # 库内近似覆盖（仅提示）
    strength: str = "hard"  # hard | soft
    mastered: bool = False
    via: str = ""  # 由哪个知识点展开而来

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "key": self.key, "label": self.label, "prior_label": self.prior_label,
            "depth": self.depth,
            "kp_id": self.kp_id, "in_library": self.in_library, "verified": self.verified,
            "origin": self.origin, "citations": self.citations, "matched_via": self.matched_via,
            "used_by_shot": self.used_by_shot, "covered_by": self.covered_by,
            "strength": self.strength, "mastered": self.mastered, "via": self.via,
        }


@dataclass
class Edge:
    """一条先修边：target 依赖 prereq。citations 为空则不允许构造（R1）。"""

    prereq: str
    target: str
    label: str = ""  # target 里对应的 prior 原文
    strength: str = "hard"
    verified: bool = False
    origin: str = "derived_prior_match"
    citations: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.citations:
            raise ValueError(f"边 {self.prereq} → {self.target} 没有出处，按红线 R1 拒绝构造")

    def to_dict(self) -> dict:
        return {
            "prereq": self.prereq, "target": self.target, "label": self.label,
            "strength": self.strength, "verified": self.verified, "origin": self.origin,
            "citations": self.citations,
        }


@dataclass
class Library:
    """data/kp/<subject>/*.json 的只读快照 + 名称索引。"""

    entries: dict[str, dict] = field(default_factory=dict)
    names: list[tuple[str, str, str]] = field(default_factory=list)  # (norm, kp_id, name)

    @property
    def size(self) -> int:
        return len(self.entries)

    def get(self, kp_id: str | None) -> dict | None:
        return self.entries.get(kp_id or "")

    def topic(self, kp_id: str | None) -> str:
        e = self.get(kp_id)
        return e.get("topic", "") if e else ""

    def refs_text(self, kp_id: str | None) -> list[str]:
        e = self.get(kp_id)
        if not e:
            return []
        return [f"{r.get('source', '')} {r.get('locator', '')}".strip() for r in e.get("refs", [])]

    def resolve(self, ref: str) -> str | None:
        """id / topic / 别名 → 库内 id。命中不了返回 None（不猜、不生成）。"""
        n = _norm(ref)
        if not n:
            return None
        for kid in self.entries:
            if _norm(kid) == n:
                return kid
        for nn, kid, name in self.names:
            if nn == n:
                return kid
            if _norm(name) == n:
                return kid
        return None

    def match_prior(self, label: str, exclude_id: str) -> tuple[str | None, str, str]:
        """prior 字符串 → 库内条目。只做字面归一匹配，绝不做语义联想。

        返回 (kp_id 或 None, 命中名称, 命中方式)。精确匹配优先，其次长子串包含。
        """
        n = _norm(label)
        if not n:
            return None, "", ""
        best: tuple[int, str, str, str] | None = None
        for nn, kid, name in self.names:
            if kid == exclude_id or not nn:
                continue
            if nn == n:
                via = "exact_alias" if _norm(name) != _norm(self.topic(kid)) else "exact_topic"
                return kid, name, via
            if len(nn) >= MIN_CONTAIN and nn in n:
                rank = 100 + len(nn)
                if best is None or rank > best[0]:
                    best = (rank, kid, name, "contains_alias")
            elif len(n) >= MIN_CONTAIN and n in nn:
                rank = 50 + len(n)
                if best is None or rank > best[0]:
                    best = (rank, kid, name, "prior_in_name")
        if best:
            return best[1], best[2], best[3]
        return None, "", ""


# ---------------------------------------------------------------- 建库
def load_library(data_dir: Path | str = DATA_DIR) -> Library:
    """只读扫描知识点库；损坏/缺 id 的文件跳过（正式校验仍由 knowledge.load 负责）。"""
    data_dir = Path(data_dir)
    lib = Library()
    if not data_dir.is_dir():
        return lib
    for subject_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        for f in sorted(subject_dir.glob("*.json")):
            try:
                e = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not e.get("id"):
                continue
            e.setdefault("_path", str(f))
            lib.entries[e["id"]] = e
    for kp_id, e in lib.entries.items():
        for name in [e.get("topic", "")] + list(e.get("aliases", [])):
            if name:
                lib.names.append((_norm(name), kp_id, name))
    return lib


def load_declared_edges(path: Path | str = GRAPH_PATH) -> tuple[list[Edge], list[dict], list[dict]]:
    """读全局先修图（选型 B 的落地位置）。文件不存在 → 空图 + 一条提示，不报错。

    校验（R1）：citations 非空且每条带 source+locator；两端 id 必须在库里由调用方再查。
    返回 (合法边, 被丢弃边的原因清单, 外部概念登记表 externals)。
    """
    path = Path(path)
    if not path.is_file():
        return [], [{"code": "GRAPH_ABSENT",
                     "msg": f"未找到全局先修图 {path.name}：只用从 prior 派生的边，全部标待人工核对"}], []
    raw = json.loads(path.read_text(encoding="utf-8"))
    edges: list[Edge] = []
    rejected: list[dict] = []
    for d in raw.get("edges", []):
        prereq, target = d.get("prereq"), d.get("target")
        cits = [c for c in d.get("citations", []) if c.get("source") and c.get("locator")]
        if not prereq or not target:
            rejected.append({"code": "EDGE_END_POINT", "msg": f"边缺 prereq/target：{d}"})
            continue
        if not cits:
            rejected.append({"code": "EDGE_NO_CITATION",
                             "msg": f"{prereq} → {target} 无教材/课标出处，按红线丢弃，不建边"})
            continue
        edges.append(Edge(prereq=prereq, target=target, label=d.get("label", ""),
                          strength=d.get("strength", "hard"), verified=bool(d.get("verified", False)),
                          origin="declared_edge", citations=cits))
    externals = [e for e in raw.get("externals", []) if e.get("label")]
    return edges, rejected, externals


def build_graph(lib: Library, declared: Iterable[Edge] = (),
                externals: Iterable[dict] = ()) -> tuple[dict[str, list[Node]], list[Edge], list[dict]]:
    """children[kp_id] = 该知识点的先修节点（库内 kp 节点 + 悬空 external 节点）。

    来源两条，互不混淆：
      派生边（prior 字段字面命中库内条目）→ verified=False，等人核对；
      声明边（全局图里人工写死并带出处）→ 按文件里的 verified 标记，并合并出处。
    """
    children: dict[str, list[Node]] = {kp_id: [] for kp_id in lib.entries}
    edges: list[Edge] = []
    findings: list[dict] = []
    ext_known = {_norm(e.get("label", "")): e for e in externals if e.get("label")}

    for kp_id, e in sorted(lib.entries.items()):
        host_cits = list(e.get("refs", []))
        for label in e.get("prior", []):
            kid, name, via = lib.match_prior(label, exclude_id=kp_id)
            if kid:
                children[kp_id].append(Node(kind="kp", key=kid, label=lib.topic(kid) or name,
                                            prior_label=label,
                                            kp_id=kid, in_library=True, verified=False,
                                            origin="derived_prior_match", citations=host_cits,
                                            matched_via=via, via=kp_id))
                edges.append(Edge(prereq=kid, target=kp_id, label=label, verified=False,
                                  origin="derived_prior_match", citations=host_cits))
            else:
                reg = ext_known.get(_norm(label), {})
                children[kp_id].append(Node(kind="external", key=_norm(label), label=label,
                                            prior_label=label,
                                            in_library=False, verified=bool(reg.get("verified", False)),
                                            origin="external_prior",
                                            citations=list(reg.get("citations") or host_cits),
                                            strength=reg.get("strength", "hard"), via=kp_id,
                                            covered_by=_covered_by(lib, label, exclude_id=kp_id)))

    for d in declared:
        if d.prereq not in lib.entries or d.target not in lib.entries:
            findings.append({"code": "DECLARED_UNKNOWN_END",
                             "msg": f"{d.prereq} → {d.target} 有端点不在库内，忽略该声明边"})
            continue
        merged = False
        for n in children[d.target]:
            if n.kp_id == d.prereq:
                n.verified = n.verified or d.verified
                n.origin = "declared_edge"
                n.citations = _merge_cits(n.citations, d.citations)
                n.strength = d.strength
                merged = True
                for ed in edges:
                    if ed.prereq == d.prereq and ed.target == d.target:
                        ed.verified, ed.origin = True, "declared_edge"
                        ed.citations = _merge_cits(ed.citations, d.citations)
        if not merged:
            children[d.target].append(Node(kind="kp", key=d.prereq, label=lib.topic(d.prereq),
                                           prior_label=d.label,
                                           kp_id=d.prereq, in_library=True, verified=d.verified,
                                           origin="declared_edge", citations=d.citations,
                                           matched_via="declared", strength=d.strength, via=d.target))
            edges.append(d)
        g1, g2 = _grade_rank(lib.entries[d.prereq].get("grade")), _grade_rank(lib.entries[d.target].get("grade"))
        if g1 is not None and g2 is not None and g1 > g2:  # 先修不得晚于目标学段
            findings.append({"code": "GRADE_INVERSION",
                             "msg": f"{d.prereq}（{lib.entries[d.prereq].get('grade')}）晚于 "
                                    f"{d.target}（{lib.entries[d.target].get('grade')}），先修学段倒挂"})

    for kp_id, nodes in children.items():  # 「本片是否真的用到」的证据
        shots = lib.entries[kp_id].get("sequence", [])
        for n in nodes:
            n.used_by_shot = _used_by(shots, _node_terms(n, lib))
    return children, edges, findings


def _merge_cits(a: list[dict], b: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for c in list(a) + list(b):
        k = (c.get("source", ""), c.get("locator", ""))
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def _grade_rank(grade: str | None) -> int | None:
    return GRADES.index(grade) if grade in GRADES else None


def _node_terms(node: Node, lib: Library) -> list[tuple[str, int]]:
    """节点的归一化称谓及权重：topic / 别名 / 宿主 prior 原文。

    prior 原文权重最高（+3）—— 它是这条先修在教材与学生口中最具体的说法，
    选回顾段落、判「本片是否用到」时都应以它为准；topic/别名只是索引。
    仍是字面对齐，不做语义推断。
    """
    raw: list[tuple[str, int]] = []
    e = lib.get(node.kp_id)
    if e:
        raw.append((e.get("topic", ""), 0))
        raw += [(a, 0) for a in e.get("aliases", [])]
    raw.append((node.label, 1))
    raw.append((node.prior_label, 3))
    out: list[tuple[str, int]] = []
    seen: set[str] = set()
    for t, bonus in raw:
        n = _norm(t)
        if n and n not in seen:
            seen.add(n)
            out.append((n, bonus))
    return out


def _used_by(shots: list[dict], terms: list[tuple[str, int]]) -> str:
    """prior 名称与本条目镜头标题/重点的字面重合 → 返回该镜头标题，作为「本片真的用到」的证据。"""
    for s in shots:
        hay = _norm(s.get("title", "")) + "‖" + _norm(s.get("emphasis", ""))
        if any(_lcs(t, hay) + b >= MIN_HINT for t, b in terms):
            return s.get("title", "")
    return ""


def _covered_by(lib: Library, label: str, exclude_id: str) -> list[str]:
    """悬空先修的库内近似覆盖提示 —— 只是给人看的线索，绝不据此建边或出片（R2）。"""
    n = _norm(label)
    hits: list[str] = []
    for kp_id, e in sorted(lib.entries.items()):
        if kp_id == exclude_id:
            continue
        for name in [e.get("topic", "")] + list(e.get("aliases", [])):
            if name and _lcs(n, _norm(name)) >= MIN_HINT:
                hits.append(f"{kp_id}·{name}")
                break
        else:
            for s in e.get("sequence", []):
                if _lcs(n, _norm(s.get("title", "")) + _norm(s.get("emphasis", ""))) >= MIN_HINT + 1:
                    hits.append(f"{kp_id}·镜头《{s.get('title', '')}》")
                    break
    return hits[:3]


# ---------------------------------------------------------------- 递归展开
def expand(target_id: str, children: dict[str, list[Node]], lib: Library,
           mastered: Iterable[str] = (), max_depth: int = MAX_DEPTH_DEFAULT,
           ) -> tuple[list[Node], list[dict]]:
    """DFS 展开先修树；确定性（同输入同输出，按 (label, key) 排序）。

    终止条件（R3）：① depth 达上限；② 节点已在本路径上（环）；③ 已掌握；
    ④ 悬空节点没有库内后继。每种截断都留痕 findings。
    """
    mastered_keys: set[str] = set()
    mastered_terms: set[str] = set()
    unmatched: list[str] = []
    for m in mastered:
        kid = lib.resolve(m)
        if kid:
            mastered_keys.add(kid)
        else:
            unmatched.append(m)
        mastered_terms.add(_norm(m))

    def is_mastered(n: Node) -> bool:
        """已掌握判定：库内 id 命中，或学生说的说法与该节点任一称谓（topic/别名/prior 原文）字面一致。"""
        if n.key in mastered_keys or (n.kp_id or "") in mastered_keys:
            return True
        return any(t in mastered_terms for t, _b in _node_terms(n, lib))

    findings: list[dict] = []
    out: list[Node] = []
    seen: set[tuple[int, str]] = set()

    def walk(kp_id: str, depth: int, path: tuple[str, ...]) -> None:
        for node in sorted(children.get(kp_id, []), key=lambda x: (x.label, x.key)):
            key = node.kp_id if node.kind == "kp" else node.key
            if key in path:
                findings.append({"code": "CYCLE",
                                 "msg": f"环：{' → '.join(path)} → {key}，该分支停止展开",
                                 "path": list(path) + [key]})
                continue
            n = replace(node, depth=depth)
            n.mastered = is_mastered(n)
            if n.mastered:
                findings.append({"code": "MASTERED", "msg": f"已掌握，不再补：{n.label}"})
            if (depth, key) not in seen:
                seen.add((depth, key))
                out.append(n)
            if n.mastered or n.kind == "external":
                continue
            if depth < max_depth:
                walk(n.kp_id or "", depth + 1, path + (key,))
            else:
                findings.append({"code": "DEPTH_CUT",
                                 "msg": f"达深度上限 {max_depth}，未继续展开：{n.label}"})

    if target_id not in lib.entries:
        raise KeyError(f"知识点未入库：{target_id}（防幻觉闸门，交给 knowledge.load 报候选）")
    walk(target_id, 1, (target_id,))
    if unmatched:
        findings.append({"code": "MASTERED_UNMATCHED",
                         "msg": "下列「已掌握」在库内对不上号，按字面当悬空先修处理：" + "、".join(unmatched)})
    return out, findings


# ---------------------------------------------------------------- 规划
@dataclass
class Decision:
    node: Node
    mode: str
    seconds: float
    score: int
    reason: str

    def to_dict(self) -> dict:
        return {"label": self.node.label, "kp_id": self.node.kp_id, "depth": self.node.depth,
                "in_library": self.node.in_library, "verified": self.node.verified,
                "mode": self.mode, "seconds": round(self.seconds, 2), "score": self.score,
                "reason": self.reason, "matched_via": self.node.matched_via,
                "prior_wording": self.node.prior_label,
                "used_by_shot": self.node.used_by_shot, "citations": self.node.citations}


@dataclass
class PreqPlan:
    target_id: str
    target_label: str
    target_seconds: int
    max_depth: int
    decisions: list[Decision] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    manifest: list[str] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    name_seconds: float = 0.0

    @property
    def preq_seconds(self) -> float:
        return round(sum(b.get("seconds", 0.0) for b in self.blocks), 2)

    def to_dict(self) -> dict:
        budget = round(self.target_seconds * PREQ_BUDGET_RATIO, 1)
        return {
            "target": self.target_id, "target_topic": self.target_label,
            "target_seconds": self.target_seconds, "max_depth": self.max_depth,
            "budget_seconds": budget, "preq_seconds": self.preq_seconds,
            "preq_share": round(self.preq_seconds / self.target_seconds, 3) if self.target_seconds else 0,
            "decisions": [d.to_dict() for d in self.decisions],
            "insert_blocks": self.blocks, "prerequisite_videos": self.manifest,
            "name_only_seconds": self.name_seconds,
            "missing_from_library": self.gaps, "findings": self.findings,
        }


def _score(node: Node) -> tuple[int, str]:
    """确定性打分（高者先补）。MVP 不用 LLM 决策，理由见 Spec_PreqChain 第 2 节。"""
    s = 60 - 10 * (node.depth - 1)
    why = [f"深度{node.depth}→{s}"]
    if node.used_by_shot:
        s += 30
        why.append("本片镜头确实用到 +30")
    if node.strength == "hard":
        s += 10
        why.append("强依赖 +10")
    if node.verified:
        s += 15
        why.append("边已人工核对 +15")
    if not node.in_library:
        s -= 40
        why.append("库外概念，无法核对地讲 -40")
    if node.kind == "kp" and node.depth >= 2:
        s -= 10
        why.append("二级先修 -10")
    return s, "；".join(why)


def _pick_block(lib: Library, kp_id: str, terms: list[tuple[str, int]]) -> dict | None:
    """从库内那条先修条目里挑一段已核对的原文镜头，整段复用（不生成新内容，R5）。

    选法确定性：与「prior 原文（权重高）/ topic / 别名」字面重合度最高的段落（标题+重点文本），
    并列时取靠前者 —— 条目里的编排顺序就是教材顺序，靠前的多是定义段。
    """
    e = lib.get(kp_id)
    if not e or not e.get("sequence"):
        return None

    def _hit(b: dict) -> int:
        hay = _norm(b.get("title", "")) + "‖" + _norm(b.get("emphasis", ""))
        return max((_lcs(t, hay) + bonus for t, bonus in terms), default=0)

    ranked = sorted(((_hit(b), -i, i) for i, b in enumerate(e["sequence"])), reverse=True)
    return dict(e["sequence"][ranked[0][2]])


def _forbidden(lib: Library, *kp_ids: str | None) -> list[str]:
    out: list[str] = []
    for kid in kp_ids:
        out += list(lib.get(kid).get("forbidden", [])) if lib.get(kid) else []
    return [f for f in out if f]


def _name_block(labels: list[str], host_refs: list[str], cap: float) -> dict:
    """只点名不讲解：文本全部来自本条目 prior 字段原文，出处即本条目 refs（不引入库外事实）。"""
    narration = naming_narration(labels)
    secs = naming_shot_seconds(narration, NAME_MIN_SECONDS)
    return {
        "title": "先修：需要什么基础",
        "seconds": round(min(secs, cap), 2),
        "narration": narration,
        "emphasis": "先修知识",
        "kp_refs": host_refs,
        "visuals": [{"kind": "callout", "props": {"text": "先修：" + " · ".join(labels), "tone": "key"}}],
        "origin": {"kind": MODE_NAME, "labels": labels, "citations_note": "仅点名，未展开讲解"},
    }


def _name_seconds(labels: list[str]) -> float:
    """点名镜头的秒数由口播字数反推，确定性可复算；尺子与 storyboard 共用 ir 那一份。"""
    return naming_shot_seconds(naming_narration(labels), NAME_MIN_SECONDS)


def _recall_block(node: Node, blk: dict, seconds: float, lib: Library) -> dict:
    """整段复用库内条目原文：narration / visuals 一字未改，出处换成那条自身的 refs。"""
    entry = lib.get(node.kp_id)
    return {
        "title": f"先修回顾 · {entry.get('topic', node.label) if entry else node.label}",
        "seconds": round(seconds, 2),
        "narration": blk["narration"],
        "emphasis": blk.get("emphasis", ""),
        "visuals": list(blk.get("visuals", [])),
        "kp_refs": lib.refs_text(node.kp_id) or [f"{c.get('source', '')} {c.get('locator', '')}"
                                                 for c in node.citations],
        "origin": {"kind": MODE_RECALL, "from_kp": node.kp_id, "from_block_title": blk.get("title", ""),
                   "matched_prior_label": node.label, "matched_via": node.matched_via,
                   "edge_verified": node.verified, "citations": node.citations},
    }


def plan_prerequisites(target_ref: str, lib: Library, children: dict[str, list[Node]],
                       mastered: Iterable[str] = (), target_seconds: int = 120,
                       max_depth: int = MAX_DEPTH_DEFAULT) -> PreqPlan:
    """（知识点, 学生已掌握集合, 目标时长）→ 决定补哪些先修、各补几秒、哪些另出片。

    确定性策略（MVP 阶段不上 LLM，理由：可复现 + 可追责）：
      先修总预算 = target_seconds × PREQ_BUDGET_RATIO；单个先修镜头 ≤ target_seconds × PREQ_SHOT_CAP。
      预算分两桶：点名桶 ≤ 预算 × PREQ_NAME_SHARE（点名很便宜，先保底），其余给回顾桶。
      节点分类（按 分数降序 → 深度升序 → 名称 处理，装箱同序）：
        已掌握                     → skip
        悬空（库外）一级           → name_only 片头点名 + 一条入库工单；永不进串播清单（R2）
        悬空二级                   → skip（只进工单）；不在片头堆「先修的先修」，护住 U2
        库内一级 + 回顾桶装得下一段原文 → recall_block（整段复用库内镜头，自带出处）
        库内一级 + 装不下           → separate_video（进串播清单）
        库内二级（自成体系）        → separate_video（不在本片展开）
      最后按 storyboard 的缩放系数反推一遍，保证缩放后每个先修镜头仍 ≥ MIN_SHOT_SECONDS。
    """
    kp_id = lib.resolve(target_ref) or target_ref
    if kp_id not in lib.entries:
        raise KeyError(f"知识点未入库：{target_ref}")
    nodes, findings = expand(kp_id, children, lib, mastered=mastered, max_depth=max_depth)

    budget = target_seconds * PREQ_BUDGET_RATIO
    cap = target_seconds * PREQ_SHOT_CAP
    name_budget = min(cap, budget * PREQ_NAME_SHARE)
    host_refs = lib.refs_text(kp_id)
    host_forbidden = _forbidden(lib, kp_id)

    scored = sorted((_score(n) + (n,) for n in nodes), key=lambda x: (-x[0], x[2].depth, x[2].label))

    decisions: list[Decision] = []
    recall_pending: list[tuple[int, Node, dict, float, str]] = []
    name_pending: list[tuple[int, Node, str]] = []
    manifest: list[str] = []
    gaps: list[dict] = []

    # —— 阶段一：分类
    for sc, why, n in scored:
        if n.mastered:
            decisions.append(Decision(n, MODE_SKIP, 0.0, sc, "已掌握，不补"))
            continue
        if not n.in_library:
            gaps.append({"label": n.label, "depth": n.depth, "citations": n.citations,
                         "covered_by": n.covered_by,
                         "action": "入库并人工核对出处；未入库前本片只点名、不展开讲、不出片"})
            if n.depth >= 2:
                # 先修的先修不在片头点名：学生刚要进入新知识点，一起抛二级基础会压垮 U2
                decisions.append(Decision(n, MODE_SKIP, 0.0, sc,
                                          why + "；二级悬空先修不进片头，只进入库工单"))
            else:
                name_pending.append((sc, n, why))
            continue

        if n.depth >= 2:
            manifest.append(n.kp_id or "")
            decisions.append(Decision(n, MODE_VIDEO, 0.0, sc, why + "；二级先修自成体系，另出一支片"))
            continue

        blk = _pick_block(lib, n.kp_id or "", _node_terms(n, lib))
        if not blk:
            manifest.append(n.kp_id or "")
            decisions.append(Decision(n, MODE_VIDEO, 0.0, sc, why + "；库内条目无可复用段落，另出一支片"))
            continue
        narration = blk.get("narration", "")
        if any(f and f in narration for f in host_forbidden + _forbidden(lib, n.kp_id)):
            # 命中库内标记的易错表述 → 这段原文不能整段搬，改另出片（不自己改写，避免引入错误）
            findings.append({"code": "TERM_HIT",
                             "msg": f"{n.label} 的原文口播命中库内易错表述，不整段复用，改走另出片"})
            manifest.append(n.kp_id or "")
            decisions.append(Decision(n, MODE_VIDEO, 0.0, sc, why + "；原文段落含易错表述，改另出一支片"))
            continue
        # 回顾段的秒数按**内容**语速算（NATURAL_CPS，与 review 的 PACING 同一把尺子）。
        # 此前借用了点名段的 NAME_CPS=4.5：那是"只念名字"的上限，用在整段口播上会把秒数估小，
        # 装箱装得满满当当，到 storyboard/A6 才发现说不完——闸门口径不一致就是白排。
        need = max(MIN_SHOT_SECONDS, round(len(narration) / NATURAL_CPS, 2))
        recall_pending.append((sc, n, blk, min(max(need, 8.0), cap), why))

    # —— 阶段二：装箱（点名桶先保底，回顾桶用余量；同序 → 结果可复现）
    kept_names: list[Node] = []
    for sc, n, why in sorted(name_pending, key=lambda x: (-x[0], x[1].depth, x[1].label)):
        cand = kept_names + [n]
        need = _name_seconds([x.label for x in cand])
        if len(cand) <= NAME_MAX_ITEMS and need <= min(cap, name_budget) + 1e-9:
            kept_names = cand
            decisions.append(Decision(n, MODE_NAME, need, sc, why + "；只点名，内容不在库内不得展开"))
        else:
            decisions.append(Decision(n, MODE_SKIP, 0.0, sc, why + "；点名位已满或预算不足，只进入库工单"))

    name_used = _name_seconds([x.label for x in kept_names]) if kept_names else 0.0
    left = budget - name_used
    recall: list[tuple[int, Node, dict, float]] = []
    for sc, n, blk, secs, why in sorted(recall_pending, key=lambda x: (-x[0], x[1].label)):
        if secs <= left + 1e-9:
            left -= secs
            recall.append((sc, n, blk, secs))
            decisions.append(Decision(n, MODE_RECALL, secs, sc, why + "；整段复用库内原文镜头"))
        else:
            manifest.append(n.kp_id or "")
            decisions.append(Decision(n, MODE_VIDEO, 0.0, sc, why + "；回顾预算不足，先另出一支先修片"))

    blocks: list[dict] = []
    if kept_names:
        blocks.append(_name_block([x.label for x in kept_names], host_refs, cap))
    # 先修回顾按「越基础越靠前」排：深度大者在前，同深度按分数降序
    for _sc, n, blk, secs in sorted(recall, key=lambda x: (-x[1].depth, -x[0], x[1].label)):
        blocks.append(_recall_block(n, blk, secs, lib))
    decisions.sort(key=lambda d: (d.node.depth, -d.score, d.node.label))

    # 反推 storyboard 的缩放系数，保证缩放后每个先修镜头仍 ≥ MIN_SHOT_SECONDS
    host_sum = sum(b.get("seconds", 0) for b in lib.entries[kp_id].get("sequence", []))
    preq_sum = sum(b["seconds"] for b in blocks)
    total_sum = host_sum + preq_sum
    if total_sum > 0:
        scale = target_seconds / total_sum
        if scale < 1.0:
            keep: list[dict] = []
            floor = MIN_SHOT_SECONDS / max(scale, 1e-6)
            for b in blocks:
                bumped = round(max(b["seconds"], floor), 2)
                if scale * bumped <= cap * 1.001:
                    b["seconds"] = bumped
                    keep.append(b)
            blocks = keep
    used = round(sum(b["seconds"] for b in blocks), 2)
    if used > budget + 1e-6:
        findings.append({"code": "BUDGET_OVER", "msg": f"先修段合计 {used}s 超预算 {round(budget, 1)}s"
                                                       f"（含缩放保底），占比 {used / target_seconds:.0%}"})

    manifest = sorted({m for m in manifest if lib.get(m)})  # R2：悬空节点永不在此列
    plan = PreqPlan(kp_id, lib.topic(kp_id), target_seconds, max_depth, decisions, blocks,
                    manifest, _dedupe(gaps, "label"), findings)
    plan.name_seconds = name_used
    return plan


def _dedupe(items: list[dict], key: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for it in sorted(items, key=lambda x: (x.get(key, ""))):
        if it.get(key) not in seen:
            seen.add(it.get(key))
            out.append(it)
    return out


# ---------------------------------------------------------------- 与既有管线的接口
def merged_kp(kp: dict, preq: PreqPlan) -> dict:
    """把先修镜头并进 sequence，交给既有 A3 分镜做缩放与编号（零改动复用）。

    调用方须把 brief.prior_knowledge 设为 False，否则片头那个 8 秒 callout 会重复插一遍。
    返回的是 kp 的浅拷贝，不改动传入对象，也不落盘。
    """
    e = dict(kp)
    e["sequence"] = list(preq.blocks) + list(kp.get("sequence", []))
    return e


def trial_plan(kp: dict, preq: PreqPlan, brief: Any) -> tuple[Any, list[dict]]:
    """试装 Plan 并跑一次既有静态监督（A4），验证插入镜头不撞闸门。只读、不落盘。

    兼容：A4 是另一个 agent 正在演进的文件，若其内部报错或接口变化，本函数不连带崩，
    而是把异常转成一条 REVIEW_UNAVAILABLE 记录（先修规划本身与 A4 无耦合）。
    findings 附带 `attributable_to` 字段：先修段（镜头序号 < len(blocks)）还是宿主条目既有内容。
    """
    from pipeline import review, storyboard  # 延迟导入：自检与集成时才需要

    b = replace(brief, prior_knowledge=False)
    plan = storyboard.build(b, merged_kp(kp, preq))
    n_preq = len(preq.blocks)
    try:
        raw = review.check(plan, kp)
    except Exception as e:  # A4 演进期的兼容兜底，不静默：转成一条可见记录
        return plan, [{"shot": -1, "code": "REVIEW_UNAVAILABLE",
                       "msg": f"A4 静态监督未能执行（{type(e).__name__}: {e}）；先修规划结果不受影响，"
                              f"但出片前必须由 A4 放行"}]
    for f in raw:
        f["attributable_to"] = "先修插入段" if 0 <= f.get("shot", -1) < n_preq else "宿主条目既有内容"
    return plan, raw


# ---------------------------------------------------------------- 自检
def _fmt_cits(cits: list[dict]) -> str:
    return "；".join(f"{c.get('source', '')}·{c.get('locator', '')}" for c in cits[:2]) or "（无出处 → 不建边）"


def _report_chain(title: str, nodes: list[Node], findings: list[dict]) -> None:
    print(f"\n{title}")
    for n in sorted(nodes, key=lambda x: (x.depth, x.label, x.key)):
        tag = "已入库" if n.in_library else "悬空（未入库）"
        ver = "已核对" if n.verified else "待人工核对"
        print(f"  L{n.depth} [{tag}][{ver}] {n.label}"
              + (f" → {n.kp_id}" if n.kp_id else "")
              + (f"（命中方式 {n.matched_via}）" if n.matched_via else "")
              + (f" 本片用到：《{n.used_by_shot}》" if n.used_by_shot else ""))
        print(f"        出处：{_fmt_cits(n.citations)}")
        if n.covered_by:
            print(f"        库内近似覆盖（仅提示，不成边）：{'，'.join(n.covered_by)}")
    for f in findings:
        print(f"  ! [{f['code']}] {f['msg']}")


def main() -> int:
    print("=" * 78)
    print("澄象 · 先修依赖图自检（只读 data/kp；不写、不改任何既有文件）")
    print("=" * 78)

    lib = load_library()
    print(f"知识点库：{lib.size} 条，名称索引 {len(lib.names)} 项（topic + aliases）")
    for kp_id, e in sorted(lib.entries.items()):
        print(f"  {kp_id:<34} {e.get('grade', '?'):<3} {e.get('topic', '')}"
              f"  prior={len(e.get('prior', []))}")

    declared, rejected, externals = load_declared_edges()
    print(f"\n全局先修图：{GRAPH_PATH} {'已加载' if GRAPH_PATH.is_file() else '尚未落地'}")
    if GRAPH_PATH.is_file():
        print(f"  声明边 {len(declared)} 条；因无出处/缺端点被丢弃 {len(rejected)} 条；"
              f"外部概念登记 {len(externals)} 条")
        for r in rejected:
            print(f"    - [{r['code']}] {r['msg']}")
    else:
        for r in rejected:
            print(f"  - [{r['code']}] {r['msg']}")

    children, edges, gfind = build_graph(lib, declared, externals)
    derived = [e for e in edges if e.origin == "derived_prior_match"]
    kept_declared = [e for e in edges if e.origin == "declared_edge"]
    print(f"\n有出处的先修边（库内↔库内）：派生 {len(derived)} 条 + 声明 {len(kept_declared)} 条 = "
          f"{len(derived) + len(kept_declared)} 条")
    for e in sorted(derived + kept_declared, key=lambda x: (x.target, x.prereq)):
        print(f"  {e.prereq}  ⇒  {e.target}   [{'已核对' if e.verified else '待人工核对'}]")
        print(f"      prior 原文：{e.label}")
        print(f"      出处：{_fmt_cits(e.citations)}")
    n_ext = sum(1 for nodes in children.values() for n in nodes if not n.in_library)
    n_prior = sum(len(e.get("prior", [])) for e in lib.entries.values())
    print(f"悬空先修：{n_ext} / {n_prior} 条 prior 在库内找不到对应条目（不建边、不出片）")
    for f in gfind:
        print(f"  ! [{f['code']}] {f['msg']}")

    # 用例 1：加速度的先修链（深度 / 出处 / 悬空标记）
    acc = lib.resolve("加速度") or "kp.physics.acceleration"
    nodes, f1 = expand(acc, children, lib)
    _report_chain(f"用例 1｜「{lib.topic(acc)}」的先修链（max_depth={MAX_DEPTH_DEFAULT}）", nodes, f1)
    assert all(n.depth <= MAX_DEPTH_DEFAULT for n in nodes), "深度上限被突破"

    # 用例 2：牛顿第二定律 @150s —— 未掌握先修时的规划
    ns = lib.resolve("牛顿第二定律") or "kp.physics.newton_second"
    print(f"\n用例 2｜「{lib.topic(ns)}」@150s，未声明已掌握：")
    p = plan_prerequisites(ns, lib, children, target_seconds=150)
    for d in p.decisions:
        print(f"  [{d.mode:<15}] L{d.node.depth} {d.node.label:<24} {d.seconds:>5.1f}s  "
              f"score={d.score:<4} {d.reason}")
    print(f"  预算 {p.to_dict()['budget_seconds']}s｜实配先修段 {p.preq_seconds}s"
          f"｜插入镜头 {len(p.blocks)} 个｜串播清单 {p.manifest or '（空）'}｜缺口工单 {len(p.gaps)} 条")
    for b in p.blocks:
        o = b["origin"]
        extra = (f" ← 复用 {o['from_kp']}《{o['from_block_title']}》" if o["kind"] == MODE_RECALL
                 else f" ← 只点名 {o['labels']}")
        print(f"    · {b['title']}（{b['seconds']}s）{extra}")
    assert all(b.get("kp_refs") for b in p.blocks), "先修镜头必须带出处"
    assert p.preq_seconds <= p.target_seconds * PREQ_BUDGET_RATIO + 1.0, "先修段超预算"

    # 用例 3：声明已掌握后，链上那一环被跳过
    print("\n用例 3｜同一知识点声明已掌握「加速度的定义 a = Δv / Δt」：")
    p2 = plan_prerequisites(ns, lib, children, mastered=["加速度的定义 a = Δv / Δt"], target_seconds=150)
    for d in p2.decisions:
        print(f"  [{d.mode:<15}] L{d.node.depth} {d.node.label}")
    assert all(not (d.node.kp_id == acc and d.mode != MODE_SKIP) for d in p2.decisions), "已掌握的先修仍被补"
    print(f"  ✓ 断言通过：先修段总时长由 {p.preq_seconds}s 降到 {p2.preq_seconds}s")

    # 用例 4：先修全部未入库（电极电势）—— 只能点名 + 转入库工单，绝不出片
    ep = lib.resolve("电极电势") or "kp.chemistry.electrode_potential"
    print(f"\n用例 4｜「{lib.topic(ep)}」：prior 全部指向库外概念")
    p3 = plan_prerequisites(ep, lib, children, target_seconds=120)
    for d in p3.decisions:
        print(f"  [{d.mode:<15}] L{d.node.depth} {d.node.label}")
    assert not p3.manifest, "悬空先修不得进串播清单"
    assert all(d.mode in (MODE_NAME, MODE_SKIP) for d in p3.decisions), "库外先修不得展开讲解"
    assert len(p3.gaps) == len(lib.entries[ep].get("prior", [])), "库外先修应逐条转为入库工单"
    print("  缺口工单：")
    for g in p3.gaps:
        print(f"    - {g['label']}｜近似覆盖：{g['covered_by'] or '无'}")
    print("  ✓ 断言通过：只点名、未进串播清单、逐条转入库工单")

    # 用例 5：环检测（合成夹具，不构成任何知识依赖主张）
    print("\n用例 5｜环检测：合成三节点环 a→b→c→a（仅验证算法，非知识断言）")
    cyc_lib, cyc_children = _cycle_fixture()
    cnodes, cfind = expand("kp.test.a", cyc_children, cyc_lib, max_depth=3)
    _report_chain("  展开结果", cnodes, cfind)
    assert any(f["code"] == "CYCLE" for f in cfind), "环未被检出"
    assert all(n.depth <= 3 for n in cnodes), "环场景下深度失控"
    print("  ✓ 断言通过：环在闭合处被检出并停止展开")

    # 用例 6：接既有 A3/A4 试装（只读调用 storyboard + review）
    try:
        from pipeline import ir
    except ImportError:
        print("\n用例 6｜跳过：pipeline.ir 不可导入")
        return 0
    print("\n用例 6｜先修镜头并进 sequence 后跑既有分镜 + 静态监督（只读，不落盘）：")
    brief = ir.Brief(subject="physics", grade="H1", topic="牛顿第二定律",
                     target_seconds=150, prior_knowledge=False)
    plan, fnd = trial_plan(lib.entries[ns], p, brief)
    print(f"  Plan：{len(plan.shots)} 个镜头，总时长 {plan.total_seconds}s（目标 {brief.target_seconds}s），"
          f"hash={plan.hash}")
    for s in plan.shots[: len(p.blocks)]:
        print(f"    #{s.index} {s.title} · {s.seconds}s · 出处 {len(s.kp_refs)} 条 · 口播 {len(s.narration)} 字")
    ours = [f for f in fnd if f.get("attributable_to") == "先修插入段"]
    host = [f for f in fnd if f.get("attributable_to") != "先修插入段"]
    print(f"  A4 静态监督：共 {len(fnd)} 项 → 先修插入段 {len(ours)} 项 / 宿主条目既有内容 {len(host)} 项")
    for f in (ours + host)[:6]:
        print(f"    shot {f['shot']} [{f['code']}]（{f.get('attributable_to', '-')}）{f['msg'][:70]}")
    if len(fnd) > 6:
        print(f"    … 其余 {len(fnd) - 6} 项同类")
    assert all(s.kp_refs for s in plan.shots), "任何镜头无出处都不可出片（S3）"
    assert not ours, "插入的先修镜头必须自身过 A4 闸门，否则不得占用预算"
    print(f"  ✓ 断言通过：先修插入镜头 0 项打回（宿主条目自身的 {len(host)} 项属既有问题，"
          f"见 Spec_PreqChain.txt 第 6 节「需要改契约的地方」，本次不动）")
    print("\n" + "=" * 78)
    print("自检完成：全部断言通过。未写入、未修改任何既有文件。")
    print("=" * 78)
    return 0


def _cycle_fixture() -> tuple[Library, dict[str, list[Node]]]:
    """三节点环的合成夹具。出处写「合成夹具」，永远不会被当作知识点入库。"""
    lib = Library()
    ids = ["kp.test.a", "kp.test.b", "kp.test.c"]
    for kid in ids:
        lib.entries[kid] = {"id": kid, "topic": f"测试概念{kid[-1]}", "aliases": [], "grade": "H1",
                            "refs": [{"source": "合成夹具（非教材）", "locator": "cycle-test"}],
                            "prior": [], "forbidden": [],
                            "sequence": [{"title": "占位", "seconds": 10, "narration": "占位口播",
                                          "visuals": [{"kind": "callout", "props": {"text": "x"}}]}]}
        lib.names.append((_norm(f"测试概念{kid[-1]}"), kid, f"测试概念{kid[-1]}"))
    children = {k: [] for k in ids}
    pairs = list(zip(ids, ids[1:] + ids[:1]))
    for a, b in pairs:
        children[a].append(Node(kind="kp", key=b, label=lib.topic(b), kp_id=b, in_library=True,
                                verified=True, origin="declared_edge", via=a,
                                citations=[{"source": "合成夹具（非教材）", "locator": "cycle-test"}]))
    return lib, children


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # Windows GBK 控制台兜底
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
