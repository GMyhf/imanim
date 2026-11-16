"""动态规划入门：状态少了一维（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。三角形、dp 表、路径与对拍结果全部来自 dpintrodata
（讲义 naive_odd / fixed_odd / brute_odd 原样；test_dpintro.py 对撞讲义输出、递归穷举与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dpintrodata as D  # noqa: E402
from cine import *  # noqa: E402,F403

COIN_COL = {1: C_GREY, 3: C_TEAL, 4: C_BLUE}


def cell_pos(i, j, cx, top, dx, dy):
    return np.array([cx + (j - i / 2) * dx, top - i * dy, 0])


def num_cells(rows, cx, top, dx=1.2, dy=0.95, size=0.62, color=C_GREY):
    """三角形排布的数字格子：{(i, j): VGroup(框, 数字)}。rows[i][j] 为 None 表示只画空框。"""
    out = {}
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            box = RoundedRectangle(corner_radius=0.1, width=size, height=size, stroke_color=color, stroke_width=2.5)
            box.set_fill(BG, 1)                                   # 不透明底：路径线放在下层，不压数字
            lab = MathTex(str(v)).scale(0.7) if v is not None else VMobject()
            out[(i, j)] = VGroup(box, lab).move_to(cell_pos(i, j, cx, top, dx, dy))
            lab.move_to(box)
    return out


def tri_edges(n, cells, color=C_GREY):
    g = VGroup()
    for i in range(n - 1):
        for j in range(i + 1):
            for k in (j, j + 1):
                g.add(Line(cells[(i, j)][0].get_bottom(), cells[(i + 1, k)][0].get_top(), buff=0.04,
                           stroke_color=color, stroke_width=1.5, stroke_opacity=0.6))
    return g


def path_line(cells, path, color=C_YELLOW, width=6):
    line = VMobject(stroke_color=color, stroke_width=width).set_points_as_corners(
        [cells[c][0].get_center() for c in path])
    return line.set_z_index(-1)                                # 画在格子下层，只露出格子之间的线段


def dots_grid(oks, cx, cy, cols=50, cell=0.085):
    """2000 组对拍结果画成方点阵：对的绿、错的红。按行分块做成少量 VMobject，渲染快。"""
    chunks = VGroup()
    rows = (len(oks) + cols - 1) // cols
    x0 = cx - (cols - 1) * cell / 2
    y0 = cy + (rows - 1) * cell / 2
    s = cell * 0.78 / 2
    for r0 in range(0, rows, 5):
        good, bad = VMobject(), VMobject()
        for idx in range(r0 * cols, min(len(oks), (r0 + 5) * cols)):
            r, c = divmod(idx, cols)
            x, y = x0 + c * cell, y0 - r * cell
            vm = good if oks[idx] else bad
            vm.start_new_path(np.array([x - s, y - s, 0]))
            for p in ((x + s, y - s), (x + s, y + s), (x - s, y + s), (x - s, y - s)):
                vm.add_line_to(np.array([p[0], p[1], 0]))
        good.set_fill(C_GREEN, 0.85).set_stroke(width=0)
        bad.set_fill(C_RED, 1).set_stroke(width=0)
        chunks.add(VGroup(good, bad))
    return chunks


class DPIntroLesson(Lesson):
    def construct(self):
        for b in ("title", "premise", "paths", "naive", "where", "property", "fixed", "duel", "three", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：硬币反例
    def title_beat(self):
        self.beat("title")
        head = VGroup(T("凑出 6", 34), T("面额 1、3、4", 28, C_GREY)).arrange(RIGHT, buff=0.6).move_to([0, 2.6, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.8)

        def coin_row(vals, label, col, y):
            lab = T(label, 28, col).move_to([-4.2, y, 0])
            coins = VGroup(*[VGroup(Circle(0.36, stroke_color=COIN_COL[v], stroke_width=4).set_fill(COIN_COL[v], 0.2),
                                    MathTex(str(v)).scale(0.85)) for v in vals]).arrange(RIGHT, buff=0.25)
            coins.next_to(lab, RIGHT, buff=0.6)
            cnt = T(f"{len(vals)} 枚", 30, col).next_to(coins, RIGHT, buff=0.6)
            return lab, coins, cnt
        g = coin_row(D.greedy_coins(), "贪心", C_RED, 1.1)
        o = coin_row(D.dp_coins(), "最优", C_GREEN, -0.1)
        self.wait_until(self.cue_start("贪心每次", self.now))
        self.play(FadeIn(g[0]), LaggedStart(*[FadeIn(c, shift=DOWN * 0.4) for c in g[1]], lag_ratio=0.3), run_time=1.4)
        self.play(FadeIn(g[2]), run_time=0.4)
        self.wait_until(self.cue_start("最优却是", self.now))
        self.play(FadeIn(o[0]), LaggedStart(*[FadeIn(c, shift=DOWN * 0.4) for c in o[1]], lag_ratio=0.3), run_time=1.1)
        self.play(FadeIn(o[2]), run_time=0.4)
        self.play(Indicate(o[2], color=C_GREEN), run_time=0.6)
        self.wait_until(self.cue_start("贪心失效", self.now))
        title = T("动态规划入门", 60).move_to([0, -1.5, 0])
        sub = T("状态少了一维", 32, C_YELLOW).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, *g, *o, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 两个前提
    def premise_beat(self):
        self.beat("premise")
        cards = VGroup()
        for name, body, bad, col in (("最优子结构", "大问题的最优解\n由子问题的最优解构成", "不成立：答案是错的", C_RED),
                                     ("重叠子问题", "同一个子问题\n被反复求解", "不成立：只是不如分治", C_GREY)):
            box = RoundedRectangle(corner_radius=0.2, width=5.2, height=3.0, stroke_color=col, stroke_width=3)
            txt = VGroup(T(name, 34, col), T(body, 24, "#D8DCE6", line_spacing=1.0), T(bad, 24, col))
            txt.arrange(DOWN, buff=0.35).move_to(box)
            cards.add(VGroup(box, txt))
        cards.arrange(RIGHT, buff=0.8).move_to([0, 0.5, 0])
        self.play(FadeIn(cards[0][0]), FadeIn(cards[0][1][:2]), run_time=0.9)
        self.wait_until(self.cue_start("它不成立，转移方程", self.now))
        self.play(FadeIn(cards[0][1][2], shift=UP * 0.2), Indicate(cards[0][0], color=C_RED, scale_factor=1.03),
                  run_time=1.0)
        self.wait_until(self.cue_start("第二，重叠子问题", self.now))
        self.play(FadeIn(cards[1][0]), FadeIn(cards[1][1][:2]), run_time=0.9)
        self.wait_until(self.cue_start("它不成立不会算错", self.now))
        self.play(FadeIn(cards[1][1][2], shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("难判断", self.now))
        self.play(cards[1][0].animate.set_stroke(opacity=0.3), cards[1][1].animate.set_opacity(0.3),
                  Circumscribe(cards[0], color=C_YELLOW, buff=0.1), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(cards), run_time=0.6)

    # ---------------------------------------------------------------- 八条路径，只有一条是奇数
    def make_value_tri(self, cx=-3.6, top=2.3):
        cells = num_cells(D.TRI, cx, top)
        edges = tri_edges(len(D.TRI), cells)
        return cells, edges

    def paths_beat(self):
        self.beat("paths")
        cells, edges = self.make_value_tri()
        self.play(FadeIn(edges), LaggedStart(*[FadeIn(c, scale=0.8) for c in cells.values()], lag_ratio=0.08),
                  run_time=1.4)
        rule = T("每步：左下 或 右下", 24, C_GREY).next_to(cells[(3, 0)], DOWN, buff=0.45).align_to(cells[(3, 0)], LEFT)
        self.play(FadeIn(rule), run_time=0.5)
        self.wait_until(self.cue_start("路径和必须是奇数", self.now))
        cond = T("限制：路径和必须是奇数，求最大", 28, C_YELLOW).move_to([3.0, 3.0, 0])
        self.play(FadeIn(cond, shift=DOWN * 0.2), run_time=0.8)
        paths = D.all_paths(D.TRI)
        rows = VGroup()
        for k, (pc, s) in enumerate(paths):
            vals = "→".join(str(D.TRI[i][j]) for i, j in pc)
            odd = s % 2 == 1
            row = VGroup(Text(vals, font=MONO, font_size=22, color=C_YELLOW if odd else "#D8DCE6"),
                         MathTex(str(s), color=C_YELLOW if odd else C_GREY).scale(0.7)).arrange(RIGHT, buff=0.35)
            row.move_to([1.6 + 3.1 * (k // 4), 1.95 - 0.62 * (k % 4), 0])
            rows.add(row)
        step = max(0.35, min(0.75, (self.cue_start("只有一条", self.now + 4) - self.now) / len(paths)))
        line = None
        for (pc, s), row in zip(paths, rows):
            new = path_line(cells, pc, C_BLUE, 5)
            anims = [FadeIn(row, shift=LEFT * 0.2)]
            anims.append(Create(new) if line is None else Transform(line, new))
            self.play(*anims, run_time=step)
            if line is None:
                line = new
        self.wait_until(self.cue_start("只有一条", self.now))
        odd_k = next(k for k, (_, s) in enumerate(paths) if s % 2)
        gold = path_line(cells, paths[odd_k][0], C_YELLOW, 7)
        box = SurroundingRectangle(rows[odd_k], color=C_YELLOW, buff=0.1)
        self.play(Transform(line, gold), Create(box), *[r.animate.set_opacity(0.35) for k, r in enumerate(rows) if k != odd_k],
                  run_time=1.0)
        ans = VGroup(T("暴力枚举：", 26, C_GREEN), MathTex("17", color=C_GREEN).scale(1.0)).arrange(RIGHT, buff=0.2)
        ans.move_to([3.0, -0.8, 0])
        self.play(FadeIn(ans, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rows, box, cond, rule, line)), ans.animate.move_to([-3.6, -1.75, 0]), run_time=0.6)
        self.vtri, self.vedges, self.brute_ans = cells, edges, ans

    # ---------------------------------------------------------------- 朴素状态：全是偶数
    def naive_beat(self):
        self.beat("naive")
        nt = D.naive_table(D.TRI)
        cells = num_cells([[None] * len(r) for r in nt], 3.4, 2.3, color=C_BLUE)
        edges = tri_edges(len(nt), cells, C_BLUE)
        head = Text("dp[i][j] = 到这一格的最大路径和", font=MONO, font_size=22, color=C_BLUE).move_to([3.4, 3.15, 0])
        self.play(FadeIn(head), FadeIn(edges), *[FadeIn(c[0]) for c in cells.values()], run_time=1.0)
        self.wait_until(self.cue_start("逐行填下来", self.now))
        labs = {}
        rt = max(0.35, min(0.9, (self.cue_start("底行是", self.now + 3.6) - self.now) / len(nt)))
        for i, row in enumerate(nt):
            anims = []
            for j, v in enumerate(row):
                lab = MathTex(str(v)).scale(0.7).move_to(cells[(i, j)][0])
                labs[(i, j)] = lab
                srcs = [self.vtri[(i, j)][1]] + ([labs[(i - 1, k)] for k in (j - 1, j) if (i - 1, k) in labs] if i else [])
                anims.append(TransformFromCopy(VGroup(*srcs), lab))
            self.play(*anims, run_time=rt)
        self.wait_until(self.cue_start("全是偶数", self.now) - 0.4)
        evens = VGroup(*[T("偶", 20, C_RED).next_to(cells[(3, j)][0], DOWN, buff=0.12) for j in range(4)])
        self.play(*[cells[(3, j)][0].animate.set_stroke(C_RED, 3.5) for j in range(4)],
                  LaggedStart(*[FadeIn(e, shift=UP * 0.1) for e in evens], lag_ratio=0.15), run_time=1.0)
        res = VGroup(T("朴素 DP：", 26, C_RED), MathTex("-1", color=C_RED), T("（无解）", 26, C_RED)).arrange(RIGHT, buff=0.15)
        res.move_to([3.4, -1.75, 0])
        self.wait_until(self.cue_start("程序返回负一", self.now))
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("可我们刚刚数过", self.now))
        self.play(Indicate(self.brute_ans, color=C_GREEN, scale_factor=1.2), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        self.ncells, self.nlabs, self.nedges, self.nhead, self.nevens, self.nres = cells, labs, edges, head, evens, res

    # ---------------------------------------------------------------- 错在哪一步
    def where_beat(self):
        self.beat("where")
        cells, labs = self.ncells, self.nlabs
        self.play(FadeOut(self.nevens), *[cells[(3, j)][0].animate.set_stroke(C_BLUE, 2.5) for j in range(4)],
                  run_time=0.5)
        self.wait_until(self.cue_start("第四行这个四", self.now))
        self.play(Indicate(self.vtri[(3, 1)], color=C_YELLOW, scale_factor=1.3),
                  cells[(3, 1)][0].animate.set_stroke(C_YELLOW, 4), run_time=0.9)
        a13 = Arrow(cells[(2, 0)][0].get_bottom(), cells[(3, 1)][0].get_top(), buff=0.06, color=C_RED, stroke_width=4,
                    max_tip_length_to_length_ratio=0.25)
        a18 = Arrow(cells[(2, 1)][0].get_bottom(), cells[(3, 1)][0].get_top(), buff=0.06, color=C_GREEN, stroke_width=4,
                    max_tip_length_to_length_ratio=0.25)
        t13 = T("奇", 22, C_RED).next_to(cells[(2, 0)][0], LEFT, buff=0.12)
        t18 = T("偶", 22, C_GREEN).next_to(cells[(2, 1)][0], RIGHT, buff=0.05)
        self.wait_until(self.cue_start("十三是奇数", self.now))
        self.play(GrowArrow(a13), GrowArrow(a18), FadeIn(t13), FadeIn(t18), run_time=1.0)
        self.wait_until(self.cue_start("朴素状态只留下", self.now))
        keep = T("只留最大", 22, C_GREEN).next_to(cells[(3, 1)][0], DOWN, buff=0.15)
        cross = Cross(cells[(2, 0)], stroke_color=C_RED, stroke_width=5).scale(0.9)   # 只划掉 13，旁边的「奇」要留着能读
        self.play(FadeIn(keep), Create(cross), a13.animate.set_opacity(0.3), run_time=1.0)
        self.wait_until(self.cue_start("恰好是十三加四", self.now))
        odd_path = next(pc for pc, s in D.all_paths(D.TRI) if s % 2)
        gold = path_line(self.vtri, odd_path, C_YELLOW, 7)
        eq = MathTex("13", "+", "4", "=", "17", color=C_YELLOW).scale(0.9).move_to([-3.6, -2.5, 0])
        eq[0].set_color(C_RED)
        self.play(Create(gold), Write(eq), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*self.vtri.values(), self.vedges, *cells.values(), *labs.values(), self.nedges,
                                 self.nhead, self.nres, a13, a18, t13, t18, keep, cross, gold, eq, self.brute_ans)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 最优子结构是状态定义的性质
    def property_beat(self):
        self.beat("property")
        q1 = T("最优子结构", 44, C_YELLOW)
        q2 = T("是状态定义的性质，不是题目的性质", 36)
        quote = VGroup(q1, q2).arrange(DOWN, buff=0.3).move_to([0, 1.6, 0])
        self.play(Write(q1), run_time=1.0)
        self.play(FadeIn(q2, shift=UP * 0.2), run_time=1.0)
        self.wait_until(self.cue_start("子问题的最优解十八", self.now))
        chips = VGroup(VGroup(MathTex("18", color=C_GREEN), T("子问题最优，父问题用不上", 24, C_GREEN)).arrange(RIGHT, buff=0.3),
                       VGroup(MathTex("13", color=C_RED), T("次优被挤掉，答案却要它", 24, C_RED)).arrange(RIGHT, buff=0.3))
        chips.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([0, -0.15, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=RIGHT * 0.2) for c in chips], lag_ratio=0.4), run_time=1.2)
        self.wait_until(self.cue_start("检验的办法", self.now))
        box = RoundedRectangle(corner_radius=0.2, width=11.4, height=1.15, stroke_color=C_BLUE, stroke_width=3)
        box.move_to([0, -1.95, 0])
        test = T("把子问题的最优解换成次优解，父问题会不会反而更好？", 28, C_BLUE).move_to(box)
        self.play(Create(box), FadeIn(test), run_time=1.0)
        self.wait_until(self.cue_start("会，就说明", self.now))
        ans = T("会 → 状态少了一维", 28, C_YELLOW).next_to(box, DOWN, buff=0.12)
        self.play(FadeIn(ans, shift=UP * 0.1), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(quote, chips, box, test, ans)), run_time=0.6)

    # ---------------------------------------------------------------- 补一维
    def fixed_beat(self):
        self.beat("fixed")
        vcells, vedges = self.make_value_tri(cx=-4.0, top=2.1)
        vt = VGroup(*vcells.values(), vedges).scale(0.85, about_point=np.array([-4.0, 2.1, 0]))
        ft = D.fixed_table(D.TRI)
        cx, top, dx, dy = 2.9, 2.2, 1.55, 1.05
        pair = {}
        for i, row in enumerate(ft):
            for j, _ in enumerate(row):
                c = cell_pos(i, j, cx, top, dx, dy)
                ev = Rectangle(width=0.62, height=0.56, stroke_color=C_BLUE, stroke_width=2.5).move_to(c + LEFT * 0.31)
                od = Rectangle(width=0.62, height=0.56, stroke_color=C_YELLOW, stroke_width=2.5).move_to(c + RIGHT * 0.31)
                pair[(i, j)] = VGroup(ev, od)
        edges = VGroup()
        for i in range(3):
            for j in range(i + 1):
                for k in (j, j + 1):
                    edges.add(Line(pair[(i, j)].get_bottom(), pair[(i + 1, k)].get_top(), buff=0.04, stroke_color=C_GREY,
                                   stroke_width=1.5, stroke_opacity=0.6))
        head = Text("dp[i][j][p]：p = 路径和的奇偶", font=MONO, font_size=22, color=C_YELLOW).move_to([2.9, 3.15, 0])
        legend = VGroup(T("左：偶", 20, C_BLUE), T("右：奇", 20, C_YELLOW)).arrange(RIGHT, buff=0.4)
        legend.next_to(head, DOWN, buff=0.12)
        self.play(FadeIn(vt), FadeIn(head), run_time=0.9)
        self.wait_until(self.cue_start("每个格子存两个值", self.now))
        self.play(FadeIn(legend), FadeIn(edges), *[FadeIn(p) for p in pair.values()], run_time=1.0)
        self.wait_until(self.cue_start("逐行填下来", self.now))
        labs = {}
        for i, row in enumerate(ft):
            anims = []
            for j, (ev, od) in enumerate(row):
                for p, v in ((0, ev), (1, od)):
                    if v == D.NEG:
                        lab = T("–", 20, C_GREY)
                    else:
                        lab = MathTex(str(int(v)), color=C_BLUE if p == 0 else C_YELLOW).scale(0.6)
                    lab.move_to(pair[(i, j)][p])
                    labs[(i, j, p)] = lab
                    anims.append(FadeIn(lab, scale=1.3))
            self.play(LaggedStart(*anims, lag_ratio=0.08), run_time=0.9)
        self.wait_until(self.cue_start("第四行这个四", self.now))
        hit = SurroundingRectangle(pair[(3, 1)][1], color=C_YELLOW, buff=0.06, stroke_width=4)
        self.play(Create(hit), Indicate(vcells[(3, 1)], color=C_YELLOW, scale_factor=1.3),
                  Indicate(labs[(3, 1, 1)], color=C_YELLOW, scale_factor=1.6), run_time=1.0)
        self.wait_until(self.cue_start("底行取奇数", self.now))
        res = VGroup(T("补一维：", 26, C_GREEN), MathTex("17", color=C_GREEN)).arrange(RIGHT, buff=0.15)
        res.move_to([2.9, -1.85, 0])
        self.play(*[pair[(3, j)][1].animate.set_stroke(C_GREEN, 3.5) for j in range(4)], FadeIn(res, shift=UP * 0.2),
                  run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(vt, head, legend, edges, *pair.values(), *labs.values(), hit, res)), run_time=0.6)

    # ---------------------------------------------------------------- 对拍
    def duel_beat(self):
        self.beat("duel")
        chips = VGroup()
        for name, val, col in (("暴力枚举", D.brute_odd(D.TRI), C_GREEN), ("朴素 DP", D.naive_odd(D.TRI), C_RED),
                               ("补一维", D.fixed_odd(D.TRI), C_GREEN)):
            box = RoundedRectangle(corner_radius=0.15, width=2.9, height=1.0, stroke_color=col, stroke_width=3)
            chips.add(VGroup(box, VGroup(T(name, 24, col), MathTex(str(val), color=col).scale(0.9))
                             .arrange(RIGHT, buff=0.3).move_to(box)))
        chips.arrange(RIGHT, buff=0.5).move_to([0, 2.65, 0])
        self.wait_until(self.cue_start("暴力枚举十七", self.now))
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.2) for c in chips], lag_ratio=0.45), run_time=1.8)
        fx, nv = D.duel()
        self.wait_until(self.cue_start("两千个三角形", self.now))
        g1 = dots_grid(fx, -3.3, -0.85)
        g2 = dots_grid(nv, 3.3, -0.85)
        h1 = T(f"补一维：{sum(fx)} / {len(fx)} 一致", 24, C_GREEN).next_to(g1, UP, buff=0.18)
        h2 = T(f"朴素：答错 {nv.count(False)} 组", 24, C_RED).next_to(g2, UP, buff=0.18)
        self.play(FadeIn(h1), FadeIn(h2), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(c) for c in g1], lag_ratio=0.25),
                  LaggedStart(*[FadeIn(c) for c in g2], lag_ratio=0.25), run_time=2.8)
        self.play(Indicate(h2, color=C_RED, scale_factor=1.15), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(chips, g1, g2, h1, h2)), run_time=0.6)

    # ---------------------------------------------------------------- DP 三要素
    def three_beat(self):
        self.beat("three")
        title = T("DP 三要素", 40, C_YELLOW).move_to([0, 2.9, 0])
        self.play(Write(title), run_time=0.8)
        rows = [("状态", "dp 表示什么：要能一句话说清", "dp[i][j][p] = 到 (i,j)、和的奇偶为 p 的最大和", C_BLUE, "状态"),
                ("转移", "怎么由更小的状态算出来", "两个前驱 × 两种奇偶，加上 tri[i][j]", C_TEAL, "转移"),
                ("边界", "最小状态是多少，答案在哪", "dp[0][0][6 % 2] = 6；答案取底行奇数栏", C_GREEN, "边界")]
        group = VGroup()
        for k, (name, desc, eg, col, key) in enumerate(rows):
            self.wait_until(self.cue_start(key, self.now))
            badge = VGroup(Circle(0.42, stroke_color=col, stroke_width=3).set_fill(col, 0.15), T(name, 24, col))
            badge[1].move_to(badge[0])
            txt = VGroup(T(desc, 26), Text(eg, font=MONO, font_size=19, color=C_GREY)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
            row = VGroup(badge, txt).arrange(RIGHT, buff=0.4).move_to([0, 1.55 - 1.35 * k, 0]).align_to(np.array([-4.6, 0, 0]), LEFT)
            group.add(row)
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, group)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        q = T("好像没有最优子结构？", 34).move_to([0, 2.3, 0])
        q2 = T("先问：我的状态是不是少了一维", 38, C_YELLOW).next_to(q, DOWN, buff=0.3)
        self.play(FadeIn(q, shift=DOWN * 0.2), run_time=0.8)
        self.play(Write(q2), run_time=1.2)
        self.wait_until(self.cue_start("常见的那一维", self.now))
        dims = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.15, width=2.5, height=0.8, stroke_color=col, stroke_width=2.5),
                               T(t, 26, col)) for t, col in (("剩余容量", C_BLUE), ("已用次数", C_TEAL),
                                                             ("上一步选了什么", C_PURPLE), ("当前第几段", C_GREEN))])
        for d in dims:
            d[0].stretch_to_fit_width(d[1].width + 0.6)
            d[1].move_to(d[0])
        dims.arrange(RIGHT, buff=0.35).move_to([0, -0.6, 0])
        self.play(LaggedStart(*[FadeIn(d, shift=UP * 0.2) for d in dims], lag_ratio=0.3), run_time=1.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 10 周 动态规划入门 P13–P24", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
