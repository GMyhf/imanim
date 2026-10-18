"""A1.5 先修规划器测试。

这个模块此前**从未能被 import**（prereq.py 顶部导入了一个 ir 里不存在的名字），而全库没有一条
用例 import 它，所以坏了很久没人发现。本文件的第一价值就是这条 import 本身；往下的用例钉的是
"两处各写一把尺子"那一族：先修段的秒数必须与 review/storyboard 用同一个语速口径。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import prereq as Q  # noqa: E402
from pipeline.ir import MIN_SHOT_SECONDS, NATURAL_CPS  # noqa: E402

LONG_NARRATION = "加速度刻画速度变化的快慢，定义式是速度变化量除以发生这段变化所用的时间间隔，" \
                 "它是矢量，方向与速度变化量的方向相同，单位是米每二次方秒。"


def _fixture(narration: str = LONG_NARRATION, seconds: float = 12.0):
    """一条 host（牛顿第二定律）+ 一条库内先修（加速度）的两节点夹具。"""
    lib = Q.Library()
    for kid, topic in (("kp.physics.newton_second", "牛顿第二定律"), ("kp.physics.acceleration", "加速度")):
        lib.entries[kid] = {"id": kid, "topic": topic, "aliases": [], "grade": "H1",
                            "refs": [{"source": "合成夹具（非教材）", "locator": "prereq-test"}],
                            "prior": [], "forbidden": [],
                            "sequence": [{"title": topic, "seconds": seconds, "narration": narration,
                                          "visuals": [{"kind": "callout", "props": {"text": topic}}]}]}
        lib.names.append((Q._norm(topic), kid, topic))
    child = Q.Node(kind="kp", key="kp.physics.acceleration", label="加速度",
                   kp_id="kp.physics.acceleration", in_library=True, verified=True,
                   origin="declared_edge", via="kp.physics.newton_second", depth=1,
                   citations=[{"source": "合成夹具（非教材）", "locator": "prereq-test"}])
    return lib, {"kp.physics.newton_second": [child], "kp.physics.acceleration": []}


class TestRecallPricing(unittest.TestCase):
    """回顾段（整段复用库内镜头）的秒数按内容语速算。"""

    def test_recall_seconds_use_the_content_rate(self):
        lib, children = _fixture()
        plan = Q.plan_prerequisites("kp.physics.newton_second", lib, children, target_seconds=120)
        recall = [d for d in plan.decisions if d.mode == Q.MODE_RECALL]
        self.assertEqual(len(recall), 1, f"夹具应当产出一段回顾，实际 {[(d.node.label, d.mode) for d in plan.decisions]}")
        need = len(LONG_NARRATION) / NATURAL_CPS
        self.assertGreaterEqual(recall[0].seconds, need,
                                f"回顾段按 {recall[0].seconds}s 装箱，可这段口播 {len(LONG_NARRATION)} 字"
                                f"要 {need:.1f}s 才讲得完——语速口径又分叉了")

    def test_short_narration_still_gets_a_legal_shot(self):
        lib, children = _fixture(narration="一句话", seconds=3.0)
        plan = Q.plan_prerequisites("kp.physics.newton_second", lib, children, target_seconds=120)
        recall = [d for d in plan.decisions if d.mode == Q.MODE_RECALL]
        self.assertTrue(recall, "短段落也应进回顾（只是秒数由下限决定）")
        self.assertGreaterEqual(recall[0].seconds, MIN_SHOT_SECONDS)


class TestNamingPricing(unittest.TestCase):
    """点名段的秒数走 ir 里那一条尺子，与 storyboard 共用一个函数。"""

    def test_name_seconds_equals_the_shared_ruler(self):
        labels = ["加速度", "速度", "位移"]
        self.assertAlmostEqual(Q._name_seconds(labels),
                               Q.naming_shot_seconds(Q.naming_narration(labels), Q.NAME_MIN_SECONDS))

    def test_name_bucket_is_priced_before_the_recall_bucket_spends_it(self):
        lib, children = _fixture()
        plan = Q.plan_prerequisites("kp.physics.newton_second", lib, children, target_seconds=120)
        self.assertLessEqual(plan.preq_seconds, 120 * Q.PREQ_BUDGET_RATIO + 1e-6,
                             "先修总时长越过了预算上限：装箱没守住两桶的份额")


if __name__ == "__main__":
    unittest.main()
