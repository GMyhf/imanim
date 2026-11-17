"""牌堆魔术精讲片数字的独立对撞：题面样例、枚举全部排列的暴力参照、片中每一步牌堆状态、旁白数字。

独立实现都不调用 novdata / novcarddata 的算法：正着翻牌用 list 切片模拟，答案靠枚举 n! 个排列找唯一解，
位置做法用「下一个未翻的位置跳过一个」现找，搬动次数用真实 list.insert 前后的长度累加。
用法（cwd = cs101/cinematic）：python -m unittest test_novcard
"""
from itertools import permutations
import json
from pathlib import Path
import random
import unittest

import novcarddata as C
import novdata as N

HERE = Path(__file__).resolve().parent


def reveal(order):
    """按题意正着做：顶牌移到底，再翻开顶牌。list 切片写法，与 deque 无关。"""
    a, out = list(order), []
    while a:
        a = a[1:] + a[:1]
        out.append(a.pop(0))
    return out


def brute(n):
    sols = [list(p) for p in permutations(range(1, n + 1)) if reveal(p) == list(range(1, n + 1))]
    assert len(sols) == 1
    return sols[0]


def by_positions(n):
    """位置做法的独立写法：在还没填的位置里循环，跳过一个、填下一个。"""
    deck, alive, cur = [0] * n, list(range(n)), 0
    for k in range(1, n + 1):
        cur = (cur + 1) % len(alive)
        deck[alive.pop(cur)] = k
        if alive:
            cur %= len(alive)
    return deck


def undo_states(n, swapped=False):
    """倒推每一轮后的牌堆（list 写法）；swapped=True 是两步写反（判空后）。"""
    a, rows = [], []
    for i in range(n, 0, -1):
        if swapped:
            if a:
                a = a[-1:] + a[:-1]
            a = [i] + a
        else:
            a = [i] + a
            put = list(a)
            a = a[-1:] + a[:-1]
            rows.append((put, list(a)))
    return rows if not swapped else a


class NovCardFacts(unittest.TestCase):
    def test_samples(self):
        for n, out in ((4, "4 1 3 2"), (5, "3 1 5 2 4")):
            self.assertIn((f"{n}\n", out), N.SAMPLES["t4"])
            self.assertEqual(N.run_io(N.solve_t4, f"{n}\n"), out)
            self.assertEqual(" ".join(map(str, brute(n))), out)

    def test_brute_random(self):
        for n in range(1, 9):
            self.assertEqual(C.answer(n), brute(n))
            self.assertEqual(by_positions(n), brute(n))
        rnd = random.Random(31532)
        for _ in range(30):
            n = rnd.randint(9, 400)
            ans = C.answer(n)
            self.assertEqual(reveal(ans), list(range(1, n + 1)))
            self.assertEqual(C.position_trace(n)[1], ans)
            self.assertEqual(by_positions(n), ans)

    def test_forward_rounds(self):
        """样例 1 正着表演：移到底的牌 4 3 4 4，翻出 1 2 3 4。"""
        rounds = C.forward_rounds([4, 1, 3, 2])
        self.assertEqual([r["moved"] for r in rounds], [4, 3, 4, 4])
        self.assertEqual([r["shown"] for r in rounds], reveal([4, 1, 3, 2]))
        self.assertEqual([r["shown"] for r in rounds], [1, 2, 3, 4])
        self.assertEqual([r["after"] for r in rounds], [[3, 2, 4], [4, 3], [4], []])

    def test_reverse_steps(self):
        """样例 2 每一轮的「放牌后」「移底牌后」，以及撤销小演示用到的样例 1 最后一轮。"""
        for n in (4, 5):
            st = N.cards_reverse_trace(n)
            self.assertEqual([(s["put"], s["moved"]) for s in st], undo_states(n))
        st = N.cards_reverse_trace(5)
        self.assertEqual([s["moved"] for s in st], [[5], [5, 4], [4, 3, 5], [5, 2, 4, 3], [3, 1, 5, 2, 4]])
        self.assertEqual([s["put"] for s in st], [[5], [4, 5], [3, 5, 4], [2, 4, 3, 5], [1, 5, 2, 4, 3]])
        last = N.cards_reverse_trace(4)[-1]
        self.assertEqual((last["put"], last["moved"]), ([1, 3, 2, 4], [4, 1, 3, 2]))

    def test_positions(self):
        steps, deck = C.position_trace(5)
        self.assertEqual([s["pos"] for s in steps], [1, 3, 0, 4, 2])
        self.assertEqual(deck, [3, 1, 5, 2, 4])
        self.assertEqual(steps[0]["rotated"], [1, 2, 3, 4, 0])

    def test_swapped_bug(self):
        with self.assertRaises(IndexError):
            C.swapped_naive(4)
        for n in range(1, 9):
            self.assertEqual(C.swapped_guarded(n), undo_states(n, swapped=True))
        self.assertEqual(C.swapped_guarded(4), [1, 3, 2, 4])
        self.assertEqual(reveal([1, 3, 2, 4]), [3, 4, 2, 1])
        self.assertEqual(C.forward_rounds([1, 3, 2, 4])[-1]["shown"], 1)
        self.assertNotEqual(C.swapped_guarded(4), brute(4))
        self.assertEqual(brute(4).index(1), 1)                         # 正确答案里牌 1 在第二张

    def test_costs(self):
        for n in range(1, 30):
            lst, moves = C.list_insert_moves(n)
            self.assertEqual(lst, C.answer(n))
            self.assertEqual(moves, n * (n - 1))
            self.assertEqual(C.list_moves_count(n), moves)
        n = 2 * 10 ** 5
        self.assertEqual(C.N_MAX, n)
        self.assertEqual(C.LIST_MOVES_BIG, n * (n - 1))
        self.assertEqual(round(C.LIST_MOVES_BIG / 10 ** 10), 4)          # 约四百亿
        self.assertEqual(C.DEQUE_OPS_BIG, 600000)                        # 六十万
        self.assertEqual(C.CODE.count("\n\n"), 0)                         # Code 字符串不能有空行

    def test_code_is_handout(self):
        """片中展示的代码就是 novdata.solve_t4 的函数体（讲义原样）。"""
        import inspect
        src = inspect.getsource(N.solve_t4)
        for line in C.CODE.splitlines()[3:6]:
            self.assertIn(line.strip(), src)

    def test_narration_numbers(self):
        txt = "".join(b["narration"] for b in json.loads((HERE / "novcard.json").read_text(encoding="utf-8"))["beats"])
        cn = "零一二三四五"
        word = lambda xs: "".join(cn[x] for x in xs)                     # noqa: E731
        self.assertIn(f"答案是{word(brute(4))}", txt)
        moved = [r["moved"] for r in C.forward_rounds(brute(4))]
        for m, s in zip(moved[:3], "一二三"):
            self.assertIn(f"{cn[m]}移到底，翻开{s}", txt)
        self.assertIn("只剩一张四", txt)
        for put, mv in undo_states(5)[1:]:
            self.assertIn(word(mv), txt)
            self.assertIn(word(put), txt)
        self.assertIn("变成三一五二四", txt)
        steps, _ = C.position_trace(5)
        self.assertIn(f"第一次弹出{cn[steps[0]['pos']]}号位，填牌一", txt)
        self.assertIn(f"接着弹出{cn[steps[1]['pos']]}号位，填二", txt)
        self.assertIn(f"然后{cn[steps[2]['pos']]}号位填三，{cn[steps[3]['pos']]}号位填四，{cn[steps[4]['pos']]}号位填五", txt)
        self.assertIn(f"却输出{word(C.swapped_guarded(4))}", txt)
        self.assertIn(f"翻出来是{word(reveal(C.swapped_guarded(4)))}", txt)
        self.assertIn("二十万", txt)
        self.assertIn("六十万次", txt)
        self.assertIn("四百亿次", txt)


if __name__ == "__main__":
    unittest.main()
