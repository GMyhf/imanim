"""这段代码够快吗：从数据范围倒推算法（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。循环格子、各级别次数、数据范围表的代入次数、list/set 比较次数、
筛法逐步划掉的数与试除/筛法的计数全部来自 complexitydata（讲义 sieve / bench / 两重循环原样，试除法为补写；
test_complexity.py 用闭式、独立判素与按素数求和的公式对撞讲义输出与旁白数字）。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import complexitydata as D  # noqa: E402
from cine import *  # noqa: E402,F403

PCOL = {2: C_BLUE, 3: C_TEAL, 5: C_PURPLE, 7: C_RED}     # 筛法里各素数划掉的颜色


def mkcode(src, size=24):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


def hl(code, lines, col, sw=2.5):
    return VGroup(*[SurroundingRectangle(code.code_lines[k], color=col, buff=(0.08, 0.03), stroke_width=sw)
                    for k in lines])


def tex(s, scale=0.8, color=WHITE):
    return MathTex(s, color=color).scale(scale)


def sci(v, digits=1):
    """3628800 → 3.6\\times10^{6}。"""
    e = int(math.floor(math.log10(v)))
    m = v / 10 ** e
    return rf"{m:.{digits}f}\times10^{{{e}}}"


def grouped(v):
    return f"{v:,}".replace(",", r"\,")


class ComplexityLesson(Lesson):
    def construct(self):
        for b in ("title", "count", "levels", "budget", "space", "hidden", "sieve", "versus", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def cue_at(self, key, default=None):
        """key 在句中的大致时刻：句起点 + 句长按字数比例。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    def fade_all(self, rt=0.6):
        keep = set(map(id, self.subs))
        rest = [m for m in self.mobjects if id(m) not in keep and m is not self.camera.frame]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)
            self.remove(*rest)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("这段代码够快吗", 54).move_to([0, 3.0, 0])
        sub = T("从数据范围倒推算法", 30, C_BLUE).next_to(title, DOWN, buff=0.2)
        prob = VGroup(T("题目：", 30, C_GREY), tex(rf"n\le 10^{{{int(math.log10(D.OPEN_N))}}}", 0.95, C_YELLOW),
                      T("，时限 1 秒", 30)).arrange(RIGHT, buff=0.15).move_to([0, 1.25, 0])
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), FadeIn(prob), run_time=1.4)
        self.wait_until(self.cue_start("你想到", self.now))
        code = mkcode("for i in range(n):\n    for j in range(i, n):\n        ...\n", 26).move_to([-0.6, -0.15, 0])
        q = T("能过吗？", 34, C_RED).next_to(code, RIGHT, buff=0.5)
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.8)
        self.play(FadeIn(q, scale=1.2), run_time=0.5)
        self.wait_until(self.cue_start("不用提交", self.now))
        lo, hi = D.OPS_PER_SEC
        cmp_ = VGroup(T("要做多少次基本操作", 28, C_TEAL), tex(r"\longleftrightarrow", 0.9, C_GREY),
                      T("机器每秒能做多少次", 28, C_YELLOW)).arrange(RIGHT, buff=0.35).move_to([0, -2.0, 0])
        self.play(FadeIn(cmp_[0], shift=UP * 0.2), run_time=0.7)
        self.play(GrowFromCenter(cmp_[1]), FadeIn(cmp_[2], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.8))
        self.play(FadeOut(VGroup(title, sub, prob, q, cmp_)), run_time=0.5)
        self.code = code

    # ---------------------------------------------------------------- 数两重循环
    def count_beat(self):
        self.beat("count")
        code = self.code
        self.play(code.animate.scale(0.9).move_to([-3.6, 1.85, 0]), run_time=0.7)
        n = D.DEMO_N
        C, gx0, gy0 = 0.6, 1.3, 2.0
        pos = lambda i, j: np.array([gx0 + C * j, gy0 - C * i, 0])  # noqa: E731
        cells = {(i, j): Square(C, stroke_color=C_GREY, stroke_width=2).move_to(pos(i, j))
                 for i in range(n) for j in range(n)}
        grid = VGroup(*cells.values())
        jl = VGroup(*[T(str(j), 20, C_GREY).next_to(cells[0, j], UP, buff=0.12) for j in range(n)])
        il = VGroup(*[T(str(i), 20, C_GREY).next_to(cells[i, 0], LEFT, buff=0.14) for i in range(n)])
        jn = T("j", 26, C_TEAL).next_to(jl, RIGHT, buff=0.3)
        inn = T("i", 26, C_YELLOW).next_to(il[0], UP, buff=0.12)
        hl_i = hl(code, [0], C_YELLOW)
        self.wait_until(self.cue_start("外层", self.now))
        self.play(Create(grid), FadeIn(il), FadeIn(inn), Create(hl_i), run_time=1.0)
        self.wait_until(self.cue_at("内层", self.now))
        hl_j = hl(code, [1], C_TEAL)
        self.play(FadeIn(jl), FadeIn(jn), ReplacementTransform(hl_i, hl_j), run_time=0.7)
        rows = D.row_counts(n)
        cells_run = D.loop_triangle(n)
        lab = T("执行次数", 28).move_to([-4.3, 0.2, 0])
        cnt = tex("0", 1.0, C_TEAL).next_to(lab, RIGHT, buff=0.3)
        rlabs = VGroup()
        self.wait_until(self.cue_start("等于六时", self.now))
        self.play(FadeIn(lab), FadeIn(cnt), FadeOut(hl_j), run_time=0.5)
        keys = ("第一行", "下一行", "一直到")
        total = 0
        for i in range(n):
            if i < len(keys):
                self.wait_until(self.cue_at(keys[i], self.now))
            row_cells = [cells[a, b] for a, b in cells_run if a == i]
            total += rows[i]
            rl = T(str(rows[i]), 24, C_TEAL).next_to(cells[i, n - 1], RIGHT, buff=0.25)
            new = tex(str(total), 1.0, C_TEAL).next_to(lab, RIGHT, buff=0.3)
            rt = 0.9 if i < 2 else 0.4
            self.play(LaggedStart(*[c.animate.set_fill(C_TEAL, 0.45).set_stroke(C_TEAL, 2.5) for c in row_cells],
                                  lag_ratio=0.15),
                      FadeIn(rl), Transform(cnt, new), run_time=rt)
            rlabs.add(rl)
        self.wait_until(self.cue_start("也就是", self.now))
        f1 = tex(rf"\frac{{n(n+1)}}{{2}}=\frac{{{n}\times{n + 1}}}{{2}}={D.triangle_count(n)}", 0.85, WHITE)
        f1.move_to([-3.6, -0.9, 0])
        self.play(Write(f1), run_time=1.0)
        self.wait_until(self.cue_start("只占", self.now))
        lower = VGroup(*[cells[i, j] for i in range(n) for j in range(i)])
        half = VGroup(tex(r"\approx\tfrac12 n^2", 0.85), tex(r"\Rightarrow\ O(n^2)", 0.85, C_RED)).arrange(RIGHT, buff=0.25)
        half.move_to([-3.6, -1.9, 0])
        self.play(*[c.animate.set_stroke(C_GREY, 3) for c in lower], FadeIn(half, shift=UP * 0.2), run_time=0.9)
        self.wait_until(self.cue_start("大 O", self.now))
        a, b, d = D.POLY
        big = tex(rf"{a}n^2+{b}n+{d}\ \longrightarrow\ O(n^2)", 0.85, C_YELLOW).move_to([2.8, -1.6, 0])
        note = T("忽略常数与低阶项", 24, C_GREY).next_to(big, DOWN, buff=0.22)
        self.play(Write(big), run_time=1.1)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 常见级别（对数横轴）
    def levels_beat(self):
        self.beat("levels")
        X0, U = -2.8, 0.58                        # 横轴起点（10⁰）与每一格（十倍）的宽度
        rows_y = [2.3, 1.5, 0.7, -0.1, -0.9]
        head = VGroup(tex(rf"n=10^{{{int(math.log10(D.LEVEL_N))}}}", 0.9, C_YELLOW),
                      T("时，各级别要做多少次", 30)).arrange(RIGHT, buff=0.2).move_to([0, 3.2, 0])
        ax_y = -1.6
        axis = Line([X0, ax_y, 0], [X0 + 12 * U, ax_y, 0], color=C_GREY, stroke_width=2)
        ticks = VGroup(*[Line([X0 + k * U, ax_y - 0.08, 0], [X0 + k * U, ax_y + 0.08, 0], color=C_GREY,
                              stroke_width=2) for k in range(13)])
        tl = VGroup(*[tex(rf"10^{{{k}}}", 0.72, C_GREY).next_to(ticks[k], DOWN, buff=0.14) for k in range(0, 13, 3)])
        self.play(FadeIn(head), Create(axis), Create(ticks), FadeIn(tl), run_time=1.0)
        lv = D.levels()
        keys = ("log n 大约", "n 是一百万", "n log n 约", "n 平方是", "二的 n 次方")
        vals = [r"\approx 20", r"10^6", r"\approx 2\times10^7", r"10^{12}", None]
        cols = [C_GREEN, C_TEAL, C_BLUE, C_YELLOW, C_RED]
        bars = VGroup()
        self.lvl_parts = []
        for k, ((name, tx, v, lg), key, val, col) in enumerate(zip(lv, keys, vals, cols)):
            y = rows_y[k]
            nm = tex(tx, 0.8, col)
            nm.move_to([X0 - 0.35 - nm.width / 2, y, 0])
            w = U * min(lg, 12)
            bar = Rectangle(width=w, height=0.4, stroke_color=col, stroke_width=2).set_fill(col, 0.45)
            bar.move_to([X0 + w / 2, y, 0])
            extra = VGroup()
            if val is None:
                vl = T("天文数字", 24, col)
                extra.add(Arrow([X0 + w - 0.1, y, 0], [X0 + w + 0.5, y, 0], buff=0, color=col, stroke_width=5,
                                max_tip_length_to_length_ratio=0.5))
            else:
                vl = tex(val, 0.7, col)
            vl.move_to([5.6, y, 0])
            self.wait_until(self.cue_at(key, self.now))
            self.play(FadeIn(nm), GrowFromEdge(bar, LEFT), *[GrowArrow(e) for e in extra], FadeIn(vl), run_time=0.7)
            bars.add(bar)
            self.lvl_parts.append((nm, bar, vl, extra))
        self.wait_until(self.cue_start("横轴", self.now))
        self.play(LaggedStart(*[Indicate(t, color=C_YELLOW, scale_factor=1.6) for t in ticks], lag_ratio=0.08),
                  run_time=1.2)
        self.wait_until(self.cue_at("n 平方比", self.now))
        xn, xn2 = X0 + 6 * U, X0 + 12 * U
        y = rows_y[1]
        g1 = DashedLine([xn, y + 0.3, 0], [xn, rows_y[3] - 0.3, 0], color=WHITE, stroke_width=2)
        g2 = DashedLine([xn2, y + 0.3, 0], [xn2, rows_y[3] - 0.3, 0], color=WHITE, stroke_width=2)
        span = DoubleArrow([xn, y, 0], [xn2, y, 0], buff=0, color=C_YELLOW, stroke_width=4,
                           max_tip_length_to_length_ratio=0.08)
        sl = VGroup(T("高出 6 格", 24, C_YELLOW), tex(r"=10^6", 0.7, C_YELLOW), T("倍", 24, C_YELLOW))
        sl.arrange(RIGHT, buff=0.12).move_to([(xn + xn2) / 2, y - 0.38, 0])
        self.play(Create(g1), Create(g2), GrowFromCenter(span), run_time=0.8)
        self.play(FadeIn(sl), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 从数据范围倒推
    def budget_beat(self):
        self.beat("budget")
        AX, Y5 = 3.7, -2.3                       # 竖轴 x、10⁵ 的位置；每格（十倍）高 1
        ay = lambda v: Y5 + (math.log10(v) - 5)  # noqa: E731
        axis = Arrow([AX, Y5 - 0.1, 0], [AX, ay(10 ** 10) + 0.35, 0], buff=0, color=C_GREY, stroke_width=2,
                     max_tip_length_to_length_ratio=0.04)
        ticks = VGroup(*[Line([AX - 0.08, ay(10 ** e), 0], [AX + 0.08, ay(10 ** e), 0], color=C_GREY, stroke_width=2)
                         for e in range(5, 11)])
        tl = VGroup(*[tex(rf"10^{{{e}}}", 0.7, C_GREY).next_to(ticks[e - 5], RIGHT, buff=0.45) for e in range(5, 11)])
        lo, hi = D.OPS_PER_SEC
        band = Rectangle(width=0.7, height=ay(hi) - ay(lo), stroke_width=0).set_fill(C_YELLOW, 0.3)
        band.move_to([AX, (ay(hi) + ay(lo)) / 2, 0])
        bl = VGroup(T("每秒", 24, C_YELLOW), tex(r"10^7\sim10^8", 0.65, C_YELLOW)).arrange(DOWN, buff=0.1)
        bl.next_to(band, RIGHT, buff=1.15)
        self.play(Create(axis), Create(ticks), FadeIn(tl), run_time=0.8)
        self.play(FadeIn(band), FadeIn(bl), run_time=0.6)
        # 左半：数据范围表
        cx = [-5.9, -4.2, -2.2, -0.15]
        hy, dy = 2.85, 0.68
        heads = VGroup(*[T(s, 22, C_GREY).move_to([x, hy, 0]) for s, x in zip(("n ≤", "复杂度", "该想什么", "代入次数"), cx)])
        self.wait_until(self.cue_start("所以看到", self.now))
        self.play(FadeIn(heads[:3]), run_time=0.5)
        rows = D.budget_rows()
        keys = ("不超过十", "二十，", "一百，", "一千，", "十万，", "一百万，")
        cols = [C_RED, C_PURPLE, C_BLUE, C_TEAL, C_GREEN, C_YELLOW]
        cells = []
        for k, ((n, cplx, what, ops), key, col) in enumerate(zip(rows, keys, cols)):
            y = hy - dy * (k + 1)
            nb = tex(grouped(n) if n < 10 ** 4 else rf"10^{{{int(math.log10(n))}}}", 0.72).move_to([cx[0], y, 0])
            cp = tex(cplx, 0.72, col).move_to([cx[1], y, 0])
            wt = T(what, 22).move_to([cx[2], y, 0])
            self.wait_until(self.cue_at(key, self.now))
            self.play(FadeIn(VGroup(nb, cp, wt), shift=RIGHT * 0.2), run_time=0.45)
            cells.append((nb, cp, wt, col, ops, y))
        self.wait_until(self.cue_start("代进去", self.now))
        opsv, dots, links = VGroup(), VGroup(), VGroup()
        for k, (nb, cp, wt, col, ops, y) in enumerate(cells):
            ov = tex(sci(ops), 0.68, col).move_to([cx[3], y, 0])
            dot = Dot([AX, ay(ops), 0], radius=0.07, color=col)
            ln = Line(ov.get_right() + RIGHT * 0.12, dot.get_center() + LEFT * 0.08, color=col, stroke_width=1.8,
                      stroke_opacity=0.7)
            opsv.add(ov)
            dots.add(dot)
            links.add(ln)
        self.play(FadeIn(heads[3]), LaggedStart(*[FadeIn(o) for o in opsv], lag_ratio=0.15), run_time=1.0)
        self.play(LaggedStart(*[Create(x) for x in links], lag_ratio=0.12), FadeIn(dots), run_time=1.2)
        mn, mx = min(r[3] for r in rows), max(r[3] for r in rows)
        brace = BraceBetweenPoints([AX + 1.1, ay(mx) + 0.05, 0], [AX + 1.1, ay(mn) - 0.05, 0], RIGHT, color=C_GREEN)
        bt = VGroup(T("留出", 22, C_GREEN), T("常数余量", 22, C_GREEN)).arrange(DOWN, buff=0.08).next_to(brace, RIGHT, buff=0.12)
        self.wait_until(self.cue_start("给常数", self.cue_at("一百万到", self.now)))
        self.play(GrowFromCenter(brace), FadeIn(bt), run_time=0.7)
        self.wait_until(self.cue_start("回到开头", self.now))
        o = D.open_ops()
        rd = Dot([AX, ay(o), 0], radius=0.11, color=C_RED)
        rl = VGroup(tex(rf"n=10^5", 0.6, C_RED), T("两重循环", 22, C_RED),
                    tex(rf"\approx {o / 1e9:.0f}\times10^9", 0.65, C_RED)).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        rl.next_to(rd, RIGHT, buff=1.15)
        tle = T("超时", 30, C_RED).next_to(rl, DOWN, buff=0.2).align_to(rl, LEFT)
        self.play(FadeIn(rd, scale=2), FadeIn(rl, shift=LEFT * 0.2), run_time=0.8)
        self.play(FadeIn(tle, scale=1.3), Flash(rd, color=C_RED), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 空间复杂度
    def space_beat(self):
        self.beat("space")
        head = T("空间也这样估", 32).move_to([0, 3.2, 0])
        self.play(FadeIn(head), run_time=0.6)
        self.wait_until(self.cue_start("列表里", self.now))
        ptr = Square(0.62, stroke_color=C_BLUE, stroke_width=3).move_to([-4.6, 2.05, 0])
        pdot = Dot(ptr.get_center(), radius=0.07, color=C_BLUE)
        obj = RoundedRectangle(corner_radius=0.12, width=1.9, height=0.75, stroke_color=C_TEAL, stroke_width=3)
        obj.move_to([-1.9, 2.05, 0])
        ot = T("int 对象", 24, C_TEAL).move_to(obj)
        link = Arrow(pdot.get_center(), obj.get_left(), buff=0.05, color=C_BLUE, stroke_width=3)
        pl = tex(rf"{D.PTR_BYTES}\,\mathrm{{B}}", 0.65, C_BLUE).next_to(ptr, DOWN, buff=0.15)
        ol = tex(rf"{D.INT_BYTES}\,\mathrm{{B}}", 0.65, C_TEAL).next_to(obj, DOWN, buff=0.15)
        pn = T("指针", 22, C_GREY).next_to(ptr, LEFT, buff=0.2)
        self.play(Create(ptr), FadeIn(pdot), FadeIn(pn), run_time=0.5)
        self.play(GrowArrow(link), Create(obj), FadeIn(ot), FadeIn(pl), FadeIn(ol), run_time=0.8)
        # 下半：以兆字节为单位的横轴
        X0, K, ay = -5.6, 11.4 / 900, -2.0
        mx = lambda mb: X0 + K * mb  # noqa: E731
        axis = Line([X0, ay, 0], [mx(900), ay, 0], color=C_GREY, stroke_width=2)
        ticks = VGroup(*[Line([mx(v), ay - 0.07, 0], [mx(v), ay + 0.07, 0], color=C_GREY, stroke_width=2)
                         for v in range(0, 901, 200)])
        tls = VGroup(*[tex(str(v), 0.65, C_GREY).next_to(ticks[k], DOWN, buff=0.1) for k, v in enumerate(range(0, 901, 200))])
        unit = tex(r"\mathrm{MB}", 0.65, C_GREY).next_to(axis, RIGHT, buff=0.15)
        self.wait_until(self.cue_start("一百万个", self.cue_at("一百万个", self.now)))
        mb = D.list_mb()
        per = tex(rf"\times 10^{{{int(math.log10(D.SPACE_LIST_N))}}}\approx {mb:.0f}\,\mathrm{{MB}}", 0.75, C_GREEN)
        per.next_to(obj, RIGHT, buff=0.5)
        gb = Rectangle(width=K * mb, height=0.42, stroke_color=C_GREEN, stroke_width=2).set_fill(C_GREEN, 0.5)
        gb.move_to([X0 + K * mb / 2, -0.35, 0])
        gl = VGroup(tex(r"10^6", 0.6, C_GREEN), T("个整数", 22, C_GREEN)).arrange(RIGHT, buff=0.1)
        gl.next_to(gb, RIGHT, buff=0.2)
        self.play(FadeIn(per, shift=LEFT * 0.2), Create(axis), Create(ticks), FadeIn(tls), FadeIn(unit), run_time=0.8)
        self.play(GrowFromEdge(gb, LEFT), FadeIn(gl), run_time=0.6)
        self.wait_until(self.cue_start("内存限制", self.now))
        lo, hi = D.MEM_LIMIT_MB
        band = Rectangle(width=K * (hi - lo), height=2.0, stroke_width=0).set_fill(C_YELLOW, 0.22)
        band.move_to([mx((lo + hi) / 2), ay + 1.05, 0]).set_z_index(-1)
        bl = VGroup(T("常见内存限制", 22, C_YELLOW), tex(rf"{lo}\sim{hi}\,\mathrm{{MB}}", 0.6, C_YELLOW))
        bl.arrange(RIGHT, buff=0.15).next_to(band, UP, buff=0.12).align_to(band, LEFT)
        self.play(FadeIn(band), FadeIn(bl), run_time=0.7)
        self.wait_until(self.cue_start("一万乘一万", self.now))
        g = D.grid_ptr_mb()
        rb = Rectangle(width=K * g, height=0.42, stroke_color=C_RED, stroke_width=2).set_fill(C_RED, 0.5)
        rb.move_to([X0 + K * g / 2, -1.3, 0])
        rl = VGroup(tex(r"10^4\times10^4", 0.6, C_RED), T("二维表，光指针", 22, C_RED),
                    tex(rf"{g:.0f}\,\mathrm{{MB}}", 0.65, C_RED)).arrange(RIGHT, buff=0.15)
        rl.next_to(rb, UP, buff=0.12).align_to(rb, RIGHT)
        self.play(GrowFromEdge(rb, LEFT), run_time=1.0)
        self.play(FadeIn(rl), run_time=0.5)
        self.wait_until(self.cue_start("必然", self.cue_at("必然", self.now)))
        mle = T("超内存", 30, C_RED).next_to(rb, RIGHT, buff=0.3)
        self.play(FadeIn(mle, scale=1.3), Indicate(rb, color=C_RED, scale_factor=1.03), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 藏在一行里的复杂度：list in 与 set in
    def hidden_beat(self):
        self.beat("hidden")
        code = mkcode("for x in queries:\n    if x in lst:\n        ...\n", 24).move_to([-3.6, 2.45, 0])
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("循环里", self.now))
        h = hl(code, [1], C_RED)
        self.play(Create(h), run_time=0.5)
        # list：从头一个个比
        vals = list(range(10))
        x = 6
        C, x0, ly = 0.55, -5.3, 0.75
        lcells = VGroup(*[Square(C, stroke_color=C_GREY, stroke_width=2).move_to([x0 + C * k, ly, 0])
                          for k in range(len(vals))])
        lnums = VGroup(*[Text(str(v), font=MONO, font_size=22).move_to(lcells[k]) for k, v in enumerate(vals)])
        dots = T("…", 24, C_GREY).next_to(lcells, RIGHT, buff=0.12)
        lname = Text("list", font=MONO, font_size=26, color=C_BLUE).next_to(lcells, LEFT, buff=0.25)
        qx = VGroup(T("找", 24), Text(str(x), font=MONO, font_size=26, color=C_YELLOW)).arrange(RIGHT, buff=0.1)
        qx.next_to(lcells, UP, buff=0.25).align_to(lcells, LEFT)
        self.wait_until(self.cue_start("list 要", self.cue_at("list 要", self.now)))
        self.play(FadeIn(VGroup(lcells, lnums, dots, lname, qx)), run_time=0.5)
        scan = D.scan_demo(vals, x)
        ptr = Triangle(color=C_YELLOW, fill_opacity=1).scale(0.1).rotate(PI).next_to(lcells[0], UP, buff=0.06)
        self.add(ptr)
        for k in scan:
            hit = vals[k] == x
            self.play(ptr.animate.next_to(lcells[k], UP, buff=0.06),
                      lcells[k].animate.set_stroke(C_GREEN if hit else C_RED, 3), run_time=0.17)
        nc = T(f"比较 {len(scan)} 次", 22, C_RED).next_to(dots, RIGHT, buff=0.25)
        self.play(FadeIn(nc), run_time=0.3)
        self.wait_until(self.cue_at("这一行就是", self.now))
        on = tex(r"O(n)", 0.7, C_RED).next_to(code, RIGHT, buff=0.3).align_to(code.code_lines[1], DOWN)
        self.play(FadeIn(on, shift=LEFT * 0.2), run_time=0.5)
        self.wait_until(self.cue_at("整个循环", self.now))
        whole = tex(r"\Rightarrow\ O(n^2)", 0.8, C_RED).next_to(on, RIGHT, buff=0.25)
        self.play(FadeIn(whole, shift=LEFT * 0.2), run_time=0.5)
        # set：哈希直接定位
        self.wait_until(self.cue_start("set 靠", self.now))
        nb = 7
        sy = -1.05
        buckets = VGroup(*[Rectangle(width=0.55, height=0.55, stroke_color=C_GREY, stroke_width=2)
                           .move_to([x0 + 0.75 * k, sy, 0]) for k in range(nb)])
        bidx = VGroup(*[T(str(k), 16, C_GREY).next_to(buckets[k], DOWN, buff=0.08) for k in range(nb)])
        bvals = VGroup()
        for v in vals:
            k = v % nb
            depth = sum(1 for u in vals if u < v and u % nb == k)
            t = Text(str(v), font=MONO, font_size=18, color=WHITE)
            t.move_to(buckets[k].get_center() + UP * (0.12 - 0.24 * depth) if any(u % nb == k and u != v for u in vals)
                      else buckets[k].get_center())
            bvals.add(t)
        sname = Text("set", font=MONO, font_size=26, color=C_TEAL).next_to(buckets, LEFT, buff=0.25)
        sname.align_to(lname, RIGHT)
        self.play(FadeIn(VGroup(buckets, bidx, bvals, sname)), run_time=0.6)
        hx = VGroup(Text(f"hash({x}) % {nb} = {x % nb}", font=MONO, font_size=24, color=C_YELLOW))
        hx.next_to(buckets, RIGHT, buff=0.35)
        tgt = buckets[x % nb]
        jump = CurvedArrow(hx.get_left() + LEFT * 0.08 + UP * 0.1, tgt.get_top() + UP * 0.05, angle=PI / 3,
                           color=C_YELLOW, stroke_width=3)
        self.play(FadeIn(hx), run_time=0.4)
        self.play(Create(jump), tgt.animate.set_stroke(C_GREEN, 3.5), run_time=0.6)
        one = T("一次", 22, C_GREEN).next_to(hx, DOWN, buff=0.15)
        self.play(FadeIn(one), run_time=0.3)
        # 右半：讲义实验
        self.wait_until(self.cue_start("讲义的实验", self.now))
        demo = VGroup(lcells, lnums, dots, lname, qx, ptr, nc, buckets, bidx, bvals, sname, hx, jump, one)
        demo.generate_target()
        demo.target.scale(0.8)
        demo.target.shift([-6.75 - demo.target.get_left()[0], -0.35 - demo.target.get_y(), 0])
        self.play(MoveToTarget(demo), run_time=0.6)
        exp = T(f"讲义实验：{D.BENCH_N // 10 ** 4} 万个数，查 {D.set_lookups()} 次", 26).move_to([3.85, 1.75, 0])
        self.play(FadeIn(exp), run_time=0.5)
        self.wait_until(self.cue_start("list 共", self.now))
        lc, sl = D.list_in_compares(), D.set_lookups()
        BX, BW = 1.2, 5.3
        lb = Rectangle(width=BW, height=0.42, stroke_color=C_BLUE, stroke_width=2).set_fill(C_BLUE, 0.45)
        lb.move_to([BX + BW / 2, 0.95, 0])
        sb = Rectangle(width=max(0.02, BW * sl / lc), height=0.42, stroke_color=C_TEAL, stroke_width=2)
        sb.set_fill(C_TEAL, 0.9).move_to([BX, -0.25, 0], aligned_edge=LEFT)
        lt = VGroup(Text("list", font=MONO, font_size=22, color=C_BLUE), T("比较", 22),
                    tex(rf"{grouped(lc)}", 0.65, C_BLUE), T("次", 22)).arrange(RIGHT, buff=0.12)
        lt.next_to(lb, DOWN, buff=0.12).align_to(lb, LEFT)
        st = VGroup(Text("set", font=MONO, font_size=22, color=C_TEAL), T("查", 22),
                    tex(str(sl), 0.65, C_TEAL), T("次", 22)).arrange(RIGHT, buff=0.12)
        st.next_to(sb, DOWN, buff=0.12).align_to(lb, LEFT)
        self.play(GrowFromEdge(lb, LEFT), FadeIn(lt), run_time=0.8)
        self.play(GrowFromEdge(sb, LEFT), FadeIn(st), run_time=0.5)
        self.wait_until(self.cue_start("实测", self.now))
        tm = VGroup(T("实测", 24, C_GREY), tex(rf"{D.TYPICAL_LIST_S}\,\mathrm{{s}}", 0.75, C_BLUE),
                    tex(r":", 0.75), tex(rf"{D.TYPICAL_SET_S:.4f}\,\mathrm{{s}}", 0.75, C_TEAL)).arrange(RIGHT, buff=0.2)
        tm.move_to([3.85, -1.4, 0])
        k = int(math.log10(D.TYPICAL_LIST_S / D.TYPICAL_SET_S))
        mag = T(f"差{'一二三四五'[k - 1]}个数量级", 30, C_YELLOW).next_to(tm, DOWN, buff=0.3)
        self.play(FadeIn(tm), run_time=0.6)
        self.play(Write(mag), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 埃氏筛
    def gpos(self, v):
        """数 v（1..100）在 10×10 格子里的位置。"""
        r, c = divmod(v - 1, 10)
        return np.array([self.GX + 0.52 * (c - 4.5), self.GY - 0.52 * (r - 4.5), 0])

    def sieve_beat(self):
        self.beat("sieve")
        N = D.SIEVE_N
        self.GX, self.GY = -3.6, 0.3
        sq = {v: Square(0.52, stroke_color=C_GREY, stroke_width=1.5).move_to(self.gpos(v)) for v in range(1, N + 1)}
        nums = {v: Text(str(v), font=MONO, font_size=18).move_to(self.gpos(v)) for v in range(1, N + 1)}
        head = T(f"{N} 以内的素数", 30).move_to([self.GX, 3.25, 0])
        self.play(FadeIn(head), Create(VGroup(*sq.values())), FadeIn(VGroup(*nums.values())), run_time=1.2)
        self.play(nums[1].animate.set_color(C_GREY).set_opacity(0.35), run_time=0.3)
        self.wait_until(self.cue_start("朴素做法", self.now))
        trial = VGroup(T("试除：", 24, C_GREY), T("每个数 x 用 2 … √x 逐个去除", 24)).arrange(RIGHT, buff=0.1)
        trial.move_to([3.6, 2.9, 0])
        self.play(FadeIn(trial, shift=LEFT * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("埃氏筛", self.now))
        code = mkcode("is_prime = [True] * (limit + 1)\nis_prime[0] = is_prime[1] = False\ni = 2\n"
                      "while i * i <= limit:\n    if is_prime[i]:\n        for j in range(i * i, limit + 1, i):\n"
                      "            is_prime[j] = False\n    i += 1\n", 20)
        code.scale_to_fit_width(6.0).move_to([3.75, 0.7, 0])
        self.play(trial.animate.set_opacity(0.45), FadeIn(code, shift=UP * 0.2), run_time=0.7)
        trace, isp = D.sieve_trace(N)
        status = T("i = 2", 24).move_to([3.75, -1.6, 0]).set_opacity(0)
        self.add(status)
        cnt_l = T("已划掉", 24, C_GREY).move_to([3.0, -2.35, 0])
        cnt = tex("0", 0.8, WHITE).next_to(cnt_l, RIGHT, buff=0.2)
        cnt_u = T("次", 24, C_GREY).next_to(cnt, RIGHT, buff=0.15)
        self.play(FadeIn(VGroup(cnt_l, cnt, cnt_u)), run_time=0.3)
        keys = {2: "二留下", 3: "三留下", 4: "四已被", 5: "然后是五", 7: "和七"}
        marked = 0
        h = None
        for i, alive, marks in trace:
            if i not in keys:
                continue
            self.wait_until(self.cue_at(keys[i], self.now))
            if not alive:
                ns = T(f"i = {i}：已被划掉，跳过", 24, C_GREY).move_to(status)
                nh = hl(code, [4], C_GREY)
                self.play(Transform(status, ns), Indicate(sq[i], color=C_GREY, scale_factor=1.3),
                          *([ReplacementTransform(h, nh)] if h else [Create(nh)]), run_time=0.6)
                h = nh
                continue
            col = PCOL[i]
            ns = T(f"i = {i}：从 {i * i} 起每隔 {i} 划一个", 24, col).move_to(status)
            nh = hl(code, [5, 6], col)
            self.play(Transform(status, ns), sq[i].animate.set_stroke(col, 3.5), nums[i].animate.set_color(C_YELLOW),
                      *([ReplacementTransform(h, nh)] if h else [Create(nh)]), run_time=0.45)
            h = nh
            marked += len(marks)
            new = tex(str(marked), 0.8, WHITE).next_to(cnt_l, RIGHT, buff=0.2)
            rt = {2: 1.6, 3: 1.2, 5: 0.8, 7: 0.6}[i]
            self.play(LaggedStart(*[AnimationGroup(sq[j].animate.set_fill(col, 0.32),
                                                   nums[j].animate.set_color(C_GREY)) for j in marks],
                                  lag_ratio=0.25), Transform(cnt, new), cnt_u.animate.next_to(new, RIGHT, buff=0.15),
                      run_time=rt)
        self.wait_until(self.cue_start("每次从", self.now))
        sqs = [i * i for i, alive, m in trace if alive]
        rings = VGroup(*[Circle(radius=0.3, color=PCOL[i], stroke_width=3.5).move_to(self.gpos(i * i))
                         for i, alive, m in trace if alive])
        ns = T("更小的倍数早被更小的因子划过", 24, C_YELLOW).move_to(status)
        self.play(Create(rings), Transform(status, ns), run_time=0.8)
        self.wait_until(self.cue_start("剩下的", self.now))
        primes = D.primes_upto(N)
        res = VGroup(T("剩下", 26), tex(str(len(primes)), 0.9, C_YELLOW), T("个素数", 26)).arrange(RIGHT, buff=0.15)
        res.move_to(status)
        self.play(FadeOut(rings), FadeOut(h),
                  *[sq[p].animate.set_stroke(C_YELLOW, 3) for p in primes],
                  *[nums[p].animate.set_color(C_YELLOW) for p in primes],
                  FadeOut(status), FadeIn(res), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()
        _ = sqs, isp

    # ---------------------------------------------------------------- 试除 vs 筛
    def versus_beat(self):
        self.beat("versus")
        cx = [-4.3, -0.4, 3.6]
        hy = 2.5
        heads = VGroup(T("范围", 26, C_GREY).move_to([cx[0], hy, 0]), T("试除：除法次数", 26, C_RED).move_to([cx[1], hy, 0]),
                       T("埃氏筛：划掉次数", 26, C_TEAL).move_to([cx[2], hy, 0]))
        rule = Line([-6.3, hy - 0.4, 0], [6.3, hy - 0.4, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(heads), Create(rule), run_time=0.7)
        rows = []
        for k, (lim, key) in enumerate(((D.SIEVE_N, "一百以内"), (D.BIG_SIEVE_N, "到一百万"))):
            y = 1.55 - 1.0 * k
            t, s = D.versus(lim)
            lab = VGroup(tex(str(lim) if lim < 10 ** 4 else rf"10^{{{int(math.log10(lim))}}}", 0.85),
                         T("以内", 26)).arrange(RIGHT, buff=0.15).move_to([cx[0], y, 0])
            tv = tex(grouped(t), 0.85, C_RED).move_to([cx[1], y, 0])
            sv = tex(grouped(s), 0.85, C_TEAL).move_to([cx[2], y, 0])
            self.wait_until(self.cue_at(key, self.now))
            self.play(FadeIn(lab), FadeIn(tv, shift=UP * 0.15), run_time=0.6)
            self.wait(0.5)
            self.play(FadeIn(sv, shift=UP * 0.15), run_time=0.6)
            rows.append((t, s, tv, sv))
        self.wait_until(self.cue_start("差了", self.cue_at("差了", self.now)))
        t, s, tv, sv = rows[-1]
        ratio = VGroup(T("约", 26, C_YELLOW), tex(rf"{t / s:.0f}", 0.9, C_YELLOW), T("倍", 26, C_YELLOW))
        ratio.arrange(RIGHT, buff=0.12).move_to([(cx[1] + cx[2]) / 2, -0.35, 0])
        arr = CurvedArrow(tv.get_bottom() + DOWN * 0.08, sv.get_bottom() + DOWN * 0.08, angle=PI / 5,
                          color=C_YELLOW, stroke_width=3)
        self.play(Create(arr), FadeIn(ratio), run_time=0.8)
        self.wait_until(self.cue_start("筛法是", self.now))
        cx1 = VGroup(T("埃氏筛", 26, C_TEAL), tex(r"O(n\log\log n)", 0.85, C_TEAL), T("几乎线性", 26)).arrange(RIGHT, buff=0.3)
        cx1.move_to([0, -1.35, 0])
        self.play(FadeIn(cx1, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("筛完以后", self.cue_at("筛完", self.now)))
        isp = D.sieve(D.SIEVE_N)
        q = 97
        look = VGroup(Text(f"is_prime[{q}]", font=MONO, font_size=26, color=WHITE), tex(r"\to", 0.8),
                      Text(str(isp[q]), font=MONO, font_size=26, color=C_GREEN),
                      T("查表一次", 24, C_GREY)).arrange(RIGHT, buff=0.25).move_to([0, -2.25, 0])
        self.play(FadeIn(look, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        steps = [("看数据范围", r"n\le10^5"), ("定复杂度上限", r"O(n\log n)"), ("再想算法", None)]
        boxes = VGroup()
        for k, (s, ex) in enumerate(steps):
            col = (C_BLUE, C_YELLOW, C_GREEN)[k]
            r = RoundedRectangle(corner_radius=0.18, width=3.4, height=1.7, stroke_color=col, stroke_width=3)
            r.set_fill(col, 0.06)
            t = T(s, 30, col)
            sub = tex(ex, 0.75, WHITE) if ex else T("排序、二分", 24)
            g = VGroup(t, sub).arrange(DOWN, buff=0.25)
            boxes.add(VGroup(r, g.move_to(r)))
        boxes.arrange(RIGHT, buff=0.9).move_to([0, 1.2, 0])
        arrows = VGroup(*[Arrow(boxes[k].get_right(), boxes[k + 1].get_left(), buff=0.1, color=C_GREY, stroke_width=4)
                          for k in range(2)])
        self.play(LaggedStart(FadeIn(boxes[0], shift=RIGHT * 0.2), GrowArrow(arrows[0]),
                              FadeIn(boxes[1], shift=RIGHT * 0.2), GrowArrow(arrows[1]),
                              FadeIn(boxes[2], shift=RIGHT * 0.2), lag_ratio=0.45), run_time=2.4)
        self.wait_until(self.cue_start("复杂度不对", self.now))
        key = T("复杂度不对，优化常数没有用", 32, C_RED).move_to([0, -1.0, 0])
        self.play(Write(key), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 4 周 算法分析入门 2.2、3.1–3.5、4.4 节", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
