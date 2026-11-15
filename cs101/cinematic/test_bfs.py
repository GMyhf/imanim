"""BFS 片数字的独立对撞：讲义输出、Bellman-Ford 式松弛求最短距离、多源 = 各源单源取最小、入队标记反例。

用法（cwd = cs101/cinematic）：python -m unittest test_bfs
"""
import json
from pathlib import Path
import unittest

import bfsdata as B


def relax_dist(grid, start):
    """不用队列：反复松弛到稳定，得到每格最短步数（不可达为 None）。"""
    n, m = len(grid), len(grid[0])
    INF = float("inf")
    d = [[INF] * m for _ in range(n)]
    d[start[0]][start[1]] = 0
    changed = True
    while changed:
        changed = False
        for x in range(n):
            for y in range(m):
                if grid[x][y] == '#' or d[x][y] == INF:
                    continue
                for dx, dy in B.DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] != '#' and d[nx][ny] > d[x][y] + 1:
                        d[nx][ny] = d[x][y] + 1
                        changed = True
    return d


class BFSFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual(B.maze_trace()[0], 8)
        self.assertEqual(B.maze_trace(["..", "##"], (0, 0), (1, 1))[0], -1)
        self.assertEqual(B.update_matrix([[0, 0, 0], [0, 1, 0], [1, 1, 1]]), [[0, 0, 0], [0, 1, 0], [1, 2, 1]])

    def test_maze_dist_is_shortest(self):
        ans, ev, dist = B.maze_trace()
        ref = relax_dist(B.MAZE, B.START)
        for x in range(5):
            for y in range(5):
                if dist[x][y] >= 0:                        # BFS 赋过值的格子，距离都等于真最短距离
                    self.assertEqual(dist[x][y], ref[x][y])
        self.assertEqual(ans, ref[4][4])
        pushes = [e for e in ev if e[0] == "push"]
        self.assertEqual(len(pushes), len({e[1] for e in pushes}))       # 每格最多入队一次
        ds = [e[2] for e in pushes]
        self.assertEqual(ds, sorted(ds))                                  # 入队距离单调不减 = 按层推进

    def test_back_path(self):
        ans, _, dist = B.maze_trace()
        p = B.back_path(dist)
        self.assertEqual((p[0], p[-1], len(p) - 1), (B.START, B.GOAL, ans))
        for (a, b), (c, d) in zip(p, p[1:]):
            self.assertEqual(abs(a - c) + abs(b - d), 1)
            self.assertNotEqual(B.MAZE[c][d], '#')

    def test_multi_source(self):
        mat = B.multi_grid()
        got = B.update_matrix(mat)
        n, m = B.MULTI_SHAPE
        open_grid = ["." * m] * n
        singles = [relax_dist(open_grid, s) for s in B.MULTI_SOURCES]
        for i in range(n):
            for j in range(m):
                self.assertEqual(got[i][j], min(s[i][j] for s in singles))

    def test_mark_on_enqueue(self):
        self.assertEqual(B.enqueue_log(True), ["s", "a", "b", "c"])
        self.assertEqual(B.enqueue_log(False).count("c"), 2)             # 出队才标记：c 入队两次

    def test_orders(self):
        bo, do = B.bfs_order(), B.dfs_order()
        self.assertEqual(len(bo), B.OPEN_N ** 2)
        self.assertEqual(sorted(bo), sorted(do))
        c = B.OPEN_N // 2
        dist = [abs(x - c) + abs(y - c) for x, y in bo]
        self.assertEqual(dist, sorted(dist))                              # BFS 顺序按距离分层

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("bfs.json").read_text(encoding="utf-8"))["beats"])
        for s in ("距离是八", "第一次访问到某个点时，走过的步数就是最短距离", "c 会被 a 放进队列一次，又被 b 放进队列一次"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
