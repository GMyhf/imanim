"""强连通分量片数字的独立对撞：讲义 Kosaraju / Tarjan / Popular Cows 原文、传递闭包暴力法、随机图、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_scc
"""
import contextlib
import io
import json
import random
import sys
import unittest
from pathlib import Path

import sccdata as S

HERE = Path(__file__).resolve().parent


def run_lecture(code, call):
    ns = {}
    exec(code, ns)
    return eval(call, ns)


def norm(sccs):
    return sorted(sorted(c) for c in sccs)


def random_graph(rng, n, p):
    return [[v for v in range(n) if v != u and rng.random() < p] for u in range(n)]


class SCCTest(unittest.TestCase):
    def test_lecture_outputs(self):
        # 讲义 console：[[0, 3, 2, 1], [6, 7], [5, 4]] 与 Tarjan 的 [[4, 5], [7, 6], [3, 2, 1, 0]]
        self.assertEqual(run_lecture(S.KOSARAJU_CODE, "kosaraju(8, ADJ)".replace("ADJ", repr(S.ADJ))),
                         [[0, 3, 2, 1], [6, 7], [5, 4]])
        self.assertEqual(S.SCCS, [[0, 3, 2, 1], [6, 7], [5, 4]])
        self.assertEqual(run_lecture(S.TARJAN_CODE, f"tarjan(8, {S.ADJ!r})"), [[4, 5], [7, 6], [3, 2, 1, 0]])
        # 讲义：第一次 DFS 后的栈（底→顶）4 5 7 6 3 2 1 0
        self.assertEqual(S.STACK, [4, 5, 7, 6, 3, 2, 1, 0])
        # 讲义：缩点后 {0,1,2,3} → {6,7} → {4,5}，外加 {0,1,2,3} → {4,5}
        self.assertEqual(S.CEDGES, [(0, 1), (0, 2), (1, 2)])

    def test_edges_and_timestamps(self):
        self.assertEqual(len(S.EDGES), 12)
        self.assertEqual(S.D_TIME, [1, 2, 3, 4, 8, 7, 5, 6])
        self.assertEqual(S.F_TIME, [16, 15, 14, 13, 9, 10, 12, 11])
        # 发现/结束时间成对嵌套（括号定理），且 1..16 各用一次
        self.assertEqual(sorted(S.D_TIME + S.F_TIME), list(range(1, 17)))
        for u in range(S.N):
            for v in range(S.N):
                a, b = (S.D_TIME[u], S.F_TIME[u]), (S.D_TIME[v], S.F_TIME[v])
                self.assertTrue(a[1] < b[0] or b[1] < a[0] or (a[0] < b[0] and b[1] < a[1])
                                or (b[0] < a[0] and a[1] < b[1]) or u == v)
        back = sorted(e for e, k in S.KIND.items() if k == "back")
        self.assertEqual(back, [(3, 0), (4, 5), (7, 6)])
        # 回边两端一定在同一块（回边 + 树路径成环）
        for u, v in back:
            self.assertEqual(S.COMP[u], S.COMP[v])
        # 结束次序：四最先，然后五、七、六，再三、二、一、零
        fin = [e[1] for e in S.TR["events"] if e[0] == "finish"]
        self.assertEqual(fin, [4, 5, 7, 6, 3, 2, 1, 0])
        # 「二到五，五已经黑了」：考察 2→5 时 5 已结束
        seq = S.TR["events"]
        i = seq.index(("edge", 2, 5, S.KIND[(2, 5)]))
        self.assertIn(("finish", 5, S.F_TIME[5]), seq[:i])

    def test_finish_max_per_component(self):
        mx = [max(S.F_TIME[v] for v in c) for c in S.SCCS]
        self.assertEqual(mx, [16, 12, 10])
        for a, b in S.CEDGES:                       # 缩点图的边：最大结束时间严格变小
            self.assertGreater(mx[a], mx[b])

    def test_second_pass_rounds(self):
        rs = S.ROUNDS
        starts = [r["start"] for r in rs]
        self.assertEqual(starts, [0, 1, 2, 3, 6, 7, 5, 4])
        self.assertEqual([r["skip"] for r in rs], [False, True, True, True, False, True, False, True])
        self.assertEqual(rs[0]["comp"], [0, 3, 2, 1])
        self.assertEqual(rs[4]["comp"], [6, 7])
        self.assertIn((6, 3, True), rs[4]["looks"])     # 「三已经访问过」
        self.assertEqual(rs[6]["comp"], [5, 4])

    def test_random_against_bruteforce(self):
        rng = random.Random(2026)
        for _ in range(400):
            n = rng.randint(1, 12)
            adj = random_graph(rng, n, rng.choice([0.1, 0.2, 0.35]))
            want = norm(S.sccs_bruteforce(adj))
            self.assertEqual(norm(S.kosaraju(adj)), want)
            self.assertEqual(norm(run_lecture(S.KOSARAJU_CODE, f"kosaraju({n}, {adj!r})")), want)
            self.assertEqual(norm(run_lecture(S.TARJAN_CODE, f"tarjan({n}, {adj!r})")), want)
            # Kosaraju 的产出次序是缩点图的拓扑序：缩点边都从前指向后
            sccs = S.kosaraju(adj)
            self.assertTrue(all(a < b for a, b in S.condensed(adj, sccs)))

    def run_cows(self, text):
        old = sys.stdin
        sys.stdin = type("In", (), {"buffer": io.BytesIO(text.encode())})()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(S.COWS_CODE, {})
        finally:
            sys.stdin = old
        return int(buf.getvalue())

    def test_popular_cows(self):
        self.assertEqual(self.run_cows(S.COWS_SAMPLE), 1)
        self.assertEqual(S.popular_cows(3, [(1, 2), (2, 1), (2, 3)]), 1)
        rng = random.Random(7)
        for _ in range(300):
            n = rng.randint(1, 9)
            m = rng.randint(0, 14)
            pairs = [(rng.randint(1, n), rng.randint(1, n)) for _ in range(m)]
            text = f"{n} {m}\n" + "".join(f"{a} {b}\n" for a, b in pairs)
            self.assertEqual(self.run_cows(text), S.popular_cows(n, pairs))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads((HERE / "scc.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("八个点、十二条边", beats["graph"])
        self.assertEqual((S.N, len(S.EDGES)), (8, 12))
        self.assertIn("分成三块", beats["graph"])
        self.assertEqual(len(S.SCCS), 3)
        self.assertIn("零的结束时间是十六", beats["dfs1"])
        self.assertEqual(S.F_TIME[0], 16)
        self.assertIn("蓝色十六，黄色十二，紫色十", beats["finish"])
        self.assertIn("答案是一", beats["cows"])


if __name__ == "__main__":
    unittest.main()
