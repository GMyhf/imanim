"""括号区间审计精讲片数字的独立对撞：题面样例、按定义的暴力随机对拍、片中画出的前缀和 / nxt / 栈 / 判定、旁白数字。

独立实现不调用 novdata / novbrkdata 的算法：合法性按定义用栈匹配现扫，nxt 逐位往右找第一个更低点，
单调栈的每一步用「栈里 = 还没找到更低点的位置」这一定义反推。
用法（cwd = cs101/cinematic）：python -m unittest test_novbrk
"""
import inspect
import json
from pathlib import Path
import random
import re
import unittest

import novbrkdata as D
import novdata as N

HERE = Path(__file__).resolve().parent
NARR = {b["id"]: b["narration"] for b in json.loads((HERE / "novbrk.json").read_text(encoding="utf-8"))["beats"]}
ALL = "".join(NARR.values())


def valid(sub):
    """按定义：栈匹配，右括号必须有左括号可配，最后栈空。"""
    st = []
    for ch in sub:
        if ch == "(":
            st.append(ch)
        elif st:
            st.pop()
        else:
            return False
    return not st


def brute(s, qs):
    return ["YES" if valid(s[l - 1:r]) else "NO" for l, r in qs]


def heights(s):
    h = [0]
    for ch in s:
        h.append(h[-1] + (1 if ch == "(" else -1))
    return h


def next_lower_brute(h):
    n = len(h) - 1
    return [next((j for j in range(i + 1, n + 1) if h[j] < h[i]), n + 1) for i in range(n + 1)]


def only_count(s, qs):
    return ["YES" if s[l - 1:r].count("(") == s[l - 1:r].count(")") else "NO" for l, r in qs]


def first_not_higher(h):
    n = len(h) - 1
    return [next((j for j in range(i + 1, n + 1) if h[j] <= h[i]), n + 1) for i in range(n + 1)]


def rand_case(rng, n, q):
    s = "".join(rng.choice("()") for _ in range(n))
    qs = []
    for _ in range(q):
        l = rng.randint(1, n)
        qs.append((l, rng.randint(l, n)))
    return s, qs


class NovBrkTest(unittest.TestCase):
    def test_samples(self):
        for inp, out in N.SAMPLES["t6"]:
            lines = inp.strip().split("\n")
            s, qs = lines[0], [tuple(map(int, x.split())) for x in lines[2:]]
            self.assertEqual("\n".join(brute(s, qs)), out)
            self.assertEqual(N.run_io(N.solve_t6, inp), out)
        self.assertEqual(D.S, "())(()")
        self.assertEqual(D.QUERIES, [(1, 2), (2, 5), (1, 6), (3, 6)])
        self.assertEqual(D.lecture_answers(D.S, D.QUERIES), ["YES", "NO", "NO", "NO"])

    def test_random_vs_brute(self):
        rng = random.Random(31534)
        for _ in range(400):
            s, qs = rand_case(rng, rng.randint(1, 14), rng.randint(1, 12))
            want = brute(s, qs)
            self.assertEqual(D.lecture_answers(s, qs), want)
            self.assertEqual([("YES" if D.judge(s, l, r)["ok"] else "NO") for l, r in qs], want)
            self.assertEqual(D.prefix(s), heights(s))
            self.assertEqual(D.next_lower(heights(s))[0], next_lower_brute(heights(s)))
            self.assertEqual(D.wrong_count_only(s, qs), only_count(s, qs))
            self.assertEqual(D.next_lower_ge(heights(s)), first_not_higher(heights(s)))

    def test_lecture_code_text(self):
        """片中展示的代码 = 讲义 Python 参考代码（novdata.solve_t6 的函数体）。"""
        body = inspect.getsource(N.solve_t6).split("\n")[1:]
        body = [ln[4:] if ln.startswith("    ") else ln for ln in body]
        self.assertEqual("\n".join(body).strip(), D.CODE.strip())
        lines = D.CODE_LINES
        self.assertIn("pre[i + 1]", lines[8])
        self.assertIn("while stk and pre[stk[-1]] > pre[j]", lines[14])
        self.assertIn("sys.stdin.read()", lines[2])
        self.assertIn("join(out)", lines[24])
        for seg, (a, b) in D.SEGMENTS.items():
            self.assertTrue(lines[a].strip() and lines[b].strip(), seg)

    def test_mountain_and_stack(self):
        h = heights(D.S)
        self.assertEqual(h, [0, 1, 0, -1, 0, 1, 0])
        self.assertEqual(D.prefix(D.S), h)
        nxt = next_lower_brute(h)
        self.assertEqual(nxt, [3, 2, 3, 7, 7, 6, 7])
        _, ev = D.next_lower(h)
        n = len(D.S)
        for j, popped, stk in ev:
            # 栈 = 前 j 个位置里还没出现更低点的，按位置排；弹出的 = 恰好在 j 找到更低点的
            self.assertEqual(stk, [i for i in range(j + 1) if nxt[i] > j])
            self.assertEqual(sorted(popped), [i for i in range(j) if nxt[i] == j])
            self.assertEqual(popped, sorted(popped, reverse=True))
            self.assertTrue(all(h[a] <= h[b] for a, b in zip(stk, stk[1:])))       # 底到顶不降
        pops = {j: p for j, p, _ in ev if p}
        self.assertEqual(pops, {2: [1], 3: [2, 0], 6: [5]})
        self.assertEqual(ev[-1][2], [3, 4, 6])
        self.assertEqual(n + 1, 7)

    def test_counterexamples_and_queries(self):
        h = heights(D.S)
        nxt = next_lower_brute(h)
        l, r = D.COUNTER[0]                                          # 四到五：不跌破但两端不等
        self.assertEqual(D.S[l - 1:r], "((")
        self.assertNotEqual(h[r], h[l - 1])
        self.assertGreaterEqual(min(h[l - 1:r + 1]), h[l - 1])
        self.assertEqual((h[l - 1], h[r]), (-1, 1))
        l, r = D.COUNTER[1]                                          # 二到五：两端同高但跌破
        self.assertEqual(D.S[l - 1:r], "))((")
        self.assertEqual(h[r], h[l - 1])
        self.assertEqual(next(k for k in range(l, r + 1) if h[k] < h[l - 1]), 2)
        self.assertEqual(h[2], 0)
        for (l, r), want in zip(D.QUERIES, ["YES", "NO", "NO", "NO"]):
            j = D.judge(D.S, l, r)
            self.assertEqual(j["nxt"], nxt[l - 1])
            self.assertEqual((j["a"], j["b"]), (h[l - 1], h[r]))
            self.assertTrue(j["c1"])                                  # 四问两端都同高
            self.assertEqual("YES" if valid(D.S[l - 1:r]) else "NO", want)
        self.assertEqual([D.judge(D.S, l, r)["nxt"] for l, r in D.QUERIES], [3, 2, 3, 3])
        self.assertEqual(D.running(D.SCAN_OK), [1, 2, 1, 0, 1, 0])
        self.assertTrue(valid(D.SCAN_OK))
        self.assertEqual(D.running(D.SCAN_BAD), [1, 0, -1, 0])
        self.assertFalse(valid(D.SCAN_BAD))

    def test_wrong_versions(self):
        self.assertEqual(only_count(D.S, D.QUERIES), ["YES"] * 4)
        self.assertEqual(D.wrong_count_only(D.S, D.QUERIES), ["YES"] * 4)
        h = heights(D.S)
        ge = first_not_higher(h)
        self.assertEqual(ge, [2, 2, 3, 7, 6, 6, 7])
        self.assertEqual(D.next_lower_ge(h), ge)
        self.assertEqual(D.wrong_ge(D.S, D.QUERIES), ["NO"] * 4)
        self.assertEqual([i for i in range(len(h)) if ge[i] != next_lower_brute(h)[i]], [0, 4])

    def test_narration_numbers(self):
        self.assertEqual(D.N_MAX, 200000)
        self.assertEqual(D.NAIVE, 200000 * 200000)
        self.assertEqual(D.NAIVE, 400 * 10 ** 8)
        for frag in ("二十万次询问", "最坏二十万步", "四百亿步", "高度依次是零、一、零、负一、零、一、零",
                     "四到五是两个左括号", "二到五两端同高", "到三，跌到负一，二和零都被弹出，答案都是三",
                     "到六，弹出五", "填七", "一到二：两端都是零，next 是三，大于二，合法", "二到五：两端都是一，可 next 是二",
                     "在三就跌破了", "三到六：同样在三跌破", "一个 YES，三个 NO", "会输出四个 YES", "四问全是 NO",
                     "零、一先入栈", "到二，弹出一"):
            self.assertIn(frag, ALL)
        n_cn = len(re.findall(r"[一-鿿]", ALL))
        self.assertTrue(780 <= n_cn <= 980, n_cn)
        self.assertEqual(list(NARR)[0], "title")
        self.assertEqual(list(NARR)[-1], "recap")


if __name__ == "__main__":
    unittest.main()
