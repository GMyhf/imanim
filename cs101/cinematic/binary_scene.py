"""二进制与补码：减法变成加法（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。除基取余的每一步、原码/反码/补码位串、8 位加法器的进位与结果、
溢出与位运算的数都来自 binarydata（test_binary.py 对撞讲义输出、独立实现与旁白数字）。
标志画面是「补码圈」：8 位的 256 种位模式排成一圈，0 在底部，右半圈非负、左半圈为负；加法就是顺着圈走。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binarydata as S  # noqa: E402
from cine import *  # noqa: E402,F403


def num(v: int) -> str:
    """MathTex 里的负号用 ASCII 减号（LaTeX 不认 Unicode 的 −）。"""
    return str(v)


class BitRow(VGroup):
    """一排位格：1 黄色、0 灰色；四位一组中间留缝。set_bits 返回改位动画。"""

    def __init__(self, bits: str, cell=0.6, nib=0.16):
        super().__init__()
        self.cell, self.bits = cell, bits
        self.boxes, self.digs = VGroup(), VGroup()
        x = 0.0
        for i, b in enumerate(bits):
            if i and i % 4 == 0:
                x += nib
            sq = Square(cell * 0.9, stroke_color=C_GREY, stroke_width=2).move_to([x, 0, 0])
            sq.set_fill(C_YELLOW, 0.16 if b == "1" else 0)
            self.boxes.add(sq)
            self.digs.add(self._digit(b).move_to(sq))
            x += cell
        self.add(self.boxes, self.digs)
        self.center()

    def _digit(self, b, color=None):
        return Text(b, font=MONO, font_size=int(self.cell * 52),
                    color=color or (C_YELLOW if b == "1" else C_GREY))

    def set_bits(self, bits: str, color=None) -> list:
        anims = []
        for i, (old, new) in enumerate(zip(self.bits, bits)):
            if old != new:
                anims += [Transform(self.digs[i], self._digit(new, color).move_to(self.boxes[i])),
                          self.boxes[i].animate.set_fill(C_YELLOW, 0.16 if new == "1" else 0)]
        self.bits = bits
        return anims


def place_values(row: BitRow, scale=0.42) -> VGroup:
    n = len(row.bits)
    return VGroup(*[MathTex(str(1 << (n - 1 - i)), color=C_GREY).scale(scale).next_to(row.boxes[i], UP, buff=0.1)
                    for i in range(n)])


class Wheel(VGroup):
    """补码圈：位置 p（= 位串当无符号数读）在角度 -90° + 360°·p/256；0 在底部，127/128 在顶部两侧。"""

    OUT = {0: "0", 64: "64", 127: "127", 128: "128", 192: "192", 255: "255"}
    IN = {0: "0", 64: "64", 127: "127", 128: "-128", 192: "-64", 255: "-1"}
    NUDGE = {0: RIGHT * 0.22, 255: LEFT * 0.28, 127: RIGHT * 0.3, 128: LEFT * 0.3}

    def __init__(self, center=(-3.4, 0.05, 0), r=2.05):
        super().__init__()
        self.c, self.r = np.array(center, dtype=float), r
        self.circle = Circle(r, stroke_color=C_GREY, stroke_width=2).move_to(self.c)
        self.ticks = VGroup(*[Line(self.pt(p, r - (0.09 if p % 32 else 0.18)), self.pt(p, r + (0.03 if p % 32 else 0.06)),
                                   stroke_color=C_GREY, stroke_width=1 if p % 32 else 2.5) for p in range(256)])
        self.outer = VGroup(*[MathTex(s, color=C_GREY).scale(0.5).move_to(self.pt(p, r + 0.4) + self.NUDGE.get(p, 0))
                              for p, s in self.OUT.items()])
        self.inner = VGroup(*[MathTex(s, color=C_RED if p >= 128 else C_TEAL).scale(0.5)
                              .move_to(self.pt(p, r - 0.5) + self.NUDGE.get(p, 0) * 0.9) for p, s in self.IN.items()])
        self.add(self.circle, self.ticks, self.outer)

    def ang(self, p):
        return -PI / 2 + TAU * p / 256

    def pt(self, p, rr=None):
        a = self.ang(p)
        return self.c + (rr or self.r) * np.array([np.cos(a), np.sin(a), 0])

    def half(self, neg: bool) -> Arc:
        return Arc(radius=self.r, start_angle=self.ang(128 if neg else 0), angle=PI, arc_center=self.c,
                   color=C_RED if neg else C_TEAL, stroke_width=7)

    def walk(self, dot, p0, steps, run_time, color=C_YELLOW):
        """dot 从 p0 顺着圈走 steps 格；同时画出走过的弧。返回 (动画, 弧)。"""
        arc = Arc(radius=self.r + 0.16, start_angle=self.ang(p0), angle=TAU * steps / 256, arc_center=self.c,
                  color=color, stroke_width=4)
        move = UpdateFromAlphaFunc(dot, lambda m, a: m.move_to(self.pt(p0 + steps * a)))
        return AnimationGroup(move, Create(arc), run_time=run_time, rate_func=smooth), arc


class BinaryLesson(Lesson):
    def construct(self):
        for b in ("title", "bases", "sign", "twos", "sub", "overflow", "bitops", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key, lead=0.0):
        t = self.cue_start(key)
        if t is not None:
            self.wait_until(t - lead)

    def close(self, *mobs, rt=0.6):
        self.wait(max(0.1, self.left() - rt))
        self.play(FadeOut(VGroup(*mobs)), run_time=rt)

    # ---------------------------------------------------------------- 片头：一串位，两种读法
    def title_beat(self):
        self.beat("title")
        row = BitRow(S.TITLE_BITS, cell=0.8).move_to([0, 0.5, 0])
        self.play(LaggedStart(*[FadeIn(VGroup(b, d), shift=DOWN * 0.2) for b, d in zip(row.boxes, row.digs)],
                              lag_ratio=0.12), run_time=1.6)
        self.add(row)
        u = VGroup(T("无符号", 26, C_GREY), MathTex(str(S.N), color=C_BLUE).scale(1.1)).arrange(RIGHT, buff=0.25)
        s = VGroup(T("有符号", 26, C_GREY), MathTex(num(S.TITLE_SIGNED), color=C_RED).scale(1.1)).arrange(RIGHT, buff=0.25)
        u.move_to([-2.6, -0.9, 0])
        s.move_to([2.6, -0.9, 0])
        self.at("无符号数读")
        self.play(FadeIn(u, shift=UP * 0.2), run_time=0.7)
        self.at("有符号数读")
        self.play(FadeIn(s, shift=UP * 0.2), run_time=0.7)
        title = T("二进制与补码", 64).move_to([0, 2.6, 0])
        sub = T("减法变成加法", 30, C_YELLOW).move_to([0, -2.1, 0])
        self.at("补码")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.close(row, u, s, title, sub)

    # ---------------------------------------------------------------- 4.1 除基取余、按权展开、四位一组
    def bases_beat(self):
        self.beat("bases")
        steps = S.div_steps(S.N)
        head = T("除基取余", 28, C_YELLOW).move_to([-4.5, 3.15, 0])
        rows = VGroup(*[MathTex(rf"{a} \div 2 = {q}", r"\;\cdots\;", str(r)).scale(0.62) for a, q, r in steps])
        rows.arrange(DOWN, buff=0.2, aligned_edge=RIGHT).move_to([-4.5, 0.75, 0])
        for m in rows:
            m[2].set_color(C_YELLOW)
        self.play(FadeIn(head), FadeIn(rows[0], shift=DOWN * 0.15), run_time=0.7)
        self.at("一直除到", 0.3)
        self.play(LaggedStart(*[FadeIn(m, shift=DOWN * 0.15) for m in rows[1:]], lag_ratio=0.3), run_time=2.0)
        row = BitRow("0" * 8, cell=0.62).move_to([2.7, 1.55, 0])
        for d in row.digs:
            d.set_opacity(0)
        pv = place_values(row)
        self.play(FadeIn(row.boxes), FadeIn(pv), run_time=0.6)
        self.at("倒过来读", 0.2)
        arrow = Arrow(rows[-1].get_right() + RIGHT * 0.25, rows[0].get_right() + RIGHT * 0.25, buff=0,
                      color=C_TEAL, stroke_width=4, max_tip_length_to_length_ratio=0.06)
        self.play(GrowArrow(arrow), run_time=0.7)
        bits = S.from_remainders(steps)
        flies = []
        for i, (_, _, r) in enumerate(steps):
            k = 7 - i
            tgt = row._digit(str(r)).move_to(row.boxes[k])
            flies.append(AnimationGroup(Transform(rows[i][2].copy(), tgt, remover=True),
                                        row.boxes[k].animate.set_fill(C_YELLOW, 0.16 if r else 0)))
        self.play(LaggedStart(*reversed(flies), lag_ratio=0.25), run_time=2.4)
        for i, (_, _, r) in enumerate(steps):
            row.digs[7 - i].become(row._digit(str(r)).move_to(row.boxes[7 - i]))
        self.add(row.digs)
        row.bits = bits
        lowtag = T("第一个余数 = 最低位", 20, C_TEAL).next_to(row.boxes[7], DOWN, buff=0.15).align_to(row.boxes[7], RIGHT)
        self.at("第一次得到", 0.2)
        self.play(Indicate(rows[0][2], color=C_TEAL), FadeIn(lowtag), run_time=0.9)
        w = S.weights(bits)
        expo = MathTex("+".join(map(str, w)) + f"={S.N}", color=C_BLUE).scale(0.75).move_to([2.7, -0.15, 0])
        self.at("按权展开", 0.2)
        ones = [pv[i] for i, b in enumerate(bits) if b == "1"]
        self.play(FadeOut(lowtag), *[x.animate.set_color(C_BLUE) for x in ones], run_time=0.5)
        self.play(Write(expo), run_time=1.3)
        groups = S.hex_groups(bits)
        braces, hexd = VGroup(), VGroup()
        for g in range(2):
            br = Brace(VGroup(*row.boxes[4 * g:4 * g + 4]), DOWN, buff=0.08, color=C_PURPLE)
            braces.add(br)
            hexd.add(Text(groups[g][1], font=MONO, font_size=30, color=C_PURPLE).next_to(br, DOWN, buff=0.08))
        self.at("四位一组", 0.2)
        self.play(expo.animate.shift(DOWN * 1.15), FadeIn(braces), run_time=0.7)
        self.play(FadeIn(hexd, shift=DOWN * 0.15), run_time=0.6)
        note = VGroup(Text("0x" + "".join(h for _, h in groups), font=MONO, font_size=30, color=C_PURPLE),
                      T("1 字节 = 2 位十六进制", 22, C_GREY)).arrange(RIGHT, buff=0.4).move_to([2.7, -2.15, 0])
        self.at("一个字节", 0.3)
        self.play(FadeIn(note, shift=UP * 0.15), run_time=0.6)
        self.close(head, rows, arrow, row, pv, expo, braces, hexd, note)

    # ---------------------------------------------------------------- 4.2 原码、反码：两个零
    def sign_beat(self):
        self.beat("sign")
        head = VGroup(MathTex("-5", color=C_RED).scale(0.9), T("的 8 位编码", 28)).arrange(RIGHT, buff=0.15)
        head.move_to([0, 3.1, 0])
        self.play(FadeIn(head), run_time=0.6)
        self.at("这叫原码", 0.4)
        lab1 = T("原码", 30, C_YELLOW).move_to([-5.2, 1.6, 0])
        r1 = BitRow(S.NEG5["原码"], cell=0.55).move_to([-1.1, 1.6, 0])
        self.play(FadeIn(lab1), FadeIn(r1), run_time=0.7)
        sb = SurroundingRectangle(r1.boxes[0], color=C_RED, buff=0.04)
        t_sign = T("符号", 20, C_RED).next_to(sb, UP, buff=0.1)
        br = Brace(VGroup(*r1.boxes[1:]), UP, buff=0.08, color=C_BLUE)
        t5 = MathTex("5", color=C_BLUE).scale(0.6).next_to(br, UP, buff=0.06)
        self.at("符号位一", 0.3)
        self.play(Create(sb), FadeIn(t_sign), FadeIn(br), FadeIn(t5), run_time=0.8)
        z = VGroup(Text("+0  0000 0000", font=MONO, font_size=22, color=C_GREY),
                   Text("−0  1000 0000", font=MONO, font_size=22, color=C_RED)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        z.move_to([4.6, 1.6, 0])
        self.at("两个零", 0.3)
        self.play(FadeIn(z, shift=LEFT * 0.2), run_time=0.7)
        warn = T("加减法要先判符号", 22, C_GREY).move_to([-1.1, 0.75, 0])
        self.at("先看符号", 0.3)
        self.play(FadeIn(warn), run_time=0.5)
        lab2 = T("反码", 30, C_YELLOW).move_to([-5.2, -0.6, 0])
        r2 = BitRow(S.NEG5["原码"], cell=0.55).move_to([-1.1, -0.6, 0])
        self.at("反码", 0.2)
        self.play(FadeIn(lab2), TransformFromCopy(r1, r2), run_time=0.8)
        self.play(*r2.set_bits(S.NEG5["反码"], C_TEAL), run_time=0.9)
        z2 = VGroup(Text("+0  0000 0000", font=MONO, font_size=22, color=C_GREY),
                    Text("−0  1111 1111", font=MONO, font_size=22, color=C_RED)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        z2.move_to([4.6, -0.6, 0])
        self.at("零仍然", 0.3)
        self.play(FadeIn(z2, shift=LEFT * 0.2), run_time=0.7)
        self.close(head, lab1, r1, sb, t_sign, br, t5, z, warn, lab2, r2, z2)

    # ---------------------------------------------------------------- 4.2 补码：取反加一；补码圈
    def twos_beat(self):
        self.beat("twos")
        pos, inv, plus = S.neg_steps(-5)
        rule = VGroup(T("补码", 32, C_YELLOW), T("正数不变；负数取反再加一", 28)).arrange(RIGHT, buff=0.4)
        rule.move_to([0, 3.1, 0])
        self.play(FadeIn(rule, shift=DOWN * 0.2), run_time=0.7)
        labs = VGroup(MathTex("5", color=C_BLUE), T("取反", 26, C_GREY), T("加一", 26, C_GREY)).scale(1)
        rows = VGroup(BitRow(pos, cell=0.6), BitRow(pos, cell=0.6), BitRow(inv, cell=0.6))   # 第三行从「取反」结果出发，加一只改末两位
        for i, (r, l) in enumerate(zip(rows, labs)):
            r.move_to([0.3, 1.7 - 1.05 * i, 0])
            l.next_to(r, LEFT, buff=0.6)
        self.play(FadeIn(labs[0]), FadeIn(rows[0]), run_time=0.6)
        self.at("五取反", 0.1)
        self.play(FadeIn(labs[1]), TransformFromCopy(rows[0], rows[1]), run_time=0.6)
        self.play(*rows[1].set_bits(inv), run_time=0.8)
        self.at("再加一", 0.2)
        self.play(FadeIn(labs[2]), TransformFromCopy(rows[1], rows[2]), run_time=0.6)
        self.play(*rows[2].set_bits(plus), run_time=0.7)
        res = MathTex("=-5", color=C_RED).scale(0.9).next_to(rows[2], RIGHT, buff=0.4)
        self.play(FadeIn(res), run_time=0.4)
        # 收成右侧小卡，左侧出补码圈
        card = VGroup(rows[2], res)
        self.at("排成一圈", 0.5)
        self.play(FadeOut(VGroup(rows[0], rows[1], labs, rule)),
                  card.animate.scale(0.75).move_to([3.6, 2.2, 0]), run_time=0.8)
        wh = Wheel()
        self.play(Create(wh.circle), LaggedStart(*[Create(t) for t in wh.ticks], lag_ratio=0.004),
                  FadeIn(wh.outer), run_time=1.6)
        dot = Dot(wh.pt(0), color=C_YELLOW, radius=0.11)
        self.add(dot)
        m1 = VGroup(MathTex("-1", color=C_RED).scale(0.8), Text("1111 1111", font=MONO, font_size=24, color=C_YELLOW))
        m1.arrange(RIGHT, buff=0.35).move_to([3.6, 1.25, 0])
        self.at("往回退一格", 0.2)
        a1, arc1 = wh.walk(dot, 0, -1, 0.8, C_RED)
        self.play(a1)
        self.play(FadeIn(m1, shift=LEFT * 0.2), run_time=0.5)
        self.at("退五格", 0.2)
        a5, arc5 = wh.walk(dot, -1, -4, 1.0, C_RED)
        self.play(a5)
        self.play(Indicate(card, color=C_RED), run_time=0.7)
        u = VGroup(T("当无符号读", 22, C_GREY), MathTex(str(S.wheel_pos(-5)), color=C_BLUE).scale(0.8))
        u.arrange(RIGHT, buff=0.25).move_to([3.6, 0.45, 0])
        self.at("二百五十一", 0.3)
        self.play(FadeIn(u, shift=LEFT * 0.2), Flash(dot, color=C_BLUE), run_time=0.8)
        lo, hi = S.RANGE8
        self.at("最高位是一", 0.2)
        self.halves = [wh.half(False), wh.half(True)]
        self.play(*[Create(h) for h in self.halves], FadeIn(wh.inner), FadeOut(arc1), FadeOut(arc5),
                  run_time=1.2)
        rng = VGroup(T("8 位补码", 24, C_GREY), MathTex(rf"{lo} \sim {hi}", color=C_YELLOW).scale(0.9))
        rng.arrange(RIGHT, buff=0.3).move_to([3.6, -0.75, 0])
        extra = VGroup(Text("1000 0000", font=MONO, font_size=24, color=C_RED), MathTex(rf"={lo}", color=C_RED).scale(0.8),
                       T("没有 +128", 22, C_GREY)).arrange(RIGHT, buff=0.25).move_to([3.6, -1.55, 0])
        legend = T("外圈：无符号　内圈：补码", 20, C_GREY).move_to([-3.4, 3.2, 0])
        self.at("范围", 0.3)
        self.play(FadeIn(rng), FadeIn(legend), run_time=0.7)
        self.at("负数比正数", 0.3)
        self.play(FadeIn(extra, shift=UP * 0.15), Indicate(wh.inner[3], color=C_RED), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(card, m1, u, rng, extra)), FadeOut(dot), run_time=0.6)
        self.wheel, self.legend = wh, legend

    # ---------------------------------------------------------------- 加法器：5 − 7、24 + (−17)
    def column(self, a: int, b: int, la: str, lb: str, y0=2.1):
        t = S.add8_trace(a, b)
        ra, rb, rr = BitRow(t["a"], 0.48), BitRow(t["b"], 0.48), BitRow(t["r"], 0.48)
        x = 3.3
        ra.move_to([x, y0, 0])
        rb.move_to([x, y0 - 0.62, 0])
        plus = MathTex("+").scale(0.8).next_to(rb, LEFT, buff=0.25)
        bar = Line([x - 2.2, y0 - 1.0, 0], [x + 2.2, y0 - 1.0, 0], color=C_GREY, stroke_width=2)
        rr.move_to([x, y0 - 1.42, 0])
        for d in rr.digs:
            d.set_opacity(0)
        tags = VGroup(MathTex(la, color=C_BLUE).scale(0.65).next_to(ra, RIGHT, buff=0.3),
                      MathTex(lb, color=C_RED).scale(0.65).next_to(rb, RIGHT, buff=0.3))
        return t, VGroup(ra, rb, plus, bar, rr, tags), rr

    def fill_result(self, rr: BitRow, bits: str, rt=1.4):
        anims = []
        for i in reversed(range(8)):
            d = rr._digit(bits[i]).move_to(rr.boxes[i])
            anims.append(AnimationGroup(Transform(rr.digs[i], d), rr.boxes[i].animate.set_fill(C_YELLOW, 0.16 if bits[i] == "1" else 0)))
        self.play(LaggedStart(*anims, lag_ratio=0.2), run_time=rt)
        rr.bits = bits

    def sub_beat(self):
        self.beat("sub")
        wh = self.wheel
        a, b = S.SUB_EXAMPLE
        eq = MathTex(rf"{a}-{b}", "=", rf"{a}+(-{b})").scale(0.85).move_to([3.3, 3.15, 0])
        eq[2].set_color(C_YELLOW)
        self.play(Write(eq), run_time=0.9)
        t, col, rr = self.column(a, S.wheel_pos(-b), str(a), f"-{b}")
        self.at("逐位相加", 0.5)
        self.play(FadeIn(col), run_time=0.6)
        self.fill_result(rr, t["r"])
        neg = SurroundingRectangle(rr.boxes[0], color=C_RED, buff=0.04)
        self.at("最高位是一", 0.2)
        self.play(Create(neg), run_time=0.4)
        back = VGroup(T("再取补码", 22, C_GREY), Text(S.neg_steps(t["sr"])[0], font=MONO, font_size=22, color=C_BLUE),
                      MathTex("=2", color=C_BLUE).scale(0.7)).arrange(RIGHT, buff=0.2).move_to([3.3, -0.05, 0])
        self.at("再取一次", 0.3)
        self.play(FadeIn(back, shift=UP * 0.15), run_time=0.6)
        ans = MathTex(rf"={num(t['sr'])}", color=C_RED).scale(0.8).next_to(rr, RIGHT, buff=0.3)
        self.at("结果是负二", 0.3)
        self.play(FadeIn(ans), run_time=0.4)
        dot = Dot(wh.pt(a), color=C_YELLOW, radius=0.11)
        self.at("在圈上看", 0.3)
        self.play(FadeIn(dot, scale=0.5), run_time=0.4)
        steps = S.wheel_pos(-b)
        walk = VGroup(MathTex(rf"+{steps}", color=C_YELLOW).scale(0.8), T("格", 22, C_GREY)).arrange(RIGHT, buff=0.1)
        walk.move_to([3.3, -0.8, 0])
        mv, arc = wh.walk(dot, a, steps, 2.6)
        self.play(mv, FadeIn(walk), run_time=2.6)
        self.play(Flash(dot, color=C_YELLOW), run_time=0.5)
        self.at("二十四加", 0.4)
        self.play(FadeOut(VGroup(eq, col, neg, back, ans, walk, arc, rr)), FadeOut(dot), run_time=0.5)
        a2, b2 = S.COURSE_ADDS[1]
        t2, col2, rr2 = self.column(a2, b2, str(S.to_signed8(a2)), num(S.to_signed8(b2)), y0=2.6)
        self.play(FadeIn(col2), run_time=0.6)
        self.fill_result(rr2, t2["r"], rt=1.2)
        carry = Text("1", font=MONO, font_size=26, color=C_RED).next_to(rr2.boxes[0], LEFT, buff=0.35)
        self.at("进出一个一", 0.3)
        self.play(FadeIn(carry, shift=LEFT * 0.2), run_time=0.5)
        cross = Cross(carry, stroke_color=C_RED, stroke_width=4, scale_factor=0.8)
        self.at("直接丢掉", 0.2)
        self.play(Create(cross), run_time=0.4)
        self.play(FadeOut(VGroup(carry, cross), shift=LEFT * 0.3), run_time=0.4)
        ans2 = MathTex(rf"={t2['sr']}", color=C_GREEN).scale(0.8).next_to(rr2, RIGHT, buff=0.3)
        dot2 = Dot(wh.pt(a2), color=C_YELLOW, radius=0.11)
        self.add(dot2)
        mv2, arc2 = wh.walk(dot2, a2, b2, 2.2, C_GREEN)
        self.play(mv2, FadeIn(ans2), run_time=2.2)
        lap = T("绕过底部一圈 = 丢掉进位", 22, C_GREEN).move_to([3.3, 0.35, 0])
        self.play(FadeIn(lap), run_time=0.5)
        key = VGroup(MathTex(r"A-B", "=", r"A+(\overline{B}+1)").scale(0.85)).move_to([3.3, -0.85, 0])
        key[0][2].set_color(C_YELLOW)
        cap = T("同一套加法电路", 24, C_YELLOW).move_to([3.3, -1.7, 0])
        self.at("同一套", 0.3)
        self.play(FadeIn(key, shift=UP * 0.15), FadeIn(cap), run_time=0.8)
        self.close(col2, rr2, ans2, lap, key, cap, arc2, dot2)

    # ---------------------------------------------------------------- 溢出
    def overflow_beat(self):
        self.beat("overflow")
        wh = self.wheel
        t = S.add8_trace(127, 1)
        dot = Dot(wh.pt(127), color=C_YELLOW, radius=0.11)
        top = Arc(radius=wh.r + 0.2, start_angle=wh.ang(126), angle=TAU * 3 / 256, arc_center=wh.c, color=C_RED,
                  stroke_width=8)
        self.play(FadeIn(dot, scale=0.5), Create(top), run_time=0.6)
        eq = VGroup(Text("0111 1111", font=MONO, font_size=26, color=C_BLUE), MathTex("+1").scale(0.8),
                    MathTex(r"\to").scale(0.8), Text(t["r"][:4] + " " + t["r"][4:], font=MONO, font_size=26, color=C_RED))
        eq.arrange(RIGHT, buff=0.25).move_to([3.4, 2.0, 0])
        val = MathTex(rf"{t['sa']}+{t['sb']}={num(t['sr'])}", color=C_RED).scale(0.9).move_to([3.4, 1.2, 0])
        self.at("一百二十七加一", 0.3)
        self.play(FadeIn(eq), run_time=0.6)
        mv, arc = wh.walk(dot, 127, 1, 0.9, C_RED)
        self.at("跨过", 0.4)
        self.play(mv)
        self.play(Flash(dot, color=C_RED, flash_radius=0.4), FadeIn(val, shift=UP * 0.15), run_time=0.7)
        tag = T("溢出", 34, C_RED).move_to([3.4, 0.25, 0])
        self.at("这就是溢出", 0.3)
        self.play(FadeIn(tag, scale=1.2), run_time=0.5)
        # 32 位：把圈收起，换成三行对照
        self.at("三十二位", 0.4)
        self.play(FadeOut(VGroup(wh, wh.inner, *self.halves, self.legend, dot, top, arc, eq, val, tag)), run_time=0.7)
        mx = S.INT32_MAX
        lines = VGroup(
            VGroup(T("32 位 int", 26, C_GREY), MathTex(rf"{mx}+1", r"\to", rf"{num(S.c_int32(mx + 1))}").scale(0.85)),
            VGroup(T("Python int", 26, C_GREY), MathTex(rf"{mx}+1", "=", rf"{mx + 1}").scale(0.85)),
        )
        for g in lines:
            g.arrange(RIGHT, buff=0.5)
        lines.arrange(DOWN, buff=0.6, aligned_edge=LEFT).move_to([0, 1.3, 0])
        lines[0][1][2].set_color(C_RED)
        lines[1][1][2].set_color(C_GREEN)
        self.play(FadeIn(lines[0], shift=UP * 0.2), run_time=0.8)
        self.at("任意精度", 0.5)
        self.play(FadeIn(lines[1], shift=UP * 0.2), run_time=0.8)
        tip = VGroup(T("C++ 做题：中间结果超过", 26), MathTex(r"2\times10^9", color=C_YELLOW).scale(0.85),
                     T("就换", 26), Text("long long", font=MONO, font_size=28, color=C_YELLOW)).arrange(RIGHT, buff=0.2)
        tip.move_to([0, -0.9, 0])
        self.at("用 C++", 0.4)
        self.play(FadeIn(tip, shift=UP * 0.2), run_time=0.8)
        self.close(lines, tip)

    # ---------------------------------------------------------------- 4.3 位运算：~6、n & (n − 1)
    def bitops_beat(self):
        self.beat("bitops")
        six = BitRow(format(6, "08b"), 0.55).move_to([-0.6, 2.3, 0])
        l6 = MathTex("6", color=C_BLUE).scale(0.85).next_to(six, LEFT, buff=0.5)
        self.play(FadeIn(six), FadeIn(l6), run_time=0.6)
        neg = BitRow(format(6, "08b"), 0.55).move_to([-0.6, 1.4, 0])
        ln = Text("~6", font=MONO, font_size=28, color=C_YELLOW).next_to(neg, LEFT, buff=0.4)
        self.at("按位取反", 0.3)
        self.play(TransformFromCopy(six, neg), FadeIn(ln), run_time=0.6)
        self.play(*neg.set_bits(S.to_twos_complement(~6)), run_time=0.8)
        r7 = MathTex(rf"={num(~6)}", color=C_RED).scale(0.85).next_to(neg, RIGHT, buff=0.35)
        self.play(FadeIn(r7), run_time=0.4)
        law = MathTex(r"\sim x = -x-1", color=C_YELLOW).scale(0.85).move_to([4.6, 1.85, 0])
        self.at("相反数减一", 0.5)
        self.play(Write(law), run_time=0.9)
        self.at("十二和十一", 0.4)
        self.play(FadeOut(VGroup(six, l6, neg, ln, r7, law)), run_time=0.5)
        n = 12
        a, b = BitRow(format(n, "08b"), 0.55), BitRow(format(n - 1, "08b"), 0.55)
        r = BitRow(format(S.clear_lowbit(n), "08b"), 0.55)
        a.move_to([-0.6, 2.3, 0])
        b.move_to([-0.6, 1.5, 0])
        bar = Line([-3.1, 1.05, 0], [1.9, 1.05, 0], color=C_GREY, stroke_width=2)
        r.move_to([-0.6, 0.6, 0])
        la = MathTex("12", color=C_BLUE).scale(0.8).next_to(a, LEFT, buff=0.5)
        lb = MathTex("11", color=C_BLUE).scale(0.8).next_to(b, LEFT, buff=0.5)
        amp = Text("&", font=MONO, font_size=30).next_to(lb, LEFT, buff=0.25)
        self.play(FadeIn(a), FadeIn(la), run_time=0.5)
        self.play(FadeIn(b), FadeIn(lb), FadeIn(amp), run_time=0.5)
        low = (n & -n).bit_length() - 1                 # 最低位 1 的位号（自右 0 起）
        k = 7 - low
        hl = SurroundingRectangle(a.boxes[k], color=C_YELLOW, buff=0.04)
        run = SurroundingRectangle(VGroup(*b.boxes[k:]), color=C_TEAL, buff=0.05)
        self.at("最低位的一变成零", 0.3)
        self.play(Create(hl), run_time=0.4)
        self.play(Create(run), run_time=0.6)
        self.at("相与之后", 0.3)
        self.play(Create(bar), FadeIn(r, shift=DOWN * 0.15), run_time=0.8)
        cleared = SurroundingRectangle(r.boxes[k], color=C_RED, buff=0.04)
        r8 = MathTex(rf"={S.clear_lowbit(n)}", color=C_GREEN).scale(0.8).next_to(r, RIGHT, buff=0.35)
        self.play(Create(cleared), FadeIn(r8), run_time=0.6)
        rule = VGroup(Text("n & (n-1) == 0", font=MONO, font_size=26, color=C_YELLOW), MathTex(r"\Leftrightarrow"),
                      T("n 只有一个 1：2 的幂", 24)).arrange(RIGHT, buff=0.3).move_to([0, -0.8, 0])
        pows = VGroup(*[Text(format(p, "b"), font=MONO, font_size=22, color=C_GREY) for p in (1, 2, 4, 8, 16)
                        if S.is_pow2(p)]).arrange(RIGHT, buff=0.5).move_to([0, -1.65, 0])
        self.at("如果结果是零", 0.3)
        self.play(FadeIn(rule, shift=UP * 0.15), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(p) for p in pows], lag_ratio=0.2), run_time=0.9)
        self.close(a, b, r, bar, la, lb, amp, hl, run, cleared, r8, rule, pows)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        items = VGroup(
            VGroup(T("进制", 28, C_YELLOW), T("除基取余倒着读 · 按权展开加回去", 28)),
            VGroup(T("补码", 28, C_YELLOW), T("负数取反加一 · 8 位排成一圈", 28)),
            VGroup(T("加法器", 28, C_YELLOW), T("减法 = 加补码 · 跨过顶端就溢出", 28)),
        )
        for g in items:
            g.arrange(RIGHT, buff=0.5)
        items.arrange(DOWN, buff=0.55, aligned_edge=LEFT).move_to([0, 0.6, 0])
        keys = ["除基取余", "负数取反", "减法就是"]
        for g, k in zip(items, keys):
            self.at(k, 0.2)
            self.play(FadeIn(g, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 3 周 计算机原理 4.1–4.3 节 P26–P37 · OpenJudge 02734", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
