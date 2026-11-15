"""A3 分镜的 LLM 实现：模型只写「讲什么、什么顺序、各占多少权重」，真实秒数、先修点名镜、
预算账本仍由 storyboard.build 的确定性代码算（把模型的镜头当作替换后的 kp.sequence 喂进去）。

闸门（review.check）不改：模型产物必须原样过 A4，被打回就把清单回灌，最多 2 次；
仍不过或模型不可用就退回确定性分镜，并在 info 里如实记下原因（不静默吞错）。
"""

from __future__ import annotations

import json
from copy import deepcopy

from . import kp_draft, llm_client, llm_prompts, review, storyboard
from .ir import VISUAL_KINDS, FIGURE_SHAPES, NATURAL_CPS, Brief, Plan
from .storyboard import MIN_SHOTS, max_shots_for  # 81-A1b：镜头密度单一真源在 storyboard，不再各写一份 MAX_SHOTS

MAX_FEEDBACK_RETRIES = 2

# #85 T2：回灌反馈要带**行动指引**，不能只把清单重列一遍。
# 线上圆锥曲线片的三轮回灌全烧在同一句「kind 必须是 (…) 之一且 props 是对象」上：模型想画的
# 双曲线当时不在 figure 的 shape 里，而 axis_graph 其实能画任意采样曲线、marks[].label 能标任意
# 点名——降级路径一直存在，只是报错从没告诉过模型，于是它只能再自造一个 kind。
# 指引文案放模块级常量，回灌各轮复用同一份（不拼三份、不与 review 的白名单各写一套）。
SCHEMA_GUIDE = (
    "要画的曲线/点在这份清单里找不到对应写法时：改用 axis_graph——curves[].points 给采样点"
    "（[[x,y],…] 至少两点）就能画任意曲线，marks[].label 支持任意字符点名；"
    f"圆锥曲线一类的几何图形用 figure（shape 枚举：{'/'.join(FIGURE_SHAPES)}，"
    '动点字母用 point_label、轴端点用 vertices）。不要自造清单之外的 kind 名。')


def _schema_errors(data, target_seconds: float = 0.0) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
        return ["顶层必须是 {\"shots\": [...]}"]
    shots = data["shots"]
    errs = []
    cap = max_shots_for(target_seconds)   # 上限随目标时长伸缩（1200s → 20），短片仍是 10
    if not MIN_SHOTS <= len(shots) <= cap:
        errs.append(f"镜头数必须在 {MIN_SHOTS}~{cap} 之间，收到 {len(shots)}")
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
            props = v.get("props", {}) if isinstance(v, dict) else {}
            if not isinstance(v, dict) or v.get("kind") not in VISUAL_KINDS or not isinstance(props, dict):
                # 报错口径与旧版一致（列合法 kind），再附一句可直接照做的降级路径。
                errs.append(f"shots[{i}].visuals[{j}] 的 kind 必须是 {list(VISUAL_KINDS)} 之一且 props 是对象"
                            f"；{SCHEMA_GUIDE}")
                continue
            if v["kind"] == "figure" and props.get("shape") is not None \
                    and str(props["shape"]) not in FIGURE_SHAPES:
                # shape 非法要说清 shape 枚举，不要泛泛报 props（#85：模型收到"props 有问题"只会换个说法再猜）。
                errs.append(f"shots[{i}].visuals[{j}] 的 figure shape 必须是 {'/'.join(FIGURE_SHAPES)} 之一，"
                            f"收到 {props['shape']!r}")
    return errs


def _blocks(data: dict) -> list[dict]:
    return [{"title": s["title"].strip(), "seconds": float(s["seconds"]), "narration": s["narration"].strip(),
             "emphasis": str(s.get("emphasis") or ""),
             "visuals": [{"kind": v["kind"], "props": deepcopy(v.get("props", {}))} for v in s["visuals"]]}
            for s in data["shots"]]


def _user_message(brief: Brief, kp: dict, feedback: list[str] | None, prev: str | None,
                  head: str = "【上一版被静态闸门/校验打回的清单，请逐条修正后重新输出完整 JSON】") -> str:
    cap = max_shots_for(brief.target_seconds)
    # 字数预算口径 = ir.NATURAL_CPS（真实语速标定 4.75 字/秒取整为 4.7，见 ir.py:46-51；
    # 旧系数 3.9 是换配音引擎前 SAPI 的读数）。A3_SYSTEM 提示词里的字数公式同一把尺子
    # （llm_prompts.py 用 {{CPS}}=NATURAL_CPS 替换），下发文本与校验口径不得漂移。
    chars = int(brief.target_seconds * NATURAL_CPS)
    msg = (f"学科：{brief.subject}  学段：{kp_draft.GRADE_ZH.get(brief.grade, brief.grade)}  风格：{brief.style}\n"
           f"目标时长：{brief.target_seconds} 秒（镜头数 {MIN_SHOTS}~{cap} 个；"
           f"口播总字数建议不超过约 {chars} 字，含所有镜头）\n")
    # 学段超纲红线与 review.check 同一份词表（review.scope_prompt），生成前就压住；
    # 生成后即使漏了还有 A4 的 GRADE_SCOPE 兜底打回。
    scope = review.scope_prompt(brief.grade, brief.subject)
    if scope:
        msg += scope + "\n"
    msg += (f"先修点名镜：{'由系统在片头另加，你不要写' if brief.prior_knowledge and kp.get('prior') else '本片不要'}\n\n"
            f"【知识点条目 JSON（唯一事实来源）】\n{json.dumps(kp, ensure_ascii=False, indent=1)}")
    if feedback:
        msg += ("\n\n【上一版输出】\n" + (prev or "") + "\n\n" + head + "\n" + "\n".join(feedback))
    return msg


def _as_json(plan: Plan) -> str:
    return json.dumps({"shots": [{"title": s.title, "seconds": s.seconds, "narration": s.narration,
                                  "emphasis": s.emphasis,
                                  "visuals": [{"kind": v.kind, "props": v.props} for v in s.visuals]}
                                 for s in plan.shots if s.emphasis != "先修知识"]},
                      ensure_ascii=False, indent=1)


def adjust(brief: Brief, kp: dict, plan: Plan, hard: list[dict]) -> tuple[Plan, dict]:
    """确定性分镜被闸门判了阻断项时的内部调整：把那一版和打回清单直接回灌给 A3 模型改写。
    仍不过就把原 plan 原样还回去，由调用方决定是否打回。"""
    feedback = [f"- shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard]
    return build(brief, kp, feedback=feedback, prev=_as_json(plan), fallback=plan)


DEFAULT_HEAD = "【上一版被静态闸门/校验打回的清单，请逐条修正后重新输出完整 JSON】"
MIXED_HEAD = "【这一版既有用户的改进要求、又有静态闸门/校验的问题，逐条处理后重新输出完整 JSON】"


def build(brief: Brief, kp: dict, *, feedback: list[str] | None = None, prev: str | None = None,
          fallback: Plan | None = None, head: str | None = None) -> tuple[Plan, dict]:
    """返回 (Plan, info)。info.source ∈ llm / fallback；fallback 时 info.reason 写明原因。

    feedback/head 是回灌通道：闸门清单和用户的改进意见走同一条路，只是话术不同；
    改进通道里用户那句在后续每一轮都留着，不能被闸门清单顶掉。
    """
    head = head or DEFAULT_HEAD
    orig = list(feedback or [])
    info: dict = {"source": "fallback", "model": llm_client.model_for("A3"), "attempts": 0, "reason": "",
                  "history": [feedback] if feedback else []}
    for attempt in range(MAX_FEEDBACK_RETRIES + 1):
        info["attempts"] = attempt + 1
        try:
            raw = llm_client.chat("A3", llm_prompts.A3_SYSTEM, _user_message(brief, kp, feedback, prev, head),
                                  max_tokens=12000, json_mode=True)
            data = llm_client.extract_json(raw)
        except llm_client.LLMError as e:
            info["reason"] = str(e)
            break
        prev = raw.strip()
        errs = _schema_errors(data, brief.target_seconds)
        if errs:
            bad = [f"- [SCHEMA] {m}" for m in errs]
            if head != DEFAULT_HEAD:     # 改进通道：用户那句要跟着闸门清单一起留着
                feedback = orig + bad
                head = MIXED_HEAD
            else:
                feedback = bad
            info["history"].append(feedback)
            continue
        kp2 = deepcopy(kp)
        kp2["sequence"] = _blocks(data)
        plan = storyboard.build(brief, kp2)
        hard = review.blocking(review.check(plan, kp))
        if not hard:
            info["source"] = "llm"
            return plan, info
        bad = [f"- shot {f['shot']} [{f['code']}] {f['msg']}" for f in hard]
        if head != DEFAULT_HEAD:          # 改进通道：用户那句要跟着闸门清单一起留着
            feedback = orig + bad
            head = MIXED_HEAD
        else:
            feedback = bad
        info["history"].append(feedback)
    if not info["reason"]:
        info["reason"] = "回灌 %d 次后仍未过静态闸门：%s" % (MAX_FEEDBACK_RETRIES, "；".join((feedback or [])[:3]))
    return (fallback if fallback is not None else storyboard.build(brief, kp)), info


def improve(brief: Brief, kp: dict, plan: Plan, instruction: str) -> tuple[Plan, dict]:
    """用户在成片下面写的改进意见：连着上一版分镜一起交给 A3 重写，新版的秒数仍由确定性分配算。

    改进版照样过闸门；模型不可用或改到过不去就原样返回上一版（info.source=fallback），
    由调用方决定是保留上一版还是报错——绝不因为一句意见把已经出来的片子毁掉。
    """
    return build(brief, kp,
                 feedback=[f"- 用户改进要求：{instruction}"],
                 prev=_as_json(plan), fallback=plan,
                 head="【用户对上一版成片的改进要求，请在上一版基础上修改后重新输出完整 JSON】")
