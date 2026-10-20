# -*- coding: utf-8 -*-
"""库外知识点起草（K0）：用户写的知识点不在库里时，由网关模型产出一条条目草稿。

与 knowledge.py 的分工：knowledge 只读库、自己绝不调模型；起草只在库里没有时发生，
产出物落进自动库（pipeline/data/kp_auto/），此后每一次读取都走 knowledge.load 的同一道校验——
单一真源不变，草稿也是文件，可被人逐字改。

诚实口径：起草前先做语料检索（pipeline/corpus.py，字面 grep）。命中则把摘录喂给模型、
refs 只允许照抄命中清单（source=书名、locator=第 N 页），落盘前 save_draft 再复核一遍；
未命中则 refs 恒空、条目带 origin="model_draft"，界面上标成「模型起草、未核对出处」。
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import time

from . import corpus, knowledge, llm_client, llm_prompts, review
from .ir import ACCEPTABLE_RATE, NAME_MAX_SHARE, NATURAL_CPS, RATE_FACTOR, naming_narration, naming_shot_seconds
from .storyboard import MIN_SHOTS, max_shots_for  # 81-A1b：镜头密度单一真源在 A3 分镜层，两处校验不得各写一份

# 与 render/scene.py 的 Scene.BUILDERS 同一份清单（tests/test_kp_draft.py 里做了比对，防漂移）。
VISUAL_KINDS = ("axis_graph", "callout", "circuit", "compare", "derivation", "energy_dist", "field", "figure",
                "force_diagram", "formula", "graph_vt", "incline", "mechanism", "microstate", "mind_map",
                "optics", "particle_box", "rod_rails", "stat_chart", "steps", "summary", "table", "title",
                "trajectory")

MAX_ATTEMPTS = 3       # 第一版 + 两次带问题清单的重写
# MIN_SHOTS / max_shots_for 见 storyboard（81-A1b）：镜头数上限随目标时长伸缩，短片仍是旧口径 10。
MAX_PRIOR_CHARS = 12  # 点名镜头把它们逐条念出来并整行上屏，整句会爆字数与字号
# 84-T1/T2：must_say 只允许「逐字摘自口播的连续片段」，超过这个长度的几乎都是重写出来的抽象断言——
# 线上 g20261020-130402-8ae0e5 三条 30+ 字的 must_say 把整段生成打死的直接原因。
MUST_SAY_MAX_CHARS = 25
GRADE_ZH = {"G8": "初二", "G9": "初三", "H1": "高一", "H2": "高二", "H3": "高三", "U1": "大一", "U2": "大二"}


class DraftError(RuntimeError):
    """起草失败。消息给人看，不含密钥，也不含半成品的伪成功。"""


# 84-T4：DraftError 走到前端时必须带一句可直接照做的建议（web 与 CLI 共用同一处映射，别写两份）。
DRAFT_ERROR_SUGGESTION = ("这条知识点一次讲不下或范围太宽：把知识点名收窄成一个具体概念（一支片只讲一个），"
                          "或把目标时长放宽到 180 秒以上后重试。若反复失败，请通过问题反馈附上任务号。")


def to_generation_error(e: DraftError):
    """把 DraftError 映射成带人话建议的 GenerationError（kind=content，findings 留空不伪造清单）。"""
    from run import GenerationError      # 延迟导入：run.py 模块级就 import kp_draft，不能反过来
    return GenerationError("content", str(e), DRAFT_ERROR_SUGGESTION)


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
                  raw_text: str, problems: list[str] | None, hits: list | None) -> str:
    lines = [f"学科：{subject}；学段：{GRADE_ZH.get(grade, grade)}（讲解深度按这个学段控制）；知识点：{topic}",
             f"目标总时长：{target_seconds:g} 秒（口播总量按这个时长控制）。"]
    # 与 A3/A4 同一份学段词表：K0 起草阶段就不把大学内容写进 H2 条目。
    scope = review.scope_prompt(grade, subject)
    if scope:
        lines.append(scope)
    if hits:
        lines.append("【教材检索命中：refs 只能逐字照抄下面清单里的 source 与 locator；"
                     "每条引用都要在口播里真的讲到对应内容；不要写清单之外的出处】")
        for h in hits:
            lines.append(f"- {h.source} 第 {h.page} 页：{h.excerpt}")
        # 系统提示词示例里写的是 "refs": []，模型会照抄示例；这里给出可直接复制的对象，并明说不许空
        pairs = list(dict.fromkeys((h.source, f"第 {h.page} 页") for h in hits))
        lines.append("refs 不许是空数组：从下面挑出口播真正讲到的 1 条或多条，逐字复制整个对象：")
        lines.append(json.dumps([{"source": s, "locator": loc} for s, loc in pairs], ensure_ascii=False))
    else:
        lines.append("refs 必须是空数组：这条内容没检索到可核对的教材出处，不许编出处。")
    if raw_text:
        lines.append(f"用户的补充要求：{raw_text}")
    if problems:
        lines.append("【上一版的问题，逐条改正后重新输出完整 JSON】")
        lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)


def _check_shape(entry: dict, topic: str, allowed: list[dict] | None = None,
                 target_seconds: float = 0.0) -> list[str]:
    errs: list[str] = []
    if not isinstance(entry, dict):
        return ["输出不是 JSON 对象"]
    if _norm(entry.get("topic")) != _norm(topic):
        errs.append(f"topic 必须逐字等于用户写的「{topic}」")
    if allowed is None:
        if entry.get("refs"):
            errs.append("refs 必须是空数组（没有教材检索命中，不许写出处）")
    else:
        refs = entry.get("refs")
        if not isinstance(refs, list) or not refs:
            errs.append("refs 不能为空：教材检索已命中，成片出处必须挂到命中的来源上")
        else:
            pairs = {(str(a.get("source")), str(a.get("locator"))) for a in allowed}
            bad = [r for r in refs if not isinstance(r, dict)
                   or (str(r.get("source") or ""), str(r.get("locator") or "")) not in pairs]
            if bad:
                errs.append(f"refs 里有命中清单之外的出处（{bad[:2]}）——只能逐字照抄清单里的 source 与 locator")
    for k in ("must_say", "forbidden"):
        v = entry.get(k)
        if not isinstance(v, list) or not v:
            errs.append(f"{k} 必须是非空字符串数组")
    for i, item in enumerate(entry.get("must_say") if isinstance(entry.get("must_say"), list) else [], 1):
        if not isinstance(item, str) or not _norm(item):
            errs.append(f"must_say 第 {i} 条必须是非空字符串")
        elif len(_norm(item)) > MUST_SAY_MAX_CHARS:
            errs.append(f"must_say 第 {i} 条 {len(_norm(item))} 字超过 {MUST_SAY_MAX_CHARS} 字上限："
                        f"must_say 必须是逐字摘自某一镜 narration 的连续片段——缩到 {MUST_SAY_MAX_CHARS}"
                        " 字以内，直接从口播原文里剪，不要重写成整句断言")
    prior = entry.get("prior")
    if not isinstance(prior, list) or len(prior) > 3 or any(
            not isinstance(p, str) or not p.strip() or len(p) > MAX_PRIOR_CHARS for p in prior):
        errs.append(f"prior 必须是最多 3 条的字符串数组，每条是不超过 {MAX_PRIOR_CHARS} 字的名词短语"
                    "（如「磁通量的含义」），不要写成整句")
    seq = entry.get("sequence")
    cap = max_shots_for(target_seconds)   # 81-A1b：上限随目标时长伸缩，短片（≤600s）仍是 10
    if not isinstance(seq, list) or not (MIN_SHOTS <= len(seq) <= cap):
        errs.append(f"sequence 必须是 {MIN_SHOTS}~{cap} 个镜头")
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
                errs.append(f"第 {i} 镜的版式 kind={kind!r} 不在渲染层支持的 {len(VISUAL_KINDS)} 种里")
            elif not isinstance(v.get("props"), dict):
                errs.append(f"第 {i} 镜 {kind} 的 props 必须是对象")
    return errs


def _fold_flat_props(entry: dict) -> None:
    """模型常把 props 拍平成 {"kind": "summary", "points": [...]}；无歧义，就地收进 props。"""
    for b in entry.get("sequence") or []:
        for v in (b.get("visuals") if isinstance(b, dict) else None) or []:
            if isinstance(v, dict) and "props" not in v and len(v) > 1:
                v["props"] = {k: v.pop(k) for k in [k for k in v if k != "kind"]}


def _must_say_miss_msg(entry: dict, phrase: str) -> str:
    """报错要给模型可照做的动作：指出最接近的镜头，并把那镜口播前 60 字摆出来让它剪。"""
    target = _norm(phrase)
    best_i, best_len, best_narr = 0, -1, ""
    for i, b in enumerate(entry.get("sequence") or [], 1):
        narr = str(b.get("narration") or "")
        m = difflib.SequenceMatcher(None, target, _norm(narr)).find_longest_match()
        if m.size > best_len:
            best_i, best_len, best_narr = i, m.size, narr
    hint = (f"最接近的是第 {best_i} 镜口播：「{best_narr[:60]}」——从里面剪一段不超过 "
            f"{MUST_SAY_MAX_CHARS} 字的连续片段换上，或把这条原句逐字写进该镜口播" if best_i else "")
    return (f"must_say 里的「{phrase}」在任何一镜的口播/屏上文字里都找不到——"
            f"要么写进口播，要么从 must_say 删掉。{hint}")


def _check_content(entry: dict, target_seconds: float) -> list[str]:
    """闸门会查的三件事，先在起草层自查一轮，省掉一次注定失败的出片。"""
    errs: list[str] = []
    texts = _norm(_texts(entry))
    for phrase in entry.get("must_say") or []:
        if _norm(phrase) not in texts:
            errs.append(_must_say_miss_msg(entry, phrase))
    for word in entry.get("forbidden") or []:
        if _norm(word) and _norm(word) in texts:
            errs.append(
                f"forbidden 里的「{word}」出现在了成片文字里——一句话不能既禁止又照讲。"
                "若它确实是错/不该讲的说法，就把它从口播和屏上文字里删掉、改写；"
                "若它其实是你本来要讲、且自认为对的说法，就把它从 forbidden 里删掉。"
                "不许两头都占：改完后 forbidden 里剩下的每一条都必须整片不出现。")
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
    # 预算天花板与 review.PACING 硬闸同源：闸门只在语速需提到 ACCEPTABLE_RATE 档以上才拦
    # （≈NATURAL_CPS / RATE_FACTOR**ACCEPTABLE_RATE 字/秒）。自查若还按自然语速算，会把闸门
    # 明明放行的稿子误打回（如「口播 526 字 / 允许约 477 字」），让起草无谓重试。共用同一把尺子。
    ceiling = NATURAL_CPS / RATE_FACTOR ** ACCEPTABLE_RATE
    budget = max(1.0, target_seconds - naming - len(seq) * 1.15) * ceiling
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


_MS_MISS_PREFIX = "must_say 里的「"


def _all_must_say_misses(problems: list[str]) -> bool:
    """问题清单里只剩 must_say 逐字未命中这一类——它不该再烧一次整篇重生成（84-T3）。"""
    return bool(problems) and all(p.startswith(_MS_MISS_PREFIX) for p in problems)


def _fallback_must_say(entry: dict) -> str | None:
    """must_say 被剪空时兜底补一条：末镜 emphasis（为空退 title）的 ≤25 字连续片段，
    保证 _check_shape 的「非空数组」不变量不被剪破。"""
    seq = entry.get("sequence") or []
    if not seq:
        return None
    last = seq[-1]
    for key in ("emphasis", "title"):
        text = str(last.get(key) or "").strip()
        if text:
            return text[:MUST_SAY_MAX_CHARS]   # 截断仍是原文里的连续片段，逐字判据成立
    return None


def _keep_reconciled(subject: str, topic: str, notes: list[str]) -> None:
    """must_say 被 reconcile 改写/剪掉的留痕：只含文本，事后能审计哪条限定没站住。"""
    try:
        d = knowledge.AUTO_DIR / "_reconciled"
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (d / f"{stamp}-{_id(subject, '', topic)[-10:]}.txt").write_text(
            "\n".join(notes) + "\n", encoding="utf-8")
    except OSError:
        pass


def _reconcile_must_say(entry: dict, subject: str, topic: str) -> dict:
    """must_say 逐字未命中的收口通道（84-T3）：一次小型网关调用，把每条未命中换成口播里
    真实存在的连续片段（≤25 字）；换不了就剪掉（留痕），永不因 must_say 单独打死整段生成。"""
    missed = [p for p in entry.get("must_say") or []
              if isinstance(p, str) and _norm(p) not in _norm(_texts(entry))]
    if not missed:
        return entry
    narrations = [{"shot": i, "narration": str(b.get("narration") or "")}
                  for i, b in enumerate(entry.get("sequence") or [], 1)]
    user = json.dumps({"missed_must_say": missed, "narrations": narrations}, ensure_ascii=False)
    quotes: dict[str, str | None] = {}
    notes: list[str] = []
    try:
        raw = llm_client.chat("K0", llm_prompts.K0_RECONCILE_SYSTEM, user,
                              max_tokens=1200, json_mode=True)
        got = llm_client.extract_json(raw)
        items = got.get("quotes") if isinstance(got, dict) else (got if isinstance(got, list) else None)
        for it in items or []:
            if isinstance(it, dict) and isinstance(it.get("must_say"), str):
                q = it.get("quote")
                quotes[it["must_say"]] = q if isinstance(q, str) else None
    except llm_client.LLMError:
        notes.append("reconcile 网关调用失败，未命中条目按剪掉处理")

    flat_texts = _norm(_texts(entry))
    kept: list[str] = []
    for item in entry.get("must_say") or []:
        if item not in missed:
            kept.append(item)
            continue
        quote = quotes.get(item)
        # 模型给的 quote 必须本地复验：逐字在口播里、且不超长——伪造的一律剪掉而不是接受
        if quote and _norm(quote) in flat_texts and len(_norm(quote)) <= MUST_SAY_MAX_CHARS:
            kept.append(quote)
            notes.append(f"改写：{item}\n  → {quote}")
        else:
            notes.append(f"剪掉（口播里找不到可逐字保留的连续片段）：{item}")
    entry["must_say"] = kept
    if not kept:
        fallback = _fallback_must_say(entry)
        if fallback:
            entry["must_say"] = [fallback]
            notes.append(f"兜底补一条（末镜 emphasis/title 的连续片段）：{fallback}")
    if notes:
        _keep_reconciled(subject, topic, notes)
    return entry


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
    hits = [h for h in corpus.search(subject, f"{topic} {raw_text}".strip(), max_hits=5)
            if corpus.page_has(h, [topic])]
    allowed, seen = [], set()
    for h in hits:
        key = (h.source, h.page)
        if key not in seen:
            seen.add(key)
            allowed.append({"source": h.source, "locator": f"第 {h.page} 页"})
    entry: dict = {}
    problems: list[str] = []
    raw = ""
    for attempt in range(MAX_ATTEMPTS):
        raw = llm_client.chat("K0", llm_prompts.K0_SYSTEM,
                              _user_message(subject, grade, topic, target_seconds, raw_text,
                                            problems or None, hits or None),
                              max_tokens=8000, json_mode=True)
        try:
            entry = llm_client.extract_json(raw)
        except llm_client.LLMError:
            entry = None
        if not isinstance(entry, dict):
            problems = ["输出不是一个合法的 JSON 对象，请只输出完整 JSON"]
            continue
        entry["topic"] = topic          # 归一：topic 永远以用户原文为准
        _fold_flat_props(entry)
        if not allowed:
            entry["refs"] = []          # 铁律：没有语料命中就没有出处
        problems = _check_shape(entry, topic, allowed or None, target_seconds) + _check_content(entry, target_seconds)
        if not problems:
            break
        if _all_must_say_misses(problems):
            # 快速通道（84-T3）：只是限定句没逐字落进文本，不再整篇重生成，进 reconcile 就地收口；
            # 收口后复验仍不过的（只可能是其他类问题）才回到整篇重试。
            entry = _reconcile_must_say(entry, subject, topic)
            problems = (_check_shape(entry, topic, allowed or None, target_seconds)
                        + _check_content(entry, target_seconds))
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
