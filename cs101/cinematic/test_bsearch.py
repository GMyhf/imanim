"""二分答案片数字的独立对撞：讲义输出、暴力枚举（组合移石 / 枚举切分点）、判定单调性、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_bsearch
"""
from itertools import combinations
import json
from pathlib import Path
import random
import unittest

import bsearchdata as S


def brute_river(L, m, rocks):
    """枚举所有移走 ≤ m 块的方案，取相邻最小距离的最大值。"""
    best = 0
    rocks = sorted(rocks)
    for k in range(m + 1):
        for gone in combinations(range(len(rocks)), k):
            keep = [0] + [r for i, r in enumerate(rocks) if i not in gone] + [L]
            best = max(best, min(b - a for a, b in zip(keep, keep[1:])))
    return best


def brute_monthly(costs, m):
    """枚举所有切分（≤ m 段），取每段和最大值的最小值。"""
    n, best = len(costs), sum(costs)
    for k in range(min(m, n)):
        for cuts in combinations(range(1, n), k):
            b = [0, *cuts, n]
            best = min(best, max(sum(costs[b[i]:b[i + 1]]) for i in range(len(b) - 1)))
    return best


class BSearchFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(S.river_rounds()[0], 4)
        self.assertEqual(S.monthly_rounds()[0], 500)

    def test_against_brute(self):
        self.assertEqual(brute_river(*S.RIVER), 4)
        self.assertEqual(brute_monthly(S.COSTS, S.M_GROUPS), 500)
        rng = random.Random(3)
        for _ in range(150):
            L = rng.randint(5, 40)
            rocks = rng.sample(range(1, L), rng.randint(1, min(6, L - 1)))
            m = rng.randint(0, len(rocks))
            self.assertEqual(S.river_rounds(L, m, rocks)[0], brute_river(L, m, rocks))
            costs = [rng.randint(1, 50) for _ in range(rng.randint(1, 7))]
            mm = rng.randint(1, len(costs))
            self.assertEqual(S.monthly_rounds(costs, mm)[0], brute_monthly(costs, mm))

    def test_monotone(self):
        ok = [S.river_feasible_log(g)[0] for g in range(S.RIVER[0] + 1)]
        self.assertEqual(ok, [True] * 5 + [False] * 21)                  # 0..4 可行，5 起不可行

    def test_feasible_four(self):
        ok, log = S.river_feasible_log(4)
        self.assertTrue(ok)
        self.assertEqual([(s, a) for s, a, _ in log],
                         [(2, "rm"), (11, "keep"), (14, "rm"), (17, "keep"), (21, "keep"), (25, "keep")])

    def test_rounds(self):
        ans, rounds = S.river_rounds()
        self.assertEqual([(r[2], r[3]) for r in rounds], [(13, False), (6, False), (3, True), (4, True), (5, False)])
        ans2, r2 = S.monthly_rounds()
        self.assertEqual((r2[0][0], r2[0][1], len(r2)), (500, 1901, 11))
        self.assertEqual(len(S.monthly_groups(500)), 5)

    def test_dead_loop(self):
        trail = S.floor_mid_loop(4, 5)
        self.assertEqual(trail, [(4, 5, 4, True)] * 4)                  # 区间纹丝不动

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("bsearch.json").read_text(encoding="utf-8"))["beats"])
        for s in ("mid 等于十三，不可行", "mid 等于六，不可行", "mid 等于三，可行", "mid 等于四，可行",
                  "mid 等于五，不可行", "答案是四", "一千九百零一", "十一轮之后，答案是五百", "只移走两块"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
