"""矩阵片的数据层：讲义第 6 周第 1 节的代码原样插桩，画面与旁白里的每个数字都从这里取。

- 浅拷贝陷阱 `[[0] * n] * m`（1.1 节，课件 P12）
- 保护圈 + 方向数组求上下左右邻居之和（1.2 节，P14–P16）
- M12560 生存游戏：保护圈 + 八邻域，结果写进新矩阵（1.2 节练习）
- 转置与顺时针旋转 `zip(*b[::-1])`（1.3 节，P17）
- M18106 螺旋矩阵（第 6 周练习 10，模拟 + 方向数组）：撞墙就右转；这里墙用保护圈表示
"""
from __future__ import annotations

# ---------------------------------------------------------------- 1.1 浅拷贝陷阱
TRAP_M, TRAP_N = 3, 4


def alias_trap(m=TRAP_M, n=TRAP_N):
    """讲义两种建法各改一次 a[0][0] = 9，返回 (错误写法结果, 正确写法结果, 错误写法里不同行对象数)。"""
    bad = [[0] * n] * m
    good = [[0] * n for _ in range(m)]
    bad[0][0] = 9
    good[0][0] = 9
    return bad, good, len({id(r) for r in bad})


# ---------------------------------------------------------------- 1.2 保护圈 + 方向数组
A = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIRS8 = tuple((di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0))


def pad(a, fill=0):
    """讲义写法：四周补一圈 fill，变成 (m+2) x (n+2)。"""
    m, n = len(a), len(a[0])
    g = [[fill] * (n + 2) for _ in range(m + 2)]
    for i in range(m):
        for j in range(n):
            g[i + 1][j + 1] = a[i][j]
    return g


def neighbor_sum(a=A):
    """讲义 1.2 节：加保护圈后对每格求上下左右之和。"""
    m, n = len(a), len(a[0])
    g = pad(a)
    res = [[0] * n for _ in range(m)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            res[i - 1][j - 1] = sum(g[i + di][j + dj] for di, dj in DIRS)
    return res


def neighbor_terms(i, j, a=A):
    """格 (i, j)（0 起）四个邻居在保护圈矩阵里的取值，按 DIRS 顺序（上下左右）。"""
    g = pad(a)
    return [g[i + 1 + di][j + 1 + dj] for di, dj in DIRS]


# ---------------------------------------------------------------- M12560 生存游戏
LIFE = [[0, 0, 1, 1], [1, 1, 0, 0], [1, 1, 0, 1]]
LIFE_OUT = [[0, 1, 1, 0], [1, 0, 0, 1], [1, 1, 1, 0]]   # 讲义给出的样例输出


def life_step(cells=LIFE):
    """讲义 M12560 代码：返回 (新矩阵, 每格活邻居数)。"""
    n, m = len(cells), len(cells[0])
    g = pad(cells)
    out, cnt = [], []
    for i in range(1, n + 1):
        row, crow = [], []
        for j in range(1, m + 1):
            c = sum(g[i + di][j + dj] for di, dj in DIRS8)
            crow.append(c)
            if g[i][j] == 1:
                row.append(1 if c in (2, 3) else 0)
            else:
                row.append(1 if c == 3 else 0)
        out.append(row)
        cnt.append(crow)
    return out, cnt


def life_inplace_wrong(cells=LIFE):
    """反例：边算边改原矩阵（讲义强调不能这样做）。"""
    n, m = len(cells), len(cells[0])
    g = pad(cells)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = sum(g[i + di][j + dj] for di, dj in DIRS8)
            g[i][j] = (1 if c in (2, 3) else 0) if g[i][j] == 1 else (1 if c == 3 else 0)
    return [row[1:m + 1] for row in g[1:n + 1]]


# ---------------------------------------------------------------- 1.3 转置与旋转
def transpose(a):
    return [list(row) for row in zip(*a)]


def rotate_cw(b):
    """讲义：顺时针 90° = 先上下翻转再转置。"""
    return [list(row) for row in zip(*b[::-1])]


def rotate_ccw(b):
    """讲义：逆时针 90° = 先转置再上下翻转。"""
    return [list(row) for row in zip(*b)][::-1]


# ---------------------------------------------------------------- M18106 螺旋矩阵
SPIRAL_N = 4
RIGHT_DOWN_LEFT_UP = ((0, 1), (1, 0), (0, -1), (-1, 0))


def spiral(n=SPIRAL_N):
    """方向数组 + 保护圈：边界外一圈填 -1 当墙，前方不是 0 就右转。返回 (矩阵, 转弯处的数, 路径)。"""
    g = [[-1] * (n + 2)] + [[-1] + [0] * n + [-1] for _ in range(n)] + [[-1] * (n + 2)]
    i, j, d = 1, 1, 0
    turns, path = [], []
    for v in range(1, n * n + 1):
        g[i][j] = v
        path.append((i - 1, j - 1))
        di, dj = RIGHT_DOWN_LEFT_UP[d]
        if g[i + di][j + dj] != 0 and v < n * n:
            d = (d + 1) % 4
            turns.append(v)
            di, dj = RIGHT_DOWN_LEFT_UP[d]
        i, j = i + di, j + dj
    return [row[1:n + 1] for row in g[1:n + 1]], turns, path
