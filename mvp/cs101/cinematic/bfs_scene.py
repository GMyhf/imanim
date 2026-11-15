"""BFS：一圈一圈往外推（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。迷宫事件序列、最短路、多源距离与访问顺序来自 bfsdata
（test_bfs.py 用松弛法求真最短距离对撞，并对撞讲义输出与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bfsdata as B  # noqa: E402
from cine import *  # noqa: E402,F403

SRC_COL = [C_BLUE, C_YELLOW, C_GREEN]


def layer_color(d, dmax):
    return interpolate_color(ManimColor(C_BLUE), ManimColor(C_YELLOW), min(1.0, d / max(1, dmax)))


def make_grid(n, m, cell, center, walls=()):
    sq = {}
    for i in range(n):
        for j in range(m):
            s = Square(cell * 0.94, stroke_color=C_GREY, stroke_width=1.5)
            s.move_to(np.array(center) + np.array([(j - (m - 1) / 2) * cell, ((n - 1) / 2 - i) * cell, 0]))
            if (i, j) in walls:
                s.set_fill(C_GREY, 0.55).set_stroke(C_GREY, 1.5)
            sq[(i, j)] = s
    return sq


class BFSLesson(Lesson):
    def construct(self):
        for b in ("title", "idea", "code", "maze", "path", "mark", "multi", "choose", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：石子与波纹
    def title_beat(self):
        self.beat("title")
        n, m, cell = 11, 21, 0.5
        sq = make_grid(n, m, cell, (0, -0.2, 0))
        grid = VGroup(*sq.values()).set_stroke(opacity=0.35)
        self.play(FadeIn(grid), run_time=0.8)
        c = (n // 2, m // 2)
        stone = Dot(sq[c].get_center() + UP * 3, radius=0.12, color=WHITE)
        self.play(FadeIn(stone), run_time=0.2)
        self.play(stone.animate.move_to(sq[c]), run_time=0.5, rate_func=rate_functions.ease_in_quad)
        self.remove(stone)
        dmax = n // 2 + m // 2
        layers = {}
        for (i, j), s in sq.items():
            layers.setdefault(abs(i - c[0]) + abs(j - c[1]), []).append(s)
        step = max(0.12, min(0.3, (self.left() * 0.55) / (dmax + 1)))
        for d in range(dmax + 1):
            col = layer_color(d, dmax)
            ring = Circle(0.2 + d * cell, stroke_color=WHITE, stroke_width=2).move_to(sq[c]).set_stroke(opacity=0.5)
            self.play(*[s.animate.set_fill(col, 0.75 - 0.5 * d / dmax).set_stroke(col, 1.5, 0.6)
                        for s in layers[d]], FadeIn(ring), run_time=step)
            self.remove(ring)
        title = T("BFS", 80).move_to([0, 0.4, 0])
        sub = T("一圈一圈往外推", 36, WHITE).next_to(title, DOWN, buff=0.25)
        back = BackgroundRectangle(VGroup(title, sub), color=BG, fill_opacity=0.82, buff=0.35)
        self.play(FadeIn(back), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(grid, back, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 按层推进
    def idea_beat(self):
        self.beat("idea")
        pos = {"s": (-4.5, 0.4), "a": (-1.5, 1.6), "b": (-1.5, -0.8), "c": (1.5, 1.6), "d": (1.5, -0.8)}
        vs = {k: VGroup(Circle(0.36, stroke_color=WHITE, stroke_width=3), MathTex(k).scale(0.9)).move_to([*p, 0])
              for k, p in pos.items()}
        es = VGroup(*[Line(vs[u].get_center(), vs[v].get_center(), buff=0.38, stroke_color=C_GREY, stroke_width=3)
                      for u, v in (("s", "a"), ("s", "b"), ("a", "c"), ("b", "d"))])
        self.play(FadeIn(es), *[FadeIn(v) for v in vs.values()], run_time=1.0)
        bands = VGroup()
        for d, ks, col in ((1, ("a", "b"), C_BLUE), (2, ("c", "d"), C_YELLOW)):
            x = pos[ks[0]][0]
            band = RoundedRectangle(corner_radius=0.3, width=1.3, height=3.6, stroke_color=col, stroke_width=2)
            band.set_fill(col, 0.08).move_to([x, 0.4, 0])
            lab = T(f"第 {d} 层：距离 {d}", 22, col).next_to(band, DOWN, buff=0.15)
            bands.add(VGroup(band, lab))
        self.play(Indicate(vs["s"], color=C_GREEN), vs["s"][0].animate.set_stroke(C_GREEN, 4), run_time=0.7)
        for k, b in enumerate(bands):
            ks = ("a", "b") if k == 0 else ("c", "d")
            self.play(FadeIn(b), *[vs[v][0].animate.set_stroke(b[0].get_stroke_color(), 4) for v in ks],
                      run_time=0.9)
        self.wait_until(self.cue_start("关键性质", self.now))
        key = VGroup(T("第一次访问到一个点", 28), T("走过的步数 = 最短距离", 28, C_YELLOW)).arrange(DOWN, buff=0.2)
        key.move_to([4.6, 1.0, 0])
        self.play(FadeIn(key, shift=LEFT * 0.2), run_time=1.0)
        self.wait_until(self.cue_start("注意前提", self.now))
        warn = VGroup(T("边权相同 → BFS", 24, C_GREEN), T("边权不同 → Dijkstra", 24, C_RED)).arrange(DOWN, buff=0.15)
        warn.next_to(key, DOWN, buff=0.6)
        self.play(FadeIn(warn, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(es, *vs.values(), bands, key, warn)), run_time=0.6)

    # ---------------------------------------------------------------- 模板与三条铁律
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="from collections import deque\ndef bfs(start, goal, get_neighbors):\n"
                                "    if start == goal:\n        return 0\n    visited = {start}\n"
                                "    q = deque([(start, 0)])\n    while q:\n        node, dist = q.popleft()\n"
                                "        for nxt in get_neighbors(node):\n            if nxt in visited:\n"
                                "                continue\n            if nxt == goal:\n                return dist + 1\n"
                                "            visited.add(nxt)\n            q.append((nxt, dist + 1))\n    return -1\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 19})
        code.move_to([-2.4, 0.3, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        rules = VGroup()

        def rule(lines, key, txt, col, k):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.04, stroke_width=2)
            tag = VGroup(T(txt[0], 24, col), T(txt[1], 20, C_GREY)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
            tag.move_to([4.2, 1.6 - 1.25 * k, 0])
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.7)
            rules.add(hl, tag)
        rule([5, 7], "第一", ("① 用 deque，不用 list", "list.pop(0) 是 O(n)"), C_BLUE, 0)
        rule([13], "第二", ("② 入队时就标记", "不是出队时"), C_YELLOW, 1)
        rule([14], "第三", ("③ 步数跟着节点走", "(nxt, dist + 1) 一起入队"), C_GREEN, 2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, rules)), run_time=0.6)

    # ---------------------------------------------------------------- 迷宫：队列推进
    def maze_beat(self):
        self.beat("maze")
        walls = {(i, j) for i, row in enumerate(B.MAZE) for j, ch in enumerate(row) if ch == "#"}
        cell = 0.88
        sq = make_grid(5, 5, cell, (-3.4, 0.35, 0), walls)
        grid = VGroup(*sq.values())
        hash_marks = VGroup(*[MathTex(r"\#", color=C_GREY).scale(0.6).move_to(sq[w]) for w in walls])
        sl = T("起", 22, C_GREEN).next_to(sq[B.START], LEFT, buff=0.15)
        gl = T("终", 22, C_RED).next_to(sq[B.GOAL], RIGHT, buff=0.15)
        self.play(FadeIn(grid), FadeIn(hash_marks), FadeIn(sl), FadeIn(gl), run_time=1.0)
        negs = {c: MathTex("-1", color=C_GREY).scale(0.45).move_to(s) for c, s in sq.items() if c not in walls}
        self.wait_until(self.cue_start("dist 数组", self.now))
        self.play(LaggedStart(*[FadeIn(x) for x in negs.values()], lag_ratio=0.03), run_time=1.0)
        qhead = VGroup(T("队列", 24, C_GREY), Text("deque", font=MONO, font_size=22, color=C_GREY)).arrange(RIGHT, buff=0.2)
        qhead.move_to([2.6, 2.75, 0])
        out_lab = T("← 队首出队", 20, C_GREY).move_to([1.0, 0.95, 0])
        in_lab = T("队尾入队 ←", 20, C_GREY).move_to([5.6, 0.95, 0])
        self.play(FadeIn(qhead), FadeIn(out_lab), FadeIn(in_lab), run_time=0.5)
        self.wait_until(self.cue_start("队首的格子", self.now) - 0.3)
        ans, ev, dist = B.maze_trace()
        dmax = ans
        chips, nums = [], {}
        slot = lambda k: np.array([0.95 + 1.12 * k, 1.75, 0])  # noqa: E731
        ring = Square(cell * 0.98, stroke_color=WHITE, stroke_width=5).move_to(sq[B.START])
        n_pop = sum(1 for e in ev if e[0] == "pop")
        step = max(0.32, min(0.75, (self.left() - 1.0) / n_pop))
        k = 0
        while k < len(ev):
            e = ev[k]
            if e[0] == "push" and not chips:                     # 起点入队
                c, d = e[1], e[2]
                chip = self._chip(c).move_to(slot(0))
                chips.append(chip)
                num = MathTex(str(d), color=WHITE).scale(0.6).move_to(sq[c])
                nums[c] = num
                self.play(ReplacementTransform(negs.pop(c), num), sq[c].animate.set_fill(layer_color(d, dmax), 0.7),
                          FadeIn(chip, shift=LEFT * 0.3), Create(ring), run_time=step)
                k += 1
                continue
            # 一次出队 + 紧随其后的若干次入队，合成一拍
            c = e[1]
            pushes = []
            k += 1
            while k < len(ev) and ev[k][0] == "push":
                pushes.append(ev[k])
                k += 1
            head = chips.pop(0)
            anims = [ring.animate.move_to(sq[c]), FadeOut(head, shift=UP * 0.5)]
            anims += [ch.animate.move_to(slot(i)) for i, ch in enumerate(chips)]
            for _, nc, d in pushes:
                chip = self._chip(nc).move_to(slot(len(chips)))
                chips.append(chip)
                num = MathTex(str(d), color=WHITE).scale(0.6).move_to(sq[nc])
                nums[nc] = num
                anims += [ReplacementTransform(negs.pop(nc), num),
                          sq[nc].animate.set_fill(layer_color(d, dmax), 0.7), FadeIn(chip, shift=LEFT * 0.3)]
            self.play(*anims, run_time=step)
        self.wait(max(0.1, self.left() - 0.2))
        self.maze = dict(sq=sq, grid=grid, hash=hash_marks, sl=sl, gl=gl, nums=nums, ring=ring, dist=dist,
                         chips=chips, q=VGroup(qhead, out_lab, in_lab), negs=negs, ans=ans)

    def _chip(self, c):
        box = RoundedRectangle(corner_radius=0.1, width=1.0, height=0.5, stroke_color=C_BLUE, stroke_width=2)
        return VGroup(box, Text(f"({c[0]},{c[1]})", font=MONO, font_size=18).move_to(box))

    # ---------------------------------------------------------------- 最短路回溯
    def path_beat(self):
        self.beat("path")
        M = self.maze
        sq, dist = M["sq"], M["dist"]
        self.play(Flash(sq[B.GOAL], color=C_YELLOW, flash_radius=0.6), Indicate(M["nums"][B.GOAL], color=C_YELLOW,
                                                                              scale_factor=1.8), run_time=1.0)
        eight = VGroup(T("最短步数", 28), MathTex(str(M["ans"]), color=C_YELLOW).scale(1.4)).arrange(RIGHT, buff=0.3)
        eight.move_to([3.4, -0.6, 0])
        self.play(FadeIn(eight, shift=UP * 0.2), FadeOut(VGroup(*M["chips"])), run_time=0.8)
        self.wait_until(self.cue_start("倒着走", self.now))
        path = B.back_path(dist)
        line = VMobject(stroke_color=C_YELLOW, stroke_width=7).set_points_as_corners([sq[c].get_center() for c in path])
        rev = line.copy().reverse_points()
        self.play(Create(rev), *[sq[c].animate.set_stroke(C_YELLOW, 3) for c in path], run_time=2.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(M["grid"], M["hash"], M["sl"], M["gl"], *M["nums"].values(), M["ring"], M["q"],
                                 *M["negs"].values(), eight, rev)), run_time=0.6)

    # ---------------------------------------------------------------- 入队时就标记
    def mark_beat(self):
        self.beat("mark")
        pos = {"s": (-5.2, 0.8), "a": (-3.6, 1.8), "b": (-3.6, -0.2), "c": (-2.0, 0.8)}
        vs = {k: VGroup(Circle(0.34, stroke_color=WHITE, stroke_width=3), MathTex(k).scale(0.85)).move_to([*p, 0])
              for k, p in pos.items()}
        es = VGroup(*[Arrow(vs[u].get_center(), vs[v].get_center(), buff=0.38, stroke_width=3, color=C_GREY,
                            tip_length=0.18) for u, vlist in B.MARK_GRAPH.items() for v in vlist])
        self.play(FadeIn(es), *[FadeIn(v) for v in vs.values()], run_time=0.9)

        def strip(log, y, col, title, bad):
            head = T(title, 24, col).move_to([2.6, y + 0.65, 0])
            chips = VGroup()
            for i, k in enumerate(log):
                box = RoundedRectangle(corner_radius=0.1, width=0.7, height=0.55,
                                       stroke_color=C_RED if (bad and k == "c") else C_GREY, stroke_width=2.5)
                chips.add(VGroup(box, MathTex(k).scale(0.75).move_to(box)).move_to([0.6 + 0.85 * i, y, 0]))
            return head, chips
        good_h, good = strip(B.enqueue_log(True), 1.2, C_GREEN, "入队时标记：每个点只进一次", False)
        bad_h, bad = strip(B.enqueue_log(False), -1.2, C_RED, "出队时才标记：c 进了两次", True)
        self.play(FadeIn(good_h), LaggedStart(*[FadeIn(c, shift=LEFT * 0.2) for c in good], lag_ratio=0.25),
                  run_time=1.6)
        self.wait_until(self.cue_start("等到出队", self.now))
        self.play(FadeIn(bad_h), LaggedStart(*[FadeIn(c, shift=LEFT * 0.2) for c in bad], lag_ratio=0.3),
                  run_time=2.0)
        twice = [c for c, k in zip(bad, B.enqueue_log(False)) if k == "c"]
        self.play(*[Indicate(c, color=C_RED, scale_factor=1.3) for c in twice], Indicate(vs["c"], color=C_RED),
                  run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(es, *vs.values(), good_h, good, bad_h, bad)), run_time=0.6)

    # ---------------------------------------------------------------- 多源 BFS
    def multi_beat(self):
        self.beat("multi")
        n, m = B.MULTI_SHAPE
        mat = B.multi_grid()
        dist = B.update_matrix(mat)
        cell = 0.62
        sq = make_grid(n, m, cell, (0, 0.35, 0))
        grid = VGroup(*sq.values())
        self.play(FadeIn(grid), run_time=0.7)
        self.wait_until(self.cue_start("所有的零", self.now))
        zeros = VGroup()
        for k, (i, j) in enumerate(B.MULTI_SOURCES):
            zeros.add(MathTex("0", color=WHITE).scale(0.6).move_to(sq[(i, j)]))
        self.play(*[sq[s].animate.set_fill(SRC_COL[k], 0.85) for k, s in enumerate(B.MULTI_SOURCES)],
                  LaggedStart(*[FadeIn(z, scale=1.6) for z in zeros], lag_ratio=0.2), run_time=1.0)
        dmax = max(max(r) for r in dist)
        nums = VGroup()
        step = max(0.35, min(0.8, (self.left() - 1.2) / dmax))
        for d in range(1, dmax + 1):
            anims = []
            for (i, j), s in sq.items():
                if dist[i][j] == d:
                    col = SRC_COL[B.nearest_source(i, j)]
                    num = MathTex(str(d), color=WHITE).scale(0.5).move_to(s)
                    nums.add(num)
                    anims += [s.animate.set_fill(col, max(0.12, 0.7 - 0.09 * d)), FadeIn(num, scale=1.4)]
            self.play(*anims, run_time=step)
        once = T("一次搜索，全部答案", 28, C_YELLOW).move_to([0, -2.55, 0])
        self.play(FadeIn(once, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(grid, zeros, nums, once)), run_time=0.6)

    # ---------------------------------------------------------------- DFS 还是 BFS
    def choose_beat(self):
        self.beat("choose")
        n = B.OPEN_N
        cell = 0.55
        left = make_grid(n, n, cell, (-3.4, 0.55, 0))
        right = make_grid(n, n, cell, (3.4, 0.55, 0))
        lt = T("DFS：一条路走到底", 26, C_RED).next_to(VGroup(*left.values()), UP, buff=0.25)
        rt = T("BFS：一圈一圈往外推", 26, C_BLUE).next_to(VGroup(*right.values()), UP, buff=0.25)
        self.play(FadeIn(VGroup(*left.values(), *right.values())), FadeIn(lt), FadeIn(rt), run_time=0.8)
        do, bo = B.dfs_order(), B.bfs_order()
        N = len(do)
        dline = VMobject(stroke_color=C_RED, stroke_width=3).set_points_as_corners([left[c].get_center() for c in do])
        rt_total = max(3.0, min(7.0, self.cue_start("要最短步数", self.now + 6) - self.now))
        self.play(LaggedStart(*[left[c].animate.set_fill(
                      interpolate_color(ManimColor(C_RED), ManimColor(C_YELLOW), k / N), 0.7) for k, c in enumerate(do)],
                      lag_ratio=0.12),
                  Create(dline, rate_func=linear),
                  LaggedStart(*[right[c].animate.set_fill(
                      interpolate_color(ManimColor(C_BLUE), ManimColor(C_YELLOW), k / N), 0.7) for k, c in enumerate(bo)],
                      lag_ratio=0.12), run_time=rt_total)
        rows = VGroup(VGroup(T("要最短", 30, C_BLUE), T("→ 广搜 BFS", 30)).arrange(RIGHT, buff=0.3),
                      VGroup(T("要所有", 30, C_RED), T("→ 深搜 DFS（回溯）", 30)).arrange(RIGHT, buff=0.3))
        rows.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([0, -2.45, 0])
        self.wait_until(self.cue_start("一句话", self.now))
        self.play(FadeIn(rows, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*left.values(), *right.values(), lt, rt, dline, rows)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        items = VGroup(Text("deque", font=MONO, font_size=34, color=C_BLUE), T("+", 34),
                       Text("visited", font=MONO, font_size=34, color=C_YELLOW), T("=", 34),
                       T("一圈一圈往外推", 34)).arrange(RIGHT, buff=0.3).move_to([0, 1.0, 0])
        self.play(LaggedStart(*[FadeIn(x, shift=UP * 0.2) for x in items], lag_ratio=0.25), run_time=1.6)
        self.wait_until(self.cue_start("第一次到达", self.now))
        key = T("第一次到达，就是最短", 40, C_YELLOW).move_to([0, -0.3, 0])
        self.play(Write(key), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 12 周 BFS P9–P21 · LeetCode 542", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
