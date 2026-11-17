"""购物片的数据层：覆盖连续金额的贪心（OpenJudge M29896，2025-11-06 模拟机考第五题）。

讲义原样（W10–11 讲义「6 覆盖连续区间 · M29896:购物」两版 + W16 讲义第 5 节 T5 一版）：
solve_scan / solve_bisect / solve_w16 三个函数体照抄讲义，只把顶层脚本包进函数，经 run_io 喂样例、收输出。
*_trace / brute_* / duel 是补写的：交出中间量给画面用，以及暴力枚举对拍（test_shopping 再用另一套独立实现对撞）。
"""
from __future__ import annotations

import contextlib
import io
import itertools
import random
import sys

SAMPLE_IN = "20 4\n1 2 5 10\n"                # 题面样例
SAMPLE_OUT = "5"
X, COINS = 20, [1, 2, 5, 10]
ALT = [1, 1, 2, 5, 10]                       # 对照：也每枚都不断档，但第二枚没挑最大的
NO_ONE = (20, [2, 5, 10])                    # 无解：没有面值一
DUEL_SEED, DUEL_N = 2025, 1000               # 随机对拍：组数


# ---------------------------------------------------------------- 讲义原样
def solve_scan():
    import sys
    input = sys.stdin.read
    data = input().split()

    X = int(data[0])
    N = int(data[1])
    coins = list(map(int, data[2:2+N]))

    # 去除大于 X 的硬币（无用）
    coins = [c for c in coins if c <= X]
    if not coins:
        if X == 0:
            return 0
        else:
            return -1

    # 排序
    coins.sort()

    # 必须要有 1，否则无法覆盖 1
    if coins[0] > 1:
        return -1

    max_reach = 0  # 当前能覆盖 [1, max_reach]
    count = 0      # 使用的硬币数量

    while max_reach < X:
        # 选择满足 coin <= max_reach + 1 的最大面值硬币
        candidate = -1
        for coin in coins:
            if coin <= max_reach + 1:
                candidate = coin
            else:
                break  # 因为已排序，后面的更大

        if candidate == -1:
            return -1  # 无法扩展

        max_reach += candidate
        count += 1

        if max_reach >= X:
            break

    return count


def solve_bisect():
    import bisect
    X, N = map(int, input().split())
    coins = list(map(int, input().split()))
    coins.sort()

    # 如果最小面值 > 1，无法凑出 1
    if coins[0] > 1:
        print(-1)
        return

    reach = 0
    ans = 0

    # 可以重复使用同一个面值多次，所以不移除
    while reach < X:
        target = reach + 1
        # 找 coins 中最大且 <= target
        idx = bisect.bisect_right(coins, target) - 1
        if idx < 0:
            print(-1)
            return
        c = coins[idx]
        reach += c
        ans += 1

    print(ans)


def solve_w16():
    X, n = map(int, input().split())
    coins = sorted(map(int, input().split()))
    reach = count = 0
    while reach < X:
        usable = [c for c in coins if c <= reach + 1]
        if not usable:
            print(-1); break
        reach += max(usable); count += 1
    else:
        print(count)


W16_CODE = """X, n = map(int, input().split())
coins = sorted(map(int, input().split()))
reach = count = 0
while reach < X:
    usable = [c for c in coins if c <= reach + 1]
    if not usable:
        print(-1); break
    reach += max(usable); count += 1
else:
    print(count)"""


def run_io(fn, text: str) -> str:
    """把 text 当标准输入喂给讲义函数；返回值或打印的内容（去空白）作为输出。"""
    old_in = sys.stdin
    sys.stdin = io.StringIO(text)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ret = fn()
    finally:
        sys.stdin = old_in
    out = buf.getvalue().strip()
    return out if out else str(ret)


def fmt_in(x, coins) -> str:
    return f"{x} {len(coins)}\n{' '.join(map(str, coins))}\n"


# ---------------------------------------------------------------- 画面用：交出中间量
def greedy_trace(x, coins):
    """与 solve_w16 逐行同逻辑，记录每一步 (带之前的 reach, 可用面值, 选中的面值, 带之后的 reach)。无解返回 None。"""
    coins = sorted(coins)
    reach, out = 0, []
    while reach < x:
        usable = [c for c in coins if c <= reach + 1]
        if not usable:
            return None
        c = max(usable)
        out.append((reach, usable, c, reach + c))
        reach += c
    return out


def prefix_reach(seq):
    """一串硬币依次带上后，每一步的 reach（前缀和）；某一枚断档（大于 reach+1）时返回到断档前为止。"""
    reach, out = 0, []
    for c in seq:
        if c > reach + 1:
            break
        reach += c
        out.append(reach)
    return out


def subset_sums(bag):
    """一袋硬币（每枚至多用一次）能凑出的全部金额，含 0。"""
    s = {0}
    for c in bag:
        s |= {v + c for v in s}
    return s


def covers(bag, x) -> bool:
    return set(range(1, x + 1)) <= subset_sums(bag)


def brute_count(x, coins, k):
    """暴力：k 枚硬币的全部多重组合里，(总数, 能覆盖 1..x 的个数)。"""
    combos = list(itertools.combinations_with_replacement(sorted(coins), k))
    return len(combos), sum(covers(b, x) for b in combos)


def brute_min(x, coins, kmax=None):
    """暴力：从 k = 1 起枚举 k 枚硬币的所有多重组合，第一个能覆盖 1..x 的 k；没有面值一则 -1。"""
    if 1 not in coins:
        return -1
    for k in range(1, (kmax or x) + 1):
        if brute_count(x, coins, k)[1]:
            return k
    return -1


def duel(seed=DUEL_SEED, n=DUEL_N):
    """随机对拍：X ≤ 25、两到四种面值（八成的组里含一），讲义 W16 版与暴力比。返回 (组数, 一致组数, 无解组数)。"""
    rnd = random.Random(seed)
    same = none = 0
    for _ in range(n):
        x = rnd.randint(1, 25)
        coins = rnd.sample(range(2, 13), rnd.randint(1, 3))
        if rnd.random() < 0.8:
            coins.append(1)
        rnd.shuffle(coins)
        got = int(run_io(solve_w16, fmt_in(x, coins)))
        want = brute_min(x, coins)
        same += got == want
        none += want == -1
    return n, same, none
