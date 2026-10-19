"""配音稿（朗读稿）生成：把混着公式/化学式的口播改写成朗读员照念的中文。

audio/tts.py 里的正则（speakable）是上下文盲的：分不清「2-碘辛烷」的定位连字符（不念减）
和「a-b」的减号，也认不得 CH3Cl / C–Br / σ* / SN2 这类化学记号。所以朗读稿交给网关模型
按整镜上下文生成；网关不可用时走本模块的小读法词典（fallback_readable）+ tts.speakable
正则的离线兜底，学科特例只在提示词里讲原则、不进词典。

开关：QX_LLM_VOICEOVER=1（或 QX_LLM_ALL=1）才启用，与 A1/A3/K0 同一套约定。默认关——
确定性管线仍是默认与兜底。
"""

from __future__ import annotations

import re

from pipeline import ir, llm_client, llm_prompts

# ── 离线兜底读法词典（非主路径）──────────────────────────────────────────
# 主路径是网关模型按整片上下文改写（见 llm_prompts.VOICEOVER_SYSTEM）；学科特例一律留给
# 上下文提示词，不往这里堆。网关关闭/失败时只做下面少量高频、跨学科通用的替换（<20 条），
# 配合 audio/tts.py 的正则（speakable）兜底：π 等希腊字母→中文音名（防读成「皮」）、
# 「2s 轨道」→「二 s 轨道」（防读成「2 秒」）、「σ*」→「西格马星」。
_FALLBACK_LETTERS = {
    "π": "派", "θ": "西塔", "μ": "谬", "ρ": "柔", "σ": "西格马", "τ": "陶",
    "α": "阿尔法", "β": "贝塔", "γ": "伽马", "δ": "德尔塔", "Δ": "德尔塔",
    "λ": "兰布达", "ω": "欧米伽", "φ": "斐",
}
_CN_DIGITS = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
              "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}

# 先跑模式（可能吃掉 σ*、数字+轨道字母），再跑单字母词典，避免 σ* 被拆成「西格马*」。
_FALLBACK_PATTERNS = [
    # σ*（反键轨道等）：星号必须并进来，否则留下「西格马*」
    (re.compile(r"σ\s*\*"), "西格马星"),
    # 「2s 轨道 / 3d 能级」：数字读数字、字母逐读加空格，防 TTS 把「2s」并读成「2 秒」；
    # 只在后面紧跟轨道/亚层/能级/电子这类词时才转，真秒数（如「2 s 后」）不动。
    (re.compile(r"(?<![0-9A-Za-z])(\d+)\s*([spdfSPDF])(?=\s*(?:轨道|亚层|能级|电子))"),
     lambda m: "".join(_CN_DIGITS[c] for c in m.group(1)) + " " + m.group(2).lower()),
]


def fallback_readable(text: str) -> str:
    """网关不可用时的离线兜底读法改写；tts.speakable 的公式正则随后仍会作用于结果。"""
    for pat, rep in _FALLBACK_PATTERNS:
        text = pat.sub(rep, text)
    for k, v in _FALLBACK_LETTERS.items():
        text = text.replace(k, v)
    return text


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
    """为每个镜头生成配音稿并写回 shot.voiceover。

    网关成功：逐镜写入模型改写稿。网关关闭/失败：用离线兜底词典（fallback_readable）
    从**当前** narration 重新生成朗读稿——不用上一版的陈旧稿，也不留裸公式给 TTS 硬念。

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
        s.voiceover = fallback_readable(s.narration)
    return {"used": False, "note": "配音稿改写跳过（网关关闭或失败），朗读稿走离线读法词典+tts 正则兜底"}
