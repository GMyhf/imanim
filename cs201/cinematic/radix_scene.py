"""分配排序：不比较，直接算位置（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。计数、前缀和、从后往前放置、
基数排序逐趟分桶与收集、后进先出的反例、判定树都来自 radixdata（讲义 7.1、7.3、10.3 节代码原样；
test_radix.py 对撞讲义打印结果、逐趟结果表、sorted() 与穷举判定树）。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radixdata as R  # noqa: E402
from cine import *  # noqa: E402,F403

DIGIT_COL = [C_GREY, C_BLUE, C_TEAL, C_GREEN, C_YELLOW, "#F0A04B", C_RED, C_PURPLE, "#E07BB5", "#9FB4FF"]
REC_COL = {"a": C_BLUE, "b": C_YELLOW, "c": C_TEAL, "d": "#F0A04B"}


def card(num: int, w=0.98, h=0.44, size=26):
    """三位补零的数字卡片：box + Text（逐字符可着色）。"""
    s = f"{num:03d}"
    box = RoundedRectangle(corner_radius=0.07, width=w, height=h, stroke_color=C_GREY, stroke_width=1.6)
    box.set_fill(BG, 1)
    txt = Text(s, font=MONO, font_size=size, color=WHITE)
    g = VGroup(box, txt.move_to(box))
    g.num, g.s = num, s
    return g


def mtx(s, scale=0.8, color=WHITE):
    return MathTex(s, color=color).scale(scale)


class RadixLesson(Lesson):
    def construct(self):
        for b in ("title", "bound", "count", "stable", "lsd", "why", "cost", "recap"):
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
        cards = VGroup(*[card(v) for v in R.RADIX_DATA]).arrange(RIGHT, buff=0.22).move_to([0, 0.6, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.3) for c in cards], lag_ratio=0.08), run_time=1.2)
        self.at("归并排序")
        cmp = mtx(r"a_i < a_j\,?", 1.1, C_YELLOW).move_to([0, 2.2, 0])
        nlog = mtx(r"\Omega(n\log n)", 1.0, C_YELLOW).move_to([0, -0.8, 0])
        self.play(FadeIn(cmp, shift=DOWN * 0.2), FadeIn(nlog), run_time=0.8)
        self.at("干脆不比较")
        cross = Cross(cmp, stroke_color=C_RED, stroke_width=6)
        self.play(Create(cross), run_time=0.6)
        self.at("这一集")
        title = T("分配排序", 60).move_to([0, 2.5, 0])
        sub = T("不比较，直接算位置", 30, C_TEAL).move_to([0, -1.6, 0])
        self.play(FadeOut(VGroup(cmp, cross, nlog)), run_time=0.4)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.0)
        # 每张卡片直接「掉」进自己的位置：排好序
        order = sorted(range(8), key=lambda k: R.RADIX_DATA[k])
        xs = [c.get_x() for c in cards]
        self.play(*[cards[k].animate.set_x(xs[r]) for r, k in enumerate(order)], run_time=1.4)
        self.hold()
        self.clear(cards, title, sub)

    # ---------------------------------------------------------------- 判定树下界
    def bound_beat(self):
        self.beat("bound")
        head = T("比较排序的下界：判定树", 30, C_YELLOW).move_to([0, 3.3, 0])
        self.play(FadeIn(head), run_time=0.5)
        leaves = R.decision_tree3()
        # 按路径建树：内部结点 = 比较，左「是」右「否」
        tree = {}
        for path, perm in leaves:
            key = ()
            for cmp, res in path:
                tree.setdefault(key, cmp)
                key = key + (res,)
            tree[key] = ("leaf", perm)

        def depth_first(key):
            v = tree[key]
            if isinstance(v, tuple):
                return [key]
            return depth_first(key + (True,)) + depth_first(key + (False,))
        leaf_keys = depth_first(())
        X0, DX, Y0, DY = -6.1, 1.5, 2.3, 1.25
        pos = {k: (X0 + i * DX, Y0 - len(k) * DY) for i, k in enumerate(leaf_keys)}

        def place(key):
            if key in pos:
                return pos[key]
            a, b = place(key + (True,)), place(key + (False,))
            pos[key] = ((a[0] + b[0]) / 2, Y0 - len(key) * DY)
            return pos[key]
        place(())
        nodes, edges, labs = {}, VGroup(), VGroup()
        for key, v in tree.items():
            x, y = pos[key]
            if isinstance(v, tuple):
                perm = v[1]
                m = mtx("<".join(perm), 0.62, C_TEAL)
                box = SurroundingRectangle(m, buff=0.08, color=C_TEAL, stroke_width=1.5, corner_radius=0.06)
                nodes[key] = VGroup(box, m).move_to([x, y, 0])
            else:
                m = mtx(v.replace("<", "<") + "?", 0.62)
                box = SurroundingRectangle(m, buff=0.09, color=C_BLUE, stroke_width=1.6, corner_radius=0.08)
                nodes[key] = VGroup(box, m).move_to([x, y, 0])
        for key in tree:
            if key:
                par = nodes[key[:-1]]
                ch = nodes[key]
                ln = Line(par.get_bottom(), ch.get_top(), color=C_GREY, stroke_width=2)
                edges.add(ln)
                lab = T("是" if key[-1] else "否", 18, C_GREEN if key[-1] else C_RED)
                lab.move_to(ln.get_center() + (LEFT if key[-1] else RIGHT) * 0.22)
                labs.add(lab)
        internal = [k for k, v in tree.items() if not isinstance(v, tuple)]
        self.play(*[FadeIn(nodes[k]) for k in internal], Create(edges), FadeIn(labs), run_time=1.6)
        self.at("六种排列")
        self.play(LaggedStart(*[FadeIn(nodes[k], shift=DOWN * 0.15) for k in leaf_keys], lag_ratio=0.12), run_time=1.2)
        f1 = VGroup(T("叶子", 26), mtx(r"\ge 3! = 6", 0.85)).arrange(RIGHT, buff=0.12).move_to([4.6, 2.2, 0])
        self.play(FadeIn(f1), run_time=0.6)
        self.at("高为二")
        f2 = VGroup(T("高 2：最多", 26), mtx(r"2^2 = 4 < 6", 0.85)).arrange(RIGHT, buff=0.12).move_to([4.6, 1.3, 0])
        deep = [k for k in leaf_keys if len(k) == 3]
        self.play(FadeIn(f2), *[nodes[k][0].animate.set_stroke(C_YELLOW, 3) for k in deep], run_time=0.8)
        f3 = VGroup(T("最坏至少比", 26), mtx(r"3", 0.95, C_YELLOW), T("次", 26)).arrange(RIGHT, buff=0.12)
        f3.move_to([4.6, 0.5, 0])
        self.play(FadeIn(f3), run_time=0.6)
        self.at("八个数")
        f4 = mtx(r"8! = 40320,\ \lceil \log_2 40320 \rceil = 16", 0.7, C_TEAL).move_to([4.5, -0.5, 0])
        self.play(FadeIn(f4, shift=UP * 0.15), run_time=0.8)
        self.at("一般地")
        f5 = mtx(r"h \ge \log_2 n! \ \ge\ \tfrac{n}{2}\log_2\tfrac{n}{2} = \Omega(n\log n)", 0.68, C_YELLOW)
        f5.move_to([3.9, -2.45, 0])
        self.play(Write(f5), run_time=1.4)
        self.hold()
        self.clear(head, *nodes.values(), edges, labs, f1, f2, f3, f4, f5)

    # ---------------------------------------------------------------- 计数排序
    def count_beat(self):
        self.beat("count")
        head = T("计数排序：数一遍，再按值写回", 30, C_YELLOW).move_to([0, 3.3, 0])
        data = R.COUNT_DATA
        n = len(data)
        src = VGroup(*[VGroup(Square(0.5, stroke_color=C_GREY, stroke_width=1.4),
                              Text(str(v), font=MONO, font_size=20)) for v in data])
        for s in src:
            s[1].move_to(s[0])
        src.arrange(RIGHT, buff=0.04).move_to([0, 2.45, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(s) for s in src], lag_ratio=0.03), run_time=1.0)
        self.at("计数排序")
        K = 20
        BW = 0.58
        bx = [(-(K - 1) / 2 + k) * BW for k in range(K)]
        base = -0.6
        bins = VGroup(*[Line([x - BW * 0.42, base, 0], [x + BW * 0.42, base, 0], color=C_GREY, stroke_width=2) for x in bx])
        idx = VGroup(*[Text(str(k + 1), font=MONO, font_size=18, color=C_GREY).move_to([x, base - 0.25, 0])
                       for k, x in enumerate(bx)])
        clab = T("count", 22, C_GREY).move_to([0, base - 0.62, 0])
        self.play(Create(bins), FadeIn(idx), FadeIn(clab), run_time=1.0)
        height = [0] * K
        moves, blocks = [], [None] * n
        for j, v in enumerate(data):
            k = v - 1
            blk = Square(0.4, stroke_width=0).set_fill(interpolate_color(ManimColor(C_BLUE), ManimColor(C_PURPLE), k / (K - 1)), 0.9)
            blk.move_to([bx[k], base + 0.24 + height[k] * 0.45, 0])
            height[k] += 1
            blocks[j] = blk
            moves.append(ReplacementTransform(src[j][0].copy(), blk))
        self.play(LaggedStart(*moves, lag_ratio=0.18), *[src[j][1].animate.set_opacity(0.35) for j in range(n)],
                  run_time=min(4.5, max(2.0, self.cue_start("再从左往右", self.now + 5) - self.now - 1.6)))
        dup = VGroup(*[SurroundingRectangle(VGroup(*[blocks[j] for j in range(n) if data[j] == v]), color=C_YELLOW,
                                            buff=0.06) for v in (4, 10)])
        self.play(Create(dup), run_time=0.6)
        self.at("再从左往右")
        self.play(FadeOut(dup), run_time=0.3)
        out_x = [(-(n - 1) / 2 + k) * 0.54 for k in range(n)]
        order = sorted(range(n), key=lambda j: data[j])
        outs, anims = VGroup(), []
        for r, j in enumerate(order):
            o = VGroup(Square(0.5, stroke_color=C_TEAL, stroke_width=1.4), Text(str(data[j]), font=MONO, font_size=20))
            o.move_to([out_x[r], -2.25, 0])
            o[1].move_to(o[0])
            outs.add(o)
            anims.append(ReplacementTransform(blocks[j], o))
        self.play(LaggedStart(*anims, lag_ratio=0.1), run_time=2.6)
        self.at("没有任何比较")
        nocmp = T("没有一次「比较」", 26, C_GREEN).move_to([4.6, 1.5, 0])
        self.play(FadeIn(nocmp, shift=LEFT * 0.2), run_time=0.5)
        self.at("代价是")
        cost = VGroup(mtx(r"O(n+k)", 0.9, C_YELLOW), T("k = 取值范围", 24, C_GREY)).arrange(RIGHT, buff=0.25)
        cost.move_to([-4.2, 1.5, 0])
        self.play(FadeIn(cost), run_time=0.6)
        self.hold()
        self.clear(head, src, bins, idx, clab, outs, nocmp, cost)

    # ---------------------------------------------------------------- 稳定版：前缀和 + 从后往前
    def stable_beat(self):
        self.beat("stable")
        head = T("稳定版：前缀和定位，从后往前放", 30, C_YELLOW).move_to([0, 3.3, 0])
        self.play(FadeIn(head), run_time=0.5)
        tr = R.stable_trace()

        def rec(k, ch):
            box = RoundedRectangle(corner_radius=0.08, width=1.2, height=0.7, stroke_color=REC_COL[ch], stroke_width=2.2)
            box.set_fill(REC_COL[ch], 0.12)
            kt = Text(str(k), font=MONO, font_size=30).move_to(box.get_center() + LEFT * 0.22)
            ct = Text(ch, font=MONO, font_size=24, color=REC_COL[ch]).move_to(box.get_center() + RIGHT * 0.28)
            g = VGroup(box, kt, ct)
            g.key, g.ch = k, ch
            return g
        ins = VGroup(*[rec(k, ch) for k, ch in R.RECORDS]).arrange(RIGHT, buff=0.35).move_to([-2.8, 1.9, 0])
        inlab = T("输入", 22, C_GREY).next_to(ins, LEFT, buff=0.3)
        self.at("四条记录")
        self.play(LaggedStart(*[FadeIn(r, shift=DOWN * 0.2) for r in ins], lag_ratio=0.15), FadeIn(inlab), run_time=1.0)
        # 计数数组（键 1..3）
        cx = [2.4 + k * 1.0 for k in range(3)]
        cbox = VGroup(*[Square(0.7, stroke_color=C_GREY, stroke_width=1.6).move_to([x, 1.9, 0]) for x in cx])
        cidx = VGroup(*[T(f"键{k + 1}", 20, C_GREY).next_to(cbox[k], UP, buff=0.1) for k in range(3)])
        cval = VGroup(*[Integer(v, font_size=34).move_to(cbox[k]) for k, v in enumerate(tr["counts"])])
        ctit = T("count", 20, C_GREY).next_to(cbox, RIGHT, buff=0.2)
        self.at("先计数")
        self.play(Create(cbox), FadeIn(cidx), FadeIn(cval), FadeIn(ctit), run_time=0.8)
        self.at("每个格子变成")
        pre = VGroup(*[Integer(v, font_size=34, color=C_YELLOW).move_to(cbox[k]) for k, v in enumerate(tr["prefix"])])
        self.play(*[Transform(cval[k], pre[k]) for k in range(3)], run_time=0.8)
        note = T("= 这个键的结束位置", 22, C_YELLOW).next_to(cbox, DOWN, buff=0.22)
        self.play(FadeIn(note), run_time=0.5)
        # 输出槽
        ox = [-2.4 + k * 1.6 for k in range(4)]
        slots = VGroup(*[DashedVMobject(RoundedRectangle(corner_radius=0.08, width=1.3, height=0.8, stroke_color=C_GREY,
                                                          stroke_width=1.6), num_dashes=22).move_to([x, -1.5, 0]) for x in ox])
        sidx = VGroup(*[Text(str(k), font=MONO, font_size=20, color=C_GREY).next_to(slots[k], DOWN, buff=0.12)
                        for k in range(4)])
        olab = T("输出", 22, C_GREY).next_to(slots, LEFT, buff=0.3)
        self.play(Create(slots), FadeIn(sidx), FadeIn(olab), run_time=0.7)
        self.at("然后从后往前放")
        cues = ["d 放到", "c 放到", "b 放到", "a 放到"]
        cur = list(tr["prefix"])
        for step, (x, k, pos) in enumerate(tr["places"]):
            self.at(cues[step])
            r = next(m for m in ins if m.ch == x[1])
            cur[k - 1] -= 1                      # count 先减一，得到的就是放置下标
            assert cur[k - 1] == pos
            newc = Integer(cur[k - 1], font_size=34, color=C_YELLOW).move_to(cbox[k - 1])
            self.play(Indicate(r, color=REC_COL[x[1]], scale_factor=1.08), Transform(cval[k - 1], newc), run_time=0.5)
            self.play(r.animate.move_to(slots[pos]), run_time=0.7)
        self.at("键相同的记录")
        b, d = next(m for m in ins if m.ch == "b"), next(m for m in ins if m.ch == "d")
        a, c = next(m for m in ins if m.ch == "a"), next(m for m in ins if m.ch == "c")
        arcs = VGroup(CurvedArrow(b.get_bottom() + DOWN * 0.05, d.get_bottom() + DOWN * 0.05, angle=PI / 3, color=C_GREEN),
                      CurvedArrow(a.get_bottom() + DOWN * 0.05, c.get_bottom() + DOWN * 0.05, angle=PI / 3, color=C_GREEN))
        ok = T("相同键：先后次序不变 = 稳定", 26, C_GREEN).move_to([0, -2.75, 0])
        self.play(Create(arcs), FadeIn(ok), run_time=0.9)
        self.hold()
        self.clear(head, ins, inlab, cbox, cidx, cval, ctit, note, slots, sidx, olab, arcs, ok)

    # ---------------------------------------------------------------- 基数排序三趟
    def buckets(self):
        base = -2.55
        xs = [(-4.5 + k) * 1.2 for k in range(10)]
        lines = VGroup(*[Line([x - 0.52, base, 0], [x + 0.52, base, 0], color=C_GREY, stroke_width=2) for x in xs])
        labs = VGroup(*[Text(str(k), font=MONO, font_size=20, color=DIGIT_COL[k]).move_to([x, base - 0.25, 0])
                        for k, x in enumerate(xs)])
        return xs, base, VGroup(lines, labs)

    def row_x(self, n=8):
        return [(-(n - 1) / 2 + k) * 1.2 for k in range(n)]

    def do_pass(self, cards, i, rt_in=1.4, rt_out=1.2, lifo=False, xs=None, base=None):
        """第 i 位（0 个位）分配 + 收集；cards 是当前行次序的卡片列表，返回新次序。"""
        pos = 2 - i
        for c in cards:
            c[1][pos].set_color(DIGIT_COL[int(c.s[pos])])
        self.play(*[c[1][pos].animate.scale(1.25) for c in cards], run_time=0.3)
        self.play(*[c[1][pos].animate.scale(1 / 1.25) for c in cards], run_time=0.2)
        stacks = [[] for _ in range(10)]
        anims = []
        for c in cards:
            d = int(c.s[pos])
            stacks[d].append(c)
            anims.append(c.animate.move_to([xs[d], base + 0.3 + (len(stacks[d]) - 1) * 0.5, 0]))
        self.play(LaggedStart(*anims, lag_ratio=0.12), run_time=rt_in)
        new = [c for st in stacks for c in (reversed(st) if lifo else st)]
        rx = self.row_x()
        self.play(LaggedStart(*[c.animate.move_to([rx[k], 2.3, 0]) for k, c in enumerate(new)], lag_ratio=0.08),
                  run_time=rt_out)
        for c in cards:
            c[1][pos].set_color(WHITE)
        return new, stacks

    def lsd_beat(self):
        self.beat("lsd")
        head = T("基数排序：从个位开始，逐位分配、收集", 30, C_YELLOW).move_to([0, 3.3, 0])
        rx = self.row_x()
        cards = [card(v).move_to([rx[k], 2.3, 0]) for k, v in enumerate(R.RADIX_DATA)]
        self.play(FadeIn(head), LaggedStart(*[FadeIn(c) for c in cards], lag_ratio=0.06), run_time=0.9)
        self.at("每一位只有")
        xs, base, bk = self.buckets()
        self.play(FadeIn(bk), run_time=0.7)
        names = ["个位", "十位", "百位"]
        tag = T("", 24)
        passes = R.radix_passes(R.RADIX_DATA)
        for i in range(3):
            if i == 0:
                self.at("基数排序从个位开始")
            nt = T(f"第 {i + 1} 趟：按{names[i]}", 24, C_TEAL).move_to([-5.0, 1.55, 0])
            self.play(FadeTransform(tag, nt) if i else FadeIn(nt), run_time=0.3)
            tag = nt
            cards, _ = self.do_pass(cards, i, xs=xs, base=base, rt_in=1.3, rt_out=1.0)
            assert [c.num for c in cards] == passes[i][2]
        self.at("三趟之后")
        done = T("排好了", 26, C_GREEN).move_to([5.0, 1.55, 0])
        self.play(FadeIn(done), *[c[0].animate.set_stroke(C_GREEN, 2.2) for c in cards], run_time=0.6)   # 只动子对象，不与移动同场
        self.at("每一趟都不比较")
        self.hold()
        self.lsd = (head, cards, bk, tag, done, xs, base)

    def why_beat(self):
        self.beat("why")
        head, cards, bk, tag, done, xs, base = self.lsd
        h2 = T("每一趟都必须稳定", 30, C_YELLOW).move_to([0, 3.3, 0])
        # 回到「前两趟之后」的次序
        rx = self.row_x()
        mid = R.LECTURE_PASSES[2]
        by = {c.num: c for c in cards}
        cards = [by[v] for v in mid]
        t2 = T("前两趟之后", 24, C_TEAL).move_to([-5.0, 1.55, 0])
        for c in cards:
            c[0].set_stroke(C_GREY, 1.6)
        self.play(FadeTransform(head, h2), FadeOut(done), FadeTransform(tag, t2),
                  *[c.animate.move_to([rx[k], 2.3, 0]) for k, c in enumerate(cards)], run_time=1.0)
        self.at("按百位分桶时")
        for c in cards:
            c[1][0].set_color(DIGIT_COL[int(c.s[0])])
        stacks = [[] for _ in range(10)]
        anims = []
        for c in cards:
            d = int(c.s[0])
            stacks[d].append(c)
            anims.append(c.animate.move_to([xs[d], base + 0.3 + (len(stacks[d]) - 1) * 0.5, 0]))
        self.play(LaggedStart(*anims, lag_ratio=0.15), run_time=1.6)
        zero = stacks[0]
        br = Brace(VGroup(*zero), LEFT, color=C_TEAL, buff=0.08)
        bt = T("次序来自前两趟", 22, C_TEAL).next_to(VGroup(*zero), UP, buff=0.15).set_x(-5.2)
        self.play(GrowFromCenter(br), FadeIn(bt), run_time=0.7)
        self.at("如果桶是后进先出")
        lifo = [c for st in stacks for c in reversed(st)]
        self.play(FadeOut(br), FadeOut(bt), run_time=0.3)
        self.play(LaggedStart(*[c.animate.move_to([rx[k], 2.3, 0]) for k, c in enumerate(lifo)], lag_ratio=0.1),
                  run_time=1.6)
        wrong = R.radix_passes_lifo(R.RADIX_DATA)[-1]
        assert [c.num for c in lifo][:6] == wrong[:6]
        self.play(*[c[0].animate.set_stroke(C_RED, 2.4) for c in lifo[:6]], run_time=0.5)
        bad = T("后进先出：90, 75, …, 2   全乱了", 26, C_RED).move_to([0, 0.9, 0])
        self.play(FadeIn(bad), run_time=0.5)
        self.at("稳定性不是")
        good = [c for st in stacks for c in st]
        self.play(*[c.animate.move_to([rx[k], 2.3, 0]) for k, c in enumerate(good)], FadeOut(bad), run_time=1.2)
        self.play(*[c[0].animate.set_stroke(C_GREEN, 2.4) for c in good], run_time=0.4)
        ok = T("先进先出（稳定）：2, 24, 45, 66, 75, 90, 170, 802", 26, C_GREEN).move_to([0, 0.9, 0])
        self.play(FadeIn(ok), run_time=0.5)
        for c in good:
            c[1][0].set_color(WHITE)
        self.hold()
        self.clear(h2, t2, bk, ok, *good)

    # ---------------------------------------------------------------- 代价
    def cost_beat(self):
        self.beat("cost")
        head = T("代价", 32, C_YELLOW).move_to([0, 3.3, 0])
        f = mtx(r"T = d\,(n + b)", 1.4).move_to([0, 2.1, 0])
        self.play(FadeIn(head), run_time=0.4)
        self.at("每一趟分配")
        legend = VGroup(T("d：趟数（位数）", 24), T("n：元素个数", 24), T("b：桶数（基数）", 24)).arrange(RIGHT, buff=0.6)
        legend.move_to([0, 1.05, 0])
        self.play(Write(f), FadeIn(legend), run_time=1.2)
        self.at("八个数")
        ex = mtx(r"3 \times (8 + 10) = 54", 1.0, C_TEAL).move_to([0, 0.05, 0])
        self.play(FadeIn(ex, shift=UP * 0.15), run_time=0.6)
        self.at("它真是线性的吗")
        q = T("真是线性吗？", 28, C_YELLOW).move_to([-3.6, -0.95, 0])
        self.play(FadeIn(q), run_time=0.4)
        self.at("个互不相同")
        g = mtx(r"d \ge \log_b n \ \Rightarrow\ d\,(n+b) = \Omega(n \log n)", 0.9).move_to([1.2, -0.95, 0])
        self.play(Write(g), run_time=1.2)
        self.at("实际中快")
        word = VGroup(*[Rectangle(width=1.5, height=0.55, stroke_color=DIGIT_COL[k * 2 + 1], stroke_width=2)
                        .set_fill(DIGIT_COL[k * 2 + 1], 0.25) for k in range(4)]).arrange(RIGHT, buff=0).move_to([-1.0, -2.2, 0])
        bl = VGroup(*[Text("8 位", font=FONT, font_size=20).move_to(word[k]) for k in range(4)])
        wl = T("32 位整数", 24, C_GREY).next_to(word, LEFT, buff=0.3)
        rt = mtx(r"d = 4,\ b = 256", 0.9, C_TEAL).next_to(word, RIGHT, buff=0.4)
        self.play(FadeIn(word), FadeIn(bl), FadeIn(wl), run_time=0.7)
        self.play(FadeIn(rt, shift=LEFT * 0.2), run_time=0.5)
        self.hold()
        self.clear(head, f, legend, ex, q, g, word, bl, wl, rt)

    # ---------------------------------------------------------------- 总结
    def recap_beat(self):
        self.beat("recap")
        left = VGroup(T("比较排序", 32, C_BLUE), mtx(r"\Omega(n\log n)", 0.95, C_BLUE),
                      T("什么数据都能排", 24, C_GREY)).arrange(DOWN, buff=0.35)
        right = VGroup(T("分配排序", 32, C_TEAL),
                       VGroup(T("计数：", 24), mtx(r"O(n+k)", 0.8), T("值域小", 24, C_GREY)).arrange(RIGHT, buff=0.15),
                       VGroup(T("基数：", 24), mtx(r"O(d(n+b))", 0.8), T("每趟稳定", 24, C_GREY)).arrange(RIGHT, buff=0.15)
                       ).arrange(DOWN, buff=0.35)
        left.move_to([-3.4, 0.9, 0])
        right.move_to([3.2, 0.9, 0])
        bar = Line([0, 2.3, 0], [0, -0.6, 0], color=C_GREY, stroke_width=2)
        self.play(FadeIn(left, shift=RIGHT * 0.2), Create(bar), FadeIn(right, shift=LEFT * 0.2), run_time=1.2)
        self.at("不比较")
        tag = T("不比较，换来的是对数据的要求", 30, C_YELLOW).move_to([0, -1.6, 0])
        self.play(FadeIn(tag, shift=UP * 0.2), run_time=0.7)
        self.hold(0.3)
        self.play(FadeOut(VGroup(left, right, bar, tag)), run_time=0.6, audit=False)
