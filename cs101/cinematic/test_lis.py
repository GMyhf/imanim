"""最长上升子序列片数字的独立对撞：讲义输出、暴力枚举子序列、耐心排序模拟、回溯结果、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_lis
"""
from itertools import combinations
import json
from pathlib import Path
import random
import unittest

import lisdata as L


def brute_best(a, ok):
    """枚举所有下标组合（从长到短），返回第一个相邻两两满足 ok 的长度。"""
    for k in range(len(a), 0, -1):
        for idx in combinations(range(len(a)), k):
            if all(ok(a[idx[t]], a[idx[t + 1]]) for t in range(k - 1)):
                return k
    return 0


def brute_sum(a):
    best = 0
    for k in range(1, len(a) + 1):
        for idx in combinations(range(len(a)), k):
            if all(a[idx[t]] < a[idx[t + 1]] for t in range(k - 1)):
                best = max(best, sum(a[t] for t in idx))
    return best


def piles_linear(a, strict=True):
    """不用 bisect：线性扫描各摞牌顶，找第一个「顶 ≥ v」（非降时「顶 > v」）的摞。"""
    piles = []
    for v in a:
        for p in piles:
            if (p[-1] >= v) if strict else (p[-1] > v):
                p.append(v)
                break
        else:
            piles.append([v])
    return piles


class LISFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual((L.lis_n2(L.A), L.lis_nlogn(L.A)), (4, 4))
        self.assertEqual(L.longest_non_increasing(L.MISSILE), 6)
        self.assertEqual(L.max_rising_sum(L.A), 18)

    def test_random_against_brute(self):
        rng = random.Random(2533)
        for _ in range(300):
            a = [rng.randint(0, 9) for _ in range(rng.randint(1, 9))]
            self.assertEqual(L.lis_n2(a), brute_best(a, lambda x, y: x < y))
            self.assertEqual(L.lis_nlogn(a), brute_best(a, lambda x, y: x < y))
            self.assertEqual(L.longest_non_increasing(a), brute_best(a, lambda x, y: x >= y))
            self.assertEqual(L.max_rising_sum(a), brute_sum(a))
            self.assertEqual(len(L.tails_trace(a, "right")[-1][3]), brute_best(a, lambda x, y: x <= y))
            # 落牌记录与线性扫描的耐心排序一致
            self.assertEqual(L.tails_trace(a)[-1][4], piles_linear(a, True))
            self.assertEqual(L.tails_trace(a, "right")[-1][4], piles_linear(a, False))
            back = L.lis_back(a)
            self.assertEqual(len(back), L.lis_n2(a))
            self.assertTrue(all(a[back[t]] < a[back[t + 1]] for t in range(len(back) - 1)))
            self.assertEqual(back, sorted(back))

    def test_n2_trace(self):
        dp, steps = L.n2_trace()
        self.assertEqual(dp, [1, 2, 2, 3, 4, 3, 4])
        for i, (cand, best) in enumerate(steps):
            self.assertEqual(cand, [j for j in range(i) if L.A[j] < L.A[i]])
            self.assertEqual(dp[i], 1 + max((dp[j] for j in cand), default=0))
            if best is not None:
                self.assertEqual(dp[best] + 1, dp[i])
        # 旁白「接在谁后面」：七、三接在一后面，五接在三，九接在五，四接在三，八接在五
        self.assertEqual([L.A[b] if b is not None else None for _, b in steps], [None, 1, 1, 3, 5, 3, 5])
        self.assertEqual(steps[4][0], [0, 1, 2, 3])                        # 九前面的数都比它小

    def test_piles_and_trap(self):
        st = L.tails_trace()
        self.assertEqual([s[3] for s in st][-1], [1, 3, 4, 8])
        # 旁白：一开第一摞，七新开，三压七，五开第三摞，九开第四摞，四压五，八压九
        self.assertEqual([(s[1], s[2]) for s in st],
                         [(0, True), (1, True), (1, False), (2, True), (3, True), (2, False), (3, False)])
        self.assertEqual(st[-1][4], [[1], [7, 3], [5, 4], [9, 8]])
        for s in st:                                                       # 牌顶递增，二分才成立
            self.assertEqual(s[3], sorted(set(s[3])))
        k, tails = L.trap_step()
        self.assertEqual((L.A[k], tails), (4, [1, 3, 4, 9]))               # 处理完四的那一刻
        self.assertLess(L.A.index(9), L.A.index(4))                        # 四排在九后面
        self.assertEqual([L.A[i] for i in L.lis_back()], [1, 3, 5, 9])
        self.assertEqual(L.compares(L.BIG_N), sum(range(L.BIG_N)))
        self.assertTrue(4.9e9 < L.compares(L.BIG_N) < 5e9)                 # 将近五十亿

    def test_variants(self):
        self.assertEqual(L.tails_strict_vs_nondec(), (1, 3))
        self.assertEqual(L.EQUAL, [2, 2, 2])
        r, st = L.missile_trace()
        self.assertEqual(r, L.MISSILE[::-1])
        self.assertEqual(len(st[-1][3]), 6)
        self.assertEqual(len(L.MISSILE), 8)
        w = L.non_increasing_witness()
        self.assertEqual(len(w), L.longest_non_increasing(L.MISSILE))
        self.assertTrue(all(L.MISSILE[w[t]] >= L.MISSILE[w[t + 1]] and w[t] < w[t + 1] for t in range(len(w) - 1)))
        dp, seq = L.rising_sum_back()
        self.assertEqual((max(dp), seq), (18, [1, 3, 5, 9]))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("lis.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("一、七、三、五、九、四、八", beats["title"])
        self.assertIn("答案是四个，比如一、三、五、九", beats["title"])
        for s in ("七接在一后面，是二", "三也只能接在一后面，是二", "五接在三后面，是三", "接在五后面，是四",
                  "四接在三后面，是三", "八接在五后面，又是四", "最大值：四"):
            self.assertIn(s, beats["fill"])
        self.assertIn("将近五十亿次", beats["cost"])
        for s in ("三压在七上", "五开第三摞，九开第四摞", "四压在五上，八压在九上", "一共四摞，答案是四"):
            self.assertIn(s, beats["piles"])
        self.assertIn("牌顶是一、三、四、九，长度四没错", beats["trap"])
        self.assertIn("真正的是一、三、五、九", beats["trap"])
        self.assertIn("严格上升长度是一，非降长度是三", beats["strict"])
        self.assertIn("样例八枚导弹，最多拦下六枚", beats["homework"])
        self.assertIn("答案是十八，等于一加三加五加九", beats["homework"])


if __name__ == "__main__":
    unittest.main()
