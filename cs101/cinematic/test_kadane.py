"""最大子段和片数字的独立对撞：讲义输出、暴力枚举区间 / 子矩阵 / 不相邻子集、画面中间量、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_kadane
"""
import itertools
import json
from pathlib import Path
import random
import unittest

import kadanedata as D


def brute_subarray(a):
    """独立方法：枚举全部 [l, r] 区间，返回 (和, l, r)，同和取先出现的。"""
    best = None
    for l in range(len(a)):
        for r in range(l, len(a)):
            s = sum(a[l:r + 1])
            if best is None or s > best[0]:
                best = (s, l, r)
    return best


def brute_submatrix(mat):
    """独立方法：枚举上下左右四条边，逐块求和。"""
    n, m = len(mat), len(mat[0])
    best = None
    for t, b in itertools.combinations_with_replacement(range(n), 2):
        for l, r in itertools.combinations_with_replacement(range(m), 2):
            s = sum(mat[i][j] for i in range(t, b + 1) for j in range(l, r + 1))
            if best is None or s > best[0]:
                best = (s, t, b, l, r)
    return best


def brute_rob(nums):
    """独立方法：枚举全部子集，跳过含相邻下标的。"""
    best, pick = 0, ()
    for k in range(len(nums) + 1):
        for c in itertools.combinations(range(len(nums)), k):
            if any(y - x == 1 for x, y in zip(c, c[1:])):
                continue
            s = sum(nums[i] for i in c)
            if s > best:
                best, pick = s, c
    return best, list(pick)


class KadaneFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual((D.max_subarray(D.T), D.max_subarray_o1(D.T)), (6, 6))     # 讲义：6 6
        self.assertEqual(D.max_submatrix(D.MAT), 15)                              # 讲义：15
        self.assertEqual((D.rob([1, 2, 3, 1]), D.rob(D.HOUSES)), (4, 12))         # 讲义：4 12

    def test_random_against_brute(self):
        rnd = random.Random(7)
        for _ in range(400):
            a = [rnd.randint(-9, 9) for _ in range(rnd.randint(1, 9))]
            b = brute_subarray(a)
            self.assertEqual(D.max_subarray(a), b[0])
            self.assertEqual(D.max_subarray_o1(a), b[0])
            s, l, r = D.best_segment(a)
            self.assertEqual(s, sum(a[l:r + 1]))
            self.assertEqual(s, b[0])
            dp, _, start = D.kadane_trace(a)
            for i in range(len(a)):                                             # dp[i] = 以 i 结尾的最大和
                self.assertEqual(dp[i], max(sum(a[k:i + 1]) for k in range(i + 1)))
                self.assertEqual(dp[i], sum(a[start[i]:i + 1]))
            h = [abs(x) for x in a]                                             # 钱数非负
            self.assertEqual(D.rob(h), brute_rob(h)[0])
            self.assertEqual(sum(h[i] for i in D.rob_choice(h)), D.rob(h))
        for _ in range(200):
            n, m = rnd.randint(1, 5), rnd.randint(1, 5)
            mat = [[rnd.randint(-9, 9) for _ in range(m)] for _ in range(n)]
            b = brute_submatrix(mat)
            self.assertEqual(D.max_submatrix(mat), b[0])
            s, t, bt, l, r = D.best_submatrix(mat)
            self.assertEqual(s, sum(mat[i][j] for i in range(t, bt + 1) for j in range(l, r + 1)))
            self.assertEqual(D.submatrix_log(mat)[-1][-1], D.max_submatrix(mat))

    def test_scan_trace(self):
        dp, restart, start = D.kadane_trace(D.T)
        self.assertEqual(dp, [-2, 1, -2, 4, 3, 5, 6, 1, 5])
        self.assertEqual([i for i, x in enumerate(restart) if x], [0, 1, 3])      # 从一、从四重新开始
        self.assertEqual(D.best_segment(D.T), (6, 3, 6))
        self.assertEqual(D.best_segment(D.T), brute_subarray(D.T))
        self.assertEqual(D.T[3:7], [4, -1, 2, 1])

    def test_submatrix(self):
        log = D.submatrix_log(D.MAT)
        self.assertEqual(len(log), 10)                                            # 上下边十种取法
        cols = {(t, b): c for t, b, c, *_ in log}
        self.assertEqual(cols[(1, 1)], D.MAT[1])
        self.assertEqual(cols[(1, 2)], [x + y for x, y in zip(D.MAT[1], D.MAT[2])])
        self.assertEqual(cols[(1, 3)], [4, 11, -10, 1])
        self.assertEqual(D.kadane_trace([4, 11, -10, 1])[0], [4, 15, 5, 6])
        self.assertEqual(D.best_submatrix(D.MAT), (15, 1, 3, 0, 1))
        self.assertEqual(D.best_submatrix(D.MAT), brute_submatrix(D.MAT))
        self.assertEqual([D.MAT[i][j] for i in (1, 2, 3) for j in (0, 1)], [9, 2, -4, 1, -1, 8])
        self.assertEqual(sorted(e[3] for e in log)[-2:], [13, 15])                # 十五唯一最大

    def test_rob(self):
        self.assertEqual(D.rob_trace(D.HOUSES), [2, 7, 11, 11, 12])
        self.assertEqual(D.rob_choice(D.HOUSES), [0, 2, 4])
        self.assertEqual(brute_rob(D.HOUSES), (12, [0, 2, 4]))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("kadane.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("负二、一、负三、四、负一、二、一、负五、四", beats["title"])
        self.assertIn("从一重新开始", beats["scan"])
        self.assertIn("又变成负二", beats["scan"])
        self.assertIn("接着是三、五、六", beats["scan"])
        self.assertIn("第七格的六是全程最大", beats["scan"])
        self.assertIn("减五剩一，加四是五", beats["scan"])
        self.assertIn("答案六，就是四、负一、二、一这一段", beats["scan"])
        self.assertIn("四乘四", beats["matrix"])
        self.assertIn("得到四、十一、负十、一", beats["squash"])
        self.assertIn("四；加十一，十五；加负十，五；加一，六", beats["demo"])
        self.assertIn("第二到第四行、第一到第二列", beats["demo"])
        self.assertIn("九、二、负四、一、负一、八，加起来正是十五", beats["demo"])
        self.assertIn("一共有十种取法", beats["all"])
        self.assertIn("二、七、九、三、一", beats["rob"])
        self.assertIn("依次是二、七、十一、十一、十二", beats["rob"])
        self.assertIn("答案十二，偷第一、第三、第五家", beats["rob"])


if __name__ == "__main__":
    unittest.main()
