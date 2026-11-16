"""马走日与数湖泊片数字的独立对撞：讲义输出、简单路径枚举、BFS 连通块、事件回放、旁白数字。

独立实现不调用 knightdata 的递归：路径用 frozenset 枚举，连通块用 BFS。
用法（cwd = cs101/cinematic）：python -m unittest test_knight
"""
from collections import deque
import json
from pathlib import Path
import random
import unittest

import knightdata as K

JUMPS = [(a, b) for a in (-2, -1, 1, 2) for b in (-2, -1, 1, 2) if abs(a) != abs(b)]
KING = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]


def simple_paths(start, cells, moves):
    """从 start 出发、只走 cells 里的格子、不重复的全部路径（含只有起点的那条），按长度计数。"""
    by_len = {}

    def go(p, seen):
        by_len[len(seen)] = by_len.get(len(seen), 0) + 1
        for dx, dy in moves:
            q = (p[0] + dx, p[1] + dy)
            if q in cells and q not in seen:
                go(q, seen | {q})
    go(start, frozenset([start]))
    return by_len


def board(n, m):
    return {(i, j) for i in range(n) for j in range(m)}


def component(start, cells, moves):
    seen, dq = {start}, deque([start])
    while dq:
        p = dq.popleft()
        for dx, dy in moves:
            q = (p[0] + dx, p[1] + dy)
            if q in cells and q not in seen:
                seen.add(q)
                dq.append(q)
    return seen


def water_cells(grid):
    return {(i, j) for i, row in enumerate(grid) for j, ch in enumerate(row) if ch == 'W'}


def lakes_bfs(grid):
    left, cnt = water_cells(grid), 0
    while left:
        left -= component(min(left), left, KING)
        cnt += 1
    return cnt


def undo_calls(grid):
    """撤销版：外层每遇到一格水（之前的起点已标记、其余都还原成水），从它出发枚举全部简单路径。"""
    w = sorted(water_cells(grid))
    per = []
    for k, s in enumerate(w):
        per.append(sum(simple_paths(s, set(w[k:]), KING).values()))
    return per


class KnightFacts(unittest.TestCase):
    def test_course_output(self):
        self.assertEqual(K.knight_tours(5, 4, 0, 0), 32)
        self.assertEqual(K.knight_tours(3, 3, 0, 0), 0)
        self.assertEqual(K.count_lakes(K.SAMPLE), 3)
        self.assertEqual(sorted(K.KNIGHT), sorted(JUMPS))

    def test_tours_against_paths(self):
        for n, m, sx, sy in [(5, 4, 0, 0), (5, 4, 1, 0), (3, 4, 0, 0), (4, 4, 0, 0), (3, 3, 0, 0)]:
            by_len = simple_paths((sx, sy), board(n, m), JUMPS)
            cnt, calls, ev, tours = K.knight_trace(n, m, sx, sy)
            self.assertEqual(cnt, K.knight_tours(n, m, sx, sy))
            self.assertEqual(cnt, by_len.get(n * m, 0))
            self.assertEqual(calls, sum(by_len.values()))          # 每个不重复的前缀就是一次调用
            self.assertEqual(len(tours), cnt)
            for t in tours:
                self.assertEqual(len(set(t)), n * m)
                for a, b in zip(t, t[1:]):
                    self.assertIn((b[0] - a[0], b[1] - a[1]), JUMPS)

    def test_tour_story(self):
        cnt, calls, ev, tours = K.knight_trace(*K.BOARD)
        self.assertEqual((cnt, calls), (32, 35661))
        # 第一次回退发生在第 14 步；第一条走法出现在第 1411 次调用
        first_in = [e for e in ev[:ev.index(next(e for e in ev if e[0] == "ret"))] if e[0] == "in"]
        self.assertEqual(first_in[-1][3], 14)
        k = 0
        for e in ev:
            k += e[0] == "in"
            if e[0] == "tour":
                break
        self.assertEqual(k, 1411)
        # 独立：按 KNIGHT 顺序先序枚举路径，第几个是满的
        order = []

        def go(path, seen):
            order.append(len(path))
            x, y = path[-1]
            for dx, dy in K.KNIGHT:
                q = (x + dx, y + dy)
                if q in board(5, 4) and q not in seen:
                    go(path + [q], seen | {q})
        go([(0, 0)], {(0, 0)})
        self.assertEqual(order.index(20) + 1, 1411)
        self.assertEqual(len(order), 35661)
        snaps = K.snapshots(*K.BOARD)
        self.assertEqual(len(snaps), 35661)
        self.assertEqual(sum(1 for s in snaps if len(s) == 20), 32)

    def test_forget_undo(self):
        cnt, calls, ev, tours = K.knight_trace(*K.BOARD, undo=False)
        self.assertEqual((cnt, calls), (0, 20))
        self.assertEqual(K.max_step(*K.BOARD, undo=False), 14)
        self.assertEqual(sum(1 for e in ev if e[0] == "out"), 0)
        # 前 14 步与正确版的第一次下探相同
        good = [e for e in K.knight_trace(*K.BOARD)[2] if e[0] == "in"][:14]
        self.assertEqual([e for e in ev if e[0] == "in"][:14], good)
        # 忘了撤销：每格最多进一次 = 起点所在的马步连通块；答案只能是 0 或 1
        for n in range(1, 6):
            for m in range(1, 6):
                for sx in range(n):
                    for sy in range(m):
                        c, k, _, _ = K.knight_trace(n, m, sx, sy, undo=False)
                        self.assertEqual(k, len(component((sx, sy), board(n, m), JUMPS)))
                        self.assertIn(c, (0, 1))
                        if n * m <= 16:
                            self.assertLessEqual(c, K.knight_tours(n, m, sx, sy))

    def test_lakes(self):
        for g in (K.LAKE, K.SAMPLE):
            cnt, calls, ev, lakes = K.lake_trace(g)
            self.assertEqual(cnt, lakes_bfs(g))
            self.assertEqual(cnt, K.count_lakes(g))
            self.assertEqual(calls, K.water(g))                   # 每格水只进一次
            self.assertEqual(set().union(*lakes), water_cells(g))
        self.assertEqual(K.lake_trace(K.LAKE)[:2], (3, 11))
        self.assertEqual(max(len(s) for s in K.lake_trace(K.LAKE)[3]), 8)
        self.assertEqual(K.lake_trace(K.SAMPLE)[:2], (3, 31))
        rnd = random.Random(7)
        for _ in range(200):
            g = ["".join(rnd.choice("W..") for _ in range(6)) for _ in range(5)]
            self.assertEqual(K.lake_trace(g)[0], lakes_bfs(g))
            self.assertEqual(K.count_lakes(g), lakes_bfs(g))

    def test_lakes_with_undo(self):
        for g, total, first in ((K.LAKE, 979, 608), (K.SAMPLE, 18811, None)):
            cnt, calls, ev, _ = K.lake_trace(g, undo=True)
            per = undo_calls(g)
            self.assertEqual(cnt, K.water(g))                     # 每格水都被当成一个新湖
            self.assertEqual(calls, sum(per))
            self.assertEqual(calls, total)
            if first:
                self.assertEqual(per[0], first)
        self.assertEqual(K.water(K.LAKE), 11)
        self.assertEqual(K.water(K.SAMPLE), 31)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("knight.json").read_text(encoding="utf-8"))["beats"]}
        n, m, _, _ = K.BOARD
        self.assertEqual((n, m), (5, 4))
        self.assertIn("五行四列", beats["knight"]); self.assertIn("全部二十格", beats["knight"])
        self.assertIn("走满二十步", beats["kcode"])
        self.assertIn("第十四步", beats["ktour"])
        self.assertIn("第一千四百一十一次调用", beats["ktour"])
        self.assertIn("三万五千六百六十一次", beats["ktour"]); self.assertIn("三十二种走法", beats["ktour"])
        self.assertIn("第十四步", beats["kforget"]); self.assertIn("二十次调用", beats["kforget"])
        self.assertIn("答案是零", beats["kforget"])
        self.assertIn("五行四列", beats["lake"])
        self.assertIn("湖有八格", beats["lwalk"])
        self.assertIn("三个湖，十一格水，正好十一次调用", beats["lwalk"])
        self.assertIn("六百零八次", beats["lwrong"]); self.assertIn("十一个湖，调用九百七十九次", beats["lwrong"])
        self.assertIn("三个湖、三十一次调用", beats["lwrong"])
        self.assertIn("三十一个湖，调用一万八千八百一十一次", beats["lwrong"])
        self.assertEqual(len(K.LAKE), 5); self.assertEqual(len(K.LAKE[0]), 4)


if __name__ == "__main__":
    unittest.main()
