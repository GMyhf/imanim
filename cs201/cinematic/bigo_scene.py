"""渐进分析：只看 n 变大以后（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。两份前缀和代码的赋值计数、各项占比、
大 O 的起点 N、Θ 夹逼曲线、滑动窗口计数、顺序检索的平均比较次数、黄页查找次数全部来自 bigodata
（讲义第 1 章第 3 节代码逐条数赋值；test_bigo.py 用闭式公式与 Fraction 精确值对撞）。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bigodata as D  # noqa: E402
from cine import *  # noqa: E402,F403

NAIVE_SRC = ("for (i = 0; i < n; i++) {\n"
             "    for (j = 1, sum = a[0]; j <= i; j++)\n"
             "        sum += a[j];\n"
             "    cout << sum;\n"
             "}")
RUN_SRC = ("for (i = sum = 0; i < n; i++) {\n"
           "    sum += a[i];\n"
           "    cout << sum;\n"
           "}")
WIN_SRC = ("for (i = 4; i < n; i++)\n"
           "    for (j = i - 3, sum = a[i - 4]; j <= i; j++)\n"
           "        sum += a[j];")
A = [3, 1, 4, 1, 5]


def code(src, width, fs=20):
    c = Code(code_string=src, language="cpp", formatter_style="monokai", background="window",
             add_line_numbers=False, paragraph_config={"font": MONO, "font_size": fs})
    c.scale_to_fit_width(width)
    return c


def cells(vals, w=0.62, color=C_BLUE, s=0.62):
    g = VGroup(*[VGroup(Square(w, stroke_color=color, stroke_width=2), MathTex(str(v)).scale(s)) for v in vals])
    g.arrange(RIGHT, buff=0)
    return g


def cn(x):
    """数字加千分位，给画面用。"""
    return f"{x:,}"


class BigOLesson(Lesson):
    def construct(self):
        for b in ("title", "count", "curves", "lower", "bigo", "theta", "nest", "cases", "growth", "tradeoff"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key):
        for c in self.cue_times():
            if key in c["text"]:
                k = c["text"].index(key)
                self.wait_until(c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"])))
                return
        raise KeyError(key)

    def hold(self, tail=0.6):
        self.wait(max(0.1, self.left() - tail))

    def clear(self, *extra, run_time=0.6):
        keep = set(map(id, self.subs))
        ms = [m for m in self.mobjects if id(m) not in keep]
        if ms:
            self.play(*[FadeOut(m) for m in ms], *extra, run_time=run_time)

    # ---------------------------------------------------------------- 片头：两份代码，同一个输出
    def title_beat(self):
        self.beat("title")
        title = T("渐进分析", 60).move_to([0, 0.6, 0])
        sub = T("只看 n 变大以后", 32, C_YELLOW).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(0.8)
        self.play(VGroup(title, sub).animate.scale(0.5).move_to([-5.0, 3.3, 0]), run_time=0.7)
        self.title_grp = VGroup(title, sub)
        arr = cells(A).move_to([-1.2, 2.3, 0])
        alab = MathTex("a", color=C_GREY).scale(0.8).next_to(arr, LEFT, buff=0.25)
        out, _ = D.prefix_running(A)
        outs = cells(out, color=C_GREEN).move_to([-1.2, 1.4, 0])
        olab = T("输出", 22, C_GREY).next_to(outs, LEFT, buff=0.25)
        self.play(FadeIn(arr), FadeIn(alab), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.15) for c in outs], lag_ratio=0.25), FadeIn(olab), run_time=1.4)
        self.at("讲义给的写法")
        left = code(NAIVE_SRC, 6.2).move_to([-3.4, -1.2, 0])
        lcap = T("从头加（讲义）", 24, C_YELLOW).next_to(left, UP, buff=0.15)
        self.play(FadeIn(left, shift=UP * 0.2), FadeIn(lcap), run_time=0.8)
        self.at("另一种写法")
        right = code(RUN_SRC, 5.2).move_to([3.6, -1.2, 0]).align_to(left, UP)
        rcap = T("接着加", 24, C_GREEN).next_to(right, UP, buff=0.15)
        self.play(FadeIn(right, shift=UP * 0.2), FadeIn(rcap), run_time=0.8)
        self.at("哪一个更快")
        q = T("哪一个更快？", 32).move_to([3.9, 1.9, 0])
        self.play(FadeIn(q, scale=1.2), run_time=0.6)
        self.codes = (left, lcap, right, rcap)
        self.hold()
        self.play(FadeOut(VGroup(arr, alab, outs, olab, q)), run_time=0.6)

    # ---------------------------------------------------------------- 不比秒数，数赋值
    def count_beat(self):
        self.beat("count")
        left, lcap, right, rcap = self.codes
        self.play(VGroup(left, lcap).animate.shift(UP * 1.9), VGroup(right, rcap).animate.shift(UP * 1.9), run_time=0.6)
        sec = VGroup(T("秒数", 28, C_GREY), MathTex(r"\times", color=C_RED)).arrange(RIGHT, buff=0.2).move_to([-3.4, -1.25, 0])
        self.play(FadeIn(sec), run_time=0.5)
        self.at("同一个程序")
        why = T("换机器、换语言，能差几十倍", 24, C_GREY).next_to(sec, RIGHT, buff=0.5)
        self.play(FadeIn(why), run_time=0.6)
        self.at("我们数基本操作")
        ops = T("数基本操作：赋值", 28, C_YELLOW).move_to([0, -2.0, 0])
        self.play(FadeOut(VGroup(sec, why)), FadeIn(ops, shift=UP * 0.2), run_time=0.7)
        self.at("从头加的写法")
        n = 1000
        assert D.prefix_naive(list(range(n)))[1] == D.naive_formula(n)
        fl = MathTex("1+3n+n(n-1)", color=C_YELLOW).scale(0.95).next_to(left, DOWN, buff=0.35)
        self.play(FadeOut(ops), Write(fl), run_time=1.0)
        self.at("接着加的写法")
        fr = MathTex("2+2n", color=C_GREEN).scale(0.95).next_to(right, DOWN, buff=0.35)
        fr.match_y(fl)
        self.play(Write(fr), run_time=0.8)
        self.fl, self.fr = fl, fr
        self.hold()

    # ---------------------------------------------------------------- 真实计数曲线
    def curves_beat(self):
        self.beat("curves")
        left, lcap, right, rcap = self.codes
        fl, fr = self.fl, self.fr
        self.play(FadeOut(VGroup(left, lcap, right, rcap, self.title_grp)),
                  fl.animate.scale(0.75).move_to([4.6, 2.9, 0]), fr.animate.scale(0.75).move_to([4.6, 2.3, 0]),
                  run_time=0.7)
        ax = Axes(x_range=[0, 40, 10], y_range=[0, 1800, 600], x_length=6.6, y_length=4.6,
                  axis_config={"color": C_GREY, "include_tip": False, "font_size": 22},
                  x_axis_config={"numbers_to_include": [10, 20, 30, 40]},
                  y_axis_config={"numbers_to_include": [600, 1200, 1800]}).move_to([-2.6, 0.15, 0])
        xl = MathTex("n", color=C_GREY).scale(0.7).next_to(ax.x_axis, RIGHT, buff=0.15)
        ylab = T("赋值次数", 20, C_GREY).next_to(ax.y_axis, UP, buff=0.1)
        self.play(Create(ax), FadeIn(xl), FadeIn(ylab), run_time=0.8)
        ns = list(range(1, 41))
        naive = [D.prefix_naive(list(range(k)))[1] for k in ns]
        run = [D.prefix_running(list(range(k)))[1] for k in ns]
        cn_ = VMobject(color=C_YELLOW, stroke_width=4).set_points_as_corners([ax.c2p(k, v) for k, v in zip(ns, naive)])
        cr = VMobject(color=C_GREEN, stroke_width=4).set_points_as_corners([ax.c2p(k, v) for k, v in zip(ns, run)])
        self.play(Create(cn_), Create(cr), run_time=1.4)
        self.at("n 等于十")
        d1 = Dot(ax.c2p(10, naive[9]), color=C_YELLOW)
        d2 = Dot(ax.c2p(10, run[9]), color=C_GREEN)
        l1 = MathTex(str(naive[9]), color=C_YELLOW).scale(0.6).next_to(d1, UP, buff=0.12)
        l2 = MathTex(str(run[9]), color=C_GREEN).scale(0.6).next_to(d2, RIGHT, buff=0.15).shift(UP * 0.12)
        self.play(FadeIn(d1, scale=1.5), FadeIn(d2, scale=1.5), FadeIn(l1), FadeIn(l2), run_time=0.8)
        self.at("n 等于一千")
        big_n = D.prefix_naive(list(range(1000)))[1]
        big_r = D.prefix_running(list(range(1000)))[1]
        tb = VGroup(MathTex(r"n=1000", color=C_GREY).scale(0.75),
                    MathTex(cn(big_n).replace(",", "{,}"), color=C_YELLOW).scale(0.85),
                    MathTex(cn(big_r).replace(",", "{,}"), color=C_GREEN).scale(0.85)).arrange(DOWN, buff=0.3)
        tb.move_to([4.6, 0.6, 0])
        self.play(FadeIn(tb, shift=LEFT * 0.2), run_time=0.8)
        self.at("差的不是倍数")
        ratio = VGroup(T("比值 =", 26), MathTex(r"\frac{n+1}{2}", color=C_RED).scale(0.9)).arrange(RIGHT, buff=0.2)
        ratio.move_to([4.6, -1.3, 0])
        grows = T("随 n 一起长", 24, C_RED).next_to(ratio, DOWN, buff=0.2)
        assert big_n * 2 == big_r * 1001 and naive[9] * 2 == run[9] * 11
        self.play(FadeIn(ratio), FadeIn(grows), run_time=0.8)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 低阶项被淹没
    def lower_beat(self):
        self.beat("lower")
        f = MathTex("f(n)=", "n^2", "+", "100n", "+", r"\log_{10} n", "+", "1000").scale(0.9).move_to([0, 2.9, 0])
        cols = {"n2": C_BLUE, "100n": C_YELLOW, "log": C_PURPLE, "1000": C_RED}
        f[1].set_color(cols["n2"]); f[3].set_color(cols["100n"]); f[5].set_color(cols["log"]); f[7].set_color(cols["1000"])
        self.at("看这个函数")
        self.play(Write(f), run_time=1.2)
        W, x0 = 9.0, -3.6
        keys = ["n 等于一，", "n 等于十", "n 等于一百", "到了一千"]
        for i, (n, key) in enumerate(zip((1, 10, 100, 1000), keys)):
            self.at(key)
            y = 1.7 - 1.05 * i
            sh = D.f_shares(n)
            lab = MathTex(f"n={n}", color=C_GREY).scale(0.7).move_to([x0 - 1.1, y, 0])
            segs, txts = VGroup(), VGroup()
            x = x0
            for k in ("n2", "100n", "log", "1000"):
                w = W * sh[k]
                if w < 0.004:
                    continue
                r = Rectangle(width=w, height=0.6, stroke_width=0).set_fill(cols[k], 0.55).move_to([x + w / 2, y, 0])
                segs.add(r)
                if sh[k] >= 0.08:
                    txts.add(Text(f"{sh[k] * 100:.0f}%", font=FONT, font_size=22).move_to(r))
                x += w
            self.play(FadeIn(lab), LaggedStart(*[GrowFromEdge(s_, LEFT) for s_ in segs], lag_ratio=0.3),
                      FadeIn(txts), run_time=1.0)
        self.at("n 越大")
        note = T("n 越大，只剩最高次项说了算", 28, C_BLUE).move_to([0.9, -2.55, 0])
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 大 O：从 N 往后压在 c·g 下面
    def bigo_beat(self):
        self.beat("bigo")
        defn = MathTex(r"f(n)\le c\,g(n)", r"\quad \text{for all } n\ge N").scale(0.85).move_to([2.4, 2.95, 0])
        defn[0].set_color(C_YELLOW)
        ax = Axes(x_range=[0, 200, 50], y_range=[0, 80000, 20000], x_length=7.4, y_length=4.4,
                  axis_config={"color": C_GREY, "include_tip": False, "font_size": 20},
                  x_axis_config={"numbers_to_include": [50, 100, 150, 200]}).move_to([-1.9, -0.25, 0])
        xl = MathTex("n", color=C_GREY).scale(0.7).next_to(ax.x_axis, RIGHT, buff=0.15)
        fg = ax.plot(lambda x: D.f_total(max(x, 1)), x_range=[1, 200], color=C_YELLOW, stroke_width=4)
        cg = ax.plot(lambda x: D.BIG_C * x * x, x_range=[0, 200], color=C_BLUE, stroke_width=4)
        fl = MathTex("f(n)", color=C_YELLOW).scale(0.75).next_to(ax.c2p(200, D.f_total(200)), RIGHT, buff=0.1)
        cl = MathTex(rf"{D.BIG_C}n^2", color=C_BLUE).scale(0.75).next_to(ax.c2p(200, D.BIG_C * 200 * 200), RIGHT, buff=0.1)
        cl.shift(DOWN * 0.15)
        self.play(Write(defn), Create(ax), FadeIn(xl), run_time=1.0)
        self.play(Create(fg), Create(cg), FadeIn(fl), FadeIn(cl), run_time=1.3)
        N = D.bigo_first_N()
        self.at("从 N 往后")
        vl = DashedLine(ax.c2p(N, 0), ax.c2p(N, 80000), color=C_GREEN)
        nl = MathTex(f"N={N}", color=C_GREEN).scale(0.7).next_to(vl, UP, buff=0.08)
        band = ax.get_area(cg, x_range=[N, 200], bounded_graph=fg, color=C_GREEN, opacity=0.18)
        isO = MathTex(r"\Rightarrow\ f(n)\in O(n^2)", color=C_YELLOW).scale(0.8).move_to([4.75, 0.5, 0])
        self.play(Create(vl), FadeIn(nl), FadeIn(band), FadeIn(isO), run_time=0.9)
        self.at("前面一小段")
        early = ax.get_area(fg, x_range=[1, N], bounded_graph=cg, color=C_RED, opacity=0.18)
        dont = T("这一段不管", 22, C_RED).move_to(ax.c2p(55, 30000))
        self.play(FadeIn(early), FadeIn(dont), run_time=0.8)
        self.at("把不等号反过来")
        assert D.omega_holds()
        lg = ax.plot(lambda x: x * x, x_range=[0, 200], color=C_PURPLE, stroke_width=3)
        ll = MathTex("n^2", color=C_PURPLE).scale(0.7).next_to(ax.c2p(200, 40000), RIGHT, buff=0.1)
        om = MathTex(r"f(n)\ge 1\cdot n^2\ \Rightarrow\ f\in\Omega(n^2)", color=C_PURPLE).scale(0.75).move_to([4.75, -1.3, 0])
        self.play(Create(lg), FadeIn(ll), FadeIn(om), run_time=1.0)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- Θ：夹在两条线之间
    def theta_beat(self):
        self.beat("theta")
        th = MathTex(r"O(g)\ \cap\ \Omega(g)\ =\ \Theta(g)", color=C_BLUE).scale(0.85).move_to([0, 3.0, 0])
        self.play(Write(th), run_time=0.9)
        self.at("讲义的例子")
        ex = MathTex(r"f(n)=100n^2+5n+500", color=C_YELLOW).scale(0.8).move_to([-2.9, 2.35, 0])
        self.play(FadeIn(ex, shift=UP * 0.15), run_time=0.6)
        N = D.theta_first_N()
        self.at("n 大于十以后")
        sand = MathTex(rf"{D.C1}n^2\le f(n)\le {D.C2}n^2\quad (n>{N})", color=WHITE).scale(0.8).move_to([3.0, 2.35, 0])
        self.play(FadeIn(sand, shift=UP * 0.15), run_time=0.7)
        self.at("把它除以")
        ax = Axes(x_range=[0, 40, 10], y_range=[95, 125, 5], x_length=8.4, y_length=3.8,
                  axis_config={"color": C_GREY, "include_tip": False, "font_size": 20},
                  x_axis_config={"numbers_to_include": [10, 20, 30, 40]},
                  y_axis_config={"numbers_to_include": [100, 105, 110, 120]}).move_to([-0.3, -0.7, 0])
        yl = MathTex(r"f(n)/n^2", color=C_GREY).scale(0.65).next_to(ax.y_axis, UP, buff=0.1)
        lo = DashedLine(ax.c2p(0, D.C1), ax.c2p(40, D.C1), color=C_GREEN)
        hi = DashedLine(ax.c2p(0, D.C2), ax.c2p(40, D.C2), color=C_GREEN)
        band = Polygon(ax.c2p(0, D.C1), ax.c2p(40, D.C1), ax.c2p(40, D.C2), ax.c2p(0, D.C2),
                       stroke_width=0).set_fill(C_GREEN, 0.15)
        pts = [(n, D.theta_f(n) / n / n) for n in range(5, 41)]
        curve = VMobject(color=C_YELLOW, stroke_width=4).set_points_smoothly([ax.c2p(n, r) for n, r in pts])
        vN = DashedLine(ax.c2p(N, 95), ax.c2p(N, 125), color=C_RED)
        nl = MathTex(f"N={N}", color=C_RED).scale(0.65).next_to(ax.c2p(N, 125), RIGHT, buff=0.1)
        self.play(Create(ax), FadeIn(yl), FadeIn(band), Create(lo), Create(hi), run_time=0.8)
        self.play(Create(curve), Create(vN), FadeIn(nl), run_time=1.6)
        self.at("所以它是")
        res = MathTex(r"f(n)\in\Theta(n^2)", color=C_BLUE).scale(0.9).move_to(ax.c2p(31, 115))
        self.play(FadeIn(res, scale=1.2), run_time=0.7)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 嵌套但线性
    def nest_beat(self):
        self.beat("nest")
        q = T("嵌套循环 = 平方？", 32).move_to([0, 3.0, 0])
        self.play(FadeIn(q), run_time=0.6)
        self.at("讲义第三段代码")
        c = code(WIN_SRC, 7.2).move_to([0, 1.65, 0])
        n = 10
        a = list(range(n))
        sums, total, inner = D.window5(a)
        arr = cells(a, w=0.62, color=C_GREY).move_to([-1.2, -0.35, 0])
        self.play(FadeOut(q), FadeIn(c, shift=UP * 0.2), FadeIn(arr), run_time=0.8)
        win = SurroundingRectangle(VGroup(*arr[0:5]), color=C_YELLOW, buff=0.04, stroke_width=4)
        four = T("内层永远 4 次", 24, C_YELLOW).move_to([4.7, -0.35, 0])
        self.play(Create(win), FadeIn(four), run_time=0.6)
        outs = VGroup()
        step = min(0.55, max(0.3, (self.left() - 7.5) / len(sums)))
        for i, sm in enumerate(sums):
            t = MathTex(str(sm), color=C_GREEN).scale(0.6).next_to(arr[i + 4], DOWN, buff=0.2)
            outs.add(t)
            self.play(win.animate.move_to(VGroup(*arr[i:i + 5])), FadeIn(t), run_time=step)
        self.at("n 等于十")
        cnt = VGroup(MathTex(r"n=10:\ ", r"1+11\times6", "=", str(total)).scale(0.8))
        cnt.move_to([0, -1.75, 0])
        cnt[0][3].set_color(C_YELLOW)
        assert total == 1 + 11 * (n - 4)
        self.play(Write(cnt), run_time=1.0)
        self.at("每多一个数")
        lin = VGroup(MathTex(r"1+11(n-4)", color=C_YELLOW).scale(0.8), T("线性", 28, C_GREEN)).arrange(RIGHT, buff=0.4)
        lin.move_to([0, -2.5, 0])
        self.play(FadeIn(lin, shift=UP * 0.15), run_time=0.7)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 最好、最坏、平均
    def cases_beat(self):
        self.beat("cases")
        n = 8
        cap = T("顺序检索：从第一个开始逐个比较", 28).move_to([0, 3.0, 0])
        self.play(FadeIn(cap), run_time=0.6)
        bx0, bw = -4.2, 0.9
        ax = Axes(x_range=[0, n, 1], y_range=[0, n, 2], x_length=bw * n, y_length=3.2,
                  axis_config={"color": C_GREY, "include_tip": False, "font_size": 20},
                  y_axis_config={"numbers_to_include": [2, 4, 6, 8]}).move_to([-0.6, 0.15, 0])
        ylab = T("比较次数", 20, C_GREY).next_to(ax.y_axis, UP, buff=0.1)
        xlab = T("K 所在位置", 20, C_GREY).next_to(ax.x_axis, DOWN, buff=0.45)
        a = list(range(n))
        cmps = [D.seq_search(a, k)[1] for k in a]
        bars = VGroup(*[Rectangle(width=bw * 0.7, height=ax.y_length * c / n, stroke_width=0)
                        .set_fill(C_BLUE, 0.6).move_to(ax.c2p(i + 0.5, 0), aligned_edge=DOWN) for i, c in enumerate(cmps)])
        pos = VGroup(*[MathTex(str(i + 1), color=C_GREY).scale(0.55).next_to(ax.c2p(i + 0.5, 0), DOWN, buff=0.12)
                       for i in range(n)])
        self.at("顺序找一个数")
        self.play(Create(ax), FadeIn(ylab), FadeIn(xlab), FadeIn(pos), run_time=0.7)
        self.at("比一次就够")
        self.play(GrowFromEdge(bars[0], DOWN), bars[0].animate.set_fill(C_GREEN, 0.8), run_time=0.6)
        best = T("最好 1", 22, C_GREEN).next_to(bars[0], UP, buff=0.55).shift(RIGHT * 0.3)
        self.play(FadeIn(best), run_time=0.3)
        self.at("排在最后")
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars[1:]], lag_ratio=0.15), run_time=1.0)
        worst = T(f"最坏 n = {n}", 22, C_RED).next_to(bars[-1], UP, buff=0.1)
        self.play(bars[-1].animate.set_fill(C_RED, 0.8), FadeIn(worst), run_time=0.5)
        self.at("每个位置机会均等")
        avg = D.avg_uniform(n)
        assert avg * 2 == n + 1
        al = DashedLine(ax.c2p(0, float(avg)), ax.c2p(n, float(avg)), color=C_YELLOW)
        at_ = MathTex(r"\frac{n+1}{2}=" + f"{float(avg):g}", color=C_YELLOW).scale(0.7).next_to(al, RIGHT, buff=0.15)
        self.play(Create(al), FadeIn(at_), run_time=0.8)
        self.at("要是它一半机会")
        probs = D.skew_probs(n)
        plabs = VGroup(*[MathTex(rf"\tfrac{{{p.numerator}}}{{{p.denominator}}}", color=C_PURPLE).scale(0.55)
                         .next_to(pos[i], DOWN, buff=0.12) for i, p in enumerate(probs)])
        self.play(FadeIn(plabs), FadeOut(xlab), FadeOut(best),
                  *[b.animate.set_fill(C_PURPLE, 0.2 + 1.2 * float(p)) for b, p in zip(bars, probs)], run_time=0.9)
        sk = D.avg_skew(n)
        sl = DashedLine(ax.c2p(0, float(sk)), ax.c2p(n, float(sk)), color=C_PURPLE)
        st = MathTex(r"1+\frac{n+3}{8}=" + f"{float(sk):g}", color=C_PURPLE).scale(0.7).next_to(sl, RIGHT, buff=0.15)
        self.play(Create(sl), FadeIn(st), run_time=0.8)
        self.at("一千个数时")
        u, s_ = D.avg_uniform(1000), D.avg_skew(1000)
        big = VGroup(MathTex(r"n=1000:", color=C_GREY), MathTex(f"{float(u):g}", color=C_YELLOW),
                     MathTex(r"\to"), MathTex(f"{float(s_):g}", color=C_PURPLE),
                     MathTex(rf"\ (\times{float(u / s_):.2f})", color=C_GREEN)).arrange(RIGHT, buff=0.15).scale(0.75)
        big.move_to([0.2, -2.65, 0])
        self.play(FadeIn(big, shift=UP * 0.15), run_time=0.5)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 增长率：n = 1000
    def growth_beat(self):
        self.beat("growth")
        cap = VGroup(T("每步 1 微秒，", 28), MathTex("n=1000", color=C_YELLOW).scale(0.9)).arrange(RIGHT, buff=0.2)
        cap.move_to([0, 3.0, 0])
        self.play(FadeIn(cap), run_time=0.6)
        sec, years = D.time_at(1000)
        rows = [(r"n", "1 毫秒", sec["n"]), (r"n^2", "1 秒", sec["n2"]),
                (r"n^3", f"{sec['n3']:.0f} 秒 ≈ {sec['n3'] / 60:.1f} 分钟", sec["n3"])]
        exp10 = math.floor(math.log10(years))
        mant = years / 10 ** exp10
        x0, unit = -3.2, 0.62          # 横轴按 log10(秒)，每 10 倍 0.62
        lo = -3.5
        keys = ["线性是", "平方是", "立方是", "指数级"]
        cols = [C_GREEN, C_BLUE, C_YELLOW, C_RED]
        for i, (sym, txt, s) in enumerate(rows):
            self.at(keys[i])
            y = 1.9 - 1.0 * i
            lab = MathTex(sym, color=cols[i]).scale(0.85).move_to([-5.4, y, 0])
            w = (math.log10(s) - lo) * unit
            bar = Rectangle(width=w, height=0.5, stroke_width=0).set_fill(cols[i], 0.6).move_to([x0 + w / 2, y, 0])
            t = T(txt, 24).next_to(bar, RIGHT, buff=0.2)
            self.play(FadeIn(lab), GrowFromEdge(bar, LEFT), FadeIn(t), run_time=0.7)
        self.at("指数级")
        y = 1.9 - 3.0
        lab = MathTex("2^n", color=C_RED).scale(0.85).move_to([-5.4, y, 0])
        bar = Rectangle(width=11.0, height=0.5, stroke_width=0).set_fill(C_RED, 0.6).move_to([x0 + 5.5, y, 0])
        t = VGroup(T("约", 24), MathTex(rf"{mant:.1f}\times10^{{{exp10}}}", color=C_RED).scale(0.8), T("年", 24))
        t.arrange(RIGHT, buff=0.12).move_to([1.6, y - 0.75, 0])
        self.play(FadeIn(lab), GrowFromEdge(bar, LEFT), run_time=1.2)
        self.play(FadeIn(t, shift=UP * 0.15), run_time=0.6)
        scale_note = T("条长按对数刻度画（每长一截是 10 倍），不按比例", 20, C_GREY).move_to([3.0, -2.55, 0])
        self.play(FadeIn(scale_note), run_time=0.4)
        self.hold()
        self.clear()

    # ---------------------------------------------------------------- 时空折衷：黄页 + 散列索引
    def tradeoff_beat(self):
        self.beat("tradeoff")
        cap = T("空间换时间", 34, C_YELLOW).move_to([0, 3.0, 0])
        self.play(FadeIn(cap), run_time=0.6)
        n = 1000
        scan, per, slots = D.phonebook(n)
        self.at("在一千家公司")
        book = VGroup(*[VGroup(Rectangle(width=3.2, height=0.42, stroke_color=C_GREY, stroke_width=1.5),
                               T(f"公司{i:04d}　电话", 20, C_GREY)) for i in range(6)])
        book.arrange(DOWN, buff=0).move_to([-3.9, 0.6, 0])
        dots = MathTex(r"\vdots", color=C_GREY).next_to(book, DOWN, buff=0.1)
        bcap = T(f"黄页：{n} 家公司", 24).next_to(book, UP, buff=0.2)
        self.play(FadeIn(book), FadeIn(dots), FadeIn(bcap), run_time=0.7)
        ptr = Arrow(LEFT * 0.6, ORIGIN, buff=0, color=C_YELLOW, stroke_width=5).next_to(book[0], LEFT, buff=0.08)
        self.play(FadeIn(ptr), run_time=0.3)
        for i in range(1, 6):
            self.play(ptr.animate.next_to(book[i], LEFT, buff=0.08), run_time=0.22)
        sc = VGroup(T("逐个比名字：平均", 24), MathTex(f"{float(scan):g}", color=C_RED).scale(0.85), T("次", 24))
        sc.arrange(RIGHT, buff=0.12).move_to([-3.9, -2.1, 0])
        self.play(FadeIn(sc), run_time=0.6)
        self.at("加一张散列索引")
        hcap = T("散列索引", 24, C_GREEN).move_to([3.4, 1.85, 0])
        h = MathTex(r"h(\text{name})", color=C_GREEN).scale(0.8).move_to([1.0, 0.6, 0])
        table = VGroup(*[Square(0.42, stroke_color=C_GREEN, stroke_width=1.5) for _ in range(8)]).arrange(RIGHT, buff=0)
        table.move_to([4.4, 0.6, 0])
        arr = Arrow(h.get_right(), table[5].get_left() + LEFT * 0.02, buff=0.1, color=C_GREEN, stroke_width=3,
                    max_tip_length_to_length_ratio=0.15)
        arr.put_start_and_end_on(h.get_right() + RIGHT * 0.1, table.get_left() + LEFT * 0.05)
        hit = table[5].copy().set_fill(C_GREEN, 0.6)
        self.play(FadeIn(hcap), Write(h), FadeIn(table), run_time=0.8)
        self.play(GrowArrow(arr), FadeIn(hit), run_time=0.6)
        sp = VGroup(T("多占", 24), MathTex(str(slots), color=C_YELLOW).scale(0.85), T("个格子", 24)).arrange(RIGHT, buff=0.12)
        sp.move_to([3.4, -0.5, 0])
        tm = VGroup(T("每次只算", 24), MathTex(str(per), color=C_GREEN).scale(0.85), T("次散列", 24)).arrange(RIGHT, buff=0.12)
        tm.move_to([3.4, -1.2, 0])
        self.play(FadeIn(sp), FadeIn(tm), run_time=0.7)
        self.at("反过来")
        rev = T("反过来：多花时间，省空间", 24, C_GREY).move_to([3.4, -2.1, 0])
        self.play(FadeIn(rev), run_time=0.6)
        self.at("没有免费的加速")
        free = T("没有免费的加速", 34, C_YELLOW)
        self.play(Transform(cap, free.move_to(cap)), run_time=0.8)
        self.hold(0.3)
