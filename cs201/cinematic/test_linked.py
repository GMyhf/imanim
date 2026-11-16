"""链表片数字的独立对撞：Python 列表反转/排序合并、按位置数中点、访问集合判圈，以及讲义里的落点表与旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_linked
"""
import json
import random
import unittest
from pathlib import Path

import linkeddata as D

S = D.Solution()


def seen_cycle(head):
    """独立 oracle：记访问过的结点，第一个重复访问的就是环入口。"""
    seen = set()
    while head:
        if id(head) in seen:
            return head
        seen.add(id(head))
        head = head.next
    return None


class LinkedTest(unittest.TestCase):
    def test_reverse_random(self):
        for n in range(0, 12):
            vals = [random.randint(0, 9) for _ in range(n)]
            head, _ = D.build(vals)
            self.assertEqual(D.to_list(S.reverseList(head)), vals[::-1])

    def test_reverse_trace(self):
        out, rounds = D.reverse_trace()
        self.assertEqual(out, [5, 4, 3, 2, 1])
        self.assertEqual([r["flip"] for r in rounds], [0, 1, 2, 3, 4])   # 每轮只改一根箭头
        self.assertEqual(rounds[-1]["curr"], -1)                          # curr 走到空
        self.assertEqual(D.REV[rounds[-1]["prev"]], 5)                    # 前驱停在五上

    def test_merge(self):
        for _ in range(200):
            a = sorted(random.randint(0, 9) for _ in range(random.randint(0, 6)))
            b = sorted(random.randint(0, 9) for _ in range(random.randint(0, 6)))
            got = S.mergeTwoLists(D.build(a)[0], D.build(b)[0])
            self.assertEqual(D.to_list(got), sorted(a + b))
        ev = D.merge_trace()
        self.assertEqual(ev[-1], ("rest", "B", 2))                        # 第一条走完时第二条剩一个四
        self.assertEqual(D.MERGE_B[2], 4)
        self.assertEqual(ev[0][1], "A")                                    # 相等先取第一条
        # 插桩版接上的顺序与讲义原版的结果一致
        order = [e[3] for e in ev if e[0] == "take"] + D.MERGE_B[2:]
        self.assertEqual(order, D.to_list(S.mergeTwoLists(D.build(D.MERGE_A)[0], D.build(D.MERGE_B)[0])))

    def test_middle_table(self):
        # 讲义表：n=1..6 时 slow 停在第 1 2 2 3 3 4 个
        want = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4}
        for n, k in want.items():
            head, nodes = D.build(list(range(1, n + 1)))
            self.assertIs(S.middle(head), nodes[k - 1])
            self.assertEqual(D.middle_trace(n)[-1][0], k)
            self.assertEqual(k, n // 2 + 1)
        self.assertEqual(D.middle_trace(6)[-1][1], None)                  # 偶数：fast 跑出链表

    def test_cycle_random(self):
        for _ in range(300):
            n = random.randint(1, 15)
            at = random.choice([None] + list(range(n)))
            head, nodes = D.build(list(range(n)), at)
            want = seen_cycle(head)
            self.assertEqual(S.hasCycle(head), want is not None)
            self.assertIs(S.detectCycle(head), want)

    def test_floyd_example(self):
        F = D.floyd_trace()
        self.assertEqual(len(D.CYC_VALS), 10)
        self.assertEqual((F["a"], F["L"]), (3, 7))                        # 环外三个，环长七
        self.assertEqual(F["slow_steps"], 7)                              # 慢指针第七步相遇
        self.assertEqual((F["a"] + F["b"]) % F["L"], 0)                   # a + b 是环长的倍数
        self.assertEqual(len(F["phase2"]) - 1, F["a"])                    # 再走三步
        self.assertEqual(D.CYC_VALS[F["entry"]], 4)                       # 在第四个结点碰头
        head, nodes = D.build(D.CYC_VALS, D.CYC_AT)
        self.assertIs(seen_cycle(head), nodes[F["entry"]])
        # 追及距离每步减一
        gaps = [(s - f) % F["L"] for s, f in F["phase1"] if s >= F["a"]]
        self.assertEqual(gaps, list(range(gaps[0], -1, -1)))

    def test_narration(self):
        nar = "".join(b["narration"] for b in
                      json.loads((Path(__file__).parent / "linked.json").read_text(encoding="utf-8"))["beats"])
        for s in ("一条是一二四，一条是一三四", "还剩一个四", "五个结点时，慢指针停在第三个", "六个结点时，停在第四个",
                  "十个结点，环外三个，环长七", "第七步", "环外长度是三，走三步", "第四个结点"):
            self.assertIn(s, nar)


if __name__ == "__main__":
    unittest.main()
