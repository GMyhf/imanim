"""最大子段和片的数据层：一维 Kadane、按列压缩的最大子矩阵、打家劫舍。

约定与讲义一致（W10 讲义 2.7、W11 讲义 2.3–2.4 · M02766）：max_subarray / max_subarray_o1 / max_submatrix / rob
照抄讲义，T / MAT / HOUSES 是讲义里的例子；*_trace 版本与讲义函数逐行同逻辑，只是把中间量交出来给画面用
（test_kadane 对撞两者结果、暴力枚举与旁白数字）。
"""
from __future__ import annotations

T = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
MAT = [[0, -2, -7, 0],
       [9, 2, -6, 2],
       [-4, 1, -4, 1],
       [-1, 8, 0, -2]]
HOUSES = [2, 7, 9, 3, 1]


# ---------------------------------------------------------------- 讲义原样
def max_subarray(a):
    dp = [0] * len(a)
    dp[0] = a[0]
    for i in range(1, len(a)):
        dp[i] = max(a[i], dp[i - 1] + a[i])
    return max(dp)


def max_subarray_o1(a):                   # 滚动
    best = cur = a[0]
    for v in a[1:]:
        cur = max(v, cur + v)
        best = max(best, cur)
    return best


def max_submatrix(mat):
    n, m = len(mat), len(mat[0])
    best = mat[0][0]
    for top in range(n):
        col = [0] * m                          # 第 top..bottom 行的列和
        for bottom in range(top, n):
            row = mat[bottom]
            for j in range(m):
                col[j] += row[j]
            # 对 col 跑 Kadane
            cur = col[0]
            best = max(best, cur)
            for j in range(1, m):
                cur = max(col[j], cur + col[j])
                best = max(best, cur)
    return best


def rob(nums):
    prev, cur = 0, 0            # prev = dp[i-2], cur = dp[i-1]
    for v in nums:
        prev, cur = cur, max(cur, prev + v)
    return cur


# ---------------------------------------------------------------- 画面用：交出中间量
def kadane_trace(a):
    """讲义 max_subarray 的 dp 数组，外加每格是否「另起一段」（前一格 dp 为负）与每段起点。

    返回 (dp, restart, start)：restart[i] 为真表示 dp[i] 取的是 a[i] 自己；start[i] 是以 i 结尾那段的起点。
    """
    dp, restart, start = [a[0]], [True], [0]
    for i in range(1, len(a)):
        take_new = dp[i - 1] < 0                      # 前一格为负才另起；为零时两种取法同值，算接上
        dp.append(max(a[i], dp[i - 1] + a[i]))
        restart.append(take_new)
        start.append(i if take_new else start[i - 1])
    return dp, restart, start


def best_segment(a):
    """最大子段和与对应区间 [l, r]（取第一个达到最大值的结尾）。"""
    dp, _, start = kadane_trace(a)
    r = max(range(len(a)), key=lambda i: (dp[i], -i))
    return dp[r], start[r], r


def submatrix_log(mat):
    """讲义 max_submatrix 逐 (top, bottom) 记录：(top, bottom, 列和, 本对最大段和, 段左端, 段右端, 截至此时 best)。"""
    n, m = len(mat), len(mat[0])
    best = mat[0][0]
    out = []
    for top in range(n):
        col = [0] * m
        for bottom in range(top, n):
            row = mat[bottom]
            for j in range(m):
                col[j] += row[j]
            s, l, r = best_segment(col)
            best = max(best, s)
            out.append((top, bottom, col[:], s, l, r, best))
    return out


def best_submatrix(mat):
    """最大子矩阵 (和, top, bottom, left, right)：取 submatrix_log 里第一个达到最大值的。"""
    log = submatrix_log(mat)
    t, b, _, s, l, r, _ = max(log, key=lambda e: e[3])
    return s, t, b, l, r


def rob_trace(nums):
    """讲义 rob 的逐步 (prev, cur)，以及 dp 数组 dp[i] = 前 i+1 家的最大收益。"""
    prev, cur = 0, 0
    dp = []
    for v in nums:
        prev, cur = cur, max(cur, prev + v)
        dp.append(cur)
    return dp


def rob_choice(nums):
    """从 dp 数组倒推偷了哪些家（下标从 0）。"""
    dp = rob_trace(nums)
    picks, i = [], len(nums) - 1
    while i >= 0:
        before = dp[i - 1] if i >= 1 else 0
        if dp[i] != before:
            picks.append(i)
            i -= 2
        else:
            i -= 1
    return sorted(picks)
