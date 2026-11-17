"""数的划分片数字的独立对撞：讲义原样输出、穷举分法、换一种递推（完全背包计数）、搜索树规模、旁白数字。

独立实现不调用 partitiondata 的算法：穷举用 itertools.combinations_with_replacement，
另一种递推用「最大的一份恰好是 k」的共轭视角：把 n-k 用面值 1..k 的硬币凑（完全背包计数）。
用法（cwd = cs101/cinematic）：python -m unittest test_partition
"""
from itertools import combinations_with_replacement
import json
from pathlib import Path
import random
import unittest

import partitiondata as P


def brute(n, k):
    """穷举所有非降的 k 元组。"""
    return sum(1 for c in combinations_with_replacement(range(1, n + 1), k) if sum(c) == n)


def conj(n, k):
    """共轭：分成 k 份 ⇔ 最大的一份恰好是 k。去掉一个 k，剩下 n-k 用 1..k 凑，顺序无关（完全背包计数）。"""
    if n < k:
        return 0
    ways = [1] + [0] * (n - k)
    for c in range(1, k + 1):
        for v in range(c, n - k + 1):
            ways[v] += ways[v - c]
    return ways[n - k]


def tree_size(rem, left, low, bound):
    """搜索树节点数（不记忆化），与 partitiondata 的插桩独立地数。"""
    if left == 1:
        return 1
    hi = rem // left if bound else rem
    return 1 + sum(tree_size(rem - x, left - 1, x, bound) for x in range(low, hi + 1))


class PartitionFacts(unittest.TestCase):
    def test_samples(self):
        self.assertEqual(P.run_lecture(P.N, P.K), 4)                    # 样例一
        self.assertEqual(P.run_lecture(P.N2, P.K2), 3)                  # 样例二
        self.assertEqual((P.dp_count(7, 3), P.dp_count(7, 2)), (4, 3))
        self.assertEqual(P.partitions(), [(1, 1, 5), (1, 2, 4), (1, 3, 3), (2, 2, 3)])

    def test_against_independent(self):
        for n in range(1, 31):
            for k in range(1, 7):
                self.assertEqual(P.dp_count(n, k), brute(n, k), (n, k))
                self.assertEqual(P.dfs_count(n, k)[0], brute(n, k), (n, k))
        rng = random.Random(28906)
        for _ in range(40):
            n, k = rng.randint(P.N_LO, P.N_HI), rng.randint(P.K_LO, P.K_HI)
            self.assertEqual(P.run_lecture(n, k), conj(n, k))
            self.assertEqual(P.dp_count(n, k), conj(n, k))
        self.assertEqual(P.run_lecture(*P.BIG), conj(*P.BIG))

    def test_cross_check(self):
        cnt, bad = P.cross_check()
        self.assertEqual(cnt, (P.N_HI - P.N_LO + 1) * (P.K_HI - P.K_LO + 1))
        self.assertEqual((cnt, bad), (970, []))
        self.assertEqual(P.brute_check(), (P.BRUTE_MAX * 6, []))

    def test_dup_and_tree(self):
        comp = P.compositions()
        self.assertEqual(len(comp), 15)
        self.assertEqual(len(set(comp)), 15)
        self.assertEqual(sorted({tuple(sorted(c)) for c in comp}), P.partitions())
        t = P.dfs_tree()
        self.assertEqual(len(t), tree_size(7, 3, 1, True))
        self.assertEqual(len(t), 7)
        root = t[0]
        self.assertEqual([t[c]["x"] for c in root["kids"]], [1, 2])     # 第一份可以是一或二
        self.assertEqual((t[root["kids"][0]]["rem"], t[root["kids"][0]]["left"]), (6, 2))
        leaves = [x for x in t if x["left"] == 1]
        self.assertTrue(all(x["ok"] for x in leaves))
        self.assertEqual([tuple(x["path"]) for x in leaves], P.partitions())
        full = P.dfs_tree(bound=False)
        self.assertEqual(len(full), tree_size(7, 3, 1, False))
        self.assertEqual(len(full), 20)
        self.assertEqual(sum(not x["useful"] for x in full), 13)
        self.assertEqual(sorted(map(P.tree_key, t)), sorted(P.tree_key(x) for x in full if x["useful"]))

    def test_memo_and_dp(self):
        ans, calls, states = P.dfs_count(*P.BIG, memo=False)
        self.assertEqual(ans, 4132096)
        self.assertEqual(calls, tree_size(200, 6, 1, True))
        self.assertTrue(4_300_000 <= calls < 4_400_000)                # 四百三十多万次
        self.assertEqual(P.dfs_count(*P.BIG)[1:], (11888, 11888))
        self.assertEqual(states, 11888)
        ones, removed, rest, minus = P.split_classes()
        self.assertEqual(len(ones), brute(6, 2))
        self.assertEqual(len(rest), brute(4, 3))
        self.assertEqual((len(ones), len(rest)), (3, 1))
        self.assertEqual(sorted(removed), sorted(c for c in combinations_with_replacement(range(1, 7), 2) if sum(c) == 6))
        self.assertEqual(minus, [(1, 1, 2)])
        dp = P.dp_table(7, 3)
        self.assertEqual(dp[7][3], dp[6][2] + dp[4][3])
        self.assertEqual(dp[0][0], 1)
        self.assertEqual(P.dp_cells(*P.BIG), 1200)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("partition.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("二八九零六", beats["title"])
        for s in ("七分三份，答案是四：一一五、一二四、一三三、二二三", "七分两份，答案是三",
                  "n 不超过两百，k 在二到六之间"):
            self.assertIn(s, beats["read"])
        self.assertIn("十五种", beats["dup"])
        self.assertIn("十五种收拢成四种", beats["dup"])
        self.assertIn("第一份可以是一或二", beats["tree"])
        self.assertIn("剩六、分两份", beats["tree"])
        self.assertIn("四个叶子，四种分法", beats["tree"])
        self.assertIn("至少是它的三倍", beats["prune"])
        self.assertIn("二十个节点，十三个是死路", beats["prune"])
        self.assertIn("四百一十三万两千零九十六", beats["memo"])
        self.assertIn("四百三十多万次", beats["memo"])
        self.assertIn("一万一千八百八十八种状态", beats["memo"])
        for s in ("六分两份，三种", "四分三份，一种", "三加一，等于四"):
            self.assertIn(s, beats["split"])
        for s in ("七分三份是四，七分两份是三", "一千二百格"):
            self.assertIn(s, beats["table"])
        self.assertIn("九百七十组全部一致", beats["check"])
        self.assertIn("答案四百多万", beats["choose"])


if __name__ == "__main__":
    unittest.main()
