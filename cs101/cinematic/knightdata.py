"""马走日与数湖泊片的数据层：讲义 knight_tours / count_lakes 原样 + 插桩版（含「写反了」的两个变体）。

约定与讲义一致（W09 1.5–1.6 节）：马走日 n 行 m 列、从 (sx, sy) 出发、八个方向按 KNIGHT 的顺序试；
数湖泊八连通，DIRS8 按 (-1,-1) (-1,0) … (1,1) 的顺序试。画面和旁白里的数字都从这里取。

插桩版把讲义的递归 / 显式栈改写成同构的递归，只多一个开关：
- 马走日 undo=False：去掉 `visited[nx][ny] = False` 那一行（忘了回溯）；
- 数湖泊 undo=True：递归回来后把格子改回 'W'（不该回溯却回溯了）。
"""
from __future__ import annotations

import sys

KNIGHT = ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
          (1, -2), (1, 2), (2, -1), (2, 1))

BOARD = (5, 4, 0, 0)                     # 讲义样例：5×4 棋盘，从左上角出发

LAKE = ["WW..",                          # 片中小网格：同样 5×4，三个湖
        "WWW.",
        "WWW.",
        "....",
        "W.WW"]

SAMPLE = [                               # 讲义 02386 样例
    "W........WW.",
    ".WWW.....WWW",
    "....WW...WW.",
    ".........WW.",
    ".........W..",
    "..W......W..",
    ".W.W.....WW.",
    "W.W.W.....W.",
    ".W.W......W.",
    "..W.......W.",
]


# ---------------------------------------------------------------- 讲义原版
def knight_tours(n, m, sx, sy):
    """讲义 1.5 节原样。"""
    visited = [[False] * m for _ in range(n)]
    visited[sx][sy] = True
    total = n * m
    count = 0

    def dfs(x, y, step):
        nonlocal count
        if step == total:
            count += 1
            return
        for dx, dy in KNIGHT:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and not visited[nx][ny]:
                visited[nx][ny] = True
                dfs(nx, ny, step + 1)
                visited[nx][ny] = False        # 回溯
    dfs(sx, sy, 1)
    return count


def count_lakes(grid):
    """讲义 1.6 节原样（迭代版 DFS，显式栈）。"""
    n, m = len(grid), len(grid[0])
    g = [list(row) for row in grid]
    DIRS8 = tuple((di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1)
                  if (di, dj) != (0, 0))

    def flood(i, j):
        """迭代版 DFS：用显式栈，避免递归过深。"""
        stack = [(i, j)]
        g[i][j] = '.'
        while stack:
            x, y = stack.pop()
            for dx, dy in DIRS8:
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < m and g[nx][ny] == 'W':
                    g[nx][ny] = '.'          # 标记后再入栈，避免重复入栈
                    stack.append((nx, ny))

    cnt = 0
    for i in range(n):
        for j in range(m):
            if g[i][j] == 'W':
                flood(i, j)
                cnt += 1
    return cnt


DIRS8 = tuple((di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0))


# ---------------------------------------------------------------- 插桩：马走日
def knight_trace(n, m, sx, sy, undo=True):
    """讲义 knight_tours 的插桩版。返回 (count, calls, events, tours)。

    events：("in", x, y, step) 进入一次 dfs；("out", x, y) 回溯撤销标记（undo=False 时没有）；
    ("ret", x, y) 一次 dfs 返回；("tour",) 走满一次。tours 是每条完整走法的格子序列。
    """
    visited = [[False] * m for _ in range(n)]
    visited[sx][sy] = True
    total = n * m
    count = calls = 0
    ev, tours, path = [], [], [(sx, sy)]
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 10 * total + 100))

    def dfs(x, y, step):
        nonlocal count, calls
        calls += 1
        ev.append(("in", x, y, step))
        if step == total:
            count += 1
            tours.append(tuple(path))
            ev.append(("tour",))
            ev.append(("ret", x, y))
            return
        for dx, dy in KNIGHT:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and not visited[nx][ny]:
                visited[nx][ny] = True
                path.append((nx, ny))
                dfs(nx, ny, step + 1)
                path.pop()
                if undo:
                    visited[nx][ny] = False
                    ev.append(("out", nx, ny))
        ev.append(("ret", x, y))
    dfs(sx, sy, 1)
    sys.setrecursionlimit(old)
    return count, calls, ev, tours


def snapshots(n, m, sx, sy, undo=True):
    """每次进入 dfs 时的当前路径（格子序列）。马走日片的快进动画按它逐帧画。"""
    out, path = [], []
    for e in knight_trace(n, m, sx, sy, undo)[2]:
        if e[0] == "in":
            del path[e[3] - 1:]
            path.append((e[1], e[2]))
            out.append(tuple(path))
    return out


def max_step(n, m, sx, sy, undo=True):
    return max(e[3] for e in knight_trace(n, m, sx, sy, undo)[2] if e[0] == "in")


# ---------------------------------------------------------------- 插桩：数湖泊（递归写法，与马走日同构）
def lake_trace(grid, undo=False):
    """递归版 flood fill，结构与 knight_tours 一一对应。返回 (湖数, 调用次数, events, 每个湖的格子)。

    events：("start", i, j) 外层循环发现一格水、湖数加一；("in", x, y, depth) 进入一次 dfs；
    ("out", x, y) 回溯把格子改回水（只有 undo=True 才有）。
    """
    n, m = len(grid), len(grid[0])
    g = [list(row) for row in grid]
    cnt = calls = 0
    ev, lakes = [], []

    def dfs(x, y, depth):
        nonlocal calls
        calls += 1
        ev.append(("in", x, y, depth))
        lakes[-1].add((x, y))
        for dx, dy in DIRS8:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and g[nx][ny] == 'W':
                g[nx][ny] = '.'
                dfs(nx, ny, depth + 1)
                if undo:
                    g[nx][ny] = 'W'          # 写反了：不该撤销
                    ev.append(("out", nx, ny))

    for i in range(n):
        for j in range(m):
            if g[i][j] == 'W':
                g[i][j] = '.'
                cnt += 1
                lakes.append(set())
                ev.append(("start", i, j))
                dfs(i, j, 1)
    return cnt, calls, ev, lakes


def water(grid):
    return sum(row.count('W') for row in grid)


def knight_moves(n, m, x, y):
    return [(x + dx, y + dy) for dx, dy in KNIGHT if 0 <= x + dx < n and 0 <= y + dy < m]


if __name__ == "__main__":
    print(knight_tours(5, 4, 0, 0), knight_tours(3, 3, 0, 0))
    print(count_lakes(SAMPLE))
    c, k, ev, tours = knight_trace(*BOARD)
    print("马走日", c, k, "第一条", tours[0])
    print("忘了撤销", knight_trace(*BOARD, undo=False)[:2], "最深", max_step(*BOARD, undo=False))
    for gname, gr in (("LAKE", LAKE), ("SAMPLE", SAMPLE)):
        print(gname, water(gr), lake_trace(gr)[:2], lake_trace(gr, True)[:2])
