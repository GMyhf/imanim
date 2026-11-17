"""双重回文精讲片数字的独立对撞：题面样例、暴力随机对拍、插桩回放、片中画出的数字、旁白数字。

独立实现不调用 novpaldata / novdata 的算法：回文用 format(i, 'b') 与字符串翻转判断，
pal 轨迹用「把 x 的 base 进制数字串逐个前缀反转后 int(s, base)」重建。
用法（cwd = cs101/cinematic）：python -m unittest test_novpal
"""
import inspect
import json
from pathlib import Path
import random
import unittest

import novpaldata as D

HERE = Path(__file__).resolve().parent
NARR = "".join(b["narration"] for b in json.loads((HERE / "novpal.json").read_text(encoding="utf-8"))["beats"])


def is_pal_s(s):
    return s == s[::-1]


def brute(n):
    """全部 1..n（含偶数）逐个判，字符串翻转。"""
    return [i for i in range(1, n + 1) if is_pal_s(str(i)) and is_pal_s(format(i, "b"))]


def digits(x, base):
    s = ""
    while x:
        s = "0123456789"[x % base] + s
        x //= base
    return s


def rev_prefixes(x, base):
    """把 x 的数字串倒过来，逐个前缀转回整数：应与 pal 每一步的 y 相同。"""
    r = digits(x, base)[::-1]
    return [int(r[:k], base) for k in range(1, len(r) + 1)]


class NovPalTest(unittest.TestCase):
    def test_samples(self):
        for inp, out in D.SAMPLES:
            self.assertEqual(D.run_io(D.SOLVE, inp), out)
        self.assertEqual(D.SAMPLES, [("5\n", "3 5"), ("100\n", "7 99")])

    def test_code_text_is_handout(self):
        src = inspect.getsource(D.N.solve_t1).splitlines()[1:]
        self.assertEqual([s[4:] for s in src], D.PY_CODE)

    def test_random_vs_brute(self):
        rng = random.Random(31529)
        for n in [1, 2, 3, 4, 5, 9, 10, 32, 33, 34, 99, 100, 101] + [rng.randint(1, 20000) for _ in range(40)]:
            b = brute(n)
            self.assertEqual(D.run_io(D.SOLVE, f"{n}\n"), f"{len(b)} {b[-1]}")
            self.assertEqual(D.double_pals(n), b)

    def test_big(self):
        n, cnt, best = D.BIG
        b = brute(n)
        self.assertEqual((len(b), b[-1]), (cnt, best))
        self.assertEqual(D.run_io(D.SOLVE, f"{n}\n"), f"{cnt} {best}")
        self.assertEqual(len(format(best, "b")), 20)
        self.assertTrue(is_pal_s(format(best, "b")))

    def test_even_never(self):
        for i in range(2, 5000, 2):
            s = format(i, "b")
            self.assertEqual((s[0], s[-1]), ("1", "0"))
        for e in D.EX_EVEN:
            self.assertFalse(D.pal(e, 2))
        self.assertEqual([format(e, "b") for e in D.EX_EVEN], ["110", "1010"])

    def test_nostrip(self):
        self.assertEqual(D.run_io(D.solve_t1_nostrip, "5\n"), "0 1")
        self.assertEqual(bin(5), "0b101")
        self.assertEqual(bin(5)[::-1], "101b0")

    def test_pal_trace(self):
        for x in [1, 5, 33, 37, 99, 585585, 123, 1000]:
            for base in (2, 10):
                st = D.pal_trace(x, base)
                self.assertEqual([y for _, _, y in st], rev_prefixes(x, base))
                self.assertEqual([r for _, r, _ in st], [int(c) for c in digits(x, base)[::-1]])
                self.assertEqual(D.pal(x, base), is_pal_s(digits(x, base)))
        self.assertEqual([y for _, _, y in D.pal_trace(D.EX_YES, 2)], [1, 2, 4, 8, 16, 33])
        self.assertEqual([r for _, r, _ in D.pal_trace(D.EX_YES, 2)], [1, 0, 0, 0, 0, 1])
        self.assertEqual([t for t, _, _ in D.pal_trace(D.EX_YES, 2)], [33, 16, 8, 4, 2, 1])
        self.assertEqual(D.pal_trace(D.EX_NO, 2)[-1][2], 41)
        self.assertEqual([y for _, _, y in D.pal_trace(D.EX_NO, 2)], [1, 2, 5, 10, 20, 41])
        self.assertEqual([y for _, _, y in D.pal_trace(D.EX_DEC, 10)], [5, 58, 585, 5855, 58558, 585585])

    def test_scan_table(self):
        tab = D.scan_table(5)
        self.assertEqual([b for _, b, _, _ in tab], ["1", "10", "11", "100", "101"])
        self.assertEqual([i for i, _, d, b in tab if d and b], [1, 3, 5])

    def test_sample2_steps(self):
        dp = D.dec_pals(100)
        self.assertEqual(dp, [i for i in range(1, 101) if is_pal_s(str(i))])
        self.assertEqual(len(dp), 18)
        odd = [i for i in dp if i % 2]
        self.assertEqual(odd, [1, 3, 5, 7, 9, 11, 33, 55, 77, 99])
        self.assertEqual([format(i, "b") for i in (11, 33, 99)], ["1011", "100001", "1100011"])
        self.assertEqual([i for i in odd if is_pal_s(format(i, "b"))], [1, 3, 5, 7, 9, 33, 99])

    def test_title_example(self):
        self.assertEqual(format(D.EX_TITLE, "b"), "1001001001")
        self.assertTrue(is_pal_s(str(D.EX_TITLE)) and is_pal_s(format(D.EX_TITLE, "b")))

    def test_cost(self):
        n = 10 ** 6
        odd = range(1, n + 1, 2)
        self.assertEqual(len(odd), 500000)
        self.assertEqual(max(len(str(i)) for i in odd), 6)
        self.assertEqual(max(len(format(i, "b")) for i in odd), 20)
        tot = sum(len(str(i)) + len(format(i, "b")) for i in odd)
        self.assertEqual(D.char_total(n), tot)
        self.assertEqual(round(tot / 1e6), 12)               # 「大约一千二百万个字符」

    def test_narration_numbers(self):
        for s in ["最大一百万", "n 等于五", "二是一零，倒过来是零一", "四是一零零", "五是一零一",
                  "一共三个，最大是五，输出三和五", "零 b 一零一", "一零一 b 零", "输出零个，最大的还是初值一",
                  "六是一一零，十是一零一零", "三十三按二进制", "余数依次是一零零零零一",
                  "一、二、四、八、十六、三十三", "换成三十七：y 最后是四十一", "五八五五八五倒过来",
                  "n 等于一百", "十一是一零一一", "三十三是一零零零零一", "九十九是一一零零零一一",
                  "剩下十个", "一共七个，最大九十九，输出七和九十九", "五十万个", "十进制最多六位", "二进制最多二十位",
                  "大约一千二百万个字符", "答案是十九个", "五十八万五千五百八十五", "二进制有二十位",
                  "n 等于一，输出一和一"]:
            self.assertIn(s, NARR)
        self.assertEqual(D.run_io(D.SOLVE, "1\n"), "1 1")


if __name__ == "__main__":
    unittest.main()
