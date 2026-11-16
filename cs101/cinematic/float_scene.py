"""浮点数：0.1 + 0.2 为什么不等于 0.3（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。位串、二进制展开、相邻浮点数的间距、舍入结果全部来自 floatdata
（test_float.py 用独立的按定义编码器与有理数精确运算对撞，并检查旁白数字）。
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import floatdata as S  # noqa: E402
from cine import *  # noqa: E402,F403

C_SIGN, C_EXP, C_MANT = C_RED, C_YELLOW, C_BLUE


def M(s, size=26, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def fr_str(f: Fraction) -> str:
    """乘二表里的小数：0.2、1.6 这种一位小数。"""
    return f"{float(f):.1f}"


class FloatLesson(Lesson):
    def construct(self):
        for b in ("title", "sci", "layout", "tenth", "sum", "gap", "compare", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key):
        """等到旁白读到 key：在所在字幕句里按字数比例估计时刻（一句里常有好几个要对的点）。"""
        for c in self.cue_times():
            i = c["text"].find(key)
            if i >= 0:
                self.wait_until(c["start"] + (c["end"] - c["start"]) * i / max(1, len(c["text"])))
                return

    def close(self, *mobs, tail=0.6):
        self.wait(max(0.1, self.left() - tail))
        self.play(FadeOut(VGroup(*mobs)), run_time=0.6)

    # ---------------------------------------------------------------- 片头：解释器里的一行
    def title_beat(self):
        self.beat("title")
        p1 = M(">>> 0.1 + 0.2", 34, C_GREY)
        r1 = M(S.SUM_REPR, 40)
        p2 = M(">>> 0.1 + 0.2 == 0.3", 34, C_GREY)
        r2 = M(str(S.SUM_EQ), 40, C_RED)
        term = VGroup(p1, r1, p2, r2).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([0, 0.6, 0])
        self.play(FadeIn(p1, shift=UP * 0.2), run_time=0.6)
        self.at("打印出来")
        self.play(AddTextLetterByLetter(r1), run_time=1.4)
        tail = SurroundingRectangle(r1[-1], color=C_RED, buff=0.06)
        self.play(Create(tail), run_time=0.5)
        self.at("相等吗")
        self.play(FadeIn(p2, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(r2, scale=1.3), run_time=0.5)
        self.at("问题出在")
        title = T("浮点数", 72).move_to([0, 3.0, 0])
        sub = MathTex(r"0.1+0.2\neq 0.3", color=C_YELLOW).scale(1.0).move_to([0, -2.2, 0])
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.close(term, tail, title, sub)

    # ---------------------------------------------------------------- 科学计数法与规范化
    def sci_beat(self):
        self.beat("sci")
        fixed = VGroup(T("定点：小数点钉死", 26, C_GREY),
                       MathTex(r"1.00234\ \to\ 1.00", color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.5)
        fixed.move_to([0, 2.9, 0])
        self.play(FadeIn(fixed, shift=DOWN * 0.2), run_time=0.8)
        self.at("科学计数法")
        sci = VGroup(T("浮点：科学计数法", 26, C_GREY),
                     MathTex(r"7\,425\,000\cdots000 = 7.425\times10^{21}", color=C_TEAL).scale(0.8)).arrange(RIGHT, buff=0.5)
        sci.move_to([0, 2.0, 0])
        self.play(FadeIn(sci, shift=DOWN * 0.2), run_time=0.8)
        self.at("二进制也一样")
        digits = S.NORM_BITS.replace(".", "")
        step = 0.62
        x0 = -step * (len(digits) - 1) / 2 - 1.0
        cells = VGroup(*[M(d, 44).move_to([x0 + step * i, 0.2, 0]) for i, d in enumerate(digits)])
        dot_at = S.NORM_BITS.index(".")                     # 点在第 dot_at 个数字之前
        dot = Dot(radius=0.08, color=C_YELLOW).move_to([x0 + step * (dot_at - 0.5), -0.05, 0])
        sub2 = MathTex("_2", color=C_GREY).scale(1.0).next_to(cells, RIGHT, buff=0.1).shift(DOWN * 0.15)
        self.play(FadeIn(cells), FadeIn(dot), FadeIn(sub2), run_time=0.8)
        shift = VGroup(T("左移", 24, C_GREY), Integer(0, color=C_YELLOW).scale(0.8), T("位", 24, C_GREY))
        shift.arrange(RIGHT, buff=0.12).move_to([1.6, -1.0, 0])
        self.play(FadeIn(shift), run_time=0.3)
        for k in range(1, S.NORM_SHIFT + 1):
            self.play(dot.animate.move_to([x0 + step * (dot_at - k - 0.5), -0.05, 0]),
                      shift[1].animate.set_value(k), run_time=0.32)
        pw = MathTex(r"\times 2^{%d}" % S.NORM_SHIFT, color=C_YELLOW).scale(1.1).next_to(sub2, RIGHT, buff=0.25)
        pw.align_to(cells, DOWN)
        self.play(FadeIn(pw, shift=LEFT * 0.2), run_time=0.6)
        self.at("规范化")
        lead = SurroundingRectangle(cells[0], color=C_RED, buff=0.1)
        note = T("打头总是 1：隐含，不存", 26, C_RED).next_to(lead, DOWN, buff=0.75).align_to(lead, LEFT)
        mant = SurroundingRectangle(cells[1:], color=C_BLUE, buff=0.1)
        mlab = T("尾数", 26, C_BLUE).next_to(mant, UP, buff=0.12)
        self.play(Create(lead), FadeIn(note), run_time=0.7)
        self.play(cells[0].animate.set_opacity(0.3), Create(mant), FadeIn(mlab), run_time=0.8)
        self.close(fixed, sci, cells, dot, sub2, shift, pw, lead, note, mant, mlab)

    # ---------------------------------------------------------------- 64 位的布局：-6.5
    def layout_beat(self):
        self.beat("layout")
        w = 0.205
        x0 = -w * 63 / 2
        cols = [C_SIGN] + [C_EXP] * 11 + [C_MANT] * 52
        cells = VGroup(*[Square(w * 0.92, stroke_color=c, stroke_width=1.5).set_fill(c, 0.18)
                         .move_to([x0 + w * i, 1.7, 0]) for i, c in enumerate(cols)])
        head = T("双精度：64 位", 30).move_to([0, 3.3, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.01), run_time=1.2)
        groups = [(0, 1, "符号 1", C_SIGN), (1, 12, "指数 11", C_EXP), (12, 64, "尾数 52", C_MANT)]
        labs = VGroup()
        for a, b, s, c in groups:
            br = Line(cells[a].get_corner(UL) + UP * 0.12, cells[b - 1].get_corner(UR) + UP * 0.12, color=c, stroke_width=3)
            lb = T(s, 22, c).next_to(br, UP, buff=0.08)
            labs.add(VGroup(br, lb))
        labs[0][1].next_to(cells[0], DOWN, buff=0.12).align_to(cells[0], LEFT)
        self.play(LaggedStart(*[FadeIn(g) for g in labs], lag_ratio=0.4), run_time=1.6)
        formula = VGroup(MathTex(r"(-1)^{S}\times 1.M\times 2^{\,E-1023}").scale(0.8),
                         T("S 符号 · E 指数 · M 尾数", 20, C_GREY)).arrange(RIGHT, buff=0.5).move_to([0, -2.4, 0])
        self.play(FadeIn(formula, shift=UP * 0.2), run_time=0.7)
        self.at("拿负六点五")
        sgn, E, e, mbits, _ = S.decode(S.EX)
        ex = MathTex(r"-6.5 = -" + S.EX_BIN + r"_2 = -1.101_2\times 2^{%d}" % e).scale(0.9).move_to([0, 0.5, 0])
        self.play(Write(ex), run_time=1.4)
        bits = "".join(S.float_bits(S.EX))

        def fill(lo, hi, run_time=0.8):
            ds = VGroup(*[M(bits[i], 13, cols[i]).move_to(cells[i]) for i in range(lo, hi)])
            self.play(LaggedStart(*[FadeIn(d) for d in ds], lag_ratio=0.02), run_time=run_time)
            return ds
        self.at("符号位是一")
        d0 = fill(0, 1, 0.4)
        n_sign = T(f"负数 → S = {sgn}", 22, C_SIGN).move_to([-4.4, -0.6, 0])
        self.play(FadeIn(n_sign), run_time=0.4)
        self.at("指数二")
        n_exp = MathTex(r"%d + 1023 = %d = %s_2" % (e, E, format(E, "011b")), color=C_EXP).scale(0.7).move_to([0.6, -0.6, 0])
        self.play(FadeIn(n_exp, shift=UP * 0.2), run_time=0.6)
        d1 = fill(1, 12)
        self.at("尾数只存")
        n_mant = T("尾数：101，后面补 0", 22, C_MANT).move_to([0, -1.4, 0])
        self.play(FadeIn(n_mant), run_time=0.4)
        d2 = fill(12, 64, 1.2)
        self.close(head, cells, labs, formula, ex, d0, d1, d2, n_sign, n_exp, n_mant)

    # ---------------------------------------------------------------- 0.1 的二进制：乘二取整
    def tenth_beat(self):
        self.beat("tenth")
        head = T("0.1 的二进制：乘 2，取整数部分", 28).move_to([0, 3.3, 0])
        self.play(FadeIn(head), run_time=0.6)
        steps = S.doubling_steps(n=6)
        rows = VGroup()
        prev = Fraction(1, 10)
        for y, d, rest in steps:
            row = VGroup(MathTex(fr_str(prev) + r"\times 2 =", color=C_GREY).scale(0.7),
                         MathTex(fr_str(y)).scale(0.7),
                         MathTex(r"\to", color=C_GREY).scale(0.7),
                         MathTex(str(d), color=C_YELLOW if d else WHITE).scale(0.8))
            row.arrange(RIGHT, buff=0.25)
            rows.add(row)
            prev = rest
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.22).move_to([-3.6, 0.3, 0])
        exp = VGroup(MathTex("0.", color=WHITE).scale(0.9))
        digit_mobs = VGroup()
        self.at("不断乘二")
        exp.move_to([1.0, 1.6, 0])
        self.play(FadeIn(exp), run_time=0.3)
        keys = {0: "零点二，零点四", 3: "一点六", 4: "一点二"}
        for i, (row, (y, d, rest)) in enumerate(zip(rows, steps)):
            if i in keys:
                self.at(keys[i])
            dm = MathTex(str(d), color=C_YELLOW if d else WHITE).scale(0.9)
            dm.next_to(exp if not digit_mobs else digit_mobs[-1], RIGHT, buff=0.08)
            dm.align_to(exp, DOWN)
            digit_mobs.add(dm)
            self.play(FadeIn(row, shift=RIGHT * 0.2), TransformFromCopy(row[3], dm), run_time=0.55)
        self.at("又回到")
        c0, cs = S.cycle_start()
        loop = CurvedArrow(rows[-1].get_right() + RIGHT * 0.15, rows[c0].get_right() + RIGHT * 0.15,
                           angle=TAU / 4, color=C_RED)
        loop_lab = T("又回到 0.2", 22, C_RED).next_to(loop, RIGHT, buff=0.1)
        self.play(Create(loop), FadeIn(loop_lab), run_time=0.8)
        more = VGroup(*[MathTex(ch, color=C_YELLOW if ch == "1" else WHITE).scale(0.9)
                        for ch in S.binary_expansion(n=12)[len(steps):]],
                      MathTex(r"\cdots", color=C_GREY).scale(0.9))
        more.arrange(RIGHT, buff=0.08).next_to(digit_mobs[-1], RIGHT, buff=0.08).align_to(exp, DOWN)
        cyc = SurroundingRectangle(VGroup(*digit_mobs[c0:c0 + cs]), color=C_RED, buff=0.06)
        self.play(FadeIn(more), Create(cyc), run_time=0.8)
        self.at("就像十进制")
        cmp_ = VGroup(MathTex(r"\tfrac13 = 0.333\cdots_{10}", color=C_GREY).scale(0.75),
                      MathTex(r"\tfrac1{10} = 0.0\overline{0011}\cdots_{2}", color=C_TEAL).scale(0.75),
                      MathTex(r"10 = 2\times 5", color=C_GREY).scale(0.75)).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        cmp_.move_to([3.2, 0.1, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.15) for m in cmp_], lag_ratio=0.4), run_time=1.4)
        self.at("尾数只有")
        stored = M(S.TENTH_20, 30).move_to([1.6, -1.65, 0])
        cap = T("存进去的值", 22, C_GREY).next_to(stored, LEFT, buff=0.3)
        hl = SurroundingRectangle(stored[-3:], color=C_RED, buff=0.05)
        err = S.stored_error("0.1")
        mant, ex10 = f"{float(err):.2e}".split("e")
        errt = MathTex(r"\approx 0.1 + %s\times10^{%d}" % (mant, int(ex10)), color=C_RED).scale(0.7)
        errt.next_to(stored, DOWN, buff=0.22).align_to(stored, RIGHT)
        self.play(FadeIn(cap), FadeIn(stored, shift=UP * 0.2), run_time=0.7)
        self.play(Create(hl), FadeIn(errt), run_time=0.7)
        self.close(head, rows, exp, digit_mobs, loop, loop_lab, more, cyc, cmp_, stored, cap, hl, errt)

    # ---------------------------------------------------------------- 0.1 + 0.2 落在哪一格
    def sum_beat(self):
        self.beat("sum")
        X0, X1, Y = -5.5, 5.5, 2.4
        coarse = NumberLine(x_range=[0, 0.4, 0.1], length=X1 - X0, color=C_GREY, include_numbers=False).move_to([0, Y, 0])
        nums = VGroup(*[MathTex(f"{v:.1f}", color=C_GREY).scale(0.55).next_to(coarse.n2p(v), DOWN, buff=0.15)
                        for v in (0.0, 0.1, 0.2, 0.3, 0.4)])
        self.play(Create(coarse), FadeIn(nums), run_time=0.8)
        bigger = VGroup(*[T("存大了一点", 18, C_RED).next_to(coarse.n2p(v), UP, buff=0.15) for v in (0.1, 0.2)])
        self.play(FadeIn(bigger[0]), run_time=0.4)
        self.play(FadeIn(bigger[1]), run_time=0.4)
        self.at("两个近似值相加")
        plus = VGroup(MathTex(r"0.1 + 0.2 \Rightarrow", color=C_PURPLE).scale(0.7), T("再舍入", 20, C_PURPLE))
        plus.arrange(RIGHT, buff=0.15).next_to(coarse.n2p(0.3), UP, buff=0.15)
        self.play(FadeIn(plus, shift=DOWN * 0.15), run_time=0.6)
        self.at("把零点三附近放大")
        ulp = Fraction(S.ULP_03)
        unit = 3.0
        FY = -0.6

        def fx(v):
            return float((Fraction(v) - Fraction(3, 10)) / ulp) * unit + 0.0
        lo_f, up_f = Fraction(S.LOWER), Fraction(S.UPPER)
        grid = [lo_f - ulp, lo_f, up_f, up_f + ulp]
        fine = Line([-6.4, FY, 0], [6.4, FY, 0], color=C_GREY, stroke_width=2)
        ticks = VGroup(*[Line([fx(g), FY - 0.18, 0], [fx(g), FY + 0.18, 0], color=C_BLUE, stroke_width=4) for g in grid])
        lens = Rectangle(width=0.22, height=0.5, color=C_YELLOW, stroke_width=2).move_to(coarse.n2p(0.3))
        rays = VGroup(DashedLine(lens.get_corner(DL), [-6.4, FY + 0.3, 0], color=C_YELLOW, stroke_width=1.5),
                      DashedLine(lens.get_corner(DR), [6.4, FY + 0.3, 0], color=C_YELLOW, stroke_width=1.5))
        self.play(FadeOut(plus), Create(lens), run_time=0.4)
        self.play(Create(rays), Create(fine), run_time=0.8)
        self.play(LaggedStart(*[Create(t) for t in ticks], lag_ratio=0.2), run_time=0.8)
        gap_br = BraceBetweenPoints([fx(grid[2]), FY - 0.25, 0], [fx(grid[3]), FY - 0.25, 0], DOWN, color=C_BLUE)
        gap_lab = MathTex(r"2^{-54}\approx %.2f\times10^{-17}" % (S.ULP_03 * 1e17), color=C_BLUE).scale(0.6)
        gap_lab.next_to(gap_br, DOWN, buff=0.1)
        self.play(GrowFromCenter(gap_br), FadeIn(gap_lab), run_time=0.7)
        self.at("零点三本身")
        true03 = Line([fx(Fraction(3, 10)), FY - 0.35, 0], [fx(Fraction(3, 10)), FY + 0.35, 0], color=WHITE, stroke_width=2)
        true_lab = MathTex("0.3", color=WHITE).scale(0.6).next_to(true03, UP, buff=0.1)
        low_dot = Dot([fx(lo_f), FY, 0], radius=0.11, color=C_YELLOW)
        low_lab = T("0.3 存在这一格", 20, C_YELLOW).next_to(low_dot, DOWN, buff=0.35).align_to(low_dot, RIGHT).shift(RIGHT * 0.2)
        self.play(Create(true03), FadeIn(true_lab), run_time=0.5)
        self.play(GrowFromCenter(low_dot), FadeIn(low_lab), run_time=0.6)
        self.at("精确和")
        mid = S.EXACT_SUM
        mid_mark = Triangle(color=C_PURPLE).set_fill(C_PURPLE, 1).scale(0.13).rotate(PI).move_to([fx(mid), FY + 0.95, 0])
        mid_lab = T("精确和：正中间", 20, C_PURPLE).next_to(mid_mark, UP, buff=0.1)
        self.play(FadeIn(mid_mark, shift=DOWN * 0.2), FadeIn(mid_lab), run_time=0.6)
        self.at("就近取偶")
        up_dot = Dot([fx(up_f), FY, 0], radius=0.11, color=C_RED)
        arc = CurvedArrow(mid_mark.get_bottom() + DOWN * 0.05, up_dot.get_top() + UP * 0.05, angle=-TAU / 6, color=C_RED)
        up_lab = MathTex(r"0.1+0.2", color=C_RED).scale(0.6).next_to(up_dot, UP, buff=0.35).shift(RIGHT * 0.6)
        even = T("尾数末位为 0", 18, C_RED).next_to(up_lab, RIGHT, buff=0.2)
        self.play(Create(arc), GrowFromCenter(up_dot), run_time=0.7)
        self.play(FadeIn(up_lab), FadeIn(even), run_time=0.5)
        self.at("两个不同")
        neq = MathTex(r"\neq", color=C_RED).scale(1.4).move_to([(fx(lo_f) + fx(up_f)) / 2, FY - 1.55, 0])
        self.play(FadeIn(neq, scale=1.5), Indicate(low_dot, color=C_YELLOW), Indicate(up_dot, color=C_RED), run_time=0.8)
        self.close(coarse, nums, bigger, lens, rays, fine, ticks, gap_br, gap_lab, true03, true_lab, low_dot, low_lab,
                   mid_mark, mid_lab, up_dot, arc, up_lab, even, neq)

    # ---------------------------------------------------------------- 格子变宽：2^53 与大整数开方
    def gap_beat(self):
        self.beat("gap")
        head = VGroup(MathTex(r"53 = 52 + 1", color=C_YELLOW).scale(0.9), T("（隐含的 1）", 24, C_YELLOW))
        head.arrange(RIGHT, buff=0.2).move_to([0, 3.2, 0])
        self.at("五十三位")
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.7)
        self.at("到了二的五十三次方")
        lo, hi = -3, 4
        step = 1.45
        Y = 1.4
        line = Line([lo * step - 0.6, Y, 0], [hi * step + 0.6, Y, 0], color=C_GREY, stroke_width=2)
        marks, labs = VGroup(), VGroup()
        for k in range(lo, hi + 1):
            n = S.P53 + k
            ok = float(n) == n
            p = [k * step, Y, 0]
            marks.add(Dot(p, radius=0.1, color=C_BLUE) if ok else Circle(0.1, color=C_RED, stroke_width=3).move_to(p))
            labs.add(MathTex(r"2^{53}" + (f"{k:+d}" if k else ""), color=C_BLUE if ok else C_RED).scale(0.5)
                     .next_to(p, DOWN, buff=0.25))
        self.play(Create(line), LaggedStart(*[FadeIn(m) for m in marks], lag_ratio=0.1), FadeIn(labs), run_time=1.2)
        one = marks[1 - lo]
        to = CurvedArrow(one.get_top() + UP * 0.05, marks[-lo].get_top() + UP * 0.05, angle=TAU / 4, color=C_RED)
        eq = M(f"float(2**53 + 1) == float(2**53)  ->  {S.P53_COLLIDE}", 20, C_RED).move_to([0, 2.55, 0])
        self.play(Create(to), FadeIn(eq), run_time=0.8)
        self.at("大整数开方")
        code = VGroup(M(f"x = (10**8 + 7)**2 - 1", 24, C_GREY),
                      VGroup(M("int(x ** 0.5)", 26), M(f"->  {S.SQ_FLOAT}", 26, C_RED), MathTex(r"\times", color=C_RED)),
                      VGroup(M("math.isqrt(x)", 26), M(f"->  {S.SQ_EXACT}", 26, C_GREEN), MathTex(r"\checkmark", color=C_GREEN)))
        for row in code[1:]:
            row.arrange(RIGHT, buff=0.3)
        code.arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([0, -1.2, 0])
        self.play(FadeIn(code[0]), run_time=0.5)
        self.play(FadeIn(code[1], shift=UP * 0.15), run_time=0.6)
        self.at("整数开方函数")
        self.play(FadeIn(code[2], shift=UP * 0.15), run_time=0.6)
        self.close(head, line, marks, labs, to, eq, code)

    # ---------------------------------------------------------------- 正确的比较
    def compare_beat(self):
        self.beat("compare")
        rows = [("不要用等号", "a == b", C_RED, r"\times"),
                ("看两数之差", "abs(a - b) < 1e-9", C_GREEN, r"\checkmark"),
                ("isclose", "math.isclose(a, b)", C_GREEN, r"\checkmark"),
                ("Decimal", f"Decimal('0.1') + Decimal('0.2')  ->  {S.DEC_SUM}", C_GREEN, r"\checkmark"),
                ("能用整数", "math.isqrt(n)   //   %", C_GREEN, r"\checkmark")]
        mobs = VGroup()
        for _, code, c, mark in rows:
            mobs.add(VGroup(MathTex(mark, color=c).scale(0.9), M(code, 24, c if c == C_RED else WHITE)).arrange(RIGHT, buff=0.35))
        mobs.arrange(DOWN, aligned_edge=LEFT, buff=0.38).move_to([0, 1.2, 0])
        for (key, *_), m in zip(rows, mobs):
            self.at(key)
            self.play(FadeIn(m, shift=RIGHT * 0.2), run_time=0.6)
        self.at("也不是所有")
        ok = VGroup(M("0.5 + 0.25 == 0.75", 28, C_TEAL), M(f"->  {S.HALF_QUARTER}", 28, C_GREEN)).arrange(RIGHT, buff=0.3)
        why = MathTex(r"\tfrac12,\ \tfrac14,\ \tfrac34 = \tfrac{k}{2^n}", color=C_GREY).scale(0.8)
        grp = VGroup(ok, why).arrange(DOWN, buff=0.25).move_to([0, -1.9, 0])
        self.play(FadeIn(ok, shift=UP * 0.15), run_time=0.6)
        self.play(FadeIn(why), run_time=0.6)
        self.close(mobs, grp)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        a = VGroup(T("二进制科学计数法", 36, C_BLUE), T("53 位有效数字", 36, C_YELLOW)).arrange(RIGHT, buff=0.8)
        a.move_to([0, 1.2, 0])
        self.play(FadeIn(a, shift=UP * 0.2), run_time=1.0)
        b = T("比较留误差，能用整数就用整数", 34).move_to([0, -0.1, 0])
        self.at("比较时")
        self.play(Write(b), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 3 周 计算机原理 4.4 节 · 第 4 周 浮点开方", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
