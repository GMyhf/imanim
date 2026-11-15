"""动态规划入门片数字的独立对撞：讲义输出、整张 dp 表、路径枚举、随机对拍、硬币反例、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_dpintro
"""
import json
from pathlib import Path
import random
import unittest

import dpintrodata as D


def recursive_odd(tri):
    """独立方法：递归遍历所有路径（不用 itertools），收集奇数和的最大值。"""
    best = [-1]

    def go(i, j, s):
        s += tri[i][j]
        if i == len(tri) - 1:
            if s % 2:
                best[0] = max(best[0], s)
            return
        go(i + 1, j, s)
        go(i + 1, j + 1, s)
    go(0, 0, 0)
    return best[0]


def min_coins_brute(coins, amount):
    """枚举每种面额的枚数。"""
    best = None
    for a in range(amount // coins[0] + 1):
        for b in range(amount // coins[1] + 1):
            for c in range(amount // coins[2] + 1):
                if a * coins[0] + b * coins[1] + c * coins[2] == amount:
                    k = a + b + c
                    best = k if best is None else min(best, k)
    return best


class DPIntroFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(D.brute_odd(D.TRI), 17)
        self.assertEqual(D.naive_odd(D.TRI), -1)
        self.assertEqual(D.fixed_odd(D.TRI), 17)

    def test_tables_match_course_functions(self):
        rnd = random.Random(3)
        for _ in range(300):
            n = rnd.randint(2, 7)
            t = [[rnd.randint(0, 9) for _ in range(i + 1)] for i in range(n)]
            nt = D.naive_table(t)
            odd = [v for v in nt[-1] if v % 2]
            self.assertEqual(max(odd) if odd else -1, D.naive_odd(t))
            ft = D.fixed_table(t)
            best = max(c[1] for c in ft[-1])
            self.assertEqual(best if best > D.NEG else -1, D.fixed_odd(t))
            self.assertEqual(D.fixed_odd(t), recursive_odd(t))

    def test_tri_tables(self):
        nt = D.naive_table(D.TRI)
        self.assertEqual(nt[-1], [20, 22, 24, 22])                           # 讲义：全是偶数
        self.assertEqual((nt[2][0], nt[2][1]), (13, 18))                      # 4 的两个前驱
        ft = D.fixed_table(D.TRI)
        self.assertEqual(ft[3][1][1], 17)                                     # 第 4 行的 4，奇数栏 17
        self.assertEqual(max(c[1] for c in ft[3]), 17)

    def test_paths(self):
        ps = D.all_paths(D.TRI)
        self.assertEqual(len(ps), 8)
        self.assertEqual(sorted(s for _, s in ps), sorted([20, 17, 20, 18, 22, 20, 24, 22]))  # 讲义表格
        odd = [(c, s) for c, s in ps if s % 2]
        self.assertEqual(len(odd), 1)
        self.assertEqual([D.TRI[i][j] for i, j in odd[0][0]], [6, 7, 0, 4])

    def test_duel(self):
        fx, nv = D.duel()
        self.assertEqual(len(fx), 2000)
        self.assertTrue(all(fx))
        self.assertEqual(nv.count(False), 298)

    def test_coins(self):
        self.assertEqual(D.greedy_coins(), [4, 1, 1])
        self.assertEqual(D.dp_coins(), [3, 3])
        self.assertEqual(len(D.dp_coins()), min_coins_brute(D.COINS, D.AMOUNT))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("dpintro.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("三枚：四加一加一", beats["title"])
        self.assertIn("两枚：三加三", beats["title"])
        self.assertIn("一共八条路径", beats["paths"])
        self.assertIn("六、七、零、四，和为十七", beats["paths"])
        self.assertIn("二十、二十二、二十四、二十二", beats["naive"])
        self.assertIn("十三是奇数，十八是偶数", beats["where"])
        self.assertIn("答错了二百九十八组", beats["duel"])
        self.assertIn("两千个三角形", beats["duel"])


if __name__ == "__main__":
    unittest.main()
