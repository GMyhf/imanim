"""强连通分量片的数据：讲义 4.6 节 8 个顶点的例图、Kosaraju 两遍 DFS 的逐事件轨迹、发现/结束时间与边的分类。

画面与旁白里的每个数字都从这里来；test_scc.py 用讲义原版代码（KOSARAJU_CODE、TARJAN_CODE、COWS_CODE 原样 exec）、
传递闭包暴力法与随机图对撞。
时间戳口径同 2026spring 图讲义 DFSGraph：进入一个顶点 time+1 记发现时间，离开时 time+1 记结束时间，从 1 起。
"""
from __future__ import annotations

N = 8
# 讲义例图：0→1 1→2 1→4 2→3 2→5 3→0 3→6 4→5 5→4 6→7 7→5 7→6
ADJ = [[1], [2, 4], [3, 5], [0, 6],
       [5], [4], [7], [5, 6]]
EDGES = [(u, v) for u in range(N) for v in ADJ[u]]

# 讲义 4.6 节 Kosaraju 原文（片中代码窗口展示的就是这一段的核心）
KOSARAJU_CODE = '''def kosaraju(n, adj):
    visited = [False] * n
    stack = []
    def dfs1(u):                        # 第一次 DFS：在 G 上
        visited[u] = True
        for v in adj[u]:
            if not visited[v]:
                dfs1(v)
        stack.append(u)                 # 结束时压栈
    for i in range(n):
        if not visited[i]:
            dfs1(i)
    radj = [[] for _ in range(n)]       # 转置图 G^T
    for u in range(n):
        for v in adj[u]:
            radj[v].append(u)
    def dfs2(u, comp):                  # 第二次 DFS：在 G^T 上
        visited[u] = True
        comp.append(u)
        for v in radj[u]:
            if not visited[v]:
                dfs2(v, comp)
    visited, sccs = [False] * n, []
    while stack:                        # 按结束时间递减取起点
        u = stack.pop()
        if not visited[u]:
            sccs.append([])
            dfs2(u, sccs[-1])
    return sccs
'''

# 片中代码窗口：只放两遍 DFS 的骨架（讲义原文删去建转置图的四行，那一步在画面上单独演示）
CODE_SHOWN = '''def dfs1(u):                    # 第一次：在 G 上
    visited[u] = True
    for v in adj[u]:
        if not visited[v]:
            dfs1(v)
    stack.append(u)             # 结束时压栈
def dfs2(u, comp):              # 第二次：在 G 的转置上
    visited[u] = True
    comp.append(u)
    for v in radj[u]:
        if not visited[v]:
            dfs2(v, comp)
while stack:                    # 结束最晚的先当起点
    u = stack.pop()
    if not visited[u]:
        sccs.append([])
        dfs2(u, sccs[-1])'''

TARJAN_CODE = '''def tarjan(n, adj):
    dfn, low = [-1] * n, [0] * n        # dfn = -1 表示未访问
    on_stk = [False] * n
    stk, sccs = [], []
    t = 0
    def dfs(u):
        nonlocal t
        dfn[u] = low[u] = t
        t += 1
        stk.append(u)                   # 访问即入栈
        on_stk[u] = True
        for v in adj[u]:
            if dfn[v] == -1:            # 树边：先递归
                dfs(v)
                low[u] = min(low[u], low[v])
            elif on_stk[v]:             # 指回栈中的点
                low[u] = min(low[u], dfn[v])
        if low[u] == dfn[u]:            # u 是 SCC 的根
            comp = []
            while True:
                v = stk.pop()
                on_stk[v] = False
                comp.append(v)
                if v == u: break
            sccs.append(comp)
    for i in range(n):
        if dfn[i] == -1:
            dfs(i)
    return sccs
'''

# 讲义 OJ02186 Popular Cows 原文（显式栈 Kosaraju）
COWS_CODE = '''import sys

def main():
    data = sys.stdin.buffer.read().split()
    n, m = int(data[0]), int(data[1])
    adj = [[] for _ in range(n + 1)]
    radj = [[] for _ in range(n + 1)]
    for i in range(m):
        a, b = int(data[2 + 2 * i]), int(data[3 + 2 * i])
        adj[a].append(b)
        radj[b].append(a)

    # 第一次 DFS（显式栈）：记结束顺序
    visited = [False] * (n + 1)
    order = []
    for s in range(1, n + 1):
        if visited[s]:
            continue
        visited[s] = True
        stack = [(s, 0)]
        while stack:
            u, i = stack[-1]
            if i < len(adj[u]):
                stack[-1] = (u, i + 1)
                v = adj[u][i]
                if not visited[v]:
                    visited[v] = True
                    stack.append((v, 0))
            else:
                stack.pop()
                order.append(u)          # 结束时记下

    # 第二次 DFS：在转置图上按结束时间递减取起点，comp[v] 是 SCC 编号
    comp = [-1] * (n + 1)
    count = 0
    for s in reversed(order):
        if comp[s] != -1:
            continue
        comp[s] = count
        stack = [s]
        while stack:
            u = stack.pop()
            for v in radj[u]:
                if comp[v] == -1:
                    comp[v] = count
                    stack.append(v)
        count += 1

    out_degree = [0] * count
    size = [0] * count
    for u in range(1, n + 1):
        size[comp[u]] += 1
        for v in adj[u]:
            if comp[u] != comp[v]:
                out_degree[comp[u]] += 1
    sinks = [c for c in range(count) if out_degree[c] == 0]
    print(size[sinks[0]] if len(sinks) == 1 else 0)

main()
'''
COWS_SAMPLE = "3 3\n1 2\n2 1\n2 3\n"


def transpose(adj=ADJ):
    """讲义写法：按 u 从小到大、adj[u] 次序把 u→v 记成 v→u。"""
    n = len(adj)
    radj = [[] for _ in range(n)]
    for u in range(n):
        for v in adj[u]:
            radj[v].append(u)
    return radj


def dfs1_trace(adj=ADJ):
    """第一次 DFS（讲义 dfs1 原样，外层按编号起点），插桩记录事件与时间戳。

    events：("enter", u, t) / ("edge", u, v, kind) / ("finish", u, t)
    kind：tree 树边（白点）、back 回边（灰点，正在递归栈上）、forward 前向边、cross 横叉边（黑点）。
    """
    n = len(adj)
    color = ["white"] * n
    d, f = [0] * n, [0] * n
    stack, events = [], []
    time = 0

    def dfs1(u):
        nonlocal time
        color[u] = "gray"
        time += 1
        d[u] = time
        events.append(("enter", u, time))
        for v in adj[u]:
            if color[v] == "white":
                events.append(("edge", u, v, "tree"))
                dfs1(v)
            elif color[v] == "gray":
                events.append(("edge", u, v, "back"))
            else:
                events.append(("edge", u, v, "forward" if d[v] > d[u] else "cross"))
        color[u] = "black"
        time += 1
        f[u] = time
        stack.append(u)
        events.append(("finish", u, time))

    for i in range(n):
        if color[i] == "white":
            dfs1(i)
    return {"events": events, "d": d, "f": f, "stack": stack}


def dfs2_trace(adj=ADJ, stack=None):
    """第二次 DFS（讲义 dfs2 原样）：按 stack 从顶到底取起点，在转置图上走；记录每块的访问次序与考察的弧。"""
    radj = transpose(adj)
    stack = list(dfs1_trace(adj)["stack"] if stack is None else stack)
    n = len(adj)
    visited = [False] * n
    rounds = []
    while stack:
        u = stack.pop()
        if visited[u]:
            rounds.append({"start": u, "skip": True})
            continue
        comp, looks = [], []

        def dfs2(x):
            visited[x] = True
            comp.append(x)
            for y in radj[x]:
                looks.append((x, y, visited[y]))
                if not visited[y]:
                    dfs2(y)
        dfs2(u)
        rounds.append({"start": u, "skip": False, "comp": comp, "looks": looks})
    return rounds


def kosaraju(adj=ADJ):
    return [r["comp"] for r in dfs2_trace(adj) if not r["skip"]]


def comp_of(sccs, n=N):
    c = [-1] * n
    for k, comp in enumerate(sccs):
        for v in comp:
            c[v] = k
    return c


def condensed(adj=ADJ, sccs=None):
    """缩点图的弧（分量编号按 Kosaraju 产出次序），去重。"""
    sccs = kosaraju(adj) if sccs is None else sccs
    c = comp_of(sccs, len(adj))
    return sorted({(c[u], c[v]) for u in range(len(adj)) for v in adj[u] if c[u] != c[v]})


def reach(adj, s):
    seen, st = {s}, [s]
    while st:
        u = st.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                st.append(v)
    return seen


def sccs_bruteforce(adj):
    """独立 oracle：u、v 互相可达 ⇔ 同一分量（逐点求可达集）。"""
    n = len(adj)
    R = [reach(adj, s) for s in range(n)]
    seen, out = set(), []
    for u in range(n):
        if u in seen:
            continue
        comp = sorted(v for v in range(n) if v in R[u] and u in R[v])
        seen.update(comp)
        out.append(comp)
    return out


def popular_cows(n, pairs):
    """独立 oracle：被其他所有奶牛「可达」的奶牛数（逐点求可达集，O(n·(n+m))）。"""
    adj = [[] for _ in range(n + 1)]
    for a, b in pairs:
        adj[a].append(b)
    R = [None] + [reach(adj, s) for s in range(1, n + 1)]
    return sum(all(v in R[u] for u in range(1, n + 1)) for v in range(1, n + 1))


TR = dfs1_trace()
D_TIME, F_TIME, STACK = TR["d"], TR["f"], TR["stack"]
KIND = {(e[1], e[2]): e[3] for e in TR["events"] if e[0] == "edge"}
ROUNDS = dfs2_trace()
SCCS = kosaraju()                       # [[0, 3, 2, 1], [6, 7], [5, 4]]
COMP = comp_of(SCCS)
CEDGES = condensed()                    # 缩点图：块0→块1、块0→块2、块1→块2

if __name__ == "__main__":
    print("d =", D_TIME)
    print("f =", F_TIME)
    print("stack =", STACK)
    print("kinds =", KIND)
    print("sccs =", SCCS, "condensed =", CEDGES)
    print("max f per comp =", [max(F_TIME[v] for v in c) for c in SCCS])
