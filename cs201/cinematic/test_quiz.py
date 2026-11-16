"""看后小测 site/quiz.json 的对撞测试：格式、下标、与生成脚本一致；计算题用独立实现重算正确项。

(cd cs201/cinematic && PYTHONPATH=../../cs101/cinematic python -m unittest test_quiz)
"""
import heapq
import json
import sys
import unittest
from fractions import Fraction
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "site"))
import quiz_gen  # noqa: E402

FMT = quiz_gen.fmt_list


# ---------------------------------------------------------------- 独立实现（不调用各片 data 模块）
def postfix_of(expr):
    """递归下降：expr := term (('+'|'-') term)*，term := factor (('*'|'/') factor)*。"""
    toks, i = [], 0
    while i < len(expr):
        if expr[i].isdigit():
            j = i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            toks.append(expr[i:j])
            i = j
        else:
            toks.append(expr[i])
            i += 1
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def eat():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def factor():
        if peek() == "(":
            eat()
            r = expression()
            eat()
            return r
        return [eat()]

    def term():
        r = factor()
        while peek() in ("*", "/"):
            op = eat()
            r = r + factor() + [op]
        return r

    def expression():
        r = term()
        while peek() in ("+", "-"):
            op = eat()
            r = r + term() + [op]
        return r
    return " ".join(expression())


def eval_postfix(s):
    st = []
    for t in s.split():
        if t in "+-*/":
            b, a = st.pop(), st.pop()
            st.append({"+": a + b, "-": a - b, "*": a * b, "/": Fraction(a, b)}[t])
        else:
            st.append(int(t))
    return st[0]


def lps_brute(p):
    return [max(k for k in range(i + 1) if p[:k] == p[i + 1 - k:i + 1]) for i in range(len(p))]


def pre_from(ino, post):
    if not ino:
        return ""
    r = post[-1]
    k = ino.index(r)
    return r + pre_from(ino[:k], post[:k]) + pre_from(ino[k + 1:], post[k:-1])


def bst_insert(tree, root, x):
    if root is None:
        tree[x] = [None, None]
        return x
    cur = root
    while True:
        side = 0 if x < cur else 1
        if tree[cur][side] is None:
            tree[cur][side] = x
            tree[x] = [None, None]
            return root
        cur = tree[cur][side]


def bst_build(keys):
    tree, root = {}, None
    for k in keys:
        root = bst_insert(tree, root, k)
    return tree, root


def sift_down(a, i):
    n = len(a)
    while 2 * i + 1 < n:
        c = 2 * i + 1
        if c + 1 < n and a[c + 1] < a[c]:
            c += 1
        if a[i] <= a[c]:
            break
        a[i], a[c] = a[c], a[i]
        i = c


def is_min_heap(a):
    return all(a[(i - 1) // 2] <= a[i] for i in range(1, len(a)))


def huffman(w):
    """返回 (WPL, 各字符深度)；合并时把两边所有字符的深度加一。"""
    h = [(v, i, (k,)) for i, (k, v) in enumerate(w.items())]
    heapq.heapify(h)
    depth = {k: 0 for k in w}
    nxt, total = len(h), 0
    while len(h) > 1:
        a, b = heapq.heappop(h), heapq.heappop(h)
        for s in a[2] + b[2]:
            depth[s] += 1
        total += a[0] + b[0]
        heapq.heappush(h, (a[0] + b[0], nxt, a[2] + b[2]))
        nxt += 1
    return total, depth


def topo_ok(n, edges, seq):
    pos = {v: i for i, v in enumerate(seq)}
    return sorted(seq) == list(range(n)) and all(pos[u] < pos[v] for u, v in edges)


def kahn(n, edges):
    indeg = [0] * n
    for _, v in edges:
        indeg[v] += 1
    q = [v for v in range(n) if indeg[v] == 0]
    out = []
    while q:
        u = q.pop(0)
        out.append(u)
        for v in sorted(v for x, v in edges if x == u):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return out


def reach(adj, s):
    seen, st = {s}, [s]
    while st:
        u = st.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                st.append(v)
    return seen


def ve_vl(n, edges):
    from functools import lru_cache

    @lru_cache(None)
    def ve(v):
        return max((ve(u) + w for u, x, w in edges if x == v), default=0)
    total = max(ve(v) for v in range(n))

    @lru_cache(None)
    def vl(u):
        return min((vl(v) - w for x, v, w in edges if x == u), default=total)
    return total, ve, vl


def dijkstra(n, edges, s):
    d = [float("inf")] * n
    d[s] = 0
    pq = [(0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]:
            continue
        for x, v, w in edges:
            if x == u and du + w < d[v]:
                d[v] = du + w
                heapq.heappush(pq, (d[v], v))
    return d


def simple_paths_min(n, edges, s, t):
    best = float("inf")

    def go(u, seen, cost):
        nonlocal best
        if u == t:
            best = min(best, cost)
            return
        for x, v, w in edges:
            if x == u and v not in seen:
                go(v, seen | {v}, cost + w)
    go(s, {s}, 0)
    return best


def mst_brute(n, edges):
    best = None
    for sub in combinations(edges, n - 1):
        parent = list(range(n))

        def f(x):
            while parent[x] != x:
                x = parent[x]
            return x
        ok = True
        for u, v, _ in sub:
            a, b = f(u), f(v)
            if a == b:
                ok = False
                break
            parent[a] = b
        if ok:
            w = sum(e[2] for e in sub)
            best = w if best is None else min(best, w)
    return best


def lomuto(a):
    a = list(a)
    pivot, b = a[-1], 0
    for i in range(len(a) - 1):
        if a[i] < pivot:
            a[b], a[i] = a[i], a[b]
            b += 1
    a[b], a[-1] = a[-1], a[b]
    return a, b


def linear_probe(keys, m):
    table, where = [None] * m, {}
    for k in keys:
        p = k % m
        while table[p] is not None:
            p = (p + 1) % m
        table[p], where[k] = k, p
    return where


def longest_pal(s):
    best = ""
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            t = s[i:j]
            if t == t[::-1] and len(t) > len(best):
                best = t
    return best


def expected(check):
    """由题型与输入独立算出正确项（字符串，与选项同格式）；topo_invalid 例外，单独判。"""
    kind, *a = check
    if kind == "seq_avg":
        n = a[0]
        return str(Fraction(n * (n + 1) // 2, n))
    if kind == "middle":
        return str(a[0] // 2 + 1)
    if kind == "postfix":
        return postfix_of(a[0])
    if kind == "evalpost":
        return str(eval_postfix(a[0]))
    if kind == "lps":
        return FMT(lps_brute(a[0]))
    if kind == "rep":
        s = a[0]
        return str(max(k for k in range(1, len(s) + 1) if len(s) % k == 0 and s[:len(s) // k] * k == s))
    if kind == "pre_from_in_post":
        return pre_from(*a)
    if kind == "bst_search":
        tree, cur = bst_build(a[0])
        cnt = 0
        while cur is not None:
            cnt += 1
            if cur == a[1]:
                break
            cur = tree[cur][0 if a[1] < cur else 1]
        return str(cnt)
    if kind == "bst_levels":
        tree, root = bst_build(a[0])

        def h(x):
            return 0 if x is None else 1 + max(h(tree[x][0]), h(tree[x][1]))
        return str(h(root))
    if kind == "buildheap":
        h = list(a[0])
        for i in reversed(range(len(h) // 2)):
            sift_down(h, i)
        assert is_min_heap(h) and sorted(h) == sorted(a[0])
        return FMT(h)
    if kind == "heap_insert":
        h = list(a[0]) + [a[1]]
        i = len(h) - 1
        while i and h[(i - 1) // 2] > h[i]:
            h[i], h[(i - 1) // 2] = h[(i - 1) // 2], h[i]
            i = (i - 1) // 2
        assert is_min_heap(h)
        return FMT(h)
    if kind == "wpl":
        return str(huffman(a[0])[0])
    if kind == "huff_depth":
        return str(huffman(a[0])[1][a[1]])
    if kind == "forest_post":
        ch, roots = a

        def post(v):
            return "".join(post(c) for c in ch[v]) + v
        return "".join(post(r) for r in roots)
    if kind == "forest_right":
        ch, roots, v = a
        for sibs in [roots] + list(ch.values()):
            if v in sibs:
                i = sibs.index(v)
                return sibs[i + 1] if i + 1 < len(sibs) else "无（空）"
    if kind == "kahn":
        out = kahn(*a)
        assert topo_ok(a[0], a[1], out)
        return " ".join(map(str, out))
    if kind == "scc_count":
        adj = a[0]
        r = [reach(adj, s) for s in range(len(adj))]
        return str(len({frozenset(v for v in r[u] if u in r[v]) for u in range(len(adj))}))
    if kind == "aoe_total":
        return str(ve_vl(*a)[0])
    if kind == "aoe_slack":
        n, edges, (u, v) = a
        _, ve, vl = ve_vl(n, edges)
        w = next(e[2] for e in edges if e[:2] == (u, v))
        return str(vl(v) - w - ve(u))
    if kind == "floyd":
        n, edges, i, j = a
        return str(dijkstra(n, edges, i)[j])
    if kind == "bf":
        return str(simple_paths_min(*a))
    if kind == "mst":
        return str(mst_brute(*a))
    if kind == "lomuto":
        out, p = lomuto(a[0])
        assert all(x < out[p] for x in out[:p]) and all(x >= out[p] for x in out[p + 1:])
        return FMT(out)
    if kind == "radix_pass":
        arr, k = a
        for d in range(k):
            arr = sorted(arr, key=lambda x: x // 10 ** d % 10)     # sorted 是稳定的
        return FMT(arr)
    if kind == "lb":
        f, h = 1, 0
        for i in range(2, a[0] + 1):
            f *= i
        while 2 ** h < f:
            h += 1
        return str(h)
    if kind == "linear":
        keys, m, k = a
        return str(linear_probe(keys, m)[k])
    if kind == "trie_nodes":
        return str(len({w[:i] for w in a[0] for i in range(len(w) + 1)}))
    if kind == "trie_complete":
        words, pre = a
        return " ".join(sorted(w for w in set(words) if w.startswith(pre)))
    if kind == "bit_q":
        i, out = a[0], []
        while i:
            out.append(i)
            i &= i - 1
        return FMT(out)
    if kind == "bit_u":
        i, n, out = a[0], a[1], []
        while i <= n:
            out.append(i)
            i += i & -i
        return FMT(out)
    if kind == "bit_cover":
        i = a[0]
        return f"a[{i - (i & -i) + 1}] 到 a[{i}]"
    if kind == "lps_pal":
        return longest_pal(a[0])
    if kind == "slidemax":
        arr, k = a
        return FMT([max(arr[j:j + k]) for j in range(len(arr) - k + 1)])
    if kind == "slidemax_q":
        arr, k, i = a     # 队列里留下的是：仍在窗口内、且右边（到 i 为止）没有不小于它的数的下标
        return FMT([j for j in range(max(0, i - k + 1), i + 1) if all(arr[t] < arr[j] for t in range(j + 1, i + 1))])
    raise KeyError(kind)


class QuizTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = quiz_gen.build_all(with_checks=True)
        cls.disk = json.loads((HERE / "site" / "quiz.json").read_text(encoding="utf-8"))
        films = json.loads((HERE / "site" / "films.json").read_text(encoding="utf-8"))
        cls.ids = [f["id"] for w in films["weeks"] for f in w["films"]]

    def test_covers_every_film(self):
        self.assertEqual(sorted(self.disk), sorted(self.ids))

    def test_disk_is_up_to_date(self):
        self.assertEqual(self.disk, quiz_gen.build_all(), "quiz.json 过期：在 site/ 下重跑 python quiz_gen.py")

    def test_format(self):
        for film, qs in self.disk.items():
            self.assertEqual(len(qs), 3, film)
            for q in qs:
                self.assertEqual(set(q), {"q", "options", "answer", "explain"}, film)
                self.assertTrue(q["q"].strip() and q["explain"].strip(), film)
                self.assertEqual(len(q["options"]), 4, (film, q["q"]))
                self.assertEqual(len(set(q["options"])), 4, (film, q["options"]))
                self.assertTrue(all(isinstance(o, str) and o.strip() for o in q["options"]), film)
                self.assertIsInstance(q["answer"], int)
                self.assertIn(q["answer"], range(4), film)

    def test_answer_positions_vary(self):
        pos = [q["answer"] for qs in self.disk.values() for q in qs]
        for k in range(4):
            self.assertGreater(pos.count(k), len(pos) // 8, f"正确项落在 {k} 号的太少")

    def test_each_film_has_computed_question(self):
        for film, qs in self.full.items():
            self.assertTrue(any("_check" in q for q in qs), film)

    def test_computed_answers(self):
        for film, qs in self.full.items():
            for q in qs:
                if "_check" not in q:
                    continue
                with self.subTest(film=film, q=q["q"][:30]):
                    kind = q["_check"][0]
                    if kind == "topo_invalid":
                        _, n, edges = q["_check"]
                        bad = [i for i, o in enumerate(q["options"])
                               if not topo_ok(n, edges, [int(x) for x in o.split()])]
                        self.assertEqual(bad, [q["answer"]])
                    elif kind == "aoe_crit":
                        _, n, edges, (u, v) = q["_check"]
                        _, ve, vl = ve_vl(n, edges)
                        slack = {f"<{x},{y}>（{w} 天）": vl(y) - w - ve(x) for x, y, w in edges}
                        zero = [i for i, o in enumerate(q["options"]) if slack[o] == 0]
                        self.assertEqual(zero, [q["answer"]])
                    else:
                        self.assertEqual(q["options"][q["answer"]], expected(q["_check"]))


if __name__ == "__main__":
    unittest.main()
