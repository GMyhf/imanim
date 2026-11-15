"""二分答案片的数据层：讲义两道例题原样插桩，记录每轮 lo/hi/mid/判定 与判定函数的贪心过程。

约定与课件一致（W12 P23–P26、讲义第 5 节）：河中跳房子求最大可行值（lo = mid，上取整），
月度开销求最小可行值（hi = mid，下取整）。
"""
from __future__ import annotations

RIVER = (25, 2, [2, 11, 14, 17, 21])                 # 河宽 L、最多移走 m、石头位置
COSTS, M_GROUPS = [100, 400, 300, 100, 500, 101, 400], 5


def river_feasible_log(gap, L=RIVER[0], m=RIVER[1], rocks=RIVER[2]):
    """讲义 feasible(gap) 插桩：返回 (可行?, [(石头, 'keep'|'rm', 与上一块保留石头的距离)])。"""
    stones = sorted(rocks) + [L]
    removed, last, log = 0, 0, []
    for s in stones:
        if s - last < gap:
            removed += 1
            log.append((s, "rm", s - last))
            if removed > m:
                return False, log
        else:
            log.append((s, "keep", s - last))
            last = s
    return True, log


def river_rounds(L=RIVER[0], m=RIVER[1], rocks=RIVER[2]):
    """讲义 river_hopscotch 插桩：返回 (答案, [(lo, hi, mid, 可行?)])。"""
    lo, hi, rounds = 0, L, []
    while lo < hi:
        mid = (lo + hi + 1) // 2
        ok = river_feasible_log(mid, L, m, rocks)[0]
        rounds.append((lo, hi, mid, ok))
        if ok:
            lo = mid
        else:
            hi = mid - 1
    return lo, rounds


def floor_mid_loop(lo, hi, steps=4, L=RIVER[0], m=RIVER[1], rocks=RIVER[2]):
    """错误写法 mid = (lo + hi) // 2 且 lo = mid：走 steps 轮，记录区间（会原地打转）。"""
    trail = []
    for _ in range(steps):
        if lo >= hi:
            break
        mid = (lo + hi) // 2
        ok = river_feasible_log(mid, L, m, rocks)[0]
        trail.append((lo, hi, mid, ok))
        if ok:
            lo = mid
        else:
            hi = mid - 1
    return trail


def monthly_groups(limit, costs=COSTS):
    """讲义 feasible(limit) 插桩：返回分段列表。"""
    groups, cur = [[]], 0
    for c in costs:
        if cur + c > limit:
            groups.append([c])
            cur = c
        else:
            groups[-1].append(c)
            cur += c
    return groups


def monthly_rounds(costs=COSTS, m=M_GROUPS):
    lo, hi, rounds = max(costs), sum(costs), []
    while lo < hi:
        mid = (lo + hi) // 2
        ok = len(monthly_groups(mid, costs)) <= m
        rounds.append((lo, hi, mid, ok))
        if ok:
            hi = mid
        else:
            lo = mid + 1
    return lo, rounds
