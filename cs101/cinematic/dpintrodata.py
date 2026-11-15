"""动态规划入门片的数据层：硬币反例、奇数路径和三角形（朴素 DP / 补一维 / 暴力）、随机对拍。

约定与课件一致（W10 P13–P24、讲义 2.1–2.4）：naive_odd / fixed_odd / brute_odd / TRI 照抄讲义；
table 版本与讲义函数逐行同逻辑，只是把整张 dp 表交出来给画面用（test_dpintro 对撞两者结果）。
"""
from __future__ import annotations

import itertools
import random

NEG = float('-inf')

TRI = [[6],
       [7, 9],
       [0, 3, 7],
       [7, 4, 2, 0]]


# ---------------------------------------------------------------- 讲义原样
def naive_odd(tri):
    """朴素状态：dp[i][j] = 到 (i, j) 的最大路径和，最后在底行里挑奇数。"""
    dp = [tri[0][:]]
    for i in range(1, len(tri)):
        dp.append([max(dp[i - 1][k] for k in (j - 1, j) if 0 <= k <= i - 1)
                   + tri[i][j] for j in range(i + 1)])
    odd = [v for v in dp[-1] if v % 2 == 1]
    return max(odd) if odd else -1


def fixed_odd(tri):
    """补一维奇偶：dp[i][j][p] = 到 (i, j) 且路径和奇偶为 p 的最大和。"""
    n = len(tri)
    dp = [[[NEG, NEG] for _ in range(n)] for _ in range(n)]
    dp[0][0][tri[0][0] % 2] = tri[0][0]
    for i in range(1, n):
        for j in range(i + 1):
            for k in (j - 1, j):
                if 0 <= k <= i - 1:
                    for p in (0, 1):
                        if dp[i - 1][k][p] > NEG:
                            v = dp[i - 1][k][p] + tri[i][j]
                            dp[i][j][v % 2] = max(dp[i][j][v % 2], v)
    best = max(dp[n - 1][j][1] for j in range(n))
    return best if best > NEG else -1


def brute_odd(tri):
    """枚举全部 2^(n-1) 条路径，取和为奇数的最大值；没有就返回 -1。"""
    best = -1
    for turns in itertools.product((0, 1), repeat=len(tri) - 1):
        j, s = 0, tri[0][0]
        for i, d in enumerate(turns, 1):
            j += d
            s += tri[i][j]
        if s % 2 == 1:
            best = max(best, s)
    return best


# ---------------------------------------------------------------- 画面用：交出整张表 / 全部路径
def naive_table(tri):
    dp = [tri[0][:]]
    for i in range(1, len(tri)):
        dp.append([max(dp[i - 1][k] for k in (j - 1, j) if 0 <= k <= i - 1)
                   + tri[i][j] for j in range(i + 1)])
    return dp


def fixed_table(tri):
    n = len(tri)
    dp = [[[NEG, NEG] for _ in range(n)] for _ in range(n)]
    dp[0][0][tri[0][0] % 2] = tri[0][0]
    for i in range(1, n):
        for j in range(i + 1):
            for k in (j - 1, j):
                if 0 <= k <= i - 1:
                    for p in (0, 1):
                        if dp[i - 1][k][p] > NEG:
                            v = dp[i - 1][k][p] + tri[i][j]
                            dp[i][j][v % 2] = max(dp[i][j][v % 2], v)
    return [row[:i + 1] for i, row in enumerate(dp)]


def all_paths(tri):
    """按讲义表格的顺序（product 顺序）列出全部路径：[(格子序列, 和), ...]。"""
    out = []
    for turns in itertools.product((0, 1), repeat=len(tri) - 1):
        j, cells = 0, [(0, 0)]
        for i, d in enumerate(turns, 1):
            j += d
            cells.append((i, j))
        out.append((cells, sum(tri[i][c] for i, c in cells)))
    return out


def duel(seed=10, rounds=2000):
    """讲义的 2000 组随机对拍（同一随机种子与生成方式），顺带记录朴素版本每组对错。"""
    rnd = random.Random(seed)
    fixed_ok, naive_ok = [], []
    for _ in range(rounds):
        n = rnd.randint(2, 7)
        t = [[rnd.randint(0, 9) for _ in range(i + 1)] for i in range(n)]
        b = brute_odd(t)
        fixed_ok.append(fixed_odd(t) == b)
        naive_ok.append(naive_odd(t) == b)
    return fixed_ok, naive_ok


# ---------------------------------------------------------------- 硬币反例（第 6 周）
COINS, AMOUNT = [1, 3, 4], 6


def greedy_coins(coins=COINS, amount=AMOUNT):
    out = []
    for c in sorted(coins, reverse=True):
        while amount >= c:
            out.append(c)
            amount -= c
    return out


def dp_coins(coins=COINS, amount=AMOUNT):
    """最少枚数并回溯出一组用法。"""
    INF = float('inf')
    best, last = [0] + [INF] * amount, [0] * (amount + 1)
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and best[a - c] + 1 < best[a]:
                best[a], last[a] = best[a - c] + 1, c
    out, a = [], amount
    while a:
        out.append(last[a])
        a -= last[a]
    return sorted(out, reverse=True)
