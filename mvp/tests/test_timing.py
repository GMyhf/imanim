"""A6 时长对齐回路的富余分配（第四轮 F-4：一镜冻 5 秒不是节奏）。

评审实测（batch_v7）：一次函数镜4 尾静音 5.0s、二次函数镜4 4.7s、一次函数镜2 3.68s——
配音讲完了，画面还停在同一帧。根因不在 A3 的分镜预算（全库计划富余最长才 1.1s），
而在 `seconds = max(spoken, floor)` 这一行：实测口播比 NATURAL_CPS 的估算快 20%~25%，
差额整块堆在那一镜的结尾。这里钉死新规则：富余保留，但摊平到各镜、每镜不超过
MAX_SHOT_IDLE，实在摊不下的还给总时长（由 ±10% 的 duration 闸门如实报），
不再拿冻屏去凑目标秒数。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run  # noqa: E402
from pipeline.ir import MAX_SHOT_IDLE  # noqa: E402


class TestSpreadSurplus(unittest.TestCase):
    def test_surplus_is_spread_not_stacked(self):
        # v7 一次函数的形状：预算全压在镜0（floor 24s），口播实测三镜都只要 10s
        out = run._spread_surplus([10.0, 10.0, 10.0], [24.0, 10.5, 10.5])
        self.assertTrue(all(o - s <= MAX_SHOT_IDLE + 1e-9 for o, s in zip(out, [10.0] * 3)), out)
        self.assertLess(max(o - s for o, s in zip(out, [10.0] * 3)), 5.0)

    def test_total_is_kept_when_every_shots_deficit_fits_under_the_cap(self):
        # 每镜缺口都 ≤ MAX_SHOT_IDLE=1.5s 时，封顶不生效，富余原样保留、总时长精确回到预算
        spoken, floors = [10.0, 10.0, 10.0], [11.2, 11.2, 11.4]
        out = run._spread_surplus(spoken, floors)
        self.assertAlmostEqual(sum(out), sum(floors), places=1)

    def test_overflown_surplus_returns_to_the_film(self):
        # 预算远超实测口播：摊到上限后剩下的秒数还给总时长，不换一镜的冻屏
        spoken, floors = [10.0, 10.0], [40.0, 40.0]
        out = run._spread_surplus(spoken, floors)
        self.assertAlmostEqual(sum(out), 2 * (10.0 + MAX_SHOT_IDLE), places=2)

    def test_no_surplus_leaves_the_measured_windows_alone(self):
        spoken, floors = [12.0, 9.0], [11.0, 8.0]
        self.assertEqual(run._spread_surplus(spoken, floors), spoken)

    def test_shots_without_a_deficit_get_nothing(self):
        """按各镜自己的缺口封顶，不按总量均分——否则没缺口的镜头会被凭空塞出一个新冻屏。

        这条夹具是 ACCEL 的真实形状（physics/加速度 batch_v7）：镜0 spoken==floor（零缺口），
        其余六镜缺口 1.5~4.2s 不等。旧的"总富余 ÷ 镜数"写法会让镜0 也分到 1.5s——
        这镜子原本一帧都不冻，均分之后反而冻了，等于用修复引入新的回归。
        """
        spoken = [14.04, 10.71, 17.82, 14.48, 23.59, 14.48, 9.15]
        floors = [14.04, 12.56, 20.93, 17.02, 27.79, 17.0, 10.66]
        out = run._spread_surplus(spoken, floors)
        self.assertEqual(out[0], spoken[0], "镜0 没有缺口，不该被均分进任何富余")
        for o, s, f in zip(out, spoken, floors):
            need = max(0.0, f - s)
            self.assertAlmostEqual(o - s, min(MAX_SHOT_IDLE, need), places=2)

    def test_cap_is_per_shot_not_averaged_across_the_film(self):
        # 每镜各自的缺口各自封顶，与镜头序号或其它镜头的缺口无关（P2 可复现）
        out = run._spread_surplus([8.0, 12.0, 10.0], [9.0, 13.0, 12.0])
        self.assertEqual([round(o - s, 2) for o, s in zip(out, [8.0, 12.0, 10.0])],
                         [1.0, 1.0, 1.5])


if __name__ == "__main__":
    unittest.main()
