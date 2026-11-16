"""浮点数片的数据层：讲义 W03 4.4 节「浮点数与精度陷阱」的代码原样搬来，片中每个数字都从这里算。

依据：计算概论（B）2026fall 第 3 周 计算机原理 4.4 节（float_bits、0.1 的二进制展开、0.1 + 0.2、
2⁵³、math.isqrt）与第 4 周 讲义「浮点开方偏 1」。全部用 struct / fractions / decimal 精确计算，
不手抄任何一位。
"""
from __future__ import annotations

import math
import struct
from decimal import Decimal
from fractions import Fraction

BIAS = 1023                       # 双精度指数偏移量
NSIGN, NEXP, NMANT = 1, 11, 52


def float_bits(x):
    """讲义原样：返回双精度浮点数 x 的 (符号, 指数, 尾数) 三段位串。"""
    b = format(struct.unpack('>Q', struct.pack('>d', x))[0], '064b')
    return b[0], b[1:12], b[12:]


def decode(x):
    """拆位后按 (-1)^S × 1.尾数 × 2^(指数-1023) 还原，返回 (S, 存储指数, 真实指数, 尾数位串, 还原值 Fraction)。"""
    s, e, m = float_bits(x)
    E = int(e, 2)
    val = (-1) ** int(s) * (1 + Fraction(int(m, 2), 2 ** NMANT)) * Fraction(2) ** (E - BIAS)
    return int(s), E, E - BIAS, m, val


# ---------------------------------------------------------------- 规范化：讲义例 +1000111.0101
NORM_BITS = "1000111.0101"
NORM_SHIFT = NORM_BITS.index(".") - 1                     # 小数点左移 6 位
NORM_MANT = NORM_BITS.replace(".", "")[1:]                 # 0001110101


def normalize_value():
    ip, fp = NORM_BITS.split(".")
    return Fraction(int(ip + fp, 2), 2 ** len(fp))


# ---------------------------------------------------------------- 例：-6.5
EX = -6.5
EX_BIN = "110.1"                                          # 6.5 = 110.1₂ = 1.101₂ × 2²


def doubling_steps(frac=Fraction(1, 10), n=8):
    """十进制小数反复乘二取整数部分：返回 [(乘二后的值, 取出的位, 剩下的小数)]，前 n 步。"""
    out, x = [], frac
    for _ in range(n):
        y = x * 2
        d = int(y)
        out.append((y, d, y - d))
        x = y - d
    return out


def cycle_start(frac=Fraction(1, 10), limit=64):
    """返回 (循环开始的步号, 循环节长度)：小数部分第一次重复出现的位置。"""
    seen, x = {}, frac
    for i in range(limit):
        if x in seen:
            return seen[x], i - seen[x]
        seen[x] = i
        x = x * 2 - int(x * 2)
    raise ValueError("没找到循环")


def binary_expansion(frac=Fraction(1, 10), n=20):
    return "".join(str(d) for _, d, _ in doubling_steps(frac, n))


TENTH_HEX = (0.1).hex()                                   # 0x1.999999999999ap-4
TENTH_20 = f"{0.1:.20f}"                                  # 0.10000000000000000555
TENTH_DECIMAL = str(Decimal(0.1))                          # 存进去的真实值


def stored_error(x_text):
    """十进制字面量 x_text 存成 double 之后比原数大多少（精确有理数差）。"""
    return Fraction(float(x_text)) - Fraction(Decimal(x_text))


# ---------------------------------------------------------------- 0.1 + 0.2 落在哪一格
SUM = 0.1 + 0.2
SUM_REPR = repr(SUM)                                     # 0.30000000000000004
SUM_EQ = SUM == 0.3                                       # False
ULP_03 = math.ulp(0.3)                                    # 相邻两格间距 2^-54
LOWER, UPPER = 0.3, math.nextafter(0.3, 1.0)              # 0.3 存的那一格、右边紧挨的一格
EXACT_SUM = Fraction(0.1) + Fraction(0.2)                 # 两个近似值的精确和


def sum_is_tie():
    """精确和是否恰好落在两格正中间。"""
    return EXACT_SUM == (Fraction(LOWER) + Fraction(UPPER)) / 2


def is_even(x):
    """尾数最低位是否为 0（就近取偶里的「偶」）。"""
    return float_bits(x)[2][-1] == "0"


# ---------------------------------------------------------------- 2^53 与大整数开方
P53 = 2 ** 53
P53_COLLIDE = float(P53 + 1) == float(P53)                 # True
GAP_AT_P53 = math.ulp(float(P53))                         # 2.0
SQ_R = 10 ** 8 + 7
SQ_X = SQ_R * SQ_R - 1
SQ_FLOAT = int(SQ_X ** 0.5)                               # 100000007，多了 1
SQ_EXACT = math.isqrt(SQ_X)                               # 100000006


# ---------------------------------------------------------------- 正确比较
ISCLOSE = math.isclose(0.1 + 0.2, 0.3)                    # True
ABS_EPS = abs((0.1 + 0.2) - 0.3) < 1e-9                    # True
DEC_SUM = str(Decimal('0.1') + Decimal('0.2'))             # '0.3'
HALF_QUARTER = 0.5 + 0.25 == 0.75                         # True：k/2ⁿ 能精确表示
