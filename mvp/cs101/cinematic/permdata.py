"""全排列片的数据层：决策树、回溯事件序列、节点计数、子集树。

约定与课件一致（W08 P29–P35、讲义 3.3–3.4）：permutations 用 used 数组 + 共享 path 的显式回溯，
按下标升序枚举（结果为字典序）；子集先走「不选」分支，只在叶子收答案。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import factorial


@dataclass
class TNode:
    path: tuple
    id: int                         # 先序编号 = DFS 到达的顺序
    depth: int
    parent: int | None
    children: list[int] = field(default_factory=list)
    x: float = 0.0


def _layout(nodes: list[TNode]) -> None:
    leaf = 0

    def place(i):
        nonlocal leaf
        nd = nodes[i]
        if not nd.children:
            nd.x = float(leaf)
            leaf += 1
            return
        for c in nd.children:
            place(c)
        nd.x = sum(nodes[c].x for c in nd.children) / len(nd.children)
    place(0)


def perm_tree(a: list) -> list[TNode]:
    nodes: list[TNode] = []

    def go(path, used, depth, parent):
        nd = TNode(tuple(path), len(nodes), depth, parent)
        nodes.append(nd)
        if len(path) < len(a):
            for i in range(len(a)):
                if not used[i]:
                    used[i] = True
                    nd.children.append(go(path + [a[i]], used, depth + 1, nd.id))
                    used[i] = False
        return nd.id
    go([], [False] * len(a), 0, None)
    _layout(nodes)
    return nodes


def walk_events(a: list) -> list[tuple]:
    """回溯的事件序列：("down", 节点id, 选的下标) / ("collect", 叶子id) / ("up", 节点id, 撤销的下标)。

    与讲义 permutations() 一一对应：down = used[i]=True + path.append；up = path.pop + used[i]=False。
    """
    nodes = perm_tree(a)
    by_path = {nd.path: nd.id for nd in nodes}
    ev: list[tuple] = []
    path: list = []
    used = [False] * len(a)

    def dfs():
        if len(path) == len(a):
            ev.append(("collect", by_path[tuple(path)]))
            return
        for i in range(len(a)):
            if used[i]:
                continue
            used[i] = True
            path.append(a[i])
            ev.append(("down", by_path[tuple(path)], i))
            dfs()
            ev.append(("up", by_path[tuple(path)], i))
            path.pop()
            used[i] = False
    dfs()
    return ev


def level_counts(n: int) -> list[int]:
    """决策树第 k 层（根为第 0 层）的节点数 = n! / (n-k)!。"""
    return [factorial(n) // factorial(n - k) for k in range(n + 1)]


def node_total(n: int) -> int:
    return sum(level_counts(n))


def subset_tree(nums: list) -> list[TNode]:
    """选或不选的二叉决策树：左孩子 = 不选 nums[i]，右孩子 = 选。path 存当前 sol。"""
    nodes: list[TNode] = []

    def go(i, sol, parent):
        nd = TNode(tuple(sol), len(nodes), i, parent)
        nodes.append(nd)
        if i < len(nums):
            nd.children.append(go(i + 1, sol, nd.id))
            nd.children.append(go(i + 1, sol + [nums[i]], nd.id))
        return nd.id
    go(0, [], None)
    _layout(nodes)
    return nodes
