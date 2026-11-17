"""箭头迷阵精讲片的数据层：讲义 Python 参考代码原样在 novdata.solve_t3，这里只补插桩与对照写法。

讲义：2026fall courseware/202611_ADS_November_Exam_Review.md 第 3 节 T3（M31531 箭头迷阵）。
- 样例 1、样例 2 用题面原样；每次出发的 path / 收尾方式取 novdata.arrows_trace（与讲义代码逐行同逻辑）。
- 「绕圈不等于成环」的 3×3 螺旋网格 SPIRAL 与改一格后的 SPIRAL_CYC 为自拟。
- 递归写法 solve_rec 为自拟对照（讲义只说「递归会撞上深度限制」），用来实际跑出 RecursionError。
test_novarrow.py 用逐格模拟 nm+1 步的暴力独立对撞。
"""
from __future__ import annotations

import inspect
import sys
import textwrap

import novdata as N

MOVE = N.MOVE
SAMPLE1 = ["UD", "DU"]                          # 题面样例 1，答案 2
SAMPLE2 = ["URD", "LDR", "RUL"]                 # 题面样例 2，答案 5
assert N.ARROWS == SAMPLE2

# 自拟：从中心出发绕一整圈再从左下角出界；把左下角改成向上就回到走过的格子
SPIRAL = ["RRD", "ULD", "LLL"]
SPIRAL_CYC = ["RRD", "ULD", "ULL"]
SPIRAL_START = (1, 1)

N_MAX = 2 * 10 ** 5                             # n×m ≤ 2×10⁵
BRUTE_STEPS = N_MAX * (N_MAX + 1)               # 暴力：每格最多走 nm+1 步，约 4×10¹⁰
REC_OK, REC_BAD = 900, 2000                     # 一行全是 R：递归写法 900 能过、2000 报错


def solve(g: list[str]) -> int:
    """喂给讲义原样代码 novdata.solve_t3。"""
    return int(N.run_io(N.solve_t3, f"{len(g)} {len(g[0])}\n" + "\n".join(g) + "\n"))


def trace(g: list[str]):
    """每次出发的 path（格子编号 u = i*m + j）、收尾方式、撞到的位置、结论；以及最终状态表。"""
    walks, st = N.arrows_trace(g)
    m = len(g[0])
    for w in walks:
        w["ids"] = [i * m + j for i, j in w["path"]]
        w["sid"] = w["ids"][0]
    return walks, st


def route(g: list[str], start):
    """从 start 照箭头走，直到出界或回到走过的格子。返回 (经过的格子, 停下的位置, 是否出界)。"""
    n, m = len(g), len(g[0])
    i, j = start
    seen, cells = set(), []
    while 0 <= i < n and 0 <= j < m and (i, j) not in seen:
        seen.add((i, j))
        cells.append((i, j))
        di, dj = MOVE[g[i][j]]
        i, j = i + di, j + dj
    return cells, (i, j), not (0 <= i < n and 0 <= j < m)


def total_steps(walks) -> int:
    """每次出发：path 上每格一步，加上停下前多看的那一格。"""
    return sum(len(w["path"]) + 1 for w in walks)


# ---------------------------------------------------------------- 自拟对照：递归写法
REC_SRC = '''def go(i, j):
    if not (0 <= i < n and 0 <= j < m):
        return 2
    u = i * m + j
    if st[u] == 1:
        return 3
    if st[u]:
        return st[u]
    st[u] = 1
    di, dj = MOVE[g[i][j]]
    st[u] = go(i + di, j + dj)
    return st[u]'''


def solve_rec(g: list[str]) -> int:
    """与讲义同一个算法，只是把 path 换成调用栈。路线太长时抛 RecursionError。"""
    n, m = len(g), len(g[0])
    st = [0] * (n * m)
    env = {"n": n, "m": m, "st": st, "g": g, "MOVE": MOVE}
    exec(REC_SRC, env)
    go = env["go"]
    for s in range(n * m):
        if not st[s]:
            go(s // m, s % m)
    return st.count(2)


def rec_outcome(m: int) -> str:
    """一行 m 个 R：返回递归写法的结果文字（答案或异常名）。"""
    try:
        return str(solve_rec(["R" * m]))
    except RecursionError:
        return "RecursionError"


# ---------------------------------------------------------------- 讲义代码节选（核心循环，原样）
def lecture_lines() -> list[str]:
    body = inspect.getsource(N.solve_t3).split("\n", 1)[1]        # 去掉 def 行，函数体即讲义顶层脚本
    lines = textwrap.dedent(body).splitlines()
    a = next(k for k, s in enumerate(lines) if s.startswith("for s in range"))
    b = next(k for k, s in enumerate(lines) if s.strip() == "st[u] = res")
    return lines[a:b + 1]


CODE = lecture_lines()
CODE_MARKS = {                                   # 片中高亮的行（CODE 里的下标）
    "skip": [CODE.index("    if st[s]:"), CODE.index("        continue")],
    "out": [k for k, s in enumerate(CODE) if "res = 2" in s or "if not (0 <= i" in s],
    "cyc": [k for k, s in enumerate(CODE) if "st[u] == 1" in s or "res = 3" in s],
    "join": [k for k, s in enumerate(CODE) if s.strip() in ("if st[u]:", "res = st[u]  # 接上已知结论")],
    "step": [k for k, s in enumerate(CODE) if s.strip() in ("st[u] = 1", "path.append(u)", "di, dj = MOVE[g[i][j]]",
                                                          "i, j = i + di, j + dj")],
    "fill": [k for k, s in enumerate(CODE) if s.strip() in ("for u in path:", "st[u] = res")],
}

if __name__ == "__main__":
    print(sys.getrecursionlimit(), rec_outcome(REC_OK), rec_outcome(REC_BAD))
    for w in trace(SAMPLE2)[0]:
        print(w["ids"], w["end"], w["hit"])
    print(route(SPIRAL, SPIRAL_START), route(SPIRAL_CYC, SPIRAL_START), solve(SPIRAL), solve(SPIRAL_CYC))
    print("\n".join(CODE)); print(CODE_MARKS)
