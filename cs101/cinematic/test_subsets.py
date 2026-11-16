"""回溯三形态片数字的独立对撞：讲义输出、itertools 枚举、另写的节点计数、剪枝前后节点与比较次数、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_subsets
"""
from itertools import combinations, combinations_with_replacement, permutations
import json
from math import comb, factorial
from pathlib import Path
import unittest

import subsetsdata as S


def all_subsets(nums):
    return {c for k in range(len(nums) + 1) for c in combinations(nums, k)}


def csum_brute(cands, target):
    """不用回溯：枚举长度 1..target//min 的可重复组合，挑和为 target 的。"""
    cands = sorted(cands)
    out = []
    for k in range(1, target // cands[0] + 1):
        out += [list(c) for c in combinations_with_replacement(cands, k) if sum(c) == target]
    return sorted(out)


def csum_counts(cands, target):
    """另写一遍计数：不剪枝的节点数、剪枝后的节点数、continue / break 的比较次数。"""
    cands = sorted(cands)

    def none(start, rest):
        if rest <= 0:
            return 1
        return 1 + sum(none(i, rest - cands[i]) for i in range(start, len(cands)))

    def pruned(start, rest):
        if rest == 0:
            return 1, 0, 0
        n, c_cont, c_brk = 1, 0, 0
        ok = [i for i in range(start, len(cands)) if cands[i] <= rest]
        c_cont += len(cands) - start                          # continue：每个候选都比一次
        c_brk += len(ok) + (1 if len(ok) < len(cands) - start else 0)   # break：合法的 + 第一个超额的
        for i in ok:
            a, b, c = pruned(i, rest - cands[i])
            n, c_cont, c_brk = n + a, c_cont + b, c_brk + c
        return n, c_cont, c_brk
    return none(0, target), *pruned(0, target)


class SubsetsFacts(unittest.TestCase):
    def test_course_outputs(self):
        """讲义里印出来的结果。"""
        self.assertEqual(S.subsets_pick([1, 2, 3]), [[], [3], [2], [2, 3], [1], [1, 3], [1, 2], [1, 2, 3]])
        self.assertEqual(S.subsets_start([1, 2, 3]), [[], [1], [1, 2], [1, 2, 3], [1, 3], [2], [2, 3], [3]])
        self.assertEqual(S.combination_sum([2, 3, 6, 7], 7), [[2, 2, 3], [7]])
        self.assertEqual(["".join(map(str, p)) for p in S.permutations([1, 2, 3])],
                         "123 132 213 231 312 321".split())

    def test_against_itertools(self):
        for n in range(0, 7):
            a = list(range(1, n + 1))
            want = all_subsets(a)
            self.assertEqual({tuple(x) for x in S.subsets_pick(a)}, want)
            self.assertEqual({tuple(x) for x in S.subsets_start(a)}, want)
            self.assertEqual(len(S.subsets_start(a)), 2 ** n)
            self.assertEqual([tuple(p) for p in S.permutations(a)], list(permutations(a)))
            for k in range(n + 1):
                self.assertEqual([tuple(c) for c in S.combine(a, k)], list(combinations(a, k)))
        for cands, t in (([2, 3, 6, 7], 7), ([2, 3, 5], 8), ([2, 3, 6, 7], 10), ([3, 5, 2], 12)):
            for mode in ("none", "continue", "break"):
                self.assertEqual(sorted(S.combination_sum(cands, t, mode=mode)), csum_brute(cands, t))

    def test_trees(self):
        for n in range(1, 6):
            a = list(range(1, n + 1))
            pick = S.pick_tree(a)
            self.assertEqual(len(pick), 2 ** (n + 1) - 1)
            leaves = [list(nd.path) for nd in pick if not nd.children]
            self.assertEqual(leaves, S.subsets_pick(a))
            self.assertTrue(all(nd.collected == (not nd.children) for nd in pick))
            st = S.start_tree(a)
            self.assertEqual(len(st), 2 ** n)
            self.assertTrue(all(nd.collected for nd in st))
            self.assertEqual([list(nd.path) for nd in sorted(st, key=lambda d: d.order)], S.subsets_start(a))
            for nd in st:                                   # 孩子 = 往后挑：最后一个数之后的每个数各一个
                tail = a[a.index(nd.path[-1]) + 1:] if nd.path else a
                self.assertEqual([st[c].path[-1] for c in nd.children], tail)
            pt = S.perm_tree(a)
            self.assertEqual(len(pt), sum(factorial(n) // factorial(n - k) for k in range(n + 1)))
            for k in range(n + 1):
                ct = S.combine_tree(a, k)
                self.assertEqual(sum(nd.collected for nd in ct), comb(n, k))
                # 长度不超过 k 的升序路径都会走到（后面不剩数的节点只是没有孩子）：节点数 = Σ C(n, d)
                self.assertEqual(len(ct), sum(comb(n, d) for d in range(k + 1)))

    def test_next_choices(self):
        """片中高亮的节点 [2]：子集、组合只能挑 3，组合总和还能再挑 2，排列能挑 1 和 3。"""
        self.assertEqual(S.next_choices("subset", (2,)), [3])
        self.assertEqual(S.next_choices("combine", (2,)), [3])
        self.assertEqual(S.next_choices("perm", (2,)), [1, 3])
        self.assertEqual(S.next_choices("csum", (2,), [2, 3, 6, 7]), [2, 3, 6, 7])
        for kind, tree in (("subset", S.start_tree()), ("combine", S.combine_tree()), ("perm", S.perm_tree())):
            for nd in tree:
                self.assertEqual([tree[c].path[-1] for c in nd.children], S.next_choices(kind, nd.path))

    def test_prune_counts(self):
        f = S.facts()
        none, brk, c_cont, c_brk = csum_counts(S.CANDS, S.TARGET)
        self.assertEqual((f["csum_none"], f["csum_break"], f["cmp_continue"], f["cmp_break"]),
                         (none, brk, c_cont, c_brk))
        self.assertEqual((none, brk, c_cont, c_brk), (28, 10, 27, 16))
        self.assertEqual(f["csum_dead"], none - brk)                 # 剪掉的恰好是全部死节点
        self.assertEqual(f["csum_continue"], brk)
        self.assertEqual(f["breaks"], 7)
        for cands, t in (([2, 3, 5], 8), ([2, 3, 6, 7], 10)):
            n0, n1, a, b = csum_counts(cands, t)
            self.assertEqual(len(S.csum_tree(cands, t, "none")), n0)
            self.assertEqual(len(S.csum_tree(cands, t, "break")), n1)
            self.assertEqual(S.csum_compares(cands, t, "continue"), a)
            self.assertEqual(S.csum_compares(cands, t, "break"), b)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("subsets.json").read_text(encoding="utf-8"))["beats"]}
        f = S.facts()
        self.assertEqual((f["pick_nodes"], f["pick_leaves"]), (15, 8))
        self.assertIn("十五个节点，只有最底层的八个叶子", beats["pick"])
        self.assertEqual(f["start_nodes"], 8)
        self.assertIn("八个节点，正好八个子集，比二叉树少了七个节点", beats["start"])
        self.assertIn("可以挑一、二、三", beats["start"])
        self.assertIn("只能往后挑二或三", beats["start"])
        self.assertIn("下一层只能挑三", beats["three"])
        self.assertIn("没用过的一和三都能选", beats["three"])
        self.assertEqual(f["csum_answers"], [[2, 2, 3], [7]])
        self.assertIn("二二三，和七", beats["csum"])
        for s in ("二十八个节点", "十八个是红色的死路", "只剩十个节点", "节点也是十个", "一共二十七次", "只比较十六次"):
            self.assertIn(s, beats["prune"])
        self.assertIn("三者的差别，只在下一层能选哪些数", beats["three"])


if __name__ == "__main__":
    unittest.main()
