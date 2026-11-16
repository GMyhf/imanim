"""最大子段和：从一维到二维（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。数组、dp 值、列和、十种上下边的结果、打家劫舍的 dp 全部来自 kadanedata
（讲义 max_subarray / max_subarray_o1 / max_submatrix / rob 原样；test_kadane.py 用暴力枚举对撞讲义输出与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kadanedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

AW = 1.1                                  # 一维数组格宽
AY, DY = 1.7, 0.1                         # 数组行 / dp 行
GX0, GW = -4.35, 0.95                     # 矩阵第 0 列中心、格宽
GY0, GH = 2.4, 0.8                        # 矩阵第 0 行中心、格高
CY = -1.5                                 # 列和行
RX0 = 1.4                                 # 右侧 Kadane 面板第 0 格


def num(v, scale=0.7, color=WHITE):
    return MathTex(str(v), color=color).scale(scale)


def box(w, h, color=C_GREY, sw=2.5):
    return Rectangle(width=w, height=h, stroke_color=color, stroke_width=sw)


def ax(i, n=len(D.T)):
    return (i - (n - 1) / 2) * AW


def gpos(i, j):
    return np.array([GX0 + GW * j, GY0 - GH * i, 0])


def grect(t, b, l, r, color=C_YELLOW, sw=5, buff=0.05):
    """矩阵上第 t..b 行、第 l..r 列那一块的外框。"""
    x0, x1 = GX0 + GW * (l - 0.5) - buff, GX0 + GW * (r + 0.5) + buff
    y0, y1 = GY0 - GH * (b + 0.5) - buff, GY0 - GH * (t - 0.5) + buff
    return Rectangle(width=x1 - x0, height=y1 - y0, stroke_color=color, stroke_width=sw).move_to(
        [(x0 + x1) / 2, (y0 + y1) / 2, 0])


def crect(l, r, color=C_YELLOW, y=CY, x0=GX0, w=GW, h=0.7):
    """一行格子里第 l..r 格的外框。"""
    a, b = x0 + w * (l - 0.5) - 0.05, x0 + w * (r + 0.5) + 0.05
    return Rectangle(width=b - a, height=h + 0.12, stroke_color=color, stroke_width=4.5).move_to([(a + b) / 2, y, 0])


class KadaneLesson(Lesson):
    def construct(self):
        for b in ("title", "state", "scan", "why", "matrix", "squash", "demo", "all", "rob", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：一排有正有负的数
    def title_beat(self):
        self.beat("title")
        n = len(D.T)
        boxes = VGroup(*[box(AW * 0.9, 0.7).move_to([ax(i), AY, 0]) for i in range(n)])
        labs = VGroup(*[num(v, 0.75, C_TEAL if v > 0 else (C_RED if v < 0 else WHITE)).move_to(boxes[i])
                        for i, v in enumerate(D.T)])
        self.play(LaggedStart(*[FadeIn(VGroup(b, l), shift=DOWN * 0.2) for b, l in zip(boxes, labs)], lag_ratio=0.12),
                  run_time=2.0)
        self.wait_until(self.cue_start("挑连续的一段", self.now))
        tries = [(1, 2), (5, 8), (3, 6)]
        rect = sm = None
        for l, r in tries:
            nr = crect(l, r, C_YELLOW, AY, ax(0), AW)
            ns = VGroup(T("和", 24, C_YELLOW), num(sum(D.T[l:r + 1]), 0.7, C_YELLOW)).arrange(RIGHT, buff=0.15)
            ns.next_to(nr, UP, buff=0.15)
            if rect is None:
                rect, sm = nr, ns
                self.play(Create(rect), FadeIn(sm), run_time=0.6)
            else:
                self.play(Transform(rect, nr), Transform(sm, ns), run_time=0.6)
            self.wait(0.3)
        self.wait_until(self.cue_start("枚举所有区间", self.now))
        cnt = n * (n + 1) // 2
        brute = T(f"{n} 个数，区间共 {cnt} 个：枚举是平方级", 28, C_GREY).move_to([0, 0.5, 0])
        self.play(FadeIn(brute, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("今天看", self.now))
        title = T("最大子段和", 60).move_to([0, -1.0, 0])
        sub = T("Kadane：一遍扫完，再推到二维", 32, C_YELLOW).next_to(title, DOWN, buff=0.25)
        self.play(FadeOut(rect), FadeOut(sm), brute.animate.set_opacity(0.4), Write(title),
                  FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(brute, title, sub)), run_time=0.6)
        self.aboxes, self.alabs = boxes, labs

    # ---------------------------------------------------------------- 状态：以 i 结尾
    def state_beat(self):
        self.beat("state")
        n = len(D.T)
        la = MathTex("a", color=C_GREY).scale(0.8).move_to([ax(0) - 1.0, AY, 0])
        ld = MathTex("dp", color=C_BLUE).scale(0.8).move_to([ax(0) - 1.0, DY, 0])
        dboxes = VGroup(*[box(AW * 0.9, 0.7, C_BLUE).move_to([ax(i), DY, 0]) for i in range(n)])
        idx = VGroup(*[MathTex(str(i), color=C_GREY).scale(0.5).next_to(self.aboxes[i], UP, buff=0.12)
                       for i in range(n)])
        self.play(FadeIn(la), FadeIn(ld), FadeIn(idx), Create(dboxes), run_time=1.0)
        defn = VGroup(MathTex("dp[i]", color=C_BLUE).scale(0.8), T("=", 28), T("以第 i 格结尾", 28, C_YELLOW),
                      T("的最大子段和", 28)).arrange(RIGHT, buff=0.15).move_to([0, -1.0, 0])
        self.play(FadeIn(defn, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("关键在", self.now))
        self.play(Indicate(defn[2], color=C_YELLOW, scale_factor=1.15), run_time=0.9)
        self.wait_until(self.cue_start("每一格只有两种", self.now))
        f = MathTex(r"dp[i] = \max(", r"a[i]", ",\ ", r"dp[i-1] + a[i]", ")").scale(0.8).move_to([-2.0, -1.95, 0])
        f[1].set_color(C_TEAL)
        f[3].set_color(C_BLUE)
        self.play(Write(f), run_time=1.1)
        l1 = T("另起一段", 22, C_TEAL).next_to(f[1], DOWN, buff=0.15)
        l2 = T("接上前面那段", 22, C_BLUE).next_to(f[3], DOWN, buff=0.15)
        self.wait_until(self.cue_start("接在前一格", self.now))
        self.play(FadeIn(l2, shift=UP * 0.1), run_time=0.5)
        self.wait_until(self.cue_start("或者自己另起", self.now + 1.2))
        self.play(FadeIn(l1, shift=UP * 0.1), run_time=0.5)
        self.wait_until(self.cue_start("答案是整个", self.now))
        ans = VGroup(T("答案：", 26, C_YELLOW), MathTex(r"\max(dp)", color=C_YELLOW).scale(0.8),
                     T("不一定是最后一格", 22, C_GREY)).arrange(RIGHT, buff=0.15).move_to([3.7, -1.95, 0])
        self.play(FadeIn(ans, shift=LEFT * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(defn, f, l1, l2, ans)), run_time=0.6)
        self.la, self.ld, self.dboxes, self.idx = la, ld, dboxes, idx

    # ---------------------------------------------------------------- 一路往右扫
    def scan_beat(self):
        self.beat("scan")
        dp, restart, start = D.kadane_trace(D.T)
        dl = {}
        bar = None
        best_i = None
        tri = Triangle(color=C_YELLOW, fill_opacity=1, stroke_width=0).scale(0.11)
        mark = VGroup(tri, T("最好", 20, C_YELLOW)).arrange(DOWN, buff=0.08)
        drops = VGroup()
        seglab = T("当前段", 20, C_TEAL).move_to([ax(0) - 1.0, 0.98, 0])

        def seg_bar(l, r):
            a, b = ax(l) - AW * 0.45, ax(r) + AW * 0.45
            return Line([a, 0.98, 0], [b, 0.98, 0], color=C_TEAL, stroke_width=8)

        def step(i, rt, extra=()):
            nonlocal bar, best_i
            lab = num(dp[i], 0.75, C_BLUE).move_to(self.dboxes[i])
            dl[i] = lab
            src = [self.alabs[i]] + ([] if restart[i] or i == 0 else [dl[i - 1]])
            anims = [TransformFromCopy(VGroup(*src), lab), *extra]
            nb = seg_bar(start[i], i)
            if bar is None:
                bar = nb
                anims += [Create(bar), FadeIn(seglab)]
            else:
                anims.append(Transform(bar, nb))
            if best_i is None or dp[i] > dp[best_i]:
                best_i = i
                pos = self.dboxes[i].get_bottom() + DOWN * (0.12 + mark.height / 2)
                if i == 0:
                    anims.append(FadeIn(mark.move_to(pos)))
                else:
                    anims.append(mark.animate.move_to(pos))
            self.play(*anims, run_time=rt)

        def drop(i, play=True):
            x = T("扔掉", 20, C_RED).next_to(self.dboxes[i], DOWN, buff=0.12)
            drops.add(x)
            anims = [self.dboxes[i].animate.set_stroke(C_RED), dl[i].animate.set_color(C_RED), FadeIn(x)]
            if not play:
                return anims
            self.play(*anims, run_time=0.5)

        self.wait_until(self.cue_start("第一格是负二", self.now))
        step(0, 0.8)
        self.wait_until(self.cue_start("接上只会拖累", self.now))
        step(1, 0.9, drop(0, play=False))                # 先挪走「最好」标记再标「扔掉」，两者同在 dp[0] 下面会叠字
        self.wait_until(self.cue_start("加上负三", self.now))
        step(2, 0.8)
        self.wait_until(self.cue_start("加上负三", self.now) + 1.3)
        drop(2)
        self.wait_until(self.cue_start("从四重新开始", self.now))
        step(3, 0.7)
        for i in (4, 5, 6):
            step(i, 0.55)
        self.wait_until(self.cue_start("第七格的六", self.now))
        self.play(Indicate(dl[6], color=C_YELLOW, scale_factor=1.4), self.dboxes[6].animate.set_stroke(C_YELLOW, 4),
                  run_time=0.9)
        self.wait_until(self.cue_start("后面减五", self.now))
        step(7, 0.7)
        step(8, 0.7)
        self.wait_until(self.cue_start("答案六", self.now))
        s, l, r = D.best_segment(D.T)
        hl = crect(l, r, C_YELLOW, AY, ax(0), AW)
        parts = [str(v) if v >= 0 else f"({v})" for v in D.T[l:r + 1]]
        eq = MathTex(" + ".join(parts) + f" = {s}", color=C_YELLOW).scale(0.8).move_to([0, -1.75, 0])
        self.play(Create(hl), FadeOut(bar), FadeOut(seglab), Write(eq), run_time=1.1)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(self.aboxes, self.alabs, self.la, self.ld, self.dboxes, self.idx, *dl.values(),
                                 mark, drops, hl, eq)), run_time=0.6)

    # ---------------------------------------------------------------- 为什么扔得放心
    def why_beat(self):
        self.beat("why")
        neg = Rectangle(width=2.2, height=0.75, stroke_color=C_RED, stroke_width=3).set_fill(C_RED, 0.15)
        rest = Rectangle(width=3.6, height=0.75, stroke_color=C_BLUE, stroke_width=3).set_fill(C_BLUE, 0.15)
        blocks = VGroup(neg, rest).arrange(RIGHT, buff=0).move_to([0, 2.4, 0])
        tn = T("前缀：和 < 0", 24, C_RED).move_to(neg)
        tr = T("后面任意一段", 24, C_BLUE).move_to(rest)
        self.wait_until(self.cue_start("一段和为负", self.now))
        self.play(FadeIn(blocks), FadeIn(tn), FadeIn(tr), run_time=0.9)
        ineq = VGroup(T("负前缀", 26, C_RED), MathTex(r"+\ S\ <\ S").scale(0.85)).arrange(RIGHT, buff=0.15)
        ineq.move_to([0, 1.45, 0])
        self.play(Write(ineq), run_time=0.9)
        self.wait_until(self.cue_start("所以前一格", self.now))
        rule = VGroup(MathTex(r"dp[i-1] < 0", color=C_BLUE).scale(0.8), MathTex(r"\Rightarrow").scale(0.8),
                      T("从当前格重新开始", 28, C_TEAL)).arrange(RIGHT, buff=0.25).move_to([0, 0.55, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("每个数只看一次", self.now))
        code = ["def max_subarray_o1(a):", "    best = cur = a[0]", "    for v in a[1:]:",
                "        cur = max(v, cur + v)", "        best = max(best, cur)", "    return best"]
        cw = Text("x" * 20, font=MONO, font_size=24).width / 20          # Text 会吃掉行首空格，缩进手工补
        lines = VGroup(*[Text(s.lstrip(), font=MONO, font_size=24, color="#D8DCE6") for s in code])
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        for ln, s in zip(lines, code):
            ln.shift(RIGHT * cw * (len(s) - len(s.lstrip())))
        lines.move_to([-2.3, -1.35, 0])
        self.play(FadeIn(lines, shift=UP * 0.2), run_time=0.8)
        c1 = VGroup(T("时间", 26, C_GREY), MathTex("O(n)", color=C_GREEN).scale(0.9)).arrange(RIGHT, buff=0.25)
        c2 = VGroup(T("空间", 26, C_GREY), MathTex("O(1)", color=C_GREEN).scale(0.9)).arrange(RIGHT, buff=0.25)
        c1.move_to([4.0, -0.85, 0])
        c2.move_to([4.0, -1.95, 0])
        self.play(FadeIn(c1, shift=LEFT * 0.2), Indicate(lines[2], color=C_YELLOW, scale_factor=1.05), run_time=0.9)
        self.wait_until(self.cue_start("只留两个变量", self.now))
        self.play(FadeIn(c2, shift=LEFT * 0.2), Indicate(lines[1], color=C_YELLOW, scale_factor=1.05), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(blocks, tn, tr, ineq, rule, lines, c1, c2)), run_time=0.6)

    # ---------------------------------------------------------------- 二维：最大子矩阵
    def matrix_beat(self):
        self.beat("matrix")
        n, m = len(D.MAT), len(D.MAT[0])
        gb, gl = {}, {}
        for i in range(n):
            for j in range(m):
                gb[(i, j)] = box(GW * 0.92, GH * 0.88).move_to(gpos(i, j))
                v = D.MAT[i][j]
                gl[(i, j)] = num(v, 0.7, C_TEAL if v > 0 else (C_RED if v < 0 else WHITE)).move_to(gpos(i, j))
        rl = VGroup(*[T(f"第{i + 1}行", 20, C_GREY).move_to(gpos(i, 0) + LEFT * 1.0) for i in range(n)])
        head = VGroup(T("最大子矩阵", 40), T("OpenJudge 02766", 22, C_GREY)).arrange(DOWN, buff=0.15)
        head.move_to([3.4, 2.5, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(VGroup(gb[k], gl[k]), scale=0.85) for k in gb], lag_ratio=0.04),
                  FadeIn(rl), run_time=1.6)
        self.wait_until(self.cue_start("四条边决定", self.now))
        t, b, l, r = 0, 2, 1, 2
        x0, x1 = GX0 + GW * (l - 0.5), GX0 + GW * (r + 0.5)
        y1, y0 = GY0 - GH * (t - 0.5), GY0 - GH * (b + 0.5)
        edges = VGroup(Line([x0, y1, 0], [x1, y1, 0], color=C_YELLOW, stroke_width=6),
                       Line([x0, y0, 0], [x1, y0, 0], color=C_YELLOW, stroke_width=6),
                       Line([x0, y0, 0], [x0, y1, 0], color=C_PURPLE, stroke_width=6),
                       Line([x1, y0, 0], [x1, y1, 0], color=C_PURPLE, stroke_width=6))
        legend = VGroup(T("上、下", 28, C_YELLOW), T("左、右", 28, C_PURPLE), T("四条边", 28)).arrange(RIGHT, buff=0.3)
        legend.move_to([3.4, 1.0, 0])
        self.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.3), FadeIn(legend), run_time=1.4)
        self.wait_until(self.cue_start("四条边全枚举", self.now))
        cnt = (n * (n + 1) // 2) * (m * (m + 1) // 2)
        msg = VGroup(T(f"子矩阵共 {cnt} 个", 28), T("每个再求和：太慢", 28, C_RED)).arrange(DOWN, buff=0.25)
        msg.move_to([3.4, -0.6, 0])
        self.play(FadeOut(edges), FadeIn(msg[0]), run_time=0.5)
        flick = None
        for (t, b, l, r) in [(0, 1, 0, 2), (2, 3, 1, 3), (1, 1, 0, 3), (0, 3, 2, 2), (1, 2, 1, 2), (3, 3, 0, 1)]:
            nr = grect(t, b, l, r, C_GREY, 4)
            if flick is None:
                flick = nr
                self.play(Create(flick), run_time=0.25)
            else:
                self.play(Transform(flick, nr), run_time=0.25)
        self.play(FadeIn(msg[1], shift=UP * 0.1), FadeOut(flick), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, legend, msg)), run_time=0.6)
        self.gb, self.gl, self.rl = gb, gl, rl

    # ---------------------------------------------------------------- 降维：按列压成一行
    def band(self, t, b):
        x0, x1 = GX0 - GW * 0.5 - 0.08, GX0 + GW * 3.5 + 0.08
        y1, y0 = GY0 - GH * (t - 0.5) + 0.04, GY0 - GH * (b + 0.5) - 0.04
        r = Rectangle(width=x1 - x0, height=y1 - y0, stroke_color=C_YELLOW, stroke_width=3)
        r.set_fill(C_YELLOW, 0.1).move_to([(x0 + x1) / 2, (y0 + y1) / 2, 0]).set_z_index(-1)
        tl = T("上边", 22, C_YELLOW).next_to(r.get_corner(UR), RIGHT, buff=0.15).shift(DOWN * 0.2)
        bl = T("下边", 22, C_YELLOW).next_to(r.get_corner(DR), RIGHT, buff=0.15).shift(UP * 0.2)
        if t == b:
            tl = T("上边 = 下边", 22, C_YELLOW).next_to(r, RIGHT, buff=0.15)
            bl = VGroup()
        return VGroup(r, tl, bl)

    def col_labels(self, col, color=WHITE):
        return VGroup(*[num(v, 0.7, color).move_to([GX0 + GW * j, CY, 0]) for j, v in enumerate(col)])

    def squash_beat(self):
        self.beat("squash")
        m = len(D.MAT[0])
        log = {(t, b): c for t, b, c, *_ in D.submatrix_log(D.MAT)}
        cboxes = VGroup(*[box(GW * 0.92, 0.7, C_BLUE).move_to([GX0 + GW * j, CY, 0]) for j in range(m)])
        clab = T("列和", 22, C_BLUE).move_to([GX0 - 1.0, CY, 0])
        title = T("固定上边和下边", 34, C_YELLOW).move_to([3.4, 2.5, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.wait_until(self.cue_start("上边取第二行", self.now))
        top = 1
        bd = self.band(top, top)
        self.play(FadeIn(bd), run_time=0.7)
        self.wait_until(self.cue_start("下边也是第二行", self.now))
        cl = self.col_labels(log[(top, top)])
        self.play(Create(cboxes), FadeIn(clab),
                  *[TransformFromCopy(self.gl[(top, j)], cl[j]) for j in range(m)], run_time=1.0)
        note = None
        for b, key in ((2, "扩到第三行"), (3, "再扩到第四行")):
            self.wait_until(self.cue_start(key, self.now))
            nb = self.band(top, b)
            self.play(Transform(bd, nb), run_time=0.6)
            cps = VGroup(*[self.gl[(b, j)].copy() for j in range(m)])
            self.add(cps)
            self.play(*[cps[j].animate.move_to(cl[j].get_center() + UP * 0.02) for j in range(m)],
                      run_time=0.9, audit=False)
            new = self.col_labels(log[(top, b)])
            self.play(FadeOut(cps), *[Transform(cl[j], new[j]) for j in range(m)], run_time=0.5)
            if note is None:
                note = T("每列加上新的一行", 24, C_GREY).move_to([3.4, CY, 0])
                self.play(FadeIn(note), run_time=0.4)
        self.wait_until(self.cue_start("任意一段", self.now))
        col = log[(top, 3)]
        l, r = 1, 3
        seg = crect(l, r, C_BLUE)
        blk = grect(top, 3, l, r, C_BLUE, 4)
        s1 = sum(col[l:r + 1])
        s2 = sum(D.MAT[i][j] for i in range(top, 4) for j in range(l, r + 1))
        eq = VGroup(T("段和", 26, C_BLUE), num(s1, 0.8, C_BLUE), T("= 子矩阵和", 26, C_BLUE), num(s2, 0.8, C_BLUE))
        eq.arrange(RIGHT, buff=0.15).move_to([3.4, 0.6, 0])
        self.play(FadeOut(note), Create(seg), Create(blk), run_time=0.9)
        self.wait_until(self.cue_start("和也相等", self.now))
        self.play(FadeIn(eq, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(seg, blk, eq, title)), run_time=0.6)
        self.bd, self.cboxes, self.cl, self.clab, self.top = bd, cboxes, cl, clab, top

    # ---------------------------------------------------------------- 对列和跑 Kadane
    def demo_beat(self):
        self.beat("demo")
        col = next(c for t, b, c, *_ in D.submatrix_log(D.MAT) if (t, b) == (self.top, 3))
        dp, _, _ = D.kadane_trace(col)
        m = len(col)
        head = T("对这一行跑 Kadane", 30, C_YELLOW).move_to([3.0, 2.6, 0])
        rb = VGroup(*[box(1.0, 0.7, C_BLUE).move_to([RX0 + 1.1 * j, 1.5, 0]) for j in range(m)])
        rd = VGroup(*[box(1.0, 0.7, C_TEAL).move_to([RX0 + 1.1 * j, 0.4, 0]) for j in range(m)])
        rl1 = T("列和", 22, C_BLUE).next_to(rb, LEFT, buff=0.25)
        rl2 = MathTex("dp", color=C_TEAL).scale(0.7).next_to(rd, LEFT, buff=0.25)
        rv = VGroup(*[num(v, 0.7).move_to(rb[j]) for j, v in enumerate(col)])
        self.play(FadeIn(head), FadeIn(rb), FadeIn(rl1), FadeIn(rd), FadeIn(rl2),
                  *[TransformFromCopy(self.cl[j], rv[j]) for j in range(m)], run_time=1.0)
        dv = {}
        for j in range(m):
            if j == 1:
                self.wait_until(self.cue_start("加十一", self.now))
            dv[j] = num(dp[j], 0.7, C_TEAL).move_to(rd[j])
            src = [rv[j]] + ([dv[j - 1]] if j and dp[j - 1] >= 0 else [])
            self.play(TransformFromCopy(VGroup(*src), dv[j]), run_time=0.75)
        s, l, r = D.best_segment(col)
        bi = dp.index(s)
        self.wait_until(self.cue_start("最大是十五", self.now))
        h1 = crect(l, r, C_YELLOW)
        h2 = crect(l, r, C_YELLOW, 1.5, RX0, 1.1)
        self.play(rd[bi].animate.set_stroke(C_YELLOW, 4), Indicate(dv[bi], color=C_YELLOW, scale_factor=1.4),
                  Create(h1), Create(h2), run_time=1.0)
        self.wait_until(self.cue_start("回到矩阵上", self.now))
        blk = grect(self.top, 3, l, r, C_YELLOW, 6)
        self.play(Create(blk), run_time=1.0)
        self.wait_until(self.cue_start("加起来正是", self.now))
        vals = [D.MAT[i][j] for i in range(self.top, 4) for j in range(l, r + 1)]
        eq = MathTex(" + ".join(str(v) if v >= 0 else f"({v})" for v in vals) + f" = {sum(vals)}",
                     color=C_YELLOW).scale(0.7).move_to([3.0, -0.75, 0])
        self.play(Write(eq), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, rb, rd, rl1, rl2, rv, *dv.values(), h1, h2, blk, eq)), run_time=0.6)

    # ---------------------------------------------------------------- 十种上下边
    def all_beat(self):
        self.beat("all")
        log = D.submatrix_log(D.MAT)
        hx = (1.35, 2.45, 3.25, 4.05, 4.85, 6.0)
        head = VGroup(T("行", 22, C_GREY).move_to([hx[0], 2.95, 0]), T("列和", 22, C_GREY).move_to([3.65, 2.95, 0]),
                      T("最大段", 22, C_GREY).move_to([hx[5], 2.95, 0]))
        rule = Line([0.95, 2.7, 0], [6.6, 2.7, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(head), Create(rule), run_time=0.6)
        rows = VGroup()
        t_end = self.cue_start("每种取法", self.now + 8)
        step = max(0.45, min(1.1, (t_end - self.now) / len(log)))
        for k, (t, b, col, s, l, r, _) in enumerate(log):
            y = 2.42 - 0.47 * k
            lab = T(f"{t + 1}–{b + 1}", 22).move_to([hx[0], y, 0])
            cs = VGroup(*[num(v, 0.55, C_YELLOW if l <= j <= r else "#D8DCE6").move_to([hx[1 + j], y, 0])
                          for j, v in enumerate(col)])
            bs = num(s, 0.6, C_GREEN).move_to([hx[5], y, 0])
            row = VGroup(lab, cs, bs)
            rows.add(row)
            new = self.col_labels(col)
            for j in range(len(col)):
                if l <= j <= r:
                    new[j].set_color(C_YELLOW)
            self.play(Transform(self.bd, self.band(t, b)), *[Transform(self.cl[j], new[j]) for j in range(len(col))],
                      FadeIn(row, shift=LEFT * 0.15), run_time=step)
        self.wait_until(self.cue_start("立方级", self.now))
        cx = VGroup(MathTex(r"O(n^2)", color=C_BLUE).scale(0.7), T("种 ×", 24), MathTex(r"O(n)", color=C_TEAL).scale(0.7),
                    MathTex(r"= O(n^3)", color=C_YELLOW).scale(0.75)).arrange(RIGHT, buff=0.15).move_to([3.1, -2.45, 0])
        self.play(FadeIn(cx, shift=UP * 0.15), run_time=0.8)
        self.wait_until(self.cue_start("十种里最大的", self.now))
        s, t, b, l, r = D.best_submatrix(D.MAT)
        k = next(k for k, e in enumerate(log) if (e[0], e[1]) == (t, b))
        hl = SurroundingRectangle(rows[k], color=C_YELLOW, buff=0.08)
        new = self.col_labels(log[k][2])
        for j in range(l, r + 1):
            new[j].set_color(C_YELLOW)
        blk = grect(t, b, l, r, C_YELLOW, 6)
        self.play(Create(hl), Transform(self.bd, self.band(t, b)), *[Transform(self.cl[j], new[j]) for j in range(len(new))],
                  Create(blk), *[rows[q].animate.set_opacity(0.4) for q in range(len(rows)) if q != k], run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, rule, rows, cx, hl, blk, self.bd, self.cboxes, self.cl, self.clab, self.rl,
                                 *self.gb.values(), *self.gl.values())), run_time=0.6)

    # ---------------------------------------------------------------- 打家劫舍
    def rob_beat(self):
        self.beat("rob")
        h = D.HOUSES
        n = len(h)
        xs = [(k - (n - 1) / 2) * 2.0 for k in range(n)]
        title = T("打家劫舍", 40).move_to([0, 3.15, 0])
        self.play(Write(title), run_time=0.8)
        self.wait_until(self.cue_start("一排房子", self.now))
        houses, money = VGroup(), VGroup()
        for k, v in enumerate(h):
            body = Square(1.05, stroke_color=C_GREY, stroke_width=3).move_to([xs[k], 1.25, 0])
            roof = Polygon(body.get_corner(UL) + LEFT * 0.12, body.get_corner(UR) + RIGHT * 0.12,
                           body.get_top() + UP * 0.55, stroke_color=C_GREY, stroke_width=3)
            houses.add(VGroup(body, roof))
            money.add(num(v, 0.85, C_YELLOW).move_to(body))
        self.play(LaggedStart(*[FadeIn(VGroup(hh, mm), shift=UP * 0.2) for hh, mm in zip(houses, money)],
                              lag_ratio=0.2), run_time=1.6)
        self.wait_until(self.cue_start("不能偷相邻", self.now))
        x = Cross(Square(0.35), stroke_color=C_RED, stroke_width=5).move_to([(xs[1] + xs[2]) / 2, 1.25, 0])
        nadj = T("相邻两家不能都偷", 24, C_RED).move_to([(xs[1] + xs[2]) / 2, 0.25, 0])
        self.play(Create(x), FadeIn(nadj), houses[1][0].animate.set_stroke(C_RED), houses[2][0].animate.set_stroke(C_RED),
                  run_time=0.8)
        self.wait_until(self.cue_start("每到一家", self.now))
        f = MathTex(r"dp[i] = \max(", r"dp[i-1]", ",\ ", r"dp[i-2] + v_i", ")").scale(0.8).move_to([0, -1.55, 0])
        f[1].set_color(C_GREY)
        f[3].set_color(C_TEAL)
        lb1 = T("不偷", 22, C_GREY).next_to(f[1], DOWN, buff=0.15)
        lb2 = T("偷", 22, C_TEAL).next_to(f[3], DOWN, buff=0.15)
        self.play(FadeOut(x), FadeOut(nadj), houses[1][0].animate.set_stroke(C_GREY),
                  houses[2][0].animate.set_stroke(C_GREY), Write(f), run_time=1.0)
        self.wait_until(self.cue_start("沿用到前一家", self.now))
        self.play(FadeIn(lb1, shift=UP * 0.1), run_time=0.5)
        self.wait_until(self.cue_start("偷，就用", self.now))
        self.play(FadeIn(lb2, shift=UP * 0.1), run_time=0.5)
        dpb = VGroup(*[box(1.0, 0.7, C_BLUE).move_to([xs[k], -0.3, 0]) for k in range(n)])
        dl = MathTex("dp", color=C_BLUE).scale(0.7).next_to(dpb, LEFT, buff=0.3)
        self.play(Create(dpb), FadeIn(dl), run_time=0.8)
        self.wait_until(self.cue_start("依次是", self.now))
        dp = D.rob_trace(h)
        dv = []
        for k in range(n):
            took = dp[k] != (dp[k - 1] if k else 0)
            lab = num(dp[k], 0.75, C_TEAL if took else C_GREY).move_to(dpb[k])
            src = [money[k]] + ([dv[k - 2]] if k >= 2 else []) if took else [dv[k - 1]]
            dv.append(lab)
            self.play(TransformFromCopy(VGroup(*src), lab), run_time=0.6)
        self.wait_until(self.cue_start("答案十二", self.now))
        picks = D.rob_choice(h)
        eq = MathTex(" + ".join(str(h[k]) for k in picks) + f" = {dp[-1]}", color=C_YELLOW).scale(0.85)
        eq.move_to([0, -1.55, 0])
        self.play(*[houses[k].animate.set_stroke(C_YELLOW, 5) for k in picks],
                  *[money[k].animate.scale(1.2) for k in picks], dpb[-1].animate.set_stroke(C_YELLOW, 4),
                  FadeOut(VGroup(lb1, lb2)), ReplacementTransform(f, eq), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, houses, money, dpb, dl, *dv, eq)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        cards = VGroup()
        for name, body, col in (("一维：一遍扫完", "以这一格结尾 / 到这一格为止\n每格只看左边一两格", C_TEAL),
                                ("二维：先固定一维", "固定上下边，按列压成一行\n再跑一遍 Kadane", C_YELLOW)):
            bx = RoundedRectangle(corner_radius=0.2, width=6.0, height=2.8, stroke_color=col, stroke_width=3)
            txt = VGroup(T(name, 34, col), T(body, 27, "#D8DCE6", line_spacing=1.0)).arrange(DOWN, buff=0.4).move_to(bx)
            cards.add(VGroup(bx, txt))
        cards.arrange(RIGHT, buff=0.5).move_to([0, 0.6, 0])
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.9)
        self.wait_until(self.cue_start("遇到二维", self.now))
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 10 周 2.7 · 第 11 周 2.3–2.4 · M02766", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
