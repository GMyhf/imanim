"""11 月月考讲评片数字的独立对撞：题面样例、暴力参照随机对拍、插桩回放、旁白数字。

独立实现都不调用 novdata 的算法：回文用字符串翻转、选座逐人从左找、箭头逐格模拟 nm+1 步、
牌堆按题意正着模拟所有排列、渗透每步 BFS、括号每问用栈现扫。
用法（cwd = cs101/cinematic）：python -m unittest test_nov
"""
from collections import deque
from itertools import permutations
import json
from pathlib import Path
import random
import unittest

import novdata as D

HERE = Path(__file__).resolve().parent


def pals_brute(n):
    return [i for i in range(1, n + 1) if str(i) == str(i)[::-1] and bin(i)[2:] == bin(i)[2:][::-1]]


def seats_brute(s, m):
    s, n, sat = list(s), len(s), 0
    for _ in range(m):                           # 每位同学都从头找
        for i in range(n):
            if s[i] == '0' and (i == 0 or s[i - 1] == '0') and (i == n - 1 or s[i + 1] == '0'):
                s[i] = '1'
                sat += 1
                break
    return sat, "".join(s)


def arrows_brute(g):
    n, m = len(g), len(g[0])
    cnt = 0
    for si in range(n):
        for sj in range(m):
            i, j = si, sj
            for _ in range(n * m + 1):           # 走 nm+1 步还在场内，必然绕圈
                if not (0 <= i < n and 0 <= j < m):
                    break
                di, dj = D.MOVE[g[i][j]]
                i, j = i + di, j + dj
            cnt += not (0 <= i < n and 0 <= j < m)
    return cnt


def reveal(order):
    dq, out = deque(order), []
    while dq:
        dq.rotate(-1)
        out.append(dq.popleft())
    return out


def perc_brute(n, m, ops):
    opened = set()
    for k, (r, c) in enumerate(ops):
        opened.add((r - 1, c - 1))
        seen = {(0, j) for j in range(m) if (0, j) in opened}
        q = deque(seen)
        while q:
            i, j = q.popleft()
            if i == n - 1:
                return k + 1
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if (a, b) in opened and (a, b) not in seen:
                    seen.add((a, b))
                    q.append((a, b))
    return -1


def legal(t):
    d = 0
    for ch in t:
        d += 1 if ch == '(' else -1
        if d < 0:
            return False
    return d == 0


class NovFacts(unittest.TestCase):
    def test_samples(self):
        for k, cases in D.SAMPLES.items():
            for inp, out in cases:
                self.assertEqual(D.run_io(D.SOLVERS[k], inp), out, (k, inp))

    def test_t1(self):
        self.assertEqual(D.PALS_100, pals_brute(100))
        self.assertEqual(D.PALS_100, [1, 3, 5, 7, 9, 33, 99])
        n, cnt, best = D.T1_BIG
        big = D.double_pals(n)
        self.assertEqual((len(big), big[-1]), (cnt, best))
        self.assertEqual(D.run_io(D.solve_t1, f"{n}\n"), f"{cnt} {best}")
        self.assertTrue(all(x % 2 == 1 for x in pals_brute(5000)))          # 偶数不可能是二进制回文

    def test_t2(self):
        s, m = D.SEATS
        steps, sat, final = D.seats_trace(s, m)
        self.assertEqual((sat, final), seats_brute(s, m))
        self.assertEqual((sat, final), (3, "1010101010"))                  # 第 4 位没座位
        rnd = random.Random(31530)
        for _ in range(500):
            n = rnd.randint(1, 12)
            s = "".join(rnd.choice("0001") for _ in range(n))
            m = rnd.randint(1, 8)
            sat, fin = seats_brute(s, m)
            self.assertEqual(D.run_io(D.solve_t2, f"{n} {m}\n{s}\n"), f"{sat}\n{fin}")

    def test_t3(self):
        walks, st = D.arrows_trace(D.ARROWS)
        self.assertEqual(st.count(2), arrows_brute(D.ARROWS))
        self.assertEqual(st.count(2), 5)
        self.assertEqual([w["end"] for w in walks], ["out", "out", "out", "cycle", "join", "join"])
        self.assertEqual(sum(len(w["path"]) for w in walks), 9)            # 每格只走一次
        rnd = random.Random(31531)
        for _ in range(300):
            n, m = rnd.randint(1, 5), rnd.randint(1, 5)
            g = ["".join(rnd.choice("UDLR") for _ in range(m)) for _ in range(n)]
            self.assertEqual(D.run_io(D.solve_t3, f"{n} {m}\n" + "\n".join(g) + "\n"), str(arrows_brute(g)))
            self.assertEqual(D.arrows_trace(g)[1].count(2), arrows_brute(g))

    def test_t3_long_row(self):
        """讲义：一行全是 R 的路线可长达 2×10⁵，循环写法不受递归深度限制。"""
        m = 2 * 10 ** 5
        self.assertEqual(D.run_io(D.solve_t3, f"1 {m}\n{'R' * m}\n"), str(m))

    def test_t4(self):
        steps = D.cards_reverse_trace(4)
        self.assertEqual([s["moved"] for s in steps], [[4], [4, 3], [3, 2, 4], [4, 1, 3, 2]])   # 讲义的验算
        for n in range(1, 8):
            want = [p for p in permutations(range(1, n + 1)) if reveal(p) == list(range(1, n + 1))]
            self.assertEqual(len(want), 1)
            self.assertEqual(D.run_io(D.solve_t4, f"{n}\n"), " ".join(map(str, want[0])))
            self.assertEqual(D.cards_forward(list(want[0])), list(range(1, n + 1)))

    def test_t5(self):
        n, m, ops = D.PERC
        self.assertEqual(D.perc_answer(n, m, ops), perc_brute(n, m, ops))
        self.assertEqual(D.perc_answer(n, m, ops), 6)
        steps = D.perc_trace(n, m, ops)
        self.assertEqual([s["done"] for s in steps], [False] * 5 + [True])
        self.assertTrue(steps[0]["top"] and steps[1]["bot"])
        self.assertEqual((D.perc_elif_bug(1, 3, [(1, 2)]), D.perc_answer(1, 3, [(1, 2)])), (-1, 1))
        rnd = random.Random(31533)
        for _ in range(300):
            n, m = rnd.randint(1, 5), rnd.randint(1, 5)
            cells = [(i, j) for i in range(1, n + 1) for j in range(1, m + 1)]
            rnd.shuffle(cells)
            ops = cells[:rnd.randint(1, len(cells))]
            inp = f"{n} {m} {len(ops)}\n" + "".join(f"{r} {c}\n" for r, c in ops)
            self.assertEqual(D.run_io(D.solve_t5, inp), str(perc_brute(n, m, ops)))

    def test_t6(self):
        s = D.BRACKETS
        pre = D.prefix(s)
        nxt, _ = D.next_lower(pre)
        self.assertEqual(pre, [0, 1, 2, 1, 2, 1, 0])
        self.assertEqual(nxt, [7, 6, 3, 6, 5, 6, 7])
        for l, r in D.QUERIES:
            self.assertEqual(D.judge(s, l, r)[0], legal(s[l - 1:r]))
        self.assertEqual([D.judge(s, l, r)[:2] for l, r in D.SHOWN], [(True, True), (False, False), (False, True)])
        rnd = random.Random(31534)
        for _ in range(300):
            n = rnd.randint(1, 12)
            t = "".join(rnd.choice("()") for _ in range(n))
            qs = [(l, r) for l in range(1, n + 1) for r in range(l, n + 1)]
            inp = f"{t}\n{len(qs)}\n" + "".join(f"{l} {r}\n" for l, r in qs)
            want = "\n".join("YES" if legal(t[l - 1:r]) else "NO" for l, r in qs)
            self.assertEqual(D.run_io(D.solve_t6, inp), want)
        self.assertEqual(D.NAIVE_T6, 4 * 10 ** 10)

    def test_narration_numbers(self):
        txt = "".join(b["narration"] for b in json.loads((HERE / "nov.json").read_text(encoding="utf-8"))["beats"])
        n, cnt, _ = D.T1_BIG
        self.assertIn("一百万以内有十九个", txt)
        self.assertEqual((n, cnt), (10 ** 6, 19))
        self.assertIn("第四位同学没有座位", txt)
        self.assertEqual(D.SEATS[1], 4)
        self.assertEqual(D.seats_trace(*D.SEATS)[1], 3)
        self.assertIn("样例答案是五", txt)
        self.assertIn("得到四一三二", txt)
        self.assertIn("第六步渗透", txt)
        self.assertIn("四百亿步", txt)
        self.assertIn("第一次跌破在六", txt)
        self.assertEqual(D.judge(D.BRACKETS, 2, 5)[2], 6)
        self.assertIn("可三就跌破了", txt)
        self.assertEqual(D.judge(D.BRACKETS, 3, 4)[2], 3)
        self.assertIn("两端都是一", txt)
        pre = D.prefix(D.BRACKETS)
        self.assertEqual((pre[1], pre[5]), (1, 1))


if __name__ == "__main__":
    unittest.main()
