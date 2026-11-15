"""汉诺塔片的数据层：移动序列、调用树（中序编号）、步数与「64 片金片」换算。

约定与课件一致（W08 P26–P28）：hanoi(n, src, aux, dst)，n == 0 为基例；
调用树省略 n == 0 的空调用，每个节点恰好做一次移动（三步里的第二步）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

SECONDS_PER_YEAR = 365 * 24 * 3600


@dataclass
class Call:
    n: int
    src: str
    aux: str
    dst: str
    depth: int
    id: int                       # 先序编号 = 调用发生的顺序
    inorder: int = 0              # 中序编号 = 这次调用的那一步移动是第几步（1 起）
    children: list[int] = field(default_factory=list)


def moves(n: int, src="A", aux="B", dst="C") -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []

    def go(k, s, a, d):
        if k == 0:
            return
        go(k - 1, s, d, a)
        out.append((k, s, d))
        go(k - 1, a, s, d)
    go(n, src, aux, dst)
    return out


def call_tree(n: int, src="A", aux="B", dst="C") -> list[Call]:
    calls: list[Call] = []
    counter = 0

    def go(k, s, a, d, depth) -> int | None:
        nonlocal counter
        if k == 0:
            return None
        c = Call(k, s, a, d, depth, len(calls))
        calls.append(c)
        left = go(k - 1, s, d, a, depth + 1)
        counter += 1
        c.inorder = counter
        right = go(k - 1, a, s, d, depth + 1)
        c.children = [x for x in (left, right) if x is not None]
        return c.id
    go(n, src, aux, dst, 0)
    return calls


def count(n: int) -> int:
    """递推 T(n) = 2T(n-1) + 1，T(0) = 0（不用闭式，留给测试对撞）。"""
    t = 0
    for _ in range(n):
        t = 2 * t + 1
    return t


def legend_years(n: int = 64) -> float:
    """每秒移动一次，移完 n 片需要多少年。"""
    return count(n) / SECONDS_PER_YEAR
