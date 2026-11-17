"""带状态 BFS 与多源 BFS 片的数据层：讲义 naruto / update_matrix / flood_army 原样，另加插桩与对照版本。

约定与讲义一致（W12 2.4–2.6 节）：四方向顺序 DIRS = 上、下、左、右；'@' 鸣人，'+' 佐助，'#' 大蛇丸的手下，
走进 '#' 花 1 点查克拉；出队时判断是否到达佐助。

- naruto / update_matrix / flood_army：讲义原样。
- naruto_coord：只按坐标记 visited 的错误写法（片中演示的反例，不是讲义代码）。
- naruto_states：visited 按（行、列、剩余查克拉）三维记的写法，插桩交出每个状态的步数与前驱。
- naruto_best_trace：讲义 naruto 逐行插桩，交出 best 表、入队事件与剪枝事件。
- super_source_bfs：在图外加一个超级源点、向每个源点连边，再跑普通单源 BFS（对照多源 BFS）。
- flood_trace：讲义 flood_army 逐行插桩，交出每次「淹没 / 水位抬高」事件。
"""
from __future__ import annotations

from collections import deque

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))

# 讲义 2.4 节样例
G_COURSE = ["@####",
            ".#..+",
            "....."]

# 反例：只按坐标记 visited 会错（T = 1）
G_TRAP = ["@#.#+",
          "...##",
          "....."]
T_TRAP = 1


# ---------------------------------------------------------------- 讲义原样
def naruto(grid, T):
    n, m = len(grid), len(grid[0])
    sx = sy = gx = gy = -1
    for i in range(n):
        for j in range(m):
            if grid[i][j] == '@':
                sx, sy = i, j
            elif grid[i][j] == '+':
                gx, gy = i, j
    DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
    # visited[x][y] = 到达 (x,y) 时曾拥有过的最大剩余查克拉
    best = [[-1] * m for _ in range(n)]
    best[sx][sy] = T
    q = deque([(sx, sy, T, 0)])
    while q:
        x, y, t, step = q.popleft()
        if (x, y) == (gx, gy):
            return step
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nt = t - 1 if grid[nx][ny] == '#' else t
            if nt < 0:
                continue
            if nt <= best[nx][ny]:            # 已经用更多查克拉到过这里，剪枝
                continue
            best[nx][ny] = nt
            q.append((nx, ny, nt, step + 1))
    return -1


def update_matrix(mat):
    n, m = len(mat), len(mat[0])
    dist = [[-1] * m for _ in range(n)]
    q = deque()
    for i in range(n):
        for j in range(m):
            if mat[i][j] == 0:
                dist[i][j] = 0
                q.append((i, j))                # 全部 0 一起入队
    DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < m and dist[nx][ny] < 0:
                dist[nx][ny] = dist[x][y] + 1
                q.append((nx, ny))
    return dist


def flood_army(height, sources, hq):
    """height: 二维高度；sources: 放水点列表；hq: 司令部坐标。"""
    n, m = len(height), len(height[0])
    DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
    water = [[-1] * m for _ in range(n)]        # 记录淹没该格的水位
    q = deque()
    for sx, sy in sources:
        if water[sx][sy] < height[sx][sy]:
            water[sx][sy] = height[sx][sy]
            q.append((sx, sy))
    while q:
        x, y = q.popleft()
        level = water[x][y]
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            if height[nx][ny] < level and water[nx][ny] < level:
                water[nx][ny] = level          # 水位更高才值得再扩展
                q.append((nx, ny))
    hx, hy = hq
    return water[hx][hy] >= 0


# ---------------------------------------------------------------- 鸣人和佐助：对照与插桩
def find(grid):
    s = g = None
    for i, row in enumerate(grid):
        for j, ch in enumerate(row):
            if ch == '@':
                s = (i, j)
            elif ch == '+':
                g = (i, j)
    return s, g


def naruto_coord(grid, T):
    """错误写法：visited 只记坐标。返回 (答案, 每格第一次被标记时的 (步数, 剩余查克拉))。"""
    n, m = len(grid), len(grid[0])
    (sx, sy), goal = find(grid)
    seen = {(sx, sy): (0, T)}
    q = deque([(sx, sy, T, 0)])
    while q:
        x, y, t, step = q.popleft()
        if (x, y) == goal:
            return step, seen
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nt = t - 1 if grid[nx][ny] == '#' else t
            if nt < 0 or (nx, ny) in seen:
                continue
            seen[(nx, ny)] = (step + 1, nt)
            q.append((nx, ny, nt, step + 1))
    return -1, seen


def naruto_coord_path(grid, T):
    """错误写法实际找到的那条路（沿第一次标记的前驱倒推）。"""
    n, m = len(grid), len(grid[0])
    (sx, sy), goal = find(grid)
    prev, seen = {}, {(sx, sy)}
    q = deque([(sx, sy, T)])
    while q:
        x, y, t = q.popleft()
        if (x, y) == goal:
            break
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nt = t - 1 if grid[nx][ny] == '#' else t
            if nt < 0 or (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny, nt))
    if goal not in prev:
        return None
    path = [goal]
    while path[-1] != (sx, sy):
        path.append(prev[path[-1]])
    return path[::-1]


def naruto_states(grid, T, stop=False):
    """visited 按（行、列、剩余查克拉）记。返回 (答案, dist{状态: 步数}, prev{状态: 前驱状态})。

    stop=False 时不在终点提前返回，搜完全部可达状态（画分层图上每个状态的步数用）。
    """
    n, m = len(grid), len(grid[0])
    (sx, sy), goal = find(grid)
    s0 = (sx, sy, T)
    dist, prev = {s0: 0}, {}
    q = deque([s0])
    ans = -1
    while q:
        x, y, t = st = q.popleft()
        if (x, y) == goal and ans < 0:
            ans = dist[st]
            if stop:
                break
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nt = t - 1 if grid[nx][ny] == '#' else t
            ns = (nx, ny, nt)
            if nt < 0 or ns in dist:
                continue
            dist[ns] = dist[st] + 1
            prev[ns] = st
            q.append(ns)
    return ans, dist, prev


def state_path(grid, T):
    """最短路的状态序列 [(行, 列, 剩余查克拉)]，从起点到佐助。"""
    ans, dist, prev = naruto_states(grid, T, stop=True)
    _, goal = find(grid)
    end = min((s for s in dist if s[:2] == goal), key=lambda s: dist[s])
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    return path[::-1]


def naruto_best_trace(grid, T):
    """讲义 naruto 逐行插桩：返回 (答案, best 表, 事件)。

    事件：("push", (x, y), nt, step) 入队并更新 best；("prune", (x, y), nt, best 旧值, step) 被剪枝。
    """
    n, m = len(grid), len(grid[0])
    (sx, sy), (gx, gy) = find(grid)
    best = [[-1] * m for _ in range(n)]
    best[sx][sy] = T
    q = deque([(sx, sy, T, 0)])
    ev = [("push", (sx, sy), T, 0)]
    while q:
        x, y, t, step = q.popleft()
        if (x, y) == (gx, gy):
            return step, best, ev
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            nt = t - 1 if grid[nx][ny] == '#' else t
            if nt < 0:
                continue
            if nt <= best[nx][ny]:
                ev.append(("prune", (nx, ny), nt, best[nx][ny], step + 1))
                continue
            best[nx][ny] = nt
            q.append((nx, ny, nt, step + 1))
            ev.append(("push", (nx, ny), nt, step + 1))
    return -1, best, ev


def n_states(grid, T):
    return len(grid) * len(grid[0]) * (T + 1)


# ---------------------------------------------------------------- 多源 BFS = 超级源点
MS_GRID = [[1, 1, 1, 1, 1, 1],
           [1, 0, 1, 1, 1, 1],
           [1, 1, 1, 1, 1, 0],
           [1, 1, 1, 0, 1, 1]]


def super_source_bfs(mat):
    """在图外加一个超级源点 S（编号 n*m），向每个 0 连一条边；从 S 跑普通单源 BFS。返回 (各格到 S 的距离, 每层的格子)。"""
    n, m = len(mat), len(mat[0])
    S = n * m
    adj = {S: [i * m + j for i in range(n) for j in range(m) if mat[i][j] == 0]}
    for i in range(n):
        for j in range(m):
            adj[i * m + j] = [(i + dx) * m + j + dy for dx, dy in DIRS if 0 <= i + dx < n and 0 <= j + dy < m]
    d = {S: 0}
    q = deque([S])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in d:
                d[v] = d[u] + 1
                q.append(v)
    dist = [[d[i * m + j] for j in range(m)] for i in range(n)]
    layers = {}
    for i in range(n):
        for j in range(m):
            layers.setdefault(dist[i][j], []).append((i, j))
    return dist, layers


# ---------------------------------------------------------------- 水淹七军：两个放水点
FL_H = [[6, 1, 1, 1, 1, 3],
        [9, 9, 9, 4, 9, 9]]
FL_SRC = [(0, 0), (0, 5)]
FL_HQ = (1, 3)


def flood_trace(height, sources, hq):
    """讲义 flood_army 逐行插桩：返回 (是否被淹, 最终 water, 事件)。

    事件：("src", (x, y), 水位) 放水点入队；("pop", (x, y), 水位) 出队；
          ("wet", (x, y), 新水位, 旧水位) 淹没或把水位抬高并入队。
    """
    n, m = len(height), len(height[0])
    water = [[-1] * m for _ in range(n)]
    q = deque()
    ev = []
    for sx, sy in sources:
        if water[sx][sy] < height[sx][sy]:
            water[sx][sy] = height[sx][sy]
            q.append((sx, sy))
            ev.append(("src", (sx, sy), height[sx][sy]))
    while q:
        x, y = q.popleft()
        level = water[x][y]
        ev.append(("pop", (x, y), level))
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < m):
                continue
            if height[nx][ny] < level and water[nx][ny] < level:
                ev.append(("wet", (nx, ny), level, water[nx][ny]))
                water[nx][ny] = level
                q.append((nx, ny))
    hx, hy = hq
    return water[hx][hy] >= 0, water, ev


if __name__ == "__main__":
    print("讲义", naruto(G_COURSE, 2), naruto(G_COURSE, 0), "坐标", naruto_coord(G_COURSE, 2)[0],
          naruto_coord(G_COURSE, 0)[0])
    print("反例", naruto(G_TRAP, T_TRAP), naruto_coord(G_TRAP, T_TRAP)[0], naruto_states(G_TRAP, T_TRAP)[0])
    print("坐标路", naruto_coord_path(G_TRAP, T_TRAP), naruto_coord(G_TRAP, T_TRAP)[1])
    print("正确路", state_path(G_TRAP, T_TRAP))
    print("样例路", state_path(G_COURSE, 2), state_path(G_COURSE, 0))
    a, dist, _ = naruto_states(G_TRAP, T_TRAP)
    for t in (1, 0):
        print(t, [[dist.get((i, j, t), '.') for j in range(5)] for i in range(3)])
    a, best, ev = naruto_best_trace(G_TRAP, T_TRAP)
    print("best", best, [e for e in ev if e[0] == "prune"])
    print("states", n_states(G_TRAP, T_TRAP), len(dist))
    print(update_matrix(MS_GRID), super_source_bfs(MS_GRID))
    print(flood_army([[5, 2, 2], [4, 1, 2], [3, 3, 2]], [(0, 0)], (1, 1)),
          flood_army([[5, 2, 2], [4, 1, 2], [3, 3, 2]], [(1, 1)], (0, 0)))
    r, w, ev = flood_trace(FL_H, FL_SRC, FL_HQ)
    print(r, w, flood_army(FL_H, [FL_SRC[1]], FL_HQ))
    for e in ev:
        print(e)
