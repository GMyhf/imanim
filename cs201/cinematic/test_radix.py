"""分配排序片数字的独立对撞：讲义打印结果与逐趟结果表、sorted()、穷举判定树、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_radix
"""
import json
import math
import random
import unittest
from itertools import permutations
from pathlib import Path

import radixdata as R

NARR = "".join(b["narration"] for b in json.loads((Path(__file__).parent / "radix.json").read_text(encoding="utf-8"))["beats"])


class RadixTest(unittest.TestCase):
    def test_lecture_outputs(self):
        self.assertEqual(R.counting_sort(R.COUNT_DATA),
                         [1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        self.assertEqual(R.counting_sort([3, -1, 2, -1]), [-1, -1, 2, 3])
        self.assertEqual(R.counting_sort_stable(R.RECORDS, key=lambda t: t[0]),
                         [(1, 'b'), (1, 'd'), (3, 'a'), (3, 'c')])
        self.assertEqual(R.radix_sort(R.RADIX_DATA), [2, 24, 45, 66, 75, 90, 170, 802])
        self.assertEqual(R.radix_sort_counting(R.RADIX_DATA), [2, 24, 45, 66, 75, 90, 170, 802])

    def test_pass_table(self):
        """讲义 7.3 逐趟结果表 = 分桶写法每趟收集 = 计数写法每趟输出。"""
        got = [R.RADIX_DATA] + [p[2] for p in R.radix_passes(R.RADIX_DATA)]
        self.assertEqual(got, R.LECTURE_PASSES)
        arr, exp, cnt = R.RADIX_DATA, 1, [R.RADIX_DATA]
        while max(R.RADIX_DATA) // exp > 0:
            arr = R.counting_sort_by_digit(arr, exp)
            cnt.append(arr)
            exp *= 10
        self.assertEqual(cnt, R.LECTURE_PASSES)

    def test_random(self):
        rng = random.Random(201)
        for _ in range(400):
            a = [rng.randrange(0, rng.choice([10, 1000, 10**6])) for _ in range(rng.randrange(1, 40))]
            self.assertEqual(R.radix_sort(a), sorted(a))
            self.assertEqual(R.radix_sort_counting(a), sorted(a))
            self.assertEqual(R.counting_sort(a), sorted(a))
            recs = [(rng.randrange(5), i) for i in range(rng.randrange(1, 30))]
            self.assertEqual(R.counting_sort_stable(recs, key=lambda t: t[0]), sorted(recs, key=lambda t: t[0]))

    def test_stable_trace(self):
        tr = R.stable_trace()
        self.assertEqual(tr["counts"], [2, 0, 2])
        self.assertEqual(tr["prefix"], [2, 2, 4])
        self.assertEqual([(x[1], p) for x, _, p in tr["places"]], [('d', 1), ('c', 3), ('b', 0), ('a', 2)])

    def test_unstable_counterexample(self):
        lifo = R.radix_passes_lifo(R.RADIX_DATA)
        self.assertNotEqual(lifo[-1], sorted(R.RADIX_DATA))
        self.assertEqual(lifo[-1][:6], [90, 75, 66, 45, 24, 2])
        zero = R.radix_passes(R.RADIX_DATA)[2][1][0]
        self.assertEqual(zero, [2, 24, 45, 66, 75, 90])     # 百位零号桶：旁白念的六个数

    def test_decision_tree(self):
        leaves = R.decision_tree3()
        self.assertEqual(len(leaves), 6)
        self.assertEqual(len({p for _, p in leaves}), 6)
        self.assertEqual(max(len(path) for path, _ in leaves), 3)
        for vals in permutations([1, 2, 3]):              # 沿树真走一遍，必须落到正确的叶子
            v = dict(zip("abc", vals))
            for path, perm in leaves:
                if all((v[c[0]] < v[c[2]]) == res for c, res in path):
                    self.assertEqual(perm, "".join(sorted("abc", key=v.get)))
                    break
            else:
                self.fail(vals)
        self.assertLess(2 ** 2, 6)
        self.assertEqual(R.lower_bound(3), 3)
        self.assertEqual(math.factorial(8), 40320)
        self.assertEqual(R.lower_bound(8), 16)

    def test_narration_numbers(self):
        self.assertEqual(len(R.COUNT_DATA), 22)
        self.assertEqual((min(R.COUNT_DATA), max(R.COUNT_DATA)), (1, 20))
        self.assertEqual(sorted(v for v in set(R.COUNT_DATA) if R.COUNT_DATA.count(v) == 2), [4, 10])
        self.assertEqual(R.radix_ops(8, 3), 54)
        self.assertEqual(len(R.radix_passes(R.RADIX_DATA)), 3)
        self.assertEqual(32 // 8, 4)
        for w in ("二十二个数", "一到二十", "四万零三百二十", "十六次", "五十四步", "二百五十六", "四趟", "三趟", "八个数"):
            self.assertIn(w, NARR)


if __name__ == "__main__":
    unittest.main()
