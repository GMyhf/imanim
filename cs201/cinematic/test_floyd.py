"""Floyd 片数字的独立对撞：讲义第 1 章结果矩阵与答案、讲义图 7.21、n 次 Dijkstra、Bellman-Ford、穷举简单路径、
错误循环次序的反例、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_floyd
"""
import heapq
import itertools
import json
from pathlib import Path
import random
import unittest

import floyddata as D

HERE = Path(__file__).resolve().parent
INF = float("inf")


def dijkstra_all(n, edges):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    out = []
    for s in range(n):
        dist = [INF] * n
        dist[s] = 0
        pq = [(0, s)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in adj[u]:
                if d + w < dist[v]:
                    dist[v] = d + w
                    heapq.heappush(pq, (d + w, v))
        out.append(dist)
    return out


def bellman_all(n, edges):
    out = []
    for s in range(n):
        d = [INF] * n
        d[s] = 0
        for _ in range(n - 1):
            for u, v, w in edges:
                if d[u] + w < d[v]:
                    d[v] = d[u] + w
        out.append(d)
    return out


def brute(n, edges):
    """穷举所有简单路径。"""
    w = {(u, v): c for u, v, c in edges}
    best = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            others = [x for x in range(n) if x not in (i, j)]
            for r in range(len(others) + 1):
                for mid in itertools.permutations(others, r):
                    seq = (i, *mid, j)
                    if all((a, b) in w for a, b in zip(seq, seq[1:])):
                        best[i][j] = min(best[i][j], sum(w[(a, b)] for a, b in zip(seq, seq[1:])))
    return best


class FloydTest(unittest.TestCase):
    def test_lecture_rumor(self):
        # 讲义第 1 章「Floyd 算完之后的结果矩阵」与答案 B3、10
        d, _, _ = D.floyd_trace()
        self.assertEqual(d, [[0, 8, INF, 4, 3], [13, 0, INF, 17, 8], [6, 7, 0, 10, 2],
                             [INF, INF, INF, 0, INF], [5, 5, INF, 9, 0]])
        best, ecc = D.best_source()
        self.assertEqual(best, 2)
        self.assertEqual(ecc, [INF, INF, 10, INF, INF])
        self.assertEqual(D.route(1, 3), [1, 4, 0, 3])          # 讲义：B2→B5→B1→B4 = 8+5+4 = 17

    def test_changes_per_round(self):
        _, snaps, ch = D.floyd_trace()
        self.assertEqual(ch, [[(4, 3, INF, 9)], [], [], [], [(1, 0, INF, 13), (1, 3, INF, 17)]])
        self.assertEqual(snaps[4][4][3], 9)                    # 「这个九」在最后一轮开始前已就位
        self.assertEqual(D.adjacency()[4][3], INF)

    def test_lecture_fig_7_21(self):
        edges = [(0, 2, 2), (1, 0, 5), (1, 2, 8), (2, 1, 3)]
        d, _, ch = D.floyd_trace(3, edges)
        self.assertEqual(d, [[0, 5, 2], [5, 0, 7], [8, 3, 0]])
        self.assertEqual([[(i, j, new) for i, j, _, new in c] for c in ch], [[(1, 2, 7)], [(2, 0, 8)], [(0, 1, 5)]])
        self.assertEqual(D.route(2, 0, 3, edges), [2, 1, 0])

    def test_wrong_order(self):
        right, _, _ = D.floyd_trace(D.CHAIN_N, D.CHAIN)
        wrong = D.floyd_wrong_order()
        self.assertEqual(right[0][1], 3)
        self.assertEqual(wrong[0][1], INF)

    def test_random_oracles(self):
        rng = random.Random(201)
        for _ in range(150):
            n = rng.randint(1, 6)
            edges = [(u, v, rng.randint(0, 9)) for u in range(n) for v in range(n) if u != v and rng.random() < 0.4]
            d, _, _ = D.floyd_trace(n, edges)
            self.assertEqual(d, dijkstra_all(n, edges))
            self.assertEqual(d, brute(n, edges))
            self.assertEqual(D.path(n, edges)[0], d)
            for i in range(n):
                for j in range(n):
                    r = D.route(i, j, n, edges)
                    if d[i][j] == INF:
                        self.assertIsNone(r)
                    else:
                        w = {(u, v): c for u, v, c in edges}
                        self.assertEqual(sum(w[(a, b)] for a, b in zip(r, r[1:])), d[i][j])
        # 负权边（无负环）：Floyd 与 Bellman-Ford 一致
        for _ in range(100):
            n = rng.randint(2, 6)
            perm = list(range(n))
            rng.shuffle(perm)
            edges = [(u, v, rng.randint(-5, 9)) for u in range(n) for v in range(n)
                     if u != v and perm[u] < perm[v] and rng.random() < 0.5]     # DAG：一定没有负环
            self.assertEqual(D.floyd_trace(n, edges)[0], bellman_all(n, edges))

    def test_narration_numbers(self):
        s = json.loads((HERE / "floyd.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in s["beats"]}
        w = {(u, v): c for u, v, c in D.EDGES}
        self.assertEqual((w[(0, 4)], w[(4, 0)]), (3, 5))
        self.assertIn("一号传给五号要三，五号传回一号要五", nar["problem"])
        self.assertIn("五加四等于九", nar["run"])
        self.assertIn("八加五，十三", nar["run"])
        self.assertIn("八加九，十七", nar["run"])
        self.assertIn("最大是十", nar["answer"])
        self.assertIn("答案是三号", nar["answer"])
        self.assertIn("真正的答案是三", nar["order"])
        self.assertEqual(len(D.EDGES), 10)


if __name__ == "__main__":
    unittest.main()
