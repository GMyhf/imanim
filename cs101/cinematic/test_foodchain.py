"""食物链片数字的独立对撞：讲义输出、穷举物种分配、带权（模 3）并查集、插桩记录与旁白数字。

两种独立实现都不用扩展域：
- brute_lies：维护已接受的真话，每来一句就穷举所有动物的物种（0/1/2）分配，看能否同时满足；
- weighted_lies：带权并查集，d[x] = x 相对根的物种差（模 3），x 吃 y 即 (sx - sy) ≡ 1。
用法（cwd = cs101/cinematic）：python -m unittest test_foodchain
"""
from itertools import product
import json
from pathlib import Path
import random
import unittest

import foodchaindata as F


def brute_lies(n, stmts):
    ok = []                                  # 已接受的 (kind, x, y)
    lies = []
    for k, (kind, x, y) in enumerate(stmts):
        if not (1 <= x <= n and 1 <= y <= n) or (kind == 2 and x == y):
            lies.append(k + 1)
            continue
        cand = ok + [(kind, x, y)]
        who = sorted({a for _, a, b in cand} | {b for _, a, b in cand})
        idx = {a: i for i, a in enumerate(who)}

        def sat(s):
            for t, a, b in cand:
                da = (s[idx[a]] - s[idx[b]]) % 3
                if da != (0 if t == 1 else 1):   # x 吃 y：x 的物种 = y 的物种 + 1（模 3）
                    return False
            return True
        if any(sat(s) for s in product(range(3), repeat=len(who))):
            ok.append((kind, x, y))
        else:
            lies.append(k + 1)
    return lies


def weighted_lies(n, stmts):
    par = list(range(n + 1))
    off = [0] * (n + 1)                      # 相对父结点的物种差

    def find(x):
        if par[x] == x:
            return x
        r = find(par[x])
        off[x] = (off[x] + off[par[x]]) % 3
        par[x] = r
        return r
    lies = []
    for k, (kind, x, y) in enumerate(stmts):
        if not (1 <= x <= n and 1 <= y <= n) or (kind == 2 and x == y):
            lies.append(k + 1)
            continue
        want = 0 if kind == 1 else 1
        rx, ry = find(x), find(y)
        if rx == ry:
            if (off[x] - off[y]) % 3 != want:
                lies.append(k + 1)
        else:
            par[rx] = ry
            off[rx] = (want + off[y] - off[x]) % 3
    return lies


def random_stmts(rng, n, m):
    return [(rng.randint(1, 2), rng.randint(1, n + 1), rng.randint(1, n + 1)) for _ in range(m)]


class FoodChainFacts(unittest.TestCase):
    def test_course_output(self):
        self.assertEqual(F.food_chain(F.N, F.SAMPLE), 3)                  # 讲义 print 的结果
        self.assertEqual(F.lie_lines(), brute_lies(F.N, F.SAMPLE))
        self.assertEqual(F.lie_lines(), weighted_lies(F.N, F.SAMPLE))
        self.assertEqual(F.lie_lines(), [1, 4, 5])

    def test_random(self):
        rng = random.Random(1182)
        for _ in range(400):
            n = rng.randint(1, 5)
            s = random_stmts(rng, n, rng.randint(1, 12))
            want = brute_lies(n, s)
            self.assertEqual(weighted_lies(n, s), want)
            self.assertEqual(F.food_chain(n, s), len(want))
            self.assertEqual(F.lie_lines(n, s), want)
            self.assertEqual(F.lies_of(n, s), F.food_chain(n, s))       # 插桩版与原版逐句一致

    def test_trace_sample(self):
        log = F.food_chain_trace()
        self.assertEqual(len(log), 7)
        self.assertEqual([r["why"] for r in log], ["range", None, None, "self", "check0", None, None])
        # 一吃二、二吃三：三对都真正合并
        for r in log[1:3]:
            self.assertEqual([u[2] for u in r["unions"]], [True] * 3)
        # 第三句之后：九个结点三个集合，每个集合正好一类
        sets = F.species_sets(log[2])
        self.assertEqual(len(sets), 3)
        self.assertIn([(1, 0), (2, 2), (3, 1)], sets)                   # 一号、二号的天敌、三号的猎物
        for s in sets:
            self.assertEqual(sorted(a for a, _ in s), [1, 2, 3])        # 每个动物每个集合恰好一个域
        # 第五句：一号已和三号猎物域连通
        self.assertEqual(log[4]["checks"], [((1, 0), (3, 1), True)])
        # 第六句：两对都不连通，三对 union 全返回 False
        self.assertEqual([c[2] for c in log[5]["checks"]], [False, False])
        self.assertEqual([u[2] for u in log[5]["unions"]], [False] * 3)
        self.assertFalse(log[6]["lie"])

    def test_missing_third(self):
        log = F.food_chain_trace(third=False)
        self.assertEqual(F.lie_lines(third=False), [1, 4, 6])
        self.assertEqual(log[-1]["lies"], 3)                            # 总数碰巧还是三
        # 第五句前（第三句后），三号的猎物域孤零零一个点
        self.assertIn([(3, 1)], F.species_sets(log[2]))
        self.assertFalse(log[4]["lie"])
        self.assertTrue(log[5]["lie"])
        self.assertEqual(log[5]["why"], "check0")                       # 三与一已「同类」
        # 随机数据上，少连第三对确实会出错
        rng = random.Random(3)
        bad = sum(F.lie_lines(n, s, third=False) != brute_lies(n, s)
                  for n, s in ((4, random_stmts(rng, 4, 10)) for _ in range(200)))
        self.assertGreater(bad, 0)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("foodchain.json").read_text(encoding="utf-8"))["beats"]}
        self.assertEqual(F.N, 100)
        self.assertIn("n 是一百，一共七句话", beats["run1"])
        self.assertEqual(F.SAMPLE[0], (1, 101, 1))
        self.assertIn("一百零一超出范围", beats["run1"])
        self.assertEqual(F.SAMPLE[1:3], [(2, 1, 2), (2, 2, 3)])
        self.assertIn("第二句，一吃二", beats["run1"])
        self.assertIn("第三句，二吃三", beats["run1"])
        self.assertEqual(len(F.SHOW) * 3, 9)
        self.assertIn("九个结点只剩三个集合", beats["run1"])
        self.assertEqual(F.SAMPLE[3:], [(2, 3, 3), (1, 1, 3), (2, 3, 1), (1, 5, 5)])
        for s in ("第四句，三吃三", "第五句，一和三同类", "第六句，三吃一", "第七句，五和五同类", "一共三句假话"):
            self.assertIn(s, beats["run2"])
        self.assertIn("总数碰巧还是三", beats["missing"])
        self.assertIn("第六句三吃一，反倒判成假话", beats["missing"])


if __name__ == "__main__":
    unittest.main()
