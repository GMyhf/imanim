"""A3 分镜的 LLM 实现：模型只写「讲什么、什么顺序、各占多少权重」，真实秒数、先修点名镜、
预算账本仍由 storyboard.build 的确定性代码算（把模型的镜头当作替换后的 kp.sequence 喂进去）。

闸门（review.check）不改：模型产物必须原样过 A4，被打回就把清单回灌，最多 2 次；
仍不过或模型不可用就退回确定性分镜，并在 info 里如实记下原因（不静默吞错）。
"""

from __future__ import annotations

import json
from copy import deepcopy

from . import llm_client, llm_prompts, review, storyboard
from .ir import VISUAL_KINDS, Brief, Plan

MAX_FEEDBACK_RETRIES = 2
MIN_SHOTS, MAX_SHOTS = 4, 10


def _schema_errors(data) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
        return ["顶层必须是 {\"shots\": [...]}"]
    shots = data["shots"]
    errs = []
    if not MIN_SHOTS <= len(shots) <= MAX_SHOTS:
        errs.append(f"镜头数必须在 {MIN_SHOTS}~{MAX_SHOTS} 之间，收到 {len(shots)}")
    for i, s in enumerate(shots):
        if not isinstance(s, dict):
            errs.append(f"shots[{i}] 不是对象")
            continue
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            errs.append(f"shots[{i}] 缺 title")
        if not isinstance(s.get("narration"), str) or not s["narration"].strip():
            errs.append(f"shots[{i}] narration 必须是非空字符串")
        if not isinstance(s.get("seconds"), (int, float)) or isinstance(s.get("seconds"), bool) or s["seconds"] <= 0:
            errs.append(f"shots[{i}] seconds 必须是正数")
        vs = s.get("visuals")
        if not isinstance(vs, list) or not vs:
            errs.append(f"shots[{i}] visuals 必须是非空数组")
            continue
        for j, v in enumerate(vs):
            if not isinstance(v, dict) or v.get("kind") not in VISUAL_KINDS or not isinstance(v.get("props", {}), dict):
                errs.append(f"shots[{i}].visuals[{j}] 的 kind 必须是 {list(VISUAL_KINDS)} 之一且 props 是对象")
    return errs


def _blocks(data: dict) -> list[dict]:
    return [{"title": s["title"].strip(), "seconds": float(s["seconds"]), "narration": s["narration"].strip(),
             "emphasis": str(s.get("emphasis") or ""),
             "visuals": [{"kind": v["kind"], "props": deepcopy(v.get("props", {}))} for v in s["visuals"]]}
            for s in data["shots"]]


def _user_message(brief: Brief, kp: dict, feedback: list[str] | None, prev: str | None) -> str:
    chars = int(brief.target_seconds * 3.9)
    msg = (f"学科：{brief.subject}  学段：{brief.grade}  风格：{brief.style}\n"
           f"目标时长：{brief.target_seconds} 秒（口播总字数建议不超过约 {chars} 字，含所有镜头）\n"
           f"先修点名镜：{'由系统在片头另加，你不要写' if brief.prior_knowledge and kp.get('prior') else '本片不要'}\n\n"
           f"【知识点条目 JSON（唯一事实来源）】\n{json.dumps(kp, ensure_ascii=False, indent=1)}")
    if feedback:
        msg += ("\n\n【上一版输出】\n" + (prev or "") +
                "\n\n【上一版被静态闸门/校验打回的清单，请逐条修正后重新输出完整 JSON】\n" + "\n".join(feedback))
    return msg


def build(brief: Brief, kp: dict) -> tuple[Plan, dict]:
    """返回 (Plan, info)。info.source ∈ llm / fallback；fallback 时 info.reason 写明原因。"""
    info: dict = {"source": "fallback", "model": llm_client.model_for("A3"), "attempts": 0, "reason": "", "history": []}
    feedback: list[str] | None = None
    prev: str | None = None
    for attempt in range(MAX_FEEDBACK_RETRIES + 1):
        info["attempts"] = attempt + 1
        try:
            raw = llm_client.chat("A3", llm_prompts.A3_SYSTEM, _user_message(brief, kp, feedback, prev),
                                  max_tokens=12000, json_mode=True)
            data = llm_client.extract_json(raw)
        except llm_client.LLMError as e:
            info["reason"] = str(e)
            break
        prev = raw.strip()
        errs = _schema_errors(data)
        if errs:
            feedback = [f"- [SCHEMA] {m}" for m in errs]
            info["history"].append(feedback)
            continue
        kp2 = deepcopy(kp)
        kp2["sequence"] = _blocks(data)
        plan = storyboard.build(brief, kp2)
        hard = review.blocking(review.check(plan, kp))
        if not hard:
            info["source"] = "llm"
            return plan, info
        feedback = [f"- shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard]
        info["history"].append(feedback)
    if not info["reason"]:
        info["reason"] = "回灌 %d 次后仍未过静态闸门：%s" % (MAX_FEEDBACK_RETRIES, "；".join((feedback or [])[:3]))
    return storyboard.build(brief, kp), info
