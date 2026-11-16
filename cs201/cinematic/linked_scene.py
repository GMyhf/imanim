"""链表：三根指针的舞蹈（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。合并、反转、快慢指针、判圈与求环入口的每一步
都来自 linkeddata（讲义附录 A 模板原样插桩；test_linked.py 对撞 Python 列表与访问集合）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linkeddata as D  # noqa: E402
from cine import *  # noqa: E402,F403

NW, NH = 0.86, 0.62


def node(val, color=C_BLUE, w=NW, h=NH, dashed=False):
    box = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=3)
    box.set_fill(color, 0.16)
    if dashed:
        box = DashedVMobject(box, num_dashes=24)
    lab = (MathTex(str(val), color=WHITE).scale(0.8) if isinstance(val, int) else T(val, 22, color))
    return VGroup(box, lab.move_to(box))


def link(a, b, color=C_GREY, sw=4):
    """a 的右边指向 b 的左边（b 也可以是一个点）。"""
    end = b.get_left() if isinstance(b, Mobject) else b
    return Arrow(a.get_right(), end, buff=0.06, stroke_width=sw, color=color,
                 max_tip_length_to_length_ratio=0.3, tip_length=0.18)


def back_link(a, b, color=C_YELLOW, sw=4):
    """a 的左边指向 b 的右边（反转后的箭头）。"""
    end = b.get_right() if isinstance(b, Mobject) else b
    return Arrow(a.get_left(), end, buff=0.06, stroke_width=sw, color=color,
                 max_tip_length_to_length_ratio=0.3, tip_length=0.18)


def mono(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


class LinkedLesson(Lesson):
    def construct(self):
        for b in ("title", "merge", "reverse", "revrun", "middle", "cycle", "entry", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def hold_and_clear(self, *mobs):
        self.wait(max(0.1, self.left() - 0.6))
        self.play(*[FadeOut(m) for m in mobs], run_time=0.6)

    # ---------------------------------------------------------------- 片头：挪数据 vs 改链接
    def title_beat(self):
        self.beat("title")
        title = T("链表：三根指针的舞蹈", 44).move_to([0, 3.1, 0])
        self.play(Write(title), run_time=1.0)
        vals = [3, 8, 1, 9, 4]
        cells = VGroup(*[Square(0.72, stroke_color=C_GREY, stroke_width=3) for _ in range(6)])
        cells.arrange(RIGHT, buff=0).move_to([0.4, 1.55, 0])
        nums = VGroup(*[MathTex(str(v)).scale(0.8).move_to(cells[k]) for k, v in enumerate(vals)])
        alab = T("数组", 26, C_GREY).next_to(cells, LEFT, buff=0.5)
        self.play(FadeIn(cells), FadeIn(nums), FadeIn(alab), run_time=0.8)
        seven = MathTex("7", color=C_YELLOW).scale(0.8).move_to(cells[2].get_center() + UP * 0.95)
        self.play(FadeIn(seven, shift=DOWN * 0.2), run_time=0.4)
        self.play(LaggedStart(*[nums[k].animate.move_to(cells[k + 1]) for k in (4, 3, 2)], lag_ratio=0.5),
                  *[cells[k].animate.set_stroke(C_RED, 4) for k in (2, 3, 4, 5)], run_time=1.6)
        self.play(seven.animate.move_to(cells[2]), run_time=0.5)
        cost1 = T("挪 3 个元素", 24, C_RED).next_to(cells, RIGHT, buff=0.4)
        self.play(FadeIn(cost1), run_time=0.4)

        self.wait_until(self.cue_start("链表不挪", self.now))
        y = -1.15
        nodes = VGroup(*[node(v) for v in vals])
        for k, n in enumerate(nodes):
            n.move_to([-3.4 + 1.7 * k, y, 0])
        arrows = VGroup(*[link(nodes[k], nodes[k + 1]) for k in range(4)])
        llab = T("链表", 26, C_GREY).move_to([-5.6, y, 0])
        self.play(LaggedStart(*[FadeIn(n) for n in nodes], lag_ratio=0.15), FadeIn(llab), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.15), run_time=0.8)
        pre = T("前驱", 22, C_TEAL).next_to(nodes[1], DOWN, buff=0.2)
        self.play(nodes[1][0].animate.set_stroke(C_TEAL, 4), FadeIn(pre), run_time=0.5)
        new = node(7, C_YELLOW).move_to([(nodes[1].get_x() + nodes[2].get_x()) / 2, y + 1.05, 0])
        self.play(FadeIn(new, shift=DOWN * 0.2), run_time=0.5)
        a1 = Arrow(nodes[1].get_right() + UP * 0.1, new.get_left(), buff=0.06, stroke_width=4, color=C_YELLOW,
                   tip_length=0.18)
        a2 = Arrow(new.get_right(), nodes[2].get_left() + UP * 0.1, buff=0.06, stroke_width=4, color=C_YELLOW,
                   tip_length=0.18)
        self.play(GrowArrow(a2), run_time=0.6)
        self.play(ReplacementTransform(arrows[1], a1), run_time=0.7)
        cost2 = T("改 2 根指针", 24, C_GREEN).move_to([4.6, y + 1.05, 0])
        self.play(FadeIn(cost2), run_time=0.4)

        self.wait_until(self.cue_start("前提", self.now))
        self.play(Indicate(pre, color=C_TEAL, scale_factor=1.3), run_time=0.9)
        self.wait_until(self.cue_start("今天看", self.now))
        tags = VGroup(T("哨兵", 30, C_TEAL), T("三指针反转", 30, C_YELLOW), T("快慢指针", 30, C_RED))
        tags.arrange(RIGHT, buff=1.0).move_to([0, 0.3, 0])
        self.play(FadeOut(VGroup(cells, nums, alab, seven, cost1, nodes, arrows[0], arrows[2:], a1, a2, new,
                                 llab, pre, cost2)), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.2) for t in tags], lag_ratio=0.4), run_time=1.4)
        self.hold_and_clear(title, tags)

    # ---------------------------------------------------------------- 哨兵 + 合并
    def merge_beat(self):
        self.beat("merge")
        A, B = D.MERGE_A, D.MERGE_B
        ev = D.merge_trace()
        head = T("合并两个有序链表", 30).move_to([0, 3.25, 0])
        ya, yb, yr, dx = 2.15, 0.75, -1.45, 1.55
        an = VGroup(*[node(v, C_BLUE).move_to([-3.6 + dx * k, ya, 0]) for k, v in enumerate(A)])
        bn = VGroup(*[node(v, C_PURPLE).move_to([-3.6 + dx * k, yb, 0]) for k, v in enumerate(B)])
        aa = [link(an[k], an[k + 1]) for k in range(2)]
        ba = [link(bn[k], bn[k + 1]) for k in range(2)]
        la, lb = T("list1", 22, C_BLUE).move_to([-5.4, ya, 0]), T("list2", 22, C_PURPLE).move_to([-5.4, yb, 0])
        self.play(FadeIn(head), run_time=0.5)
        self.wait_until(self.cue_start("一条是", self.now))
        self.play(LaggedStart(*[FadeIn(n) for n in an], lag_ratio=0.2), *[GrowArrow(a) for a in aa], FadeIn(la),
                  run_time=0.9)
        self.play(LaggedStart(*[FadeIn(n) for n in bn], lag_ratio=0.2), *[GrowArrow(a) for a in ba], FadeIn(lb),
                  run_time=0.9)

        self.wait_until(self.cue_start("造一个", self.now))
        slots = [np.array([-5.4 + dx * k, yr, 0]) for k in range(7)]
        dummy = node("哨兵", C_GREY, dashed=True).move_to(slots[0])
        tail = T("tail", 22, C_YELLOW).next_to(dummy, DOWN, buff=0.2)
        self.play(FadeIn(dummy, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(tail, shift=UP * 0.1), run_time=0.4)
        p1 = Triangle(color=C_BLUE).scale(0.1).rotate(PI).set_fill(C_BLUE, 1).next_to(an[0], UP, buff=0.1)
        p2 = Triangle(color=C_PURPLE).scale(0.1).set_fill(C_PURPLE, 1).next_to(bn[0], DOWN, buff=0.1)
        self.play(FadeIn(p1), FadeIn(p2), run_time=0.4)

        self.wait_until(self.cue_start("每次比较", self.now))
        res = [dummy]
        res_arrows = VGroup()
        src = {"A": (an, aa, p1, A, UP), "B": (bn, ba, p2, B, DOWN)}
        idx = {"A": 0, "B": 0}
        t_end = self.cue_start("第一条走完", self.now + 14) - 0.3
        takes = [e for e in ev if e[0] == "take"]
        step = max(1.2, min(2.6, (t_end - self.now) / len(takes)))
        cmp_pos = np.array([3.6, 1.45, 0])
        for e in takes:
            _, which, k, v = e
            nodes, arr, ptr, vals, side = src[which]
            ia, ib = idx["A"], idx["B"]
            sym = r"\le" if which == "A" else r">"
            cmp = MathTex(str(A[ia]), sym, str(B[ib]), color=WHITE).scale(1.0).move_to(cmp_pos)
            cmp[0].set_color(C_BLUE)
            cmp[2].set_color(C_PURPLE)
            pick = T("取 list1" if which == "A" else "取 list2", 22, C_BLUE if which == "A" else C_PURPLE)
            pick.next_to(cmp, DOWN, buff=0.2)
            self.play(FadeIn(cmp), FadeIn(pick), run_time=step * 0.25)
            n = nodes[k]
            slot = slots[len(res)]
            anims = [n.animate.move_to(slot), FadeOut(cmp), FadeOut(pick)]
            if k < len(arr):
                anims.append(FadeOut(arr[k]))
            self.play(*anims, run_time=step * 0.35)
            ra = link(res[-1], n, C_YELLOW)
            res_arrows.add(ra)
            res.append(n)
            idx[which] += 1
            ptr_anim = (ptr.animate.next_to(nodes[k + 1], side, buff=0.1) if k + 1 < len(vals)
                        else FadeOut(ptr))
            self.play(GrowArrow(ra), tail.animate.next_to(n, DOWN, buff=0.2), ptr_anim, run_time=step * 0.3)
        self.wait_until(self.cue_start("第一条走完", self.now))
        rest = next(e for e in ev if e[0] == "rest")
        nodes, arr, ptr, vals, side = src[rest[1]]
        seg = VGroup(*nodes[rest[2]:])
        self.play(Indicate(seg, color=C_PURPLE), run_time=0.8)
        self.wait_until(self.cue_start("数组要", self.now))
        code = mono("tail.next = list1 if list1 else list2", 22, C_YELLOW).move_to([2.9, 2.6, 0])
        self.play(FadeIn(code), run_time=0.5)
        self.play(seg.animate.move_to(slots[len(res)]), FadeOut(ptr), run_time=0.8)
        ra = link(res[-1], seg[0], C_YELLOW)
        o1 = MathTex(r"O(1)", color=C_GREEN).scale(0.9).next_to(code, DOWN, buff=0.25)
        self.play(GrowArrow(ra), FadeIn(o1), run_time=0.6)
        res_arrows.add(ra)
        self.wait_until(self.cue_start("最后返回", self.now))
        ret = mono("return dummy.next", 24, C_YELLOW).move_to([0.9, -2.55, 0])
        self.play(res_arrows[0].animate.set_color(C_GREEN), dummy.animate.set_opacity(0.35),
                  FadeOut(tail), FadeIn(ret), run_time=0.8)
        self.hold_and_clear(head, la, lb, dummy, *res[1:], seg, res_arrows, code, o1, ret)

    # ---------------------------------------------------------------- 三指针反转：讲解第一轮
    def reverse_setup(self):
        vals = D.REV
        y = 1.35
        nodes = VGroup(*[node(v).move_to([-3.4 + 1.7 * k, y, 0]) for k, v in enumerate(vals)])
        nl = mono("None", 22, C_GREY).move_to([-5.45, y, 0])
        nr = mono("None", 22, C_GREY).move_to([5.45, y, 0])
        fwd = [link(nodes[k], nodes[k + 1]) for k in range(4)] + [link(nodes[4], nr.get_left())]
        lines = ["while curr:", "    nxt = curr.next", "    curr.next = prev", "    prev = curr",
                 "    curr = nxt"]
        marks = ["", "① 先存后继", "② 掉头", "③ prev 前进", "④ curr 前进"]
        code = VGroup(*[mono(s, 26) for s in lines]).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        code.move_to([-1.6, -1.55, 0])
        for line in code[1:]:
            line.shift(RIGHT * 0.55)                 # Text 会吃掉行首空格，缩进手动补
        notes = VGroup(*[T(m, 22, C_GREY).move_to([2.9, line.get_y(), 0], aligned_edge=LEFT)
                         if m else VMobject() for m, line in zip(marks, code)])
        return dict(nodes=nodes, nl=nl, nr=nr, fwd=fwd, code=code, notes=notes, y=y)

    def ptr_label(self, name, color, target, where):
        lab = mono(name, 22, color)
        return lab.next_to(target, where, buff=0.18 if where is UP else 0.2)

    def place(self, lab, target, where, extra=0.0):
        """返回把 lab 挪到 target 上方/下方的动画（extra 用于把 nxt 摆在 curr 下面一层）。"""
        p = target.get_center() + where * (NH / 2 + 0.3 + extra)
        return lab.animate.move_to(p)

    def reverse_beat(self):
        self.beat("reverse")
        R = self.reverse_setup()
        self.R = R
        head = T("三指针反转", 30).move_to([0, 3.25, 0])
        nodes, fwd = R["nodes"], R["fwd"]
        self.play(FadeIn(head), LaggedStart(*[FadeIn(n) for n in nodes], lag_ratio=0.12), FadeIn(R["nl"]),
                  FadeIn(R["nr"]), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(a) for a in fwd], lag_ratio=0.12), run_time=0.8)
        self.wait_until(self.cue_start("本质", self.now))
        demo = back_link(nodes[2], nodes[1])
        self.play(Indicate(fwd[1], color=C_YELLOW), run_time=0.7)
        ghost = fwd[1].copy()
        self.play(Transform(ghost, demo), run_time=1.0)
        self.play(FadeOut(ghost), run_time=0.4)

        self.wait_until(self.cue_start("单链表走不回去", self.now))
        prev = self.ptr_label("prev", C_TEAL, R["nl"], UP)
        curr = self.ptr_label("curr", C_YELLOW, nodes[0], DOWN)
        self.play(FadeIn(prev, shift=DOWN * 0.1), FadeIn(curr, shift=UP * 0.1), run_time=0.6)
        self.play(Indicate(prev, color=C_TEAL, scale_factor=1.3), run_time=0.8)

        self.wait_until(self.cue_start("每一轮四个动作", self.now))
        self.play(FadeIn(R["code"]), run_time=0.6)
        hl = SurroundingRectangle(R["code"][1], color=C_YELLOW, buff=0.08, stroke_width=2).set_fill(C_YELLOW, 0.12)
        hl.stretch_to_fit_width(R["code"].width + 0.3).align_to(R["code"], LEFT).shift(LEFT * 0.15)
        self.hl = hl
        nxt = self.ptr_label("nxt", C_PURPLE, nodes[1], DOWN)
        self.nxt_lab = nxt
        self.prev_lab, self.curr_lab = prev, curr
        t0 = self.cue_start("先存后继", self.now)
        self.wait_until(t0)
        self.round(0, 1.0, first=True)
        self.wait(max(0.1, self.left() - 0.2))
        self.head = head

    def round(self, k, step, first=False):
        """第 k 轮（0 起）的四个动作；step 是每个动作的时长。"""
        R = self.R
        nodes, fwd, code = R["nodes"], R["fwd"], R["code"]
        hl = self.hl
        nxt_t = nodes[k + 1] if k + 1 < 5 else R["nr"]
        prev_t = nodes[k - 1] if k > 0 else R["nl"]

        def show(line, *anims):
            target = hl.copy().set_y(code[line].get_y())
            note = R["notes"][line]
            if first:
                self.play(hl.animate.move_to(target), FadeIn(note), *anims, run_time=step)
            else:
                self.play(hl.animate.move_to(target), *anims, run_time=step)
        if first:
            self.add(hl)
            self.bring_to_back(hl)
        nxt = self.nxt_lab
        nxt_pos = nxt_t.get_center() + DOWN * (NH / 2 + 0.75)
        if first:
            nxt.move_to(nxt_pos)
            show(1, FadeIn(nxt, shift=UP * 0.1))
        else:
            show(1, nxt.animate.move_to(nxt_pos))
        new = back_link(nodes[k], prev_t)
        show(2, Transform(fwd[k], new))
        show(3, self.prev_lab.animate.move_to(nodes[k].get_center() + UP * (NH / 2 + 0.3)))
        show(4, self.curr_lab.animate.move_to(nxt_t.get_center() + DOWN * (NH / 2 + 0.3)))

    def revrun_beat(self):
        self.beat("revrun")
        R = self.R
        nodes, fwd = R["nodes"], R["fwd"]
        _, rounds = D.reverse_trace()
        self.wait_until(self.cue_start("每一轮只改", self.now))
        self.round(1, 0.42)
        self.round(2, 0.42)
        self.wait_until(self.cue_start("一旦先掉了头", self.now))
        # 假设先掉头：curr 指向的 4 号结点之后的整条链没人记得
        k = 3
        self.play(Indicate(R["code"][1], color=C_RED), run_time=0.6)
        lost = VGroup(*nodes[k + 1:], *fwd[k + 1:], R["nr"])
        what = T("若不先存：后继地址丢失", 24, C_RED).move_to([2.9, 2.55, 0])
        ghost = back_link(nodes[k], nodes[k - 1], C_RED)
        self.play(FadeIn(what), FadeIn(ghost), fwd[k].animate.set_opacity(0.15), run_time=0.7)
        self.play(lost.animate.set_opacity(0.15), run_time=0.8)
        self.wait(1.2)
        self.play(lost.animate.set_opacity(1), fwd[k].animate.set_opacity(1), FadeOut(ghost), FadeOut(what),
                  run_time=0.6)
        R["nr"].set_opacity(1)
        self.round(3, 0.4)
        self.wait_until(self.cue_start("当前指针走到空", self.now))
        self.round(4, 0.45)
        newhead = T("新表头", 24, C_GREEN).next_to(self.prev_lab, UP, buff=0.12)
        self.play(nodes[4][0].animate.set_stroke(C_GREEN, 5), FadeIn(newhead), run_time=0.7)
        res = MathTex(r"5\to4\to3\to2\to1", color=C_GREEN).scale(0.8).move_to([3.6, -0.1, 0])
        assert D.reverse_trace()[0] == [5, 4, 3, 2, 1] and rounds[-1]["prev"] == 4
        self.play(FadeIn(res), run_time=0.5)
        self.hold_and_clear(self.head, nodes, VGroup(*fwd), R["nl"], R["nr"], R["code"], R["notes"], self.hl,
                            self.prev_lab, self.curr_lab, self.nxt_lab, newhead, res)

    # ---------------------------------------------------------------- 快慢指针找中点
    def middle_beat(self):
        self.beat("middle")
        head = T("快慢指针找中点", 30).move_to([0, 3.25, 0])
        rows = []
        dx, x0 = 1.4, -4.2
        for n, y in ((5, 1.25), (6, -1.15)):
            nodes = VGroup(*[node(k + 1, C_BLUE, w=0.72, h=0.56).move_to([x0 + dx * k, y, 0]) for k in range(n)])
            none = mono("None", 20, C_GREY).move_to([x0 + dx * n, y, 0])
            arrows = VGroup(*[link(nodes[k], nodes[k + 1]) for k in range(n - 1)], link(nodes[-1], none.get_left()))
            lab = MathTex(f"n={n}", color=C_GREY).scale(0.75).move_to([-6.0, y, 0])
            slow = T("慢", 22, C_TEAL).next_to(nodes[0], UP, buff=0.15)
            fast = T("快", 22, C_RED).next_to(nodes[0], DOWN, buff=0.15)
            rows.append(dict(n=n, nodes=nodes, none=none, arrows=arrows, lab=lab, slow=slow, fast=fast,
                             steps=D.middle_trace(n)))
        self.play(FadeIn(head), *[FadeIn(VGroup(r["nodes"], r["none"], r["arrows"], r["lab"])) for r in rows],
                  run_time=1.0)
        self.wait_until(self.cue_start("慢指针一次走一步", self.now))
        self.play(*[FadeIn(r["slow"]) for r in rows], *[FadeIn(r["fast"]) for r in rows], run_time=0.5)
        nmax = max(len(r["steps"]) for r in rows)
        for t in range(1, nmax):
            anims = []
            for r in rows:
                if t < len(r["steps"]):
                    s, f = r["steps"][t]
                    anims.append(r["slow"].animate.next_to(r["nodes"][s - 1], UP, buff=0.15))
                    tgt = r["nodes"][f - 1] if f else r["none"]
                    anims.append(r["fast"].animate.next_to(tgt, DOWN, buff=0.15))
            self.play(*anims, run_time=0.9)
            self.wait(0.3)
        self.wait_until(self.cue_start("五个结点时", self.now))
        r5, r6 = rows
        s5, s6 = r5["steps"][-1][0], r6["steps"][-1][0]
        m5 = T(f"第 {s5} 个 · 正中间", 22, C_TEAL).move_to([3.9, 2.3, 0])
        self.play(r5["nodes"][s5 - 1][0].animate.set_stroke(C_TEAL, 5), FadeIn(m5), run_time=0.7)
        self.wait_until(self.cue_start("六个结点时", self.now))
        m6 = T(f"第 {s6} 个 · 后半段第一个", 22, C_TEAL).move_to([3.9, -0.1, 0])
        self.play(r6["nodes"][s6 - 1][0].animate.set_stroke(C_TEAL, 5), FadeIn(m6), run_time=0.7)
        self.wait_until(self.cue_start("记一个式子", self.now))
        f = VGroup(T("慢指针停在第", 26, C_YELLOW),
                   MathTex(r"\left\lfloor \tfrac{n}{2} \right\rfloor + 1", color=C_YELLOW).scale(0.85),
                   T("个", 26, C_YELLOW)).arrange(RIGHT, buff=0.15).move_to([0.2, 0.05, 0])
        self.play(Write(f), run_time=1.2)
        self.hold_and_clear(head, f, m5, m6, *[VGroup(r["nodes"], r["none"], r["arrows"], r["lab"], r["slow"],
                                                       r["fast"]) for r in rows])

    # ---------------------------------------------------------------- Floyd 判圈
    def rho(self):
        F = D.floyd_trace()
        n, at = len(D.CYC_VALS), D.CYC_AT
        L = n - at
        cx, cy, r = 2.75, 0.25, 2.05
        pos = {}
        for k in range(at, n):
            ang = PI - (k - at) * TAU / L
            pos[k] = np.array([cx + r * np.cos(ang), cy + r * np.sin(ang), 0])
        for k in range(at):
            pos[k] = pos[at] + LEFT * 1.45 * (at - k)
        rad = 0.3
        nodes = VGroup(*[VGroup(Circle(rad, stroke_color=C_BLUE, stroke_width=3).set_fill(C_BLUE, 0.15),
                                MathTex(str(v)).scale(0.65)).move_to(pos[k]) for k, v in enumerate(D.CYC_VALS)])
        for nd in nodes:
            nd[1].move_to(nd[0])
        arrows = VGroup()
        for k in range(n):
            j = k + 1 if k + 1 < n else at
            a, b = pos[k], pos[j]
            u = (b - a) / np.linalg.norm(b - a)
            arrows.add(Arrow(a + u * rad, b - u * rad, buff=0.04, stroke_width=3, color=C_GREY,
                             tip_length=0.16, max_tip_length_to_length_ratio=0.35))
        return dict(F=F, pos=pos, nodes=nodes, arrows=arrows, L=L, at=at, cx=cx, cy=cy, r=r)

    def cycle_beat(self):
        self.beat("cycle")
        P = self.rho()
        self.P = P
        head = T("Floyd 判圈", 30).move_to([-3.8, 3.25, 0])
        self.play(FadeIn(head), LaggedStart(*[AnimationGroup(FadeIn(nd), GrowArrow(a))
                                              for nd, a in zip(P["nodes"], P["arrows"])], lag_ratio=0.25),
                  run_time=2.4)
        self.play(Indicate(P["arrows"][-1], color=C_RED, scale_factor=1.2), run_time=0.8)
        # 一个指针绕圈：停不下来
        walker = Circle(0.42, stroke_color=WHITE, stroke_width=3).move_to(P["pos"][0])
        self.play(FadeIn(walker), run_time=0.3)
        loop = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 3, 4, 5]
        self.play(Succession(*[walker.animate(run_time=0.18).move_to(P["pos"][k]) for k in loop[1:]]),
                  run_time=0.18 * (len(loop) - 1))
        self.play(FadeOut(walker), run_time=0.3)

        self.wait_until(self.cue_start("快慢指针照样能用", self.now))
        slow = Circle(0.42, stroke_color=C_TEAL, stroke_width=5).move_to(P["pos"][0])
        fast = Circle(0.52, stroke_color=C_RED, stroke_width=5).move_to(P["pos"][0])
        leg = VGroup(VGroup(Circle(0.12, stroke_color=C_TEAL, stroke_width=4), T("慢：一次一步", 22, C_TEAL)).arrange(RIGHT, buff=0.15),
                     VGroup(Circle(0.14, stroke_color=C_RED, stroke_width=4), T("快：一次两步", 22, C_RED)).arrange(RIGHT, buff=0.15))
        leg.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([-4.6, 2.2, 0])
        stepl = T("步数", 22, C_GREY)
        stepn = Integer(0, color=WHITE).scale(0.8)
        gapl = T("追及距离", 22, C_GREY)
        gapn = Integer(0, color=C_YELLOW).scale(0.8).set_opacity(0)
        info = VGroup(VGroup(stepl, stepn).arrange(RIGHT, buff=0.25),
                      VGroup(gapl, gapn).arrange(RIGHT, buff=0.25)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        info.move_to([-4.6, -1.6, 0])
        self.play(FadeIn(slow), FadeIn(fast), FadeIn(leg), FadeIn(info[0]), run_time=0.6)
        ph1 = P["F"]["phase1"]
        L, at = P["L"], P["at"]
        t_meet = self.cue_start("这个例子", self.now + 6) + 5.5
        step = max(0.7, min(1.2, (t_meet - self.now) / (len(ph1) - 1)))
        prev_f = 0
        shown_gap = False
        for t in range(1, len(ph1)):
            s, f = ph1[t]
            mid = prev_f + 1 if prev_f + 1 < len(D.CYC_VALS) else at
            anims = [slow.animate(run_time=step).move_to(P["pos"][s]),
                     Succession(fast.animate(run_time=step / 2).move_to(P["pos"][mid]),
                                fast.animate(run_time=step / 2).move_to(P["pos"][f])),
                     ChangeDecimalToValue(stepn, t, run_time=step)]
            both_in = s >= at
            gap = (s - f) % L
            if both_in:
                if not shown_gap:
                    gapn.set_value((ph1[t - 1][0] - ph1[t - 1][1]) % L if ph1[t - 1][0] >= at else gap)
                    gapn.set_value(gap)
                    self.play(*anims, run_time=step)
                    self.play(FadeIn(info[1][0]), gapn.animate.set_opacity(1), run_time=0.4)
                    shown_gap = True
                else:
                    anims.append(ChangeDecimalToValue(gapn, gap, run_time=step))
                    self.play(*anims, run_time=step)
            else:
                self.play(*anims, run_time=step)
            prev_f = f
        meet = P["F"]["meet"]
        boom = Flash(P["pos"][meet], color=C_YELLOW, line_length=0.3, flash_radius=0.6)
        ctr = np.array([P["cx"], P["cy"], 0])
        meet_lab = T("相遇", 24, C_YELLOW).move_to(P["pos"][meet] + (ctr - P["pos"][meet]) * 0.42)
        self.play(boom, FadeIn(meet_lab), run_time=0.8)
        F = P["F"]
        nums = T(f"环外 {F['a']} 个 · 环长 {F['L']} · 慢指针走 {F['slow_steps']} 步", 22).move_to([-3.4, -2.7, 0])
        F = P["F"]
        assert (F["a"], F["L"], F["slow_steps"]) == (3, 7, 7)
        self.play(FadeIn(nums), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.2))
        self.cyc = dict(slow=slow, fast=fast, leg=leg, info=info, meet_lab=meet_lab, nums=nums, head=head)

    def entry_beat(self):
        self.beat("entry")
        P, C = self.P, self.cyc
        F = P["F"]
        at, meet, L = P["at"], F["meet"], P["L"]
        q = T("环入口在哪？", 28, C_YELLOW).move_to([-3.8, 2.2, 0])
        self.play(FadeOut(C["leg"]), FadeOut(C["info"]), FadeOut(C["nums"]), FadeOut(C["fast"]),
                  FadeIn(q), P["nodes"][at][0].animate.set_stroke(C_YELLOW, 4), run_time=0.7)
        self.wait_until(self.cue_start("相遇时", self.now))
        # a：表头到入口（直线段）；b：入口到相遇点（弧）
        a_line = Line(P["pos"][0] + DOWN * 0.55, P["pos"][at] + DOWN * 0.55, color=C_TEAL, stroke_width=5)
        a_lab = MathTex("a", color=C_TEAL).scale(0.9).next_to(a_line, DOWN, buff=0.12)
        ang0, ang1 = PI, PI - (meet - at) * TAU / L
        b_arc = Arc(radius=P["r"] + 0.55, start_angle=ang0, angle=ang1 - ang0, arc_center=[P["cx"], P["cy"], 0],
                    color=C_PURPLE, stroke_width=5)
        mid = (ang0 + ang1) / 2
        b_lab = MathTex("b", color=C_PURPLE).scale(0.9).move_to(
            [P["cx"] + (P["r"] + 0.95) * np.cos(mid), P["cy"] + (P["r"] + 0.95) * np.sin(mid), 0])
        self.play(Create(a_line), FadeIn(a_lab), run_time=0.8)
        self.play(Create(b_arc), FadeIn(b_lab), run_time=0.8)
        eqs = VGroup(VGroup(T("慢走", 24, C_TEAL), MathTex("a+b").scale(0.8)).arrange(RIGHT, buff=0.2),
                     VGroup(T("快走", 24, C_RED), MathTex("2(a+b)=a+b+kL").scale(0.8)).arrange(RIGHT, buff=0.2))
        eqs.arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([-3.9, -1.55, 0])
        self.play(FadeIn(eqs[0]), run_time=0.6)
        self.play(FadeIn(eqs[1]), run_time=0.6)
        self.wait_until(self.cue_start("多走的那一份", self.now))
        e3 = MathTex(r"\Rightarrow\ a+b=kL\ \Rightarrow\ a=kL-b", color=C_YELLOW).scale(0.75)
        e3.next_to(eqs, DOWN, buff=0.22, aligned_edge=LEFT)
        self.play(Write(e3), run_time=1.0)
        self.wait_until(self.cue_start("所以从相遇点", self.now))
        rest = Arc(radius=P["r"] + 0.55, start_angle=ang1, angle=-(TAU - (ang0 - ang1)), arc_center=[P["cx"], P["cy"], 0],
                   color=C_YELLOW, stroke_width=5)
        self.play(Create(rest), run_time=1.2)
        self.wait_until(self.cue_start("于是让一个指针", self.now))
        p = Circle(0.52, stroke_color=C_YELLOW, stroke_width=5).move_to(P["pos"][0])
        plab = T("从表头", 20, C_YELLOW).next_to(p, UP, buff=0.12)
        self.play(FadeIn(p), FadeIn(plab), FadeOut(C["meet_lab"]), FadeOut(q), run_time=0.6)
        self.wait_until(self.cue_start("这里环外长度", self.now))
        slow = C["slow"]
        ph2 = F["phase2"]
        for t in range(1, len(ph2)):
            pk, sk = ph2[t]
            self.play(p.animate.move_to(P["pos"][pk]), slow.animate.move_to(P["pos"][sk]), FadeOut(plab),
                      run_time=0.8)
        assert F["entry"] == at and D.CYC_VALS[at] == 4
        ent = T("环入口", 24, C_YELLOW).move_to(P["pos"][at] + UP * 0.8 + LEFT * 0.3)
        self.play(Flash(P["pos"][at], color=C_YELLOW, flash_radius=0.6), FadeIn(ent), run_time=0.8)
        self.hold_and_clear(P["nodes"], P["arrows"], a_line, a_lab, b_arc, b_lab, eqs, e3, rest, p, slow, ent,
                            C["head"])

    # ---------------------------------------------------------------- 回顾：五个模板
    def recap_beat(self):
        self.beat("recap")
        rows = [("哨兵", "dummy = ListNode(0, head)", C_TEAL),
                ("三指针反转", "nxt = curr.next  # 先存后继", C_YELLOW),
                ("快慢找中点", "slow, fast = slow.next, fast.next.next", C_RED),
                ("快慢判环 / 入口", "if slow is fast: …", C_RED),
                ("换道对齐", "pA = pA.next if pA else headB", C_PURPLE)]
        grp = VGroup()
        for name, code, col in rows:
            grp.add(VGroup(T(name, 26, col), mono(code, 22)))
        for r in grp:
            r[0].move_to([-6.2, 0, 0], aligned_edge=LEFT)
            r[1].move_to([-1.9, 0, 0], aligned_edge=LEFT)
        grp.arrange(DOWN, buff=0.38, aligned_edge=LEFT).move_to([0, 0.95, 0])
        for r in grp:
            r[0].move_to([-6.2, r[0].get_y(), 0], aligned_edge=LEFT)
            r[1].move_to([-1.9, r[0].get_y(), 0], aligned_edge=LEFT)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in grp], lag_ratio=0.5), run_time=6.0)
        self.wait_until(self.cue_start("链表题的错误", self.now))
        small = VGroup()
        for k, n in enumerate((0, 1, 2)):
            g = VGroup(*[node(v + 1, C_GREY, w=0.5, h=0.4) for v in range(n)])
            if n:
                g.arrange(RIGHT, buff=0.35)
            lab = T(f"{n} 个结点", 20, C_GREY)
            cell = VGroup(g, lab).arrange(DOWN, buff=0.15) if n else VGroup(mono("None", 20, C_GREY), lab).arrange(DOWN, buff=0.15)
            small.add(cell)
        small.arrange(RIGHT, buff=1.2).move_to([0, -2.1, 0])
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.2) for s in small], lag_ratio=0.3), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 2 周 线性表 附录 A · LeetCode 21、206、876、141、142", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
