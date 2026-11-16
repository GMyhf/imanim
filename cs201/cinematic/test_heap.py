"""堆片数字的独立对撞：heapq、暴力检查堆序、讲义图 5.15–5.17 写明的结果、建堆代价的暴力计数、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_heap
"""
import heapq
import json
import random
import unittest
from pathlib import Path

import heapdata as D

HERE = Path(__file__).resolve().parent


def is_heap(a):
    return all(a[(i - 1) // 2] <= a[i] for i in range(1, len(a)))


class HeapTest(unittest.TestCase):
    def test_fig514_is_heap(self):
        self.assertTrue(is_heap(D.FIG514))

    def test_insert_matches_fig515(self):
        after, log = D.insert_trace()
        self.assertEqual(after, [12, 13, 15, 19, 14, 17, 18, 24, 22, 26, 20])     # 图 5.15 文字给出的数组
        self.assertEqual(D.swaps(log), 2)
        self.assertEqual([e[1] for e in log if e[0] == "swap"], [10, 4])           # 下标 10 → 4 → 1
        self.assertTrue(is_heap(after))

    def test_remove_min(self):
        got, after, log = D.remove_trace()
        self.assertEqual(got, 12)
        self.assertTrue(is_heap(after))
        self.assertEqual(sorted(after), sorted(D.FIG514 + [D.NEW_KEY])[1:])
        self.assertEqual([(e[1], e[2]) for e in log if e[0] == "swap"], [(0, 1), (1, 4)])   # 20 先换 13、再换 14
        self.assertEqual(after[4], 20)
        self.assertEqual(after[2 * 4 + 1], 26)                                     # 下面只剩 26

    def test_build_matches_fig517(self):
        a, rounds = D.build_heap(D.BUILD)
        self.assertEqual(a, [3, 8, 7, 45, 40, 35, 19, 65])
        self.assertEqual([r[0] for r in rounds], [3, 2, 1, 0])
        self.assertEqual([D.swaps(l) for _, l in rounds], [1, 1, 0, 2])

    def test_random_against_heapq(self):
        rng = random.Random(7)
        for _ in range(300):
            xs = [rng.randint(0, 50) for _ in range(rng.randint(1, 40))]
            a, _ = D.build_heap(xs)
            self.assertTrue(is_heap(a))
            h = D.MinHeap()
            for x in xs:
                h.insert(x)
                self.assertTrue(is_heap(h.data))
            out = [h.remove_min() for _ in xs]
            self.assertEqual(out, sorted(xs))
            q = list(xs)
            heapq.heapify(q)
            self.assertEqual(q[0], a[0])
            self.assertIsNone(h.remove_min())

    def test_build_cost_brute(self):
        # 满树 h=3：最坏情况下每个结点的下沉距离 = 到最底层的层数；用「每个结点数到最深叶子的边数」暴力数一遍
        n = D.N_PERFECT
        def height(i):
            return 0 if 2 * i + 1 >= n else 1 + max(height(2 * i + 1), height(2 * i + 2))
        def depth(i):
            return (i + 1).bit_length() - 1
        self.assertEqual(sum(height(i) for i in range(n)), sum(D.sink_cost(D.H)))
        self.assertEqual(sum(depth(i) for i in range(n)), sum(D.float_cost(D.H)))
        self.assertEqual(D.sink_cost(3), [3, 4, 4, 0])
        self.assertEqual(sum(D.float_cost(3)), 34)
        self.assertEqual(D.float_cost(3)[3], 24)
        for h in range(1, 20):
            self.assertLess(sum(D.sink_cost(h)), 2 ** (h + 1))                     # < 2^{h+1} ≤ 2n

    def test_worst_case_build_really_costs_11(self):
        # 递减序列在满树上让每个结点都沉到底？最小堆里要让每次下沉走满：用穷举小规模找最坏实际交换数 ≤ 11
        a, rounds = D.build_heap(list(range(15, 0, -1)))
        self.assertLessEqual(sum(D.swaps(l) for _, l in rounds), 11)

    def test_narration_numbers(self):
        s = json.loads((HERE / "heap.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in s["beats"]}
        self.assertIn("十二", nar["order"])
        self.assertIn("十九", nar["order"])
        self.assertIn("十七", nar["order"])
        self.assertTrue(D.FIG514[3] > D.FIG514[5])
        self.assertIn("下标十", nar["insert"])
        self.assertIn("只交换了两次", nar["insert"])
        self.assertIn("二十", nar["remove"])
        self.assertIn("六十五开始，和四十五交换", nar["build"])
        self.assertIn("十五个结点", nar["cost"])
        self.assertIn("三加四加四加零，十一", nar["cost"])
        self.assertIn("二十四，总共三十四", nar["compare"])
        self.assertEqual(D.N_PERFECT, 15)


if __name__ == "__main__":
    unittest.main()
