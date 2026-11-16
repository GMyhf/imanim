"""Manacher：照镜子找回文（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。每个下标的情况（R 外 / 镜像在内 /
镜像顶到边界）、初值、逐次比较、C 与 R 的移动、比较次数都来自 manacherdata（讲义 LC_top-100-liked M5
方法二、方法三原样插桩；test_manacher.py 对撞讲义两份代码、暴力枚举与摊还上界）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manacherdata as M  # noqa: E402
from cine import *  # noqa: E402,F403

TR = M.manacher_trace(M.DEMO)
W = 0.56                                    # 主例每格宽
ROW_Y, IDX_Y, P_Y = 1.45, 0.95, 0.42


def cx(i, n=21, w=W, x0=0.0):
    return x0 + (i - (n - 1) / 2) * w


def strip(chars, y, w=0.8, size=30, x0=0.0, hash_col=C_GREY):
    g = VGroup()
    n = len(chars)
    for i, ch in enumerate(chars):
        sq = Square(w * 0.94, stroke_color=C_GREY, stroke_width=1.5).move_to([cx(i, n, w, x0), y, 0])
        tx = Text(ch, font=MONO, font_size=size, color=hash_col if ch == "#" else WHITE).move_to(sq)
        g.add(VGroup(sq, tx))
    return g


def arc_span(a, b, y, n=21, w=W, col=C_YELLOW, h=0.32, x0=0.0, sw=3):
    """下标 a..b 的回文跨度：一条贴在格子上方的括弧。"""
    xa, xb = cx(a, n, w, x0) - w * 0.42, cx(b, n, w, x0) + w * 0.42
    top = y + w * 0.5 + 0.08
    return VMobject(stroke_color=col, stroke_width=sw).set_points_as_corners(
        [[xa, top, 0], [xa, top + h * 0.4, 0], [xb, top + h * 0.4, 0], [xb, top, 0]])


class ManacherLesson(Lesson):
    def construct(self):
        for b in ("title", "expand", "sharp", "mirror", "inside", "edge", "run", "linear", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, k, default=None):
        return next((c["start"] for c in self.cue_times() if k in c["text"]), default)

    def at(self, k):
        self.wait_until(self.cue_start(k, self.now))

    def hold(self, tail=0.6):
        self.wait(max(0.1, self.left() - tail))

    def clear(self, *mobs, rt=0.6):
        mobs = [m for m in mobs if m is not None]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=rt, audit=False)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        s = strip(M.BABAD, 0.6, w=0.9, size=40)
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.2) for c in s], lag_ratio=0.1), run_time=1.0)
        self.at("比如")
        a1 = arc_span(0, 2, 0.6, n=5, w=0.9, col=C_YELLOW, h=0.4)
        a2 = arc_span(1, 3, 0.6, n=5, w=0.9, col=C_TEAL, h=0.4).shift(UP * 0.28)
        l1 = Text("bab", font=MONO, font_size=28, color=C_YELLOW).move_to([-2.0, -0.7, 0])
        l2 = Text("aba", font=MONO, font_size=28, color=C_TEAL).move_to([2.0, -0.7, 0])
        self.play(Create(a1), *[s[k][0].animate.set_stroke(C_YELLOW, 2.5) for k in range(3)], FadeIn(l1), run_time=0.8)
        self.play(Create(a2), FadeIn(l2), run_time=0.8)
        self.at("马拉车算法")
        title = T("Manacher", 60).move_to([0, 2.7, 0])
        sub = T("照镜子找回文", 32, C_TEAL).move_to([0, -1.9, 0])
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.1)
        self.hold()
        self.clear(s, a1, a2, l1, l2, title, sub)

    # ---------------------------------------------------------------- 中心扩展与平方
    def expand_beat(self):
        self.beat("expand")
        head = T("中心扩展：每个中心向两边扩", 30, C_YELLOW).move_to([0, 3.3, 0])
        s = strip(M.BABAD, 2.0, w=0.8, size=34, x0=-3.2)
        self.play(FadeIn(head), FadeIn(s), run_time=0.7)
        dots = VGroup()
        for k in range(9):
            x = cx(k / 2, 5, 0.8, -3.2)
            dots.add(Dot([x, 1.4, 0], radius=0.07, color=C_YELLOW if k % 2 == 0 else C_TEAL))
        cnt = VGroup(T("中心", 24), MathTex(r"2n-1 = 9", color=WHITE).scale(0.8)).arrange(RIGHT, buff=0.2)
        cnt.move_to([-3.2, 0.85, 0])
        self.play(LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.1), FadeIn(cnt), run_time=1.2)
        self.at("从中心出发")
        sp = arc_span(1, 1, 2.0, n=5, w=0.8, x0=-3.2)
        self.play(Create(sp), run_time=0.4)
        self.play(Transform(sp, arc_span(0, 2, 2.0, n=5, w=0.8, x0=-3.2)), run_time=0.6)
        self.at("最怕")
        self.clear(s, dots, cnt, sp, rt=0.4)
        n = 10
        aa = strip("a" * n, 1.8, w=0.6, size=28, x0=-3.2)
        counter = VGroup(T("比较", 24), Integer(0, font_size=36, color=C_RED)).arrange(RIGHT, buff=0.2).move_to([-3.2, 0.8, 0])
        self.play(FadeIn(aa), FadeIn(counter), run_time=0.5)
        total = 0
        span = None
        budget = max(2.5, self.cue_start("十个 a", self.now + 4) - self.now - 0.2)
        per = budget / (2 * n - 1)
        txt = "a" * n
        for c2 in range(2 * n - 1):          # 中心 c2/2：字符（偶数）或空隙（奇数），照讲义 expandAroundCenter 数比较
            left, right = c2 // 2, (c2 + 1) // 2
            while left >= 0 and right < n:
                total += 1
                if txt[left] != txt[right]:
                    break
                left -= 1
                right += 1
            a, b = left + 1, right - 1
            ns = arc_span(a, b, 1.8, n=n, w=0.6, x0=-3.2, col=C_RED)
            anims = [counter[1].animate.set_value(total)]
            if span is None:
                span = ns
                anims.append(Create(span))
            else:
                anims.append(Transform(span, ns))
            self.play(*anims, run_time=per)
        assert total == M.expand_count(txt) - 0, (total, M.expand_count(txt))   # 讲义还会试 (n-1, n) 这个空隙：0 次
        # 增长曲线：四个长度的比较次数
        rows = M.grow_table()
        base_y, top_h = -2.6, 4.2
        xs = [1.6 + k * 1.3 for k in range(4)]
        axis = Line([0.9, base_y, 0], [6.6, base_y, 0], color=C_GREY, stroke_width=2)
        bars, labs, nlabs = VGroup(), VGroup(), VGroup()
        for k, (nn, e, _) in enumerate(rows):
            h = max(0.04, e / rows[-1][1] * top_h)
            bar = Rectangle(width=0.7, height=h, stroke_width=0).set_fill(C_RED, 0.8)
            bar.move_to([xs[k], base_y, 0], aligned_edge=DOWN)
            bars.add(bar)
            labs.add(Text(str(e), font=MONO, font_size=20, color=C_RED).next_to(bar, UP, buff=0.08))
            nlabs.add(Text(f"n={nn}", font=MONO, font_size=18, color=C_GREY).next_to([xs[k], base_y, 0], DOWN, buff=0.12))
        self.at("十个 a")
        self.play(Create(axis), FadeIn(nlabs), run_time=0.4)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.2), FadeIn(labs), run_time=1.4)
        sq = MathTex(r"\Theta(n^2)", color=C_RED).scale(0.9).move_to([2.2, 1.0, 0])
        self.play(FadeIn(sq), run_time=0.5)
        self.hold()
        self.clear(head, aa, counter, span, axis, bars, labs, nlabs, sq)

    # ---------------------------------------------------------------- 插井号
    def sharp_beat(self):
        self.beat("sharp")
        head = T("插井号：所有回文都变成奇数长度", 30, C_YELLOW).move_to([0, 3.3, 0])
        s = strip(M.ABBA, 1.9, w=0.8, size=34)
        self.play(FadeIn(head), FadeIn(s), run_time=0.6)
        self.at("a b b a")
        t = M.manacher_trace(M.ABBA)["t"]
        s2 = strip(t, 0.5, w=0.8, size=34)
        moves = [ReplacementTransform(s[k].copy(), s2[2 * k + 1]) for k in range(4)]
        self.play(*moves, LaggedStart(*[FadeIn(s2[k]) for k in range(0, 9, 2)], lag_ratio=0.1), run_time=1.2)
        idx = VGroup(*[Text(str(k), font=MONO, font_size=18, color=C_GREY).next_to(s2[k], DOWN, buff=0.1) for k in range(9)])
        self.play(FadeIn(idx), s2[4][0].animate.set_stroke(C_YELLOW, 3), run_time=0.6)
        sp = arc_span(0, 8, 0.5, n=9, w=0.8, col=C_TEAL, h=0.35)
        ctr = T("中心落在井号上", 24, C_YELLOW).move_to([0, -1.0, 0])
        self.play(Create(sp), FadeIn(ctr), run_time=0.8)
        self.at("以下标 i")
        pv = M.manacher_trace(M.ABBA)["p"][4]
        f = VGroup(MathTex(rf"p[4] = {pv}", color=C_TEAL).scale(0.9),
                   MathTex(rf"p - 1 = {pv - 1} = |\mathtt{{abba}}|", color=WHITE).scale(0.9)).arrange(RIGHT, buff=0.8)
        f.move_to([0, -1.9, 0])
        self.play(FadeOut(ctr), FadeIn(f), run_time=0.8)
        self.hold()
        self.clear(head, s, s2, idx, sp, f)

    # ---------------------------------------------------------------- 主例：C 与 R
    def mark(self, i, txt, col, up=True):
        x = cx(i)
        y = ROW_Y + (0.75 if up else -0.0)
        tri = Triangle(color=col, fill_opacity=1, stroke_width=0).scale(0.09).rotate(PI).move_to([x, y, 0])
        lab = Text(txt, font=MONO, font_size=22, color=col).next_to(tri, UP, buff=0.05)
        return VGroup(tri, lab)

    def set_p(self, i, rt=0.25):
        v = Text(str(TR["p"][i]), font=MONO, font_size=22, color=C_TEAL).move_to([cx(i), P_Y, 0])
        self.pv[i] = v
        return FadeIn(v, shift=UP * 0.1)

    def mirror_beat(self):
        self.beat("mirror")
        t = TR["t"]
        row = strip(t, ROW_Y, w=W, size=24)
        idx = VGroup(*[Text(str(k), font=MONO, font_size=15, color=C_GREY).move_to([cx(k), IDX_Y, 0]) for k in range(21)])
        hdr = VGroup(T("下标", 18, C_GREY).move_to([-6.55, IDX_Y, 0]), Text("p", font=MONO, font_size=22, color=C_TEAL)
                     .move_to([-6.55, P_Y, 0]))
        self.row, self.idx, self.hdr, self.pv = row, idx, hdr, {}
        self.play(LaggedStart(*[FadeIn(c) for c in row], lag_ratio=0.03), FadeIn(idx), FadeIn(hdr), run_time=1.2)
        self.at("从左往右算")
        cur = Square(W * 0.94, stroke_color=C_YELLOW, stroke_width=3.5).move_to(row[0])
        self.ptr = cur
        self.play(Create(cur), run_time=0.3)
        for i in range(7):
            st = TR["steps"][i]
            sp = arc_span(i - st["p"] + 1, i + st["p"] - 1, ROW_Y, col=C_YELLOW, h=0.26)
            self.play(cur.animate.move_to(row[i]), FadeIn(sp), self.set_p(i), run_time=0.22)
            self.play(FadeOut(sp), run_time=0.12)
        self.at("算到下标七")
        st = TR["steps"][7]
        self.play(cur.animate.move_to(row[7]), run_time=0.3)
        sp = arc_span(7, 7, ROW_Y, col=C_YELLOW, h=0.26)
        self.play(FadeIn(sp), run_time=0.2)
        for r in range(1, st["p"]):
            self.play(Transform(sp, arc_span(7 - r, 7 + r, ROW_Y, col=C_YELLOW, h=0.26)), run_time=0.22)
        self.play(self.set_p(7), run_time=0.3)
        self.at("记下这个最右边界")
        band = Rectangle(width=(st["R2"] + 1) * W, height=W * 1.05, stroke_width=0).set_fill(C_TEAL, 0.16)
        band.move_to([(cx(0) + cx(st["R2"])) / 2, ROW_Y, 0])
        mC, mR = self.mark(st["C2"], "C", C_YELLOW), self.mark(st["R2"], "R", C_RED)
        self.add(band)
        self.bring_to_back(band)
        self.play(FadeIn(band), FadeOut(sp), FadeIn(mC), FadeIn(mR), run_time=0.8)
        self.band, self.mC, self.mR = band, mC, mR
        f = MathTex(r"C = 7,\quad R = 14", color=WHITE).scale(0.85).move_to([0, -0.5, 0])
        self.play(FadeIn(f), run_time=0.5)
        self.at("之后的下标 i")
        i, j = 10, 4
        arr = CurvedDoubleArrow(row[j].get_top() + UP * 0.12, row[i].get_top() + UP * 0.12, angle=-PI / 2.2,
                                color=C_PURPLE, tip_length=0.15)
        f2 = MathTex(r"\text{mirror} = 2C - i", color=C_PURPLE).scale(0.85).move_to([0, -1.4, 0])
        self.play(Create(arr), FadeIn(f2), run_time=1.0)
        self.hold()
        self.clear(arr, f, f2, rt=0.4)

    def mirror_span(self, m, col=C_PURPLE):
        p = TR["p"][m]
        return Rectangle(width=(2 * p - 1) * W, height=W * 0.98, stroke_color=col, stroke_width=3).move_to(
            [cx(m), ROW_Y, 0])

    def compare_mark(self, a, b, ok):
        col = C_GREEN if ok else C_RED
        la = Line(self.row[a].get_top() + UP * 0.04, self.row[a].get_top() + UP * 0.24, color=col, stroke_width=3)
        lb = Line(self.row[b].get_top() + UP * 0.04, self.row[b].get_top() + UP * 0.24, color=col, stroke_width=3)
        return VGroup(la, lb)

    def quick(self, i, rt=0.3):
        st = TR["steps"][i]
        self.play(self.ptr.animate.move_to(self.row[i]), self.set_p(i), run_time=rt)

    def inside_beat(self):
        self.beat("inside")
        head = T("情况一：镜像回文在大回文里面", 28, C_YELLOW).move_to([0, 3.4, 0])
        self.play(FadeIn(head), run_time=0.4)
        self.quick(8)
        self.at("比如下标九")
        st = TR["steps"][9]
        m = st["mirror"]
        self.play(self.ptr.animate.move_to(self.row[9]), run_time=0.3)
        ms = self.mirror_span(m)
        ml = Text(f"p[{m}]={TR['p'][m]}", font=MONO, font_size=20, color=C_PURPLE).move_to([cx(m), -0.35, 0])
        self.play(Create(ms), FadeIn(ml), run_time=0.7)
        copy = ms.copy()
        self.play(copy.animate(path_arc=-PI / 3).move_to([cx(9), ROW_Y, 0]), run_time=0.9)
        self.at("大回文左右对称")
        a, b, ok = st["cmps"][0]
        cm = self.compare_mark(a, b, ok)
        ln = DashedLine(cm[0].get_top(), cm[1].get_top(), color=C_RED, stroke_width=2)
        xm = Text("✗", font=FONT, font_size=26, color=C_RED).next_to(ln, UP, buff=0.06)
        self.play(self.set_p(9), run_time=0.4)
        self.play(Create(cm), Create(ln), FadeIn(xm), run_time=0.6)
        note = T("直接抄 p = 2，只比一次", 26, C_TEAL).move_to([0, -1.3, 0])
        self.play(FadeIn(note), run_time=0.5)
        self.hold(0.9)
        self.clear(ms, ml, copy, cm, ln, xm, note, head, rt=0.4)
        self.quick(10, rt=0.25)

    def edge_beat(self):
        self.beat("edge")
        head = T("情况二：镜像回文顶到了左边界", 28, C_YELLOW).move_to([0, 3.4, 0])
        self.play(FadeIn(head), run_time=0.4)
        st = TR["steps"][11]
        m = st["mirror"]
        self.at("下标十一")
        self.play(self.ptr.animate.move_to(self.row[11]), run_time=0.3)
        ms = self.mirror_span(m)
        ml = Text(f"p[{m}]={TR['p'][m]}", font=MONO, font_size=20, color=C_PURPLE).move_to([cx(m), -0.35, 0])
        L = 2 * st["C"] - st["R"]
        mL = self.mark(L, "L", C_RED)
        self.play(Create(ms), FadeIn(ml), FadeIn(mL), run_time=0.8)
        room = Text(f"R - i + 1 = {st['R'] - 11 + 1}", font=MONO, font_size=22, color=C_RED).move_to([cx(11) + 1.2, -0.35, 0])
        self.play(FadeIn(room), run_time=0.4)
        self.at("所以先取四")
        init = st["init"]
        sp = Rectangle(width=(2 * init - 1) * W, height=W * 0.98, stroke_color=C_YELLOW, stroke_width=3).move_to(
            [cx(11), ROW_Y, 0])
        self.play(FadeOut(ms), FadeOut(ml), Create(sp), run_time=0.6)
        cm_all = VGroup()
        p = init
        budget = max(2.0, self.cue_start("这一下", self.now + 4) - self.now + 2.0)
        per = budget / max(1, len(st["cmps"]))
        for a, b, ok in st["cmps"]:
            cm = self.compare_mark(a, b, ok)
            cm_all.add(cm)
            p += 1 if ok else 0
            self.play(Create(cm), Transform(sp, Rectangle(width=(2 * p - 1) * W, height=W * 0.98, stroke_color=C_YELLOW,
                                                         stroke_width=3).move_to([cx(11), ROW_Y, 0])), run_time=per)
        assert p == st["p"]
        self.at("半径十")
        band2 = Rectangle(width=(st["R2"] - (2 * st["C2"] - st["R2"]) + 1) * W, height=W * 1.05, stroke_width=0)
        band2.set_fill(C_TEAL, 0.16).move_to([(cx(2 * st["C2"] - st["R2"]) + cx(st["R2"])) / 2, ROW_Y, 0])
        nC, nR = self.mark(st["C2"], "C", C_YELLOW), self.mark(st["R2"], "R", C_RED)
        self.play(self.set_p(11), Transform(self.band, band2), Transform(self.mC, nC), Transform(self.mR, nR),
                  FadeOut(mL), FadeOut(room), run_time=1.0)
        f = MathTex(r"R:\ 14 \to 20", color=C_RED).scale(0.9).move_to([0, -1.3, 0])
        self.play(FadeIn(f), run_time=0.4)
        self.hold()
        self.clear(head, sp, cm_all, f, rt=0.4)

    def run_beat(self):
        self.beat("run")
        head = T("情况三：i 在 R 外面，只能从 1 开始扩", 28, C_YELLOW).move_to([0, 3.4, 0])
        self.play(FadeIn(head), run_time=0.4)
        for i in range(12, 21):
            self.quick(i, rt=0.3)
        self.at("把整串跑一遍")
        # R 的轨迹：阶梯只升不降
        base, top = -2.75, -0.55
        pts = [[cx(st["i"]), base + st["R2"] / 20 * (top - base), 0] for st in TR["steps"]]
        stairs = VMobject(stroke_color=C_RED, stroke_width=3)
        corners = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            corners += [[b[0], a[1], 0], b]
        stairs.set_points_as_corners(corners)
        dots = VGroup(*[Dot(p, radius=0.045, color=C_RED) for p in pts])
        rl = T("R", 22, C_RED).move_to([-6.55, (base + top) / 2, 0])
        self.play(Create(stairs), FadeIn(dots), FadeIn(rl), run_time=1.6)
        self.at("最长回文")
        best = TR["p"].index(max(TR["p"]))
        a, b = best - TR["p"][best] + 1, best + TR["p"][best] - 1
        hl = Rectangle(width=(b - a + 1) * W, height=W * 1.05, stroke_color=C_YELLOW, stroke_width=3.5).move_to(
            [(cx(a) + cx(b)) / 2, ROW_Y, 0])
        self.play(FadeOut(stairs), FadeOut(dots), FadeOut(rl), Create(hl),
                  self.pv[best].animate.set_color(C_YELLOW).scale(1.3), run_time=0.8)
        ans = VGroup(Text(" ".join(TR["answer"]), font=MONO, font_size=34, color=C_YELLOW),
                     T(f"长度 {len(TR['answer'])}", 28)).arrange(RIGHT, buff=0.6).move_to([0, -1.5, 0])
        self.play(FadeIn(ans, shift=UP * 0.2), run_time=0.7)
        self.hold()
        self.clear(head, hl, ans, self.row, self.idx, self.hdr, self.band, self.mC, self.mR, self.ptr,
                   *self.pv.values())

    # ---------------------------------------------------------------- 线性
    def linear_beat(self):
        self.beat("linear")
        head = T("为什么是线性的：盯住 R", 30, C_YELLOW).move_to([0, 3.3, 0])
        lines = VGroup(T("失败的比较：每个下标最多一次", 24),
                       T("往外成功一次：R 右移一格", 24, C_GREEN),
                       T("R 只增不减，最多走到末尾", 24, C_RED)).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        lines.move_to([-3.4, 1.0, 0])
        self.play(FadeIn(head), run_time=0.4)
        self.at("失败的比较")
        self.play(FadeIn(lines[0], shift=RIGHT * 0.2), run_time=0.5)
        self.play(FadeIn(lines[1], shift=RIGHT * 0.2), run_time=0.5)
        self.play(FadeIn(lines[2], shift=RIGHT * 0.2), run_time=0.5)
        self.at("八十个 a")
        rows = M.grow_table()
        base_y, top_h = -2.7, 4.6
        xs = [1.5 + k * 1.35 for k in range(4)]
        axis = Line([0.9, base_y, 0], [6.6, base_y, 0], color=C_GREY, stroke_width=2)
        bars, labs, nl = VGroup(), VGroup(), VGroup()
        for k, (nn, e, mm) in enumerate(rows):
            for v, dx, col in ((e, -0.2, C_RED), (mm, 0.2, C_GREEN)):
                h = max(0.03, v / rows[-1][1] * top_h)
                bar = Rectangle(width=0.36, height=h, stroke_width=0).set_fill(col, 0.85)
                bar.move_to([xs[k] + dx, base_y, 0], aligned_edge=DOWN)
                bars.add(bar)
            nl.add(Text(f"n={nn}", font=MONO, font_size=18, color=C_GREY).next_to([xs[k], base_y, 0], DOWN, buff=0.12))
        e80, m80 = rows[-1][1], rows[-1][2]
        labs.add(Text(str(e80), font=MONO, font_size=22, color=C_RED).next_to(bars[-2], LEFT, buff=0.1).align_to(bars[-2], UP))
        labs.add(Text(str(m80), font=MONO, font_size=22, color=C_GREEN).next_to(bars[-1], UP, buff=0.08).shift(RIGHT * 0.25))
        leg = VGroup(VGroup(Square(0.2, stroke_width=0).set_fill(C_RED, 0.85), T("中心扩展", 20)).arrange(RIGHT, buff=0.1),
                     VGroup(Square(0.2, stroke_width=0).set_fill(C_GREEN, 0.85), T("马拉车", 20)).arrange(RIGHT, buff=0.1)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to([2.0, 1.6, 0])
        self.play(Create(axis), FadeIn(nl), FadeIn(leg), run_time=0.5)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.1), run_time=1.4)
        self.play(FadeIn(labs), run_time=0.5)
        self.hold()
        self.clear(head, lines, axis, bars, labs, nl, leg)

    # ---------------------------------------------------------------- 总结
    def recap_beat(self):
        self.beat("recap")
        k = VGroup(T("KMP", 34, C_BLUE), T("前后缀对称", 26), T("模式指针跳回 next", 22, C_GREY)).arrange(DOWN, buff=0.3)
        m = VGroup(T("Manacher", 34, C_TEAL), T("镜像对称", 26), T("p[i] 抄 p[2C − i]", 22, C_GREY)).arrange(DOWN, buff=0.3)
        k.move_to([-3.3, 1.3, 0])
        m.move_to([3.3, 1.3, 0])
        bar = Line([0, 2.4, 0], [0, 0.1, 0], color=C_GREY, stroke_width=2)
        self.play(FadeIn(k, shift=RIGHT * 0.2), Create(bar), FadeIn(m, shift=LEFT * 0.2), run_time=1.0)
        self.at("在 R 里面")
        tag = T("在 R 里面少干活；突破 R，就推着 R 往右走", 28, C_YELLOW).move_to([0, -1.2, 0])
        self.play(FadeIn(tag, shift=UP * 0.2), run_time=0.7)
        self.hold(0.3)
        self.play(FadeOut(VGroup(k, m, bar, tag)), run_time=0.6, audit=False)
