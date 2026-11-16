"""从递归到 DP：爬楼梯与数字三角形（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。调用次数、各级被问次数、dp 表、记忆化填表顺序、滚动数组逐格记录
全部来自 triangledata（讲义 climb_stairs / max_path_sum / max_path_sum_1d 原样；test_triangle.py 对撞
讲义输出、序列枚举、路径穷举与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import triangledata as D  # noqa: E402
from cine import *  # noqa: E402,F403

N = D.N_STAIRS
SF = D.stairs_facts()
SXS, SW, SYG, SH = -6.3, 0.82, -2.5, 0.5          # 楼梯：第 0 级（地面）踏面中心 x、级宽、地面 y、级高
TDX, TDY, TSZ = 1.12, 0.92, 0.6                   # 三角形格距与格子边长
LEFT_C, RIGHT_C, TTOP = -3.7, 3.5, 2.45           # 左（原数）/ 右（dp 表）三角形中心 x 与顶行 y

REC_SRC = ("def climb(n):\n    if n <= 1:\n        return 1\n    return climb(n-1) + climb(n-2)\n")
MEMO_SRC = ("memo = {}\ndef climb(n):\n    if n <= 1:\n        return 1\n    if n in memo:\n        return memo[n]\n"
            "    memo[n] = climb(n-1) + climb(n-2)\n    return memo[n]\n")
TABLE_SRC = ("dp = [0] * (n + 1)\ndp[0] = 1\nfor i in range(1, n + 1):\n"
             "    dp[i] = dp[i - 1] + (dp[i - 2] if i >= 2 else 0)\n")
ROLL_SRC = ("dp = tri[-1][:]\nfor i in range(len(tri) - 2, -1, -1):\n    for j in range(i + 1):\n"
            "        dp[j] = tri[i][j] + max(dp[j], dp[j + 1])\n")


def code_block(src, size=22):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


def tread(k):
    """第 k 级踏面中心。"""
    return np.array([SXS + k * SW, SYG + k * SH, 0])


def staircase():
    pts = [tread(0) + LEFT * SW * 0.7]
    for k in range(N + 1):
        c = tread(k)
        pts.append(c + LEFT * SW / 2 if k else c + LEFT * SW * 0.7)
        pts.append(c + RIGHT * SW / 2)
        if k < N:
            pts.append(c + RIGHT * SW / 2 + UP * SH)
    line = VMobject(stroke_color=C_GREY, stroke_width=3).set_points_as_corners(pts[1:])
    idx = VGroup(*[T("地面" if k == 0 else f"{k}", 18 if k == 0 else 20, C_GREY).move_to(tread(k) + DOWN * 0.24)
                   for k in range(N + 1)])
    return line, idx


def tpos(i, j, cx, top=TTOP):
    return np.array([cx + (j - i / 2) * TDX, top - i * TDY, 0])


def tri_cells(rows, cx, color=C_GREY, top=TTOP):
    """三角形排布的格子：{(i, j): VGroup(框, 数字或空)}。"""
    out = {}
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            box = RoundedRectangle(corner_radius=0.1, width=TSZ, height=TSZ, stroke_color=color, stroke_width=2.5)
            box.set_fill(BG, 1)
            lab = MathTex(str(v)).scale(0.68) if v is not None else VMobject()
            out[(i, j)] = VGroup(box, lab).move_to(tpos(i, j, cx, top))
            lab.move_to(box)
    return out


def tri_edges(cells, n, color=C_GREY):
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
    return line.set_z_index(-1)


def all_paths(n):
    out = []
    for mask in range(2 ** (n - 1)):
        j, cells = 0, [(0, 0)]
        for i in range(1, n):
            j += (mask >> (n - 1 - i)) & 1
            cells.append((i, j))
        out.append(cells)
    return out


class TriangleLesson(Lesson):
    def construct(self):
        for b in ("title", "stairs", "rec", "memo", "table", "tri", "trimemo", "triup", "forward", "roll", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("从递归到 DP", 54).move_to([0, 2.8, 0])
        sub = T("三步演化", 30, C_YELLOW).next_to(title, DOWN, buff=0.2)
        # 小楼梯
        pts, w, h = [], 0.45, 0.3
        for k in range(6):
            pts += [np.array([k * w, k * h, 0]), np.array([(k + 1) * w, k * h, 0])]
        icon1 = VMobject(stroke_color=C_TEAL, stroke_width=4).set_points_as_corners(pts).move_to([-3.4, 0.55, 0])
        lab1 = T("爬楼梯", 28, C_TEAL).next_to(icon1, DOWN, buff=0.3)
        mini = tri_cells([[7], [3, 8], [8, 1, 0]], 3.4, C_BLUE, top=1.3)
        for c in mini.values():
            c.scale(0.75, about_point=np.array([3.4, 0.55, 0]))
        icon2 = VGroup(*mini.values())
        lab2 = T("数字三角形", 28, C_BLUE).next_to(icon2, DOWN, buff=0.3)
        lab1.set_y(lab2.get_y())
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.play(Create(icon1), FadeIn(lab1), LaggedStart(*[FadeIn(c, scale=0.8) for c in icon2], lag_ratio=0.1),
                  FadeIn(lab2), run_time=1.4)
        self.wait_until(self.cue_start("先写递归", self.now))
        steps = VGroup()
        for k, (name, col) in enumerate((("① 递归", C_RED), ("② 记忆化", C_TEAL), ("③ 倒过来填表", C_GREEN))):
            box = RoundedRectangle(corner_radius=0.15, height=0.8, width=2.9, stroke_color=col, stroke_width=2.5)
            steps.add(VGroup(box, T(name, 28, col).move_to(box)))
        steps.arrange(RIGHT, buff=0.75).move_to([0, -1.7, 0])
        arrows = VGroup(*[Arrow(steps[k].get_right(), steps[k + 1].get_left(), buff=0.1, color=C_GREY, stroke_width=3)
                          for k in range(2)])
        for k in range(3):
            self.play(FadeIn(steps[k], shift=UP * 0.2), *([GrowArrow(arrows[k - 1])] if k else []), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, sub, icon1, lab1, icon2, lab2, steps, arrows)), run_time=0.6)

    # ---------------------------------------------------------------- 爬楼梯：只看最后一步
    def stairs_beat(self):
        self.beat("stairs")
        line, idx = staircase()
        q = T("每次爬 1 级或 2 级，爬到第 7 级有几种爬法？", 28).move_to([0, 3.3, 0])
        self.play(Create(line), FadeIn(idx), FadeIn(q, shift=DOWN * 0.2), run_time=1.4)
        self.wait_until(self.cue_start("只看最后一步", self.now))
        top = tread(N) + UP * 0.12
        a1 = CurvedArrow(tread(N - 1) + UP * 0.12, top, angle=-PI / 2.2, color=C_TEAL, stroke_width=4)
        a2 = CurvedArrow(tread(N - 2) + UP * 0.12, top, angle=-PI / 2.4, color=C_YELLOW, stroke_width=4)
        l1 = T("+1 级", 22, C_TEAL).next_to(a1, RIGHT, buff=0.12)
        l2 = T("+2 级", 22, C_YELLOW).next_to(a2, LEFT, buff=0.12)
        self.play(Create(a1), FadeIn(l1), run_time=0.8)
        self.play(Create(a2), FadeIn(l2), run_time=0.8)
        self.wait_until(self.cue_start("所以爬到", self.now))
        rule = MathTex(r"\mathrm{dp}[i]", "=", r"\mathrm{dp}[i-1]", "+", r"\mathrm{dp}[i-2]").scale(0.95)
        rule[2].set_color(C_TEAL)
        rule[4].set_color(C_YELLOW)
        rule.move_to([3.9, 1.9, 0])
        cap = T("爬到第 i 级的方法数", 22, C_GREY).next_to(rule, UP, buff=0.25)
        self.play(FadeIn(cap), Write(rule), run_time=1.2)
        self.wait_until(self.cue_start("地面算一种", self.now))
        base = MathTex(r"\mathrm{dp}[0]=\mathrm{dp}[1]=1", color=C_BLUE).scale(0.85).next_to(rule, DOWN, buff=0.35)
        tab = SF["table"]
        vals = [MathTex(str(v)).scale(0.75).move_to(tread(k) + UP * 0.3) for k, v in enumerate(tab)]
        self.play(FadeIn(base), FadeOut(VGroup(a1, a2, l1, l2)), FadeIn(vals[0], scale=1.4), FadeIn(vals[1], scale=1.4),
                  run_time=0.9)
        self.wait_until(self.cue_start("一路加上去", self.now))
        step = max(0.35, min(0.7, (self.left() - 1.2) / (N - 1)))
        for k in range(2, N + 1):
            self.play(TransformFromCopy(VGroup(vals[k - 1], vals[k - 2]), vals[k]), run_time=step)
        ring = SurroundingRectangle(vals[N], color=C_YELLOW, buff=0.1)
        self.play(Create(ring), vals[N].animate.set_color(C_YELLOW), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(q, rule, cap, base, ring, *vals)), run_time=0.6)
        self.stair = VGroup(line, idx)

    # ---------------------------------------------------------------- 第一步：暴力递归
    def bars(self, counts, color):
        unit = 0.13
        g = VGroup()
        for k, c in enumerate(counts):
            bar = Rectangle(width=0.42, height=max(0.02, c * unit), stroke_width=0).set_fill(color, 0.55)
            bar.move_to(tread(k) + UP * (0.04 + c * unit / 2))
            num = MathTex(str(c), color=color).scale(0.6).next_to(bar, UP, buff=0.08)
            g.add(VGroup(bar, num))
        return g

    def rec_beat(self):
        self.beat("rec")
        code = code_block(REC_SRC).move_to([3.75, 2.55, 0])
        head = T("第一步：暴力递归", 28, C_RED).move_to([-3.4, 3.3, 0])
        self.play(FadeIn(head), FadeIn(code, shift=LEFT * 0.3), run_time=1.0)
        self.wait_until(self.cue_start("它是对的", self.now))
        ok = VGroup(Text("climb(7)", font=MONO, font_size=24), MathTex(r"\to 21", color=C_GREEN).scale(0.8),
                    MathTex(r"\checkmark", color=C_GREEN)).arrange(RIGHT, buff=0.2).move_to([3.75, 0.75, 0])
        self.play(FadeIn(ok), run_time=0.6)
        cnt_lab = T("调用次数", 26, C_GREY)
        cnt = Integer(0, color=C_RED).scale(1.1)
        counter = VGroup(cnt_lab, cnt).arrange(RIGHT, buff=0.3).move_to([3.75, -0.3, 0])
        bars = self.bars(SF["rec_per_level"], C_RED)
        self.play(FadeIn(cnt_lab), FadeIn(cnt), run_time=0.4)
        self.play(ChangeDecimalToValue(cnt, SF["rec_calls"]),
                  LaggedStart(*[GrowFromEdge(b[0], DOWN) for b in bars], lag_ratio=0.1),
                  LaggedStart(*[FadeIn(b[1]) for b in bars], lag_ratio=0.1), run_time=2.0)
        self.wait_until(self.cue_start("第一级被问了", self.now))
        self.play(Indicate(bars[1], color=C_YELLOW, scale_factor=1.15), run_time=0.8)
        self.play(Indicate(bars[0], color=C_YELLOW, scale_factor=1.15), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        self.rec = VGroup(head, code, ok)
        self.cnt, self.cnt_lab, self.bars_now = cnt, cnt_lab, bars

    # ---------------------------------------------------------------- 第二步：记忆化
    def memo_beat(self):
        self.beat("memo")
        code = code_block(MEMO_SRC, 21).move_to([3.7, 1.7, 0])
        head = T("第二步：记忆化", 28, C_TEAL).move_to([-3.4, 3.3, 0])
        self.play(FadeOut(self.rec), FadeIn(head), FadeIn(code, shift=LEFT * 0.3),
                  self.cnt_lab.animate.move_to([3.0, -0.75, 0]), self.cnt.animate.move_to([4.5, -0.75, 0]),
                  run_time=1.0)
        ln = code.code_lines
        hl_look = VGroup(*[SurroundingRectangle(ln[k], color=C_TEAL, buff=(0.08, 0.03), stroke_width=2) for k in (4, 5)])
        hl_save = SurroundingRectangle(ln[6], color=C_YELLOW, buff=(0.08, 0.03), stroke_width=2)
        hl_dict = SurroundingRectangle(ln[0], color=C_TEAL, buff=(0.08, 0.03), stroke_width=2)
        self.wait_until(self.cue_start("算完就存进去", self.now))
        self.play(Create(hl_dict), Create(hl_save), run_time=0.6)
        self.wait_until(self.cue_start("下次先查表", self.now - 1.4) + 1.4)
        self.play(Create(hl_look), run_time=0.6)
        self.wait_until(self.cue_start("调用从四十一", self.now))
        new = self.bars(SF["memo_per_level"], C_TEAL)
        self.cnt.set_color(C_TEAL)
        self.play(ChangeDecimalToValue(self.cnt, SF["memo_calls"]),
                  *[Transform(o, n) for o, n in zip(self.bars_now, new)], run_time=1.6)
        was = T("原来 41", 22, C_RED).next_to(VGroup(self.cnt_lab, self.cnt), DOWN, buff=0.2)
        self.play(FadeIn(was), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, code, hl_look, hl_save, hl_dict, was, self.cnt, self.cnt_lab, self.bars_now)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 第三步：倒过来填表
    def table_beat(self):
        self.beat("table")
        head = T("第三步：自底向上填表", 28, C_GREEN).move_to([-3.4, 3.3, 0])
        code = code_block(TABLE_SRC, 18).move_to([3.55, 2.5, 0])
        self.play(FadeIn(head), FadeIn(code, shift=LEFT * 0.3), run_time=0.9)
        d = tread(N) - tread(0)
        u = d / np.linalg.norm(d)
        perp = np.array([-u[1], u[0], 0])
        down = Arrow(tread(N) + perp * 1.0, tread(0) + perp * 1.0 + u * 0.4, buff=0, color=C_RED, stroke_width=5)
        dl = T("递归：从上往下问", 24, C_RED).next_to(down.get_center() + perp * 0.1, UP + LEFT, buff=0.1)
        up = Arrow(tread(0) + perp * 1.0 + u * 0.4, tread(N) + perp * 1.0, buff=0, color=C_GREEN, stroke_width=5)
        ul = T("填表：从下往上算", 24, C_GREEN).move_to(dl)
        self.wait_until(self.cue_start("递归从第七级", self.now))
        self.play(GrowArrow(down), FadeIn(dl), run_time=1.0)
        self.wait_until(self.cue_start("填表从地面", self.now))
        self.play(ReplacementTransform(down, up), ReplacementTransform(dl, ul), run_time=1.0)
        tab = SF["table"]
        vals = [MathTex(str(v)).scale(0.75).move_to(tread(k) + UP * 0.3) for k, v in enumerate(tab)]
        hl = SurroundingRectangle(code.code_lines[3], color=C_YELLOW, buff=(0.06, 0.03), stroke_width=2)
        self.play(FadeIn(vals[0], scale=1.4), Create(hl), run_time=0.6)
        loop = VGroup(T("循环", 24, C_GREY), Integer(0, color=C_GREEN).scale(0.9), T("次", 24, C_GREY))
        loop.arrange(RIGHT, buff=0.15).move_to([3.55, 0.3, 0])
        self.play(FadeIn(loop), run_time=0.3)
        end = self.cue_start("一个循环", self.now + 6)
        step = max(0.4, min(0.9, (end - self.now) / N))
        for k in range(1, N + 1):
            srcs = VGroup(*[vals[m] for m in (k - 1, k - 2) if m >= 0])
            self.play(TransformFromCopy(srcs, vals[k]), loop[1].animate.set_value(k), run_time=step)
        self.play(vals[N].animate.set_color(C_YELLOW), Indicate(loop, color=C_GREEN), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, code, hl, loop, up, ul, *vals, self.stair)), run_time=0.6)

    # ---------------------------------------------------------------- 数字三角形
    def tri_beat(self):
        self.beat("tri")
        cells = tri_cells(D.TRI, LEFT_C)
        edges = tri_edges(cells, len(D.TRI))
        head = T("02760 数字三角形", 28, C_BLUE).move_to([3.5, 2.4, 0])
        rule = T("每步走到左下或右下", 24, C_GREY).next_to(head, DOWN, buff=0.25)
        self.play(FadeIn(edges), LaggedStart(*[FadeIn(c, scale=0.8) for c in cells.values()], lag_ratio=0.06),
                  FadeIn(head), FadeIn(rule), run_time=1.4)
        self.wait_until(self.cue_start("五行一共", self.now))
        cnt = VGroup(Integer(0, color=C_BLUE).scale(0.9), T("条路径", 26, C_GREY)).arrange(RIGHT, buff=0.25)
        cnt.move_to([3.5, 0.6, 0])
        self.play(FadeIn(cnt), run_time=0.3)
        paths = all_paths(len(D.TRI))
        line = path_line(cells, paths[0], C_BLUE, 5)
        self.play(Create(line), cnt[0].animate.set_value(1), run_time=0.3)
        for k, p in enumerate(paths[1:], 2):
            self.play(Transform(line, path_line(cells, p, C_BLUE, 5)), cnt[0].animate.set_value(k), run_time=0.17)
        self.wait_until(self.cue_start("路径和最大", self.now))
        best = D.best_path()
        gold = path_line(cells, best, C_YELLOW, 7)
        eq = MathTex("+".join(str(D.TRI[i][j]) for i, j in best), "=", str(D.max_path_sum(D.TRI)), color=C_YELLOW)
        eq.scale(0.9).move_to([3.5, -0.6, 0])
        self.play(Transform(line, gold), *[cells[c][0].animate.set_stroke(C_YELLOW, 3.5) for c in best], run_time=0.9)
        self.play(Write(eq), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, rule, cnt, eq, line)), *[cells[c][0].animate.set_stroke(C_GREY, 2.5) for c in best],
                  run_time=0.6)
        self.vcells, self.vedges = cells, edges

    # ---------------------------------------------------------------- 记忆化：同一张表，递归的顺序
    def dp_frame(self, color=C_BLUE):
        cells = tri_cells([[None] * len(r) for r in D.TRI], RIGHT_C, color)
        return cells, tri_edges(cells, len(D.TRI), color)

    def trimemo_beat(self):
        self.beat("trimemo")
        dcells, dedges = self.dp_frame()
        f = MathTex(r"f(i,j)", "=", r"a_{i,j}", "+", r"\max\big(f(i{+}1,j),\ f(i{+}1,j{+}1)\big)").scale(0.72)
        f[2].set_color(C_GREY)
        f.scale(0.94).move_to([3.3, 3.35, 0])
        cap = T("从这一格走到底的最大和", 22, C_BLUE).next_to(f, DOWN, buff=0.15)
        self.play(Write(f), FadeIn(cap), FadeIn(dedges), *[FadeIn(c[0]) for c in dcells.values()], run_time=1.4)
        self.wait_until(self.cue_start("等于它自己", self.now))
        me, kids = self.vcells[(3, 1)][0], [self.vcells[(4, 1)][0], self.vcells[(4, 2)][0]]
        self.play(me.animate.set_stroke(C_YELLOW, 3.5), *[k.animate.set_stroke(C_TEAL, 3.5) for k in kids], run_time=0.6)
        self.play(Indicate(self.vcells[(4, 1)][1], color=C_TEAL, scale_factor=1.4), run_time=0.7)
        self.wait(0.6)
        self.play(me.animate.set_stroke(C_GREY, 2.5), *[k.animate.set_stroke(C_GREY, 2.5) for k in kids], run_time=0.4)
        self.wait_until(self.cue_start("直接递归", self.now))
        rec = VGroup(T("直接递归：", 24, C_RED), Integer(0, color=C_RED).scale(0.8), T("次调用", 24, C_RED))
        rec.arrange(RIGHT, buff=0.18).move_to([3.5, -2.15, 0])
        log = []
        D.tri_rec(D.TRI, log)
        self.play(FadeIn(rec[0]), FadeIn(rec[2]), FadeIn(rec[1]), run_time=0.3)
        self.play(ChangeDecimalToValue(rec[1], len(log)), run_time=1.4)
        _, _, order, memo = D.tri_memo()
        self.wait_until(self.cue_start("加上记忆化", self.now))
        mem = VGroup(T("记忆化：", 24, C_TEAL), Integer(len(order), color=C_TEAL).scale(0.8), T("格各算一次", 24, C_TEAL))
        mem.arrange(RIGHT, buff=0.18).next_to(rec, DOWN, buff=0.18)
        self.play(FadeIn(mem, shift=UP * 0.1), rec.animate.set_opacity(0.5), run_time=0.6)
        self.wait_until(self.cue_start("看它填表", self.now - 0.5))
        labs = {}
        step = max(0.35, min(0.75, (self.left() - 0.8) / len(order)))
        for i, j in order:
            lab = MathTex(str(memo[(i, j)]), color=C_TEAL).scale(0.68).move_to(dcells[(i, j)][0])
            srcs = [self.vcells[(i, j)][1]] + ([labs[(i + 1, j)], labs[(i + 1, j + 1)]] if i + 1 < len(D.TRI) else [])
            labs[(i, j)] = lab
            self.play(TransformFromCopy(VGroup(*srcs), lab), dcells[(i, j)][0].animate.set_stroke(C_TEAL), run_time=step)
        self.play(Indicate(labs[(0, 0)], color=C_YELLOW, scale_factor=1.4), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.2))
        self.dcells, self.dedges, self.dlabs, self.dhead = dcells, dedges, labs, VGroup(f, cap, rec, mem)

    # ---------------------------------------------------------------- 自底向上：同一张表，另一种顺序
    def triup_beat(self):
        self.beat("triup")
        dcells, labs = self.dcells, self.dlabs
        up = D.up_table()
        tag = T("一行一行往上推", 24, C_GREEN).move_to([3.5, -2.15, 0])
        self.play(FadeOut(self.dhead[2:]), FadeOut(VGroup(*labs.values())),
                  *[c[0].animate.set_stroke(C_BLUE) for c in dcells.values()], FadeIn(tag), run_time=0.8)
        new = {}
        self.wait_until(self.cue_start("底行就是它自己", self.now))
        n = len(D.TRI)
        for i in range(n - 1, -1, -1):
            anims = []
            for j in range(i + 1):
                lab = MathTex(str(up[i][j]), color=C_GREEN).scale(0.68).move_to(dcells[(i, j)][0])
                srcs = [self.vcells[(i, j)][1]] + ([new[(i + 1, j)], new[(i + 1, j + 1)]] if i + 1 < n else [])
                new[(i, j)] = lab
                anims.append(TransformFromCopy(VGroup(*srcs), lab))
                anims.append(dcells[(i, j)][0].animate.set_stroke(C_GREEN))
            self.play(*anims, run_time=1.0)
        self.wait_until(self.cue_start("十五个数", self.now))
        same = T("和记忆化填的完全一样", 24, C_TEAL).move_to(tag)
        self.play(FadeOut(tag), FadeIn(same), Indicate(new[(0, 0)], color=C_YELLOW, scale_factor=1.4), run_time=0.9)
        self.wait_until(self.cue_start("沿着较大", self.now))
        best = D.best_path()
        g1 = path_line(dcells, best, C_YELLOW, 7)
        g2 = path_line(self.vcells, best, C_YELLOW, 7)
        self.play(Create(g1), Create(g2), *[dcells[c][0].animate.set_stroke(C_YELLOW, 3.5) for c in best],
                  *[self.vcells[c][0].animate.set_stroke(C_YELLOW, 3.5) for c in best], run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(g1, g2, same, *new.values())), *[c[0].animate.set_stroke(C_GREY, 2.5)
                                                                   for c in self.vcells.values()], run_time=0.6)

    # ---------------------------------------------------------------- 从上往下推：两端特例
    def forward_beat(self):
        self.beat("forward")
        dcells = self.dcells
        fw = D.forward_table()
        cap = T("另一种状态：从顶走到这一格的最大和", 22, C_PURPLE).move_to(self.dhead[1])
        self.play(FadeOut(self.dhead[:2]), FadeIn(cap), *[c[0].animate.set_stroke(C_PURPLE, 2.5) for c in dcells.values()],
                  run_time=0.7)
        labs = {}
        anims = []
        for i, row in enumerate(fw):
            for j, v in enumerate(row):
                labs[(i, j)] = MathTex(str(v), color=WHITE).scale(0.68).move_to(dcells[(i, j)][0])
        self.play(LaggedStart(*[FadeIn(labs[(i, j)]) for i in range(len(fw)) for j in range(i + 1)], lag_ratio=0.08),
                  run_time=1.6)
        self.wait_until(self.cue_start("两端的格子", self.now))
        ends = [(i, j) for i in range(1, len(fw)) for j in (0, i)]
        note = VGroup(T("两端", 22, C_RED), T("只有一个来源", 22, C_RED)).arrange(DOWN, buff=0.08).move_to([1.15, 1.45, 0])
        self.play(*[dcells[c][0].animate.set_stroke(C_RED, 3.5) for c in ends], FadeIn(note), run_time=0.9)
        self.wait_until(self.cue_start("答案还得", self.now))
        brace = Brace(VGroup(*[dcells[(4, j)][0] for j in range(5)]), DOWN, buff=0.1, color=C_PURPLE)
        bt = T(f"再挑最大：{max(fw[-1])}", 22, C_PURPLE).next_to(brace, DOWN, buff=0.08)
        self.play(GrowFromCenter(brace), FadeIn(bt), run_time=0.8)
        self.wait_until(self.cue_start("两种定义", self.now))
        self.play(Indicate(labs[(4, 1)], color=C_YELLOW, scale_factor=1.4), run_time=0.8)
        self.wait_until(self.cue_start("可从终点倒推", self.now))
        up = D.up_table()
        ulabs = {(i, j): MathTex(str(up[i][j]), color=C_GREEN).scale(0.68).move_to(dcells[(i, j)][0])
                 for i in range(len(up)) for j in range(i + 1)}
        ucap = T("倒推：从这一格走到底的最大和", 22, C_GREEN).move_to(cap)
        self.play(*[ReplacementTransform(labs[k], ulabs[k]) for k in labs], FadeOut(VGroup(note, brace, bt)),
                  ReplacementTransform(cap, ucap), *[c[0].animate.set_stroke(C_GREEN, 2.5) for c in dcells.values()],
                  run_time=1.0)
        labs, cap = ulabs, ucap
        top_ring = SurroundingRectangle(dcells[(0, 0)][0], color=C_YELLOW, buff=0.08)
        self.wait_until(self.cue_start("答案就在顶上", self.now))
        self.play(Create(top_ring), Indicate(labs[(0, 0)], color=C_YELLOW, scale_factor=1.4), run_time=0.8)
        self.wait_until(self.cue_start("所以遇到", self.now))
        tip = T("路径题：先试从终点倒推", 30, C_YELLOW).move_to([LEFT_C, -2.45, 0])
        self.play(Write(tip), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cap, top_ring, tip, self.dedges, *labs.values(), *[c[0] for c in dcells.values()])),
                  run_time=0.6)

    # ---------------------------------------------------------------- 滚动数组
    def roll_beat(self):
        self.beat("roll")
        code = code_block(ROLL_SRC, 18).move_to([3.5, 2.75, 0])
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        n = len(D.TRI)
        boxes = VGroup(*[Square(0.72, stroke_color=C_BLUE, stroke_width=3).move_to([RIGHT_C + (j - 2) * 0.95, 0.1, 0])
                         for j in range(n)])
        idx = VGroup(*[MathTex(str(j), color=C_GREY).scale(0.55).next_to(boxes[j], DOWN, buff=0.12) for j in range(n)])
        name = Text("dp", font=MONO, font_size=26, color=C_BLUE).next_to(boxes, LEFT, buff=0.3)
        self.wait_until(self.cue_start("先把底行", self.now))
        vals = [MathTex(str(v)).scale(0.7).move_to(boxes[j]) for j, v in enumerate(D.TRI[-1])]
        self.play(FadeIn(boxes), FadeIn(idx), FadeIn(name),
                  *[TransformFromCopy(self.vcells[(n - 1, j)][1], vals[j]) for j in range(n)], run_time=1.0)
        log = D.roll_log()
        self.wait_until(self.cue_start("往上每一行", self.now))
        hl = SurroundingRectangle(code.code_lines[3], color=C_YELLOW, buff=(0.06, 0.03), stroke_width=2)
        self.play(Create(hl), run_time=0.4)
        end = self.cue_start("从左往右改", self.now + 8)
        step = max(0.55, min(1.0, (end - self.now) / len(log)))
        cur_row = None
        for i, j, a, b, v in log:
            anims = []
            if i != cur_row:
                anims += [boxes[k].animate.set_stroke(C_GREY if k > i + 1 else C_BLUE, opacity=0.35 if k > i + 1 else 1)
                          for k in range(n)]
                cur_row = i
            tv = self.vcells[(i, j)]
            self.play(*anims, tv[0].animate.set_stroke(C_YELLOW, 3.5), boxes[j].animate.set_stroke(C_TEAL, 4),
                      boxes[j + 1].animate.set_stroke(C_TEAL, 4), run_time=step * 0.35)
            nv = MathTex(str(v), color=C_GREEN).scale(0.7).move_to(boxes[j])
            self.play(ReplacementTransform(VGroup(vals[j], tv[1].copy()), nv), boxes[j + 1].animate.set_stroke(C_BLUE, 3),
                      boxes[j].animate.set_stroke(C_BLUE, 3), tv[0].animate.set_stroke(C_GREY, 2.5), run_time=step * 0.65)
            vals[j] = nv
        self.play(*[boxes[k].animate.set_stroke(C_GREY, opacity=0.35) for k in range(1, n)],
                  boxes[0].animate.set_stroke(C_YELLOW, 4), vals[0].animate.set_color(C_YELLOW), run_time=0.6)
        self.wait_until(self.cue_start("要读的右边", self.now))
        why = T("改第 j 格时，第 j+1 格还是下一行的旧值", 22, C_TEAL).move_to([RIGHT_C, -1.3, 0])
        self.play(FadeIn(why, shift=UP * 0.1), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, hl, boxes, idx, name, why, *vals, self.vedges, *self.vcells.values())),
                  run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        cols = [("递归", "想清转移", C_RED), ("记忆化", "去掉重复", C_TEAL), ("倒过来填表", "定好顺序", C_GREEN),
                ("滚成一行", "省空间", C_BLUE)]
        heads = VGroup()
        for name, sub, col in cols:
            box = RoundedRectangle(corner_radius=0.15, width=2.7, height=1.15, stroke_color=col, stroke_width=2.5)
            heads.add(VGroup(box, VGroup(T(name, 28, col), T(sub, 20, C_GREY)).arrange(DOWN, buff=0.1).move_to(box)))
        heads.arrange(RIGHT, buff=0.35).move_to([0.6, 2.2, 0])
        _, mcalls, morder, _ = D.tri_memo()
        rows = [("爬楼梯", [f"{SF['rec_calls']} 次调用", f"{SF['memo_calls']} 次调用", f"循环 {SF['loop_iters']} 次", "两个变量"]),
                ("三角形", [f"{2 ** len(D.TRI) - 1} 次调用", f"{len(morder)} 格", f"{len(morder)} 格", f"一行 {len(D.TRI)} 格"])]
        grid = VGroup()
        for r, (lab, items) in enumerate(rows):
            y = 0.75 - 0.75 * r
            grid.add(T(lab, 26).move_to([-5.6, y, 0]))
            for k, s in enumerate(items):
                grid.add(T(s, 24, "#D8DCE6").move_to([heads[k].get_x(), y, 0]))
        self.play(LaggedStart(*[FadeIn(h, shift=UP * 0.2) for h in heads], lag_ratio=0.25), run_time=1.6)
        self.play(FadeIn(grid), run_time=0.8)
        self.wait_until(self.cue_start("下一支", self.now))
        nxt = VGroup(T("加一条限制：路径和必须是奇数", 30, C_YELLOW), T("这张表还够用吗？", 26, C_GREY)).arrange(DOWN, buff=0.2)
        nxt.move_to([0, -1.65, 0])
        self.play(FadeIn(nxt, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 10 周 动态规划入门 · 讲义 2.3–2.6", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
