"""拓扑排序片的数据层：讲义 topological_sort（相邻矩阵 + 队列，Kahn）与 dfs_topo_sort 原样插桩。

图是讲义图 7.17 的课程先修关系（c0…c8，弧 <ci,cj> 表示 ci 是 cj 的先修课）；同一步里多个顶点入度归 0
时按列号从小到大入队（矩阵扫一行的次序），与讲义手算表一致。画面和旁白里的每个数字都从这里来。
"""
from __future__ import annotations

N = 9
NAMES = ["高等数学", "程序设计", "离散数学", "数据结构", "算法语言", "编译原理", "操作系统", "普通物理", "计算机原理"]
EDGES = [(0, 2), (0, 7), (1, 2), (1, 3), (1, 4), (2, 3), (3, 5), (3, 6), (4, 5), (7, 8), (8, 6)]
CYCLE_EDGE = (6, 0)          # 讲义：「若再加一条 <c6,c0>，c0 入度为 1，整条链都卡住」
INF = float("inf")


def matrix(edges=EDGES, n=N):
    m = [[INF] * n for _ in range(n)]
    for i in range(n):
        m[i][i] = 0
    for u, v in edges:
        m[u][v] = 1
    return m


def indegrees(edges=EDGES, n=N):
    d = [0] * n
    for _, v in edges:
        d[v] += 1
    return d


def kahn_trace(edges=EDGES, n=N):
    """讲义 modern.py topological_sort 原样，插桩记事件。

    事件：("init", indegree 列表, 初始队列) / ("pop", u) / ("dec", u, v, 新入度) / ("push", v)。
    返回 (result 或 None, 事件, 结束时的入度表)。
    """
    adjacency = matrix(edges, n)
    infinity = INF
    indegree = [0] * n
    for source in range(n):
        for target in range(n):
            if source != target and adjacency[source][target] < infinity:
                indegree[target] += 1
    queue = [vertex for vertex in range(n) if indegree[vertex] == 0]
    ev = [("init", list(indegree), list(queue))]
    head = 0
    result: list[int] = []
    while head < len(queue):
        source = queue[head]
        head += 1
        result.append(source)
        ev.append(("pop", source))
        for target in range(n):
            if source != target and adjacency[source][target] < infinity:
                indegree[target] -= 1
                ev.append(("dec", source, target, indegree[target]))
                if indegree[target] == 0:
                    queue.append(target)
                    ev.append(("push", target))
    return (result if len(result) == n else None), ev, indegree


def kahn_steps(edges=EDGES, n=N):
    """按出队分步：[(出队点, [(v, 旧入度, 新入度)], [新入队], 出队后的队列)]，对应讲义手算表的每一行。"""
    _, ev, _ = kahn_trace(edges, n)
    queue = list(ev[0][2])
    steps, cur = [], None
    for e in ev[1:]:
        if e[0] == "pop":
            queue.pop(0)
            cur = [e[1], [], [], None]
            steps.append(cur)
        elif e[0] == "dec":
            cur[1].append((e[2], e[3] + 1, e[3]))
        else:
            cur[2].append(e[1])
            queue.append(e[1])
        if cur is not None:
            cur[3] = list(queue)
    return [tuple(s) for s in steps]


def graph_dict(edges=EDGES, n=N):
    g = {v: [] for v in range(n)}
    for u, v in sorted(edges):
        g[u].append(v)
    return g


def dfs_topo_trace(graph=None):
    """讲义 dfs_topo_sort 原样，插桩记事件：("enter", u) / ("finish", u) / ("gray", u, v) 撞上灰点。

    返回 (拓扑序 或 None, 结束顺序, 事件)。
    """
    graph = graph_dict() if graph is None else graph
    state = {v: 0 for v in graph}
    finish_order = []
    ev = []

    def dfs(u):
        state[u] = 1
        ev.append(("enter", u))
        for v in graph[u]:
            if state[v] == 1:
                ev.append(("gray", u, v))
                return False
            if state[v] == 0 and not dfs(v):
                return False
        state[u] = 2
        finish_order.append(u)
        ev.append(("finish", u))
        return True

    for u in graph:
        if state[u] == 0 and not dfs(u):
            return None, finish_order, ev
    return finish_order[::-1], finish_order, ev


def stuck_after_cycle():
    """加上 <c6,c0> 之后：输出了哪些点、卡住的点及其剩余入度。"""
    res, ev, indeg = kahn_trace(EDGES + [CYCLE_EDGE])
    out = [e[1] for e in ev if e[0] == "pop"]
    stuck = {v: indeg[v] for v in range(N) if v not in out}
    return res, out, stuck


def cycle_edges():
    """加边后图中位于某个有向环上的弧（弧 u→v 在环上 ⇔ v 能走回 u）。"""
    edges = EDGES + [CYCLE_EDGE]
    g = graph_dict(edges)

    def reach(a, b):
        seen, st = {a}, [a]
        while st:
            x = st.pop()
            if x == b:
                return True
            for y in g[x]:
                if y not in seen:
                    seen.add(y)
                    st.append(y)
        return False
    return [(u, v) for u, v in edges if reach(v, u)]


def layers(edges=EDGES, n=N):
    """最长路分层（画图排版用）：没有前驱的在第 0 层。"""
    lv = [0] * n
    order, _, _ = kahn_trace(edges, n)
    for u in order:
        for a, b in edges:
            if a == u:
                lv[b] = max(lv[b], lv[u] + 1)
    return lv


# 画面上展示的代码：讲义 sy403「先导课程」的写法，把最小堆换回普通队列（即讲义 Kahn 算法的邻接表版）。
# test_topo.py 会原样 exec 这段代码，与 kahn_trace 对撞。
KAHN_CODE = """def topo_sort(n, edges):
    graph = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v in edges:
        graph[u].append(v)
        indeg[v] += 1
    queue = deque(v for v in range(n) if indeg[v] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return order if len(order) == n else None
"""
