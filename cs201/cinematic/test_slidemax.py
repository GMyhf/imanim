"""滑动窗口最大值片数字的独立对撞：讲义两份原版（T239 Solution、26978 题解）、暴力解、随机数据，以及旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_slidemax
"""
import json
import random
import unittest
from pathlib import Path

import slidemaxdata as D

SCRIPT = json.loads((Path(__file__).parent / "slidemax.json").read_text(encoding="utf-8"))
SAY = {b["id"]: b["narration"] for b in SCRIPT["beats"]}


class SlideMaxTest(unittest.TestCase):
    def test_samples(self):
        self.assertEqual(D.Solution().maxSlidingWindow(D.NUMS, D.K), [3, 3, 5, 5, 6, 7])   # LeetCode 示例 1
        self.assertEqual(D.Solution().maxSlidingWindow([1], 1), [1])                         # 示例 2
        self.assertEqual(D.run_oj("8 3\n1 3 -1 -3 5 3 6 7\n"), "3 3 5 5 6 7")
        self.assertEqual(D.trace(D.NUMS, D.K)[0], [3, 3, 5, 5, 6, 7])

    def test_random_vs_brute(self):
        rng = random.Random(239)
        for _ in range(3000):
            n = rng.randint(1, 30)
            k = rng.randint(1, n)
            a = [rng.randint(-5, 5) for _ in range(n)]      # 值域窄，重复值多，查 <= 与 < 两种写法
            want = D.brute(a, k)
            self.assertEqual(D.trace(a, k)[0], want)
            self.assertEqual(D.Solution().maxSlidingWindow(a, k), want)
            self.assertEqual(D.run_oj(f"{n} {k}\n{' '.join(map(str, a))}\n"), " ".join(map(str, want)))
            for q in D.snapshots(a, k):                      # 队列里下标递增、值严格递减（<= 弹队尾）
                self.assertEqual(q, sorted(q))
                self.assertTrue(all(a[x] > a[y] for x, y in zip(q, q[1:])))
                self.assertLessEqual(len(q), k)
            push, pops = D.op_counts(a, k)
            self.assertEqual(push, n)
            self.assertLessEqual(pops, n)

    def test_trace_story(self):
        """旁白「跑一遍」里的每一步。"""
        ans, ev = D.trace(D.NUMS, D.K)
        self.assertEqual(ev[1], ("pop", 1, 0))                                   # 三来了，弹掉一
        i4 = [e for e in ev if e[1] == 4]
        self.assertEqual(i4, [("expire", 4, 1), ("pop", 4, 3), ("pop", 4, 2), ("push", 4), ("out", 4, 4, 5)])
        self.assertEqual([e[2] for e in ev if e[0] == "pop" and e[1] == 6], [5, 4])   # 六弹掉三和五
        self.assertEqual([e[2] for e in ev if e[0] == "pop" and e[1] == 7], [6])      # 七弹掉六
        self.assertEqual(D.snapshots(D.NUMS, D.K), [[0], [1], [1, 2], [1, 2, 3], [4], [4, 5], [6], [7]])
        self.assertEqual(max(map(len, D.snapshots(D.NUMS, D.K))), 3)              # 画面队列容量

    def test_narration_numbers(self):
        self.assertEqual(len(D.brute(D.NUMS, D.K)), 6)
        self.assertIn("六个窗口", SAY["read"])
        self.assertIn("三、三、五、五、六、七", SAY["read"])
        self.assertEqual(D.brute_compares(len(D.NUMS), D.K), 12)
        self.assertIn("十二次", SAY["brute"])
        big = D.brute_compares(D.BIG_N, D.BIG_K)
        self.assertTrue(2.4e9 < big < 2.5e9)                                      # 「将近二十五亿」
        self.assertIn("将近二十五亿", SAY["brute"])
        self.assertEqual(D.op_counts(D.NUMS, D.K), (8, 7))
        self.assertIn("入队八次，出队七次", SAY["cost"])
        self.assertGreater(big / (2 * D.BIG_N), 1e4)                              # 「快了一万倍以上」
        self.assertIn("一万倍以上", SAY["cost"])


    def test_quiz_numbers(self):
        """入口页小测的答案。"""
        ev = D.trace(D.NUMS, D.K)[1]
        self.assertEqual([e[2] for e in ev if e[0] == "expire"], [1])          # i=4 时队首过期的是下标 1
        self.assertEqual(D.snapshots(D.NUMS, D.K)[3], [1, 2, 3])               # 处理完 i=3 后的队列
        self.assertEqual(D.trace([2, 1, 4, 3], 2)[0], [2, 4, 4])


if __name__ == "__main__":
    unittest.main()
