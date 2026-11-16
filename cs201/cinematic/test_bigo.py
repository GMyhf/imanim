"""渐进分析片数字的独立对撞：赋值计数对闭式公式、各项占比、大 O 起点、Θ 夹逼、顺序检索平均次数、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_bigo
"""
import json
import math
import random
import unittest
from fractions import Fraction
from pathlib import Path

import bigodata as B


class BigOTest(unittest.TestCase):
    def test_assignment_counts(self):
        rng = random.Random(1)
        for n in [1, 2, 3, 10, 57, 1000]:
            a = [rng.randint(-9, 9) for _ in range(n)]
            out_n, c_n = B.prefix_naive(a)
            out_r, c_r = B.prefix_running(a)
            self.assertEqual(out_n, out_r)                                  # 两份代码输出一样
            self.assertEqual(out_r, [sum(a[:i + 1]) for i in range(n)])
            self.assertEqual(c_n, 1 + 3 * n + n * (n - 1))                  # 讲义公式
            self.assertEqual(c_r, 2 + 2 * n)
            self.assertEqual(B.sum_array(a), (sum(a), 2 + 2 * n))
            self.assertEqual(Fraction(c_n, c_r), Fraction(n + 1, 2))        # 比值 (n+1)/2
        self.assertEqual(B.prefix_naive(list(range(10)))[1], 121)
        self.assertEqual(B.prefix_running(list(range(10)))[1], 22)
        self.assertEqual(B.prefix_naive(list(range(1000)))[1], 1_002_001)
        self.assertEqual(B.prefix_running(list(range(1000)))[1], 2002)

    def test_window(self):
        for n in range(5, 40):
            a = list(range(n))
            sums, total, inner = B.window5(a)
            self.assertEqual(sums, [sum(a[i - 4:i + 1]) for i in range(4, n)])
            self.assertEqual(total, 1 + 11 * (n - 4))
            self.assertEqual(inner, 8 * (n - 4))                            # 讲义只数内层：8(n−4)
        self.assertEqual(B.window5(list(range(10)))[1], 67)

    def test_lower_terms(self):
        s1, s10, s100, s1000 = (B.f_shares(n) for n in (1, 10, 100, 1000))
        self.assertGreater(s1["1000"], 0.9)                                 # n=1：常数占九成
        self.assertAlmostEqual(s10["100n"], s10["1000"])                    # n=10：100n 与 1000 打平
        self.assertAlmostEqual(s100["n2"], s100["100n"])                    # n=100：n² 追上 100n
        self.assertGreater(s1000["n2"], 0.9)                                # n=1000：n² 九成以上

    def test_bigo_N(self):
        N = B.bigo_first_N()
        self.assertEqual(N, 110)
        f = lambda n: n * n + 100 * n + math.log10(n) + 1000  # noqa: E731
        self.assertGreater(f(N - 1), 2 * (N - 1) ** 2)
        self.assertTrue(all(f(n) <= 2 * n * n for n in range(N, 5000)))
        self.assertTrue(B.omega_holds(1, 5000))

    def test_theta(self):
        self.assertEqual(B.theta_first_N(), 10)                             # 讲义：c1=100, c2=105, N=10
        self.assertTrue(all(100 * n * n <= B.theta_f(n) <= 105 * n * n for n in range(11, 20000)))
        self.assertFalse(B.theta_f(10) <= 105 * 100)

    def test_search_cases(self):
        for n in (3, 8, 50, 1000):
            self.assertEqual(B.avg_uniform(n), Fraction(n + 1, 2))
            self.assertEqual(sum(B.skew_probs(n)), 1)
            self.assertEqual(B.avg_skew(n), 1 + Fraction(n + 3, 8))         # 讲义推导的闭式
        self.assertEqual(B.avg_skew(8), Fraction(19, 8))
        r = B.avg_uniform(1000) / B.avg_skew(1000)
        self.assertTrue(3.9 < r < 4)                                         # 「快了将近四倍」

    def test_growth(self):
        sec, years = B.time_at(1000)
        self.assertEqual((sec["n"], sec["n2"], sec["n3"]), (0.001, 1.0, 1000.0))
        self.assertAlmostEqual(sec["n3"] / 60, 16.67, places=2)
        self.assertEqual(math.floor(math.log10(years)), 287)
        self.assertEqual(round(years / 10 ** 287, 1), 3.4)
        self.assertEqual(B.growth_row(16), {"1": 1, "log": 4, "n": 16, "nlog": 64, "n2": 256, "2n": 65536})

    def test_phonebook(self):
        scan, per, slots = B.phonebook(1000)
        self.assertEqual(scan, Fraction(1001, 2))
        self.assertEqual((per, slots), (1, 1000))

    def test_narration_numbers(self):
        script = json.loads((Path(__file__).parent / "bigo.json").read_text(encoding="utf-8"))
        t = {b["id"]: b["narration"] for b in script["beats"]}
        self.assertIn("一百二十一次，一个是二十二次", t["curves"])
        self.assertIn("一百万两千零一次", t["curves"])
        self.assertIn("两千零二次", t["curves"])
        self.assertIn("一加三倍的 n，再加 n 乘以 n 减一", t["count"])
        self.assertIn("二加二倍的 n", t["count"])
        self.assertIn("n 大于十以后", t["theta"])
        self.assertIn("一百 n 平方和一百零五 n 平方", t["theta"])
        self.assertIn("六十七次赋值", t["nest"])
        self.assertIn("只多十一次", t["nest"])
        self.assertIn("n 加一除以二", t["cases"])
        self.assertIn("一加八分之 n 加三", t["cases"])
        self.assertIn("十六分多钟", t["growth"])
        self.assertIn("三乘十的二百八十七次方年", t["growth"])
        self.assertIn("五百多次", t["tradeoff"])
        self.assertIn("多占一千个格子", t["tradeoff"])


if __name__ == "__main__":
    unittest.main()
