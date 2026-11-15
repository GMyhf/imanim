"""0/1 背包片数字的独立对撞：讲义输出、暴力枚举子集、正序/倒序一轮的结果、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_knap
"""
from itertools import combinations, product
import json
from pathlib import Path
import random
import unittest

import knapdata as K


def brute01(ws, vs, cap):
    best = 0
    for r in range(len(ws) + 1):
        for comb in combinations(range(len(ws)), r):
            if sum(ws[i] for i in comb) <= cap:
                best = max(best, sum(vs[i] for i in comb))
    return best


def brute_unbounded(ws, vs, cap):
    best = 0
    for counts in product(*[range(cap // w + 1) for w in ws]):
        if sum(k * w for k, w in zip(counts, ws)) <= cap:
            best = max(best, sum(k * v for k, v in zip(counts, vs)))
    return best


class KnapFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(K.knapsack_2d()[-1][-1], 3500)
        self.assertEqual(K.knapsack_1d(), 3500)
        self.assertEqual(K.unbounded_knapsack(), 6000)
        self.assertEqual(K.caiyao(70, [(71, 100), (69, 1), (1, 2)]), 3)

    def test_table(self):
        self.assertEqual(K.knapsack_2d(), [[0, 0, 0, 0, 0],
                                           [0, 1500, 1500, 1500, 1500],
                                           [0, 1500, 1500, 1500, 3000],
                                           [0, 1500, 1500, 2000, 3500]])
        last = [x for x in K.fill_log() if x[0] == 3 and x[1] == 4][0]
        self.assertEqual(last[2:], (3000, 3500, 3500))                    # 不拿 3000，拿 1500+2000

    def test_backtrack(self):
        self.assertEqual(K.chosen(), [1, 3])
        self.assertEqual(sum(K.WEIGHTS[i - 1] for i in K.chosen()), 4)
        self.assertEqual(sum(K.VALUES[i - 1] for i in K.chosen()), 3500)

    def test_random_against_brute(self):
        rng = random.Random(11)
        for _ in range(300):
            n = rng.randint(1, 5)
            ws = [rng.randint(1, 6) for _ in range(n)]
            vs = [rng.randint(1, 20) for _ in range(n)]
            cap = rng.randint(0, 12)
            self.assertEqual(K.knapsack_2d(ws, vs, cap)[-1][-1], brute01(ws, vs, cap))
            self.assertEqual(K.knapsack_1d(ws, vs, cap), brute01(ws, vs, cap))
            self.assertEqual(K.unbounded_knapsack(ws, vs, cap), brute_unbounded(ws, vs, cap))
            ch = K.chosen(ws, vs, cap)
            self.assertLessEqual(sum(ws[i - 1] for i in ch), cap)
            self.assertEqual(sum(vs[i - 1] for i in ch), brute01(ws, vs, cap))

    def test_one_pass(self):
        back, _ = K.one_pass(1, 1500, [0] * 5, forward=False)
        fwd, log = K.one_pass(1, 1500, [0] * 5, forward=True)
        self.assertEqual(back, [0, 1500, 1500, 1500, 1500])                 # 倒序：只拿一次
        self.assertEqual(fwd, [0, 1500, 3000, 4500, 6000])                  # 正序：重复拿
        self.assertEqual(log[1], (2, 0, 1500, 3000))                        # 容量二读到本轮的一千五

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("knap.json").read_text(encoding="utf-8"))["beats"])
        for s in ("一千五加两千，等于三千五", "第一件和第三件", "于是变成三千", "容量四变成六千",
                  "零一背包是三千五，完全背包是六千"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
