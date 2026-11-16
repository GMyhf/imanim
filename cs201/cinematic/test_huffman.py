"""Huffman 片数字的独立对撞：讲义码表、195/228、14 位电文、图 5.18 三个 WPL、讲义 OJ04080 解法、
穷举所有满二叉树形求最小 WPL、前缀性与随机译码往返、旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_huffman
"""
import itertools
import json
import random
import unittest
from functools import lru_cache
from pathlib import Path

import huffmandata as D

HERE = Path(__file__).resolve().parent


def brute_min_wpl(ws):
    """穷举：把多重集任意二分成左右子树，WPL(T) = 总权 + WPL(左) + WPL(右)。"""
    @lru_cache(maxsize=None)
    def go(t):
        if len(t) == 1:
            return 0
        best = None
        n = len(t)
        for mask in range(1, 2 ** n - 1):
            if not mask & 1:
                continue
            l = tuple(sorted(t[i] for i in range(n) if mask >> i & 1))
            r = tuple(sorted(t[i] for i in range(n) if not mask >> i & 1))
            v = sum(t) + go(l) + go(r)
            best = v if best is None else min(best, v)
        return best
    return go(tuple(sorted(ws)))


class HuffmanTest(unittest.TestCase):
    def test_lecture_code_table(self):
        root, _, merges = D.fig_tree()
        self.assertEqual(D.codes(root), {"a": "00", "b": "11110", "c": "1110", "d": "11111", "e": "10", "f": "110",
                                         "g": "01"})
        self.assertEqual([p.weight for _, _, p in merges], [7, 13, 23, 33, 43, 76])
        self.assertEqual([(l.weight, r.weight) for l, r, _ in merges], [(2, 5), (6, 7), (10, 13), (15, 18), (20, 23), (33, 43)])

    def test_totals(self):
        root, _, merges = D.fig_tree()
        c = D.codes(root)
        self.assertEqual(sum(D.FREQ[s] * len(c[s]) for s in c), 195)
        self.assertEqual(D.wpl(root), 195)
        self.assertEqual(sum(p.weight for _, _, p in merges), 195)
        self.assertEqual(D.fixed_bits(7, 76), (3, 228))
        self.assertEqual(D.oj04080(D.FREQ.values()), 195)
        self.assertEqual(brute_min_wpl(list(D.FREQ.values())), 195)

    def test_message(self):
        root, _, _ = D.msg_tree()
        c = D.codes(root)
        self.assertEqual(c, {"a": "0", "b": "10", "c": "110", "d": "111"})
        self.assertEqual(len("".join(c[x] for x in D.MSG)), 14)
        self.assertEqual(D.wpl(root), 14)
        self.assertEqual(D.fixed_bits(4, len(D.MSG)), (2, 16))

    def test_fig518(self):
        self.assertEqual({k: D.nested_wpl(t) for k, t in D.FIG518_TREES.items()}, {"a": 30, "b": 31, "c": 29})
        self.assertEqual(brute_min_wpl(D.FIG518), 29)
        self.assertEqual(D.oj04080([1, 1, 3, 5]), 17)            # 讲义 OJ04080 样例
        self.assertEqual(D.oj04080([2, 3, 4, 7]), 30)

    def test_ambiguous_code(self):
        bad = {"a": "0", "b": "1", "c": "01", "d": "10"}
        parses = set()
        def go(s, acc):
            if not s:
                parses.add(acc)
                return
            for ch, code in bad.items():
                if s.startswith(code):
                    go(s[len(code):], acc + ch)
        go("011", "")
        self.assertEqual(parses, {"abb", "cb"})

    def test_decode_word(self):
        root, _, _ = D.fig_tree()
        c = D.codes(root)
        bits = "".join(c[x] for x in D.WORD)
        self.assertEqual(bits, "11100011010")
        self.assertEqual(D.decode_trace(root, bits)[0], D.WORD)

    def test_random_optimal_prefix_roundtrip(self):
        rng = random.Random(3)
        for _ in range(60):
            n = rng.randint(2, 7)
            syms = "abcdefg"[:n]
            ws = [rng.randint(1, 30) for _ in range(n)]
            root, _, _ = D.build(list(syms), ws)
            c = D.codes(root)
            self.assertEqual(D.wpl(root), brute_min_wpl(ws))
            self.assertEqual(D.wpl(root), D.oj04080(ws))
            for x, y in itertools.permutations(c.values(), 2):
                self.assertFalse(y.startswith(x))
            text = "".join(rng.choice(syms) for _ in range(20))
            self.assertEqual(D.decode_trace(root, "".join(c[t] for t in text))[0], text)

    def test_equal_weights(self):
        root, _, _ = D.build(list("stuvwxyz"), [1] * 8)
        self.assertEqual({len(v) for v in D.codes(root).values()}, {3})

    def test_narration_numbers(self):
        s = json.loads((HERE / "huffman.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in s["beats"]}
        self.assertIn("十六位", nar["title"])
        self.assertIn("三十、三十一、二十九", nar["wpl"])
        self.assertIn("十五、二、六、五、二十、十、十八", nar["build1"])
        self.assertIn("二和五，合成七", nar["build1"])
        self.assertIn("十和十三合成二十三", nar["build1"])
        self.assertIn("三十三和四十三合成七十六", nar["build2"])
        self.assertIn("一百九十五位", nar["total"])
        self.assertIn("二百二十八位", nar["total"])
        self.assertIn("七、十三、二十三、三十三、四十三、七十六", nar["total"])
        self.assertIn("c、a、f、e", nar["decode"])
        self.assertIn("一共十四位", nar["recap"])


if __name__ == "__main__":
    unittest.main()
