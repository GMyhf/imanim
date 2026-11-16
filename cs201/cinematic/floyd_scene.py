"""Floyd：一次算出所有点对（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。矩阵初值、每轮变小的格、错误循环次序的结果、
「最小化最大距离」的答案都来自 floyddata（讲义 floyd、RumorNetwork.best_source 原样插桩；test_floyd.py 用 n 次
Dijkstra、Bellman-Ford、穷举简单路径对撞）。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import floyddata as D  # noqa: E402
from cine import *  # noqa: E402,F403

INF = D.INF
# 平面排布：B1 B3 B5 外三角，B2 在内，B4 挂在 B1–B3 边外侧——十条边没有交叉
GPOS = {0: (-6.0, -1.5), 4: (-0.9, -1.5), 2: (-3.45, 2.9), 1: (-3.45, 0.25), 3: (-6.4, 1.9)}
SIDE = {(0, 1): -1, (2, 4): -1}   # 权值标签放在行进方向左手边的边（其余放右手边），避免挤进中间
R = 0.36
CELL = 0.8
MX, MY = 2.95, 0.8          # 矩阵中心


def num(v, color=WHITE, s=0.62):
    return MathTex(r"\infty" if v == INF else str(int(v)), color=color).scale(s)


def cell_center(i, j):
    return np.array([MX + (j - 2) * CELL, MY + (2 - i) * CELL, 0])


class FloydLesson(Lesson):
    def construct(self):
        for b in ("title", "problem", "matrix", "idea", "code", "run", "order", "answer", "compare", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key, default=None):
        for c in self.cue_times():
            if key in c["text"]:
                k = c["text"].index(key)
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return self.now if default is None else default

    def wait_key(self, key):
        self.wait_until(self.at(key))

    # ---------------------------------------------------------------- 片头：矩阵上扫过的十字
    def title_beat(self):
        self.beat("title")
        rng = random.Random(3)
        n = 6
        edges = [(u, v, rng.randint(1, 9)) for u in range(n) for v in range(n) if u != v and rng.random() < 0.3]
        _, snaps, changes = D.floyd_trace(n, edges)
        c = 0.62
        org = np.array([0, -0.55, 0])
        pos = lambda i, j: org + np.array([(j - (n - 1) / 2) * c, ((n - 1) / 2 - i) * c, 0])  # noqa: E731
        grid = VGroup(*[Square(c, stroke_color=C_GREY, stroke_width=1.5).move_to(pos(i, j))
                        for i in range(n) for j in range(n)])
        vals = {(i, j): num(snaps[0][i][j], C_GREY, 0.5).move_to(pos(i, j)) for i in range(n) for j in range(n)}
        self.play(FadeIn(grid), *[FadeIn(v) for v in vals.values()], run_time=0.8)
        step = max(0.3, min(0.9, (self.left() * 0.55) / n))
        for k in range(n):
            row = Rectangle(width=c * n, height=c, stroke_color=C_YELLOW, stroke_width=3).move_to(org + np.array([0, ((n - 1) / 2 - k) * c, 0]))
            col = Rectangle(width=c, height=c * n, stroke_color=C_YELLOW, stroke_width=3).move_to(org + np.array([(k - (n - 1) / 2) * c, 0, 0]))
            self.play(FadeIn(row), FadeIn(col), run_time=step * 0.35)
            anims = []
            for i, j, _, new in changes[k]:
                nv = num(new, C_YELLOW, 0.5).move_to(pos(i, j))
                anims.append(Transform(vals[(i, j)], nv))
            if anims:
                self.play(*anims, run_time=step * 0.4)
            self.play(FadeOut(row), FadeOut(col), run_time=step * 0.25)
        title = T("Floyd", 72).move_to([0, 3.0, 0])
        sub = T("一次算出所有点对", 32, C_YELLOW).next_to(title, DOWN, buff=0.15)
        self.wait_key("这一集")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), *[v.animate.set_color(WHITE) for v in vals.values()],
                  run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(grid, *vals.values(), title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 图
    def build_graph(self):
        nodes = {k: VGroup(Circle(R, stroke_color=WHITE, stroke_width=3), MathTex(D.LABELS[k]).scale(0.7)).move_to([*p, 0])
                 for k, p in GPOS.items()}
        pairs = {(u, v) for u, v, _ in D.EDGES if any(a == v and b == u for a, b, _ in D.EDGES)}
        arrows, wl = {}, {}
        for u, v, w in D.EDGES:
            p, q = nodes[u].get_center(), nodes[v].get_center()
            d = (q - p) / np.linalg.norm(q - p)
            nrm = rotate_vector(d, -PI / 2) * SIDE.get((u, v), 1)    # 行进方向右手边
            if (u, v) in pairs:
                off = nrm * 0.16
                a = Arrow(p + d * R + off, q - d * R + off, buff=0.02, stroke_width=3, color=C_GREY, tip_length=0.18,
                          max_tip_length_to_length_ratio=0.12)
                lab_at = (p + q) / 2 + nrm * 0.42
            else:
                a = Arrow(p, q, buff=R + 0.03, stroke_width=3, color=C_GREY, tip_length=0.18,
                          max_tip_length_to_length_ratio=0.12)
                lab_at = (p + q) / 2 + nrm * 0.3
            arrows[(u, v)] = a
            wl[(u, v)] = MathTex(str(w), color=C_YELLOW).scale(0.62).move_to(lab_at)
        return nodes, arrows, wl

    def graph_group(self):
        return VGroup(*self.arrows.values(), *self.wlabs.values(), *self.nodes.values())

    # ---------------------------------------------------------------- 股市的传言
    def problem_beat(self):
        self.beat("problem")
        nodes, arrows, wl = self.build_graph()
        self.nodes, self.arrows, self.wlabs = nodes, arrows, wl
        head = T("股市的传言", 30, C_BLUE).move_to([2.9, 3.2, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(n, scale=0.6) for n in nodes.values()], lag_ratio=0.12),
                  run_time=1.2)
        self.wait_key("箭头表示")
        self.play(*[GrowArrow(a) for a in arrows.values()], run_time=1.2)
        self.wait_key("数字是要花的时间")
        self.play(LaggedStart(*[FadeIn(w, scale=1.3) for w in wl.values()], lag_ratio=0.06), run_time=1.0)
        self.wait_key("一号传给五号")
        e1, e2 = (0, 4), (4, 0)
        self.play(arrows[e1].animate.set_color(C_GREEN).set_stroke(width=5), Indicate(wl[e1], scale_factor=1.6),
                  run_time=0.8)
        self.wait_key("五号传回一号")
        self.play(arrows[e2].animate.set_color(C_RED).set_stroke(width=5), Indicate(wl[e2], scale_factor=1.6),
                  run_time=0.8)
        self.wait_key("问题是")
        q = VGroup(T("从谁开始散布消息，", 26), T("能让所有人最快都知道？", 26)).arrange(DOWN, buff=0.15).move_to([2.9, 1.5, 0])
        self.play(FadeIn(q, shift=UP * 0.2), arrows[e1].animate.set_color(C_GREY).set_stroke(width=3),
                  arrows[e2].animate.set_color(C_GREY).set_stroke(width=3), run_time=0.9)
        self.wait_key("先得知道")
        need = T("先求：任意两人之间的最短时间", 26, C_YELLOW).move_to([2.9, -0.2, 0])
        self.play(FadeIn(need, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, q, need)), run_time=0.6)

    # ---------------------------------------------------------------- 相邻矩阵
    def matrix_beat(self):
        self.beat("matrix")
        n = D.N
        cells = {(i, j): Square(CELL, stroke_color=C_GREY, stroke_width=2).move_to(cell_center(i, j))
                 for i in range(n) for j in range(n)}
        rh = VGroup(*[MathTex(D.LABELS[i], color=C_BLUE).scale(0.6).move_to(cell_center(i, 0) + LEFT * 0.75) for i in range(n)])
        ch = VGroup(*[MathTex(D.LABELS[j], color=C_TEAL).scale(0.6).move_to(cell_center(0, j) + UP * 0.68) for j in range(n)])
        cap = VGroup(T("行：从谁", 20, C_BLUE), T("列：传给谁", 20, C_TEAL)).arrange(RIGHT, buff=0.5)
        cap.move_to([MX, MY - 2.65 * CELL - 0.15, 0])
        self.cells, self.rh, self.ch, self.cap = cells, rh, ch, cap
        self.play(FadeIn(VGroup(*cells.values())), FadeIn(rh), FadeIn(ch), run_time=0.8)
        self.wait_key("第几行第几列")
        self.play(FadeIn(cap), run_time=0.5)
        adj = D.adjacency()
        self.vals = {}
        flies = []
        for u, v, w in D.EDGES:
            t = num(w).move_to(cell_center(u, v))
            self.vals[(u, v)] = t
            flies.append(TransformFromCopy(self.wlabs[(u, v)], t))
        self.play(LaggedStart(*flies, lag_ratio=0.12), run_time=2.4)
        self.wait_key("对角线是零")
        zeros = [num(0, C_GREY).move_to(cell_center(i, i)) for i in range(n)]
        for i, z in enumerate(zeros):
            self.vals[(i, i)] = z
        self.play(LaggedStart(*[FadeIn(z, scale=1.4) for z in zeros], lag_ratio=0.12), run_time=1.0)
        self.wait_key("没有直接的边")
        infs = []
        for i in range(n):
            for j in range(n):
                if adj[i][j] == INF:
                    t = num(INF, C_GREY).move_to(cell_center(i, j))
                    self.vals[(i, j)] = t
                    infs.append(t)
        self.play(LaggedStart(*[FadeIn(t) for t in infs], lag_ratio=0.05), run_time=1.2)
        self.wait_key("这是算法的输入")
        box = SurroundingRectangle(VGroup(*cells.values()), color=C_BLUE, buff=0.06)
        self.play(Create(box), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(box), run_time=0.4)

    def matrix_group(self):
        return VGroup(*self.cells.values(), self.rh, self.ch, self.cap, *self.vals.values())

    # ---------------------------------------------------------------- 一次放开一个中转点
    def idea_beat(self):
        self.beat("idea")
        dp = T("动态规划：一次只多放开一个中转点", 26, C_YELLOW).move_to([0, 3.45, 0])
        self.play(FadeIn(dp, shift=DOWN * 0.2), run_time=0.8)
        self.wait_key("从甲到乙")
        # 在图上指一个具体例子：五号到四号，直接没有边；经一号中转
        i, k, j = 4, 0, 3
        tags = VGroup(T("甲", 22, C_GREEN).next_to(self.nodes[i], DOWN, buff=0.12),
                      T("中转", 22, C_YELLOW).next_to(self.nodes[k], DOWN, buff=0.12),
                      T("乙", 22, C_RED).next_to(self.nodes[j], UP, buff=0.12))
        self.play(FadeIn(tags), run_time=0.6)
        self.play(self.arrows[(i, k)].animate.set_color(C_YELLOW).set_stroke(width=5),
                  self.arrows[(k, j)].animate.set_color(C_YELLOW).set_stroke(width=5), run_time=0.8)
        f = MathTex(r"d[i][j]", r"\leftarrow", r"\min(", r"d[i][j]", ",", r"\ d[i][k]+d[k][j]", ")").scale(0.72)
        f[3].set_color(C_GREY)
        f[5].set_color(C_YELLOW)
        f.move_to([2.95, -2.2, 0])
        lg = T("i 起点   j 终点   k 中转点", 20, C_GREY).next_to(f, DOWN, buff=0.15)
        self.play(FadeOut(self.cap), Write(f), FadeIn(lg), run_time=1.2)
        self.wait_key("放开第几个中转点")
        mean = T("放开前 k 个中转点后：每格 = 只经过它们的最短距离", 22, C_TEAL).move_to([0, 3.45, 0])
        self.play(ReplacementTransform(dp, mean), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tags, mean)), self.arrows[(i, k)].animate.set_color(C_GREY).set_stroke(width=3),
                  self.arrows[(k, j)].animate.set_color(C_GREY).set_stroke(width=3), run_time=0.6)
        self.formula = VGroup(f, lg)

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="for k in range(n):\n    for i in range(n):\n        for j in range(n):\n"
                                "            if d[i][k] + d[k][j] < d[i][j]:\n"
                                "                d[i][j] = d[i][k] + d[k][j]",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 26})
        code.scale_to_fit_width(6.9)
        code.move_to([-3.5, 0.3, 0])
        g = self.graph_group()
        self.play(FadeOut(g), run_time=0.6)
        self.play(FadeIn(code, shift=RIGHT * 0.3), run_time=0.7)
        ln = code.code_lines
        hls = VGroup()

        def mark(lines, key, col, note=None):
            self.wait_key(key)
            hl = SurroundingRectangle(VGroup(*[ln[k] for k in lines]), color=col, buff=0.05, stroke_width=2.5)
            anims = [Create(hl)]
            if note is not None:
                anims.append(FadeIn(note))
            self.play(*anims, run_time=0.6)
            hls.add(hl)
            if note is not None:
                hls.add(note)
        n1 = T("中转点：最外层", 22, C_YELLOW).next_to(code, UP, buff=0.25).align_to(code, LEFT)
        mark([0], "最外层", C_YELLOW, n1)
        mark([1, 2], "里面两层", C_BLUE)
        mark([3, 4], "两段都能走通", C_GREEN)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, hls)), run_time=0.6)

    # ---------------------------------------------------------------- 跑一遍
    def run_beat(self):
        self.beat("run")
        self.play(FadeIn(self.graph_group()), run_time=0.8)
        _, snaps, changes = D.floyd_trace()
        n = D.N
        keys = {0: "放开一号", 1: "放开二号", 4: "最后放开五号"}
        head = None
        for k in range(n):
            if k in keys:
                self.wait_key(keys[k])
            elif k in (2, 3):
                self.wait(0.15)
            row = SurroundingRectangle(VGroup(*[self.cells[(k, j)] for j in range(n)]), color=C_YELLOW, buff=0.0,
                                       stroke_width=3)
            col = SurroundingRectangle(VGroup(*[self.cells[(i, k)] for i in range(n)]), color=C_YELLOW, buff=0.0,
                                       stroke_width=3)
            h = VGroup(T("中转点", 24, C_YELLOW), MathTex(D.LABELS[k], color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.15)
            h.move_to([MX, 3.45, 0])
            anims = [Create(row), Create(col), self.nodes[k][0].animate.set_stroke(C_YELLOW, 5)]
            anims.append(FadeIn(h) if head is None else ReplacementTransform(head, h))
            if k > 0:
                anims.append(self.nodes[k - 1][0].animate.set_stroke(WHITE, 3))
            self.play(*anims, run_time=0.6 if k in keys else 0.45)
            head = h
            if k == 0:
                self.wait_key("五号到四号原来")
            if k == 4:
                self.wait_key("二号到一号")
            for (i, j, old, new) in changes[k]:
                if (i, j) == (1, 3):
                    self.wait_key("二号到四号")
                a, b = self.vals[(i, k)], self.vals[(k, j)]
                hi = VGroup(SurroundingRectangle(self.cells[(i, k)], color=C_GREEN, buff=0.03, stroke_width=4),
                            SurroundingRectangle(self.cells[(k, j)], color=C_GREEN, buff=0.03, stroke_width=4))
                tgt = SurroundingRectangle(self.cells[(i, j)], color=C_RED, buff=0.03, stroke_width=4)
                self.play(Create(tgt), *[Indicate(x, color=C_GREEN, scale_factor=1.4) for x in (a, b)],
                          Create(hi), run_time=0.7)
                route = D.route(i, j)
                path_edges = [(route[t], route[t + 1]) for t in range(len(route) - 1)]
                if k == 0:
                    self.wait_key("绕道一号")
                sm = MathTex(f"{int(snaps[k][i][k])}+{int(snaps[k][k][j])}={int(new)}", color=C_YELLOW).scale(0.7)
                sm.move_to([MX, -1.55, 0])
                nv = num(new, C_YELLOW).move_to(self.cells[(i, j)])
                self.play(FadeIn(sm, shift=UP * 0.15),
                          *[self.arrows[e].animate.set_color(C_GREEN).set_stroke(width=5) for e in path_edges],
                          run_time=0.6)
                self.play(Transform(self.vals[(i, j)], nv), Flash(self.cells[(i, j)], color=C_YELLOW, flash_radius=0.5),
                          run_time=0.7)
                self.wait(0.8)
                self.play(FadeOut(VGroup(hi, tgt, sm)),
                          *[self.arrows[e].animate.set_color(C_GREY).set_stroke(width=3) for e in path_edges],
                          run_time=0.4)
            if k in (1, 2, 3):
                self.wait(0.5)
            if k == 3:
                nochg = T("没有一格变小", 22, C_GREY).move_to([MX, -1.55, 0])
                self.play(FadeIn(nochg), run_time=0.4)
                self.wait(0.6)
                self.play(FadeOut(nochg), run_time=0.3)
            self.play(FadeOut(row), FadeOut(col), run_time=0.3)
        self.play(self.nodes[n - 1][0].animate.set_stroke(WHITE, 3), FadeOut(head), run_time=0.4)
        self.wait_key("这个九")
        nine = VGroup(SurroundingRectangle(self.cells[(4, 3)], color=C_YELLOW, buff=0.03, stroke_width=4),
                      SurroundingRectangle(self.cells[(1, 3)], color=C_YELLOW, buff=0.03, stroke_width=4))
        r = D.route(1, 3)
        pe = [(r[t], r[t + 1]) for t in range(len(r) - 1)]
        fin, _, _ = D.floyd_trace()
        eq = MathTex(str(int(fin[1][3])), "=", str(int(fin[1][4])), "+", str(int(fin[4][3]))).scale(0.75)
        eq[0].set_color(C_YELLOW)
        eq[4].set_color(C_YELLOW)
        eq.move_to([MX, -1.5, 0])
        self.play(Create(nine), FadeIn(eq[:4]), TransformFromCopy(self.vals[(4, 3)], eq[4]),
                  *[self.arrows[e].animate.set_color(C_YELLOW).set_stroke(width=5) for e in pe], run_time=1.2)
        arr = eq
        self.wait_key("前面的结果")
        dpn = T("前面的结果被后面接着用：动态规划", 24, C_YELLOW).move_to([MX, -1.5, 0])
        self.play(FadeOut(eq), FadeIn(dpn, shift=UP * 0.15), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(nine, dpn)),
                  *[self.arrows[e].animate.set_color(C_GREY).set_stroke(width=3) for e in pe], run_time=0.6)

    # ---------------------------------------------------------------- 为什么中转点在最外层
    def order_beat(self):
        self.beat("order")
        keep = VGroup(self.graph_group(), self.matrix_group(), self.formula)
        self.play(FadeOut(keep), run_time=0.7)
        title = T("中转点必须在最外层", 30, C_YELLOW).move_to([0, 3.3, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.wait_key("看一个小例子")
        xs = {0: -4.5, 2: -1.5, 3: 1.5, 1: 4.5}
        ns = {k: VGroup(Circle(0.36, stroke_color=WHITE, stroke_width=3), MathTex(str(k)).scale(0.8)).move_to([x, 1.8, 0])
              for k, x in xs.items()}
        ars = VGroup(*[Arrow(ns[u].get_center(), ns[v].get_center(), buff=0.4, stroke_width=3, color=C_GREY, tip_length=0.18)
                       for u, v, _ in D.CHAIN])
        ws = VGroup(*[MathTex("1", color=C_YELLOW).scale(0.65).next_to(a, UP, buff=0.08) for a in ars])
        self.play(*[FadeIn(x) for x in ns.values()], *[GrowArrow(a) for a in ars], FadeIn(ws), run_time=1.0)
        self.wait_key("如果把中转点放到最内层")
        bad = Code(code_string="for i in range(n):\n    for j in range(n):\n        for k in range(n):   # 错\n"
                               "            d[i][j] = min(d[i][j], d[i][k] + d[k][j])",
                   language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                   paragraph_config={"font": MONO, "font_size": 24})
        bad.scale_to_fit_width(6.9)
        bad.move_to([-3.5, -0.75, 0])
        self.play(FadeIn(bad, shift=UP * 0.2), run_time=0.7)
        wrong = D.floyd_wrong_order()
        right, _, _ = D.floyd_trace(D.CHAIN_N, D.CHAIN)
        self.wait_key("先算零到一")
        lines = VGroup(VGroup(MathTex(r"d[0][3]=\infty").scale(0.72), T("这一行还没算到", 20, C_GREY)).arrange(RIGHT, buff=0.25),
                       VGroup(MathTex(r"d[2][1]=\infty").scale(0.72), T("这一行还没轮到", 20, C_GREY)).arrange(RIGHT, buff=0.25))
        lines.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([3.4, 0.0, 0])
        self.play(FadeIn(lines[0], shift=LEFT * 0.2), Indicate(ns[0]), Indicate(ns[1]), run_time=0.8)
        self.play(FadeIn(lines[1], shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("结果就停在无穷")
        res = MathTex(r"d[0][1]=" + (r"\infty" if wrong[0][1] == INF else str(wrong[0][1])), color=C_RED).scale(0.85)
        res.move_to([3.4, -1.3, 0])
        cross = T("✗", 30, C_RED).next_to(res, RIGHT, buff=0.25)
        self.play(Write(res), FadeIn(cross), run_time=0.8)
        self.wait_key("可真正的答案是三")
        ok = VGroup(T("真正的答案", 22, C_GREEN), MathTex(str(int(right[0][1])), color=C_GREEN).scale(0.9)).arrange(RIGHT, buff=0.2)
        ok.next_to(res, DOWN, buff=0.3)
        self.play(FadeIn(ok), *[a.animate.set_color(C_GREEN) for a in ars], run_time=0.8)
        self.wait_key("中转点在外层")
        concl = T("中转点在外层：用到的每一格都是上一轮的定稿", 24, C_YELLOW).move_to([0, -2.55, 0])
        self.play(FadeIn(concl, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, *ns.values(), ars, ws, bad, lines, res, cross, ok, concl)), run_time=0.6)

    # ---------------------------------------------------------------- 回到传言：最小化最大距离
    def answer_beat(self):
        self.beat("answer")
        self.play(FadeIn(self.graph_group()), FadeIn(VGroup(*self.cells.values(), self.rh, self.ch, *self.vals.values())),
                  run_time=0.9)
        best, ecc = D.best_source()
        n = D.N
        mh = T("最大", 20, C_YELLOW).move_to(cell_center(0, n - 1) + np.array([CELL + 0.25, 0.68, 0]))
        self.wait_key("对每个起点")
        mx = []
        for i in range(n):
            col = C_RED if ecc[i] == INF else C_YELLOW
            mx.append(num(ecc[i], col).move_to(cell_center(i, n - 1) + RIGHT * (CELL + 0.25)))
        self.play(FadeIn(mh), run_time=0.4)
        for i in range(n):
            rowr = SurroundingRectangle(VGroup(*[self.cells[(i, j)] for j in range(n)]), color=C_GREY, buff=0.0)
            self.play(Create(rowr), run_time=0.25)
            self.play(FadeIn(mx[i], shift=RIGHT * 0.2), FadeOut(rowr), run_time=0.4)
        self.wait_key("这几行都有无穷")
        bad_rows = [i for i in range(n) if ecc[i] == INF]
        self.play(*[Indicate(mx[i], color=C_RED, scale_factor=1.4) for i in bad_rows], run_time=0.9)
        self.wait_key("只有三号这一行")
        brow = SurroundingRectangle(VGroup(*[self.cells[(best, j)] for j in range(n)], mx[best]), color=C_GREEN, buff=0.04,
                                    stroke_width=4)
        tree = [(best, j) for j in range(n) if j != best and (best, j) in self.arrows]
        self.play(Create(brow), self.nodes[best][0].animate.set_stroke(C_GREEN, 5),
                  *[self.arrows[e].animate.set_color(C_GREEN).set_stroke(width=5) for e in tree], run_time=1.0)
        self.wait_key("答案是三号")
        ans = VGroup(T("答案", 26), MathTex(D.LABELS[best], color=C_GREEN).scale(0.9), T("，", 26),
                     MathTex(str(int(ecc[best])), color=C_YELLOW).scale(0.9), T("个时间单位", 26)).arrange(RIGHT, buff=0.12)
        ans.move_to([MX, -1.55, 0])
        self.play(FadeIn(ans, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(self.graph_group(), *self.cells.values(), self.rh, self.ch, *self.vals.values(),
                                 mh, *mx, brow, ans)), run_time=0.6)

    # ---------------------------------------------------------------- 复杂度与比较
    def compare_beat(self):
        self.beat("compare")
        big = MathTex(r"O(n^3)", color=C_YELLOW).scale(1.4).move_to([0, 2.4, 0])
        self.play(Write(big), run_time=0.9)
        cards = VGroup()
        for head, body, col in (("n 次 Dijkstra", "同一数量级", C_BLUE), ("Floyd", "三行循环", C_GREEN),
                                ("负权边", "可以，只要没有负环", C_RED)):
            box = RoundedRectangle(corner_radius=0.2, width=3.9, height=1.8, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06)
            cards.add(VGroup(box, VGroup(T(head, 28, col), T(body, 22)).arrange(DOWN, buff=0.25).move_to(box)))
        cards.arrange(RIGHT, buff=0.35).move_to([0, -0.1, 0])
        self.wait_key("对每个点各跑一次")
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.7)
        self.wait_key("但弗洛伊德")
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.7)
        self.wait_key("边权有负数")
        self.play(FadeIn(cards[2], shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(big, cards)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(T("一次放开一个中转点", 34), T("留下更短的那条路", 34, C_YELLOW),
                      T("中转点在最外层", 34, C_GREEN)).arrange(DOWN, buff=0.4).move_to([0, 0.8, 0])
        self.play(FadeIn(rows[0], shift=UP * 0.2), run_time=0.7)
        self.wait_key("留下更短")
        self.play(FadeIn(rows[1], shift=UP * 0.2), run_time=0.7)
        self.wait_key("中转点在最外层")
        self.play(FadeIn(rows[2], shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 1 周 股市的传言 · 第 7 周 图 5.2 节 Floyd", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
