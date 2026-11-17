"""箭头迷阵精讲片的独立对撞：题面样例、暴力随机对拍、片中画出的每个状态/数字、旁白数字。

独立实现不调用 novdata / novarrowdata 的算法：逐格照箭头模拟 nm+1 步（鸽巢：还在场内就是绕圈）。
用法（cwd = cs101/cinematic）：python -m unittest test_novarrow
"""
import json
from pathlib import Path
import random
import sys
import unittest

import novarrowdata as D
import novdata as N

HERE = Path(__file__).resolve().parent
MV = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def escapes(g, si, sj):
    """暴力：最多走 nm+1 步。"""
    n, m = len(g), len(g[0])
    i, j = si, sj
    for _ in range(n * m + 1):
        if not (0 <= i < n and 0 <= j < m):
            return True
        di, dj = MV[g[i][j]]
        i, j = i + di, j + dj
    return not (0 <= i < n and 0 <= j < m)


def brute(g):
    return sum(escapes(g, i, j) for i in range(len(g)) for j in range(len(g[0])))


def brute_states(g):
    return [2 if escapes(g, i, j) else 3 for i in range(len(g)) for j in range(len(g[0]))]


class NovArrowFacts(unittest.TestCase):
    def test_samples(self):
        for inp, out in N.SAMPLES["t3"]:
            self.assertEqual(N.run_io(N.solve_t3, inp), out)
        self.assertEqual((D.solve(D.SAMPLE1), D.solve(D.SAMPLE2)), (2, 5))
        self.assertEqual((brute(D.SAMPLE1), brute(D.SAMPLE2)), (2, 5))

    def test_random(self):
        rnd = random.Random(31531)
        for _ in range(400):
            n, m = rnd.randint(1, 6), rnd.randint(1, 6)
            g = ["".join(rnd.choice("UDLR") for _ in range(m)) for _ in range(n)]
            self.assertEqual(D.solve(g), brute(g))
            walks, st = D.trace(g)
            self.assertEqual(st, brute_states(g))
            self.assertEqual(sorted(u for w in walks for u in w["ids"]), list(range(n * m)))   # 每格只进一次 path
            self.assertLessEqual(D.total_steps(walks), 2 * n * m)
            if n * m < 900:
                self.assertEqual(D.solve_rec(g), brute(g))                                     # 递归写法同一个算法

    def test_sample1_drawn(self):
        walks, st = D.trace(D.SAMPLE1)
        self.assertEqual(st, [2, 3, 2, 3])
        self.assertEqual([(w["start"], w["end"]) for w in walks], [((0, 0), "out"), ((0, 1), "cycle"), ((1, 0), "out")])

    def test_sample2_drawn(self):
        walks, st = D.trace(D.SAMPLE2)
        self.assertEqual(st, brute_states(D.SAMPLE2))
        self.assertEqual(st, [2, 2, 2, 2, 3, 2, 3, 3, 3])
        self.assertEqual([w["ids"] for w in walks], [[0], [1, 2, 5], [3], [4, 7], [6], [8]])
        self.assertEqual([w["end"] for w in walks], ["out", "out", "out", "cycle", "join", "join"])
        self.assertEqual([w["hit"] for w in walks[3:]], [(1, 1), (2, 1), (2, 1)])           # 撞 4、撞 7、撞 7
        self.assertEqual(sorted(set(range(9)) - {w["sid"] for w in walks}), [2, 5, 7])        # 跳过的出发点
        self.assertEqual([u for u in range(9) if st[u] == 2], [0, 1, 2, 3, 5])
        self.assertEqual((sum(len(w["path"]) for w in walks), len(walks), D.total_steps(walks)), (9, 6, 15))

    def test_graph_loop(self):
        cells, stop, out = D.route(D.SAMPLE2, (1, 1))
        self.assertEqual((cells, stop, out), ([(1, 1), (2, 1)], (1, 1), False))             # 4 → 7 → 4
        self.assertFalse(escapes(D.SAMPLE2, 1, 1))

    def test_wander(self):
        cells, stop, out = D.route(D.SPIRAL, D.SPIRAL_START)
        self.assertTrue(out)
        self.assertEqual(len(cells), 9)
        self.assertEqual(len(set(cells)), 9)
        self.assertEqual(cells[-1], (2, 0))                                                  # 从左下角出界
        self.assertEqual(stop, (2, -1))
        self.assertTrue(all(escapes(D.SPIRAL, i, j) for i in range(3) for j in range(3)))
        self.assertEqual(brute(D.SPIRAL), 9)
        diff = [(i, j) for i in range(3) for j in range(3) if D.SPIRAL[i][j] != D.SPIRAL_CYC[i][j]]
        self.assertEqual(diff, [(2, 0)])
        self.assertEqual(D.SPIRAL_CYC[2][0], "U")                                           # 左下角改成向上
        cells2, stop2, out2 = D.route(D.SPIRAL_CYC, D.SPIRAL_START)
        self.assertEqual((cells2, stop2, out2), (cells, (1, 0), False))
        self.assertEqual(brute(D.SPIRAL_CYC), 0)                                             # 九格全都出不去
        self.assertEqual(D.solve(D.SPIRAL_CYC), 0)

    def test_scale_and_recursion(self):
        self.assertEqual(D.N_MAX, 200000)
        self.assertEqual(D.BRUTE_STEPS, 200000 * 200001)                                     # 约 4×10¹⁰
        self.assertEqual(round(D.BRUTE_STEPS / 10 ** 10), 4)
        self.assertEqual(sys.getrecursionlimit(), 1000)
        self.assertEqual(D.rec_outcome(D.REC_OK), "900")
        self.assertEqual(D.rec_outcome(D.REC_BAD), "RecursionError")
        self.assertEqual(N.run_io(N.solve_t3, f"1 {D.N_MAX}\n{'R' * D.N_MAX}\n"), str(D.N_MAX))  # 循环写法不受限

    def test_code_excerpt(self):
        import inspect
        src = inspect.getsource(N.solve_t3)
        for line in D.CODE:
            self.assertIn(line.strip(), src)
        self.assertTrue(all(line.strip() for line in D.CODE))                               # 无空行，code_lines 下标不乱
        self.assertEqual(D.CODE[0], "for s in range(n * m):")
        self.assertEqual(D.CODE[-1], "        st[u] = res")
        mk = D.CODE_MARKS
        self.assertEqual({k: len(v) for k, v in mk.items()},
                         {"skip": 2, "out": 2, "cyc": 2, "join": 2, "step": 4, "fill": 2})

    def test_narration_numbers(self):
        txt = "".join(b["narration"] for b in json.loads((HERE / "novarrow.json").read_text(encoding="utf-8"))["beats"])
        self.assertIn("答案是二", txt)
        self.assertIn("二十万乘二十万，约四百亿步", txt)
        self.assertIn("格子按行编号零到八", txt)
        self.assertIn("path 是一二五", txt)
        self.assertIn("四和七都逃不出", txt)
        self.assertIn("六号向右撞上七", txt)
        self.assertIn("八号向左也撞上七", txt)
        self.assertIn("能逃的是零一二三五，答案五", txt)
        self.assertIn("九格各走一次", txt)
        self.assertIn("九格全都出不去", txt)
        self.assertIn("九个格子，六次出发，一共只看了十五格", txt)
        self.assertIn("不超过格子数的两倍", txt)
        self.assertIn("一行，二十万个向右", txt)
        self.assertIn("深度二十万", txt)
        self.assertIn("上限约一千", txt)
        self.assertIn("一行九百个还能过，两千个就报错", txt)
        self.assertEqual((D.REC_OK, D.REC_BAD), (900, 2000))
        g = D.SAMPLE2
        self.assertEqual([g[0][1], g[0][2], g[1][2]], ["R", "D", "R"])                       # 一号向右到二，向下到五，再向右出界
        self.assertEqual([g[1][1], g[2][1], g[2][0], g[2][2], g[1][0], g[0][0]], ["D", "U", "R", "L", "L", "U"])


if __name__ == "__main__":
    unittest.main()
