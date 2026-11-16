"""分配排序片的数据：讲义代码原样 + 插桩轨迹。画面和旁白里的每个数字都从这里来。

出处：2026fall-cs201 讲义 202611_DSA_08_sorting_algorithms.md 第 7 节（7.1 计数排序简单版与稳定版、
7.3 基数排序分桶写法与计数写法、逐趟结果表），10.3 节（比较排序的下界：判定树）。
"""
from __future__ import annotations

import math
from itertools import permutations


# ---------------------------------------------------------------- 讲义原样（7.1 计数排序）
def counting_sort(arr):
    if not arr:
        return arr
    min_value, max_value = min(arr), max(arr)
    count = [0] * (max_value - min_value + 1)   # 用 min_value 做偏移，支持负数
    for num in arr:
        count[num - min_value] += 1
    sorted_arr = []
    for i, c in enumerate(count):
        sorted_arr.extend([i + min_value] * c)
    return sorted_arr


def counting_sort_stable(arr, key=lambda x: x):
    if not arr:
        return arr
    keys = [key(x) for x in arr]
    lo = min(keys)
    count = [0] * (max(keys) - lo + 1)
    for k in keys:
        count[k - lo] += 1
    for i in range(1, len(count)):          # 前缀和：count[i] = 键 <= i+lo 的元素个数
        count[i] += count[i - 1]
    output = [None] * len(arr)
    for x, k in zip(reversed(arr), reversed(keys)):   # 从后往前，保证稳定
        count[k - lo] -= 1
        output[count[k - lo]] = x
    return output


# ---------------------------------------------------------------- 讲义原样（7.3 基数排序）
def radix_sort(arr):
    # 只适用于非负整数；有负数时见下面的 radix_sort_signed
    if not arr:
        return arr
    digits = len(str(max(arr)))             # 最大值的位数 = 趟数
    for i in range(digits):
        buckets = [[] for _ in range(10)]
        for num in arr:
            buckets[num // 10 ** i % 10].append(num)    # 按第 i 位分配（入桶保持原次序）
        arr = [num for bucket in buckets for num in bucket]   # 按桶号收集
    return arr


def counting_sort_by_digit(arr, exp):
    # 按 exp 所在的那一位（exp = 1 个位、10 十位、100 百位……）做一次稳定的计数排序
    count = [0] * 10
    for x in arr:
        count[x // exp % 10] += 1
    for d in range(1, 10):                  # 前缀和：count[d] = 该位 <= d 的元素个数
        count[d] += count[d - 1]
    output = [0] * len(arr)
    for x in reversed(arr):                 # 从后往前放，保证稳定
        d = x // exp % 10
        count[d] -= 1
        output[count[d]] = x
    return output


def radix_sort_counting(arr):
    if not arr:
        return arr
    max_val = max(arr)
    exp = 1
    while max_val // exp > 0:               # 从个位开始，逐位稳定排序
        arr = counting_sort_by_digit(arr, exp)
        exp *= 10
    return arr


# ---------------------------------------------------------------- 片中用到的例子（都取自讲义）
COUNT_DATA = [6, 5, 18, 2, 16, 15, 19, 13, 10, 12, 7, 9, 4, 4, 8, 1, 11, 14, 3, 20, 17, 10]   # 7.1 主例
RECORDS = [(3, 'a'), (1, 'b'), (3, 'c'), (1, 'd')]                                          # 7.1 稳定版例
RADIX_DATA = [170, 45, 75, 90, 802, 24, 2, 66]                                              # 7.3 主例
LECTURE_PASSES = [                                                                          # 7.3 逐趟结果表
    [170, 45, 75, 90, 802, 24, 2, 66],
    [170, 90, 802, 2, 24, 45, 75, 66],
    [802, 2, 24, 45, 66, 170, 75, 90],
    [2, 24, 45, 66, 75, 90, 170, 802]]


# ---------------------------------------------------------------- 插桩
def radix_passes(arr):
    """radix_sort 每一趟：[(位号 i, 各桶内容 buckets, 收集结果)]。"""
    out = []
    digits = len(str(max(arr)))
    for i in range(digits):
        buckets = [[] for _ in range(10)]
        for num in arr:
            buckets[num // 10 ** i % 10].append(num)
        arr = [num for bucket in buckets for num in bucket]
        out.append((i, [list(b) for b in buckets], list(arr)))
    return out


def radix_passes_lifo(arr):
    """反例：每个桶改成「后进先出」收集（不稳定），其余不变。返回每趟收集结果。"""
    out = []
    digits = len(str(max(arr)))
    for i in range(digits):
        buckets = [[] for _ in range(10)]
        for num in arr:
            buckets[num // 10 ** i % 10].append(num)
        arr = [num for bucket in buckets for num in reversed(bucket)]
        out.append(list(arr))
    return out


def stable_trace(arr=RECORDS, key=lambda t: t[0]):
    """counting_sort_stable 的过程：计数、前缀和、从后往前的每一次放置 [(记录, 键, 放到的下标)]。"""
    keys = [key(x) for x in arr]
    lo = min(keys)
    count = [0] * (max(keys) - lo + 1)
    for k in keys:
        count[k - lo] += 1
    counts = list(count)
    for i in range(1, len(count)):
        count[i] += count[i - 1]
    prefix = list(count)
    output = [None] * len(arr)
    places = []
    for x, k in zip(reversed(arr), reversed(keys)):
        count[k - lo] -= 1
        output[count[k - lo]] = x
        places.append((x, k, count[k - lo]))
    return {"lo": lo, "counts": counts, "prefix": prefix, "places": places, "output": output}


def lower_bound(n: int) -> int:
    """判定树：n! 片叶子的二叉树至少高 ceil(log2 n!)，即最坏至少比较这么多次。"""
    return math.ceil(math.log2(math.factorial(n)))


def decision_tree3():
    """三个数 a,b,c 的一棵判定树（插入排序的比较顺序）：返回 [(路径上的比较结果, 输出排列)]，共 3! 片叶子。"""
    leaves = []
    for perm in permutations("abc"):
        rank = {ch: r for r, ch in enumerate(perm)}       # perm 是从小到大的次序
        path = [("a<b", rank["a"] < rank["b"])]
        if rank["a"] < rank["b"]:
            path.append(("b<c", rank["b"] < rank["c"]))
            if not rank["b"] < rank["c"]:
                path.append(("a<c", rank["a"] < rank["c"]))
        else:
            path.append(("a<c", rank["a"] < rank["c"]))
            if not rank["a"] < rank["c"]:
                path.append(("b<c", rank["b"] < rank["c"]))
        leaves.append((path, "".join(perm)))
    return leaves


def radix_ops(n: int, d: int, b: int = 10) -> int:
    """d 趟、每趟分配 n 个数、收集 b 个桶：d(n+b)。"""
    return d * (n + b)


if __name__ == "__main__":
    print(counting_sort(COUNT_DATA))
    print(stable_trace())
    for p in radix_passes(RADIX_DATA):
        print(p)
    print(radix_passes_lifo(RADIX_DATA))
    print(lower_bound(3), lower_bound(8), math.factorial(8), math.log2(math.factorial(8)))
    print(decision_tree3())
    print(radix_ops(8, 3), radix_ops(10**6, 4, 256))
