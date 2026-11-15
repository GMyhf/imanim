"""区间贪心片的数据层：讲义 1.1–1.5 节代码原样 + 插桩记录扫描事件。

约定与课件一致（W10 P4–P11、讲义第 1 节）：合并区间按左端点、无重叠区间与引爆气球按右端点
（前者 lo >= end、后者 lo > end）、区间分组按左端点 + 小根堆；sorted 稳定，并列保持原顺序。
"""
from __future__ import annotations

import heapq

MERGE_EX = [[1, 3], [2, 6], [8, 10], [15, 18]]
MAX_PITFALL = [[1, 10], [2, 3]]
KEEP_EX = [[1, 2], [2, 3], [3, 4], [1, 3]]
ARROW_EX = [[10, 16], [2, 8], [1, 6], [7, 12]]
GROUP_EX = [(1, 4), (2, 5), (6, 8), (3, 7)]
# 「为什么按右端点」的两个反例（片中自拟，讲义只给了交换论证）
BAD_LEFT = [[1, 10], [2, 3], [4, 5]]
BAD_LEN = [[1, 5], [4, 7], [6, 10]]


def merge(intervals):
    """讲义 1.1 节原样。"""
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    out = [list(intervals[0])]
    for lo, hi in intervals[1:]:
        if lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def merge_trace(intervals=MERGE_EX):
    """返回 (排序后, 事件)。事件：("start", 区间) / ("extend", 区间, 新右端点) / ("new", 区间)。"""
    s = sorted(intervals, key=lambda x: x[0])
    out = [list(s[0])]
    ev = [("start", s[0])]
    for lo, hi in s[1:]:
        if lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
            ev.append(("extend", [lo, hi], out[-1][1]))
        else:
            out.append([lo, hi])
            ev.append(("new", [lo, hi]))
    return s, ev, out


def merge_no_max(intervals):
    """错误写法：延长时直接赋值。"""
    s = sorted(intervals, key=lambda x: x[0])
    out = [list(s[0])]
    for lo, hi in s[1:]:
        if lo <= out[-1][1]:
            out[-1][1] = hi
        else:
            out.append([lo, hi])
    return out


def erase_overlap_intervals(intervals):
    """讲义 1.2 节原样。"""
    if not intervals:
        return 0
    intervals = sorted(intervals, key=lambda x: x[1])
    keep, end = 1, intervals[0][1]
    for lo, hi in intervals[1:]:
        if lo >= end:
            keep += 1
            end = hi
    return len(intervals) - keep


def greedy_keep(intervals, key):
    """按给定键排序后的「能保留就保留」（lo >= end），返回 (排序后, 保留标记列表)。"""
    s = sorted(intervals, key=key)
    flags, end = [], -float("inf")
    for lo, hi in s:
        if lo >= end:
            flags.append(True)
            end = hi
        else:
            flags.append(False)
    return s, flags


def find_min_arrow_shots(points):
    """讲义 1.3 节原样。"""
    if not points:
        return 0
    points = sorted(points, key=lambda x: x[1])
    arrows, end = 1, points[0][1]
    for lo, hi in points[1:]:
        if lo > end:
            arrows += 1
            end = hi
    return arrows


def arrow_trace(points=ARROW_EX):
    """返回 (排序后, 每个气球被哪支箭射中的箭位置列表, 箭位置列表)。"""
    s = sorted(points, key=lambda x: x[1])
    shots = [s[0][1]]
    hit = [s[0][1]]
    for lo, hi in s[1:]:
        if lo > shots[-1]:
            shots.append(hi)
        hit.append(shots[-1])
    return s, hit, shots


def min_groups(intervals):
    """讲义 1.5 节堆做法原样。"""
    intervals = sorted(intervals, key=lambda x: x[0])
    heap = []
    for lo, hi in intervals:
        if heap and heap[0] < lo:
            heapq.heapreplace(heap, hi)
        else:
            heapq.heappush(heap, hi)
    return len(heap)


def min_groups_diff(intervals):
    """讲义 1.5 节差分做法原样。"""
    events = []
    for lo, hi in intervals:
        events.append((lo, 1))
        events.append((hi + 1, -1))
    events.sort()
    cur = best = 0
    for _, delta in events:
        cur += delta
        best = max(best, cur)
    return best


def group_trace(intervals=GROUP_EX):
    """堆做法插桩：堆里存 (右端点, 组号)，决策与讲义只存右端点完全相同（只比较 heap[0] 的右端点）。

    返回 (排序后, 每个区间分到的组号, 每步之后堆里的右端点列表)。
    """
    s = sorted(intervals, key=lambda x: x[0])
    heap, lanes, states = [], [], []
    for lo, hi in s:
        if heap and heap[0][0] < lo:
            _, g = heap[0]
            heapq.heapreplace(heap, (hi, g))
        else:
            g = len(heap)
            heapq.heappush(heap, (hi, g))
        lanes.append(g)
        states.append(sorted(h for h, _ in heap))
    return s, lanes, states


def overlap_profile(intervals=GROUP_EX):
    """差分扫描：返回 [(位置, 该位置起同时开着的区间数)]，闭区间在 hi + 1 处释放。"""
    events = []
    for lo, hi in intervals:
        events.append((lo, 1))
        events.append((hi + 1, -1))
    events.sort()
    out, cur = [], 0
    for i, (x, d) in enumerate(events):
        cur += d
        if i + 1 == len(events) or events[i + 1][0] != x:
            out.append((x, cur))
    return out
