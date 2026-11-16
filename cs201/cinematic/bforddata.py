"""Bellman-Ford 片的数据层：讲义第 7 章 5.3 节 bellman_ford 原样插桩。

图是讲义的 4 点小图：边 <0,1>4、<0,2>5、<1,3>2、<2,1>−3（边序即讲义的松弛次序），
负环版再加 <3,2>−4（环 2→1→3→2 总权 −5）。画面和旁白里的每个数字都从这里来；
test_bford.py 用穷举简单路径、讲义原版函数与 SPFA 对撞。
"""
from __future__ import annotations

from collections import deque

INF = float("inf")
N = 4
EDGES = [(0, 1, 4), (0, 2, 5), (1, 3, 2), (2, 1, -3)]
NEG_EDGE = (3, 2, -4)
REORDER = [(0, 1, 4), (0, 2, 5), (2, 1, -3), (1, 3, 2)]     # 把 <2,1> 排到 <1,3> 前面


# ---------------------------------------------------------------- 讲义原样
def bellman_ford(n, edges, source):
    # edges = [(u, v, w), ...]，w 可以是负数
    INF = float('inf')
    dist = [INF] * n
    dist[source] = 0
    for _ in range(n - 1):              # 最短路至多 n-1 条边
        changed = False
        for u, v, w in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:                 # 一整轮没改动：提前收敛
            break
    for u, v, w in edges:               # 第 n 轮还能松弛 → 负环
        if dist[u] != INF and dist[u] + w < dist[v]:
            return None
    return dist


# ---------------------------------------------------------------- 插桩版（逻辑与上面逐行相同）
def bf_trace(n=N, edges=EDGES, source=0):
    """返回 (rounds, check, result)。

    rounds：每轮一个 dict {"ok": [(u, v, w, 旧, 新), ...] 本轮松弛成功的边（按边序）, "dist": 轮末 dist}；
    提前收敛的那一轮（ok 为空）也记下。check：第 n 轮检查时仍可松弛的边。result：同讲义返回值。
    """
    dist = [INF] * n
    dist[source] = 0
    rounds = []
    for _ in range(n - 1):
        changed = False
        ok = []
        for u, v, w in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                ok.append((u, v, w, dist[v], dist[u] + w))
                dist[v] = dist[u] + w
                changed = True
        rounds.append({"ok": ok, "dist": dist[:]})
        if not changed:
            break
    check = [(u, v, w) for u, v, w in edges if dist[u] != INF and dist[u] + w < dist[v]]
    return rounds, check, (None if check else dist)


def edge_checks(rounds, m, check_round=True):
    """讲义写法实际检查边的次数：每轮扫 m 条边，外加第 n 轮的一次检查扫描（未返回 None 时整轮扫完）。"""
    return len(rounds) * m + (m if check_round else 0)


# ---------------------------------------------------------------- Dijkstra（集合 S 版：进了 S 的点不再改）
def dijkstra_S(n=N, edges=EDGES, source=0):
    """教科书描述的 Dijkstra：每次把 V−S 里 D 最小的点移进 S，S 里的点认定为最终值，不再更新。

    返回 (D, order)：order 是进入 S 的次序 [(点, 当时的 D)]。
    """
    adj = {u: [] for u in range(n)}
    for u, v, w in edges:
        adj[u].append((v, w))
    D = [INF] * n
    D[source] = 0
    S = set()
    order = []
    for _ in range(n):
        cand = [v for v in range(n) if v not in S and D[v] < INF]
        if not cand:
            break
        u = min(cand, key=lambda v: (D[v], v))
        S.add(u)
        order.append((u, D[u]))
        for v, w in adj[u]:
            if v not in S and D[u] + w < D[v]:
                D[v] = D[u] + w
    return D, order


# ---------------------------------------------------------------- 统一加常数为什么不行
def shortest_paths_brute(n, edges, source=0):
    """穷举所有简单路径，返回 {v: (最短长, 路径)}；用来对撞，也用来画「加常数后路径变了」。"""
    adj = {u: [] for u in range(n)}
    for u, v, w in edges:
        adj[u].append((v, w))
    best = {source: (0, [source])}

    def dfs(u, d, path):
        for v, w in adj[u]:
            if v in path:
                continue
            nd = d + w
            if v not in best or nd < best[v][0] or (nd == best[v][0] and len(path) + 1 < len(best[v][1])):
                best[v] = (nd, path + [v])
            dfs(v, nd, path + [v])
    dfs(source, 0, [source])
    return best


SHIFT = 3        # 把最负的 −3 抬到 0


def shifted(edges=EDGES, c=SHIFT):
    return [(u, v, w + c) for u, v, w in edges]


# ---------------------------------------------------------------- 动态规划视角：dp[k][v] = 至多 k 条边的最短长
def dp_table(n=N, edges=EDGES, source=0):
    dp = [[INF] * n]
    dp[0][source] = 0
    for _ in range(n - 1):
        prev = dp[-1]
        cur = prev[:]
        for u, v, w in edges:
            if prev[u] != INF and prev[u] + w < cur[v]:
                cur[v] = prev[u] + w
        dp.append(cur)
    return dp


def dp_paths(n=N, edges=EDGES, source=0):
    """dp_table 的同时记下每格对应的路径：paths[k][v] = 至多 k 条边的一条最短路（顶点列表），到不了为 None。"""
    paths = [[None] * n]
    paths[0][source] = [source]
    best = [[INF] * n]
    best[0][source] = 0
    for _ in range(n - 1):
        pb, pp = best[-1], paths[-1]
        cb, cp = pb[:], [x[:] if x else None for x in pp]
        for u, v, w in edges:
            if pb[u] != INF and pb[u] + w < cb[v]:
                cb[v] = pb[u] + w
                cp[v] = pp[u] + [v]
        best.append(cb)
        paths.append(cp)
    return paths


# ---------------------------------------------------------------- SPFA：只把 dist 刚变小的点放进队列
def spfa(n=N, edges=EDGES, source=0):
    """返回 (dist, 检查边的次数, 入队次数, 事件)；无负环时用。

    事件：("pop", u)、("relax", u, v, 新值)、("push", v)。
    """
    adj = {u: [] for u in range(n)}
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [INF] * n
    dist[source] = 0
    q = deque([source])
    inq = [False] * n
    inq[source] = True
    checks, pushes, ev = 0, 1, [("push", source)]
    while q:
        u = q.popleft()
        inq[u] = False
        ev.append(("pop", u))
        for v, w in adj[u]:
            checks += 1
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                ev.append(("relax", u, v, dist[v]))
                if not inq[v]:
                    q.append(v)
                    inq[v] = True
                    pushes += 1
                    ev.append(("push", v))
    return dist, checks, pushes, ev


def fmt(x):
    return "∞" if x == INF else str(x)


if __name__ == "__main__":
    print(bellman_ford(4, EDGES, 0), bellman_ford(4, EDGES + [NEG_EDGE], 0))
    r, c, res = bf_trace()
    for x in r:
        print(x)
    print("check", c, res, "edge checks", edge_checks(r, 4))
    r2, _, _ = bf_trace(edges=REORDER)
    print("reorder rounds", [x["dist"] for x in r2])
    rn, cn, resn = bf_trace(edges=EDGES + [NEG_EDGE])
    print("neg", [x["dist"] for x in rn], cn, resn)
    print("dijkstra", dijkstra_S())
    print("true", shortest_paths_brute(4, EDGES))
    print("shifted", shortest_paths_brute(4, shifted()))
    print("dp", dp_table())
    print("spfa", spfa())
