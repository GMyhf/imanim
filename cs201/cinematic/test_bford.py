"""Bellman-Ford 片数字的独立对撞：讲义输出、穷举简单路径、逐轮表格、负环检查、dp 表、SPFA、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_bford
"""
import itertools
import json
import random
import unittest
from pathlib import Path

import bforddata as B

INF = B.INF


def brute(n, edges, s=0):
    """不依赖 bforddata 的穷举：枚举所有顶点排列前缀作为简单路径。"""
    w = {}
    for u, v, c in edges:
        w[(u, v)] = min(w.get((u, v), INF), c)
    best = [INF] * n
    best[s] = 0
    others = [x for x in range(n) if x != s]
    for k in range(1, n):
        for perm in itertools.permutations(others, k):
            path = (s, *perm)
            if all((a, b) in w for a, b in zip(path, path[1:])):
                best[path[-1]] = min(best[path[-1]], sum(w[(a, b)] for a, b in zip(path, path[1:])))
    return best


def has_neg_cycle(n, edges):
    """独立判负环（从 0 可达）：Floyd 对角线 < 0 且该点从 0 可达。"""
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, c in edges:
        d[u][v] = min(d[u][v], c)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return any(d[i][i] < 0 and d[0][i] < INF for i in range(n))


class BFordTest(unittest.TestCase):
    def test_lecture_output(self):
        # 讲义打印：[0, 2, 5, 4] 和 None
        self.assertEqual(B.bellman_ford(4, B.EDGES, 0), [0, 2, 5, 4])
        self.assertIsNone(B.bellman_ford(4, B.EDGES + [B.NEG_EDGE], 0))
        self.assertEqual(brute(4, B.EDGES), [0, 2, 5, 4])

    def test_round_table(self):
        # 讲义表格：第 1 轮 0 2 5 6（四条边全部松弛成功），第 2 轮只有 <1,3> 改成 4，第 3 轮无改动提前结束
        rounds, check, res = B.bf_trace()
        self.assertEqual([r["dist"] for r in rounds], [[0, 2, 5, 6], [0, 2, 5, 4], [0, 2, 5, 4]])
        self.assertEqual([(u, v, new) for u, v, w, old, new in rounds[0]["ok"]], [(0, 1, 4), (0, 2, 5), (1, 3, 6), (2, 1, 2)])
        self.assertEqual([(u, v, new) for u, v, w, old, new in rounds[1]["ok"]], [(1, 3, 4)])
        self.assertEqual(rounds[2]["ok"], [])
        self.assertEqual(check, [])
        self.assertEqual(B.edge_checks(rounds, 4), 16)
        # 换边序：第 1 轮就全对
        r2, _, _ = B.bf_trace(edges=B.REORDER)
        self.assertEqual(r2[0]["dist"], [0, 2, 5, 4])

    def test_neg_cycle(self):
        rounds, check, res = B.bf_trace(edges=B.EDGES + [B.NEG_EDGE])
        self.assertEqual([r["dist"] for r in rounds], [[0, 2, 2, 6], [0, -1, 0, 4], [0, -3, -3, 1]])
        self.assertEqual({(u, v) for u, v, w in check}, {(1, 3), (2, 1)})
        self.assertIsNone(res)
        self.assertEqual(-3 + 2 + B.NEG_EDGE[2], -5)
        self.assertTrue(has_neg_cycle(4, B.EDGES + [B.NEG_EDGE]))

    def test_dijkstra_wrong(self):
        D, order = B.dijkstra_S()
        self.assertEqual(order, [(0, 0), (1, 4), (2, 5), (3, 6)])
        self.assertEqual((D[1], D[3]), (4, 6))
        truth = B.shortest_paths_brute(4, B.EDGES)
        self.assertEqual((truth[1][0], truth[3][0]), (2, 4))
        self.assertEqual(truth[1][1], [0, 2, 1])

    def test_shift_changes_path(self):
        sh = B.shifted()
        self.assertTrue(all(w >= 0 for _, _, w in sh))
        best = B.shortest_paths_brute(4, sh)
        self.assertEqual(best[1], (7, [0, 1]))
        direct = dict(((u, v), w) for u, v, w in sh)
        self.assertEqual(direct[(0, 2)] + direct[(2, 1)], 8)
        self.assertNotEqual(best[1][1], B.shortest_paths_brute(4, B.EDGES)[1][1])

    def test_dp_bound(self):
        dp = B.dp_table()
        self.assertEqual(dp, [[0, INF, INF, INF], [0, 4, 5, INF], [0, 2, 5, 6], [0, 2, 5, 4]])
        rounds, _, _ = B.bf_trace()
        for k, r in enumerate(rounds, 1):
            self.assertTrue(all(a <= b for a, b in zip(r["dist"], dp[k])))
        paths = B.dp_paths()
        self.assertEqual(paths[3][3], [0, 2, 1, 3])

    def test_random(self):
        rng = random.Random(201)
        for _ in range(400):
            n = rng.randint(2, 6)
            edges = [(u, v, rng.randint(-4, 9)) for u in range(n) for v in range(n) if u != v and rng.random() < 0.4]
            got = B.bellman_ford(n, edges, 0)
            if has_neg_cycle(n, edges):
                self.assertIsNone(got)
                continue
            self.assertEqual(got, brute(n, edges))
            r, _, res = B.bf_trace(n, edges)
            self.assertEqual(res, got)
            self.assertLessEqual(len(r), n - 1)
            self.assertEqual(B.spfa(n, edges)[0], got)

    def test_spfa_counts(self):
        dist, checks, pushes, ev = B.spfa()
        self.assertEqual(dist, [0, 2, 5, 4])
        self.assertEqual(checks, 5)
        self.assertEqual(sum(1 for e in ev if e[0] == "push"), pushes)

    def test_narration_numbers(self):
        script = json.loads((Path(__file__).parent / "bford.json").read_text(encoding="utf-8"))
        text = {b["id"]: b["narration"] for b in script["beats"]}
        self.assertIn("零到一是四，零到二是五，二到一是负三，一到三是二", text["wrong"])
        self.assertIn("一号点，距离四", text["wrong"])
        self.assertIn("三号点是六", text["wrong"])
        self.assertIn("一号点只要二，到三号点只要四", text["wrong"])
        self.assertIn(f"加上三", text["shift"])
        self.assertEqual(B.SHIFT, 3)
        self.assertIn("直走是七，绕道是八", text["shift"])
        self.assertIn("答案是零、二、五、四", text["rounds"])
        self.assertIn("二加二等于四", text["rounds"])
        self.assertIn("一圈总共负五", text["negcycle"])
        self.assertIn("零、负三、负三、一", text["negcycle"])
        self.assertIn("十六次边", text["spfa"])
        self.assertIn("只检查五次", text["spfa"])


if __name__ == "__main__":
    unittest.main()
