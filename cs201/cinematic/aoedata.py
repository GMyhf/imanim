"""关键路径片的数据：讲义 4.7 节 6 个事件、8 个活动的 AOE 网，critical_path 原样插桩。

画面与旁白里的每个数字都从这里来；test_aoe.py 把讲义原版代码（CODE 原样 exec）、穷举全部源汇路径的最长路、
随机 DAG 与「把某活动拖延 x 看工期变不变」的定义式机动时间对撞。
"""
from __future__ import annotations

from collections import deque
from itertools import product

N = 6
# 讲义例：活动 <u, v> 耗时 w
EDGES = [(0, 1, 3), (0, 2, 2), (1, 3, 2), (1, 4, 3),
         (2, 3, 4), (2, 5, 1), (3, 5, 2), (4, 5, 1)]

CODE = '''from collections import deque
def critical_path(n, edges):
    # edges = [(u, v, w), ...]：活动 <u, v> 耗时 w
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v, w in edges:
        adj[u].append((v, w))
        indeg[v] += 1
    # 1. 拓扑序 + 最早发生时间 ve：取 max
    q = deque(i for i in range(n) if indeg[i] == 0)
    order, ve = [], [0] * n
    while q:
        u = q.popleft()
        order.append(u)
        for v, w in adj[u]:
            ve[v] = max(ve[v], ve[u] + w)
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) < n:
        return None                     # 有环：不是 AOE 网
    total = max(ve)
    # 2. 逆拓扑序 + 最迟发生时间 vl：取 min
    vl = [total] * n
    for u in reversed(order):
        for v, w in adj[u]:
            vl[u] = min(vl[u], vl[v] - w)
    # 3. 关键活动：e == l
    crit = [(u, v) for u, v, w in edges if ve[u] == vl[v] - w]
    return total, ve, vl, crit
'''

# 片中代码窗口：讲义原文的三段核心（删去建表与判环几行）
CODE_SHOWN = '''# 1. 拓扑序 + 最早发生时间 ve：取 max
while q:
    u = q.popleft()
    order.append(u)
    for v, w in adj[u]:
        ve[v] = max(ve[v], ve[u] + w)
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
# 2. 逆拓扑序 + 最迟发生时间 vl：取 min
vl = [total] * n
for u in reversed(order):
    for v, w in adj[u]:
        vl[u] = min(vl[u], vl[v] - w)
# 3. 关键活动：e == l
crit = [(u, v) for u, v, w in edges
        if ve[u] == vl[v] - w]'''


def critical_path_trace(n=N, edges=EDGES):
    """讲义 critical_path 原样插桩：记录正向（出队、ve 更新）与反向（vl 更新）两遍的每一步。

    fwd：[(u, [(v, w, 旧 ve[v], 新 ve[v]), ...]), ...]，按出队次序
    bwd：[(u, [(v, w, 旧 vl[u], 新 vl[u]), ...]), ...]，按逆拓扑序
    """
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v, w in edges:
        adj[u].append((v, w))
        indeg[v] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    order, ve = [], [0] * n
    fwd = []
    while q:
        u = q.popleft()
        order.append(u)
        ups = []
        for v, w in adj[u]:
            old = ve[v]
            ve[v] = max(ve[v], ve[u] + w)
            ups.append((v, w, old, ve[v]))
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
        fwd.append((u, ups))
    if len(order) < n:
        return None
    total = max(ve)
    vl = [total] * n
    bwd = []
    for u in reversed(order):
        ups = []
        for v, w in adj[u]:
            old = vl[u]
            vl[u] = min(vl[u], vl[v] - w)
            ups.append((v, w, old, vl[u]))
        bwd.append((u, ups))
    crit = [(u, v) for u, v, w in edges if ve[u] == vl[v] - w]
    return {"total": total, "ve": ve, "vl": vl, "crit": crit, "order": order, "fwd": fwd, "bwd": bwd}


def activities(tr, edges=EDGES):
    """每个活动的 e、l、机动时间 l - e。"""
    return [{"u": u, "v": v, "w": w, "e": tr["ve"][u], "l": tr["vl"][v] - w,
             "slack": tr["vl"][v] - w - tr["ve"][u]} for u, v, w in edges]


def paths(n=N, edges=EDGES, s=0, t=N - 1):
    """独立 oracle：枚举所有源→汇路径及长度。"""
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    out = []

    def go(u, p, L):
        if u == t:
            out.append((tuple(p), L))
            return
        for v, w in adj[u]:
            go(v, p + [v], L + w)
    go(s, [s], 0)
    return out


def duration(edges):
    """独立 oracle：工期 = 最长源→汇路径（按事件最早时间的定义逐点求 max，不用拓扑排序：反复松弛到不动）。"""
    n = 1 + max(max(u, v) for u, v, _ in edges)
    ve = [0] * n
    changed = True
    while changed:
        changed = False
        for u, v, w in edges:
            if ve[u] + w > ve[v]:
                ve[v] = ve[u] + w
                changed = True
    return max(ve)


def with_weight(edges, k, w):
    e = list(edges)
    u, v, _ = e[k]
    e[k] = (u, v, w)
    return e


TR = critical_path_trace()
TOTAL, VE, VL, CRIT = TR["total"], TR["ve"], TR["vl"], TR["crit"]     # 8；[0,3,2,6,6,8]；[0,4,2,6,7,8]
ACTS = activities(TR)
PATHS = paths()
# 拖延 <0,1> 一天：同一条路上 <1,3>、<1,4> 的机动时间也跟着用掉
DELAY01 = critical_path_trace(N, with_weight(EDGES, 0, 4))
# 缩短非关键活动 <1,4>（3 → 1）：工期不变
SHORT14 = critical_path_trace(N, with_weight(EDGES, 3, 1))
# 缩短关键活动 <2,3>（4 → 2）：工期只降到 7，别的路成了关键路径
SHORT23 = critical_path_trace(N, with_weight(EDGES, 4, 2))

if __name__ == "__main__":
    print(TOTAL, VE, VL, CRIT, TR["order"])
    for a in ACTS:
        print(a)
    print(PATHS)
    print("delay01", DELAY01["total"], [a["slack"] for a in activities(DELAY01, with_weight(EDGES, 0, 4))])
    print("short14", SHORT14["total"], SHORT14["crit"])
    print("short23", SHORT23["total"], SHORT23["crit"])
