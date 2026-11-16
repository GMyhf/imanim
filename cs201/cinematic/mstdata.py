"""最小生成树片的数据：讲义（2026fall 第 7 章 6 节）图 7.23 的带权图，Prim / Kruskal 原样插桩。

画面与旁白里的每个数字都从这里来；test_mst.py 用枚举全部生成树、随机图对撞。
讲义 Python 版写成 Graph 的方法（modern.py#prim / #kruskal），这里把方法体原样搬成函数，
只把 self._adjacency / self.vertices / self.infinity 换成参数，并在关键处记事件。
"""
from __future__ import annotations

from typing import NamedTuple

INF = float("inf")
N = 7
# 图 7.23（无向）：讲义逐步表格里出现的九条边
EDGES = [(0, 1, 20), (0, 4, 1), (4, 5, 15), (5, 3, 12), (5, 6, 10), (6, 3, 8), (6, 2, 2), (2, 1, 6), (1, 3, 4)]


class Edge(NamedTuple):
    source: int
    target: int
    weight: int


def matrix(n=N, edges=EDGES):
    adj = [[INF] * n for _ in range(n)]
    for u, v, w in edges:
        adj[u][v] = adj[v][u] = w
    return adj


def _nearest(distance, used):
    best = None
    for v in range(len(distance)):
        if not used[v] and (best is None or distance[v] < distance[best]):
            best = v
    return best


def prim_trace(source=0, n=N, edges=EDGES):
    """讲义 modern.py#prim 原样；事件：("pick", v, 树边或 None, distance 快照)、("update", v, 旧, 新, from)。"""
    adjacency, vertices, infinity = matrix(n, edges), n, INF
    ev = []
    distance = [infinity] * vertices
    predecessor = [0] * vertices
    used = [False] * vertices
    result: list[Edge] = []
    distance[source] = 0
    for _ in range(vertices):
        vertex = _nearest(distance, used)
        if vertex is None or distance[vertex] == infinity:
            return None, ev
        used[vertex] = True
        if vertex != source:
            result.append(Edge(predecessor[vertex], vertex, distance[vertex]))
        ev.append(("pick", vertex, result[-1] if vertex != source else None, list(distance)))
        for target in range(vertices):
            if not used[target] and adjacency[vertex][target] < distance[target]:
                ev.append(("update", target, distance[target], adjacency[vertex][target], vertex))
                distance[target] = adjacency[vertex][target]
                predecessor[target] = vertex
    return result, ev


def kruskal_trace(n=N, edges=EDGES):
    """讲义 modern.py#kruskal 原样（含冒泡排边、路径减半的 root）；事件：("take"|"skip", Edge)。"""
    adjacency, vertices, infinity = matrix(n, edges), n, INF
    ev = []
    edges = [Edge(source, target, adjacency[source][target])
             for source in range(vertices) for target in range(source + 1, vertices)
             if adjacency[source][target] < infinity]
    for end in range(len(edges) - 1, 0, -1):
        for index in range(end):
            if edges[index].weight > edges[index + 1].weight:
                edges[index], edges[index + 1] = edges[index + 1], edges[index]
    parent = list(range(vertices))

    def root(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    result: list[Edge] = []
    for edge in edges:
        left = root(edge.source)
        right = root(edge.target)
        if left != right:
            parent[left] = right
            result.append(edge)
            ev.append(("take", edge))
        else:
            ev.append(("skip", edge))
    return (result if len(result) + 1 == vertices else None), ev


def sorted_edges():
    return [e for _, e in kruskal_trace()[1]]


def tree_path(tree, a, b):
    """树边集合里 a 到 b 的路径（顶点序列）；Kruskal 舍边时画出那个环。"""
    adj = {}
    for e in tree:
        adj.setdefault(e.source, []).append(e.target)
        adj.setdefault(e.target, []).append(e.source)
    prev, stack = {a: None}, [a]
    while stack:
        u = stack.pop()
        for v in adj.get(u, []):
            if v not in prev:
                prev[v] = u
                stack.append(v)
    if b not in prev:
        return None
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return path[::-1]


def crossing(inside):
    """一端在 inside、一端在外的边（Prim 每一步的候选跨界边）。"""
    return [(u, v, w) for u, v, w in EDGES if (u in inside) != (v in inside)]


def weight(tree):
    return sum(e.weight for e in tree)


def undirected(e):
    return (min(e[0], e[1]), max(e[0], e[1]))


# 一棵「随手连」的生成树：片中第二个 beat 用来对比总权
NAIVE = [(0, 1, 20), (0, 4, 1), (4, 5, 15), (5, 3, 12), (5, 6, 10), (6, 2, 2)]

# 切分性质：U = {0, 4, 5}，跨界边 20、12、10，最轻的是 (5, 6) 10
CUT_U = {0, 4, 5}
# 反证用的「不含 (5, 6) 的生成树」：最小生成树把 (5, 6) 换成 (5, 3)，总权 40
PROOF_T = [(0, 4, 1), (4, 5, 15), (5, 3, 12), (6, 2, 2), (2, 1, 6), (1, 3, 4)]


def light_crossing(inside):
    return min(crossing(inside), key=lambda e: e[2])


# 最短路树 ≠ 最小生成树：讲义 6.3 的三点反例 A-B 2、B-C 2、A-C 3（A=0，B=1，C=2）
TRI = [(0, 1, 2), (1, 2, 2), (0, 2, 3)]


def spt(n, edges, src=0):
    """Dijkstra（朴素 O(n^2)）求最短路树：每个点连向它的前驱。"""
    adj = matrix(n, edges)
    d, pre, used = [INF] * n, [None] * n, [False] * n
    d[src] = 0
    for _ in range(n):
        u = _nearest(d, used)
        used[u] = True
        for v in range(n):
            if not used[v] and d[u] + adj[u][v] < d[v]:
                d[v], pre[v] = d[u] + adj[u][v], u
    return [(pre[v], v, adj[pre[v]][v]) for v in range(n) if pre[v] is not None], d


if __name__ == "__main__":
    t, _ = prim_trace()
    print("prim", t, weight(t))
    k, ev = kruskal_trace()
    print("kruskal", [(a, e) for a, e in ev], weight(k))
    print("spt", spt(3, TRI))
