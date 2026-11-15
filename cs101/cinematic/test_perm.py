"""全排列片数字的独立对撞：讲义原版代码（插桩记录）、itertools、阶乘公式与旁白稿。

用法（cwd = cs101/cinematic）：python -m unittest test_perm
"""
from itertools import permutations as it_perm
import json
from math import e, factorial
from pathlib import Path
import unittest

import permdata as P


def course_permutations(a, log):
    """讲义 3.3 节代码原样照抄，只加了 log 插桩。"""
    res = []
    used = [False] * len(a)
    path = []

    def dfs():
        if len(path) == len(a):
            res.append(path[:])
            log.append(("collect", tuple(path)))
            return
        for i in range(len(a)):
            if used[i]:
                continue
            used[i] = True
            path.append(a[i])
            log.append(("down", tuple(path), i))
            dfs()
            log.append(("up", tuple(path), i))
            path.pop()
            used[i] = False

    dfs()
    return res


def course_subsets(nums):
    n, ans, sol = len(nums), [], []

    def backtrack(i):
        if i == n:
            ans.append(sol[:])
            return
        backtrack(i + 1)
        sol.append(nums[i])
        backtrack(i + 1)
        sol.pop()

    backtrack(0)
    return ans


class PermFacts(unittest.TestCase):
    def test_leaves_are_permutations_in_order(self):
        for n in range(1, 6):
            a = list(range(1, n + 1))
            leaves = [nd.path for nd in P.perm_tree(a) if not nd.children]
            self.assertEqual(leaves, list(it_perm(a)))
            self.assertEqual(leaves, [tuple(p) for p in course_permutations(a, [])])

    def test_walk_matches_course_code(self):
        for n in range(1, 5):
            a = list(range(1, n + 1))
            log = []
            course_permutations(a, log)
            nodes = P.perm_tree(a)
            mine = [(k, nodes[x[1]].path, *x[2:]) for x in P.walk_events(a) for k in [x[0]]]
            self.assertEqual(mine, log)

    def test_counts(self):
        self.assertEqual(P.level_counts(3), [1, 3, 6, 6])
        self.assertEqual(P.node_total(3), 16)
        self.assertEqual(len(P.perm_tree([1, 2, 3])), 16)
        for n in range(1, 9):
            self.assertEqual(len(P.perm_tree(list(range(n)))), P.node_total(n))
            self.assertLess(P.node_total(n), e * factorial(n))
        ev = P.walk_events([1, 2, 3])
        self.assertEqual(sum(1 for x in ev if x[0] == "down"), 15)
        self.assertEqual(sum(1 for x in ev if x[0] == "collect"), 6)

    def test_alias_pitfall(self):
        """不拷贝：六个答案是同一个列表，搜索结束后全空。"""
        res, used, path, a = [], [False] * 3, [], [1, 2, 3]

        def dfs():
            if len(path) == 3:
                res.append(path)
                return
            for i in range(3):
                if not used[i]:
                    used[i] = True
                    path.append(a[i])
                    dfs()
                    path.pop()
                    used[i] = False
        dfs()
        self.assertEqual(res, [[]] * 6)
        self.assertTrue(all(r is res[0] for r in res))

    def test_subsets(self):
        leaves = [list(nd.path) for nd in P.subset_tree([1, 2, 3]) if not nd.children]
        self.assertEqual(leaves, course_subsets([1, 2, 3]))
        self.assertEqual(leaves, [[], [3], [2], [2, 3], [1], [1, 3], [1, 2], [1, 2, 3]])  # 讲义输出

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("perm.json").read_text(encoding="utf-8"))["beats"])
        for s in ("三乘二等于六种", "六、六、三、一，一共十六个", "十六个节点，收下六个排列",
                  "二的三次方，八个叶子", "六个空列表"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
