"""Floyd 片的数据层：讲义 modern.py floyd（第 7 章 5.2 节）与 RumorNetwork.best_source（第 1 章「股市的传言」）原样插桩。

图是第 1 章五个经纪人 B1…B5（下标 0…4）、10 条有向带权边；矩阵 distance[from][to]，「到不了」记 INF。
画面和旁白里的每个数字都从这里来；test_floyd.py 用 n 次 Dijkstra、Bellman-Ford、穷举简单路径对撞。
"""
from __future__ import annotations

INF = float("inf")
N = 5
LABELS = ["B_1", "B_2", "B_3", "B_4", "B_5"]
# 讲义 demo.cpp 的 add_route 顺序
EDGES = [(0, 3, 4), (0, 4, 3), (0, 1, 8), (1, 4, 8), (2, 0, 6), (2, 1, 7), (2, 3, 10), (2, 4, 2), (4, 0, 5), (4, 1, 5)]

# 「中转点必须在最外层」的反例：链 v0→v2→v3→v1，权都为 1（4 个点）
CHAIN_N = 4
CHAIN = [(0, 2, 1), (2, 3, 1), (3, 1, 1)]


def adjacency(n=N, edges=EDGES):
    adj = [[INF] * n for _ in range(n)]
    for i in range(n):
        adj[i][i] = 0
    for u, v, w in edges:
        adj[u][v] = min(adj[u][v], w)
    return adj


def floyd_trace(n=N, edges=EDGES):
    """讲义 floyd 原样（via 最外层），插桩：每轮 via 记下变小的格 (from, to, 旧值, 新值)。

    返回 (最终矩阵, [每轮开始时的矩阵快照], [每轮的变化列表])。
    """
    unreachable = INF
    distance = [[w if w < INF else unreachable for w in row] for row in adjacency(n, edges)]
    snaps, changes = [], []
    for via in range(n):
        snaps.append([row[:] for row in distance])
        ch = []
        for source in range(n):
            for target in range(n):
                if distance[source][via] != unreachable and distance[via][target] != unreachable:
                    candidate = distance[source][via] + distance[via][target]
                    if candidate < distance[source][target]:
                        ch.append((source, target, distance[source][target], candidate))
                    distance[source][target] = min(distance[source][target], candidate)
        changes.append(ch)
    return distance, snaps, changes


def floyd_wrong_order(n=CHAIN_N, edges=CHAIN):
    """常见错法：中转点放最内层（for from: for to: for via）。返回结果矩阵。"""
    d = adjacency(n, edges)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def best_source(n=N, edges=EDGES):
    """讲义 RumorNetwork::best_source：每行最大值（离心率）里取最小；整行有 INF 的起点不合格。

    返回 (答案下标或 None, 每行最大值列表)。
    """
    shortest, _, _ = floyd_trace(n, edges)
    result = None
    smallest = INF
    ecc = []
    for source in range(n):
        largest = 0
        for target in range(n):
            d = shortest[source][target]
            largest = d if d > largest else largest
        ecc.append(largest)
        if largest < smallest:
            smallest = largest
            result = source
    return result, ecc


def path(n=N, edges=EDGES):
    """带 path 矩阵的 Floyd（讲义：path[i][j] 是 vj 前面那个顶点，更新时 path[i][j] = path[k][j]）。"""
    d = adjacency(n, edges)
    p = [[(i if (i == j or d[i][j] < INF) else -1) for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
                    p[i][j] = p[k][j]
    return d, p


def route(i, j, n=N, edges=EDGES):
    """从 path 矩阵倒着读出 i→j 的顶点序列。"""
    _, p = path(n, edges)
    if p[i][j] == -1:
        return None
    seq = [j]
    while seq[-1] != i:
        seq.append(p[i][seq[-1]])
    return seq[::-1]
