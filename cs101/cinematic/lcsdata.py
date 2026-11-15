"""LCS 与编辑距离片的数据层：讲义两段代码原样 + 插桩版（整张表、逐格来源）+ 回溯。

约定与课件一致（W11 P20–P21、讲义 2.2 节）：dp[i][j] 定义在 s[:i]、t[:j] 两个前缀上；
LCS 边界全 0，编辑距离第一列 i（删光）、第一行 j（全插入）；删 = 上、插 = 左、改 = 左上。
"""
from __future__ import annotations

LCS_S, LCS_T = "abcfbc", "abfcab"
ED_S, ED_T = "horse", "ros"


def lcs(s, t):
    """讲义原样。"""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def edit_distance(s, t):
    """讲义原样。"""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],
                                   dp[i][j - 1],
                                   dp[i - 1][j - 1])
    return dp[m][n]


def lcs_table(s=LCS_S, t=LCS_T):
    """插桩版：返回 (dp, log)，log 按填表顺序记 (i, j, 来源, 值)；来源 diag=末字符相同、up、left。"""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    log = []
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                src = "diag"
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
                src = "up" if dp[i - 1][j] >= dp[i][j - 1] else "left"
            log.append((i, j, src, dp[i][j]))
    return dp, log


def lcs_back(s=LCS_S, t=LCS_T):
    """从右下角回溯：相同走左上并记字符；不同走较大一边（相等时向上）。返回 (路径格子, 记下的 (i, j))、子序列。"""
    dp, _ = lcs_table(s, t)
    i, j = len(s), len(t)
    path, picks = [(i, j)], []
    while i > 0 and j > 0:
        if s[i - 1] == t[j - 1]:
            picks.append((i, j))
            i, j = i - 1, j - 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
        path.append((i, j))
    picks.reverse()
    return path, picks, "".join(s[a - 1] for a, _ in picks)


def ed_table(s=ED_S, t=ED_T):
    """插桩版：返回 (dp, log)，log 记 (i, j, 来源, 值)；来源 keep=末字符相同、del=上、ins=左、rep=左上。"""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    log = []
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                src = "keep"
            else:
                opts = [(dp[i - 1][j], "del"), (dp[i][j - 1], "ins"), (dp[i - 1][j - 1], "rep")]
                best = min(v for v, _ in opts)
                dp[i][j] = 1 + best
                src = next(name for v, name in opts if v == best)
            log.append((i, j, src, dp[i][j]))
    return dp, log


def ed_back(s=ED_S, t=ED_T):
    """回溯出一组最少操作（顺序：相同 > 改 > 删 > 插），按从左到右返回；并给出逐步变形的中间串。

    返回 (路径格子, ops, 中间串列表)，ops 元素为 (类型, s 中下标, 字符)。"""
    dp, _ = ed_table(s, t)
    i, j = len(s), len(t)
    path, ops = [(i, j)], []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and s[i - 1] == t[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(("rep", i - 1, s[i - 1], t[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("del", i - 1, s[i - 1], None))
            i -= 1
        else:
            ops.append(("ins", i, None, t[j - 1]))
            j -= 1
        path.append((i, j))
    ops.reverse()
    # 从左到右逐个施加：offset 记录前面插/删造成的位移
    cur, steps, offset = list(s), ["".join(s)], 0
    for kind, pos, a, b in ops:
        p = pos + offset
        if kind == "rep":
            cur[p] = b
        elif kind == "del":
            del cur[p]
            offset -= 1
        else:
            cur.insert(p, b)
            offset += 1
        steps.append("".join(cur))
    return path, ops, steps
