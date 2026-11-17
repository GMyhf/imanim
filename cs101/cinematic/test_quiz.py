"""看后小测 site/quiz.json 的校验：格式、答案下标、选项不重复；计算题用独立实现重算正确选项。

独立实现故意不调用各片的 *data.py：暴力枚举、闭式、itertools、另写的 BFS / Bellman-Ford 等。
题目里的输入从 quiz_gen 读（同一份题面），算法不共用。
"""
from __future__ import annotations

import itertools
import json
import sys
import unittest
from collections import deque
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "site"))

import quiz_gen as G  # noqa: E402

QUIZ = json.loads((HERE / "site" / "quiz.json").read_text(encoding="utf-8"))
FILMS = [f["id"] for w in json.loads((HERE / "site" / "films.json").read_text(encoding="utf-8"))["weeks"]
         for f in w["films"]]


def right(fid, k):
    q = QUIZ[fid][k]
    return q["options"][q["answer"]]


# ---------------------------------------------------------------- 独立实现
def inversions(a):
    return sum(a[i] > a[j] for i, j in itertools.combinations(range(len(a)), 2))


def postfix(tokens):
    st = []
    ops = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, "*": lambda x, y: x * y, "/": lambda x, y: x / y}
    for t in tokens:
        if t in ops:
            y, x = st.pop(), st.pop()
            st.append(ops[t](x, y))
        else:
            st.append(float(t))
    return st[0]


def rain(h):
    return sum(max(0, min(max(h[:i + 1]), max(h[i:])) - h[i]) for i in range(len(h)))


def first_bad_paren(s):
    st = []
    for i, ch in enumerate(s):
        if ch in "([{":
            st.append(ch)
        elif not st or "([{"[")]}".index(ch)] != st.pop():
            return i
    return None if not st else len(s)


def hanoi_moves(n, s="A", a="B", d="C"):
    return [] if n == 0 else hanoi_moves(n - 1, s, d, a) + [(n, s, d)] + hanoi_moves(n - 1, a, s, d)


def queens_count(n):
    return sum(all(abs(p[i] - p[j]) != j - i for i, j in itertools.combinations(range(n), 2))
               for p in itertools.permutations(range(n)))


def components(n, edges):
    adj = {i: set() for i in range(n)}
    for a, b in edges:
        adj[a].add(b); adj[b].add(a)
    seen, c = set(), 0
    for s in range(n):
        if s not in seen:
            c += 1
            stack = [s]
            while stack:
                u = stack.pop()
                if u not in seen:
                    seen.add(u); stack.extend(adj[u])
    return c


def merge_brute(iv):
    pts = sorted({x for a, b in iv for x in range(2 * a, 2 * b + 1)})      # 加倍后连续整点即同一段
    out = []
    for x in pts:
        if out and x == out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return [[a // 2, b // 2] for a, b in out]


def min_arrows(pts):
    xs = sorted({x for p in pts for x in p})
    for k in range(1, len(pts) + 1):
        for shot in itertools.combinations(xs, k):
            if all(any(a <= s <= b for s in shot) for a, b in pts):
                return k


def max_overlap(iv):
    return max(sum(a <= x <= b for a, b in iv) for x in range(min(a for a, _ in iv), max(b for _, b in iv) + 1))


def coins_min(coins, amt):
    for k in range(1, amt + 1):
        if any(sum(c) == amt for c in itertools.combinations_with_replacement(coins, k)):
            return k


def tri_paths(tri):
    out = []
    for turns in itertools.product((0, 1), repeat=len(tri) - 1):
        j, s = 0, tri[0][0]
        for i, d in enumerate(turns, 1):
            j += d; s += tri[i][j]
        out.append(s)
    return out


def knap01(w, v, cap):
    best = (0, ())
    for r in range(len(w) + 1):
        for pick in itertools.combinations(range(len(w)), r):
            if sum(w[i] for i in pick) <= cap:
                best = max(best, (sum(v[i] for i in pick), tuple(i + 1 for i in pick)))
    return best


def knap_unbounded(w, v, cap):
    @lru_cache(None)
    def f(c):
        return max([0] + [f(c - wi) + vi for wi, vi in zip(w, v) if wi <= c])
    return f(cap)


def lcs_len(s, t):
    @lru_cache(None)
    def f(i, j):
        if i == len(s) or j == len(t):
            return 0
        return f(i + 1, j + 1) + 1 if s[i] == t[j] else max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)


def edit(s, t):
    @lru_cache(None)
    def f(i, j):
        if i == len(s):
            return len(t) - j
        if j == len(t):
            return len(s) - i
        if s[i] == t[j]:
            return f(i + 1, j + 1)
        return 1 + min(f(i + 1, j), f(i, j + 1), f(i + 1, j + 1))
    return f(0, 0)


def grid_bfs(grid, s, g):
    n, m = len(grid), len(grid[0])
    d = {s: 0}
    q = deque([s])
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] != "#" and (nx, ny) not in d:
                d[(nx, ny)] = d[(x, y)] + 1
                q.append((nx, ny))
    return d.get(g, -1)


def bellman_ford(adj, src):
    n = len(adj)
    d = [float("inf")] * n
    d[src] = 0
    for _ in range(n - 1):
        for u in range(n):
            for v, w in adj[u]:
                d[v] = min(d[v], d[u] + w)
    return d


def stale_pops(adj, src):
    """另写一遍懒删除 Dijkstra，只数过期条目（用排序列表代替 heapq）。"""
    dist = {src: 0}
    pq, stale = [(0, src)], 0
    while pq:
        pq.sort()
        d, u = pq.pop(0)
        if d > dist[u]:
            stale += 1
            continue
        for v, w in adj[u]:
            if d + w < dist.get(v, float("inf")):
                dist[v] = d + w
                pq.append((d + w, v))
    return stale


def river_best(L, m, rocks):
    best = 0
    for r in range(m + 1):
        for rm in itertools.combinations(rocks, r):
            kept = [0] + [x for x in rocks if x not in rm] + [L]
            best = max(best, min(b - a for a, b in zip(kept, kept[1:])))
    return best


def split_best(costs, m):
    best = sum(costs)
    for k in range(1, m + 1):
        for cuts in itertools.combinations(range(1, len(costs)), k - 1):
            b = (0,) + cuts + (len(costs),)
            best = min(best, max(sum(costs[b[i]:b[i + 1]]) for i in range(k)))
    return best


def csum_multisets(cands, target):
    """不用回溯：枚举可重复组合（多重集），挑和为 target 的。"""
    lo = min(cands)
    return [c for k in range(1, target // lo + 1)
            for c in itertools.combinations_with_replacement(sorted(cands), k) if sum(c) == target]


def csum_calls_break(cands, target):
    """排序后 break 的调用次数：节点 = 和不超过 target 的非降序列（前缀），含空序列。"""
    cands = sorted(cands)

    def go(start, rest):
        return 1 + sum(go(i, rest - cands[i]) for i in range(start, len(cands)) if cands[i] <= rest)
    return go(0, target)


KNIGHT_JUMPS = [(a, b) for a in (-2, -1, 1, 2) for b in (-2, -1, 1, 2) if abs(a) != abs(b)]


def knight_paths(n, m, start):
    """不用 visited 数组：用 frozenset 枚举从 start 出发的全部不重复马步路径，返回 (调用数, 走满的条数)。"""
    cells = {(i, j) for i in range(n) for j in range(m)}
    calls = full = 0

    def go(p, seen):
        nonlocal calls, full
        calls += 1
        full += len(seen) == len(cells)
        for dx, dy in KNIGHT_JUMPS:
            q = (p[0] + dx, p[1] + dy)
            if q in cells and q not in seen:
                go(q, seen | {q})
    go(start, frozenset([start]))
    return calls, full


def knight_reach(n, m, start):
    """BFS：马从 start 能跳到的格子数（忘了撤销时每格恰好进一次）。"""
    seen, dq = {start}, deque([start])
    while dq:
        x, y = dq.popleft()
        for dx, dy in KNIGHT_JUMPS:
            q = (x + dx, y + dy)
            if 0 <= q[0] < n and 0 <= q[1] < m and q not in seen:
                seen.add(q)
                dq.append(q)
    return len(seen)


def lakes8(grid):
    cells = {(i, j) for i, row in enumerate(grid) for j, ch in enumerate(row) if ch == "W"}
    cnt = 0
    while cells:
        dq = deque([cells.pop()])
        cnt += 1
        while dq:
            x, y = dq.popleft()
            for dx, dy in itertools.product((-1, 0, 1), repeat=2):
                if (x + dx, y + dy) in cells:
                    cells.remove((x + dx, y + dy))
                    dq.append((x + dx, y + dy))
    return cnt


def stair_ways(n):
    """枚举每步走 1 还是 2 的全部序列，数和为 n 的。"""
    return sum(1 for k in range(n + 1) for s in itertools.product((1, 2), repeat=k) if sum(s) == n)


def tri_best_from(tri, i, j):
    """从 (i, j) 出发到底的最大和：枚举从这一格出发的全部路径。"""
    best = None
    for turns in itertools.product((0, 1), repeat=len(tri) - 1 - i):
        c, s = j, tri[i][j]
        for r, d in enumerate(turns, i + 1):
            c += d
            s += tri[r][c]
        best = s if best is None else max(best, s)
    return best


def max_seg_brute(a):
    """枚举全部 [l, r] 区间求和。"""
    return max(sum(a[l:r + 1]) for l in range(len(a)) for r in range(l, len(a)))


def max_block_brute(mat):
    """枚举上下左右四条边，逐块求和。"""
    n, m = len(mat), len(mat[0])
    return max(sum(mat[i][j] for i in range(t, b + 1) for j in range(l, r + 1))
               for t in range(n) for b in range(t, n) for l in range(m) for r in range(l, m))


def rob_brute(h):
    """枚举全部不含相邻下标的子集。"""
    best = 0
    for k in range(len(h) + 1):
        for c in itertools.combinations(range(len(h)), k):
            if all(y - x > 1 for x, y in zip(c, c[1:])):
                best = max(best, sum(h[i] for i in c))
    return best


def split_by_powers(k):
    """1、2、4… 只要加上不超过 k 就收下，最后补余数。"""
    out, p = [], 1
    while sum(out) + p <= k:
        out.append(p)
        p *= 2
    return out + ([k - sum(out)] if k > sum(out) else [])


def exact_brute(w, v, cap):
    best = -1
    for r in range(len(w) + 1):
        for pick in itertools.combinations(range(len(w)), r):
            if sum(w[i] for i in pick) == cap:
                best = max(best, sum(v[i] for i in pick))
    return best


def frac_best(items, cap):
    """连续背包按单价从高到低装，用 Fraction 精确算。"""
    total, rest = Fraction(0), Fraction(cap)
    for val, wt in sorted(items, key=lambda it: Fraction(it[0], it[1]), reverse=True):
        take = min(rest, wt)
        total += Fraction(val, wt) * take
        rest -= take
    return total


def lis_brute(a, ok):
    """枚举所有下标组合，相邻两两满足 ok 的最长长度。"""
    for k in range(len(a), 0, -1):
        for idx in itertools.combinations(range(len(a)), k):
            if all(ok(a[idx[t]], a[idx[t + 1]]) for t in range(k - 1)):
                return k
    return 0


def tails_linear(a):
    """线性扫描版 tails：找第一个 ≥ v 的位置替换，没有就追加。"""
    t = []
    for v in a:
        p = next((k for k, x in enumerate(t) if x >= v), len(t))
        t[p:p + 1] = [v]
    return t


def is_subseq(sub, a):
    it = iter(a)
    return all(x in it for x in sub)


def grid_rd_brute(g):
    """枚举所有只向右 / 向下的路径。"""
    n, m = len(g), len(g[0])
    best = None
    for downs in itertools.combinations(range(n + m - 2), n - 1):
        i = j = 0
        s = g[0][0]
        for k in range(n + m - 2):
            i, j = (i + 1, j) if k in downs else (i, j + 1)
            s += g[i][j]
        best = s if best is None else min(best, s)
    return best


def grid_four_relax(g):
    """四方向反复松弛到不再变化。"""
    n, m = len(g), len(g[0])
    d = [[float("inf")] * m for _ in range(n)]
    d[0][0] = g[0][0]
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in range(m):
                for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < n and 0 <= b < m and d[i][j] + g[a][b] < d[a][b]:
                        d[a][b] = d[i][j] + g[a][b]
                        changed = True
    return d[-1][-1]


def cx_loop_runs(n):
    """直接数：for i in range(n): for j in range(i, n)。"""
    return sum(1 for i in range(n) for j in range(i, n))


def cx_marks_formula(limit):
    """每个素数 p ≤ √limit 从 p² 划到 limit：⌊(limit − p²)/p⌋ + 1 次；素数用试除独立求。"""
    ps = [p for p in range(2, int(limit ** 0.5) + 1) if all(p % d for d in range(2, p))]
    return sum((limit - p * p) // p + 1 for p in ps)


def divide_mults(b):
    """讲义 fast_pow 的乘法次数，另写成自底向上逐位扫：每位平方一次，位为 1 再乘一次。"""
    m = 0
    while b:
        m += 1 + (b & 1)
        b >>= 1
    return m


def divide_squares(w, h):
    """长方形切正方形，另写成一刀一块的减法：返回 (最后边长, 块数)。"""
    cnt = side = 0
    while w and h:
        side = min(w, h)
        cnt += 1
        if w >= h:
            w -= h
        else:
            h -= w
    return side, cnt


@lru_cache(maxsize=None)
def divide_twice_calls(b):
    return 1 if b == 0 else 1 + 2 * divide_twice_calls(b // 2)


def food_brute_lies(n, stmts):
    """维护已接受的真话；每来一句，穷举涉及动物的物种 0/1/2，能同时满足才算真话。x 吃 y ⇔ s[x] − s[y] ≡ 1。"""
    ok, lies = [], 0
    for kind, x, y in stmts:
        if not (1 <= x <= n and 1 <= y <= n) or (kind == 2 and x == y):
            lies += 1
            continue
        cand = ok + [(kind, x, y)]
        who = sorted({a for _, a, _ in cand} | {b for _, _, b in cand})
        pos = {a: i for i, a in enumerate(who)}
        if any(all((s[pos[a]] - s[pos[b]]) % 3 == (0 if t == 1 else 1) for t, a, b in cand)
               for s in itertools.product(range(3), repeat=len(who))):
            ok.append((kind, x, y))
        else:
            lies += 1
    return lies


def food_classes(n, stmts):
    """真话确定下来的「等价类 × 三类」：按真话把动物连成若干块，每块对应 3 个集合，没提到的动物各占 3 个。"""
    par = list(range(n + 1))

    def find(x):
        while par[x] != x:
            x = par[x]
        return x
    for _, x, y in stmts:
        par[find(x)] = find(y)
    return 3 * len({find(a) for a in range(1, n + 1)})


def sb_naruto_relax(grid, T):
    """在（行、列、剩余查克拉）状态上反复松弛到稳定，取佐助各层的最小步数。"""
    n, m = len(grid), len(grid[0])
    cells = [(i, j) for i in range(n) for j in range(m)]
    s = next(c for c in cells if grid[c[0]][c[1]] == '@')
    g = next(c for c in cells if grid[c[0]][c[1]] == '+')
    inf = float("inf")
    d = {(i, j, t): inf for i, j in cells for t in range(T + 1)}
    d[(*s, T)] = 0
    changed = True
    while changed:
        changed = False
        for (x, y, t), v in list(d.items()):
            for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if v < inf and 0 <= a < n and 0 <= b < m:
                    nt = t - (grid[a][b] == '#')
                    if nt >= 0 and d[(a, b, nt)] > v + 1:
                        d[(a, b, nt)] = v + 1
                        changed = True
    best = min(d[(*g, t)] for t in range(T + 1))
    return -1 if best == inf else best


def sb_flood_by_source(h, sources):
    """每个放水点单独用栈灌一遍，各格取最高水位；返回被淹格数。"""
    n, m = len(h), len(h[0])
    wet = set()
    for sx, sy in sources:
        lv, st, seen = h[sx][sy], [(sx, sy)], {(sx, sy)}
        while st:
            x, y = st.pop()
            wet.add((x, y))
            for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= a < n and 0 <= b < m and (a, b) not in seen and h[a][b] < lv:
                    seen.add((a, b))
                    st.append((a, b))
    return len(wet)


def rt_loop_body_count(n):
    """独立方法：sys.settrace 单步数讲义循环在 n 与 0 下执行的字节码条数之差（即循环体共执行几条）。"""
    src = "s = 0\nfor i in range(n):\n    s += i\n"

    def run(m):
        code = compile(src, "<q>", "exec")
        cnt = [0]

        def tr(frame, ev, arg):
            frame.f_trace_opcodes = True
            if ev == "opcode" and frame.f_code is code:
                cnt[0] += 1
            return tr
        sys.settrace(tr)
        try:
            exec(code, {"n": m})
        finally:
            sys.settrace(None)
        return cnt[0]
    return run(n) - run(0)


def rt_col_misses(n, line, ways):
    """独立方法：按列访问顺序 + 记最近使用时刻的 LRU。"""
    last, miss = {}, 0
    for t, (i, j) in enumerate((i, j) for j in range(n) for i in range(n)):
        key = (i, j // line)
        if key not in last:
            miss += 1
            if len(last) == ways:
                del last[min(last, key=last.get)]
        last[key] = t
    return miss


def rt_block_writes(n, buf):
    """独立方法：总字节数按缓冲区大小向上取整。"""
    nbytes = sum(len(str(i * i)) + 1 for i in range(n))
    return -(-nbytes // buf)


def deadline_best(tasks):
    """枚举全部子集，按截止排序逐个检查能否全部按时；不经堆。"""
    for k in range(len(tasks), -1, -1):
        for sub in itertools.combinations(tasks, k):
            t, ok = 0, True
            for c, d in sorted(sub, key=lambda x: x[1]):
                t += c
                ok = ok and t <= d
            if ok:
                return k
    return 0


def deadline_drops(tasks):
    """自己写的大根堆反悔：用排好序的列表代替 heapq，返回依次扔掉的耗时。"""
    kept, total, out = [], 0, []
    for c, d in sorted(tasks, key=lambda x: x[1]):
        kept.append(c)
        total += c
        if total > d:
            kept.sort()
            out.append(kept.pop())
            total -= out[-1]
    return out


def shop_cover_bits(bag, x):
    """位运算子集和：第 v 位为 1 表示能凑出 v；检查 1..x 全为 1。"""
    bits = 1
    for c in bag:
        bits |= bits << c
    full = (1 << (x + 1)) - 2
    return bits & full == full


def shop_min_brute(x, coins):
    """枚数从小到大枚举全部多重组合；最小面值大于 1 时 1 凑不出，直接无解。"""
    if min(coins) > 1:
        return -1
    for k in itertools.count(1):
        if any(shop_cover_bits(b, x) for b in itertools.combinations_with_replacement(sorted(set(coins)), k)):
            return k


def nov_reveal(order):
    """牌堆魔术按题意正着做（不调用 novdata）。"""
    dq, out = deque(order), []
    while dq:
        dq.rotate(-1)
        out.append(dq.popleft())
    return out


def nov_escape(g):
    """逐格模拟 nm+1 步还在场内就是绕圈（不调用 novdata）。"""
    n, m = len(g), len(g[0])
    mv = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
    cnt = 0
    for si in range(n):
        for sj in range(m):
            i, j = si, sj
            for _ in range(n * m + 1):
                if not (0 <= i < n and 0 <= j < m):
                    break
                i, j = i + mv[g[i][j]][0], j + mv[g[i][j]][1]
            cnt += not (0 <= i < n and 0 <= j < m)
    return cnt


def partition_brute(n, k):
    """穷举非降 k 元组（不调用 partitiondata）。"""
    return sum(1 for c in itertools.combinations_with_replacement(range(1, n + 1), k) if sum(c) == n)


def partition_first_parts(n, k):
    """根节点第一份能取哪些值：存在一个以 x 开头、各份 ≥ x 的非降分法。"""
    return [x for x in range(1, n + 1)
            if any(c[0] == x for c in itertools.combinations_with_replacement(range(1, n + 1), k) if sum(c) == n)]


class QuizFormatTest(unittest.TestCase):
    def test_films_and_shape(self):
        self.assertEqual(sorted(QUIZ), sorted(FILMS))
        for fid, qs in QUIZ.items():
            self.assertEqual(len(qs), 3, fid)
            for q in qs:
                self.assertEqual(set(q), {"q", "options", "answer", "explain"}, fid)
                self.assertTrue(q["q"].strip() and q["explain"].strip(), fid)
                self.assertGreaterEqual(len(q["options"]), 3, (fid, q["q"]))
                self.assertEqual(len(set(q["options"])), len(q["options"]), (fid, q["q"]))
                self.assertTrue(all(isinstance(o, str) and o.strip() for o in q["options"]))
                self.assertIsInstance(q["answer"], int)
                self.assertTrue(0 <= q["answer"] < len(q["options"]))

    def test_reproducible(self):
        self.assertEqual(G.build(), QUIZ, "quiz.json 不是最新的：重跑 site/quiz_gen.py")

    def test_answers_not_always_same_slot(self):
        slots = [q["answer"] for qs in QUIZ.values() for q in qs]
        self.assertGreater(len(set(slots)), 2)


class QuizAnswerTest(unittest.TestCase):
    """每片至少一道「新输入」计算题，这里逐题独立重算。"""

    def test_sort(self):
        self.assertEqual(right("sort", 0), str(inversions(G.INV_ARR)))
        x = G.MERGE_R[0]
        self.assertEqual(right("sort", 1), str(sum(v > x for v in G.MERGE_L)))
        rows = sorted(sorted([("a", 2), ("b", 1), ("c", 2)]), key=lambda r: r[1])
        self.assertEqual(right("sort", 2), "、".join(f"{k}{v}" for k, v in rows))

    def test_stack(self):
        self.assertEqual(right("stack", 0), f"{postfix(G.POSTFIX):g}")
        self.assertEqual(right("stack", 1), str(rain(G.RAIN)))
        i = first_bad_paren(G.BAD_PAREN)
        self.assertTrue(right("stack", 2).startswith(f"读到第 {i + 1} 个字符 {G.BAD_PAREN[i]} 时"))

    def test_fib(self):
        f = [0, 1, 1]
        for _ in range(G.FIB_N):
            f.append(f[-1] + f[-2])
        self.assertEqual(right("fib", 0), str(2 * f[G.FIB_N] - 1))            # 闭式 C(n) = 2F(n) − 1
        self.assertEqual(right("fib", 1), str(2 * G.FIB_N - 3))              # 一条链 n−1 次 + 查表 n−2 次

    def test_hanoi(self):
        self.assertEqual(right("hanoi", 0), str(2 ** G.HANOI_N - 1))
        k, s, d = hanoi_moves(3)[G.HANOI3_STEP - 1]
        self.assertEqual(right("hanoi", 1), f"把 {k} 号盘从 {s} 移到 {d}")
        big = [i for i, m in enumerate(hanoi_moves(G.HANOI_BIG), 1) if m[0] == G.HANOI_BIG]
        self.assertEqual(right("hanoi", 2), str(big[0]))

    def test_perm(self):
        p = sorted(itertools.permutations(G.PERM_A))[G.PERM_K - 1]
        self.assertEqual(right("perm", 0), "".join(map(str, p)))
        n = len(G.PERM_A)
        self.assertEqual(right("perm", 1), str(sum(len(list(itertools.permutations(range(n), k))) for k in range(n + 1))))
        leaves = [tuple(x for x, b in zip(G.SUBSET, bits) if b) for bits in itertools.product((0, 1), repeat=3)]
        self.assertEqual(right("perm", 2), str(leaves.index((1, 3)) + 1))

    def test_queens(self):
        self.assertEqual(right("queens", 0), str(queens_count(G.QUEENS_N)))
        first = next(p for p in itertools.permutations(range(4))
                     if all(abs(p[i] - p[j]) != j - i for i, j in itertools.combinations(range(4), 2)))
        self.assertEqual(right("queens", 1), " ".join(str(c + 1) for c in first))

        def calls(row, path):          # 每个合法前缀都是一次调用
            return 1 + (0 if row == 4 else sum(calls(row + 1, path + [c]) for c in range(4)
                                               if all(c != pc and abs(c - pc) != row - r for r, pc in enumerate(path))))
        self.assertEqual(right("queens", 2), str(calls(0, [])))

    def test_dsu(self):
        # 另写一遍：递归 find 全压缩，按集合大小合并，等大把 y 的根挂到 x 的根下；最后 find(3)
        parent, size = list(range(G.DSU_N)), [1] * G.DSU_N

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        for a, b in G.DSU_OPS:
            ra, rb = find(a), find(b)
            if ra != rb:
                big, small = (rb, ra) if size[ra] < size[rb] else (ra, rb)
                parent[small] = big
                size[big] += size[small]
        find(3)
        self.assertEqual(right("dsu", 0), str(parent[3]))
        self.assertEqual(right("dsu", 1), str(components(G.REL_N, G.REL_PAIRS)))
        first = next(G.CYCLE[k] for k in range(len(G.CYCLE))
                     if components(4, G.CYCLE[:k]) == components(4, G.CYCLE[:k + 1]))
        self.assertEqual(right("dsu", 2), f"({first[0]}, {first[1]})")

    def test_interval(self):
        self.assertEqual(right("interval", 0), " ".join(f"[{a}, {b}]" for a, b in merge_brute(G.MERGE_IV)))
        self.assertEqual(right("interval", 1), str(min_arrows(G.BALLOONS)))
        self.assertEqual(right("interval", 2), str(max_overlap(G.GROUPS)))

    def test_dpintro(self):
        self.assertEqual(right("dpintro", 0), str(coins_min(G.COINS, G.AMOUNT)))
        self.assertEqual(right("dpintro", 1), str(max(s for s in tri_paths(G.TRI) if s % 2)))

    def test_knap(self):
        val, pick = knap01(G.KW, G.KV, G.KCAP)
        self.assertEqual(right("knap", 0), str(val))
        self.assertEqual(right("knap", 1), str(knap_unbounded(G.KW, G.KV, G.KCAP)))
        self.assertEqual(right("knap", 2), "第 " + "、".join(map(str, pick)) + " 件")

    def test_lcs(self):
        self.assertEqual(right("lcs", 0), str(lcs_len(*G.LCS_PAIR)))
        self.assertEqual(right("lcs", 1), str(edit(*G.ED_PAIR)))

    def test_bfs(self):
        self.assertEqual(right("bfs", 0), str(grid_bfs(G.MAZE, (0, 0), (3, 3))))
        zeros = [(i, j) for i, r in enumerate(G.MAT) for j, v in enumerate(r) if v == 0]
        self.assertEqual(right("bfs", 1), str(min(abs(0 - i) + abs(2 - j) for i, j in zeros)))

    def test_dijkstra(self):
        self.assertEqual(right("dijkstra", 0), f"{bellman_ford(G.GRAPH, 0)[4]:g}")
        self.assertEqual(right("dijkstra", 1), str(stale_pops(G.GRAPH, 0)))

    def test_bsearch(self):
        self.assertEqual(right("bsearch", 0), str(river_best(*G.RIVER)))
        self.assertEqual(right("bsearch", 1), str(split_best(G.MONTH, G.MONTH_M)))

    def test_binary(self):
        v = G.BIN_BITS - 256 if G.BIN_BITS >= 128 else G.BIN_BITS
        self.assertEqual(right("binary", 0), str(v).replace("-", "−"))
        self.assertEqual(right("binary", 1), format(256 + G.BIN_NEG, "08b"))
        r = sum(G.BIN_ADD) % 256
        self.assertEqual(right("binary", 2), str(r - 256 if r >= 128 else r).replace("-", "−"))

    def test_float(self):
        import math
        import struct
        e = struct.unpack(">Q", struct.pack(">d", G.FLOAT_X))[0] >> 52 & 0x7FF
        self.assertEqual(right("float", 0), str(e))
        self.assertEqual(e - 1023, math.frexp(G.FLOAT_X)[1] - 1)
        self.assertEqual(right("float", 1), repr(sum(G.FLOAT_SUM)))
        from fractions import Fraction
        exact = [x for x in G.FLOAT_EXACT if Fraction(x).denominator & (Fraction(x).denominator - 1) == 0]
        self.assertEqual([right("float", 2)], exact)

    def test_matrix(self):
        self.assertEqual(right("matrix", 0), "[0, 0, 5]")
        m, n = len(G.ROT), len(G.ROT[0])
        cw = [[G.ROT[m - 1 - i][j] for i in range(m)] for j in range(n)]   # 下标公式 b[j][i] = a[m-1-i][j]
        self.assertEqual(right("matrix", 1), str(cw[0]))
        n, qi, qj = G.SPIRAL_Q
        g = [[0] * n for _ in range(n)]
        top, bot, lef, rig, v = 0, n - 1, 0, n - 1, 1                      # 按层剥皮
        while top <= bot and lef <= rig:
            for j in range(lef, rig + 1):
                g[top][j], v = v, v + 1
            for i in range(top + 1, bot + 1):
                g[i][rig], v = v, v + 1
            if top < bot:
                for j in range(rig - 1, lef - 1, -1):
                    g[bot][j], v = v, v + 1
            if lef < rig:
                for i in range(bot - 1, top, -1):
                    g[i][lef], v = v, v + 1
            top, bot, lef, rig = top + 1, bot - 1, lef + 1, rig - 1
        self.assertEqual(right("matrix", 2), str(g[qi][qj]))

    def test_lights(self):
        R, C = 5, 6
        self.assertEqual(right("lights", 0), str(sum(0 <= i < R and 0 <= j < C
                                                     for i, j in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)))))
        # GF(2) 高斯消元：30 个未知数（各按钮按不按），每盏灯一条方程
        rows = []
        on = set(G.LIGHT_ON)
        for r in range(R):
            for c in range(C):
                mask = 0
                for i, j in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if 0 <= i < R and 0 <= j < C:
                        mask |= 1 << (i * C + j)
                rows.append([mask, int((r, c) in on)])
        n, piv = R * C, []
        for col in range(n):
            k = next((k for k in range(len(piv), len(rows)) if rows[k][0] >> col & 1), None)
            self.assertIsNotNone(k, "矩阵满秩，解唯一")
            rows[len(piv)], rows[k] = rows[k], rows[len(piv)]
            for t in range(len(rows)):
                if t != len(piv) and rows[t][0] >> col & 1:
                    rows[t][0] ^= rows[len(piv)][0]
                    rows[t][1] ^= rows[len(piv)][1]
            piv.append(col)
        self.assertEqual(right("lights", 2), str(sum(rows[k][1] for k in range(n))))

    def test_subsets(self):
        self.assertEqual(right("subsets", 0), str(len(csum_multisets(G.SUBS_CANDS, G.SUBS_TARGET))))
        self.assertEqual(right("subsets", 1), str(csum_calls_break(G.SUBS_CANDS, G.SUBS_TARGET)))
        # 往后挑的先序 = 按字典序比较的升序子集序列
        subs = sorted((list(c) for k in range(len(G.SUBS_A) + 1) for c in itertools.combinations(G.SUBS_A, k)))
        self.assertEqual(right("subsets", 2), "[" + ", ".join(map(str, subs[G.SUBS_K - 1])) + "]")

    def test_knight(self):
        n, m, sx, sy = G.KNIGHT_Q
        self.assertEqual(right("knight", 0), str(knight_paths(n, m, (sx, sy))[1]))
        self.assertEqual(right("knight", 1), str(lakes8(G.LAKE_Q)))
        fn, fm, fx, fy = G.KNIGHT_FORGET
        self.assertEqual(right("knight", 2), str(knight_reach(fn, fm, (fx, fy))))

    def test_triangle(self):
        self.assertEqual(right("triangle", 0), str(stair_ways(G.STAIR_Q)))
        self.assertEqual(right("triangle", 1), str(tri_best_from(G.TRI_Q, 0, 0)))
        n = len(G.TRI_Q)
        row = [tri_best_from(G.TRI_Q, n - 2, j) for j in range(n - 1)] + [G.TRI_Q[-1][-1]]
        self.assertEqual(right("triangle", 2), "[" + ", ".join(map(str, row)) + "]")

    def test_kadane(self):
        self.assertEqual(right("kadane", 0), str(max_seg_brute(G.KAD_ARR)))
        self.assertEqual(right("kadane", 1), str(max_block_brute(G.KAD_MAT)))
        self.assertEqual(right("kadane", 2), str(rob_brute(G.ROB_H)))

    def test_knapvar(self):
        parts = split_by_powers(G.KV_SPLIT)
        reach = {0}
        for p in parts:
            reach |= {r + p for r in reach}
        self.assertEqual(reach, set(range(G.KV_SPLIT + 1)))
        self.assertEqual(right("knapvar", 0), ", ".join(map(str, parts)))
        self.assertEqual(right("knapvar", 1), str(exact_brute(G.KV_EX_W, G.KV_EX_V, G.KV_EX_CAP)))
        self.assertEqual(right("knapvar", 2), f"{float(frac_best(G.KV_FRAC, G.KV_FRAC_CAP)):g}")

    def test_lis(self):
        self.assertEqual(right("lis", 0), str(lis_brute(G.LIS_ARR, lambda x, y: x < y)))
        t = tails_linear(G.LIS_TRAP)
        self.assertEqual(len(t), lis_brute(G.LIS_TRAP, lambda x, y: x < y))
        self.assertEqual(right("lis", 1), f"[{', '.join(map(str, t))}]，" + ("是" if is_subseq(t, G.LIS_TRAP) else "不是"))
        self.assertTrue(right("lis", 2).startswith(f"{lis_brute(G.LIS_EQ, lambda x, y: x <= y)}，bisect_right"))

    def test_grid(self):
        self.assertEqual(right("grid", 0), str(grid_rd_brute(G.GRID_RD)))
        self.assertEqual(right("grid", 1), str(grid_four_relax(G.GRID_4)))
        n, m = G.GRID_CNT
        self.assertEqual(right("grid", 2), str(len(list(itertools.combinations(range(n + m - 2), n - 1)))))

    def test_complexity(self):
        self.assertEqual(right("complexity", 0), str(cx_loop_runs(G.CX_LOOP_N)))
        n = G.CX_LIMIT_N
        lg = len(bin(n)) - 3 + 1                      # ⌈log₂ n⌉ 的整数上界，独立于 math.log2
        ops = {"O(n²)": n * n, "O(n√n)": n * int(n ** 0.5 + 1), "O(n log² n)": n * lg * lg, "O(n log n)": n * lg}
        over = [k for k, v in ops.items() if v > 10 ** 8]
        self.assertEqual(over, ["O(n²)"])
        self.assertEqual(right("complexity", 1), "、".join(over))
        self.assertEqual(set(QUIZ["complexity"][1]["options"]), set(ops))
        self.assertEqual(right("complexity", 2), str(cx_marks_formula(G.CX_SIEVE_N)))

    def test_divide(self):
        self.assertEqual(right("divide", 0), str(divide_mults(G.DIV_POW_B)))
        side, cnt = divide_squares(*G.DIV_RECT)
        self.assertEqual(side, max(d for d in range(1, min(G.DIV_RECT) + 1)
                                   if all(x % d == 0 for x in G.DIV_RECT)))
        self.assertEqual(right("divide", 1), f"边长 {side}，共 {cnt} 块")
        self.assertEqual(right("divide", 2), str(divide_twice_calls(G.DIV_TWICE_B)))

    def test_foodchain(self):
        self.assertEqual(right("foodchain", 0), str(food_brute_lies(G.FOOD_Q_N, G.FOOD_Q)))
        extra = food_brute_lies(3, G.FOOD_INFER + [G.FOOD_INFER_Q]) - food_brute_lies(3, G.FOOD_INFER)
        self.assertEqual(right("foodchain", 1), "假话" if extra else "真话")
        self.assertEqual(food_brute_lies(4, G.FOOD_SETS), 0)              # 题面说都是真话
        self.assertEqual(right("foodchain", 2), str(food_classes(4, G.FOOD_SETS)))

    def test_statebfs(self):
        self.assertEqual(right("statebfs", 0), str(sb_naruto_relax(G.SB_GRID, G.SB_T)))
        n, m, t = G.SB_SIZE
        self.assertEqual(right("statebfs", 1), str(len(list(itertools.product(range(n), range(m), range(t + 1))))))
        self.assertEqual(right("statebfs", 2), str(sb_flood_by_source(G.SB_FL_H, G.SB_FL_SRC)))

    def test_runtime(self):
        self.assertEqual(right("runtime", 0), str(G.RT_PER * G.RT_LOOP_N))
        if sys.version_info[:2] in ((3, 11), (3, 14)):                 # 每圈条数随解释器版本变，只在实测过的版本上核对
            self.assertEqual(rt_loop_body_count(G.RT_LOOP_N), G.RT_PER * G.RT_LOOP_N)
        self.assertEqual(right("runtime", 1), str(rt_col_misses(*G.RT_CACHE)))
        self.assertEqual(right("runtime", 2), str(rt_block_writes(G.RT_PRINT_N, G.RT_BUF)))

    def test_deadline(self):
        self.assertEqual(right("deadline", 0), str(deadline_best(G.DL_TASKS)))
        self.assertEqual(right("deadline", 1), "已选任务（含新来的）里耗时最长的")
        drops = deadline_drops(G.DL_TASKS)
        self.assertEqual(len(G.DL_TASKS) - len(drops), deadline_best(G.DL_TASKS))
        self.assertEqual(right("deadline", 2), ", ".join(map(str, drops)))

    def test_shopping(self):
        self.assertEqual(right("shopping", 0), str(shop_min_brute(G.SHOP_X, G.SHOP_COINS)))
        hole = next(v for v in itertools.count(1) if not shop_cover_bits(G.SHOP_BAG, v))
        self.assertEqual(right("shopping", 1), str(hole))
        neg = [(x, c) for x, c in G.SHOP_CANDS if shop_min_brute(x, c) == -1]
        self.assertEqual(len(neg), 1)
        x, c = neg[0]
        self.assertEqual(right("shopping", 2), f"X = {x}，面值 {' '.join(map(str, c))}")

    def test_nov(self):
        n = G.NOV_CARDS
        want = next(p for p in itertools.permutations(range(1, n + 1)) if nov_reveal(p) == list(range(1, n + 1)))
        self.assertEqual(right("nov", 0), " ".join(map(str, want)))
        self.assertEqual(right("nov", 1), str(nov_escape(G.NOV_ARROWS)))
        s, (l, r) = G.NOV_BR, G.NOV_Q
        sub, d, ok = s[l - 1:r], 0, True
        for ch in sub:
            d += 1 if ch == "(" else -1
            ok = ok and d >= 0
        self.assertFalse(ok and d == 0)
        pre = [0]
        for ch in s:
            pre.append(pre[-1] + (1 if ch == "(" else -1))
        nx = next((k for k in range(l, len(s) + 1) if pre[k] < pre[l - 1]), len(s) + 1)
        self.assertEqual(pre[r], pre[l - 1])
        self.assertEqual(right("nov", 2), f"NO：nxt[{l - 1}] = {nx} ≤ {r}，中途跌破起点")

    def test_partition(self):
        n, k = G.PART_Q1
        self.assertEqual(right("partition", 0), str(partition_brute(n, k)))
        xs = partition_first_parts(*G.PART_ROOT)
        self.assertEqual(xs, list(range(xs[0], xs[-1] + 1)))
        self.assertEqual(right("partition", 1), f"{xs[0]} 到 {xs[-1]}")
        self.assertTrue(right("partition", 2).startswith("深搜"))
        self.assertIn(f"只有 {partition_brute(*G.PART_LIST)} 种", QUIZ["partition"][2]["explain"])


if __name__ == "__main__":
    unittest.main()
