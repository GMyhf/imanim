"""斐波那契：一棵树怎样塌缩成一行（3B1B 风格）。

由 make.py 驱动：环境变量 CINE_TIMING 指向各 beat 的配音时长与句级时间戳，
场景按配音给每个 beat 留足时间，并把实际起点写到 CINE_MARKS。
所有数字来自 fibdata（test_fib.py 对撞真实递归 / lru_cache）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fibdata  # noqa: E402
from cine import *  # noqa: E402,F403

NCOLOR = {1: C_GREY, 2: C_TEAL, 3: C_YELLOW, 4: C_RED, 5: C_PURPLE, 6: C_BLUE}


N = 6
FACTS = fibdata.facts(N)



def fib_spiral(k: int = 8, unit: float = 0.26) -> VGroup:
    """斐波那契方块铺砌 + 黄金螺线（片头背景）。"""
    sizes = [fibdata.fib(i) for i in range(1, k + 1)]
    squares, arcs, labels = VGroup(), VGroup(), VGroup()
    x0 = y0 = 0
    x1 = y1 = 0
    dirs = ["down", "right", "up", "left"]
    for i, s in enumerate(sizes):
        d = dirs[i % 4] if i else "down"
        if i == 0:
            a, b, x0, y0, x1, y1 = 0, 0, 0, 0, 1, 1
            start, center = (0, 1), (1, 1)
        elif d == "right":
            a, b = x1, y0
            start, center = (x1, y0), (x1, y1)
            x1 += s
        elif d == "up":
            a, b = x0, y1
            start, center = (x1, y1), (x0, y1)
            y1 += s
        elif d == "left":
            a, b = x0 - s, y0
            start, center = (x0, y1), (x0, y0)
            x0 -= s
        else:
            a, b = x0, y0 - s
            start, center = (x0, y0), (x1, y0)
            y0 -= s
        col = NCOLOR[i + 1] if i < 6 else C_BLUE
        sq = Square(s * unit, stroke_color=col, stroke_width=2.5, fill_color=col, fill_opacity=0.10)
        sq.move_to([(a + s / 2) * unit, (b + s / 2) * unit, 0])
        squares.add(sq)
        if s * unit > 0.45:
            labels.add(MathTex(str(s), color=col).scale(min(1.2, 0.28 * s * unit + 0.35)).move_to(sq))
        sx, sy = start
        cx, cy = center
        th = np.arctan2(sy - cy, sx - cx)
        arcs.add(Arc(radius=s * unit, start_angle=th, angle=PI / 2, arc_center=[cx * unit, cy * unit, 0],
                     stroke_color=C_YELLOW, stroke_width=4))
    g = VGroup(squares, labels, arcs)
    return g.move_to(ORIGIN)


class FibLesson(Lesson):
    def construct(self):
        self.title_beat()
        self.define_beat()
        self.code_beat()
        self.tree_beat()
        self.repeat_beat()
        self.growth_beat()
        self.memo_beat()
        self.collapse_beat()
        self.table_beat()
        self.recap_beat()
        self.finish()

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        d = self.beat("title")
        sp = fib_spiral()
        squares, labels, arcs = sp
        self.play(LaggedStart(*[DrawBorderThenFill(s) for s in squares], lag_ratio=0.35, run_time=3.2),
                  LaggedStart(*[FadeIn(l, scale=0.5) for l in labels], lag_ratio=0.35, run_time=3.2))
        self.play(Create(arcs, run_time=2.4, rate_func=linear))
        title = T("斐波那契", 84).shift(UP * 0.45)
        sub = T("一棵树怎样塌缩成一行", 40, C_BLUE).next_to(title, DOWN, buff=0.35)
        self.play(squares.animate.set_stroke(opacity=0.28).set_fill(opacity=0.04),
                  labels.animate.set_opacity(0.18), arcs.animate.set_stroke(opacity=0.35),
                  Write(title, run_time=1.6))
        self.play(FadeIn(sub, shift=UP * 0.2))
        src = T("计算概论（B）· 第 8 周 递归 · OpenJudge 02753", 22, C_GREY).to_corner(DR, buff=0.4).shift(UP * 0.55)
        self.play(FadeIn(src))
        self.wait(max(0.1, self.left() - 0.8))
        self.play(FadeOut(VGroup(sp, title, sub, src)), run_time=0.8)

    # ---------------------------------------------------------------- 定义
    def define_beat(self):
        self.beat("define")
        rule = MathTex(r"F(1)=F(2)=1", r"\qquad", r"F(n)", r"=", r"F(n-1)", r"+", r"F(n-2)").scale(1.05)
        rule.shift(UP * 2.2)
        rule[4].set_color(C_TEAL)
        rule[6].set_color(C_YELLOW)
        self.play(Write(rule[:2]), run_time=1.6)
        self.play(Write(rule[2:]), run_time=1.6)
        vals = [fibdata.fib(i) for i in range(1, 8)]
        nums = VGroup(*[MathTex(str(v)).scale(1.5) for v in vals]).arrange(RIGHT, buff=0.95).shift(DOWN * 0.1)
        idx = VGroup(*[MathTex(f"F({i})", color=C_GREY).scale(0.6).next_to(nums[i - 1], DOWN, buff=0.35)
                       for i in range(1, 8)])
        self.play(FadeIn(nums[0], shift=UP * 0.3), FadeIn(nums[1], shift=UP * 0.3), FadeIn(idx[:2]))
        step = max(0.7, min(1.25, (self.left() - 0.5) / 5))
        for i in range(2, 7):
            a, b = nums[i - 2], nums[i - 1]
            self.play(a.animate.set_color(C_YELLOW), b.animate.set_color(C_TEAL), run_time=step * 0.3)
            self.play(TransformFromCopy(VGroup(a, b), nums[i]), FadeIn(idx[i]),
                      a.animate.set_color(WHITE), b.animate.set_color(WHITE), run_time=step * 0.7)
        self.define_group = VGroup(rule, nums, idx)

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="def fib(n):\n    if n <= 2:\n        return 1\n    return fib(n - 1) + fib(n - 2)\n",
                    language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 30})
        code.move_to(UP * 0.9)
        self.play(FadeOut(self.define_group, shift=UP * 0.5), FadeIn(code, shift=UP * 0.5), run_time=1.2)
        self.wait(max(0.1, min(4.5, self.left() * 0.35)))
        ok = VGroup(MathTex(r"\texttt{fib(10)}", r"\to", r"55"),).scale(1.0)
        ok[0][2].set_color(C_GREEN)
        ok.next_to(code, DOWN, buff=0.6).shift(LEFT * 2.2)
        check = MathTex(r"\checkmark", color=C_GREEN).next_to(ok, RIGHT, buff=0.3)
        self.play(Write(ok), run_time=1.0)
        self.play(FadeIn(check, scale=1.6), run_time=0.5)
        slow = MathTex(r"\texttt{fib(40)}", r"\to").next_to(ok, RIGHT, buff=1.6)
        spinner = Arc(radius=0.24, angle=1.5 * PI, stroke_color=C_RED, stroke_width=6).next_to(slow, RIGHT, buff=0.3)
        self.play(Write(slow), Create(spinner), run_time=0.9)
        spinner.add_updater(lambda m, dt: m.rotate(-4 * dt))
        q = MathTex("?", color=C_RED).scale(1.4).next_to(spinner, RIGHT, buff=0.3)
        self.wait(max(0.1, self.left() - 1.3))
        self.play(FadeIn(q, scale=2), run_time=0.5)
        self.code, self.code_extra = code, VGroup(ok, check, slow, spinner, q)

    # ---------------------------------------------------------------- 调用树
    def build_tree(self):
        nodes = fibdata.apply_memo(fibdata.call_tree(N))
        xs = [n.x for n in nodes]
        mid = (min(xs) + max(xs)) / 2
        gap, top, dy, r = 1.45, 2.55, 1.15, 0.32
        mobs, edges = [], {}
        for nd in nodes:
            pos = np.array([(nd.x - mid) * gap, top - dy * nd.depth, 0])
            circ = Circle(r, stroke_color=WHITE, stroke_width=3.5).set_fill(BG, 1).move_to(pos)
            lab = MathTex(str(nd.n)).scale(0.85).move_to(pos)
            mobs.append(VGroup(circ, lab))
        for nd in nodes:
            if nd.parent is not None:
                p, c = mobs[nd.parent][0].get_center(), mobs[nd.id][0].get_center()
                u = (c - p) / np.linalg.norm(c - p)
                edges[nd.id] = Line(p + u * r, c - u * r, stroke_color=C_GREY, stroke_width=3)
        return nodes, mobs, edges

    def tree_beat(self):
        self.beat("tree")
        self.code_extra[3].clear_updaters()
        corner = self.code.copy().scale(0.42).to_corner(UL, buff=0.25)
        self.play(FadeOut(self.code_extra), Transform(self.code, corner), run_time=1.0)
        nodes, mobs, edges = self.build_tree()
        self.nodes, self.mobs, self.edges = nodes, mobs, edges
        lab = T("调用次数", 26, C_GREY).move_to([-5.75, 1.75, 0])
        cnt = Integer(0, color=WHITE).scale(1.1).next_to(lab, DOWN, buff=0.18)
        self.play(FadeIn(lab), FadeIn(cnt), run_time=0.4)
        ptr = Circle(0.44, stroke_color=C_YELLOW, stroke_width=6).move_to(mobs[0])
        step = max(0.45, min(0.85, (self.left() - 2.6) / len(nodes)))
        for nd in nodes:
            m = mobs[nd.id]
            anims = [GrowFromCenter(m), cnt.animate.set_value(nd.id + 1)]
            if nd.parent is None:
                anims.append(Create(ptr))
            else:
                anims += [Create(edges[nd.id]), ptr.animate.move_to(m)]
            self.play(*anims, run_time=step)
        self.play(FadeOut(ptr), Indicate(cnt, color=C_YELLOW, scale_factor=1.5), run_time=1.0)
        self.counter = VGroup(lab, cnt)

    # ---------------------------------------------------------------- 重叠子问题
    def repeat_beat(self):
        self.beat("repeat")
        # 半透明填充：LaggedStart 会把这些圆重新加到场景最上层，不透明填充会把圆里的数字永久盖住
        self.play(LaggedStart(*[m[0].animate.set_stroke(NCOLOR[nd.n]).set_fill(NCOLOR[nd.n], 0.22)
                                for nd, m in zip(self.nodes, self.mobs)], lag_ratio=0.06, run_time=2.4))
        tally = VGroup()
        step = max(1.0, min(2.6, (self.left() - 3.2) / 3))
        for i, k in enumerate((4, 3, 2)):
            row = VGroup(MathTex(rf"\texttt{{fib({k})}}", color=NCOLOR[k]), MathTex(r"\times"),
                         MathTex(str(FACTS["repeats"][k]), color=NCOLOR[k])).arrange(RIGHT, buff=0.2).scale(0.9)
            row.move_to([5.6, 3.35 - 0.52 * i, 0])
            tally.add(row)
            same = [m for nd, m in zip(self.nodes, self.mobs) if nd.n == k]
            self.play(LaggedStart(*[Circumscribe(m, Circle, color=NCOLOR[k], buff=0.08) for m in same],
                                  lag_ratio=0.15), FadeIn(row, shift=LEFT * 0.3), run_time=step)
        term = T("重叠子问题", 36, C_YELLOW).move_to([5.6, 1.72, 0])
        self.play(Write(term), run_time=1.2)
        self.tally = VGroup(tally, term)

    # ---------------------------------------------------------------- 指数增长
    def growth_beat(self):
        self.beat("growth")
        tree = VGroup(*self.mobs, *self.edges.values())
        tree.save_state()
        self.play(FadeOut(self.tally), FadeOut(self.counter),
                  tree.animate.scale(0.4).to_corner(UL, buff=0.3).shift(DOWN * 0.95),
                  FadeOut(self.code), run_time=1.2)
        top = 20
        calls = [fibdata.naive_calls(n) for n in range(1, top + 1)]
        ax = Axes(x_range=[0, top + 1, 5], y_range=[0, 14000, 5000], x_length=7.4, y_length=4.4,
                  axis_config={"color": C_GREY, "include_tip": False}, tips=False,
                  x_axis_config={"numbers_to_include": [5, 10, 15, 20]},
                  y_axis_config={"numbers_to_include": [5000, 10000], "decimal_number_config": {"num_decimal_places": 0}})
        ax.move_to([2.6, 0.75, 0])
        xl = MathTex("n", color=C_GREY).next_to(ax.x_axis, DOWN, buff=0.45).align_to(ax.x_axis, RIGHT)
        yl = T("调用次数", 22, C_GREY).next_to(ax.y_axis, UP, buff=0.15)
        bars = VGroup()
        for n, c in enumerate(calls, 1):
            h = max(0.004, ax.c2p(0, c)[1] - ax.c2p(0, 0)[1])
            col = interpolate_color(ManimColor(C_BLUE), ManimColor(C_RED), n / top)
            bar = Rectangle(width=0.26, height=h, stroke_width=0, fill_color=col, fill_opacity=0.9)
            bar.move_to(ax.c2p(n, 0), aligned_edge=DOWN)
            bars.add(bar)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), run_time=1.0)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.25), run_time=3.0)
        ratio = MathTex(r"\frac{C(n+1)}{C(n)}", r"\to", r"\varphi", r"\approx 1.618").scale(0.85)
        ratio[2].set_color(C_YELLOW)
        ratio.move_to([-4.3, -1.2, 0])
        self.play(Write(ratio), Indicate(bars[-1], color=C_YELLOW), run_time=1.6)
        big = DecimalNumber(0, num_decimal_places=0, group_with_commas=True, color=C_RED).scale(1.15)
        lhs = MathTex(r"\texttt{fib(40)}", ":").scale(0.95)
        tail = T("次调用", 30)
        row = VGroup(lhs, big, tail).arrange(RIGHT, buff=0.3)
        row.shift([-0.3 - row.get_left()[0], -2.45 - row.get_y(), 0])   # 左端固定：数字变长只往右长，不出画
        big.add_updater(lambda m: m.next_to(lhs, RIGHT, buff=0.3))
        tail.add_updater(lambda m: m.next_to(big, RIGHT, buff=0.25))
        self.play(FadeIn(lhs), FadeIn(tail), run_time=0.4)
        self.play(ChangeDecimalToValue(big, FACTS["big_calls"]), run_time=max(1.2, min(3.0, self.left() - 0.3)),
                  rate_func=rate_functions.ease_in_expo)
        big.clear_updaters(), tail.clear_updaters()
        self.growth_group = VGroup(ax, xl, yl, bars, ratio, row)
        self.tree = tree

    # ---------------------------------------------------------------- 记忆化
    def memo_beat(self):
        self.beat("memo")
        self.play(FadeOut(self.growth_group), Restore(self.tree), FadeIn(self.code), run_time=1.2)
        cells, vals = VGroup(), {}
        for k in range(1, N + 1):
            sq = Square(0.56, stroke_color=NCOLOR[k], stroke_width=3).move_to([2.95 + 0.66 * (k - 1), 3.3, 0])
            cells.add(VGroup(sq, MathTex(str(k), color=C_GREY).scale(0.5).next_to(sq, DOWN, buff=0.08)))
        head = T("memo", 26, C_GREY).next_to(cells, LEFT, buff=0.3)
        self.play(FadeIn(head), LaggedStart(*[Create(c) for c in cells], lag_ratio=0.1), run_time=1.0)
        naive = VGroup(T("朴素", 22, C_GREY), Integer(FACTS["naive_calls"]).scale(0.8)).arrange(RIGHT, buff=0.2)
        memo = VGroup(T("记忆化", 22, C_GREEN), Integer(0, color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.2)
        stats = VGroup(naive, memo).arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to([-5.65, 1.75, 0])
        self.play(FadeIn(stats), run_time=0.4)
        nodes, mobs, edges = self.nodes, self.mobs, self.edges
        # 事件序列：进入（指针 + 计数）/ 查表返回 / 算完写表
        events = []

        def walk(i):
            nd = nodes[i]
            if nd.pruned:
                return
            events.append(("enter", i))
            if nd.memo_hit:
                events.append(("hit", i))
                return
            for c in nd.children:
                walk(c)
            events.append(("done", i))
        walk(0)
        n_slow = sum(1 for e in events if e[0] in ("hit", "done"))
        step = max(0.35, min(1.0, (self.left() - 3.0) / (len(events) * 0.55 + n_slow)))
        ptr = Circle(0.44, stroke_color=C_YELLOW, stroke_width=6).move_to(mobs[0])
        self.play(Create(ptr), run_time=0.4)
        calls = 0
        for kind, i in events:
            nd, m = nodes[i], mobs[i]
            if kind == "enter":
                calls += 1
                self.play(ptr.animate.move_to(m), memo[1].animate.set_value(calls), run_time=step * 0.55)
            elif kind == "done":
                if nd.n not in vals:
                    v = MathTex(str(fibdata.fib(nd.n)), color=NCOLOR[nd.n]).scale(0.75).move_to(cells[nd.n - 1][0])
                    vals[nd.n] = v
                    self.play(ptr.animate.move_to(m), TransformFromCopy(m[1], v), run_time=step)
                else:
                    self.play(ptr.animate.move_to(m), run_time=step * 0.5)
            else:   # hit：查表返回，整棵子树不再生长
                dead = [j for j in range(len(nodes)) if nodes[j].pruned and self._under(j, i)]
                ghost = VGroup(*[mobs[j] for j in dead], *[edges[j] for j in dead])
                link = Arrow(cells[nd.n - 1][0].get_bottom(), m[0].get_top(), buff=0.08, color=C_GREEN,
                             stroke_width=3, max_tip_length_to_length_ratio=0.12)
                self.play(ghost.animate.set_opacity(0.07), m[0].animate.set_stroke(C_GREEN, 4),
                          Indicate(cells[nd.n - 1], color=C_GREEN), GrowArrow(link), run_time=step)
                self.play(FadeOut(link), run_time=step * 0.4)
        self.play(FadeOut(ptr), Indicate(memo, color=C_GREEN, scale_factor=1.3), run_time=0.8)
        self.memo_cells, self.memo_vals, self.memo_head, self.stats = cells, vals, head, stats

    def _under(self, j, i):
        p = self.nodes[j].parent
        while p is not None:
            if p == i:
                return True
            p = self.nodes[p].parent
        return False

    # ---------------------------------------------------------------- 塌缩
    def collapse_beat(self):
        self.beat("collapse")
        nodes, mobs, edges = self.nodes, self.mobs, self.edges
        dead = [i for i, nd in enumerate(nodes) if nd.pruned]
        self.play(FadeOut(VGroup(*[mobs[i] for i in dead], *[edges[i] for i in dead])),
                  FadeOut(self.stats), FadeOut(self.code), run_time=0.8)
        live = [nd for nd in nodes if not nd.pruned]
        keep = {nd.n: nd.id for nd in live if not nd.memo_hit}          # 每个参数的「本尊」
        hits = [nd for nd in live if nd.memo_hit]
        old_edges = VGroup(*[edges[nd.id] for nd in live if nd.parent is not None])
        # 1) 同参节点合并：查表叶子飞到本尊身上
        self.play(*[mobs[nd.id].animate.move_to(mobs[keep[nd.n]]) for nd in hits],
                  FadeOut(old_edges), run_time=1.6, audit=False)   # 同参节点故意叠在一起，下一行即移除
        self.remove(*[mobs[nd.id] for nd in hits])
        # 2) 排成一行：n = 1..6 从左到右，依赖箭头 n-1 → n、n-2 → n
        xs = {k: -4.0 + 1.6 * (k - 1) for k in range(1, N + 1)}
        self.play(*[mobs[keep[k]].animate.move_to([xs[k], 0.3, 0]) for k in keep], run_time=1.6)
        arrows = VGroup()
        for k in range(3, N + 1):
            a = mobs[keep[k - 1]][0]
            b = mobs[keep[k - 2]][0]
            t = mobs[keep[k]][0]
            arrows.add(Arrow(a.get_right(), t.get_left(), buff=0.05, color=NCOLOR[k], stroke_width=3))
            arrows.add(CurvedArrow(b.get_top() + UP * 0.02, t.get_top() + UP * 0.02, angle=-PI / 2.2,
                                   color=NCOLOR[k], stroke_width=3, tip_length=0.18))
        self.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.15), run_time=2.0)
        # 3) 摊平成数组：memo 表落下来，变成 dp 数组
        cells = VGroup(*[Square(1.0, stroke_color=NCOLOR[k], stroke_width=3).move_to([xs[k], -1.6, 0])
                         for k in range(1, N + 1)])
        vals = VGroup(*[MathTex(str(fibdata.fib(k)), color=NCOLOR[k]).move_to(cells[k - 1])
                        for k in range(1, N + 1)])
        self.play(ReplacementTransform(VGroup(*[c[0] for c in self.memo_cells]), cells),
                  ReplacementTransform(VGroup(*[self.memo_vals[k] for k in range(1, N + 1)]), vals),
                  FadeOut(VGroup(*[c[1] for c in self.memo_cells]), self.memo_head), run_time=1.6)
        self.wait(max(0.1, self.left() - 1.0))
        self.chain = VGroup(*[mobs[keep[k]] for k in range(1, N + 1)], arrows)
        self.row_cells, self.row_vals = cells, vals

    # ---------------------------------------------------------------- 自底向上
    def table_beat(self):
        self.beat("table")
        M, w = 10, 1.02
        x0 = -(M - 1) * w / 2
        cells = VGroup(*[Square(w * 0.92, stroke_color=C_GREY, stroke_width=3).move_to([x0 + w * i, -0.9, 0])
                         for i in range(M)])
        idx = VGroup(*[MathTex(str(i + 1), color=C_GREY).scale(0.55).next_to(cells[i], DOWN, buff=0.15)
                       for i in range(M)])
        code = Code(code_string="dp = [0, 1, 1] + [0] * (n - 2)\nfor i in range(3, n + 1):\n"
                                "    dp[i] = dp[i - 1] + dp[i - 2]\n",
                    language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 26})
        code.move_to([0, 2.2, 0])
        self.play(FadeOut(self.chain), ReplacementTransform(self.row_cells, cells[:N]),
                  FadeOut(self.row_vals), FadeIn(cells[N:]), FadeIn(idx), FadeIn(code, shift=DOWN * 0.3),
                  run_time=1.4)
        vals = [MathTex(str(fibdata.fib(i + 1))).move_to(cells[i]) for i in range(M)]
        self.play(FadeIn(vals[0], scale=1.5), FadeIn(vals[1], scale=1.5),
                  cells[0].animate.set_stroke(C_BLUE), cells[1].animate.set_stroke(C_BLUE), run_time=0.8)
        hl = SurroundingRectangle(code.code_lines[2], color=C_YELLOW,
                                  buff=0.06, stroke_width=2)
        self.play(Create(hl), run_time=0.4)
        step = max(0.6, min(1.3, (self.left() - 2.2) / (M - 2)))
        for i in range(2, M):
            a, b = cells[i - 1], cells[i - 2]
            self.play(a.animate.set_stroke(C_TEAL), b.animate.set_stroke(C_YELLOW), run_time=step * 0.25)
            self.play(TransformFromCopy(VGroup(vals[i - 1], vals[i - 2]), vals[i]),
                      cells[i].animate.set_stroke(C_BLUE), a.animate.set_stroke(C_BLUE),
                      b.animate.set_stroke(C_BLUE), run_time=step * 0.75)
        self.play(FadeOut(hl), cells[-1].animate.set_stroke(C_YELLOW, 5), vals[-1].animate.set_color(C_YELLOW),
                  Flash(cells[-1], color=C_YELLOW, flash_radius=0.75), run_time=1.0)
        self.table_group = VGroup(cells, idx, code, *vals)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        self.play(FadeOut(self.table_group), run_time=0.8)
        steps = [("调用树", "重叠子问题", C_RED), ("记忆化", "每棵子树只算一次", C_GREEN),
                 ("自底向上", "动态规划", C_BLUE)]
        cards = VGroup()
        for head, body, col in steps:
            box = RoundedRectangle(corner_radius=0.18, width=3.5, height=1.7, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.08)
            txt = VGroup(T(head, 34, col), T(body, 24, "#D8DCE6")).arrange(DOWN, buff=0.22).move_to(box)
            cards.add(VGroup(box, txt))
        cards.arrange(RIGHT, buff=0.9).shift(UP * 1.0)
        arrows = VGroup(*[Arrow(cards[i].get_right(), cards[i + 1].get_left(), buff=0.1, color=C_GREY)
                          for i in range(2)])
        step = max(0.8, (self.left() * 0.6) / 3)
        for i, c in enumerate(cards):
            anims = [FadeIn(c, shift=UP * 0.3)]
            if i:
                anims.append(GrowArrow(arrows[i - 1]))
            self.play(*anims, run_time=step)
        big = MathTex(r"O(\varphi^n)", color=C_RED).scale(1.6).shift(DOWN * 1.45)
        lin = MathTex(r"O(n)", color=C_GREEN).scale(1.6).move_to(big)
        self.play(Write(big), run_time=0.9)
        self.play(TransformMatchingTex(big, lin), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 8 周 递归 P23–P25 · OpenJudge 02753", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.play(FadeOut(VGroup(cards, arrows)), lin.animate.move_to(UP * 0.4).scale(0.8), run_time=1.0)
        self.play(FadeIn(src), run_time=0.6)
        self.clear_subs()
