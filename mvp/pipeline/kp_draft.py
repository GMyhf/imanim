# -*- coding: utf-8 -*-
"""库外知识点起草（K0）：用户写的知识点不在库里时，由网关模型产出一条「未核对出处」的条目草稿。

与 knowledge.py 的分工：knowledge 只读库、自己绝不调模型；起草只在库里没有时发生，
产出物落进自动库（pipeline/data/kp_auto/），此后每一次读取都走 knowledge.load 的同一道校验——
单一真源不变，草稿也是文件，可被人逐字改。

诚实口径：草稿的 refs 恒为空（不冒充教材出处），条目带 origin="model_draft"，
界面上必须标成「模型起草、未核对出处」。
"""

from __future__ import annotations

import hashlib
import re

from . import knowledge, llm_client, llm_prompts
from .ir import NATURAL_CPS

# 与 render/scene.py 的 Scene.BUILDERS 同一份清单（tests/test_kp_draft.py 里做了比对，防漂移）。
VISUAL_KINDS = ("axis_graph", "callout", "compare", "energy_dist", "figure", "formula", "graph_vt",
                "microstate", "mind_map", "particle_box", "stat_chart", "steps", "summary",
                "table", "title")

MAX_ATTEMPTS = 2       # 第一版 + 一次带问题清单的重写
MIN_SHOTS, MAX_SHOTS = 4, 10


class DraftError(RuntimeError):
    """起草失败。消息给人看，不含密钥，也不含半成品的伪成功。"""


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or ""))


def _texts(entry: dict) -> str:
    """条目里所有会念出口或写上屏的文字，拼成一个串供 forbidden/must_say 核对。"""
    out = []
    for b in entry.get("sequence") or []:
        out.append(str(b.get("narration") or ""))
        out.append(str(b.get("title") or ""))
        out.append(str(b.get("emphasis") or ""))
        for v in b.get("visuals") or []:
            out.append(re.sub(r"[{}\[\]\"' :,]+", " ", str(v.get("props") or {})))
    return "\n".join(out)


def _user_message(subject: str, grade: str, topic: str, target_seconds: float,
                  raw_text: str, problems: list[str] | None) -> str:
    lines = [f"学科：{subject}；学段：{grade}；知识点：{topic}",
             f"目标总时长：{target_seconds:g} 秒（口播总量按这个时长控制）。",
             "refs 必须是空数组：这条内容还没核对过教材出处，不许编出处。"]
    if raw_text:
        lines.append(f"用户的补充要求：{raw_text}")
    if problems:
        lines.append("【上一版的问题，逐条改正后重新输出完整 JSON】")
        lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)


def _check_shape(entry: dict, topic: str) -> list[str]:
    errs: list[str] = []
    if not isinstance(entry, dict):
        return ["输出不是 JSON 对象"]
    if _norm(entry.get("topic")) != _norm(topic):
        errs.append(f"topic 必须逐字等于用户写的「{topic}」")
    if entry.get("refs"):
        errs.append("refs 必须是空数组（未核对过教材出处，不许写出处）")
    for k in ("must_say", "forbidden"):
        v = entry.get(k)
        if not isinstance(v, list) or not v:
            errs.append(f"{k} 必须是非空字符串数组")
    seq = entry.get("sequence")
    if not isinstance(seq, list) or not (MIN_SHOTS <= len(seq) <= MAX_SHOTS):
        errs.append(f"sequence 必须是 {MIN_SHOTS}~{MAX_SHOTS} 个镜头")
        return errs
    for i, b in enumerate(seq, 1):
        if not isinstance(b, dict):
            errs.append(f"第 {i} 镜不是对象")
            continue
        lack = [k for k in ("title", "seconds", "narration", "visuals") if not b.get(k)]
        if lack:
            errs.append(f"第 {i} 镜缺字段：{lack}")
            continue
        if not isinstance(b["visuals"], list) or not b["visuals"]:
            errs.append(f"第 {i} 镜 visuals 必须是非空数组")
            continue
        for v in b["visuals"]:
            kind = v.get("kind") if isinstance(v, dict) else None
            if kind not in VISUAL_KINDS:
                errs.append(f"第 {i} 镜的版式 kind={kind!r} 不在渲染层支持的 15 种里")
            elif not isinstance(v.get("props"), dict):
                errs.append(f"第 {i} 镜 {kind} 的 props 必须是对象")
    return errs


def _check_content(entry: dict, target_seconds: float) -> list[str]:
    """闸门会查的三件事，先在起草层自查一轮，省掉一次注定失败的出片。"""
    errs: list[str] = []
    texts = _norm(_texts(entry))
    for phrase in entry.get("must_say") or []:
        if _norm(phrase) not in texts:
            errs.append(f"must_say 里的「{phrase}」在任何一镜的口播/屏上文字里都找不到——要么写进口播，要么从 must_say 删掉")
    for word in entry.get("forbidden") or []:
        if _norm(word) and _norm(word) in texts:
            errs.append(f"forbidden 里的「{word}」出现在了成片文字里——必须改写口播/屏上内容，不能把它从 forbidden 删掉来蒙过检查")
    seq = entry.get("sequence") or []
    chars = sum(len(str(b.get("narration") or "")) for b in seq)
    budget = max(1.0, target_seconds - len(seq) * 1.15) * NATURAL_CPS
    if chars > budget:
        errs.append(f"口播总字数 {chars} 超过目标时长允许的约 {int(budget)} 字，请精简口播（宁少勿多）")
    return errs


def _id(subject: str, grade: str, topic: str) -> str:
    return f"draft.{subject}.{hashlib.sha1(f'{grade}|{topic}'.encode('utf-8')).hexdigest()[:10]}"


def draft(subject: str, grade: str, topic: str, target_seconds: float = 120.0,
          raw_text: str = "") -> dict:
    """产出一条自动草稿条目并落进自动库，返回它经 knowledge.load 复核后的样子。

    调用方（jobrunner）只在 knowledge.load 抛 KnowledgeNotFound 之后才走到这里，
    所以库内条目永远不会被模型改写；同一知识点第二次生成会命中上一次的草稿文件，不再烧额度。
    """
    if not llm_client.enabled("K0"):
        raise DraftError(
            f"知识点库里没有「{topic}」，补这条内容需要模型起草，但生成环节当前未开启"
            "（部署侧需 QX_LLM_K0=1 或 QX_LLM_ALL=1，并配好密钥）")
    topic = str(topic).strip()
    entry: dict = {}
    problems: list[str] = []
    for attempt in range(MAX_ATTEMPTS):
        raw = llm_client.chat("K0", llm_prompts.K0_SYSTEM,
                              _user_message(subject, grade, topic, target_seconds, raw_text, problems),
                              max_tokens=8000, json_mode=True)
        entry = llm_client.extract_json(raw)
        entry["topic"] = topic          # 归一：topic 永远以用户原文为准
        entry["refs"] = []              # 铁律：草稿不写出处
        problems = _check_shape(entry, topic) + _check_content(entry, target_seconds)
        if not problems:
            break
    if problems:
        raise DraftError("知识点起草未通过自检（已重写一次）：" + "；".join(problems[:6]))

    entry.update({"id": _id(subject, grade, topic), "subject": subject,
                  "grade": grade, "origin": "model_draft"})
    knowledge.save_draft(entry)
    try:
        return knowledge.load(subject, topic, grade)
    except (knowledge.KnowledgeNotFound, ValueError) as e:
        raise DraftError(f"草稿落库后仍读不到（自动库异常）：{e}") from e
