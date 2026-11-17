"""分治片数字的独立对撞：讲义输出、内建 pow / math.gcd、按二进制位迭代的快速幂、暴力找公约数、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_divide
"""
import json
import math
from pathlib import Path
import random
import unittest

import dividedata as D


def pow_iter_mults(b):
    """独立实现：讲义 fast_pow 每层先平方（1 次）、奇数再乘 a（1 次），自底向上按二进制位数。"""
    return b.bit_length() + bin(b).count("1") if b else 0


def twice_calls_closed(b):
    """两次调用版的调用次数：满二叉树，深度 = 位数 + 1，节点 2^(位数+1) − 1。"""
    return 2 ** (b.bit_length() + 1) - 1


def twice_mults_closed(b):
    """两次调用版的乘法次数：第 k 层（从 0 起）有 2^k 个节点，指数 b >> k，各做 1 + 奇偶位 次乘法。"""
    return sum(2 ** k * (1 + ((b >> k) & 1)) for k in range(b.bit_length()))


def gcd_brute(a, b):
    return max(d for d in range(1, max(a, b) + 1) if a % d == 0 and b % d == 0)


def divisors_common(a, b):
    return {d for d in range(1, max(a, b) + 1) if a % d == 0 and b % d == 0}


def squares_by_subtract(w, h):
    """独立实现：每次从长边减去短边（一刀一个正方形），合并相邻同边长的。"""
    out = []
    while w and h:
        side = min(w, h)
        if out and out[-1][0] == side:
            out[-1] = (side, out[-1][1] + 1)
        else:
            out.append((side, 1))
        if w >= h:
            w -= h
        else:
            h -= w
    return out


class DivideFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(D.fast_pow(2, 10), 1024)
        self.assertEqual(D.fast_pow(3, 100, 1000000007), pow(3, 100, 1000000007))
        self.assertEqual((D.gcd(12, 18), D.lcm(4, 6)), (6, 12))

    def test_random(self):
        rng = random.Random(3248)
        for _ in range(500):
            a, b = rng.randint(0, 50), rng.randint(0, 200)
            m = rng.choice([None, 7, 1000000007])
            self.assertEqual(D.fast_pow(a, b, m), pow(a, b, m) if m else a ** b)
            self.assertEqual(D.pow_mults(b), pow_iter_mults(b))
            self.assertEqual(D.pow_calls(b), b.bit_length() + 1)
            x, y = rng.randint(1, 300), rng.randint(1, 300)
            self.assertEqual(D.gcd(x, y), math.gcd(x, y))
            self.assertEqual(D.lcm(x, y), x * y // math.gcd(x, y))
            self.assertEqual(D.squares(x, y), squares_by_subtract(x, y))
            self.assertEqual(D.squares(x, y)[-1][0], math.gcd(x, y))
            firsts, ok = D.halving(max(x, y), min(x, y))       # a ≥ b 时隔两步至少减半
            self.assertTrue(ok)
            # 余数小于 a 的一半（a ≥ b 时）
            p, q = max(x, y), min(x, y)
            self.assertLess(p % q, p / 2)
            # 正方形面积之和 = 长方形面积，且互不重叠（逐格涂色）
            tiles = D.square_tiles(max(x, y), min(x, y))
            self.assertEqual(sum(s * s for _, _, s in tiles), x * y)
        for b in range(0, 40):
            v, calls, mults = D.twice_counts(3, b)
            self.assertEqual(v, 3 ** b)
            self.assertEqual(calls, twice_calls_closed(b))
            self.assertEqual(mults, twice_mults_closed(b))

    def test_tiles_cover(self):
        w, h = D.RECT
        grid = [[0] * w for _ in range(h)]
        for x, y, s in D.square_tiles(w, h):
            for i in range(x, x + s):
                for j in range(y, y + s):
                    grid[j][i] += 1
        self.assertTrue(all(c == 1 for row in grid for c in row))

    def test_film_numbers(self):
        v, lv = D.pow_trace(2, 10)
        self.assertEqual(v, 1024)
        self.assertEqual([x["b"] for x in lv], [10, 5, 2, 1, 0])
        self.assertEqual([(x["half"], x["res"]) for x in lv[:-1]][::-1], [(1, 2), (2, 4), (4, 32), (32, 1024)])
        self.assertEqual([x["odd"] for x in lv], [False, True, False, True, False])
        self.assertEqual(D.pow_mults(10), 6)
        self.assertEqual(D.naive_pow(2, 10), (1024, 10))
        self.assertEqual(bin(10)[2:], "1010")
        self.assertEqual(D.BIG_B.bit_length(), 30)
        self.assertEqual(D.pow_mults(D.BIG_B), 43)
        self.assertLessEqual(D.pow_mults(D.BIG_B), 2 * 30)
        self.assertEqual(D.twice_counts(2, 10), (1024, 31, 25))
        self.assertEqual(D.gcd_trace(12, 18), [(12, 18), (18, 12), (12, 6), (6, 0)])
        self.assertEqual(D.squares(*D.RECT), [(27, 2), (21, 1), (6, 3), (3, 2)])
        self.assertEqual(gcd_brute(*D.RECT), 3)
        self.assertEqual(divisors_common(75, 27), divisors_common(27, 75 % 27))
        self.assertEqual(D.halving(*D.RECT)[0], [75, 27, 21, 6, 3])

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("divide.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("乘十次二", beats["naive"])
        self.assertIn("二的十次方，是二的五次方的平方", beats["naive"])
        self.assertIn("二的五次方，是二的二次方的平方，再乘一个二", beats["naive"])
        self.assertIn("指数十、五、二、一、零", beats["chain"])
        for s in ("一的平方乘二，得二", "二的平方，得四", "四的平方乘二，得三十二", "三十二的平方，得一千零二十四",
                  "一共六次乘法，连乘要十次"):
            self.assertIn(s, beats["chain"])
        self.assertIn("十是一零一零", beats["binary"])
        self.assertIn("十亿只有三十位，四十三次乘法", beats["binary"])
        self.assertIn("调用三十一次，乘二十五次", beats["twice"])
        self.assertIn("十二和十八，换成十八和十二，再到十二和六、六和零，答案是六", beats["gcd"])
        for s in ("七十五乘二十七", "两个边长二十七的正方形，剩下二十七乘二十一", "切一个二十一的，剩下二十一乘六",
                  "切三个六的，剩下六乘三", "再切两个三的，正好切完", "最后的边长三"):
            self.assertIn(s, beats["rect"])
        self.assertIn("七十五、二十一、三", beats["halving"])


if __name__ == "__main__":
    unittest.main()
