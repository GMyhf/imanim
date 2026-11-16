"""Manacher 片数字的独立对撞：讲义两份代码、暴力枚举、计数包装的中心扩展、摊还上界、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_manacher
"""
import json
import random
import unittest
from pathlib import Path

import manacherdata as M

NARR = "".join(b["narration"] for b in json.loads((Path(__file__).parent / "manacher.json").read_text(encoding="utf-8"))["beats"])


def brute_len(s):
    return max((j - i for i in range(len(s)) for j in range(i + 1, len(s) + 1) if s[i:j] == s[i:j][::-1]), default=0)


class CountStr(str):
    """计数包装：讲义中心扩展每比一次读两个下标。"""
    reads = 0

    def __getitem__(self, k):
        CountStr.reads += 1
        return str.__getitem__(self, k)


def is_pal(s):
    return s == s[::-1]


class ManacherTest(unittest.TestCase):
    def test_lecture_examples(self):
        a = M.SolutionManacher().longestPalindrome("babad")
        b = M.SolutionExpand().longestPalindrome("babad")
        self.assertIn(a, ("bab", "aba"))
        self.assertIn(b, ("bab", "aba"))
        self.assertEqual(M.SolutionManacher().longestPalindrome("cbbd"), "bb")

    def test_random_vs_brute(self):
        rng = random.Random(5)
        for _ in range(500):
            s = "".join(rng.choice("ab" if rng.random() < 0.5 else "abc") for _ in range(rng.randrange(1, 25)))
            want = brute_len(s)
            for got in (M.SolutionManacher().longestPalindrome(s), M.SolutionExpand().longestPalindrome(s),
                        M.manacher_trace(s)["answer"]):
                self.assertEqual(len(got), want)
                self.assertTrue(is_pal(got) and got in s)
            tr = M.manacher_trace(s)
            t = tr["t"]
            for i, p in enumerate(tr["p"]):                 # p 是真实的最大半径（暴力验证）
                r = 1
                while i - r >= 0 and i + r < len(t) and t[i - r] == t[i + r]:
                    r += 1
                self.assertEqual(p, r)

    def test_expand_count(self):
        for n in M.GROW:
            CountStr.reads = 0
            M.SolutionExpand().longestPalindrome(CountStr("a" * n))
            self.assertEqual(M.expand_count("a" * n), CountStr.reads // 2)

    def test_amortized(self):
        """失败 ≤ 每个下标一次；边界复核 ≤ 每个下标一次；越过 R 的成功比较 ≤ R 的总推进。"""
        rng = random.Random(9)
        cases = ["a" * 80, M.DEMO] + ["".join(rng.choice("ab") for _ in range(rng.randrange(1, 60))) for _ in range(300)]
        for s in cases:
            tr = M.manacher_trace(s)
            n = len(tr["t"])
            beyond = 0
            for st in tr["steps"]:
                self.assertLessEqual(sum(1 for c in st["cmps"] if not c[2]), 1)
                if st["case"] == "in":
                    self.assertEqual(len(st["cmps"]), 1)         # 第一种情况：只比一次且失败
                    self.assertFalse(st["cmps"][0][2])
                for k, (_, r, eq) in enumerate(st["cmps"]):
                    if eq and r > st["R"]:
                        beyond += 1
                    elif eq:
                        self.assertEqual((k, r, st["case"]), (0, st["R"], "edge"))   # 唯一的例外：边界上的复核
            self.assertLessEqual(beyond, tr["steps"][-1]["R2"])
            self.assertLessEqual(tr["cmps"], 3 * n)

    def test_demo_numbers(self):
        tr = M.manacher_trace(M.DEMO)
        st = tr["steps"]
        self.assertEqual(len(tr["t"]), 21)
        self.assertEqual((st[7]["case"], st[7]["p"], st[7]["R2"], st[7]["C2"]), ("out", 8, 14, 7))
        self.assertEqual((st[9]["case"], st[9]["mirror"], tr["p"][5], st[9]["p"], len(st[9]["cmps"])), ("in", 5, 2, 2, 1))
        self.assertEqual((st[11]["case"], st[11]["mirror"], tr["p"][3], st[11]["R"] - 11, st[11]["init"]),
                         ("edge", 3, 4, 3, 3))
        self.assertEqual((st[11]["p"], st[11]["R"], st[11]["R2"]), (10, 14, 20))
        self.assertEqual(tr["answer"], "bacabacab")
        self.assertEqual(max(tr["p"]), 10)
        self.assertEqual(tr["p"].index(10), 11)
        ab = M.manacher_trace(M.ABBA)
        self.assertEqual(len(ab["t"]), 9)
        self.assertEqual((ab["t"][4], ab["p"][4] - 1), ("#", 4))
        self.assertEqual(M.grow_table()[0][:2], (10, 55))
        self.assertEqual(M.grow_table()[-1], (80, 3240, 316))
        self.assertEqual(2 * 10 - 1, 19)

    def test_narration_numbers(self):
        for w in ("五十五次", "三千二百四十次", "三百一十六次", "二十一格", "下标七", "下标十四", "下标九", "下标五",
                  "下标十一", "下标三", "半径四", "只剩三格", "半径十", "从十四推到二十", "长度九", "九个字符"):
            self.assertIn(w, NARR)


if __name__ == "__main__":
    unittest.main()
