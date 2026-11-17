"""分治片的数据层：讲义 4.1 快速幂、4.3 最大公约数原样 + 插桩版（调用链、乘法计数、矩形切正方形）。

讲义原样：fast_pow、gcd、lcm（W08 讲义第 4 节）。
补写（讲义没有，片中用来对比）：naive_pow（连乘）、fast_pow_twice（把 half 写成两次调用的反例）、
squares（辗转相除的几何版：长方形切正方形）。
"""
from __future__ import annotations

A, B = 2, 10                     # 二的十次方
BIG_B = 10 ** 9                  # 「指数到十亿」
MOD = 1000000007                 # 讲义 fast_pow(3, 100, 1000000007)
G12, G18 = 12, 18                # 讲义 gcd(12, 18)
L4, L6 = 4, 6                    # 讲义 lcm(4, 6)
RECT = (75, 27)                  # 几何演示的长方形（自拟）


# ------------------------------------------------------------------ 讲义原样
def fast_pow(a, b, mod=None):
    """计算 a^b（可选取模），O(log b)。"""
    if b == 0:
        return 1 % mod if mod else 1
    half = fast_pow(a, b // 2, mod)
    res = half * half
    if b & 1:
        res *= a
    return res % mod if mod else res


def gcd(a, b):
    return a if b == 0 else gcd(b, a % b)


def lcm(a, b):
    return a // gcd(a, b) * b        # 先除后乘，避免中间结果过大


# ------------------------------------------------------------------ 补写：对比用
def naive_pow(a, b):
    """连乘：从 1 开始乘 b 次 a。返回 (结果, 乘法次数)。"""
    res, cnt = 1, 0
    for _ in range(b):
        res *= a
        cnt += 1
    return res, cnt


def fast_pow_twice(a, b, cnt):
    """反例：不存 half，写成两次递归调用相乘。cnt = {"calls": 0, "mults": 0}。"""
    cnt["calls"] += 1
    if b == 0:
        return 1
    res = fast_pow_twice(a, b // 2, cnt) * fast_pow_twice(a, b // 2, cnt)
    cnt["mults"] += 1
    if b & 1:
        res *= a
        cnt["mults"] += 1
    return res


def twice_counts(a=A, b=B):
    cnt = {"calls": 0, "mults": 0}
    v = fast_pow_twice(a, b, cnt)
    return v, cnt["calls"], cnt["mults"]


# ------------------------------------------------------------------ 插桩版
def pow_trace(a=A, b=B, mod=None):
    """讲义 fast_pow 插桩：返回 (结果, 层列表)。

    层列表自顶向下，每层 dict：b、half（下一层返回值）、odd、res（本层返回值）、mults（本层乘法次数）。
    """
    levels = []

    def go(b):
        lv = {"b": b}
        levels.append(lv)
        if b == 0:
            lv.update(half=None, odd=False, res=1 % mod if mod else 1, mults=0)
            return lv["res"]
        half = go(b // 2)
        res = half * half
        m = 1
        if b & 1:
            res *= a
            m += 1
        res = res % mod if mod else res
        lv.update(half=half, odd=bool(b & 1), res=res, mults=m)
        return res
    v = go(b)
    return v, levels


def pow_mults(b):
    """讲义 fast_pow 算 a^b 的乘法次数（不计取模）。"""
    return sum(lv["mults"] for lv in pow_trace(1, b)[1])


def pow_calls(b):
    return len(pow_trace(1, b)[1])


def gcd_trace(a, b):
    """讲义 gcd 的调用链：[(a, b), ...] 直到 b == 0。"""
    out = [(a, b)]
    while b:
        a, b = b, a % b
        out.append((a, b))
    return out


def squares(w, h):
    """长方形 w×h 反复切下最大的正方形：返回 [(边长, 个数), ...]，最后一个边长就是 gcd。"""
    out = []
    while w and h:
        if w < h:
            w, h = h, w
        k = w // h
        out.append((h, k))
        w -= k * h
    return out


def square_tiles(w, h):
    """每个正方形的位置：[(x, y, 边长), ...]，长方形左下角为原点、宽 w 高 h（w ≥ h）。"""
    x0, y0, tiles = 0, 0, []
    while w and h:
        if w >= h:                    # 横着切：从左往右切下 h×h
            k = w // h
            tiles += [(x0 + t * h, y0, h) for t in range(k)]
            x0 += k * h
            w -= k * h
        else:                         # 竖着切：从下往上切下 w×w
            k = h // w
            tiles += [(x0, y0 + t * w, w) for t in range(k)]
            y0 += k * w
            h -= k * w
    return tiles


def halving(a, b):
    """辗转相除的第一个参数序列，以及「隔两步至少减半」是否处处成立（要求 a ≥ b）。"""
    firsts = [x for x, _ in gcd_trace(a, b)]
    ok = all(firsts[k + 2] <= firsts[k] / 2 for k in range(len(firsts) - 2) if firsts[k + 2])
    return firsts, ok


if __name__ == "__main__":
    print(fast_pow(2, 10), fast_pow(3, 100, MOD), pow(3, 100, MOD))
    print(gcd(G12, G18), lcm(L4, L6))
    v, lv = pow_trace()
    print(v, lv, pow_mults(B), naive_pow(A, B)[1])
    print(bin(BIG_B), BIG_B.bit_length(), bin(BIG_B).count("1"), pow_mults(BIG_B), pow_calls(BIG_B))
    print(twice_counts())
    print(gcd_trace(G12, G18), gcd_trace(*RECT), squares(*RECT), halving(*RECT))
    print(square_tiles(*RECT))
