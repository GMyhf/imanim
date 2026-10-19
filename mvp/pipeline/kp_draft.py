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
import time

from . import knowledge, llm_client, llm_prompts, review
from .ir import NAME_MAX_SHARE, NATURAL_CPS, naming_narration, naming_shot_seconds

# 与 render/scene.py 的 Scene.BUILDERS 同一份清单（tests/test_kp_draft.py 里做了比对，防漂移）。
VISUAL_KINDS = ("axis_graph", "callout", "compare", "energy_dist", "figure", "formula", "graph_vt",
                "microstate", "mind_map", "particle_box", "stat_chart", "steps", "summary",
                "table", "title")

MAX_ATTEMPTS = 3       # 第一版 + 两次带问题清单的重写
MIN_SHOTS, MAX_SHOTS = 4, 10
MAX_PRIOR_CHARS = 12  # 点名镜头把它们逐条念出来并整行上屏，整句会爆字数与字号
GRADE_ZH = {"G8": "初二", "G9": "初三", "H1": "高一", "H2": "高二", "H3": "高三", "U1": "大一", "U2": "大二"}


class DraftError(RuntimeError):
    """起草失败。消息给人看，不含密钥，也不含半成品的伪成功。"""


def _norm(s: str) -> str:
    """与 review._flat 同口径：去空白与标点再比，两道闸不能一松一紧。"""
    return review._flat(str(s or ""))


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
    lines = [f"学科：{subject}；学段：{GRADE_ZH.get(grade, grade)}（讲解深度按这个学段控制）；知识点：{topic}",
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
    prior = entry.get("prior")
    if not isinstance(prior, list) or len(prior) > 3 or any(
            not isinstance(p, str) or not p.strip() or len(p) > MAX_PRIOR_CHARS for p in prior):
        errs.append(f"prior 必须是最多 3 条的字符串数组，每条是不超过 {MAX_PRIOR_CHARS} 字的名词短语"
                    "（如「磁通量的含义」），不要写成整句")
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
    # 开了「先修」时，分镜会在正片前加一段点名镜头（storyboard.build），它先吃掉自己的秒数
    prior = [p for p in (entry.get("prior") or []) if isinstance(p, str) and p.strip()]
    naming = 0.0
    if prior:
        need, cap = naming_shot_seconds(naming_narration(prior)), NAME_MAX_SHARE * target_seconds
        if need > cap:
            # 点名镜头最多占全片 15%，超出部分闸门会判 OVERLOAD；短片只能少点几条或不点
            errs.append(f"prior 太长：点名镜头念完要 {need:.1f}s，{target_seconds:g}s 的片子只给它 {cap:.1f}s；"
                        "删掉次要的条目、缩短措辞，或直接给空数组")
        naming = min(need, cap)
    budget = max(1.0, target_seconds - naming - len(seq) * 1.15) * NATURAL_CPS
    if chars > budget:
        errs.append(f"口播总字数 {chars} 超过目标时长允许的约 {int(budget)} 字，请精简口播（宁少勿多）")
    return errs


def _keep_rejected(subject: str, topic: str, raw: str, problems: list[str]) -> None:
    """起草失败时留下模型原始输出，事后才分得清是标点差异还是模型真的改写了。
    放在 AUTO_DIR/_rejected 下、扩展名 .txt：knowledge 只读 AUTO_DIR/<学科>/*.json，读不到它。"""
    try:
        d = knowledge.AUTO_DIR / "_rejected"
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (d / f"{stamp}-{_id(subject, '', topic)[-10:]}.txt").write_text(
            "问题：\n" + "\n".join(problems) + "\n\n模型原始输出：\n" + raw, encoding="utf-8")
    except OSError:
        pass


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
    raw = ""
    for attempt in range(MAX_ATTEMPTS):
        raw = llm_client.chat("K0", llm_prompts.K0_SYSTEM,
                              _user_message(subject, grade, topic, target_seconds, raw_text, problems),
                              max_tokens=8000, json_mode=True)
        try:
            entry = llm_client.extract_json(raw)
        except llm_client.LLMError:
            entry = None
        if not isinstance(entry, dict):
            problems = ["输出不是一个合法的 JSON 对象，请只输出完整 JSON"]
            continue
        entry["topic"] = topic          # 归一：topic 永远以用户原文为准
        entry["refs"] = []              # 铁律：草稿不写出处
        problems = _check_shape(entry, topic) + _check_content(entry, target_seconds)
        if not problems:
            break
    if problems:
        _keep_rejected(subject, topic, raw, problems)
        raise DraftError(f"知识点起草未通过自检（已重试 {MAX_ATTEMPTS - 1} 次）：" + "；".join(problems[:6]))

    entry.update({"id": _id(subject, grade, topic), "subject": subject,
                  "grade": grade, "origin": "model_draft"})
    knowledge.save_draft(entry)
    try:
        return knowledge.load(subject, topic, grade)
    except (knowledge.KnowledgeNotFound, ValueError) as e:
        raise DraftError(f"草稿落库后仍读不到（自动库异常）：{e}") from e
