"""配音稿（朗读稿）生成：把混着公式/化学式的口播改写成朗读员照念的中文。

audio/tts.py 里的正则（speakable）是上下文盲的：分不清「2-碘辛烷」的定位连字符（不念减）
和「a-b」的减号，也认不得 CH3Cl / C–Br / σ* / SN2 这类化学记号。所以朗读稿交给网关模型
按整镜上下文生成；正则只当离线兜底（见 tts.speakable）。

开关：QX_LLM_VOICEOVER=1（或 QX_LLM_ALL=1）才启用，与 A1/A3/K0 同一套约定。默认关——
确定性管线仍是默认与兜底。
"""

from __future__ import annotations

from pipeline import ir, llm_client, llm_prompts


def rewrite(narrations: list[str], brief: ir.Brief) -> list[str] | None:
    """把整片口播一次性改写成朗读稿；网关关闭/失败/条数对不上时返回 None，由调用方回退正则。"""
    if not llm_client.enabled("VOICEOVER"):
        return None
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(narrations))
    user = (f"学科：{brief.subject}；学段：{brief.grade}\n"
            f"共 {len(narrations)} 段，逐段改写（顺序、条数不能变）：\n{numbered}")
    try:
        raw = llm_client.chat("VOICEOVER", llm_prompts.VOICEOVER_SYSTEM, user,
                              max_tokens=8000, json_mode=True)
    except llm_client.LLMError:
        return None
    try:
        obj = llm_client.extract_json(raw)
    except llm_client.LLMError:
        return None
    lines = obj.get("lines") if isinstance(obj, dict) else (obj if isinstance(obj, list) else None)
    if not isinstance(lines, list) or len(lines) != len(narrations):
        return None
    if not all(isinstance(x, str) and x.strip() for x in lines):
        return None
    return [x.strip() for x in lines]


def apply(plan: ir.Plan) -> dict:
    """为每个镜头生成配音稿并写回 shot.voiceover；失败/关闭时清空 voiceover（TTS 回退正则）。

    返回一段可塞进 sidecar 的记账：used / model / note。
    """
    narrations = [s.narration for s in plan.shots]
    lines = rewrite(narrations, plan.brief)
    if lines:
        for s, v in zip(plan.shots, lines):
            s.voiceover = v
        return {"used": True, "model": llm_client.model_for("VOICEOVER"),
                "shots": len(plan.shots)}
    for s in plan.shots:
        s.voiceover = ""
    return {"used": False, "note": "配音稿改写跳过（网关关闭或失败），TTS 回退正则朗读"}
