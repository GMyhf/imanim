"""A3 分镜：Knowledge + Brief → Plan（分镜 IR）。

MVP 用确定性模板编排，保证可复现（P2）；LLM 版将来作为另一实现插进来，IR 不变。
"""

from __future__ import annotations

from copy import deepcopy
from math import ceil

from .ir import (BUDGET_REF_KIND, MIN_SHOT_SECONDS, NAME_MAX_SHARE, NATURAL_CPS, SHOT_HEAD,
                 SHOT_TAIL, Brief, Plan, Shot, Visual, naming_narration, naming_shot_seconds, num)
from .review import _text as _pace_text  # 字数口径与 A4 PACING 同一把尺子：分镜与闸门不得各算各的

# 秒数一律换算成整数「厘秒」再分配：浮点累加与遍历顺序都不许影响结果（P2 可复现）。
_CS = 100
_HEAD_TAIL_CS = int(round((SHOT_HEAD + SHOT_TAIL) * _CS))
_MIN_WINDOW_CS = int(round(max(0.0, MIN_SHOT_SECONDS - SHOT_HEAD - SHOT_TAIL) * _CS))

# 预算账本随 plan.json 落盘（refs 是 Plan 里唯一可自由结构化的字段），前端与 A4 都能读到。
# 字段名常量住在 ir.BUDGET_REF_KIND —— review 要读它，而 review 不能 import storyboard（循环导入）。


def _all_refs(kp: dict) -> list[str]:
    return [f"{r['source']} {r['locator']}" for r in kp["refs"]]


def _chars(narration) -> int:
    return len(_pace_text(narration))


def _need_cs(chars: int) -> int:
    """这一镜口播在自然语速下要占的可说窗（厘秒）；镜头秒数还要另加头尾留白。"""
    return int(round(chars / NATURAL_CPS * _CS))


def _apportion(total: int, quotas: list[int]) -> list[int]:
    """把 total 厘秒按 quotas 占比切成整数份，和恰好等于 total（最大余额法，同余额按镜头序号）。"""
    n = len(quotas)
    if n == 0:
        return []
    sum_q = sum(quotas)
    if sum_q <= 0:
        base, extra = divmod(total, n)
        return [base + (1 if i < extra else 0) for i in range(n)]
    give = [total * q // sum_q for q in quotas]
    rem = [total * q % sum_q for q in quotas]
    for i in sorted(range(n), key=lambda i: (-rem[i], i))[:total - sum(give)]:
        give[i] += 1
    return give


def _allocate(budget_cs: int, need_cs: list[int], weight_cs: list[int]) -> list[int]:
    """分可说窗（镜头秒数扣掉头尾留白）：够就按自然需要，不够就按字数等比压缩。

    等比压缩 = 每镜同一语速，于是「99 字挤 9.3s、37 字空等 16.3s」不再可能同时出现（审计 §1.3）。
    每镜的可说窗不低于 MIN_SHOT_SECONDS 的下限；下限之外的「念不完」是全片级的，
    任何分配都消不掉，交给 OVERLOAD/PACING 说，而不是靠把某一镜压过头来掩盖。
    """
    n = len(need_cs)
    if n == 0:
        return []
    floors = [_MIN_WINDOW_CS] * n
    if sum(floors) > budget_cs:  # 目标短到连镜头下限都放不下：保住下限，多出的秒数由 TARGET 闸门报
        return floors
    wants = [max(a, b) for a, b in zip(need_cs, floors)]
    if sum(wants) <= budget_cs:  # 有富余：自然需要照给，余量按模板 seconds 的相对权重分
        extra = _apportion(budget_cs - sum(wants),
                           weight_cs if sum(weight_cs) > 0 else need_cs)
        return [w + e for w, e in zip(wants, extra)]
    locked = [False] * n
    while True:
        free = [i for i in range(n) if not locked[i]]
        if not free:
            break
        rest = budget_cs - sum(floors[i] for i in range(n) if locked[i])
        share = _apportion(rest, [need_cs[i] for i in free])
        under = [k for k, i in enumerate(free) if share[k] < floors[i]]
        if not under:
            out = [0] * n
            for k, i in enumerate(free):
                out[i] = share[k]
            for i in range(n):
                if locked[i]:
                    out[i] = floors[i]
            left = budget_cs - sum(out)  # 全被下限锁死时可能还剩几厘秒，按字数权重补上，保证总额精确
            if left > 0:
                for i, e in zip(range(n), _apportion(left, need_cs)):
                    out[i] += e
            return out
        for k in under:
            locked[free[k]] = True
    return floors


def budget_of(plan) -> dict | None:
    """读回 A3 的预算账本（plan.json 里的 refs 标记）；没有就返回 None。"""
    refs = getattr(plan, "refs", None) or (plan.get("refs") if isinstance(plan, dict) else None)
    for r in refs or []:
        if isinstance(r, dict) and r.get("kind") == BUDGET_REF_KIND:
            return r
    return None


def build(brief: Brief, kp: dict) -> Plan:
    blocks = list(kp["sequence"])
    refs = _all_refs(kp)

    prior = None
    prior_chars = 0
    if brief.prior_knowledge and kp.get("prior"):
        narr = naming_narration(kp["prior"])
        # 时长跟着标签文本走：先前写死 8s，四条长标签就是 9 字/秒，闸门判它说不完。
        # 尺子取自 ir.naming_shot_seconds——prereq.py 对同一段文本必须算出同一个秒数。
        need = naming_shot_seconds(narr)
        prior = {
            "title": "先修：需要什么基础",
            "seconds": round(min(need, NAME_MAX_SHARE * num(brief.target_seconds)), 2),
            "narration": narr,
            "emphasis": "先修知识",
            "visuals": [{"kind": "callout", "props": {"text": "先修：" + " · ".join(kp["prior"]), "tone": "key"}}],
        }
        prior_chars = _chars(narr)
        blocks = [prior] + blocks

    # 点名段是固定开销，不参与重分：它先按自己的文本拿够时间，正片分剩下的预算。
    fixed = prior["seconds"] if prior else 0.0
    target = num(brief.target_seconds)
    body = [b for b in blocks if b is not prior]
    chars = [_chars(b.get("narration")) for b in body]
    needs = [_need_cs(c) for c in chars]
    weights = [max(0, int(round(num(b.get("seconds")) * _CS))) for b in body]
    budget = int(round((target - fixed) * _CS)) - len(body) * _HEAD_TAIL_CS
    secs = [round((_HEAD_TAIL_CS + w) / _CS, 2) for w in _allocate(budget, needs, weights)]

    # 「按自然语速讲完整片」需要多少秒：装不下就留结构化标记，不许把压缩默默吃掉。
    natural = fixed + sum(max(MIN_SHOT_SECONDS, (_HEAD_TAIL_CS + nd) / _CS) for nd in needs)
    marker = {
        "kind": BUDGET_REF_KIND,
        "source": "A3 分镜预算",
        "locator": f"target={int(target)}s",
        "narration_chars": sum(chars) + prior_chars,
        "natural_seconds": round(natural, 2),
        "budgeted_seconds": round(fixed + sum(secs), 2),
        "fits_natural": natural <= target + 1e-9,
        "min_seconds_for_natural": int(ceil(natural - 1e-9)),
    }

    alloc = iter(secs)
    shots = []
    for i, b in enumerate(blocks):
        secs_i = b["seconds"] if b is prior else next(alloc)
        shots.append(
            Shot(
                index=i,
                title=b["title"],
                seconds=secs_i,
                narration=b["narration"],
                visuals=[Visual(v["kind"], deepcopy(v.get("props", {}))) for v in b["visuals"]],
                kp_refs=deepcopy(b.get("kp_refs", refs)),
                emphasis=b.get("emphasis", ""),
            )
        )
    return Plan(brief=brief, knowledge_id=kp["id"], shots=shots,
                refs=deepcopy(kp["refs"]) + [marker])
