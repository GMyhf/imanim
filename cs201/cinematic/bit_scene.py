"""树状数组：最低位的一（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。C 数组、查询/修改跳过的下标、蚂蚁扫描的每一步都来自
bitdata（讲义附录 A 与 M20018 代码原样插桩；test_bit.py 对撞讲义打印、暴力前缀和与 O(n²) 数对）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bitdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

LVC = [C_TEAL, C_BLUE, C_GREEN, C_YELLOW, C_PURPLE]      # 管辖长度 1/2/4/8/16 各一种颜色
X0, DX, CW = -5.0, 0.72, 0.62                            # 16 格的位置：第 i 格中心 X0 + (i-1)·DX


def X(i):
    return X0 + (i - 1) * DX


def level(i):
    return D.lowbit(i).bit_length() - 1


def num(v, color=WHITE, s=0.6):
    return MathTex(str(v), color=color).scale(s)


class Row(VGroup):
    """一排格子：cells / vals / idx（下标在格子上方）。"""

    def __init__(self, values, y, xf=X, cw=CW, color=C_GREY, idx=True, s=0.6):
        super().__init__()
        self.xf, self.y = xf, y
        self.cells = VGroup(*[RoundedRectangle(corner_radius=0.06, width=cw, height=0.5, stroke_color=color,
                                               stroke_width=2).set_fill(color, 0.12).move_to([xf(i + 1), y, 0])
                              for i in range(len(values))])
        self.vals = VGroup(*[num(v, s=s).move_to(c) for v, c in zip(values, self.cells)])
        self.idx = VGroup(*[MathTex(str(i + 1), color=C_GREY).scale(0.42).next_to(c, UP, buff=0.1)
                            for i, c in enumerate(self.cells)]) if idx else VGroup()
        self.add(self.cells, self.vals, self.idx)


class Bars(VGroup):
    """树状数组的管辖段：第 i 格画成横条 [i-lowbit(i)+1, i]，按长度分层；edges[i] 连到 i+lowbit(i)。"""

    def __init__(self, values, n, xf=X, cw=CW, y0=-1.45, dy=0.68, h=0.42, s=0.55):
        super().__init__()
        self.n, self.xf, self.cw = n, xf, cw
        self.bar, self.lab, self.edges = {}, {}, {}
        for i in range(1, n + 1):
            lo, hi = D.cover(i)
            col = LVC[level(i)]
            y = y0 + level(i) * dy
            r = Rectangle(width=xf(hi) - xf(lo) + cw, height=h, stroke_color=col, stroke_width=2.5)
            r.set_fill(col, 0.22).move_to([(xf(lo) + xf(hi)) / 2, y, 0])
            self.bar[i] = r
            self.lab[i] = num(values[i], s=s).move_to([xf(i), y, 0])
        for i in range(1, n + 1):
            p = i + D.lowbit(i)
            if p <= n:
                self.edges[i] = Line([xf(i), self.bar[i].get_top()[1], 0], [xf(i), self.bar[p].get_bottom()[1], 0],
                                     stroke_color=C_GREY, stroke_width=2, stroke_opacity=0.6)
        self.add(*self.edges.values(), *self.bar.values(), *self.lab.values())

    def group(self, i):
        return VGroup(self.bar[i], self.lab[i])


class BITLesson(Lesson):
    def construct(self):
        for b in ("title", "dilemma", "lowbit", "cover", "query", "update", "cost", "ants", "scan", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    # ---------------------------------------------------------------- 片头：一排十六个数
    def title_beat(self):
        self.beat("title")
        row = Row(D.A, 0.0)
        self.A = row
        self.play(LaggedStart(*[FadeIn(VGroup(c, v, k), shift=DOWN * 0.2)
                                for c, v, k in zip(row.cells, row.vals, row.idx)], lag_ratio=0.06), run_time=1.6)
        self.at("前十四个数")
        br = Brace(VGroup(*row.cells[:14]), DOWN, color=C_BLUE)
        q = VGroup(T("前 14 个数的和", 28, C_BLUE), MathTex("=\\,?", color=C_BLUE).scale(0.9)).arrange(RIGHT, buff=0.15)
        q.next_to(br, DOWN, buff=0.15)
        self.play(GrowFromCenter(br), FadeIn(q, shift=UP * 0.2), run_time=0.9)
        self.at("改掉")
        new6 = num(9, C_RED).move_to(row.cells[5])
        self.play(Indicate(row.cells[5], color=C_RED), Transform(row.vals[5], new6), run_time=0.8)
        self.play(Transform(row.vals[5], num(6).move_to(row.cells[5])), run_time=0.5)
        self.at("树状数组")
        title = T("树状数组", 80).move_to([0, 2.5, 0])
        sub = T("Binary Indexed Tree · Fenwick 1994", 26, C_GREY).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(br, q, title, sub)), row.animate.shift(UP * 1.6), run_time=0.6)

    # ---------------------------------------------------------------- 两难：原数组 vs 前缀和
    def dilemma_beat(self):
        self.beat("dilemma")
        A = self.A
        tagA = T("原数组", 24, C_GREY).next_to(A.cells, LEFT, buff=0.15)
        self.play(FadeIn(tagA), run_time=0.4)
        self.at("改一个数")
        self.play(Indicate(A.cells[2], color=C_GREEN, scale_factor=1.25), run_time=0.7)
        costA = VGroup(T("修改 1 步", 24, C_GREEN), MathTex("O(1)", color=C_GREEN).scale(0.7)).arrange(RIGHT, buff=0.15)
        costA.move_to([3.3, 0.95, 0])
        self.play(FadeIn(costA), run_time=0.4)
        self.at("从头加过去")
        self.play(LaggedStart(*[c.animate.set_fill(C_RED, 0.45) for c in A.cells[:14]], lag_ratio=0.25), run_time=2.2)
        qA = VGroup(T("查询 14 步", 24, C_RED), MathTex("O(n)", color=C_RED).scale(0.7)).arrange(RIGHT, buff=0.15)
        qA.move_to([-2.6, 0.95, 0])
        self.play(FadeIn(qA), A.cells.animate.set_fill(C_GREY, 0.12), run_time=0.6)
        self.at("前缀和")
        S = Row(D.PREFIX[1:], -0.9, idx=False, color=C_BLUE, s=0.5)
        tagS = T("前缀和", 24, C_BLUE).next_to(S.cells, LEFT, buff=0.15)
        self.play(TransformFromCopy(A.cells, S.cells), FadeIn(S.vals, shift=DOWN * 0.3), FadeIn(tagS), run_time=1.2)
        self.at("查询一步")
        self.play(S.cells[13].animate.set_fill(C_GREEN, 0.6), Indicate(S.vals[13], color=C_GREEN), run_time=0.8)
        qS = VGroup(T("查询 1 步", 24, C_GREEN), MathTex("O(1)", color=C_GREEN).scale(0.7)).arrange(RIGHT, buff=0.15)
        qS.move_to([-2.6, -1.55, 0])
        self.play(FadeIn(qS), run_time=0.4)
        self.at("第三个数变了")
        self.play(Indicate(A.cells[2], color=C_RED, scale_factor=1.25), S.cells[13].animate.set_fill(C_BLUE, 0.12),
                  run_time=0.6)
        self.play(LaggedStart(*[c.animate.set_fill(C_RED, 0.5) for c in S.cells[2:]], lag_ratio=0.15), run_time=1.8)
        uS = VGroup(T(f"修改 {D.PREFIX_TOUCH} 处", 24, C_RED), MathTex("O(n)", color=C_RED).scale(0.7))
        uS.arrange(RIGHT, buff=0.15).move_to([3.3, -1.55, 0])
        self.play(FadeIn(uS), run_time=0.4)
        self.at("两头都")
        wish = VGroup(T("想要：查询、修改都是", 30, C_YELLOW), MathTex(r"O(\log n)", color=C_YELLOW))
        wish.arrange(RIGHT, buff=0.2).move_to([0.4, -2.45, 0])
        self.play(FadeIn(wish, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(A, tagA, costA, qA, S, tagS, qS, uS, wish)), run_time=0.6)

    # ---------------------------------------------------------------- lowbit：x & -x
    def lowbit_beat(self):
        self.beat("lowbit")
        ys = [1.6, 0.75, -0.1, -1.05]
        labels = ["x", "取反 ~x", "-x = ~x + 1", "x & -x"]
        decs = ["12", "", "-12", "4"]
        cols = [WHITE, C_GREY, C_BLUE, C_YELLOW]
        rows = []
        for (name, b), lab, dec, y, col in zip(D.LB_ROWS, labels, decs, ys, cols):
            bits = VGroup(*[Text(ch, font=MONO, font_size=38, color=col).move_to([-1.2 + 0.55 * k, y, 0])
                            for k, ch in enumerate(b)])
            l = (T(lab, 26, col) if not lab[0].isascii() else Text(lab, font=MONO, font_size=26, color=col))
            l.next_to([-1.75, y, 0], LEFT, buff=0.2)
            d = MathTex(dec, color=col).scale(0.85).move_to([4.3, y, 0]) if dec else VGroup()
            rows.append(VGroup(l, bits, d))
        rule = Line([-1.6, -0.58, 0], [2.95, -0.58, 0], stroke_color=C_GREY, stroke_width=2)
        self.at("十二写成二进制")
        self.play(FadeIn(rows[0], shift=RIGHT * 0.2), run_time=0.8)
        self.at("按位取反")
        self.play(TransformFromCopy(rows[0][1], rows[1][1]), FadeIn(rows[1][0]), run_time=0.9)
        self.play(TransformFromCopy(rows[1][1], rows[2][1]), FadeIn(rows[2][0]), FadeIn(rows[2][2]), run_time=0.9)
        self.at("按位与")
        col5 = SurroundingRectangle(VGroup(rows[0][1][5], rows[2][1][5]), color=C_YELLOW, buff=0.1)
        self.play(Create(rule), Create(col5), run_time=0.6)
        self.play(TransformFromCopy(VGroup(rows[0][1], rows[2][1]), rows[3][1]), FadeIn(rows[3][0]),
                  run_time=1.0)
        self.play(FadeIn(rows[3][2]), Indicate(rows[3][1][5], color=C_YELLOW, scale_factor=1.5), run_time=0.8)
        self.at("代码里")
        code = Text("lowbit(x) = x & -x", font=MONO, font_size=34, color=C_YELLOW).move_to([0.4, 2.75, 0])
        self.play(FadeIn(code, shift=DOWN * 0.2), run_time=0.7)
        self.at("同样")
        more = VGroup()
        for x, lb in D.LB_MORE:
            more.add(VGroup(Text(f"{x} = {x:b}", font=MONO, font_size=26, color=C_GREY),
                            MathTex(r"\to", color=C_GREY).scale(0.7),
                            Text(str(lb), font=MONO, font_size=26, color=C_YELLOW)).arrange(RIGHT, buff=0.15))
        more.arrange(RIGHT, buff=0.9).move_to([0.4, -2.2, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in more], lag_ratio=0.5), run_time=1.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*rows, rule, col5, more)), code.animate.scale(0.8).move_to([-3.6, 3.2, 0]),
                  run_time=0.6)
        self.code = code

    # ---------------------------------------------------------------- 每格管一段：长成一棵树
    def cover_beat(self):
        self.beat("cover")
        A = Row(D.A, -2.45)
        A.idx.shift(UP * 0.02)
        B = Bars(D.C, D.N)
        self.A, self.B = A, B
        defin = MathTex(r"C[i] = A[i-\mathrm{lowbit}(i)+1] + \cdots + A[i]", color=WHITE).scale(0.8)
        defin.move_to([1.6, 2.45, 0])
        self.play(FadeIn(A), Write(defin), run_time=1.2)
        keys = ["只管自己", "二管两个", "四管四个", "八管八个", "十六管"]
        for lv, key in enumerate(keys):
            self.at(key)
            ids = [i for i in range(1, D.N + 1) if level(i) == lv]
            rt = 0.9 if lv < 4 else 1.1
            self.play(*[GrowFromEdge(B.bar[i], RIGHT) for i in ids], *[FadeIn(B.lab[i]) for i in ids], run_time=rt)
        self.at("一层层叠起来")
        self.play(LaggedStart(*[Create(e) for e in B.edges.values()], lag_ratio=0.08), run_time=1.8)
        self.add(*B.bar.values(), *B.lab.values())     # 连线放到横条底下
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(defin), run_time=0.5)

    # ---------------------------------------------------------------- 查询：往下减
    def query_beat(self):
        self.beat("query")
        A, B = self.A, self.B
        trk = Text(f"i = {D.Q_I:>2} = {D.Q_I:05b}", font=MONO, font_size=32).move_to([-2.4, 2.45, 0])
        self.play(FadeIn(trk), run_time=0.5)
        others = [i for i in range(1, D.N + 1) if i not in D.Q_PATH]
        self.play(*[B.bar[i].animate.set_fill(opacity=0.06).set_stroke(opacity=0.3) for i in others],
                  *[B.lab[i].animate.set_opacity(0.25) for i in others], run_time=0.6)
        keys = ["第十四格管", "第十二格管", "第八格管"]
        terms = VGroup()
        for k, (j, key) in enumerate(zip(D.Q_PATH, keys)):
            self.at(key)
            lo, hi = D.cover(j)
            col = LVC[level(j)]
            t = Text(f"i = {j:>2} = {j:05b}", font=MONO, font_size=32).move_to(trk)
            term = num(D.C[j], col, 0.85)
            extra = []
            if k:
                plus = MathTex("+", color=WHITE).scale(0.85)
                terms.add(plus)
                extra.append(FadeIn(plus))
            terms.add(term)
            terms.arrange(RIGHT, buff=0.18).move_to([1.6, 2.45, 0], aligned_edge=LEFT)
            self.play(Transform(trk, t), B.bar[j].animate.set_fill(col, 0.6).set_stroke(width=5),
                      *[A.cells[m - 1].animate.set_fill(col, 0.5) for m in range(lo, hi + 1)],
                      TransformFromCopy(B.lab[j], term), *extra, run_time=1.0)
        self.at("到零")
        self.play(Transform(trk, Text(" i =  0  停", font=MONO, font_size=32, color=C_GREY).move_to(trk)),
                  run_time=0.6)
        self.at("三段拼起来")
        br = Brace(VGroup(*A.cells[:D.Q_I]), DOWN, color=WHITE, buff=0.06)
        tot = VGroup(MathTex("=", color=WHITE).scale(0.85), num(D.Q_SUM, C_YELLOW, 0.95)).arrange(RIGHT, buff=0.18)
        tot.next_to(terms, RIGHT, buff=0.18)
        self.play(GrowFromCenter(br), FadeIn(tot, shift=LEFT * 0.2), run_time=1.0)
        self.at("抹掉一个一")
        bits = VGroup(*[Text(f"{j:05b}", font=MONO, font_size=26, color=LVC[level(j)]) for j in D.Q_PATH],
                      Text("00000", font=MONO, font_size=26, color=C_GREY))
        bits.arrange(RIGHT, buff=0.55).move_to([-2.4, 3.3, 0]).shift(RIGHT * 1.2)
        arrows = VGroup(*[Arrow(bits[k].get_right(), bits[k + 1].get_left(), buff=0.08, stroke_width=3,
                                max_tip_length_to_length_ratio=0.3, color=C_GREY) for k in range(len(bits) - 1)])
        self.play(FadeOut(self.code), LaggedStart(*[FadeIn(b) for b in bits], lag_ratio=0.3), Create(arrows),
                  run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(trk, terms, tot, br, bits, arrows)),
                  *[B.bar[i].animate.set_fill(LVC[level(i)], 0.22).set_stroke(width=2.5, opacity=1)
                    for i in range(1, D.N + 1)],
                  *[B.lab[i].animate.set_opacity(1) for i in range(1, D.N + 1)],
                  A.cells.animate.set_fill(C_GREY, 0.12), run_time=0.6)

    # ---------------------------------------------------------------- 修改：往上加
    def update_beat(self):
        self.beat("update")
        A, B = self.A, self.B
        trk = Text(f"A[{D.U_I}] += {D.U_V}", font=MONO, font_size=32, color=C_RED).move_to([-2.4, 2.45, 0])
        self.play(FadeIn(trk), A.cells[D.U_I - 1].animate.set_fill(C_RED, 0.55), run_time=0.7)
        keys = [None, "到八", "到十六"]
        hops = VGroup()
        for k, (j, key) in enumerate(zip(D.U_PATH, keys)):
            if key:
                self.at(key)
            anims = [B.bar[j].animate.set_stroke(C_RED, width=5)]
            if k:
                prev = D.U_PATH[k - 1]
                e = B.edges[prev].copy().set_stroke(C_RED, width=6, opacity=1)
                hops.add(e)
                anims.append(Create(e))
            t = Text(f"i = {j:>2} = {j:05b}", font=MONO, font_size=30).move_to([3.3, 2.45, 0])
            if k == 0:
                self.play(FadeIn(t), *anims, run_time=0.8)
                self.itrk = t
            else:
                self.play(Transform(self.itrk, t), *anims, run_time=0.8)
        self.at("出界")
        self.play(Transform(self.itrk, Text("i = 32 > 16 停", font=MONO, font_size=30, color=C_GREY)
                            .move_to([3.3, 2.45, 0])), run_time=0.5)
        self.at("各加三")
        plus = VGroup()
        anims = []
        for j in D.U_PATH:
            p = MathTex(f"+{D.U_V}", color=C_RED).scale(0.5).next_to(B.lab[j], UR, buff=0.02)
            plus.add(p)
            anims.append(Transform(B.lab[j], num(D.C_AFTER[j], C_RED, 0.55).move_to(B.lab[j])))
        self.play(LaggedStart(*[FadeIn(p, shift=UP * 0.15) for p in plus], lag_ratio=0.3), *anims, run_time=1.2)
        self.play(FadeOut(plus), run_time=0.4)
        self.at("进位")
        carry = VGroup(Text("0110", font=MONO, font_size=28), MathTex("+", color=C_GREY).scale(0.7),
                       Text("0010", font=MONO, font_size=28, color=C_YELLOW), MathTex("=", color=C_GREY).scale(0.7),
                       Text("1000", font=MONO, font_size=28, color=C_RED)).arrange(RIGHT, buff=0.2)
        carry.move_to([-2.4, 3.3, 0])
        self.play(FadeIn(carry, shift=DOWN * 0.2), run_time=0.8)
        self.at("从九出发")
        hops2 = VGroup()
        self.play(*[B.bar[j].animate.set_stroke(C_RED, width=2.5, opacity=0.5) for j in D.U_PATH],
                  FadeOut(hops), A.cells[D.U_I - 1].animate.set_fill(C_GREY, 0.12),
                  A.cells[8].animate.set_fill(C_GREEN, 0.55), run_time=0.5)
        path = D.U2_PATH
        for k, j in enumerate(path):
            anims = [B.bar[j].animate.set_stroke(C_GREEN, width=5, opacity=1)]
            if k:
                e = B.edges[path[k - 1]].copy().set_stroke(C_GREEN, width=6, opacity=1)
                hops2.add(e)
                anims.append(Create(e))
            self.play(Transform(self.itrk, Text(f"i = {j:>2} = {j:05b}", font=MONO, font_size=30)
                                .move_to([3.3, 2.45, 0])), *anims, run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(A, B, hops2, trk, self.itrk, carry)), run_time=0.6)

    # ---------------------------------------------------------------- 代价
    def cost_beat(self):
        self.beat("cost")
        rules = VGroup(
            VGroup(T("查询", 28, C_TEAL), Text("i -= i & -i", font=MONO, font_size=28, color=C_TEAL),
                   T("每步抹掉一个 1", 26, C_GREY)),
            VGroup(T("修改", 28, C_RED), Text("i += i & -i", font=MONO, font_size=28, color=C_RED),
                   T("最低位的 1 至少左移一位", 26, C_GREY)))
        for r, y in zip(rules, (2.6, 1.9)):
            r[0].move_to([-5.0, y, 0])
            r[1].move_to([-4.3, y, 0], aligned_edge=LEFT)
            r[2].move_to([-0.6, y, 0], aligned_edge=LEFT)
        self.play(FadeIn(rules[0], shift=RIGHT * 0.2), run_time=0.7)
        self.at("修改每跳一步")
        self.play(FadeIn(rules[1], shift=RIGHT * 0.2), run_time=0.7)
        self.at("一百万")
        big = VGroup(MathTex(r"n = 10^6", color=WHITE).scale(0.9), MathTex(r"\to", color=C_GREY).scale(0.8),
                     T(f"最多 {D.BIG_STEPS} 步", 30, C_YELLOW)).arrange(RIGHT, buff=0.25).move_to([0, 1.0, 0])
        self.play(FadeIn(big, shift=UP * 0.2), run_time=0.8)
        self.at("原数组和前缀和")
        tab = [("", "查询", "修改"), ("原数组", "O(n)", "O(1)"), ("前缀和", "O(1)", "O(n)"),
               ("树状数组", r"O(\log n)", r"O(\log n)")]
        cells = VGroup()
        for r, row in enumerate(tab):
            y = 0.05 - 0.6 * r
            for c, s in enumerate(row):
                if not s:
                    continue
                x = [-3.0, 0.2, 3.0][c]
                if r == 0:
                    m = T(s, 26, C_GREY)
                elif c == 0:
                    m = T(s, 26, C_YELLOW if r == 3 else WHITE)
                else:
                    col = C_YELLOW if "log" in s else (C_GREEN if s == "O(1)" else C_RED)
                    m = MathTex(s, color=col).scale(0.8)
                cells.add(m.move_to([x, y, 0]))
        self.play(LaggedStart(*[FadeIn(m) for m in cells], lag_ratio=0.08), run_time=1.6)
        self.at("下标必须从一开始")
        warn = VGroup(T("下标从 1 开始：", 26, C_RED), Text("0 & -0 = 0", font=MONO, font_size=26, color=C_RED),
                      T("会原地打转", 26, C_RED)).arrange(RIGHT, buff=0.2).move_to([0, -2.45, 0])
        self.play(FadeIn(warn, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rules, big, cells, warn)), run_time=0.6)

    # ---------------------------------------------------------------- 应用：蚂蚁越野跑，离散化
    def ants_beat(self):
        self.beat("ants")
        xs = [-4.4, -2.2, 0.0, 2.2, 4.4]
        ants = VGroup()
        for x, v in zip(xs, D.ANTS):
            ants.add(VGroup(Circle(0.38, stroke_color=WHITE, stroke_width=3).set_fill(C_GREY, 0.15),
                            num(v, s=0.75)).move_to([x, 1.9, 0]))
        head = VGroup(Arrow([-5.0, 1.9, 0], [-6.7, 1.9, 0], buff=0, stroke_width=4, color=C_GREY),
                      T("前进", 22, C_GREY))
        head[1].next_to(head[0], UP, buff=0.12)
        self.ants, self.xs = ants, xs
        self.play(LaggedStart(*[FadeIn(a, shift=LEFT * 0.4) for a in ants], lag_ratio=0.2), FadeIn(head),
                  run_time=1.6)
        self.at("前小后大")
        ex = ArcBetweenPoints(ants[1].get_top() + UP * 0.05, ants[3].get_top() + UP * 0.05, angle=-PI / 3,
                              color=C_YELLOW, stroke_width=4)
        exl = VGroup(num(5, C_YELLOW, 0.6), MathTex("<", color=C_YELLOW).scale(0.6), num(7, C_YELLOW, 0.6),
                     T("追上", 22, C_YELLOW)).arrange(RIGHT, buff=0.12).next_to(ex, UP, buff=0.08)
        self.play(Create(ex), FadeIn(exl), run_time=0.9)
        self.at("离散化")
        self.play(FadeOut(VGroup(ex, exl)), run_time=0.4)
        srt = VGroup(*[num(v, s=0.7) for v in D.VALS]).arrange(RIGHT, buff=0.75).move_to([0, 0.15, 0])
        rk = VGroup(*[MathTex(str(D.RANK[v]), color=C_YELLOW).scale(0.6).next_to(s, DOWN, buff=0.3) for v, s in
                      zip(D.VALS, srt)])
        lab1 = T("排序去重", 22, C_GREY).next_to(srt, LEFT, buff=0.5)
        lab2 = T("名次", 22, C_YELLOW).next_to(rk, LEFT, buff=0.5).align_to(lab1, RIGHT)
        src = [ants[D.ANTS.index(v)][1] for v in D.VALS]
        self.play(*[TransformFromCopy(s, d) for s, d in zip(src, srt)], FadeIn(lab1), run_time=1.0)
        self.at("一排第一")
        self.play(LaggedStart(*[FadeIn(r, shift=DOWN * 0.15) for r in rk], lag_ratio=0.3), FadeIn(lab2),
                  run_time=1.4)
        tags = VGroup(*[MathTex(str(D.RANK[v]), color=C_YELLOW).scale(0.6).next_to(a, DOWN, buff=0.15)
                        for v, a in zip(D.ANTS, ants)])
        self.play(*[TransformFromCopy(rk[D.VALS.index(v)], t) for v, t in zip(D.ANTS, tags)], run_time=1.2)
        self.tags, self.head = tags, head
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(srt, rk, lab1, lab2)), run_time=0.6)

    # ---------------------------------------------------------------- 从前往后扫
    def scan_beat(self):
        self.beat("scan")
        m = len(D.VALS)
        xf = lambda i: -5.2 + (i - 1) * 0.95  # noqa: E731
        cnt = Row([0] * m, -2.45, xf=xf, cw=0.82)
        B = Bars([0] * (m + 1), m, xf=xf, cw=0.82, y0=-1.45, dy=0.68)
        cap1 = T("每个名次有几只", 20, C_GREY).next_to(cnt.cells, RIGHT, buff=0.25)
        cap2 = T("树状数组", 20, C_GREY).next_to(B.bar[4], RIGHT, buff=0.25)
        hdr = VGroup(*[T(s, 22, C_GREY) for s in ("速度", "名次", "前面更慢", "累计")])
        cx = [1.9, 3.0, 4.4, 5.9]
        for h, x in zip(hdr, cx):
            h.move_to([x, 0.15, 0])
        self.play(FadeIn(cnt), FadeIn(B), FadeIn(cap1), FadeIn(cap2), FadeIn(hdr), run_time=1.0)
        pin = SurroundingRectangle(self.ants[0], color=C_YELLOW, buff=0.08)
        keys = [None, None, "轮到速度十", "轮到七", "轮到六"]
        rows = VGroup()
        for k, (st, key) in enumerate(zip(D.ANT_STEPS, keys)):
            if key:
                self.at(key)
            rt = 0.5 if k < 2 else 0.8
            y = -0.3 - 0.4 * k
            pa = [Transform(pin, SurroundingRectangle(self.ants[k], color=C_YELLOW, buff=0.08))] if k else [Create(pin)]
            self.play(*pa, run_time=rt * 0.6)
            q = st["q"]
            if q:
                self.play(*[B.bar[j].animate.set_fill(C_TEAL, 0.65) for j in q], run_time=rt)
            row = VGroup(num(st["x"], s=0.6), num(st["r"], C_YELLOW, 0.6), num(st["got"], C_TEAL, 0.6),
                         num(st["ans"], s=0.6))
            for r, x in zip(row, cx):
                r.move_to([x, y, 0])
            rows.add(row)
            new = st["tree"]
            anims = [B.bar[j].animate.set_stroke(C_YELLOW, width=5) for j in st["u"]]
            anims += [Transform(B.lab[j], num(new[j], s=0.55).move_to(B.lab[j])) for j in st["u"]]
            c_r = sum(1 for s2 in D.ANT_STEPS[:k + 1] if s2["r"] == st["r"])
            anims += [Transform(cnt.vals[st["r"] - 1], num(c_r, s=0.6).move_to(cnt.vals[st["r"] - 1])),
                      cnt.cells[st["r"] - 1].animate.set_fill(C_YELLOW, 0.4)]
            self.play(FadeIn(row, shift=LEFT * 0.2), *anims, run_time=rt)
            self.play(*[B.bar[j].animate.set_fill(LVC[level(j)], 0.22).set_stroke(LVC[level(j)], width=2.5)
                        for j in set(q) | set(st["u"])], run_time=rt * 0.6)
        self.at("零加一")
        sm = VGroup(MathTex(r"0+1+2+2+2 =", color=WHITE).scale(0.75), num(D.ANT_ANS, C_YELLOW, 0.9))
        sm.arrange(RIGHT, buff=0.18).move_to([4.0, -2.55, 0])
        self.play(FadeIn(sm, shift=UP * 0.2), run_time=0.8)
        self.at("一共七次")
        arcs = VGroup()
        for i, j in D.ANT_PAIRS:
            a = ArcBetweenPoints(self.ants[i].get_top() + UP * 0.05, self.ants[j].get_top() + UP * 0.05,
                                 angle=-PI / 2.6, color=C_YELLOW, stroke_width=3)
            arcs.add(a)
        self.play(FadeOut(pin), LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.2), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cnt, B, cap1, cap2, hdr, rows, sm, arcs, self.ants, self.tags, self.head)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        ql = ["def query(i):", "    s = 0", "    while i > 0:", "        s += C[i]", "        i -= i & -i",
              "    return s"]
        ul = ["def update(i, v):", "    while i <= n:", "        C[i] += v", "        i += i & -i"]

        def block(lines, x, hot, col):
            cw = Text("m" * 10, font=MONO, font_size=26).width / 10       # Text 会吃掉行首空格，缩进手动补
            g = VGroup(*[Text(s.lstrip(), font=MONO, font_size=26, color=col if k == hot else WHITE) for k, s in
                         enumerate(lines)])
            g.arrange(DOWN, buff=0.18, aligned_edge=LEFT).move_to([x, 1.2, 0], aligned_edge=UP + LEFT)
            for t, s in zip(g, lines):
                t.shift(RIGHT * cw * (len(s) - len(s.lstrip())))
            return g
        q = block(ql, -6.0, 4, C_TEAL).align_to([0, 2.9, 0], UP)
        u = block(ul, 0.9, 3, C_RED).align_to([0, 2.9, 0], UP)
        self.play(FadeIn(q, shift=RIGHT * 0.2), FadeIn(u, shift=LEFT * 0.2), run_time=1.0)
        self.at("最低位的一")
        lb = Text("lowbit(i) = i & -i", font=MONO, font_size=28, color=C_YELLOW).move_to([0, -0.6, 0])
        self.play(FadeIn(lb, shift=UP * 0.2), run_time=0.7)
        self.at("查询往下减")
        self.play(Indicate(q[4], color=C_TEAL, scale_factor=1.08), run_time=0.8)
        self.play(Indicate(u[3], color=C_RED, scale_factor=1.08), run_time=0.8)
        res = VGroup(T("查询、修改都是", 28, WHITE), MathTex(r"O(\log n)", color=C_YELLOW)).arrange(RIGHT, buff=0.2)
        res.move_to([0, -1.5, 0])
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026spring · 第 2 周 树状数组 第 3 节与附录 A · LeetCode 307 · OpenJudge 20018",
                20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
