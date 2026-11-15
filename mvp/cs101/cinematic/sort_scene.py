"""排序：从 n² 到 n log n（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。冒泡 / 插入 / 归并的每一步来自 sortdata 对讲义代码的插桩
（test_sort.py 对撞 sorted()、讲义输出、暴力数逆序对与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sortdata as S  # noqa: E402
from cine import *  # noqa: E402,F403


def val_color(v, vmax=8):
    return interpolate_color(ManimColor(C_BLUE), ManimColor(C_YELLOW), (v - 1) / max(1, vmax - 1))


class Bars(VGroup):
    """柱状条：bars[k] 是第 k 个槽位上的柱子（矩形 + 下方数字）。"""

    def __init__(self, vals, cx=0.0, base=-1.9, w=0.62, gap=0.92, unit=0.48):
        super().__init__()
        n = len(vals)
        self.xs = [cx + (k - (n - 1) / 2) * gap for k in range(n)]
        self.bars = []
        for k, v in enumerate(vals):
            r = Rectangle(width=w, height=v * unit, stroke_width=0).set_fill(val_color(v), 0.85)
            r.move_to([self.xs[k], base, 0], aligned_edge=DOWN)
            lab = MathTex(str(v)).scale(0.6).next_to(r, DOWN, buff=0.12)
            g = VGroup(r, lab)
            g.value = v
            self.bars.append(g)
        self.add(*self.bars)

    def swap(self, j, k, arc=PI / 2.5):
        a, b = self.bars[j], self.bars[k]
        self.bars[j], self.bars[k] = b, a
        return [a.animate(path_arc=-arc).set_x(self.xs[k]), b.animate(path_arc=-arc).set_x(self.xs[j])]


def cell(v, size=0.6, col=C_GREY):
    sq = Square(size, stroke_color=col, stroke_width=2.5)
    return VGroup(sq, MathTex(str(v)).scale(0.7).move_to(sq))


class SortLesson(Lesson):
    def construct(self):
        for b in ("title", "table", "bubble", "insertion", "merge", "growth", "stable", "inversion", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        bars = Bars(S.DATA, base=-1.6)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars.bars], lag_ratio=0.12), run_time=1.4)
        q = T("排好要比较多少次？", 32, C_YELLOW).move_to([0, 2.6, 0])
        self.play(FadeIn(q, shift=DOWN * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("有的要比较", self.now))
        order = sorted(range(len(S.DATA)), key=lambda k: S.DATA[k])
        self.play(*[bars.bars[k].animate(path_arc=-PI / 3).set_x(bars.xs[r]) for r, k in enumerate(order)],
                  run_time=1.6)
        title = T("排序", 72).move_to([0, 2.6, 0])
        sub = MathTex(r"n^2", r"\;\longrightarrow\;", r"n\log n").scale(1.1).next_to(title, DOWN, buff=0.25)
        sub[0].set_color(C_RED)
        sub[2].set_color(C_GREEN)
        self.play(FadeOut(q), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(bars, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 一览表
    def table_beat(self):
        self.beat("table")
        head = ["算法", "平均", "最坏", "额外空间", "稳定"]
        rows = [("冒泡", r"n^2", r"n^2", "1", "是"), ("选择", r"n^2", r"n^2", "1", "否"),
                ("插入", r"n^2", r"n^2", "1", "是"), ("归并", r"n\log n", r"n\log n", "n", "是"),
                ("快排", r"n\log n", r"n^2", r"\log n", "否")]
        xs = [-4.6, -2.3, 0.0, 2.3, 4.6]
        hdr = VGroup(*[T(h, 26, C_GREY).move_to([x, 2.5, 0]) for h, x in zip(head, xs)])
        line = Line([-5.6, 2.15, 0], [5.6, 2.15, 0], stroke_color=C_GREY, stroke_width=2)
        body = VGroup()
        for r, row in enumerate(rows):
            y = 1.6 - 0.75 * r
            g = VGroup(T(row[0], 28).move_to([xs[0], y, 0]))
            for c in (1, 2, 3):
                g.add(MathTex(row[c]).scale(0.8).move_to([xs[c], y, 0]))
            g.add(T(row[4], 26, C_GREEN if row[4] == "是" else C_RED).move_to([xs[4], y, 0]))
            body.add(g)
        self.play(FadeIn(hdr), Create(line), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(g, shift=UP * 0.15) for g in body], lag_ratio=0.2), run_time=1.6)
        self.wait_until(self.cue_start("冒泡、选择、插入", self.now))
        box1 = SurroundingRectangle(body[:3], color=C_RED, buff=0.12, corner_radius=0.1)
        self.play(Create(box1), run_time=0.7)
        self.wait_until(self.cue_start("归并稳定", self.now))
        box2 = SurroundingRectangle(body[3], color=C_GREEN, buff=0.12, corner_radius=0.1)
        self.play(Create(box2), run_time=0.7)
        self.wait_until(self.cue_start("快排", self.now))
        worst = SurroundingRectangle(body[4][2], color=C_RED, buff=0.1)
        self.play(Create(worst), run_time=0.6)
        self.wait_until(self.cue_start("合并过程要会写", self.now))
        self.play(Indicate(body[3], color=C_YELLOW, scale_factor=1.08), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(hdr, line, body, box1, box2, worst)), run_time=0.6)

    # ---------------------------------------------------------------- 冒泡
    def bubble_beat(self):
        self.beat("bubble")
        bars = Bars(S.DATA)
        cap = T("冒泡排序", 30, C_RED).move_to([-4.6, 2.9, 0])
        cnt = VGroup(T("比较", 24, C_GREY), Integer(0).scale(0.9)).arrange(RIGHT, buff=0.25).move_to([4.6, 2.9, 0])
        self.play(FadeIn(bars), FadeIn(cap), FadeIn(cnt), run_time=0.8)
        ev, _ = S.bubble_trace(S.DATA)
        n_cmp = sum(1 for e in ev if e[0] == "cmp")
        step = max(0.25, min(0.55, (self.left() - 2.5) / n_cmp))
        k, done, tag = 0, len(S.DATA), VMobject()
        for e in ev:
            if e[0] == "cmp":
                j, sw = e[1], e[2]
                a, b = bars.bars[j], bars.bars[j + 1]
                k += 1
                anims = [cnt[1].animate.set_value(k)]
                hl = VGroup(SurroundingRectangle(a, color=C_YELLOW, buff=0.05),
                            SurroundingRectangle(b, color=C_YELLOW, buff=0.05))
                if sw:
                    self.play(FadeIn(hl, run_time=step * 0.3), *bars.swap(j, j + 1), *anims, run_time=step)
                else:
                    self.play(FadeIn(hl), *anims, run_time=step * 0.6)
                self.remove(hl)
            else:
                i, swapped = e[1], e[2]
                done -= 1
                if swapped:
                    self.play(bars.bars[done][0].animate.set_fill(C_GREEN, 0.9), run_time=0.3)
                else:
                    tag = T("这一趟没有交换：提前退出", 26, C_GREEN).move_to([0, 2.9, 0])
                    self.play(FadeIn(tag), *[b[0].animate.set_fill(C_GREEN, 0.9) for b in bars.bars], run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(bars, cap, cnt, tag)), run_time=0.6)

    # ---------------------------------------------------------------- 插入
    def insertion_beat(self):
        self.beat("insertion")
        bars = Bars(S.DATA, base=-2.2, unit=0.3)          # 矮一些，手里那张能整张抬到所有柱子上方
        lift = 2.7
        cap = T("插入排序", 30, C_YELLOW).move_to([-4.6, 2.9, 0])
        self.play(FadeIn(bars), FadeIn(cap), run_time=0.8)
        ev, _ = S.insertion_trace(S.DATA)
        step = max(0.18, min(0.45, (self.left() - 2.0) / len(ev)))
        held = None
        for e in ev:
            if e[0] == "lift":
                held = bars.bars[e[1]]
                bars.bars[e[1]] = None
                held.generate_target()
                held.target.shift(UP * lift)
                held.target[0].set_fill(C_YELLOW, 0.95)
                self.play(MoveToTarget(held), run_time=step)
            elif e[0] == "shift":
                j = e[1]
                b = bars.bars[j]
                bars.bars[j + 1], bars.bars[j] = b, None
                self.play(b.animate.set_x(bars.xs[j + 1]), held.animate.set_x(bars.xs[j]), run_time=step)
            else:
                p = e[1]
                bars.bars[p] = held
                held.generate_target()
                held.target.set_x(bars.xs[p]).shift(DOWN * lift)
                held.target[0].set_fill(val_color(held.value), 0.85)
                self.play(MoveToTarget(held), run_time=step)
        near = T("近乎有序时接近线性", 26, C_GREEN).move_to([0, 2.9, 0])
        self.wait_until(self.cue_start("近乎有序", self.now))
        self.play(FadeIn(near, shift=DOWN * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*bars.bars, cap, near)), run_time=0.6)

    # ---------------------------------------------------------------- 归并：分与合
    def merge_beat(self):
        self.beat("merge")
        a = S.DATA
        n = len(a)
        splits, merges = S.merge_levels(a)
        ys = {0: 2.55, 1: 1.45, 2: 0.35, 3: -0.75}

        def x_of(k, d):
            size = n >> d
            seg = k // size
            return (k - (n - 1) / 2) * 0.7 + (seg - ((n // size) - 1) / 2) * 0.32
        rows = {d: {} for d in range(4)}
        for k, v in enumerate(a):
            rows[0][k] = cell(v).move_to([x_of(k, 0), ys[0], 0])
        cap = T("归并排序", 30, C_GREEN).move_to([-5.3, 2.55, 0])
        self.play(FadeIn(cap), *[FadeIn(c) for c in rows[0].values()], run_time=0.8)
        for d in (1, 2, 3):
            for k, v in enumerate(a):
                rows[d][k] = cell(v).move_to([x_of(k, d), ys[d], 0])
            self.play(*[TransformFromCopy(rows[d - 1][k], rows[d][k]) for k in range(n)], run_time=0.7)
        self.wait_until(self.cue_start("再两两合并", self.now))
        # 自底向上：同一层的合并一起做；最顶层单独慢放并显示两个指针
        by_d = {}
        for lo, mid, hi, takes, d in merges:
            by_d.setdefault(d, []).append((lo, mid, hi, takes))
        ptr_i = Triangle(color=C_BLUE).set_fill(C_BLUE, 1).scale(0.12).rotate(PI)
        ptr_j = Triangle(color=C_RED).set_fill(C_RED, 1).scale(0.12).rotate(PI)
        for d in (2, 1, 0):
            group = by_d[d]
            self.play(*[rows[d][k][1].animate.set_opacity(0) for lo, _, hi, _ in group for k in range(lo, hi)],
                      run_time=0.3)
            nsteps = max(len(t) for _, _, _, t in group)
            top = d == 0
            if top:
                self.wait_until(self.cue_start("两个指针", self.now))
                ptr_i.move_to(rows[1][0].get_top() + UP * 0.2)
                ptr_j.move_to(rows[1][4].get_top() + UP * 0.2)
                self.play(FadeIn(ptr_i), FadeIn(ptr_j), run_time=0.4)
            iters = {lo: [lo, mid] for lo, mid, _, _ in group}
            for s in range(nsteps):
                anims = []
                for lo, mid, hi, takes in group:
                    if s >= len(takes):
                        continue
                    side, v = takes[s]
                    src_k = iters[lo][0] if side == "L" else iters[lo][1]
                    iters[lo][0 if side == "L" else 1] += 1
                    new = MathTex(str(v)).scale(0.7).move_to(rows[d][lo + s][0])
                    anims.append(TransformFromCopy(rows[d + 1][src_k][1], new))
                    anims.append(rows[d][lo + s][0].animate.set_stroke(C_GREEN, 3))
                    rows[d][lo + s][1] = new
                    if top:
                        li, rj = iters[lo]
                        if li < mid:
                            anims.append(ptr_i.animate.move_to(rows[1][li].get_top() + UP * 0.2))
                        if rj < hi:
                            anims.append(ptr_j.animate.move_to(rows[1][rj].get_top() + UP * 0.2))
                self.play(*anims, run_time=0.55 if top else 0.35)
            if top:
                self.play(FadeOut(ptr_i), FadeOut(ptr_j), run_time=0.3)
        self.wait_until(self.cue_start("小于等于", self.now))
        code = Text("if left[i] <= right[j]:", font=MONO, font_size=26, color=C_YELLOW)
        code.move_to([0, -1.85, 0])
        why = T("相等时先取左边 → 稳定", 24, C_GREEN).next_to(code, DOWN, buff=0.18)
        self.play(FadeIn(code, shift=UP * 0.2), FadeIn(why), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        everything = VGroup(cap, code, why, *[c for d in rows for c in rows[d].values()])
        self.play(FadeOut(everything), run_time=0.6)

    # ---------------------------------------------------------------- n² vs n log n
    def growth_beat(self):
        self.beat("growth")
        ax = Axes(x_range=[0, 40, 10], y_range=[0, 1600, 400], x_length=5.6, y_length=3.6,
                  axis_config={"color": C_GREY, "include_tip": False},
                  x_axis_config={"numbers_to_include": [10, 20, 30, 40]},
                  y_axis_config={"numbers_to_include": [400, 800, 1200, 1600],
                                 "decimal_number_config": {"num_decimal_places": 0}})
        ax.move_to([-3.2, 0.6, 0])
        sq = ax.plot(lambda x: x * x, x_range=[0.5, 40], color=C_RED, stroke_width=4)
        nl = ax.plot(lambda x: x * np.log2(x), x_range=[1, 40], color=C_GREEN, stroke_width=4)
        lsq = MathTex("n^2", color=C_RED).scale(0.8).next_to(ax.c2p(30, 900), LEFT, buff=0.25)
        lnl = MathTex(r"n\log n", color=C_GREEN).scale(0.8).next_to(ax.c2p(40, 213), UP, buff=0.15)
        self.play(Create(ax), run_time=0.8)
        self.play(Create(sq), Create(nl), FadeIn(lsq), FadeIn(lnl), run_time=1.6)
        self.wait_until(self.cue_start("一千", self.now))
        big, small = S.growth(1000)
        L = 5.0
        hdr = MathTex("n = 1000").scale(0.9).move_to([3.4, 2.4, 0])
        b1 = Rectangle(width=L, height=0.42, stroke_width=0).set_fill(C_RED, 0.85)
        b1.move_to([0.9, 1.4, 0], aligned_edge=LEFT)
        b2 = Rectangle(width=max(0.03, L * small / big), height=0.42, stroke_width=0).set_fill(C_GREEN, 0.95)
        b2.move_to([0.9, 0.0, 0], aligned_edge=LEFT)
        t1 = MathTex(r"n^2 = 1{,}000{,}000", color=C_RED).scale(0.75).next_to(b1, DOWN, buff=0.12).align_to(b1, LEFT)
        t2 = MathTex(r"n\log_2 n \approx " + f"{small:,.0f}".replace(",", "{,}"), color=C_GREEN).scale(0.75)
        t2.next_to(b2, DOWN, buff=0.12).align_to(b2, LEFT)
        self.play(FadeIn(hdr), GrowFromEdge(b1, LEFT), FadeIn(t1), run_time=1.0)
        self.play(GrowFromEdge(b2, LEFT), FadeIn(t2), run_time=0.8)
        self.play(Indicate(b2, color=C_GREEN, scale_factor=4), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, sq, nl, lsq, lnl, hdr, b1, b2, t1, t2)), run_time=0.6)

    # ---------------------------------------------------------------- 稳定性：两次排序
    def stable_beat(self):
        self.beat("stable")
        cols = {"a": C_BLUE, "b": C_YELLOW, "c": C_RED}

        def card(name, num):
            box = RoundedRectangle(corner_radius=0.15, width=1.5, height=1.0, stroke_color=cols[name], stroke_width=3)
            box.set_fill(cols[name], 0.15)
            txt = VGroup(Text(name, font=MONO, font_size=30), MathTex(str(num)).scale(0.9)).arrange(RIGHT, buff=0.3)
            return VGroup(box, txt.move_to(box))
        xs = [-2.0, 0.0, 2.0]
        cards = {r[0]: card(*r).move_to([x, 0.6, 0]) for r, x in zip(S.ROWS, xs)}
        cap = T("Python 的 sort 是稳定的", 30).move_to([0, 2.6, 0])
        self.play(FadeIn(cap), *[FadeIn(c, shift=UP * 0.2) for c in cards.values()], run_time=1.0)
        first, second = S.two_pass(S.ROWS)
        self.wait_until(self.cue_start("先按次关键字", self.now))
        s1 = Text("rows.sort(key=lambda r: r[0])", font=MONO, font_size=24, color=C_GREY).move_to([0, -1.1, 0])
        self.play(FadeIn(s1), *[cards[r[0]].animate.set_x(xs[k]) for k, r in enumerate(first)], run_time=0.9)
        s2 = Text("rows.sort(key=lambda r: r[1])", font=MONO, font_size=24, color=C_YELLOW).move_to([0, -1.7, 0])
        self.play(FadeIn(s2), run_time=0.4)
        self.play(*[cards[r[0]].animate(path_arc=-PI / 3).set_x(xs[k]) for k, r in enumerate(second)], run_time=1.2)
        self.wait_until(self.cue_start("a 和 c", self.now))
        keep = T("a 仍在 c 前面", 28, C_GREEN).move_to([0, 1.75, 0])
        self.play(Indicate(cards["a"], color=C_GREEN), Indicate(cards["c"], color=C_GREEN), FadeIn(keep), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cap, *cards.values(), s1, s2, keep)), run_time=0.6)

    # ---------------------------------------------------------------- 逆序对：一次加一批
    def inversion_beat(self):
        self.beat("inversion")
        L, R = S.INV_LEFT, S.INV_RIGHT
        lc = [cell(v, col=C_BLUE).move_to([-3.6 + 0.75 * k, 1.5, 0]) for k, v in enumerate(L)]
        rc = [cell(v, col=C_RED).move_to([1.6 + 0.75 * k, 1.5, 0]) for k, v in enumerate(R)]
        oc = [Square(0.6, stroke_color=C_GREY, stroke_width=2).move_to([-1.85 + 0.75 * k, -0.6, 0])
              for k in range(len(L) + len(R))]
        tl = T("left", 22, C_BLUE).next_to(VGroup(*lc), UP, buff=0.2)
        tr = T("right", 22, C_RED).next_to(VGroup(*rc), UP, buff=0.2)
        to = T("out", 22, C_GREY).next_to(VGroup(*oc), LEFT, buff=0.3)
        defin = T("逆序对：位置靠前、数值更大", 26).move_to([0, 2.9, 0])
        cnt = VGroup(Text("cnt", font=MONO, font_size=28, color=C_YELLOW), MathTex("=").scale(0.9),
                     Integer(0, color=C_YELLOW).scale(1.1)).arrange(RIGHT, buff=0.2).move_to([4.6, -0.6, 0])
        self.play(FadeIn(defin), run_time=0.6)
        self.wait_until(self.cue_start("左半二五七", self.now))
        self.play(*[FadeIn(c) for c in lc + rc + oc], FadeIn(tl), FadeIn(tr), FadeIn(to), FadeIn(cnt), run_time=1.0)
        ev, total = S.merge_count_trace(L, R)
        keys = ["一先出来", "三出来时", "六出来时"]
        r_seen, outk, total_now = 0, 0, 0
        for kind, i, j, add in ev:
            if kind == "L":
                new = MathTex(str(L[i])).scale(0.7).move_to(oc[outk])
                self.play(TransformFromCopy(lc[i][1], new), lc[i][0].animate.set_stroke(C_GREY, 2), run_time=0.5)
            else:
                t = self.cue_start(keys[r_seen], self.now) if r_seen < len(keys) else self.now
                self.wait_until(t)
                r_seen += 1
                brace = Brace(VGroup(*lc[i:]), DOWN, color=C_YELLOW)
                lab = MathTex(f"+{add}", color=C_YELLOW).scale(0.8).next_to(brace, DOWN, buff=0.08)
                new = MathTex(str(R[j])).scale(0.7).move_to(oc[outk])
                total_now += add
                self.play(GrowFromCenter(brace), FadeIn(lab), TransformFromCopy(rc[j][1], new),
                          rc[j][0].animate.set_stroke(C_GREY, 2), cnt[2].animate.set_value(total_now), run_time=0.9)
                self.wait(0.5)
                self.play(FadeOut(brace), FadeOut(lab), run_time=0.3)
            outk += 1
        i_end = sum(1 for e in ev if e[0] == "L")
        j_end = sum(1 for e in ev if e[0] == "R")
        tail = [(lc[k], L[k]) for k in range(i_end, len(L))] + [(rc[k], R[k]) for k in range(j_end, len(R))]
        rest = [MathTex(str(v)).scale(0.7).move_to(oc[outk + k]) for k, (_, v) in enumerate(tail)]
        src = [c for c, _ in tail]
        if rest:
            self.play(*[TransformFromCopy(s[1], m) for s, m in zip(src, rest)], run_time=0.5)
        self.wait_until(self.cue_start("一共六个", self.now))
        self.play(Indicate(cnt, color=C_YELLOW, scale_factor=1.3), run_time=0.8)
        self.wait_until(self.cue_start("这就是为什么", self.now))
        code = Text("cnt += len(left) - i", font=MONO, font_size=28, color=C_YELLOW).move_to([0, -2.0, 0])
        box = SurroundingRectangle(code, color=C_YELLOW, buff=0.15, corner_radius=0.1)
        self.play(FadeIn(code, shift=UP * 0.2), Create(box), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        objs = [m for m in self.mobjects if m not in self.subs]
        self.play(*[FadeOut(m) for m in objs], run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(
            VGroup(MathTex("n^2", color=C_RED).scale(1.1), T("冒泡 · 插入：简单、原地", 30)).arrange(RIGHT, buff=0.5),
            VGroup(MathTex(r"n\log n", color=C_GREEN).scale(1.1), T("归并：分治", 30)).arrange(RIGHT, buff=0.5),
            VGroup(Text("sort()", font=MONO, font_size=32, color=C_BLUE), T("稳定 · 会写合并", 30)).arrange(RIGHT, buff=0.5),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([0, 0.6, 0])
        step = max(0.7, (self.left() - 1.0) / 3)
        for r in rows:
            self.play(FadeIn(r, shift=UP * 0.2), run_time=step * 0.6)
            self.wait(step * 0.4)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 6 周 排序 P26–P34", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
