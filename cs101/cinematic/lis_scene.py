"""最长上升子序列：两种写法（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。dp 逐格来源、tails 逐步落牌、回溯与变形题数字都来自 lisdata
（test_lis.py 对撞讲义输出、暴力枚举子序列、线性扫描的耐心排序与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lisdata as L  # noqa: E402
from cine import *  # noqa: E402,F403

CARD_W, CARD_H, CARD_DY = 1.2, 0.8, 0.6        # 牌的宽高与同摞叠放的错位


def num(v, scale=0.75, color=WHITE):
    return MathTex(str(v), color=color).scale(scale)


def make_row(vals, y, cell=0.9, sp=1.15, scale=0.75, x=0.0):
    """一排方格：返回 VGroup(格子 VGroup, 数字 VGroup)。格子无填充（LaggedStart 不会盖字）。"""
    n = len(vals)
    boxes = VGroup(*[Square(cell, stroke_color=C_GREY, stroke_width=2)
                     .move_to([x + (k - (n - 1) / 2) * sp, y, 0]) for k in range(n)])
    nums = VGroup(*[num(v, scale).move_to(b) for v, b in zip(vals, boxes)])
    return VGroup(boxes, nums)


def card(v, color=C_BLUE, w=CARD_W, h=CARD_H, scale=0.75):
    """一张牌：不透明底色，叠放时盖住下面那张的上沿；数字在中间、不被上面那张盖到。"""
    r = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=3)
    r.set_fill(BG, 1)
    return VGroup(r, num(v, scale, WHITE))


def arc(p, q, color, angle=-PI / 3, width=3, tip=True):
    a = ArcBetweenPoints(p, q, angle=angle, color=color, stroke_width=width)
    if tip:
        a.add_tip(tip_length=0.16, tip_width=0.14)
    return a


class LISLesson(Lesson):
    def construct(self):
        for b in ("title", "state", "fill", "cost", "piles", "bisect", "trap", "strict", "homework", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def cue_at(self, key, default=None):
        """key 在句中的大致时刻：句起点 + 句长按字数比例（同一句里先后两件事时用）。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        row = make_row(L.A, 0.0)
        self.play(LaggedStart(*[FadeIn(VGroup(b, t), shift=DOWN * 0.2) for b, t in zip(*row)], lag_ratio=0.12),
                  run_time=1.6)
        self.wait_until(self.cue_start("答案是四个", self.now))
        pick = L.lis_back()
        links = VGroup(*[arc(row[0][a].get_top() + UP * 0.05, row[0][b].get_top() + UP * 0.05, C_YELLOW)
                         for a, b in zip(pick, pick[1:])])
        self.play(*[row[0][k].animate.set_stroke(C_YELLOW, 4) for k in pick],
                  *[row[1][k].animate.set_color(C_YELLOW) for k in pick],
                  LaggedStart(*[Create(x) for x in links], lag_ratio=0.3), run_time=1.6)
        self.wait_until(self.cue_start("这就是", self.now))
        title = T("最长上升子序列", 56).move_to([0, 2.6, 0])
        sub = T("两种写法：O(n²) 与 O(n log n)", 30, C_BLUE).next_to(title, DOWN, buff=0.22)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.8))
        self.play(FadeOut(VGroup(title, sub, links)),
                  *[row[0][k].animate.set_stroke(C_GREY, 2) for k in pick],
                  *[row[1][k].animate.set_color(WHITE) for k in pick], run_time=0.5)
        self.play(row.animate.move_to([0, 1.6, 0]), run_time=0.5)
        self.row = row

    # ---------------------------------------------------------------- 状态与转移
    def state_beat(self):
        self.beat("state")
        row = self.row
        la = T("a", 30, C_GREY).next_to(row[0][0], LEFT, buff=0.35)
        idx = VGroup(*[T(str(k), 18, C_GREY).next_to(b, UP, buff=0.1) for k, b in enumerate(row[0])])
        defn = VGroup(MathTex(r"dp[i]", color=C_YELLOW).scale(0.8), T("= 以 a[i] 结尾的最长上升子序列长度", 26))
        defn.arrange(RIGHT, buff=0.2).move_to([0, 3.05, 0])
        self.play(FadeIn(la), FadeIn(idx), Write(defn), run_time=1.2)
        self.wait_until(self.cue_start("初值", self.now))
        dprow = make_row([1] * len(L.A), 0.45)
        for t in dprow[1]:
            t.set_color(C_GREY)
        ld = T("dp", 30, C_YELLOW).next_to(dprow[0][0], LEFT, buff=0.25)
        self.play(FadeIn(dprow[0]), FadeIn(ld), LaggedStart(*[FadeIn(t) for t in dprow[1]], lag_ratio=0.08),
                  run_time=1.0)
        self.wait_until(self.cue_start("转移", self.now))
        eq = MathTex(r"dp[i]=\max_{j<i,\ a[j]<a[i]} dp[j]+1", color=WHITE).scale(0.8).move_to([0, -1.75, 0])
        self.play(Write(eq), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.2))
        self.idx, self.la, self.defn, self.dprow, self.ld, self.eq = idx, la, defn, dprow, ld, eq

    # ---------------------------------------------------------------- 逐格填 dp
    def fill_beat(self):
        self.beat("fill")
        row, dprow = self.row, self.dprow
        dp, steps = L.n2_trace()
        keys = ("一前面", "七接在", "三也只能", "五接在", "九前面", "四接在", "八接在")
        ring = Square(0.9 * 1.12, stroke_color=WHITE, stroke_width=5).move_to(row[0][0]).set_opacity(0)
        self.add(ring)
        for i, ((cand, best), key) in enumerate(zip(steps, keys)):
            self.wait_until(self.cue_start(key, self.now))
            self.play(ring.animate.move_to(row[0][i]).set_stroke(opacity=1),
                      *[row[1][j].animate.set_color(C_TEAL) for j in cand], run_time=0.4)
            arcs = VGroup(*[arc(dprow[0][j].get_bottom() + DOWN * 0.05, dprow[0][i].get_bottom() + DOWN * 0.05,
                                C_YELLOW if j == best else C_GREY, angle=PI / 3,
                                width=4 if j == best else 2, tip=j == best) for j in cand])
            new = num(dp[i], 0.75, C_YELLOW).move_to(dprow[0][i])
            anims = [ReplacementTransform(dprow[1][i], new), dprow[0][i].animate.set_stroke(C_YELLOW, 3)]
            if cand:
                anims += [Create(arcs), Indicate(dprow[1][best], color=C_YELLOW, scale_factor=1.3)]
            self.play(*anims, run_time=0.8)
            dprow[1].submobjects[i] = new
            self.play(FadeOut(arcs), *[row[1][j].animate.set_color(WHITE) for j in cand],
                      dprow[0][i].animate.set_stroke(C_GREY, 2), new.animate.set_color(WHITE), run_time=0.3)
        self.wait_until(self.cue_start("答案是", self.now))
        top = max(dp)
        hi = [k for k, v in enumerate(dp) if v == top]
        ans = VGroup(MathTex(r"\max(dp)=", color=WHITE).scale(0.8), num(top, 0.9, C_YELLOW)).arrange(RIGHT, buff=0.15)
        ans.move_to([0, -2.6, 0])
        self.play(FadeOut(ring), *[dprow[1][k].animate.set_color(C_YELLOW) for k in hi],
                  *[Circumscribe(dprow[0][k], color=C_YELLOW) for k in hi], FadeIn(ans), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(self.defn, self.eq, ans, self.idx)), run_time=0.6)
        self.dp_ans = ans

    # ---------------------------------------------------------------- 慢在哪，换个问法
    def cost_beat(self):
        self.beat("cost")
        row, dprow = self.row, self.dprow
        big = VGroup(T("两层循环", 28), MathTex(r"O(n^2)", color=C_RED).scale(1.0)).arrange(RIGHT, buff=0.3)
        big.move_to([0, -0.9, 0])
        self.play(FadeIn(big, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("到十万", self.now))
        c = L.compares(L.BIG_N)
        cnt = VGroup(MathTex(rf"n={L.BIG_N:,}".replace(",", r"\,"), color=WHITE).scale(0.75),
                     MathTex(r"\to").scale(0.75),
                     MathTex(rf"\frac{{n(n-1)}}{{2}}\approx {c / 1e8:.0f}", color=C_RED).scale(0.75),
                     T("亿次比较", 26, C_RED)).arrange(RIGHT, buff=0.22).scale(1.15).move_to([0, -1.9, 0])
        self.play(FadeIn(cnt, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("换个问法", self.now))
        self.play(FadeOut(VGroup(big, cnt, dprow, self.ld)), row.animate.scale(0.8).move_to([0, 2.7, 0]),
                  self.la.animate.scale(0.8).move_to([-3.55, 2.7, 0]), run_time=0.8)
        q = VGroup(T("长度为 1、2、3 … 的上升子序列", 30), T("结尾最小能是多少？", 30, C_YELLOW))
        q.arrange(DOWN, buff=0.18).move_to([0, 1.2, 0])
        self.play(FadeIn(q, shift=UP * 0.2), run_time=0.9)
        self.wait_until(self.cue_start("结尾越小", self.now) - 2.0)
        # 两条长度 2 的序列：1 7 与 1 3；来了 5，只有结尾小的那条接得上
        ch1 = VGroup(card(1, C_GREY), card(7, C_GREY)).arrange(RIGHT, buff=0.35).move_to([-2.4, -0.5, 0])
        ch2 = VGroup(card(1, C_GREY), card(3, C_TEAL)).arrange(RIGHT, buff=0.35).move_to([-2.4, -1.8, 0])
        five = card(5, C_YELLOW).move_to([2.6, -1.15, 0])
        self.play(FadeIn(ch1), FadeIn(ch2), FadeIn(five), run_time=0.6)
        no = arc(five.get_left() + LEFT * 0.1, ch1[1].get_right() + RIGHT * 0.1, C_RED, angle=PI / 6)
        yes = arc(ch2[1].get_right() + RIGHT * 0.1, five.get_left() + LEFT * 0.1, C_GREEN, angle=PI / 6)
        lab_no = T("7 > 5，接不上", 22, C_RED).next_to(no, UP, buff=0.12)
        lab_yes = T("3 < 5，接得上", 22, C_GREEN).next_to(yes, DOWN, buff=0.12)
        self.play(Create(no), FadeIn(lab_no), run_time=0.7)
        self.play(Create(yes), FadeIn(lab_yes), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(q, ch1, ch2, five, no, yes, lab_no, lab_yes)), run_time=0.6)

    # ---------------------------------------------------------------- 摞牌
    def pile_pos(self, k, h, x0=-5.0, sp=1.55, y0=-0.5):
        return np.array([x0 + sp * k, y0 + CARD_DY * h, 0])

    def piles_beat(self):
        self.beat("piles")
        row = self.row
        steps = L.tails_trace()
        n_p = len(steps[-1][3])
        base = VGroup(*[Line(self.pile_pos(k, 0) + DOWN * 0.5 + LEFT * 0.62, self.pile_pos(k, 0) + DOWN * 0.5 + RIGHT * 0.62,
                             color=C_GREY, stroke_width=2) for k in range(n_p)])
        labs = VGroup(*[T(f"长度 {k + 1}", 22, C_GREY).next_to(base[k], DOWN, buff=0.15) for k in range(n_p)])
        self.play(Create(base[0]), Create(base[1]), FadeIn(labs[0]), FadeIn(labs[1]), run_time=0.8)
        self.wait_until(self.cue_start("规则", self.now))
        rule = VGroup(T("新数 v 放到第一个", 26), T("牌顶 ≥ v 的那一摞", 26, C_YELLOW),
                      T("牌顶都比 v 小 → 新开一摞", 26, C_TEAL)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        rule.move_to([3.7, 0.9, 0])
        self.play(FadeIn(rule, shift=LEFT * 0.2), run_time=0.9)
        tl = T("tails =", 26, C_GREY).move_to([2.35, -1.2, 0])
        self.play(FadeIn(tl), run_time=0.3)
        cards = [[] for _ in range(n_p)]
        tv = None
        keys = ("一开第一摞", "七新开", "三压在七", "五开第三摞", "九开第四摞", "四压在五", "八压在九")
        for i, ((v, pos, new, tails, _), key) in enumerate(zip(steps, keys)):
            self.wait_until(self.cue_at(key, self.now))
            c = card(v, C_YELLOW).move_to(row[0][i])
            target = self.pile_pos(pos, len(cards[pos]))
            anims = [c.animate.move_to(target), row[1][i].animate.set_color(C_YELLOW)]
            if new and pos >= 2:
                anims += [Create(base[pos]), FadeIn(labs[pos])]
            if cards[pos]:                                     # 被压住的旧牌顶变暗
                old = cards[pos][-1]
                anims += [old[0].animate.set_stroke(C_GREY, 2), old[1].animate.set_color(C_GREY)]
            if i:
                anims.append(row[1][i - 1].animate.set_color(WHITE))
            ntv = Text(str(tails).replace(" ", ""), font=MONO, font_size=26, color=WHITE)
            ntv.next_to(tl, RIGHT, buff=0.2)
            anims.append(FadeIn(ntv) if tv is None else Transform(tv, ntv))
            self.play(*anims, run_time=0.7)
            self.play(c[0].animate.set_stroke(C_BLUE, 3), run_time=0.15)
            if tv is None:
                tv = ntv
            cards[pos].append(c)
        self.play(row[1][len(steps) - 1].animate.set_color(WHITE), run_time=0.2)
        self.wait_until(self.cue_start("一共四摞", self.now))
        br = Brace(VGroup(labs), DOWN, buff=0.1, color=C_YELLOW)
        bl = T(f"{n_p} 摞 = 最长上升子序列长度 {n_p}", 24, C_YELLOW).next_to(br, DOWN, buff=0.1)
        self.play(GrowFromCenter(br), FadeIn(bl), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(br, bl, rule)), run_time=0.6)
        self.cards, self.base, self.labs, self.tl, self.tv = cards, base, labs, tl, tv

    # ---------------------------------------------------------------- 二分：bisect_left
    def bisect_beat(self):
        self.beat("bisect")
        tops = VGroup(*[p[-1] for p in self.cards])
        inc = Arrow([tops[0].get_left()[0], 0.6, 0], [tops[-1].get_right()[0], 0.6, 0],
                    color=C_TEAL, stroke_width=4, buff=0)
        inc_l = T("牌顶从左到右递增", 24, C_TEAL).next_to(inc, UP, buff=0.12)
        self.play(GrowArrow(inc), FadeIn(inc_l), *[Indicate(t[1], color=C_TEAL) for t in tops], run_time=1.0)
        code = Code(code_string="def lis_nlogn(a):\n    tails = []\n    for v in a:\n"
                                "        pos = bisect.bisect_left(tails, v)\n        if pos == len(tails):\n"
                                "            tails.append(v)\n        else:\n            tails[pos] = v\n"
                                "    return len(tails)\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 24})
        if code.width > 6.2:
            code.scale_to_fit_width(6.2)
        code.move_to([3.6, 0.15, 0])
        self.play(FadeOut(VGroup(self.tl, self.tv)), FadeIn(code, shift=UP * 0.2), run_time=0.8)
        ln = code.code_lines

        def hl(lines, col):
            return VGroup(*[SurroundingRectangle(ln[k], color=col, buff=(0.08, 0.03), stroke_width=2) for k in lines])
        self.wait_until(self.cue_start("bisect_left", self.now))
        h1 = hl([3], C_YELLOW)
        self.play(Create(h1), run_time=0.6)
        self.wait_until(self.cue_start("位置等于长度", self.now))
        h2 = hl([4, 5], C_TEAL)
        self.play(ReplacementTransform(h1, h2), run_time=0.6)
        self.wait_until(self.cue_start("否则", self.now))
        h3 = hl([7], C_BLUE)
        self.play(ReplacementTransform(h2, h3), run_time=0.6)
        self.wait_until(self.cue_start("每个数", self.now))
        cx = VGroup(T("每个数二分一次", 24), MathTex(r"\Rightarrow\ O(n\log n)", color=C_YELLOW).scale(0.85))
        cx.arrange(RIGHT, buff=0.25).next_to(code, DOWN, buff=0.35)
        self.play(FadeOut(h3), FadeIn(cx, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, cx, inc, inc_l)), run_time=0.6)

    # ---------------------------------------------------------------- 易错点：tails 不是答案序列
    def trap_beat(self):
        self.beat("trap")
        row, cards = self.row, self.cards
        k, tails = L.trap_step()
        steps = L.tails_trace()
        # 回到处理完四的那一刻：把之后落下的牌退回去
        undo = []
        for v, pos, new, _, _ in steps[k + 1:]:
            c = cards[pos].pop()
            undo.append(FadeOut(c, shift=UP * 0.4))
            if cards[pos]:
                old = cards[pos][-1]
                undo += [old[0].animate.set_stroke(C_BLUE, 3), old[1].animate.set_color(WHITE)]
        self.play(*undo, row.animate.move_to([0, 2.3, 0]), self.la.animate.move_to([-3.55, 2.3, 0]), run_time=0.8)
        self.wait_until(self.cue_start("回到处理完", self.now))
        mark = SurroundingRectangle(row[0][k], color=WHITE, buff=0.06, stroke_width=4)
        self.play(Create(mark), *[cards[p][-1][0].animate.set_stroke(C_RED, 4) for p in range(len(tails))],
                  run_time=0.7)
        # tails 的四个数在原数组里的位置（处理到第 k 个为止，取最后一次出现）
        where = [max(i for i in range(k + 1) if L.A[i] == v) for v in tails]
        self.wait_until(self.cue_start("可四在", self.now))
        bad = VGroup()
        for a, b in zip(where, where[1:]):
            back = b < a
            p, q = row[0][a].get_top() + UP * 0.05, row[0][b].get_top() + UP * 0.05
            bad.add(arc(p, q, C_RED, angle=PI / 2.2 if back else -PI / 3, width=5 if back else 3))
        cross = T("往回走了", 22, C_RED).next_to(row[0][k], UR, buff=0.08)
        self.play(*[row[1][i].animate.set_color(C_RED) for i in where], Create(bad), run_time=1.0)
        self.play(FadeIn(cross), run_time=0.4)
        self.wait_until(self.cue_start("真正的是", self.now))
        good_idx = L.lis_back()
        p1 = VGroup(T("tails", 26, C_RED), *[card(v, C_RED, 0.8, 0.6, 0.65) for v in tails], T("✗", 30, C_RED))
        p2 = VGroup(T("真正的", 26, C_YELLOW), *[card(L.A[i], C_YELLOW, 0.8, 0.6, 0.65) for i in good_idx],
                    T("✓", 30, C_GREEN))
        for p in (p1, p2):
            p.arrange(RIGHT, buff=0.22)
        VGroup(p1, p2).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([3.7, 0.3, 0])
        self.play(FadeIn(p1, shift=LEFT * 0.2), run_time=0.5)
        self.play(FadeIn(p2, shift=LEFT * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("要输出序列", self.now))
        # 回到 dp：在原数组下面标出 dp，从最大值倒着找
        dp, _ = L.n2_trace()
        self.play(FadeOut(VGroup(*[c for p in cards for c in p], self.base, self.labs, bad, cross, mark)),
                  *[row[1][i].animate.set_color(WHITE) for i in where],
                  VGroup(p1, p2).animate.scale(1.25).move_to([0, -1.0, 0]), run_time=0.6)
        dpl = VGroup(*[T(f"dp {v}", 20, C_GREY).next_to(row[0][i], DOWN, buff=0.12) for i, v in enumerate(dp)])
        self.play(FadeIn(dpl), run_time=0.5)
        chain = good_idx[::-1]
        step = max(0.35, min(0.7, (self.left() - 0.8) / len(chain)))
        prev = None
        links = VGroup()
        for i in chain:
            anims = [row[1][i].animate.set_color(C_YELLOW), dpl[i].animate.set_color(C_YELLOW),
                     row[0][i].animate.set_stroke(C_YELLOW, 3)]
            if prev is not None:
                lk = arc(dpl[prev].get_bottom() + DOWN * 0.05, dpl[i].get_bottom() + DOWN * 0.05, C_YELLOW,
                         angle=-PI / 1.6)
                links.add(lk)
                anims.append(Create(lk))
            self.play(*anims, run_time=step)
            prev = i
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(p1, p2, dpl, links, row, self.la)), run_time=0.6)

    # ---------------------------------------------------------------- 严格上升与非降
    def strict_beat(self):
        self.beat("strict")
        a = L.EQUAL
        inp = VGroup(T("输入", 24, C_GREY), *[num(v, 0.8) for v in a]).arrange(RIGHT, buff=0.35).move_to([0, 2.7, 0])
        heads = VGroup(VGroup(Text("bisect_left", font=MONO, font_size=28, color=C_YELLOW), T("严格上升", 24, C_GREY))
                       .arrange(DOWN, buff=0.12).move_to([-3.5, 1.6, 0]),
                       VGroup(Text("bisect_right", font=MONO, font_size=28, color=C_TEAL), T("非降：允许相等", 24, C_GREY))
                       .arrange(DOWN, buff=0.12).move_to([3.5, 1.6, 0]))
        sep = DashedLine([0, 2.1, 0], [0, -2.7, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(inp), FadeIn(heads[0]), Create(sep), run_time=0.8)
        L_steps, R_steps = L.tails_trace(a, "left"), L.tails_trace(a, "right")
        lpos = lambda k, h: np.array([-3.5 + 1.5 * k, -1.4 + CARD_DY * h, 0])  # noqa: E731
        rpos = lambda k, h: np.array([3.5 + 1.5 * (k - 1), -1.4 + CARD_DY * h, 0])  # noqa: E731
        lc, rc = [[] for _ in a], [[] for _ in a]
        for i, (v, pos, new, _, _) in enumerate(L_steps):
            c = card(v, C_YELLOW).move_to(inp[1 + i])
            anims = [c.animate.move_to(lpos(pos, len(lc[pos])))]
            if lc[pos]:
                anims += [lc[pos][-1][1].animate.set_color(C_GREY), lc[pos][-1][0].animate.set_stroke(C_GREY, 2)]
            self.play(*anims, run_time=0.5)
            lc[pos].append(c)
        n_l = len(L_steps[-1][3])
        res_l = T(f"长度 {n_l}", 26, C_YELLOW).move_to([-3.5, -2.55, 0])
        self.play(FadeIn(res_l), run_time=0.4)
        self.wait_until(self.cue_start("允许相等", self.now))
        self.play(FadeIn(heads[1]), run_time=0.6)
        for i, (v, pos, new, _, _) in enumerate(R_steps):
            c = card(v, C_TEAL).move_to(inp[1 + i])
            self.play(c.animate.move_to(rpos(pos, len(rc[pos]))), run_time=0.5)
            rc[pos].append(c)
        n_r = len(R_steps[-1][3])
        res_r = T(f"长度 {n_r}", 26, C_TEAL).move_to([3.5, -2.55, 0])
        self.play(FadeIn(res_r), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(inp, heads, sep, res_l, res_r, *[c for p in lc + rc for c in p])), run_time=0.6)

    # ---------------------------------------------------------------- 作业变形
    def homework_beat(self):
        self.beat("homework")
        m = L.MISSILE
        h1 = VGroup(T("拦截导弹", 30, C_BLUE), Text("M02945", font=MONO, font_size=24, color=C_GREY),
                    T("最长不上升子序列", 24)).arrange(RIGHT, buff=0.3).move_to([0, 2.95, 0])
        mrow = make_row(m, 2.0, cell=0.95, sp=1.1, scale=0.6)
        self.play(FadeIn(h1), FadeIn(mrow), run_time=0.8)
        self.wait_until(self.cue_start("反过来", self.now))
        trick = VGroup(T("反转", 24), MathTex(r"\Rightarrow").scale(0.7), T("最长不降", 24),
                       Text("bisect_right", font=MONO, font_size=24, color=C_TEAL)).arrange(RIGHT, buff=0.25)
        trick.move_to([0, 1.05, 0])
        self.play(FadeIn(trick, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("样例", self.now))
        w = L.non_increasing_witness()
        ans1 = T(f"最多拦下 {L.longest_non_increasing(m)} 枚", 26, C_YELLOW).next_to(trick, RIGHT, buff=0.6)
        if ans1.get_right()[0] > 6.8:
            VGroup(trick, ans1).arrange(RIGHT, buff=0.6).move_to([0, 1.05, 0])
        self.play(*[mrow[1][i].animate.set_color(C_YELLOW) for i in w],
                  *[mrow[0][i].animate.set_stroke(C_YELLOW, 3) for i in w], FadeIn(ans1), run_time=1.0)
        self.wait_until(self.cue_start("最大上升子序列和", self.now))
        h2 = VGroup(T("最大上升子序列和", 30, C_PURPLE), Text("03532", font=MONO, font_size=24, color=C_GREY))
        h2.arrange(RIGHT, buff=0.3).move_to([0, 0.0, 0])
        rule = MathTex(r"dp[i]=\max\big(dp[j]+1\big)", color=C_GREY).scale(0.7)
        rule2 = MathTex(r"dp[i]=\max\big(dp[j]+a[i]\big)", color=WHITE).scale(0.7)
        rule.move_to([0, -0.8, 0])
        rule2.move_to(rule)
        self.play(FadeIn(h2), FadeIn(rule), run_time=0.7)
        self.play(ReplacementTransform(rule, rule2), run_time=0.9)
        self.wait_until(self.cue_start("答案是十八", self.now))
        arow = make_row(L.A, -1.85, cell=0.8, sp=1.0, scale=0.65, x=-1.3)
        dp, seq = L.rising_sum_back()
        pick = [L.A.index(v) for v in seq]
        tot = VGroup(MathTex("=" + "+".join(map(str, seq)) + f"={max(dp)}", color=C_YELLOW).scale(0.75))
        tot.next_to(arow, RIGHT, buff=0.35)
        self.play(FadeIn(arow), run_time=0.4)
        self.play(*[arow[1][i].animate.set_color(C_YELLOW) for i in pick],
                  *[arow[0][i].animate.set_stroke(C_YELLOW, 3) for i in pick], FadeIn(tot), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(h1, mrow, trick, ans1, h2, rule2, arow, tot)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        left = VGroup(MathTex(r"O(n^2)", color=C_BLUE).scale(0.9), MathTex(r"dp[i]", color=WHITE).scale(0.75),
                      T("以 a[i] 结尾的最长长度", 24)).arrange(DOWN, buff=0.25)
        right = VGroup(MathTex(r"O(n\log n)", color=C_TEAL).scale(0.9), MathTex(r"tails[k]", color=WHITE).scale(0.75),
                       T("长度 k+1 的最小结尾", 24)).arrange(DOWN, buff=0.25)
        cards = VGroup()
        for g, col in ((left, C_BLUE), (right, C_TEAL)):
            box = RoundedRectangle(corner_radius=0.18, width=5.0, height=2.4, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06).move_to(g)
            cards.add(VGroup(box, g))
        cards.arrange(RIGHT, buff=0.7).move_to([0, 1.2, 0])
        self.play(FadeIn(cards[0], shift=RIGHT * 0.3), FadeIn(cards[1], shift=LEFT * 0.3), run_time=1.2)
        self.wait_until(self.cue_start("tails 的长度", self.now))
        key = T("tails 的长度是答案，它本身不是", 30, C_YELLOW).move_to([0, -1.3, 0])
        self.play(Write(key), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 11 周 动态规划 2.1 节 · OpenJudge 02533 · M02945 · 03532", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
