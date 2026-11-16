"""例题精讲：滑动窗口最大值（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。双端队列的每一步都来自 slidemaxdata.trace
（与作业 26978 题解同一写法；test_slidemax.py 对撞讲义两份原版、暴力解与随机数据）。

画面：上半是数组（柱高 = 值 + 4，柱下写值和下标），黄框是窗口；左下是双端队列（左队首、右队尾），右下是输出。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slidemaxdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

A, K = D.NUMS, D.K
BASE_Y, BAR_W, UNIT = 0.0, 0.8, 0.27
VAL_Y, IDX_Y = -0.32, -0.72
WIN_TOP, WIN_BOT = 3.2, -0.98
DQ_Y, DQ_X0, DQ_STEP, DQ_L, DQ_R = -1.9, -4.55, 1.0, -5.15, -0.95
OUT_X0, OUT_STEP = 1.55, 0.8
CODE = ("q = deque()                       # 存下标，值递减\n"
        "ans = []\n"
        "for i, x in enumerate(a):\n"
        "    while q and q[0] <= i - k:    # 队首过期\n"
        "        q.popleft()\n"
        "    while q and a[q[-1]] <= x:    # 队尾不比 x 大\n"
        "        q.pop()\n"
        "    q.append(i)\n"
        "    if i >= k - 1:\n"
        "        ans.append(a[q[0]])")


def xs(i):
    return -4.9 + 1.4 * i


def num(v, size=28, color=WHITE):
    return Text(str(v), font=MONO, font_size=size, color=color)


class SlideMaxLesson(Lesson):
    def construct(self):
        for b in ("title", "read", "brute", "observe", "model", "run", "code", "cost", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    # ---------------------------------------------------------------- 时间轴小工具
    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key, extra=0.0):
        t = self.cue_start(key)
        if t is not None:
            self.wait_until(t + extra)

    def hold(self, keep=0.6):
        self.wait(max(0.1, self.left() - keep))

    # ---------------------------------------------------------------- 数组、窗口、队列
    def build_array(self):
        self.bars = VGroup(*[
            Rectangle(width=BAR_W, height=(v + 4) * UNIT, stroke_color=C_BLUE, stroke_width=2)
            .set_fill(C_BLUE, 0.5).move_to([xs(i), BASE_Y + (v + 4) * UNIT / 2, 0]) for i, v in enumerate(A)])
        self.vals = VGroup(*[num(v).move_to([xs(i), VAL_Y, 0]) for i, v in enumerate(A)])
        self.idxs = VGroup(*[Text(str(i), font=MONO, font_size=18, color=C_GREY).move_to([xs(i), IDX_Y, 0])
                             for i in range(len(A))])
        self.caps = VGroup(T("值", 18, C_GREY).move_to([-6.2, VAL_Y, 0]),
                           T("下标", 18, C_GREY).move_to([-6.2, IDX_Y, 0]))
        return VGroup(self.bars, self.vals, self.idxs, self.caps)

    def bar_color(self, i, col, op=0.5):
        return self.bars[i].animate.set_fill(col, op).set_stroke(col)

    def win_rect(self, l, r, color=C_YELLOW):
        w = (r - l) * 1.4 + 1.4
        return Rectangle(width=w, height=WIN_TOP - WIN_BOT, stroke_color=color, stroke_width=3).move_to(
            [(xs(l) + xs(r)) / 2, (WIN_TOP + WIN_BOT) / 2, 0])

    def build_tube(self):
        top = Line([DQ_L, DQ_Y + 0.42, 0], [DQ_R, DQ_Y + 0.42, 0], stroke_color=C_GREY, stroke_width=3)
        bot = Line([DQ_L, DQ_Y - 0.42, 0], [DQ_R, DQ_Y - 0.42, 0], stroke_color=C_GREY, stroke_width=3)
        lh = T("队首", 20, C_GREY).next_to(top, UP, buff=0.12).align_to(top, LEFT)
        lt = T("队尾", 20, C_GREY).next_to(top, UP, buff=0.12).align_to(top, RIGHT)
        name = T("双端队列", 20, C_TEAL).next_to(top, UP, buff=0.12)
        self.tube = VGroup(top, bot, lh, lt, name)
        return self.tube

    def slot(self, s):
        return np.array([DQ_X0 + DQ_STEP * s, DQ_Y, 0])

    def item(self, j, color=C_TEAL):
        box = RoundedRectangle(corner_radius=0.08, width=0.86, height=0.66, stroke_color=color,
                               stroke_width=3).set_fill(color, 0.16)
        v = num(A[j], 26).move_to(box).shift(LEFT * 0.08 + UP * 0.04)
        ix = Text(f"#{j}", font=MONO, font_size=14, color=C_GREY).move_to(box.get_corner(DR) + np.array([-0.17, 0.13, 0]))
        return VGroup(box, v, ix)

    def out_pos(self, j):
        return np.array([OUT_X0 + OUT_STEP * j, DQ_Y, 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("例题精讲：滑动窗口最大值", 46).move_to([0, 2.3, 0])
        sub = Text("LeetCode 239 · OpenJudge 26978", font=MONO, font_size=26, color=C_GREY).move_to([0, 1.45, 0])
        self.play(Write(title), run_time=1.2)
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)
        self.at("机考里")
        tag = T("单调队列", 30, C_YELLOW).move_to([0, 0.45, 0])
        self.play(FadeIn(tag, scale=1.2), run_time=0.6)
        self.at("我们按")
        steps = ["读题", "找规律", "建模", "写代码", "算复杂度"]
        chips = VGroup()
        for s in steps:
            t = T(s, 24)
            r = RoundedRectangle(corner_radius=0.12, width=t.width + 0.4, height=0.62, stroke_color=C_BLUE,
                                 stroke_width=2).set_fill(C_BLUE, 0.1)
            chips.add(VGroup(r, t.move_to(r)))
        chips.arrange(RIGHT, buff=0.55).move_to([0, -1.2, 0])
        arrows = VGroup(*[Arrow(chips[i].get_right(), chips[i + 1].get_left(), buff=0.06, stroke_width=3,
                                color=C_GREY, tip_length=0.14) for i in range(4)])
        for i in range(5):
            anims = [FadeIn(chips[i], shift=RIGHT * 0.15)]
            if i:
                anims.append(GrowArrow(arrows[i - 1]))
            self.play(*anims, run_time=0.45)
        self.hold()
        self.corner = T("例题精讲 · LeetCode 239", 20, C_GREY).to_corner(UL, buff=0.3)
        self.play(FadeOut(VGroup(sub, tag, chips, arrows)), ReplacementTransform(title, self.corner), run_time=0.6)

    # ---------------------------------------------------------------- 读题
    def read_beat(self):
        self.beat("read")
        arr = self.build_array()
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in self.bars], lag_ratio=0.1), FadeIn(self.vals), run_time=1.4)
        self.at("窗口从最左边")
        kt = MathTex("k=3", color=C_YELLOW).scale(0.9).to_corner(UR, buff=0.3)
        self.win = self.win_rect(0, 2)
        self.play(Create(self.win), FadeIn(kt), run_time=0.8)
        for l in range(1, 6):
            self.play(self.win.animate.become(self.win_rect(l, l + 2)), run_time=0.45)
        self.play(self.win.animate.become(self.win_rect(0, 2)), run_time=0.5)
        self.at("样例是")
        self.play(LaggedStart(*[Indicate(v, color=C_YELLOW, scale_factor=1.25) for v in self.vals], lag_ratio=0.15),
                  FadeIn(self.idxs), FadeIn(self.caps), run_time=2.2)
        self.at("答案是")
        lab = T("输出", 22, C_GREY).move_to([OUT_X0 - 0.95, DQ_Y, 0])
        self.play(FadeIn(lab), run_time=0.3)
        ans = D.brute(A, K)
        outs = VGroup()
        for l, v in enumerate(ans):
            j = l + int(np.argmax(A[l:l + K]))
            anims = [self.win.animate.become(self.win_rect(l, l + K - 1))] if l else []
            if anims:
                self.play(*anims, run_time=0.35)
            o = num(v, 30, C_YELLOW).move_to(self.out_pos(l))
            self.play(self.bar_color(j, C_YELLOW, 0.7), TransformFromCopy(self.vals[j], o), run_time=0.5)
            self.play(self.bar_color(j, C_BLUE), run_time=0.2)
            outs.add(o)
        cnt = T("6 个窗口 = n − k + 1", 22, C_GREY).next_to(outs, DOWN, buff=0.28)
        self.play(FadeIn(cnt), run_time=0.4)
        self.hold()
        self.play(FadeOut(VGroup(outs, lab, cnt)), self.win.animate.become(self.win_rect(0, 2)), run_time=0.6)
        self.kt = kt

    # ---------------------------------------------------------------- 暴力
    def brute_beat(self):
        self.beat("brute")
        counter = VGroup(T("比较次数", 24, C_GREY), Integer(0, font_size=40, color=C_RED)).arrange(RIGHT, buff=0.3)
        counter.move_to([-3.2, -1.7, 0])
        self.play(FadeIn(counter), run_time=0.4)
        dot = Dot(radius=0.09, color=C_RED)
        n = 0
        for l in range(6):
            if l:
                self.play(self.win.animate.become(self.win_rect(l, l + 2)), run_time=0.25)
            dot.move_to([xs(l), WIN_TOP - 0.25, 0])
            self.add(dot)
            for j in range(l + 1, l + K):
                n += 1
                self.play(dot.animate.move_to([xs(j), WIN_TOP - 0.25, 0]),
                          ChangeDecimalToValue(counter[1], n), run_time=0.28)
            self.remove(dot)
        assert n == D.brute_compares(len(A), K) == 12
        self.at("可是")
        big = D.brute_compares(D.BIG_N, D.BIG_K)
        f1 = MathTex(r"(n-k+1)(k-1)").scale(0.85).move_to([2.7, -1.45, 0])
        f2 = MathTex(r"n=10^5,\ k=5\times10^4", r"\Rightarrow", rf"\approx {big / 1e9:.1f}\times10^9").scale(0.75)
        f2.next_to(f1, DOWN, buff=0.3)
        f2[2].set_color(C_RED)
        self.play(Write(f1), run_time=0.8)
        self.play(Write(f2), run_time=1.4)
        tle = T("超时", 26, C_RED).next_to(f2, DOWN, buff=0.22)
        self.play(FadeIn(tle, scale=1.3), run_time=0.4)
        self.at("相邻两个窗口")
        self.play(FadeOut(VGroup(f1, f2, tle, counter)), self.win.animate.become(self.win_rect(0, 2)), run_time=0.5)
        w2 = self.win_rect(1, 3, C_TEAL)
        self.play(Create(w2), run_time=0.6)
        ov = Rectangle(width=1.4 + 1.4 - 0.3, height=WIN_TOP - WIN_BOT - 0.3, stroke_width=0).set_fill(C_RED, 0.18)
        ov.move_to([(xs(1) + xs(2)) / 2, (WIN_TOP + WIN_BOT) / 2, 0])
        lab = T("重叠的 k − 1 个数，又比了一遍", 24, C_RED).move_to([0, -1.8, 0])
        self.play(FadeIn(ov), FadeIn(lab), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(w2, ov, lab)), FadeOut(self.win), run_time=0.6)

    # ---------------------------------------------------------------- 关键观察
    def observe_beat(self):
        self.beat("observe")
        self.at("三进来时")
        self.play(*[self.bars[i].animate.set_fill(C_BLUE, 0.15).set_stroke(opacity=0.3) for i in range(2, 8)],
                  *[self.vals[i].animate.set_opacity(0.3) for i in range(2, 8)],
                  self.bar_color(1, C_TEAL, 0.7), run_time=0.7)
        new = T("新来", 20, C_TEAL).next_to(self.bars[1], UP, buff=0.12)
        self.play(FadeIn(new), run_time=0.4)
        self.at("一比三先")
        f1 = T("1 比 3 先离开窗口", 24).move_to([-2.4, -1.55, 0])
        f2 = T("1 又比 3 小", 24).next_to(f1, DOWN, buff=0.22).align_to(f1, LEFT)
        self.play(FadeIn(f1, shift=UP * 0.1), run_time=0.5)
        self.wait(1.2)
        self.play(FadeIn(f2, shift=UP * 0.1), run_time=0.5)
        self.wait(1.0)
        verdict = T("⇒ 1 永无出头之日，扔掉", 26, C_RED).move_to([2.9, -1.8, 0])
        cross = Cross(self.bars[0], stroke_color=C_RED, stroke_width=4)
        self.play(FadeIn(verdict), Create(cross), self.bars[0].animate.set_fill(C_GREY, 0.2).set_stroke(C_GREY),
                  self.vals[0].animate.set_opacity(0.3), run_time=0.8)
        self.at("换句话说")
        rule = T("新来的数，淘汰它前面所有不比它大的数", 28, C_YELLOW).move_to([0, -1.8, 0])
        self.play(FadeOut(VGroup(f1, f2, verdict, cross, new)), FadeIn(rule, shift=UP * 0.15), run_time=0.7)
        # 演示：5 进来，挡住前面的 −1、−3
        self.play(*[self.bars[i].animate.set_fill(C_BLUE, 0.5).set_stroke(C_BLUE, opacity=1) for i in range(8)],
                  *[v.animate.set_opacity(1) for v in self.vals], run_time=0.5)
        self.play(self.bar_color(4, C_TEAL, 0.7), run_time=0.4)
        top = self.bars[4].get_top()[1]
        sight = DashedLine([xs(4), top, 0], [xs(2) - 0.5, top, 0], stroke_color=C_TEAL, stroke_width=3)
        self.play(Create(sight), run_time=0.6)
        self.play(*[self.bars[i].animate.set_fill(C_GREY, 0.2).set_stroke(C_GREY) for i in (2, 3)],
                  *[self.vals[i].animate.set_opacity(0.3) for i in (2, 3)], run_time=0.6)
        self.at("留下来的候选人")
        self.play(FadeOut(sight), *[self.bars[i].animate.set_fill(C_BLUE, 0.5).set_stroke(C_BLUE) for i in range(8)],
                  *[v.animate.set_opacity(1) for v in self.vals], run_time=0.5)
        snap = D.snapshots(A, K)[3]                     # i = 3 时的候选人：下标 1, 2, 3
        assert snap == [1, 2, 3]
        win = self.win_rect(1, 3)
        stairs = VMobject(stroke_color=C_YELLOW, stroke_width=3).set_points_as_corners(
            [self.bars[j].get_top() for j in snap])
        self.play(Create(win), *[self.bar_color(j, C_YELLOW, 0.6) for j in snap], run_time=0.7)
        self.play(Create(stairs), run_time=0.7)
        dec = T("候选人从左到右递减", 28, C_YELLOW).move_to([0, -1.8, 0])
        self.play(ReplacementTransform(rule, dec), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(win, stairs, dec)), *[self.bar_color(j, C_BLUE) for j in snap], run_time=0.6)

    # ---------------------------------------------------------------- 建模
    def model_beat(self):
        self.beat("model")
        tube = self.build_tube()
        rules = VGroup(T("① 队尾：弹出不比新数大的", 22), T("② 新下标 i 入队尾", 22),
                       T("③ 队首：下标 ≤ i − k 就弹出", 22), T("④ 队首就是窗口最大值", 22, C_YELLOW))
        rules.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([3.4, -2.0, 0])
        self.play(Create(tube[:2]), FadeIn(tube[2:]), run_time=0.8)
        # 演示队尾：i = 6 之前队里是 #4(5)、#5(3)，6 进来弹掉两个
        snaps = D.snapshots(A, K)
        items = [self.item(j).move_to(self.slot(s)) for s, j in enumerate(snaps[5])]
        self.play(*[FadeIn(m) for m in items], run_time=0.5)
        self.at("新数进来之前")
        self.play(FadeIn(rules[0]), run_time=0.4)
        newc = self.item(6, C_YELLOW).move_to(self.slot(2) + np.array([0, 0, 0]))
        newc.next_to(tube[0], RIGHT, buff=0.15).set_y(DQ_Y)
        self.play(TransformFromCopy(self.vals[6], newc[1]), FadeIn(newc[0]), FadeIn(newc[2]), self.bar_color(6, C_YELLOW, 0.6),
                  run_time=0.6)
        pops = [e[2] for e in D.trace(A, K)[1] if e[0] == "pop" and e[1] == 6]
        assert pops == [5, 4]
        for j in pops:
            m = items.pop()
            self.play(m.animate.shift(DOWN * 0.5).set_opacity(0), run_time=0.45)
        self.play(newc.animate.move_to(self.slot(0)), FadeIn(rules[1]), run_time=0.5)
        self.at("队首最大")
        self.play(FadeIn(rules[2]), run_time=0.4)
        # 演示队首：i = 4 时 #1 已在窗口 [2, 4] 外
        self.play(FadeOut(newc), self.bar_color(6, C_BLUE), run_time=0.3)
        olds = [self.item(j).move_to(self.slot(s)) for s, j in enumerate(snaps[3])]
        win = self.win_rect(2, 4)
        self.play(*[FadeIn(m) for m in olds], Create(win), run_time=0.6)
        exp = [e for e in D.trace(A, K)[1] if e[0] == "expire"]
        assert exp == [("expire", 4, 1)]
        self.at("下标小于等于")
        mark = MathTex(r"1\le 4-3", color=C_RED).scale(0.7).next_to(olds[0], DOWN, buff=0.4)
        self.play(Indicate(olds[0][2], color=C_RED, scale_factor=1.6), Indicate(self.idxs[1], color=C_RED, scale_factor=1.5),
                  FadeIn(mark), run_time=0.9)
        self.play(olds[0].animate.shift(LEFT * 0.6).set_opacity(0), FadeOut(mark), run_time=0.5)
        self.play(*[m.animate.move_to(self.slot(s)) for s, m in enumerate(olds[1:])], run_time=0.4)
        self.at("剩下的队首")
        self.play(FadeIn(rules[3]), Indicate(olds[1], color=C_YELLOW, scale_factor=1.2), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(*items, *olds[1:], win)), run_time=0.5)
        self.rules = rules

    # ---------------------------------------------------------------- 在样例上跑一遍
    def run_beat(self):
        self.beat("run")
        self.play(self.rules.animate.set_opacity(0.0), run_time=0.3)
        self.remove(self.rules)
        lab = T("输出", 22, C_GREY).move_to([OUT_X0 - 0.95, DQ_Y, 0])
        self.play(FadeIn(lab), run_time=0.3)
        ans, ev = D.trace(A, K)
        cue = {0: "一入队", 1: "三来了", 2: "负一入队", 3: "负三入队", 4: "五来了", 5: "三入队，输出五", 6: "六弹掉"}
        q, outs = [], VGroup()                # q: [(下标, 方块)]
        win = None
        by_i = {}
        for e in ev:
            by_i.setdefault(e[1], []).append(e)
        for i in range(len(A)):
            if i in cue:
                self.at(cue[i])
            l = max(0, i - K + 1)
            anims = [self.bar_color(i, C_TEAL, 0.75)] + ([self.bar_color(i - 1, C_BLUE)] if i else [])
            if win is None:
                win = self.win_rect(l, i)
                self.play(Create(win), *anims, run_time=0.4)
            else:
                self.play(win.animate.become(self.win_rect(l, i)), *anims, run_time=0.35)
            slow = i == 4
            for e in by_i[i]:
                if e[0] == "expire":
                    if slow:
                        self.at("三的下标")
                    j, m = q.pop(0)
                    tag = T("过期", 20, C_RED).next_to(m, DOWN, buff=0.2)
                    self.play(FadeIn(tag), m[0].animate.set_stroke(C_RED), run_time=0.5)
                    self.play(m.animate.shift(LEFT * 0.6).set_opacity(0), FadeOut(tag),
                              *[mm.animate.move_to(self.slot(s)) for s, (_, mm) in enumerate(q)], run_time=0.55)
                    if slow:
                        self.at("再从队尾")
                elif e[0] == "pop":
                    j, m = q.pop()
                    self.play(m[0].animate.set_stroke(C_RED), run_time=0.2 if not slow else 0.35)
                    self.play(m.animate.shift(DOWN * 0.5).set_opacity(0), run_time=0.35 if not slow else 0.5)
                elif e[0] == "push":
                    m = self.item(i).move_to(self.slot(len(q)))
                    self.play(TransformFromCopy(self.vals[i], m[1]), FadeIn(m[0]), FadeIn(m[2]), run_time=0.45)
                    q.append((i, m))
                elif e[0] == "out":
                    _, j, v = e[1:]
                    assert q[0][0] == j
                    o = num(v, 30, C_YELLOW).move_to(self.out_pos(len(outs)))
                    self.play(Indicate(q[0][1], color=C_YELLOW, scale_factor=1.15),
                              TransformFromCopy(q[0][1][1], o), run_time=0.5)
                    outs.add(o)
        assert [int(o.text) for o in outs] == ans == D.brute(A, K)
        self.at("结果和样例")
        ok = T("= 样例 ✓", 24, C_GREEN).next_to(outs, DOWN, buff=0.25)
        self.play(FadeIn(ok, shift=UP * 0.1), run_time=0.5)
        self.hold()
        self.play(FadeOut(VGroup(lab, outs, ok, win, self.tube, *[m for _, m in q])),
                  FadeOut(VGroup(self.bars, self.vals, self.idxs, self.caps)), FadeOut(self.kt), run_time=0.6)

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string=CODE, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 20})
        code.scale_to_fit_width(9.4)
        if code.height > 5.2:
            code.scale_to_fit_height(5.2)
        code.move_to([-1.3, 0.35, 0])
        ln = code.code_lines
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.8)
        self.at("第一个从队首")
        hl = SurroundingRectangle(VGroup(ln[3], ln[4]), color=C_RED, buff=0.05, stroke_width=2)
        self.play(Create(hl), run_time=0.5)
        self.at("第二个")
        self.play(hl.animate.become(SurroundingRectangle(VGroup(ln[5], ln[6]), color=C_TEAL, buff=0.05,
                                                         stroke_width=2)), run_time=0.5)
        self.at("然后新下标")
        self.play(hl.animate.become(SurroundingRectangle(ln[7], color=C_BLUE, buff=0.05, stroke_width=2)),
                  run_time=0.5)
        self.at("i 到了")
        self.play(hl.animate.become(SurroundingRectangle(VGroup(ln[8], ln[9]), color=C_YELLOW, buff=0.05,
                                                         stroke_width=2)), run_time=0.5)
        self.at("比较的是值")
        n1 = VGroup(T("比较：值", 24, C_TEAL), Text("a[q[-1]] <= x", font=MONO, font_size=22, color=C_TEAL)
                    ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        n2 = VGroup(T("存放：下标", 24, C_BLUE), Text("q.append(i)", font=MONO, font_size=22, color=C_BLUE)
                    ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        notes = VGroup(n1, n2).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([5.0, 0.4, 0])
        self.play(FadeOut(hl), FadeIn(notes, shift=LEFT * 0.2), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(code, notes)), run_time=0.6)

    # ---------------------------------------------------------------- 复杂度
    def cost_beat(self):
        self.beat("cost")
        looks = MathTex(r"\text{for} \supset \text{while}", r"\;\Rightarrow\;", r"n^2\,?").scale(0.9).move_to([0, 2.7, 0])
        looks[2].set_color(C_RED)
        self.play(Write(looks), run_time=1.0)
        ev = D.trace(A, K)[1]
        leave = {e[2] for e in ev if e[0] in ("pop", "expire")}
        push, pops = D.op_counts(A, K)
        assert (push, pops) == (8, 7) and len(leave) == 7
        cols = [-3.5 + 1.0 * i for i in range(len(A))]
        heads = VGroup(*[Text(f"#{i}", font=MONO, font_size=20, color=C_GREY).move_to([x, 1.55, 0])
                         for i, x in enumerate(cols)])
        rin = T("入队", 22, C_GREEN).move_to([-5.0, 0.85, 0])
        rout = T("出队", 22, C_RED).move_to([-5.0, 0.1, 0])
        self.play(FadeIn(heads), FadeIn(rin), FadeIn(rout), run_time=0.6)
        self.at("样例入队")
        din = VGroup(*[Dot([x, 0.85, 0], radius=0.13, color=C_GREEN) for x in cols])
        dout = VGroup(*[Dot([cols[i], 0.1, 0], radius=0.13, color=C_RED) for i in range(len(A)) if i in leave])
        nin = Integer(push, font_size=34, color=C_GREEN).move_to([cols[-1] + 1.0, 0.85, 0])
        nout = Integer(pops, font_size=34, color=C_RED).move_to([cols[-1] + 1.0, 0.1, 0])
        self.play(LaggedStart(*[GrowFromCenter(d) for d in din], lag_ratio=0.12), FadeIn(nin), run_time=1.2)
        self.play(LaggedStart(*[GrowFromCenter(d) for d in dout], lag_ratio=0.12), FadeIn(nout), run_time=1.1)
        self.at("总操作")
        bound = MathTex(r"\le 2n", r"\;\Rightarrow\;", r"O(n)").scale(1.0).move_to([0, -0.8, 0])
        bound[2].set_color(C_GREEN)
        cross = Cross(looks[2], stroke_color=C_RED, stroke_width=4)
        self.play(Write(bound), Create(cross), run_time=1.0)
        self.at("n 等于十万")
        big = D.brute_compares(D.BIG_N, D.BIG_K)
        cmp = VGroup(VGroup(T("暴力", 22, C_RED), MathTex(rf"\approx {big / 1e9:.1f}\times10^9", color=C_RED).scale(0.8)
                            ).arrange(RIGHT, buff=0.3),
                     VGroup(T("单调队列", 22, C_GREEN), MathTex(r"\approx 2\times10^5", color=C_GREEN).scale(0.8)
                            ).arrange(RIGHT, buff=0.3)).arrange(RIGHT, buff=1.2).move_to([0, -1.75, 0])
        self.play(FadeIn(cmp[0]), run_time=0.5)
        self.play(FadeIn(cmp[1]), run_time=0.5)
        ratio = big / (2 * D.BIG_N)
        times = T(f"快约 {ratio / 1e4:.2f} 万倍", 26, C_YELLOW).move_to([0, -2.4, 0])
        self.play(FadeIn(times, scale=1.2), run_time=0.5)
        self.hold()
        self.play(FadeOut(VGroup(looks, cross, heads, rin, rout, din, dout, nin, nout, bound, cmp, times)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾与同类题
    def recap_beat(self):
        self.beat("recap")

        def box(head, txt, col):
            h = T(head, 22, col)
            t = T(txt, 22)
            g = VGroup(h, t).arrange(DOWN, buff=0.14)
            r = RoundedRectangle(corner_radius=0.12, width=2.9, height=1.3, stroke_color=col,
                                 stroke_width=3).set_fill(col, 0.08)
            return VGroup(r, g.move_to(r))
        chain = VGroup(box("读题", "找出重复比较", C_BLUE), box("观察", "被淘汰的不翻身", C_TEAL),
                       box("建模", "存下标的单调队列", C_YELLOW), box("复杂度", "进出各一次 O(n)", C_GREEN))
        chain.arrange(RIGHT, buff=0.36).move_to([0, 1.5, 0])
        arrows = VGroup(*[Arrow(chain[i].get_right(), chain[i + 1].get_left(), buff=0.04, stroke_width=3,
                                color=C_GREY, tip_length=0.12) for i in range(3)])
        for i in range(4):
            self.play(FadeIn(chain[i], shift=RIGHT * 0.15), *([GrowArrow(arrows[i - 1])] if i else []), run_time=0.6)
        self.at("同类题")
        head = T("同类题", 26, C_YELLOW).move_to([-4.0, -0.15, 0])
        items = VGroup(T("窗口最小值：把递减改成递增", 22),
                       T("洛谷 P2698 Flowerpot（讲义 5.4 练习）", 22),
                       T("OpenJudge 04137 最小新整数（单调栈）", 22),
                       T("OpenJudge 26977 接雨水（单调栈）", 22))
        items.arrange(DOWN, buff=0.22, aligned_edge=LEFT).next_to(head, RIGHT, buff=0.5).align_to(head, UP)
        self.play(FadeIn(head), run_time=0.4)
        for it in items:
            self.play(FadeIn(it, shift=UP * 0.1), run_time=0.45)
            self.wait(1.2)
        self.hold(0.2)
        src = T("数据结构与算法（B）2026spring 线性结构 5.3–5.4 节 · 2026fall 每日选作 0930 · LeetCode 239 · OpenJudge 26978",
                18, C_GREY).to_edge(DOWN, buff=0.2)
        if src.width > 13.4:
            src.scale_to_fit_width(13.4)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(VGroup(chain, arrows, head, items, src, self.corner)), run_time=0.6)
