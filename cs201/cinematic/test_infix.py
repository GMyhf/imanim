"""中缀转后缀片数字的独立对撞：讲义原版转换/求值（OJ24591、OJ24588 样例）、Python eval、随机表达式，以及旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_infix
"""
import json
import random
import unittest
from pathlib import Path

import infixdata as D


def rand_expr(depth=0):
    if depth > 2 or random.random() < 0.3:
        return str(random.randint(1, 30))
    op = random.choice("+-*/")
    left, right = rand_expr(depth + 1), rand_expr(depth + 1)
    s = f"{left}{op}{right}"
    return f"({s})" if random.random() < 0.4 else s


class InfixTest(unittest.TestCase):
    def test_oj_samples(self):
        # OJ24591 样例
        cases = {"7+8.3": "7 8.3 +", "3+4.5*(7+2)": "3 4.5 7 2 + * +",
                 "(3)*((3+4)*(2+3.5)/(4+5))": "3 3 4 + 2 3.5 + * 4 5 + / *"}
        for e, want in cases.items():
            self.assertEqual(D.infix_to_postfix(e), want)
            self.assertEqual(" ".join(D.convert_trace(e)[1]), want)
        # OJ24588 样例
        for e, want in {"5 3.4 +": "8.40", "5 3.4 + 6 /": "1.40", "5 3.4 + 6 * 3 +": "53.40"}.items():
            self.assertEqual(f"{D.evaluate_postfix(e):.2f}", want)

    def test_book(self):
        toks, out, ev = D.convert_trace(D.BOOK)
        self.assertEqual(" ".join(out), "23 34 45 * 5 6 + 7 + / +")       # 讲义给出的后缀式
        self.assertEqual(D.infix_to_postfix(D.BOOK), " ".join(out))
        res, ev2 = D.eval_trace(out)
        self.assertEqual(res, 108)
        self.assertEqual([e[5] for e in ev2 if e[0] == "op"], [1530, 11, 18, 85, 108])
        div = next(e for e in ev2 if e[0] == "op" and e[2] == "/")
        self.assertEqual((div[3], div[4]), (1530, 18))                      # 先弹出的 18 是右操作数
        self.assertEqual(max(len(s) for s in self.stack_depths(D.BOOK)), 4)  # 侧线最深 4 格（画面容量）

    def stack_depths(self, expr):
        toks, out, ev = D.convert_trace(expr)
        st, snaps = [], []
        for e in ev:
            if e[0] in ("lpar", "push"):
                st.append(e)
            elif e[0] in ("pop", "drop"):
                st.pop()
            snaps.append(list(st))
        return snaps

    def test_simple_and_assoc(self):
        self.assertEqual(" ".join(D.convert_trace("3+4*2")[1]), "3 4 2 * +")
        self.assertEqual(" ".join(D.convert_trace("3*4+2")[1]), "3 4 * 2 +")
        good = D.convert_trace(D.ASSOC)[1]
        bad = D.convert_trace(D.ASSOC, strict=True)[1]
        self.assertEqual(" ".join(good), "1 2 - 3 -")
        self.assertEqual(" ".join(bad), "1 2 3 - -")
        self.assertEqual(D.eval_trace(good)[0], -4)
        self.assertEqual(D.eval_trace(bad)[0], 2)
        self.assertEqual(eval(D.ASSOC), -4)

    def test_random_against_eval_and_book(self):
        random.seed(7)
        n = 0
        while n < 400:
            e = rand_expr()
            try:
                want = eval(e)
            except ZeroDivisionError:
                continue
            out = D.convert_trace(e)[1]
            self.assertEqual(" ".join(out), D.infix_to_postfix(e))
            try:
                got = D.eval_trace(out)[0]
            except ZeroDivisionError:
                continue
            self.assertAlmostEqual(got, want, places=6)
            self.assertAlmostEqual(D.evaluate_postfix(" ".join(out)), want, places=6)
            n += 1

    def test_narration(self):
        nar = "".join(b["narration"] for b in
                      json.loads((Path(__file__).parent / "infix.json").read_text(encoding="utf-8"))["beats"])
        for s in ("结果是三四二乘加", "结果是三四乘二加", "一二减三减，等于负四", "一二三减减", "等于二",
                  "一千五百三十", "得十一", "得十八", "得八十五", "得一百零八"):
            self.assertIn(s, nar)


if __name__ == "__main__":
    unittest.main()
