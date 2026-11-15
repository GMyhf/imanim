"""Dijkstra 片的数据层：讲义 dijkstra / mountain_path 原样插桩，记录出堆、跳过、松弛事件。

约定与课件一致（W12 P18–P19、讲义第 3 节）：堆里放 (距离, 节点)；出堆时 d > dist[u] 即过期条目、跳过；
走山路每步代价 = 相邻格高度差的绝对值，弹出终点即返回。
"""
from __future__ import annotations

import heapq

INF = float("inf")

# 讲义示例：四个点的有向带权图
N = 4
ADJ = [[(1, 4), (2, 1)],
       [(3, 1)],
       [(1, 2), (3, 5)],
       []]
EDGES = [(u, v, w) for u, lst in enumerate(ADJ) for v, w in lst]


def dijkstra_trace(n=N, adj=ADJ, src=0):
    """讲义 dijkstra 插桩。事件：("pop", d, u) / ("stale", d, u) / ("relax", u, v, nd)。"""
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    ev = []
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            ev.append(("stale", d, u))
            continue
        ev.append(("pop", d, u))
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
                ev.append(("relax", u, v, nd))
    return dist, ev


def bfs_hops_cost(n=N, adj=ADJ, src=0):
    """把带权图当无权图做 BFS：第一次碰到某点时，沿那条边累加的代价（会算错）。"""
    from collections import deque
    cost = [None] * n
    cost[src] = 0
    q = deque([src])
    while q:
        u = q.popleft()
        for v, w in adj[u]:
            if cost[v] is None:
                cost[v] = cost[u] + w
                q.append(v)
    return cost


# 讲义「走山路」示例
GRID = [[1, 5, 9],
        [2, 3, 8],
        [4, 4, 7]]
START, GOAL = (0, 0), (2, 2)
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def mountain_trace(grid=GRID, start=START, goal=GOAL):
    """讲义 mountain_path 插桩。返回 (答案, 事件, dist)。事件同上，节点为 (x, y)；另有 ("goal", d, cell)。"""
    n, m = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal
    ev = []
    if grid[sx][sy] == '#' or grid[gx][gy] == '#':
        return -1, ev, None
    dist = [[INF] * m for _ in range(n)]
    dist[sx][sy] = 0
    pq = [(0, sx, sy)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if (x, y) == (gx, gy):
            ev.append(("goal", d, (x, y)))
            return d, ev, dist
        if d > dist[x][y]:
            ev.append(("stale", d, (x, y)))
            continue
        ev.append(("pop", d, (x, y)))
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m) or grid[nx][ny] == '#':
                continue
            nd = d + abs(grid[nx][ny] - grid[x][y])
            if nd < dist[nx][ny]:
                dist[nx][ny] = nd
                heapq.heappush(pq, (nd, nx, ny))
                ev.append(("relax", (x, y), (nx, ny), nd))
    return -1, ev, dist


def mountain_path(grid=GRID, start=START, goal=GOAL):
    """完整跑一遍 Dijkstra 并记前驱，回溯出一条代价最小的路径（画面用）。"""
    n, m = len(grid), len(grid[0])
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, INF):
            continue
        for dx, dy in DIRS:
            v = (u[0] + dx, u[1] + dy)
            if 0 <= v[0] < n and 0 <= v[1] < m and grid[v[0]][v[1]] != '#':
                nd = d + abs(grid[v[0]][v[1]] - grid[u[0]][u[1]])
                if nd < dist.get(v, INF):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return path[::-1], dist[goal]


# 片头用的带权格点图（无向，权重固定随机种子），只做氛围：按出堆顺序点亮
TITLE_ROWS, TITLE_COLS = 4, 7


def title_graph(seed=11):
    import random
    rng = random.Random(seed)
    idx = lambda r, c: r * TITLE_COLS + c  # noqa: E731
    edges = []
    for r in range(TITLE_ROWS):
        for c in range(TITLE_COLS):
            if c + 1 < TITLE_COLS:
                edges.append((idx(r, c), idx(r, c + 1), rng.randint(1, 9)))
            if r + 1 < TITLE_ROWS:
                edges.append((idx(r, c), idx(r + 1, c), rng.randint(1, 9)))
    n = TITLE_ROWS * TITLE_COLS
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    return n, edges, adj
