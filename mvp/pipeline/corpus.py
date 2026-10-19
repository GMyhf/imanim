# -*- coding: utf-8 -*-
"""A2.5 语料检索：对 OCR 抽取的教材纯文本做字面 grep（与 knowledge.py 一样刻意不调 LLM）。

语料形态（由 mvp/tools_corpus.py 从 OCR 后的 PDF 抽出）：
    mvp/pipeline/data/corpus/<subject>/<book_slug>.txt       正文，页与页之间用「===== 第 N 页 =====」隔开
    mvp/pipeline/data/corpus/<subject>/<book_slug>.meta.json  {"title": "书名", ...}，缺文件时书名退回 slug

kp_draft 起草前先 search()；命中才允许草稿带 refs（source=书名、locator=第 N 页），
knowledge.save_draft 落盘前再用 validate_refs() 复核一遍——出处只能来自语料命中，不许编。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "data" / "corpus"

_PAGE_MARK = re.compile(r"^=+\s*第\s*(\d+)\s*页\s*=*$", re.M)
_SPLIT_RE = re.compile(r"[\s,，。；;、/|（）()]+")
_MAX_EXCERPT = 400   # 摘录喂给 K0，宁短勿长
_MAX_PER_BOOK = 3    # 单本教材最多贡献几条命中，防止一本霸榜


@dataclass
class Hit:
    subject: str
    book: str        # slug
    source: str      # 展示名（书名）
    page: int
    excerpt: str


@lru_cache(maxsize=64)
def _pages(path: Path, mtime_ns: int) -> list[tuple[int, str]]:
    """(页码, 该页文本)。mtime_ns 参与缓存键：语料在镜像里不变，本机补 OCR 后自动失效。"""
    text = path.read_text(encoding="utf-8")
    marks = list(_PAGE_MARK.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((int(m.group(1)), text[m.end():end]))
    return out


def books(subject: str) -> list[tuple[str, dict]]:
    """(slug, meta) 列表。meta 缺文件或损坏时退回 {"title": slug}。"""
    d = CORPUS_DIR / subject
    if not d.is_dir():
        return []
    out = []
    for txt in sorted(d.glob("*.txt")):
        meta = {}
        m = txt.with_suffix(".meta.json")
        if m.is_file():
            try:
                meta = json.loads(m.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        if not isinstance(meta, dict) or not str(meta.get("title") or "").strip():
            meta = {"title": txt.stem}
        out.append((txt.stem, meta))
    return out


def terms(query: str) -> list[str]:
    """全串 + 空白/标点切出的词 + 双字滑窗。全串命中计分最高（「楞次定律」逐字出现在原文），
    滑窗兜底主题词被打散进长句的情况。中文没有分词器，不做更复杂的切词。"""
    q = str(query or "").strip()
    if not q:
        return []
    parts = [p for p in _SPLIT_RE.split(q) if p]
    grams = [q[i:i + 2] for i in range(len(q) - 1)] if len(q) >= 2 else []
    seen, out = set(), []
    for t in [q] + parts + grams:
        t = t.strip()
        if len(t) >= 2 and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _excerpt(content: str, term: str) -> str:
    idx = content.find(term)
    if idx < 0:
        return content.strip()[: _MAX_EXCERPT]
    start = max(0, idx - 120)
    end = min(len(content), idx + len(term) + 280)
    head = "…" if start > 0 else ""
    tail = "…" if end < len(content) else ""
    return head + content[start:end].strip() + tail


def search(subject: str, query: str, max_hits: int = 5) -> list[Hit]:
    """按页计分（全串命中每次 4 分，其余切词/双字组每次 1 分），返回得分最高的若干命中。"""
    ts = terms(query)
    if not ts:
        return []
    full, parts = ts[0], ts[1:]
    scored: list[tuple[int, str, str, int, str]] = []
    for slug, meta in books(subject):
        txt = CORPUS_DIR / subject / f"{slug}.txt"
        try:
            pages = _pages(txt, txt.stat().st_mtime_ns)
        except OSError:
            continue
        source = str(meta.get("title") or slug)
        for page, content in pages:
            # 全串逐字命中计 4 分，其余词条各计 1 分：整串命中远重于零散词命中
            score = content.count(full) * 4 + sum(content.count(t) for t in ts[1:])
            if score <= 0:
                continue
            scored.append((score, slug, source, page, content))
    scored.sort(key=lambda x: (-x[0], x[1], x[3]))
    hits, per_book = [], {}
    for score, slug, source, page, content in scored:
        if per_book.get(slug, 0) >= _MAX_PER_BOOK:
            continue
        anchor = full if content.find(full) >= 0 else next(
            (t for t in parts if content.find(t) >= 0), ts[-1])
        hits.append(Hit(subject, slug, source, page, _excerpt(content, anchor)))
        per_book[slug] = per_book.get(slug, 0) + 1
        if len(hits) >= max_hits:
            break
    return hits


def _page_numbers(subject: str, book: str) -> set[int]:
    txt = CORPUS_DIR / subject / f"{book}.txt"
    try:
        return {p for p, _ in _pages(txt, txt.stat().st_mtime_ns)}
    except OSError:
        return set()


def validate_refs(subject: str, refs: list) -> list[str]:
    """复核草稿 refs 是否真的来自语料命中。返回问题清单（空=通过）。"""
    problems = []
    if not refs:
        return problems
    known = {str(m.get("title") or slug): slug for slug, m in books(subject)}
    for r in refs:
        if not isinstance(r, dict):
            problems.append(f"refs 条目不是对象：{r!r}")
            continue
        source, locator = str(r.get("source") or ""), str(r.get("locator") or "")
        slug = known.get(source) or known.get(source.strip())
        if not slug:
            problems.append(f"refs 来源「{source or '(空)'}」不在语料库里——出处只能来自语料检索命中")
            continue
        m = re.fullmatch(r"第\s*(\d+)\s*页", locator.strip())
        if not m:
            problems.append(f"refs 定位语「{locator or '(空)'}」不是「第 N 页」形态")
            continue
        if int(m.group(1)) not in _page_numbers(subject, slug):
            problems.append(f"《{source}》没有第 {m.group(1)} 页——locator 必须是命中页")
    return problems
