"""二叉搜索树片的数据：讲义 BinarySearchTree（C++ 教学版【算法5.9】【算法5.10】）逐句翻成 Python 并插桩，
加春季讲义的 AVL（晴问 9.5 的 Python 原样，只加了旋转记录）。画面与旁白里的每个数字都从这里来。

C++ 里的 `Node** link`（「新结点该挂在哪根指针上」）在 Python 里写成 (owner, attr)：owner 是结点或树本身，
attr 是 "left" / "right" / "root"，读写 getattr/setattr——逐句对应原版的 `*link`。
"""
from __future__ import annotations

KEYS = [50, 19, 35, 55, 20, 5, 100, 52, 88, 53, 92]      # 讲义图 5.11 的插入次序


class Node:
    def __init__(self, value, left=None, right=None):
        self.value, self.left, self.right = value, left, right


class BST:
    def __init__(self):
        self.root = None

    # 【算法5.9】插入：一路比较着往下走，走到空位就挂上去；返回走过的结点值（插桩）
    def insert(self, value):
        link = (self, "root")                       # Node** link = &root_;
        path = []
        while getattr(*link) is not None:
            cur = getattr(*link)
            path.append(cur.value)
            if value < cur.value:
                link = (cur, "left")
            elif cur.value < value:
                link = (cur, "right")
            else:
                return False, path                  # 已经有了
        setattr(*link, Node(value))                 # *link = new Node{value, nullptr, nullptr};
        return True, path

    # 查找：同样一路往下走；返回 (是否找到, 比较过的结点, 最后停在哪个结点的哪一侧)
    def contains(self, value):
        current, path, last = self.root, [], None
        while current is not None:
            path.append(current.value)
            if value < current.value:
                last = (current.value, "left")
                current = current.left
            elif current.value < value:
                last = (current.value, "right")
                current = current.right
            else:
                return True, path, None
        return False, path, last

    # 【算法5.10】删除。返回插桩信息：情形、被删结点、顶替者、前驱原来的左孩子
    def remove(self, value):
        info = {}
        ok = self._remove_impl((self, "root"), value, info)
        return ok, info

    def _remove_impl(self, link, value, info):
        node = getattr(*link)
        if node is None:
            return False
        if value < node.value:
            return self._remove_impl((node, "left"), value, info)
        if node.value < value:
            return self._remove_impl((node, "right"), value, info)

        removed = node
        if removed.left is None:                    # 没有左孩子：右孩子直接顶上
            setattr(*link, removed.right)
            info.update(case="leaf" if removed.right is None else "right_only", removed=removed.value,
                        replacement=None if removed.right is None else removed.right.value)
            return True

        # 找中序前驱：从左孩子出发，一路向右走到底
        predecessor_link = (removed, "left")
        walk = [removed.left.value]
        while getattr(*predecessor_link).right is not None:
            predecessor_link = (getattr(*predecessor_link), "right")
            walk.append(getattr(*predecessor_link).value)
        replacement = getattr(*predecessor_link)
        info.update(case="two" if removed.right is not None else "left_only", removed=removed.value,
                    replacement=replacement.value, walk=walk,
                    pred_left=None if replacement.left is None else replacement.left.value,
                    pred_parent=predecessor_link[0].value)
        setattr(*predecessor_link, replacement.left)   # 前驱可能还有左孩子，先接走
        replacement.left = removed.left
        replacement.right = removed.right
        setattr(*link, replacement)
        return True

    def inorder(self):
        out = []

        def go(n):
            if n is None:
                return
            go(n.left)
            out.append(n.value)
            go(n.right)
        go(self.root)
        return out


# ---------------------------------------------------------------- AVL（春季讲义 8.2.1，晴问 9.5 原样 + 旋转记录）
class AVLNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


class AVL:
    def __init__(self):
        self.root = None
        self.log = []                               # 插桩：每次旋转 (方向, 绕哪个结点, 树型)
        self.mid = []                               # 插桩：双旋转第一转之后、以失衡结点为根的子树形状

    def insert(self, value):
        if not self.root:
            self.root = AVLNode(value)
        else:
            self.root = self._insert(value, self.root)

    def _insert(self, value, node):
        if not node:
            return AVLNode(value)
        elif value < node.value:
            node.left = self._insert(value, node.left)
        else:
            node.right = self._insert(value, node.right)

        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))

        balance = self._get_balance(node)

        if balance > 1:
            if value < node.left.value:	# 树形是 LL
                self.log.append(("right", node.value, "LL"))
                return self._rotate_right(node)
            else:	# 树形是 LR
                self.log.append(("left", node.left.value, "LR"))
                node.left = self._rotate_left(node.left)
                self.mid.append(shape(node))
                self.log.append(("right", node.value, "LR"))
                return self._rotate_right(node)

        if balance < -1:
            if value > node.right.value:	# 树形是 RR
                self.log.append(("left", node.value, "RR"))
                return self._rotate_left(node)
            else:	# 树形是 RL
                self.log.append(("right", node.right.value, "RL"))
                node.right = self._rotate_right(node.right)
                self.mid.append(shape(node))
                self.log.append(("left", node.value, "RL"))
                return self._rotate_left(node)

        return node

    def _get_height(self, node):
        if not node:
            return 0
        return node.height

    def _get_balance(self, node):
        if not node:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)

    def _rotate_left(self, z):
        y = z.right
        T2 = y.left
        y.left = z
        z.right = T2
        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))
        return y

    def _rotate_right(self, y):
        x = y.left
        T2 = x.right
        x.right = y
        y.left = T2
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))
        x.height = 1 + max(self._get_height(x.left), self._get_height(x.right))
        return x

    def preorder(self):
        return self._preorder(self.root)

    def _preorder(self, node):
        if not node:
            return []
        return [node.value] + self._preorder(node.left) + self._preorder(node.right)


# ---------------------------------------------------------------- 快照与度量
def shape(root) -> dict:
    """结点 → (左孩子值, 右孩子值)；外加键 None → 根。场景按它布局。"""
    out = {None: None if root is None else root.value}

    def go(n):
        if n is None:
            return
        out[n.value] = (n.left.value if n.left else None, n.right.value if n.right else None)
        go(n.left)
        go(n.right)
    go(root)
    return out


def levels(root) -> int:
    """层数（只有根算 1 层；空树 0）。"""
    return 0 if root is None else 1 + max(levels(root.left), levels(root.right))


def balance_factors(root) -> dict:
    out = {}

    def h(n):
        if n is None:
            return 0
        a, b = h(n.left), h(n.right)
        out[n.value] = a - b
        return 1 + max(a, b)
    h(root)
    return out


def build(keys) -> BST:
    t = BST()
    for k in keys:
        t.insert(k)
    return t


# 片中用到的各个快照（场景直接取）
def film():
    t = BST()
    inserts = []
    for k in KEYS:
        _, path = t.insert(k)
        inserts.append((k, path, shape(t.root)))
    fig511 = shape(t.root)
    search = {v: t.contains(v) for v in (53, 60)}
    sorted_keys = t.inorder()
    deletes = []
    for v in (5, 52, 50):                           # 叶子、只有右孩子、两个孩子（前驱自己还有左孩子）
        ok, info = t.remove(v)
        deletes.append((v, info, shape(t.root)))
    chain = build(range(1, 8))
    avl, avl_steps = AVL(), []
    for v in range(1, 8):
        before = len(avl.log)
        avl.insert(v)
        avl_steps.append((v, avl.log[before:], shape(avl.root), balance_factors(avl.root)))
    lr, lr_steps = AVL(), []
    for v in (5, 2, 3):
        before = len(lr.log)
        lr.insert(v)
        lr_steps.append((v, lr.log[before:], shape(lr.root), list(lr.mid), balance_factors(lr.root)))
        lr.mid.clear()
    return {"inserts": inserts, "fig511": fig511, "search": search, "sorted": sorted_keys,
            "levels511": levels(build(KEYS).root), "deletes": deletes, "after_delete": t.inorder(),
            "chain": shape(chain.root), "chain_levels": levels(chain.root),
            "avl_steps": avl_steps, "avl_levels": levels(avl.root), "avl_rotations": len(avl.log),
            "lr_steps": lr_steps}


if __name__ == "__main__":
    import pprint
    pprint.pprint(film(), width=140)
