"""例题精讲·滑动窗口最大值片的数据：讲义两份参考解原样搬来（LeetCode 239 的 Solution 类、OpenJudge 26978 的
作业题解 main），另写插桩版逐步记录双端队列的入队、队尾弹出、队首过期与输出，画面和旁白里的每个数字都从这里来。

讲义：数据结构与算法（B）2026spring 第 4–5.5 周《线性结构》5.3 双端队列、5.4 单调队列（练习 T239）；
作业 2025数据结构与算法A-作业「26978 滑动窗口最大值（单调队列）」；2026fall 每日选作 0930。
test_slidemax.py 对撞两份讲义原版、暴力解与随机数据，以及旁白里写死的数字。
"""
from __future__ import annotations

import io
import sys
from collections import deque
from typing import List

NUMS = [1, 3, -1, -3, 5, 3, 6, 7]      # LeetCode 239 示例 1
K = 3
BIG_N, BIG_K = 100_000, 50_000         # 题目上限 n ≤ 10^5，取 k = n/2 估暴力的比较次数


# ------------------------------------------------------------------ 讲义原版：2026spring 5.4 练习 T239
class Solution:
    def maxSlidingWindow(self, nums: List[int], k: int) -> List[int]:
        if not nums or k == 0:
            return []

        n = len(nums)
        if k == 1:
            return nums

        deque_index = deque()  # 存储索引，保持双端队列中的值递减
        res = []

        for i in range(n):
            # 移除滑出窗口的元素（队首元素）
            if deque_index and deque_index[0] < i - k + 1:
                deque_index.popleft()

            # 移除所有小于当前元素的队尾元素
            while deque_index and nums[deque_index[-1]] < nums[i]:
                deque_index.pop()

            # 将当前元素的索引加入队列
            deque_index.append(i)

            # 从第 k 个元素开始记录结果，队首始终是窗口的最大值
            if i >= k - 1:
                res.append(nums[deque_index[0]])

        return res


# ------------------------------------------------------------------ 讲义原版：作业 26978 Python 题解
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2 + n]))

    q = deque()                                # 存下标，对应值单调递减
    ans = []
    for i, x in enumerate(a):
        while q and q[0] <= i - k:             # 队首滑出窗口
            q.popleft()
        while q and a[q[-1]] <= x:             # 队尾比新元素小，永无出头之日
            q.pop()
        q.append(i)
        if i >= k - 1:
            ans.append(a[q[0]])
    print(' '.join(map(str, ans)))


def run_oj(text: str) -> str:
    """把一组 OJ 输入喂给 main()，取回它打印的一行。"""
    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(text), io.StringIO()
    try:
        main()
        return sys.stdout.getvalue().strip()
    finally:
        sys.stdin, sys.stdout = old_in, old_out


# ------------------------------------------------------------------ 插桩版（与 26978 题解同一写法：<= 弹队尾）
def trace(a, k):
    """返回 (结果列表, 事件)。事件逐条按代码执行顺序：
    ("expire", i, j) 下标 j 从队首过期弹出；("pop", i, j) 下标 j 不比 a[i] 大，从队尾弹出；
    ("push", i) 下标 i 入队尾；("out", i, j, v) 窗口 [i-k+1, i] 满，输出队首 j 的值 v。
    """
    q, ans, ev = deque(), [], []
    for i, x in enumerate(a):
        while q and q[0] <= i - k:
            ev.append(("expire", i, q.popleft()))
        while q and a[q[-1]] <= x:
            ev.append(("pop", i, q.pop()))
        q.append(i)
        ev.append(("push", i))
        if i >= k - 1:
            ans.append(a[q[0]])
            ev.append(("out", i, q[0], a[q[0]]))
    return ans, ev


def snapshots(a, k):
    """每处理完一个 i 之后队列里的下标。"""
    q, snaps = [], []
    for e in trace(a, k)[1]:
        if e[0] == "expire":
            q.pop(0)
        elif e[0] == "pop":
            q.pop()
        elif e[0] == "push":
            q.append(e[1])
            snaps.append(list(q))
    return snaps


def brute(a, k):
    return [max(a[i:i + k]) for i in range(len(a) - k + 1)]


def brute_compares(n, k):
    """每个窗口从头比一遍：n-k+1 个窗口，每个 k-1 次比较。"""
    return (n - k + 1) * (k - 1)


def op_counts(a, k):
    ev = trace(a, k)[1]
    push = sum(e[0] == "push" for e in ev)
    pops = sum(e[0] in ("pop", "expire") for e in ev)
    return push, pops


if __name__ == "__main__":
    ans, ev = trace(NUMS, K)
    print(ans, Solution().maxSlidingWindow(NUMS, K), brute(NUMS, K))
    for e in ev:
        print(e)
    print(snapshots(NUMS, K))
    print("brute", brute_compares(len(NUMS), K), brute_compares(BIG_N, BIG_K), "ops", op_counts(NUMS, K))
    print(run_oj("8 3\n1 3 -1 -3 5 3 6 7\n"))
