"""拓扑排序片数字的独立对撞：讲义手算表、讲义 DFS 输出、画面代码、穷举全排列验证、随机图判环、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_topo
"""
from collections import deque
import itertools
import json
from pathlib import Path
import random
import unittest

import topodata as D

HERE = Path(__file__).resolve().parent


def is_topo(order, n, edges):
    if order is None or sorted(order) != list(range(n)):
        return False
    pos = {v: k for k, v in enumerate(order)}
    return all(pos[u] < pos[v] for u, v in edges)


def has_cycle(n, edges):
    """独立判环：Floyd–Warshall 式传递闭包，看有没有点能走回自己。"""
    r = [[False] * n for _ in range(n)]
    for u, v in edges:
        r[u][v] = True
    for k in range(n):
        for i in range(n):
            if r[i][k]:
                for j in range(n):
                    if r[k][j]:
                        r[i][j] = True
    return any(r[i][i] for i in range(n))


def shown_code():
    ns = {"deque": deque}
    exec(D.KAHN_CODE, ns)  # noqa: S102 画面上展示的代码原样执行
    return ns["topo_sort"]


def random_graph(rng, n, p, dag=True):
    perm = list(range(n))
    rng.shuffle(perm)
    edges = []
    for a in range(n):
        for b in range(n):
            if a != b and rng.random() < p and (not dag or perm[a] < perm[b]):
                edges.append((a, b))
    return edges


class TopoTest(unittest.TestCase):
    def test_lecture_table(self):
        # 讲义「手算：图 7.17 上逐步执行 topological_sort()」
        res, ev, _ = D.kahn_trace()
        self.assertEqual(res, [0, 1, 7, 2, 4, 8, 3, 5, 6])
        self.assertEqual(ev[0][2], [0, 1])
        self.assertEqual(D.indegrees(), [0, 0, 2, 2, 1, 2, 2, 1, 1])
        steps = D.kahn_steps()
        self.assertEqual([s[0] for s in steps], res)
        self.assertEqual(steps[1][1], [(2, 1, 0), (3, 2, 1), (4, 1, 0)])
        self.assertEqual(steps[1][3], [7, 2, 4])
        self.assertEqual(steps[6][2], [5, 6])
        self.assertEqual(len(D.EDGES), 11)

    def test_lecture_dfs(self):
        topo, finish, _ = D.dfs_topo_trace()
        self.assertEqual(topo, [1, 4, 0, 7, 8, 2, 3, 6, 5])          # 讲义 console 输出
        self.assertEqual(finish, [5, 6, 3, 2, 8, 7, 0, 4, 1])
        self.assertTrue(is_topo(topo, D.N, D.EDGES))

    def test_caption_sequences_valid(self):
        for seq in ([0, 1, 2, 3, 4, 5, 7, 8, 6], [0, 7, 8, 1, 4, 2, 3, 6, 5]):
            self.assertTrue(is_topo(seq, D.N, D.EDGES))
            self.assertNotEqual(seq, D.kahn_trace()[0])

    def test_count_all_orders(self):
        # 穷举：Kahn 结果确实是拓扑序之一，且拓扑序不唯一
        good = [p for p in itertools.permutations(range(D.N)) if is_topo(list(p), D.N, D.EDGES)]
        self.assertIn(tuple(D.kahn_trace()[0]), good)
        self.assertGreater(len(good), 1)

    def test_cycle(self):
        edges = D.EDGES + [D.CYCLE_EDGE]
        self.assertTrue(has_cycle(D.N, edges))
        res, out, stuck = D.stuck_after_cycle()
        self.assertIsNone(res)
        self.assertEqual(out, [1, 4])
        self.assertEqual(len(stuck), 7)
        self.assertTrue(all(d > 0 for d in stuck.values()))
        self.assertEqual(D.indegrees(edges)[0], 1)
        self.assertIsNone(D.dfs_topo_trace(D.graph_dict(edges))[0])
        # 编译原理（5）不在环上，却也卡住
        cyc = D.cycle_edges()
        self.assertNotIn(5, {x for e in cyc for x in e})
        self.assertIn(5, stuck)

    def test_shown_code_and_random(self):
        f = shown_code()
        self.assertEqual(f(D.N, D.EDGES), D.kahn_trace()[0])
        rng = random.Random(2026)
        for _ in range(300):
            n = rng.randint(1, 9)
            dag = rng.random() < 0.6
            edges = random_graph(rng, n, rng.uniform(0.1, 0.5), dag)
            cyc = has_cycle(n, edges)
            k, _, _ = D.kahn_trace(edges, n)
            g = {v: [] for v in range(n)}
            for u, v in edges:
                g[u].append(v)
            dfs, _, _ = D.dfs_topo_trace(g)
            self.assertEqual(k is None, cyc)
            self.assertEqual(dfs is None, cyc)
            self.assertEqual(f(n, edges) is None, cyc)
            if not cyc:
                self.assertTrue(is_topo(k, n, edges))
                self.assertTrue(is_topo(dfs, n, edges))
                self.assertEqual(f(n, edges), k)

    def test_sy403_samples(self):
        # 讲义 sy403 样例：样例 2 不能学的课程数为 3
        e1 = [(0, 1), (0, 2), (0, 3), (1, 2), (3, 2)]
        self.assertTrue(is_topo(D.kahn_trace(e1, 4)[0], 4, e1))
        e2 = [(0, 1), (1, 2), (2, 3), (3, 1)]
        _, ev, _ = D.kahn_trace(e2, 4)
        self.assertEqual(4 - sum(1 for e in ev if e[0] == "pop"), 3)

    def test_narration_numbers(self):
        s = json.loads((HERE / "topo.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in s["beats"]}
        self.assertIn("九门课，十一条边", nar["dag"])
        self.assertIn("离散数学入度是二", nar["indeg"])
        self.assertIn("剩下七门课", nar["cycle"])
        self.assertIn("输出不足九个", nar["cycle"])
        # run 段按讲义手算表的出队顺序念
        names = {0: "高数", 1: "程序设计", 7: "物理", 2: "离散", 4: "算法语言", 8: "计算机原理", 3: "数据结构",
                 5: "编译", 6: "操作系统"}
        text = nar["run"]
        at = 0
        for v in D.kahn_trace()[0]:
            key = names[v] + ("出队" if v not in (5, 6) else "")
            k = text.find(key, at)
            self.assertGreaterEqual(k, 0, key)
            at = k + len(key)
        self.assertIn("编译、操作系统依次出队", text)
        # dfs 段的结束顺序
        self.assertEqual([D.NAMES[v] for v in D.dfs_topo_trace()[1]][:2], ["编译原理", "操作系统"])


if __name__ == "__main__":
    unittest.main()
