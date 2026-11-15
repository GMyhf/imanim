"""八皇后片的数据层：讲义 solve_queens 原样 + 插桩事件、搜索树、剪枝前后节点数。

约定与课件一致（W09 P5–P6、P11–P13，讲义 1.3–1.4 节）：逐行放置，三个集合 cols / diag(row-c) / anti(row+c)，
列号输出为 1 起，按字典序。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import factorial


def solve_queens(n=8):
    """讲义 1.4 节原样：返回全部解，每个解是长度 n 的列号元组（1-indexed），按字典序。"""
    res = []
    cols, diag, anti = set(), set(), set()
    path = []

    def dfs(row):
        if row == n:
            res.append(tuple(path))
            return
        for c in range(n):
            if c in cols or (row - c) in diag or (row + c) in anti:
                continue                       # 可行性剪枝
            cols.add(c); diag.add(row - c); anti.add(row + c)
            path.append(c + 1)
            dfs(row + 1)
            path.pop()
            cols.remove(c); diag.remove(row - c); anti.remove(row + c)

    dfs(0)
    return res


@dataclass
class Call:
    id: int
    row: int                      # 这次调用要放第几行（根为 0）
    col: int | None               # 进入这次调用前，上一行放在哪一列（根为 None）
    parent: int | None
    children: list[int] = field(default_factory=list)
    conflicts: list[int] = field(default_factory=list)   # 本层循环里因冲突跳过的列
    solution: bool = False
    x: float = 0.0


def trace(n=4):
    """插桩版：返回 (解, 事件, 调用树)。

    事件：("place", row, c) / ("conflict", row, c, 原因) / ("remove", row, c) / ("solution", path)；
    原因是 "col" / "diag" / "anti" 中第一个命中的（与讲义 if 的短路顺序一致）。
    """
    res, ev, calls = [], [], []
    cols, diag, anti = set(), set(), set()
    path = []

    def dfs(row, col, parent):
        me = Call(len(calls), row, col, parent)
        calls.append(me)
        if parent is not None:
            calls[parent].children.append(me.id)
        if row == n:
            res.append(tuple(path))
            me.solution = True
            ev.append(("solution", tuple(path)))
            return
        for c in range(n):
            why = "col" if c in cols else "diag" if (row - c) in diag else "anti" if (row + c) in anti else None
            if why:
                me.conflicts.append(c)
                ev.append(("conflict", row, c, why))
                continue
            cols.add(c); diag.add(row - c); anti.add(row + c)
            path.append(c + 1)
            ev.append(("place", row, c))
            dfs(row + 1, c, me.id)
            path.pop()
            cols.remove(c); diag.remove(row - c); anti.remove(row + c)
            ev.append(("remove", row, c))

    dfs(0, None, None)
    leaf = 0

    def place(i):
        nonlocal leaf
        nd = calls[i]
        if not nd.children:
            nd.x = float(leaf)
            leaf += 1
            return
        for ch in nd.children:
            place(ch)
        nd.x = sum(calls[ch].x for ch in nd.children) / len(nd.children)
    place(0)
    return res, ev, calls


def naive_nodes(n):
    """每行随便放、走到底才检查：决策树节点数 1 + n + n² + … + nⁿ。"""
    return sum(n ** k for k in range(n + 1))


def perm_nodes(n):
    """只保证不同列（全排列的决策树）：Σ n!/(n-k)!。"""
    return sum(factorial(n) // factorial(n - k) for k in range(n + 1))


def pruned_nodes(n):
    """三个集合剪枝后实际的递归调用次数。"""
    return len(trace(n)[2])


def attacked(n, r, c):
    """(r, c) 上的皇后能攻击到的格子（不含自身）。"""
    return [(i, j) for i in range(n) for j in range(n)
            if (i, j) != (r, c) and (i == r or j == c or i - j == r - c or i + j == r + c)]
