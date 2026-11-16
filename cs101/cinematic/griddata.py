"""网格 DP 与搜索分界片的数据层：讲义 min_path_sum / dijkstra 原样，另加插桩版本交出整张表与事件。

约定与讲义一致（W12 第 6 节；Dijkstra 见第 3 节）：
- min_path_sum：讲义原样，只能向右 / 向下，讲义输出 7。
- dijkstra(n, adj, src)：讲义原样；网格建成有向图，走进格子 v 的边权 = grid[v]，起点自身的数另加。
- naive_four：把 min_path_sum 照搬到四方向——同样按行填表，转移取上下左右四个邻居的最小值；
  还没算到的格子当作无穷大（这是片中演示的错误写法，不是讲义代码）。
- grid_dijkstra：把讲义 mountain_path 的「高度差」换成「走进去那一格的数」，起点距离为 grid[0][0]；
  插桩记录出堆顺序与前驱（test_grid 对撞讲义 dijkstra 原样结果）。
- count_paths：只能右 / 下的路径计数 dp[i][j] = dp[i-1][j] + dp[i][j-1]（讲义判断表「求方案数」一行）。
"""
from __future__ import annotations

import heapq

INF = float("inf")

# 讲义第 6 节示例
G0 = [[1, 3, 1],
      [1, 5, 1],
      [4, 2, 1]]

# 四方向反例：9 是高地、1 是平路；最好的路要在第三列往上走一步，只能右、下走时绕不过去
G4 = [[1, 9, 9, 9, 9],
      [1, 9, 9, 9, 9],
      [1, 9, 1, 1, 1],
      [1, 1, 1, 9, 1]]

DIRS4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ---------------------------------------------------------------- 讲义原样
def min_path_sum(grid):
    n, m = len(grid), len(grid[0])
    dp = [[0] * m for _ in range(n)]
    dp[0][0] = grid[0][0]
    for j in range(1, m):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
    for i in range(1, n):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
    for i in range(1, n):
        for j in range(1, m):
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
    return dp[n - 1][m - 1]


def dijkstra(n, adj, src):
    """adj: [(邻居, 权重)] 的邻接表；返回 src 到各点的最短距离。"""
    INF = float('inf')
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:                  # 过期条目，跳过
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


# ---------------------------------------------------------------- 画面用：插桩版本
def dp_table(grid):
    """与 min_path_sum 逐行同逻辑，交出整张表和填表顺序 [(i, j, 取自哪一格或 None)]。"""
    n, m = len(grid), len(grid[0])
    dp = [[0] * m for _ in range(n)]
    order = [(0, 0, None)]
    dp[0][0] = grid[0][0]
    for j in range(1, m):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
        order.append((0, j, (0, j - 1)))
    for i in range(1, n):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
        order.append((i, 0, (i - 1, 0)))
    for i in range(1, n):
        for j in range(1, m):
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
            order.append((i, j, (i - 1, j) if dp[i - 1][j] <= dp[i][j - 1] else (i, j - 1)))
    return dp, order


def dp_path(grid):
    """按 dp 表从终点倒推一条最优路径（只能右 / 下；并列时取上方）。"""
    dp, _ = dp_table(grid)
    i, j = len(grid) - 1, len(grid[0]) - 1
    path = [(i, j)]
    while (i, j) != (0, 0):
        if i and (j == 0 or dp[i - 1][j] <= dp[i][j - 1]):
            i -= 1
        else:
            j -= 1
        path.append((i, j))
    return path[::-1]


def naive_four(grid):
    """错误写法：按行填表，取上下左右四个邻居的最小值，还没算到的格子当作无穷大。返回整张表。"""
    n, m = len(grid), len(grid[0])
    dp = [[INF] * m for _ in range(n)]
    dp[0][0] = grid[0][0]
    for i in range(n):
        for j in range(m):
            if (i, j) == (0, 0):
                continue
            best = min((dp[i + dx][j + dy] for dx, dy in DIRS4
                        if 0 <= i + dx < n and 0 <= j + dy < m), default=INF)
            dp[i][j] = best + grid[i][j]
    return dp


def naive_ready(grid, i, j):
    """按行填到 (i, j) 时，它的四个邻居里哪些已经算好、哪些还是无穷大。"""
    n, m = len(grid), len(grid[0])
    done, todo = [], []
    for dx, dy in DIRS4:
        a, b = i + dx, j + dy
        if 0 <= a < n and 0 <= b < m:
            (done if (a, b) < (i, j) else todo).append((a, b))
    return done, todo


def grid_adj(grid):
    """网格建成讲义 dijkstra 用的邻接表：节点 i*m+j，走进邻居 v 的边权是 v 格的数。"""
    n, m = len(grid), len(grid[0])
    adj = [[] for _ in range(n * m)]
    for i in range(n):
        for j in range(m):
            for dx, dy in DIRS4:
                a, b = i + dx, j + dy
                if 0 <= a < n and 0 <= b < m:
                    adj[i * m + j].append((a * m + b, grid[a][b]))
    return adj


def grid_dijkstra(grid):
    """mountain_path 改代价后的插桩版：返回 (答案, 出堆序列 [(d, (x, y))], dist, prev)。弹出终点即返回。"""
    n, m = len(grid), len(grid[0])
    gx, gy = n - 1, m - 1
    dist = [[INF] * m for _ in range(n)]
    dist[0][0] = grid[0][0]
    prev = {}
    pq = [(grid[0][0], 0, 0)]
    pops = []
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist[x][y]:
            continue
        pops.append((d, (x, y)))
        if (x, y) == (gx, gy):
            return d, pops, dist, prev
        for dx, dy in DIRS4:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nd = d + grid[nx][ny]
            if nd < dist[nx][ny]:
                dist[nx][ny] = nd
                prev[(nx, ny)] = (x, y)
                heapq.heappush(pq, (nd, nx, ny))
    return -1, pops, dist, prev


def best_path(grid):
    _, _, _, prev = grid_dijkstra(grid)
    c = (len(grid) - 1, len(grid[0]) - 1)
    path = [c]
    while c != (0, 0):
        c = prev[c]
        path.append(c)
    return path[::-1]


def count_paths(n, m):
    """只能右 / 下：dp[i][j] = dp[i-1][j] + dp[i][j-1]，第一行第一列都是 1。返回整张表。"""
    dp = [[1] * m for _ in range(n)]
    for i in range(1, n):
        for j in range(1, m):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp


def simple_paths(n, m):
    """四方向、不许重复经过同一格：从左上到右下的路径条数（回溯一条条数）。"""
    seen = [[False] * m for _ in range(n)]
    cnt = 0

    def go(x, y):
        nonlocal cnt
        if (x, y) == (n - 1, m - 1):
            cnt += 1
            return
        for dx, dy in DIRS4:
            a, b = x + dx, y + dy
            if 0 <= a < n and 0 <= b < m and not seen[a][b]:
                seen[a][b] = True
                go(a, b)
                seen[a][b] = False
    seen[0][0] = True
    go(0, 0)
    return cnt


if __name__ == "__main__":
    print(min_path_sum(G0), dp_table(G0)[0], dp_path(G0))
    print("right/down", min_path_sum(G4), dp_table(G4)[0])
    print("naive", naive_four(G4))
    a, pops, dist, _ = grid_dijkstra(G4)
    print("dij", a, pops, best_path(G4))
    print("adj", dijkstra(20, grid_adj(G4), 0)[-1] + G4[0][0])
    print(count_paths(4, 5), simple_paths(4, 5), simple_paths(3, 3))
