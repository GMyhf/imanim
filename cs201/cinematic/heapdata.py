"""堆片的数据：讲义 5.1 节 OJ04078 的 Python 版 MinHeap 原样搬来，只在交换/停下处插桩记事件。

画面里每一步上浮、下沉、建堆的交换，旁白里的每个数字（交换次数、建堆代价 11 与 34）都从这里来；
test_heap.py 用 heapq、暴力检查堆序、讲义图 5.15/5.17 的文字结果对撞。
"""
from __future__ import annotations

FIG514 = [12, 14, 15, 19, 20, 17, 18, 24, 22, 26]   # 图 5.14 的最小堆
NEW_KEY = 13                                        # 图 5.15：插入 13
BUILD = [19, 8, 35, 65, 40, 3, 7, 45]               # 图 5.17：建堆的关键码集合


class MinHeap:
    """讲义 OJ04078 题解的 MinHeap；self.log 是插桩：记下每次比较的结果。"""

    def __init__(self):
        self.data = []
        self.log = []

    def insert(self, value):                # 放到末尾，再上浮
        a = self.data
        a.append(value)
        i = len(a) - 1
        self.log.append(("place", i, value))
        while i > 0:
            parent = (i - 1) // 2
            if not a[i] < a[parent]:
                self.log.append(("stop", i, parent))
                break
            a[i], a[parent] = a[parent], a[i]
            self.log.append(("swap", i, parent))
            i = parent
        else:
            self.log.append(("root", i))

    def remove_min(self):                   # 末尾元素搬到根上，再下沉；空堆返回 None
        a = self.data
        if not a:
            return None
        smallest = a[0]
        last = a.pop()
        self.log.append(("take", 0, smallest, len(a)))
        if a:
            a[0] = last
            i, n = 0, len(a)
            while True:
                left, right, m = 2 * i + 1, 2 * i + 2, i
                if left < n and a[left] < a[m]:
                    m = left
                if right < n and a[right] < a[m]:
                    m = right
                if m == i:
                    self.log.append(("stop", i, None))
                    break
                a[i], a[m] = a[m], a[i]
                self.log.append(("swap", i, m))
                i = m
        return smallest


def sift_down(a, i, n, log):
    """建堆用的下沉：与 remove_min 里那段循环逐字相同，只是起点 i 由参数给出。"""
    while True:
        left, right, m = 2 * i + 1, 2 * i + 2, i
        if left < n and a[left] < a[m]:
            m = left
        if right < n and a[right] < a[m]:
            m = right
        if m == i:
            log.append(("stop", i, None))
            return
        a[i], a[m] = a[m], a[i]
        log.append(("swap", i, m))
        i = m


def build_heap(keys):
    """筛选法建堆：从最后一个非叶结点 n//2-1 倒着对每个结点下沉。返回 (堆, [(起点, 事件列表)])。"""
    a = list(keys)
    n = len(a)
    rounds = []
    for i in range(n // 2 - 1, -1, -1):
        log = []
        sift_down(a, i, n, log)
        rounds.append((i, log))
    return a, rounds


def insert_trace():
    h = MinHeap()
    h.data = list(FIG514)
    h.insert(NEW_KEY)
    return list(h.data), h.log


def remove_trace():
    h = MinHeap()
    h.data = insert_trace()[0]
    got = h.remove_min()
    return got, list(h.data), h.log


def swaps(log):
    return sum(1 for e in log if e[0] == "swap")


def sink_cost(h):
    """每层排满、深度为 h 的树：第 i 层 2^i 个结点各最多下沉 h-i 层，逐层的代价。"""
    return [2 ** i * (h - i) for i in range(h + 1)]


def float_cost(h):
    """同一棵树若逐个 insert：第 i 层 2^i 个结点各最多上浮 i 层。"""
    return [2 ** i * i for i in range(h + 1)]


H = 3
N_PERFECT = 2 ** (H + 1) - 1          # 15
