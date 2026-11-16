"""关键路径片数字的独立对撞：讲义 critical_path 原文与 console、穷举源汇路径、反复松弛求工期、
「拖延 x 天工期变不变」的定义式机动时间、随机 DAG、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_aoe
"""
import json
import random
import unittest
from pathlib import Path

import aoedata as A

HERE = Path(__file__).resolve().parent


def lecture(n, edges):
    ns = {}
    exec(A.CODE, ns)
    return ns["critical_path"](n, edges)


def random_dag(rng, n):
    perm = list(range(n))
    rng.shuffle(perm)
    rank = {v: k for k, v in enumerate(perm)}
    edges = [(u, v, rng.randint(1, 9)) for u in range(n) for v in range(n)
             if rank[u] < rank[v] and rng.random() < 0.35]
    return edges


def slack_by_delay(n, edges, k):
    """定义式机动时间：活动 k 最多能拖几天而工期不变（逐天试）。"""
    base = A.duration(edges + [(i, i, 0) for i in range(n)])
    x = 0
    while x < 100:
        e = A.with_weight(edges, k, edges[k][2] + x + 1)
        if A.duration(e + [(i, i, 0) for i in range(n)]) > base:
            return x
        x += 1
    return x


class AOETest(unittest.TestCase):
    def test_lecture_console(self):
        total, ve, vl, crit = lecture(6, A.EDGES)
        self.assertEqual(total, 8)
        self.assertEqual(ve, [0, 3, 2, 6, 6, 8])
        self.assertEqual(vl, [0, 4, 2, 6, 7, 8])
        self.assertEqual(crit, [(0, 2), (2, 3), (3, 5)])
        self.assertEqual((A.TOTAL, A.VE, A.VL, A.CRIT), (total, ve, vl, crit))

    def test_lecture_tables(self):
        # 讲义「拓扑序出队」表：0 1 2 4 3 5，ve3 先 5 后 6，ve5 依次 3、7、8
        self.assertEqual(A.TR["order"], [0, 1, 2, 4, 3, 5])
        hist = {}
        for u, ups in A.TR["fwd"]:
            for v, w, old, new in ups:
                hist.setdefault(v, []).append(new)
        self.assertEqual(hist[3], [5, 6])
        self.assertEqual(hist[5], [3, 7, 8])
        # 讲义 e / l / l-e 表
        self.assertEqual([a["slack"] for a in A.ACTS], [1, 0, 1, 1, 0, 5, 0, 1])
        self.assertEqual([a["e"] for a in A.ACTS], [0, 0, 3, 3, 2, 2, 6, 6])
        self.assertEqual([a["l"] for a in A.ACTS], [1, 0, 4, 4, 2, 7, 6, 7])
        # vl2 = min(6-4, 8-1)
        bw = dict(A.TR["bwd"])
        self.assertEqual([(old, new) for _, _, old, new in bw[2]], [(8, 2), (2, 2)])

    def test_paths_and_longest(self):
        self.assertEqual(sorted(L for _, L in A.PATHS), [3, 7, 7, 8])
        self.assertEqual(max(L for _, L in A.PATHS), A.TOTAL)
        longest = [p for p, L in A.PATHS if L == A.TOTAL]
        self.assertEqual(longest, [(0, 2, 3, 5)])
        self.assertEqual(A.duration(A.EDGES), 8)

    def test_slack_matches_definition(self):
        for k in range(len(A.EDGES)):
            self.assertEqual(slack_by_delay(A.N, A.EDGES, k), A.ACTS[k]["slack"])

    def test_share_and_shorten(self):
        d = A.with_weight(A.EDGES, 0, 4)
        self.assertEqual(A.DELAY01["total"], 8)
        sl = {(a["u"], a["v"]): a["slack"] for a in A.activities(A.DELAY01, d)}
        self.assertEqual((sl[(1, 3)], sl[(1, 4)]), (0, 0))
        self.assertEqual(A.SHORT14["total"], 8)
        self.assertEqual(A.SHORT23["total"], 7)
        e = A.with_weight(A.EDGES, 4, 2)
        sev = [p for p, L in A.paths(edges=e) if L == 7]
        self.assertEqual(sorted(sev), [(0, 1, 3, 5), (0, 1, 4, 5)])

    def test_random_dags(self):
        rng = random.Random(2026)
        for _ in range(300):
            n = rng.randint(2, 9)
            edges = random_dag(rng, n)
            if not edges:
                continue
            got = lecture(n, edges)
            tr = A.critical_path_trace(n, edges)
            self.assertEqual(got, (tr["total"], tr["ve"], tr["vl"], tr["crit"]))
            pad = edges + [(i, i, 0) for i in range(n)]
            self.assertEqual(got[0], A.duration(pad))
            for k, a in enumerate(A.activities(tr, edges)):
                self.assertEqual(a["slack"], slack_by_delay(n, edges, k))
        # 有环返回 None
        self.assertIsNone(lecture(3, [(0, 1, 1), (1, 2, 1), (2, 1, 1)]))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads((HERE / "aoe.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("四条路", beats["longest"])
        self.assertEqual(len(A.PATHS), 4)
        self.assertIn("零一三五，七天；零一四五，也是七天；零二三五，八天；零二五，三天", beats["longest"])
        self.assertIn("依次更新成三、七、八", beats["ve"])
        self.assertIn("一最迟第四天", beats["vl"])
        self.assertEqual(A.VL[1], 4)
        self.assertIn("二到五能拖五天", beats["slack"])
        self.assertIn("工期却只降到七", beats["shorten"])


if __name__ == "__main__":
    unittest.main()
