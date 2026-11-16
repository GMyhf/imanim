"""网格上走：DP 还是搜索（3B1B 风格）。bfs、dijkstra 两支片之后，讲两者与动态规划的分界。

由 make.py 驱动，时间轴约定见 cine.py。网格、dp 表、照搬四方向的错误表、出堆顺序与路径计数全部来自 griddata
（讲义 min_path_sum / dijkstra 原样；test_grid.py 对撞枚举路径、松弛到收敛的真最短、拓扑序与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import griddata as D  # noqa: E402
from cine import *  # noqa: E402,F403

DP_COL, SR_COL = C_TEAL, C_BLUE


def tex(v, scale=0.62, color=WHITE):
    return MathTex(r"\infty" if v == D.INF else str(v), color=color).scale(scale)


def cell_centers(n, m, center, pitch):
    c = np.array([*center[:2], 0], dtype=float)
    return {(i, j): c + np.array([(j - (m - 1) / 2) * pitch, ((n - 1) / 2 - i) * pitch, 0])
            for i in range(n) for j in range(m)}


def make_grid(vals, center, pitch=1.0, size=0.82, color=C_GREY, scale=0.62, num_color=WHITE):
    """方格：{(i, j): VGroup(框, 数字)}。vals[i][j] 为 None 只画空框。框用不透明底色，路径线放下层。"""
    n, m = len(vals), len(vals[0])
    pos = cell_centers(n, m, center, pitch)
    out = {}
    for (i, j), p in pos.items():
        box = Square(size, stroke_color=color, stroke_width=2.5).set_fill(BG, 1).move_to(p)
        v = vals[i][j]
        lab = tex(v, scale, num_color).move_to(p) if v is not None else VMobject()
        out[(i, j)] = VGroup(box, lab)
    return out


def path_line(cells, path, color=C_YELLOW, width=7):
    line = VMobject(stroke_color=color, stroke_width=width).set_points_as_corners(
        [cells[c][0].get_center() for c in path])
    return line.set_z_index(-1)


def val_color(v):
    return C_RED if v == 9 else WHITE


class GridLesson(Lesson):
    def construct(self):
        for b in ("title", "table", "dp", "order", "four", "cycle", "dijkstra", "count", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def grid4(self, center, pitch=1.02, size=0.86):
        g = D.G4
        cells = make_grid(g, center, pitch, size, scale=0.72)
        for (i, j), c in cells.items():
            c[1].set_color(C_RED if g[i][j] == 9 else WHITE)
        return cells

    # ---------------------------------------------------------------- 片头：两道长得一样的题
    def title_beat(self):
        self.beat("title")
        title = T("网格上走", 54).move_to([0, 2.95, 0])
        sub = T("DP 还是搜索", 32, C_YELLOW).next_to(title, DOWN, buff=0.15)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        L = make_grid(D.G0, [-3.4, -0.3], 0.95, 0.8)
        R = make_grid(D.G0, [3.4, -0.3], 0.95, 0.8)
        for cells, col in ((L, DP_COL), (R, SR_COL)):
            cells[(0, 0)][0].set_stroke(C_GREEN, 3.5)
            cells[(2, 2)][0].set_stroke(C_RED, 3.5)
        self.play(*[FadeIn(c) for c in [*L.values(), *R.values()]], run_time=0.9)
        self.wait_until(self.cue_start("只许往右", self.now))
        arrows_l = VGroup(Arrow(ORIGIN, RIGHT * 0.9, buff=0, color=DP_COL, stroke_width=6),
                          Arrow(ORIGIN, DOWN * 0.9, buff=0, color=DP_COL, stroke_width=6))
        arrows_l.arrange(RIGHT, buff=0.4).next_to(L[(0, 1)], UP, buff=0.35)
        rule_l = T("只许右、下", 26, DP_COL).next_to(L[(2, 1)], DOWN, buff=0.3)
        self.play(GrowArrow(arrows_l[0]), GrowArrow(arrows_l[1]), FadeIn(rule_l), run_time=0.9)
        self.wait_until(self.cue_start("四个方向", self.now))
        cross = VGroup(*[Arrow(ORIGIN, d * 0.55, buff=0, color=SR_COL, stroke_width=6) for d in (UP, DOWN, LEFT, RIGHT)])
        cross.next_to(R[(0, 1)], UP, buff=0.2)
        rule_r = T("四个方向都能走", 26, SR_COL).next_to(R[(2, 1)], DOWN, buff=0.3)
        self.play(*[GrowArrow(a) for a in cross], FadeIn(rule_r), run_time=0.9)
        self.wait_until(self.cue_start("前一道", self.now))
        m_l = T("动态规划", 32, DP_COL).next_to(rule_l, DOWN, buff=0.2)
        m_r = T("搜索", 32, SR_COL).next_to(rule_r, DOWN, buff=0.2)
        self.play(FadeIn(m_l, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(m_r, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("分界线", self.now))
        sep = DashedLine([0, 1.6, 0], [0, -2.6, 0], color=C_YELLOW, dash_length=0.15)
        q = T("？", 48, C_YELLOW).move_to([0, -0.4, 0]).set_z_index(2)
        bg = Square(0.8, stroke_width=0).set_fill(BG, 1).move_to(q)
        self.play(Create(sep), FadeIn(bg), FadeIn(q, scale=1.4), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, sub, *L.values(), *R.values(), arrows_l, rule_l, cross, rule_r, m_l, m_r,
                                 sep, q, bg)), run_time=0.6)

    # ---------------------------------------------------------------- 讲义的判断表
    def table_beat(self):
        self.beat("table")
        rows = [("只能向右 / 向下（无环，有拓扑序）", "DP", DP_COL, "向右"),
                ("可以四方向走（有环）", "BFS / Dijkstra", SR_COL, "四个方向"),
                ("求方案数、路径和最大值，方向单调", "DP", DP_COL, "方案数"),
                ("求最短步数 / 最少代价，方向任意", "搜索", SR_COL, "最短步数")]
        xl, xr, y0, dy = -5.9, 3.0, 1.45, 0.82
        head = VGroup(T("条件", 26, C_GREY).move_to([xl, y0 + 0.85, 0], aligned_edge=LEFT),
                      T("方法", 26, C_GREY).move_to([xr, y0 + 0.85, 0], aligned_edge=LEFT))
        rule0 = Line([xl - 0.1, y0 + 0.45, 0], [6.1, y0 + 0.45, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(head), Create(rule0), run_time=0.6)
        group = VGroup()
        for k, (cond, meth, col, key) in enumerate(rows):
            y = y0 - k * dy
            self.wait_until(self.cue_start(key, self.now))
            r = VGroup(T(cond, 28).move_to([xl, y, 0], aligned_edge=LEFT),
                       T(meth, 30, col).move_to([xr, y, 0], aligned_edge=LEFT),
                       Line([xl - 0.1, y - dy / 2, 0], [6.1, y - dy / 2, 0], color=C_GREY, stroke_width=1,
                            stroke_opacity=0.4))
            group.add(r)
            self.play(FadeIn(r, shift=RIGHT * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("判据只有一条", self.now))
        box = RoundedRectangle(corner_radius=0.2, width=6.2, height=1.0, stroke_color=C_YELLOW, stroke_width=3)
        box.move_to([0, -2.3, 0])
        crit = T("判据：有没有环", 34, C_YELLOW).move_to(box)
        self.play(Create(box), Write(crit), run_time=1.0)
        ring = VGroup(*[SurroundingRectangle(group[k][0], color=C_YELLOW, buff=0.06,
                                             stroke_width=2) for k in (0, 1)])
        self.play(Create(ring), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, rule0, group, box, crit, ring)), run_time=0.6)

    # ---------------------------------------------------------------- 讲义例子：DP 填表
    def dp_beat(self):
        self.beat("dp")
        g = D.G0
        dp, order = D.dp_table(g)
        L = make_grid(g, [-3.3, -0.05], 1.15, 0.95, scale=0.8)
        R = make_grid([[None] * 3 for _ in range(3)], [3.3, -0.05], 1.15, 0.95, color=DP_COL)
        lt = T("网格", 26, C_GREY).next_to(VGroup(*L.values()), UP, buff=0.3)
        rt = Text("dp[i][j] = 走到这一格的最小路径和", font=MONO, font_size=24, color=DP_COL)
        rt.next_to(VGroup(*R.values()), UP, buff=0.3)
        rt.shift(RIGHT * min(0, 6.9 - rt.get_right()[0]))
        self.play(*[FadeIn(c) for c in L.values()], FadeIn(lt), run_time=0.8)
        self.wait_until(self.cue_start("dp 表示", self.now))
        self.play(*[FadeIn(c[0]) for c in R.values()], FadeIn(rt), run_time=0.8)
        labs = {}

        def fill(items, rt_):
            anims = []
            for i, j, src in items:
                lab = tex(dp[i][j], 0.8, DP_COL).move_to(R[(i, j)][0])
                labs[(i, j)] = lab
                srcs = [L[(i, j)][1]] + ([labs[src]] if src else [])
                anims.append(TransformFromCopy(VGroup(*srcs), lab))
            self.play(LaggedStart(*anims, lag_ratio=0.35), run_time=rt_)

        self.wait_until(self.cue_start("第一行只能", self.now))
        fill([o for o in order if o[0] == 0], 1.4)
        self.wait_until(self.cue_start("第一列只能", self.now))
        fill([o for o in order if o[1] == 0 and o[0] > 0], 1.0)
        self.wait_until(self.cue_start("其余格子", self.now))
        rest = [o for o in order if o[0] > 0 and o[1] > 0]
        t_end = self.cue_start("填到右下角", self.now + 4)
        for k, (i, j, src) in enumerate(rest):
            up, lf = R[(i - 1, j)][0], R[(i, j - 1)][0]
            win = up if src == (i - 1, j) else lf
            hl = VGroup(SurroundingRectangle(up, color=C_GREY, buff=0.03, stroke_width=3),
                        SurroundingRectangle(lf, color=C_GREY, buff=0.03, stroke_width=3))
            rt_ = max(0.4, min(1.0, (t_end - self.now) / (len(rest) - k) / 2))
            self.play(FadeIn(hl), run_time=rt_ * 0.5)
            self.play(hl[0 if win is up else 1].animate.set_color(C_YELLOW), run_time=rt_ * 0.4)
            fill([(i, j, src)], rt_ * 0.8)
            self.play(FadeOut(hl), run_time=rt_ * 0.3)
        self.wait_until(self.cue_start("填到右下角", self.now))
        path = D.dp_path(g)
        line = path_line(L, path)
        rline = path_line(R, path)
        ans = VGroup(T("答案", 28), tex(D.min_path_sum(g), 1.0, C_YELLOW)).arrange(RIGHT, buff=0.25)
        ans.next_to(VGroup(*R.values()), DOWN, buff=0.3)
        self.play(R[(2, 2)][0].animate.set_stroke(C_YELLOW, 4), Indicate(labs[(2, 2)], color=C_YELLOW),
                  FadeIn(ans), run_time=0.9)
        self.wait_until(self.cue_start("一、三、一", self.now))
        self.play(Create(line), Create(rline), *[L[c][0].animate.set_stroke(C_YELLOW, 3.5) for c in path], run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*L.values(), lt, line, rline, ans, rt)), *[FadeOut(R[c][0]) for c in R],
                  *[labs[c].animate.move_to(self.node_pos(c)) for c in labs], run_time=0.8)
        self.dp_labs = labs

    # ---------------------------------------------------------------- 依赖箭头与拓扑序
    @staticmethod
    def node_pos(c, center=(-2.2, 0.1), pitch=2.0):
        return cell_centers(3, 3, [*center, 0], pitch)[c]

    def order_beat(self):
        self.beat("order")
        labs = self.dp_labs
        nodes = {c: Circle(0.42, stroke_color=DP_COL, stroke_width=3).move_to(self.node_pos(c)) for c in labs}
        self.play(*[Create(n) for n in nodes.values()], run_time=0.7)
        arrows = VGroup()
        for (i, j) in nodes:
            for c in ((i - 1, j), (i, j - 1)):
                if c in nodes:
                    arrows.add(Arrow(nodes[c].get_center(), nodes[(i, j)].get_center(), buff=0.48, color=C_GREY,
                                     stroke_width=4, tip_length=0.22, max_tip_length_to_length_ratio=0.3))
        note = VGroup(T("箭头：谁依赖谁", 28, C_GREY), T("全部朝右或朝下", 28, C_YELLOW),
                      T("没有一条往回指", 28, C_YELLOW)).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        note.move_to([3.9, 1.3, 0])
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.12), FadeIn(note[0]), run_time=1.8)
        self.wait_until(self.cue_start("所有箭头", self.now))
        self.play(arrows.animate.set_color(C_YELLOW), FadeIn(note[1:], shift=UP * 0.15), run_time=0.9)
        self.wait_until(self.cue_start("按行从上到下", self.now))
        idx = VGroup()
        t_end = self.cue_start("轮到谁", self.now + 3)
        rt_ = max(0.3, min(0.6, (t_end - self.now) / 9))
        for k, c in enumerate(sorted(nodes)):
            lab = T(str(k + 1), 24, C_GREEN).next_to(nodes[c], UL, buff=-0.04)
            idx.add(lab)
            self.play(nodes[c].animate.set_fill(C_GREEN, 0.18).set_stroke(C_GREEN), FadeIn(lab, scale=1.3),
                      run_time=rt_)
        self.wait_until(self.cue_start("拓扑序", self.now))
        topo = VGroup(T("这样的顺序", 28), T("拓扑序", 44, C_GREEN)).arrange(DOWN, buff=0.2).move_to([3.9, -1.2, 0])
        self.play(FadeIn(topo[0]), Write(topo[1]), run_time=1.0)
        self.wait_until(self.cue_start("靠的就是它", self.now))
        self.play(Circumscribe(topo[1], color=C_GREEN), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*nodes.values(), *labs.values(), arrows, note, idx, topo)), run_time=0.6)

    # ---------------------------------------------------------------- 照搬到四方向
    def four_beat(self):
        self.beat("four")
        L = self.grid4([-3.6, 0.2])
        lt = T("四行五列，四个方向都能走", 24, C_GREY).next_to(VGroup(*L.values()), UP, buff=0.3)
        self.play(*[FadeIn(c) for c in L.values()], FadeIn(lt), run_time=1.0)
        legend = VGroup(VGroup(tex(9, 0.72, C_RED), T("高地", 24, C_GREY)).arrange(RIGHT, buff=0.15),
                        VGroup(tex(1, 0.72), T("平路", 24, C_GREY)).arrange(RIGHT, buff=0.15)).arrange(RIGHT, buff=0.5)
        legend.next_to(VGroup(*L.values()), DOWN, buff=0.3)
        self.wait_until(self.cue_start("九是高地", self.now))
        self.play(FadeIn(legend), run_time=0.6)
        self.wait_until(self.cue_start("照搬过来", self.now))
        R = make_grid([[D.INF] * 5 for _ in range(4)], [3.6, 0.2], 1.02, 0.86, color=C_PURPLE, scale=0.72,
                      num_color=C_GREY)
        rt = Text("dp = min(上, 下, 左, 右) + 自己", font=MONO, font_size=24, color=C_PURPLE)
        rt.next_to(VGroup(*R.values()), UP, buff=0.3)
        self.play(*[FadeIn(c[0]) for c in R.values()], FadeIn(rt), run_time=0.9)
        self.wait_until(self.cue_start("当成无穷大", self.now) - 0.3)
        self.play(LaggedStart(*[FadeIn(c[1]) for c in R.values()], lag_ratio=0.03), run_time=1.0)
        nv = D.naive_four(D.G4)
        self.wait_until(self.cue_start("填完", self.now))
        t_end = self.cue_start("右下角是十六", self.now + 2.5)
        labs = {}
        for i in range(4):
            new = {(i, j): tex(nv[i][j], 0.72, C_PURPLE).move_to(R[(i, j)][0]) for j in range(5)}
            rt_ = max(0.4, min(0.9, (t_end - self.now) / (4 - i)))
            self.play(*[FadeOut(R[c][1]) for c in new], *[FadeIn(v, scale=1.3) for v in new.values()], run_time=rt_)
            labs.update(new)
        self.wait_until(self.cue_start("右下角是十六", self.now))
        cmp = VGroup(T("照搬四方向：", 24, C_PURPLE), tex(nv[-1][-1], 0.75, C_PURPLE), T("只许右、下：", 24, DP_COL),
                     tex(D.min_path_sum(D.G4), 0.75, DP_COL)).arrange(RIGHT, buff=0.15)
        cmp[2].shift(RIGHT * 0.3)
        cmp[3].shift(RIGHT * 0.3)
        cmp.next_to(VGroup(*R.values()), DOWN, buff=0.3)
        self.play(R[(3, 4)][0].animate.set_stroke(C_YELLOW, 4), Indicate(labs[(3, 4)], color=C_YELLOW), run_time=0.8)
        self.wait_until(self.cue_start("一模一样", self.now))
        self.play(FadeIn(cmp, shift=UP * 0.15), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(lt, legend, cmp, rt)), R[(3, 4)][0].animate.set_stroke(C_PURPLE, 2.5), run_time=0.6)
        self.L4, self.R4, self.nlabs = L, R, labs

    # ---------------------------------------------------------------- 依赖成环
    def cycle_beat(self):
        self.beat("cycle")
        L, R, labs = self.L4, self.R4, self.nlabs
        nv = D.naive_four(D.G4)
        a, b = (2, 2), (3, 2)
        self.play(R[a][0].animate.set_stroke(C_YELLOW, 4.5), L[a][0].animate.set_stroke(C_YELLOW, 4.5), run_time=0.7)
        self.wait_until(self.cue_start("下面那一格还没算", self.now))
        later = [c for c in labs if c > a]                       # 回到「刚要算这一格」的时刻：后面的格子还是无穷大
        infs = {c: tex(D.INF, 0.72, C_GREY).move_to(R[c][0]) for c in later}
        self.play(*[FadeOut(labs[c]) for c in later], *[FadeIn(infs[c]) for c in later],
                  R[b][0].animate.set_stroke(C_RED, 4.5), L[b][0].animate.set_stroke(C_RED, 4.5), run_time=0.9)
        self.wait_until(self.cue_start("得到十三", self.now))
        up, lf = (1, 2), (2, 1)
        eq = MathTex(r"\min(", str(nv[1][2]), ",", str(nv[2][1]), ",", r"\infty", r")+", "1", "=", str(nv[2][2]))
        eq.scale(0.7).next_to(VGroup(*R.values()), DOWN, buff=0.3)
        eq[1].set_color(C_GREEN)
        eq[3].set_color(C_GREEN)
        eq[5].set_color(C_RED)
        eq[9].set_color(C_YELLOW)
        self.play(Indicate(labs[up], color=C_GREEN), Indicate(labs[lf], color=C_GREEN), Indicate(infs[b], color=C_RED),
                  Write(eq), run_time=1.2)
        self.wait_until(self.cue_start("反过来也要用它", self.now))
        # 两格之间画一对弯箭头：在网格右侧放大重画这两格，避免压住相邻格子的数字
        za = VGroup(Square(1.0, stroke_color=C_YELLOW, stroke_width=4), tex(nv[2][2], 0.85, C_YELLOW))
        zb = VGroup(Square(1.0, stroke_color=C_RED, stroke_width=4), tex(D.INF, 0.85, C_RED))
        zoom = VGroup(za, zb).arrange(DOWN, buff=1.3)
        za[1].move_to(za[0])
        zb[1].move_to(zb[0])
        self.play(FadeOut(VGroup(*R.values(), *[labs[c] for c in labs if c not in later], *infs.values(), eq)),
                  run_time=0.5)
        zoom.move_to([3.3, 0.15, 0])
        ab = CurvedArrow(za[0].get_left() + DOWN * 0.2, zb[0].get_left() + UP * 0.2, angle=PI / 2, color=C_YELLOW,
                         stroke_width=5)
        ba = CurvedArrow(zb[0].get_right() + UP * 0.2, za[0].get_right() + DOWN * 0.2, angle=PI / 2, color=C_RED,
                         stroke_width=5)
        la = T("这一格要用下面", 24, C_RED).next_to(ba, RIGHT, buff=0.15)
        lb = T("下面也要用这一格", 24, C_YELLOW).next_to(ab, LEFT, buff=0.15)
        self.play(FadeIn(za), FadeIn(zb), run_time=0.5)
        self.play(Create(ba), FadeIn(la), run_time=0.7)
        self.play(Create(ab), FadeIn(lb), run_time=0.7)
        self.wait_until(self.cue_start("依赖成环", self.now))
        ring = T("依赖成环", 34, C_RED).move_to([3.3, 2.75, 0])
        self.play(Write(ring), run_time=0.8)
        self.wait_until(self.cue_start("最好的路", self.now))
        best = D.best_path(D.G4)
        line = path_line(L, best, C_GREEN)
        _, _, dist, _ = D.grid_dijkstra(D.G4)
        self.play(Create(line), *[L[c][0].animate.set_stroke(C_GREEN, 3.5) for c in best if c not in (a, b)],
                  run_time=1.6)
        self.wait_until(self.cue_start("走到下面是六", self.now))
        z6 = tex(dist[3][2], 0.85, C_GREEN).move_to(zb[0])
        self.play(FadeOut(zb[1]), FadeIn(z6, scale=1.3), zb[0].animate.set_stroke(C_GREEN), run_time=0.7)
        self.wait_until(self.cue_start("往上一步", self.now))
        z7 = tex(dist[2][2], 0.85, C_GREEN).move_to(za[0])
        cross = Line(za[1].get_corner(DL), za[1].get_corner(UR), color=C_RED, stroke_width=4)
        self.play(Create(cross), za[1].animate.set_opacity(0.5), run_time=0.4)
        z7.next_to(za[0], UP, buff=0.12)
        self.play(FadeIn(z7, scale=1.3), za[0].animate.set_stroke(C_GREEN), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(za, zb, z6, z7, cross, ab, ba, la, lb, ring, line)),
                  *[L[c][0].animate.set_stroke(C_GREY, 2.5) for c in L], run_time=0.6)

    # ---------------------------------------------------------------- 同一张图换成 Dijkstra
    def dijkstra_beat(self):
        self.beat("dijkstra")
        L = self.L4
        lift = UP * 0.6
        R = make_grid([[None] * 5 for _ in range(4)], [3.6, 0.2 + 0.6], 1.02, 0.86, color=SR_COL)
        rt = T("出堆时定下的路径和", 24, SR_COL).next_to(VGroup(*R.values()), UP, buff=0.25)
        lt = T("Dijkstra：每次取出路径和最小的格子", 24, SR_COL).next_to(VGroup(*L.values()), UP, buff=0.25)
        lt.shift(lift)
        self.play(VGroup(*L.values()).animate.shift(lift), *[FadeIn(c[0]) for c in R.values()], FadeIn(rt), FadeIn(lt),
                  run_time=0.8)
        ans, pops, _, prev = D.grid_dijkstra(D.G4)
        sy, sx0, sdx = -2.68, -4.3, 0.86
        strip_lab = T("出堆顺序", 22, C_GREY).move_to([-6.3, sy, 0], aligned_edge=LEFT)
        self.play(FadeIn(strip_lab), run_time=0.3)
        chips, slot = VGroup(), {}
        keys = {0: "一、二、三、四", 4: "五、六", 6: "七，", 7: "八、九", 9: "最后右下角"}
        vals = {}
        k = 0
        lit = interpolate_color(ManimColor(BG), ManimColor(SR_COL), 0.22)      # 不透明的浅底：下层路径线不压数字
        groups = [(0, 4), (4, 6), (6, 7), (7, 9), (9, len(pops))]
        for g0, g1 in groups:
            self.wait_until(self.cue_start(keys[g0], self.now))
            for d, c in pops[g0:g1]:
                v = tex(d, 0.72, SR_COL).move_to(R[c][0])
                vals[c] = v
                chip = VGroup(RoundedRectangle(corner_radius=0.08, width=0.7, height=0.52, stroke_color=SR_COL,
                                               stroke_width=2), tex(d, 0.55))
                chip[1].move_to(chip[0])
                chip.move_to([sx0 + sdx * k, sy, 0])
                chips.add(chip)
                slot[c] = chip
                k += 1
                self.play(L[c][0].animate.set_stroke(SR_COL, 4).set_fill(lit, 1),
                          R[c][0].animate.set_fill(lit, 1), FadeIn(v, scale=1.3),
                          FadeIn(chip, shift=LEFT * 0.1), run_time=0.45)
        best = D.best_path(D.G4)
        line = path_line(L, best, C_YELLOW)
        res = VGroup(T("答案", 26), tex(ans, 0.95, C_YELLOW), T("比照搬的 DP 少", 22, C_GREY),
                     tex(D.naive_four(D.G4)[-1][-1] - ans, 0.75, C_GREY)).arrange(RIGHT, buff=0.18)
        res.next_to(VGroup(*R.values()), DOWN, buff=0.25)
        self.wait_until(self.cue_start("答案是十", self.now))
        self.play(Create(line), R[(3, 4)][0].animate.set_stroke(C_YELLOW, 4), FadeIn(res, shift=UP * 0.15),
                  run_time=1.2)
        # 出堆顺序条上，从每格的前驱连一条弧到它：弧全部朝右——依赖的格子总在前面出堆
        self.wait_until(self.cue_start("早已出堆", self.now) - 1.0)
        arcs = VGroup()
        for c in best[1:]:
            a, b = slot[prev[c]][0].get_top() + UP * 0.03, slot[c][0].get_top() + UP * 0.03
            arcs.add(CurvedArrow(a, b, angle=-PI * 0.7, color=C_YELLOW, stroke_width=3.5, tip_length=0.14))
        self.play(FadeOut(res), LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.2), run_time=1.8)
        self.wait_until(self.cue_start("现场造出", self.now))
        topo = T("依赖全朝右：按距离从小到大，现场造出拓扑序", 26, C_GREEN).move_to([0, -1.42, 0])
        self.play(FadeIn(topo, shift=UP * 0.15), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*L.values(), *R.values(), *vals.values(), rt, lt, strip_lab, chips, line, arcs,
                                 topo)), run_time=0.6)

    # ---------------------------------------------------------------- 方案数
    def count_beat(self):
        self.beat("count")
        n, m = 4, 5
        cnt = D.count_paths(n, m)
        R = make_grid([[None] * m for _ in range(n)], [-3.5, 0.25], 1.05, 0.9, color=DP_COL)
        head = T("只许右、下：走法有几条", 26, DP_COL).next_to(VGroup(*R.values()), UP, buff=0.3)
        self.play(*[FadeIn(c[0]) for c in R.values()], FadeIn(head), run_time=0.8)
        rule = MathTex(r"f[i][j]=f[i-1][j]+f[i][j-1]", color=DP_COL).scale(0.7)
        rule.next_to(VGroup(*R.values()), DOWN, buff=0.3)
        self.wait_until(self.cue_start("等于从上面来的", self.now))
        self.play(Write(rule), run_time=1.0)
        labs = {}
        self.wait_until(self.cue_start("都是一", self.now))
        edge = [(i, j) for i in range(n) for j in range(m) if i == 0 or j == 0]
        for c in edge:
            labs[c] = tex(1, 0.75, DP_COL).move_to(R[c][0])
        self.play(LaggedStart(*[FadeIn(labs[c], scale=1.3) for c in edge], lag_ratio=0.08), run_time=1.0)
        t_end = self.cue_start("右下角是三十五", self.now + 3)
        for i in range(1, n):
            new = {(i, j): tex(cnt[i][j], 0.75, WHITE).move_to(R[(i, j)][0]) for j in range(1, m)}
            rt_ = max(0.5, min(1.0, (t_end - self.now) / (n - i)))
            self.play(*[TransformFromCopy(VGroup(labs[(i - 1, j)], labs.get((i, j - 1)) or new[(i, j - 1)]), v) for j, v in
                        ((j, new[(i, j)]) for j in range(1, m))], run_time=rt_)
            labs.update(new)
        self.wait_until(self.cue_start("右下角是三十五", self.now))
        self.play(R[(n - 1, m - 1)][0].animate.set_stroke(C_YELLOW, 4), labs[(n - 1, m - 1)].animate.set_color(C_YELLOW),
                  Indicate(labs[(n - 1, m - 1)], color=C_YELLOW), run_time=0.8)
        # 右侧：四方向
        self.wait_until(self.cue_start("换成四个方向", self.now))
        loop_cells = make_grid([[None] * 2 for _ in range(2)], [3.6, 1.45], 1.1, 0.9, color=SR_COL)
        cc = [loop_cells[c][0].get_center() for c in ((0, 0), (0, 1), (1, 1), (1, 0))]
        loop = VGroup(*[CurvedArrow(cc[q], cc[(q + 1) % 4], angle=-PI / 3, color=C_RED, stroke_width=5, tip_length=0.18)
                        for q in range(4)])
        loop.set_z_index(2)
        inf = VGroup(T("可以来回兜圈", 26, C_RED), MathTex(r"\to\ \infty", color=C_RED).scale(0.9)).arrange(RIGHT, buff=0.2)
        inf.next_to(VGroup(*loop_cells.values()), DOWN, buff=0.3)
        self.play(*[FadeIn(c) for c in loop_cells.values()], run_time=0.5)
        self.play(Create(loop), FadeIn(inf), run_time=1.2)
        self.wait_until(self.cue_start("不许重复", self.now))
        simple = VGroup(T("不许重复经过：", 26, SR_COL), tex(D.simple_paths(n, m), 0.85, SR_COL), T("条", 26, SR_COL))
        simple.arrange(RIGHT, buff=0.15).move_to([3.6, -0.75, 0])
        self.play(FadeIn(simple, shift=UP * 0.15), run_time=0.8)
        self.wait_until(self.cue_start("记住走过", self.now))
        how = T("状态要记走过哪些格 → 回溯", 24, C_GREY).next_to(simple, DOWN, buff=0.3)
        self.play(FadeIn(how), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*R.values(), *labs.values(), head, rule, *loop_cells.values(), loop, inf, simple,
                                 how)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        q = T("能不能走回头路？", 40, C_YELLOW).move_to([0, 2.4, 0])
        self.play(Write(q), run_time=1.0)
        cards = VGroup()
        for head, lines, col in (("走不回去", ["有拓扑序", "按顺序填表", "动态规划"], DP_COL),
                                 ("走得回去", ["依赖成环", "要最短", "广搜 / Dijkstra"], SR_COL)):
            box = RoundedRectangle(corner_radius=0.2, width=4.6, height=2.8, stroke_color=col, stroke_width=3)
            body = VGroup(T(head, 32, col), *[T(s, 26) for s in lines]).arrange(DOWN, buff=0.22).move_to(box)
            cards.add(VGroup(box, body))
        cards.arrange(RIGHT, buff=1.0).move_to([0, -0.4, 0])
        self.wait_until(self.cue_start("走不回去", self.now))
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("走得回去", self.now))
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 12 周 网格 DP 与搜索的分界", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
