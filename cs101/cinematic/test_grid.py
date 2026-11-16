"""网格 DP 与搜索分界片数字的独立对撞：讲义输出、枚举路径、松弛到收敛的真最短、出堆顺序是拓扑序、路径计数、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_grid
"""
import itertools
import json
from math import comb
from pathlib import Path
import random
import unittest

import griddata as D


def brute_rd(grid):
    """独立方法：枚举所有只向右 / 向下的路径（选哪几步向下），取路径和最小值。"""
    n, m = len(grid), len(grid[0])
    best = None
    for downs in itertools.combinations(range(n + m - 2), n - 1):
        i = j = 0
        s = grid[0][0]
        for k in range(n + m - 2):
            if k in downs:
                i += 1
            else:
                j += 1
            s += grid[i][j]
        best = s if best is None else min(best, s)
    return best


def relax_all(grid):
    """独立方法：四方向反复松弛到不再变化（Bellman-Ford 式），得到每格真正的最小路径和。"""
    n, m = len(grid), len(grid[0])
    d = [[float("inf")] * m for _ in range(n)]
    d[0][0] = grid[0][0]
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in range(m):
                for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < n and 0 <= b < m and d[i][j] + grid[a][b] < d[a][b]:
                        d[a][b] = d[i][j] + grid[a][b]
                        changed = True
    return d


def simple_paths_mask(n, m):
    """独立方法：位掩码记录走过的格子，数四方向不重复的路径。"""
    goal = n * m - 1

    def go(u, mask):
        if u == goal:
            return 1
        x, y = divmod(u, m)
        tot = 0
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < n and 0 <= b < m:
                v = a * m + b
                if not mask >> v & 1:
                    tot += go(v, mask | 1 << v)
        return tot
    return go(0, 1)


class GridFacts(unittest.TestCase):
    def test_course_output(self):
        self.assertEqual(D.min_path_sum(D.G0), 7)                       # 讲义输出
        dp, order = D.dp_table(D.G0)
        self.assertEqual(dp, [[1, 4, 5], [2, 7, 6], [6, 8, 7]])
        self.assertEqual(len(order), 9)
        self.assertEqual([D.G0[i][j] for i, j in D.dp_path(D.G0)], [1, 3, 1, 1, 1])

    def test_dp_matches_brute(self):
        rnd = random.Random(5)
        for _ in range(300):
            n, m = rnd.randint(1, 5), rnd.randint(1, 5)
            g = [[rnd.randint(0, 9) for _ in range(m)] for _ in range(n)]
            self.assertEqual(D.min_path_sum(g), brute_rd(g))
            self.assertEqual(D.dp_table(g)[0][-1][-1], brute_rd(g))
            self.assertEqual(sum(g[i][j] for i, j in D.dp_path(g)), brute_rd(g))

    def test_order_is_topological(self):
        """填表顺序里，每格用到的上 / 左邻居都排在它前面。"""
        _, order = D.dp_table(D.G4)
        pos = {(i, j): k for k, (i, j, _) in enumerate(order)}
        for i, j, _ in order:
            for a, b in ((i - 1, j), (i, j - 1)):
                if (a, b) in pos:
                    self.assertLess(pos[(a, b)], pos[(i, j)])

    def test_naive_four(self):
        nv = D.naive_four(D.G4)
        self.assertEqual(nv, D.dp_table(D.G4)[0])                       # 照搬四方向 = 只许右下
        self.assertEqual(nv[-1][-1], 16)
        self.assertEqual(brute_rd(D.G4), 16)
        self.assertEqual(nv[2][2], 13)
        done, todo = D.naive_ready(D.G4, 2, 2)
        self.assertIn((3, 2), todo)
        self.assertEqual(sorted(done), [(1, 2), (2, 1)])

    def test_true_answer(self):
        d = relax_all(D.G4)
        ans, pops, dist, _ = D.grid_dijkstra(D.G4)
        self.assertEqual(ans, d[-1][-1])
        self.assertEqual(ans, 10)
        self.assertEqual((d[3][2], d[2][2]), (6, 7))
        n, m = len(D.G4), len(D.G4[0])
        self.assertEqual(D.dijkstra(n * m, D.grid_adj(D.G4), 0)[-1] + D.G4[0][0], 10)   # 讲义 dijkstra 原样
        for dd, (x, y) in pops:
            self.assertEqual(dd, d[x][y])
        self.assertEqual(16 - 10, 6)
        rnd = random.Random(8)
        for _ in range(200):
            nn, mm = rnd.randint(1, 5), rnd.randint(1, 5)
            g = [[rnd.randint(0, 9) for _ in range(mm)] for _ in range(nn)]
            self.assertEqual(D.grid_dijkstra(g)[0], relax_all(g)[-1][-1])
            self.assertEqual(D.dijkstra(nn * mm, D.grid_adj(g), 0)[-1] + g[0][0], relax_all(g)[-1][-1])

    def test_pop_order(self):
        _, pops, _, prev = D.grid_dijkstra(D.G4)
        self.assertEqual([d for d, _ in pops], sorted(d for d, _ in pops))
        self.assertEqual([d for d, _ in pops[:9]], list(range(1, 10)))
        path = D.best_path(D.G4)
        self.assertEqual([c for _, c in pops[:9]], path[:9])            # 前九次出堆正好是最优路径前九格
        self.assertEqual(pops[-1], (10, (3, 4)))
        self.assertEqual(sum(D.G4[i][j] for i, j in path), 10)
        ups = [(a, b) for a, b in zip(path, path[1:]) if b[0] < a[0]]
        self.assertEqual(ups, [((3, 2), (2, 2))])                       # 在第三列往上一步
        seen = set()
        for _, c in pops:                                               # 出堆顺序是拓扑序
            if c != (0, 0):
                self.assertIn(prev[c], seen)
            seen.add(c)

    def test_count(self):
        t = D.count_paths(4, 5)
        self.assertEqual(t[-1][-1], 35)
        self.assertEqual(t[-1][-1], comb(7, 3))
        self.assertEqual(D.simple_paths(4, 5), 976)
        self.assertEqual(simple_paths_mask(4, 5), 976)
        self.assertEqual(simple_paths_mask(3, 3), D.simple_paths(3, 3))

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("grid.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("答案是七：一、三、一、一、一", beats["dp"])
        self.assertIn("三乘三", beats["dp"])
        self.assertIn("四行五列", beats["four"])
        self.assertIn("右下角是十六", beats["four"])
        self.assertIn("得到十三", beats["cycle"])
        self.assertIn("走到下面是六，往上一步只要七", beats["cycle"])
        self.assertIn("答案是十，比照搬的动态规划少了六", beats["dijkstra"])
        self.assertIn("一、二、三、四", beats["dijkstra"])
        self.assertIn("右下角是三十五", beats["count"])
        self.assertIn("九百七十六条", beats["count"])


if __name__ == "__main__":
    unittest.main()
