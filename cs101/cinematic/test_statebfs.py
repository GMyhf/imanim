"""带状态 BFS 片数字的独立对撞：讲义输出、状态图上反复松弛的真最短、只按坐标记的反例、超级源点、水淹七军逐源灌水、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_statebfs
"""
import json
from pathlib import Path
import random
import unittest

import statebfsdata as D

INF = float("inf")


def relax_states(grid, T):
    """独立方法：不用队列，在（行、列、剩余查克拉）状态上反复松弛到稳定（Bellman-Ford 式）。返回 {状态: 最短步数}。"""
    n, m = len(grid), len(grid[0])
    s = next((i, j) for i in range(n) for j in range(m) if grid[i][j] == '@')
    d = {(i, j, t): INF for i in range(n) for j in range(m) for t in range(T + 1)}
    d[(*s, T)] = 0
    changed = True
    while changed:
        changed = False
        for (x, y, t), v in list(d.items()):
            if v == INF:
                continue
            for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= a < n and 0 <= b < m:
                    nt = t - (grid[a][b] == '#')
                    if nt >= 0 and d[(a, b, nt)] > v + 1:
                        d[(a, b, nt)] = v + 1
                        changed = True
    return d


def true_answer(grid, T):
    d = relax_states(grid, T)
    g = next((i, j) for i in range(len(grid)) for j in range(len(grid[0])) if grid[i][j] == '+')
    best = min(d[(*g, t)] for t in range(T + 1))
    return -1 if best == INF else best


def rand_grid(rnd, n, m):
    cells = [rnd.choice("..#") for _ in range(n * m)]
    a, b = rnd.sample(range(n * m), 2)
    cells[a], cells[b] = '@', '+'
    return ["".join(cells[i * m:(i + 1) * m]) for i in range(n)]


def flood_by_source(height, sources):
    """独立方法：每个放水点单独用栈灌一遍（水位固定为放水点高度），各格取最高水位。"""
    n, m = len(height), len(height[0])
    water = [[-1] * m for _ in range(n)]
    for sx, sy in sources:
        lv = height[sx][sy]
        seen, st = {(sx, sy)}, [(sx, sy)]
        while st:
            x, y = st.pop()
            water[x][y] = max(water[x][y], lv)
            for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= a < n and 0 <= b < m and (a, b) not in seen and height[a][b] < lv:
                    seen.add((a, b))
                    st.append((a, b))
    return water


class StateBFSFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(D.naruto(D.G_COURSE, 2), 5)
        self.assertEqual(D.naruto(D.G_COURSE, 0), 7)
        self.assertEqual(D.update_matrix([[0, 0, 0], [0, 1, 0], [1, 1, 1]]), [[0, 0, 0], [0, 1, 0], [1, 2, 1]])
        h = [[5, 2, 2], [4, 1, 2], [3, 3, 2]]
        self.assertTrue(D.flood_army(h, [(0, 0)], (1, 1)))
        self.assertFalse(D.flood_army(h, [(1, 1)], (0, 0)))

    def test_course_paths(self):
        for T, ans in ((2, 5), (0, 7)):
            p = D.state_path(D.G_COURSE, T)
            self.assertEqual(len(p) - 1, ans)
            self.assertEqual(true_answer(D.G_COURSE, T), ans)
            self.assertEqual(sum(D.G_COURSE[x][y] == '#' for x, y, _ in p[1:]), T - p[-1][2])

    def test_coord_passes_samples(self):
        self.assertEqual(D.naruto_coord(D.G_COURSE, 2)[0], 5)
        self.assertEqual(D.naruto_coord(D.G_COURSE, 0)[0], 7)

    def test_trap(self):
        g, T = D.G_TRAP, D.T_TRAP
        self.assertEqual(T, 1)
        self.assertEqual((len(g), len(g[0])), (3, 5))
        self.assertEqual(true_answer(g, T), 6)
        self.assertEqual(D.naruto(g, T), 6)
        self.assertEqual(D.naruto_states(g, T)[0], 6)
        wrong, seen = D.naruto_coord(g, T)
        self.assertEqual(wrong, 8)
        self.assertEqual(seen[(0, 2)], (2, 0))                  # 中间格第二步被占，查克拉用光
        cp = D.naruto_coord_path(g, T)
        self.assertEqual(len(cp) - 1, 8)
        self.assertTrue(all(x == 2 for x, _ in cp[2:7]))        # 绕最下面一行
        d = relax_states(g, T)
        self.assertEqual((d[(0, 2, 0)], d[(0, 2, 1)]), (2, 4))  # 同一格两个状态：下层第二步、上层第四步
        p = D.state_path(g, T)
        self.assertEqual(len(p) - 1, 6)
        self.assertIn((0, 2, 1), p)
        self.assertEqual(p[-1], (0, 4, 0))
        for (a, b, t), (c, e, u) in zip(p, p[1:]):
            self.assertEqual(abs(a - c) + abs(b - e), 1)
            self.assertEqual(u, t - (g[c][e] == '#'))
        self.assertEqual(D.n_states(g, T), 30)

    def test_states_vs_relax(self):
        _, dist, _ = D.naruto_states(D.G_TRAP, D.T_TRAP)
        d = relax_states(D.G_TRAP, D.T_TRAP)
        self.assertEqual(dist, {s: v for s, v in d.items() if v < INF})

    def test_random(self):
        rnd = random.Random(12)
        coord_wrong = 0
        for _ in range(600):
            n, m, T = rnd.randint(1, 5), rnd.randint(2, 6), rnd.randint(0, 3)
            g = rand_grid(rnd, n, m)
            ref = true_answer(g, T)
            self.assertEqual(D.naruto(g, T), ref, g)
            self.assertEqual(D.naruto_states(g, T)[0], ref, g)
            coord_wrong += D.naruto_coord(g, T)[0] != ref
        self.assertGreater(coord_wrong, 0)                      # 只按坐标记，随机数据上也会错

    def test_best_trace(self):
        ans, best, ev = D.naruto_best_trace(D.G_TRAP, D.T_TRAP)
        self.assertEqual(ans, 6)
        pushes = [(e[2], e[3]) for e in ev if e[0] == "push" and e[1] == (0, 2)]
        self.assertEqual(pushes, [(0, 2), (1, 4)])              # 第二步记零，第四步带一点来，放行
        for e in ev:
            if e[0] == "prune":
                self.assertLessEqual(e[2], e[3])

    def test_super_source(self):
        mat = D.MS_GRID
        got = D.update_matrix(mat)
        sd, layers = D.super_source_bfs(mat)
        n, m = len(mat), len(mat[0])
        srcs = [(i, j) for i in range(n) for j in range(m) if mat[i][j] == 0]
        self.assertEqual(sorted(layers[1]), srcs)               # 第一层恰好是全部源点
        for i in range(n):
            for j in range(m):
                self.assertEqual(sd[i][j] - 1, got[i][j])
                self.assertEqual(got[i][j], min(abs(i - a) + abs(j - b) for a, b in srcs))

    def test_flood(self):
        ok, water, ev = D.flood_trace(D.FL_H, D.FL_SRC, D.FL_HQ)
        self.assertTrue(ok)
        self.assertEqual(ok, D.flood_army(D.FL_H, D.FL_SRC, D.FL_HQ))
        self.assertEqual(water, flood_by_source(D.FL_H, D.FL_SRC))
        self.assertFalse(D.flood_army(D.FL_H, [D.FL_SRC[1]], D.FL_HQ))  # 只有右边的水：淹不到
        hx, hy = D.FL_HQ
        near = (hx - 1, hy)
        self.assertEqual(D.FL_H[hx][hy], 4)
        self.assertEqual([D.FL_H[x][y] for x, y in D.FL_SRC], [6, 3])
        wets = [(e[2], e[3]) for e in ev if e[0] == "wet" and e[1] == near]
        self.assertEqual(wets, [(3, -1), (6, 3)])                 # 先淹到三，再被六抬高
        rnd = random.Random(29)
        for _ in range(300):
            n, m = rnd.randint(1, 4), rnd.randint(1, 5)
            h = [[rnd.randint(0, 6) for _ in range(m)] for _ in range(n)]
            src = [(rnd.randrange(n), rnd.randrange(m)) for _ in range(rnd.randint(1, 3))]
            w = flood_by_source(h, src)
            self.assertEqual(D.flood_trace(h, src, (0, 0))[1], w)
            hq = (rnd.randrange(n), rnd.randrange(m))
            self.assertEqual(D.flood_army(h, src, hq), w[hq[0]][hq[1]] >= 0)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("statebfs.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("两点查克拉，直接打穿手下走近路，五步", beats["problem"])
        self.assertIn("只能绕开所有手下，七步", beats["problem"])
        self.assertIn("五和七都对", beats["naive"])
        self.assertIn("三行五列，只有一点查克拉", beats["naive"])
        self.assertIn("第二步就到了中间这一格", beats["wrong"])
        self.assertIn("第四步才到同一格，手里还剩一点", beats["wrong"])
        self.assertIn("八步。正确答案是六步", beats["wrong"])
        self.assertIn("下层第二步到，上层第四步到", beats["layers"])
        self.assertIn("第六步被找到", beats["layers"])
        self.assertIn("这里是三十", beats["layers"])
        self.assertIn("第二步记下零，第四步带着一点来", beats["code"])
        self.assertIn("右边的水位是三", beats["flood"])
        self.assertIn("高四的司令部", beats["flood"])
        self.assertIn("左边水位六", beats["flood"])


if __name__ == "__main__":
    unittest.main()
