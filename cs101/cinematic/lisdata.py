"""最长上升子序列片的数据层：讲义 2.1 节四段代码原样 + 插桩版（dp 逐格来源、tails 逐步落牌、回溯）。

约定与讲义一致（W11 讲义 2.1 节）：dp[i] = 以 a[i] 结尾的最长上升子序列长度；
tails[k] = 长度为 k+1 的上升子序列的最小结尾，严格上升用 bisect_left、非降用 bisect_right。
片中主数据取 OpenJudge 02533 的样例（也是讲义的例子）。
"""
from __future__ import annotations

import bisect

A = [1, 7, 3, 5, 9, 4, 8]                              # 02533 样例 / 讲义例子
MISSILE = [389, 207, 155, 300, 299, 170, 158, 65]      # M02945 样例
EQUAL = [2, 2, 2]                                      # 严格上升与非降的对比
BIG_N = 100_000                                        # 「n 到十万」


# ------------------------------------------------------------------ 讲义原样
def lis_n2(a):
    n = len(a)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp) if dp else 0


def lis_nlogn(a):
    tails = []
    for v in a:
        pos = bisect.bisect_left(tails, v)   # 严格上升用 bisect_left
        if pos == len(tails):
            tails.append(v)
        else:
            tails[pos] = v                    # 用更小的值替换，为后面留空间
    return len(tails)


def longest_non_increasing(a):
    """最长不上升子序列长度 = 反转后取最长不降子序列。"""
    tails = []
    for v in reversed(a):
        pos = bisect.bisect_right(tails, v)
        if pos == len(tails):
            tails.append(v)
        else:
            tails[pos] = v
    return len(tails)


def max_rising_sum(a):
    n = len(a)
    dp = a[:]                                  # dp[i] = 以 i 结尾的最大上升子序列和
    for i in range(n):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + a[i])
    return max(dp)


# ------------------------------------------------------------------ 插桩版
def n2_trace(a=A):
    """O(n²) 插桩：返回 (dp, steps)。steps[i] = (候选 j 列表, 取到最大值的 j 或 None)。

    候选 j 是所有 j < i 且 a[j] < a[i] 的下标；最佳 j 取 dp 最大者里最靠左的那个（与「接在谁后面」的旁白一致：八接在五后面）。
    """
    n = len(a)
    dp = [1] * n
    steps = []
    for i in range(n):
        cand = []
        for j in range(i):
            if a[j] < a[i]:
                cand.append(j)
                dp[i] = max(dp[i], dp[j] + 1)
        best = max(cand, key=lambda j: (dp[j], -j)) if cand else None
        steps.append((cand, best))
    return dp, steps


def compares(n):
    """两层循环里 a[j] < a[i] 的比较次数：n(n-1)/2。"""
    return n * (n - 1) // 2


def lis_back(a=A):
    """从 dp 最大值（第一个）往前倒着找：每次找一个更小、dp 正好少一的数（取最近的）。返回下标列表（正序）。"""
    dp, _ = n2_trace(a)
    if not a:
        return []
    i = dp.index(max(dp))
    out = [i]
    while dp[i] > 1:
        i = next(j for j in range(i - 1, -1, -1) if a[j] < a[i] and dp[j] == dp[i] - 1)
        out.append(i)
    return out[::-1]


def tails_trace(a=A, side="left"):
    """tails 插桩：每来一个数记一步 (值, 位置, 是否新开一摞, tails 快照, 各摞牌)。

    「摞」是把被替换掉的旧结尾也留在下面：piles[k] 自底向上，牌顶 = tails[k]。
    """
    find = bisect.bisect_left if side == "left" else bisect.bisect_right
    tails, piles, steps = [], [], []
    for v in a:
        pos = find(tails, v)
        new = pos == len(tails)
        if new:
            tails.append(v)
            piles.append([v])
        else:
            tails[pos] = v
            piles[pos].append(v)
        steps.append((v, pos, new, tails[:], [p[:] for p in piles]))
    return steps


def is_subseq_of(seq, a):
    """seq 是否是 a 的子序列（按顺序出现）。"""
    it = iter(a)
    return all(x in it for x in seq)


def trap_step(a=A):
    """第一个「tails 不是真实子序列」的时刻：返回 (步号, tails 快照)；没有则 None。"""
    for k, (_, _, _, tails, _) in enumerate(tails_trace(a)):
        if not is_subseq_of(tails, a[:k + 1]):
            return k, tails
    return None


def tails_strict_vs_nondec(a=EQUAL):
    """严格上升（bisect_left）与非降（bisect_right）下的 tails 长度。"""
    return len(tails_trace(a, "left")[-1][3]), len(tails_trace(a, "right")[-1][3])


def missile_trace(a=MISSILE):
    """拦截导弹：反转后用 bisect_right 落牌，返回反转后的数组与逐步记录。"""
    r = list(reversed(a))
    return r, tails_trace(r, "right")


def non_increasing_witness(a=MISSILE):
    """一条最长不上升子序列（O(n²) dp 倒着找，取最近的前驱），返回下标列表（正序）。"""
    n = len(a)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if a[j] >= a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    if not a:
        return []
    i = dp.index(max(dp))
    out = [i]
    while dp[i] > 1:
        i = next(j for j in range(i - 1, -1, -1) if a[j] >= a[i] and dp[j] == dp[i] - 1)
        out.append(i)
    return out[::-1]


def rising_sum_back(a=A):
    """最大上升子序列和的 dp 与一条取到最大值的序列（倒着找 dp[j] = dp[i] - a[i]）。"""
    n = len(a)
    dp = a[:]
    for i in range(n):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + a[i])
    i = dp.index(max(dp))
    out = [i]
    while dp[i] != a[i]:
        i = next(j for j in range(i - 1, -1, -1) if a[j] < a[i] and dp[j] == dp[i] - a[i])
        out.append(i)
    return dp, [a[k] for k in out[::-1]]


if __name__ == "__main__":
    print(lis_n2(A), lis_nlogn(A), n2_trace()[0], lis_back(), [A[i] for i in lis_back()])
    for s in tails_trace():
        print(s)
    print(trap_step(), tails_strict_vs_nondec(), longest_non_increasing(MISSILE), missile_trace()[1][-1])
    print(max_rising_sum(A), rising_sum_back(), compares(BIG_N))
