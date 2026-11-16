"""二叉树周游片数字的独立对撞：讲义表格（图5.5 三种序列、层次序列、图5.6 前缀/后缀式、OJ24750 样例）、
独立写的迭代周游（显式栈）、随机树往返重建、穷举小树验证「单个序列 / 前序+后序 不唯一」，以及旁白稿里写死的数。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_trav
"""
import itertools
import json
import random
import unittest
from pathlib import Path

import travdata as D


def iter_pre(tree, root):                       # 讲义「非递归周游」前序：弹出即访问，先压右再压左
    out, st = [], [root] if root else []
    while st:
        n = st.pop()
        out.append(n)
        l, r = tree[n]
        if r:
            st.append(r)
        if l:
            st.append(l)
    return out


def iter_in(tree, root):
    out, st, cur = [], [], root
    while cur or st:
        while cur:
            st.append(cur)
            cur = tree[cur][0]
        cur = st.pop()
        out.append(cur)
        cur = tree[cur][1]
    return out


def iter_post(tree, root):
    out, st = [], [(root, False)] if root else []
    while st:
        n, ex = st.pop()
        if ex:
            out.append(n)
        else:
            st.append((n, True))
            l, r = tree[n]
            if r:
                st.append((r, False))
            if l:
                st.append((l, False))
    return out


def random_tree(n, rng):
    keys = [chr(65 + i) if i < 26 else f"k{i}" for i in range(n)]
    rng.shuffle(keys)
    tree = {keys[0]: [None, None]}
    for k in keys[1:]:
        cur = keys[0]
        while True:
            side = rng.randrange(2)
            if tree[cur][side] is None:
                tree[cur][side] = k
                tree[k] = [None, None]
                break
            cur = tree[cur][side]
    return {k: tuple(v) for k, v in tree.items()}, keys[0]


def all_shapes(n):
    """n 个结点的所有二叉树形状（结点按前序编号），用于穷举。"""
    if n == 0:
        return [None]
    out = []
    for left in range(n):
        for L in all_shapes(left):
            for R in all_shapes(n - 1 - left):
                out.append((L, R))
    return out


def label(shape, names):
    """形状 + 按前序依次给名字 → dict 树。"""
    tree, it = {}, iter(names)

    def go(s):
        if s is None:
            return None
        k = next(it)
        tree[k] = None
        l = go(s[0])
        r = go(s[1])
        tree[k] = (l, r)
        return k
    root = go(shape)
    return tree, root


class TravTest(unittest.TestCase):
    def test_lecture_tables(self):
        self.assertEqual(" ".join(D.PRE), "A B D E G C F H I")
        self.assertEqual(" ".join(D.IN), "D B G E A C H F I")
        self.assertEqual(" ".join(D.POST), "D G E B H I F C A")
        self.assertEqual(" ".join(D.LEVEL), "A B C D E F G H I")
        self.assertEqual([D.label(x) for x in D.order("pre", D.EXPR, D.EXPR_ROOT)], list("+A×B+CD"))
        self.assertEqual([D.label(x) for x in D.order("in", D.EXPR, D.EXPR_ROOT)], list("A+B×C+D"))
        self.assertEqual([D.label(x) for x in D.order("post", D.EXPR, D.EXPR_ROOT)], list("ABCD+×+"))

    def test_oj24750(self):
        self.assertEqual(D.preorder_of("BADC", "BDCA"), "ABCD")       # 题目样例
        self.assertEqual(D.preorder_of(D.IN, D.POST), D.PRE)             # 讲义：输出 ABDEGCFHI

    def test_euler_three_times(self):
        ev = D.euler()
        self.assertEqual(len(ev), 3 * len(D.FIG55))
        for side, seq in ((0, D.PRE), (1, D.IN), (2, D.POST)):
            self.assertEqual("".join(n for n, s in ev if s == side), seq)

    def test_iterative_matches_recursive_random(self):
        rng = random.Random(7)
        for _ in range(300):
            tree, root = random_tree(rng.randint(1, 30), rng)
            self.assertEqual(iter_pre(tree, root), D.order("pre", tree, root))
            self.assertEqual(iter_in(tree, root), D.order("in", tree, root))
            self.assertEqual(iter_post(tree, root), D.order("post", tree, root))
            lv = [s[0] for s in D.level_order(tree, root)]
            # 层次序列：按 (深度, 中序名次) 排序就是逐层从左到右
            depth, pos = {}, {k: i for i, k in enumerate(D.order("in", tree, root))}

            def go(n, d):
                if n:
                    depth[n] = d
                    go(tree[n][0], d + 1)
                    go(tree[n][1], d + 1)
            go(root, 0)
            self.assertEqual(lv, sorted(tree, key=lambda k: (depth[k], pos[k])))

    def test_rebuild_roundtrip_random(self):
        rng = random.Random(11)
        for _ in range(300):
            tree, root = random_tree(rng.randint(1, 26), rng)
            ino, post = "".join(D.order("in", tree, root)), "".join(D.order("post", tree, root))
            shape, pre, trace = D.rebuild(ino, post)
            self.assertEqual(shape, tree)
            self.assertEqual(pre, "".join(D.order("pre", tree, root)))
            self.assertEqual(trace[0]["root"], root)

    def test_rebuild_film_trace(self):
        shape, pre, trace = D.rebuild(D.IN, D.POST)
        self.assertEqual(shape, D.FIG55)
        t0 = trace[0]
        self.assertEqual((t0["root"], t0["k"]), ("A", 4))                # 左边四个、右边四个
        self.assertEqual(D.POST[:4], "DGEB")
        self.assertEqual(D.POST[4:8], "HIFC")
        self.assertEqual(len(trace), 9)

    def test_uniqueness_by_exhaustion(self):
        for n in range(1, 7):
            trees = [label(s, "ABCDEFG"[:n]) for s in all_shapes(n)]
            seqs = [{k: "".join(D.order(k, t, r)) for k in ("pre", "in", "post")} for t, r in trees]
            # 中序 + 前序、中序 + 后序：两两不同
            self.assertEqual(len({(s["in"], s["pre"]) for s in seqs}), len(trees))
            self.assertEqual(len({(s["in"], s["post"]) for s in seqs}), len(trees))
            if n >= 2:      # 前序 + 后序：有撞车
                self.assertLess(len({(s["pre"], s["post"]) for s in seqs}), len(trees))
        # 旁白里的两个例子
        lc = {"A": ("B", None), "B": ("C", None), "C": (None, None)}
        rc = {"A": (None, "B"), "B": (None, "C"), "C": (None, None)}
        self.assertEqual(D.order("pre", lc, "A"), D.order("pre", rc, "A"))
        t1, t2 = {"A": ("B", None), "B": (None, None)}, {"A": (None, "B"), "B": (None, None)}
        for k in ("pre", "post"):
            self.assertEqual(D.order(k, t1, "A"), D.order(k, t2, "A"))
        self.assertEqual(D.order("pre", t1, "A"), ["A", "B"])
        self.assertEqual(D.order("post", t1, "A"), ["B", "A"])
        self.assertNotEqual(D.order("in", t1, "A"), D.order("in", t2, "A"))

    def test_costs_and_narration(self):
        self.assertEqual(D.levels(D.FIG55, D.ROOT), 4)                  # 递归栈深 = 树高 4 层
        self.assertEqual(D.widest(D.FIG55, D.ROOT), 3)                  # 队列：最宽一层 3 个
        self.assertEqual(max(len(s[2]) for s in D.level_order()) , 3)   # 队列实际最长 3
        n = json.loads((Path(__file__).parent / "trav.json").read_text(encoding="utf-8"))
        text = {b["id"]: b["narration"] for b in n["beats"]}
        self.assertIn("这里是 A", text["rebuild"])
        self.assertIn("左边四个结点是左子树，右边四个是右子树", text["rebuild"])
        self.assertIn("六种排法", text["three"])
        self.assertEqual(len(list(itertools.permutations("tLR"))), 6)
        self.assertEqual(sum(1 for p in itertools.permutations("tLR") if p.index("L") < p.index("R")), 3)
        self.assertIn("三次", text["contour"])


if __name__ == "__main__":
    unittest.main()
