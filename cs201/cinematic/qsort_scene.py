"""快速排序：力气花在分上（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。指针停靠、交换、基准归位、
递归树都来自 qsortdata（讲义 partition_pair 原样插桩；test_qsort.py 对撞讲义原版、sorted() 与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qsortdata as Q  # noqa: E402
from cine import *  # noqa: E402,F403


def vcol(v, vmax):
    return interpolate_color(ManimColor(C_BLUE), ManimColor(C_PURPLE), (v - 1) / max(1, vmax - 1))


class Bars(VGroup):
    """柱状条：slots[k] 是第 k 个槽位上的柱子（矩形 + 下方数字），交换时只换槽位里的对象。"""

    def __init__(self, vals, cx, base, w, gap, unit, lab_scale=0.6, vmax=None):
        super().__init__()
        n = len(vals)
        vmax = vmax or max(vals)
        self.base = base
        self.xs = [cx + (k - (n - 1) / 2) * gap for k in range(n)]
        self.slots = []
        for k, v in enumerate(vals):
            r = Rectangle(width=w, height=v * unit, stroke_width=0).set_fill(vcol(v, vmax), 0.8)
            r.move_to([self.xs[k], base, 0], aligned_edge=DOWN)
            lab = MathTex(str(v)).scale(lab_scale).next_to(r, DOWN, buff=0.1)
            g = VGroup(r, lab)
            g.value, g.color0 = v, vcol(v, vmax)
            self.slots.append(g)
        self.add(*self.slots)

    def swap(self, i, j, arc=PI / 2.5):
        if i == j:
            return []
        a, b = self.slots[i], self.slots[j]
        self.slots[i], self.slots[j] = b, a
        return [a.animate(path_arc=-arc).set_x(self.xs[j]), b.animate(path_arc=-arc).set_x(self.xs[i])]

    def apply(self, events):
        """把一段 partition 事件里的交换一次性应用，返回整体移动动画（片头快放用）。"""
        before = list(self.slots)
        for e in events:
            if e[0] == "swap":
                self.slots[e[1]], self.slots[e[2]] = self.slots[e[2]], self.slots[e[1]]
            elif e[0] == "place":
                self.slots[e[1]], self.slots[e[2]] = self.slots[e[2]], self.slots[e[1]]
        return [g.animate.set_x(self.xs[k]) for k, g in enumerate(self.slots) if before[k] is not g]

    def tint(self, k, col, op=0.8):
        return self.slots[k][0].animate.set_fill(col, op)


PART_SRC = ("def partition_pair(arr, lo, hi):\n    pivot = arr[lo]\n    left, right = lo + 1, hi\n    while True:\n"
            "        while left <= right and arr[left] <= pivot:\n            left += 1\n"
            "        while left <= right and arr[right] >= pivot:\n            right -= 1\n"
            "        if left > right:\n            break\n"
            "        arr[left], arr[right] = arr[right], arr[left]\n"
            "    arr[lo], arr[right] = arr[right], arr[lo]\n    return right\n")


class QSortLesson(Lesson):
    def construct(self):
        for b in ("title", "idea", "partition", "tree", "cost", "worst", "random", "merge", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, k, default=None):
        return next((c["start"] for c in self.cue_times() if k in c["text"]), default)

    def at(self, k):
        self.wait_until(self.cue_start(k, self.now))

    def hold(self, tail=0.6):
        self.wait(max(0.1, self.left() - tail))

    def nine(self, vals=Q.DATA):
        return Bars(vals, cx=-3.2, base=-1.3, w=0.5, gap=0.7, unit=0.36, lab_scale=0.62, vmax=9)

    # ---------------------------------------------------------------- 片头：二十二个数快放
    def title_beat(self):
        self.beat("title")
        data = Q.LECTURE_DATA
        bars = Bars(data, cx=0, base=-2.0, w=0.4, gap=0.56, unit=0.19, lab_scale=0.45, vmax=20)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars.slots], lag_ratio=0.06), run_time=1.4)
        _, nodes = Q.full_trace(data)
        self.at("快速排序挑一个数")
        step = max(0.2, min(0.6, (self.left() - 3.0) / (1.3 * len(nodes))))
        for lo, hi, p, d, _, ev in nodes:
            if ev:
                self.play(bars.slots[lo][0].animate.set_fill(C_YELLOW, 0.95), run_time=step * 0.35)
                mv = bars.apply(ev)
                if mv:
                    self.play(*mv, run_time=step * 0.65)
            self.play(bars.slots[p][0].animate.set_fill(C_GREEN, 0.9), run_time=step * 0.3)
        title = T("快速排序", 64).move_to([0, 2.7, 0])
        sub = T("力气花在「分」上", 30, C_YELLOW).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.0)
        self.hold()
        self.play(FadeOut(VGroup(bars, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 思路：小的去左，大的去右
    def idea_beat(self):
        self.beat("idea")
        bars = self.nine()
        self.bars = bars
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars.slots], lag_ratio=0.08), run_time=1.0)
        self.at("取第一个数五")
        piv = 5
        plab = T("基准", 24, C_YELLOW).next_to(bars.slots[0], UP, buff=0.15)
        self.play(bars.tint(0, C_YELLOW, 0.95), FadeIn(plab, shift=DOWN * 0.15), run_time=0.7)
        self.at("比五小的")
        small = [k for k, g in enumerate(bars.slots) if g.value < piv]
        big = [k for k, g in enumerate(bars.slots) if g.value > piv]
        self.play(*[bars.tint(k, C_BLUE, 0.9) for k in small], run_time=0.7)
        self.at("比五大的")
        self.play(*[bars.tint(k, C_RED, 0.75) for k in big], run_time=0.7)
        self.at("分完之后")
        ghost = VGroup(*[Rectangle(width=0.5, height=0.08, stroke_width=0).set_fill(C_BLUE if k < 4 else (C_YELLOW if k == 4 else C_RED), 0.9)
                         .move_to([bars.xs[k], 2.35, 0]) for k in range(9)])
        slot = DashedVMobject(Rectangle(width=0.62, height=0.36 * piv + 0.15, stroke_color=C_YELLOW, stroke_width=2),
                              num_dashes=24).move_to([bars.xs[4], bars.base + 0.36 * piv / 2, 0])
        lab = T("最终位置", 22, C_YELLOW).move_to([bars.xs[4], 2.75, 0])
        self.play(FadeIn(ghost), Create(slot), FadeIn(lab), run_time=1.0)
        steps = VGroup(T("① 选基准", 26, C_YELLOW), T("② 分割：小的去左，大的去右", 26),
                       T("③ 两段各自递归", 26), T("不需要「合」", 26, C_GREEN)).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
        steps.move_to([3.6, 0.4, 0])
        self.play(FadeIn(steps[:2], shift=LEFT * 0.2), run_time=0.8)
        self.at("左右两段分别递归")
        self.play(FadeIn(steps[2], shift=LEFT * 0.2), run_time=0.6)
        self.at("不需要再合并")
        self.play(FadeIn(steps[3], shift=LEFT * 0.2), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(ghost, slot, lab, steps, plab)),
                  *[bars.tint(k, g.color0, 0.8) for k, g in enumerate(bars.slots)], run_time=0.6)

    # ---------------------------------------------------------------- 原地分割：成对交换
    def pointer(self, label, col, drop=0.06):
        """drop：标签离箭头的距离；left / right 两个指针的标签错开高度，指针相邻或交错时不叠字。"""
        arr = Arrow(DOWN * 0.45, UP * 0.05, buff=0, color=col, stroke_width=5, max_tip_length_to_length_ratio=0.4)
        return VGroup(arr, Text(label, font=MONO, font_size=22, color=col).next_to(arr, DOWN, buff=drop))

    def partition_beat(self):
        self.beat("partition")
        bars = self.bars
        code = Code(code_string=PART_SRC, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 14})
        code.move_to([3.6, 0.55, 0])
        ln = code.code_lines
        self.play(FadeIn(code, shift=LEFT * 0.3), bars.tint(0, C_YELLOW, 0.95), run_time=0.8)
        y_ptr = bars.base - 0.6
        L = self.pointer("left", C_BLUE)
        Rp = self.pointer("right", C_RED, drop=0.3)
        hl = SurroundingRectangle(ln[4], color=C_BLUE, buff=0.03, stroke_width=2)
        self.at("左指针从左往右")
        L.move_to([bars.xs[1], y_ptr, 0], aligned_edge=UP)
        Rp.move_to([bars.xs[8], y_ptr, 0], aligned_edge=UP)
        self.play(FadeIn(L), Create(hl), run_time=0.6)
        self.play(FadeIn(Rp), hl.animate.become(SurroundingRectangle(ln[6], color=C_RED, buff=0.03, stroke_width=2)),
                  run_time=0.6)
        _, _, ev, _ = Q.partition_events()
        keys = {0: "左指针停在九", 2: "两者交换", 3: "左指针停在七", 5: "再交换", 6: "左指针停在八", 8: "最后把基准"}
        for i, e in enumerate(ev):
            if i in keys:
                self.at(keys[i])
            if e[0] == "L":
                self.play(L.animate.set_x(bars.xs[e[1]]), hl.animate.become(SurroundingRectangle(ln[4], color=C_BLUE, buff=0.03, stroke_width=2)),
                          run_time=0.6)
                self.play(Indicate(bars.slots[e[1]], color=C_BLUE, scale_factor=1.05), run_time=0.4)
            elif e[0] == "R":
                self.play(Rp.animate.set_x(bars.xs[e[1]]), hl.animate.become(SurroundingRectangle(ln[6], color=C_RED, buff=0.03, stroke_width=2)),
                          run_time=0.6)
                if e[1] < ev[i - 1][1]:
                    cross = T("交错", 24, C_RED).move_to([(bars.xs[e[1]] + bars.xs[ev[i - 1][1]]) / 2, 2.3, 0])
                    self.play(FadeIn(cross), hl.animate.become(SurroundingRectangle(VGroup(ln[8], ln[9]), color=C_RED, buff=0.03, stroke_width=2)),
                              run_time=0.5)
                    self.cross_lab = cross
                else:
                    self.play(Indicate(bars.slots[e[1]], color=C_RED, scale_factor=1.05), run_time=0.4)
            elif e[0] == "swap":
                self.play(*bars.swap(e[1], e[2]), hl.animate.become(SurroundingRectangle(ln[10], color=C_YELLOW, buff=0.03, stroke_width=2)),
                          run_time=0.8)
            else:
                self.play(*bars.swap(e[1], e[2]), hl.animate.become(SurroundingRectangle(ln[11], color=C_GREEN, buff=0.03, stroke_width=2)),
                          run_time=0.9)
                p = e[2]
                self.play(bars.tint(p, C_GREEN, 0.95), *[bars.tint(k, C_BLUE, 0.45) for k in range(p)],
                          *[bars.tint(k, C_RED, 0.4) for k in range(p + 1, 9)], run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(code, hl, L, Rp, self.cross_lab)), run_time=0.5)

    # ---------------------------------------------------------------- 递归树
    def tree_pos(self, idx, depth, dy=0.95, top=2.5):
        return np.array([1.0 + 0.66 * idx, top - dy * depth, 0])

    def grow_tree(self, bars, nodes, keys=None, dy=0.95, top=2.5, step=None, show_swap=False):
        par = Q.parents(nodes)
        tnodes, tedges = [], VGroup()
        step = step or 0.8
        for i, (lo, hi, p, d, k, ev) in enumerate(nodes):
            if keys and i in keys:
                self.at(keys[i])
            if show_swap and k is not None and k != lo:
                self.play(bars.tint(k, C_YELLOW, 0.95), run_time=step * 0.2)
                self.play(*bars.swap(lo, k, arc=PI / 3), run_time=step * 0.3)
            elif ev:
                self.play(bars.tint(lo, C_YELLOW, 0.95), run_time=step * 0.2)
            if ev:
                mv = bars.apply(ev)
                if mv:
                    self.play(*mv, run_time=step * 0.35)
            v = bars.slots[p].value
            pos = self.tree_pos(p, d, dy, top)
            node = VGroup(Circle(0.25, stroke_color=C_GREEN, stroke_width=3), MathTex(str(v)).scale(0.62)).move_to(pos)
            anims = [bars.tint(p, C_GREEN, 0.95), TransformFromCopy(bars.slots[p][1], node[1]), Create(node[0])]
            if par[i] is not None:
                e = Line(tnodes[par[i]].get_center(), pos, buff=0.27, stroke_color=C_GREY, stroke_width=2.5)
                tedges.add(e)
                anims.append(Create(e))
            self.play(*anims, run_time=step * 0.45)
            tnodes.append(node)
        return VGroup(*tnodes), tedges

    def tree_beat(self):
        self.beat("tree")
        bars = self.bars
        _, nodes = Q.full_trace(Q.DATA)
        # 根结点（5）已经分好：重置三色，只把根画进树
        self.play(*[bars.tint(k, g.color0, 0.8) for k, g in enumerate(bars.slots) if k != 4], run_time=0.4)
        step = max(0.7, min(1.5, (self.left() - 7.0) / len(nodes)))
        root = nodes[0]
        bars.apply([])  # 根结点的分割已在上一段做完
        tn, te = self.grow_tree(bars, [(root[0], root[1], root[2], root[3], None, [])] + nodes[1:], step=step)
        self.tnodes, self.tedges = tn, te
        self.at("从左往右读")
        iso = VGroup(T("中序读出 = 排好的顺序", 24, C_GREEN), T("树高 = 递归层数", 24, C_YELLOW)).arrange(DOWN, buff=0.15)
        iso.move_to([3.6, -2.4, 0])
        self.play(FadeIn(iso, shift=UP * 0.2), run_time=0.8)
        self.hold()
        self.play(FadeOut(iso), run_time=0.4)

    # ---------------------------------------------------------------- 代价：每层 n，层数 log n
    def cost_beat(self):
        self.beat("cost")
        self.play(FadeOut(self.bars), run_time=0.6)
        depth = max(n[3] for n in Q.full_trace(Q.DATA)[1]) + 1
        lines = VGroup(*[DashedLine([0.6, 2.5 - 0.95 * d, 0], [6.6, 2.5 - 0.95 * d, 0], stroke_color=C_GREY,
                                    stroke_width=1.5, dash_length=0.08).set_opacity(0.5).set_z_index(-1)
                       for d in range(depth)])
        self.play(FadeIn(lines), run_time=0.6)
        self.at("同一层")
        per = VGroup(T("每一层", 26), T("最多看", 26), MathTex("n", color=C_YELLOW), T("个数", 26)).arrange(RIGHT, buff=0.12)
        per.move_to([-3.4, 1.8, 0])
        self.play(FadeIn(per, shift=RIGHT * 0.2), run_time=0.8)
        self.at("恰好对半分")
        h = VGroup(T("对半分：层数", 26), MathTex(r"\log_2 n", color=C_YELLOW)).arrange(RIGHT, buff=0.15).move_to([-3.4, 0.9, 0])
        rec = MathTex("T(n)", "=", "2T(n/2)", "+", "cn").scale(0.9).move_to([-3.4, 0.0, 0])
        self.play(FadeIn(h, shift=RIGHT * 0.2), Write(rec), run_time=1.0)
        tot = MathTex(r"n \log n", color=C_GREEN).scale(1.3).move_to([-3.4, -1.1, 0])
        self.play(TransformFromCopy(rec, tot), run_time=1.0)
        self.at("随机的输入")
        avg = T("随机输入：平均也是 n log n", 24, C_GREY).move_to([-3.4, -2.0, 0])
        self.play(FadeIn(avg), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(lines, per, h, rec, tot, avg, self.tnodes, self.tedges)), run_time=0.6)

    # ---------------------------------------------------------------- 有序输入退化成链
    def stats(self, cmp_, depth, col):
        return VGroup(VGroup(T("比较", 24, C_GREY), MathTex(str(cmp_), color=col).scale(0.85)).arrange(RIGHT, buff=0.15),
                      VGroup(T("深度", 24, C_GREY), MathTex(str(depth), color=col).scale(0.85)).arrange(RIGHT, buff=0.15)
                      ).arrange(RIGHT, buff=0.6).move_to([-3.2, 2.7, 0])

    def worst_beat(self):
        self.beat("worst")
        asc = list(range(1, 10))
        bars = self.nine(asc)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars.slots], lag_ratio=0.06), run_time=0.9)
        self.at("首元素是最小的")
        _, nodes = Q.full_trace(asc)
        _, _, cmp_, depth = Q.sort_trace(asc)
        step = max(0.5, min(1.0, (self.left() - 9.0) / len(nodes)))
        self.at("首元素是最小的")
        tn, te = self.grow_tree(bars, nodes, dy=0.58, top=2.6, step=step)
        st = self.stats(cmp_, depth, C_RED)
        self.play(FadeIn(st), run_time=0.6)
        self.at("一千个有序的数")
        big = Q.big_counts()
        k1 = VGroup(MathTex("n=1000", color=C_GREY).scale(0.7),
                    T("比较约 50 万次，递归 1000 层", 22, C_RED)).arrange(RIGHT, buff=0.2)
        k1.move_to([-3.2, -2.4, 0])
        self.play(FadeIn(k1, shift=UP * 0.2), run_time=0.8)
        self.at("递归上限")
        err = Text("RecursionError", font=MONO, font_size=26, color=C_RED).move_to([-3.2, 2.05, 0])
        self.play(FadeIn(err, scale=1.3), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(tn, te, st, k1, err)), *[bars.tint(k, g.color0, 0.8) for k, g in enumerate(bars.slots)],
                  run_time=0.6)
        self.asc_bars = bars
        assert big["fixed_depth"] == 1000

    # ---------------------------------------------------------------- 随机基准
    def random_beat(self):
        self.beat("random")
        bars = self.asc_bars
        asc = list(range(1, 10))
        tip = T("随机选一个位置 → 换到最前面当基准", 22, C_YELLOW).move_to([-3.2, 2.7, 0])
        self.play(FadeIn(tip), run_time=0.6)
        self.at("树一下子变矮")
        _, nodes = Q.full_trace(asc, "random", seed=Q.RANDOM_DEMO_SEED)
        _, _, cmp_, depth = Q.sort_trace(asc, "random", seed=Q.RANDOM_DEMO_SEED)
        step = max(0.6, min(1.2, (self.left() - 6.0) / len(nodes)))
        tn, te = self.grow_tree(bars, nodes, step=step, show_swap=True)
        st = self.stats(cmp_, depth, C_GREEN).move_to([-3.2, 2.05, 0])
        self.play(FadeIn(st), run_time=0.6)
        self.at("一千个有序的数")
        big = Q.big_counts()
        k1 = VGroup(MathTex("n=1000", color=C_GREY).scale(0.7),
                    T(f"比较约 1.2 万次，递归 {big['random_depth']} 层", 22, C_GREEN)).arrange(RIGHT, buff=0.2)
        k1.move_to([-3.2, -2.4, 0])
        self.play(FadeIn(k1, shift=UP * 0.2), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(tn, te, st, k1, tip, bars)), run_time=0.6)

    # ---------------------------------------------------------------- 与归并对比
    def row(self, vals, cx, y, col=C_GREY, gaps=()):
        g = VGroup()
        x = cx - (len(vals) - 1) * 0.5 / 2 - 0.12 * len(gaps) / 2
        for k, v in enumerate(vals):
            if k in gaps:
                x += 0.12
            sq = Square(0.46, stroke_color=col, stroke_width=2)
            g.add(VGroup(sq, MathTex(str(v)).scale(0.55).move_to(sq)).move_to([x, y, 0]))
            x += 0.5
        return g

    def merge_beat(self):
        self.beat("merge")
        data = Q.MERGE_DEMO
        lx, rx = -3.4, 3.4
        hl = T("归并", 32, C_BLUE).move_to([lx, 2.75, 0])
        hr = T("快排", 32, C_YELLOW).move_to([rx, 2.75, 0])
        top_l = self.row(data, lx, 1.9)
        top_r = self.row(data, rx, 1.9)
        self.play(FadeIn(hl), FadeIn(hr), FadeIn(top_l), FadeIn(top_r), run_time=0.8)
        self.at("一刀切开")
        half = len(data) // 2
        mid_l = self.row(data, lx, 0.4, C_BLUE, gaps=(half,))
        a1 = Arrow([lx, 1.55, 0], [lx, 0.75, 0], buff=0, color=C_GREY, stroke_width=2)
        t1 = T("按位置切开：不费力", 20, C_GREY).next_to(a1, RIGHT, buff=0.15)
        self.play(GrowArrow(a1), TransformFromCopy(top_l, mid_l), FadeIn(t1), run_time=0.9)
        bot_l = self.row(sorted(data), lx, -1.1, C_GREEN)
        a2 = Arrow([lx, 0.05, 0], [lx, -0.75, 0], buff=0, color=C_YELLOW, stroke_width=7)
        t2 = T("合并：力气在这里", 20, C_YELLOW).next_to(a2, RIGHT, buff=0.15)
        self.at("力气全花在")
        self.play(GrowArrow(a2), TransformFromCopy(mid_l, bot_l), FadeIn(t2), run_time=0.9)
        self.at("快排正好反过来")
        arr = list(data)
        p = Q.partition_pair(arr, 0, len(arr) - 1)
        mid_r = self.row(arr, rx, 0.4, C_YELLOW, gaps=(p, p + 1))
        mid_r[p][0].set_stroke(C_GREEN, 3)
        b1 = Arrow([rx, 1.55, 0], [rx, 0.75, 0], buff=0, color=C_YELLOW, stroke_width=7)
        u1 = T("分割：力气在这里", 20, C_YELLOW).next_to(b1, RIGHT, buff=0.15)
        self.play(GrowArrow(b1), TransformFromCopy(top_r, mid_r), FadeIn(u1), run_time=0.9)
        bot_r = self.row(sorted(data), rx, -1.1, C_GREEN)
        b2 = Arrow([rx, 0.05, 0], [rx, -0.75, 0], buff=0, color=C_GREY, stroke_width=2)
        u2 = T("直接连上，不用合", 20, C_GREY).next_to(b2, RIGHT, buff=0.15)
        self.at("不用合")
        self.play(GrowArrow(b2), TransformFromCopy(mid_r, bot_r), FadeIn(u2), run_time=0.9)
        self.at("原地排序")
        s1 = VGroup(T("原地 · 额外空间只是递归栈", 22), MathTex(r"O(\log n)", color=C_GREEN).scale(0.7)).arrange(RIGHT, buff=0.15)
        s1.move_to([rx, -2.0, 0])
        self.play(FadeIn(s1), run_time=0.6)
        self.at("不稳定")
        s2 = T("不稳定：相等元素可能换乱", 22, C_RED).move_to([rx, -2.6, 0])
        self.play(FadeIn(s2), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(hl, hr, top_l, top_r, mid_l, mid_r, bot_l, bot_r, a1, a2, b1, b2, t1, t2, u1, u2, s1, s2)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 小结
    def recap_beat(self):
        self.beat("recap")
        words = ["选基准", "分两边", "基准归位", "两边递归"]
        chain = VGroup()
        for i, w in enumerate(words):
            chain.add(T(w, 32, [C_YELLOW, WHITE, C_GREEN, WHITE][i]))
            if i < len(words) - 1:
                chain.add(MathTex(r"\rightarrow", color=C_GREY))
        chain.arrange(RIGHT, buff=0.3).move_to([0, 1.2, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.15) for m in chain], lag_ratio=0.2), run_time=1.6)
        self.at("平均")
        facts = VGroup(VGroup(T("平均", 26, C_GREY), MathTex(r"n\log n", color=C_GREEN).scale(0.85)).arrange(RIGHT, buff=0.15),
                       VGroup(T("有序输入", 26, C_GREY), MathTex(r"n^2", color=C_RED).scale(0.85)).arrange(RIGHT, buff=0.15),
                       T("随机基准来化解", 26, C_YELLOW)).arrange(RIGHT, buff=0.7).move_to([0, -0.4, 0])
        self.play(LaggedStart(*[FadeIn(f, shift=UP * 0.15) for f in facts], lag_ratio=0.35), run_time=1.6)
        self.hold(0.8)
        self.play(FadeOut(VGroup(chain, facts)), run_time=0.8)
