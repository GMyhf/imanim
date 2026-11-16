"""树状数组片的数据层：讲义代码原样 + 插桩，画面与旁白里的每个数字都从这里来。

依据：数据结构与算法（B）2026spring 第 2 周讲义 202603_DSA_W02_BIT_Fenwick.md
  - 第 3 节与附录 A：bit_sum / bit_update / construct（arr = 1..16，讲义打印 BIT: 0 1 3 3 10 5 11 7 36 …）；
  - 附录 A 的两个例子：get_sum(14) = C[14]+C[12]+C[8]，给 A[6] 加 v 要改 C[6]、C[8]、C[16]，A[9] 改 C[9]、C[10]、C[12]、C[16]；
  - 练习 M20018 蚂蚁王国的越野跑：BIT 类 + 离散化 + 从左到右扫描（样例 1 5 10 7 6 → 7）。
"""
from __future__ import annotations


# ------------------------------------------------------------ 讲义附录 A 原样
def bit_sum(BIT, i):
    """计算树状数组 BIT 从索引 1 到 i 的前缀和"""
    s = 0
    while i > 0:
        s += BIT[i]
        i -= i & (-i)  # 回溯至祖先节点
    return s


def bit_update(BIT, i, v):
    """在树状数组 BIT 中更新索引 i 处的值 v"""
    while i < len(BIT):
        BIT[i] += v
        i += i & (-i)  # 回溯至祖先节点


def construct(arr, n):
    BIT = [0] * (n + 1)
    for i in range(n):  # Store the actual values in BIT[] using bit_update()
        bit_update(BIT, i + 1, arr[i])

    return BIT


# ------------------------------------------------------------ M20018 讲义 BIT 类原样
class BIT:
    def __init__(self, n):
        self.n = n
        self.tree = [0]*(n+1)

    def update(self, i, v=1):
        while i <= self.n:
            self.tree[i] += v
            i += i & -i

    def query(self, i):
        s = 0
        while i > 0:
            s += self.tree[i]
            i -= i & -i
        return s


# ------------------------------------------------------------ 插桩：记下跳过的下标
def lowbit(x: int) -> int:
    return x & -x


def cover(i: int) -> tuple[int, int]:
    """C[i] 管辖的闭区间 [i - lowbit(i) + 1, i]。"""
    return i - lowbit(i) + 1, i


def query_path(i: int) -> list[int]:
    """bit_sum 循环里依次读到的下标。"""
    out = []
    while i > 0:
        out.append(i)
        i -= i & (-i)
    return out


def update_path(i: int, n: int) -> list[int]:
    """bit_update 循环里依次改到的下标（BIT 长 n+1）。"""
    out = []
    while i < n + 1:
        out.append(i)
        i += i & (-i)
    return out


def bits(x: int, w: int = 8) -> str:
    """w 位补码。"""
    return format(x & ((1 << w) - 1), f"0{w}b")


# ------------------------------------------------------------ 片中用到的具体数字
N = 16
A = list(range(1, N + 1))                     # 讲义附录 arr = [1, 2, …, 16]
C = construct(A, N)                          # [0, 1, 3, 3, 10, 5, 11, 7, 36, 9, 19, 11, 42, 13, 27, 15, 136]
PREFIX = [sum(A[:i]) for i in range(N + 1)]  # 前缀和数组 S[0..16]

LB_X = 12                                    # lowbit 演示：12 & -12 = 4
LB_ROWS = [("x", bits(LB_X)), ("~x", bits(~LB_X)), ("-x = ~x + 1", bits(-LB_X)), ("x & -x", bits(LB_X & -LB_X))]
LB_MORE = [(x, lowbit(x)) for x in (6, 7, 8)]

Q_I = 14                                     # 查询前 14 个数
Q_PATH = query_path(Q_I)                     # [14, 12, 8]
Q_PARTS = [C[j] for j in Q_PATH]             # [27, 42, 36]
Q_SUM = bit_sum(C, Q_I)                      # 105

U_I, U_V = 6, 3                              # 给第 6 个数加 3
U_PATH = update_path(U_I, N)                 # [6, 8, 16]
C_AFTER = C[:]
bit_update(C_AFTER, U_I, U_V)
U2_PATH = update_path(9, N)                  # [9, 10, 12, 16]

PREFIX_TOUCH = N - 3 + 1                     # 前缀和数组里改第 3 个数要动 S[3..16]：14 个
BIG_N = 10 ** 6
BIG_STEPS = BIG_N.bit_length()               # 20

# 蚂蚁越野跑（M20018 样例 1）
ANTS = [1, 5, 10, 7, 6]
VALS = sorted(set(ANTS))
RANK = {x: i + 1 for i, x in enumerate(VALS)}


def ant_scan(v):
    """讲义的扫描循环原样，逐步记下 (速度, 排名, 前面更慢的个数, 累计, 查询路径, 修改路径, 修改后的 tree)。"""
    vals = sorted(set(v))
    rank = {x: i+1 for i, x in enumerate(vals)}
    bit = BIT(len(vals))
    ans = 0
    steps = []
    for x in v:
        r = rank[x]
        got = bit.query(r-1)
        ans += got
        bit.update(r)
        steps.append({"x": x, "r": r, "got": got, "ans": ans, "q": query_path(r - 1),
                      "u": update_path(r, len(vals)), "tree": bit.tree[:]})
    return ans, steps


ANT_ANS, ANT_STEPS = ant_scan(ANTS)          # 7
ANT_PAIRS = [(i, j) for i in range(len(ANTS)) for j in range(i + 1, len(ANTS)) if ANTS[i] < ANTS[j]]
