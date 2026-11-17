"""渗透实验精讲片（M31533）的数据层：讲义 Python 参考代码原样复用 novdata.solve_t5，这里只补插桩。

- halving_trace：与 solve_t5 的 find 逐行同逻辑（fa[x] = fa[fa[x]] 路径减半），记录每一步父指针快照；
- walk_trace：自拟 4×5 网格八次打开，复用 novdata.perc_trace（与讲义同逻辑），再给每个连通块定颜色类别；
- solve_t5_elif：把讲义源码里第二个 if 原样改成 elif 后 exec 出来的「错误写法」，用来实际跑 n = 1；
- MAIN_LOOP：片中对照的讲义代码段（从 solve_t5 源码里原样截取，不手抄）。
test_novperc.py 用每步 BFS 的暴力实现、独立写的并查集对撞。
"""
from __future__ import annotations

import inspect
import textwrap

import novdata as N

solve_t5 = N.solve_t5
run_io = N.run_io
SAMPLES = N.SAMPLES["t5"]                       # [(样例 1 输入, "3"), (样例 2 输入, "-1")]
SAMPLE_OPS = [[(1, 1), (2, 1), (3, 1)], [(1, 1), (1, 2), (1, 3), (2, 2)]]   # 与 SAMPLES 同一份数据，画面用

# ---------------------------------------------------------------- 规模（旁白：四百亿步）
CELLS_MAX = 2 * 10 ** 5                         # n·m ≤ 2×10⁵
NAIVE_STEPS = CELLS_MAX * CELLS_MAX             # 全部打开 2×10⁵ 次，每次 BFS 走 2×10⁵ 格


def inp_of(n: int, m: int, ops) -> str:
    return f"{n} {m} {len(ops)}\n" + "".join(f"{r} {c}\n" for r, c in ops)


# ---------------------------------------------------------------- 路径减半
CHAIN = {1: 1, 2: 1, 3: 2, 4: 3, 5: 4}         # 五指四、四指三、三指二、二指一
CHAIN_FROM = 5


def halving_trace(fa: dict, x: int):
    """与讲义 find 同逻辑：while fa[x] != x: fa[x] = fa[fa[x]]; x = fa[x]。

    返回 (根, 步骤列表)，每步 {"x": 改的结点, "old": 原父亲, "new": 新父亲, "fa": 改后快照}。
    """
    fa, steps = dict(fa), []
    while fa[x] != x:
        old = fa[x]
        fa[x] = fa[fa[x]]
        steps.append({"x": x, "old": old, "new": fa[x], "fa": dict(fa)})
        x = fa[x]
    return x, steps


def depth(fa: dict, x: int) -> int:
    d = 0
    while fa[x] != x:
        x, d = fa[x], d + 1
    return d


# ---------------------------------------------------------------- 4×5 网格逐步打开（自拟）
WALK = (4, 5, [(1, 2), (4, 4), (3, 3), (2, 2), (4, 5), (2, 3), (1, 5), (3, 4)])   # 1-based 行列


def walk_trace(n: int, m: int, ops):
    """novdata.perc_trace 的每一步，再给每个打开格标连通块类别：
    "both"（同时含 TOP 与 BOT）/ "top" / "bot" / "free:<根>"（不含虚拟结点的孤立块）。"""
    steps = N.perc_trace(n, m, ops)
    for st in steps:
        roots = st["roots"]
        rt, rb = roots["TOP"], roots["BOT"]
        kind = {}
        for c, r in roots.items():
            if c in ("TOP", "BOT"):
                continue
            kind[c] = "both" if r == rt == rb else "top" if r == rt else "bot" if r == rb else f"free:{r}"
        st["kind"] = kind
        r, c = st["cell"]
        st["u"] = r * m + c
    return steps


# ---------------------------------------------------------------- n = 1 的 elif 错误写法
_SRC = textwrap.dedent(inspect.getsource(N.solve_t5))
_IF2 = "    if r == n - 1:\n"
assert _SRC.count(_IF2) == 1
_BUG_SRC = _SRC.replace(_IF2, "    elif r == n - 1:\n").replace("def solve_t5(", "def solve_t5_elif(")
_ns: dict = {}
exec(compile(_BUG_SRC, "<讲义 solve_t5 改 elif>", "exec"), _ns)   # noqa: S102  讲义源码只改一个词
solve_t5_elif = _ns["solve_t5_elif"]
ONE_ROW = (1, 3, [(1, 2)])                      # 只有一行三格，打开中间一格


# ---------------------------------------------------------------- 讲义代码段（片中对照）
def _main_loop() -> str:
    lines = _SRC.splitlines()
    a = next(i for i, s in enumerate(lines) if s.strip().startswith("for k in range(q):"))
    b = next(i for i, s in enumerate(lines) if s.strip() == "break")
    return textwrap.dedent("\n".join(lines[a:b + 1])) + "\n"


MAIN_LOOP = _main_loop()
HEAD_LINES = [s.strip() for s in _SRC.splitlines() if s.strip().startswith(("TOP, BOT", "fa = list"))]


# ---------------------------------------------------------------- 朴素做法示意：一次 BFS 的波纹（自拟 5×8 局面）
NAIVE_GRID = ["..#.#...",
              "#...#.#.",
              "..#...#.",
              ".##.#...",
              "...#.#.#"]


def bfs_layers(g: list[str]):
    """从第一行所有打开格出发的多源 BFS，按层返回格子列表（0-based）。"""
    n, m = len(g), len(g[0])
    cur = [(0, j) for j in range(m) if g[0][j] == "."]
    seen, layers = set(cur), []
    while cur:
        layers.append(cur)
        nxt = []
        for i, j in cur:
            for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if 0 <= a < n and 0 <= b < m and g[a][b] == "." and (a, b) not in seen:
                    seen.add((a, b))
                    nxt.append((a, b))
        cur = nxt
    return layers


# ---------------------------------------------------------------- find / union 原样（片中右侧代码）
def _block(name: str) -> list[str]:
    lines = _SRC.splitlines()
    a = next(i for i, s in enumerate(lines) if s.strip().startswith(f"def {name}("))
    out = [lines[a]]
    for s in lines[a + 1:]:
        if not s.strip():
            break
        out.append(s)
    return textwrap.dedent("\n".join(out)).splitlines()


FIND_LINES = _block("find")
UNION_LINES = _block("union")
UNION_DEMO = (6, 1)                             # 路径减半之后再 union(6, 1)：6 是单独一个根


def union_apply(fa: dict, a: int, b: int):
    """与讲义 union 同逻辑：fa[find(a)] = find(b)。返回改后的快照。"""
    ra, st = halving_trace(fa, a)
    f = st[-1]["fa"] if st else dict(fa)
    rb, st = halving_trace(f, b)
    f = dict(st[-1]["fa"] if st else f)
    f[ra] = rb
    return f
