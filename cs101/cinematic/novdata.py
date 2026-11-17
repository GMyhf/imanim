"""11 月月考讲评片的数据层：讲义六题的 Python 参考代码原样 + 插桩，画面和旁白里的每个数字都从这里来。

讲义：2026fall courseware/202611_ADS_November_Exam_Review.md 第 3 节（E31529 双重回文、E31530 图书馆选座、
M31531 箭头迷阵、M31532 牌堆魔术、M31533 渗透实验、T31534 括号区间审计）。
solve_t1 … solve_t6 的函数体照抄讲义，只把顶层脚本包进函数，经 run_io 喂样例、收输出。
*_trace 是补写的：与讲义代码逐行同逻辑，交出中间量给画面用（test_nov 再用独立实现对撞）。
片中自拟数据：SEATS（选座的一排十个座位）、PERC（4×4 渗透的六次打开）。其余用题面样例。
"""
from __future__ import annotations

import contextlib
import io
import sys
from collections import deque

# ---------------------------------------------------------------- 题面样例（讲义原样）
SAMPLES = {
    "t1": [("5\n", "3 5"), ("100\n", "7 99")],
    "t2": [("5 2\n00000\n", "2\n10100"), ("4 2\n0100\n", "1\n0101")],
    "t3": [("2 2\nUD\nDU\n", "2"), ("3 3\nURD\nLDR\nRUL\n", "5")],
    "t4": [("4\n", "4 1 3 2"), ("5\n", "3 1 5 2 4")],
    "t5": [("3 3 3\n1 1\n2 1\n3 1\n", "3"), ("3 3 4\n1 1\n1 2\n1 3\n2 2\n", "-1")],
    "t6": [("(()())\n5\n1 6\n2 5\n1 5\n3 4\n4 4\n", "YES\nYES\nNO\nNO\nNO"),
           ("())(()\n4\n1 2\n2 5\n1 6\n3 6\n", "YES\nNO\nNO\nNO")],
}
T1_BIG = (10 ** 6, 19, 585585)                  # 讲义：n = 10⁶ 时答案是 19 585585


# ---------------------------------------------------------------- 讲义原样
def solve_t1():
    n = int(input())
    cnt, best = 0, 1
    for i in range(1, n + 1, 2):  # 偶数二进制末位是 0
        d, b = str(i), bin(i)[2:]
        if d == d[::-1] and b == b[::-1]:
            cnt += 1
            best = i
    print(cnt, best)


def solve_t2():
    n, m = map(int, input().split())
    s = list(input().strip())
    sat = 0
    for i in range(n):  # 从左到右一遍扫描
        if sat == m:
            break
        left = i == 0 or s[i - 1] == '0'
        right = i == n - 1 or s[i + 1] == '0'
        if s[i] == '0' and left and right:
            s[i] = '1'
            sat += 1
    print(sat)
    print(''.join(s))


def solve_t3():
    import sys

    data = sys.stdin.read().split()
    n, m = int(data[0]), int(data[1])
    g = data[2:2 + n]
    MOVE = {'U': (-1, 0), 'D': (1, 0),
            'L': (0, -1), 'R': (0, 1)}
    st = [0] * (n * m)  # 0 未访问 1 在路上 2 能逃 3 逃不出
    for s in range(n * m):
        if st[s]:
            continue
        path, i, j = [], s // m, s % m
        while True:
            if not (0 <= i < n and 0 <= j < m):
                res = 2  # 出界：逃出
                break
            u = i * m + j
            if st[u] == 1:
                res = 3  # 撞上本条路径：成环
                break
            if st[u]:
                res = st[u]  # 接上已知结论
                break
            st[u] = 1
            path.append(u)
            di, dj = MOVE[g[i][j]]
            i, j = i + di, j + dj
        for u in path:
            st[u] = res
    print(st.count(2))


def solve_t4():
    from collections import deque

    n = int(input())
    dq = deque()
    for i in range(n, 0, -1):  # 倒着做
        dq.appendleft(i)  # 撤销"翻开"：牌 i 放回牌顶
        dq.appendleft(dq.pop())  # 撤销"顶移到底"
    print(*dq)


def solve_t5():
    import sys

    data = sys.stdin.buffer.read().split()
    n, m, q = int(data[0]), int(data[1]), int(data[2])
    TOP, BOT = n * m, n * m + 1  # 两个虚拟结点
    fa = list(range(n * m + 2))
    opened = [False] * (n * m)

    def find(x):
        while fa[x] != x:
            fa[x] = fa[fa[x]]  # 路径减半
            x = fa[x]
        return x

    def union(a, b):
        fa[find(a)] = find(b)

    ans = -1
    for k in range(q):
        r = int(data[3 + 2 * k]) - 1
        c = int(data[4 + 2 * k]) - 1
        u = r * m + c
        opened[u] = True
        if r == 0:
            union(u, TOP)
        if r == n - 1:
            union(u, BOT)
        for nr, nc in ((r - 1, c), (r + 1, c),
                       (r, c - 1), (r, c + 1)):
            v = nr * m + nc
            if 0 <= nr < n and 0 <= nc < m and opened[v]:
                union(u, v)
        if find(TOP) == find(BOT):
            ans = k + 1
            break
    print(ans)


def solve_t6():
    import sys

    data = sys.stdin.read().split()
    s = data[0]
    n = len(s)
    # pre[i]：前 i 个字符中 左括号数 - 右括号数
    pre = [0] * (n + 1)
    for i, ch in enumerate(s):
        pre[i + 1] = pre[i] + (1 if ch == '(' else -1)

    # nxt[i]：i 右边第一个 pre 比 pre[i] 小的位置（单调栈）
    nxt = [n + 1] * (n + 1)
    stk = []
    for j in range(n + 1):
        while stk and pre[stk[-1]] > pre[j]:
            nxt[stk.pop()] = j
        stk.append(j)

    q = int(data[1])
    out = []
    for k in range(q):
        l, r = int(data[2 + 2 * k]), int(data[3 + 2 * k])
        ok = pre[r] == pre[l - 1] and nxt[l - 1] > r
        out.append('YES' if ok else 'NO')
    print('\n'.join(out))


SOLVERS = {"t1": solve_t1, "t2": solve_t2, "t3": solve_t3, "t4": solve_t4, "t5": solve_t5, "t6": solve_t6}


def run_io(fn, text: str) -> str:
    """把 text 当标准输入喂给讲义函数（同时提供 sys.stdin.buffer），返回打印的内容（去首尾空白）。"""
    old_in = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(text.encode()), encoding="utf-8")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    finally:
        sys.stdin = old_in
    return buf.getvalue().strip()


# ---------------------------------------------------------------- T1：双重回文
def is_pal(x: int, base: int) -> bool:
    """讲义 C++ 版的 pal：按 base 进制把 x 倒过来，看是否等于自己。"""
    y, t = 0, x
    while t > 0:
        y = y * base + t % base
        t //= base
    return y == x


def double_pals(n: int) -> list[int]:
    return [i for i in range(1, n + 1, 2) if is_pal(i, 10) and is_pal(i, 2)]


PALS_100 = double_pals(100)                     # [1, 3, 5, 7, 9, 33, 99]


# ---------------------------------------------------------------- T2：选座（自拟一排十个座位）
SEATS = ("0010000010", 4)                       # 初始占用、来的人数：第 4 位找不到座位


def seats_trace(s: str, m: int):
    """与 solve_t2 同逻辑。返回 (每个 i 的判定列表 [(i, 能坐吗, 原因)], 坐下人数, 最终串)。"""
    s, n, sat, steps = list(s), len(s), 0, []
    for i in range(n):
        if sat == m:
            break
        left = i == 0 or s[i - 1] == '0'
        right = i == n - 1 or s[i + 1] == '0'
        if s[i] == '0' and left and right:
            s[i] = '1'
            sat += 1
            steps.append((i, True, "坐"))
        else:
            steps.append((i, False, "有人" if s[i] == '1' else ("左邻有人" if not left else "右邻有人")))
    return steps, sat, "".join(s)


# ---------------------------------------------------------------- T3：箭头迷阵（题面样例 2）
ARROWS = ["URD", "LDR", "RUL"]
MOVE = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}


def arrows_trace(g: list[str]):
    """与 solve_t3 同逻辑，记录每次出发：{"start", "path": [(i, j)], "end": out|cycle|join, "hit": (i, j)|None, "res"}。"""
    n, m = len(g), len(g[0])
    st = [0] * (n * m)
    walks = []
    for s in range(n * m):
        if st[s]:
            continue
        path, i, j = [], s // m, s % m
        while True:
            if not (0 <= i < n and 0 <= j < m):
                res, end, hit = 2, "out", (i, j)
                break
            u = i * m + j
            if st[u] == 1:
                res, end, hit = 3, "cycle", (i, j)
                break
            if st[u]:
                res, end, hit = st[u], "join", (i, j)
                break
            st[u] = 1
            path.append((i, j))
            di, dj = MOVE[g[i][j]]
            i, j = i + di, j + dj
        for (a, b) in path:
            st[a * m + b] = res
        walks.append({"start": divmod(s, m), "path": path, "end": end, "hit": hit, "res": res})
    return walks, st


# ---------------------------------------------------------------- T4：牌堆魔术
def cards_reverse_trace(n: int):
    """与 solve_t4 同逻辑。每个 i 记两步：放回牌顶后、底牌移回牌顶后（牌堆从上到下）。"""
    dq, steps = deque(), []
    for i in range(n, 0, -1):
        dq.appendleft(i)
        a = list(dq)
        dq.appendleft(dq.pop())
        steps.append({"card": i, "put": a, "moved": list(dq)})
    return steps


def cards_forward(order: list[int]) -> list[int]:
    """按题意正着做：先把顶牌移到底，再翻开顶牌拿走。返回翻开顺序。"""
    dq, out = deque(order), []
    while dq:
        dq.append(dq.popleft())
        out.append(dq.popleft())
    return out


# ---------------------------------------------------------------- T5：渗透（自拟 4×4，第 6 步渗透）
PERC = (4, 4, [(1, 2), (4, 3), (2, 2), (3, 4), (3, 3), (2, 3)])   # 1-based 行列


def perc_trace(n: int, m: int, ops):
    """与 solve_t5 同逻辑。每步记：打开的格、连了 TOP/BOT 吗、合并的邻格、各打开格与 TOP/BOT 的根、是否渗透。"""
    TOP, BOT = n * m, n * m + 1
    fa = list(range(n * m + 2))
    opened = [False] * (n * m)

    def find(x):
        while fa[x] != x:
            fa[x] = fa[fa[x]]
            x = fa[x]
        return x

    def union(a, b):
        fa[find(a)] = find(b)

    steps = []
    for k, (r1, c1) in enumerate(ops):
        r, c = r1 - 1, c1 - 1
        u = r * m + c
        opened[u] = True
        top = bot = False
        if r == 0:
            union(u, TOP)
            top = True
        if r == n - 1:
            union(u, BOT)
            bot = True
        nbr = []
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            v = nr * m + nc
            if 0 <= nr < n and 0 <= nc < m and opened[v]:
                union(u, v)
                nbr.append((nr, nc))
        roots = {(x // m, x % m): find(x) for x in range(n * m) if opened[x]}
        roots["TOP"], roots["BOT"] = find(TOP), find(BOT)
        done = roots["TOP"] == roots["BOT"]
        steps.append({"k": k + 1, "cell": (r, c), "top": top, "bot": bot, "nbr": nbr, "roots": roots, "done": done})
        if done:
            break
    return steps


def perc_answer(n, m, ops) -> int:
    st = perc_trace(n, m, ops)
    return st[-1]["k"] if st and st[-1]["done"] else -1


def perc_elif_bug(n, m, ops) -> int:
    """常见错误：写成 if r == 0 … elif r == n - 1 …，n = 1 时格子只连 TOP 不连 BOT。"""
    TOP, BOT = n * m, n * m + 1
    fa = list(range(n * m + 2))
    opened = [False] * (n * m)

    def find(x):
        while fa[x] != x:
            x = fa[x]
        return x
    for k, (r1, c1) in enumerate(ops):
        r, c = r1 - 1, c1 - 1
        u = r * m + c
        opened[u] = True
        if r == 0:
            fa[find(u)] = find(TOP)
        elif r == n - 1:
            fa[find(u)] = find(BOT)
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            v = nr * m + nc
            if 0 <= nr < n and 0 <= nc < m and opened[v]:
                fa[find(u)] = find(v)
        if find(TOP) == find(BOT):
            return k + 1
    return -1


# ---------------------------------------------------------------- T6：括号区间审计（题面样例 1）
BRACKETS = "(()())"
QUERIES = [(1, 6), (2, 5), (1, 5), (3, 4), (4, 4)]
SHOWN = [(2, 5), (1, 5), (3, 4)]                # 片中逐个演示的三问：合法 / 两端不等 / 中途跌破


def prefix(s: str) -> list[int]:
    pre = [0] * (len(s) + 1)
    for i, ch in enumerate(s):
        pre[i + 1] = pre[i] + (1 if ch == '(' else -1)
    return pre


def next_lower(pre: list[int]):
    """与 solve_t6 的单调栈同逻辑。返回 (nxt, 事件列表 [(j, 弹出的下标列表, 入栈后的栈)])。"""
    n = len(pre) - 1
    nxt, stk, ev = [n + 1] * (n + 1), [], []
    for j in range(n + 1):
        popped = []
        while stk and pre[stk[-1]] > pre[j]:
            p = stk.pop()
            nxt[p] = j
            popped.append(p)
        stk.append(j)
        ev.append((j, popped, list(stk)))
    return nxt, ev


def judge(s: str, l: int, r: int):
    """返回 (合法吗, 两端相等吗, nxt[l-1])。"""
    pre = prefix(s)
    nxt, _ = next_lower(pre)
    eq = pre[r] == pre[l - 1]
    return eq and nxt[l - 1] > r, eq, nxt[l - 1]


# ---------------------------------------------------------------- 旁白里的规模数字
N_MAX = 2 * 10 ** 5
NAIVE_T6 = N_MAX * N_MAX                        # 每问现扫：4×10¹⁰
