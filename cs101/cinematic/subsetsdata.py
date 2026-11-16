"""回溯三形态片的数据层：子集（两种树）、组合、排列三棵决策树，组合总和的剪枝前后节点数。

约定与课件一致（W09 讲义 1.2–1.3 节、W08 讲义 3.3–3.4 节）：
- subsets_pick / subsets_start / combination_sum / permutations 照抄讲义，只在函数体里加插桩（log 参数，缺省不记）；
- combine 是讲义 1.2 节表格「组合（不可重复用）dfs(i + 1)，LC 77」那一行：子集模板换成「长度为 k 才收」，讲义没有给代码；
- 决策树节点的 path 存选过的数，先序编号 = DFS 到达的顺序；x 是叶子从左到右的横坐标（内部节点取孩子平均）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

NUMS = [1, 2, 3]
K = 2                                   # 并排比较时的组合：从 1、2、3 里选两个
CANDS, TARGET = [2, 3, 6, 7], 7         # 讲义 LC 39 例题


# ---------------------------------------------------------------- 讲义原版（加插桩）
def subsets_pick(nums, log=None):
    """W08 3.4 节：选或不选。log 记 ("node", sol) / ("collect", sol)。"""
    n, ans, sol = len(nums), [], []

    def backtrack(i):
        if log is not None:
            log.append(("node", tuple(sol)))
        if i == n:                   # 叶子：每个元素都决定过了
            ans.append(sol[:])
            if log is not None:
                log.append(("collect", tuple(sol)))
            return
        backtrack(i + 1)             # 不选 nums[i]
        sol.append(nums[i])          # 选 nums[i]
        backtrack(i + 1)
        sol.pop()                    # 手动撤销

    backtrack(0)
    return ans


def subsets_start(nums, log=None):
    """W09 1.2 节：从起始下标往后挑，每个节点都收。"""
    res, path = [], []

    def dfs(start):
        if log is not None:
            log.append(("node", tuple(path)))
        res.append(path[:])              # 每个节点都是一个答案
        if log is not None:
            log.append(("collect", tuple(path)))
        for i in range(start, len(nums)):
            path.append(nums[i])
            dfs(i + 1)                   # i+1：不能回头选，避免重复
            path.pop()

    dfs(0)
    return res


def combine(nums, k, log=None):
    """讲义表格 LC 77 一行：同一个模板，长度为 k 才收。"""
    res, path = [], []

    def dfs(start):
        if log is not None:
            log.append(("node", tuple(path)))
        if len(path) == k:
            res.append(path[:])
            if log is not None:
                log.append(("collect", tuple(path)))
            return
        for i in range(start, len(nums)):
            path.append(nums[i])
            dfs(i + 1)
            path.pop()

    dfs(0)
    return res


def permutations(a, log=None):
    """W08 3.3 节：used 数组。"""
    res = []
    used = [False] * len(a)
    path = []

    def dfs():
        if log is not None:
            log.append(("node", tuple(path)))
        if len(path) == len(a):
            res.append(path[:])          # ⚠️ 必须拷贝，否则存的是同一个列表
            if log is not None:
                log.append(("collect", tuple(path)))
            return
        for i in range(len(a)):
            if used[i]:
                continue
            used[i] = True
            path.append(a[i])
            dfs()
            path.pop()                   # 回溯：撤销选择
            used[i] = False

    dfs()
    return res


def combination_sum(candidates, target, log=None, mode="break"):
    """W09 1.2 节 LC 39 原样（mode="break"）。

    插桩：log 记 ("node", path, rest) / ("collect", path) / ("cmp", path, 候选数)——每次做 candidates[i] > rest 比较记一条。
    对照用的两种改写：mode="continue" 把 break 换成 continue；mode="none" 去掉这条判断，
    改成进入节点后 rest < 0 就返回（先走进去、超了再退回）。
    """
    res, path = [], []
    candidates = sorted(candidates)

    def dfs(start, rest):
        if log is not None:
            log.append(("node", tuple(path), rest))
        if mode == "none" and rest < 0:
            return
        if rest == 0:
            res.append(path[:])
            if log is not None:
                log.append(("collect", tuple(path)))
            return
        for i in range(start, len(candidates)):
            if mode != "none":
                if log is not None:
                    log.append(("cmp", tuple(path), candidates[i]))
                if candidates[i] > rest:     # 剪枝：排序后，后面的更大，直接停
                    if mode == "break":
                        break
                    continue
            path.append(candidates[i])
            dfs(i, rest - candidates[i]) # i 而不是 i+1：可重复使用
            path.pop()

    dfs(0, target)
    return res


# ---------------------------------------------------------------- 由插桩日志建树
@dataclass
class TNode:
    path: tuple
    id: int
    depth: int
    parent: int | None
    children: list[int] = field(default_factory=list)
    x: float = 0.0
    rest: int | None = None              # 组合总和：还差多少
    collected: bool = False
    order: int | None = None             # 第几个收到的答案（1 起）


def _layout(nodes):
    leaf = 0

    def place(i):
        nonlocal leaf
        nd = nodes[i]
        if not nd.children:
            nd.x = float(leaf)
            leaf += 1
            return
        for c in nd.children:
            place(c)
        nd.x = sum(nodes[c].x for c in nd.children) / len(nd.children)
    place(0)


def tree_from_log(log):
    """日志里的 node 事件按先序出现；父节点 = 栈里路径恰好少最后一个数的那个节点。"""
    nodes: list[TNode] = []
    stack: list[int] = []
    n_col = 0
    for e in log:
        if e[0] == "node":
            path = e[1]
            while stack and nodes[stack[-1]].path != path[:-1]:
                stack.pop()
            parent = stack[-1] if stack and path else None
            nd = TNode(path, len(nodes), 0 if parent is None else nodes[parent].depth + 1, parent,
                       rest=e[2] if len(e) > 2 else None)
            if parent is not None:
                nodes[parent].children.append(nd.id)
            nodes.append(nd)
            stack.append(nd.id)
        elif e[0] == "collect":
            n_col += 1
            nd = nodes[stack[-1]]
            nd.collected, nd.order = True, n_col
    _layout(nodes)
    return nodes


def _binary_rebuild(log):
    """选或不选的树：不选时路径不变，path 认不出父节点；改按「孩子满两个就出栈、叶子收完就返回」恢复。"""
    nodes: list[TNode] = []
    stack: list[int] = []
    n_col = 0
    for e in log:
        if e[0] == "node":
            while stack and len(nodes[stack[-1]].children) == 2:
                stack.pop()
            parent = stack[-1] if stack else None
            nd = TNode(e[1], len(nodes), 0 if parent is None else nodes[parent].depth + 1, parent)
            if parent is not None:
                nodes[parent].children.append(nd.id)
            nodes.append(nd)
            stack.append(nd.id)
        elif e[0] == "collect":
            n_col += 1
            nodes[stack[-1]].collected, nodes[stack[-1]].order = True, n_col
            stack.pop()                  # 叶子收完就返回
    _layout(nodes)
    return nodes


def pick_tree(nums=NUMS):
    log = []
    subsets_pick(nums, log)
    return _binary_rebuild(log)


def start_tree(nums=NUMS):
    log = []
    subsets_start(nums, log)
    return tree_from_log(log)


def combine_tree(nums=NUMS, k=K):
    log = []
    combine(nums, k, log)
    return tree_from_log(log)


def perm_tree(a=NUMS):
    log = []
    permutations(a, log)
    return tree_from_log(log)


def csum_tree(cands=CANDS, target=TARGET, mode="break"):
    log = []
    combination_sum(cands, target, log, mode)
    return tree_from_log([e for e in log if e[0] != "cmp"])


def csum_compares(cands=CANDS, target=TARGET, mode="break"):
    log = []
    combination_sum(cands, target, log, mode)
    return sum(1 for e in log if e[0] == "cmp")


def next_choices(kind, path, nums=NUMS):
    """节点 path 的下一层能选哪些数（按讲义的循环范围）。kind：subset / combine / csum / perm。"""
    if kind == "perm":
        return [v for v in nums if v not in path]
    start = nums.index(path[-1]) if path else 0
    if kind in ("subset", "combine"):
        start += 1 if path else 0
        if kind == "combine" and len(path) == K:
            return []
    return list(nums[start:])


def facts():
    """画面与旁白用到的全部数字。"""
    none = csum_tree(mode="none")
    brk = csum_tree(mode="break")
    return {
        "pick_nodes": len(pick_tree()),
        "pick_leaves": sum(1 for nd in pick_tree() if not nd.children),
        "start_nodes": len(start_tree()),
        "combine_nodes": len(combine_tree()),
        "combine_answers": len(combine(NUMS, K)),
        "perm_nodes": len(perm_tree()),
        "csum_answers": combination_sum(CANDS, TARGET),
        "csum_none": len(none),
        "csum_dead": sum(1 for nd in none if nd.rest < 0),
        "csum_break": len(brk),
        "csum_continue": len(csum_tree(mode="continue")),
        "cmp_continue": csum_compares(mode="continue"),
        "cmp_break": csum_compares(mode="break"),
        "breaks": csum_compares(mode="break") - (len(brk) - 1),   # 比较次数 = 往下走的次数 + break 的次数
    }


if __name__ == "__main__":
    import json
    print(json.dumps(facts(), ensure_ascii=False))
    print([nd.path for nd in start_tree()])
    print([(nd.path, nd.rest, len(nd.children)) for nd in csum_tree(mode="none")])
