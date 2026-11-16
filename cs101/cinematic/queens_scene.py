"""八皇后：回溯与剪枝（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。解、放置/冲突/撤销事件、搜索树与节点数来自 queensdata
（test_queens.py 对撞讲义输出、暴力枚举全排列、事件回放与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queensdata as Q  # noqa: E402
from cine import *  # noqa: E402,F403

SQ_A, SQ_B = "#232836", "#1a1e28"
SOL8 = Q.solve_queens(8)


def make_board(n, cell, center):
    center = np.array(center, dtype=float)
    sq = {}
    for r in range(n):
        for c in range(n):
            s = Square(cell, stroke_width=0).set_fill(SQ_A if (r + c) % 2 == 0 else SQ_B, 1)
            s.move_to(center + np.array([(c - (n - 1) / 2) * cell, ((n - 1) / 2 - r) * cell, 0]))
            sq[(r, c)] = s
    frame = Square(cell * n, stroke_color=C_GREY, stroke_width=2).move_to(center)
    return sq, frame


def queen(cell, color=C_YELLOW):
    d = Circle(cell * 0.32, stroke_color=WHITE, stroke_width=2).set_fill(color, 1)
    return VGroup(d, Text("Q", font=MONO, font_size=max(10, int(cell * 34)), color=BG).move_to(d))


def set_line(name, items, col):
    body = "{" + ", ".join(str(x) for x in items) + "}" if items else "{ }"
    return Text(f"{name} = {body}", font=MONO, font_size=24, color=col)


class QueensLesson(Lesson):
    def construct(self):
        for b in ("title", "rules", "sets", "diag", "walk", "tree", "count", "all", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        sq, frame = make_board(8, 0.6, (-3.0, 0.2, 0))
        self.play(FadeIn(VGroup(*sq.values())), Create(frame), run_time=1.0)
        qs = VGroup()
        for r, c1 in enumerate(SOL8[0]):
            q = queen(0.6).move_to(sq[(r, c1 - 1)])
            qs.add(q)
        self.play(LaggedStart(*[FadeIn(q, shift=DOWN * 0.5) for q in qs], lag_ratio=0.3), run_time=2.4)
        title = T("八皇后", 72).move_to([3.4, 1.6, 0])
        sub = T("回溯与剪枝", 36, C_BLUE).next_to(title, DOWN, buff=0.25)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait_until(self.cue_start("靠蛮力", self.now))
        brute = VGroup(T("蛮力", 26, C_RED), MathTex(r"19\,173\,961", color=C_RED).scale(0.9), T("步", 26, C_RED))
        brute.arrange(RIGHT, buff=0.2).move_to([3.4, -0.4, 0])
        self.play(FadeIn(brute, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("回溯加剪枝", self.now))
        smart = VGroup(T("回溯 + 剪枝", 26, C_GREEN), MathTex(r"2\,057", color=C_GREEN).scale(0.9), T("步", 26, C_GREEN))
        smart.arrange(RIGHT, buff=0.2).next_to(brute, DOWN, buff=0.35)
        assert Q.naive_nodes(8) == 19173961 and Q.pruned_nodes(8) == 2057
        self.play(FadeIn(smart, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*sq.values(), frame, qs, title, sub, brute, smart)), run_time=0.6)

    # ---------------------------------------------------------------- 规则：逐行放置
    def rules_beat(self):
        self.beat("rules")
        cell = 0.55
        sq, frame = make_board(8, cell, (-3.3, 0.1, 0))
        self.play(FadeIn(VGroup(*sq.values())), Create(frame), run_time=0.7)
        r0, c0 = 3, 2
        q = queen(cell).move_to(sq[(r0, c0)])
        self.play(FadeIn(q, scale=1.4), run_time=0.5)
        hit = Q.attacked(8, r0, c0)
        self.play(*[sq[p].animate.set_fill(interpolate_color(ManimColor(SQ_A), ManimColor(C_RED), 0.45), 1) for p in hit],
                  run_time=1.2)
        rule = VGroup(T("不同行", 30), T("不同列", 30), T("不同对角线", 30)).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        rule.move_to([2.6, 1.4, 0])
        self.play(LaggedStart(*[FadeIn(x, shift=LEFT * 0.2) for x in rule], lag_ratio=0.3), run_time=1.2)
        self.wait_until(self.cue_start("一行放一个", self.now))
        self.play(*[sq[p].animate.set_fill(SQ_A if (p[0] + p[1]) % 2 == 0 else SQ_B, 1) for p in hit],
                  FadeOut(q), run_time=0.6)
        bands = VGroup(*[Rectangle(width=cell * 8, height=cell, stroke_color=C_BLUE, stroke_width=2)
                         .move_to(VGroup(*[sq[(r, c)] for c in range(8)])) for r in range(8)])
        qs = VGroup(*[queen(cell).move_to(sq[(r, SOL8[0][r] - 1)]) for r in range(8)])
        self.play(LaggedStart(*[AnimationGroup(Create(bands[r]), FadeIn(qs[r], shift=DOWN * 0.3)) for r in range(8)],
                              lag_ratio=0.35), run_time=2.6)
        self.wait_until(self.cue_start("不同行自动满足", self.now))
        tick = MathTex(r"\checkmark", color=C_GREEN).scale(0.9).next_to(rule[0], LEFT, buff=0.25)
        self.play(FadeIn(tick, scale=1.5), rule[0].animate.set_color(C_GREEN), FadeOut(bands), run_time=0.8)
        self.wait_until(self.cue_start("只需要检查", self.now))
        need = VGroup(T("只需检查：", 26, C_GREY), T("列 + 两条对角线", 26, C_YELLOW)).arrange(RIGHT, buff=0.2)
        need.next_to(rule, DOWN, buff=0.6).align_to(rule, LEFT)
        self.play(FadeIn(need, shift=UP * 0.2), Indicate(rule[1], color=C_YELLOW), Indicate(rule[2], color=C_YELLOW),
                  run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*sq.values(), frame, qs, rule, tick, need)), run_time=0.6)

    # ---------------------------------------------------------------- 三个集合（讲义代码）
    def sets_beat(self):
        self.beat("sets")
        code = Code(code_string="def dfs(row):\n    if row == n:\n        res.append(tuple(path))\n        return\n"
                                "    for c in range(n):\n"
                                "        if c in cols or (row - c) in diag or (row + c) in anti:\n"
                                "            continue\n"
                                "        cols.add(c); diag.add(row - c); anti.add(row + c)\n"
                                "        path.append(c + 1)\n        dfs(row + 1)\n        path.pop()\n"
                                "        cols.remove(c); diag.remove(row - c); anti.remove(row + c)\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 18})
        code.move_to([-1.3, 0.3, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.1, 0.03), stroke_width=2)  # 左右留足、上下收紧：相邻两块高亮不叠边
            tag = T(txt, 22, col).next_to(code, RIGHT, buff=0.25).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
        mark([5, 6], "三次判断", "可行性剪枝", C_RED)
        mark([7, 8], "各加一个", "做选择", C_GREEN)
        mark([10, 11], "各删一个", "撤销", C_YELLOW)
        self.wait_until(self.cue_start("前后对称", self.now))
        pair = DashedLine(tags[2].get_right() + RIGHT * 0.15, tags[4].get_right() + RIGHT * 0.15, color=C_GREY)
        sym = T("对称", 22, C_GREY).next_to(pair, RIGHT, buff=0.12)
        self.play(Create(pair), FadeIn(sym), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, tags, pair, sym)), run_time=0.6)

    # ---------------------------------------------------------------- row − c 与 row + c
    def diag_beat(self):
        self.beat("diag")
        n, cell = 8, 0.62
        sq, frame = make_board(n, cell, (-2.9, 0.1, 0))
        self.play(FadeIn(VGroup(*sq.values())), Create(frame), run_time=0.7)
        pal = [C_BLUE, C_TEAL, C_GREEN, C_YELLOW, "#FF8E5E", C_RED, C_PURPLE]

        def col_of(v, lo, hi):
            t = (v - lo) / (hi - lo)
            k = t * (len(pal) - 1)
            i = min(int(k), len(pal) - 2)
            return interpolate_color(ManimColor(pal[i]), ManimColor(pal[i + 1]), k - i)

        def numbers(f, lo, hi):
            return VGroup(*[MathTex(str(f(r, c)), color=WHITE).scale(0.5).move_to(sq[(r, c)]).set_z_index(2)
                            for r in range(n) for c in range(n)]), \
                [sq[(r, c)].animate.set_fill(interpolate_color(ManimColor(SQ_A), col_of(f(r, c), lo, hi), 0.55), 1)
                 for r in range(n) for c in range(n)]
        self.wait_until(self.cue_start("行号减列号", self.now))
        nums, fills = numbers(lambda r, c: r - c, -(n - 1), n - 1)
        self.play(*fills, run_time=1.0)
        self.play(FadeIn(nums), run_time=0.8)
        eq1 = VGroup(MathTex(r"\searrow", color=C_PURPLE).scale(1.2), MathTex(r"r - c", "=", r"\text{const}").scale(0.95))
        eq1.arrange(RIGHT, buff=0.3).move_to([3.6, 1.3, 0])
        self.wait_until(self.cue_start("从左上到右下", self.now))
        # 半透明、压在数字下面：斜线正好穿过要读的那一串常数
        line1 = Line(sq[(0, 0)].get_center(), sq[(7, 7)].get_center(), stroke_color=WHITE, stroke_width=4,
                     stroke_opacity=0.5).set_z_index(1)
        self.play(Create(line1), FadeIn(eq1, shift=LEFT * 0.2), run_time=1.2)
        self.wait_until(self.cue_start("行号加列号", self.now))
        nums2, fills2 = numbers(lambda r, c: r + c, 0, 2 * (n - 1))
        self.play(FadeOut(line1), *fills2, ReplacementTransform(nums, nums2), run_time=1.2)
        eq2 = VGroup(MathTex(r"\swarrow", color=C_TEAL).scale(1.2), MathTex(r"r + c", "=", r"\text{const}").scale(0.95))
        eq2.arrange(RIGHT, buff=0.3).next_to(eq1, DOWN, buff=0.6).align_to(eq1, LEFT)
        self.wait_until(self.cue_start("从右上到左下", self.now))
        line2 = Line(sq[(0, 7)].get_center(), sq[(7, 0)].get_center(), stroke_color=WHITE, stroke_width=4,
                     stroke_opacity=0.5).set_z_index(1)
        self.play(Create(line2), FadeIn(eq2, shift=LEFT * 0.2), run_time=1.2)
        self.wait_until(self.cue_start("丢进集合", self.now))
        into = VGroup(Text("diag.add(row - c)", font=MONO, font_size=22, color=C_PURPLE),
                      Text("anti.add(row + c)", font=MONO, font_size=22, color=C_TEAL)).arrange(DOWN, buff=0.2,
                                                                                               aligned_edge=LEFT)
        into.next_to(eq2, DOWN, buff=0.7).align_to(eq1, LEFT)
        self.play(FadeIn(into, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*sq.values(), frame, nums2, line2, eq1, eq2, into)), run_time=0.6)

    # ---------------------------------------------------------------- 4 皇后完整回溯
    def walk_beat(self):
        self.beat("walk")
        n, cell = 4, 1.0
        sq, frame = make_board(n, cell, (-3.5, 0.2, 0))
        head = T("4 皇后", 26, C_GREY).next_to(frame, UP, buff=0.2)
        self.play(FadeIn(VGroup(*sq.values())), Create(frame), FadeIn(head), run_time=0.7)
        res, ev, calls = Q.trace(n)
        cols, diag, anti, path = [], [], [], []
        panel = VGroup(set_line("cols", cols, C_BLUE), set_line("diag", diag, C_PURPLE),
                       set_line("anti", anti, C_TEAL), Text("path = [ ]", font=MONO, font_size=24, color=WHITE))
        panel.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([2.6, 1.0, 0])
        stats = VGroup(T("放下", 24, C_GREY), Integer(0).scale(0.8), T("解", 24, C_GREY), Integer(0, color=C_GREEN).scale(0.8))
        stats.arrange(RIGHT, buff=0.25).next_to(panel, DOWN, buff=0.6).align_to(panel, LEFT)
        stats[2:].shift(RIGHT * 0.55)                      # 给两位数留位置，免得「放下 16」顶到「解」
        self.play(FadeIn(panel), FadeIn(stats), run_time=0.5)
        sols = VGroup()
        # 事件分组：连续的同一行冲突合成一拍
        steps = []
        for e in ev:
            if e[0] == "conflict" and steps and steps[-1][0] == "conflicts" and steps[-1][1] == e[1]:
                steps[-1][2].append(e[2])
            elif e[0] == "conflict":
                steps.append(["conflicts", e[1], [e[2]]])
            else:
                steps.append(list(e))
        queens_on = {}
        crosses = VGroup()
        n_place = 0
        t_first = self.cue_start("第一行放在", self.now)
        t_second = self.cue_start("第二行试过去", t_first + 2)
        t_third = self.cue_start("第三行无处可放", t_second + 3)
        t_rest = self.cue_start("每次撤销", t_third + 4)
        t_end = self.t0 + LEAD + self.dur.get("walk", 20.0) - 0.5          # 快进段一直放到这段配音结尾
        sync = {0: t_first, 1: t_second, 3: t_third, 4: t_third + 1.8}

        def panel_anims():
            new = VGroup(set_line("cols", sorted(cols), C_BLUE), set_line("diag", sorted(diag), C_PURPLE),
                         set_line("anti", sorted(anti), C_TEAL),
                         Text("path = [" + ", ".join(map(str, path)) + "]" if path else "path = [ ]",
                              font=MONO, font_size=24, color=WHITE))
            new.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(panel, aligned_edge=LEFT)
            return [Transform(panel[i], new[i]) for i in range(4)]
        for k, st in enumerate(steps):
            if k in sync:
                self.wait_until(sync[k])
            if k < 5:
                rt = 0.8
            else:
                if k == 5:
                    self.wait_until(t_rest)
                rt = max(0.2, min(0.6, (t_end - self.now) / max(1, len(steps) - k + 2)))
            clear = [FadeOut(crosses)] if len(crosses) else []
            if st[0] == "conflicts":
                r = st[1]
                crosses = VGroup(*[Cross(sq[(r, c)], stroke_color=C_RED, stroke_width=5).scale(0.45) for c in st[2]])
                self.play(*clear, LaggedStart(*[Create(x) for x in crosses], lag_ratio=0.25), run_time=rt)
            elif st[0] == "place":
                r, c = st[1], st[2]
                cols.append(c); diag.append(r - c); anti.append(r + c); path.append(c + 1)
                q = queen(cell).move_to(sq[(r, c)])
                queens_on[r] = q
                n_place += 1
                self.play(*clear, FadeIn(q, shift=DOWN * 0.3), *panel_anims(),
                          ChangeDecimalToValue(stats[1], n_place), run_time=rt)
                crosses = VGroup()
            elif st[0] == "remove":
                r, c = st[1], st[2]
                cols.remove(c); diag.remove(r - c); anti.remove(r + c); path.pop()
                q = queens_on.pop(r)
                self.play(*clear, FadeOut(q, shift=UP * 0.3), *panel_anims(), run_time=rt)
                crosses = VGroup()
            else:
                mini = VGroup(*[q.copy() for q in queens_on.values()])
                self.play(*clear, frame.animate.set_stroke(C_GREEN, 5), ChangeDecimalToValue(stats[3], len(sols) + 1),
                          run_time=rt)
                lab = Text("".join(map(str, st[1])), font=MONO, font_size=24, color=C_GREEN)
                lab.next_to(stats, DOWN, buff=0.35 + 0.45 * len(sols)).align_to(stats, LEFT)
                self.play(TransformFromCopy(mini, lab), frame.animate.set_stroke(C_GREY, 2), run_time=rt)
                sols.add(lab)
                crosses = VGroup()
        if len(crosses):
            self.play(FadeOut(crosses), run_time=0.3)
        self.play(Indicate(stats, color=C_YELLOW), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*sq.values(), frame, head, panel, stats, sols, *queens_on.values())), run_time=0.6)

    # ---------------------------------------------------------------- 4 皇后的搜索树
    def tree_beat(self):
        self.beat("tree")
        res, ev, calls = Q.trace(4)
        xs = [c.x for c in calls]
        mid, span = (max(xs) + min(xs)) / 2, max(1.0, max(xs) - min(xs))
        dx = min(1.4, 11.0 / span)
        ys = {0: 2.7, 1: 1.55, 2: 0.4, 3: -0.75, 4: -1.9}
        nodes, edges, marks = {}, VGroup(), VGroup()
        for c in calls:
            col = C_GREEN if c.solution else (C_RED if not c.children else WHITE)
            circ = Circle(0.24, stroke_color=col, stroke_width=3)
            lab = MathTex(str(c.col + 1) if c.col is not None else r"\cdot").scale(0.55)
            nodes[c.id] = VGroup(circ, lab).move_to([(c.x - mid) * dx, ys[c.row], 0])
        for c in calls:
            for ch in c.children:
                edges.add(Line(nodes[c.id].get_bottom(), nodes[ch].get_top(), stroke_color=C_GREY, stroke_width=2.5))
            if c.conflicts:
                row = VGroup(*[Cross(Square(0.14), stroke_color=C_RED, stroke_width=3) for _ in c.conflicts])
                row.arrange(RIGHT, buff=0.04).next_to(nodes[c.id], DOWN, buff=0.06)
                if c.children:
                    row.next_to(nodes[c.id], RIGHT, buff=0.06)
                marks.add(row)
        self.play(LaggedStart(*[FadeIn(nodes[c.id], scale=0.6) for c in calls], lag_ratio=0.08),
                  Create(edges), run_time=2.4)
        cnt = VGroup(T("递归调用", 24, C_GREY), MathTex(str(len(calls))).scale(0.9)).arrange(RIGHT, buff=0.25)
        cnt.move_to([-5.2, 2.7, 0])
        self.play(FadeIn(cnt), run_time=0.5)
        self.wait_until(self.cue_start("红叉", self.now))
        self.play(LaggedStart(*[FadeIn(m, scale=1.4) for m in marks], lag_ratio=0.1), run_time=1.6)
        n_conf = sum(len(c.conflicts) for c in calls)
        cc = VGroup(T("冲突剪掉", 24, C_RED), MathTex(str(n_conf), color=C_RED).scale(0.9)).arrange(RIGHT, buff=0.25)
        cc.next_to(cnt, DOWN, buff=0.25).align_to(cnt, LEFT)
        self.play(FadeIn(cc), run_time=0.5)
        self.wait_until(self.cue_start("只有两条路", self.now))
        sol_ids = [c.id for c in calls if c.solution]
        paths = VGroup()
        for sid in sol_ids:
            chain, cur = [], sid
            while calls[cur].parent is not None:
                chain.append(Line(nodes[calls[cur].parent].get_bottom(), nodes[cur].get_top(),
                                  stroke_color=C_GREEN, stroke_width=6))
                cur = calls[cur].parent
            paths.add(*chain)
        self.play(Create(paths), *[Indicate(nodes[s], color=C_GREEN, scale_factor=1.4) for s in sol_ids], run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*nodes.values(), edges, marks, cnt, cc, paths)), run_time=0.6)

    # ---------------------------------------------------------------- 8 皇后：剪枝前后节点数
    def count_beat(self):
        self.beat("count")
        rows = [("每行随便放，走到底才检查", Q.naive_nodes(8), C_RED, "随便放"),
                ("只保证不同列（全排列）", Q.perm_nodes(8), C_YELLOW, "不同列"),
                ("三个集合剪枝", Q.pruned_nodes(8), C_GREEN, "剪枝之后")]
        head = T("8 皇后：搜索的节点数（对数刻度）", 26, C_GREY).move_to([0, 3.0, 0])
        self.play(FadeIn(head), run_time=0.5)
        k = 9.0 / np.log10(rows[0][1])
        x0 = -5.6
        for i, (name, v, col, key) in enumerate(rows):
            self.wait_until(self.cue_start(key, self.now))
            y = 1.7 - 1.55 * i
            lab = T(name, 24, col).move_to([x0, y + 0.42, 0], aligned_edge=LEFT)
            bar = Rectangle(width=k * np.log10(v), height=0.42, stroke_width=0).set_fill(col, 0.8)
            bar.move_to([x0, y - 0.1, 0], aligned_edge=LEFT)
            num = MathTex(f"{v:,}".replace(",", r"\,"), color=col).scale(0.85).next_to(bar, RIGHT, buff=0.25)
            if num.get_right()[0] > 6.8:
                num.next_to(bar.get_right(), DOWN, buff=0.15).align_to(bar, RIGHT).shift(UP * 0.0)
            self.play(FadeIn(lab), GrowFromEdge(bar, LEFT), FadeIn(num), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(*[FadeOut(m) for m in self.mobjects if m not in self.subs], run_time=0.6)

    # ---------------------------------------------------------------- 92 个解
    def all_beat(self):
        self.beat("all")
        size, gap = 0.5, 0.08
        boards = VGroup()
        for s in SOL8:
            bg = Square(size, stroke_color=C_GREY, stroke_width=1).set_fill("#1d2230", 1)
            dots = VGroup(*[Dot(radius=0.028, color=C_YELLOW).move_to(
                bg.get_center() + np.array([(c - 1 - 3.5) * size / 8, (3.5 - r) * size / 8, 0]))
                for r, c in enumerate(s)])
            boards.add(VGroup(bg, dots))
        boards.arrange_in_grid(4, 23, buff=gap).move_to([0, 1.55, 0])
        cnt = VGroup(MathTex(str(len(SOL8)), color=C_YELLOW).scale(1.1), T("个解", 28)).arrange(RIGHT, buff=0.2)
        cnt.move_to([0, 3.25, 0])
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in boards], lag_ratio=0.03), FadeIn(cnt), run_time=3.0)
        self.wait_until(self.cue_start("第一个是", self.now))
        big = []
        for idx, x in ((0, -3.6), (91, 3.0)):
            hl = SurroundingRectangle(boards[idx], color=C_YELLOW, buff=0.03, stroke_width=3)
            sq, frame = make_board(8, 0.22, (x, -1.35, 0))
            qs = VGroup(*[Dot(radius=0.07, color=C_YELLOW).move_to(sq[(r, c - 1)]) for r, c in enumerate(SOL8[idx])])
            lab = Text("".join(map(str, SOL8[idx])), font=MONO, font_size=28, color=C_YELLOW)
            lab.next_to(frame, RIGHT, buff=0.35)
            tag = T("第一个" if idx == 0 else "最后一个", 22, C_GREY).next_to(lab, UP, buff=0.15).align_to(lab, LEFT)
            grp = VGroup(*sq.values(), frame, qs)
            self.play(Create(hl), FadeIn(grp, scale=0.6), run_time=0.8)
            self.play(Write(lab), FadeIn(tag), run_time=0.8)
            big += [hl, grp, lab, tag]
            if idx == 0:
                self.wait_until(self.cue_start("最后一个", self.now))
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(boards, cnt, *big)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        l1 = VGroup(T("回溯", 34, C_YELLOW), MathTex("="), T("DFS", 32), MathTex("+"), T("撤销", 34, C_RED))
        l1.arrange(RIGHT, buff=0.25)
        l2 = VGroup(T("剪枝", 34, C_GREEN), MathTex("="), T("剪掉注定走不通的整棵子树", 30)).arrange(RIGHT, buff=0.25)
        lines = VGroup(l1, l2).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([0, 1.4, 0])
        self.play(FadeIn(l1, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("剪枝，就是", self.now))
        self.play(FadeIn(l2, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("两个必犯错误", self.now))
        errs = VGroup(T("两个必犯错误", 26, C_GREY),
                      VGroup(T("收答案忘了拷贝", 28, C_RED), T("·", 28, C_GREY), T("回溯时忘了还原", 28, C_RED))
                      .arrange(RIGHT, buff=0.3)).arrange(DOWN, buff=0.25).move_to([0, -0.9, 0])
        self.play(FadeIn(errs, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 9 周 回溯 P5–P6、P11–P13 · OpenJudge 02754", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
