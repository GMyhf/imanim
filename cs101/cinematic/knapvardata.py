"""背包三个变形片的数据层：二进制拆分与可达集合、恰好装满与不超过两种初值、Coins、二维费用、分数背包与 0/1 贪心反例。

约定与讲义一致（W11 讲义 1.4–1.6）：binary_split / multi_knapsack / exact_fill_max / pokemon / fractional_knapsack
照抄讲义，只加插桩（记录可达集合、每件物品后的整行 dp、每件物品切下的比例）。
coins（作业 M01742）讲义没有给代码，按 multi_knapsack 的结构写成布尔版：二进制拆分 + 每捆当 0/1 倒序。
"""
from __future__ import annotations

from itertools import combinations

# ---- 片中用到的数据
SPLIT_KS = (1, 5, 7, 10, 13)                    # 讲义验证拆分的那几个 k
SPLIT_K = 13                                     # 主例：13 拆成 1 2 4 6
EX_W, EX_V, EX_CAP = [2, 4], [10, 20], 5         # 讲义 exact_fill_max 第二例：凑不出 5
COIN_A, COIN_C, COIN_M = [1, 2, 4], [2, 1, 1], 10  # Coins 样例第一组，答案 8
PK_BALLS, PK_HP = 10, 100                        # 讲义 pokemon 例
PK_PETS = [(7, 10), (2, 40), (2, 50), (1, 20), (4, 20)]
FR_ITEMS, FR_CAP = [(30, 6), (20, 5), (20, 5)], 10   # (总价值, 重量)：分数 46、0/1 贪心 30、0/1 最优 40
COURSE_FR = [(4, 4), (10, 5), (7, 2)]           # 讲义 fractional_knapsack 例，20.0


# ---------------------------------------------------------------- 1.4 多重背包与二进制拆分（讲义原样）
def multi_knapsack(items, cap):
    """items: [(体积, 价值, 数量)]。"""
    dp = [0] * (cap + 1)
    for w, v, k in items:
        cnt = 1
        while k > 0:
            take = min(cnt, k)
            ww, vv = w * take, v * take
            for c in range(cap, ww - 1, -1):       # 每一"捆"当 0-1 背包
                dp[c] = max(dp[c], dp[c - ww] + vv)
            k -= take
            cnt <<= 1
    return dp[cap]


def binary_split(k):
    parts, cnt = [], 1
    while k > 0:
        take = min(cnt, k)
        parts.append(take)
        k -= take
        cnt <<= 1
    return parts


def reach_steps(k):
    """讲义的验证循环插桩：每加一捆之后的可达集合（排好序），第 0 项是只有 {0}。"""
    parts = binary_split(k)
    reachable = {0}
    out = [sorted(reachable)]
    for p in parts:
        reachable |= {r + p for r in reachable}
        out.append(sorted(reachable))
    return out


# ---------------------------------------------------------------- 1.5 恰好装满（讲义原样 + 两种初值的逐件记录）
def exact_fill_max(weights, values, cap):
    NEG = float('-inf')
    dp = [NEG] * (cap + 1)
    dp[0] = 0                                # 只有容量 0 是"可达"的起点
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):
            if dp[c - w] != NEG:
                dp[c] = max(dp[c], dp[c - w] + v)
    return dp[cap] if dp[cap] != NEG else -1


def fill_rows(weights, values, cap, exact):
    """同一段 0/1 倒序代码，只换初值。返回 [初值行, 放完第 1 件后的行, ...]；-inf 表示到不了。"""
    NEG = float('-inf')
    dp = [NEG] * (cap + 1) if exact else [0] * (cap + 1)
    dp[0] = 0
    rows = [dp[:]]
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):
            if dp[c - w] != NEG:
                dp[c] = max(dp[c], dp[c - w] + v)
        rows.append(dp[:])
    return rows


# ---------------------------------------------------------------- 作业 M01742 Coins（布尔版多重背包）
def coins_steps(A, C, m):
    """返回 (捆列表 [(面值×枚数, 金额)], 每加一捆后的可达行 [bool]*(m+1), 1..m 能凑出的个数)。"""
    ok = [False] * (m + 1)
    ok[0] = True
    bundles, rows = [], [ok[:]]
    for a, k in zip(A, C):
        cnt = 1
        while k > 0:
            take = min(cnt, k)
            ww = a * take
            for c in range(m, ww - 1, -1):         # 每一捆当 0-1，倒序
                if ok[c - ww]:
                    ok[c] = True
            bundles.append((a, take, ww))
            rows.append(ok[:])
            k -= take
            cnt <<= 1
    return bundles, rows, sum(ok[1:])


def coins(A, C, m):
    return coins_steps(A, C, m)[2]


# ---------------------------------------------------------------- 1.6 二维费用（讲义原样）
def pokemon(balls, hp, pets):
    """pets: [(消耗球数, 消耗体力)]；返回 (最多收服数, 剩余最大体力)。"""
    # dp[b][h] = 用不超过 b 个球、消耗不超过 h 点体力，最多收服几只
    dp = [[0] * (hp + 1) for _ in range(balls + 1)]
    for cost_b, cost_h in pets:
        for b in range(balls, cost_b - 1, -1):
            for h in range(hp, cost_h - 1, -1):
                dp[b][h] = max(dp[b][h], dp[b - cost_b][h - cost_h] + 1)
    best = dp[balls][hp]
    left = 0
    for h in range(hp + 1):
        if dp[balls][h] == best:
            left = hp - h                     # 第一个达到 best 的 h 就是最省体力的
            break
    return best, left


def pokemon_pick(balls, hp, pets):
    """画面上要标出收服了哪几只：在只数最多的方案里取耗体力最少的（下标从 0）。"""
    best, left = pokemon(balls, hp, pets)
    for comb in combinations(range(len(pets)), best):
        if sum(pets[i][0] for i in comb) <= balls and hp - sum(pets[i][1] for i in comb) == left:
            return list(comb)
    raise AssertionError("找不到与 pokemon() 一致的方案")


# ---------------------------------------------------------------- 1.6 分数背包（讲义原样 + 切分记录）
def fractional_knapsack(items, cap):
    """items: [(总价值, 重量)]，可切分。"""
    items = sorted(items, key=lambda it: it[0] / it[1], reverse=True)
    total, rest = 0.0, cap
    for value, weight in items:
        if rest >= weight:
            total += value
            rest -= weight
        else:
            total += value * rest / weight
            break
    return total


def fractional_trace(items, cap):
    """同上，记录每件物品拿走的重量：[(价值, 重量, 拿走的重量, 得到的价值)]。"""
    items = sorted(items, key=lambda it: it[0] / it[1], reverse=True)
    rest, out = cap, []
    for value, weight in items:
        if rest >= weight:
            out.append((value, weight, weight, value))
            rest -= weight
        else:
            out.append((value, weight, rest, value * rest / weight))
            rest = 0
            break
    return out


def greedy_01(items, cap):
    """常见的错误做法：不能切的物品也按单价从高到低整件装，装不下就跳过。返回 (总价值, 装了哪几件的下标)。"""
    order = sorted(range(len(items)), key=lambda i: items[i][0] / items[i][1], reverse=True)
    total, rest, took = 0, cap, []
    for i in order:
        value, weight = items[i]
        if weight <= rest:
            total += value
            rest -= weight
            took.append(i)
    return total, took


def knap01(items, cap):
    """0/1 背包一维倒序（与 knap 片同一段代码），items 是 (价值, 重量)。"""
    dp = [0] * (cap + 1)
    for value, weight in items:
        for c in range(cap, weight - 1, -1):
            dp[c] = max(dp[c], dp[c - weight] + value)
    return dp[cap]
