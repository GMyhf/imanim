"""树与森林片的数据：讲义图 6.5 那片森林、「连线 / 切线 / 旋转」后的二叉树、先根 / 后根 / 层次周游、
OJ24729 讲义 Python 解法（括号嵌套建「左子/右兄」二叉链表 + 一次 walk 同时出先根与后根，原样插桩），
以及 3.3 节「带度数的后根次序」用栈还原森林的逐步快照。画面与旁白里的每个序列都从这里来。

森林用 dict 表示：结点 → 孩子列表（有序）；ROOTS 是各棵树的根，按从左到右的次序。
"""
from __future__ import annotations

from collections import deque

# 图 6.5(a)：A(B, C(E, F), D) 与 G(H(J), I)
CHILDREN = {"A": ["B", "C", "D"], "B": [], "C": ["E", "F"], "D": [], "E": [], "F": [],
            "G": ["H", "I"], "H": ["J"], "I": [], "J": []}
ROOTS = ["A", "G"]


def parent_edges(ch=CHILDREN):
    return [(p, c) for p, kids in ch.items() for c in kids]


def sibling_edges(ch=CHILDREN, roots=ROOTS):
    """连线：同一父结点的相邻兄弟，以及相邻两棵树的根（森林里的根互为兄弟）。"""
    out = [(a, b) for kids in [roots, *ch.values()] for a, b in zip(kids, kids[1:])]
    return out


def cut_edges(ch=CHILDREN):
    """切线：每个父结点只留通往第一个孩子的线，其余剪掉。"""
    return [(p, c) for p, kids in ch.items() for c in kids[1:]]


def to_binary(ch=CHILDREN, roots=ROOTS):
    """森林 → 二叉树：左 = 第一个孩子，右 = 下一个兄弟。返回 (shape, root)，shape: 结点 → (左, 右)。"""
    shape = {}

    def conv(seq):
        for i, n in enumerate(seq):
            kids = ch[n]
            shape[n] = (kids[0] if kids else None, seq[i + 1] if i + 1 < len(seq) else None)
            conv(kids)
    conv(roots)
    return shape, roots[0] if roots else None


def forest_order(kind, ch=CHILDREN, roots=ROOTS):
    out = []

    def go(n):
        if kind == "pre":
            out.append(n)
        for c in ch[n]:
            go(c)
        if kind == "post":
            out.append(n)
    for r in roots:
        go(r)
    return out


def forest_level(ch=CHILDREN, roots=ROOTS):
    out, q = [], deque(roots)
    while q:
        n = q.popleft()
        out.append(n)
        q.extend(ch[n])
    return out


def binary_order(kind, shape, root):
    out = []

    def go(n):
        if n is None:
            return
        if kind == "pre":
            out.append(n)
        go(shape[n][0])
        if kind == "in":
            out.append(n)
        go(shape[n][1])
    go(root)
    return out


def binary_level(shape, root):
    out, q = [], deque([root])
    while q:
        n = q.popleft()
        if n is None:
            continue
        out.append(n)
        q.extend(shape[n])
    return out


def depth_of(shape, root):
    d = {}

    def go(n, k):
        if n is None:
            return
        d[n] = k
        go(shape[n][0], k + 1)
        go(shape[n][1], k + 1)
    go(root, 0)
    return d


# ---------------------------------------------------------------- 讲义 OJ24729 解法（原样，walk 里加事件记录）
class Node:
    def __init__(self, val):
        self.val = val
        self.left = None    # 指向第一个孩子
        self.right = None   # 指向下一个兄弟


def build_tree(s):
    i = 0
    n = len(s)

    def build():
        nonlocal i
        node = Node(s[i])
        i += 1
        if i < n and s[i] == "(":
            i += 1                     # 跳过 '('
            node.left = build()        # 第一个孩子作为左孩子
            curr = node.left
            while i < n and s[i] == ",":
                i += 1                 # 跳过 ','
                curr.right = build()   # 其余孩子依次接成前一个孩子的右兄弟
                curr = curr.right
            i += 1                     # 跳过 ')'
        return node
    return build()


def traverse(root, events=None):
    pre_out, post_out = [], []

    def walk(curr):
        if curr is None:
            return
        pre_out.append(curr.val)    # 二叉树前序位置 = 原树先根
        if events is not None:
            events.append(("pre", curr.val))
        walk(curr.left)             # 左子树 = 原树的孩子们
        post_out.append(curr.val)   # 二叉树中序位置 = 原树后根
        if events is not None:
            events.append(("post", curr.val))
        walk(curr.right)            # 右子树 = 原树的后续兄弟
    walk(root)
    return "".join(pre_out), "".join(post_out)


def bracket(n, ch=CHILDREN):
    """把一棵树写成讲义的嵌套括号表示法。"""
    return n + ("(" + ",".join(bracket(c, ch) for c in ch[n]) + ")" if ch[n] else "")


def forest_via_oj():
    """用 OJ 解法建森林：两棵树各自建好，第二棵的根接成第一棵根的右兄弟（森林的根互为兄弟）。"""
    roots = [build_tree(bracket(r)) for r in ROOTS]
    for a, b in zip(roots, roots[1:]):
        a.right = b
    return roots[0]


# ---------------------------------------------------------------- 3.3 节 带度数的后根次序 → 用栈还原
def degree_postorder(ch=CHILDREN, roots=ROOTS):
    return [(n, len(ch[n])) for n in forest_order("post", ch, roots)]


def rebuild_from_degrees(seq):
    """每读到度为 d 的结点，从栈顶弹出 d 棵子树做它的孩子（逆序接回），再把新树压回去。
    返回 (森林 children, 根列表, 快照)；快照 = [(结点, 度, 弹出的子树根, 之后的栈)]。"""
    ch, stack, snaps = {}, [], []
    for n, d in seq:
        kids = [stack.pop() for _ in range(d)][::-1]
        ch[n] = kids
        stack.append(n)
        snaps.append((n, d, kids, list(stack)))
    return ch, list(stack), snaps


BIN, BIN_ROOT = to_binary()
PRE = forest_order("pre")            # A B C E F D G H J I
POST = forest_order("post")          # B E F C D A J H I G
LEVEL = forest_level()               # A G B C D H I E F J
BIN_PRE = binary_order("pre", BIN, BIN_ROOT)
BIN_IN = binary_order("in", BIN, BIN_ROOT)
BIN_LEVEL = binary_level(BIN, BIN_ROOT)
DEG_POST = degree_postorder()
REBUILD = rebuild_from_degrees(DEG_POST)
