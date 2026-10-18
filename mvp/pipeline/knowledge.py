"""A2 资料调用：本地知识点库检索。

这一层刻意不调用 LLM —— 内容要么来自可核对的库，要么来自 kp_draft 起草、明确标了
origin="model_draft"（无出处、待人工核对）的自动条目；两种都从文件读，命中不了就终止（Spec_Workflow A2）。
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "kp"
# kp_draft（K0）起草的库外知识点落这里。load 会一起扫，所以下游（storyboard/prereq/jobrunner）
# 不必知道自己读的是库内条目还是自动条目——单一真源仍是文件。
AUTO_DIR = Path(__file__).resolve().parent / "data" / "kp_auto"

REQUIRED_FIELDS = ("id", "subject", "grade", "topic", "refs", "sequence")


class KnowledgeNotFound(KeyError):
    def __init__(self, subject: str, topic: str, candidates: list[str]):
        super().__init__(f"资料库中没有 {subject}/{topic}")
        self.candidates = candidates


def _entries(subject: str) -> list[dict]:
    out = []
    for base in (DATA_DIR, AUTO_DIR):
        d = base / subject
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                raise ValueError(f"知识点库文件损坏：{f} → {e}") from e
    return out


def load(subject: str, topic: str, grade: str | None = None) -> dict:
    """精确匹配 topic 或别名；未命中则抛 KnowledgeNotFound 并附候选清单。

    grade 不为空时还要求学段一致——同名的不同学段条目不能混用（出处不同）。
    """
    entries = _entries(subject)
    wrong_grade: list[str] = []
    for e in entries:
        names = [e.get("topic", "")] + list(e.get("aliases", []))
        if topic in names or topic == e.get("id"):
            if grade and e.get("grade") != grade:
                wrong_grade.append(f"{e.get('topic')}（库内学段 {e.get('grade')}，请求 {grade}）")
                continue
            _check(e)
            return e
    raise KnowledgeNotFound(subject, topic, wrong_grade or [e.get("topic", "") for e in entries])


def _check(e: dict) -> None:
    # 自动草稿条目（origin=model_draft）本来就没有教材出处，refs 必须留空——
    # 这里不能因为它诚实地留空就判它缺字段。
    required = [k for k in REQUIRED_FIELDS if k != "refs" or not e.get("origin")]
    missing = [k for k in required if not e.get(k)]
    if missing:
        raise ValueError(f"知识点 {e.get('id', '?')} 缺字段：{missing}")
    for r in e["refs"]:
        if not isinstance(r, dict) or not r.get("source") or not r.get("locator"):
            raise ValueError(f"知识点 {e['id']} 的 refs 必须是含 source/locator 的对象，收到：{r!r}")
    for i, b in enumerate(e["sequence"]):
        if not isinstance(b, dict):
            raise ValueError(f"知识点 {e['id']} 的 sequence[{i}] 不是对象：{b!r}")
        lack = [k for k in ("title", "seconds", "narration", "visuals") if not b.get(k)]
        if lack:
            raise ValueError(f"知识点 {e['id']} 的 sequence[{i}]（{b.get('title', '?')}）缺字段：{lack}")


def save_draft(entry: dict) -> Path:
    """把 kp_draft（K0）的产出写进自动库。同 id 覆盖（人工改过这条草稿后再起草也会覆盖，
    所以改动想留存就先改 id 或搬进 kp/）。"""
    if entry.get("origin") != "model_draft":
        raise ValueError("只有 origin=model_draft 的条目能走 save_draft，库内条目不许被覆盖")
    if entry.get("refs"):
        raise ValueError("自动草稿不能带 refs（未核对的出处就是编造）")
    _check(entry)
    d = AUTO_DIR / str(entry["subject"])
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{entry['id'].rsplit('.', 1)[-1]}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path
