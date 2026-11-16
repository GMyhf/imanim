"""二叉搜索树片数字的独立对撞：讲义图 5.11 的中序与深度、图 5.12/5.13 的删除结果、随机插删对撞 Python 集合、
BST 性质与 AVL 平衡的暴力检查、晴问 9.5 样例（5 2 3 6 8 → 3 2 6 5 8）、OJ22275 样例，以及旁白稿里写死的数。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_bst
"""
import json
import random
import unittest
from pathlib import Path

import bstdata as B


def is_bst(n, lo=float("-inf"), hi=float("inf")):
    if n is None:
        return True
    return lo < n.value < hi and is_bst(n.left, lo, n.value) and is_bst(n.right, n.value, hi)


def heights_ok(n):
    """返回 (是否处处平衡, 高度)。"""
    if n is None:
        return True, 0
    a, ha = heights_ok(n.left)
    b, hb = heights_ok(n.right)
    return a and b and abs(ha - hb) <= 1, 1 + max(ha, hb)


def postorder_of(pre):                          # OJ22275 讲义解法（原样）
    out = []
    i = 0

    def build(lo, hi):
        nonlocal i
        if i == len(pre) or not (lo < pre[i] < hi):
            return
        root = pre[i]
        i += 1
        build(lo, root)
        build(root, hi)
        out.append(root)
    build(float('-inf'), float('inf'))
    return out


def post(n):
    return [] if n is None else post(n.left) + post(n.right) + [n.value]


def pre(n):
    return [] if n is None else [n.value] + pre(n.left) + pre(n.right)


class BSTTest(unittest.TestCase):
    def setUp(self):
        self.F = B.film()
        self.text = {b["id"]: b["narration"] for b in json.loads(
            (Path(__file__).parent / "bst.json").read_text(encoding="utf-8"))["beats"]}

    def test_fig511(self):
        t = B.build(B.KEYS)
        self.assertEqual(t.inorder(), [5, 19, 20, 35, 50, 52, 53, 55, 88, 92, 100])
        self.assertEqual(B.levels(t.root), 5)               # 讲义：深度 4（50→55→100→88→92，按边数）
        self.assertTrue(is_bst(t.root))
        self.assertEqual(len(B.KEYS), 11)

    def test_lecture_deletions(self):
        t = B.build(B.KEYS)                               # 图 5.12(a)：删 52，右子树的根 53 顶上
        t.remove(52)
        self.assertEqual(B.shape(t.root)[55], (53, 100))
        t = B.build(B.KEYS)                               # 图 5.13：删 55，53 接过 52 与 100，深度仍是 4
        ok, info = t.remove(55)
        self.assertTrue(ok)
        self.assertEqual(info["replacement"], 53)
        self.assertEqual(B.shape(t.root)[53], (52, 100))
        self.assertEqual(B.levels(t.root), 5)

    def test_film_steps(self):
        F = self.F
        self.assertEqual(F["search"][53], (True, [50, 55, 52, 53], None))
        self.assertEqual(F["search"][60][0], False)
        self.assertEqual(F["search"][60][2], (88, "left"))
        (v1, i1, _), (v2, i2, _), (v3, i3, s3) = F["deletes"]
        self.assertEqual((v1, i1["case"]), (5, "leaf"))
        self.assertEqual((v2, i2["case"], i2["replacement"]), (52, "right_only", 53))
        self.assertEqual((v3, i3["case"], i3["replacement"], i3["pred_left"]), (50, "two", 35, 20))
        self.assertEqual(s3[None], 35)
        self.assertEqual(s3[19], (None, 20))               # 20 接到 35 原来的位置
        self.assertEqual(F["after_delete"], sorted(set(B.KEYS) - {5, 52, 50}))
        self.assertEqual(F["chain_levels"], 7)
        self.assertEqual(F["avl_levels"], 3)
        self.assertEqual(F["avl_rotations"], 4)
        self.assertEqual(F["avl_steps"][2][1], [("left", 1, "RR")])     # 插入 3 时绕 1 左旋
        self.assertEqual(F["avl_steps"][-1][2][None], 4)
        self.assertTrue(all(v == 0 for v in F["avl_steps"][-1][3].values()))   # 满二叉树
        v, rots, after, mids, _ = F["lr_steps"][2]
        self.assertEqual(rots, [("left", 2, "LR"), ("right", 5, "LR")])
        self.assertEqual(after[None], 3)
        self.assertEqual(mids[0], {None: 5, 5: (3, None), 3: (2, None), 2: (None, None)})

    def test_random_against_set(self):
        rng = random.Random(3)
        for _ in range(200):
            t, ref = B.BST(), set()
            for _ in range(rng.randint(1, 60)):
                k = rng.randint(0, 40)
                if rng.random() < 0.6:
                    ok, _ = t.insert(k)
                    self.assertEqual(ok, k not in ref)
                    ref.add(k)
                else:
                    ok, _ = t.remove(k)
                    self.assertEqual(ok, k in ref)
                    ref.discard(k)
                self.assertTrue(is_bst(t.root))
                self.assertEqual(t.inorder(), sorted(ref))
            for k in range(-1, 42):
                self.assertEqual(t.contains(k)[0], k in ref)

    def test_avl_random(self):
        rng = random.Random(5)
        for _ in range(200):
            vals = rng.sample(range(1, 500), rng.randint(1, 80))
            a = B.AVL()
            for v in vals:
                a.insert(v)
            ok, h = heights_ok(a.root)
            self.assertTrue(ok)
            self.assertTrue(is_bst(a.root))
            self.assertEqual(B.levels(a.root), h)
            self.assertLessEqual(h, 1.4405 * __import__("math").log2(len(vals) + 2))

    def test_judge_samples(self):
        a = B.AVL()
        for v in (5, 2, 3, 6, 8):                         # 晴问 9.5 样例
            a.insert(v)
        self.assertEqual(a.preorder(), [3, 2, 6, 5, 8])
        self.assertEqual(postorder_of([4, 2, 1, 3, 5]), [1, 3, 2, 5, 4])     # OJ22275 样例
        t = B.build(B.KEYS)
        self.assertEqual(postorder_of(pre(t.root)), post(t.root))

    def test_narration_numbers(self):
        x = self.text
        self.assertIn("比了四次", x["search"])
        self.assertIn("八十八的左边", x["search"])
        self.assertIn("十一个数", x["build"])
        self.assertIn("五十二，让它的右孩子五十三", x["del1"])
        self.assertIn("这里是三十五", x["del2"])
        self.assertIn("左孩子二十", x["del2"])
        self.assertIn("七层", x["chain"])
        self.assertIn("转了四次", x["avl"])
        self.assertIn("只有三层", x["avl"])
        self.assertIn("一的平衡因子是负二", x["avl"])
        bf = B.balance_factors(B.build([1, 2, 3]).root)
        self.assertEqual(bf[1], -2)
        bf = B.balance_factors(B.build([5, 2, 3]).root)
        self.assertEqual((bf[5], bf[2]), (2, -1))           # 五的平衡因子是二，左孩子二往右倾


if __name__ == "__main__":
    unittest.main()
