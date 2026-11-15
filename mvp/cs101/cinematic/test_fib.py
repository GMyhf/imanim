"""斐波那契片数字的独立对撞：真实执行带计数器的递归 / lru_cache，不复用 fibdata 的建树逻辑。

用法（cwd = mvp/cs101/cinematic）：python -m unittest test_fib
"""
import functools
import json
from pathlib import Path
import unittest

import fibdata


def run_naive(n):
    log = []
    def f(k):
        log.append(k)
        return 1 if k <= 2 else f(k - 1) + f(k - 2)
    return f(n), log


def run_memo(n):
    log = []
    @functools.lru_cache(maxsize=None)
    def inner(k):
        return 1 if k <= 2 else f(k - 1) + f(k - 2)
    def f(k):
        log.append(k)          # 每次「调用」都记账，命中缓存也算一次（画面里的查表叶子）
        return inner(k)
    return f(n), log


class FibFacts(unittest.TestCase):
    def test_tree_matches_real_call_order(self):
        for n in range(1, 12):
            _, log = run_naive(n)
            self.assertEqual([x.n for x in fibdata.call_tree(n)], log)

    def test_memo_matches_lru_cache(self):
        for n in range(1, 15):
            val, log = run_memo(n)
            nodes = fibdata.apply_memo(fibdata.call_tree(n))
            self.assertEqual([x.n for x in nodes if not x.pruned], log)
            self.assertEqual(val, fibdata.fib(n))

    def test_counts_in_narration(self):
        f = fibdata.facts()
        self.assertEqual(f["naive_calls"], 15)
        self.assertEqual(f["memo_calls"], 9)
        self.assertEqual({k: f["repeats"][k] for k in (4, 3, 2)}, {4: 2, 3: 3, 2: 5})
        self.assertEqual(f["big_calls"], 2 * fibdata.fib(40) - 1)   # 闭式：调用数 = 2F(n) - 1
        self.assertEqual(f["table"][-1], 55)

    def test_naive_calls_closed_form(self):
        for n in range(1, 25):
            self.assertEqual(fibdata.naive_calls(n), len(run_naive(n)[1]))

    def test_narration_numbers(self):
        """旁白稿里写死的中文数字必须与 facts 一致（改了 n 忘改稿会在这里炸）。"""
        text = "".join(b["narration"] for b in json.loads(
            (Path(__file__).with_name("fib.json")).read_text(encoding="utf-8"))["beats"])
        for phrase in ("调用了十五次", "十五次调用变成九次", "fib 四被算了两次", "fib 三被算了三次",
                       "fib 二被算了五次", "两亿多次", "五十五"):
            self.assertIn(phrase, text)
        self.assertTrue(2e8 <= fibdata.naive_calls(40) < 3e8)


if __name__ == "__main__":
    unittest.main()
