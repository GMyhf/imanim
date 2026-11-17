"""双重回文精讲片的数据层：讲义 Python 参考代码复用 novdata.solve_t1（原样），这里只补插桩。

讲义：2026fall courseware/202611_ADS_November_Exam_Review.md 第 3 节 T1（E31529）。
- pal_trace：与讲义 C++ 版 pal(x, base) 逐行同逻辑，交出每一步的 t、余数、y；
- solve_t1_nostrip：讲义 Python 版只删掉 bin(i) 后面的 [2:]，演示「忘了切 0b 前缀」跑出的错误输出；
- scan_table / odd_dec_pals 等：样例逐个检查的表格数据。
test_novpal.py 用字符串翻转暴力与 int(s, base) 逐位重建独立对撞。
"""
from __future__ import annotations

import novdata as N

SOLVE = N.solve_t1
run_io = N.run_io
SAMPLES = N.SAMPLES["t1"]                         # [("5\n", "3 5"), ("100\n", "7 99")]
BIG = N.T1_BIG                                     # (10**6, 19, 585585)

PY_CODE = [                                        # 讲义 Python 版（与 novdata.solve_t1 同文）
    "n = int(input())",
    "cnt, best = 0, 1",
    "for i in range(1, n + 1, 2):  # 偶数二进制末位是 0",
    "    d, b = str(i), bin(i)[2:]",
    "    if d == d[::-1] and b == b[::-1]:",
    "        cnt += 1",
    "        best = i",
    "print(cnt, best)",
]
CPP_PAL = [                                        # 讲义 C++ 版的 pal
    "bool pal(int x, int base) {  // 把 x 按 base 进制倒过来",
    "    int y = 0;",
    "    for (int t = x; t > 0; t /= base)",
    "        y = y * base + t % base;",
    "    return y == x;",
    "}",
]


def solve_t1_nostrip():
    """错误写法：bin(i) 忘了切掉 '0b' 前缀，其余与讲义一字不差。"""
    n = int(input())
    cnt, best = 0, 1
    for i in range(1, n + 1, 2):
        d, b = str(i), bin(i)
        if d == d[::-1] and b == b[::-1]:
            cnt += 1
            best = i
    print(cnt, best)


def pal_trace(x: int, base: int) -> list[tuple[int, int, int]]:
    """讲义 C++ pal 的逐步轨迹：每步 (循环开始时的 t, t % base, 更新后的 y)。"""
    steps, y, t = [], 0, x
    while t > 0:
        y = y * base + t % base
        steps.append((t, t % base, y))
        t //= base
    return steps


def pal(x: int, base: int) -> bool:
    st = pal_trace(x, base)
    return (st[-1][2] if st else 0) == x


def binstr(i: int) -> str:
    return bin(i)[2:]


def scan_table(n: int) -> list[tuple[int, str, bool, bool]]:
    """1..n 逐个：(i, 二进制, 十进制回文?, 二进制回文?)。"""
    return [(i, binstr(i), pal(i, 10), pal(i, 2)) for i in range(1, n + 1)]


def double_pals(n: int) -> list[int]:
    """与讲义 Python 版同一循环（只枚举奇数），交出全部双重回文。"""
    out = []
    for i in range(1, n + 1, 2):
        d, b = str(i), bin(i)[2:]
        if d == d[::-1] and b == b[::-1]:
            out.append(i)
    return out


def dec_pals(n: int) -> list[int]:
    return [i for i in range(1, n + 1) if pal(i, 10)]


def char_total(n: int) -> int:
    """只枚举奇数时，十进制与二进制字符串的总长。"""
    return sum(len(str(i)) + len(binstr(i)) for i in range(1, n + 1, 2))


EX_TITLE = 585                                     # 片头举例：585 = 1001001001₂
EX_EVEN = [6, 10]                                  # 偶数举例
EX_YES, EX_NO, EX_DEC = 33, 37, 585585             # pal 逐步演示：二进制回文 / 不是 / 十进制
