"""算法分析片的数据层：讲义 W04 第 2.2、3.3、3.4、4.4 节代码原样 + 插桩版。

讲义原样：容器对比实验 bench()（2.2 节）、两重循环的两种写法（3.3 节）、埃拉托色尼筛 sieve()（4.4 节）。
讲义的表格（3.2 节常见级别、3.4 节数据范围）抄成常量，代入的次数由这里现算。
补写（讲义只有一句「判素数的朴素做法是 O(√n)」，没有代码）：试除法 is_prime_trial 及其计数。
画面和旁白里的每个数字都从这里来，test_complexity.py 用独立实现对撞。
"""
from __future__ import annotations

import math
import time
from functools import lru_cache

DEMO_N = 6                     # 画两重循环格子用的 n
OPEN_N = 10 ** 5               # 开场那道题：n 最大十万
LEVEL_N = 10 ** 6              # 常见级别表：n = 10⁶
OPS_PER_SEC = (10 ** 7, 10 ** 8)   # 评测机每秒基本操作数（讲义 3.4 节）
POLY = (3, 100, 500)           # 3n² + 100n + 500（讲义 3.1 节）
BENCH_N, BENCH_STEP = 200000, 1000  # 讲义 2.2 节实验
TYPICAL_LIST_S, TYPICAL_SET_S = 0.6, 0.0001   # 讲义给出的典型实测结果（秒），不在这里现测
SIEVE_N = 100                  # 画面上筛的范围
BIG_SIEVE_N = 10 ** 6          # 「到一百万」


# ------------------------------------------------------------------ 讲义原样
def bench():
    """讲义 2.2 节：list 的 in 与 set 的 in 实测（只供参考，计时随机器而变，画面不用）。"""
    n = 200000
    data = list(range(n))
    lst, st = data, set(data)

    t0 = time.time()
    sum(1 for x in range(0, n, 1000) if x in lst)     # list 的 in：O(n) 每次
    t1 = time.time()
    sum(1 for x in range(0, n, 1000) if x in st)      # set 的 in：O(1) 每次
    t2 = time.time()
    return t1 - t0, t2 - t1


def sieve(limit):
    """返回长度 limit+1 的布尔数组，is_prime[i] 表示 i 是否为素数。O(n log log n)。"""
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    i = 2
    while i * i <= limit:
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):   # 从 i*i 开始，前面的已被更小的因子筛掉
                is_prime[j] = False
        i += 1
    return is_prime


# ------------------------------------------------------------------ 3.3 节两重循环（插桩：记下每次执行的 (i, j)）
def loop_square(n):
    """for i in range(n): for j in range(n)。"""
    cells = []
    for i in range(n):
        for j in range(n):
            cells.append((i, j))
    return cells


def loop_triangle(n):
    """for i in range(n): for j in range(i, n) —— n²/2 ~ O(n²)。"""
    cells = []
    for i in range(n):
        for j in range(i, n):
            cells.append((i, j))
    return cells


def triangle_count(n):
    """loop_triangle 的执行次数，闭式 n(n+1)/2（大 n 时不真的跑循环）。"""
    return n * (n + 1) // 2


def row_counts(n=DEMO_N):
    """每个 i 内层执行几次：[n, n-1, …, 1]。"""
    cells = loop_triangle(n)
    return [sum(1 for a, _ in cells if a == i) for i in range(n)]


def poly(n, c=POLY):
    a, b, d = c
    return a * n * n + b * n + d


# ------------------------------------------------------------------ 3.2 节常见级别（n = 10⁶）
def levels(n=LEVEL_N):
    """[(名字, LaTeX, 次数或 None, log10(次数))]；2ⁿ 太大，次数给 None，只给 log10。"""
    lg = math.log2(n)
    return [("log n", r"\log n", lg, math.log10(lg)),
            ("n", r"n", n, math.log10(n)),
            ("n log n", r"n\log n", n * lg, math.log10(n * lg)),
            ("n²", r"n^2", n * n, math.log10(n * n)),
            ("2ⁿ", r"2^n", None, n * math.log10(2))]


# ------------------------------------------------------------------ 3.4 节从数据范围倒推
BUDGET = [  # (n 的上限, 复杂度 LaTeX, 该想什么, 次数函数)
    (10, r"O(n!)", "全排列", math.factorial),
    (20, r"O(2^n)", "枚举子集", lambda n: 2 ** n),
    (100, r"O(n^3)", "Floyd、区间 DP", lambda n: n ** 3),
    (1000, r"O(n^2)", "两重循环", lambda n: n ** 2),
    (10 ** 5, r"O(n\log n)", "排序、二分", lambda n: n * math.log2(n)),
    (10 ** 6, r"O(n)", "一遍扫描", lambda n: n),
]


def budget_rows():
    """[(n, 复杂度, 该想什么, 代入后的次数)]。"""
    return [(n, cx, what, f(n)) for n, cx, what, f in BUDGET]


def open_ops(n=OPEN_N):
    """开场那道题按 3.3 节第二种两重循环写，要执行的次数。"""
    return triangle_count(n)


def seconds_at_best(ops):
    """按每秒 10⁸ 次（预算上限）算，最快要几秒。"""
    return ops / OPS_PER_SEC[1]


# ------------------------------------------------------------------ 3.5 节空间复杂度（讲义经验值）
PTR_BYTES, INT_BYTES = 8, 28        # 列表里一个元素的指针 / 一个 int 对象（64 位 CPython）
MEM_LIMIT_MB = (64, 256)            # OJ 常见内存限制
SPACE_LIST_N = 10 ** 6              # 一百万个整数的列表
SPACE_GRID = 10 ** 4                # 一万乘一万的二维表


def list_mb(n=SPACE_LIST_N):
    """n 个不同整数的列表：每个指针 + 每个对象，单位兆字节（10⁶ 字节）。"""
    return n * (PTR_BYTES + INT_BYTES) / 10 ** 6


def grid_ptr_mb(side=SPACE_GRID):
    """side × side 的二维表，只算指针（元素全是同一个对象时也省不掉）。"""
    return side * side * PTR_BYTES / 10 ** 6


# ------------------------------------------------------------------ 2.2 节 list in 与 set in（插桩：数比较次数）
def list_in_compares(n=BENCH_N, step=BENCH_STEP):
    """data = list(range(n))，逐个查 range(0, n, step)：x in lst 从头比到 x 才命中，比较 x+1 次。"""
    lst = list(range(n))
    total = 0
    for x in range(0, n, step):
        for v in lst:
            total += 1
            if v == x:
                break
    return total


def list_in_compares_fast(n=BENCH_N, step=BENCH_STEP):
    """同上，按「命中位置 + 1」直接求和（命中位置就是 x 本身）。"""
    return sum(x + 1 for x in range(0, n, step))


def set_lookups(n=BENCH_N, step=BENCH_STEP):
    """set 每查一次只算一次哈希：查询次数。"""
    return len(range(0, n, step))


def scan_demo(vals, x):
    """画面上的小例子：list 里找 x，依次比过的下标。"""
    out = []
    for k, v in enumerate(vals):
        out.append(k)
        if v == x:
            break
    return out


# ------------------------------------------------------------------ 4.4 节埃氏筛（插桩）
def sieve_trace(limit=SIEVE_N):
    """与 sieve() 同一流程，记下每个外层 i：(i, 当时 is_prime[i], 划掉的 j 列表)。返回 (trace, is_prime)。"""
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    trace = []
    i = 2
    while i * i <= limit:
        marks, alive = [], is_prime[i]
        if alive:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = False
                marks.append(j)
        trace.append((i, alive, marks))
        i += 1
    return trace, is_prime


@lru_cache(maxsize=None)
def sieve_marks(limit):
    """内层 is_prime[j] = False 一共执行几次（重复划同一个数也算）。"""
    trace, _ = sieve_trace(limit)
    return sum(len(m) for _, _, m in trace)


def primes_upto(limit):
    return [i for i, p in enumerate(sieve(limit)) if p]


# ------------------------------------------------------------------ 补写：试除法
def is_prime_trial(x, counter=None):
    """朴素判素数：用 2..√x 逐个去除，碰到能整除的就停。counter[0] 累加除法（取模）次数。"""
    if x < 2:
        return False
    d = 2
    while d * d <= x:
        if counter is not None:
            counter[0] += 1
        if x % d == 0:
            return False
        d += 1
    return True


def trial_count(limit):
    """对 2..limit 每个数各试除一遍，一共做几次除法（逐个真跑）。"""
    c = [0]
    for x in range(2, limit + 1):
        is_prime_trial(x, c)
    return c[0]


@lru_cache(maxsize=None)
def trial_count_fast(limit):
    """同 trial_count，但不真的去除：x 的最小素因子 p ≤ √x 时试了 p−1 次，否则试了 ⌊√x⌋−1 次。

    最小素因子用线性预处理求，一百万也只要一两秒（真跑试除要六千多万次取模）。
    """
    spf = list(range(limit + 1))
    i = 2
    while i * i <= limit:
        if spf[i] == i:
            for j in range(i * i, limit + 1, i):
                if spf[j] == j:
                    spf[j] = i
        i += 1
    total = 0
    for x in range(2, limit + 1):
        p = spf[x]
        total += p - 1 if p * p <= x else math.isqrt(x) - 1
    return total


def versus(limit):
    """(试除次数, 筛法划掉次数)。"""
    t = trial_count(limit) if limit <= 10 ** 5 else trial_count_fast(limit)
    return t, sieve_marks(limit)


if __name__ == "__main__":
    print(row_counts(), triangle_count(DEMO_N), len(loop_square(DEMO_N)), poly(10 ** 6))
    for r in levels():
        print(r)
    for r in budget_rows():
        print(r)
    print(open_ops(), seconds_at_best(open_ops()), list_mb(), grid_ptr_mb())
    print(list_in_compares_fast(), set_lookups(), bench())
    tr, isp = sieve_trace()
    print([(i, len(m)) for i, _, m in tr], sieve_marks(SIEVE_N), len(primes_upto(SIEVE_N)))
    print(versus(SIEVE_N), versus(BIG_SIEVE_N))
