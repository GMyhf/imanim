"""汉诺塔：相信更小的自己（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。所有移动序列、树形与计数来自 hanoidata
（test_hanoi.py 用三根栈逐步模拟验证合法性，并对撞讲义输出与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hanoidata as H  # noqa: E402
from cine import *  # noqa: E402,F403

DCOL = [C_YELLOW, C_RED, C_BLUE, C_PURPLE, C_TEAL, C_GREEN, "#FF8E5E", "#C9E265"]
GOLD_A, GOLD_B = "#F7D774", "#B9822A"


def mv_tex(k, s, d, **kw):
    return MathTex(rf"{k}{{:}}\ \mathrm{{{s}}}\to\mathrm{{{d}}}", **kw)


class Towers(VGroup):
    """三根柱子 + n 个盘子，带栈状态；move() 返回「抬起 → 弧线越过 → 落下」的动画。"""

    def __init__(self, n, xs=(-4.5, 0.0, 4.5), base_y=-2.25, peg_h=3.0, h=0.36, wmin=1.0, wstep=0.5,
                 gold=False, numbered=True):
        super().__init__()
        self.xs = dict(zip("ABC", xs))
        self.base_y, self.h = base_y, h
        self.top_y = base_y + peg_h + 0.35
        half = (wmin + wstep * (n - 1)) / 2 + 0.35
        self.base = Line([xs[0] - half, base_y, 0], [xs[2] + half, base_y, 0], stroke_color=C_GREY, stroke_width=4)
        self.pegs = VGroup(*[RoundedRectangle(corner_radius=0.05, width=0.1, height=peg_h, stroke_width=0)
                             .set_fill(C_GREY, 0.55).move_to([x, base_y + peg_h / 2, 0]) for x in xs])
        self.names = VGroup(*[T(c, 26, C_GREY).move_to([x, base_y - 0.38, 0]) for c, x in zip("ABC", xs)])
        self.discs = {}
        for k in range(n, 0, -1):
            col = (interpolate_color(ManimColor(GOLD_A), ManimColor(GOLD_B), (k - 1) / max(1, n - 1))
                   if gold else ManimColor(DCOL[(k - 1) % len(DCOL)]))
            d = RoundedRectangle(corner_radius=h * 0.4, width=wmin + wstep * (k - 1), height=h * 0.86,
                                 stroke_color=interpolate_color(col, ManimColor(WHITE), 0.35), stroke_width=2)
            d.set_fill(col, 0.88)
            if numbered:
                d.add(MathTex(str(k), color="#14161c").scale(0.55).move_to(d))
            self.discs[k] = d
        self.stacks = {"A": list(range(n, 0, -1)), "B": [], "C": []}
        for lvl, k in enumerate(self.stacks["A"]):
            self.discs[k].move_to(self.slot("A", lvl))
        self.add(self.base, self.pegs, self.names, *[self.discs[k] for k in range(n, 0, -1)])

    def slot(self, peg, level):
        return np.array([self.xs[peg], self.base_y + self.h * (level + 0.5), 0])

    def where(self, k):
        return next(p for p, st in self.stacks.items() if k in st)

    def move(self, k, dst, rt=0.9):
        src = self.where(k)
        assert self.stacks[src][-1] == k, "只能移动柱顶的盘子"
        assert not self.stacks[dst] or self.stacks[dst][-1] > k, "大盘不能压小盘"
        self.stacks[src].pop()
        target = self.slot(dst, len(self.stacks[dst]))
        self.stacks[dst].append(k)
        return self.travel(self.discs[k], src, dst, target, rt)

    def travel(self, mob, src, dst, target, rt=0.9):
        """mob 的中心沿「竖直抬起 → 弧线 → 竖直落下」到 target。"""
        up = mob.get_center().copy()
        up[1] = max(up[1], self.top_y + mob.height / 2)
        over = np.array([target[0], up[1], 0])
        arc = -PI * 0.42 if self.xs[dst] > self.xs[src] else PI * 0.42
        return Succession(mob.animate(run_time=rt * 0.24, rate_func=smooth).move_to(up),
                          mob.animate(run_time=rt * 0.52, path_arc=arc, rate_func=smooth).move_to(over),
                          mob.animate(run_time=rt * 0.24, rate_func=smooth).move_to(target))


class HanoiLesson(Lesson):
    def construct(self):
        for b in ("title", "rules", "idea", "code", "run", "tree", "inorder", "count", "legend", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        """当前 beat 里第一句包含 key 的字幕起点（绝对时间）。"""
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：传说
    def title_beat(self):
        self.beat("title")
        tw = Towers(8, xs=(-4.6, 0, 4.6), base_y=-2.4, peg_h=2.5, h=0.27, wmin=0.75, wstep=0.36,
                    gold=True, numbered=False)
        title = T("汉诺塔", 80).move_to([0, 2.7, 0])
        sub = T("相信更小的自己", 36, C_BLUE).next_to(title, DOWN, buff=0.25)
        credit = T("1883 · Édouard Lucas", 22, C_GREY).next_to(sub, DOWN, buff=0.2)
        self.play(Create(tw.base), FadeIn(tw.pegs), FadeIn(tw.names), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(tw.discs[k], shift=DOWN * 0.6) for k in range(8, 0, -1)],
                              lag_ratio=0.18), Write(title), run_time=2.2)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(credit), run_time=0.8)
        rt = 0.55
        for k, s, d in H.moves(8):                   # 僧侣开工：按真实解法走，配音结束前停手
            if self.left() < rt + 1.0:
                break
            self.play(tw.move(k, d, rt))
        self.wait(max(0.1, self.left() - 0.8))
        self.play(FadeOut(VGroup(tw, title, sub, credit)), run_time=0.8)

    # ---------------------------------------------------------------- 规则
    def rules_beat(self):
        self.beat("rules")
        tw = Towers(3)
        r1 = T("① 每次只移动一片", 30).move_to([-3.2, 3.0, 0])
        r2 = T("② 大盘不能压在小盘上", 30).next_to(r1, RIGHT, buff=1.0)
        self.play(FadeIn(tw, shift=UP * 0.3), run_time=1.0)
        self.play(FadeIn(r1, shift=DOWN * 0.2), run_time=0.6)
        self.play(tw.move(1, "C", 0.9))
        ok = MathTex(r"\checkmark", color=C_GREEN).scale(1.3).next_to(tw.discs[1], UP, buff=0.3)
        self.play(FadeIn(ok, scale=1.5), run_time=0.4)
        self.play(FadeIn(r2, shift=DOWN * 0.2), FadeOut(ok), run_time=0.6)
        d2 = tw.discs[2]
        home = d2.get_center().copy()
        hover = tw.slot("C", 1) + UP * 0.9
        self.play(tw.travel(d2, "A", "C", hover, 0.9))
        cross = Cross(d2, stroke_color=C_RED, stroke_width=6).scale(0.6)
        self.play(Create(cross), Wiggle(d2, scale_value=1.05), run_time=0.8)
        self.play(FadeOut(cross), tw.travel(d2, "C", "A", home, 0.9))
        self.play(tw.move(1, "A", 0.8))
        t = self.cue_start("任务", self.now)
        self.wait_until(t)
        goal = VGroup(T("起点", 22, C_BLUE).next_to(tw.names[0], RIGHT, buff=0.15),
                      T("辅助", 22, C_GREY).next_to(tw.names[1], RIGHT, buff=0.15),
                      T("目标", 22, C_GREEN).next_to(tw.names[2], RIGHT, buff=0.15))
        self.play(LaggedStart(*[FadeIn(g) for g in goal], lag_ratio=0.4),
                  Indicate(tw.names[0], color=C_BLUE), Indicate(tw.names[2], color=C_GREEN), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tw, r1, r2, goal)), run_time=0.6)

    # ---------------------------------------------------------------- 三步：相信它
    def idea_beat(self):
        self.beat("idea")
        tw = Towers(4, xs=(-4.6, 0, 4.6), h=0.4)
        self.play(FadeIn(tw, shift=UP * 0.3), run_time=1.0)
        top3 = VGroup(*[tw.discs[k] for k in (1, 2, 3)])
        box = DashedVMobject(SurroundingRectangle(top3, buff=0.12, corner_radius=0.12, color=C_TEAL), num_dashes=40)
        lab = MathTex("n-1", color=C_TEAL).scale(0.8).next_to(box, LEFT, buff=0.2)
        nlab = MathTex("n", color=C_PURPLE).scale(0.8).next_to(tw.discs[4], LEFT, buff=0.3)
        self.wait_until(self.cue_start("看成一整块", self.now) + 0.6)
        self.play(Create(box), Write(lab), Write(nlab), run_time=1.2)
        block = VGroup(top3, box, lab)
        steps = VGroup(T("① n−1 个：A → B", 26, C_TEAL),
                       T("② 第 n 个：A → C", 26, C_PURPLE), T("③ n−1 个：B → C", 26, C_TEAL))
        steps.arrange(RIGHT, buff=0.8).move_to([0, 3.1, 0])
        for i, (key, src, dst) in enumerate((("第一步", "A", "B"), ("第二步", "A", "C"), ("第三步", "B", "C"))):
            self.wait_until(self.cue_start(key, self.now))
            if i == 1:
                tw.stacks["A"] = [4]
                big = VGroup(tw.discs[4], nlab)
                target = big.get_center() + (tw.slot("C", 0) - tw.discs[4].get_center())
                self.play(FadeIn(steps[i], shift=DOWN * 0.2), tw.travel(big, "A", "C", target, 1.4))
            else:
                shift = tw.slot(dst, 0 if dst == "B" else 1)[0] - top3.get_center()[0]
                base_lvl = 0 if dst == "B" else 1
                dy = tw.slot(dst, base_lvl + 1)[1] - top3.get_center()[1]
                target = block.get_center() + np.array([shift, dy, 0])
                self.play(FadeIn(steps[i], shift=DOWN * 0.2), tw.travel(block, src, dst, target, 1.6))
        tw.stacks = {"A": [], "B": [], "C": [4, 3, 2, 1]}
        self.wait_until(self.cue_start("三个怎么移", self.now))
        top2 = VGroup(tw.discs[1], tw.discs[2])
        box2 = DashedVMobject(SurroundingRectangle(top2, buff=0.07, corner_radius=0.1, color=C_YELLOW), num_dashes=30)
        lab2 = MathTex("n-2", color=C_YELLOW).scale(0.7).next_to(box, RIGHT, buff=0.2).align_to(box2, UP)
        self.play(Create(box2), Write(lab2), run_time=1.0)
        box3 = DashedVMobject(SurroundingRectangle(tw.discs[1], buff=0.04, corner_radius=0.08, color=C_RED),
                              num_dashes=22)
        self.play(Create(box3), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tw, box, lab, nlab, steps, box2, lab2, box3)), run_time=0.6)

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="def hanoi(n, src, aux, dst, moves):\n    if n == 0:\n        return\n"
                                "    hanoi(n - 1, src, dst, aux, moves)\n"
                                "    moves.append(f\"{n}:{src}->{dst}\")\n"
                                "    hanoi(n - 1, aux, src, dst, moves)\n",
                    language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 26})
        code.move_to([-1.2, 0.4, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=1.0)
        lines = code.code_lines
        tags = [("① n−1 个 → 辅助柱", C_TEAL), ("② 最大的 → 目标柱", C_PURPLE), ("③ n−1 个 → 目标柱", C_TEAL)]
        marks = VGroup()
        for i, (txt, col) in enumerate(tags):
            ln = lines[3 + i]
            hl = SurroundingRectangle(ln, color=col, buff=(0.09, 0.02), stroke_width=2)   # 左右留白；上下收紧，相邻三行的框不叠边
            tag = T(txt, 24, col).next_to(code, RIGHT, buff=0.35).match_y(ln)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.8)
            marks.add(hl, tag)
        self.wait_until(self.cue_start("基例", self.now + 0.5) + 0.8)
        base = SurroundingRectangle(VGroup(lines[1], lines[2]), color=C_GREY, buff=(0.09, 0.02), stroke_width=2)
        btag = T("基例", 24, C_GREY).next_to(code, RIGHT, buff=0.35).match_y(base)
        self.play(Create(base), FadeIn(btag), run_time=0.7)
        self.wait_until(self.cue_start("第一步和第三步", self.now))
        trust = T("相信它们已经解决", 30, C_YELLOW).next_to(code, DOWN, buff=0.5)
        self.play(Indicate(marks[0], color=C_YELLOW), Indicate(marks[4], color=C_YELLOW),
                  Write(trust), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, marks, base, btag, trust)), run_time=0.6)

    # ---------------------------------------------------------------- 跑一遍 n = 3
    def run_beat(self):
        self.beat("run")
        tw = Towers(3, xs=(-5.3, -2.55, 0.2), h=0.42, wmin=0.9, wstep=0.62)
        self.play(FadeIn(tw, shift=UP * 0.3), run_time=0.8)
        head = T("moves", 26, C_GREY).move_to([4.3, 2.9, 0])
        cnt_l = T("步数", 24, C_GREY).move_to([-5.6, 2.9, 0])
        cnt = Integer(0).scale(0.9).next_to(cnt_l, RIGHT, buff=0.25)
        self.play(FadeIn(head), FadeIn(cnt_l), FadeIn(cnt), run_time=0.5)
        ms = H.moves(3)
        starts = [c["start"] for c in self.cue_times() if "号盘" in c["text"]]
        if len(starts) != len(ms):                              # 拿不到句级时间戳时均匀铺开
            starts = list(np.linspace(self.now + 0.3, self.now + max(3.0, self.left() - 2.0), len(ms)))
        log = VGroup()
        for i, ((k, s, d), t) in enumerate(zip(ms, starts)):
            self.wait_until(t)
            row = mv_tex(k, s, d, color=DCOL[k - 1]).scale(0.85).move_to([4.3, 2.25 - 0.6 * i, 0])
            log.add(row)
            self.play(tw.move(k, d, 1.0), FadeIn(row, shift=LEFT * 0.3), cnt.animate.set_value(i + 1),
                      run_time=1.0)
        self.wait_until(self.cue_start("一共", self.now))
        self.play(Indicate(cnt, color=C_YELLOW, scale_factor=1.6),
                  Circumscribe(log, color=C_YELLOW, buff=0.15), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tw, head, cnt_l, cnt, log)), run_time=0.6)

    # ---------------------------------------------------------------- 调用树
    def tree_beat(self):
        self.beat("tree")
        calls = H.call_tree(3)
        ys = {0: 2.2, 1: 0.85, 2: -0.5}
        nodes, edges = {}, VGroup()
        for c in calls:
            x = -5.4 + 1.8 * (c.inorder - 1)
            box = RoundedRectangle(corner_radius=0.14, width=1.55, height=0.62, stroke_color=DCOL[c.n - 1],
                                   stroke_width=3).set_fill(BG, 1)
            lab = mv_tex(c.n, c.src, c.dst).scale(0.62).move_to(box)
            nodes[c.id] = VGroup(box, lab).move_to([x, ys[c.depth], 0])
        edge_of = {}
        for c in calls:
            for ch in c.children:
                e = Line(nodes[c.id].get_bottom(), nodes[ch].get_top(), stroke_color=C_GREY, stroke_width=2.5)
                edges.add(e)
                edge_of[ch] = e
        ptr = SurroundingRectangle(nodes[0], color=C_YELLOW, buff=0.08, corner_radius=0.16)
        step = max(0.5, min(1.0, (self.left() * 0.55) / len(calls)))
        for c in calls:                                       # 按真实调用顺序（先序）长出来
            anims = [GrowFromCenter(nodes[c.id])]
            anims.append(Create(ptr) if c.id == 0 else ptr.animate.move_to(nodes[c.id]))
            if c.id in edge_of:
                anims.append(Create(edge_of[c.id]))
            self.play(*anims, run_time=step)
        self.play(FadeOut(ptr), run_time=0.3)
        self.wait_until(self.cue_start("一加二加四", self.now))
        levels = [[nodes[c.id] for c in calls if c.depth == d] for d in range(3)]
        eq = MathTex("1", "+", "2", "+", "4", "=", "7").scale(1.0).move_to([-4.6, 3.25, 0])
        for d, part in enumerate((eq[0], eq[2], eq[4])):
            self.play(*[Indicate(m, color=C_YELLOW, scale_factor=1.12) for m in levels[d]],
                      FadeIn(part), *( [FadeIn(eq[2 * d - 1])] if d else []), run_time=0.7)
        self.play(FadeIn(eq[5:]), run_time=0.5)
        self.tree_nodes, self.tree_edges, self.calls, self.eq = nodes, edges, calls, eq

    # ---------------------------------------------------------------- 中序遍历
    def inorder_beat(self):
        self.beat("inorder")
        nodes, calls = self.tree_nodes, self.calls
        order = sorted(calls, key=lambda c: c.inorder)
        badges = {}
        ring = SurroundingRectangle(nodes[order[0].id], color=C_BLUE, buff=0.08, corner_radius=0.16)
        step = max(0.45, min(0.9, (self.left() * 0.45) / len(order)))
        self.play(FadeOut(self.eq), Create(ring), run_time=0.5)
        for c in order:
            b = VGroup(Circle(0.2, color=C_BLUE, stroke_width=3).set_fill(C_BLUE, 0.25),
                       MathTex(str(c.inorder), color=WHITE).scale(0.55))
            b.next_to(nodes[c.id], UP, buff=0.06)
            badges[c.id] = b
            self.play(ring.animate.move_to(nodes[c.id]), FadeIn(b, scale=1.6), run_time=step)
        self.play(FadeOut(ring), run_time=0.3)
        self.wait_until(self.cue_start("压平", self.now))
        row_y = -2.2
        self.play(FadeOut(self.tree_edges),
                  *[VGroup(nodes[c.id], badges[c.id]).animate.shift(UP * (row_y - nodes[c.id].get_y()))
                    for c in calls], run_time=1.6, rate_func=rate_functions.ease_in_out_cubic)
        out = VGroup(*[Text(f"{c.n}:{c.src}->{c.dst}", font=MONO, font_size=22, color=C_GREY)
                       .next_to(nodes[c.id], DOWN, buff=0.18) for c in order])
        self.play(LaggedStart(*[FadeIn(o, shift=UP * 0.15) for o in out], lag_ratio=0.15), run_time=1.4)
        self.wait_until(self.cue_start("中序遍历", self.now))
        lrr = VGroup(T("中序遍历", 40, C_BLUE), T("左 → 根 → 右", 32)).arrange(DOWN, buff=0.3).move_to([0, 1.3, 0])
        self.play(Write(lrr[0]), FadeIn(lrr[1], shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*nodes.values(), *badges.values(), out, lrr)), run_time=0.6)

    # ---------------------------------------------------------------- 2^n − 1
    def count_beat(self):
        self.beat("count")
        rec = MathTex(r"T(n)", "=", r"2\,T(n-1)", "+", "1").scale(1.1).move_to([0, 2.9, 0])
        sol = MathTex(r"T(n)", "=", r"2^n", "-", "1").scale(1.1).move_to(rec)
        sol[2].set_color(C_YELLOW)
        self.play(Write(rec), run_time=1.6)
        self.wait_until(self.cue_start("解出来", self.now))
        self.play(TransformMatchingTex(rec, sol), run_time=1.2)
        vals = [H.count(k) for k in range(1, 8)]
        bars, labs, ns = VGroup(), VGroup(), VGroup()
        for i, v in enumerate(vals):
            b = Rectangle(width=0.72, height=max(0.03, 3.5 * v / vals[-1]), stroke_width=0)
            b.set_fill(interpolate_color(ManimColor(C_BLUE), ManimColor(C_YELLOW), i / 6), 0.9)
            b.move_to([-3.6 + 1.2 * i, -2.45, 0], aligned_edge=DOWN)
            bars.add(b)
            labs.add(MathTex(str(v)).scale(0.7).next_to(b, UP, buff=0.12))
            ns.add(MathTex(f"n={i + 1}", color=C_GREY).scale(0.55).next_to(b, DOWN, buff=0.15))
        t = self.cue_start("一到七个", self.now)
        self.wait_until(t)
        step = 0.6                                           # 跟念数节奏：七个数约 4 秒念完
        self.play(FadeIn(ns), run_time=0.3)
        for b, l in zip(bars, labs):
            self.play(GrowFromEdge(b, DOWN), FadeIn(l, shift=UP * 0.2), run_time=step)
        self.wait_until(self.cue_start("翻一倍", self.now))
        arrows = VGroup(*[CurvedArrow(labs[i].get_top() + UP * 0.05, labs[i + 1].get_top() + UP * 0.05,
                                      angle=-PI / 3, color=C_GREY, stroke_width=2, tip_length=0.12)
                          for i in range(6)])
        x2 = VGroup(*[MathTex(r"\times 2", color=C_YELLOW).scale(0.5).next_to(a, UP, buff=0.02) for a in arrows])
        self.play(LaggedStart(*[AnimationGroup(Create(a), FadeIn(x)) for a, x in zip(arrows, x2)],
                              lag_ratio=0.2), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(sol, bars, labs, ns, arrows, x2)), run_time=0.6)

    # ---------------------------------------------------------------- 64 片金片
    def legend_beat(self):
        self.beat("legend")
        big = MathTex(r"2^{64}-1", "=", r"18\,446\,744\,073\,709\,551\,615").scale(1.0).move_to([0, 2.8, 0])
        big[0].set_color(C_YELLOW)
        assert H.count(64) == 18446744073709551615
        approx = MathTex(r"\approx 1.8\times 10^{19}", color=C_YELLOW).scale(1.1).next_to(big, DOWN, buff=0.4)
        self.play(Write(big[0]), run_time=1.0)
        self.play(Write(big[1:]), run_time=1.6)
        self.play(FadeIn(approx, shift=UP * 0.2), run_time=0.8)
        years = H.legend_years()
        yi = int(round(years / 1e8 / 10) * 10)               # 亿年，取到十位：5850
        earth = 45
        self.wait_until(self.cue_start("每秒", self.now))
        L = 11.0
        bar_h = Rectangle(width=L, height=0.5, stroke_width=0).set_fill(GOLD_B, 0.9)
        bar_h.move_to([0, -0.4, 0])
        bar_e = Rectangle(width=max(0.03, L * earth / (years / 1e8)), height=0.5, stroke_width=0).set_fill(C_BLUE, 1)
        bar_e.align_to(bar_h, LEFT).shift(DOWN * 1.25)
        lab_h = T(f"每秒一次，移完 64 片：约 {yi} 亿年", 28, GOLD_A).next_to(bar_h, UP, buff=0.18).align_to(bar_h, LEFT)
        bar_h_full = bar_h.copy()
        bar_h.stretch(0.001, 0, about_edge=LEFT)
        self.play(FadeIn(lab_h), Transform(bar_h, bar_h_full), run_time=2.0, rate_func=rate_functions.ease_in_quad)
        self.wait_until(self.cue_start("地球", self.now))
        lab_e = T(f"地球的年龄：约 {earth} 亿年", 28, C_BLUE).next_to(bar_e, RIGHT, buff=0.3)
        self.play(GrowFromEdge(bar_e, LEFT), FadeIn(lab_e, shift=LEFT * 0.2), run_time=1.0)
        self.play(Indicate(bar_e, color=C_BLUE, scale_factor=3), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(big, approx, bar_h, lab_h, bar_e, lab_e)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾：调用栈替你记住
    def recap_beat(self):
        self.beat("recap")
        tw = Towers(3, xs=(1.3, 3.6, 5.9), base_y=-1.9, peg_h=2.6, h=0.36, wmin=0.7, wstep=0.45)
        frames_args = [(3, "A", "B", "C"), (2, "A", "C", "B"), (1, "A", "B", "C")]
        stack_lab = T("调用栈", 26, C_GREY).move_to([-3.8, -2.45, 0])
        self.play(FadeIn(tw, shift=UP * 0.3), FadeIn(stack_lab), run_time=0.8)
        frames = VGroup()
        step = max(0.6, min(1.1, (self.left() * 0.45) / 5))
        for i, (n, s, a, d) in enumerate(frames_args):
            f = VGroup(RoundedRectangle(corner_radius=0.1, width=4.3, height=0.62,
                                        stroke_color=DCOL[n - 1], stroke_width=3).set_fill(BG, 1),
                       Text(f"hanoi({n}, {s}, {a}, {d})", font=MONO, font_size=24))
            f[1].move_to(f[0])
            f.move_to([-3.8, -1.75 + 0.75 * i, 0])
            frames.add(f)
            self.play(FadeIn(f, shift=DOWN * 0.4), run_time=step)
        self.play(tw.move(1, "C", step), Indicate(frames[2], color=C_YELLOW), run_time=step)
        self.play(FadeOut(frames[2], shift=UP * 0.4), run_time=step * 0.6)
        self.play(tw.move(2, "B", step), Indicate(frames[1], color=C_YELLOW), run_time=step)
        t = self.cue_start("只需要相信", self.now)
        self.wait_until(t)
        quote = T("相信：更小的问题已经解决", 44, C_YELLOW).move_to([0, 2.6, 0])
        self.play(Write(quote), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 8 周 递归 P26–P28 · OpenJudge 04147", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeOut(VGroup(tw, frames[:2], stack_lab)), quote.animate.move_to(UP * 0.3), run_time=1.0)
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
