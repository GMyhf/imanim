"""排序片数字的独立对撞：sorted()、讲义输出、暴力 O(n²) 数逆序对、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_sort
"""
import json
from pathlib import Path
import random
import unittest

import sortdata as S


def replay_bubble(a, ev):
    a = a[:]
    for e in ev:
        if e[0] == "cmp" and e[2]:
            j = e[1]
            a[j], a[j + 1] = a[j + 1], a[j]
    return a


def replay_insertion(a, ev):
    a, key = a[:], None
    for e in ev:
        if e[0] == "lift":
            key = a[e[1]]
        elif e[0] == "shift":
            a[e[1] + 1] = a[e[1]]
        else:
            a[e[1]] = key
    return a


class SortFacts(unittest.TestCase):
    def test_all_sorts_agree(self):
        rng = random.Random(1)
        for _ in range(200):
            t = [rng.randint(0, 100) for _ in range(rng.randint(0, 30))]
            want = sorted(t)
            self.assertEqual(S.bubble_sort(t), want)
            self.assertEqual(S.insertion_sort(t), want)
            self.assertEqual(S.merge_sort(t), want)
            self.assertEqual(S.quick_sort(t), want)
            self.assertEqual(S.count_inversions(t), (want, S.brute_inversions(t)))

    def test_traces_replay(self):
        ev, out = S.bubble_trace(S.DATA)
        self.assertEqual(replay_bubble(S.DATA, ev), sorted(S.DATA))
        self.assertEqual(out, sorted(S.DATA))
        self.assertEqual(ev[-1], ("pass", ev[-1][1], False))          # 最后一趟没交换才退出
        iev, iout = S.insertion_trace(S.DATA)
        self.assertEqual(replay_insertion(S.DATA, iev), sorted(S.DATA))
        splits, merges = S.merge_levels(S.DATA)
        lo, mid, hi, takes, d = merges[-1]
        self.assertEqual((lo, hi, d), (0, len(S.DATA), 0))
        self.assertEqual([v for _, v in takes], sorted(S.DATA))
        self.assertEqual(len(splits[3]), 8)

    def test_course_outputs(self):
        self.assertEqual(S.count_inversions([3, 1, 2])[1], 2)
        self.assertEqual(S.count_inversions([5, 4, 3, 2, 1])[1], 10)
        first, second = S.two_pass(S.ROWS)
        self.assertEqual(second, [("b", 1), ("a", 2), ("c", 2)])

    def test_batch_counting(self):
        ev, cnt = S.merge_count_trace(S.INV_LEFT, S.INV_RIGHT)
        self.assertEqual([e[3] for e in ev if e[0] == "R"], [3, 2, 1])   # 一次加三、加二、加一
        self.assertEqual(cnt, 6)
        self.assertEqual(cnt, S.brute_inversions(S.INV_LEFT + S.INV_RIGHT))

    def test_growth(self):
        sq, nlog = S.growth(1000)
        self.assertEqual(sq, 1_000_000)
        self.assertEqual(round(nlog, -3), 10_000)                     # 大约一万

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("sort.json").read_text(encoding="utf-8"))["beats"])
        for s in ("一百万", "大约一万", "一次加三", "加二", "加一", "一共六个", "左半二五七，右半一三六"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
