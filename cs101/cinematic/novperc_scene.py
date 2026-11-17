"""渗透实验：并查集加两个虚拟结点（M31533 精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。两个题面样例、朴素 BFS 的波纹、路径减半的父指针快照、
4×5 网格八次打开的每一步连通块、n = 1 时 elif 写法的实际输出都来自 novpercdata
（讲义 Python 参考代码 novdata.solve_t5 原样；test_novperc.py 用每步 BFS 与洪水填充独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novpercdata as D  # noqa: E402
from cine import *  # noqa: E402,F403
from dsu_scene import Forest  # noqa: E402

C_ORANGE = "#FF9F43"
CLOSED = "#20242e"
DIM = "#3a4050"
KIND_COL = {"top": C_BLUE, "bot": C_ORANGE, "both": C_GREEN}


def kcol(kind: str) -> str:
    return KIND_COL.get(kind, C_PURPLE)


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def code_block(lines, size=22, color=WHITE, buff=0.12):
    """逐行等宽文字，保留行首缩进（Text 会吞掉前导空格，这里按字符宽度平移）。"""
    cw = M("x" * 20, size).width / 20
    g = VGroup()
    for s in lines:
        ind = len(s) - len(s.lstrip(" "))
        t = M(s.strip(), size, color)
        g.add(t)
        t.ind = ind
    g.arrange(DOWN, buff=buff, aligned_edge=LEFT)
    for t in g:
        t.shift(RIGHT * cw * t.ind)
    return g


class Board(VGroup):
    """n×m 网格 + 可选 TOP / BOT 条。"""

    def __init__(self, n, m, cs, center, bars=False, nums=False):
        super().__init__()
        self.n, self.m, self.cs = n, m, cs
        self.c = np.array(center, dtype=float)
        self.cells = {}
        for i in range(n):
            for j in range(m):
                sq = Square(cs * 0.92, stroke_color=C_GREY, stroke_width=2).set_fill(CLOSED, 0.9).move_to(self.pos(i, j))
                self.cells[(i, j)] = sq
        self.grid = VGroup(*self.cells.values())
        self.add(self.grid)
        self.nums = VGroup()
        if nums:
            for (i, j), sq in self.cells.items():
                t = M(str(i * m + j), 14, C_GREY)
                t.move_to(sq.get_corner(UL) + np.array([t.width / 2 + 0.07, -t.height / 2 - 0.06, 0]))
                self.nums.add(t)
        self.topb = self.botb = None
        if bars:
            w = m * cs
            self.topb = RoundedRectangle(corner_radius=0.1, width=w, height=0.4, stroke_color=C_GREY, stroke_width=2.5)
            self.topb.move_to(self.c + np.array([0, n * cs / 2 + 0.42, 0]))
            self.botb = self.topb.copy().move_to(self.c - np.array([0, n * cs / 2 + 0.42, 0]))
            self.topl = M("TOP", 20, C_GREY).move_to(self.topb)
            self.botl = M("BOT", 20, C_GREY).move_to(self.botb)

    def pos(self, i, j):
        return self.c + np.array([(j - (self.m - 1) / 2) * self.cs, -(i - (self.n - 1) / 2) * self.cs, 0])

    def bars(self):
        return VGroup(self.topb, self.topl, self.botb, self.botl)

    def link_top(self, i, j, color=WHITE):
        p = self.pos(i, j)
        return Line(self.cells[(i, j)].get_top(), [p[0], self.topb.get_bottom()[1], 0], color=color, stroke_width=4)

    def link_bot(self, i, j, color=WHITE):
        p = self.pos(i, j)
        return Line(self.cells[(i, j)].get_bottom(), [p[0], self.botb.get_top()[1], 0], color=color, stroke_width=4)

    def link(self, a, b, color=WHITE):
        p, q = self.pos(*a), self.pos(*b)
        v = (q - p) / np.linalg.norm(q - p)
        return Line(p + v * self.cs * 0.28, q - v * self.cs * 0.28, color=color, stroke_width=6)


class NovPercLesson(Lesson):
    def construct(self):
        for b in ("title", "problem", "naive", "dsu", "virtual", "walk", "code", "pitfall", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novperc] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)
            self.remove(*rest)

    def head(self, no, name, tag, pos=(-6.6, 3.2)):
        g = VGroup(T(no, 26, C_BLUE), T(name, 32), T(tag, 22, C_GREY)).arrange(RIGHT, buff=0.3)
        return g.move_to([pos[0] + g.width / 2, pos[1], 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("月考精讲 · T5 · M31533", 26, C_BLUE).move_to([0, 2.9, 0])
        title = T("渗透实验", 60).next_to(kick, DOWN, buff=0.25)
        sub = T("并查集加两个虚拟结点", 32, C_YELLOW).next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)
        bd = Board(4, 6, 0.42, [0, -1.25, 0])
        self.play(FadeIn(bd), run_time=0.5)
        self.at("一个一个")
        n, m, ops = 4, 6, [(1, 3), (2, 3), (2, 4), (3, 4), (4, 4)]          # 片头装饰：自上而下打通一条
        assert D.run_io(D.solve_t5, D.inp_of(n, m, ops)) == "5"
        for r, c in ops:
            self.play(bd.cells[(r - 1, c - 1)].animate.set_fill(WHITE, 0.55), run_time=0.3)
        self.play(*[bd.cells[(r - 1, c - 1)].animate.set_fill(C_GREEN, 0.7).set_stroke(C_GREEN, 2.5) for r, c in ops],
                  run_time=0.5)
        self.at("两件事")
        q1 = T("① 为什么用并查集", 26, WHITE)
        q2 = T("② 一整行 → 一个点", 26, WHITE)
        qs = VGroup(q1, q2).arrange(DOWN, buff=0.3, aligned_edge=LEFT).next_to(bd, RIGHT, buff=0.8)
        self.play(FadeIn(q1, shift=LEFT * 0.2), run_time=0.5)
        self.at("一整行")
        self.play(FadeIn(q2, shift=LEFT * 0.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 题意与两个样例
    def problem_beat(self):
        self.beat("problem")
        h = self.head("T5", "渗透实验", "M31533 · 并查集 · 虚拟结点")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        rules = [("n×m 网格，n·m ≤ 2×10⁵，初始全部封闭", "全部封闭"),
                 ("依次打开 q 个格子 (r, c)", "依次打开"),
                 ("只走打开的格子、四连通，第 1 行 → 第 n 行：渗透", "上下左右"),
                 ("输出第一次渗透的操作编号；始终不渗透输出 −1", "输出第一次")]
        lines = VGroup()
        for k, (txt, _) in enumerate(rules):
            t = T(txt, 25, WHITE if k != 2 else C_YELLOW)
            t.move_to([-6.4 + t.width / 2, 2.35 - 0.55 * k, 0])
            lines.add(t)
        for t, (_, key) in zip(lines, rules):
            self.at(key)
            self.play(FadeIn(t, shift=RIGHT * 0.15), run_time=0.5)
        # 两个样例
        res = []
        for idx, (ops, (inp, out)) in enumerate(zip(D.SAMPLE_OPS, D.SAMPLES)):
            assert D.run_io(D.solve_t5, inp) == out
            res.append(out)
        cs = 0.5
        b1, b2 = Board(3, 3, cs, [-4.6, -1.45, 0]), Board(3, 3, cs, [1.4, -1.45, 0])
        l1 = T("样例 1", 24, C_BLUE).next_to(b1, UP, buff=0.18)
        l2 = T("样例 2", 24, C_BLUE).next_to(b2, UP, buff=0.18)
        self.at("样例一")
        self.play(FadeIn(b1), FadeIn(l1), run_time=0.5)
        tags = VGroup()
        for k, (r, c) in enumerate(D.SAMPLE_OPS[0]):
            sq = b1.cells[(r - 1, c - 1)]
            num = M(str(k + 1), 20, BG).move_to(sq)
            tags.add(num)
            self.play(sq.animate.set_fill(WHITE, 0.85), FadeIn(num), run_time=0.35)
        col = [b1.cells[(r - 1, c - 1)] for r, c in D.SAMPLE_OPS[0]]
        a1 = T(f"第 3 次连成竖线 → 输出 {res[0]}", 24, C_GREEN).next_to(b1, RIGHT, buff=0.4)
        self.play(*[s.animate.set_fill(C_GREEN, 0.8).set_stroke(C_GREEN, 2.5) for s in col], FadeIn(a1), run_time=0.6)
        self.at("样例二")
        self.play(FadeIn(b2), FadeIn(l2), run_time=0.5)
        for k, (r, c) in enumerate(D.SAMPLE_OPS[1]):
            sq = b2.cells[(r - 1, c - 1)]
            num = M(str(k + 1), 20, BG).move_to(sq)
            tags.add(num)
            self.play(sq.animate.set_fill(WHITE, 0.85), FadeIn(num), run_time=0.3)
        self.at("还到不了")
        row3 = SurroundingRectangle(VGroup(*[b2.cells[(2, j)] for j in range(3)]), color=C_RED, buff=0.05)
        a2 = T(f"第 3 行一格没开 → 输出 {res[1]}", 24, C_RED).next_to(b2, RIGHT, buff=0.4)
        self.play(Create(row3), FadeIn(a2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 朴素：每次 BFS
    def naive_beat(self):
        self.beat("naive")
        g = D.NAIVE_GRID
        n, m = len(g), len(g[0])
        bd = Board(n, m, 0.62, [-3.3, 0.35, 0])
        for (i, j), sq in bd.cells.items():
            if g[i][j] == ".":
                sq.set_fill(WHITE, 0.25)
        cap = T("每开一格：从第一行出发 BFS 一次", 26, C_YELLOW).move_to([-3.3, 2.75, 0])
        self.play(FadeIn(bd), FadeIn(cap), run_time=0.6)
        self.at("走遍")
        layers = D.bfs_layers(g)
        for k, layer in enumerate(layers):
            self.play(*[bd.cells[c].animate.set_fill(C_TEAL, 0.75) for c in layer], run_time=0.28)
        self.at("二十万次")
        cost = VGroup(MathTex(r"2\times10^{5}", color=WHITE), T("次", 26), MathTex(r"\times", color=C_GREY),
                      MathTex(r"2\times10^{5}", color=WHITE), T("格", 26)).arrange(RIGHT, buff=0.18)
        cost.move_to([3.6, 1.2, 0])
        assert D.NAIVE_STEPS == 4 * 10 ** 10
        tot = VGroup(MathTex(r"=4\times10^{10}", color=C_RED), T("步", 26, C_RED)).arrange(RIGHT, buff=0.18)
        tot.next_to(cost, DOWN, buff=0.35)
        self.play(FadeIn(cost), run_time=0.6)
        self.at("四百亿")
        tle = T("超时", 30, C_RED).next_to(tot, DOWN, buff=0.35)
        self.play(FadeIn(tot), run_time=0.5)
        self.play(FadeIn(tle, scale=1.2), run_time=0.4)
        self.at("从零开始")
        reset = [bd.cells[c].animate.set_fill(WHITE, 0.25) for layer in layers for c in layer]
        waste = T("前面算过的连通关系\n全扔了", 26, C_GREY).next_to(tle, DOWN, buff=0.5)
        self.play(*reset, FadeIn(waste), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 并查集：路径减半与 union
    def dsu_beat(self):
        self.beat("dsu")
        h = T("只开不关 → 连通块只合并不拆分 → 并查集", 28, C_YELLOW).move_to([0, 3.2, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.6)
        fa0 = dict(D.CHAIN)
        fa0[D.UNION_DEMO[0]] = D.UNION_DEMO[0]
        fo = Forest(fa0, r=0.27, cx=-3.6, top=2.2, dx=0.9, dy=0.95, tree_gap=0.9)
        code = code_block(D.FIND_LINES + D.UNION_LINES, 22)
        code.move_to([3.3, 1.3, 0])
        code[len(D.FIND_LINES)].shift(DOWN * 0.15)
        code[len(D.FIND_LINES) + 1].shift(DOWN * 0.15)
        keys = sorted(fa0)
        w = 0.62
        cells = VGroup(*[Square(w * 0.9, stroke_color=C_GREY, stroke_width=2) for _ in keys]).arrange(RIGHT, buff=w * 0.1)
        cells.move_to([3.2, -1.75, 0])
        idx = VGroup(*[M(str(k), 18, C_GREY).next_to(c, UP, buff=0.1) for k, c in zip(keys, cells)])
        vals = VGroup(*[M(str(fa0[k]), 24).move_to(c) for k, c in zip(keys, cells)])
        lab = M("fa", 22, C_GREY).next_to(cells, LEFT, buff=0.25)
        self.at("每块")
        self.play(FadeIn(fo), run_time=0.7)
        self.at("find")
        self.play(FadeIn(code[:len(D.FIND_LINES)]), FadeIn(VGroup(cells, idx, vals, lab)), run_time=0.6)
        self.at("路径减半")
        hl = SurroundingRectangle(code[2], color=C_YELLOW, buff=0.06)
        self.play(Create(hl), run_time=0.5)
        self.at("看这条链")
        self.play(*[Indicate(fo.nodes[k], color=C_BLUE, scale_factor=1.15) for k in (5, 4, 3, 2)], run_time=1.0)
        self.at("从五查")
        root, steps = D.halving_trace(fa0, D.CHAIN_FROM)
        assert root == 1 and D.depth(fa0, 5) == 4
        ring = Circle(0.4, stroke_color=C_YELLOW, stroke_width=6).move_to(fo.nodes[D.CHAIN_FROM])
        cur = {"x": D.CHAIN_FROM}

        def follow(r):
            r.move_to(fo.nodes[cur["x"]])
        self.play(Create(ring), run_time=0.3)
        for st in steps:
            x = st["x"]
            k = keys.index(x)
            newv = M(str(st["new"]), 24, C_YELLOW).move_to(cells[k])
            ring.add_updater(follow)                    # 结点挪位时光圈跟着当前的 x
            self.play(*fo.relayout(st["fa"]), Transform(vals[k], newv), run_time=0.8)
            ring.remove_updater(follow)
            cur["x"] = st["new"]                        # x = fa[x]
            self.play(ring.animate.move_to(fo.nodes[st["new"]]), run_time=0.35)
        after = steps[-1]["fa"]
        assert D.depth(after, 5) == 2
        dep = T(f"5 到根：{D.depth(fa0, 5)} 步 → {D.depth(after, 5)} 步", 26, C_GREEN).move_to([-3.6, -2.55, 0])
        self.play(FadeIn(dep), FadeOut(ring), run_time=0.5)
        self.at("union")
        a, b = D.UNION_DEMO
        fa2 = D.union_apply(after, a, b)
        assert fa2[a] == b and all(fa2[k] == after[k] for k in after if k != a)
        hl2 = SurroundingRectangle(code[len(D.FIND_LINES) + 1], color=C_GREEN, buff=0.06)
        call = M(f"union({a}, {b})", 22, C_GREEN).next_to(code, DOWN, buff=0.3).align_to(code, LEFT)
        self.play(FadeIn(code[len(D.FIND_LINES):]), Transform(hl, hl2), FadeIn(call), run_time=0.6)
        k = keys.index(a)
        self.play(*fo.relayout(fa2), Transform(vals[k], M(str(b), 24, C_GREEN).move_to(cells[k])), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        fo.freeze()
        self.clear_all()

    # ---------------------------------------------------------------- 难点：两个虚拟结点
    def virtual_beat(self):
        self.beat("virtual")
        n, m = 4, 5
        bd = Board(n, m, 0.8, [-3.3, -0.3, 0], bars=True)
        tops, bots = [(0, 0), (0, 2), (0, 4)], [(3, 1), (3, 3), (3, 4)]     # 示意：两行各开三格
        for c in tops + bots:
            bd.cells[c].set_fill(WHITE, 0.55)
        cap = T("第一行任意一格 ⇝ 最后一行任意一格", 26, C_YELLOW).move_to([0, 3.2, 0])
        self.play(FadeIn(bd), FadeIn(cap), run_time=0.6)
        self.at("两两比根")
        pairs = VGroup(*[Line(bd.pos(*a), bd.pos(*b), color=C_RED, stroke_width=2.5) for a in tops for b in bots])
        self.play(LaggedStart(*[Create(p) for p in pairs], lag_ratio=0.12), run_time=1.4)
        x0 = 0.9
        mm = VGroup(T("两两比根：最坏", 26), MathTex(r"m\times m", color=C_RED), T("次", 26)).arrange(RIGHT, buff=0.18)
        mm.move_to([x0 + mm.width / 2, 1.6, 0])
        self.play(FadeIn(mm), run_time=0.5)
        self.at("虚拟结点")
        self.play(FadeOut(pairs), FadeIn(bd.bars()), run_time=0.6)
        self.at("代表第一行")
        t1 = VGroup(M("TOP", 24, C_BLUE), T("代表第一行", 26)).arrange(RIGHT, buff=0.2)
        t2 = VGroup(M("BOT", 24, C_ORANGE), T("代表最后一行", 26)).arrange(RIGHT, buff=0.2)
        for k, t in enumerate((t1, t2)):
            t.move_to([x0 + t.width / 2, 0.75 - 0.6 * k, 0])
        self.play(FadeIn(t1), bd.topb.animate.set_stroke(C_BLUE, 3), run_time=0.5)
        self.play(FadeIn(t2), bd.botb.animate.set_stroke(C_ORANGE, 3), run_time=0.5)
        self.at("一打开")
        lt = VGroup(*[bd.link_top(*c, C_BLUE) for c in tops])
        self.play(*[Create(x) for x in lt], *[bd.cells[c].animate.set_fill(C_BLUE, 0.6) for c in tops], run_time=0.7)
        self.at("并进 BOT")
        lb = VGroup(*[bd.link_bot(*c, C_ORANGE) for c in bots])
        self.play(*[Create(x) for x in lb], *[bd.cells[c].animate.set_fill(C_ORANGE, 0.6) for c in bots], run_time=0.7)
        self.at("等价于")
        eq = VGroup(T("渗透", 28, C_GREEN), MathTex(r"\iff", color=C_GREEN),
                    M("find(TOP) == find(BOT)", 24, C_GREEN)).arrange(RIGHT, buff=0.2)
        eq.move_to([x0 + eq.width / 2, -1.3, 0])
        one = T("只比一次", 26, C_GREEN).next_to(eq, DOWN, buff=0.3).align_to(eq, LEFT)
        self.play(FadeIn(eq, shift=UP * 0.15), run_time=0.6)
        self.at("只比一次")
        self.play(FadeIn(one), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 4×5 网格逐步打开
    def walk_beat(self):
        self.beat("walk")
        n, m, ops = D.WALK
        steps = D.walk_trace(n, m, ops)
        assert D.run_io(D.solve_t5, D.inp_of(n, m, ops)) == str(steps[-1]["k"]) == "8"
        bd = Board(n, m, 0.9, [-3.3, -0.3, 0], bars=True, nums=True)
        TOP, BOT = n * m, n * m + 1
        tl = M(f"= {TOP}", 18, C_GREY).next_to(bd.topb, RIGHT, buff=0.15)
        bl = M(f"= {BOT}", 18, C_GREY).next_to(bd.botb, RIGHT, buff=0.15)
        cap = T("4 行 5 列，打开 8 次", 26, C_YELLOW).move_to([0.8, 3.2, 0], aligned_edge=LEFT)
        self.play(FadeIn(bd), FadeIn(bd.nums), FadeIn(bd.bars()), FadeIn(tl), FadeIn(bl), FadeIn(cap), run_time=0.7)
        x0 = 0.8
        legend = VGroup()
        for col, txt in ((C_BLUE, "含 TOP"), (C_ORANGE, "含 BOT"), (C_PURPLE, "孤立块"), (C_GREEN, "TOP、BOT 同根")):
            legend.add(VGroup(Square(0.26, stroke_width=0).set_fill(col, 0.8), T(txt, 20, C_GREY)).arrange(RIGHT, buff=0.12))
        legend.arrange_in_grid(rows=2, cols=2, buff=(0.4, 0.14), cell_alignment=LEFT)
        legend.move_to([x0, -2.45, 0], aligned_edge=LEFT)
        three = VGroup(T("每开一格：", 24, C_GREY), T("① 第一行连 TOP", 24), T("② 最后一行连 BOT", 24),
                       T("③ 与打开的邻格合并", 24)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        three.move_to([x0, 2.0, 0], aligned_edge=UL)
        three.shift(UP * (2.55 - three.get_top()[1]))
        info = VGroup()
        state = {"info": None}
        links = VGroup()
        self.add(links)

        def info_group(st):
            i, j = st["cell"]
            act = []
            if st["top"]:
                act.append("连 TOP")
            if st["bot"]:
                act.append("连 BOT")
            if st["nbr"]:
                act.append("并 " + " ".join(f"{a * m + b}" for a, b in st["nbr"]))
            rt, rb = st["roots"]["TOP"], st["roots"]["BOT"]
            g = VGroup(T(f"第 {st['k']} 步：打开 ({i + 1}, {j + 1})", 26, WHITE),
                       M(f"u = {i}×{m}+{j} = {st['u']}", 22, C_GREY),
                       T("、".join(act) if act else "四周都没开", 22, C_YELLOW if act else C_GREY),
                       M(f"find(TOP)={rt}  find(BOT)={rb}", 22, C_GREEN if rt == rb else WHITE))
            g.arrange(DOWN, buff=0.16, aligned_edge=LEFT)
            return g.move_to([x0, 0.4, 0], aligned_edge=UL).shift(UP * (0.55 - g.get_top()[1]))

        def do_step(st, rt=1.0):
            i, j = st["cell"]
            new = []
            if st["top"]:
                new.append(bd.link_top(i, j))
            if st["bot"]:
                new.append(bd.link_bot(i, j))
            for c in st["nbr"]:
                new.append(bd.link((i, j), c))
            g = info_group(st)
            first = [bd.cells[(i, j)].animate.set_fill(WHITE, 0.7)]
            first.append(Transform(state["info"], g) if state["info"] else FadeIn(g))
            self.play(*first, run_time=rt * 0.35)
            if state["info"] is None:
                state["info"] = g
            if new:
                links.add(*new)
                self.play(*[Create(x) for x in new], run_time=rt * 0.3)
            anims = []
            for c, k in st["kind"].items():
                cc = kcol(k)
                anims.append(bd.cells[c].animate.set_fill(cc, 0.65).set_stroke(cc, 2.5))
            kinds = set(st["kind"].values())
            tc = C_GREEN if "both" in kinds else C_BLUE if "top" in kinds else C_GREY
            bc = C_GREEN if "both" in kinds else C_ORANGE if "bot" in kinds else C_GREY
            anims += [bd.topb.animate.set_stroke(tc, 3), bd.botb.animate.set_stroke(bc, 3)]
            self.play(*anims, run_time=rt * 0.35)

        self.at("三件事")
        self.play(FadeIn(three), run_time=0.5)
        do_step(steps[0], 1.1)
        self.at("前五步")
        self.play(FadeOut(three), run_time=0.3)
        for st in steps[1:5]:
            do_step(st, 0.85)
            assert not st["done"]
        k5 = steps[4]["kind"]
        assert sorted(set(k5.values())) == ["bot", "free:12", "top"]
        self.play(FadeIn(legend), run_time=0.4)
        self.at("第六步")
        assert steps[5]["nbr"] == [(2, 2), (1, 1)] and k5[(2, 2)].startswith("free") and k5[(1, 1)] == "top"
        do_step(steps[5], 1.1)
        self.at("第七步")
        st7 = steps[6]
        assert st7["cell"] == (0, m - 1) and not st7["nbr"] and st7["kind"][(0, m - 1)] == "top"
        do_step(st7, 1.1)
        self.play(Indicate(bd.topb, color=C_BLUE, scale_factor=1.05), run_time=0.6)
        self.at("第八步")
        st8 = steps[7]
        assert st8["done"] and st8["nbr"] == [(3, 3), (2, 2)]
        do_step(st8, 1.2)
        ans = T(f"TOP 与 BOT 同根 → 答案 {st8['k']}", 28, C_GREEN).move_to([x0, -1.45, 0], aligned_edge=LEFT)
        self.play(FadeIn(ans, shift=UP * 0.15), Indicate(bd.topb, color=C_GREEN), Indicate(bd.botb, color=C_GREEN),
                  run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 讲义代码对照
    def code_beat(self):
        self.beat("code")
        code = Code(code_string=D.MAIN_LOOP, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 17})
        if code.height > 5.9:
            code.scale_to_fit_height(5.9)
        code.move_to([-6.7 + code.width / 2, -0.1, 0])
        ln = code.code_lines
        assert len(ln) == len(D.MAIN_LOOP.strip("\n").splitlines()) == 17
        x0 = code.get_right()[0] + 0.45
        enc = VGroup(T("(r, c) 从 0 数起", 24, C_GREY), M("u = r * m + c  ∈ [0, nm−1]", 22),
                     M(D.HEAD_LINES[0].split("  #")[0], 22, C_YELLOW), M(D.HEAD_LINES[1], 22, C_YELLOW))
        enc.arrange(DOWN, buff=0.18, aligned_edge=LEFT).move_to([x0, 2.9, 0], aligned_edge=UL)
        enc.shift(UP * (2.95 - enc.get_top()[1]))
        for t in enc:
            if t.get_right()[0] > 6.8:
                t.scale_to_fit_width(6.8 - x0)
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.7)
        self.at("编号")
        self.play(FadeIn(enc[:2]), run_time=0.5)
        self.at("虚拟结点排在")
        self.play(FadeIn(enc[2:]), run_time=0.5)
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.at(key)
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.08, 0.03), stroke_width=2)
            tag = T(txt, 22, col).move_to([x0, 0, 0], aligned_edge=LEFT).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.5)
            tags.add(hl, tag)
        self.at("主循环")
        self.play(FadeOut(enc), run_time=0.3)
        mark([0, 1, 2, 3, 4], "标记打开", "① 编号、标记打开", C_GREY)
        mark([5, 6, 7, 8], "连顶连底", "② 两个 if：连顶、连底", C_YELLOW)
        mark([9, 10, 11, 12, 13], "四个方向", "③ 合并打开的邻格", C_BLUE)
        mark([14, 15, 16], "同根", "④ 同根：答案 k + 1", C_GREEN)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 失分点：elif
    def pitfall_beat(self):
        self.beat("pitfall")
        n, m, ops = D.ONE_ROW
        inp = D.inp_of(n, m, ops)
        good, bad = D.run_io(D.solve_t5, inp), D.run_io(D.solve_t5_elif, inp)
        assert (good, bad) == ("1", "-1")
        h = T("⚠ 失分点：n = 1，第一行就是最后一行", 28, C_RED).move_to([0, 3.2, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        code_ok = code_block(["if r == 0:", "    union(u, TOP)", "if r == n - 1:", "    union(u, BOT)"], 24, C_GREEN, 0.1)
        code_bad = code_block(["if r == 0:", "    union(u, TOP)", "elif r == n - 1:", "    union(u, BOT)"], 24, C_RED, 0.1)
        b1 = Board(n, m, 0.75, [2.2, 1.25, 0], bars=True)
        b2 = Board(n, m, 0.75, [2.2, -1.45, 0], bars=True)
        code_ok.move_to([-5.9 + code_ok.width / 2, 1.25, 0])
        code_bad.move_to([-5.9 + code_bad.width / 2, -1.45, 0])
        for b in (b1, b2):
            b.topb.stretch_to_fit_height(0.32)
            b.botb.stretch_to_fit_height(0.32)
            b.topb.move_to(b.c + UP * (0.75 / 2 + 0.3))
            b.botb.move_to(b.c + DOWN * (0.75 / 2 + 0.3))
            b.topl.scale(0.85).move_to(b.topb)
            b.botl.scale(0.85).move_to(b.botb)
        r, c = ops[0][0] - 1, ops[0][1] - 1
        self.play(FadeIn(code_ok), FadeIn(b1), FadeIn(b1.bars()), run_time=0.6)
        self.at("同时连上")
        self.play(b1.cells[(r, c)].animate.set_fill(WHITE, 0.7), run_time=0.3)
        self.play(Create(b1.link_top(r, c, C_GREEN)), Create(b1.link_bot(r, c, C_GREEN)), run_time=0.5)
        self.add(b1.link_top(r, c, C_GREEN), b1.link_bot(r, c, C_GREEN))
        o1 = T(f"输出 {good}", 26, C_GREEN).next_to(b1.grid, RIGHT, buff=0.5)
        self.play(b1.cells[(r, c)].animate.set_fill(C_GREEN, 0.7), b1.topb.animate.set_stroke(C_GREEN, 3),
                  b1.botb.animate.set_stroke(C_GREEN, 3), FadeIn(o1), run_time=0.5)
        self.at("elif")
        self.play(FadeIn(code_bad), FadeIn(b2), FadeIn(b2.bars()), run_time=0.6)
        self.at("再跑一遍")
        self.play(b2.cells[(r, c)].animate.set_fill(WHITE, 0.7), run_time=0.3)
        lt = b2.link_top(r, c, C_BLUE)
        self.play(Create(lt), b2.topb.animate.set_stroke(C_BLUE, 3), run_time=0.5)
        dead = SurroundingRectangle(code_bad[2:], color=C_RED, buff=0.06)
        never = T("进不去", 22, C_RED).next_to(dead, RIGHT, buff=0.2)
        self.play(Create(dead), FadeIn(never), b2.cells[(r, c)].animate.set_fill(C_BLUE, 0.7), run_time=0.5)
        self.at("输出负一")
        o2 = T(f"输出 {bad}", 26, C_RED).next_to(b2.grid, RIGHT, buff=0.5)
        self.play(FadeIn(o2, scale=1.2), run_time=0.5)
        self.at("各自判断")
        self.play(Indicate(code_ok[2], color=C_GREEN), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        head = T("回顾", 34, C_YELLOW).move_to([0, 2.9, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)
        rows = [("只开不关", "并查集增量合并，不再每次 BFS", "增量"),
                ("整行对整行", "加 TOP、BOT，渗透 ⟺ 同根", "整行"),
                ("坐标编号", "u = r·m + c，虚拟结点 nm、nm+1", "坐标"),
                ("边界", "n = 1 必测：两个 if，不写 elif", "一定要测")]
        tab = VGroup()
        for a, b, _ in rows:
            tab.add(VGroup(T(a, 28, C_BLUE), T(b, 26)))
        wa = max(r[0].width for r in tab)
        for i, r in enumerate(tab):
            y = 1.7 - 0.85 * i
            r[0].move_to([-5.6 + r[0].width / 2, y, 0])
            r[1].move_to([-5.6 + wa + 0.6 + r[1].width / 2, y, 0])
        for r, (*_, key) in zip(tab, rows):
            self.at(key)
            self.play(FadeIn(r, shift=UP * 0.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 11 月月考讲评与阶段复习 · OpenJudge M31533", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
