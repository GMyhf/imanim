"""0/1 背包片的数据层：二维 dp 表、倒推选了哪些物品、一维滚动正序/倒序的逐格记录、完全背包。

约定与课件一致（W11 P4–P8、讲义 1.1–1.3）：例题 23421 小偷背包 weights=[1,4,3]、values=[1500,3000,2000]、
容量 4；knapsack_2d / knapsack_1d / unbounded_knapsack 照抄讲义，只加插桩。
"""
from __future__ import annotations

WEIGHTS = [1, 4, 3]
VALUES = [1500, 3000, 2000]
CAP = 4


def knapsack_2d(weights=WEIGHTS, values=VALUES, cap=CAP):
    """讲义二维写法，返回整张 dp 表。"""
    n = len(weights)
    dp = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w, v = weights[i - 1], values[i - 1]
        for c in range(cap + 1):
            dp[i][c] = dp[i - 1][c]
            if c >= w:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w] + v)
    return dp


def fill_log(weights=WEIGHTS, values=VALUES, cap=CAP):
    """逐格记录：(i, c, 不拿的值, 拿的值或 None, 结果)。"""
    dp = knapsack_2d(weights, values, cap)
    out = []
    for i in range(1, len(weights) + 1):
        w, v = weights[i - 1], values[i - 1]
        for c in range(cap + 1):
            skip = dp[i - 1][c]
            take = dp[i - 1][c - w] + v if c >= w else None
            out.append((i, c, skip, take, dp[i][c]))
    return out


def backtrack(weights=WEIGHTS, values=VALUES, cap=CAP):
    """从 dp[n][cap] 倒推：与上一行同值就是没拿，否则拿了第 i 个。返回 [(i, c, 拿没拿)]。"""
    dp = knapsack_2d(weights, values, cap)
    c, steps = cap, []
    for i in range(len(weights), 0, -1):
        took = dp[i][c] != dp[i - 1][c]
        steps.append((i, c, took))
        if took:
            c -= weights[i - 1]
    return steps


def chosen(weights=WEIGHTS, values=VALUES, cap=CAP):
    return sorted(i for i, _, took in backtrack(weights, values, cap) if took)


def knapsack_1d(weights=WEIGHTS, values=VALUES, cap=CAP):
    dp = [0] * (cap + 1)
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[cap]


def unbounded_knapsack(weights=WEIGHTS, values=VALUES, cap=CAP):
    dp = [0] * (cap + 1)
    for w, v in zip(weights, values):
        for c in range(w, cap + 1):
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[cap]


def one_pass(w, v, dp, forward: bool):
    """对一维数组做一轮（一件物品），返回 (新数组, 逐格记录 [(c, 旧 dp[c], 读到的 dp[c-w], 新值)])。"""
    dp = dp[:]
    cap = len(dp) - 1
    order = range(w, cap + 1) if forward else range(cap, w - 1, -1)
    log = []
    for c in order:
        old, src = dp[c], dp[c - w]
        dp[c] = max(dp[c], dp[c - w] + v)
        log.append((c, old, src, dp[c]))
    return dp, log


def caiyao(T, herbs):
    dp = [0] * (T + 1)
    for t, v in herbs:
        for c in range(T, t - 1, -1):
            dp[c] = max(dp[c], dp[c - t] + v)
    return dp[T]
