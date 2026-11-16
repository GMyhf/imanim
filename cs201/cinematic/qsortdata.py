"""快速排序片的数据：讲义（2026fall 第 8 章 5.2 节）「成对交换」分割 partition_pair 原样，另附插桩版。

画面里的每次指针移动、交换、递归区间，旁白里的比较次数，都从这里来；test_qsort.py 对撞
讲义原版输出、sorted()、暴力数比较次数。
"""
from __future__ import annotations

import random
import sys


# ---------------------------------------------------------------- 讲义原样
def partition_pair(arr, lo, hi):            # ① 成对交换，首元素当基准
    pivot = arr[lo]
    left, right = lo + 1, hi
    while True:
        while left <= right and arr[left] <= pivot:
            left += 1                       # 找第一个 > pivot 的
        while left <= right and arr[right] >= pivot:
            right -= 1                      # 找第一个 < pivot 的
        if left > right:                    # 指针交错：扫描结束
            break
        arr[left], arr[right] = arr[right], arr[left]
    arr[lo], arr[right] = arr[right], arr[lo]   # 基准归位
    return right


def partition_lomuto(arr, lo, hi):          # ② Lomuto，末元素当基准
    pivot = arr[hi]
    boundary = lo                           # [lo, boundary) 都 < pivot
    for i in range(lo, hi):                 # [boundary, i) 都 >= pivot
        if arr[i] < pivot:
            arr[boundary], arr[i] = arr[i], arr[boundary]
            boundary += 1
    arr[boundary], arr[hi] = arr[hi], arr[boundary]
    return boundary


def quick_sort(arr, partition=partition_lomuto, lo=0, hi=None):
    if hi is None:
        hi = len(arr) - 1
    if lo < hi:
        p = partition(arr, lo, hi)
        quick_sort(arr, partition, lo, p - 1)
        quick_sort(arr, partition, p + 1, hi)
    return arr


LECTURE_DATA = [6, 5, 18, 2, 16, 15, 19, 13, 10, 12, 7, 9, 4, 4, 8, 1, 11, 14, 3, 20, 17, 10]

# 片中主例：九个数，首元素 5 恰好是中位数，一次分割演示两次交换 + 基准归位
DATA = [5, 9, 2, 7, 1, 8, 3, 6, 4]


# ---------------------------------------------------------------- 插桩版（逻辑与 partition_pair 逐行相同）
def partition_trace(arr, lo, hi, ev, cnt):
    """事件：("L", 位置)、("R", 位置) 指针停下；("swap", i, j)；("place", lo, right)。cnt[0] 记比较次数。"""
    pivot = arr[lo]
    left, right = lo + 1, hi
    while True:
        while left <= right and _le(arr[left], pivot, cnt):
            left += 1
        ev.append(("L", left))
        while left <= right and _ge(arr[right], pivot, cnt):
            right -= 1
        ev.append(("R", right))
        if left > right:
            break
        arr[left], arr[right] = arr[right], arr[left]
        ev.append(("swap", left, right))
    arr[lo], arr[right] = arr[right], arr[lo]
    ev.append(("place", lo, right))
    return right


def _le(a, b, cnt):
    cnt[0] += 1
    return a <= b


def _ge(a, b, cnt):
    cnt[0] += 1
    return a >= b


def partition_events(data=DATA):
    arr = list(data)
    ev, cnt = [], [0]
    p = partition_trace(arr, 0, len(arr) - 1, ev, cnt)
    return arr, p, ev, cnt[0]


def sort_trace(data, pivot_rule="first", seed=0):
    """整趟快排（非递归展开、先左后右，与递归次序相同）。

    pivot_rule="random"：先随机挑一个位置和 lo 交换，再照常用首元素分割（随机基准）。
    返回 (排好的数组, 递归结点列表[(lo, hi, p, depth)], 比较次数, 最大深度)。
    """
    arr, rng, cnt, nodes = list(data), random.Random(seed), [0], []
    stack = [(0, len(arr) - 1, 0)]
    while stack:
        lo, hi, d = stack.pop()
        if lo < hi:
            if pivot_rule == "random":
                k = rng.randint(lo, hi)
                arr[lo], arr[k] = arr[k], arr[lo]
            p = partition_trace(arr, lo, hi, [], cnt)
            nodes.append((lo, hi, p, d))
            stack.append((p + 1, hi, d + 1))
            stack.append((lo, p - 1, d + 1))
        elif lo == hi:
            nodes.append((lo, hi, lo, d))
    depth = max(d for *_, d in nodes) + 1 if nodes else 0
    return arr, nodes, cnt[0], depth


def full_trace(data, pivot_rule="first", seed=0):
    """逐个递归结点的完整轨迹（画面用）：[(lo, hi, p, depth, pre_swap, events)]，先序次序。

    pre_swap：随机基准时换到 lo 的那个位置（None 表示没换）；events：partition_trace 的事件；
    lo == hi 的单元素段也记一个结点（p = lo，events 为空），它同样「落地」。
    """
    arr, rng, out = list(data), random.Random(seed), []
    stack = [(0, len(arr) - 1, 0)]
    while stack:
        lo, hi, d = stack.pop()
        if lo < hi:
            k = None
            if pivot_rule == "random":
                k = rng.randint(lo, hi)
                arr[lo], arr[k] = arr[k], arr[lo]
            ev = []
            p = partition_trace(arr, lo, hi, ev, [0])
            out.append((lo, hi, p, d, k, ev))
            stack.append((p + 1, hi, d + 1))
            stack.append((lo, p - 1, d + 1))
        elif lo == hi:
            out.append((lo, hi, lo, d, None, []))
    return arr, out


def parents(nodes):
    """先序结点列表 → 每个结点的父结点下标（深度比它小一的最近前驱）。"""
    par, last = [], {}
    for i, (*_, d) in enumerate((n[0], n[1], n[2], n[3]) for n in nodes):
        par.append(last.get(d - 1))
        last[d] = i
    return par


MERGE_DEMO = [5, 9, 2, 7, 1, 8, 3, 6]
RANDOM_DEMO_SEED = 1      # 有序九个数用随机基准：这个种子下树高 4


def tree_of(data=DATA):
    """递归树：结点 = 基准值，(值, 深度, 左右序号) —— 与把数据依次插入二叉搜索树同构。"""
    arr, nodes, _, _ = sort_trace(data)
    return [(arr[p], d, p) for lo, hi, p, d in nodes]


def recursion_limit_hit(n=1000):
    """讲义原话：首元素当基准，1000 个有序元素就抛 RecursionError（默认上限约 1000）。"""
    try:
        quick_sort(list(range(n)), partition_pair)
    except RecursionError:
        return True
    return False


# 旁白里的规模对比：一千个数，已经有序
BIG_N = 1000


def big_counts():
    asc = list(range(BIG_N))
    _, _, fixed, depth_fixed = sort_trace(asc, "first")
    _, _, rnd, depth_rnd = sort_trace(asc, "random", seed=2026)
    return {"fixed": fixed, "fixed_depth": depth_fixed, "random": rnd, "random_depth": depth_rnd}


if __name__ == "__main__":
    print(partition_events())
    print(tree_of())
    print(sort_trace(list(range(1, 10))))
    print(big_counts(), sys.getrecursionlimit(), recursion_limit_hit())
