"""A3 分镜：Knowledge + Brief → Plan（分镜 IR）。

MVP 用确定性模板编排，保证可复现（P2）；LLM 版将来作为另一实现插进来，IR 不变。
"""

from __future__ import annotations

import re
from copy import deepcopy
from math import ceil

from .ir import (BUDGET_REF_KIND, FAST_CPS, MIN_SHOT_SECONDS, NAME_MAX_SHARE, NATURAL_CPS, SHOT_HEAD,
                 SHOT_TAIL, Brief, Plan, Shot, Visual, fit_naming_labels, naming_narration,
                 naming_shot_seconds, num)
from .review import (CALLOUT_FS, CALLOUT_PAD, MAX_SHOT_SHARE, SAFE_WIDTH, _est_width,
                     _text as _pace_text)  # 字数与宽度口径与 A4 同一把尺子：分镜与闸门不得各算各的

# 秒数一律换算成整数「厘秒」再分配：浮点累加与遍历顺序都不许影响结果（P2 可复现）。
_CS = 100
_HEAD_TAIL_CS = int(round((SHOT_HEAD + SHOT_TAIL) * _CS))
_MIN_WINDOW_CS = int(round(max(0.0, MIN_SHOT_SECONDS - SHOT_HEAD - SHOT_TAIL) * _CS))
_SAFE_CPS = FAST_CPS * 0.97
_STRETCH = 1.09  # 留 1% 给 A6 实测抖动，不顶到 TARGET 闸门的 10% 线上

# ── 分镜密度（81-A1b，单一真源）──────────────────────────────────────────
# 镜头数上限随目标时长伸缩；kp_draft（K0 起草自查）与 storyboard_llm（A3 输出校验）都从本模块
# 取同一份口径，不再各写一份 `MIN_SHOTS, MAX_SHOTS = 4, 10`，避免双份常量漂移。推演：
#   · 旧上限 10 镜是 ≤600s 短片的口径，MIN_SHOTS=4 下限不动；
#   · 长片按 llm_prompts A3_HEAD【长片指引】「每 60~90 秒一个概念台阶」组织，取台阶下限 60s
#     作「合理单镜秒数」——1200s 长片最多 1200/60 = 20 镜，平均每镜 ≥60s，正好一镜一台阶；
#   · 60~600s 各档 ceil(t/60) ≤ 10，max(10, ·) 恒等于 10 ⇒ 短片维持旧上限，不被误放宽。
# 公式：max_shots_for(t) = max(MAX_SHOTS_BASE, ceil(t / SHOT_STEP_SECONDS))
MIN_SHOTS = 4              # 下限，旧口径不动
MAX_SHOTS_BASE = 10        # 旧上限，≤600s 时长档仍然封在这里
SHOT_STEP_SECONDS = 60.0   # 概念台阶的最短秒数（A3_HEAD【长片指引】60~90s 的下限）


def max_shots_for(target_seconds) -> int:
    """给定目标时长的镜头数上限（含端点）。脏数值走 ir.num 兜底，读不出时长就退回旧上限 10。"""
    return max(MAX_SHOTS_BASE, ceil(num(target_seconds) / SHOT_STEP_SECONDS))

# 预算账本随 plan.json 落盘（refs 是 Plan 里唯一可自由结构化的字段），前端与 A4 都能读到。
# 字段名常量住在 ir.BUDGET_REF_KIND —— review 要读它，而 review 不能 import storyboard（循环导入）。


def _all_refs(kp: dict) -> list[str]:
    return [f"{r['source']} {r['locator']}" for r in kp["refs"]]


_SENT = re.compile(r"[^。！？；\n]+[。！？；\n]*")
_CALLOUT_AVAIL = SAFE_WIDTH - 2 * CALLOUT_PAD


def _sentences(text: str) -> list[str]:
    return [m.group(0) for m in _SENT.finditer(str(text or ""))]


def _fits_callout(text: str) -> bool:
    return all(_est_width(p.strip(), CALLOUT_FS) <= _CALLOUT_AVAIL
               for p in re.split(r"\s+·\s+", str(text)) if p.strip())


def _reflow_callout(text: str) -> str:
    """一屏字太宽会被渲染层整条缩到读不见（LEGIBLE）。渲染按「 · 」逐行排，
    所以先在句读处拆行，再把拆不开的行按宽度贪心合回——只改排版，不删内容。"""
    if _fits_callout(text):
        return text
    rows: list[str] = []
    for part in [p.strip() for p in re.split(r"\s+·\s+", str(text)) if p.strip()]:
        pieces = [s for s in re.split(r"(?<=[，；。！？])", part) if s.strip()]
        cur = ""
        for s in pieces:
            if cur and _est_width((cur + s).strip(), CALLOUT_FS) > _CALLOUT_AVAIL:
                rows.append(cur.strip())
                cur = s
            else:
                cur = (cur + s).strip()
        if cur.strip():
            rows.append(cur.strip())
    rows = [re.sub(r"[，；。！？]+$", "", r) or r for r in rows]
    if not rows or len(rows) > 5 or not all(_est_width(r, CALLOUT_FS) <= _CALLOUT_AVAIL for r in rows):
        return text   # 拆到 4 行还塞不进的是真长句，留给闸门/模型处理，不做无原则截断
    return " · ".join(rows)


def _fit_callouts(blocks: list[dict]) -> None:
    for b in blocks:
        for v in b.get("visuals") or []:
            if isinstance(v, dict) and v.get("kind") == "callout" and isinstance(v.get("props"), dict):
                t = v["props"].get("text")
                if isinstance(t, str) and t:
                    v["props"]["text"] = _reflow_callout(t)


# ── 82-SD1b：推导兜底（确定性路径）────────────────────────────────────────
# 生产 plan 的 derivation.sub 使用率 = 0：A3 遇到口播里的「代入/化简得/联立」仍爱用
# formula/steps 一屏贴完。这里在分镜装配前做一次最小改写：只认口播触发词，只从本镜
# 现有 formula.expr / steps.lines / narration 里抽等式，最多 3 步；抽不到第二式就
# 老实留单步书写（Write），绝不编造物理结论。LLM 已给 derivation 的镜不动。
_DERIV_TRIGGER_RE = re.compile(r"代入|化简得|化简|联立|因此可得|解得|由[^。！？；]{0,20}?得")
_EQ_RE = re.compile(
    r"[A-Za-zΑ-ωΔ][A-Za-zΑ-ωΔ0-9_^{}²³·×÷+\-*/()\s]{0,28}"
    r"[=＝]"
    r"[A-Za-zΑ-ωΔ0-9_^{}²³·×÷+\-*/()\s]{1,40}")


def _equations(text: str) -> list[str]:
    """从一句话里抽等式串（只认「字母开头、含 =、两边非空」的连续符号段）。"""
    out: list[str] = []
    for m in _EQ_RE.finditer(str(text or "")):
        eq = re.sub(r"\s+", " ", m.group(0)).strip().replace("＝", "=")
        if "=" not in eq:
            continue
        lhs, rhs = (x.strip() for x in eq.split("=", 1))
        if lhs and rhs and eq not in out:
            out.append(eq)
    return out


def _expand_product(eq: str) -> str | None:
    """把 F=BIL 展开成 F = B·I·L（只对纯字母乘积），给「代入」一步留出可指的字母槽。"""
    if "=" not in eq:
        return None
    lhs, rhs = (x.strip() for x in eq.split("=", 1))
    compact = rhs.replace(" ", "")
    if len(compact) >= 2 and re.fullmatch(r"[A-Za-zΑ-ωΔ]{2,6}", compact):
        return f"{lhs} = " + "·".join(compact)
    return None


def _derivation_fallback(blocks: list[dict]) -> None:
    """口播在推导、版面却只有 formula/steps 时，最小化改出一版 derivation（原地替换）。"""
    for b in blocks:
        narr = str(b.get("narration") or "")
        trig = _DERIV_TRIGGER_RE.search(narr)
        if not trig:
            continue
        visuals = b.get("visuals") or []
        if any(isinstance(v, dict) and v.get("kind") == "derivation" for v in visuals):
            continue                       # A3 已经给了推导：一律不碰
        target = next((v for v in visuals if isinstance(v, dict)
                       and v.get("kind") == "formula"), None)
        if target is not None:
            # 多张 formula 同屏时改成推导会多出图例/已知条/注记，版面必超高；交给 A3 正常产出。
            if sum(1 for v in visuals if isinstance(v, dict) and v.get("kind") == "formula") > 1:
                continue
        else:
            target = next((v for v in visuals if isinstance(v, dict)
                           and v.get("kind") == "steps"), None)
        if target is None:
            continue                       # 没有可承接的公式/步骤块：不无中生有
        texts: list[str] = []
        for v in visuals:
            if not isinstance(v, dict):
                continue
            props = v.get("props") or {}
            if v.get("kind") == "formula":
                texts.append(str(props.get("expr") or ""))
            elif v.get("kind") == "steps":
                texts.extend(str(x) for x in (props.get("lines") or []))
        texts.append(narr)
        eqs: list[str] = []
        seen: set[str] = set()
        for t in texts:
            for eq in _equations(t):
                key = re.sub(r"\s+", "", eq)      # F = BIL 与 F=BIL 是同一式，别记两遍
                if key not in seen:
                    seen.add(key)
                    eqs.append(eq)
        if not eqs:
            continue                       # 口播只有文字结论：抽不出等式就不假装推导
        eqs = eqs[:3]

        # 代入：找一个「单字母 X=值」的已知式，X 出现在首式里 → 展开首式并挂 sub。
        # 展开不出可指代 X 的槽位就不挂 sub（否则动画会指错位置，review 的 KIND 会打回）。
        sub = None
        src_eq = None
        chain = [eqs[0]]
        if "代入" in narr:
            head_lhs = eqs[0].split("=", 1)[0].strip()
            for eq in eqs[1:]:
                lhs, rhs = (x.strip() for x in eq.split("=", 1))
                if len(lhs) == 1 and lhs.isalpha() and lhs != head_lhs and lhs in eqs[0]:
                    expanded = _expand_product(eqs[0])
                    if expanded and re.search(rf"(?<![A-Za-z]){re.escape(lhs)}(?![A-Za-z])", expanded):
                        sub = (lhs, rhs)
                        src_eq = eq
                        chain.append(expanded)
                    break
        for eq in eqs[1:]:
            if eq == src_eq or eq in chain:
                continue
            chain.append(eq)
        chain = chain[:3]

        # at 必须逐字来自口播、且各步不同：按口播里出现的先后顺序把触发短语分给第 2、3 步，
        # 没那么多触发词才退回行序比例（scene 会按比例映射）。
        triggers: list[str] = []
        for m in _DERIV_TRIGGER_RE.finditer(narr):
            if m.group(0) not in triggers:
                triggers.append(m.group(0))

        def _at(i: int) -> str | float:
            if i == 0:
                return 0.0
            if i - 1 < len(triggers):
                return triggers[i - 1]
            return round(i / len(chain), 3)

        steps = []
        for i, eq in enumerate(chain):
            st: dict = {"text": eq, "at": _at(i)}
            if i == 0:
                st["note"] = "已知" if "已知" in narr else ""
            elif sub is not None and i == 1:
                st["sub"] = {sub[0]: sub[1]}
                st["note"] = f"把 {sub[0]}={sub[1]} 代入"
            else:
                st["transform"] = max(0, i - 1)
                st["note"] = "化简得" if "化简" in narr else ""
            steps.append(st)

        letters: dict[str, str] = {}
        for eq in chain:
            for ch in re.findall(r"[A-Za-zΑ-ωΔ]", eq):
                letters.setdefault(ch, "")     # 只给同字母同色；不编物理含义（图例留空）
        label = "推导"
        if target.get("kind") == "steps":
            label = str((target.get("props") or {}).get("heading") or "推导").strip() or "推导"
        props = {
            "steps": steps,
            "symbols": letters,
            "label": label,
            "at": [st["at"] for st in steps],
        }
        last_rhs = chain[-1].split("=", 1)[-1].strip()
        if last_rhs:
            props["result"] = last_rhs
        target["kind"] = "derivation"
        target["props"] = props


def _reveal_keys(node) -> set[str]:
    """一镜版式里所有 at 揭示键（含 graph_vt 的 cases[].at；at 可为字符串或列表）。"""
    out: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "at":
                out.update(x.strip() for x in ([v] if isinstance(v, str) else v if isinstance(v, list) else [])
                           if isinstance(x, str) and x.strip())
            else:
                out |= _reveal_keys(v)
    elif isinstance(node, list):
        for v in node:
            out |= _reveal_keys(v)
    return out


def _reflow_narration(blocks: list[dict], chars: list[int], cap_total: int, cap_shot: int,
                      must_say: list[str]) -> None:
    """内部调整：正片口播超预算时从最长的镜头开始按句裁尾，直到总线和单镜线都过。

    两类句子不裁：命中 must_say 的（那是这一条知识点的口径），以及每镜仅剩的最后一句
    （宁可让 OVERLOAD/DUR_SHARE 说「时长装不下这些内容」，也不交出一句空话）。
    """
    locked = []
    for b in blocks:
        sents = _sentences(b.get("narration"))
        keys = _reveal_keys(b.get("visuals"))
        # 按句子文本记锁，不按下标：裁一句后面所有的下标都会左移。
        # 版式的揭示键（at）也锁：裁掉「图线下斜…」那句，graph_vt 那条图线就永远等不到它（KIND）。
        locked.append({s for s in sents
                       if any(_pace_text(p) and _pace_text(p) in _pace_text(s) for p in must_say)
                       or any(k in s for k in keys)})
    guard = sum(len(_sentences(b.get("narration"))) for b in blocks)
    while (sum(chars) > cap_total or (chars and max(chars) > cap_shot)) and guard > 0:
        guard -= 1
        cand = None
        for i in sorted(range(len(blocks)), key=lambda k: -chars[k]):
            sents = _sentences(blocks[i].get("narration"))
            if len(sents) < 2:
                continue
            # 逐句摘除（不是整段截尾）：must_say 锁住的句子留在原位，首句永不删，
            # 否则一镜裁到只剩半句空话，比让闸门报 OVERLOAD 更糟。
            drop = next((j for j in range(len(sents) - 1, 0, -1) if sents[j] not in locked[i]), None)
            if drop is not None:
                cand = (i, drop, sents)
                break
        if cand is None:
            break
        i, drop, sents = cand
        blocks[i]["narration"] = "".join(sents[:drop] + sents[drop + 1:]).strip()
        chars[i] = _chars(blocks[i]["narration"])



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
    # 深拷贝：内部调整就地改文案，不许回头污染调用方传进来的 kp（knowledge.load 的缓存）
    blocks = deepcopy(list(kp["sequence"]))
    refs = _all_refs(kp)
    # 内部调整第一步：屏上字太宽先按句读拆行（LEGIBLE 的根因大多是排版而非内容）
    _fit_callouts(blocks)
    # 82-SD1b：口播在推导、画面却只有 formula/steps 的镜，就地兜底成 derivation
    # （确定性、无 LLM；只用本镜已有等式，最多 3 步；已有 derivation 的镜不碰）
    _derivation_fallback(blocks)

    prior = None
    prior_chars = 0
    # 点名镜只配 NAME_MAX_SHARE 的预算：标签去掉括注后按原顺序装，装不下的尾巴不念（内部调整，
    # 不把"标签写长了"变成整片打回）。
    labels = fit_naming_labels(kp.get("prior") or [], NAME_MAX_SHARE * num(brief.target_seconds))
    if brief.prior_knowledge and labels:
        narr = naming_narration(labels)
        # 时长跟着标签文本走：先前写死 8s，四条长标签就是 9 字/秒，闸门判它说不完。
        # 尺子取自 ir.naming_shot_seconds——prereq.py 对同一段文本必须算出同一个秒数。
        need = naming_shot_seconds(narr)
        prior = {
            "title": "先修：需要什么基础",
            "seconds": round(min(need, NAME_MAX_SHARE * num(brief.target_seconds)), 2),
            "narration": narr,
            "emphasis": "先修知识",
            "visuals": [{"kind": "callout", "props": {"text": "先修：" + " · ".join(labels), "tone": "key"}}],
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

    # 内部调整：正片口播按闸门上限语速（留 3% 抖动）都塞不进剩余预算时，先让出点名镜，
    # 再把总时长放宽到 TARGET 闸门 ±10% 带内；仍不够才交给 OVERLOAD/PACING 去说。
    tight = sum(max(_MIN_WINDOW_CS, int(ceil(c / (_SAFE_CPS) * _CS))) for c in chars) \
        + len(body) * _HEAD_TAIL_CS
    if prior and tight > int(round((target - fixed) * _CS)):
        blocks, prior, fixed, prior_chars = body, None, 0.0, 0
    spend = target - fixed
    if int(round(spend * _CS)) < tight <= int(round((_STRETCH * target - fixed) * _CS)):
        spend = tight / _CS
    budget = int(round(spend * _CS)) - len(body) * _HEAD_TAIL_CS
    # 内部调整第二步：连上限语速都念不完的字数，先按句裁掉最长的镜头再重分秒数
    # （must_say 的句子不裁）。裁到无可裁仍超的，才是「这些内容装不进这个时长」，交给闸门如实说。
    cap_total = int(budget / _CS * _SAFE_CPS)
    if body and (sum(chars) > cap_total or max(chars) > int(MAX_SHOT_SHARE * cap_total)):
        _reflow_narration(body, chars, cap_total, int(MAX_SHOT_SHARE * cap_total),
                          [str(m) for m in (kp.get("must_say") or []) if str(m).strip()])
        needs = [_need_cs(c) for c in chars]
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
