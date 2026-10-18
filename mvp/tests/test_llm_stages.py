"""LLM 四环节接入的回归：全部用假传输，不联网、不读密钥。

锁住的是边界，而不是模型说了什么：开关默认关；A1 只认库内命中；A3 的产物必须原样过 A4，
被打回就回灌、仍不过就退回确定性分镜；S2.2 无引文的扣分作废；密钥不进异常信息。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _util import ACCEL, ok_brief  # noqa: E402
from pipeline import (knowledge, llm_client, requirement_llm, review, scoring_llm,  # noqa: E402
                      storyboard, storyboard_llm, visual_review_llm)

KP = knowledge.load("physics", "加速度", "H1")


def _shots_json(kp=KP) -> str:
    return json.dumps({"shots": [{k: b[k] for k in ("title", "seconds", "narration", "emphasis", "visuals")
                                  if k in b} for b in kp["sequence"]]}, ensure_ascii=False)


class TestToggles(unittest.TestCase):
    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            for st in llm_client.STAGES:
                self.assertFalse(llm_client.enabled(st))

    def test_single_and_all(self):
        with mock.patch.dict(os.environ, {"QX_LLM_A3": "1"}, clear=True):
            self.assertTrue(llm_client.enabled("A3"))
            self.assertFalse(llm_client.enabled("A1"))
        with mock.patch.dict(os.environ, {"QX_LLM_ALL": "1"}, clear=True):
            self.assertTrue(all(llm_client.enabled(s) for s in llm_client.STAGES))

    def test_four_stages_use_distinct_models(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            models = [llm_client.model_for(s) for s in llm_client.STAGES]
        self.assertEqual(len(set(models)), 4)

    def test_four_prompts_distinct(self):
        from pipeline import llm_prompts as p
        self.assertEqual(len({p.A1_SYSTEM, p.A3_SYSTEM, p.A8_SYSTEM, p.S22_SYSTEM}), 4)


class TestKeyHygiene(unittest.TestCase):
    def test_missing_key_error_has_no_secret(self):
        with mock.patch.dict(os.environ, {"QX_LLM_API_KEY": "", "QX_LLM_KEY_FILE": str(Path(tempfile.gettempdir()) / "no_such_key_file.txt")}):
            with self.assertRaises(llm_client.LLMError):
                llm_client._api_key()

    def test_http_error_message_omits_key(self):
        secret = "sk-TESTSECRET123"
        import urllib.error
        import io
        err = urllib.error.HTTPError("u", 401, "x", {}, io.BytesIO(b"denied"))
        with mock.patch.dict(os.environ, {"QX_LLM_API_KEY": secret}), \
                mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(llm_client.LLMError) as cm:
                llm_client.chat("A1", "s", "u", retries=0)
        self.assertNotIn(secret, str(cm.exception))

    def test_extract_json_fenced(self):
        self.assertEqual(llm_client.extract_json('说明\n```json\n{"a": 1}\n```'), {"a": 1})
        with self.assertRaises(llm_client.LLMError):
            llm_client.extract_json("not json")


class TestA1(unittest.TestCase):
    def test_exact_hit_skips_model(self):
        with mock.patch.object(llm_client, "chat", side_effect=AssertionError("不该调用")):
            r = requirement_llm.normalize("physics", "H1", "加速度", 120)
        self.assertEqual(r["source"], "exact")

    def test_llm_hit_accepted_only_if_in_library(self):
        reply = json.dumps({"matched": True, "topic_id": "kp.physics.acceleration", "confidence": 0.9, "reason": "同义"})
        with mock.patch.object(llm_client, "chat", return_value=reply):
            r = requirement_llm.normalize("physics", "H1", "速度变化有多快", 120)
        self.assertEqual(r["source"], "llm")
        knowledge.load("physics", r["topic"], "H1")

    def test_invented_id_discarded(self):
        reply = json.dumps({"matched": True, "topic_id": "kp.physics.made_up", "reason": "x"})
        with mock.patch.object(llm_client, "chat", return_value=reply):
            r = requirement_llm.normalize("physics", "H1", "量子纠缠", 120)
        self.assertEqual(r["source"], "unchanged")
        self.assertEqual(r["topic"], "量子纠缠")

    def test_wrong_grade_id_discarded(self):
        reply = json.dumps({"matched": True, "topic_id": "kp.physics.acceleration"})
        with mock.patch.object(llm_client, "chat", return_value=reply):
            r = requirement_llm.normalize("physics", "G8", "速度变化有多快", 120)
        self.assertEqual(r["source"], "unchanged")

    def test_model_failure_falls_back_to_original_topic(self):
        with mock.patch.object(llm_client, "chat", side_effect=llm_client.LLMError("boom")):
            r = requirement_llm.normalize("physics", "H1", "速度变化有多快", 120)
        self.assertEqual((r["source"], r["topic"]), ("error", "速度变化有多快"))


class TestA3(unittest.TestCase):
    def test_good_output_passes_gate_unmodified(self):
        brief = ok_brief()
        with mock.patch.object(llm_client, "chat", return_value=_shots_json()):
            plan, info = storyboard_llm.build(brief, KP)
        self.assertEqual(info["source"], "llm")
        self.assertEqual(review.blocking(review.check(plan, KP)), [])
        self.assertTrue(storyboard.budget_of(plan))
        self.assertEqual(plan.refs[0], KP["refs"][0])

    def test_bad_then_good_feeds_back_findings(self):
        brief = ok_brief()
        bad = json.dumps({"shots": [{"title": "x", "seconds": 5, "narration": "说了" * 3,
                                     "visuals": [{"kind": "callout", "props": {"text": "t"}}]}] * 4}, ensure_ascii=False)
        calls = []

        def fake(stage, system, user, *a, **k):
            calls.append(user)
            return bad if len(calls) == 1 else _shots_json()

        with mock.patch.object(llm_client, "chat", side_effect=fake):
            plan, info = storyboard_llm.build(brief, KP)
        self.assertEqual(info["source"], "llm")
        self.assertEqual(info["attempts"], 2)
        self.assertIn("被静态闸门", calls[1])

    def test_always_bad_falls_back_to_deterministic(self):
        brief = ok_brief()
        with mock.patch.object(llm_client, "chat", return_value='{"shots": []}') as m:
            plan, info = storyboard_llm.build(brief, KP)
        self.assertEqual(m.call_count, storyboard_llm.MAX_FEEDBACK_RETRIES + 1)
        self.assertEqual(info["source"], "fallback")
        self.assertEqual(plan.to_dict(), storyboard.build(brief, KP).to_dict())

    def test_transport_error_falls_back_without_retrying(self):
        with mock.patch.object(llm_client, "chat", side_effect=llm_client.LLMError("down")) as m:
            plan, info = storyboard_llm.build(ok_brief(), KP)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(info["source"], "fallback")
        self.assertIn("down", info["reason"])

    def test_model_cannot_set_real_seconds(self):
        data = json.loads(_shots_json())
        for s in data["shots"]:
            s["seconds"] = 999
        with mock.patch.object(llm_client, "chat", return_value=json.dumps(data, ensure_ascii=False)):
            plan, info = storyboard_llm.build(ok_brief(), KP)
        total = sum(s.seconds for s in plan.shots)
        self.assertLess(abs(total - 120) / 120, 0.10)


class TestA8(unittest.TestCase):
    def _png(self):
        d = Path(tempfile.mkdtemp())
        p = d / "contact_sheet.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        return p

    def test_issues_make_fail_and_unknown_codes_dropped(self):
        reply = json.dumps({"verdict": "pass", "issues": [
            {"shot": 2, "frame": "尾", "code": "G3_CLIP", "msg": "字幕被裁"},
            {"shot": 1, "frame": "头", "code": "SCIENCE_WRONG", "msg": "越权"}], "summary": "s"})
        with mock.patch.object(llm_client, "chat", return_value=reply), \
                mock.patch.object(llm_client, "image_part", return_value={}):
            r = visual_review_llm.review(self._png())
        self.assertEqual(r["verdict"], "fail")
        self.assertEqual([i["code"] for i in r["issues"]], ["G3_CLIP"])

    def test_no_issues_is_pass(self):
        with mock.patch.object(llm_client, "chat", return_value='{"verdict": "fail", "issues": [], "summary": ""}'):
            r = visual_review_llm.review(self._png())
        self.assertEqual(r["verdict"], "pass")

    def test_unavailable_not_masquerading_as_pass(self):
        with mock.patch.object(llm_client, "chat", side_effect=llm_client.LLMError("down")):
            r = visual_review_llm.review(self._png())
        self.assertEqual(r["verdict"], "unavailable")


class TestS22(unittest.TestCase):
    def _plan(self):
        return storyboard.build(ok_brief(), KP).to_dict()

    def test_score_without_real_quote_is_voided(self):
        reply = json.dumps({"gates": {}, "S": {"S1": 3, "S2": 5, "S3": 5, "S4": 5, "S5": 5},
                            "U": {"U1": 5, "U2": 5, "U3": 5, "U4": 5, "U5": 5},
                            "evidence": [{"item": "S1", "shot": 1, "quote": "这句话分镜里根本没有", "why": "x"}]})
        with mock.patch.object(llm_client, "chat", return_value=reply):
            r = scoring_llm.score(self._plan(), KP)
        self.assertEqual(r["scores"]["S1"], 5)
        self.assertEqual(r["dropped_without_evidence"], ["S1"])

    def test_score_with_verbatim_quote_kept(self):
        plan = self._plan()
        quote = plan["shots"][1]["narration"][:8]
        reply = json.dumps({"gates": {}, "S": {"S1": 3, "S2": 5, "S3": 5, "S4": 5, "S5": 5},
                            "U": {"U1": 5, "U2": 5, "U3": 5, "U4": 5, "U5": 5},
                            "evidence": [{"item": "S1", "shot": 1, "quote": quote, "why": "x"}]})
        with mock.patch.object(llm_client, "chat", return_value=reply):
            r = scoring_llm.score(plan, KP)
        self.assertEqual(r["scores"]["S1"], 3)
        self.assertEqual(r["S"], 4.6)

    def test_unavailable(self):
        with mock.patch.object(llm_client, "chat", side_effect=llm_client.LLMError("down")):
            self.assertFalse(scoring_llm.score(self._plan(), KP)["available"])


if __name__ == "__main__":
    unittest.main()
