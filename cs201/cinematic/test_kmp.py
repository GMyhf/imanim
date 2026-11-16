"""KMP 片数字的独立对撞：str.find / 暴力边界 / 讲义手算表 / 旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_kmp
"""
import itertools
import json
import random
import re
import unittest
from pathlib import Path

import kmpdata as K


def brute_lps(p):
    return [max([k for k in range(i + 1) if p[:k] == p[i + 1 - k:i + 1]]) for i in range(len(p))]


def all_find(t, p):
    out, s = [], t.find(p)
    while s != -1:
        out.append(s)
        s = t.find(p, s + 1)
    return out


def brute_period(s):
    return next(p for p in range(1, len(s) + 1) if all(s[i] == s[i + p] for i in range(len(s) - p)))


class KMPTest(unittest.TestCase):
    def test_lecture_outputs(self):
        # spring W03 讲义：pos matched： [4, 13]
        self.assertEqual(K.kmp_search(K.LONG_T, K.LONG_P), [4, 13])
        # fall 3.2 节：kmp_search("abababd", "ababd") = 2；朴素 11 次、KMP 8 次比较（3.3 节逐步追踪表）
        self.assertEqual(K.kmp_search(K.SHORT_T, K.SHORT_P), [2])
        self.assertEqual(K.naive_search(K.SHORT_T, K.SHORT_P), 2)
        self.assertEqual(len(K.SHORT_NAIVE), 11)
        self.assertEqual(K.cmp_count(K.SHORT_KMP), 8)
        # fall 3.2 节：lps 表 0 0 0 0 1 1 2 3 1 2（模式 abcdaabcab）
        self.assertEqual(K.compute_lps("abcdaabcab"), [0, 0, 0, 0, 1, 1, 2, 3, 1, 2])
        # fall 3.4 节四例
        for s, p, r in [("abcabcabc", 3, 3), ("ababa", 2, 1), ("abcd", 4, 1), ("aaaa", 1, 4)]:
            self.assertEqual((K.minimal_period(s), K.repetition_count(s)), (p, r))

    def test_lps_brute_and_trace(self):
        rng = random.Random(7)
        cases = ["".join(c) for n in range(1, 9) for c in itertools.product("ab", repeat=n)]
        cases += ["".join(rng.choice("abc") for _ in range(rng.randint(1, 30))) for _ in range(300)]
        for p in cases:
            lps = K.compute_lps(p)
            self.assertEqual(lps, brute_lps(p), p)
            self.assertEqual(K.lps_trace(p)[1], lps, p)
            self.assertEqual(K.minimal_period(p), brute_period(p), p)

    def test_search_against_find(self):
        rng = random.Random(11)
        for _ in range(1500):
            t = "".join(rng.choice("ab") for _ in range(rng.randint(0, 40)))
            p = "".join(rng.choice("ab") for _ in range(rng.randint(1, 6)))
            want = all_find(t, p)
            self.assertEqual(K.kmp_search(t, p), want)
            ev = K.kmp_trace(t, p)
            self.assertEqual([e[1] for e in ev if e[0] == "match"], want)
            self.assertLessEqual(K.cmp_count(ev), 2 * len(t))
            # 目标指针只增不减
            ii = [e[1] for e in ev if e[0] == "cmp"]
            self.assertEqual(ii, sorted(ii))
            self.assertEqual(K.naive_search(t, p), want[0] if want else None)
            self.assertEqual(K.naive_all_count(t, p)[1], want)

    def test_scene_numbers(self):
        self.assertEqual(K.compute_lps(K.SHORT_P), [0, 0, 1, 2, 0])
        self.assertEqual(K.LONG_LPS, [0, 0, 1, 2, 0, 1, 2, 3, 4])
        self.assertEqual(K.borders("abab")[2], [2])
        self.assertEqual(K.cmp_count(K.LONG_KMP), 33)
        self.assertEqual(K.LONG_NAIVE_CNT, 59)
        self.assertEqual(K.WORST_NAIVE_CNT, K.WORST_M * (K.WORST_N - K.WORST_M + 1))   # 讲义：|P|(|T|-|P|+1)
        self.assertEqual((K.WORST_NAIVE_CNT, K.WORST_KMP_CNT), (80, 36))
        self.assertEqual(len(K.LONG_T), 27)
        self.assertEqual(len(K.LONG_P), 9)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in
                 json.loads((Path(__file__).parent / "kmp.json").read_text(encoding="utf-8"))["beats"]}
        cn = {2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 8: "八", 9: "九", 11: "十一", 13: "十三",
              20: "二十", 27: "二十七", 33: "三十三", 36: "三十六", 59: "五十九", 80: "八十"}
        self.assertIn(f"比较了{cn[len(K.SHORT_NAIVE)]}次", beats["naive"])
        self.assertIn(f"起点是{cn[K.SHORT_NAIVE_RET]}号", beats["naive"])
        self.assertIn(f"长度为{cn[K.borders('abab')[2][-1]]}", beats["waste"])
        self.assertIn(f"最后一格是{cn[K.LONG_LPS[-1]]}", beats["build"])
        self.assertIn(f"只比较了{cn[K.cmp_count(K.SHORT_KMP)]}次", beats["search"])
        a = beats["all"]
        self.assertIn(f"目标{cn[len(K.LONG_T)]}个字符，模式{cn[len(K.LONG_P)]}个字符", a)
        self.assertIn(f"找到{cn[K.LONG_MATCHES[0]]}号和{cn[K.LONG_MATCHES[1]]}号", a)
        self.assertIn(f"比较{cn[K.cmp_count(K.LONG_KMP)]}次", a)
        self.assertIn(f"要比{cn[K.LONG_NAIVE_CNT]}次", a)
        li = beats["linear"]
        self.assertIn(f"在{cn[K.WORST_N]}个 a 里找{cn[K.WORST_M - 1]}个 a", li)
        self.assertIn(f"朴素要比{cn[K.WORST_NAIVE_CNT]}次，KMP 只要{cn[K.WORST_KMP_CNT]}次", li)
        pe = beats["period"]
        s1, s2 = K.PERIOD_CASES
        n1, b1 = len(s1), K.compute_lps(s1)[-1]
        self.assertIn(f"长{cn[n1]}，最后一格是{cn[b1]}", pe)
        self.assertIn(f"{cn[n1]}减{cn[b1]}，也就是{cn[n1 - b1]}位", pe)
        self.assertEqual(K.repetition_count(s1), 3)
        n2, b2 = len(s2), K.compute_lps(s2)[-1]
        self.assertIn(f"{cn[n2]}减{cn[b2]}等于{cn[n2 - b2]}", pe)
        self.assertNotEqual(n2 % (n2 - b2), 0)
        # 旁白里不出现阿拉伯数字（让 TTS 一律按中文读）
        for bid, text in beats.items():
            self.assertIsNone(re.search(r"\d", text), bid)


if __name__ == "__main__":
    unittest.main()
