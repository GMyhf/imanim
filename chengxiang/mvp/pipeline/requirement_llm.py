"""A1 需求分析的 LLM 实现：把自然语言 topic 归一到库内知识点。

边界（Spec_Workflow A1）：结果必须能在库内命中才算数；不改学段与时长，只补全和校验。
精确命中时不调用模型（确定性优先，也省钱）；模型出错或没命中一律退回原 topic，
让 A2 按原样报"未入库"，不由 LLM 兜底编造。
"""

from __future__ import annotations

from . import knowledge, llm_client, llm_prompts


def _candidates(subject: str) -> list[dict]:
    return [{"id": e.get("id"), "topic": e.get("topic"), "grade": e.get("grade"),
             "aliases": list(e.get("aliases", []))} for e in knowledge._entries(subject)]


def normalize(subject: str, grade: str, topic: str, target_seconds: int) -> dict:
    """返回 {"topic", "source", "reason", "duration_hint"}。source ∈ exact / llm / unchanged / error。"""
    try:
        knowledge.load(subject, topic, grade)
        return {"topic": topic, "source": "exact", "reason": "", "duration_hint": ""}
    except knowledge.KnowledgeNotFound:
        pass

    cands = _candidates(subject)
    if not cands:
        return {"topic": topic, "source": "unchanged", "reason": f"{subject} 下没有任何入库条目", "duration_hint": ""}

    import json
    user = (f"学科：{subject}\n学段：{grade}\n目标时长：{target_seconds} 秒\n老师填写的知识点：{topic}\n\n"
            f"【候选清单】\n{json.dumps(cands, ensure_ascii=False, indent=1)}")
    try:
        got = llm_client.extract_json(llm_client.chat("A1", llm_prompts.A1_SYSTEM, user, max_tokens=600, json_mode=True))
    except llm_client.LLMError as e:
        return {"topic": topic, "source": "error", "reason": str(e), "duration_hint": ""}
    if not isinstance(got, dict):
        return {"topic": topic, "source": "error", "reason": "模型输出不是对象", "duration_hint": ""}

    hint = str(got.get("duration_hint") or "")
    picked = str(got.get("topic_id") or "")
    if got.get("matched") is True and picked:
        try:  # 库内命中才算数：id 必须真的存在，且学段与老师要的一致
            knowledge.load(subject, picked, grade)
            return {"topic": picked, "source": "llm", "reason": str(got.get("reason") or ""), "duration_hint": hint}
        except knowledge.KnowledgeNotFound:
            return {"topic": topic, "source": "unchanged",
                    "reason": "模型给出的 id 在库内（该学段）不存在，已丢弃", "duration_hint": hint}
    return {"topic": topic, "source": "unchanged", "reason": str(got.get("reason") or "模型判定库内无对应条目"),
            "duration_hint": hint}
