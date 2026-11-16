"""二叉树周游片的数据：讲义图 5.5 那棵树、三种深度优先周游（【算法5.3】三个递归函数照搬）、
层次周游（【算法5.7】，队列换成 collections.deque）、由中序 + 后序重建（OJ24750 讲义 Python 解法原样插桩）、
表达式树（图 5.6）。画面与旁白里的每个序列都从这里来。

树用 dict 表示：结点 → (左孩子, 右孩子)，没有孩子写 None；ROOT 为根。
"""
from __future__ import annotations

from collections import deque

# 图 5.5：根 A；B 有孩子 D、E，E 有左孩子 G；C 有右孩子 F，F 有孩子 H、I
FIG55 = {"A": ("B", "C"), "B": ("D", "E"), "C": (None, "F"), "D": (None, None), "E": ("G", None),
         "F": ("H", "I"), "G": (None, None), "H": (None, None), "I": (None, None)}
ROOT = "A"

# 图 5.6：A + B × (C + D)。内部结点用 +1/×/+2 区分两个加号，显示时去掉编号
EXPR = {"+1": ("A", "×"), "×": ("B", "+2"), "+2": ("C", "D"),
        "A": (None, None), "B": (None, None), "C": (None, None), "D": (None, None)}
EXPR_ROOT = "+1"


def label(k: str) -> str:
    return k.rstrip("12") if k[0] in "+×" else k


# ---------------------------------------------------------------- 【算法5.3】三个递归函数，只差 visit 那一行的位置
def preorder_impl(tree, node, visit):
    if node is None:
        return
    visit(node)                             # 根
    preorder_impl(tree, tree[node][0], visit)   # 左
    preorder_impl(tree, tree[node][1], visit)   # 右


def inorder_impl(tree, node, visit):
    if node is None:
        return
    inorder_impl(tree, tree[node][0], visit)    # 左
    visit(node)                             # 根
    inorder_impl(tree, tree[node][1], visit)    # 右


def postorder_impl(tree, node, visit):
    if node is None:
        return
    postorder_impl(tree, tree[node][0], visit)  # 左
    postorder_impl(tree, tree[node][1], visit)  # 右
    visit(node)                             # 根


def order(kind, tree=FIG55, root=ROOT) -> list:
    out = []
    {"pre": preorder_impl, "in": inorder_impl, "post": postorder_impl}[kind](tree, root, out.append)
    return out


# ---------------------------------------------------------------- 【算法5.7】层次周游：插桩记下每次出队后的队列
def level_order(tree=FIG55, root=ROOT):
    """返回 [(出队结点, 这次入队的孩子们, 之后的队列)]。"""
    steps = []
    front = deque([root]) if root is not None else deque()
    while front:
        node = front.popleft()              # 出队，访问
        pushed = [c for c in tree[node] if c is not None]
        front.extend(pushed)                # 左右孩子依次入队
        steps.append((node, pushed, list(front)))
    return steps


# ---------------------------------------------------------------- 绕轮廓走一圈（欧拉环游）
def euler(tree=FIG55, root=ROOT):
    """贴着树的轮廓走：每个结点经过三次，side 0=从左边下来（前序）、1=从底下穿过（中序）、2=从右边上去（后序）。"""
    ev = []

    def go(n):
        if n is None:
            return
        ev.append((n, 0))
        go(tree[n][0])
        ev.append((n, 1))
        go(tree[n][1])
        ev.append((n, 2))
    go(root)
    return ev


# ---------------------------------------------------------------- OJ24750 讲义解法（原样 + 插桩）
def preorder_of(inorder, postorder, trace=None):
    pos = {c: i for i, c in enumerate(inorder)}   # 「点名册」：字符 → 中序下标
    out = []

    def build(in_lo, in_hi, post_lo):             # 中序段 [in_lo, in_hi)，后序段从 post_lo 起、一样长
        if in_lo == in_hi:
            return
        root = postorder[post_lo + (in_hi - in_lo) - 1]   # 后序段的最后一个是根
        k = pos[root]
        if trace is not None:
            trace.append({"root": root, "in": (in_lo, in_hi), "post": (post_lo, post_lo + in_hi - in_lo), "k": k})
        out.append(root)                          # 前序：根最先输出
        build(in_lo, k, post_lo)                  # 左子树
        build(k + 1, in_hi, post_lo + (k - in_lo))   # 右子树：后序起点跳过左子树的 k - in_lo 个

    build(0, len(inorder), 0)
    return ''.join(out)


def rebuild(inorder, postorder) -> tuple[dict, str, list]:
    """把 preorder_of 的调用轨迹还原成树：每次 build 的根挂到父调用的左/右。"""
    trace = []
    pre = preorder_of(inorder, postorder, trace)
    tree = {t["root"]: [None, None] for t in trace}
    for i, t in enumerate(trace):
        lo, hi = t["in"]
        for p in reversed(trace[:i]):             # 最近的、中序段包含本段的祖先
            plo, phi = p["in"]
            if plo <= lo and hi <= phi and p is not t:
                tree[p["root"]][0 if hi <= p["k"] else 1] = t["root"]
                break
    return {k: tuple(v) for k, v in tree.items()}, pre, trace


def levels(tree, root) -> int:
    return 0 if root is None else 1 + max(levels(tree, tree[root][0]), levels(tree, tree[root][1]))


def widest(tree, root) -> int:
    cur, best = [root], 0
    while cur:
        best = max(best, len(cur))
        cur = [c for n in cur for c in tree[n] if c is not None]
    return best


PRE, IN, POST = "".join(order("pre")), "".join(order("in")), "".join(order("post"))
LEVEL = "".join(s[0] for s in level_order())

if __name__ == "__main__":
    print(PRE, IN, POST, LEVEL)
    print(rebuild(IN, POST)[1])
    print([label(x) for x in order("pre", EXPR, EXPR_ROOT)], [label(x) for x in order("post", EXPR, EXPR_ROOT)])
    print(level_order())
