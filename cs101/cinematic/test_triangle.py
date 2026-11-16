"""从递归到 DP 片数字的独立对撞：讲义输出、递归计数闭式、路径穷举、两种填法与滚动数组、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_triangle
"""
import itertools
import json
from functools import lru_cache
from pathlib import Path
import random
import unittest

import triangledata as D


def stairs_brute(n):
    """独立方法：枚举每一步走 1 还是 2 的全部序列，数和为 n 的。"""
    return sum(1 for k in range(n + 1) for seq in itertools.product((1, 2), repeat=k) if sum(seq) == n)


def rec_calls_closed(n):
    """朴素递归调用次数 C(n) = C(n-1) + C(n-2) + 1，C(0) = C(1) = 1，用迭代独立推。"""
    c = [1, 1]
    for _ in range(2, n + 1):
        c.append(c[-1] + c[-2] + 1)
    return c[n]


def tri_paths(tri):
    """独立方法：枚举全部左/右转向序列，返回 [(格子序列, 和)]。"""
    out = []
    for turns in itertools.product((0, 1), repeat=len(tri) - 1):
        j, cells = 0, [(0, 0)]
        for i, d in enumerate(turns, 1):
            j += d
            cells.append((i, j))
        out.append((cells, sum(tri[i][c] for i, c in cells)))
    return out


def best_from(tri, i, j):
    """从 (i, j) 出发到底的最大和：枚举从这格出发的所有路径。"""
    sub = [row[j:j + k + 1] for k, row in enumerate(tri[i:])]
    return max(s for _, s in tri_paths(sub))


def best_to(tri, i, j):
    """从顶走到 (i, j) 的最大和：枚举所有到达 (i, j) 的路径。"""
    return max(s for cells, s in tri_paths(tri[:i + 1]) if cells[-1] == (i, j))


class TriangleFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual((D.f1(20), D.f2(20), D.f3(20)), (6765, 6765, 6765))
        self.assertEqual(D.f4(20), 6765)
        self.assertEqual([D.climb_stairs(k) for k in range(1, 8)], [1, 2, 3, 5, 8, 13, 21])
        self.assertEqual(D.max_path_sum(D.TRI), 30)
        self.assertEqual(D.max_path_sum_1d(D.TRI), 30)

    def test_stairs_three_steps_agree(self):
        for n in range(0, 16):
            want = stairs_brute(n)
            self.assertEqual(D.climb_rec(n), want)
            self.assertEqual(D.climb_memo(n), want)
            self.assertEqual(D.climb_stairs(n), want)
            self.assertEqual(D.climb_table(n)[n], want)
            if n >= 1:
                self.assertEqual(D.climb_rec(n), D.f1(n + 1))         # 爬楼梯 = 斐波那契错一位

    def test_stairs_counts(self):
        f = D.stairs_facts()
        self.assertEqual(f["answer"], 21)
        self.assertEqual(f["rec_calls"], rec_calls_closed(D.N_STAIRS))
        self.assertEqual(f["rec_calls"], 41)
        self.assertEqual(f["rec_per_level"][1], 13)
        self.assertEqual(f["rec_per_level"][0], 8)
        self.assertEqual(sum(f["rec_per_level"]), 41)
        self.assertEqual(f["memo_calls"], 13)
        self.assertEqual(f["memo_calls"], 2 * D.N_STAIRS - 1)
        self.assertEqual(f["table"], [stairs_brute(k) for k in range(D.N_STAIRS + 1)])
        # 记忆化：每级恰好真算一次（base 也只出现在第一次）
        log = []
        D.climb_memo(D.N_STAIRS, None, log)
        calc = [a for a, how in log if how == "calc"]
        self.assertEqual(sorted(calc), list(range(2, D.N_STAIRS + 1)))

    def test_triangle_paths(self):
        ps = tri_paths(D.TRI)
        self.assertEqual(len(ps), 16)
        self.assertEqual(D.count_paths(), 16)
        best = max(s for _, s in ps)
        self.assertEqual(best, 30)
        winners = [c for c, s in ps if s == best]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0], D.best_path())
        self.assertEqual([D.TRI[i][j] for i, j in D.best_path()], [7, 3, 8, 7, 5])

    def test_two_fill_orders_same_table(self):
        up = D.up_table()
        ans, calls, order, memo = D.tri_memo()
        self.assertEqual(ans, 30)
        self.assertEqual(len(order), 15)
        self.assertEqual(len(set(order)), 15)
        for (i, j), v in memo.items():
            self.assertEqual(v, up[i][j])
            self.assertEqual(v, best_from(D.TRI, i, j))
        # 记忆化填表顺序：每格算完时，它下面两格都已经算完
        done = set()
        for i, j in order:
            if i < 4:
                self.assertIn((i + 1, j), done)
                self.assertIn((i + 1, j + 1), done)
            done.add((i, j))
        self.assertEqual(order[:3], [(4, 0), (4, 1), (3, 0)])        # 先沿左边扎到底
        self.assertEqual(order[-1], (0, 0))                           # 顶上最后填
        log = []
        self.assertEqual(D.tri_rec(D.TRI, log), 30)
        self.assertEqual(len(log), 2 ** 5 - 1)                         # 31 次调用

    def test_forward_and_roll(self):
        fw = D.forward_table()
        for i, row in enumerate(fw):
            for j, v in enumerate(row):
                self.assertEqual(v, best_to(D.TRI, i, j))
        self.assertEqual(max(fw[-1]), 30)
        log = D.roll_log()
        self.assertEqual(len(log), 10)
        up = D.up_table()
        for i, j, a, b, v in log:
            self.assertEqual(v, up[i][j])
            self.assertEqual((a, b), (up[i + 1][j], up[i + 1][j + 1]))   # 读到的都是下一行的旧值
        self.assertEqual(log[-1][4], 30)

    def test_random(self):
        rnd = random.Random(7)
        for _ in range(300):
            n = rnd.randint(1, 7)
            t = [[rnd.randint(0, 9) for _ in range(i + 1)] for i in range(n)]
            want = max(s for _, s in tri_paths(t))
            self.assertEqual(D.max_path_sum(t), want)
            self.assertEqual(D.max_path_sum_1d(t), want)
            self.assertEqual(D.tri_memo(t)[0], want)
            self.assertEqual(D.tri_rec(t), want)
            self.assertEqual(max(D.forward_table(t)[-1]), want)

            @lru_cache(None)
            def g(i, j):
                return t[i][j] + (0 if i == n - 1 else max(g(i + 1, j), g(i + 1, j + 1)))
            self.assertEqual(g(0, 0), want)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("triangle.json").read_text(encoding="utf-8"))["beats"]}
        f = D.stairs_facts()
        self.assertEqual(f["answer"], 21)
        self.assertIn("楼梯有七级", beats["stairs"])
        self.assertIn("第七级是二十一种", beats["stairs"])
        self.assertIn("一共调用了四十一次", beats["rec"])
        self.assertIn("第一级被问了十三次，地面被问了八次", beats["rec"])
        self.assertIn("从四十一次降到十三次", beats["memo"])
        self.assertIn("七次加法", beats["table"])
        self.assertEqual(f["loop_iters"], 7)
        self.assertIn("五行一共十六条路径", beats["tri"])
        self.assertIn("最大是三十，只有一条路径拿得到：七、三、八、七、五", beats["tri"])
        self.assertIn("调用三十一次", beats["trimemo"])
        self.assertIn("十五个格子各算一次", beats["trimemo"])
        self.assertIn("顶上是三十", beats["triup"])
        self.assertIn("两种定义都得到三十", beats["forward"])
        self.assertEqual(max(D.forward_table()[-1]), D.up_table()[0][0])
        self.assertIn("最后剩下三十", beats["roll"])


if __name__ == "__main__":
    unittest.main()
