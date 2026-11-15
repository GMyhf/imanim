"""并查集片的数据层：讲义 DSU 原样实现 + 各段演示用的父指针快照。

约定与课件一致（W09 P16–P30、讲义第 2 节）：DSU 用迭代两趟 find（路径压缩）+ 按大小合并，
规模相等时把 y 的根挂到 x 的根下；期中手算题用「根存负的集合大小、等大取小编号为根」。
"""
from __future__ import annotations


class DSU:
    """讲义 2.3 节标准实现（原样）。"""

    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n
        self.count = n

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.size[rx] < self.size[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        self.size[rx] += self.size[ry]
        self.count -= 1
        return True


class NaiveDSU:
    """讲义 2.2 节朴素实现（原样）。"""

    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry


def path_to_root(parent, x):
    path = [x]
    while parent[path[-1]] != path[-1]:
        path.append(parent[path[-1]])
    return path


def depth(parent, x):
    return len(path_to_root(parent, x)) - 1


# ---- 父指针表示：四次合并后的森林（find 只落在深度 ≤ 1 的点上，压缩不改变形状）
FOREST_N = 8
FOREST_UNIONS = [(0, 1), (2, 3), (0, 2), (4, 5)]


def forest_snapshots():
    d = DSU(FOREST_N)
    snaps = [d.parent[:]]
    for a, b in FOREST_UNIONS:
        d.union(a, b)
        snaps.append(d.parent[:])
    return snaps


# ---- 退化：同一串 union(i, i+1)，朴素合并成链，按大小合并成一层
CHAIN_N = 8


def chain_vs_weighted():
    naive, good = NaiveDSU(CHAIN_N), DSU(CHAIN_N)
    na, gd = [naive.parent[:]], [good.parent[:]]
    for i in range(CHAIN_N - 1):
        naive.union(i, i + 1)
        good.union(i, i + 1)
        na.append(naive.parent[:])
        gd.append(good.parent[:])
    return na, gd


# ---- 路径压缩（讲义图 6.13 的形状）：对 7 做一次 find
COMPRESS_PARENT = {1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 5, 8: 5, 9: 7, 10: 7}


def compress_demo():
    keys = sorted(COMPRESS_PARENT)
    idx = {k: i for i, k in enumerate(keys)}
    d = DSU(len(keys))
    d.parent = [idx[COMPRESS_PARENT[k]] for k in keys]
    before = {k: keys[d.parent[idx[k]]] for k in keys}
    path = [keys[i] for i in path_to_root(d.parent, idx[7])]
    root = keys[d.find(idx[7])]
    after = {k: keys[d.parent[idx[k]]] for k in keys}
    return before, path, root, after


# ---- 期中手算题：根存 -(集合大小)；Find 完全路径压缩；Union 先两次 Find，小挂大，等大取小编号
EXAM_P0 = [-4, 0, 1, 0, -3, 4, 5, -2, 7, -1]


def exam_find(p, x):
    root = x
    while p[root] >= 0:
        root = p[root]
    while p[x] >= 0 and p[x] != root:
        p[x], x = root, p[x]
    return root


def exam_union(p, a, b):
    ra, rb = exam_find(p, a), exam_find(p, b)
    if ra == rb:
        return
    if p[ra] < p[rb] or (p[ra] == p[rb] and ra < rb):
        big, small = ra, rb
    else:
        big, small = rb, ra
    p[big] += p[small]
    p[small] = big


def exam_steps():
    """返回各步之后的数组：初始、find(2)、find(6)、合并、再 find(6)。"""
    p = EXAM_P0[:]
    steps = [("init", p[:])]
    exam_find(p, 2)
    steps.append(("find2", p[:]))
    exam_find(p, 6)
    steps.append(("find6", p[:]))
    ra, rb = exam_find(p, 2), exam_find(p, 6)       # 已压缩过，这两次 find 不再改动
    if p[ra] < p[rb] or (p[ra] == p[rb] and ra < rb):
        big, small = ra, rb
    else:
        big, small = rb, ra
    p[big] += p[small]
    p[small] = big
    steps.append(("link", p[:]))
    exam_find(p, 6)
    steps.append(("find6b", p[:]))
    return steps


def exam_as_parent(p):
    """把「根存负数」的数组转成父指针（根指向自己），给画森林用。"""
    return [i if v < 0 else v for i, v in enumerate(p)]


# ---- 应用：宗教信仰（数连通块）与判环
RELIGION = (10, [(0, 1), (1, 2), (3, 4)])
CYCLE_EDGES = [(0, 1), (1, 2), (2, 0)]


def religion_counts():
    n, pairs = RELIGION
    d = DSU(n)
    out = [d.count]
    for a, b in pairs:
        d.union(a, b)
        out.append(d.count)
    return out


def cycle_returns():
    d = DSU(3)
    return [d.union(a, b) for a, b in CYCLE_EDGES]
