"""二分答案：最小化最大值（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。每轮 lo/hi/mid/判定 与判定函数的贪心过程来自 bsearchdata
（test_bsearch.py 用暴力枚举对撞讲义两道例题，并检查判定单调与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bsearchdata as S  # noqa: E402
from cine import *  # noqa: E402,F403

L, M, ROCKS = S.RIVER
RX0, RX1 = -6.0, 6.0


def rx(v):
    return RX0 + (RX1 - RX0) * v / L


class River(VGroup):
    """河道 + 两岸 + 石头（带位置标签）。"""

    def __init__(self, y=0.4):
        super().__init__()
        self.y = y
        self.water = Rectangle(width=RX1 - RX0, height=0.9, stroke_width=0).set_fill(C_BLUE, 0.16).move_to([0, y, 0])
        self.banks = VGroup(*[Line([x, y - 0.6, 0], [x, y + 0.6, 0], stroke_color=C_GREY, stroke_width=5)
                              for x in (rx(0), rx(L))])
        self.stones = {}
        for s in sorted(ROCKS):
            c = Circle(0.2, stroke_color=WHITE, stroke_width=3).set_fill(C_GREY, 0.35).move_to([rx(s), y, 0])
            self.stones[s] = c
        self.labels = VGroup(*[MathTex(str(v), color=C_GREY).scale(0.55).move_to([rx(v), y - 0.75, 0])
                               for v in [0, *sorted(ROCKS), L]])
        self.add(self.water, self.banks, *self.stones.values(), self.labels)


class AnswerAxis(VGroup):
    """答案轴 0..L：每个整数一个小格，可着色。"""

    def __init__(self, y=-1.8, lo=0, hi=L, x0=-6.0, x1=6.0, every=5):
        super().__init__()
        self.lo, self.hi, self.y = lo, hi, y
        self.w = (x1 - x0) / (hi - lo + 1)
        self.x0 = x0
        self.cells = VGroup(*[Square(self.w * 0.86, stroke_color=C_GREY, stroke_width=1.5)
                              .move_to([self.x(v), y, 0]) for v in range(lo, hi + 1)])
        self.nums = VGroup(*[MathTex(str(v), color=C_GREY).scale(0.45).next_to(self.cells[v - lo], DOWN, buff=0.1)
                             for v in range(lo, hi + 1) if (v - lo) % every == 0 or v == hi])
        self.add(self.cells, self.nums)

    def x(self, v):
        return self.x0 + self.w * (v - self.lo + 0.5)

    def cell(self, v):
        return self.cells[v - self.lo]


class BSearchLesson(Lesson):
    def construct(self):
        for b in ("title", "pattern", "check", "binary", "plusone", "monthly", "template", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：河与石头
    def title_beat(self):
        self.beat("title")
        rv = River(y=0.0)
        self.play(FadeIn(rv.water), Create(rv.banks), FadeIn(rv.labels), run_time=1.0)
        self.play(LaggedStart(*[GrowFromCenter(s) for s in rv.stones.values()], lag_ratio=0.2), run_time=1.2)
        q = VGroup(T("最多移走 2 块", 28, C_YELLOW), T("让相邻最小距离尽量大", 28)).arrange(RIGHT, buff=0.4)
        q.move_to([0, 1.5, 0])
        self.wait_until(self.cue_start("最多移走", self.now))
        self.play(FadeIn(q, shift=DOWN * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("换个问法", self.now))
        title = T("二分答案", 72).move_to([0, 2.9, 0])
        sub = T("最小化最大值", 32, C_BLUE).move_to([0, -1.7, 0])
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(q, title, sub)), rv.animate.shift(UP * 1.2), run_time=0.6)
        rv.y += 1.2
        self.river = rv

    # ---------------------------------------------------------------- 题型：判定 + 单调
    def pattern_beat(self):
        self.beat("pattern")
        kinds = VGroup(T("最小的最大值", 28, C_YELLOW), T("最大的最小值", 28, C_YELLOW)).arrange(RIGHT, buff=1.0)
        kinds.move_to([0, 3.1, 0])
        self.play(FadeIn(kinds, shift=DOWN * 0.2), run_time=0.8)
        ax = AnswerAxis(y=-1.4)
        cap = T("答案轴：间距 gap", 22, C_GREY).next_to(ax.cells, UP, buff=0.25).align_to(ax.cells, LEFT)
        self.wait_until(self.cue_start("给你一个候选答案", self.now))
        self.play(FadeIn(ax), FadeIn(cap), run_time=0.8)
        flow = VGroup(T("候选答案", 24), MathTex(r"\to"), Text("feasible(x)", font=MONO, font_size=24, color=C_BLUE),
                      MathTex(r"\to"), T("行 / 不行", 24)).arrange(RIGHT, buff=0.25).move_to([0, -0.15, 0])
        self.play(FadeIn(flow, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("关键是单调", self.now))
        ok = [S.river_feasible_log(g)[0] for g in range(L + 1)]
        self.play(LaggedStart(*[ax.cell(g).animate.set_fill(C_GREEN if ok[g] else C_RED, 0.55)
                                for g in range(L + 1)], lag_ratio=0.05), run_time=2.2)
        edge = max(g for g in range(L + 1) if ok[g])
        xb = (ax.x(edge) + ax.x(edge + 1)) / 2
        line = DashedLine([xb, -2.3, 0], [xb, -0.95, 0], color=C_YELLOW, stroke_width=4)
        lab = T("分界线", 24, C_YELLOW).next_to(line, UP, buff=0.08).shift(RIGHT * 0.6)
        legend = VGroup(T("可行", 22, C_GREEN), T("不可行", 22, C_RED)).arrange(RIGHT, buff=0.5)
        legend.next_to(ax.cells, DOWN, buff=0.5)
        self.wait_until(self.cue_start("分界线", self.now))
        self.play(Create(line), FadeIn(lab), FadeIn(legend), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(kinds, ax, cap, flow, line, lab, legend)), run_time=0.6)

    # ---------------------------------------------------------------- 判定函数：gap = 4
    def check_beat(self):
        self.beat("check")
        rv = self.river
        gap = 4
        code = Code(code_string="for s in stones:\n    if s - last < gap:\n        removed += 1\n"
                                "        if removed > m:\n            return False\n    else:\n        last = s\n"
                                "return True\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 18})
        code.move_to([-3.6, -1.25, 0])
        head = VGroup(Text("feasible(gap = 4)", font=MONO, font_size=26, color=C_BLUE))
        head.move_to([2.6, -0.45, 0])
        rem = VGroup(Text("removed", font=MONO, font_size=24, color=C_GREY), Integer(0, color=C_RED).scale(0.9))
        rem.arrange(RIGHT, buff=0.3).move_to([2.6, -1.25, 0])
        self.play(FadeIn(code, shift=UP * 0.2), FadeIn(head), FadeIn(rem), run_time=0.9)
        ok, log = S.river_feasible_log(gap)
        y = rv.y
        last_mark = Triangle(color=C_YELLOW).set_fill(C_YELLOW, 1).scale(0.12).rotate(PI).move_to([rx(0), y + 0.7, 0])
        last_lab = Text("last", font=MONO, font_size=18, color=C_YELLOW).next_to(last_mark, UP, buff=0.05)
        self.play(FadeIn(last_mark), FadeIn(last_lab), run_time=0.4)
        keys = {2: "二离起点", 11: "十一保留", 14: "十四离十一", 17: "十七"}
        last, n_rm = 0, 0
        for s, act, d in log:
            if s in keys:
                self.wait_until(self.cue_start(keys[s], self.now))
            bridge = DoubleArrow([rx(last), y - 0.35, 0], [rx(s), y - 0.35, 0], buff=0, stroke_width=3,
                                 tip_length=0.12, color=C_RED if act == "rm" else C_GREEN)
            dl = MathTex(str(d), color=C_RED if act == "rm" else C_GREEN).scale(0.55).next_to(bridge, DOWN, buff=0.05)
            target = rv.stones.get(s)
            if act == "rm":
                n_rm += 1
                self.play(GrowFromCenter(bridge), FadeIn(dl), run_time=0.45)
                anims = [rem[1].animate.set_value(n_rm), FadeOut(bridge), FadeOut(dl)]
                if target is not None:
                    anims.append(target.animate.set_stroke(C_RED, 3).set_fill(C_RED, 0.15).set_opacity(0.35))
                self.play(*anims, run_time=0.55)
            else:
                self.play(GrowFromCenter(bridge), FadeIn(dl), run_time=0.4)
                anims = [last_mark.animate.move_to([rx(s), y + 0.7, 0]), FadeOut(bridge), FadeOut(dl)]
                if target is not None:
                    anims.append(target.animate.set_stroke(C_GREEN, 3).set_fill(C_GREEN, 0.4))
                self.play(*anims, last_lab.animate.move_to([rx(s), y + 0.95, 0]), run_time=0.45)
                last = s
        self.wait_until(self.cue_start("只移走两块", self.now))
        verdict = VGroup(MathTex(r"2\le m=2", color=C_GREEN).scale(0.8), T("可行", 28, C_GREEN),
                         MathTex(r"\checkmark", color=C_GREEN)).arrange(RIGHT, buff=0.25).move_to([2.6, -2.1, 0])
        self.play(FadeIn(verdict, shift=UP * 0.2), Indicate(rem, color=C_GREEN), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, head, rem, verdict, last_mark, last_lab, rv)), run_time=0.6)

    # ---------------------------------------------------------------- 二分五轮
    def binary_beat(self):
        self.beat("binary")
        ans, rounds = S.river_rounds()
        ax = AnswerAxis(y=0.3)
        code = Text("mid = (lo + hi + 1) // 2", font=MONO, font_size=26, color=C_BLUE).move_to([0, 2.9, 0])
        self.play(FadeIn(ax), FadeIn(code), run_time=0.8)
        band = Rectangle(width=ax.x(L) - ax.x(0) + ax.w, height=ax.w * 1.25, stroke_color=C_YELLOW, stroke_width=3)
        band.move_to([(ax.x(0) + ax.x(L)) / 2, ax.y, 0])
        lo_l = MathTex("lo", color=C_YELLOW).scale(0.6).next_to(band, UP, buff=0.1).align_to(band, LEFT)
        hi_l = MathTex("hi", color=C_YELLOW).scale(0.6).next_to(band, UP, buff=0.1).align_to(band, RIGHT)
        self.play(Create(band), FadeIn(lo_l), FadeIn(hi_l), run_time=0.7)
        ptr = Triangle(color=WHITE).set_fill(WHITE, 1).scale(0.14).rotate(PI)
        log = VGroup()
        cn = ["一", "二", "三", "四", "五"]
        for i, (lo, hi, mid, ok) in enumerate(rounds):
            self.wait_until(self.cue_start(f"第{cn[i]}轮", self.now))
            ptr_t = ptr.copy().move_to([ax.x(mid), ax.y + ax.w * 0.95, 0])
            col = C_GREEN if ok else C_RED
            row = VGroup(T(f"第 {i + 1} 轮", 22, C_GREY), MathTex(rf"\mathrm{{mid}}={mid}").scale(0.65),
                         MathTex(r"\checkmark" if ok else r"\times", color=col).scale(0.8))
            row.arrange(RIGHT, buff=0.3).move_to([-4.2, -1.1 - 0.42 * i, 0]).align_to([-5.6, 0, 0], LEFT)
            if i == 0:
                self.play(FadeIn(ptr_t), run_time=0.4)
                ptr = ptr_t
            else:
                self.play(ptr.animate.move_to(ptr_t), run_time=0.4)
            self.play(ax.cell(mid).animate.set_fill(col, 0.7), FadeIn(row, shift=LEFT * 0.2), run_time=0.5)
            nlo, nhi = (mid, hi) if ok else (lo, mid - 1)
            dead = [v for v in range(lo, hi + 1) if v < nlo or v > nhi]
            new_band = Rectangle(width=ax.x(nhi) - ax.x(nlo) + ax.w, height=ax.w * 1.25, stroke_color=C_YELLOW,
                                 stroke_width=3).move_to([(ax.x(nlo) + ax.x(nhi)) / 2, ax.y, 0])
            upd = MathTex(rf"\mathrm{{lo}}={nlo}" if ok else rf"\mathrm{{hi}}={nhi}", color=C_YELLOW).scale(0.6)
            upd.next_to(row, RIGHT, buff=0.35)
            self.play(Transform(band, new_band), *[ax.cell(v).animate.set_fill(C_GREY, 0.25) for v in dead if v != mid],
                      lo_l.animate.next_to(new_band, UP, buff=0.1).align_to(new_band, LEFT),
                      hi_l.animate.next_to(new_band, UP, buff=0.1).align_to(new_band, RIGHT).shift(RIGHT * 0.3 * (nlo == nhi)),
                      FadeIn(upd), run_time=0.6)
            log.add(row, upd)
        self.wait_until(self.cue_start("相遇", self.now))
        res = VGroup(T("答案", 30), MathTex(str(ans), color=C_YELLOW).scale(1.3)).arrange(RIGHT, buff=0.3)
        res.move_to([3.4, -1.9, 0])
        self.play(FadeIn(res, shift=UP * 0.2), Flash(ax.cell(ans), color=C_YELLOW, flash_radius=0.4), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, code, band, lo_l, hi_l, ptr, log, res)), run_time=0.6)

    # ---------------------------------------------------------------- 加一不能少
    def plusone_beat(self):
        self.beat("plusone")
        head = Text("mid = (lo + hi + 1) // 2", font=MONO, font_size=30, color=C_BLUE).move_to([0, 3.0, 0])
        self.play(FadeIn(head), run_time=0.6)
        hl = SurroundingRectangle(head[10:12], color=C_YELLOW, buff=0.06)
        self.play(Create(hl), run_time=0.5)
        self.wait_until(self.cue_start("如果用下取整", self.now))
        left_t = VGroup(Text("(lo + hi) // 2", font=MONO, font_size=26, color=C_RED),
                        MathTex(r"\times", color=C_RED)).arrange(RIGHT, buff=0.3).move_to([-3.4, 1.8, 0])
        right_t = VGroup(Text("(lo + hi + 1) // 2", font=MONO, font_size=26, color=C_GREEN),
                         MathTex(r"\checkmark", color=C_GREEN)).arrange(RIGHT, buff=0.3).move_to([3.4, 1.8, 0])
        self.play(FadeIn(left_t), run_time=0.5)

        def pair(cx, lo, hi, mid=None):
            cells = VGroup()
            for v in (lo, hi) if lo != hi else (lo,):
                sq = Square(0.8, stroke_color=C_YELLOW, stroke_width=3).set_fill(C_GREEN if v <= 4 else C_RED, 0.35)
                cells.add(VGroup(sq, MathTex(str(v)).scale(0.8).move_to(sq)))
            cells.arrange(RIGHT, buff=0.1).move_to([cx, 0.5, 0])
            return cells
        trail = S.floor_mid_loop(4, 5)
        lp = pair(-3.4, 4, 5)
        ptr = Triangle(color=WHITE).set_fill(WHITE, 1).scale(0.14).rotate(PI).next_to(lp[0], UP, buff=0.1)
        state = MathTex(r"\mathrm{lo}=4,\ \mathrm{hi}=5,\ \mathrm{mid}=4", color=C_GREY).scale(0.6).move_to([-3.4, -0.5, 0])
        self.play(FadeIn(lp), FadeIn(ptr), FadeIn(state), run_time=0.6)
        loop = Arc(radius=0.55, start_angle=PI / 2, angle=1.7 * PI, color=C_RED, stroke_width=5).move_to([-3.4, -1.55, 0])
        loop.add_tip(tip_length=0.18)
        cnt = VGroup(T("第", 22, C_GREY), Integer(1, color=C_RED).scale(0.7), T("轮", 22, C_GREY)).arrange(RIGHT, buff=0.1)
        cnt.next_to(loop, RIGHT, buff=0.3)
        self.play(Create(loop), FadeIn(cnt), run_time=0.6)
        for k, (lo, hi, mid, ok) in enumerate(trail[1:], 2):
            self.play(Rotate(loop, angle=-2 * PI, about_point=loop.get_center()), Indicate(lp[0], color=C_GREEN),
                      cnt[1].animate.set_value(k), run_time=0.7)
        dl = T("死循环", 30, C_RED).next_to(loop, DOWN, buff=0.2)
        self.play(FadeIn(dl, scale=1.4), run_time=0.5)
        rp = pair(3.4, 4, 5)
        rptr = ptr.copy().next_to(rp[1], UP, buff=0.1)
        rstate = MathTex(r"\mathrm{mid}=5\ \times \Rightarrow \mathrm{hi}=4", color=C_GREY).scale(0.6).move_to([3.4, -0.5, 0])
        self.play(FadeIn(right_t), FadeIn(rp), FadeIn(rptr), run_time=0.6)
        self.play(FadeIn(rstate), run_time=0.5)
        rdone = pair(3.4, 4, 4)
        endt = T("区间收缩，结束", 26, C_GREEN).move_to([3.4, -1.55, 0])
        self.play(Transform(rp, rdone), FadeOut(rptr), FadeIn(endt), run_time=0.8)
        self.wait_until(self.cue_start("记住一句话", self.now))
        rule = VGroup(VGroup(Text("lo = mid", font=MONO, font_size=26, color=C_YELLOW), T("→ 上取整", 26)).arrange(RIGHT, buff=0.3),
                      VGroup(Text("hi = mid", font=MONO, font_size=26, color=C_YELLOW), T("→ 下取整", 26)).arrange(RIGHT, buff=0.3))
        rule.arrange(RIGHT, buff=1.2).move_to([0, -2.55, 0])
        self.play(FadeIn(rule[0], shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(rule[1], shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, hl, left_t, right_t, lp, ptr, state, loop, cnt, dl, rp, rstate, endt, rule)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 月度开销
    def monthly_beat(self):
        self.beat("monthly")
        costs = S.COSTS
        scale = 2.3 / max(costs)
        bars = VGroup()
        for i, c in enumerate(costs):
            b = Rectangle(width=0.62, height=c * scale, stroke_width=0).set_fill(C_BLUE, 0.6)
            b.move_to([-5.9 + 0.75 * i, 0.0, 0], aligned_edge=DOWN)
            bars.add(VGroup(b, MathTex(str(c)).scale(0.42).next_to(b, UP, buff=0.06)))
        head = T("7 天开销，最多分 5 段", 26).move_to([-3.65, 3.0, 0])
        self.play(FadeIn(head), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.12), run_time=1.4)
        self.wait_until(self.cue_start("判定函数", self.now))
        limit = 500
        groups = S.monthly_groups(limit)
        cols = [C_YELLOW, C_GREEN, C_RED, C_PURPLE, C_TEAL]
        k, braces = 0, VGroup()
        for gi, g in enumerate(groups):
            seg = VGroup(*[bars[k + t] for t in range(len(g))])
            k += len(g)
            br = Line(seg.get_corner(DL) + DOWN * 0.15, seg.get_corner(DR) + DOWN * 0.15, color=cols[gi], stroke_width=5)
            braces.add(br, MathTex(str(sum(g)), color=cols[gi]).scale(0.45).next_to(br, DOWN, buff=0.08))
        lim_cap = MathTex(r"\mathrm{limit}=500", color=C_YELLOW).scale(0.6).move_to([-3.65, -1.05, 0])
        self.play(FadeIn(lim_cap), LaggedStart(*[FadeIn(b) for b in braces], lag_ratio=0.15), run_time=1.6)
        five = T(f"{len(groups)} 段 ≤ 5", 22, C_GREEN).next_to(lim_cap, DOWN, buff=0.12)
        self.play(FadeIn(five), run_time=0.4)
        ans, rounds = S.monthly_rounds()
        lo0, hi0 = rounds[0][0], rounds[0][1]
        X0, X1, Y = 0.4, 6.4, 0.9
        def px(v):
            return X0 + (X1 - X0) * (v - lo0) / (hi0 - lo0)
        axis = NumberLine(x_range=[lo0, hi0, 1401], length=X1 - X0, include_numbers=False, color=C_GREY).move_to([(X0 + X1) / 2, Y, 0])
        ends = VGroup(MathTex(str(lo0), color=C_GREY).scale(0.5).next_to(axis.get_left(), DOWN, buff=0.2),
                      MathTex(str(hi0), color=C_GREY).scale(0.5).next_to(axis.get_right(), DOWN, buff=0.2))
        cap = VGroup(T("下界：最大单日", 20, C_GREY), T("上界：全部之和", 20, C_GREY))
        cap[0].next_to(ends[0], DOWN, buff=0.1)
        cap[1].next_to(ends[1], DOWN, buff=0.1).align_to(ends[1], RIGHT)
        self.wait_until(self.cue_start("下界", self.now))
        self.play(Create(axis), FadeIn(ends), FadeIn(cap), run_time=1.0)
        band = Line([px(lo0), Y, 0], [px(hi0), Y, 0], color=C_YELLOW, stroke_width=10)
        code = Text("mid = (lo + hi) // 2", font=MONO, font_size=24, color=C_BLUE).move_to([3.4, 2.4, 0])
        self.wait_until(self.cue_start("下取整", self.now) - 0.5)
        self.play(FadeIn(band), FadeIn(code), run_time=0.5)
        rcnt = VGroup(T("轮数", 22, C_GREY), Integer(0, color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.2)
        rcnt.move_to([3.4, -0.4, 0])
        self.play(FadeIn(rcnt), run_time=0.3)
        t_end = self.cue_start("十一轮之后", self.now + 4)
        step = max(0.25, min(0.6, (t_end - self.now) / len(rounds)))
        ticks = VGroup()
        for i, (lo, hi, mid, ok) in enumerate(rounds):
            nlo, nhi = (lo, mid) if ok else (mid + 1, hi)
            tick = Line([px(mid), Y - 0.2, 0], [px(mid), Y + 0.2, 0], color=C_GREEN if ok else C_RED, stroke_width=3)
            self.play(FadeIn(tick), band.animate.put_start_and_end_on([px(nlo), Y, 0], [px(nhi) + 1e-3, Y, 0]),
                      rcnt[1].animate.set_value(i + 1), run_time=step)
            ticks.add(tick)
        res = VGroup(T("答案", 28), MathTex(str(ans), color=C_YELLOW).scale(1.2)).arrange(RIGHT, buff=0.3)
        res.move_to([3.4, -1.3, 0])
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, bars, braces, lim_cap, five, axis, ends, cap, band, code, rcnt, res, ticks)), run_time=0.6)

    # ---------------------------------------------------------------- 三步模板
    def template_beat(self):
        self.beat("template")
        steps = [("1", "确定答案的取值范围", Text("[lo, hi]", font=MONO, font_size=24, color=C_GREY)),
                 ("2", "写判定函数，确认单调", Text("feasible(x)", font=MONO, font_size=24, color=C_GREY)),
                 ("3", "二分", VGroup(T("求最小：hi = mid，下取整", 20, C_GREY), T("求最大：lo = mid，上取整", 20, C_GREY))
                  .arrange(DOWN, aligned_edge=LEFT, buff=0.12))]
        cards = VGroup()
        for num, head, body in steps:
            box = RoundedRectangle(corner_radius=0.18, width=4.1, height=2.2, stroke_color=C_BLUE, stroke_width=3)
            box.set_fill(C_BLUE, 0.06)
            content = VGroup(T(head, 26, C_YELLOW), body).arrange(DOWN, buff=0.3)
            badge = VGroup(Circle(0.26, color=C_BLUE).set_fill(C_BLUE, 0.3), MathTex(num).scale(0.7))
            card = VGroup(box, content.move_to(box), badge.move_to(box.get_corner(UL) + np.array([0.05, -0.05, 0])))
            cards.add(card)
        cards.arrange(RIGHT, buff=0.3).move_to([0, 0.4, 0])
        keys = ["第一", "第二", "第三"]
        for c, k in zip(cards, keys):
            self.wait_until(self.cue_start(k, self.now))
            self.play(FadeIn(c, shift=UP * 0.3), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(cards), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        a = VGroup(T("求解", 40, C_GREY), MathTex(r"\Rightarrow").scale(1.2), T("验证", 40, C_YELLOW)).arrange(RIGHT, buff=0.4)
        a.move_to([0, 1.0, 0])
        self.play(FadeIn(a, shift=UP * 0.2), run_time=1.0)
        b = T("会判断，就会求最优", 34, C_BLUE).move_to([0, -0.2, 0])
        self.wait_until(self.cue_start("会判断", self.now))
        self.play(Write(b), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 12 周 二分答案 P23–P26 · OpenJudge 08210 · 04135", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
