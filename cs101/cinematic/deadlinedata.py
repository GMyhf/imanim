"""最多按时完成几个任务（例题精讲）片的数据层：讲义 W13 5.3 节两段代码原样 + 插桩，画面和旁白里的每个数字都从这里来。

题目（讲义 5.3）：n 个任务，第 i 个耗时 tᵢ、截止 dᵢ，任意顺序、不可中断，求最多能按时完成几个（n ≤ 10⁵）。
解法：按截止时间排序，依次加入；总时长超过当前截止时间，就从已选里丢掉耗时最长的（大根堆，存负数）。

讲义原样：max_tasks、max_tasks_brute、讲义两行 print 的样例、讲义对拍循环（seed 101、200 组）。
补写（讲义没有）：trace 插桩、skip_greedy（「超时就跳过新任务」的错误贪心，易错点用）、drop_options、
edf_ok、prefix_best、range 数字。片中主例 TASKS 是自拟数据（六个任务，耗时互不相同，便于画堆）。
"""
from __future__ import annotations

import heapq
import itertools
import math
import random

# ------------------------------------------------------------------ 讲义原样
def max_tasks(tasks):
    """tasks: [(耗时, 截止时间)]；返回最多按时完成的任务数。"""
    tasks = sorted(tasks, key=lambda t: t[1])       # 按截止时间
    heap, total = [], 0                             # heap 存 -耗时（大根堆）
    for cost, deadline in tasks:
        heapq.heappush(heap, -cost)
        total += cost
        if total > deadline:                        # 超时了
            total += heapq.heappop(heap)            # 丢掉耗时最长的（弹出的是负数）
    return len(heap)


def max_tasks_brute(tasks):
    n = len(tasks)
    best = 0
    for k in range(n, 0, -1):
        for combo in itertools.combinations(range(n), k):
            for order in itertools.permutations(combo):
                t = 0
                ok = True
                for i in order:
                    t += tasks[i][0]
                    if t > tasks[i][1]:
                        ok = False
                        break
                if ok:
                    return k
    return 0


LECTURE_SAMPLES = [([(3, 4), (2, 3), (1, 2)], 2),                # 讲义 print 的两行与注释里的输出
                   ([(5, 5), (1, 1), (1, 2), (1, 3)], 3)]


def lecture_check(seed=101, rounds=200):
    """讲义对拍循环原样（random.seed(101) 换成同种子的独立 Random 对象，生成序列相同）。返回全部数据组。"""
    rnd = random.Random(seed)
    cases = []
    for _ in range(rounds):
        n = rnd.randint(1, 6)
        ts = [(rnd.randint(1, 5), rnd.randint(1, 12)) for _ in range(n)]
        assert max_tasks(ts) == max_tasks_brute(ts), ts
        cases.append(ts)
    return cases


# ------------------------------------------------------------------ 片中主例（自拟）
TASKS = [(6, 9), (1, 2), (4, 10), (2, 7), (3, 11), (5, 6)]      # 题目给出的顺序（未排序）
SORTED = sorted(TASKS, key=lambda t: t[1])                      # 按截止时间
N_BIG = 10 ** 5                                                 # 数据范围 n ≤ 10⁵


# ------------------------------------------------------------------ 插桩与补写
def trace(tasks=TASKS):
    """max_tasks 插桩：每加入一个任务记一步。

    返回 [dict(cost, deadline, pushed=堆(正数，heapq 数组顺序), total_in=加入后的总时长,
              dropped=扔掉的耗时或 None, heap=处理完的堆, total=处理完的总时长)]。
    """
    tasks = sorted(tasks, key=lambda t: t[1])
    heap, total, out = [], 0, []
    for cost, deadline in tasks:
        heapq.heappush(heap, -cost)
        total += cost
        pushed, total_in, dropped = [-x for x in heap], total, None
        if total > deadline:
            x = heapq.heappop(heap)
            total += x
            dropped = -x
        out.append(dict(cost=cost, deadline=deadline, pushed=pushed, total_in=total_in,
                        dropped=dropped, heap=[-x for x in heap], total=total))
    return out


def skip_greedy(tasks=TASKS):
    """常见错误：按截止排序后，放得下就放，超时就跳过新来的，不反悔。返回 (个数, 每步是否放下)。"""
    total, took = 0, []
    for cost, deadline in sorted(tasks, key=lambda t: t[1]):
        ok = total + cost <= deadline
        if ok:
            total += cost
        took.append(ok)
    return sum(took), took


def wrong_sign(tasks=TASKS):
    """易错点：弹出来的是负数，却写成 total -= heappop(heap)。返回这样写出的答案。"""
    tasks = sorted(tasks, key=lambda t: t[1])
    heap, total = [], 0
    for cost, deadline in tasks:
        heapq.heappush(heap, -cost)
        total += cost
        if total > deadline:
            total -= heapq.heappop(heap)
    return len(heap)


def drop_options(step):
    """第 step 步超时那一刻：已选任务（含新来的）各扔一个后剩下的总时长 [(扔掉的耗时, 剩余总时长)]，按耗时升序。"""
    st = trace()[step]
    return [(c, st["total_in"] - c) for c in sorted(st["pushed"])]


def edf_ok(chosen):
    """一组任务能否全部按时：按截止时间从早到晚做，检查每个的完成时刻。"""
    t = 0
    for cost, deadline in sorted(chosen, key=lambda x: x[1]):
        t += cost
        if t > deadline:
            return False
    return True


def layout(chosen):
    """按截止排好后各任务在时间轴上的 [开始, 结束)。"""
    t, out = 0, []
    for cost, deadline in sorted(chosen, key=lambda x: x[1]):
        out.append((cost, deadline, t, t + cost))
        t += cost
    return out


def check_stats(seed=101, rounds=200):
    """讲义对拍那 200 组：(组数, 最大任务数, 不反悔贪心答错的组数)。"""
    cases = lecture_check(seed, rounds)
    bad = sum(skip_greedy(ts)[0] != max_tasks(ts) for ts in cases)
    return len(cases), max(map(len, cases)), bad


TR = trace()
ANSWER = max_tasks(TASKS)
SKIP_ANSWER = skip_greedy()[0]
DROPS = [(k, s["dropped"]) for k, s in enumerate(TR) if s["dropped"] is not None]   # (第几步, 扔掉的耗时)
N2 = N_BIG ** 2                                    # 一百亿
NLOGN = N_BIG * math.log2(N_BIG)                   # 约一百六十六万，不到两百万
CHECK = check_stats()

if __name__ == "__main__":
    print("样例：", [max_tasks(t) for t, _ in LECTURE_SAMPLES])
    print("排序后：", SORTED)
    for s in TR:
        print(s)
    print("答案", ANSWER, "不反悔", SKIP_ANSWER, skip_greedy()[1], "符号写错", wrong_sign())
    print("第一次超时各扔一个：", drop_options(DROPS[0][0]), "第二次：", drop_options(DROPS[1][0]))
    print("最终时间轴：", layout([(s, d) for s, d in SORTED if s in TR[-1]["heap"]]))
    print("n²", N2, "n log n", NLOGN, "对拍", CHECK)
