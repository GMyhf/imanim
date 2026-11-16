"""树状数组片数字的独立对撞：讲义附录打印、暴力前缀和、管辖区间定义、O(n²) 数顺序对、旁白数字。

用法（cwd = cs201/cinematic）：python -m unittest test_bit
"""
import json
from pathlib import Path
import random
import unittest

import bitdata as D

NARR = {b["id"]: b["narration"] for b in json.loads((Path(__file__).parent / "bit.json").read_text("utf-8"))["beats"]}


class BITFacts(unittest.TestCase):
    def test_lecture_output(self):
        # 讲义附录 A 的 Output 第一行
        self.assertEqual(D.C, [int(x) for x in "0 1 3 3 10 5 11 7 36 9 19 11 42 13 27 15 136".split()])
        self.assertEqual(D.bit_sum(D.C, 5), 15)

    def test_cover_definition(self):
        for i in range(1, D.N + 1):
            lo, hi = D.cover(i)
            self.assertEqual(D.C[i], sum(D.A[lo - 1:hi]))
            self.assertEqual(hi - lo + 1, D.lowbit(i))
            self.assertEqual(D.lowbit(i) & (D.lowbit(i) - 1), 0)     # 2 的幂

    def test_query_tiles(self):
        for x in range(1, 65):
            path = D.query_path(x)
            segs = sorted(D.cover(j) for j in path)
            self.assertEqual(segs[0][0], 1)
            self.assertEqual(segs[-1][1], x)
            for a, b in zip(segs, segs[1:]):
                self.assertEqual(a[1] + 1, b[0])                      # 不重叠、不留缝
            self.assertEqual(len(path), bin(x).count("1"))
        self.assertEqual(D.Q_PATH, [14, 12, 8])
        self.assertEqual(D.Q_PARTS, [27, 42, 36])
        self.assertEqual(D.Q_SUM, sum(range(1, 15)))

    def test_update_hits_exactly_covering(self):
        for n in (16, 37):
            for i in range(1, n + 1):
                want = [j for j in range(1, n + 1) if D.cover(j)[0] <= i <= j]
                self.assertEqual(D.update_path(i, n), want)
        self.assertEqual(D.U_PATH, [6, 8, 16])
        self.assertEqual(D.U2_PATH, [9, 10, 12, 16])
        self.assertEqual([D.C_AFTER[j] - D.C[j] for j in D.U_PATH], [3, 3, 3])

    def test_random_against_brute(self):
        rng = random.Random(1)
        for _ in range(100):
            n = rng.randint(1, 40)
            a = [rng.randint(-50, 50) for _ in range(n)]
            t = D.construct(a, n)
            for _ in range(30):
                if rng.random() < 0.5:
                    i, v = rng.randint(1, n), rng.randint(-9, 9)
                    a[i - 1] += v
                    D.bit_update(t, i, v)
                x = rng.randint(0, n)
                self.assertEqual(D.bit_sum(t, x), sum(a[:x]))

    def test_steps_bound(self):
        for x in range(1, 2000):
            self.assertLessEqual(len(D.query_path(x)), x.bit_length())
            self.assertLessEqual(len(D.update_path(x, 2000)), 2000 .bit_length())
        self.assertEqual(D.BIG_STEPS, 20)
        self.assertEqual(D.lowbit(0), 0)                               # 下标从 0 开始会原地打转

    def test_lowbit_rows(self):
        self.assertEqual(D.LB_ROWS[0][1], "00001100")
        self.assertEqual(D.LB_ROWS[2][1], "11110100")
        self.assertEqual(int(D.LB_ROWS[3][1], 2), 4)
        self.assertEqual(D.LB_MORE, [(6, 2), (7, 1), (8, 8)])

    def test_ants(self):
        def brute(v):
            return sum(1 for i in range(len(v)) for j in range(i + 1, len(v)) if v[i] < v[j])
        self.assertEqual(D.ANT_ANS, 7)
        self.assertEqual(D.ant_scan([1, 5, 5, 7, 6])[0], 8)             # 讲义样例 2
        self.assertEqual(len(D.ANT_PAIRS), 7)
        self.assertEqual([s["got"] for s in D.ANT_STEPS], [0, 1, 2, 2, 2])
        self.assertEqual([D.RANK[x] for x in D.ANTS], [1, 2, 5, 4, 3])
        rng = random.Random(3)
        for _ in range(200):
            v = [rng.randint(0, 8) for _ in range(rng.randint(1, 12))]
            self.assertEqual(D.ant_scan(v)[0], brute(v))

    def test_narration_numbers(self):
        self.assertIn("二十七加四十二加三十六，等于一百零五", NARR["query"])
        self.assertIn("十四有三个一", NARR["query"])
        self.assertIn("十四个前缀和", NARR["dilemma"])
        self.assertEqual(D.PREFIX_TOUCH, 14)
        self.assertIn("值是四", NARR["lowbit"])
        self.assertIn("九、十、十二、十六", NARR["update"])
        self.assertIn("最多二十步", NARR["cost"])
        self.assertIn("一共七次赶超", NARR["scan"])
        self.assertIn("一排第一，五排第二，六第三，七第四，十第五", NARR["ants"])
        self.assertIn("零加一加二加二加二", NARR["scan"])


if __name__ == "__main__":
    unittest.main()
