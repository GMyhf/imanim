"""快速排序片数字的独立对撞：插桩版与讲义原版逐结果一致、sorted()、二叉搜索树同构、暴力数比较次数、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_qsort
"""
import json
from pathlib import Path
import random
import unittest

import qsortdata as Q


def bst_depths(seq):
    """把数依次插入二叉搜索树（相等进右），返回 {值: 深度}（值互不相同时用）。"""
    root, depth = None, {}
    kids = {}
    for x in seq:
        if root is None:
            root, depth[x] = x, 0
            continue
        cur, d = root, 0
        while True:
            side = 0 if x < cur else 1
            nxt = kids.get((cur, side))
            d += 1
            if nxt is None:
                kids[(cur, side)] = x
                depth[x] = d
                break
            cur = nxt
    return depth


class QSortFacts(unittest.TestCase):
    def test_lecture_output(self):
        want = [1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        for part in (Q.partition_pair, Q.partition_lomuto):
            self.assertEqual(Q.quick_sort(Q.LECTURE_DATA[:], part), want)
        self.assertEqual(Q.full_trace(Q.LECTURE_DATA)[0], want)

    def test_trace_matches_lecture_partition(self):
        rng = random.Random(11)
        for _ in range(500):
            a = [rng.randint(0, 9) for _ in range(rng.randint(1, 12))]
            lo, hi = 0, len(a) - 1
            b, c = a[:], a[:]
            p1 = Q.partition_pair(b, lo, hi)
            p2 = Q.partition_trace(c, lo, hi, [], [0])
            self.assertEqual((p1, b), (p2, c))
            self.assertEqual(Q.full_trace(a)[0], sorted(a))
            self.assertEqual(Q.full_trace(a, "random", rng.randint(0, 99))[0], sorted(a))

    def test_partition_demo(self):
        arr, p, ev, _ = Q.partition_events()
        self.assertEqual(p, 4)
        self.assertEqual(arr[p], 5)
        self.assertTrue(all(x < 5 for x in arr[:p]) and all(x > 5 for x in arr[p + 1:]))
        vals = list(Q.DATA)
        stops = []
        for e in ev:
            if e[0] in ("L", "R"):
                stops.append((e[0], vals[e[1]]))
            elif e[0] == "swap":
                vals[e[1]], vals[e[2]] = vals[e[2]], vals[e[1]]
        # 旁白：左停九、右停四；左停七、右停三；左停八、右退到一
        self.assertEqual(stops, [("L", 9), ("R", 4), ("L", 7), ("R", 3), ("L", 8), ("R", 1)])
        self.assertEqual(sum(1 for e in ev if e[0] == "swap"), 2)

    def test_tree_is_bst(self):
        _, nodes = Q.full_trace(Q.DATA)
        arr = sorted(Q.DATA)
        # 结点 x 坐标 = 最终下标，所以中序读出就是排好的顺序；每个结点左子树的值都小于它、右子树都大于它
        self.assertEqual(len(nodes), len(Q.DATA))
        for lo, hi, p, d, *_ in nodes:
            self.assertTrue(all(arr[k] <= arr[p] for k in range(lo, p)))
            self.assertTrue(all(arr[k] >= arr[p] for k in range(p + 1, hi + 1)))
        self.assertEqual(max(n[3] for n in nodes) + 1, Q.sort_trace(Q.DATA)[3])
        # 讲义 5.6 的「与二叉搜索树同构」说的是 5.1 列表推导版（稳定、保持原次序）：那一版的递归树与依次插入 BST 相同
        def simple_depths(a, d=0, out=None):
            out = {} if out is None else out
            if a:
                out[a[0]] = d
                simple_depths([x for x in a[1:] if x < a[0]], d + 1, out)
                simple_depths([x for x in a[1:] if x >= a[0]], d + 1, out)
            return out
        self.assertEqual(simple_depths(Q.DATA), bst_depths(Q.DATA))
        par = Q.parents(nodes)
        for i, j in enumerate(par):
            if j is not None:
                self.assertEqual(nodes[j][3], nodes[i][3] - 1)

    def test_worst_and_random(self):
        asc = list(range(1, 10))
        _, _, cmp_, depth = Q.sort_trace(asc)
        self.assertEqual((cmp_, depth), (44, 9))
        # 暴力：有序输入时每段 [lo, hi] 左指针比 1 次、右指针一路比到 lo，共 (hi-lo)+1 次
        self.assertEqual(sum((hi - lo) + 1 for lo, hi in [(k, 8) for k in range(8)]), 44)
        _, _, _, d2 = Q.sort_trace(asc, "random", Q.RANDOM_DEMO_SEED)
        self.assertEqual(d2, 4)
        big = Q.big_counts()
        self.assertEqual(big["fixed"], 500499)
        self.assertEqual(big["fixed_depth"], 1000)
        self.assertTrue(11500 <= big["random"] < 12500)        # 旁白：大约一万两千次
        self.assertEqual(big["random_depth"], 25)
        self.assertTrue(Q.recursion_limit_hit(1000))

    def test_narration_numbers(self):
        script = json.loads((Path(__file__).parent / "qsort.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in script["beats"]}
        self.assertIn("二十二个数", nar["title"])
        self.assertEqual(len(Q.LECTURE_DATA), 22)
        self.assertIn("九层深，比较了四十四次", nar["worst"])
        self.assertIn("大约五十万次，递归一千层", nar["worst"])
        self.assertIn("大约一万两千次，递归只有二十五层", nar["random"])
        self.assertIn("五正好站在第五个位置", nar["idea"])
        for s in ("左指针停在九，右指针停在四", "左指针停在七，右指针停在三", "左指针停在八，右指针退到一"):
            self.assertIn(s, nar["partition"])


if __name__ == "__main__":
    unittest.main()
