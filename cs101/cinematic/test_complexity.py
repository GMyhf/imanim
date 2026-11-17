"""算法分析片数字的独立对撞：循环次数闭式、讲义筛法输出、试除与筛法计数、list/set 比较次数、旁白数字。

独立实现不调用 complexitydata 的插桩函数：闭式求和、逐数找最小因子、按素数求和的划掉次数公式等。
用法（cwd = cs101/cinematic）：python -m unittest test_complexity
"""
import json
import math
from pathlib import Path
import random
import unittest

import complexitydata as D


def primes_by_trial(n):
    """独立判素：用 all() 一次性试除到 √x。"""
    return [x for x in range(2, n + 1) if all(x % d for d in range(2, math.isqrt(x) + 1))]


def trial_divisions_indep(n):
    """独立计数：每个 x 试除到第一个因子或 ⌊√x⌋，次数 = 停下来时的除数 − 1。"""
    total = 0
    for x in range(2, n + 1):
        r = math.isqrt(x)
        first = next((d for d in range(2, r + 1) if x % d == 0), None)
        total += (first - 1) if first else (r - 1)
    return total


def sieve_marks_formula(n):
    """每个素数 p ≤ √n 从 p² 划到 n，步长 p：⌊(n − p²)/p⌋ + 1 次。"""
    return sum((n - p * p) // p + 1 for p in primes_by_trial(math.isqrt(n)))


class ComplexityFacts(unittest.TestCase):
    def test_course_sieve_output(self):
        # 讲义 4.4 节的打印结果
        self.assertEqual(D.primes_upto(100), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61,
                                               67, 71, 73, 79, 83, 89, 97])
        for n in (2, 3, 10, 50, 97, 100, 1000, 9973):
            self.assertEqual(D.primes_upto(n), primes_by_trial(n))
        _, isp = D.sieve_trace(100)
        self.assertEqual(isp, D.sieve(100))

    def test_loops(self):
        for n in range(0, 30):
            self.assertEqual(len(D.loop_triangle(n)), n * (n + 1) // 2)
            self.assertEqual(D.triangle_count(n), sum(range(1, n + 1)))
            self.assertEqual(len(D.loop_square(n)), n * n)
        self.assertEqual(D.row_counts(6), [6, 5, 4, 3, 2, 1])
        self.assertEqual(D.triangle_count(D.DEMO_N), 21)
        self.assertTrue(all(i <= j for i, j in D.loop_triangle(6)))           # 只有右上半
        self.assertEqual(D.open_ops(), 5_000_050_000)                          # 约五十亿
        self.assertEqual(round(D.open_ops() / 1e9), 5)
        self.assertGreater(D.seconds_at_best(D.open_ops()), 1)                 # 超时
        self.assertEqual(D.poly(10 ** 6), 3 * 10 ** 12 + 10 ** 8 + 500)

    def test_levels_and_budget(self):
        lv = {name: v for name, _, v, _ in D.levels()}
        self.assertEqual(round(lv["log n"]), 20)                              # 约二十
        self.assertEqual(lv["n"], 10 ** 6)
        self.assertEqual(round(lv["n log n"] / 1e7), 2)                       # 约两千万
        self.assertEqual(lv["n²"], 10 ** 12)                                  # 一万亿
        self.assertEqual(round(math.log10(lv["n²"]) - math.log10(lv["n"])), 6)  # 高出六格
        rows = D.budget_rows()
        self.assertEqual([r[0] for r in rows], [10, 20, 100, 1000, 10 ** 5, 10 ** 6])
        ops = [r[3] for r in rows]
        self.assertEqual(ops[:4], [3628800, 2 ** 20, 10 ** 6, 10 ** 6])
        self.assertTrue(all(10 ** 6 <= v < 4 * 10 ** 6 for v in ops))        # 一百万到四百万之间
        self.assertTrue(all(v < D.OPS_PER_SEC[0] for v in ops))               # 留出常数余量

    def test_space(self):
        import sys
        self.assertEqual(sys.getsizeof(10 ** 6 + 7), D.INT_BYTES)            # 64 位 CPython 的小 int 对象
        self.assertEqual(sys.getsizeof([None] * 1000) - sys.getsizeof([]), 1000 * D.PTR_BYTES)
        self.assertEqual(D.list_mb(), 36)                                     # 三十多兆
        self.assertEqual(D.SPACE_GRID ** 2, 10 ** 8)                          # 一亿个格子
        self.assertEqual(D.grid_ptr_mb(), 800)                                # 八百兆
        self.assertLess(D.list_mb(), D.MEM_LIMIT_MB[0])
        self.assertGreater(D.grid_ptr_mb(), D.MEM_LIMIT_MB[1])

    def test_list_vs_set(self):
        self.assertEqual(D.list_in_compares(), D.list_in_compares_fast())
        n, s = D.BENCH_N, D.BENCH_STEP
        q = n // s
        self.assertEqual(D.set_lookups(), q)
        self.assertEqual(q, 200)                                               # 查两百次
        self.assertEqual(D.list_in_compares(), s * q * (q - 1) // 2 + q)       # 闭式
        self.assertEqual(round(D.list_in_compares() / 1e7), 2)                 # 约两千万
        self.assertTrue(3 <= math.log10(D.TYPICAL_LIST_S / D.TYPICAL_SET_S) < 4)        # 三个数量级
        self.assertEqual(D.scan_demo([0, 1, 2, 3, 4, 5], 4), [0, 1, 2, 3, 4])

    def test_sieve_vs_trial(self):
        rng = random.Random(4)
        for n in [2, 3, 4, 10, 100, 1000] + [rng.randint(2, 20000) for _ in range(20)]:
            self.assertEqual(D.sieve_marks(n), sieve_marks_formula(n))
            self.assertEqual(D.trial_count(n), trial_divisions_indep(n))
            self.assertEqual(D.trial_count_fast(n), D.trial_count(n))
        self.assertEqual(D.trial_count_fast(10 ** 5), trial_divisions_indep(10 ** 5))
        self.assertEqual(D.versus(100), (236, 104))
        t, s = D.versus(10 ** 6)
        self.assertEqual(s, sieve_marks_formula(10 ** 6))
        self.assertEqual((t // 10 ** 6, s // 10 ** 4), (67, 212))             # 六千七百多万、约二百一十二万
        self.assertEqual(int(t / s) // 10, 3)                                  # 三十多倍
        tr, _ = D.sieve_trace(100)
        self.assertEqual([i for i, alive, m in tr if alive], [2, 3, 5, 7])     # 二、三、五、七；四被跳过
        self.assertFalse(tr[2][1])                                             # i = 4 时已被划掉
        self.assertTrue(all(m[0] == i * i for i, _, m in tr if m))             # 从 i 的平方开始
        self.assertEqual(tr[-1][0], 10)                                        # 十一的平方超过一百就停
        self.assertEqual(len(D.primes_upto(100)), 25)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("complexity.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("n 最大到十万，时限一秒", beats["title"])
        for s in ("n 等于六时，第一行六次，下一行五次", "最后一行一次，一共二十一次", "n 乘 n 加一再除以二",
                  "三 n 平方加一百 n 加五百"):
            self.assertIn(s, beats["count"])
        for s in ("n 等于一百万", "log n 大约二十", "n 是一百万", "n log n 约两千万", "n 平方是一万亿",
                  "整整六格，也就是一百万倍"):
            self.assertIn(s, beats["levels"])
        for s in ("一千万到一亿次", "n 不超过十，可以全排列；二十，枚举子集；一百，n 的立方；一千，n 平方；十万，n log n；一百万，只能线性",
                  "一百万到四百万之间", "n 等于十万，两重循环要五十亿次"):
            self.assertIn(s, beats["budget"])
        for s in ("八字节指针加二十八字节对象，一百万个就是三十多兆", "六十四到二百五十六兆", "一亿个格子，光指针就要八百兆"):
            self.assertIn(s, beats["space"])
        for s in ("二十万个数，查两百次", "约两千万次，set 只查两百次", "零点六秒对万分之一秒，差了三个数量级"):
            self.assertIn(s, beats["hidden"])
        for s in ("一百以内", "然后是五和七", "剩下的二十五个"):
            self.assertIn(s, beats["sieve"])
        for s in ("试除做了二百三十六次除法，筛法只划了一百零四次", "试除要六千七百多万次，筛法约二百一十二万次",
                  "差了三十多倍"):
            self.assertIn(s, beats["versus"])


if __name__ == "__main__":
    unittest.main()
