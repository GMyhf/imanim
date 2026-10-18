"""A2 资料调用闸门测试（红线 2）。

覆盖：topic / alias / id 命中、未命中抛 KnowledgeNotFound 并带候选、
坏数据（缺出处/缺字段/损坏 JSON）必须被拒。
坏数据一律写在 tempfile 目录里，绝不污染 pipeline/data/kp 真实库。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import knowledge
from pipeline.ir import SUBJECTS  # noqa: E402
from pipeline.knowledge import KnowledgeNotFound  # noqa: E402

REAL_DIR = knowledge.DATA_DIR


def sample_entry(**over) -> dict:
    e = {
        "id": "kp.test.sample",
        "subject": "physics",
        "grade": "H1",
        "topic": "测试知识点",
        "aliases": ["test alias"],
        "refs": [{"source": "测试教材", "locator": "第 1 章 1.1"}],
        "sequence": [{"title": "开场", "seconds": 8, "narration": "一句话。",
                      "visuals": [{"kind": "title", "props": {"main": "测试"}}]}],
    }
    e.update(over)
    return e


class TempLibrary(unittest.TestCase):
    """把 knowledge.DATA_DIR 临时指向 tempfile 目录（ASCII 路径）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "kp"
        (self.root / "physics").mkdir(parents=True)
        knowledge.DATA_DIR = self.root
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(setattr, knowledge, "DATA_DIR", REAL_DIR)

    def write(self, name: str, entry) -> Path:
        p = self.root / "physics" / f"{name}.json"
        p.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        return p

    def write_raw(self, name: str, text: str) -> Path:
        p = self.root / "physics" / f"{name}.json"
        p.write_text(text, encoding="utf-8")
        return p


class TestHitRealLibrary(unittest.TestCase):
    def test_hit_by_topic(self):
        e = knowledge.load("physics", "加速度")
        self.assertEqual(e["id"], "kp.physics.acceleration")
        self.assertEqual(e["subject"], "physics")

    def test_hit_by_alias(self):
        for alias in ("a=Δv/Δt", "acceleration", "速度变化的快慢"):
            self.assertEqual(knowledge.load("physics", alias)["id"], "kp.physics.acceleration")

    def test_hit_by_id(self):
        self.assertEqual(knowledge.load("physics", "kp.physics.acceleration")["topic"], "加速度")

    def test_every_library_entry_hits_by_topic_and_has_traceable_refs(self):
        ids = set()
        for subject in SUBJECTS:
            d = REAL_DIR / subject
            self.assertTrue(d.is_dir(), f"缺学科目录 {d}")
            for f in sorted(d.glob("*.json")):
                raw = json.loads(f.read_text(encoding="utf-8"))
                e = knowledge.load(subject, raw["topic"])
                self.assertEqual(e["id"], raw["id"])
                self.assertEqual(e["id"], f"kp.{subject}.{f.stem}", "文件名须与 id 一致")
                self.assertTrue(e["refs"], "出处不得为空")
                for r in e["refs"]:
                    self.assertTrue(r.get("source") and r.get("locator"), f"{e['id']} 出处不可追溯")
                self.assertTrue(e["sequence"], f"{e['id']} 无分镜序列")
                self.assertIn(e["grade"], ("G8", "G9", "H1", "H2"))
                ids.add(e["id"])
        self.assertGreaterEqual(len(ids), 8, "MVP 知识点库应有多条")

    def test_no_duplicate_topic_within_subject(self):
        for subject in SUBJECTS:
            topics = [json.loads(f.read_text(encoding="utf-8"))["topic"]
                      for f in sorted((REAL_DIR / subject).glob("*.json"))]
            self.assertEqual(len(topics), len(set(topics)), "同主题重名会让检索命中不确定")


class TestMissIsHardStop(TempLibrary):
    """防幻觉闸门：未命中必须终止，不允许模糊命中。"""

    def test_miss_raises_knowledge_not_found_with_candidates(self):
        self.write("sample", sample_entry())
        with self.assertRaises(KnowledgeNotFound) as ctx:
            knowledge.load("physics", "没入库的主题")
        err = ctx.exception
        self.assertEqual(err.candidates, ["测试知识点"])
        self.assertIn("没入库的主题", str(err))

    def test_not_found_is_a_keyerror_for_callers(self):
        self.write("sample", sample_entry())
        with self.assertRaises(KeyError):
            knowledge.load("physics", "不存在")

    def test_missing_subject_dir_yields_empty_candidates(self):
        with self.assertRaises(KnowledgeNotFound) as ctx:
            knowledge.load("chemistry", "任意")
        self.assertEqual(ctx.exception.candidates, [])

    def test_partial_match_is_not_a_hit(self):
        self.write("sample", sample_entry(topic="加速度与v-t图像"))
        with self.assertRaises(KnowledgeNotFound):
            knowledge.load("physics", "加速度")

    def test_lookup_is_case_sensitive_on_ascii_alias(self):
        self.write("sample", sample_entry(aliases=["Accel"]))
        with self.assertRaises(KnowledgeNotFound):
            knowledge.load("physics", "accel")


class TestBadDataRejected(TempLibrary):
    def test_ref_missing_locator_rejected(self):
        self.write("sample", sample_entry(refs=[{"source": "只有出处没有页码"}]))
        with self.assertRaises(ValueError) as ctx:
            knowledge.load("physics", "测试知识点")
        self.assertIn("source", str(ctx.exception))

    def test_ref_missing_source_rejected(self):
        self.write("sample", sample_entry(refs=[{"locator": "第 2 章"}]))
        with self.assertRaises(ValueError):
            knowledge.load("physics", "测试知识点")

    def test_empty_refs_rejected(self):
        self.write("sample", sample_entry(refs=[]))
        with self.assertRaises(ValueError):
            knowledge.load("physics", "测试知识点")

    def test_missing_container_field_reported_as_missing(self):
        for field in ("refs", "sequence"):
            self.write(f"bad_{field}", sample_entry(**{field: []}))
            with self.assertRaises(ValueError) as ctx:
                knowledge.load("physics", "测试知识点")
            self.assertIn(field, str(ctx.exception), f"{field} 为空必须报缺字段")
            (self.root / "physics" / f"bad_{field}.json").unlink()

    def test_missing_scalar_field_never_returns_silently(self):
        """坏条目要么被 ValueError 拒绝，要么根本命中不了（KnowledgeNotFound）——
        两条路都构成闸门；唯独不能返回一个缺字段的 dict 给下游。"""
        for field in ("id", "subject", "grade", "topic"):
            self.write(f"bad_{field}", sample_entry(**{field: ""}))
            with self.assertRaises((ValueError, KnowledgeNotFound)):
                knowledge.load("physics", "测试知识点")
            (self.root / "physics" / f"bad_{field}.json").unlink()

    def test_corrupt_json_raises_valueerror(self):
        self.write_raw("broken", "{ 这不是合法 JSON ")
        with self.assertRaises(ValueError) as ctx:
            knowledge.load("physics", "测试知识点")
        self.assertIn("损坏", str(ctx.exception))

    def test_valid_entry_still_reachable_when_no_bad_files(self):
        self.write("sample", sample_entry())
        self.assertEqual(knowledge.load("physics", "测试知识点")["id"], "kp.test.sample")

    def test_non_dict_ref_should_be_rejected_cleanly_not_crash(self):
        """BUG（记录用，不改源码）：pipeline/knowledge.py:51
        refs 元素写成字符串（人或 LLM 手改 JSON 很常见）时，r.get 抛 AttributeError，
        闸门应给出可读的 ValueError 拒绝信息而不是崩溃。"""
        self.write("sample", sample_entry(refs=["人教版高中物理必修第一册 第一章 1.3"]))
        with self.assertRaises(ValueError):
            knowledge.load("physics", "测试知识点")

    def test_grade_should_filter_lookup(self):
        """BUG（记录用，不改源码）：pipeline/knowledge.py:35 load(subject, topic)
        Spec_Workflow A2 的输入是规范化 Brief（subject/grade/topic），
        当前签名不收 grade，同 topic 跨学段重复时会静默命中第一条。"""
        self.write("g8", sample_entry(id="kp.test.g8", grade="G8"))
        self.write("g9", sample_entry(id="kp.test.g9", grade="G9"))
        e = knowledge.load("physics", "测试知识点", grade="G9")
        self.assertEqual(e["grade"], "G9")


if __name__ == "__main__":
    unittest.main()
