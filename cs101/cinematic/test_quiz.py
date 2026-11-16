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

    # ---- 新片：独立实现（不调用 binarydata / floatdata / matrixdata / lightsdata）
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


if __name__ == "__main__":
    unittest.main()
