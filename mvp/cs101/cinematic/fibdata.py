"""斐波那契片的数据层：调用树、记忆化剪枝、计数。

画面与旁白里出现的每个数字（调用次数、重复次数、表值）都从这里算出，
test_fib.py 用独立的方式（闭式计数、迭代）对撞，不在场景里手写常数。
约定与课件一致（W08 P23）：F(1) = F(2) = 1，n <= 2 为基例。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    n: int
    id: int                      # DFS 先序编号 = 真实调用顺序
    depth: int
    parent: int | None
    children: list[int] = field(default_factory=list)
    x: float = 0.0               # 叶序布局坐标（单位：叶间距）
    memo_hit: bool = False       # 记忆化后此调用直接查表返回
    pruned: bool = False         # 记忆化后此调用根本不会发生


def call_tree(n: int) -> list[Node]:
    """朴素递归 fib(n) 的调用树，按先序（真实调用顺序）编号。"""
    nodes: list[Node] = []

    def go(k: int, depth: int, parent: int | None) -> int:
        node = Node(k, len(nodes), depth, parent)
        nodes.append(node)
        if k > 2:
            for c in (k - 1, k - 2):
                node.children.append(go(c, depth + 1, node.id))
        return node.id

    go(n, 0, None)
    leaf = 0
    def place(i: int) -> None:
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
    return nodes


def apply_memo(nodes: list[Node]) -> list[Node]:
    """按 lru_cache 语义标记：参数第一次出现的调用真算；之后同参调用查表返回，其子树不发生。"""
    seen: set[int] = set()

    def go(i: int, dead: bool) -> None:
        nd = nodes[i]
        if dead:
            nd.pruned = True
        elif nd.n in seen:
            nd.memo_hit = True
        else:
            # 先序进入时还没算完，但 DFS 先走左孩子，左边的同参调用必然先完成
            pass
        for c in nd.children:
            go(c, dead or nd.memo_hit)
        if not dead and not nd.memo_hit:
            seen.add(nd.n)

    go(0, False)
    return nodes


def fib(n: int) -> int:
    a, b = 1, 1
    for _ in range(n - 2):
        a, b = b, a + b
    return 1 if n <= 2 else b


def naive_calls(n: int) -> int:
    """朴素递归的调用次数（递推，不建树）。"""
    c = {1: 1, 2: 1}
    for k in range(3, n + 1):
        c[k] = c[k - 1] + c[k - 2] + 1
    return c[n]


def repeat_counts(nodes: list[Node]) -> dict[int, int]:
    out: dict[int, int] = {}
    for nd in nodes:
        out[nd.n] = out.get(nd.n, 0) + 1
    return out


def facts(n: int = 6, big: int = 40, table: int = 10) -> dict:
    nodes = apply_memo(call_tree(n))
    return {
        "n": n,
        "naive_calls": len(nodes),
        "memo_calls": sum(1 for x in nodes if not x.pruned),
        "repeats": repeat_counts(nodes),
        "big": big,
        "big_calls": naive_calls(big),
        "table": [fib(k) for k in range(1, table + 1)],
    }
