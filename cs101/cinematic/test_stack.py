"""栈片数字的独立对撞：讲义输出、反复消去配对括号的暴力判定、Python eval、按列求水量的暴力法、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_stack
"""
import itertools
import json
from pathlib import Path
import random
import unittest

import stackdata as S


def brute_valid(s):
    prev = None
    while prev != s:
        prev = s
        for p in ("()", "[]", "{}"):
            s = s.replace(p, "")
    return s == ""


def brute_trap(h):
    return sum(max(0, min(max(h[:i + 1]), max(h[i:])) - h[i]) for i in range(len(h)))


class StackFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual([S.is_valid(x) for x in ("([]{})", "(]", "(")], [True, False, False])
        self.assertEqual(S.eval_postfix("1 2 + 3 *".split()), 9.0)
        self.assertEqual(S.eval_postfix("10 3 - 2 -".split()), 5.0)
        self.assertEqual(S.next_greater([2, 1, 2, 4, 3]), [3, 2, 3, -1, -1])
        self.assertEqual(S.trap(S.RAIN), 6)

    def test_valid_brute(self):
        for n in range(0, 7):
            for t in itertools.product("()[]{}", repeat=n):
                s = "".join(t)
                self.assertEqual(S.is_valid(s), brute_valid(s), s)

    def test_three_failures(self):
        """片中三种失败：不配对、遇右括号时栈已空、结束时栈有剩余。"""
        _, ev = S.is_valid_trace("(]")
        self.assertEqual(ev[-1], ("pop", 1, "(", False))
        _, ev = S.is_valid_trace(")")
        self.assertEqual(ev[-1], ("empty", 0))
        ok, ev = S.is_valid_trace("((")
        self.assertEqual((ok, ev[-1]), (False, ("end", 2)))

    def test_postfix_eval(self):
        rng = random.Random(3)
        for _ in range(300):
            nums = [str(rng.randint(1, 9)) for _ in range(rng.randint(1, 5))]
            toks, st = [nums[0]], [nums[0]]
            for x in nums[1:]:
                op = rng.choice("+-*")
                toks += [x, op]
                st = [f"({st[0]}{op}{x})"]
            self.assertAlmostEqual(S.eval_postfix(toks), eval(st[0]))
        _, ev = S.eval_postfix_trace("1 2 + 3 *".split())
        self.assertEqual([e for e in ev if e[0] == "op"], [("op", 2, "+", 1.0, 2.0, 3.0), ("op", 4, "*", 3.0, 3.0, 9.0)])

    def test_trap_brute(self):
        rng = random.Random(5)
        for _ in range(500):
            h = [rng.randint(0, 5) for _ in range(rng.randint(0, 14))]
            self.assertEqual(S.trap(h), brute_trap(h))
        w, ev = S.trap_trace()
        pushes = sum(1 for e in ev if e[0] == "push")
        pops = sum(1 for e in ev if e[0] in ("pop", "noleft"))
        self.assertEqual(pushes, len(S.RAIN))
        self.assertLessEqual(pops, len(S.RAIN))                          # 每个下标最多出栈一次
        self.assertEqual([e[-1] for e in ev if e[0] == "water"][-1], 6)

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("stack.json").read_text(encoding="utf-8"))["beats"])
        for s in ("最后栈顶就是结果，九", "结果是五", "一共能接六格雨水", "一、二、加、三、乘", "两 n 次"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
