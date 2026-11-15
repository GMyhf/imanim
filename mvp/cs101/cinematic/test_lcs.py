"""LCS 与编辑距离片数字的独立对撞：讲义输出、暴力枚举子序列、BFS 求编辑距离、回溯结果、旁白数字。

用法（cwd = mvp/cs101/cinematic）：python -m unittest test_lcs
"""
from collections import deque
from itertools import combinations
import json
from pathlib import Path
import random
import unittest

import lcsdata as L


def is_subseq(a, b):
    it = iter(b)
    return all(ch in it for ch in a)


def brute_lcs(s, t):
    """枚举 s 的所有子序列（从长到短），第一个也是 t 子序列的就是答案。"""
    for k in range(len(s), -1, -1):
        for idx in combinations(range(len(s)), k):
            if is_subseq("".join(s[i] for i in idx), t):
                return k
    return 0


def brute_ed(s, t):
    """在字符串空间上 BFS：每步一次插入/删除/替换（字母表取两串字符）。"""
    alpha = sorted(set(s + t))
    limit = max(len(s), len(t)) + 1
    seen, q = {s: 0}, deque([s])
    while q:
        u = q.popleft()
        if u == t:
            return seen[u]
        nxt = set()
        for i in range(len(u) + 1):
            for c in alpha:
                if len(u) < limit:
                    nxt.add(u[:i] + c + u[i:])
                if i < len(u):
                    nxt.add(u[:i] + c + u[i + 1:])
            if i < len(u):
                nxt.add(u[:i] + u[i + 1:])
        for v in nxt:
            if v not in seen:
                seen[v] = seen[u] + 1
                q.append(v)


class LCSFacts(unittest.TestCase):
    def test_course_outputs(self):
        self.assertEqual((L.lcs("abcfbc", "abfcab"), L.lcs("programming", "contest")), (4, 2))
        self.assertEqual((L.edit_distance("horse", "ros"), L.edit_distance("intention", "execution")), (3, 5))

    def test_tables_match_course(self):
        dp, log = L.lcs_table()
        self.assertEqual(dp[-1][-1], L.lcs(L.LCS_S, L.LCS_T))
        self.assertEqual(len(log), len(L.LCS_S) * len(L.LCS_T))
        for i, j, src, v in log:
            self.assertEqual(src == "diag", L.LCS_S[i - 1] == L.LCS_T[j - 1])
        d2, log2 = L.ed_table()
        self.assertEqual(d2[-1][-1], L.edit_distance(L.ED_S, L.ED_T))
        self.assertEqual([d2[i][0] for i in range(len(L.ED_S) + 1)], list(range(len(L.ED_S) + 1)))
        self.assertEqual(d2[0], list(range(len(L.ED_T) + 1)))

    def test_random_against_brute(self):
        rng = random.Random(11)
        for _ in range(300):
            s = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
            t = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
            self.assertEqual(L.lcs(s, t), brute_lcs(s, t))
        for _ in range(150):
            s = "".join(rng.choice("ab") for _ in range(rng.randint(0, 4)))
            t = "".join(rng.choice("ab") for _ in range(rng.randint(0, 4)))
            self.assertEqual(L.edit_distance(s, t), brute_ed(s, t))

    def test_backtracks(self):
        path, picks, sub = L.lcs_back()
        self.assertEqual(len(sub), 4)
        self.assertTrue(is_subseq(sub, L.LCS_S) and is_subseq(sub, L.LCS_T))
        self.assertEqual(path[0], (6, 6))
        self.assertEqual(path[-1][0] * path[-1][1], 0)
        rng = random.Random(5)
        for _ in range(200):
            s = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
            t = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
            _, _, sub = L.lcs_back(s, t)
            self.assertEqual(len(sub), L.lcs(s, t))
            self.assertTrue(is_subseq(sub, s) and is_subseq(sub, t))
            _, ops, steps = L.ed_back(s, t)
            self.assertEqual((len(ops), steps[-1]), (L.edit_distance(s, t), t))
        _, ops, steps = L.ed_back()
        self.assertEqual(steps, ["horse", "rorse", "rose", "ros"])          # 旁白：h 改 r，删 r，删 e
        self.assertEqual([(k, a) for k, _, a, _ in ops], [("rep", "h"), ("del", "r"), ("del", "e")])

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("lcs.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("右下角就是答案：四", beats["fill"])
        self.assertIn("长度为四", beats["back"])
        self.assertIn("右下角是三", beats["edfill"])
        self.assertIn("三步具体的操作", beats["align"])
        for s in ("先把 h 改成 r", "再删掉一个 r", "最后删掉 e"):
            self.assertIn(s, beats["align"])
        self.assertIn("要五步", beats["same"])


if __name__ == "__main__":
    unittest.main()
