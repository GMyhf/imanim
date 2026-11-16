"""矩阵片数字的独立对撞：讲义样例输出、不加保护圈的越界判断写法、numpy 式下标旋转、
题库样例代码（M18106 判越界版）与旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_matrix
"""
import json
from pathlib import Path
import random
import unittest

import matrixdata as S


def neighbor_sum_bounds(a, dirs):
    """讲义「没有保护圈」的写法：每次判越界。"""
    m, n = len(a), len(a[0])
    res = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < m and 0 <= nj < n:
                    res[i][j] += a[ni][nj]
    return res


def life_ref(cells):
    n, m = len(cells), len(cells[0])
    out = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            c = sum(cells[i + di][j + dj] for di in (-1, 0, 1) for dj in (-1, 0, 1)
                    if (di, dj) != (0, 0) and 0 <= i + di < n and 0 <= j + dj < m)
            out[i][j] = 1 if (c == 3 or (cells[i][j] and c == 2)) else 0
    return out


def spiral_ref(n):
    """题库 18106 样例代码（判越界 + 判已填）。"""
    matrix = [[0] * n for _ in range(n)]
    ptr, p = (0, 0), 0
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    for i in range(1, n ** 2 + 1):
        matrix[ptr[0]][ptr[1]] = i
        nptr = (ptr[0] + directions[p][0], ptr[1] + directions[p][1])
        if nptr[0] >= n or nptr[0] < 0 or nptr[1] >= n or nptr[1] < 0 or matrix[nptr[0]][nptr[1]] != 0:
            p = (p + 1) % 4
            nptr = (ptr[0] + directions[p][0], ptr[1] + directions[p][1])
        ptr = nptr
    return matrix


class MatrixFacts(unittest.TestCase):
    def test_trap(self):
        bad, good, rows = S.alias_trap()
        self.assertEqual(rows, 1)
        self.assertEqual([r[0] for r in bad], [9, 9, 9])
        self.assertEqual([r[0] for r in good], [9, 0, 0])

    def test_padding(self):
        self.assertEqual(S.neighbor_sum(), [[6, 9, 8], [13, 20, 17], [12, 21, 14]])   # 讲义输出
        rng = random.Random(5)
        for _ in range(100):
            a = [[rng.randint(-9, 9) for _ in range(rng.randint(1, 6))]]
            a += [[rng.randint(-9, 9) for _ in a[0]] for _ in range(rng.randint(0, 5))]
            self.assertEqual(S.neighbor_sum(a), neighbor_sum_bounds(a, S.DIRS))
        self.assertEqual(S.neighbor_terms(0, 0), [0, 4, 0, 2])
        self.assertEqual(S.neighbor_terms(1, 1), [2, 8, 4, 6])
        self.assertEqual(len(S.DIRS8), 8)

    def test_life(self):
        out, cnt = S.life_step()
        self.assertEqual(out, S.LIFE_OUT)
        self.assertEqual(out, life_ref(S.LIFE))
        self.assertEqual((S.LIFE[1][1], cnt[1][1], out[1][1]), (1, 4, 0))      # 第二行第二列：四个活邻居，死去
        self.assertEqual((S.LIFE[0][1], cnt[0][1], out[0][1]), (0, 3, 1))      # 第一行第二列：三个活邻居，复活
        self.assertNotEqual(S.life_inplace_wrong(), S.LIFE_OUT)
        rng = random.Random(7)
        for _ in range(100):
            n, m = rng.randint(1, 6), rng.randint(1, 6)
            cells = [[rng.randint(0, 1) for _ in range(m)] for _ in range(n)]
            self.assertEqual(S.life_step(cells)[0], life_ref(cells))

    def test_rotate(self):
        self.assertEqual(S.transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])   # 讲义输出
        self.assertEqual(S.rotate_cw([[1, 2], [3, 4]]), [[3, 1], [4, 2]])
        self.assertEqual(S.rotate_ccw([[1, 2], [3, 4]]), [[2, 4], [1, 3]])
        a = S.A
        n = len(a)
        self.assertEqual(S.rotate_cw(a), [[a[n - 1 - j][i] for j in range(n)] for i in range(n)])
        self.assertEqual(S.rotate_ccw(a), [[a[j][n - 1 - i] for j in range(n)] for i in range(n)])
        self.assertEqual(S.rotate_cw(a)[0], [7, 4, 1])
        self.assertEqual(S.rotate_ccw(S.rotate_cw(a)), a)

    def test_spiral(self):
        g, turns, path = S.spiral()
        self.assertEqual(g, [[1, 2, 3, 4], [12, 13, 14, 5], [11, 16, 15, 6], [10, 9, 8, 7]])
        self.assertEqual(turns[:4], [4, 7, 10, 12])
        self.assertEqual(path[-1], (2, 1))                 # 十六在第三行第二列
        self.assertEqual(S.spiral(3)[0], [[1, 2, 3], [8, 9, 4], [7, 6, 5]])   # 题面样例
        for n in range(1, 21):
            self.assertEqual(S.spiral(n)[0], spiral_ref(n))

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("matrix.json").read_text(encoding="utf-8"))["beats"])
        for s in ("邻居是零、四、零、二，和是六", "邻居是二、八、四、六，和是二十", "有四个活邻居，太挤，死去",
                  "恰有三个活邻居，复活", "第一行变成七、四、一", "填到四撞墙", "填到七，向左", "填到十，向上",
                  "填到十二", "最后一个数十六，落在第三行第二列", "一二五六零", "一八一零六"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
