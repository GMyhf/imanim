"""并查集片数字的独立对撞：讲义输出、期中题标准答案、树高界、旁白数字。

用法（cwd = mvp/cs101/cinematic）：python -m unittest test_dsu
"""
import json
from math import log2
from pathlib import Path
import random
import unittest

import dsudata as D


class DSUFacts(unittest.TestCase):
    def test_course_example(self):
        d = D.DSU(6)
        d.union(0, 1); d.union(1, 2); d.union(3, 4)
        self.assertEqual((d.find(0) == d.find(2), d.find(0) == d.find(3), d.count), (True, False, 3))

    def test_random_against_brute(self):
        rng = random.Random(7)
        for _ in range(200):
            n = rng.randint(1, 12)
            pairs = [(rng.randrange(n), rng.randrange(n)) for _ in range(rng.randint(0, 15))]
            d = D.DSU(n)
            for a, b in pairs:
                d.union(a, b)
            comp = {}
            for i in range(n):
                comp.setdefault(d.find(i), set()).add(i)
            # 用 BFS 求连通块对撞
            adj = {i: set() for i in range(n)}
            for a, b in pairs:
                adj[a].add(b); adj[b].add(a)
            seen, blocks = set(), []
            for s in range(n):
                if s in seen:
                    continue
                stack, blk = [s], set()
                seen.add(s)
                while stack:
                    u = stack.pop(); blk.add(u)
                    for v in adj[u]:
                        if v not in seen:
                            seen.add(v); stack.append(v)
                blocks.append(blk)
            self.assertEqual(sorted(map(sorted, comp.values())), sorted(map(sorted, blocks)))
            self.assertEqual(d.count, len(blocks))
            for i in range(n):                         # 按大小合并：树高 ≤ log2(集合大小)
                r = d.find(i)
                self.assertLessEqual(D.depth(d.parent, i), log2(d.size[r]))

    def test_chain_vs_weighted(self):
        na, gd = D.chain_vs_weighted()
        self.assertEqual(na[-1], [1, 2, 3, 4, 5, 6, 7, 7])                 # 0→1→…→7 一条链
        self.assertEqual(D.depth(na[-1], 0), 7)
        self.assertEqual(gd[-1], [0] * 8)                                  # 全挂在 0 下
        self.assertEqual(max(D.depth(gd[-1], i) for i in range(8)), 1)

    def test_forest(self):
        snaps = D.forest_snapshots()
        self.assertEqual(snaps[-1], [0, 0, 0, 2, 4, 4, 6, 7])
        self.assertEqual(D.path_to_root(snaps[-1], 3), [3, 2, 0])

    def test_compress(self):
        before, path, root, after = D.compress_demo()
        self.assertEqual(path, [7, 5, 2, 1])                               # 讲义：路径 7、5、2、1
        self.assertEqual(root, 1)
        self.assertEqual((after[7], after[5], after[2]), (1, 1, 1))
        self.assertEqual((after[9], after[10]), (7, 7))                    # 9、10 仍在 7 下
        changed = {k for k in before if before[k] != after[k]}
        self.assertEqual(changed, {7, 5})

    def test_exam(self):
        steps = dict(D.exam_steps())
        p0 = steps["init"]
        self.assertEqual([i for i, v in enumerate(p0) if v < 0], [0, 4, 7, 9])   # 四个集合
        self.assertEqual(steps["find2"][2], 0)
        self.assertEqual(steps["find6"][6], 4)
        self.assertEqual(steps["link"], [-7, 0, 0, 0, 0, 4, 4, -2, 7, -1])        # 第 (2) 问
        self.assertEqual(steps["find6b"], [-7, 0, 0, 0, 0, 4, 0, -2, 7, -1])      # 第 (3) 问
        p = D.EXAM_P0[:]
        D.exam_union(p, 2, 6)
        self.assertEqual(p, steps["link"])

    def test_apps(self):
        self.assertEqual(D.religion_counts(), [10, 9, 8, 7])
        self.assertEqual(D.cycle_returns(), [True, True, False])

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("dsu.json").read_text(encoding="utf-8"))["beats"])
        for s in ("路径是七、五、二、一", "七和五被改挂到根一下面", "九和十不在路径上",
                  "零、四、七、九是根，一共四个集合", "零变成负七", "最后剩七组", "合并返回 False"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
