"""汉诺塔片数字的独立对撞：三根栈逐步模拟验证合法性，闭式 2^n - 1 对撞递推，旁白数字对撞数据层。

用法（cwd = mvp/cs101/cinematic）：python -m unittest test_hanoi
"""
import json
from pathlib import Path
import unittest

import hanoidata as H

CN_DISC = {1: "一", 2: "二", 3: "三"}


def simulate(n, ms):
    pegs = {"A": list(range(n, 0, -1)), "B": [], "C": []}
    for disc, s, d in ms:
        assert pegs[s] and pegs[s][-1] == disc, f"盘 {disc} 不在 {s} 顶上"
        assert not pegs[d] or pegs[d][-1] > disc, f"盘 {disc} 压到了更小的盘上"
        pegs[d].append(pegs[s].pop())
    return pegs


class HanoiFacts(unittest.TestCase):
    def test_moves_legal_and_complete(self):
        for n in range(1, 11):
            pegs = simulate(n, H.moves(n))
            self.assertEqual(pegs, {"A": [], "B": [], "C": list(range(n, 0, -1))})

    def test_course_output(self):
        """讲义 3.2 节程序输出的七行。"""
        got = [f"{k}:{s}->{d}" for k, s, d in H.moves(3)]
        self.assertEqual(got, ["1:A->C", "2:A->B", "1:C->B", "3:A->C", "1:B->A", "2:B->C", "1:A->C"])

    def test_tree_inorder_is_move_order(self):
        for n in range(1, 9):
            calls = H.call_tree(n)
            self.assertEqual(len(calls), 2 ** n - 1)                     # 满二叉树节点数
            by_inorder = sorted(calls, key=lambda c: c.inorder)
            self.assertEqual([(c.n, c.src, c.dst) for c in by_inorder], H.moves(n))
            self.assertTrue(all(len(c.children) in (0, 2) for c in calls))

    def test_counts(self):
        self.assertEqual([H.count(k) for k in range(1, 8)], [1, 3, 7, 15, 31, 63, 127])
        for n in range(0, 70):
            self.assertEqual(H.count(n), 2 ** n - 1)
        self.assertEqual(round(H.count(64) / 1e19, 1), 1.8)
        self.assertEqual(round(H.legend_years() / 1e8 / 10) * 10, 5850)  # 约五千八百五十亿年

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("hanoi.json").read_text(encoding="utf-8"))["beats"]}
        spoken = [f"{CN_DISC[k]}号盘，{s} 到 {d}" for k, s, d in H.moves(3)]
        at = 0
        for x in spoken:                      # 按顺序逐句往后找（同一句会出现多次）
            at = beats["run"].find(x, at)
            self.assertGreaterEqual(at, 0, f"run 旁白缺少或顺序不对：{x}")
            at += len(x)
        self.assertEqual(beats["run"].count("号盘"), 7)
        self.assertIn("一共七步", beats["run"])
        self.assertIn("一、三、七、十五、三十一、六十三、一百二十七", beats["count"])
        for s in ("一点八乘十的十九次方", "五千八百五十亿年", "二的六十四次方减一"):
            self.assertIn(s, beats["legend"])


if __name__ == "__main__":
    unittest.main()
