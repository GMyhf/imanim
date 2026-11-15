"""区间贪心片数字的独立对撞：讲义输出、小规模暴力枚举、旁白数字。

用法（cwd = mvp/cs101/cinematic）：python -m unittest test_interval
"""
from itertools import combinations
import json
from pathlib import Path
import random
import unittest

import intervaldata as I


def brute_keep(iv):
    """最多不相交（端点相接不算重叠）：枚举子集。"""
    for r in range(len(iv), 0, -1):
        for c in combinations(iv, r):
            s = sorted(c, key=lambda x: x[0])
            if all(s[k + 1][0] >= s[k][1] for k in range(len(s) - 1)):
                return r
    return 0


def brute_arrows(iv):
    """最少点数（闭区间）：候选点取所有端点，枚举点集。"""
    cands = sorted({v for a in iv for v in a})
    for r in range(1, len(iv) + 1):
        for pts in combinations(cands, r):
            if all(any(lo <= p <= hi for p in pts) for lo, hi in iv):
                return r
    return 0


def brute_overlap(iv):
    """闭区间的最大同时重叠数：逐个整点数。"""
    return max(sum(lo <= x <= hi for lo, hi in iv) for x in range(min(a for a, _ in iv), max(b for _, b in iv) + 1))


def covered_points(iv):
    return {x for lo, hi in iv for x in range(lo, hi + 1)}


class IntervalFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(I.merge(I.MERGE_EX), [[1, 6], [8, 10], [15, 18]])
        self.assertEqual(I.merge([[1, 4], [4, 5]]), [[1, 5]])
        self.assertEqual(I.erase_overlap_intervals(I.KEEP_EX), 1)
        self.assertEqual(I.find_min_arrow_shots(I.ARROW_EX), 2)
        self.assertEqual(I.min_groups(I.GROUP_EX), 3)
        self.assertEqual(I.min_groups_diff(I.GROUP_EX), 3)

    def test_traces_match_course(self):
        s, ev, out = I.merge_trace()
        self.assertEqual(out, I.merge(I.MERGE_EX))
        self.assertEqual([e[0] for e in ev], ["start", "extend", "new", "new"])
        self.assertEqual(I.merge(I.MAX_PITFALL), [[1, 10]])
        self.assertEqual(I.merge_no_max(I.MAX_PITFALL), [[1, 3]])          # 不写 max：10 被缩成 3
        s, flags = I.greedy_keep(I.KEEP_EX, key=lambda x: x[1])
        self.assertEqual(len(I.KEEP_EX) - sum(flags), I.erase_overlap_intervals(I.KEEP_EX))
        s, hit, shots = I.arrow_trace()
        self.assertEqual((len(shots), shots), (2, [6, 12]))
        for (lo, hi), p in zip(s, hit):
            self.assertTrue(lo <= p <= hi)
        s, lanes, states = I.group_trace()
        self.assertEqual(max(lanes) + 1, I.min_groups(I.GROUP_EX))
        for g in set(lanes):                                               # 每组内互不重叠
            mem = sorted(iv for iv, l in zip(s, lanes) if l == g)
            self.assertTrue(all(mem[k + 1][0] > mem[k][1] for k in range(len(mem) - 1)))
        self.assertEqual(max(c for _, c in I.overlap_profile()), 3)

    def test_counterexamples(self):
        for ex in (I.BAD_LEFT, I.BAD_LEN):
            self.assertEqual(brute_keep(ex), 2)
            self.assertEqual(sum(I.greedy_keep(ex, key=lambda x: x[1])[1]), 2)
        self.assertEqual(sum(I.greedy_keep(I.BAD_LEFT, key=lambda x: x[0])[1]), 1)
        self.assertEqual(sum(I.greedy_keep(I.BAD_LEN, key=lambda x: x[1] - x[0])[1]), 1)

    def test_random_against_brute(self):
        rng = random.Random(10)
        for _ in range(300):
            n = rng.randint(1, 7)
            iv = []
            for _ in range(n):
                a = rng.randint(0, 12)
                iv.append([a, a + rng.randint(1, 6)])                      # start < end（LC 435 的前提）
            self.assertEqual(len(iv) - I.erase_overlap_intervals(iv), brute_keep(iv))
            self.assertEqual(I.find_min_arrow_shots(iv), brute_arrows(iv))
            self.assertEqual(I.min_groups(iv), brute_overlap(iv))
            self.assertEqual(I.min_groups_diff(iv), brute_overlap(iv))
            m = I.merge(iv)
            self.assertEqual(covered_points(m), covered_points(iv))
            self.assertTrue(all(m[k + 1][0] > m[k][1] for k in range(len(m) - 1)))

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("interval.json").read_text(encoding="utf-8"))["beats"])
        for s in ("四个区间，合并成三段", "会把十缩成三", "四个区间保留三个，移除一个", "四个气球，两支箭",
                  "四个区间，需要三组", "只能留一个，可明明能留两个"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
