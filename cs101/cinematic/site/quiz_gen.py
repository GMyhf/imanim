"""生成 CS101 入口页的看后小测 quiz.json：每支片 3 题。

计算题的正确答案一律由该片的 <id>data.py（讲义原版代码插桩）现算，不手写结果；
干扰项尽量取「常见错误理解」算出来的值（比如正序滚动数组得到的完全背包结果、贪心找零的枚数）。
test_quiz.py 再用独立实现重算每道计算题的正确选项。

python quiz_gen.py        # 写 site/quiz.json；选项顺序用固定种子打乱，重复运行结果不变
格式：{"<film_id>": [{"q": 题干, "options": [...], "answer": 正确选项下标, "explain": 解析}]}
"""
from __future__ import annotations

import json
import math
from collections import deque
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import bfsdata  # noqa: E402
import binarydata  # noqa: E402
import bsearchdata  # noqa: E402
import complexitydata  # noqa: E402
import deadlinedata  # noqa: E402
import dijkstradata  # noqa: E402
import dividedata  # noqa: E402
import dpintrodata  # noqa: E402
import dsudata  # noqa: E402
import fibdata  # noqa: E402
import floatdata  # noqa: E402
import foodchaindata  # noqa: E402
import griddata  # noqa: E402
import hanoidata  # noqa: E402
import intervaldata  # noqa: E402
import kadanedata  # noqa: E402
import knapdata  # noqa: E402
import knapvardata  # noqa: E402
import knightdata  # noqa: E402
import lcsdata  # noqa: E402
import lightsdata  # noqa: E402
import lisdata  # noqa: E402
import matrixdata  # noqa: E402
import partitiondata  # noqa: E402
import permdata  # noqa: E402
import queensdata  # noqa: E402
import runtimedata  # noqa: E402
import shoppingdata  # noqa: E402
import sortdata  # noqa: E402
import stackdata  # noqa: E402
import statebfsdata  # noqa: E402
import subsetsdata  # noqa: E402
import triangledata  # noqa: E402

INV_ARR = [3, 1, 4, 5, 2]
MERGE_L, MERGE_R = [1, 4, 6], [2, 3, 5]
POSTFIX = ["4", "2", "5", "*", "+", "6", "-"]
RAIN = [3, 0, 2, 0, 4]
BAD_PAREN = "([)]"
FIB_N = 7
HANOI_N, HANOI3_STEP, HANOI_BIG = 5, 4, 4
PERM_A, PERM_K = [1, 2, 3, 4], 10
SUBSET = [1, 2, 3]
QUEENS_N = 6
DSU_N, DSU_OPS = 4, [(0, 1), (2, 3), (1, 3)]
REL_N, REL_PAIRS = 8, [(0, 1), (2, 3), (1, 2), (0, 3), (5, 6)]
CYCLE = [(0, 1), (1, 2), (2, 3), (3, 1)]
MERGE_IV = [[2, 3], [1, 10], [11, 12], [4, 6]]
BALLOONS = [[1, 2], [3, 4], [2, 3], [4, 5]]
GROUPS = [(1, 3), (2, 4), (3, 5), (6, 7)]
COINS, AMOUNT = [1, 4, 5], 8
TRI = [[7], [5, 5], [9, 4, 7], [0, 9, 0, 0]]
KW, KV, KCAP = [1, 3, 4], [15, 20, 30], 4
LCS_PAIR = ("ABCBDAB", "BDCABA")
ED_PAIR = ("intention", "execution")
MAZE = ["..#.", ".#..", "....", "#.#."]
MAT = [[0, 1, 1], [1, 1, 1], [1, 1, 0]]
GRAPH = [[(1, 2), (2, 6)], [(2, 3), (3, 7)], [(3, 1), (4, 5)], [(4, 2)], []]
RIVER = (20, 1, [4, 9, 13, 17])
MONTH, MONTH_M = [7, 2, 5, 10, 8], 2
BIN_BITS, BIN_NEG, BIN_ADD = 0b11100110, -12, (100, 50)
FLOAT_X, FLOAT_SUM, FLOAT_EXACT = 10.0, (0.1, 0.7), ["0.75", "0.1", "0.2", "0.3"]
ROT = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
SPIRAL_Q = (5, 1, 1)                     # 5×5 螺旋矩阵第 2 行第 2 列（下标从 0）
LIGHT_ON = [(0, 0)]                      # 5×6 盘面只有左上角亮


def Q(q, right, wrong, explain):
    """right 是正确选项文字，wrong 是干扰项；去重后打乱在 build() 里做。"""
    return {"q": q, "right": str(right), "wrong": [str(w) for w in wrong], "explain": explain}


def seq(xs):
    return ", ".join(str(x) for x in xs)


def ivs(xs):
    return " ".join(f"[{a}, {b}]" for a, b in xs)


def q_sort():
    _, inv = sortdata.count_inversions(INV_ARR)
    ev, _ = sortdata.merge_count_trace(MERGE_L, MERGE_R)
    first_r = next(e for e in ev if e[0] == "R")
    _, after = sortdata.two_pass(sortdata.ROWS)
    order = lambda rows: "、".join(f"{k}{v}" for k, v in rows)  # noqa: E731
    return [
        Q(f"数组 [{seq(INV_ARR)}] 里一共有多少个逆序对？",
          inv, [inv - 1, inv + 1, len(INV_ARR) * (len(INV_ARR) - 1) // 2],
          "逆序对是前大后小的一对：(3, 1)、(3, 2)、(4, 2)、(5, 2)。10 是全部数对的个数。归并时右半的元素先落下，就一次加上左半还没落下的个数。"),
        Q(f"归并统计逆序对：左半 [{seq(MERGE_L)}]、右半 [{seq(MERGE_R)}] 都已有序。"
          f"右半的 {MERGE_R[first_r[2]]} 先落下时，计数器一次加几？",
          first_r[3], [1, len(MERGE_L), 0],
          f"左半还剩 {first_r[3]} 个数没落下，它们都比 {MERGE_R[first_r[2]]} 大，各和它组成一个逆序对，所以一次加一批。"),
        Q("三条记录 a2、b1、c2（字母是名字，数字是分数）。先按名字排一次，再用稳定排序按分数排一次，结果是？",
          order(after), ["b1、c2、a2", "a2、c2、b1", "c2、a2、b1"],
          "稳定排序不打乱分数相同的记录，第一次按名字排好的 a 在 c 前面，这个先后会保留下来。"),
    ]


def q_stack():
    val = stackdata.eval_postfix(POSTFIX)
    ok, ev = stackdata.is_valid_trace(BAD_PAREN)
    assert not ok
    bad = ev[-1]                               # ("pop", i, top, False)
    right = f"读到第 {bad[1] + 1} 个字符 {BAD_PAREN[bad[1]]} 时，弹出的栈顶是 {bad[2]}，配不上"
    return [
        Q(f"后缀表达式 {' '.join(POSTFIX)} 的值是？", f"{val:g}", ["-8", "24", "12"],
          "遇到运算符弹两次：先弹出的是右操作数。4 + 2×5 = 14，再 14 − 6 = 8；把减法的两个数弄反会得到 −8。"),
        Q(f"柱高 [{seq(RAIN)}]（每柱宽 1），能接多少单位雨水？",
          stackdata.trap(RAIN), [6, 4, 9],
          "单调栈每弹出一个低洼，就按「左右两墙较矮者 − 洼底」乘宽度结一层水：3 + 1 + 3 = 7。"),
        Q(f"用栈检查括号串 {BAD_PAREN}，在哪一步判为不合法？", right,
          ["读完全部字符后，栈里还剩括号", f"读到第 4 个字符 {BAD_PAREN[3]} 时，栈已经空了", "它是合法的：每种括号都成对出现"],
          "右括号必须和最近一个没配上的左括号同类；只数个数相等是不够的。"),
    ]


def q_fib():
    calls = fibdata.naive_calls(FIB_N)
    memo = fibdata.facts(FIB_N)["memo_calls"]
    return [
        Q(f"朴素递归求 fib({FIB_N})（fib(1) = fib(2) = 1 为基例），一共调用几次 fib？",
          calls, [fibdata.fib(FIB_N), memo, 2 ** (FIB_N - 1)],
          f"调用次数 C(n) = C(n−1) + C(n−2) + 1，C(1) = C(2) = 1，推到 C({FIB_N}) = {calls}。"),
        Q(f"加上 lru_cache 记忆化后，fib({FIB_N}) 实际发生的调用（含查表直接返回的）有几次？",
          memo, [FIB_N, calls, FIB_N - 1],
          "每个参数只真算一次，其余同参调用查表返回、子树整个消失，调用树塌成一条链加一排查表。"),
        Q("朴素递归 fib(n) 的调用次数随 n 怎样增长？",
          "指数增长，n 每加 1 约乘 1.618", ["线性增长，和 n 成正比", "平方增长，和 n² 成正比", "n log n"],
          "C(n) = 2·fib(n) − 1，和斐波那契数本身同阶，而 fib(n) 按黄金比例增长。"),
    ]


def q_hanoi():
    mv = hanoidata.moves(3)
    k, s, d = mv[HANOI3_STEP - 1]
    fmt = lambda m: f"把 {m[0]} 号盘从 {m[1]} 移到 {m[2]}"  # noqa: E731
    root = hanoidata.call_tree(HANOI_BIG)[0]
    return [
        Q(f"{HANOI_N} 片金片的汉诺塔，最少要移动几步？",
          hanoidata.count(HANOI_N), [2 ** HANOI_N, HANOI_N * HANOI_N, 2 * HANOI_N - 1],
          "T(n) = 2T(n−1) + 1：先把上面 n−1 片挪开，移最大的一片，再把 n−1 片挪回来，得 2ⁿ − 1。"),
        Q("3 片从 A 移到 C（B 作中转，1 号最小），第 4 步是哪一步？",
          fmt((k, s, d)), [fmt(mv[2]), fmt(mv[4]), fmt((3, "A", "B"))],
          "前 3 步把上面 2 片挪到 B，第 4 步正好轮到最大的 3 号盘从 A 直接到 C。"),
        Q(f"{HANOI_BIG} 片时，最大的盘在第几步移动？",
          root.inorder, [2 ** HANOI_BIG, 2 ** HANOI_BIG - 1, 1],
          f"最大的盘要等上面 {HANOI_BIG - 1} 片全部挪开（2^{HANOI_BIG - 1} − 1 步）之后才动，所以是第 2^{HANOI_BIG - 1} 步。"),
    ]


def q_perm():
    nodes = permdata.perm_tree(PERM_A)
    leaves = [nd.path for nd in nodes if not nd.children]
    cat = lambda p: "".join(map(str, p))  # noqa: E731
    sub = [nd.path for nd in permdata.subset_tree(SUBSET) if not nd.children]
    pos = sub.index((1, 3)) + 1
    return [
        Q(f"按讲义的回溯（used 数组、下标从小到大试），[{seq(PERM_A)}] 收集到的第 {PERM_K} 个排列是？",
          cat(leaves[PERM_K - 1]), [cat(leaves[PERM_K - 2]), cat(leaves[PERM_K]), "2431"],
          "下标升序试探，叶子按字典序出现：以 1 开头的 6 个之后，第 7～12 个以 2 开头。"),
        Q(f"n = {len(PERM_A)} 的全排列决策树（含根）一共几个节点？",
          permdata.node_total(len(PERM_A)), [24, 64, sum(len(PERM_A) ** k for k in range(len(PERM_A) + 1))],
          "第 k 层有 n!/(n−k)! 个节点：1 + 4 + 12 + 24 + 24 = 65。24 只是叶子数；341 是不排除已用数字时（每层都有 4 个分支）的节点数。"),
        Q(f"子集的决策树：对 [{seq(SUBSET)}] 每个数先走「不选」、再走「选」，只在叶子收答案。{{1, 3}} 是第几个收到的？",
          pos, [3, 5, 2],
          "叶子顺序就是把「选 = 1」看成二进制从小到大：000、001、010、011、100、101……{1, 3} 是 101，第 6 个。"),
    ]


def q_queens():
    sols = queensdata.solve_queens(4)
    sp = lambda t: " ".join(map(str, t))  # noqa: E731
    return [
        Q(f"{QUEENS_N} 皇后问题一共有几个解？",
          len(queensdata.solve_queens(QUEENS_N)), [2, 10, QUEENS_N],
          "回溯逐行放置、三个集合剪枝即可数出：4 皇后 2 个、5 皇后 10 个、6 皇后反而只有 4 个，解数不随 n 单调。"),
        Q("4 皇后按讲义写法（逐行放、列号从小到大试）找到的第一个解是？（第 i 个数是第 i 行皇后的列号）",
          sp(sols[0]), [sp(sols[1]), "1 3 2 4", "1 4 2 3"],
          "第一行放第 1 列的所有分支都会走进死路，第一个解从第 1 行放第 2 列开始。"),
        Q("4 皇后用列、主对角线、副对角线三个集合剪枝，实际递归调用（含根）多少次？",
          queensdata.pruned_nodes(4), [queensdata.perm_nodes(4), queensdata.naive_nodes(4), 24],
          "只保证不同列要 65 个节点，放到底再检查要 341 个；冲突的格子在循环里直接跳过，只剩 17 次调用。"),
    ]


def q_dsu():
    d = dsudata.DSU(DSU_N)
    for a, b in DSU_OPS:
        d.union(a, b)
    before = d.parent[3]
    d.find(3)
    r = dsudata.DSU(REL_N)
    for a, b in REL_PAIRS:
        r.union(a, b)
    c = dsudata.DSU(4)
    first = next(e for e in CYCLE if not c.union(*e))
    ops = "、".join(f"union({a}, {b})" for a, b in DSU_OPS)
    return [
        Q(f"讲义的 DSU（按大小合并，大小相等时把 y 的根挂到 x 的根下；find 做路径压缩），n = {DSU_N}，依次 {ops}，"
          f"再调用 find(3)。之后 parent[3] 是？",
          d.parent[3], [before, 1, 3],
          f"union(1, 3) 时两棵树一样大，把 3 所在树的根 2 挂到 0 下，3 仍指着 2；find(3) 一路找到根 0，再把 3 直接改指 0。"),
        Q(f"{REL_N} 个人，信同一宗教的关系有 {ivs(REL_PAIRS)}。最多有几种不同的宗教？",
          r.count, [REL_N - len(REL_PAIRS), REL_N - len(REL_PAIRS) + 2, 2],
          "每次 union 成功集合数才减 1；(0, 3) 时两人已在同一集合，union 返回 False，不能再减。"),
        Q(f"无向图依次加边 {ivs(CYCLE)}，用并查集判环，哪条边第一次让 union 返回 False（出现环）？",
          f"({first[0]}, {first[1]})", [f"({a}, {b})" for a, b in CYCLE if (a, b) != first],
          "加边前两端已经连通，再连就成环；1、2、3 在加 (2, 3) 之后已经连通。"),
    ]


def q_interval():
    good = intervaldata.merge(MERGE_IV)
    bad = intervaldata.merge_no_max(MERGE_IV)
    shots = intervaldata.find_min_arrow_shots(BALLOONS)
    groups = intervaldata.min_groups(GROUPS)
    return [
        Q(f"合并区间 {ivs(MERGE_IV)}，结果是？",
          ivs(good), [ivs(bad), "[1, 12]", ivs(sorted(MERGE_IV))],
          "按左端点排序后扫描，重叠就延长；延长时要取 max(原右端点, 新右端点)，直接赋值会被 [2, 3] 缩短。"),
        Q(f"气球的水平区间为 {ivs(BALLOONS)}（端点碰到也算射中），最少几支箭？",
          shots, [1, 3, 4],
          "按右端点排序，每支箭射在当前气球的右端点上；只要下一个气球左端点不超过箭的位置，就一起射穿。"),
        Q(f"闭区间 {ivs(GROUPS)} 要分成若干组，组内互不相交（端点相同也算相交），最少几组？",
          groups, [groups - 1, groups + 1, 1],
          "答案等于同一时刻最多重叠的区间数：在 3 这一点上 [1, 3]、[2, 4]、[3, 5] 同时覆盖。"),
    ]


def q_dpintro():
    greedy = dpintrodata.greedy_coins(COINS, AMOUNT)
    dp = dpintrodata.dp_coins(COINS, AMOUNT)
    fixed, naive = dpintrodata.fixed_odd(TRI), dpintrodata.naive_odd(TRI)
    top = max(s for _, s in dpintrodata.all_paths(TRI))
    rows = " / ".join(" ".join(map(str, r)) for r in TRI)
    return [
        Q(f"硬币面值 {seq(COINS)}，凑出 {AMOUNT} 最少要几枚？",
          len(dp), [len(greedy), len(dp) + 1, 1],
          f"贪心先拿最大的 5，剩下只能 1+1+1，共 {len(greedy)} 枚；DP 发现 4 + 4 只要 {len(dp)} 枚。"),
        Q(f"数字三角形（从上到下，每步走到正下或右下）：{rows}。路径和为奇数的最大值是？",
          fixed, [naive, top, -1],
          f"只记「到这格的最大和」会丢掉奇偶信息，最后在底行挑奇数得 {naive}；补一维奇偶后才得到 {fixed}。{top} 是最大和，但它是偶数。"),
        Q("上一题里，朴素状态「dp[i][j] = 到 (i, j) 的最大路径和」为什么会算错？",
          "最大和可能是偶数，被丢掉的次大奇数和才有用", ["三角形太小，DP 不适用", "转移方程少考虑了左下方向", "dp 数组下标越界"],
          "状态要带上后面还用得到的信息。把奇偶补进状态，dp[i][j][p] 记奇偶为 p 的最大和。"),
    ]


def q_knap():
    best = knapdata.knapsack_2d(KW, KV, KCAP)[-1][KCAP]
    unb = knapdata.unbounded_knapsack(KW, KV, KCAP)
    pick = knapdata.chosen(KW, KV, KCAP)
    items = "、".join(f"重 {w} 值 {v}" for w, v in zip(KW, KV))
    nm = lambda s: "第 " + "、".join(map(str, s)) + " 件"  # noqa: E731
    return [
        Q(f"0/1 背包：物品 {items}，容量 {KCAP}，最大价值是？",
          best, [unb, max(KV), sum(KV)],
          f"表的最后一格 dp[3][4] = {best}：前两件刚好装满。{unb} 是同一件反复拿的结果，不符合 0/1 背包。"),
        Q("同一组数据，一维滚动数组的容量循环误写成从小到大（正序），算出的结果是？",
          unb, [best, max(KV), 0],
          "正序时 dp[c − w] 可能已经是本轮更新过的值，等于同一件物品又拿了一次——这就成了完全背包。"),
        Q("从 dp 表右下角倒推，最优方案选了哪几件？",
          nm(pick), [nm([3]), nm([1, 3]), nm([2, 3])],
          "倒推：dp[i][c] 和上一行同值就是没拿第 i 件，不同就是拿了，容量减去它的重量继续往上。"),
    ]


def q_lcs():
    s, t = LCS_PAIR
    a, b = ED_PAIR
    n = lcsdata.lcs(s, t)
    e = lcsdata.edit_distance(a, b)
    return [
        Q(f"{s} 和 {t} 的最长公共子序列长度是？", n, [n - 1, n + 1, n - 2],
          "末字符相同走左上 + 1，不同取上、左较大者；例如 BCBA 就是一个长度 4 的公共子序列。"),
        Q(f"把 {a} 变成 {b}，最少几次编辑（插入、删除、替换一个字符各算 1 次）？", e, [e - 1, e + 1, len(a) - 1],
          "第一列是 i（删光）、第一行是 j（全插入），其余格子末字符相同抄左上，不同取三邻最小加 1。"),
        Q("编辑距离表里，dp[i][j] 取自正上方 dp[i−1][j] + 1，对应的操作是？",
          "删除 s 的第 i 个字符", ["在 s 后面插入 t 的第 j 个字符", "把 s 的第 i 个字符替换成 t 的第 j 个", "两个末字符相同，什么都不做"],
          "从上方来：t 的前缀不变、s 少了一个字符，就是删除；从左边来是插入，从左上来是替换或保留。"),
    ]


def q_bfs():
    ans, _, _ = bfsdata.maze_trace(MAZE, (0, 0), (3, 3))
    dist = bfsdata.update_matrix(MAT)
    twice = bfsdata.enqueue_log(False).count("c")
    rows = " / ".join(MAZE)
    return [
        Q(f"迷宫（# 是墙，按行写）{rows}，从左上角走到右下角，上下左右各算一步，最少几步？",
          ans, [ans - 2, ans + 2, -1],
          "从起点一圈圈往外推，第一次弹出终点时的层数就是最少步数；最少也要 6 步（曼哈顿距离），这里刚好走得通。"),
        Q("矩阵 0 1 1 / 1 1 1 / 1 1 0，求每格到最近的 0 的距离。右上角那格是？",
          dist[0][2], [1, 3, 4],
          "多源 BFS：所有 0 一起入队当第 0 层，波纹同时外扩；右上角离两个 0 都是 2 步。"),
        Q("图 s→a、s→b、a→c、b→c。BFS 如果改成「出队时才标记已访问」，c 会进队几次？",
          twice, [1, 0, 3],
          "a 和 b 出队时 c 都还没出队、没被标记，于是进队两次。入队就标记，每个点只进队一次。"),
    ]


def q_dijkstra():
    dist, ev = dijkstradata.dijkstra_trace(len(GRAPH), GRAPH, 0)
    stale = sum(1 for e in ev if e[0] == "stale")
    hop = dijkstradata.bfs_hops_cost(len(GRAPH), GRAPH, 0)
    edges = "，".join(f"{u}→{v} 权 {w}" for u, lst in enumerate(GRAPH) for v, w in lst)
    return [
        Q(f"有向图：{edges}。从 0 出发，到 4 的最短距离是？",
          dist[4], [hop[4], dist[4] + 1, 7],
          f"Dijkstra 每次弹出距离最小的点再松弛它的出边，最短路 0→1→2→3→4 = 2 + 3 + 1 + 2 = {dist[4]}。"
          f"按边数最少的 BFS 走 0→2→4 会得到 {hop[4]}。"),
        Q("上一题按讲义写法（堆里放 (距离, 点)，出堆时 d > dist[u] 就跳过），一共弹出了几条过期条目？",
          stale, [0, stale - 1, stale + 1],
          "同一个点被更短的距离再次松弛时，旧条目留在堆里不删；它后来被弹出时距离已经过期，直接跳过。"),
        Q("为什么出堆时遇到 d > dist[u] 可以直接跳过？",
          "这是旧的、更长的距离，u 已经用更短的距离处理过了", ["说明图里有负权边", "说明 u 不可达", "堆坏了，需要重建"],
          "懒删除：不去堆里找旧条目，而是弹出时检查是否还新鲜，代价只是堆里多几条记录。"),
    ]


def q_bsearch():
    L, m, rocks = RIVER
    ans, _ = bsearchdata.river_rounds(L, m, rocks)
    ans0, _ = bsearchdata.river_rounds(L, 0, rocks)
    month, _ = bsearchdata.monthly_rounds(MONTH, MONTH_M)
    return [
        Q(f"河宽 {L}，石头在 {seq(rocks)}，最多移走 {m} 块，最短跳跃距离最大能是多少？",
          ans, [ans0, ans + 1, ans - 2],
          f"二分答案 gap，判定函数从左往右贪心：离上一块保留的石头不足 gap 就移走。一块都不移时只有 {ans0}。"),
        Q(f"每月开销 {seq(MONTH)}，要分成不超过 {MONTH_M} 个连续段，让最大段和尽量小，这个最小值是？",
          month, [max(MONTH), sum(MONTH) // MONTH_M, sum(MONTH)],
          "在 [最大单月, 总和] 上二分上限，判定时贪心地往当前段里加，超了就开新段，段数不超过 m 就可行。"),
        Q("求「最大的可行值」时写成 lo = mid、hi = mid − 1，为什么 mid 要取 (lo + hi + 1) // 2？",
          "下取整时 mid 可能等于 lo，可行就 lo = mid，区间不缩，死循环",
          ["上取整算得更快", "防止整数溢出", "下取整会漏掉答案为 0 的情况"],
          "lo + 1 = hi 时下取整得 mid = lo，判定可行后区间原地不动；上取整保证每轮至少缩一格。"),
    ]


def _neg(v):
    return str(v).replace("-", "−")


def q_binary():
    s = binarydata.to_signed8(BIN_BITS)
    bits = format(BIN_BITS, "08b")
    t = binarydata.add8_trace(*BIN_ADD)
    return [
        Q(f"8 位补码 {bits[:4]} {bits[4:]} 表示的整数是多少？", _neg(s),
          [str(BIN_BITS), _neg(-int(bits[1:], 2)), _neg(-int(binarydata.invert(bits)[1:], 2))],
          f"最高位是 1，是负数；按无符号读是 {BIN_BITS}，减去 256 得 {_neg(s)}。按原码、反码读会得到另两个数。"),
        Q(f"{_neg(BIN_NEG)} 的 8 位补码是哪一个？", binarydata.to_twos_complement(BIN_NEG),
          [binarydata.sign_magnitude(BIN_NEG), binarydata.ones_complement(BIN_NEG), format(-BIN_NEG, "08b")],
          f"{-BIN_NEG} = {format(-BIN_NEG, '08b')}，取反再加一。{binarydata.sign_magnitude(BIN_NEG)} 是原码，"
          f"{binarydata.ones_complement(BIN_NEG)} 是反码。"),
        Q(f"8 位补码下计算 {BIN_ADD[0]} + {BIN_ADD[1]}，结果按补码读是多少？", _neg(t["sr"]),
          [str(sum(BIN_ADD)), _neg(-(sum(BIN_ADD) - 128)), _neg(t["sr"] + 1)],
          f"结果位串 {t['r']}，最高位为 1；{sum(BIN_ADD)} 超出 −128 ~ 127，上溢，读出来是 {_neg(t['sr'])}。"),
    ]


def q_float():
    s, stored, true_e = floatdata.decode(FLOAT_X)[:3]
    a, b = FLOAT_SUM
    got = repr(a + b)
    exact = [x for x in FLOAT_EXACT if floatdata.Fraction(float(x)) == floatdata.Fraction(x)]
    assert len(exact) == 1, exact
    return [
        Q(f"双精度浮点数 {FLOAT_X:g} 的指数字段存的是多少（十进制）？", stored,
          [true_e, floatdata.BIAS, stored + 1],
          f"{FLOAT_X:g} = 1.01₂ × 2^{true_e}，真实指数 {true_e} 加偏移量 {floatdata.BIAS}，存成 {stored}。"),
        Q(f"Python 里 print({a} + {b}) 的输出是？", got,
          [f"{a + b:.1f}", "0.8000000000000001", "0.7999999999999998"],
          "0.1 和 0.7 都不能精确存储，两个近似值的和落在 0.8 存储值左边那一格，repr 就把这一格如实打印出来。"),
        Q("下面哪个小数能被双精度浮点数精确表示？", exact[0], [x for x in FLOAT_EXACT if x != exact[0]],
          "只有分母是 2 的幂的分数才能精确表示：0.75 = 3/4。0.1、0.2、0.3 的二进制都是无限循环。"),
    ]


def q_matrix():
    a = [[0] * 3] * 2
    a[1][2] = 5
    rot = matrixdata.rotate_cw(ROT)
    n, i, j = SPIRAL_Q
    sp = matrixdata.spiral(n)[0]
    return [
        Q("a = [[0] * 3] * 2，执行 a[1][2] = 5 后，a[0] 是什么？", a[0], [[0, 0, 0], [5, 0, 0], "报错"],
          "乘号复制的是引用，a[0] 和 a[1] 是同一个列表。要写 [[0] * 3 for _ in range(2)]。"),
        Q(f"a = {ROT}，[list(r) for r in zip(*a[::-1])] 的第一行是？", rot[0],
          [matrixdata.transpose(ROT)[0], matrixdata.rotate_ccw(ROT)[0], ROT[-1]],
          f"先上下翻转再转置，就是顺时针转 90°：原来第一列从下往上读 {rot[0]}，成为新的第一行；3×4 转完变 4×3。"),
        Q(f"按螺旋顺序（先向右，碰壁右转）把 1 到 {n * n} 填进 {n}×{n} 矩阵，第 {i + 1} 行第 {j + 1} 列是几？",
          sp[i][j], [n * n, sp[i][j] - 1, sp[i][j] + n],
          f"外圈 {4 * (n - 1)} 个数走完回到第 2 行第 1 列，下一步右转进入第 2 行第 2 列，就是 {sp[i][j]}。"),
    ]


def q_lights():
    corner = len(lightsdata.neighbors(0, 0))
    g = [[0] * lightsdata.C for _ in range(lightsdata.R)]
    for r, c in LIGHT_ON:
        g[r][c] = 1
    press = sum(map(sum, lightsdata.solve(g)))
    return [
        Q("5×6 的熄灯盘面上，按下左上角的按钮会翻转几盏灯？", corner, [5, 4, 2],
          "自己、右边、下边；左边和上边在盘面外。"),
        Q("第一行的按法定下以后，第 2 行第 c 列按不按由什么决定？", "第 1 行第 c 列此时还亮不亮",
          ["再枚举一遍", "第 3 行第 c 列亮不亮", "第 2 行第 c 列自己亮不亮"],
          "第 1 行第 c 列的灯此后只有它正下方的按钮能动，亮着就必须按，所以下面每行都是被逼出来的。"),
        Q("5×6 盘面只有左上角一盏灯亮，其余全灭。要全部熄灭，一共要按几个按钮（答案唯一）？", press,
          [1, 3, press + 2],
          f"只按左上角会把右边、下边的灯点亮；枚举第一行推到底，唯一可行的按法一共要按 {press} 个。"),
    ]


SUBS_CANDS, SUBS_TARGET = [3, 5, 2], 8   # 组合总和新输入（片中是 [2, 3, 6, 7]、7）；故意不按序给出
SUBS_A, SUBS_K = [1, 2, 3, 4], 6         # 往后挑的子集树：第 SUBS_K 个收到的子集


def q_subsets():
    res = subsetsdata.combination_sum(SUBS_CANDS, SUBS_TARGET)
    seqs = []                                  # 常见错误：每层都从头挑（忘了起始下标），把顺序不同的算成不同组合

    def ordered(rest, path):
        if rest == 0:
            seqs.append(path)
            return
        for x in SUBS_CANDS:
            if x <= rest:
                ordered(rest - x, path + [x])
    ordered(SUBS_TARGET, [])
    unsorted = []                              # 常见错误：没排序就 break，会把后面更小的数一起剪掉

    def no_sort(start, rest, path):
        if rest == 0:
            unsorted.append(path)
            return
        for i in range(start, len(SUBS_CANDS)):
            if SUBS_CANDS[i] > rest:
                break
            no_sort(i, rest - SUBS_CANDS[i], path + [SUBS_CANDS[i]])
    no_sort(0, SUBS_TARGET, [])
    no_rep = [c for c in subsetsdata.subsets_start(SUBS_CANDS) if sum(c) == SUBS_TARGET]   # 错把 i 写成 i + 1
    brk = len(subsetsdata.csum_tree(SUBS_CANDS, SUBS_TARGET, "break"))
    none = len(subsetsdata.csum_tree(SUBS_CANDS, SUBS_TARGET, "none"))
    cmp_cont = subsetsdata.csum_compares(SUBS_CANDS, SUBS_TARGET, "continue")
    order = subsetsdata.subsets_start(SUBS_A)
    pick = subsetsdata.subsets_pick(SUBS_A)
    lst = lambda xs: "[" + ", ".join(map(str, xs)) + "]"  # noqa: E731
    return [
        Q(f"组合总和：候选数 [{seq(SUBS_CANDS)}]，每个数可重复用，和为 {SUBS_TARGET} 的组合有几个？",
          len(res), [len(seqs), len(no_rep), len(unsorted)],
          f"{len(res)} 个：{'、'.join(lst(c) for c in res)}。每层都从头挑会把 2+3+3 和 3+2+3 当成不同的，数出 {len(seqs)} 个；"
          f"递归传 i + 1（不能重复用）只剩 {lst(no_rep[0])} 一个；不先排序就 break，会漏成 {len(unsorted)} 个。"),
        Q(f"同一题按讲义写法（先排序，candidates[i] > rest 就 break），dfs 一共被调用几次（含根）？",
          brk, [none, cmp_cont, len(res)],
          f"剪掉的都是「走进去才发现超了」的死节点：不剪枝要 {none} 次调用，break 后只剩 {brk} 次。"
          f"{cmp_cont} 是改用 continue 时的比较次数，节点数不变、比较更多。"),
        Q(f"用「从起始下标往后挑、每个节点都收」的写法求 [{seq(SUBS_A)}] 的子集，第 {SUBS_K} 个收到的是？",
          lst(order[SUBS_K - 1]), [lst(pick[SUBS_K - 1]), lst(order[SUBS_K - 2]), lst(order[SUBS_K])],
          f"先序遍历：[ ]、[1]、[1, 2]、[1, 2, 3]、[1, 2, 3, 4] 之后退回 [1, 2] 挑 4，得到 {lst(order[SUBS_K - 1])}。"
          f"{lst(pick[SUBS_K - 1])} 是「选或不选、先不选」那棵树的第 {SUBS_K} 个叶子。"),
    ]


KNIGHT_Q = (3, 4, 0, 0)                  # 3 行 4 列、从左上角出发的马走日
KNIGHT_FORGET = (3, 3, 0, 0)             # 3×3 从角上出发、忘了回溯那一行
LAKE_Q = ["WW..W", "...W.", "W....", ".W.WW"]


def q_knight():
    n, m, sx, sy = KNIGHT_Q
    tours = knightdata.knight_tours(n, m, sx, sy)
    forgot = knightdata.knight_trace(n, m, sx, sy, undo=False)[0]
    fn, fm, fx, fy = KNIGHT_FORGET
    f_calls = knightdata.knight_trace(fn, fm, fx, fy, undo=False)[1]
    ok_calls = knightdata.knight_trace(fn, fm, fx, fy)[1]
    lakes = knightdata.count_lakes(LAKE_Q)
    lakes4 = len(_lakes4(LAKE_Q))
    return [
        Q(f"讲义的 knight_tours({n}, {m}, {sx}, {sy}) 输出几？（{n} 行 {m} 列，马从左上角出发，不重复地走遍所有格子）",
          tours, [forgot, 0, n * m],
          f"回溯枚举所有走法，{n}×{m} 从角上出发恰有 {tours} 种；忘了撤销标记时每格只进一次，最多走出 1 条。"),
        Q(f"网格 {' / '.join(LAKE_Q)}（W 是水，八个方向相连的水算一个湖）有几个湖？",
          lakes, [lakes4, knightdata.water(LAKE_Q), lakes - 1],
          f"斜着挨着也算相连；只看上下左右会数出 {lakes4} 个；把每格水都当成一个湖（灌水后误加撤销）会数出 "
          f"{knightdata.water(LAKE_Q)} 个。"),
        Q(f"马走日在 {fn}×{fm} 棋盘上从角上出发，忘了写 visited[nx][ny] = False，dfs 一共被调用几次？",
          f_calls, [fn * fm, ok_calls, 1],
          f"不撤销时每格最多进一次，调用次数等于马从角上能跳到的格子数；{fn}×{fm} 的中心格马跳不到，"
          f"所以是 {f_calls} 次（正确回溯版要 {ok_calls} 次，答案仍是 0）。"),
    ]


def _lakes4(grid):
    """只算上下左右相连时的湖（常见错误理解，作干扰项）。"""
    cells = {(i, j) for i, row in enumerate(grid) for j, ch in enumerate(row) if ch == "W"}
    out = []
    while cells:
        st, comp = [cells.pop()], set()
        while st:
            x, y = st.pop()
            comp.add((x, y))
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in cells:
                    cells.remove(q)
                    st.append(q)
        out.append(comp)
    return out


STAIR_Q = 8                                  # 爬到第 8 级
TRI_Q = [[3], [2, 8], [9, 1, 4], [7, 1, 2, 2]]


def q_triangle():
    ways = triangledata.climb_stairs(STAIR_Q)
    off = triangledata.climb_table(STAIR_Q - 1)[-1]            # 边界写成 dp[0] = 0、dp[1] = 1：错一位
    best = triangledata.max_path_sum(TRI_Q)
    j, greedy = 0, TRI_Q[0][0]                                 # 贪心：每步走到下一行较大的那个
    for i in range(1, len(TRI_Q)):
        j += TRI_Q[i][j + 1] > TRI_Q[i][j]
        greedy += TRI_Q[i][j]
    rowmax = sum(max(r) for r in TRI_Q)
    rows = " / ".join(" ".join(map(str, r)) for r in TRI_Q)
    i2 = len(TRI_Q) - 2
    after = [v for i, _, _, _, v in triangledata.roll_log(TRI_Q) if i == i2]
    after = after + TRI_Q[-1][len(after):]                     # 本轮没写到的位置保持底行原值
    r2l = TRI_Q[-1][:]                                         # 常见错误：内层循环从右往左
    for k in range(i2, -1, -1):
        r2l[k] = TRI_Q[i2][k] + max(r2l[k], r2l[k + 1])
    lst = lambda xs: "[" + ", ".join(map(str, xs)) + "]"      # noqa: E731
    return [
        Q(f"每次爬 1 级或 2 级，爬到第 {STAIR_Q} 级有几种爬法？（站在地面算一种：dp[0] = 1）",
          ways, [off, 2 ** (STAIR_Q - 1), ways + off],
          f"dp[i] = dp[i−1] + dp[i−2]，dp[0] = dp[1] = 1，一路加到 dp[{STAIR_Q}] = {ways}。"
          f"把边界写成 dp[0] = 0 会整体错一位，得到 {off}。"),
        Q(f"数字三角形（每步走到正下或右下）：{rows}。从顶到底的最大路径和是？",
          best, [greedy, rowmax, best - 1],
          f"每步挑下一行较大的那个是贪心，只得 {greedy}；{rowmax} 是每行最大值相加，但它们连不成一条路径。"
          f"自底向上填表，顶上一格就是 {best}。"),
        Q(f"对上一题的三角形运行一维滚动版 max_path_sum_1d：dp 先抄底行，处理完倒数第二行之后，dp 数组是？",
          lst(after), [lst(r2l), lst(TRI_Q[-1]), lst(after[:i2 + 1])],
          "从左往右改，改第 j 位时读的第 j+1 位还是底行旧值，所以正确；从右往左改会读到本轮刚改过的值。"
          "数组长度不变，只是最右一位以后不再用到。"),
    ]


# 1) import 区加：import kadanedata  # noqa: E402
# 2) 新输入常量（片中都没出现过）放到常量区：
KAD_ARR = [3, -4, 5, -1, 2, -6, 4]
KAD_MAT = [[2, -1, -4], [-3, 5, 2], [1, -2, 3]]
ROB_H = [3, 4, 3, 1, 5]
# 3) BUILDERS 里加 "kadane": q_kadane


def q_kadane():
    best = kadanedata.max_subarray(KAD_ARR)
    last = kadanedata.kadane_trace(KAD_ARR)[0][-1]            # 错把 dp[n-1] 当答案
    pos = sum(v for v in KAD_ARR if v > 0)                    # 忽略「连续」，正数全加
    sub = kadanedata.max_submatrix(KAD_MAT)
    _, st, sb, sl, sr = kadanedata.best_submatrix(KAD_MAT)
    row_only = max(kadanedata.max_subarray(r) for r in KAD_MAT)   # 只枚举了上边 = 下边
    top_cell = max(max(r) for r in KAD_MAT)
    total = sum(map(sum, KAD_MAT))
    rob = kadanedata.rob(ROB_H)
    picks = "、".join(str(k + 1) for k in kadanedata.rob_choice(ROB_H))
    greedy, left = 0, set(range(len(ROB_H)))                   # 贪心：每次拿剩下最大的一家，再划掉两个邻居
    while left:
        k = max(left, key=lambda i: (ROB_H[i], -i))
        greedy += ROB_H[k]
        left -= {k - 1, k, k + 1}
    mat = " ".join("[" + ", ".join(map(str, r)) + "]" for r in KAD_MAT)
    return [
        Q(f"数组 {seq(KAD_ARR)} 的最大子段和（连续一段，至少一个数）是？",
          best, [last, pos, max(KAD_ARR)],
          f"dp[i] 是以第 i 格结尾的最大和，答案是 max(dp) = {best}，不是最后一格的 dp = {last}；"
          f"{pos} 是把不相连的正数也加了进来。"),
        Q(f"矩阵 {mat}（按行给出）中元素和最大的子矩阵，和是？",
          sub, [row_only, top_cell, total],
          f"固定上下边、按列压成一行再跑 Kadane：第 {st + 1}–{sb + 1} 行压成一行后取第 {sl + 1}–{sr + 1} 列得 {sub}。"
          f"{row_only} 只考虑了单独一行。"),
        Q(f"打家劫舍：钱数 {seq(ROB_H)}，不能偷相邻两家，最多偷到多少？",
          rob, [greedy, sum(ROB_H), max(ROB_H)],
          f"dp[i] = max(dp[i−1], dp[i−2] + v)，扫到最后是 {rob}（第 {picks} 家）。"
          f"每次先拿最大的那家只得 {greedy}：拿下一家大的，会把两边的两家一起丢掉。"),
    ]


KV_SPLIT = 20                                        # 多重背包某种物品的个数
KV_EX_W, KV_EX_V, KV_EX_CAP = [3, 4], [5, 7], 6       # 恰好装满：3 和 4 凑不出 6
KV_FRAC, KV_FRAC_CAP = [(60, 10), (100, 20), (120, 30)], 50   # (总价值, 重量)


def q_knapvar():
    parts = knapvardata.binary_split(KV_SPLIT)
    bits = [1 << i for i in range(KV_SPLIT.bit_length()) if KV_SPLIT >> i & 1]      # 误当成 20 的二进制位
    pows = [1 << i for i in range(KV_SPLIT.bit_length())]                          # 一路翻倍、不留余数
    exact = knapvardata.exact_fill_max(KV_EX_W, KV_EX_V, KV_EX_CAP)
    loose = knapvardata.fill_rows(KV_EX_W, KV_EX_V, KV_EX_CAP, exact=False)[-1][KV_EX_CAP]
    unb = knapdata.unbounded_knapsack(KV_EX_W, KV_EX_V, KV_EX_CAP)
    frac = knapvardata.fractional_knapsack(KV_FRAC, KV_FRAC_CAP)
    g01, _ = knapvardata.greedy_01(KV_FRAC, KV_FRAC_CAP)
    best01 = knapvardata.knap01(KV_FRAC, KV_FRAC_CAP)
    items = "、".join(f"({v}, {w})" for v, w in KV_FRAC)
    return [
        Q(f"多重背包里某种物品有 {KV_SPLIT} 个，按二进制拆分，拆成的各捆依次是？",
          seq(parts), [seq(bits), seq(pows[:-1]), seq(pows)],
          f"每捆翻倍 1、2、4、8，已用 15 个，剩下的 {parts[-1]} 个单独成一捆。"
          f"{seq(bits)} 只是 {KV_SPLIT} 的二进制位，凑不出 1、2、3 这类数；一路翻到 16 又会超过 {KV_SPLIT} 个。"),
        Q(f"0/1 背包：物品 重 {KV_EX_W[0]} 值 {KV_EX_V[0]}、重 {KV_EX_W[1]} 值 {KV_EX_V[1]}，"
          f"要求恰好装满容量 {KV_EX_CAP}，最大价值是？（凑不出输出 −1）",
          exact, [loose, unb, 0],
          f"{KV_EX_W[0]} 和 {KV_EX_W[1]} 凑不出 {KV_EX_CAP}，dp[{KV_EX_CAP}] 一直是 −∞，输出 −1。"
          f"初值误写成全 0 就成了「不超过」型，得到 {loose}；{unb} 是把同一件拿了两次。"),
        Q(f"分数背包（可以只拿一部分）：物品 (价值, 重量) 为 {items}，容量 {KV_FRAC_CAP}，最大总价值是？",
          f"{frac:g}", [best01, g01, sum(v for v, _ in KV_FRAC)],
          f"单价 6、5、4，整拿前两件用掉 30，剩 20 从第三件切三分之二得 80，共 {frac:g}。"
          f"不能切时背包 DP 最优是 {best01}，按单价整件贪心只有 {g01}。"),
    ]


LIS_ARR = [10, 9, 2, 5, 3, 7, 101, 18]   # 讲义思考题 4
LIS_TRAP = [3, 5, 6, 1]                  # tails 最后变成 1 5 6，不是真实子序列
LIS_EQ = [1, 3, 3, 2, 3]                 # 严格上升 3，非降 4


def q_lis():
    n = lisdata.lis_nlogn(LIS_ARR)
    run = max(k for k in range(1, len(LIS_ARR) + 1)            # 常见误解：当成连续上升子串
              for s in range(len(LIS_ARR) - k + 1)
              if all(LIS_ARR[s + t] < LIS_ARR[s + t + 1] for t in range(k - 1)))
    tails = lisdata.tails_trace(LIS_TRAP)[-1][3]
    real = lisdata.is_subseq_of(tails, LIS_TRAP)
    truth = [LIS_TRAP[i] for i in lisdata.lis_back(LIS_TRAP)]
    yn = lambda ok: "是" if ok else "不是"  # noqa: E731
    strict, nondec = lisdata.tails_strict_vs_nondec(LIS_EQ)
    return [
        Q(f"数组 {seq(LIS_ARR)} 的最长（严格）上升子序列长度是？", n, [run, n + 1, n - 2],
          f"例如 2, 3, 7, 18。子序列不要求连续；{run} 是最长连续上升段的长度，那是子串，不是子序列。"),
        Q(f"对 {seq(LIS_TRAP)} 跑 bisect_left 版本，结束时 tails 是什么？它是一个真实的上升子序列吗？",
          f"[{seq(tails)}]，{yn(real)}",
          [f"[{seq(truth)}]，是", f"[{seq(tails)}]，{yn(not real)}", f"[{seq(tails[:1])}]，是"],
          f"最后的 1 替换了 tails[0]，但它在原数组里排在 5、6 后面。tails 只保证长度 {len(tails)} 对，"
          f"真实的最长上升子序列是 {seq(truth)}。"),
        Q(f"数组 {seq(LIS_EQ)}，允许相等的最长非降子序列长度是多少，tails 版本该用哪个函数？",
          f"{nondec}，bisect_right",
          [f"{strict}，bisect_left", f"{nondec}，bisect_left", f"{strict}，bisect_right"],
          f"非降允许相等，相等的数要新开一摞，用 bisect_right，得 1, 3, 3, 3 长度 {nondec}；"
          f"bisect_left 让相等的数互相替换，求的是严格上升，长度 {strict}。"),
    ]


GRID_RD = [[1, 2, 9], [5, 9, 1], [1, 1, 1]]                      # 只能右、下
GRID_4 = [[1, 9, 1, 1, 1], [1, 9, 1, 9, 1], [1, 1, 1, 9, 1]]       # 四方向，最好的路要往上绕
GRID_CNT = (4, 4)                                                 # 只能右、下的路径条数


def _greedy_rd(g):
    """常见错误：每步只看右边和下边哪个小就往哪走。"""
    n, m = len(g), len(g[0])
    i = j = 0
    s = g[0][0]
    while (i, j) != (n - 1, m - 1):
        if i == n - 1 or (j < m - 1 and g[i][j + 1] <= g[i + 1][j]):
            j += 1
        else:
            i += 1
        s += g[i][j]
    return s


def q_grid():
    rd = griddata.min_path_sum(GRID_RD)
    greedy = _greedy_rd(GRID_RD)
    four, _, _, _ = griddata.grid_dijkstra(GRID_4)
    copy = griddata.naive_four(GRID_4)[-1][-1]                   # 照搬到四方向的 DP，等于只许右、下
    n, m = GRID_CNT
    cnt = griddata.count_paths(n, m)[-1][-1]
    rows = " / ".join(" ".join(map(str, r)) for r in GRID_RD)
    rows4 = " / ".join(" ".join(map(str, r)) for r in GRID_4)
    return [
        Q(f"网格（按行写）{rows}，从左上走到右下，只能向右或向下，路过的数（含起点终点）之和最小是多少？",
          rd, [greedy, rd + 1, sum(map(sum, GRID_RD))],
          f"dp[i][j] = min(上, 左) + 自己，按行填到右下角是 {rd}（先一路向下再向右）。"
          f"每步只挑右、下里较小的那格，会先走到 2 再被 9 堵住，得到 {greedy}。"),
        Q(f"网格 {rows4}，现在上下左右都能走，从左上到右下的最小路径和是多少？",
          four, [copy, four - 1, four + 2],
          f"最好的路在第三列向上绕过 9，路径和 {four}，用 Dijkstra 求。把 DP 按行照搬到四方向，"
          f"还没算的格子当无穷大，往上绕的路永远用不上，得到的是只许右、下的答案 {copy}。"),
        Q(f"{n}×{m} 的网格，从左上角走到右下角，只能向右或向下，一共有几条路径？",
          cnt, [n * m, 2 ** (n + m - 2), griddata.count_paths(n + 1, m + 1)[-1][-1]],
          f"第一行、第一列都是 1，其余格子 = 上面 + 左边，右下角是 {cnt}，也就是 6 步里选 3 步向下。"),
    ]


CX_LOOP_N = 12                                    # for i in range(n): for j in range(i, n) 的 n
CX_LIMIT_N = 10 ** 5                              # 讲义思考题 3：n = 10⁵、时限 1 秒
CX_CANDS = [("O(n²)", lambda n: n * n), ("O(n√n)", lambda n: n * math.sqrt(n)),
            ("O(n log² n)", lambda n: n * math.log2(n) ** 2), ("O(n log n)", lambda n: n * math.log2(n))]
CX_SIEVE_N = 50                                   # sieve(50) 的内层赋值次数


def _cx_sci(v):
    """2.76e7 → 2.8×10⁷。"""
    m, e = f"{v:.1e}".split("e")
    return f"{m}×10" + str(int(e)).translate(str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"))


def _cx_marks_from_2i(limit):
    """常见误解：内层从 2*i 而不是 i*i 开始划，赋值次数（作干扰项）。"""
    is_prime = [True] * (limit + 1)
    c, i = 0, 2
    while i * i <= limit:
        if is_prime[i]:
            for j in range(2 * i, limit + 1, i):
                is_prime[j] = False
                c += 1
        i += 1
    return c


def q_complexity():
    n = CX_LOOP_N
    runs = complexitydata.triangle_count(n)
    budget = complexitydata.OPS_PER_SEC[1]
    over = [name for name, f in CX_CANDS if f(CX_LIMIT_N) > budget]
    ok = [name for name, f in CX_CANDS if f(CX_LIMIT_N) <= budget]
    marks = complexitydata.sieve_marks(CX_SIEVE_N)
    primes = complexitydata.primes_upto(CX_SIEVE_N)
    composites = CX_SIEVE_N - 1 - len(primes)
    from2i = _cx_marks_from_2i(CX_SIEVE_N)
    return [
        Q(f"n = {n} 时，for i in range(n): for j in range(i, n): 里的循环体一共执行几次？",
          runs, [n * n, n * (n - 1) // 2, n * n // 2],
          f"第 i 行执行 n − i 次，{n} + {n - 1} + … + 1 = n(n+1)/2 = {runs}。{n * n} 是 j 从 0 开始的正方形，"
          f"{n * (n - 1) // 2} 是 range(i + 1, n) 的次数。三者都是 O(n²)。"),
        Q(f"n = 10⁵、时限 1 秒（按每秒约 10⁸ 次基本操作），下面哪一个复杂度会超时？",
          "、".join(over), ok[:3],
          "代入 n = 10⁵：" + "；".join(f"{name[2:-1]} ≈ {_cx_sci(f(CX_LIMIT_N))}" for name, f in CX_CANDS)
          + f"。只有 {'、'.join(over)} 超过每秒 10⁸ 次，其余都在预算内。"),
        Q(f"讲义的 sieve({CX_SIEVE_N}) 里，内层 is_prime[j] = False 一共执行几次？",
          marks, [composites, from2i, len(primes)],
          f"i = 2、3、5、7 各从 i² 划到 {CX_SIEVE_N}：合计 {marks} 次，比合数个数 {composites} 多，"
          f"因为像 12 这样的数会被 2 和 3 各划一次；若从 2i 开始划要 {from2i} 次。{len(primes)} 是素数个数。"),
    ]


DIV_POW_B = 13                   # 讲义 fast_pow 算 a^13 的乘法次数
DIV_RECT = (91, 35)              # 长方形反复切最大的正方形
DIV_TWICE_B = 6                  # half 写成两次调用时的调用次数


def q_divide():
    b = DIV_POW_B
    mults = dividedata.pow_mults(b)
    w, h = DIV_RECT
    sq = dividedata.squares(w, h)
    g, n_sq = sq[-1][0], sum(k for _, k in sq)
    steps = len(dividedata.gcd_trace(w, h)) - 1               # 常见误解：切的块数 = 取模的步数
    tb = DIV_TWICE_B
    _, calls, _ = dividedata.twice_counts(2, tb)
    once = dividedata.pow_calls(tb)
    return [
        Q(f"用讲义的 fast_pow(a, {b}) 计算 a 的 {b} 次方（不取模），一共做几次乘法？",
          mults, [b, b.bit_length(), b - 1],
          f"{b} 的二进制是 {bin(b)[2:]}，共 {b.bit_length()} 位、{bin(b).count('1')} 个 1：每层平方一次，"
          f"最低位是 1 的层再乘一次 a，{b.bit_length()} + {bin(b).count('1')} = {mults}。连乘要 {b} 次。"),
        Q(f"{w}×{h} 的长方形，反复切下尽量大的正方形直到切完。最后一块正方形的边长和正方形总块数是？",
          f"边长 {g}，共 {n_sq} 块", [f"边长 {g}，共 {steps} 块", f"边长 {sq[-2][0]}，共 {n_sq} 块",
                                    f"边长 {h}，共 {w // h} 块"],
          f"依次切下 " + "、".join(f"{k} 块边长 {s}" for s, k in sq) + f"，最后的边长就是 gcd({w}, {h}) = {g}。"
          f"取模只做 {steps} 次，但一次取模可能切下好几块。"),
        Q(f"把 half 省掉，写成 res = fast_pow(a, b // 2) * fast_pow(a, b // 2)。算 a 的 {tb} 次方，"
          f"fast_pow 一共被调用几次（含 b = 0 那次）？",
          calls, [once, 2 ** tb.bit_length() - 1, tb],
          f"每层分出两个孩子，单链变成满二叉树：指数 {tb} 有 {tb.bit_length()} 位，树有 {tb.bit_length() + 1} 层，"
          f"2^{tb.bit_length() + 1} − 1 = {calls} 个节点；原来的写法只调用 {once} 次。"),
    ]


FOOD_Q_N = 4
FOOD_Q = [(2, 3, 4), (2, 5, 1), (2, 4, 1), (1, 3, 2), (2, 4, 2), (1, 1, 2), (1, 1, 3)]   # (1 同类 / 2 吃, x, y)
FOOD_INFER = [(2, 1, 2), (2, 3, 1)]          # 都是真话；接着问「2 吃 3」
FOOD_INFER_Q = (2, 2, 3)
FOOD_SETS = [(2, 1, 2), (1, 3, 4), (2, 2, 3)]  # n = 4 时 12 个结点分成几个集合


def _food_say(s):
    kind, x, y = s
    return f"{x} 和 {y} 同类" if kind == 1 else f"{x} 吃 {y}"


def q_foodchain():
    n = FOOD_Q_N
    lies = foodchaindata.food_chain(n, FOOD_Q)
    two = foodchaindata.lies_of(n, FOOD_Q, third=False)                  # 常见错误：「x 吃 y」只连前两对
    inside = [s for s in FOOD_Q if 1 <= s[1] <= n and 1 <= s[2] <= n]
    norange = foodchaindata.food_chain(n, inside)                        # 常见错误：忘了越界也算假话
    extra = foodchaindata.food_chain(3, FOOD_INFER + [FOOD_INFER_Q]) - foodchaindata.food_chain(3, FOOD_INFER)
    verdict = "假话" if extra else "真话"
    log = foodchaindata.food_chain_trace(4, FOOD_SETS, animals=[])
    log2 = foodchaindata.food_chain_trace(4, FOOD_SETS, third=False, animals=[])
    sets, sets2 = log[-1]["count"], log2[-1]["count"]
    says = "、".join(_food_say(s) for s in FOOD_Q)
    bad = foodchaindata.lie_lines(n, FOOD_Q)                             # 第几句是假话（第一条是越界那句）
    return [
        Q(f"食物链，n = {n}，依次 {len(FOOD_Q)} 句话：{says}。一共几句假话？",
          lies, [two, norange, lies + 1],
          f"5 超出范围，算一句；之后 {'、'.join(_food_say(FOOD_Q[k - 1]) for k in bad[1:])}都与前面的真话矛盾，共 {lies} 句。"
          f"「x 吃 y」只连前两对会漏掉矛盾，只数出 {two} 句；忘了越界算假话则得 {norange}。"),
        Q(f"已知「{_food_say(FOOD_INFER[0])}」「{_food_say(FOOD_INFER[1])}」都是真话，接下来有人说「{_food_say(FOOD_INFER_Q)}」，它是？",
          verdict, ["真话" if extra else "假话", "无法判断，按真话算", "无法判断，按假话算"],
          "三类成环：1 吃 2，3 吃 1，那么 2 吃的正是 3 这一类。扩展域里，「1 吃 2」的第三对把 1 的天敌域和 2 的猎物域连上，"
          "「3 吃 1」又把 3 并进 1 的天敌域；查 2 与 3、2 与 3 的猎物域都不连通，所以是真话，不必等谁直接说过 2 和 3 的关系。"),
        Q(f"n = 4，依次说了 {'、'.join(_food_say(s) for s in FOOD_SETS)}（都是真话）。扩展域并查集的 12 个结点此时分成几个集合？",
          sets, [sets2, 4, 12 - 2 * len(FOOD_SETS)],
          f"每句真话的三对合并都成功，12 − 9 = {sets}，正好对应三类动物。少连第三对会剩 {sets2} 个，环没接上。"),
    ]


SB_GRID, SB_T = ["@.##.", "#..#+", ".....", "....."], 1     # 只按坐标记会得 7，真答案 5
SB_SIZE = (100, 100, 5)                                       # 行、列、初始查克拉
SB_FL_H = [[1, 7, 3, 7], [7, 1, 2, 2], [5, 4, 6, 5]]          # 水淹七军：两个放水点
SB_FL_SRC = [(0, 0), (2, 3)]


def _sb_flood_count(h, src, le=False, follow=False):
    """常见误解的灌水：le=True 把「严格低于水位」写成「不高于」；follow=True 以为水位随地形下降（只往比当前格低处流）。"""
    n, m = len(h), len(h[0])
    w = [[-1] * m for _ in range(n)]
    q = deque()
    for x, y in src:
        if w[x][y] < h[x][y]:
            w[x][y] = h[x][y]
            q.append((x, y))
    while q:
        x, y = q.popleft()
        lv = h[x][y] if follow else w[x][y]
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= a < n and 0 <= b < m):
                continue
            low = h[a][b] <= lv if le else h[a][b] < lv
            fresh = w[a][b] < 0 if follow else w[a][b] < lv
            if low and fresh:
                w[a][b] = lv
                q.append((a, b))
    return sum(v >= 0 for r in w for v in r)


def q_statebfs():
    ans = statebfsdata.naruto(SB_GRID, SB_T)
    coord = statebfsdata.naruto_coord(SB_GRID, SB_T)[0]
    rows = " / ".join(SB_GRID)
    n, m, t = SB_SIZE
    states = statebfsdata.n_states(["." * m] * n, t)
    _, water, _ = statebfsdata.flood_trace(SB_FL_H, SB_FL_SRC, SB_FL_SRC[0])
    wet = sum(v >= 0 for r in water for v in r)
    only = sum(v >= 0 for r in statebfsdata.flood_trace(SB_FL_H, SB_FL_SRC[1:], SB_FL_SRC[1])[1] for v in r)
    hs = " / ".join(" ".join(map(str, r)) for r in SB_FL_H)
    srcs = "、".join(f"({x}, {y})" for x, y in SB_FL_SRC)
    return [
        Q(f"鸣人和佐助：地图（按行写，@ 鸣人、+ 佐助、# 手下）{rows}，查克拉 {SB_T}，打掉一个手下花 1 点。最短几步追上佐助？",
          ans, [coord, -1, ans + 1],
          f"状态记成（行、列、剩余查克拉），行列从 0 起：先右再下走到 (1, 2)，留着查克拉打掉 (1, 3) 的手下，{ans} 步。"
          f"visited 只记坐标时，(1, 1)、(1, 2) 先被打掉 (1, 0) 手下、查克拉用光的那一支占住，"
          f"后到的留有查克拉也进不去，只能绕下面，得 {coord}。"),
        Q(f"地图 {n} 行 {m} 列、初始查克拉 {t}，visited 按（行、列、剩余查克拉）记，最多有多少个不同的状态？",
          states, [n * m, n * m * t, n * m * 2 ** t],
          f"剩余查克拉可以是 0 到 {t}，共 {t + 1} 种，每格就有 {t + 1} 层：{n} × {m} × {t + 1} = {states}。"),
        Q(f"水淹七军：高度（按行写）{hs}，放水点 {srcs}（行列从 0 起），水位等于放水点高度，只流向高度严格低于水位的相邻格。"
          "最后一共有几格被淹（含放水点）？",
          wet, [_sb_flood_count(SB_FL_H, SB_FL_SRC, follow=True), _sb_flood_count(SB_FL_H, SB_FL_SRC, le=True), only],
          f"两个放水点一起入队：左上角高 1，水位 1 哪儿也流不去；右下角水位 5，淹到所有高度小于 5、连得通的格子，"
          f"共 {wet} 格。水位不随地形下降（那样只剩 {_sb_flood_count(SB_FL_H, SB_FL_SRC, follow=True)} 格）；"
          f"等高的格子不淹（写成 ≤ 会得 {_sb_flood_count(SB_FL_H, SB_FL_SRC, le=True)}）。"),
    ]


# 1) import 区加：import runtimedata  # noqa: E402
# 2) 新输入常量（片中都没出现过）放到常量区：
RT_LOOP_N = 1000                         # 循环 1000 圈（片中是三百万）
RT_CACHE = (6, 2, 8)                     # 6×6 矩阵、缓存行装 2 个数、缓存放得下 8 个缓存行（片中 8×8、4、4）
RT_PRINT_N, RT_BUF = 6000, 8192          # print 0²…5999² 到文件、8 KB 缓冲（片中一万行）
# 3) BUILDERS 里加 "runtime": q_runtime（顺序随 films.json：bsearch 之后、lights 之前）


def q_runtime():
    per, _ = runtimedata.loop_formula()
    body = per * RT_LOOP_N                                            # 只算循环体
    n, line, ways = RT_CACHE
    col = runtimedata.misses(runtimedata.col_major(n), line=line, ways=ways)
    row = runtimedata.misses(runtimedata.row_major(n), line=line, ways=ways)
    calls, nbytes = runtimedata.syscalls(runtimedata.squares_print, False, RT_PRINT_N, RT_BUF)
    term, _ = runtimedata.syscalls(runtimedata.squares_print, True, RT_PRINT_N, RT_BUF)
    return [
        Q(f"for i in range(n): s += i 每转一圈执行 {per} 条字节码。n = {RT_LOOP_N} 时，循环体一共执行多少条字节码？",
          body, [RT_LOOP_N, 2 * RT_LOOP_N, per],
          f"每圈 {per} 条（取下一个数、存 i、读 s、读 i、相加、存回 s、跳回），{RT_LOOP_N} 圈就是 {body} 条；"
          f"一行源码不等于一条字节码。"),
        Q(f"{n}×{n} 的矩阵按行连续存放，一个缓存行装 {line} 个数，缓存（LRU）放得下 {ways} 个缓存行。"
          f"按列遍历全部 {n * n} 个数，缺失几次？",
          col, [n * n, n, n * n // line // 2],
          f"每 {line} 列落在同一批 {n} 个缓存行里，缓存放得下 {ways} 个，扫后一列时全部命中；"
          f"每 {line} 列缺失 {n} 次，共 {col} 次，和按行（{row} 次）一样。按列全缺失，只在缓存装不下一列涉及的缓存行时发生。"),
        Q(f"把 0²、1²……{RT_PRINT_N - 1}² 逐行 print，重定向到文件，缓冲区 {RT_BUF} 字节（攒满才写）。"
          f"一共写出 {nbytes} 字节，底层 write 系统调用几次？",
          calls, [term, nbytes // RT_BUF, 1],
          f"攒满 {RT_BUF} 字节写一次，最后不满的一块在结束时再写一次：⌈{nbytes}/{RT_BUF}⌉ = {calls}。"
          f"输出到终端时按行刷新，才是每行一次、共 {term} 次。"),
    ]


DL_TASKS = [(4, 7), (2, 8), (3, 9), (4, 10), (5, 5)]     # (耗时, 截止)，故意不按截止给出


def q_deadline():
    best = deadlinedata.max_tasks(DL_TASKS)
    skip = deadlinedata.skip_greedy(DL_TASKS)[0]                      # 常见错误：超时就跳过新任务，不反悔
    srt = sorted(DL_TASKS, key=lambda t: t[1])
    drops = [s["dropped"] for s in deadlinedata.trace(DL_TASKS) if s["dropped"] is not None]
    skipped = [c for (c, _), ok in zip(srt, deadlinedata.skip_greedy(DL_TASKS)[1]) if not ok]   # 扔新来的
    tasks = "、".join(f"({c}, {d})" for c, d in DL_TASKS)
    return [
        Q(f"任务按 (耗时, 截止) 给出：{tasks}。一次做一个、不能中断，最多能按时完成几个？",
          best, [skip, len(DL_TASKS), best + 1],
          f"按截止排序后依次加入，超时就扔掉已选里耗时最长的，最后剩 {best} 个。"
          f"超时就跳过新任务、不反悔，会一直留着耗时 {srt[0][0]} 的任务，只完成 {skip} 个。"),
        Q("按截止时间加入任务后总时长超过了当前截止时间，应该扔掉哪一个？",
          "已选任务（含新来的）里耗时最长的", ["新来的这一个", "截止时间最早的那个", "耗时最短的那个"],
          "扔谁数量都只少一个，扔最长的剩下的总时长最少，给后面的任务留的空间最多；"
          "最长的不比新来的短，扔完总时长不超过上一步，所以一个 if 就够。"),
        Q(f"对同一组任务 {tasks} 跑讲义的大根堆解法，处理冲突时依次扔掉的任务耗时是？",
          seq(drops), [seq(skipped), seq(drops[:1]), seq(drops[::-1])],
          f"排好序是 {'、'.join(f'({c}, {d})' for c, d in srt)}。第一次超时扔掉堆顶 {drops[0]}，"
          f"最后一个任务加入时再扔堆顶 {drops[-1]}。{seq(skipped)} 是每次扔新来的那个，那是不反悔的错误做法。"),
    ]


# 1) import 区加：import shoppingdata  # noqa: E402
# 2) 新输入常量（片中都没出现过）放到常量区；test_quiz.py 里有同样一份，供独立重算
SHOP_X, SHOP_COINS = 30, [1, 5, 10, 25]                  # 最少带几枚
SHOP_BAG = [1, 2, 4, 9]                                  # 带着这几枚，凑不出的最小金额
SHOP_CANDS = [(5, [2, 3]), (100, [1]), (3, [1, 100]), (7, [1, 8, 9])]   # 哪组输入输出 -1
# 3) BUILDERS 里加 "shopping": q_shopping（放在 "lights" 之后，与片目顺序一致）


def _shop_in(x, coins):
    return f"X = {x}，面值 {' '.join(map(str, coins))}"


def q_shopping():
    ans = int(shoppingdata.run_io(shoppingdata.solve_w16, shoppingdata.fmt_in(SHOP_X, SHOP_COINS)))
    picks = "、".join(str(c) for _, _, c, _ in shoppingdata.greedy_trace(SHOP_X, SHOP_COINS))
    change = 0                                               # 误当成找零：只凑上限 X 用的最少枚数（贪心找零）
    left = SHOP_X
    for c in sorted(SHOP_COINS, reverse=True):
        change += left // c
        left %= c
    bits = SHOP_X.bit_length()                               # 误以为 1、2、4…… 二进制位数就够，不看有哪些面值
    each = len(SHOP_COINS)                                   # 误以为每种带一枚
    reach = shoppingdata.prefix_reach(SHOP_BAG)
    hole = reach[-1] + 1 if reach else 1
    brk = SHOP_BAG[len(reach)]                               # 断档的那一枚
    neg = [(x, c) for x, c in SHOP_CANDS
           if shoppingdata.run_io(shoppingdata.solve_w16, shoppingdata.fmt_in(x, c)) == "-1"]
    assert len(neg) == 1
    rest = [(x, c) for x, c in SHOP_CANDS if (x, c) != neg[0]]
    outs = "；".join(f"{_shop_in(x, c)} 输出 {shoppingdata.run_io(shoppingdata.solve_w16, shoppingdata.fmt_in(x, c))}"
                    for x, c in rest)
    return [
        Q(f"购物：面值 {seq(SHOP_COINS)}，每种无限多，要让 1 到 {SHOP_X} 的每个金额都能用带着的硬币凑出，最少带几枚？",
          ans, [change, bits, each],
          f"reach 从 0 起，每步挑不超过 reach+1 的最大面值：依次带 {picks}，共 {ans} 枚。"
          f"{change} 是只凑 {SHOP_X} 的找零枚数；{bits} 是二进制位数，可这里没有 2、4、8 这些面值；每种各带一枚连 2 都凑不出。"),
        Q(f"手上带着 {seq(SHOP_BAG)} 四枚硬币（每枚最多用一次），凑不出的最小正整数金额是？",
          hole, [sum(SHOP_BAG) + 1, brk, 2 ** len(SHOP_BAG)],
          f"按面值从小到大，reach 依次是 {seq(reach)}；下一枚 {brk} 大于 reach+1 = {hole}，"
          f"所以 {hole} 凑不出。{sum(SHOP_BAG) + 1} 是总和加一，只在每枚都接得上时才对。"),
        Q("下面哪组输入，讲义代码会输出 −1？",
          _shop_in(*neg[0]), [_shop_in(x, c) for x, c in rest],
          f"无解只有一种情况：没有面值 1，reach+1 = 1 时没有一枚接得上。其余三组都有 1：{outs}。"),
    ]


# 1) import 区加：import partitiondata  # noqa: E402
# 2) 新输入常量（片中都没出现过：片里用的是 7 分 3 份、7 分 2 份、200 分 6 份）放到常量区：
PART_Q1 = (8, 3)                 # 8 分 3 份
PART_ROOT = (10, 3)              # dfs(10, 3, 1) 第一层
PART_LIST = (20, 6)              # 要求逐个输出分法时的数据范围
# 3) BUILDERS 里加 "partition": q_partition（放在 "shopping" 之后，与片目顺序一致）


def q_partition():
    n, k = PART_Q1
    ans = partitiondata.dp_count(n, k)
    ordered = len(partitiondata.compositions(n, k))                       # 常见误解：把顺序也算上
    allow0 = sum(partitiondata.dp_count(n, j) for j in range(1, k + 1))   # 常见误解：允许有空份
    only1 = partitiondata.dp_count(n - 1, k - 1)                          # 漏了「每份都 >= 2」那一类
    rn, rk = PART_ROOT
    tree = partitiondata.dfs_tree(rn, rk)
    xs = [tree[c]["x"] for c in tree[0]["kids"]]
    span = lambda a, b: f"{a} 到 {b}"  # noqa: E731
    ln, lk = PART_LIST
    total = partitiondata.dp_count(ln, lk)
    return [
        Q(f"把 {n} 分成 {k} 份（每份不能为空，不考虑顺序），一共有几种分法？", ans, [ordered, allow0, only1],
          f"有一份是 1 的拿掉它，是 {n - 1} 分 {k - 1} 份，{only1} 种；每份都 ≥ 2 的每份减 1，是 {n - k} 分 {k} 份，"
          f"{partitiondata.dp_count(n - k, k)} 种，合计 {ans}。{ordered} 把顺序也算了进去，{allow0} 是允许有空份。"),
        Q(f"讲义的 dfs(rem, left, low) 求 {rn} 分 {rk} 份，根节点 dfs({rn}, {rk}, 1) 里第一份 x 依次试哪些值？",
          span(xs[0], xs[-1]), [span(1, rn), span(1, rn - (rk - 1)), span(1, rn // 2)],
          f"后面每一份都不小于 x，{rk} 份加起来至少是 {rk}x，所以 x ≤ {rn} // {rk} = {xs[-1]}。"
          f"试到 {rn - (rk - 1)} 只保证了后面每份至少 1，没用上「非降」这个条件。"),
        Q(f"题目改成：按字典序输出把 n 分成 k 份的每一种分法（n ≤ {ln}，k ≤ {lk}）。最合适的写法是？",
          "深搜，按非降顺序逐个输出",
          ["dp[i][j] 递推，只填一张表", "给深搜加 lru_cache，直接输出缓存", "贪心，每份尽量平均"],
          f"要列出每一种，输出量就等于方案数，只能一个一个地搜出来；{ln} 分 {lk} 份也只有 {total} 种，深搜很快。"
          f"DP 和记忆化只算个数，缓存里存的是数字，不是分法。"),
    ]


BUILDERS = {"sort": q_sort, "stack": q_stack, "fib": q_fib, "hanoi": q_hanoi, "perm": q_perm,
            "queens": q_queens, "dsu": q_dsu, "interval": q_interval, "dpintro": q_dpintro,
            "knap": q_knap, "lcs": q_lcs, "bfs": q_bfs, "dijkstra": q_dijkstra, "bsearch": q_bsearch,
            "binary": q_binary, "float": q_float, "matrix": q_matrix, "lights": q_lights,
            "subsets": q_subsets, "knight": q_knight, "triangle": q_triangle, "kadane": q_kadane, "knapvar": q_knapvar, "lis": q_lis, "grid": q_grid,
            "complexity": q_complexity, "divide": q_divide, "foodchain": q_foodchain, "statebfs": q_statebfs, "runtime": q_runtime, "deadline": q_deadline, "shopping": q_shopping, "partition": q_partition}


def build() -> dict:
    out = {}
    for fid, fn in BUILDERS.items():
        items = []
        for k, raw in enumerate(fn()):
            wrong = []
            for w in raw["wrong"]:                       # 干扰项和正确项、彼此都不能撞
                if w != raw["right"] and w not in wrong:
                    wrong.append(w)
            if len(wrong) < 2:
                raise SystemExit(f"{fid} 第 {k + 1} 题干扰项不足：{raw}")
            opts = [raw["right"]] + wrong
            random.Random(f"{fid}-{k}").shuffle(opts)
            items.append({"q": raw["q"], "options": opts, "answer": opts.index(raw["right"]),
                          "explain": raw["explain"]})
        out[fid] = items
    return out


if __name__ == "__main__":
    data = build()
    (HERE / "quiz.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data)} 支片，{sum(len(v) for v in data.values())} 题 → {HERE / 'quiz.json'}")
