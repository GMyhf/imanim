"""最多按时完成几个任务片数字的独立对撞：讲义样例输出、子集枚举 + 最早截止顺序、逐步不变量、插桩回放、旁白数字。

独立实现不调用 deadlinedata 的算法：best_subsets 枚举全部子集，用「按截止排序后逐个检查」判可行（不经堆）。
用法（cwd = cs101/cinematic）：python -m unittest test_deadline
"""
from itertools import combinations, permutations
import heapq
import json
from pathlib import Path
import random
import unittest

import deadlinedata as D


def feasible(sub):
    t = 0
    for c, d in sorted(sub, key=lambda x: x[1]):
        t += c
        if t > d:
            return False
    return True


def best_subsets(tasks):
    """返回 (最多个数, 这个个数下的最小总时长)。全部子集枚举。"""
    for k in range(len(tasks), -1, -1):
        tots = [sum(c for c, _ in s) for s in combinations(tasks, k) if feasible(s)]
        if tots:
            return k, min(tots)
    return 0, 0


def feasible_any_order(sub):
    """不假设最早截止优先：试遍全部顺序。"""
    for order in permutations(sub):
        t, ok = 0, True
        for c, d in order:
            t += c
            if t > d:
                ok = False
                break
        if ok:
            return True
    return not sub


class DeadlineFacts(unittest.TestCase):
    def test_lecture_samples(self):
        for ts, want in D.LECTURE_SAMPLES:
            self.assertEqual(D.max_tasks(ts), want)
            self.assertEqual(D.max_tasks_brute(ts), want)
            self.assertEqual(best_subsets(ts)[0], want)

    def test_lecture_check_sequence(self):
        """讲义写的是 random.seed(101) + 模块级 randint；独立 Random(101) 生成同样的 200 组。"""
        random.seed(101)
        cases = []
        for _ in range(200):
            n = random.randint(1, 6)
            cases.append([(random.randint(1, 5), random.randint(1, 12)) for _ in range(n)])
        self.assertEqual(cases, D.lecture_check())
        for ts in cases:
            self.assertEqual(D.max_tasks(ts), best_subsets(ts)[0])
        bad = sum(D.skip_greedy(ts)[0] != best_subsets(ts)[0] for ts in cases)
        self.assertEqual(D.CHECK, (200, 6, bad))
        self.assertEqual(bad, 1)

    def test_edf_order_suffices(self):
        """排序键：一组任务只要有某种顺序能全部按时，按截止时间排序就一定能。"""
        rnd = random.Random(13)
        for _ in range(300):
            sub = [(rnd.randint(1, 5), rnd.randint(1, 12)) for _ in range(rnd.randint(0, 5))]
            self.assertEqual(feasible_any_order(sub), D.edf_ok(sub))

    def test_invariant_random(self):
        """每加入一个任务后：堆的大小 = 前缀里最多能完成几个，堆里总时长 = 这个个数下的最小总时长。"""
        rnd = random.Random(1305)
        for _ in range(150):
            ts = [(rnd.randint(1, 8), rnd.randint(1, 20)) for _ in range(rnd.randint(1, 8))]
            srt = sorted(ts, key=lambda t: t[1])
            tr = D.trace(ts)
            for k, st in enumerate(tr):
                self.assertEqual((len(st["heap"]), st["total"]), best_subsets(srt[:k + 1]))
                self.assertEqual(st["total"], sum(st["heap"]))
                if st["dropped"] is not None:
                    self.assertEqual(st["dropped"], max(st["pushed"]))
                    self.assertLessEqual(st["total"], tr[k - 1]["total"] if k else 0)   # 一个 if 就够
            self.assertEqual(D.max_tasks(ts), best_subsets(ts)[0])

    def test_main_example(self):
        self.assertEqual(D.SORTED, [(1, 2), (5, 6), (2, 7), (6, 9), (4, 10), (3, 11)])
        self.assertEqual(len({c for c, _ in D.TASKS}), len(D.TASKS))         # 耗时互不相同，画堆时一一对应
        self.assertEqual(D.ANSWER, 4)
        self.assertEqual(best_subsets(D.TASKS), (4, 10))
        self.assertEqual(D.max_tasks_brute(D.TASKS), 4)
        # 逐步回放：自己维护的大根堆
        h, tot, rows = [], 0, []
        for c, d in D.SORTED:
            heapq.heappush(h, -c)
            tot += c
            tin, drop = tot, None
            if tot > d:
                drop = -heapq.heappop(h)
                tot -= drop
            rows.append((c, d, tin, drop, tot))
        self.assertEqual(rows, [(s["cost"], s["deadline"], s["total_in"], s["dropped"], s["total"]) for s in D.TR])
        self.assertEqual(rows, [(1, 2, 1, None, 1), (5, 6, 6, None, 6), (2, 7, 8, 5, 3),
                                (6, 9, 9, None, 9), (4, 10, 13, 6, 7), (3, 11, 10, None, 10)])
        self.assertEqual(D.DROPS, [(2, 5), (4, 6)])
        self.assertEqual(sorted(D.TR[-1]["heap"]), [1, 2, 3, 4])
        self.assertEqual(D.drop_options(2), [(1, 7), (2, 6), (5, 3)])
        self.assertTrue(all(d <= 7 for _, d in D.SORTED[:3]))
        self.assertEqual(D.skip_greedy(), (3, [True, True, False, False, True, False]))
        self.assertEqual(D.wrong_sign(), 2)
        lay = D.layout([(c, d) for c, d in D.SORTED if c in D.TR[-1]["heap"]])
        self.assertTrue(all(end <= d for _, d, _, end in lay))

    def test_range_numbers(self):
        self.assertEqual(D.N2, 10 ** 10)
        self.assertTrue(1.6e6 < D.NLOGN < 2e6)

    def test_narration_numbers(self):
        nar = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("deadline.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("十万", nar["read"])
        self.assertIn("一百亿次", nar["read"])
        self.assertIn("不到两百万次", nar["read"])
        w = nar["walk"]
        for s in ("耗时一，截止二", "耗时五，总时长六，正好赶上截止六", "耗时二，总时长八，超过了七",
                  "耗时五的那个，总时长降到三", "耗时六，总时长九，正好赶上", "耗时四，总时长十三，超过十，再扔堆顶的六，降到七",
                  "最后耗时三，总时长十，赶上十一", "堆里剩四个，答案是四"):
            self.assertIn(s, w)
        self.assertIn("一、五、二这三个任务，截止都不晚于七，总时长却是八，至少要扔一个", nar["why"])
        self.assertIn("扔一剩七，扔二剩六，扔五只剩三", nar["why"])
        self.assertIn("写成减号，这组数据只剩两个", nar["trap"])
        self.assertIn("后面二、六、三都放不进去，只完成三个", nar["trap"])
        self.assertIn("两百组，每组最多六个任务", nar["check"])
        self.assertIn("两百组里只有一组会报错", nar["check"])


if __name__ == "__main__":
    unittest.main()
