"""购物片数字的独立对撞：题面样例、讲义三版代码、贪心逐步 reach、暴力枚举硬币组合、旁白数字。

独立实现不调用 shoppingdata 的 covers / brute_*：用整数位运算做子集和（bits |= bits << c），按枚数逐层枚举多重组合。
用法（cwd = cs101/cinematic）：python -m unittest test_shopping
"""
import itertools
import json
from pathlib import Path
import random
import unittest

import shoppingdata as D


def bits_cover(bag, x):
    """独立方法：子集和用位运算，第 v 位为 1 表示能凑出 v；检查 1..x 全为 1。"""
    bits = 1
    for c in bag:
        bits |= bits << c
    full = (1 << (x + 1)) - 2
    return bits & full == full


def brute_min_bits(x, coins):
    """独立方法：枚数从小到大，枚举该枚数的全部多重组合。凑不出一时直接判无解（每枚面值都 ≥ 2）。"""
    if min(coins) > 1:
        return -1
    for k in itertools.count(1):
        if any(bits_cover(b, x) for b in itertools.combinations_with_replacement(sorted(set(coins)), k)):
            return k


def all_lecture(x, coins):
    s = D.fmt_in(x, coins)
    return [int(D.run_io(f, s)) for f in (D.solve_scan, D.solve_bisect, D.solve_w16)]


class ShoppingFacts(unittest.TestCase):
    def test_sample(self):
        for f in (D.solve_scan, D.solve_bisect, D.solve_w16):
            self.assertEqual(D.run_io(f, D.SAMPLE_IN), D.SAMPLE_OUT)
        self.assertEqual(brute_min_bits(D.X, D.COINS), int(D.SAMPLE_OUT))
        self.assertEqual(D.SAMPLE_IN, D.fmt_in(D.X, D.COINS))
        self.assertEqual(all_lecture(*D.NO_ONE), [-1, -1, -1])

    def test_w16_code_text(self):
        """画面上展示的十行与讲义函数体逐字一致。"""
        import inspect
        body = inspect.getsource(D.solve_w16).split("\n")[1:]
        self.assertEqual("\n".join(ln[4:] for ln in body).strip(), D.W16_CODE)
        self.assertEqual(len(D.W16_CODE.split("\n")), 10)

    def test_trace(self):
        tr = D.greedy_trace(D.X, D.COINS)
        self.assertEqual([c for _, _, c, _ in tr], [1, 2, 2, 5, 10])
        self.assertEqual([r for *_, r in tr], [1, 3, 5, 10, 20])
        self.assertEqual([r + 1 for r, *_ in tr], [1, 2, 4, 6, 11])               # 每步的上限 reach+1
        for r, usable, c, r2 in tr:
            self.assertEqual(c, max(v for v in D.COINS if v <= r + 1))
            self.assertEqual(r2, r + c)
        bag = []
        for r, _, c, r2 in tr:                                                   # 每步之后恰好覆盖到 r2
            bag.append(c)
            self.assertTrue(bits_cover(bag, r2))
            self.assertFalse(bits_cover(bag, r2 + 1))
        self.assertIsNone(D.greedy_trace(*D.NO_ONE))

    def test_gap(self):
        """面值大于 reach+1 就断档：reach+1 凑不出。"""
        for bag in ([1], [1, 2], [1, 2, 2]):
            r = sum(bag)
            self.assertTrue(bits_cover(bag, r))
            for c in D.COINS:
                self.assertEqual(bits_cover(bag + [c], r + c), c <= r + 1)

    def test_alt_and_exchange(self):
        g = [r for *_, r in D.greedy_trace(D.X, D.COINS)]
        a = D.prefix_reach(D.ALT)
        self.assertEqual(a, [1, 2, 4, 9, 19])
        self.assertEqual(len(a), len(D.ALT))                                     # 一、一、二、五、十 也不断档
        self.assertTrue(all(x >= y for x, y in zip(g, a)))
        self.assertTrue(bits_cover(D.ALT, 19) and not bits_cover(D.ALT, 20))
        rnd = random.Random(3)                                                   # 交换论证：任意不断档的带法，贪心逐步不小
        for _ in range(300):
            coins = [1] + rnd.sample(range(2, 15), rnd.randint(1, 3))
            seq = sorted(rnd.choice(coins) for _ in range(rnd.randint(1, 7)))
            pr = D.prefix_reach(seq)
            if len(pr) < len(seq):
                continue
            gr, reach = [], 0
            for _ in seq:
                reach += max(c for c in coins if c <= reach + 1)
                gr.append(reach)
            self.assertTrue(all(x >= y for x, y in zip(gr, pr)))

    def test_brute(self):
        combos4 = list(itertools.combinations_with_replacement(D.COINS, 4))
        combos5 = list(itertools.combinations_with_replacement(D.COINS, 5))
        self.assertEqual(len(combos4), 35)
        self.assertEqual(len(combos5), 56)
        self.assertEqual(sum(bits_cover(b, D.X) for b in combos4), 0)
        self.assertEqual([b for b in combos5 if bits_cover(b, D.X)], [(1, 2, 2, 5, 10)])
        self.assertEqual(D.brute_count(D.X, D.COINS, 4), (35, 0))
        self.assertEqual(D.brute_count(D.X, D.COINS, 5), (56, 1))
        self.assertEqual(D.brute_min(D.X, D.COINS), 5)

    def test_random(self):
        rnd = random.Random(11)
        for _ in range(300):
            x = rnd.randint(1, 30)
            coins = rnd.sample(range(1, 16), rnd.randint(1, 4))
            want = brute_min_bits(x, coins)
            self.assertEqual(all_lecture(x, coins), [want] * 3)
            self.assertEqual(D.brute_min(x, coins), want)
        n, same, none = D.duel()
        self.assertEqual((n, same, none), (1000, 1000, 220))
        rnd = random.Random(D.DUEL_SEED)                                         # 复现 duel 的数据，用独立暴力重数无解组
        cnt = 0
        for _ in range(D.DUEL_N):
            x = rnd.randint(1, 25)
            coins = rnd.sample(range(2, 13), rnd.randint(1, 3))
            if rnd.random() < 0.8:
                coins.append(1)
            rnd.shuffle(coins)
            cnt += brute_min_bits(x, coins) == -1
        self.assertEqual(cnt, none)

    def test_echo_knapvar(self):
        import knapvardata as K
        parts = K.binary_split(13)
        self.assertEqual(parts, [1, 2, 4, 6])
        self.assertEqual(D.prefix_reach(parts), [1, 3, 7, 13])                  # 每捆不超过前面总和加一
        self.assertTrue(parts[-1] <= sum(parts[:-1]) + 1 and sum(parts[:-1]) == 7)
        self.assertTrue(bits_cover(parts, 13))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("shopping.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("题号二九八九六", beats["title"])
        self.assertIn("上限二十，面值一、二、五、十，答案是五枚", beats["read"])
        self.assertIn("两枚十就够了", beats["read"])
        w = beats["walk"]
        for s in ("只能带一，变成一", "上限是二，挑二，变成三", "上限是四，五太大，再带一枚二，变成五",
                  "上限是六，挑五，变成十", "上限十一，挑十，变成二十", "一共五枚：一、二、二、五、十"):
            self.assertIn(s, w)
        self.assertIn("一、一、二、五、十", beats["why"])
        self.assertIn("五枚只到十九", beats["why"])
        self.assertIn("十三拆成一、二、四、六", beats["echo"])
        self.assertIn("总和七再加一", beats["echo"])
        self.assertIn("讲义代码十行", beats["code"])
        b = beats["brute"]
        for s in ("四枚的三十五种组合，一种都不行", "五枚的五十六种里只有一种行，正是一、二、二、五、十",
                  "一千组", "其中二百二十组无解"):
            self.assertIn(s, b)


if __name__ == "__main__":
    unittest.main()
