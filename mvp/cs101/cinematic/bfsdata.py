"""BFS 片的数据层：迷宫 BFS 事件序列、最短路回溯、多源 BFS、入队标记反例、DFS/BFS 访问顺序。

约定与课件一致（W12 P9–P21、讲义 2.1–2.5）：迷宫用 dist 兼作 visited（-1 = 未访问），
四方向顺序 DIRS = 上、下、左、右；出队时判断是否到达终点（讲义 maze_shortest 原样）。
"""
from __future__ import annotations

from collections import deque

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
MAZE = [
    ".....",
    ".###.",
    ".....",
    ".###.",
    ".....",
]
START, GOAL = (0, 0), (4, 4)


def maze_trace(grid=MAZE, start=START, goal=GOAL):
    """讲义 maze_shortest 插桩：返回 (答案, 事件序列, dist)。事件为 ("pop", cell) / ("push", cell, d)。"""
    n, m = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal
    ev = []
    if grid[sx][sy] == '#' or grid[gx][gy] == '#':
        return -1, ev, None
    dist = [[-1] * m for _ in range(n)]
    dist[sx][sy] = 0
    q = deque([(sx, sy)])
    ev.append(("push", (sx, sy), 0))
    while q:
        x, y = q.popleft()
        ev.append(("pop", (x, y)))
        if (x, y) == (gx, gy):
            return dist[x][y], ev, dist
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] != '#' and dist[nx][ny] < 0:
                dist[nx][ny] = dist[x][y] + 1
                q.append((nx, ny))
                ev.append(("push", (nx, ny), dist[nx][ny]))
    return -1, ev, dist


def back_path(dist, goal=GOAL):
    """从终点沿 dist 递减走回起点（按 DIRS 顺序取第一个可行邻居）。"""
    path = [goal]
    x, y = goal
    while dist[x][y] > 0:
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(dist) and 0 <= ny < len(dist[0]) and dist[nx][ny] == dist[x][y] - 1:
                x, y = nx, ny
                break
        path.append((x, y))
    return path[::-1]


def update_matrix(mat):
    """讲义 2.5 节多源 BFS（原样）。"""
    n, m = len(mat), len(mat[0])
    dist = [[-1] * m for _ in range(n)]
    q = deque()
    for i in range(n):
        for j in range(m):
            if mat[i][j] == 0:
                dist[i][j] = 0
                q.append((i, j))
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and dist[nx][ny] < 0:
                dist[nx][ny] = dist[x][y] + 1
                q.append((nx, ny))
    return dist


# 片中演示用的多源网格：三处 0，看几股波纹相遇
MULTI_SHAPE = (7, 11)
MULTI_SOURCES = [(1, 1), (5, 8), (2, 6)]


def multi_grid():
    n, m = MULTI_SHAPE
    mat = [[1] * m for _ in range(n)]
    for i, j in MULTI_SOURCES:
        mat[i][j] = 0
    return mat


def nearest_source(i, j):
    """最近的源（并列取编号小的），给波纹着色用。"""
    return min(range(len(MULTI_SOURCES)),
               key=lambda k: (abs(i - MULTI_SOURCES[k][0]) + abs(j - MULTI_SOURCES[k][1]), k))


# 入队标记反例：s→a、s→b，a→c、b→c
MARK_GRAPH = {"s": ["a", "b"], "a": ["c"], "b": ["c"], "c": []}


def enqueue_log(mark_on_enqueue: bool):
    q, seen, log = deque(["s"]), {"s"}, ["s"]
    done = set()
    while q:
        u = q.popleft()
        if not mark_on_enqueue:
            if u in done:
                continue
            done.add(u)
        for v in MARK_GRAPH[u]:
            if mark_on_enqueue:
                if v in seen:
                    continue
                seen.add(v)
            elif v in done:
                continue
            q.append(v)
            log.append(v)
    return log


# DFS / BFS 访问顺序对比（无墙方格，从中心出发）
OPEN_N = 7


def bfs_order(n=OPEN_N):
    s = (n // 2, n // 2)
    seen, q, order = {s}, deque([s]), []
    while q:
        x, y = q.popleft()
        order.append((x, y))
        for dx, dy in DIRS:
            v = (x + dx, y + dy)
            if 0 <= v[0] < n and 0 <= v[1] < n and v not in seen:
                seen.add(v)
                q.append(v)
    return order


def dfs_order(n=OPEN_N):
    s = (n // 2, n // 2)
    seen, order = set(), []

    def go(u):
        seen.add(u)
        order.append(u)
        for dx, dy in DIRS:
            v = (u[0] + dx, u[1] + dy)
            if 0 <= v[0] < n and 0 <= v[1] < n and v not in seen:
                go(v)
    go(s)
    return order
