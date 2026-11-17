"""渗透实验精讲片数字的独立对撞：题面样例、每步 BFS 暴力随机对拍、片中画出的每一步状态、旁白数字。

独立实现不调用 novdata / novpercdata 的算法：渗透用每步 BFS，连通块用另写的「洪水填充」，
路径减半用另写的「每个结点到根的距离」核对。
用法（cwd = cs101/cinematic）：python -m unittest test_novperc
"""
from collections import deque
import json
from pathlib import Path
import random
import unittest

import novpercdata as D

HERE = Path(__file__).resolve().parent
NARR = "".join(b["narration"] for b in json.loads((HERE / "novperc.json").read_text(encoding="utf-8"))["beats"])


def bfs_answer(n, m, ops):
    """每打开一格就从第一行所有打开格出发 BFS（1-based 行列）。"""
    opened = set()
    for k, (r, c) in enumerate(ops):
        opened.add((r - 1, c - 1))
        seen = {(0, j) for j in range(m) if (0, j) in opened}
        q = deque(seen)
        while q:
            i, j = q.popleft()
            if i == n - 1:
                return k + 1
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if (a, b) in opened and (a, b) not in seen:
                    seen.add((a, b))
                    q.append((a, b))
    return -1


def blocks(n, m, opened):
    """洪水填充：返回 {格: 块编号}，以及每块是否碰到第一行 / 最后一行（0-based 格）。"""
    lab, info = {}, []
    for s in sorted(opened):
        if s in lab:
            continue
        lab[s] = len(info)
        q, cells = [s], [s]
        while q:
            i, j = q.pop()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if (a, b) in opened and (a, b) not in lab:
                    lab[(a, b)] = len(info)
                    q.append((a, b))
                    cells.append((a, b))
        info.append((any(i == 0 for i, _ in cells), any(i == n - 1 for i, _ in cells)))
    return lab, info


def kind_brute(n, m, opened):
    """把「同连 TOP 的块」视为一块（TOP 把第一行的块连起来），BOT 同理，给每格分类。"""
    lab, info = blocks(n, m, opened)
    both = any(t and b for t, b in info)            # TOP 与 BOT 只能经某个同时碰到两行的块连起来
    out = {}
    for c, k in lab.items():
        t, b = info[k]
        if both and (t or b):
            out[c] = "both"
        elif t:
            out[c] = "top"
        elif b:
            out[c] = "bot"
        else:
            out[c] = ("free", k)
    return out


class NovPercFacts(unittest.TestCase):
    def test_samples(self):
        self.assertEqual([o for _, o in D.SAMPLES], ["3", "-1"])
        for (inp, out), ops in zip(D.SAMPLES, D.SAMPLE_OPS):
            self.assertEqual(D.inp_of(3, 3, ops), inp)
            self.assertEqual(D.run_io(D.solve_t5, inp), out)
            self.assertEqual(str(bfs_answer(3, 3, ops)), out)

    def test_random_vs_bfs(self):
        rnd = random.Random(31533)
        for _ in range(400):
            n, m = rnd.randint(1, 6), rnd.randint(1, 6)
            cells = [(i, j) for i in range(1, n + 1) for j in range(1, m + 1)]
            rnd.shuffle(cells)
            ops = cells[:rnd.randint(1, len(cells))]
            self.assertEqual(D.run_io(D.solve_t5, D.inp_of(n, m, ops)), str(bfs_answer(n, m, ops)))

    def test_naive_scale(self):
        self.assertEqual(D.CELLS_MAX, 200000)
        self.assertEqual(D.NAIVE_STEPS, 4 * 10 ** 10)                   # 四百亿
        self.assertIn("格子总数不超过二十万", NARR)
        self.assertIn("二十万次，每次走二十万格，就是四百亿步", NARR)

    def test_halving(self):
        fa = dict(D.CHAIN)
        self.assertEqual([fa[k] for k in (5, 4, 3, 2)], [4, 3, 2, 1])
        root, steps = D.halving_trace(fa, D.CHAIN_FROM)
        self.assertEqual(root, 1)
        # 独立按定义手推：x=5 时 fa[5] ← fa[4] = 3，跳到 3；fa[3] ← fa[2] = 1，跳到 1
        self.assertEqual([(s["x"], s["old"], s["new"]) for s in steps], [(5, 4, 3), (3, 2, 1)])
        after = steps[-1]["fa"]
        self.assertEqual(after, {1: 1, 2: 1, 3: 1, 4: 3, 5: 3})

        def dist(f, x):
            d = 0
            while f[x] != x:
                x, d = f[x], d + 1
            return d
        self.assertEqual((dist(fa, 5), dist(after, 5)), (4, 2))
        self.assertEqual((D.depth(fa, 5), D.depth(after, 5)), (4, 2))
        self.assertIn("五指四，四指三，三指二，二指一", NARR)
        self.assertIn("五改挂到三，三改挂到一", NARR)
        self.assertIn("从四步变成两步", NARR)

    def test_walk(self):
        n, m, ops = D.WALK
        self.assertEqual((n, m, len(ops)), (4, 5, 8))
        self.assertIn("四行五列", NARR)
        self.assertEqual(bfs_answer(n, m, ops), 8)
        self.assertEqual(D.run_io(D.solve_t5, D.inp_of(n, m, ops)), "8")
        self.assertIn("答案是八", NARR)
        steps = D.walk_trace(n, m, ops)
        self.assertEqual(len(steps), 8)
        self.assertEqual([s["done"] for s in steps], [False] * 7 + [True])
        opened = set()
        for st, (r, c) in zip(steps, ops):
            opened.add((r - 1, c - 1))
            self.assertEqual(st["cell"], (r - 1, c - 1))
            self.assertEqual(st["u"], (r - 1) * m + (c - 1))
            self.assertEqual((st["top"], st["bot"]), (r == 1, r == n))
            want = kind_brute(n, m, opened)
            got = {c_: (("free", None) if k.startswith("free") else k) for c_, k in st["kind"].items()}
            self.assertEqual(got, {c_: (("free", None) if isinstance(k, tuple) else k) for c_, k in want.items()})
            # 孤立块之间要分得开
            free = [c_ for c_, k in st["kind"].items() if k.startswith("free")]
            for a in free:
                for b in free:
                    self.assertEqual(st["kind"][a] == st["kind"][b], want[a] == want[b])
        # 旁白：前五步蓝块（第一行）、橙块（最后一行）、一个紫格
        k5 = steps[4]["kind"]
        self.assertEqual(sorted(v for v in k5.values() if v.startswith("free")), ["free:12"])
        self.assertEqual(sum(v == "top" for v in k5.values()), 2)
        self.assertEqual(sum(v == "bot" for v in k5.values()), 2)
        # 第六步：下接紫格、左接蓝块
        self.assertEqual(steps[5]["nbr"], [(2, 2), (1, 1)])
        self.assertEqual(k5[(2, 2)], "free:12")
        self.assertEqual(k5[(1, 1)], "top")
        self.assertIn("下接紫格，左接蓝块", NARR)
        # 第七步：第一行最右边，不与蓝块相邻，经 TOP 同块
        self.assertEqual(steps[6]["cell"], (0, m - 1))
        self.assertEqual(steps[6]["nbr"], [])
        self.assertEqual(steps[6]["kind"][(0, m - 1)], "top")
        self.assertIn("第七步在第一行最右边", NARR)
        # 第八步：下接橙块、左接蓝块
        self.assertEqual(steps[7]["nbr"], [(3, 3), (2, 2)])
        self.assertEqual(steps[6]["kind"][(3, 3)], "bot")
        self.assertEqual(steps[6]["kind"][(2, 2)], "top")
        self.assertIn("第八步，下接橙块，左接蓝块", NARR)

    def test_elif_bug(self):
        n, m, ops = D.ONE_ROW
        self.assertEqual(n, 1)
        self.assertEqual(bfs_answer(n, m, ops), 1)
        self.assertEqual(D.run_io(D.solve_t5, D.inp_of(n, m, ops)), "1")
        self.assertEqual(D.run_io(D.solve_t5_elif, D.inp_of(n, m, ops)), "-1")
        self.assertIn("答案是一", NARR)
        self.assertIn("输出负一", NARR)
        # 错误写法只在 n = 1 时出错：随机数据 n ≥ 2 与正确写法一致
        rnd = random.Random(1)
        for _ in range(200):
            n, m = rnd.randint(2, 5), rnd.randint(1, 5)
            cells = [(i, j) for i in range(1, n + 1) for j in range(1, m + 1)]
            rnd.shuffle(cells)
            inp = D.inp_of(n, m, cells)
            self.assertEqual(D.run_io(D.solve_t5_elif, inp), D.run_io(D.solve_t5, inp))

    def test_code_excerpt(self):
        self.assertIn("    if r == 0:\n        union(u, TOP)\n    if r == n - 1:\n        union(u, BOT)\n", D.MAIN_LOOP)
        self.assertNotIn("\n\n", D.MAIN_LOOP)                           # Code 的空行会打乱 code_lines 下标
        self.assertEqual(D.HEAD_LINES, ["TOP, BOT = n * m, n * m + 1  # 两个虚拟结点", "fa = list(range(n * m + 2))"])
        self.assertIn("fa 开 n m 加二个", NARR)

    def test_union_demo(self):
        _, steps = D.halving_trace(D.CHAIN, D.CHAIN_FROM)
        fa = dict(steps[-1]["fa"])
        a, b = D.UNION_DEMO
        fa[a] = a
        got = D.union_apply(fa, a, b)
        want = dict(fa)
        want[a] = b                                     # a、b 都是根：fa[a] = b，别的不动
        self.assertEqual(got, want)
        self.assertEqual(D.UNION_LINES[1].strip(), "fa[find(a)] = find(b)")
        self.assertEqual(D.FIND_LINES[2].strip(), "fa[x] = fa[fa[x]]  # 路径减半")

    def test_naive_layers(self):
        g = D.NAIVE_GRID
        n, m = len(g), len(g[0])
        opened = {(i, j) for i in range(n) for j in range(m) if g[i][j] == "."}
        lab, _ = blocks(n, m, opened)
        reach = {c for c in opened if any(lab[c] == lab[(0, j)] for j in range(m) if (0, j) in opened)}
        layers = D.bfs_layers(g)
        flat = [c for L in layers for c in L]
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(set(flat), reach)
        self.assertEqual(layers[0], [(0, j) for j in range(m) if g[0][j] == "."])


if __name__ == "__main__":
    unittest.main()
