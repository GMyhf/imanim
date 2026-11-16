"""背包三个变形片数字的独立对撞：讲义输出、暴力枚举、旁白数字。

独立实现不调用 knapvardata 的算法：多重背包按每种拿几个穷举，恰好装满按子集穷举，
Coins 按每种硬币用几枚穷举，二维费用按子集穷举，分数背包用「按单价把容量逐单位分给最贵的」重算。
用法（cwd = cs101/cinematic）：python -m unittest test_knapvar
"""
from fractions import Fraction
from itertools import combinations, product
import json
from pathlib import Path
import random
import unittest

import knapvardata as K

NARR = {b["id"]: b["narration"] for b in json.loads(
    Path(__file__).with_name("knapvar.json").read_text(encoding="utf-8"))["beats"]}
TEXT = "".join(NARR.values())


def brute_multi(items, cap):
    best = 0
    for cnt in product(*[range(k + 1) for _, _, k in items]):
        if sum(c * w for c, (w, _, _) in zip(cnt, items)) <= cap:
            best = max(best, sum(c * v for c, (_, v, _) in zip(cnt, items)))
    return best


def subsets(n):
    for r in range(n + 1):
        yield from combinations(range(n), r)


def brute_exact(ws, vs, cap):
    """恰好装满的最大价值，凑不出返回 -1；cap 处给出「不超过」的最大价值。"""
    exact = [-1] * (cap + 1)
    for s in subsets(len(ws)):
        w = sum(ws[i] for i in s)
        if w <= cap:
            exact[w] = max(exact[w], sum(vs[i] for i in s))
    return exact


def brute_coins(A, C, m):
    sums = {sum(x * a for x, a in zip(cnt, A)) for cnt in product(*[range(c + 1) for c in C])}
    return sum(1 for s in range(1, m + 1) if s in sums)


def brute_pokemon(balls, hp, pets):
    best, used = 0, 0
    for s in subsets(len(pets)):
        b, h = sum(pets[i][0] for i in s), sum(pets[i][1] for i in s)
        if b <= balls and h <= hp:
            if len(s) > best or (len(s) == best and h < used):
                best, used = len(s), h
    return best, hp - used


def frac_units(items, cap):
    """分数背包：容量逐个 1/60 单位地分给剩余单价最高的物品（与排序贪心写法无关）。"""
    left = [Fraction(w) for _, w in items]
    total, step = Fraction(0), Fraction(1, 60)
    for _ in range(cap * 60):
        cand = [i for i in range(len(items)) if left[i] > 0]
        if not cand:
            break
        i = max(cand, key=lambda j: Fraction(items[j][0], items[j][1]))
        left[i] -= step
        total += step * Fraction(items[i][0], items[i][1])
    return total


class KnapVarFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(K.multi_knapsack([(2, 5, 3)], 6), 15)
        self.assertEqual(K.multi_knapsack([(2, 5, 2)], 6), 10)
        self.assertEqual([K.binary_split(k) for k in K.SPLIT_KS],
                         [[1], [1, 2, 2], [1, 2, 4], [1, 2, 4, 3], [1, 2, 4, 6]])
        self.assertEqual(K.exact_fill_max([2, 3], [10, 20], 5), 30)
        self.assertEqual(K.exact_fill_max(K.EX_W, K.EX_V, K.EX_CAP), -1)
        self.assertEqual(K.pokemon(K.PK_BALLS, K.PK_HP, K.PK_PETS), (3, 30))
        self.assertEqual(f"{K.fractional_knapsack(K.COURSE_FR, 10):.1f}", "20.0")

    def test_split_reach(self):
        for k in range(1, 200):
            parts = K.binary_split(k)
            self.assertEqual(sum(parts), k)
            for j, p in enumerate(parts):                # 每捆不超过前面总和加一 → 不断档
                self.assertLessEqual(p, sum(parts[:j]) + 1)
            self.assertEqual(K.reach_steps(k)[-1], list(range(k + 1)))
        steps = K.reach_steps(K.SPLIT_K)
        self.assertEqual([s[-1] for s in steps], [0, 1, 3, 7, 13])        # 零到一、三、七、十三
        self.assertEqual(steps[-1][6:], list(range(6, 14)))                 # 右移六格得六到十三

    def test_multi_random(self):
        rng = random.Random(14)
        for _ in range(300):
            items = [(rng.randint(1, 5), rng.randint(1, 9), rng.randint(1, 6)) for _ in range(rng.randint(1, 3))]
            cap = rng.randint(0, 20)
            self.assertEqual(K.multi_knapsack(items, cap), brute_multi(items, cap))

    def test_exact_rows(self):
        loose = K.fill_rows(K.EX_W, K.EX_V, K.EX_CAP, exact=False)
        tight = K.fill_rows(K.EX_W, K.EX_V, K.EX_CAP, exact=True)
        ex = brute_exact(K.EX_W, K.EX_V, K.EX_CAP)
        self.assertEqual(loose[-1][-1], 20)                                 # 不超过型：容量五是二十
        self.assertEqual(max(ex), 20)
        self.assertEqual([-1 if x == float("-inf") else x for x in tight[-1]], ex)   # 恰好型逐格 = 穷举
        self.assertEqual(ex[5], -1)                                         # 二和四凑不出五
        rng = random.Random(21)
        for _ in range(300):
            n = rng.randint(1, 5)
            ws = [rng.randint(1, 6) for _ in range(n)]
            vs = [rng.randint(1, 20) for _ in range(n)]
            cap = rng.randint(0, 12)
            b = brute_exact(ws, vs, cap)
            self.assertEqual(K.exact_fill_max(ws, vs, cap), b[cap])
            self.assertEqual(K.fill_rows(ws, vs, cap, False)[-1][cap], max(b))

    def test_coins(self):
        bundles, rows, ans = K.coins_steps(K.COIN_A, K.COIN_C, K.COIN_M)
        self.assertEqual([b[2] for b in bundles], [1, 1, 2, 4])
        self.assertEqual(ans, 8)
        self.assertEqual(ans, brute_coins(K.COIN_A, K.COIN_C, K.COIN_M))
        self.assertEqual([c for c in range(K.COIN_M + 1) if not rows[-1][c]], [9, 10])
        self.assertEqual(K.coins([1, 4], [2, 1], 5), 4)                     # POJ 样例第二组
        rng = random.Random(1742)
        for _ in range(200):
            n = rng.randint(1, 3)
            A = [rng.randint(1, 8) for _ in range(n)]
            C = [rng.randint(1, 5) for _ in range(n)]
            m = rng.randint(1, 30)
            self.assertEqual(K.coins(A, C, m), brute_coins(A, C, m))

    def test_pokemon(self):
        self.assertEqual(K.pokemon(K.PK_BALLS, K.PK_HP, K.PK_PETS), brute_pokemon(K.PK_BALLS, K.PK_HP, K.PK_PETS))
        pick = K.pokemon_pick(K.PK_BALLS, K.PK_HP, K.PK_PETS)
        self.assertLessEqual(sum(K.PK_PETS[i][0] for i in pick), K.PK_BALLS)
        self.assertEqual(K.PK_HP - sum(K.PK_PETS[i][1] for i in pick), 30)
        rng = random.Random(4102)
        for _ in range(200):
            pets = [(rng.randint(1, 6), rng.randint(1, 30)) for _ in range(rng.randint(1, 5))]
            balls, hp = rng.randint(0, 12), rng.randint(0, 60)
            self.assertEqual(K.pokemon(balls, hp, pets), brute_pokemon(balls, hp, pets))

    def test_fractional_and_greedy(self):
        self.assertEqual(K.fractional_knapsack(K.FR_ITEMS, K.FR_CAP), 46)
        self.assertEqual(frac_units(K.FR_ITEMS, K.FR_CAP), 46)
        self.assertEqual(frac_units(K.COURSE_FR, 10), 20)
        tr = K.fractional_trace(K.FR_ITEMS, K.FR_CAP)
        self.assertEqual([(t[2], t[3]) for t in tr], [(6, 30), (4, 16)])   # 切下五分之四，得十六
        self.assertEqual(K.greedy_01(K.FR_ITEMS, K.FR_CAP)[0], 30)
        best01 = max(sum(K.FR_ITEMS[i][0] for i in s) for s in subsets(3)
                     if sum(K.FR_ITEMS[i][1] for i in s) <= K.FR_CAP)
        self.assertEqual(K.knap01(K.FR_ITEMS, K.FR_CAP), best01)
        self.assertEqual(best01, 40)
        self.assertEqual([v / w for v, w in K.FR_ITEMS], [5, 4, 4])        # 单价五、四

    def test_narration_numbers(self):
        for beat, s in (("split", "十三拆成一、二、四、六"), ("split", "五拆成一、二、二"), ("split", "十拆成一、二、四、三"),
                        ("why", "零到一"), ("why", "零到三"), ("why", "零到七"), ("why", "得到六到十三"),
                        ("exact", "体积二价值十，体积四价值二十，容量五"), ("exact", "容量五是二十"),
                        ("exact", "输出负一"),
                        ("coins", "一、一、二、四四捆"), ("coins", "零到八都能到，九和十不行，答案是八"),
                        ("twodim", "十个球、一百点体力，最多收服三只"), ("twodim", "剩三十点体力"),
                        ("frac", "容量十，重六价值三十，单价五"), ("frac", "两件重五价值二十，单价四"),
                        ("frac", "五分之四，得十六，一共四十六"),
                        ("greedy", "只得三十"), ("greedy", "得四十")):
            self.assertIn(s, NARR[beat], beat)
        self.assertEqual(K.COIN_M, 10)
        self.assertEqual((K.PK_BALLS, K.PK_HP), (10, 100))


if __name__ == "__main__":
    unittest.main()
