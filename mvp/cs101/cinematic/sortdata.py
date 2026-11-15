"""排序片的数据层：讲义排序代码原样插桩，记录比较 / 交换 / 挪动 / 合并事件。

约定与课件一致（W06 P26–P34、讲义 2.1–2.3）：冒泡带 swapped 提前退出；插入只在严格大于时挪动；
归并 left[i] <= right[j] 先取左边（稳定）；count_inversions 在 else 分支 cnt += len(left) - i。
"""
from __future__ import annotations

from math import log2

DATA = [5, 2, 8, 1, 7, 3, 6, 4]


def bubble_sort(a):
    """讲义原样。"""
    a = a[:]
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


def bubble_trace(a):
    """事件：("cmp", j, swap?) / ("pass", i, swapped)；同讲义循环结构。"""
    a = a[:]
    n, ev = len(a), []
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            sw = a[j] > a[j + 1]
            ev.append(("cmp", j, sw))
            if sw:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        ev.append(("pass", i, swapped))
        if not swapped:
            break
    return ev, a


def insertion_sort(a):
    """讲义原样。"""
    a = a[:]
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a


def insertion_trace(a):
    """事件：("lift", i) / ("shift", j)（a[j] 挪到 j+1）/ ("place", pos)。"""
    a = a[:]
    ev = []
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        ev.append(("lift", i))
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            ev.append(("shift", j))
            j -= 1
        a[j + 1] = key
        ev.append(("place", j + 1))
    return ev, a


def merge_sort(a):
    """讲义原样。"""
    if len(a) <= 1:
        return a[:]
    mid = len(a) // 2
    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def merge_levels(a):
    """归并的「分」与「合」按层记录。

    返回 (splits, merges)：splits[d] 是第 d 层的分段 [(lo, hi)]；
    merges 是自底向上的合并列表 [(lo, mid, hi, takes)]，takes 为依次取出的 ("L"/"R", 值)。
    """
    splits, merges = {}, []

    def go(lo, hi, d):
        splits.setdefault(d, []).append((lo, hi))
        seg = a[lo:hi]
        if hi - lo <= 1:
            return seg[:]
        mid = (lo + hi) // 2
        left, right = go(lo, mid, d + 1), go(mid, hi, d + 1)
        out, i, j, takes = [], 0, 0, []
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                out.append(left[i]); takes.append(("L", left[i])); i += 1
            else:
                out.append(right[j]); takes.append(("R", right[j])); j += 1
        takes += [("L", x) for x in left[i:]] + [("R", x) for x in right[j:]]
        out.extend(left[i:]); out.extend(right[j:])
        merges.append((lo, mid, hi, takes, d))
        return out
    go(0, len(a), 0)
    return splits, merges


def quick_sort(a):
    """讲义原样。"""
    if len(a) <= 1:
        return a[:]
    pivot = a[len(a) // 2]
    less = [x for x in a if x < pivot]
    equal = [x for x in a if x == pivot]
    greater = [x for x in a if x > pivot]
    return quick_sort(less) + equal + quick_sort(greater)


def count_inversions(a):
    """讲义原样。"""
    if len(a) <= 1:
        return a[:], 0
    mid = len(a) // 2
    left, x = count_inversions(a[:mid])
    right, y = count_inversions(a[mid:])
    out, i, j, cnt = [], 0, 0, x + y
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
            cnt += len(left) - i
    out.extend(left[i:]); out.extend(right[j:])
    return out, cnt


# 演示「一次加一批」：左右两半各自已有序，只看最顶层这一次合并
INV_LEFT, INV_RIGHT = [2, 5, 7], [1, 3, 6]


def merge_count_trace(left, right):
    """顶层合并的插桩：事件 ("L", i, j, 0) / ("R", i, j, 本次加的数)，返回 (事件, 跨两半的逆序对数)。"""
    i = j = cnt = 0
    ev = []
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            ev.append(("L", i, j, 0)); i += 1
        else:
            add = len(left) - i
            ev.append(("R", i, j, add)); cnt += add; j += 1
    return ev, cnt


def brute_inversions(a):
    return sum(1 for i in range(len(a)) for k in range(i + 1, len(a)) if a[i] > a[k])


# 稳定性：讲义 2.1 节两次排序的例子
ROWS = [("a", 2), ("b", 1), ("c", 2)]


def two_pass(rows):
    r = rows[:]
    r.sort(key=lambda t: t[0])
    first = r[:]
    r.sort(key=lambda t: t[1])
    return first, r


def growth(n):
    return n * n, n * log2(n)
