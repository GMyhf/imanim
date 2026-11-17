"""数的划分片的数据层：讲义 T4 的记忆化深搜原样 + 插桩版（搜索树、剪枝前后节点数、调用次数），
以及自拟的动态规划 dp[i][j] = dp[i-1][j-1] + dp[i-j][j]（讲义只给了深搜，没给 DP 代码）。

题面以 OpenJudge 28906 为准：把 n 分成 k 份，每份不能为空，不考虑顺序（6 < n <= 200，2 <= k <= 6）；
样例 7 3 → 4，7 2 → 3。讲义：courseware/202612_ADS_W16_Review_Final_Machine_Exam.md「T4. M28906 数的划分」。
"""
from __future__ import annotations

import io
import itertools
from contextlib import redirect_stdout
from functools import lru_cache

N, K = 7, 3                     # 样例一
N2, K2 = 7, 2                   # 样例二
BIG = (200, 6)                  # 数据范围上限
N_LO, N_HI, K_LO, K_HI = 7, 200, 2, 6   # 6 < n <= 200，2 <= k <= 6
BRUTE_MAX = 30                  # 「n 小的时候再用穷举核对」：n <= 30

# ------------------------------------------------------------------ 讲义原样（第 16 周 T4）
LECTURE_SRC = '''from functools import lru_cache
n, k = map(int, input().split())
@lru_cache(None)
def dfs(rem, left, low):
    if left == 1:
        return int(rem >= low)
    return sum(dfs(rem - x, left - 1, x)
               for x in range(low, rem // left + 1))
print(dfs(n, k, 1))
'''


def run_lecture(n, k):
    """把讲义代码原样 exec：input() 喂 "n k"，截获 print 的输出。"""
    buf = io.StringIO()
    env = {"input": lambda *a: f"{n} {k}", "__name__": "__lecture__"}
    with redirect_stdout(buf):
        exec(LECTURE_SRC, env)
    return int(buf.getvalue().strip())


# ------------------------------------------------------------------ 插桩版深搜
def dfs_count(n, k, memo=True, bound=True):
    """讲义的 dfs 插桩：返回 (答案, 函数调用次数, 不同状态数)。

    memo=False 去掉 lru_cache；bound=False 把上界 rem // left 换成 rem（不剪枝）。
    """
    calls = [0]
    seen = set()

    def body(rem, left, low):
        calls[0] += 1
        seen.add((rem, left, low))
        if left == 1:
            return int(rem >= low)
        hi = rem // left if bound else rem
        return sum(f(rem - x, left - 1, x) for x in range(low, hi + 1))

    f = lru_cache(None)(body) if memo else body
    ans = f(n, k, 1)
    return ans, calls[0], len(seen)


def dfs_tree(n=N, k=K, bound=True):
    """搜索树（不记忆化）：节点 {id, rem, left, low, x(进入本节点时选的那一份), parent, kids, ok, path}。

    ok：叶子（left == 1）且 rem >= low 为 True；其他节点为 None 时表示内部节点，
    useful：子树里有成功的叶子。path：从根到本节点已选的各份（叶子再补上最后一份 rem）。
    """
    nodes = []

    def go(rem, left, low, x, parent, path):
        me = {"id": len(nodes), "rem": rem, "left": left, "low": low, "x": x, "parent": parent,
              "kids": [], "path": path}
        nodes.append(me)
        if parent is not None:
            nodes[parent]["kids"].append(me["id"])
        if left == 1:
            me["ok"] = rem >= low
            me["useful"] = me["ok"]
            if me["ok"]:
                me["path"] = path + [rem]
            return me["useful"]
        me["ok"] = None
        hi = rem // left if bound else rem
        u = False
        for y in range(low, hi + 1):
            u = go(rem - y, left - 1, y, y, me["id"], path + [y]) or u
        me["useful"] = u
        return u
    go(n, k, 1, None, None, [])
    return nodes


def tree_key(nd):
    return (nd["rem"], nd["left"], nd["low"], nd["x"])


# ------------------------------------------------------------------ 去重：有序填法 vs 分法
def compositions(n=N, k=K):
    """一份一份随便填（每份 >= 1，有顺序）：所有填法，按字典序。"""
    return [c for c in itertools.product(range(1, n + 1), repeat=k) if sum(c) == n]


def partitions(n=N, k=K):
    """非降序列（后一份不小于前一份）：每种分法一种写法，按字典序。"""
    return sorted({tuple(sorted(c)) for c in compositions(n, k)})


# ------------------------------------------------------------------ 动态规划（自拟，讲义未给代码）
def dp_table(n, k):
    """dp[i][j] = 把 i 分成 j 份的分法数。

    至少有一份是 1：拿掉它 → dp[i-1][j-1]；每份都 >= 2：每份减 1 → dp[i-j][j]。边界 dp[0][0] = 1。
    """
    dp = [[0] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 1
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            dp[i][j] = dp[i - 1][j - 1] + dp[i - j][j]
    return dp


def dp_count(n, k):
    return dp_table(n, k)[n][k]


def split_classes(n=N, k=K):
    """把 n 分 k 份的分法按「有没有 1」分两类：返回 (有 1 的, 拿掉一个 1 后, 都 >= 2 的, 每份减 1 后)。"""
    ps = partitions(n, k)
    ones = [p for p in ps if 1 in p]
    rest = [p for p in ps if 1 not in p]
    removed = [tuple(sorted(list(p)[1:])) for p in ones]            # 非降序列第一个就是 1
    minus = [tuple(v - 1 for v in p) for p in rest]
    return ones, removed, rest, minus


def dp_cells(n, k):
    """DP 表的格子数（「两百乘六」）。"""
    return n * k


# ------------------------------------------------------------------ 对拍
def cross_check():
    """n 从 7 到 200、k 从 2 到 6：讲义深搜 vs 自拟 DP，返回 (组数, 不一致的组)。"""
    bad, cnt = [], 0
    tabs = dp_table(N_HI, K_HI)
    for n in range(N_LO, N_HI + 1):
        for k in range(K_LO, K_HI + 1):
            cnt += 1
            a, b = dfs_count(n, k)[0], tabs[n][k]
            if a != b:
                bad.append((n, k, a, b))
    return cnt, bad


def brute_check(maxn=BRUTE_MAX):
    """n <= maxn、k 从 1 到 6：穷举非降 k 元组 vs 深搜 vs DP，返回 (组数, 不一致的组)。"""
    bad, cnt = [], 0
    for n in range(1, maxn + 1):
        for k in range(1, K_HI + 1):
            cnt += 1
            b = sum(1 for c in itertools.combinations_with_replacement(range(1, n + 1), k) if sum(c) == n)
            if not b == dfs_count(n, k)[0] == dp_count(n, k):
                bad.append((n, k))
    return cnt, bad


if __name__ == "__main__":
    print(run_lecture(N, K), run_lecture(N2, K2), dp_count(N, K), dp_count(N2, K2))
    print(len(compositions()), partitions())
    t1, t2 = dfs_tree(), dfs_tree(bound=False)
    print(len(t1), len(t2), sum(not x["useful"] for x in t2))
    print(dfs_count(*BIG), dfs_count(*BIG, memo=False))
    print(split_classes())
    print(cross_check()[0], dp_cells(*BIG))
