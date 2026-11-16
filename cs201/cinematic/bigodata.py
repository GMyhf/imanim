"""渐进分析片的数据层：讲义第 1 章第 3 节的几段代码原样翻成 Python，逐条数赋值（基本操作）。

讲义口径：「时间代价」= 基本操作次数；赋值计数按 C 写法逐个数（循环初始化、循环体、i++ 都算）。
画面和旁白里的每个数字都从这里来；test_bigo.py 用闭式公式、暴力枚举与 Fraction 精确计算对撞。
"""
from __future__ import annotations

import math
from fractions import Fraction


# ---------------------------------------------------------------- 3.1 渐进分析的实例（赋值计数）
def sum_array(a):
    """for (i = sum = 0; i < n; i++) sum += a[i];   讲义：共 2 + 2n 次赋值。"""
    n, cnt = len(a), 0
    i = s = 0
    cnt += 2                            # i = sum = 0
    while i < n:
        s += a[i]; cnt += 1             # sum += a[i]
        i += 1; cnt += 1                # i++
    return s, cnt


def prefix_naive(a):
    """讲义第二段：每个子数组 a[0..i] 都从头重加。讲义：1 + 3n + n(n−1) 次赋值。

    for (i = 0; i < n; i++) {
        for (j = 1, sum = a[0]; j <= i; j++)
            sum += a[j];
        cout << ... << sum;
    }
    """
    n, cnt, out = len(a), 0, []
    i = 0; cnt += 1                     # i = 0
    while i < n:
        j = 1; s = a[0]; cnt += 2       # j = 1, sum = a[0]
        while j <= i:
            s += a[j]; cnt += 1         # sum += a[j]
            j += 1; cnt += 1            # j++
        out.append(s)
        i += 1; cnt += 1                # i++
    return out, cnt


def prefix_running(a):
    """同一个输出的另一种写法：sum 接着上一轮往下加（与 sum_array 同样 2 + 2n 次赋值）。

    for (i = sum = 0; i < n; i++) { sum += a[i]; cout << ... << sum; }
    """
    n, cnt, out = len(a), 0, []
    i = s = 0; cnt += 2
    while i < n:
        s += a[i]; cnt += 1
        out.append(s)
        i += 1; cnt += 1
    return out, cnt


def window5(a):
    """讲义第三段：嵌套循环但内层固定 4 次。全部赋值 1 + 11(n−4)，讲义只数内层的 8(n−4)。

    for (i = 4; i < n; i++)
        for (j = i - 3, sum = a[i - 4]; j <= i; j++)
            sum += a[j];
    返回 (每个窗口和, 全部赋值数, 内层赋值数)。
    """
    n, cnt, inner, out = len(a), 0, 0, []
    i = 4; cnt += 1
    while i < n:
        j = i - 3; s = a[i - 4]; cnt += 2
        while j <= i:
            s += a[j]; cnt += 1; inner += 1
            j += 1; cnt += 1; inner += 1
        out.append(s)
        i += 1; cnt += 1
    return out, cnt, inner


def naive_formula(n):
    return 1 + 3 * n + n * (n - 1)


def running_formula(n):
    return 2 + 2 * n


# ---------------------------------------------------------------- 3.1 低阶项被淹没
def f_terms(n):
    """f(n) = n² + 100n + log10(n) + 1000 各项的值。"""
    return {"n2": n * n, "100n": 100 * n, "log": math.log10(n), "1000": 1000}


def f_shares(n):
    t = f_terms(n)
    tot = sum(t.values())
    return {k: v / tot for k, v in t.items()}


BIG_C = 2       # 大 O 示意：f(n) = n² + 100n + log10 n + 1000 ≤ 2·n²


def f_total(n):
    return sum(f_terms(n).values())


def bigo_first_N(c=BIG_C):
    """最小的 N：从 N 起（查到 10⁵）都有 f(n) ≤ c·n²。"""
    ok = [f_total(n) <= c * n * n for n in range(1, 100001)]
    last_bad = max(i + 1 for i, x in enumerate(ok) if not x)
    return last_bad + 1


def omega_holds(c=1, upto=100000):
    """Ω 一侧：对所有 n ≥ 1 都有 f(n) ≥ c·n²。"""
    return all(f_total(n) >= c * n * n for n in range(1, upto + 1))


# ---------------------------------------------------------------- 3.1 Θ 的夹逼：100n² + 5n + 500 夹在 100n² 与 105n² 之间
def theta_f(n):
    return 100 * n * n + 5 * n + 500


C1, C2 = 100, 105


def theta_first_N():
    """最小的 N：对所有 n > N 都有 c1·n² ≤ f(n) ≤ c2·n²（上界一侧 5n + 500 ≤ 5n² ⇔ n² − n − 100 ≥ 0）。"""
    n = 1
    while not all(C1 * m * m <= theta_f(m) <= C2 * m * m for m in range(n + 1, n + 2000)):
        n += 1
    return n


# ---------------------------------------------------------------- 3.2 顺序检索：最佳、最差、平均
def seq_search(a, key):
    """从第一个元素起逐个比较，返回 (下标, 比较次数)。"""
    cmp = 0
    for i, x in enumerate(a):
        cmp += 1
        if x == key:
            return i, cmp
    return -1, cmp


def avg_uniform(n):
    """K 在每个位置的概率都是 1/n：逐个位置真跑一遍取平均（Fraction 精确值）。"""
    a = list(range(n))
    return Fraction(sum(seq_search(a, k)[1] for k in a), n)


def skew_probs(n):
    """讲义例：第 1 位 1/2，第 2 位 1/4，其余 n−2 个位置平分剩下的 1/4。"""
    rest = Fraction(1, 4) / (n - 2)
    return [Fraction(1, 2), Fraction(1, 4)] + [rest] * (n - 2)


def avg_skew(n):
    a = list(range(n))
    return sum(p * seq_search(a, k)[1] for p, k in zip(skew_probs(n), a))


# ---------------------------------------------------------------- 增长率表：n = 1000，每步 1 微秒
def time_at(n=1000):
    us = {"n": n, "n2": n ** 2, "n3": n ** 3}
    sec = {k: v / 1e6 for k, v in us.items()}
    two_n_years = 2 ** n / 1e6 / (365.25 * 24 * 3600)
    return sec, two_n_years


GROWTH_N = (16, 256)


def growth_row(n):
    lg = int(math.log2(n))
    return {"1": 1, "log": lg, "n": n, "nlog": n * lg, "n2": n * n, "2n": 2 ** n}


# ---------------------------------------------------------------- 3.3 时空折衷：黄页查电话
def phonebook(n=1000):
    """n 家公司。逐项比较名字：平均 (n+1)/2 次；散列索引：算一次散列直接定位，多存 n 个索引槽。

    返回 (逐项比较的平均次数 Fraction, 散列查找每次的比较次数, 额外索引槽数)。
    """
    names = [f"公司{i:04d}" for i in range(n)]
    scan = Fraction(sum(seq_search(names, x)[1] for x in names), n)
    index = {name: i for i, name in enumerate(names)}       # 额外空间：n 个槽
    hits = [1 for x in names if names[index[x]] == x]        # 每次查：一次散列 + 一次核对
    return scan, sum(hits) // n, len(index)


if __name__ == "__main__":
    for n in (10, 1000):
        a = list(range(1, n + 1))
        print(n, prefix_naive(a)[1], naive_formula(n), prefix_running(a)[1], running_formula(n))
    print(window5(list(range(10))))
    for n in (1, 10, 100, 1000):
        print(n, f_terms(n), {k: round(v, 3) for k, v in f_shares(n).items()})
    print("theta N", theta_first_N())
    print("avg", avg_uniform(8), avg_skew(8), avg_uniform(1000), avg_skew(1000))
    print(time_at())
    print([growth_row(n) for n in GROWTH_N][0])
    print(phonebook())
