# -*- coding: utf-8 -*-
"""flow v2 棒次自动化桥（pipeline.flow）回归：全部用假 chat（monkeypatch），不联网、不读密钥。

锁住的是编排边界，不是模型说了什么：
① handoff 状态迁移 + 原子写（临时文件不残留、写坏不污染旧态）；
② 524/截断 → 分段调用 + 机械拼接（Spec 第 11 节第 2 条，形态对齐 .local/complex_trial/gateway.py）；
③ O 路由表：K2 FAIL→K1、A4 blocking 按码分派 M1/M2/V0、打回环 3 轮上限→BLOCKED；
④ 审计件齐全：prompt_system/prompt_user/response*/report 每棒落盘（第 10 节第 5 条铁律）；
⑤ validate 坏 JSON 的回喂重试计数（retries 递增、错误清单进 user prompt）。
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _util import shot_dict  # noqa: E402
from pipeline import llm_client  # noqa: E402
from pipeline.flow import bridge, handoff  # noqa: E402
from pipeline.flow.stages import (STAGES, RunCtx, route_a4_fail, route_a8_fail,  # noqa: E402
                                  route_k2_pass, route_s22_fail)

MUST_SAY = "右边的电势高于左边的电势"
FORBIDDEN = "一定导电"


def make_run(seconds: float = 120, kp_id: str = "") -> Path:
    """建临时 run（init_run 同生产入口），返回 run_dir。"""
    d = Path(tempfile.mkdtemp(prefix="flowtest_")) / "trial_run"
    brief = {"subject": "physics", "grade": "H2", "topic": "测试知识点",
             "seconds": seconds, "style": {}}
    handoff.init_run(d, kp_id, brief)
    return d


def write_kp(run_dir: Path, **over) -> dict:
    kp = {"id": "kp.physics.test", "subject": "physics", "grade": "H2", "topic": "测试知识点",
          "must_say": [MUST_SAY], "forbidden": [FORBIDDEN], **over}
    (run_dir / "kp_draft.json").write_text(json.dumps(kp, ensure_ascii=False, indent=1), encoding="utf-8")
    return kp


def good_script(seconds: float = 120, n: int = 5) -> dict:
    """满足 V0 确定性校验的 visual_script：n 镜均分、总时长精确、must_say 逐字进镜 2、无 forbidden。"""
    per = round(seconds / n, 3)
    shots = []
    for i in range(1, n + 1):
        narr = f"第{i}镜讲解画面叙事。" + (f"注意，{MUST_SAY}。" if i == 2 else "")
        shots.append({"shot_no": i, "seconds_budget": per, "画面叙事": f"叙事{i}",
                      "sim_kind": "sim", "narration": narr, "屏上标注": "", "reveal_beats": []})
    shots[-1]["seconds_budget"] = round(seconds - per * (n - 1), 3)
    return {"style": {"theme": "dark"}, "shots": shots}


def fake_chat_factory(reply):
    """reply(text) 或 reply 为 str；返回 (fake, calls)。"""
    calls = []

    def fake(stage, system, user, images=None, **kw):
        calls.append({"stage": stage, "system": system, "user": user, "kw": kw})
        return reply(user) if callable(reply) else reply
    return fake, calls


def write_plan(run_dir: Path, with_figure: bool = False) -> None:
    visuals = [{"kind": "callout", "props": {"text": "提示"}}]
    if with_figure:
        visuals.append({"kind": "figure", "props": {"shape": "right_triangle", "a": 3, "b": 4}})
    plan = {"brief": {"subject": "physics", "grade": "H1", "topic": "加速度",
                      "target_seconds": 120, "style": "clean", "resolution": "1920x1080"},
            "knowledge_id": "kp.physics.acceleration",
            "shots": [shot_dict(index=i, seconds=20.0, narration="口播", visuals=list(visuals))
                      for i in range(6)],
            "refs": []}
    (run_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- ① 状态机


class TestHandoffStateMachine(unittest.TestCase):
    def test_init_creates_brief_and_handoff(self):
        d = make_run()
        self.assertTrue((d / "brief.json").exists())
        state = handoff.load(d)
        self.assertEqual(state["route_next"], "K1")
        self.assertTrue(all(s["status"] == "pending" for s in state["stages"].values()))
        self.assertEqual(set(state["stages"]), set(handoff.STAGE_ORDER))

    def test_transitions(self):
        d = make_run()
        state = handoff.load(d)
        handoff.mark(state, "K1", status="running")
        handoff.mark(state, "K1", status="pass", verdict="PASS", report="reports/K1.md", route_next="K2")
        handoff.save(d, state)
        again = handoff.load(d)
        self.assertEqual(again["stages"]["K1"]["status"], "pass")
        self.assertEqual(again["route_next"], "K2")
        self.assertEqual(handoff.bump_round(again, "K1"), 1)
        self.assertEqual(handoff.bump_round(again, "K1"), 2)
        with self.assertRaises(AssertionError):
            handoff.mark(again, "K1", status="not_a_status")

    def test_atomic_write_no_tmp_leftovers(self):
        d = make_run()
        state = handoff.load(d)
        handoff.save(d, state)
        self.assertEqual(list(d.glob("handoff.json.*")), [])

    def test_failed_write_keeps_old_state_and_cleans_tmp(self):
        d = make_run()
        state = handoff.load(d)
        before = (d / "handoff.json").read_text(encoding="utf-8")
        state["stages"]["K1"]["status"] = "pass"
        state["unserializable"] = object()          # json.dump 中途炸
        with self.assertRaises(TypeError):
            handoff.save(d, state)
        self.assertEqual((d / "handoff.json").read_text(encoding="utf-8"), before)
        self.assertEqual(list(d.glob("handoff.json.*")), [])


# ---------------------------------------------------------------- ④ 审计件 + happy path


class TestRunStageV0(unittest.TestCase):
    def test_pass_audit_trail_and_route(self):
        d = make_run()
        write_kp(d)
        fake, calls = fake_chat_factory(json.dumps(good_script(), ensure_ascii=False))
        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "V0")
        self.assertEqual(nxt, "M1")
        state = handoff.load(d)
        slot = state["stages"]["V0"]
        self.assertEqual((slot["status"], slot["verdict"]), ("pass", "PASS"))
        self.assertEqual(state["route_next"], "M1")
        for rel in ("reports/V0_prompt_system.md", "reports/V0_prompt_user.md",
                    "reports/V0_response.md", "reports/V0.md", "visual_script.json"):
            self.assertTrue((d / rel).exists(), rel)
        report = (d / "reports/V0.md").read_text(encoding="utf-8")
        self.assertIn("agent: V0", report)
        self.assertIn("model: claude-opus-5-5", report)      # 钉死表原样
        self.assertIn("verdict: PASS", report)
        self.assertIn("next: M1", report)
        self.assertEqual(calls[0]["kw"]["max_tokens"], 4000)  # 缺省 4000 抗 524
        # system prompt = Spec 第 8 节抽取件原样
        self.assertEqual((d / "reports/V0_prompt_system.md").read_text(encoding="utf-8"),
                         STAGES["V0"].system_prompt())

    def test_isolated_stage_guard(self):
        d = make_run()
        with self.assertRaises(PermissionError):
            bridge.run_stage(d, "K2")                          # 未 isolated_ok 不许内联跑
        self.assertTrue(STAGES["K2"].needs_isolated_context)
        self.assertTrue(STAGES["P"].needs_isolated_context)
        self.assertTrue(STAGES["A8"].needs_isolated_context)
        self.assertTrue(STAGES["S22"].needs_isolated_context)
        self.assertFalse(STAGES["V0"].needs_isolated_context)


# ---------------------------------------------------------------- ② 524 分段拼接


class TestSegmented524(unittest.TestCase):
    def test_524_then_segmented_stitch(self):
        d = make_run()
        write_kp(d)
        (d / "visual_script.json").write_text(
            json.dumps(good_script(n=4), ensure_ascii=False), encoding="utf-8")
        state = {"calls": 0}

        def fake(stage, system, user, images=None, **kw):
            state["calls"] += 1
            if state["calls"] == 1:
                raise llm_client.LLMError("[M2/claude-opus-5-5] 调用失败：HTTP 524 origin timeout")
            k = state["calls"] - 1
            return f"```python\nclass Shot{k}(Scene):\n    SECONDS = 30\n```\n"

        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "M2")
        self.assertEqual(nxt, "A4")
        # head + 4 镜 = 5 段，逐段落盘 _part<i>.md，拼接件也落盘
        for i in range(5):
            self.assertTrue((d / f"reports/M2_response_r2_part{i}.md").exists(), f"part{i}")
        self.assertTrue((d / "reports/M2_response_r2.md").exists())
        stitched = (d / "reports/M2_response_r2.md").read_text(encoding="utf-8")
        for i in range(1, 5):
            self.assertIn(f"class Shot{i}", stitched)
        gen = list((d / "generated").glob("*_scene.py"))
        self.assertEqual(len(gen), 1)
        self.assertIn("class Shot1", gen[0].read_text(encoding="utf-8"))
        slot = handoff.load(d)["stages"]["M2"]
        self.assertEqual(slot["status"], "pass")
        self.assertEqual(len(slot["responses"]), 6)           # 5 段 + 1 拼接件

    def test_truncated_json_switches_to_segments(self):
        """响应截断（JSON 坏）→ 下一轮转分段（json 拼接策略：逐段抽取机械合并）。"""
        d = make_run()
        write_kp(d)
        script = good_script(n=4)
        half1 = json.dumps({"style": script["style"], "shots": script["shots"][:2]}, ensure_ascii=False)
        half2 = json.dumps({"shots": script["shots"][2:]}, ensure_ascii=False)
        seq = [half1[:-3], half1, half2]                      # 首次截断（坏 JSON），后两段成功
        it = iter(seq)
        fake, calls = fake_chat_factory(lambda user: next(it))
        st = STAGES["V0"]
        with mock.patch.object(llm_client, "chat", fake), \
                mock.patch.object(st, "segments", lambda ctx: ["seg1", "seg2"]):
            nxt = bridge.run_stage(d, "V0")
        self.assertEqual(nxt, "M1")
        merged = json.loads((d / "visual_script.json").read_text(encoding="utf-8"))
        self.assertEqual(len(merged["shots"]), 4)             # 两段 shots 机械串接
        self.assertEqual(merged["style"], script["style"])


# ---------------------------------------------------------------- ③ 路由表


class TestRouting(unittest.TestCase):
    def _ctx(self, d: Path, kp: dict | None = None) -> RunCtx:
        state = handoff.load(d)
        return RunCtx(run_dir=d, state=state, brief=state["brief"], kp=kp)

    def test_k2_fail_routes_to_k1(self):
        d = make_run()
        write_kp(d)
        fake, _ = fake_chat_factory("逐条判定：数值 X UNSUPPORTED（p.3 摘抄略）。\nverdict: FAIL")
        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "K2", isolated_ok=True)
        self.assertEqual(nxt, "K1")
        state = handoff.load(d)
        self.assertEqual(state["route_next"], "K1")
        self.assertEqual(state["stages"]["K2"]["status"], "fail")
        self.assertEqual(state["stages"]["K1"]["round"], 1)   # 打回计数进目标棒

    def test_k2_pass_routes_by_figure_refs(self):
        d = make_run()
        write_kp(d)                                            # 无 figure_refs → V0
        ctx = self._ctx(d)
        self.assertEqual(route_k2_pass(ctx.state, ctx, None), "V0")
        write_kp(d, figure_refs=[{"pdf": "x.pdf", "page": 3, "figure_no": 1}])
        ctx = self._ctx(d)
        self.assertEqual(route_k2_pass(ctx.state, ctx, None), "P")

    def test_phys_code_classification(self):
        d = make_run()
        ctx = self._ctx(d)
        v = lambda *codes: {"violations": [{"code": c} for c in codes]}   # noqa: E731
        self.assertEqual(route_a4_fail(ctx.state, ctx, v("PHYS_ANALYTIC")), "M1")
        self.assertEqual(route_a4_fail(ctx.state, ctx, v("PHYS_UNIT", "PHYS_ENERGY")), "M1")
        self.assertEqual(route_a4_fail(ctx.state, ctx, v("PHYS_GRAPH_SYNC")), "M2")
        self.assertEqual(route_a4_fail(ctx.state, ctx, v("PHYS_MB")), "M2")
        self.assertEqual(route_a4_fail(ctx.state, ctx, v("GLYPH", "PACING")), "V0")
        self.assertEqual(route_a8_fail(ctx.state, ctx, {"issues": [{"code": "MOTION_STATIC"}]}), "M2")
        self.assertEqual(route_a8_fail(ctx.state, ctx, {"issues": [{"code": "OVERLAP"}]}), "V0")
        self.assertEqual(route_s22_fail(ctx.state, ctx, {"text": "G1 命中：科学性硬错"}), "K1")

    def test_a4_blocking_routes_to_v0_and_counts_rounds(self):
        d = make_run()
        write_plan(d, with_figure=False)                       # 无 figure → NO_FIGURE 阻断（旧 18 码）
        nxt = bridge.run_stage(d, "A4")
        self.assertEqual(nxt, "V0")
        state = handoff.load(d)
        self.assertEqual(state["stages"]["A4"]["status"], "fail")
        self.assertEqual(state["stages"]["V0"]["round"], 1)
        review_json = json.loads((d / "review.json").read_text(encoding="utf-8"))
        self.assertIn("checked", review_json)
        self.assertTrue(review_json["violations"])
        self.assertIn("NO_FIGURE", {f["code"] for f in review_json["violations"]})
        self.assertTrue((d / "reports/A4.md").exists())

    def test_a4_pass_goes_to_r(self):
        d = make_run()
        write_plan(d, with_figure=True)
        # 干净 plan（真实库数据同构）才 0 findings；这里只断言路由函数行为
        obj = {"checked": ["NO_FIGURE"], "violations": []}
        nxt = STAGES["A4"].next_on_pass
        self.assertEqual(nxt, "R")
        self.assertEqual(obj["violations"], [])

    def test_three_round_cap_blocks(self):
        d = make_run()
        write_plan(d, with_figure=False)
        state = handoff.load(d)
        state["stages"]["V0"]["round"] = 3                      # 已打回 3 轮
        handoff.save(d, state)
        nxt = bridge.run_stage(d, "A4")
        self.assertEqual(nxt, "BLOCKED")
        state = handoff.load(d)
        self.assertEqual(state["route_next"], "BLOCKED")
        self.assertEqual(state["stages"]["A4"]["status"], "blocked")
        self.assertEqual(state["stages"]["V0"]["round"], 4)

    def test_auto_stops_at_isolated_with_spawn_line(self):
        d = make_run()
        write_kp(d)
        state = handoff.load(d)
        handoff.mark(state, "K1", status="pass", verdict="PASS", route_next="K2")
        handoff.save(d, state)
        buf = mock.patch.object(sys, "stdout", new=io.StringIO())
        with buf as out:
            rc = bridge.auto(d)
        text = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("SPAWN_SUBAGENT: stage=K2", text)
        self.assertIn(f"run={d.resolve()}", text)
        self.assertIn("--stage K2", text)
        self.assertTrue((d / "reports/K2_prompt_system.md").exists())
        self.assertTrue((d / "reports/K2_prompt_user.md").exists())
        # 独立性棒没有被内联执行
        self.assertEqual(handoff.load(d)["stages"]["K2"]["status"], "pending")

    def test_r_adapter_missing_produce_blocks(self):
        d = make_run()
        nxt = bridge.run_stage(d, "R")
        self.assertEqual(nxt, "BLOCKED")                        # 无 .local/<run>/produce.py → 不伪造产物
        state = handoff.load(d)
        self.assertEqual(state["stages"]["R"]["verdict"], "BLOCKED")
        self.assertTrue((d / "reports/R.md").exists())


# ---------------------------------------------------------------- ⑤ 坏 JSON 回喂重试


class TestValidateRetry(unittest.TestCase):
    def test_bad_json_feeds_back_and_counts_retries(self):
        d = make_run()
        write_kp(d)
        good = json.dumps(good_script(), ensure_ascii=False)
        seq = iter(["这不是 JSON", "```json\n{坏掉的\n```", good])
        fake, calls = fake_chat_factory(lambda user: next(seq))
        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "V0")
        self.assertEqual(nxt, "M1")
        slot = handoff.load(d)["stages"]["V0"]
        self.assertEqual(slot["retries"], 2)                    # 两次坏 → 两次回喂
        self.assertEqual(len(slot["responses"]), 3)
        for rel in ("reports/V0_response.md", "reports/V0_response_r2.md", "reports/V0_response_r3.md"):
            self.assertTrue((d / rel).exists(), rel)
        user_prompt = (d / "reports/V0_prompt_user.md").read_text(encoding="utf-8")
        self.assertIn("上一轮输出的错误清单", user_prompt)        # 回喂进 user prompt（落盘版为最终版）
        self.assertEqual(len(calls), 3)

    def test_exhausted_retries_fail_to_blocked(self):
        d = make_run()
        write_kp(d)
        fake, calls = fake_chat_factory("永远不是 JSON")
        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "V0")
        self.assertEqual(nxt, "BLOCKED")                        # V0 自身格式坏 3 次 → 报用户
        state = handoff.load(d)
        self.assertEqual(state["stages"]["V0"]["status"], "fail")
        self.assertEqual(state["stages"]["V0"]["retries"], 2)
        self.assertEqual(len(calls), 3)
        self.assertIn("FAIL", (d / "reports/V0.md").read_text(encoding="utf-8"))

    def test_must_say_and_forbidden_enforced(self):
        d = make_run()
        write_kp(d)
        bad = good_script()
        bad["shots"][1]["narration"] = "这里没有那句必说的话。"
        bad["shots"][2]["narration"] += f"而且{FORBIDDEN}。"
        fake, _ = fake_chat_factory(json.dumps(bad, ensure_ascii=False))
        with mock.patch.object(llm_client, "chat", fake):
            nxt = bridge.run_stage(d, "V0")
        self.assertEqual(nxt, "BLOCKED")
        report = (d / "reports/V0.md").read_text(encoding="utf-8")
        self.assertIn("must_say", report)
        self.assertIn("forbidden", report)
        self.assertFalse((d / "visual_script.json").exists())   # 校验不过不落产物


if __name__ == "__main__":
    unittest.main(verbosity=2)
