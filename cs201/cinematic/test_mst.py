"""最小生成树片数字的独立对撞：枚举全部生成树求真最小值、讲义逐步表格、随机图上 Prim/Kruskal/暴力三方一致、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_mst
"""
import itertools
import json
from pathlib import Path
import random
import unittest

import mstdata as M


def is_spanning_tree(n, es):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for u, v, _ in es:
        a, b = find(u), find(v)
        if a == b:
            return False
        parent[a] = b
    return len(es) == n - 1


def brute_mst(n, edges):
    best = None
    for comb in itertools.combinations(edges, n - 1):
        if is_spanning_tree(n, comb):
            w = sum(e[2] for e in comb)
            best = w if best is None else min(best, w)
    return best


class MSTFacts(unittest.TestCase):
    def test_lecture_tables(self):
        tree, ev = M.prim_trace()
        self.assertEqual([(e.source, e.target, e.weight) for e in tree],
                         [(0, 4, 1), (4, 5, 15), (5, 6, 10), (6, 2, 2), (2, 1, 6), (1, 3, 4)])
        # 讲义 distance 表：第 3 轮并入 v5 后 v3=12、v6=10；第 4 轮并入 v6 后 v2=2、v3=8
        picks = [e for e in ev if e[0] == "pick"]
        self.assertEqual([p[1] for p in picks], [0, 4, 5, 6, 2, 1, 3])
        kr, kev = M.kruskal_trace()
        self.assertEqual([(a, e.weight) for a, e in kev],
                         [("take", 1), ("take", 2), ("take", 4), ("take", 6), ("skip", 8), ("take", 10),
                          ("skip", 12), ("take", 15), ("skip", 20)])
        self.assertEqual(M.weight(tree), 38)
        self.assertEqual(M.weight(kr), 38)
        self.assertEqual({M.undirected(e) for e in tree}, {M.undirected(e) for e in kr})

    def test_against_bruteforce(self):
        self.assertEqual(brute_mst(M.N, M.EDGES), 38)
        rng = random.Random(7)
        for _ in range(150):
            n = rng.randint(2, 6)
            edges = [(u, v, rng.randint(1, 9)) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.7]
            want = brute_mst(n, edges)
            p, _ = M.prim_trace(0, n, edges)
            k, _ = M.kruskal_trace(n, edges)
            if want is None:
                self.assertIsNone(p)
                self.assertIsNone(k)
            else:
                self.assertEqual(M.weight(p), want)
                self.assertEqual(M.weight(k), want)

    def test_cut_and_proof(self):
        self.assertEqual(sorted(e[2] for e in M.crossing(M.CUT_U)), [10, 12, 20])
        self.assertEqual(M.light_crossing(M.CUT_U), (5, 6, 10))
        self.assertTrue(is_spanning_tree(M.N, M.PROOF_T))
        self.assertNotIn((5, 6), {M.undirected(e) for e in M.PROOF_T})
        self.assertEqual(sum(e[2] for e in M.PROOF_T), 40)
        cyc = M.tree_path([M.Edge(*e) for e in M.PROOF_T], 5, 6)
        cross = [(a, b) for a, b in zip(cyc, cyc[1:]) if (a in M.CUT_U) != (b in M.CUT_U)]
        self.assertEqual(cross, [(5, 3)])
        self.assertEqual(40 - 12 + 10, 38)
        self.assertTrue(is_spanning_tree(M.N, M.NAIVE))
        self.assertEqual(sum(e[2] for e in M.NAIVE), 60)

    def test_spt_vs_mst(self):
        sp, dist = M.spt(3, M.TRI)
        self.assertEqual(dist, [0, 2, 3])
        self.assertEqual(sum(w for *_, w in sp), 5)
        self.assertEqual(brute_mst(3, M.TRI), 4)

    def test_narration_numbers(self):
        script = json.loads((Path(__file__).parent / "mst.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in script["beats"]}
        self.assertIn("总造价是六十", nar["problem"])
        self.assertIn("只要三十八", nar["problem"])
        self.assertIn("总权三十八", nar["prim"])
        for s in ("先取权为一", "只能取十五", "接着取十", "然后取二", "再取六", "最后取四"):
            self.assertIn(s, nar["prim"])
        self.assertIn("跨界的边只有二十和十五", nar["prim"])
        self.assertEqual(sorted(e[2] for e in M.crossing({0, 4})), [15, 20])
        self.assertIn("九条边", nar["kruskal"])
        self.assertEqual(len(M.EDGES), 9)
        self.assertIn("八，三号点和六号点", nar["kruskal"])
        self.assertIn("总权五", nar["spt"])
        self.assertIn("总权只有四", nar["spt"])


if __name__ == "__main__":
    unittest.main()
