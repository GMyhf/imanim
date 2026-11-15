"""Dijkstra 片数字的独立对撞：讲义输出、Floyd / Bellman-Ford、事件序列与旁白一致。

用法（cwd = cs101/cinematic）：python -m unittest test_dijkstra
"""
import json
from pathlib import Path
import random
import unittest

import dijkstradata as D

INF = float("inf")


def floyd(n, edges):
    d = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    for u, v, w in edges:
        d[u][v] = min(d[u][v], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def grid_bellman(grid, start):
    n, m = len(grid), len(grid[0])
    d = {(i, j): INF for i in range(n) for j in range(m)}
    d[start] = 0
    for _ in range(n * m):
        for (x, y), v in list(d.items()):
            if v == INF:
                continue
            for dx, dy in D.DIRS:
                q = (x + dx, y + dy)
                if q in d:
                    c = v + abs(grid[q[0]][q[1]] - grid[x][y])
                    if c < d[q]:
                        d[q] = c
    return d


class DijkstraFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(D.dijkstra_trace()[0], [0, 3, 1, 4])
        self.assertEqual(D.mountain_trace()[0], 6)

    def test_against_floyd(self):
        self.assertEqual(D.dijkstra_trace()[0], floyd(D.N, D.EDGES)[0])
        rng = random.Random(3)
        for _ in range(200):
            n = rng.randint(1, 8)
            edges = [(rng.randrange(n), rng.randrange(n), rng.randint(0, 9)) for _ in range(rng.randint(0, 20))]
            adj = [[] for _ in range(n)]
            for u, v, w in edges:
                adj[u].append((v, w))
            self.assertEqual(D.dijkstra_trace(n, adj, 0)[0], floyd(n, edges)[0])

    def test_events_match_narration(self):
        _, ev = D.dijkstra_trace()
        self.assertEqual([e for e in ev if e[0] != "relax"],
                         [("pop", 0, 0), ("pop", 1, 2), ("pop", 3, 1), ("stale", 4, 1), ("pop", 4, 3), ("stale", 6, 3)])
        self.assertEqual([(e[2], e[3]) for e in ev if e[0] == "relax"], [(1, 4), (2, 1), (1, 3), (3, 6), (3, 4)])

    def test_bfs_wrong(self):
        self.assertEqual(D.bfs_hops_cost()[1], 4)          # 广搜第一层碰到一号点，记下 4
        self.assertNotEqual(D.bfs_hops_cost(), D.dijkstra_trace()[0])

    def test_mountain(self):
        ans, ev, _ = D.mountain_trace()
        ref = grid_bellman(D.GRID, D.START)
        self.assertEqual(ans, ref[D.GOAL])
        for e in ev:
            if e[0] == "pop":
                self.assertEqual(e[1], ref[e[2]])           # 第一次出堆的距离就是最短距离
        path, cost = D.mountain_path()
        self.assertEqual(cost, 6)
        walk = sum(abs(D.GRID[b[0]][b[1]] - D.GRID[a[0]][a[1]]) for a, b in zip(path, path[1:]))
        self.assertEqual(walk, 6)

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("dijkstra.json").read_text(encoding="utf-8"))["beats"])
        for s in ("一加二只要三", "最短距离是零、三、一、四", "最小代价是六", "记下代价四"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
