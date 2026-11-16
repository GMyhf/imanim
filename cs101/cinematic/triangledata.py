"""从递归到 DP 三步演化片的数据层：爬楼梯（递归 / 记忆化 / 填表）与数字三角形（两种填法 / 一维滚动）。

约定与课件一致（W10 讲义 2.3–2.6）：
- f1 / f2 / f3 / f4、climb_stairs、max_path_sum、max_path_sum_1d、TRI 照抄讲义；
- 讲义 2.3 的三步演化以斐波那契为模板，本片把 f1 / f2 原样换成爬楼梯的边界（dp[0] = dp[1] = 1），
  即 climb_rec / climb_memo，test_triangle 对撞 climb_rec(n) == f1(n + 1) == climb_stairs(n)；
- 讲义 2.6 只给了自底向上一种写法，tri_rec / tri_memo（记忆化递归，同一状态「从 (i, j) 走到底的最大和」）
  与 forward_table（另一种状态「从顶走到 (i, j) 的最大和」，讲义末尾的「从上往下推」）是按讲义文字补写的，
  test_triangle 用路径穷举对撞。
插桩只加计数与记录，不改逻辑。
"""
from __future__ import annotations

N_STAIRS = 7
TRI = [[7], [3, 8], [8, 1, 0], [2, 7, 4, 4], [4, 5, 2, 6, 5]]


# ---------------------------------------------------------------- 讲义原样：斐波那契四步（2.3）
def f1(n):
    if n <= 2:
        return 1
    return f1(n - 1) + f1(n - 2)


def f2(n, memo=None):
    if memo is None:
        memo = {}
    if n <= 2:
        return 1
    if n in memo:
        return memo[n]
    memo[n] = f2(n - 1, memo) + f2(n - 2, memo)
    return memo[n]


def f3(n):
    if n <= 2:
        return 1
    dp = [0] * (n + 1)
    dp[1] = dp[2] = 1
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]


def f4(n):
    if n <= 2:
        return 1
    a, b = 1, 1
    for _ in range(n - 2):
        a, b = b, a + b
    return b


# ---------------------------------------------------------------- 讲义原样：爬楼梯（2.5）
def climb_stairs(n):
    dp = [0] * (n + 1)
    dp[0] = 1
    for i in range(1, n + 1):
        dp[i] = dp[i - 1] + (dp[i - 2] if i >= 2 else 0)
    return dp[n]


# ---------------------------------------------------------------- 爬楼梯的前两步（f1 / f2 换边界）+ 插桩
def climb_rec(n, log=None):
    """第一步：暴力递归。log 记下每次调用的参数（真实调用顺序）。"""
    if log is not None:
        log.append(n)
    if n <= 1:
        return 1
    return climb_rec(n - 1, log) + climb_rec(n - 2, log)


def climb_memo(n, memo=None, log=None):
    """第二步：记忆化。log 记 (参数, 方式)，方式为 base / hit / calc。"""
    if memo is None:
        memo = {}
    if n <= 1:
        if log is not None:
            log.append((n, "base"))
        return 1
    if n in memo:
        if log is not None:
            log.append((n, "hit"))
        return memo[n]
    if log is not None:
        log.append((n, "calc"))
    memo[n] = climb_memo(n - 1, memo, log) + climb_memo(n - 2, memo, log)
    return memo[n]


def climb_table(n):
    """climb_stairs 原样，交出整张 dp 表给画面用。"""
    dp = [0] * (n + 1)
    dp[0] = 1
    for i in range(1, n + 1):
        dp[i] = dp[i - 1] + (dp[i - 2] if i >= 2 else 0)
    return dp


def stairs_facts(n=N_STAIRS):
    rec_log, memo_log = [], []
    ans = climb_rec(n, rec_log)
    climb_memo(n, None, memo_log)
    per_level = [rec_log.count(k) for k in range(n + 1)]
    memo_level = [sum(1 for a, _ in memo_log if a == k) for k in range(n + 1)]
    return {"answer": ans, "rec_calls": len(rec_log), "rec_per_level": per_level,
            "memo_calls": len(memo_log), "memo_per_level": memo_level,
            "memo_hits": sum(1 for _, how in memo_log if how == "hit"),
            "loop_iters": n, "table": climb_table(n)}


# ---------------------------------------------------------------- 讲义原样：数字三角形（2.6）
def max_path_sum(tri):
    n = len(tri)
    dp = [row[:] for row in tri]          # ⚠️ 拷贝，不要改原数据
    for i in range(n - 2, -1, -1):
        for j in range(i + 1):
            dp[i][j] += max(dp[i + 1][j], dp[i + 1][j + 1])
    return dp[0][0]


def max_path_sum_1d(tri):
    dp = tri[-1][:]
    for i in range(len(tri) - 2, -1, -1):
        for j in range(i + 1):
            dp[j] = tri[i][j] + max(dp[j], dp[j + 1])
    return dp[0]


# ---------------------------------------------------------------- 插桩：整张表、填表顺序、滚动记录
def up_table(tri=TRI):
    """max_path_sum 原样，交出整张 dp 表（dp[i][j] = 从 (i, j) 走到底的最大和）。"""
    n = len(tri)
    dp = [row[:] for row in tri]
    for i in range(n - 2, -1, -1):
        for j in range(i + 1):
            dp[i][j] += max(dp[i + 1][j], dp[i + 1][j + 1])
    return dp


def roll_log(tri=TRI):
    """max_path_sum_1d 原样，逐次记录 (i, j, 读到的 dp[j], dp[j+1], 写入值)。"""
    dp = tri[-1][:]
    out = []
    for i in range(len(tri) - 2, -1, -1):
        for j in range(i + 1):
            a, b = dp[j], dp[j + 1]
            dp[j] = tri[i][j] + max(dp[j], dp[j + 1])
            out.append((i, j, a, b, dp[j]))
    return out


def tri_rec(tri=TRI, log=None):
    """记忆化之前：f(i, j) = tri[i][j] + max(f(i+1, j), f(i+1, j+1))，直接递归。"""
    def f(i, j):
        if log is not None:
            log.append((i, j))
        if i == len(tri) - 1:
            return tri[i][j]
        return tri[i][j] + max(f(i + 1, j), f(i + 1, j + 1))
    return f(0, 0)


def tri_memo(tri=TRI):
    """记忆化递归：返回 (答案, 调用次数, 各格算完的先后顺序, memo 表)。"""
    memo, order, calls = {}, [], [0]

    def f(i, j):
        calls[0] += 1
        if (i, j) in memo:
            return memo[(i, j)]
        if i == len(tri) - 1:
            memo[(i, j)] = tri[i][j]
        else:
            memo[(i, j)] = tri[i][j] + max(f(i + 1, j), f(i + 1, j + 1))
        order.append((i, j))
        return memo[(i, j)]
    ans = f(0, 0)
    return ans, calls[0], order, memo


def forward_table(tri=TRI):
    """另一种状态：dp[i][j] = 从顶走到 (i, j) 的最大和；两端只有一个前驱，答案要在底行挑最大。"""
    n = len(tri)
    dp = [tri[0][:]]
    for i in range(1, n):
        row = []
        for j in range(i + 1):
            if j == 0:
                row.append(dp[i - 1][0] + tri[i][j])
            elif j == i:
                row.append(dp[i - 1][i - 1] + tri[i][j])
            else:
                row.append(max(dp[i - 1][j - 1], dp[i - 1][j]) + tri[i][j])
        dp.append(row)
    return dp


def best_path(tri=TRI):
    """从顶沿 up_table 较大的一边往下走，找回一条最大和路径（相等取左）。"""
    dp = up_table(tri)
    j, cells = 0, [(0, 0)]
    for i in range(1, len(tri)):
        if dp[i][j + 1] > dp[i][j]:
            j += 1
        cells.append((i, j))
    return cells


def count_paths(tri=TRI):
    return 2 ** (len(tri) - 1)
