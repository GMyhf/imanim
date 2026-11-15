"""S2.2 独立评审的模型辅助判分：按 S1.1 量表给 G1/G3 与 S、U 两维打分。

约束：A、C 两维是客观产物指标，不在这里打；U 类主观，只作参考，仍需人工复核。
证据校验：每个小于 5 的分数必须带一条能在分镜文本里原样找到的引文，找不到的扣分作废（记为 5）——
这是对「评审编造引文」的确定性防线。模型不可用时返回 available=False，不冒充分数。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import llm_client, llm_prompts
from .review import _texts

S_ITEMS = ("S1", "S2", "S3", "S4", "S5")
U_ITEMS = ("U1", "U2", "U3", "U4", "U5")


def _flat(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _storyboard_text(plan: dict) -> str:
    lines = []
    for s in plan.get("shots", []):
        screen = _texts([{"kind": v.get("kind"), "props": v.get("props")} for v in s.get("visuals", [])])
        lines.append(f"镜{s.get('index')}《{s.get('title')}》{s.get('seconds')}s\n  旁白：{s.get('narration')}\n"
                     f"  屏上：{' | '.join(screen)}\n  出处：{'；'.join(s.get('kp_refs', []))}")
    return "\n".join(lines)


def _score(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5 else None


def score(plan: dict, kp: dict, contact_png: Path | None = None) -> dict:
    model = llm_client.model_for("S22")
    story = _storyboard_text(plan)
    user = (f"【知识点条目（唯一可信的事实来源）】\n{json.dumps(kp, ensure_ascii=False, indent=1)}\n\n"
            f"【分镜：旁白与屏上文字】\n{story}")
    imgs = [Path(contact_png)] if contact_png and Path(contact_png).exists() else None
    if imgs:
        user += "\n\n附图为镜头接触表（每镜头/尾两帧）。"
    try:
        got = llm_client.extract_json(llm_client.chat("S22", llm_prompts.S22_SYSTEM, user, imgs, max_tokens=6000))
    except llm_client.LLMError as e:
        return {"available": False, "reason": str(e), "model": model}
    if not isinstance(got, dict):
        return {"available": False, "reason": "模型输出不是对象", "model": model}

    corpus = _flat(story)
    cited = {str(e.get("item")) for e in (got.get("evidence") or [])
             if isinstance(e, dict) and _flat(str(e.get("quote") or "")) and _flat(str(e.get("quote"))) in corpus}
    dropped, scores = [], {}
    for dim, items in (("S", S_ITEMS), ("U", U_ITEMS)):
        raw = got.get(dim) if isinstance(got.get(dim), dict) else {}
        for it in items:
            sc = _score(raw.get(it))
            if sc is None:
                continue
            if sc < 5 and it not in cited:
                dropped.append(it)
                sc = 5
            scores[it] = sc
    mean = lambda items: round(sum(scores[i] for i in items if i in scores) / max(1, sum(i in scores for i in items)), 2)
    gates = got.get("gates") if isinstance(got.get("gates"), dict) else {}
    return {"available": True, "model": model, "gates": gates, "scores": scores,
            "S": mean(S_ITEMS), "U": mean(U_ITEMS), "dropped_without_evidence": dropped,
            "evidence": got.get("evidence") or [], "strengths": got.get("strengths") or [],
            "fixes": got.get("fixes") or [], "note": "U 类为模型参考分，须人工复核；A、C 两维不在此打分"}
