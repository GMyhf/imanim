"""熄灯问题片数字的独立对撞：样例输出、GF(2) 高斯消元独立求解、小盘面整表暴力对拍、插桩回放、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_lights
"""
from itertools import product
import json
from pathlib import Path
import random
import unittest

import lightsdata as L


def apply(light, press):
    """按按法表一次性算出最终盘面：每盏灯翻转次数 = 自己和四邻里按下的个数。"""
    rows, cols = len(light), len(light[0])
    return [[(light[r][c] + sum(press[i][j] for i, j in L.neighbors(r, c, rows, cols))) % 2
             for c in range(cols)] for r in range(rows)]


def gauss_solve(light, rows=L.R, cols=L.C):
    """不用枚举：把 30 个按钮当未知数，在 GF(2) 上解线性方程组 A·x = light。返回全部解。"""
    n = rows * cols
    eq = []
    for r in range(rows):
        for c in range(cols):
            row = 0
            for i, j in L.neighbors(r, c, rows, cols):   # 灯 (r,c) 受按钮 (i,j) 影响（关系对称）
                row |= 1 << (i * cols + j)
            eq.append([row, light[r][c]])
    piv_cols, rank = [], 0
    for bit in range(n):
        k = next((k for k in range(rank, n) if eq[k][0] >> bit & 1), None)
        if k is None:
            continue
        eq[rank], eq[k] = eq[k], eq[rank]
        for t in range(n):
            if t != rank and eq[t][0] >> bit & 1:
                eq[t][0] ^= eq[rank][0]
                eq[t][1] ^= eq[rank][1]
        piv_cols.append(bit)
        rank += 1
    if any(e[0] == 0 and e[1] for e in eq):
        return []
    free = [b for b in range(n) if b not in piv_cols]
    sols = []
    for fv in product((0, 1), repeat=len(free)):
        x = dict(zip(free, fv))
        for k in range(rank - 1, -1, -1):
            b = piv_cols[k]
            v = eq[k][1]
            for t in range(n):
                if t != b and eq[k][0] >> t & 1:
                    v ^= x.get(t, 0)
            x[b] = v
        sols.append([[x[r * cols + c] for c in range(cols)] for r in range(rows)])
    return sols


def brute(light):
    """整张按法表全部枚举（只用于小盘面）。"""
    rows, cols = len(light), len(light[0])
    out = []
    for bitsv in product((0, 1), repeat=rows * cols):
        press = [list(bitsv[r * cols:(r + 1) * cols]) for r in range(rows)]
        if not any(map(any, apply(light, press))):
            out.append(press)
    return out


class LightsFacts(unittest.TestCase):
    def test_sample_output(self):
        for p, want in zip(L.SAMPLE, L.SAMPLE_OUT):
            got = L.solve(p)
            self.assertEqual(got, want)
            self.assertFalse(any(map(any, apply(p, got))))

    def test_against_gauss(self):
        """随机 300 个局面：枚举第一行的结果 == 高斯消元的唯一解。"""
        rnd = random.Random(2811)
        for _ in range(300):
            p = [[rnd.randint(0, 1) for _ in range(6)] for _ in range(5)]
            g = gauss_solve(p)
            self.assertEqual(len(g), 1)
            self.assertEqual(L.solve(p), g[0])
            self.assertEqual(len(L.solve_general(p)), 1)

    def test_small_boards_brute(self):
        """小盘面（含不满秩、可能无解的）：枚举第一行找到的解集 == 整表暴力的解集。"""
        rnd = random.Random(1)
        for rows, cols in ((2, 2), (2, 3), (3, 3), (3, 4), (4, 3), (4, 4)):
            for _ in range(15):
                p = [[rnd.randint(0, 1) for _ in range(cols)] for _ in range(rows)]
                via_row = sorted(L.chase(p, m)[0] for m in L.solve_general(p))
                self.assertEqual(via_row, sorted(brute(p)))

    def test_chase_replay(self):
        """插桩快照逐步回放与 flip 一致；第 r≥1 行按下的位置恰是上一行当时还亮的灯。"""
        for m in range(64):
            press, steps, final = L.chase(L.P1, m)
            g = [row[:] for row in L.P1]
            for r, c, snap in steps:
                if r > 0:
                    self.assertEqual(g[r - 1][c], 1)
                L.flip(g, r, c)
                self.assertEqual(g, snap)
            self.assertEqual(g, final)
            self.assertEqual(final, apply(L.P1, press))
            for r in range(L.R - 1):
                self.assertFalse(any(final[r]))       # 推完以后前四行一定全灭

    def test_numbers(self):
        self.assertEqual(L.gf2_rank(), 30)
        self.assertEqual((L.N_TRIED, L.WIN_MASK, L.bits(L.WIN_MASK), L.LEFT0), (42, 41, [1, 0, 1, 0, 0, 1], 4))
        self.assertEqual((L.BRUTE, L.SMART, L.OPS, L.SPEEDUP), (1073741824, 64, 1920, 16777216))
        self.assertEqual(len(L.neighbors(0, 0)), 3)
        self.assertEqual(len(L.neighbors(0, 2)), 4)
        self.assertEqual(len(L.neighbors(2, 2)), 5)

    def test_narration_numbers(self):
        s = json.loads((Path(__file__).parent / "lights.json").read_text(encoding="utf-8"))
        nar = {b["id"]: b["narration"] for b in s["beats"]}
        self.assertIn("六十四种", nar["title"])
        self.assertIn("只影响三盏", nar["read"])
        self.assertIn("边上的影响四盏", nar["read"])
        self.assertIn("二的三十次方", nar["model"])
        self.assertIn(f"还剩{'四'}盏", nar["walk"].replace(" ", ""))
        self.assertIn("第四十二种", nar["walk"])
        self.assertIn("一零一零零一", nar["walk"])
        self.assertIn("两千次", nar["cost"])
        self.assertIn("一千六百多万倍", nar["cost"])
        self.assertIn("恰好只有一种", nar["cost"])


if __name__ == "__main__":
    unittest.main()
