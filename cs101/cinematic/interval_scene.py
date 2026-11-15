"""区间贪心：先按右端点排序（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。所有扫描事件来自 intervaldata（讲义 1.1–1.5 节代码原样插桩；
test_interval.py 对撞讲义输出、小规模暴力枚举与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intervaldata as I  # noqa: E402
from cine import *  # noqa: E402,F403

PAL = [C_BLUE, C_YELLOW, C_RED, C_GREEN, C_PURPLE, C_TEAL, "#FF8E5E", "#C9E265"]
BAR_H = 0.3


def iv_tex(iv, color=WHITE, scale=0.55):
    return MathTex(rf"[{iv[0]},{iv[1]}]", color=color).scale(scale)


class Track:
    """数轴映射：区间端点 v → 屏幕 x。"""

    def __init__(self, lo, hi, y_axis=-2.3, xl=-5.4, xr=5.6):
        self.lo, self.hi, self.y, self.xl, self.xr = lo, hi, y_axis, xl, xr

    def x(self, v):
        return self.xl + (v - self.lo) * (self.xr - self.xl) / (self.hi - self.lo)

    def axis(self, step=1, numbers=True):
        line = Line([self.xl - 0.2, self.y, 0], [self.xr + 0.2, self.y, 0], stroke_color=C_GREY, stroke_width=2)
        g = VGroup(line)
        for v in range(self.lo, self.hi + 1, step):
            g.add(Line([self.x(v), self.y - 0.07, 0], [self.x(v), self.y + 0.07, 0], stroke_color=C_GREY,
                       stroke_width=2))
            if numbers:
                g.add(MathTex(str(v), color=C_GREY).scale(0.45).move_to([self.x(v), self.y - 0.3, 0]))
        return g

    def bar(self, iv, y, col, label=True, label_side=LEFT):
        w = max(0.06, self.x(iv[1]) - self.x(iv[0]))
        r = RoundedRectangle(corner_radius=0.1, width=w, height=BAR_H, stroke_color=col, stroke_width=2)
        r.set_fill(col, 0.72).move_to([(self.x(iv[0]) + self.x(iv[1])) / 2, y, 0])
        g = VGroup(r)
        if label:
            g.add(iv_tex(iv).next_to(r, label_side, buff=0.15))
        return g


class IntervalLesson(Lesson):
    def construct(self):
        for b in ("title", "table", "merge", "keep", "why", "arrows", "groups", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def reorder(self, bars, ivs, key, ys):
        """按 key 稳定排序后，把各行挪到新位置；返回 (动画, 新顺序下标)。"""
        idx = sorted(range(len(ivs)), key=lambda k: key(ivs[k]))
        anims = [bars[k].animate.set_y(ys[pos]) for pos, k in enumerate(idx)]
        return anims, idx

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        ivs = [[2, 9], [1, 4], [11, 17], [6, 12], [3, 7], [14, 19], [9, 13], [16, 20]]
        tr = Track(0, 20, y_axis=-2.4)
        ys = [1.55 - 0.45 * k for k in range(len(ivs))]
        ax = tr.axis(step=2)
        bars = [tr.bar(iv, y, PAL[k], label=False) for k, (iv, y) in enumerate(zip(ivs, ys))]
        self.play(Create(ax), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(b, shift=DOWN * 0.6) for b in bars], lag_ratio=0.15), run_time=1.8)
        title = T("区间贪心", 72).move_to([0, 3.0, 0])
        self.play(Write(title), run_time=1.0)
        self.wait_until(self.cue_start("按什么排", self.now))
        sub = T("全部难点：按什么排", 34, C_YELLOW).next_to(title, DOWN, buff=0.2)
        sub.shift(DOWN * 0.0)
        anims, _ = self.reorder(bars, ivs, lambda iv: iv[1], ys)
        self.play(FadeIn(sub), *anims, run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, *bars, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 五类一览
    def table_beat(self):
        self.beat("table")
        rows = [("合并区间", "左端点", C_BLUE), ("区间覆盖", "左端点", C_BLUE), ("区间分组", "左端点", C_BLUE),
                ("选最多不相交区间", "右端点", C_YELLOW), ("区间选点", "右端点", C_YELLOW)]
        tab = VGroup()
        for name, key, col in rows:
            tab.add(VGroup(T(name, 30), T("按" + key + "排", 30, col)))
        for r in tab:
            r[1].next_to(r[0], RIGHT, buff=0.6)
        tab.arrange(DOWN, buff=0.32, aligned_edge=LEFT).move_to([0, 0.9, 0])
        for r in tab:
            r[1].set_x(2.4, LEFT)
        first = self.cue_start("合并区间", self.now)
        self.wait_until(first)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in tab[:3]], lag_ratio=0.4), run_time=1.8)
        self.wait_until(self.cue_start("选最多", self.now))
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in tab[3:]], lag_ratio=0.4), run_time=1.4)
        self.wait_until(self.cue_start("压成一句话", self.now))
        motto = VGroup(T("要「多」→ 按右端点", 34, C_YELLOW), T("要「合」「盖」→ 按左端点", 34, C_BLUE))
        motto.arrange(RIGHT, buff=0.8).move_to([0, -2.25, 0])
        self.play(FadeIn(motto[0], shift=UP * 0.2), run_time=0.8)
        self.play(FadeIn(motto[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tab, motto)), run_time=0.6)

    # ---------------------------------------------------------------- 合并区间
    def merge_beat(self):
        self.beat("merge")
        tr = Track(0, 19, y_axis=-2.4)
        s, ev, out = I.merge_trace()
        ys = [2.1 - 0.55 * k for k in range(len(s))]
        ax = tr.axis(step=1)
        head = T("按左端点排序", 26, C_BLUE).move_to([-4.8, 3.2, 0])
        bars = [tr.bar(iv, y, PAL[k]) for k, (iv, y) in enumerate(zip(s, ys))]
        self.play(Create(ax), FadeIn(head), LaggedStart(*[FadeIn(b, shift=RIGHT * 0.3) for b in bars],
                                                         lag_ratio=0.2), run_time=1.6)
        out_y = -1.35
        out_lab = Text("out", font=MONO, font_size=24, color=C_GREEN).move_to([tr.x(0) - 0.55, out_y, 0])
        self.play(FadeIn(out_lab), run_time=0.3)
        ptr = Arrow([tr.xl - 1.0, ys[0], 0], [tr.xl - 0.45, ys[0], 0], buff=0, color=C_YELLOW, stroke_width=5,
                    max_tip_length_to_length_ratio=0.4)
        merged = []
        step = max(0.9, min(1.6, (self.cue_start("合并成三段", self.now + 8) - self.now) / len(ev)))
        for k, e in enumerate(ev):
            mv = [ptr.animate.set_y(ys[k])] if k else [GrowArrow(ptr)]
            if e[0] in ("start", "new"):
                nb = tr.bar(e[1], out_y, C_GREEN, label=False)
                merged.append([nb, list(e[1])])
                self.play(*mv, TransformFromCopy(bars[k][0], nb[0]), run_time=step)
            else:
                cur = merged[-1]
                cur[1][1] = e[2]
                nb = tr.bar(cur[1], out_y, C_GREEN, label=False)
                self.play(*mv, Transform(cur[0], nb), Indicate(bars[k][0], color=C_GREEN, scale_factor=1.05),
                          run_time=step)
        labs = VGroup(*[iv_tex(m[1], C_GREEN).next_to(m[0], DOWN, buff=0.12) for m in merged])
        self.wait_until(self.cue_start("合并成三段", self.now))
        three = T(f"合并成 {len(out)} 段", 28, C_GREEN).move_to([4.2, 3.2, 0])
        self.play(FadeOut(ptr), FadeIn(labs), FadeIn(three), run_time=0.8)
        self.wait_until(self.cue_start("max 不能省", self.now))
        self.play(FadeOut(VGroup(*bars, labs, three, out_lab, *[m[0] for m in merged], head)), run_time=0.6)
        # ---- max 不能省：[1,10]、[2,3]
        p = I.MAX_PITFALL
        pb = [tr.bar(iv, y, c) for iv, y, c in zip(p, (2.0, 1.4), (C_BLUE, C_YELLOW))]
        self.play(*[FadeIn(b, shift=RIGHT * 0.3) for b in pb], run_time=0.8)
        bad_iv, good_iv = I.merge_no_max(p)[0], I.merge(p)[0]
        bad = tr.bar(bad_iv, 0.2, C_RED, label=False)
        good = tr.bar(good_iv, -1.1, C_GREEN, label=False)
        bad_t = VGroup(Text("out[-1][1] = hi", font=MONO, font_size=22, color=C_RED), iv_tex(bad_iv, C_RED))
        bad_t.arrange(RIGHT, buff=0.3).move_to([3.4, 0.2, 0])
        good_t = VGroup(Text("max(out[-1][1], hi)", font=MONO, font_size=22, color=C_GREEN), iv_tex(good_iv, C_GREEN))
        good_t.arrange(RIGHT, buff=0.3).move_to([3.4, -1.1, 0])
        self.wait_until(self.cue_start("直接赋值", self.now))
        full = tr.bar(p[0], 0.2, C_RED, label=False)
        self.play(FadeIn(full), FadeIn(bad_t), run_time=0.6)
        self.play(Transform(full, bad), run_time=1.0)
        cross = Cross(full, stroke_color=C_RED, stroke_width=5).scale(0.6)
        self.play(Create(cross), FadeIn(good), FadeIn(good_t), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, *pb, full, cross, good, bad_t, good_t)), run_time=0.6)

    # ---------------------------------------------------------------- 最多不相交（无重叠区间）
    def keep_beat(self):
        self.beat("keep")
        tr = Track(0, 5, y_axis=-2.4, xl=-4.6, xr=4.0)
        ivs = I.KEEP_EX
        ys = [2.2 - 0.55 * k for k in range(len(ivs))]
        ax = tr.axis(step=1)
        bars = [tr.bar(iv, y, PAL[k]) for k, (iv, y) in enumerate(zip(ivs, ys))]
        self.play(Create(ax), LaggedStart(*[FadeIn(b, shift=RIGHT * 0.3) for b in bars], lag_ratio=0.2),
                  run_time=1.4)
        self.wait_until(self.cue_start("按右端点排", self.now))
        head = T("按右端点排序", 26, C_YELLOW).move_to([-4.6, 3.2, 0])
        anims, idx = self.reorder(bars, ivs, lambda iv: iv[1], ys)
        self.play(FadeIn(head), *anims, run_time=1.2)
        s, flags = I.greedy_keep(ivs, key=lambda iv: iv[1])
        assert [ivs[k] for k in idx] == s
        end_line = DashedLine([tr.x(s[0][1]), 2.6, 0], [tr.x(s[0][1]), -2.4, 0], color=C_YELLOW, dash_length=0.1)
        end_lab = Text("end", font=MONO, font_size=22, color=C_YELLOW).next_to(end_line, UP, buff=0.05)
        kept = VGroup()
        out_y = -1.35
        step = max(0.9, min(1.6, (self.cue_start("保留三个", self.now + 7) - self.now) / len(s)))
        for pos, (k, ok) in enumerate(zip(idx, flags)):
            b = bars[k]
            if ok:
                nb = tr.bar(ivs[k], out_y, C_GREEN, label=False)
                kept.add(nb)
                anims = [TransformFromCopy(b[0], nb[0]), b[0].animate.set_stroke(C_GREEN, 3)]
                tx = tr.x(ivs[k][1])
                if pos == 0:
                    anims += [Create(end_line), FadeIn(end_lab)]
                else:
                    anims += [end_line.animate.set_x(tx), end_lab.animate.set_x(tx)]
                self.play(*anims, run_time=step)
            else:
                cr = Cross(b[0], stroke_color=C_RED, stroke_width=4).scale(0.7)
                self.play(b.animate.set_opacity(0.3), Create(cr), run_time=step)
                kept.add(cr)
        self.wait_until(self.cue_start("保留三个", self.now))
        res = VGroup(T(f"保留 {sum(flags)}", 28, C_GREEN), T(f"移除 {len(s) - sum(flags)}", 28, C_RED))
        res.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([5.6, 1.0, 0])
        self.play(FadeIn(res, shift=LEFT * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, *bars, head, end_line, end_lab, kept, res)), run_time=0.6)

    # ---------------------------------------------------------------- 为什么是右端点
    def panel(self, tr, ivs, key, y0, title, col):
        s, flags = I.greedy_keep(ivs, key=key)
        head = T(title, 26, col).move_to([-5.2, y0 + 0.55, 0])
        ys = [y0 - 0.45 * k for k in range(len(s))]
        bars = [tr.bar(iv, y, C_GREY) for iv, y in zip(s, ys)]
        return head, bars, flags

    def why_beat(self):
        self.beat("why")
        tr = Track(0, 11, xl=-3.6, xr=3.4)
        best = 2
        groups = []
        for key_name, ivs, key, y0, col in (("按左端点", I.BAD_LEFT, lambda iv: iv[0], 2.4, C_BLUE),
                                            ("按长度", I.BAD_LEN, lambda iv: iv[1] - iv[0], 0.15, C_PURPLE)):
            self.wait_until(self.cue_start(key_name, self.now))
            head, bars, flags = self.panel(tr, ivs, key, y0, key_name, col)
            self.play(FadeIn(head), LaggedStart(*[FadeIn(b, shift=RIGHT * 0.2) for b in bars], lag_ratio=0.2),
                      run_time=1.0)
            anims = []
            for b, ok in zip(bars, flags):
                anims.append(b[0].animate.set_fill(C_GREEN if ok else C_RED, 0.72).set_stroke(
                    C_GREEN if ok else C_RED, 2))
            res = VGroup(T(f"只留 {sum(flags)} 个", 24, C_RED), T(f"最优 {best} 个", 24, C_GREEN))
            res.arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to([5.4, y0 - 0.45, 0])
            self.play(*anims, run_time=1.0)
            self.play(FadeIn(res, shift=LEFT * 0.2), run_time=0.6)
            groups.append(VGroup(head, *bars, res))
        self.wait_until(self.cue_start("按右端点才对", self.now))
        self.play(*[g.animate.set_opacity(0.3) for g in groups], run_time=0.6)
        X, A = [1, 5], [3, 4]
        rest = [[5, 8], [8, 10]]
        y = -1.95
        xb = tr.bar(X, y, WHITE, label=False)
        xl = MathTex("X").scale(0.7).next_to(xb, UP, buff=0.08)
        rb = VGroup(*[tr.bar(iv, y, C_GREY, label=False) for iv in rest])
        ab = tr.bar(A, y, C_GREEN, label=False)
        al = MathTex("A", color=C_GREEN).scale(0.7).next_to(ab, UP, buff=0.08)
        self.wait_until(self.cue_start("设最优解", self.now))
        self.play(FadeIn(xb), FadeIn(xl), FadeIn(rb), run_time=0.8)
        self.wait_until(self.cue_start("把 X 换成 A", self.now))
        self.play(Transform(xb, ab), Transform(xl, al), run_time=1.2)
        note = T("右端点更早 → 后面只多不少", 24, C_GREEN).move_to([0, -2.6, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*groups, xb, xl, rb, note)), run_time=0.6)

    # ---------------------------------------------------------------- 区间选点：引爆气球
    def arrows_beat(self):
        self.beat("arrows")
        tr = Track(0, 17, y_axis=-2.4)
        ivs = I.ARROW_EX
        ys = [2.1 - 0.55 * k for k in range(len(ivs))]
        ax = tr.axis(step=1)
        bars = [tr.bar(iv, y, PAL[k]) for k, (iv, y) in enumerate(zip(ivs, ys))]
        self.play(Create(ax), LaggedStart(*[FadeIn(b, scale=0.8) for b in bars], lag_ratio=0.2), run_time=1.4)
        anims, idx = self.reorder(bars, ivs, lambda iv: iv[1], ys)
        self.play(*anims, run_time=1.0)
        s, hit, shots = I.arrow_trace()
        cnt = VGroup(T("箭", 26, C_YELLOW), Integer(0, color=C_YELLOW).scale(0.9)).arrange(RIGHT, buff=0.2)
        cnt.move_to([5.3, 3.2, 0])
        self.play(FadeIn(cnt), run_time=0.3)
        arrows = VGroup()
        t_end = self.cue_start("两支箭", self.now + 6)
        step = max(1.0, min(2.0, (t_end - self.now) / len(shots)))
        for n, p in enumerate(shots, 1):
            a = Arrow([tr.x(p), 2.9, 0], [tr.x(p), -1.75, 0], buff=0, color=C_YELLOW, stroke_width=5,
                      max_tip_length_to_length_ratio=0.05)
            lab = MathTex(f"x={p}", color=C_YELLOW).scale(0.55).next_to(a, DOWN, buff=0.05)
            popped = [bars[k] for k, h in zip(idx, hit) if h == p]
            self.play(GrowArrow(a), FadeIn(lab), ChangeDecimalToValue(cnt[1], n), run_time=step * 0.5)
            self.play(*[Flash(b[0], color=C_YELLOW, flash_radius=0.5) for b in popped],
                      *[b.animate.set_opacity(0.25) for b in popped], run_time=step * 0.5)
            arrows.add(a, lab)
        self.wait_until(self.cue_start("只差一个字", self.now))
        self.play(FadeOut(VGroup(*bars, arrows, ax)), run_time=0.6)
        l1 = VGroup(T("无重叠区间", 26, C_GREY), Text("if lo >= end:", font=MONO, font_size=30),
                    T("端点相接 = 不重叠", 24, C_GREY))
        l2 = VGroup(T("引爆气球", 26, C_GREY), Text("if lo >  end:", font=MONO, font_size=30),
                    T("端点相接 = 射得到", 24, C_GREY))
        for l in (l1, l2):
            l.arrange(RIGHT, buff=0.5)
        VGroup(l1, l2).arrange(DOWN, buff=0.6, aligned_edge=LEFT).move_to([0, 0.6, 0])
        l2[1].align_to(l1[1], LEFT)
        l2[2].align_to(l1[2], LEFT)
        self.play(FadeIn(l1, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(l2, shift=UP * 0.2), run_time=0.6)
        hl1 = SurroundingRectangle(l1[1], color=C_BLUE, buff=0.08)
        hl2 = SurroundingRectangle(l2[1], color=C_YELLOW, buff=0.08)
        self.play(Create(hl2), run_time=0.6)
        self.wait_until(self.cue_start("上一个是", self.now))
        self.play(Create(hl1), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(l1, l2, hl1, hl2, cnt)), run_time=0.6)

    # ---------------------------------------------------------------- 区间分组：堆
    def groups_beat(self):
        self.beat("groups")
        tr = Track(0, 9, y_axis=-2.4, xl=-4.4, xr=3.2)
        s, lanes, states = I.group_trace()
        ax = tr.axis(step=1)
        lane_y = [1.3, 0.45, -0.4]
        lane_lab = VGroup(*[T(f"组 {g + 1}", 24, C_GREY).move_to([-5.9, y, 0]) for g, y in enumerate(lane_y)])
        self.play(Create(ax), run_time=0.6)
        heap_t = Text("heap = []", font=MONO, font_size=24, color=C_YELLOW).move_to([5.1, 2.6, 0])
        self.play(FadeIn(heap_t), run_time=0.3)
        bars = []
        t_end = self.cue_start("需要三组", self.now + 8)
        step = max(1.0, min(1.8, (t_end - self.now) / len(s)))
        shown = set()
        for k, (iv, g, st) in enumerate(zip(s, lanes, states)):
            b = tr.bar(iv, 2.6, PAL[k])
            self.play(FadeIn(b, shift=DOWN * 0.3), run_time=step * 0.35)
            new_heap = Text(f"heap = {st}", font=MONO, font_size=24, color=C_YELLOW).move_to(heap_t)
            anims = [b.animate.set_y(lane_y[g]), Transform(heap_t, new_heap)]
            if g not in shown:
                shown.add(g)
                anims.append(FadeIn(lane_lab[g]))
            self.play(*anims, run_time=step * 0.65)
            bars.append(b)
        self.wait_until(self.cue_start("需要三组", self.now))
        three = T(f"{max(lanes) + 1} 组", 30, C_GREEN).move_to([5.1, 1.6, 0])
        self.play(FadeIn(three, scale=1.3), run_time=0.6)
        self.wait_until(self.cue_start("同一时刻", self.now))
        prof = I.overlap_profile()
        sweep = Line([tr.x(prof[0][0]), 2.1, 0], [tr.x(prof[0][0]), -2.4, 0], color=WHITE, stroke_width=3)
        cnt = MathTex(str(prof[0][1]), color=WHITE).scale(0.8).next_to(sweep, UP, buff=0.08)
        self.play(Create(sweep), FadeIn(cnt), run_time=0.4)
        peak = max(c for _, c in prof)
        st = max(0.3, min(0.6, (self.left() - 1.2) / len(prof)))
        for x, c in prof[1:]:
            col = C_RED if c == peak else WHITE
            nc = MathTex(str(c), color=col).scale(0.8).move_to([tr.x(x), 2.1 + 0.08 + 0.2, 0])
            self.play(sweep.animate.set_x(tr.x(x)), Transform(cnt, nc), run_time=st)
            if c == peak:
                self.play(Indicate(cnt, color=C_RED, scale_factor=1.6), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ax, *bars, lane_lab, heap_t, three, sweep, cnt)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        q = T("按什么排？", 48).move_to([0, 1.8, 0])
        a1 = VGroup(T("要「多」", 36, C_YELLOW), T("→ 按右端点", 36)).arrange(RIGHT, buff=0.3)
        a2 = VGroup(T("要「合」「盖」", 36, C_BLUE), T("→ 按左端点", 36)).arrange(RIGHT, buff=0.3)
        VGroup(a1, a2).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to([0, 0.0, 0])
        self.play(Write(q), run_time=1.0)
        self.wait_until(self.cue_start("要多", self.now))
        self.play(FadeIn(a1, shift=UP * 0.2), run_time=0.7)
        self.play(FadeIn(a2, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 10 周 区间问题 P4–P11 · LeetCode 56/435/452", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
