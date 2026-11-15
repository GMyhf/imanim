"""八皇后片数字的独立对撞：讲义输出、暴力枚举全排列检验、插桩事件回放、节点数、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_queens
"""
from itertools import permutations, product
import json
from pathlib import Path
import unittest

import queensdata as Q


def brute(n):
    """不用回溯：枚举每行的列号排列，逐对检查对角线。"""
    out = []
    for p in permutations(range(n)):
        if all(abs(p[i] - p[j]) != j - i for i in range(n) for j in range(i + 1, n)):
            out.append(tuple(c + 1 for c in p))
    return out


class QueensFacts(unittest.TestCase):
    def test_course_output(self):
        sols = Q.solve_queens(8)
        self.assertEqual(len(sols), 92)
        self.assertEqual("".join(map(str, sols[0])), "15863724")
        self.assertEqual("".join(map(str, sols[91])), "84136275")

    def test_against_brute(self):
        for n in range(1, 9):
            self.assertEqual(Q.solve_queens(n), brute(n))
            self.assertEqual(Q.trace(n)[0], Q.solve_queens(n))

    def test_trace_replay(self):
        """按事件回放棋盘：放下时不冲突、撤销与放下一一配对、解与讲义一致。"""
        for n in (4, 5, 6):
            res, ev, calls = Q.trace(n)
            board, sols = {}, []
            for e in ev:
                if e[0] == "place":
                    r, c = e[1], e[2]
                    self.assertNotIn(r, board)
                    for rr, cc in board.items():
                        self.assertTrue(cc != c and rr - cc != r - c and rr + cc != r + c)
                    board[r] = c
                elif e[0] == "remove":
                    self.assertEqual(board.pop(e[1]), e[2])
                elif e[0] == "conflict":
                    r, c = e[1], e[2]
                    self.assertTrue(any(cc == c or rr - cc == r - c or rr + cc == r + c for rr, cc in board.items()))
                else:
                    sols.append(tuple(board[r] + 1 for r in range(n)))
            self.assertEqual(board, {})
            self.assertEqual(sols, res)

    def test_four_queens_story(self):
        res, ev, calls = Q.trace(4)
        self.assertEqual(res, [(2, 4, 1, 3), (3, 1, 4, 2)])
        self.assertEqual(len(calls), 17)
        self.assertEqual(sum(1 for e in ev if e[0] == "place"), 16)
        self.assertEqual(sum(1 for e in ev if e[0] == "conflict"), 44)
        # 旁白：第一行放第一列；第二行前两格冲突，放第三列；第三行无处可放，撤销
        head = [e[:3] for e in ev[:9]]
        self.assertEqual(head, [("place", 0, 0), ("conflict", 1, 0), ("conflict", 1, 1), ("place", 1, 2),
                                ("conflict", 2, 0), ("conflict", 2, 1), ("conflict", 2, 2), ("conflict", 2, 3),
                                ("remove", 1, 2)])

    def test_counts(self):
        self.assertEqual(Q.naive_nodes(8), 19173961)
        self.assertEqual(Q.perm_nodes(8), 109601)
        self.assertEqual(Q.pruned_nodes(8), 2057)
        # 独立核对剪枝后各层节点数：第 k 层 = 前 k 行合法的部分摆法个数（前 6 层暴力枚举）
        levels = {}
        for c in Q.trace(8)[2]:
            levels[c.row] = levels.get(c.row, 0) + 1
        for k in range(6):
            cnt = sum(1 for p in product(range(8), repeat=k) if len(set(p)) == k and
                      all(abs(p[i] - p[j]) != j - i for i in range(k) for j in range(i + 1, k)))
            self.assertEqual(levels[k], cnt)

    def test_diag_constant(self):
        for n in (3, 8):
            for r, c in product(range(n), repeat=2):
                for i, j in Q.attacked(n, r, c):
                    self.assertTrue(i == r or j == c or i - j == r - c or i + j == r + c)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("queens.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("一千九百多万", beats["count"]); self.assertTrue(19e6 <= Q.naive_nodes(8) < 20e6)
        self.assertIn("十万多个", beats["count"]); self.assertTrue(1e5 <= Q.perm_nodes(8) < 2e5)
        self.assertIn("两千零五十七", beats["count"])
        self.assertIn("一共十七个", beats["tree"])
        self.assertIn("一共放下十六次，找到两个解", beats["walk"])
        self.assertIn("九十二个解", beats["all"])
        self.assertIn("一五八六三七二四", beats["all"]); self.assertIn("八四一三六二七五", beats["all"])
        self.assertIn("上千万步", beats["title"]); self.assertIn("两千来步", beats["title"])


if __name__ == "__main__":
    unittest.main()
