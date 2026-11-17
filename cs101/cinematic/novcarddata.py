"""牌堆魔术精讲片（T4 M31532）的数据层：画面和旁白里的每个数字都从这里来。

讲义原样代码复用 novdata.solve_t4 / cards_reverse_trace / cards_forward（不改 novdata）。
这里补写的插桩：正着表演的每一轮、位置队列的正着模拟、两步撤销写反的错误写法、
list.insert(0, x) 的元素搬动计数。test_novcard.py 用独立实现对撞。
"""
from __future__ import annotations

from collections import deque

import novdata as N

SAMPLE1, SAMPLE2 = 4, 5                          # 题面两个样例的 n
N_MAX = 2 * 10 ** 5


def forward_rounds(order: list[int]):
    """按题意正着表演。每轮记：移到底的牌、移完后的牌堆、翻开的牌、翻完后的牌堆（从上到下）。"""
    dq, rounds = deque(order), []
    while dq:
        moved = dq[0]
        dq.append(dq.popleft())
        after_move = list(dq)
        shown = dq.popleft()
        rounds.append({"moved": moved, "after_move": after_move, "shown": shown, "after": list(dq)})
    return rounds


def answer(n: int) -> list[int]:
    """讲义 Python 代码原样跑出的初始牌堆。"""
    return list(map(int, N.run_io(N.solve_t4, f"{n}\n").split()))


def position_trace(n: int):
    """另一种思路：0..n-1 号位置排成队列，先把队首移到队尾，再弹出队首，第 k 次弹出的位置填牌 k。
    返回 (每轮 {"k", "queue": 移动前的队列, "rotated": 移动后的队列, "pos": 弹出的位置}, 填好的牌堆)。"""
    q, deck, steps = deque(range(n)), [0] * n, []
    for k in range(1, n + 1):
        before = list(q)
        q.append(q.popleft())
        rotated = list(q)
        p = q.popleft()
        deck[p] = k
        steps.append({"k": k, "queue": before, "rotated": rotated, "pos": p})
    return steps, deck


def swapped_naive(n: int) -> list[int]:
    """典型错误：两步撤销写反（先把底牌移回牌顶，再放回牌 i），不加判空。第一轮牌堆空，pop 抛 IndexError。"""
    dq = deque()
    for i in range(n, 0, -1):
        dq.appendleft(dq.pop())
        dq.appendleft(i)
    return list(dq)


def swapped_guarded(n: int) -> list[int]:
    """同上，加了判空：能跑完，但结果是错的。"""
    dq = deque()
    for i in range(n, 0, -1):
        if dq:
            dq.appendleft(dq.pop())
        dq.appendleft(i)
    return list(dq)


def list_insert_moves(n: int):
    """把 appendleft 换成 list.insert(0, x)：每次插到开头要把已有元素整体后挪一位。
    返回 (结果, 被挪动的元素总数)。真跑一遍，只适合小 n。"""
    lst, moves = [], 0
    for i in range(n, 0, -1):
        moves += len(lst)
        lst.insert(0, i)
        x = lst.pop()
        moves += len(lst)
        lst.insert(0, x)
    return lst, moves


def list_moves_count(n: int) -> int:
    """list_insert_moves 的搬动数，只累加不真插（n = 2×10⁵ 用）。"""
    return sum(2 * size for size in range(n))


def deque_ops(n: int) -> int:
    """讲义写法每轮三次两端操作：appendleft、pop、appendleft。"""
    return 3 * n


LIST_MOVES_BIG = list_moves_count(N_MAX)         # 39 999 800 000 ≈ 四百亿
DEQUE_OPS_BIG = deque_ops(N_MAX)                 # 600 000

# 讲义 Python 代码（片中逐行对照，原样，无空行）
CODE = (
    "from collections import deque\n"
    "n = int(input())\n"
    "dq = deque()\n"
    "for i in range(n, 0, -1):  # 倒着做\n"
    "    dq.appendleft(i)  # 撤销\"翻开\"：牌 i 放回牌顶\n"
    "    dq.appendleft(dq.pop())  # 撤销\"顶移到底\"\n"
    "print(*dq)"
)
