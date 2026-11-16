"""熄灯问题例题精讲片的数据层：参考解（枚举第一行）原样 + 插桩，给画面和旁白提供每一个数字。

题目：OpenJudge 02811 熄灯问题（2026fall 每日选作 11-02；往年机考 cs10107 Mock Exam No.2）。
5 行 6 列的灯，1 亮 0 灭；按一个按钮，它和上下左右相邻的灯都翻转。输出一张按法表让所有灯熄灭。
约定：第一行按法用 6 位二进制数 mask 表示，第 0 列是最高位，所以 mask 从 0 数到 63 就是按字典序试第一行。
"""
from __future__ import annotations

R, C = 5, 6

# 题目样例（两组）与样例输出
SAMPLE = [
    [[0, 1, 1, 0, 1, 0],
     [1, 0, 0, 1, 1, 1],
     [0, 0, 1, 0, 0, 1],
     [1, 0, 0, 1, 0, 1],
     [0, 1, 1, 1, 0, 0]],
    [[0, 0, 1, 0, 1, 0],
     [1, 0, 1, 0, 1, 1],
     [0, 0, 1, 0, 1, 1],
     [1, 0, 1, 1, 0, 0],
     [0, 1, 0, 1, 0, 0]],
]
SAMPLE_OUT = [
    [[1, 0, 1, 0, 0, 1],
     [1, 1, 0, 1, 0, 1],
     [0, 0, 1, 0, 1, 1],
     [1, 0, 0, 1, 0, 0],
     [0, 1, 0, 0, 0, 0]],
    [[1, 0, 0, 1, 1, 1],
     [1, 1, 0, 0, 0, 0],
     [0, 0, 0, 1, 0, 0],
     [1, 1, 0, 1, 0, 1],
     [1, 0, 1, 1, 0, 1]],
]


def neighbors(r, c, rows=R, cols=C):
    """按 (r, c) 会翻转的格子：自己和上下左右，越界的不算。"""
    return [(i, j) for i, j in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= i < rows and 0 <= j < cols]


def flip(g, r, c):
    for i, j in neighbors(r, c, len(g), len(g[0])):
        g[i][j] ^= 1


def solve(light):
    """参考解原样（片中代码块就是这一段）：枚举第一行 2^6 种按法，下面各行被上一行剩下的灯逼出来。"""
    for mask in range(64):              # 第一行：2^6 种按法
        g = [row[:] for row in light]
        press = [[0] * 6 for _ in range(5)]
        for r in range(5):
            for c in range(6):
                p = mask >> (5 - c) & 1 if r == 0 else g[r - 1][c]
                if p:
                    press[r][c] = 1
                    flip(g, r, c)        # 自己和上下左右
        if not any(g[4]):              # 最后一行全灭才算成功
            return press
    return None


def chase(light, mask, rows=None, cols=None):
    """插桩：给定第一行按法，逐格推下去。返回 (press, 每次按下后的盘面快照列表, 最终盘面)。

    快照：[(r, c, 盘面拷贝)]，只记真正按下的格子，按 r、c 顺序。
    """
    rows, cols = rows or len(light), cols or len(light[0])
    g = [row[:] for row in light]
    press = [[0] * cols for _ in range(rows)]
    steps = []
    for r in range(rows):
        for c in range(cols):
            p = mask >> (cols - 1 - c) & 1 if r == 0 else g[r - 1][c]
            if p:
                press[r][c] = 1
                flip(g, r, c)
                steps.append((r, c, [row[:] for row in g]))
    return press, steps, g


def solve_general(light):
    """任意行列的同一方法，返回所有可行的第一行 mask（用于唯一性与小盘面对拍）。"""
    cols = len(light[0])
    return [m for m in range(1 << cols) if not any(chase(light, m)[2][-1])]


def tries(light):
    """按 mask 从 0 起试，每种第一行推到底后最后一行还亮几盏；成功那种为 0，之后不再试。"""
    out = []
    for m in range(64):
        left = sum(chase(light, m)[2][-1])
        out.append((m, left))
        if left == 0:
            break
    return out


def bits(mask, n=6):
    return [mask >> (n - 1 - c) & 1 for c in range(n)]


def gf2_rank(rows=R, cols=C):
    """「按钮 → 灯」的 30×30 翻转矩阵在 GF(2) 上的秩；满秩 ⇔ 每个初始局面恰有一种按法。"""
    n = rows * cols
    vecs = []
    for r in range(rows):
        for c in range(cols):
            v = 0
            for i, j in neighbors(r, c, rows, cols):
                v |= 1 << (i * cols + j)
            vecs.append(v)
    rank = 0
    for bit in range(n):
        piv = next((k for k in range(rank, n) if vecs[k] >> bit & 1), None)
        if piv is None:
            continue
        vecs[rank], vecs[piv] = vecs[piv], vecs[rank]
        for k in range(n):
            if k != rank and vecs[k] >> bit & 1:
                vecs[k] ^= vecs[rank]
        rank += 1
    return rank


# 旁白与画面里用到的数字
P1 = SAMPLE[0]
TRIES1 = tries(P1)                       # 第一组样例的试探序列
WIN_MASK = TRIES1[-1][0]                 # 成功的第一行
N_TRIED = len(TRIES1)                    # 一共试了几种（含成功那种）
LEFT0 = TRIES1[0][1]                     # 第一行全不按时，最后一行还亮几盏
BRUTE = 2 ** (R * C)                     # 直接枚举整张表
SMART = 2 ** C                           # 只枚举第一行
OPS = SMART * R * C                      # 每种第一行推一遍 30 格
SPEEDUP = BRUTE // SMART

if __name__ == "__main__":
    print("第一组：试了", N_TRIED, "种，成功 mask =", WIN_MASK, bits(WIN_MASK), "全不按剩", LEFT0)
    print("各次剩余：", TRIES1)
    print("2^30 =", BRUTE, "64 种 × 30 格 =", OPS, "加速", SPEEDUP, "秩", gf2_rank())
    for p in SAMPLE:
        for row in solve(p):
            print(*row)
