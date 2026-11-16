"""Huffman 片的数据：讲义 5 节教学版 teaching.hpp 的 MinHeap + HuffmanTree 逐行移植成 Python（并列权时的
左右次序由这份堆的上浮/下沉决定，所以照搬而不用 heapq），外加讲义 OJ04080 题解原样（只求 WPL）。

插桩：构造时记下每次合并（左、右、新根），画面里森林怎样一步步并成一棵树就按这份记录走。
test_huffman.py 对撞讲义码表、195/228、14 位电文、图 5.18 的三个 WPL，并用穷举所有二叉树形验证最优。
"""
from __future__ import annotations

import heapq

FREQ = {"a": 15, "b": 2, "c": 6, "d": 5, "e": 20, "f": 10, "g": 18}   # 图 5.20 的字符与频率
FIG518 = [6, 2, 3, 4]                                                 # 图 5.18 的四个权
MSG = "abbaaadc"                                                      # 6.2 节的电文
WORD = "cafe"                                                         # 片中演示译码的词


class MinHeap:
    """teaching.hpp 的 MinHeap 逐行移植：比较只用 <，并列时位置由上浮/下沉的路径决定。"""

    def __init__(self):
        self.data = []

    def size(self):
        return len(self.data)

    def insert(self, value):
        self.data.append(value)
        self._sift_up(len(self.data) - 1)

    def remove_min(self):
        if not self.data:
            return None
        smallest = self.data[0]
        last = self.data.pop()
        if self.data:
            self.data[0] = last
            self._sift_down(0)
        return smallest

    def _sift_up(self, index):
        d = self.data
        while index > 0:
            parent = (index - 1) // 2
            if not (d[index] < d[parent]):
                break
            d[index], d[parent] = d[parent], d[index]
            index = parent

    def _sift_down(self, index):
        d, n = self.data, len(self.data)
        while True:
            left, right, smallest = 2 * index + 1, 2 * index + 2, index
            if left < n and d[left] < d[smallest]:
                smallest = left
            if right < n and d[right] < d[smallest]:
                smallest = right
            if smallest == index:
                return
            d[index], d[smallest] = d[smallest], d[index]
            index = smallest


class Node:
    _next = 0

    def __init__(self, weight, symbol="", left=None, right=None):
        self.weight, self.symbol, self.left, self.right = weight, symbol, left, right
        self.id = Node._next
        Node._next += 1

    def __lt__(self, other):            # ByWeight：只比权
        return self.weight < other.weight

    @property
    def leaf(self):
        return self.left is None and self.right is None


def build(symbols, weights):
    """HuffmanTree 构造函数：每个权先成一棵单结点树，反复取最小、次小合并。返回 (根, 叶子列表, 合并记录)。"""
    heap = MinHeap()
    leaves = []
    for s, w in zip(symbols, weights):
        node = Node(w, s)
        leaves.append(node)
        heap.insert(node)
    merges = []
    while heap.size() > 1:
        left = heap.remove_min()        # 最小的
        right = heap.remove_min()       # 次小的
        parent = Node(left.weight + right.weight, "", left, right)
        merges.append((left, right, parent))
        heap.insert(parent)
    return heap.remove_min(), leaves, merges


def codes(root):
    """左边 0、右边 1；只有一个字符时约定编码 "0"。"""
    out = {}

    def walk(n, path):
        if n.leaf:
            out[n.symbol] = path or "0"
            return
        walk(n.left, path + "0")
        walk(n.right, path + "1")
    walk(root, "")
    return out


def depths(root):
    out = {}

    def walk(n, d):
        if n.leaf:
            out[n.symbol] = d
            return
        walk(n.left, d + 1)
        walk(n.right, d + 1)
    walk(root, 0)
    return out


def wpl(root, d=0):
    if root.leaf:
        return root.weight * d
    return wpl(root.left, d + 1) + wpl(root.right, d + 1)


def decode_trace(root, bits):
    """译码：读 0 走左、读 1 走右，到叶子吐出字符回到根。返回 (文字, [(第几位, 走到的结点, 吐出的字符或空)])。"""
    text, steps, cur = [], [], root
    for k, b in enumerate(bits):
        cur = cur.left if b == "0" else cur.right
        out = cur.symbol if cur.leaf else ""
        steps.append((k, cur, out))
        if cur.leaf:
            text.append(cur.symbol)
            cur = root
    return "".join(text), steps


def oj04080(weights):
    """讲义 OJ04080 题解原样（输入改成参数）：合并出的新权累加起来就是 WPL。"""
    weights = list(weights)
    heapq.heapify(weights)                      # 筛选法建堆，O(n)
    wpl = 0
    while len(weights) > 1:
        a = heapq.heappop(weights)              # 最小的
        b = heapq.heappop(weights)              # 次小的
        wpl += a + b                            # 新内部结点的权，计入 WPL
        heapq.heappush(weights, a + b)
    return wpl


def fig_tree():
    """图 5.20 那组字符的 Huffman 树。"""
    return build(list(FREQ), list(FREQ.values()))


def msg_tree():
    cnt = {}
    for ch in MSG:
        cnt[ch] = cnt.get(ch, 0) + 1
    syms = sorted(cnt)
    return build(syms, [cnt[s] for s in syms])


# 图 5.18 的三棵树：嵌套二元组，叶子是权
FIG518_TREES = {"a": ((6, 2), (3, 4)), "b": (((6, (2, 3)), 4)), "c": (6, (4, (2, 3)))}


def nested_wpl(t, d=0):
    if isinstance(t, int):
        return t * d
    return nested_wpl(t[0], d + 1) + nested_wpl(t[1], d + 1)


def fixed_bits(nsym, total):
    """等长编码：每个字符 ceil(log2 nsym) 位。"""
    k = max(1, (nsym - 1).bit_length())
    return k, k * total
