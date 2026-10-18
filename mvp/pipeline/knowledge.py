"""A2 资料调用：本地知识点库检索。

这一层刻意不调用 LLM —— 内容必须来自可核对的库，命中不了就终止（Spec_Workflow A2）。
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "kp"

REQUIRED_FIELDS = ("id", "subject", "grade", "topic", "refs", "sequence")


class KnowledgeNotFound(KeyError):
    def __init__(self, subject: str, topic: str, candidates: list[str]):
        super().__init__(f"资料库中没有 {subject}/{topic}")
        self.candidates = candidates


def _entries(subject: str) -> list[dict]:
    d = DATA_DIR / subject
    if not d.is_dir():
        return []
    out = []
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
    missing = [k for k in REQUIRED_FIELDS if not e.get(k)]
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
