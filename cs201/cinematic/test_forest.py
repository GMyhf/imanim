"""树与森林片的独立对撞：讲义图 6.5 的对应表与三种周游序列、3.3 节栈还原表、OJ24729 样例，
随机森林上「先根 = 前序、后根 = 中序」与带度数后根次序的往返，以及旁白稿里写死的序列。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_forest
"""
import json
import random
import unittest
from pathlib import Path

import forestdata as D

NARR = " ".join(b["narration"] for b in json.loads((Path(__file__).parent / "forest.json").read_text("utf-8"))["beats"])


def random_forest(rng, n):
    names = [chr(ord("A") + i) for i in range(n)]
    ch, roots = {x: [] for x in names}, []
    for i, x in enumerate(names):
        if i == 0 or rng.random() < 0.25:
            roots.append(x)
        else:
            ch[rng.choice(names[:i])].append(x)
    return ch, roots


def from_binary(shape, root):
    """独立写的逆转换：x 的左孩子及其整条右链都是 x 的孩子；根的右链是各棵树的根。"""
    ch = {k: [] for k in shape}

    def chain(n):
        out = []
        while n is not None:
            out.append(n)
            n = shape[n][1]
        return out
    for k in shape:
        ch[k] = chain(shape[k][0])
    return ch, chain(root)


class ForestTest(unittest.TestCase):
    def test_lecture_table(self):
        # 讲义 1.2 节对应表：结点 → (左 = 首孩子, 右 = 下一兄弟)
        table = {"A": ("B", "G"), "B": (None, "C"), "C": ("E", "D"), "D": (None, None), "E": (None, "F"),
                 "F": (None, None), "G": ("H", None), "H": ("J", "I"), "I": (None, None), "J": (None, None)}
        self.assertEqual(D.BIN, table)
        self.assertEqual(D.BIN_ROOT, "A")

    def test_lecture_sequences(self):
        self.assertEqual("".join(D.PRE), "ABCEFDGHJI")
        self.assertEqual("".join(D.POST), "BEFCDAJHIG")
        self.assertEqual("".join(D.LEVEL), "AGBCDHIEFJ")
        self.assertEqual("".join(D.BIN_LEVEL), "ABGCHEDJIF")
        self.assertEqual(D.BIN_PRE, D.PRE)
        self.assertEqual(D.BIN_IN, D.POST)
        self.assertNotEqual(D.BIN_LEVEL, D.LEVEL)
        self.assertEqual(D.traverse(D.forest_via_oj()), ("ABCEFDGHJI", "BEFCDAJHIG"))

    def test_oj24729_sample(self):
        self.assertEqual(D.traverse(D.build_tree("A(B(E),C(F,G),D(H(I)))")), ("ABECFGDHI", "EBFGCIHDA"))

    def test_degree_stack_table(self):
        # 讲义 3.3 节表格：每步之后的栈（底 → 顶）
        want = ["B", "BE", "BEF", "BC", "BCD", "A", "AJ", "AH", "AHI", "AG"]
        ch, roots, snaps = D.REBUILD
        self.assertEqual(["".join(s[3]) for s in snaps], want)
        self.assertEqual(roots, D.ROOTS)
        self.assertEqual(ch, D.CHILDREN)

    def test_connect_cut(self):
        self.assertEqual(set(D.sibling_edges()), {("A", "G"), ("B", "C"), ("C", "D"), ("E", "F"), ("H", "I")})
        self.assertEqual(set(D.cut_edges()), {("A", "C"), ("A", "D"), ("C", "F"), ("G", "I")})
        kept = set(D.parent_edges()) - set(D.cut_edges())
        # 留下的父子线 = 二叉树的左枝，兄弟线 = 右枝
        self.assertEqual(kept, {(k, l) for k, (l, r) in D.BIN.items() if l})
        self.assertEqual(set(D.sibling_edges()), {(k, r) for k, (l, r) in D.BIN.items() if r})

    def test_random_forests(self):
        rng = random.Random(24729)
        for _ in range(500):
            ch, roots = random_forest(rng, rng.randint(1, 14))
            shape, root = D.to_binary(ch, roots)
            self.assertEqual(D.binary_order("pre", shape, root), D.forest_order("pre", ch, roots))
            self.assertEqual(D.binary_order("in", shape, root), D.forest_order("post", ch, roots))
            self.assertEqual(from_binary(shape, root), (ch, roots))
            back_ch, back_roots, _ = D.rebuild_from_degrees(D.degree_postorder(ch, roots))
            self.assertEqual((back_ch, back_roots), (ch, roots))
            if len(roots) == 1:                     # 单棵树：OJ 解法的括号串往返
                self.assertEqual(D.traverse(D.build_tree(D.bracket(roots[0], ch))),
                                 ("".join(D.forest_order("pre", ch, roots)), "".join(D.forest_order("post", ch, roots))))
                self.assertIsNone(shape[root][1])   # 单棵树转成的二叉树，根没有右孩子

    def test_narration(self):
        for seq in (D.PRE, D.POST, D.LEVEL):
            self.assertIn(" ".join(seq), NARR)
        self.assertIn("A B G C H 开头", NARR)
        self.assertEqual(D.BIN_LEVEL[:5], list("ABGCH"))
        for x in ("B 连 C", "C 连 D", "E 连 F", "H 连 I", "A 到 C、A 到 D", "C 到 F", "G 到 I"):
            self.assertIn(x, NARR)
        self.assertIn("A 和 G 两棵树", NARR)


if __name__ == "__main__":
    unittest.main()
