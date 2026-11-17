"""购物：覆盖连续金额的贪心（例题精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例、每一步的 reach 与选中面值、对照带法、暴力组合数、随机对拍结果
全部来自 shoppingdata（讲义三版代码原样；test_shopping.py 用位运算子集和、逐层暴力枚举对撞讲义输出与旁白数字）。
二进制拆分那一段取 knapvardata.binary_split（与背包变形片同一份）。
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knapvardata as K  # noqa: E402
import shoppingdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

COIN_COL = {1: C_TEAL, 2: C_BLUE, 5: C_YELLOW, 10: C_PURPLE}
COVER = C_GREEN


def coin(v, r=0.36, col=None):
    col = col or COIN_COL.get(v, C_GREY)
    c = Circle(r, stroke_color=col, stroke_width=3).set_fill(col, 0.18)
    return VGroup(c, MathTex(str(v), color=col).scale(0.75 * r / 0.36).move_to(c))


def coin_alpha(cm, x):
    """硬币整体淡入淡出：填充保持半透明（直接 set_opacity(1) 会把填充变成不透明、盖住同色数字）。"""
    return [cm[0].animate.set_stroke(opacity=x).set_fill(opacity=0.18 * x), cm[1].animate.set_opacity(x)]


class NumLine(VGroup):
    """0..hi 的整数数轴：xof(v) 给横坐标；bar(a, b) 画覆盖段。"""

    def __init__(self, hi, x0, unit, y, every=1, lab_scale=0.45):
        super().__init__()
        self.hi, self.x0, self.unit, self.y = hi, x0, unit, y
        self.axis = Line([self.xof(0) - 0.3, y, 0], [self.xof(hi) + 0.3, y, 0], color=C_GREY, stroke_width=2)
        self.ticks = VGroup(*[Line([self.xof(v), y - 0.08, 0], [self.xof(v), y + 0.08, 0], color=C_GREY,
                                   stroke_width=2) for v in range(hi + 1)])
        self.labs = VGroup(*[MathTex(str(v), color=C_GREY).scale(lab_scale).move_to([self.xof(v), y - 0.35, 0])
                             for v in range(0, hi + 1, every)])
        self.add(self.axis, self.ticks, self.labs)

    def xof(self, v):
        return self.x0 + self.unit * v

    def pt(self, v, dy=0.0):
        return np.array([self.xof(v), self.y + dy, 0])

    def bar(self, a, b, col=COVER, dy=0.0, sw=12):
        if a == b:
            return Dot(self.pt(a, dy), radius=0.09, color=col)
        return Line(self.pt(a, dy), self.pt(b, dy), color=col, stroke_width=sw)


class ShoppingLesson(Lesson):
    def construct(self):
        for b in ("title", "read", "reach", "walk", "why", "echo", "code", "brute", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def tail(self, *mobs):
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*mobs)), run_time=0.6)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        tag = T("例题精讲", 28, C_GREY).move_to([0, 3.1, 0])
        title = T("购物", 72).move_to([0, 2.05, 0])
        sub = VGroup(Text("M29896", font=MONO, font_size=28, color=C_BLUE),
                     T("2025-11-06 模拟机考 · 第五题", 28, C_GREY)).arrange(RIGHT, buff=0.3).move_to([0, 1.05, 0])
        self.play(FadeIn(tag), Write(title), run_time=1.0)
        self.wait_until(self.cue_start("今天是", self.now))
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("每种面值", self.now))
        coins = VGroup(*[coin(v, 0.45) for v in D.COINS]).arrange(RIGHT, buff=0.9).move_to([0, -0.3, 0])
        inf = VGroup(*[MathTex(r"\times\infty", color=C_GREY).scale(0.75).next_to(c, RIGHT, buff=0.08) for c in coins])
        self.play(LaggedStart(*[FadeIn(c, scale=0.6) for c in coins], lag_ratio=0.15), run_time=1.0)
        self.play(FadeIn(inf), run_time=0.5)
        self.wait_until(self.cue_start("要带尽量少", self.now))
        goal = VGroup(T("带最少的硬币，使", 30), MathTex(r"1, 2, \dots, X", color=COVER).scale(0.9),
                      T("每个金额都能凑出", 30)).arrange(RIGHT, buff=0.2).move_to([0, -1.6, 0])
        self.play(FadeIn(goal, shift=UP * 0.2), run_time=0.9)
        self.wait_until(self.cue_start("做不到", self.now))
        neg = VGroup(T("做不到：输出", 26, C_GREY), MathTex("-1", color=C_RED).scale(0.85)).arrange(RIGHT, buff=0.15)
        neg.move_to([0, -2.45, 0])
        self.play(FadeIn(neg), run_time=0.6)
        self.tail(tag, title, sub, coins, inf, goal, neg)

    # ---------------------------------------------------------------- 读样例
    def cells(self, bag, y, lit_col=COVER):
        """1..X 二十格，能由 bag 凑出的点亮。"""
        sums = D.subset_sums(bag)
        g = VGroup()
        for v in range(1, D.X + 1):
            ok = v in sums
            sq = Square(0.5, stroke_color=lit_col if ok else C_RED, stroke_width=2.5)
            sq.set_fill(lit_col if ok else C_RED, 0.25 if ok else 0.08)
            g.add(VGroup(sq, MathTex(str(v), color=WHITE if ok else C_GREY).scale(0.5)))
        g.arrange(RIGHT, buff=0.08).move_to([0, y, 0])
        for sq in g:
            sq[1].move_to(sq[0])
        return g

    def read_beat(self):
        self.beat("read")
        inp = VGroup(T("样例输入", 22, C_GREY),
                     Text("20 4\n1 2 5 10", font=MONO, font_size=30, line_spacing=0.8)).arrange(DOWN, buff=0.2,
                                                                                         aligned_edge=LEFT)
        out = VGroup(T("样例输出", 22, C_GREY), Text("5", font=MONO, font_size=30, color=C_YELLOW)).arrange(
            DOWN, buff=0.2, aligned_edge=LEFT)
        io_ = VGroup(inp, out).arrange(RIGHT, buff=1.5, aligned_edge=UP).move_to([-2.4, 2.4, 0])
        self.play(FadeIn(inp, shift=UP * 0.2), run_time=0.8)
        note = VGroup(T("上限", 24, C_GREY), MathTex("X = 20", color=COVER).scale(0.8)).arrange(RIGHT, buff=0.15)
        note.next_to(io_, RIGHT, buff=1.0)
        self.play(FadeIn(note), run_time=0.5)
        self.wait_until(self.cue_start("答案是五枚", self.now))
        self.play(FadeIn(out, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("这不是找零", self.now))
        bag = VGroup(coin(10), coin(10)).arrange(RIGHT, buff=0.2).move_to([-4.6, 0.6, 0])
        lab = T("只凑 20：两枚 10", 26).next_to(bag, RIGHT, buff=0.35)
        self.play(FadeIn(bag), FadeIn(lab), run_time=0.8)
        self.wait_until(self.cue_start("每个金额都要", self.now))
        g = self.cells([10, 10], -0.5)
        miss = T(f"两枚 10 只能凑出 10 和 20，其余 {D.X - 2} 个都凑不出", 24, C_RED).move_to([0, -1.35, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.1) for c in g], lag_ratio=0.04), run_time=1.2)
        self.play(FadeIn(miss), run_time=0.5)
        self.wait_until(self.cue_start("只能用带着的", self.now))
        rule = T("付每个金额时，只能用带着的这几枚，每枚最多用一次", 26, C_YELLOW).move_to([0, -2.3, 0])
        self.play(FadeIn(rule, shift=UP * 0.15), run_time=0.7)
        self.tail(io_, note, bag, lab, g, miss, rule)

    # ---------------------------------------------------------------- 不变量：reach
    def reach_beat(self):
        self.beat("reach")
        nl = NumLine(10, -5.0, 1.0, 0.0, lab_scale=0.55)
        defn = VGroup(Text("reach", font=MONO, font_size=34, color=COVER), T("：能凑出", 30),
                      MathTex(r"1 \sim \mathrm{reach}", color=COVER).scale(0.9), T("的每一个数", 30))
        defn.arrange(RIGHT, buff=0.15).move_to([0, 3.0, 0])
        bag0 = [1, 2]
        bagm = VGroup(T("手上：", 24, C_GREY), *[coin(v, 0.3) for v in bag0]).arrange(RIGHT, buff=0.15)
        bagm.move_to([-4.6, 1.9, 0])
        r0 = sum(bag0)
        bar = nl.bar(0, r0)
        rl = MathTex(rf"\mathrm{{reach}} = {r0}", color=COVER).scale(0.75).next_to(nl.pt(r0), UP, buff=0.3)
        self.play(FadeIn(defn), Create(nl), run_time=1.0)
        self.play(FadeIn(bagm), Create(bar), FadeIn(rl), run_time=0.9)
        self.wait_until(self.cue_start("一开始", self.now))
        init = VGroup(T("什么都不带：", 24, C_GREY), MathTex(r"\mathrm{reach} = 0", color=C_GREY).scale(0.7))
        init.arrange(RIGHT, buff=0.1).move_to([3.4, 1.9, 0])
        self.play(FadeIn(init), Indicate(nl.labs[0], color=COVER), run_time=0.8)
        self.wait_until(self.cue_start("再带一枚硬币", self.now))
        c = 2
        nc = coin(c, 0.3).next_to(bagm, RIGHT, buff=0.15)
        shifted = nl.bar(0, r0, C_BLUE, dy=-0.9)
        self.play(FadeIn(nc, scale=0.5), TransformFromCopy(bar, shifted), run_time=0.8)
        arr = Arrow(nl.pt(0, -0.9) + DOWN * 0.3, nl.pt(c, -0.9) + DOWN * 0.3, buff=0, color=C_BLUE,
                    stroke_width=4, max_tip_length_to_length_ratio=0.25)
        al = VGroup(T("每个数", 22, C_BLUE), MathTex(f"+{c}", color=C_BLUE).scale(0.7)).arrange(RIGHT, buff=0.1)
        al.next_to(arr, DOWN, buff=0.1)
        self.play(shifted.animate.shift(RIGHT * nl.unit * c), GrowArrow(arr), FadeIn(al), run_time=1.2)
        self.wait_until(self.cue_start("首尾相接", self.now))
        cond = MathTex(rf"{c} \le \mathrm{{reach}} + 1 = {r0 + 1}", color=COVER).scale(0.75).move_to([3.4, -1.75, 0])
        r1 = r0 + c
        nb = nl.bar(0, r1)
        nrl = MathTex(rf"\mathrm{{reach}} = {r1}", color=COVER).scale(0.75).next_to(nl.pt(r1), UP, buff=0.3)
        self.play(FadeIn(cond), run_time=0.5)
        self.play(shifted.animate.shift(UP * 0.9).set_color(COVER), run_time=0.7)
        self.play(Transform(bar, nb), Transform(rl, nrl), FadeOut(shifted), run_time=0.6)
        self.wait_until(self.cue_start("一旦大于", self.now))
        c2 = 5
        back = nl.bar(0, r0)
        brl = MathTex(rf"\mathrm{{reach}} = {r0}", color=COVER).scale(0.75).next_to(nl.pt(r0), UP, buff=0.3)
        nc2 = coin(c2, 0.3).move_to(nc)
        sh2 = nl.bar(c2, r0 + c2, C_YELLOW, dy=0.0)
        arr2 = Arrow(nl.pt(0, -0.9) + DOWN * 0.3, nl.pt(c2, -0.9) + DOWN * 0.3, buff=0, color=C_YELLOW,
                     stroke_width=4, max_tip_length_to_length_ratio=0.12)
        al2 = VGroup(T("每个数", 22, C_YELLOW), MathTex(f"+{c2}", color=C_YELLOW).scale(0.7)).arrange(RIGHT, buff=0.1)
        al2.next_to(arr2, DOWN, buff=0.1)
        cond2 = MathTex(rf"{c2} > \mathrm{{reach}} + 1 = {r0 + 1}", color=C_RED).scale(0.75).move_to(cond)
        self.play(Transform(bar, back), Transform(rl, brl), ReplacementTransform(nc, nc2), Transform(arr, arr2),
                  Transform(al, al2), Transform(cond, cond2), run_time=0.8)
        self.play(TransformFromCopy(bar, sh2), run_time=0.9)
        self.wait_until(self.cue_start("裂开一道缝", self.now))
        gap = r0 + 1
        cross = Cross(Square(0.36), stroke_color=C_RED, stroke_width=5).move_to(nl.pt(gap))
        gl = T(f"{gap} 谁也凑不出", 26, C_RED).next_to(nl.pt(gap), UP, buff=1.0)
        self.play(Create(cross), FadeIn(gl), nl.labs[gap].animate.set_color(C_RED), run_time=0.8)
        self.tail(defn, nl, bagm, nc2, bar, rl, init, arr, al, cond, sh2, cross, gl)

    # ---------------------------------------------------------------- 样例走一遍
    def walk_beat(self):
        self.beat("walk")
        tr = D.greedy_trace(D.X, D.COINS)
        nl = NumLine(D.X, -5.5, 0.55, 0.3, lab_scale=0.42)
        pal = VGroup(*[coin(v, 0.38) for v in D.COINS]).arrange(RIGHT, buff=0.55).move_to([-2.6, 2.6, 0])
        pal_l = T("面值", 22, C_GREY).next_to(pal, LEFT, buff=0.35)
        rule = VGroup(T("每步：", 24, C_GREY), T("面值", 24), MathTex(r"\le \mathrm{reach}+1", color=C_YELLOW).scale(0.75),
                      T("里挑最大的", 24)).arrange(RIGHT, buff=0.12).move_to([3.6, 2.6, 0])
        bag_l = T("带上", 22, C_GREY).move_to([-5.6, -1.6, 0])
        cnt = VGroup(T("枚数", 22, C_GREY), Integer(0, color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.15)
        cnt.move_to([5.2, -1.6, 0])
        self.play(Create(nl), FadeIn(pal), FadeIn(pal_l), FadeIn(rule), FadeIn(bag_l), FadeIn(cnt), run_time=1.0)
        bar = nl.bar(0, 0)

        def rlab(v):                                  # reach 读数固定在数轴左上，不跟着端点跑，免得和上限标记撞
            return MathTex(rf"\mathrm{{reach}} = {v}", color=COVER).scale(0.8).move_to([-5.8, 1.5, 0], aligned_edge=LEFT)

        def limit(v):
            tri = Triangle(color=C_YELLOW, fill_opacity=1, stroke_width=0).scale(0.1).rotate(PI).move_to(nl.pt(v, 0.25))
            return VGroup(tri, MathTex(str(v), color=C_YELLOW).scale(0.6).move_to(nl.pt(v, 0.58)))
        rl = rlab(0)
        self.play(FadeIn(bar), FadeIn(rl), run_time=0.4)
        lim = limit(1)
        bag = VGroup()
        keys = ["reach 是零", "上限是二", "上限是四", "上限是六", "上限十一"]
        for k, (r, usable, c, r2) in enumerate(tr):
            self.wait_until(self.cue_start(keys[k], self.now))
            pal_anims = []
            for v, cm in zip(D.COINS, pal):
                pal_anims += coin_alpha(cm, 1.0 if v in usable else 0.25)
            pick = pal[D.COINS.index(c)]
            ring = Circle(0.5, color=WHITE, stroke_width=4).move_to(pick)
            self.play(*([FadeIn(lim)] if k == 0 else [Indicate(lim, color=C_YELLOW, scale_factor=1.3)]), *pal_anims,
                      run_time=0.6)
            self.play(Create(ring), run_time=0.35)
            nc = coin(c, 0.36).move_to(pick)
            self.add(nc)
            lim_anim = FadeOut(lim) if r2 >= D.X else Transform(lim, limit(r2 + 1))
            self.play(nc.animate.move_to([-4.6 + 1.0 * k, -1.6, 0]), Transform(bar, nl.bar(0, r2)),
                      Transform(rl, rlab(r2)), lim_anim, FadeOut(ring), ChangeDecimalToValue(cnt[1], k + 1),
                      run_time=0.8)
            bag.add(nc)
        self.wait_until(self.cue_start("一共五枚", self.now))
        done = VGroup(T("够了：", 26, COVER), MathTex(r"\mathrm{reach} = 20 \ge X", color=COVER).scale(0.75))
        done.arrange(RIGHT, buff=0.1).move_to([2.2, -1.6, 0])
        self.play(FadeIn(done), Indicate(bag, color=C_YELLOW, scale_factor=1.08),
                  *[a for cm in pal for a in coin_alpha(cm, 1.0)], run_time=0.9)
        self.tail(nl, pal, pal_l, rule, bag_l, cnt, bar, rl, bag, done)

    # ---------------------------------------------------------------- 为什么挑最大的
    def why_beat(self):
        self.beat("why")
        g = [r for *_, r in D.greedy_trace(D.X, D.COINS)]
        gc = [c for _, _, c, _ in D.greedy_trace(D.X, D.COINS)]
        a = D.prefix_reach(D.ALT)
        rows = []
        for y, seq, col, name in ((1.7, gc, COVER, "贪心"), (-0.6, D.ALT, C_PURPLE, "另一种")):
            nl = NumLine(D.X, -4.0, 0.47, y, every=5, lab_scale=0.42)
            lab = T(name, 26, col).move_to([-5.7, y + 0.05, 0])
            cs = VGroup(*[coin(v, 0.24, col) for v in seq]).arrange(RIGHT, buff=0.1).move_to([-2.3, y + 0.85, 0])
            rows.append((nl, lab, cs, col))
        self.play(*[FadeIn(VGroup(nl, lab)) for nl, lab, _, _ in rows], run_time=0.8)
        self.wait_until(self.cue_start("一、一、二", self.now))
        self.play(FadeIn(rows[1][2]), run_time=0.6)
        self.wait_until(self.cue_start("逐枚和", self.now))
        self.play(FadeIn(rows[0][2]), run_time=0.6)
        bars = [None, None]
        vals = [None, None]
        ge = None
        t_end = self.cue_start("五枚只到", self.now + 6)
        step = max(0.5, min(1.4, (t_end - self.now) / len(g) - 0.15))
        for k in range(len(g)):
            anims = []
            for i, rr in enumerate((g, a)):
                nl, _, cs, col = rows[i]
                nb = nl.bar(0, rr[k], col, sw=10)
                nv = MathTex(str(rr[k]), color=col).scale(0.8).move_to([6.35, nl.y + 0.05, 0])
                anims.append(Indicate(cs[k], color=WHITE, scale_factor=1.3))
                if bars[i] is None:
                    bars[i], vals[i] = nb, nv
                    anims += [Create(nb), FadeIn(nv)]
                else:
                    anims += [Transform(bars[i], nb), Transform(vals[i], nv)]
            nge = T("上 ≥ 下", 22, WHITE).move_to([6.35, 0.55, 0])
            if ge is None:
                ge = nge
                anims.append(FadeIn(ge))
            self.play(*anims, run_time=step)
        self.wait_until(self.cue_start("五枚只到", self.now))
        nl = rows[1][0]
        miss = VGroup(Cross(Square(0.3), stroke_color=C_RED, stroke_width=5).move_to(nl.pt(D.X)),
                      T("还差一枚", 24, C_RED).move_to([nl.xof(D.X) - 0.3, nl.y + 0.55, 0]))
        hit = T("到了", 24, COVER).move_to([rows[0][0].xof(D.X) - 0.3, rows[0][0].y + 0.55, 0])
        self.play(FadeIn(miss), FadeIn(hit), run_time=0.8)
        self.wait_until(self.cue_start("所以贪心", self.now))
        concl = VGroup(T("每一步 reach 都不比别人小", 28, COVER), MathTex(r"\Rightarrow", color=WHITE).scale(0.8),
                       T("最早到达上限", 28, C_YELLOW)).arrange(RIGHT, buff=0.25).move_to([0, -2.35, 0])
        self.play(FadeIn(concl, shift=UP * 0.2), run_time=0.8)
        self.tail(*[VGroup(*r[:3]) for r in rows], *bars, *vals, ge, miss, hit, concl)

    # ---------------------------------------------------------------- 呼应二进制拆分 + 无解
    def echo_beat(self):
        self.beat("echo")
        parts = K.binary_split(13)
        reach = D.prefix_reach(parts)
        head = VGroup(T("背包那一支：", 26, C_GREY), T("13 拆成", 28),
                      *[coin(v, 0.3, C_BLUE) for v in parts]).arrange(RIGHT, buff=0.15).move_to([-1.0, 2.8, 0])
        nl = NumLine(13, -5.2, 0.62, 1.0, lab_scale=0.45)
        self.play(FadeIn(head), Create(nl), run_time=0.9)
        bar = None
        rl = None
        for k, (p, r) in enumerate(zip(parts, reach)):
            nb = nl.bar(0, r, C_BLUE)
            nrl = MathTex(rf"0 \sim {r}", color=C_BLUE).scale(0.65).move_to([nl.xof(r), 1.6, 0])
            ind = Indicate(head[2 + k], color=WHITE, scale_factor=1.3)
            if bar is None:
                bar, rl = nb, nrl
                self.play(Create(bar), FadeIn(rl), ind, run_time=0.5)
            else:
                self.play(Transform(bar, nb), Transform(rl, nrl), ind, run_time=0.5)
        self.wait_until(self.cue_start("最后一捆", self.now))
        cond = MathTex(rf"{parts[-1]} \le {sum(parts[:-1])} + 1", color=C_YELLOW).scale(0.85)
        ok = T("不断档", 26, C_YELLOW)
        VGroup(cond, ok).arrange(RIGHT, buff=0.3).move_to([3.0, -0.2, 0])
        self.play(FadeIn(cond), FadeIn(ok), Indicate(head[-1], color=C_YELLOW, scale_factor=1.3), run_time=0.9)
        self.wait_until(self.cue_start("那里拆数量", self.now))
        pair = VGroup(T("拆数量", 28, C_BLUE), MathTex(r"\longleftrightarrow").scale(0.8), T("挑面值", 28, COVER))
        pair.arrange(RIGHT, buff=0.3)
        inv = MathTex(r"\text{next} \le \mathrm{reach} + 1", color=C_YELLOW).scale(0.85)
        grp = VGroup(pair, inv).arrange(RIGHT, buff=0.7).move_to([0, -1.3, 0])
        self.play(FadeIn(grp, shift=UP * 0.2), run_time=0.9)
        self.wait_until(self.cue_start("无解只有", self.now))
        bad = VGroup(T("面值", 24, C_GREY), *[coin(v, 0.3) for v in D.NO_ONE[1]]).arrange(RIGHT, buff=0.18)
        bad.move_to([-3.4, -0.1, 0])
        stuck = VGroup(MathTex(r"\mathrm{reach}+1 = 1", color=C_RED).scale(0.75), T("没有一枚接得上", 24, C_RED),
                       MathTex(r"\Rightarrow\ -1", color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.25)
        stuck.move_to([2.0, -0.1, 0])
        self.play(FadeOut(VGroup(head, nl, bar, rl, cond, ok)), grp.animate.move_to([0, 1.5, 0]),
                  FadeIn(bad), run_time=0.8)
        self.wait_until(self.cue_start("第一步就卡住", self.now))
        self.play(FadeIn(stuck, shift=LEFT * 0.2), run_time=0.8)
        self.tail(grp, bad, stuck)

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string=D.W16_CODE + "\n", language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 30})
        if code.width > 8.4:
            code.scale_to_fit_width(8.4)
        code.move_to([-2.2, 0.45, 0])
        ln = code.code_lines
        src = T("W16 讲义第 5 节 T5", 20, C_GREY).next_to(code, UP, buff=0.15).align_to(code, LEFT)
        self.play(FadeIn(code, shift=UP * 0.2), FadeIn(src), run_time=0.9)

        def hl(lines, col):
            return VGroup(*[SurroundingRectangle(ln[k], color=col, buff=(0.08, 0.03), stroke_width=2) for k in lines])
        side_x = 4.65
        steps = [("面值排好序", [1], C_BLUE, "升序"), ("循环里取出", [4], C_YELLOW, "能接上的面值"),
                 ("一个都没有", [5, 6], C_RED, "没有：-1"), ("否则加上", [7], COVER, "加最大的，计数 +1"),
                 ("while 后面", [8, 9], C_PURPLE, "正常结束才打印")]
        box = note = None
        for key, lines, col, txt in steps:
            self.wait_until(self.cue_start(key, self.now))
            nbx = hl(lines, col)
            nn = T(txt, 26, col).move_to([side_x, ln[lines[0]].get_y(), 0])
            if box is None:
                box, note = nbx, nn
                self.play(Create(box), FadeIn(note), run_time=0.6)
            else:
                self.play(ReplacementTransform(box, nbx), ReplacementTransform(note, nn), run_time=0.6)
                box, note = nbx, nn
        self.wait_until(self.cue_start("循环次数就是答案", self.now))
        n = len(D.greedy_trace(D.X, D.COINS))
        loop = VGroup(T("样例循环", 26), MathTex(str(n), color=C_YELLOW).scale(0.9), T("次 = 答案", 26)).arrange(RIGHT, buff=0.12)
        loop.move_to([side_x, -1.55, 0])
        self.play(FadeOut(box), FadeOut(note), FadeIn(loop), Indicate(ln[3], color=C_YELLOW, scale_factor=1.03),
                  run_time=0.8)
        self.wait_until(self.cue_start("另一版", self.now))
        bis = VGroup(T("另一版：二分找这枚硬币", 22, C_GREY),
                     Text("idx = bisect.bisect_right(coins, target) - 1", font=MONO, font_size=20, color="#D8DCE6"))
        bis.arrange(DOWN, buff=0.15).move_to([0, -2.55, 0])
        self.play(FadeIn(bis, shift=UP * 0.15), run_time=0.8)
        self.tail(code, src, loop, bis)

    # ---------------------------------------------------------------- 暴力对拍
    def combo_grid(self, k, cols, y):
        combos = list(itertools.combinations_with_replacement(D.COINS, k))
        g = VGroup()
        for b in combos:
            ok = D.covers(b, D.X)
            col = COVER if ok else C_RED
            r = RoundedRectangle(corner_radius=0.06, width=1.78, height=0.44, stroke_color=col,
                                 stroke_width=2 if not ok else 4).set_fill(col, 0.25 if ok else 0.06)
            t = Text(" ".join(map(str, b)), font=MONO, font_size=17, color=WHITE if ok else C_GREY).move_to(r)
            g.add(VGroup(r, t))
        g.arrange_in_grid(cols=cols, buff=(0.08, 0.08)).move_to([0, y, 0])
        return g, combos

    def brute_beat(self):
        self.beat("brute")
        head = T("暴力：枚数从 1 往上，枚举全部组合，检查能否凑出 1..20", 26).move_to([0, 3.1, 0])
        self.play(FadeIn(head), run_time=0.7)
        self.wait_until(self.cue_start("四枚的", self.now))
        tot4, ok4 = D.brute_count(D.X, D.COINS, 4)
        g4, _ = self.combo_grid(4, 7, 0.75)
        l4 = VGroup(T("4 枚", 26), T(f"{tot4} 种", 26, C_GREY), T(f"能行 {ok4}", 26, C_RED)).arrange(RIGHT, buff=0.3)
        l4.next_to(g4, DOWN, buff=0.3)
        self.play(LaggedStart(*[FadeIn(c) for c in g4], lag_ratio=0.02), FadeIn(l4), run_time=1.4)
        self.wait_until(self.cue_start("五枚的", self.now))
        tot5, ok5 = D.brute_count(D.X, D.COINS, 5)
        g5, combos5 = self.combo_grid(5, 7, 0.6)
        l5 = VGroup(T("5 枚", 26), T(f"{tot5} 种", 26, C_GREY), T(f"能行 {ok5}", 26, COVER)).arrange(RIGHT, buff=0.3)
        l5.next_to(g5, DOWN, buff=0.25)
        self.play(FadeOut(g4), FadeOut(l4), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(c) for c in g5], lag_ratio=0.015), FadeIn(l5), run_time=1.4)
        win = next(i for i, b in enumerate(combos5) if D.covers(b, D.X))
        self.wait_until(self.cue_start("正是", self.now))
        self.play(Indicate(g5[win], color=C_YELLOW, scale_factor=1.25), run_time=1.0)
        self.wait_until(self.cue_start("一千组", self.now))
        n, same, none = D.duel()
        stat = VGroup(T("随机", 32, C_GREY), Integer(same, color=WHITE, group_with_commas=False).scale(1.1), T("组：贪心 = 暴力", 32, COVER),
                      T(f"（{none} 组无解）", 28, C_GREY)).arrange(RIGHT, buff=0.15).move_to([0, -0.6, 0])
        stat[1].set_value(0)                     # 先按四位数排版，再归零（左端固定），数上去不会压到右边的字
        self.play(FadeOut(VGroup(*[c for i, c in enumerate(g5) if i != win])), FadeOut(l5),
                  g5[win].animate.scale(2.2).move_to([0, 1.2, 0]), FadeIn(stat), run_time=0.8)
        self.play(ChangeDecimalToValue(stat[1], same), run_time=max(0.8, min(2.0, self.left() - 1.2)))
        self.tail(head, g5[win], stat)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        items = (("不变量", "能凑出 1 ~ reach", COVER), ("接得上", "面值 ≤ reach + 1", C_YELLOW),
                 ("贪心", "挑能接上的最大面值", C_BLUE))
        cards = VGroup()
        for name, tex, col in items:
            bx = RoundedRectangle(corner_radius=0.2, width=4.3, height=2.7, stroke_color=col, stroke_width=3)
            body = T(tex, 30, "#D8DCE6")
            txt = VGroup(T(name, 38, col), body).arrange(DOWN, buff=0.45).move_to(bx)
            cards.add(VGroup(bx, txt))
        cards.arrange(RIGHT, buff=0.3).move_to([0, 0.5, 0])
        keys = ["维护能连续", "下一枚面值", "每一步挑"]
        for k, c in enumerate(cards):
            self.wait_until(self.cue_start(keys[k], self.now))
            self.play(FadeIn(c, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 例题精讲 · OpenJudge M29896 · 2025-11-06 模拟机考", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
