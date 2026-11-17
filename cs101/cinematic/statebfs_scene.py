"""状态不只是坐标：带状态 BFS 与多源 BFS（3B1B 风格）。bfs 片之后，讲 visited 该记什么。

由 make.py 驱动，时间轴约定见 cine.py。网格、步数、反例、分层图上每个状态的步数、best 剪枝事件、超级源点分层、
水淹七军的淹没事件全部来自 statebfsdata（讲义 naruto / update_matrix / flood_army 原样；test_statebfs.py 对撞
状态图上反复松弛的真最短、逐源灌水与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statebfsdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_BURN, C_LOW, C_COORD, C_BEST = C_PURPLE, C_GREEN, C_BLUE, C_YELLOW
WATER = "#3A7BD5"


def mono(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def mix(col, a):
    """不透明的浅色底：BG 与 col 按 a 混合。"""
    return interpolate_color(ManimColor(BG), ManimColor(col), a)


class Board:
    """平面网格：box[(i, j)] 方框，lab[(i, j)] 字（鸣 / 佐 / #）。字下垫一块不透明小底，路径线从字底下穿过。"""

    def __init__(self, grid, center, pitch=1.0, size=0.86, glyph=34):
        self.grid, self.pitch = grid, pitch
        n, m = len(grid), len(grid[0])
        c = np.array([*center[:2], 0], dtype=float)
        self.pos = {(i, j): c + np.array([(j - (m - 1) / 2) * pitch, ((n - 1) / 2 - i) * pitch, 0])
                    for i in range(n) for j in range(m)}
        self.box, self.lab, self.pad = {}, {}, {}
        for (i, j), p in self.pos.items():
            ch = grid[i][j]
            box = Square(size, stroke_color=C_RED if ch == '#' else C_GREY, stroke_width=2.5).move_to(p)
            box.set_fill(mix(C_RED, 0.18) if ch == '#' else BG, 1).set_z_index(0)
            self.box[(i, j)] = box
            if ch in "#@+":
                lab = (mono("#", glyph, C_RED) if ch == '#' else T("鸣" if ch == '@' else "佐", glyph, C_TEAL))
                lab.move_to(p).set_z_index(3)
                self.lab[(i, j)] = lab
                pad = Square(size * 0.5, stroke_width=0).set_fill(self.base(i, j), 1).move_to(p).set_z_index(2)
                self.pad[(i, j)] = pad
        self.group = VGroup(*self.box.values(), *self.pad.values(), *self.lab.values())

    def all(self):
        return self.group

    def base(self, i, j):
        return mix(C_RED, 0.18) if self.grid[i][j] == '#' else BG

    def _paint(self, cells, colf):
        out = []
        for c in cells:
            col = colf(c)
            out.append(self.box[c].animate.set_fill(col, 1))
            if c in self.pad:
                out.append(self.pad[c].animate.set_fill(col, 1))
        return out

    def fill(self, cells, col, a=0.35):
        return self._paint(cells, lambda c: mix(col, a + (0.1 if self.grid[c[0]][c[1]] == '#' else 0)))

    def reset(self, cells):
        return self._paint(cells, lambda c: self.base(*c))

    def line(self, cells, col, width=7):
        return VMobject(stroke_color=col, stroke_width=width).set_points_as_corners(
            [self.pos[c] for c in cells]).set_z_index(1)


class Layers:
    """把「网格 × 剩余查克拉」画成叠起来的几层斜放的网格。layer t 越大越靠上。"""

    def __init__(self, grid, T, x0=-2.2, ys=None, cw=1.05, rh=0.5, sk=0.45):
        self.grid, self.T = grid, T
        self.n, self.m = len(grid), len(grid[0])
        self.x0, self.cw, self.rh, self.sk = x0, cw, rh, sk
        self.ys = ys or {1: 1.45, 0: -1.25}
        self.poly, self.layer = {}, {}
        for t in range(T + 1):
            g = VGroup()
            for i in range(self.n):
                for j in range(self.m):
                    pts = [self.pt(i + di, j + dj, t) for di, dj in ((-.5, -.5), (-.5, .5), (.5, .5), (.5, -.5))]
                    ch = grid[i][j]
                    p = Polygon(*pts, stroke_color=C_RED if ch == '#' else C_GREY, stroke_width=2)
                    p.set_fill(mix(C_RED, 0.2) if ch == '#' else BG, 1)
                    self.poly[(i, j, t)] = p
                    g.add(p)
            self.layer[t] = g

    def pt(self, i, j, t):
        """网格坐标（可带 0.5 的半格）→ 屏幕点。第 0 行在后（屏幕上方），越往后越向右错开。"""
        v = (self.n - 1) / 2 - i
        return np.array([self.x0 + (j - (self.m - 1) / 2) * self.cw + v * self.sk, self.ys[t] + v * self.rh, 0])

    def center(self, s):
        return self.pt(*s)


class StateBFSLesson(Lesson):
    def construct(self):
        for b in ("title", "problem", "naive", "wrong", "layers", "code", "multi", "flood", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def fade_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs and m is not self.camera.frame]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)
            self.remove(*rest)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("状态不只是坐标", 54).move_to([0, 2.6, 0])
        sub = T("带状态 BFS 与多源 BFS", 32, C_YELLOW).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        box = Square(1.3, stroke_color=C_GREY, stroke_width=3).move_to([0, -0.6, 0])
        xy = mono("(1, 2)", 30).next_to(box, DOWN, buff=0.3)
        self.play(Create(box), FadeIn(xy), run_time=0.8)
        self.wait_until(self.cue_start("本钱", self.now))
        left = VGroup(Square(1.3, stroke_color=C_BURN, stroke_width=3).set_fill(mix(C_BURN, 0.3), 1),
                      mono("(1, 2, 剩 0)", 26, C_BURN))
        right = VGroup(Square(1.3, stroke_color=C_LOW, stroke_width=3).set_fill(mix(C_LOW, 0.3), 1),
                       mono("(1, 2, 剩 1)", 26, C_LOW))
        for g, x in ((left, -2.6), (right, 2.6)):
            g[0].move_to([x, -0.6, 0])
            g[1].next_to(g[0], DOWN, buff=0.3)
        self.play(ReplacementTransform(box.copy(), left[0]), ReplacementTransform(box.copy(), right[0]),
                  FadeIn(left[1]), FadeIn(right[1]), FadeOut(xy), box.animate.set_stroke(opacity=0.3), run_time=1.2)
        self.wait_until(self.cue_start("不只是坐标", self.now))
        neq = MathTex(r"\neq", color=C_YELLOW).scale(1.6).move_to([0, -0.6, 0])
        self.play(FadeOut(box), FadeIn(neq, scale=1.4), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 题目与讲义样例
    def problem_beat(self):
        self.beat("problem")
        head = VGroup(T("鸣人和佐助", 40), mono("OpenJudge 04115", 24, C_GREY)).arrange(RIGHT, buff=0.4)
        head.move_to([0, 3.15, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.7)
        g = D.G_COURSE
        L = Board(g, [-3.4, 0.35], 1.1, 0.94, 32)
        R = Board(g, [3.4, 0.35], 1.1, 0.94, 32)
        self.wait_until(self.cue_start("井号", self.now))
        self.play(FadeIn(L.all()), FadeIn(R.all()), run_time=0.8)
        legend = VGroup(VGroup(mono("#", 28, C_RED), T("大蛇丸的手下：打掉花 1 点查克拉", 24, C_GREY)).arrange(RIGHT, buff=0.15),
                        VGroup(T("鸣", 28, C_TEAL), T("起点", 24, C_GREY), T("佐", 28, C_TEAL), T("终点", 24, C_GREY))
                        .arrange(RIGHT, buff=0.15)).arrange(RIGHT, buff=0.8).move_to([0, 2.3, 0])
        self.play(FadeIn(legend), run_time=0.6)
        res = {}
        for B, T_, key, col in ((L, 2, "两点查克拉", C_YELLOW), (R, 0, "一点没有", C_BLUE)):
            self.wait_until(self.cue_start(key, self.now))
            path = D.state_path(g, T_)
            cells = [s[:2] for s in path]
            cap = VGroup(T("查克拉", 26, C_GREY), mono(str(T_), 30, col)).arrange(RIGHT, buff=0.15)
            cap.next_to(VGroup(*B.box.values()), DOWN, buff=0.3)
            ans = VGroup(mono(str(D.naruto(g, T_)), 40, col), T("步", 28, col)).arrange(RIGHT, buff=0.12)
            ans.next_to(cap, DOWN, buff=0.25)
            line = B.line(cells, col)
            self.play(FadeIn(cap), run_time=0.4)
            self.play(Create(line), *B.fill(cells[1:-1], col), run_time=1.6)
            self.play(FadeIn(ans, scale=1.3), run_time=0.5)
            res[T_] = VGroup(cap, ans, line)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 只按坐标记：样例都过
    def naive_beat(self):
        self.beat("naive")
        src = ("visited = {(sx, sy)}          # 只记坐标\n"
               "...\n"
               "    if (nx, ny) in visited:\n"
               "        continue\n"
               "    visited.add((nx, ny))\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 24})
        code.move_to([-2.3, 1.5, 0])
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("样例", self.now))
        g = D.G_COURSE
        rows = VGroup()
        for T_ in (2, 0):
            got = D.naruto_coord(g, T_)[0]
            r = VGroup(T(f"样例：查克拉 {T_}", 26, C_GREY), mono(str(got), 32, C_GREEN), T("✓", 30, C_GREEN))
            rows.add(r.arrange(RIGHT, buff=0.25))
        rows.arrange(DOWN, buff=0.3, aligned_edge=LEFT).next_to(code, RIGHT, buff=0.7)
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rows], lag_ratio=0.4), run_time=1.0)
        self.wait_until(self.cue_start("交上去会错", self.now))
        wa = T("交上去：答案错误", 30, C_RED).next_to(rows, DOWN, buff=0.35).align_to(rows, LEFT)
        self.play(FadeIn(wa, shift=UP * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("看这个反例", self.now))
        B = Board(D.G_TRAP, [-3.2, -1.15], 0.82, 0.7, 28)
        cap = VGroup(T("反例：三行五列，查克拉", 26, C_GREY), mono(str(D.T_TRAP), 30, C_YELLOW)).arrange(RIGHT, buff=0.15)
        cap.next_to(VGroup(*B.box.values()), RIGHT, buff=0.6)
        self.play(FadeIn(B.all(), shift=UP * 0.2), FadeIn(cap), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, rows, wa, cap, B.all())), run_time=0.6)

    # ---------------------------------------------------------------- 反例逐步看
    def wrong_beat(self):
        self.beat("wrong")
        g, T_ = D.G_TRAP, D.T_TRAP
        B = Board(g, [-3.5, -0.15], 1.3, 1.1, 38)
        cap = VGroup(T("只按坐标记 visited", 26, C_GREY), T("查克拉", 24, C_GREY), mono(str(T_), 28, C_YELLOW))
        cap.arrange(RIGHT, buff=0.15).next_to(VGroup(*B.box.values()), UP, buff=0.3)
        self.play(FadeIn(B.all()), FadeIn(cap), run_time=0.7)
        wrong, seen = D.naruto_coord(g, T_)
        mid = (0, 2)
        _, sdist, _ = D.naruto_states(g, T_)
        top = [(0, 0), (0, 1), mid]
        low = [(0, 0), (1, 0), (1, 1), (1, 2), mid]
        px = 0.35
        panel = VGroup()
        self.wait_until(self.cue_start("上面这条路", self.now))
        l1 = B.line(top, C_BURN)
        self.play(Create(l1), *B.fill(top[1:], C_BURN), run_time=1.2)
        ring = SurroundingRectangle(B.box[mid], color=C_YELLOW, buff=0.06, stroke_width=4)
        r1 = VGroup(T("上路", 28, C_BURN), T(f"第 {seen[mid][0]} 步到，剩", 28), mono(str(seen[mid][1]), 32, C_BURN),
                    T("先占", 28, C_BURN))
        r1.arrange(RIGHT, buff=0.15).move_to([px, 2.4, 0], aligned_edge=LEFT)
        mh = T("中间这一格", 28, C_YELLOW).move_to([px, 3.15, 0], aligned_edge=LEFT)
        self.play(Create(ring), FadeIn(mh), FadeIn(r1, shift=LEFT * 0.2), run_time=0.8)
        panel.add(mh, r1)
        self.wait_until(self.cue_start("下面这条路", self.now))
        l2 = B.line(low, C_LOW)
        self.play(Create(l2), *B.fill(low[1:-1], C_LOW), run_time=1.6)
        r2 = VGroup(T("下路", 28, C_LOW), T(f"第 {sdist[(*mid, 1)]} 步到，剩", 28), mono("1", 32, C_LOW))
        r2.arrange(RIGHT, buff=0.15).next_to(r1, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(FadeIn(r2, shift=LEFT * 0.2), run_time=0.6)
        panel.add(r2)
        self.wait_until(self.cue_start("被占了", self.now))
        p = B.pos[(1, 2)] + UP * B.pitch / 2
        cross = VGroup(Line(p + LEFT * 0.18 + UP * 0.18, p + RIGHT * 0.18 + DOWN * 0.18),
                       Line(p + LEFT * 0.18 + DOWN * 0.18, p + RIGHT * 0.18 + UP * 0.18)).set_stroke(C_RED, 7)
        cross.set_z_index(4)
        blocked = T("挡在门外", 28, C_RED).next_to(r2, RIGHT, buff=0.3)
        self.play(Create(cross), l2.animate.set_stroke(opacity=0.35), FadeIn(blocked), run_time=0.9)
        panel.add(blocked)
        self.wait_until(self.cue_start("过不去", self.now))
        q = B.pos[(0, 3)]
        cross2 = VGroup(Line(q + LEFT * 0.25 + UP * 0.25, q + RIGHT * 0.25 + DOWN * 0.25),
                        Line(q + LEFT * 0.25 + DOWN * 0.25, q + RIGHT * 0.25 + UP * 0.25)).set_stroke(C_BURN, 7)
        cross2.set_z_index(4)
        r3 = VGroup(T("剩", 28), mono("0", 32, C_BURN), T("：打不动右边的手下", 28)).arrange(RIGHT, buff=0.12)
        r3.next_to(r2, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(Create(cross2), FadeIn(r3, shift=LEFT * 0.2), run_time=0.8)
        panel.add(r3)
        self.wait_until(self.cue_start("绕最下面一行", self.now))
        cp = D.naruto_coord_path(g, T_)
        l3 = B.line(cp, C_COORD, 6)
        self.play(FadeOut(l1), FadeOut(l2), FadeOut(cross), FadeOut(cross2), FadeOut(ring),
                  *B.reset(list(B.box)),
                  run_time=0.5)
        self.play(Create(l3), *B.fill(cp[1:-1], C_COORD, 0.3), run_time=1.6)
        a1 = VGroup(T("只按坐标", 32, C_COORD), mono(str(wrong), 46, C_COORD), T("步", 32, C_COORD)).arrange(RIGHT, buff=0.15)
        a1.move_to([px, -0.6, 0], aligned_edge=LEFT)
        self.play(FadeIn(a1, scale=1.2), run_time=0.6)
        self.wait_until(self.cue_start("正确答案", self.now))
        sp = [s[:2] for s in D.state_path(g, T_)]
        l4 = B.line(sp, C_BEST, 7)
        self.play(FadeOut(l3), *B.reset(cp[1:-1]), run_time=0.4)
        self.play(Create(l4), *B.fill(sp[1:-1], C_BEST, 0.3), run_time=1.4)
        a2 = VGroup(T("正确", 32, C_BEST), mono(str(D.naruto(g, T_)), 46, C_BEST), T("步", 32, C_BEST)).arrange(RIGHT, buff=0.15)
        a2.next_to(a1, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(FadeIn(a2, scale=1.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 分层图
    def layers_beat(self):
        self.beat("layers")
        g, T_ = D.G_TRAP, D.T_TRAP
        head = VGroup(T("状态 =", 32), mono("(行, 列, 剩余查克拉)", 30, C_YELLOW)).arrange(RIGHT, buff=0.2)
        head.move_to([0, 3.3, 0])
        flat = Board(g, [0, -0.3], 1.1, 0.94, 32)
        mid2 = (0, 2)
        ring = SurroundingRectangle(flat.box[mid2], color=C_YELLOW, buff=0.06, stroke_width=4)
        two = VGroup(VGroup(T("剩", 28, C_GREY), mono("1", 32, C_LOW)).arrange(RIGHT, buff=0.1),
                     VGroup(T("剩", 28, C_GREY), mono("0", 32, C_BURN)).arrange(RIGHT, buff=0.1))
        top = ring.get_top()
        two[0].move_to(top + np.array([-1.8, 1.25, 0]))
        two[1].move_to(top + np.array([1.8, 1.25, 0]))
        fork = VGroup(*[Arrow(top, r.get_bottom(), buff=0.1, color=C_YELLOW, stroke_width=4,
                              max_tip_length_to_length_ratio=0.2) for r in two])
        self.play(FadeIn(head, shift=DOWN * 0.2), FadeIn(flat.all()), run_time=0.8)
        self.play(Create(ring), run_time=0.5)
        self.wait_until(self.cue_start("两种处境", self.now))
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(r)) for a, r in zip(fork, two)], lag_ratio=0.4),
                  run_time=1.0)
        Ls = Layers(g, T_, x0=-1.9, ys={1: 1.35, 0: -1.4}, cw=1.25, rh=0.62, sk=0.55)
        tags = {t: VGroup(T("剩", 28, C_GREY), mono(str(t), 32, C_LOW if t else C_BURN)).arrange(RIGHT, buff=0.1)
                for t in (1, 0)}
        for t, tg in tags.items():
            tg.move_to([-6.35, Ls.ys[t], 0])
        glyphs = VGroup()
        for t in (1, 0):
            for (i, j), ch in ((ij, g[ij[0]][ij[1]]) for ij in ((i, j) for i in range(3) for j in range(5))):
                if ch == '@' and t == T_ or ch == '+':
                    glyphs.add(T("鸣" if ch == '@' else "佐", 22, C_TEAL).move_to(Ls.center((i, j, t)) + LEFT * 0.36))
        self.wait_until(self.cue_start("叠起来", self.now))
        self.play(FadeOut(VGroup(flat.all(), ring, fork)), *[ReplacementTransform(two[1 - t], tags[t]) for t in (1, 0)],
                  run_time=0.7)
        self.play(LaggedStart(*[FadeIn(Ls.layer[t], shift=DOWN * 0.3) for t in (1, 0)], lag_ratio=0.5),
                  FadeIn(glyphs), run_time=1.2)
        px = 2.6
        notes = VGroup()
        self.wait_until(self.cue_start("走空地", self.now))
        a_flat = Arrow(Ls.center((1, 0, 1)), Ls.center((1, 2, 1)), buff=0.2, color=C_LOW, stroke_width=6,
                       max_tip_length_to_length_ratio=0.15).set_z_index(4)
        n1 = VGroup(Line(ORIGIN, RIGHT * 0.6, color=C_LOW, stroke_width=6), T("走空地：留在本层", 26)).arrange(RIGHT, buff=0.2)
        n1.move_to([px, 1.5, 0], aligned_edge=LEFT)
        self.play(GrowArrow(a_flat), FadeIn(n1), run_time=0.8)
        self.wait_until(self.cue_start("打一个手下", self.now))
        a_drop = CurvedArrow(Ls.center((0, 0, 1)) + RIGHT * 0.1, Ls.center((0, 1, 0)) + UP * 0.1, angle=-PI / 5,
                             color=C_BURN, stroke_width=6).set_z_index(4)
        n2 = VGroup(Line(ORIGIN, RIGHT * 0.6, color=C_BURN, stroke_width=6), T("打手下：掉到下一层", 26)).arrange(RIGHT, buff=0.2)
        n2.next_to(n1, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(Create(a_drop), FadeIn(n2), run_time=0.9)
        notes.add(n1, n2)
        _, dist, _ = D.naruto_states(g, T_)
        nums = {}
        for s, d in dist.items():
            nums[s] = mono(str(d), 26, WHITE).move_to(Ls.center(s) + RIGHT * 0.05).set_z_index(3)
        self.wait_until(self.cue_start("中间这一格", self.now))
        mid = [(0, 2, 0), (0, 2, 1)]
        self.play(*[Ls.poly[s].animate.set_stroke(C_YELLOW, 4) for s in mid], FadeOut(a_flat), FadeOut(a_drop),
                  run_time=0.6)
        self.wait_until(self.cue_start("下层第二步", self.now))
        self.play(FadeIn(nums[mid[0]], scale=1.5), run_time=0.5)
        self.wait_until(self.cue_start("上层第四步", self.now))
        self.play(FadeIn(nums[mid[1]], scale=1.5), run_time=0.5)
        n3 = T("同一格，两个不同的点", 26, C_YELLOW).next_to(n2, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(FadeIn(n3), run_time=0.5)
        notes.add(n3)
        self.wait_until(self.cue_start("普通广搜", self.now))
        t_end = self.cue_start("第六步", self.now + 3)
        rest = [s for s in dist if s not in mid]
        maxd = max(dist.values())
        for d in range(maxd + 1):
            batch = [nums[s] for s in rest if dist[s] == d]
            if batch:
                rt_ = max(0.25, min(0.5, (t_end - self.now) / (maxd + 1 - d)))
                self.play(*[FadeIn(x, scale=1.3) for x in batch], run_time=rt_)
        self.wait_until(self.cue_start("第六步", self.now))
        sp = D.state_path(g, T_)
        goal = sp[-1]
        self.play(*[Ls.poly[s].animate.set_fill(mix(C_BEST, 0.35), 1) for s in sp],
                  Ls.poly[goal].animate.set_stroke(C_BEST, 5), Indicate(nums[goal], color=C_BEST), run_time=1.0)
        drop = next((a, b) for a, b in zip(sp, sp[1:]) if b[2] < a[2])
        a_best = CurvedArrow(Ls.center(drop[0]) + RIGHT * 0.15, Ls.center(drop[1]) + UP * 0.12, angle=-PI / 5,
                             color=C_BEST, stroke_width=6).set_z_index(4)
        self.play(Create(a_best), run_time=0.7)
        self.wait_until(self.cue_start("状态数", self.now))
        n, m = len(g), len(g[0])
        cnt = MathTex(rf"{n}\times{m}\times({T_}+1)", "=", str(D.n_states(g, T_)), color=WHITE).scale(0.9)
        cnt[2].set_color(C_YELLOW)
        lab = T("状态数", 26, C_GREY)
        box = VGroup(lab, cnt).arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([px, -1.5, 0], aligned_edge=LEFT)
        self.play(FadeIn(lab), Write(cnt), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 讲义代码：best 剪枝
    def code_beat(self):
        self.beat("code")
        src = ("best = [[-1] * m for _ in range(n)]\n"
               "best[sx][sy] = T\n"
               "q = deque([(sx, sy, T, 0)])\n"
               "while q:\n"
               "    x, y, t, step = q.popleft()\n"
               "    ...\n"
               "    for dx, dy in DIRS:\n"
               "        ...\n"
               "        nt = t - 1 if grid[nx][ny] == '#' else t\n"
               "        if nt < 0:\n"
               "            continue\n"
               "        if nt <= best[nx][ny]:    # 剪枝\n"
               "            continue\n"
               "        best[nx][ny] = nt\n"
               "        q.append((nx, ny, nt, step + 1))\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 22})
        code.move_to([-3.0, 0.3, 0])
        if code.height > 6.3:
            code.scale_to_fit_height(6.3).move_to([-3.0, 0.3, 0])
        if code.get_left()[0] < -6.9:
            code.shift(RIGHT * (-6.9 - code.get_left()[0]))
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.8)
        ln = code.code_lines
        px = code.get_right()[0] + 0.4
        hls = VGroup()

        def mark(lines, col):
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.08, 0.02), stroke_width=2.5)
            hls.add(hl)
            return hl
        self.wait_until(self.cue_start("best 记的是", self.now))
        h0 = mark([0, 1], C_YELLOW)
        d1 = VGroup(mono("best[x][y]", 26, C_YELLOW), T("到达这一格时", 24), T("最多还剩多少查克拉", 24))
        d1.arrange(DOWN, buff=0.15, aligned_edge=LEFT).move_to([px, 2.4, 0], aligned_edge=LEFT)
        self.play(Create(h0), FadeIn(d1, shift=LEFT * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("剩得更多", self.now))
        h1 = mark([13, 14], C_GREEN)
        d2 = T("剩得更多：放行", 26, C_GREEN).next_to(d1, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(Create(h1), FadeIn(d2), run_time=0.7)
        self.wait_until(self.cue_start("就剪掉", self.now))
        h2 = mark([11, 12], C_RED)
        d3 = T("不比记录多：剪掉", 26, C_RED).next_to(d2, DOWN, buff=0.25, aligned_edge=LEFT)
        self.play(Create(h2), FadeIn(d3), run_time=0.7)
        self.wait_until(self.cue_start("按步数出队", self.now))
        d4 = VGroup(T("后到的：步数不更少", 24, C_GREY), T("查克拉也不更多 → 没用", 24, C_GREY))
        d4.arrange(DOWN, buff=0.12, aligned_edge=LEFT).next_to(d3, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(FadeIn(d4, shift=UP * 0.15), run_time=0.8)
        self.wait_until(self.cue_start("中间那一格", self.now))
        _, _, ev = D.naruto_best_trace(D.G_TRAP, D.T_TRAP)
        pushes = [e for e in ev if e[0] == "push" and e[1] == (0, 2)]
        cell = Square(0.9, stroke_color=C_YELLOW, stroke_width=4)
        cl = T("中间格", 22, C_YELLOW).next_to(cell, UP, buff=0.12)
        rows = VGroup()
        for _, _, nt, step in pushes:
            rows.add(VGroup(T(f"第 {step} 步", 24), mono(f"nt = {nt}", 24, C_LOW if nt else C_BURN)).arrange(RIGHT, buff=0.25))
        rows.arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        grp = VGroup(VGroup(cl, cell), rows).arrange(RIGHT, buff=0.4).move_to([px, -2.05, 0], aligned_edge=LEFT)
        val = mono("-1", 30, C_GREY).move_to(cell)
        self.play(FadeIn(cell), FadeIn(cl), FadeIn(val), run_time=0.5)
        prev = val
        cue2 = self.cue_start("第四步", self.now + 2)
        for k, (_, _, nt, step) in enumerate(pushes):
            if k:
                self.wait_until(cue2)
            nv = mono(str(nt), 30, C_LOW if nt else C_BURN).move_to(cell)
            self.play(FadeIn(rows[k], shift=LEFT * 0.15), FadeOut(prev), FadeIn(nv, scale=1.3), run_time=0.6)
            prev = nv
        self.wait_until(self.cue_start("比零多", self.now))
        ok = T("1 > 0 放行", 24, C_GREEN).next_to(rows[1], RIGHT, buff=0.25)
        if ok.get_right()[0] > 6.9:
            ok.next_to(rows[1], DOWN, buff=0.15, aligned_edge=LEFT)
        self.play(FadeIn(ok), Indicate(h1, color=C_GREEN), run_time=0.7)
        self.wait_until(self.cue_start("少了一维", self.now))
        dim = VGroup(mono("visited[x][y][t]", 24, C_GREY), MathTex(r"\to", color=C_GREY).scale(0.8),
                     mono("best[x][y]", 24, C_YELLOW)).arrange(RIGHT, buff=0.2)
        if dim.width > 6.9 - d4.get_left()[0]:
            dim.scale_to_fit_width(6.9 - d4.get_left()[0])
        dim.move_to(d4, aligned_edge=LEFT)
        self.play(FadeOut(d4), FadeIn(dim, shift=UP * 0.15), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 多源 = 超级源点
    def multi_beat(self):
        self.beat("multi")
        mat = D.MS_GRID
        n, m = len(mat), len(mat[0])
        B = Board(["." * m] * n, [-3.0, -0.75], 0.9, 0.78)
        srcs = [(i, j) for i in range(n) for j in range(m) if mat[i][j] == 0]
        zero = {c: mono("0", 26, C_TEAL).move_to(B.pos[c]).set_z_index(3) for c in srcs}
        head = T("多源广搜：所有源点一起入队", 30).move_to([0, 3.3, 0])
        self.play(FadeIn(head), FadeIn(B.all()), *[FadeIn(z) for z in zero.values()],
                  *[B.box[c].animate.set_stroke(C_TEAL, 3.5) for c in srcs], run_time=0.9)
        self.wait_until(self.cue_start("超级源点", self.now))
        S = VGroup(Circle(0.36, stroke_color=C_YELLOW, stroke_width=4).set_fill(BG, 1), mono("S", 30, C_YELLOW))
        S.move_to([-3.0, 2.25, 0]).set_z_index(5)
        sl = T("超级源点", 24, C_YELLOW).next_to(S, RIGHT, buff=0.2)
        sl2 = T("连向全部源点", 24, C_YELLOW).next_to(S, RIGHT, buff=0.2)
        edges = VGroup(*[Line(S.get_center(), B.pos[c], buff=0.4, color=C_YELLOW, stroke_width=3.5)
                         .set_z_index(1) for c in srcs])
        self.play(FadeIn(S), FadeIn(sl), run_time=0.5)
        self.wait_until(self.cue_start("连一条边", self.now))
        self.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.3), run_time=1.0)
        sd, layers = D.super_source_bfs(mat)
        px = 1.5
        self.wait_until(self.cue_start("第一层", self.now))
        rows = VGroup()
        nums = {}
        t_end = self.cue_start("整体多一", self.now + 4)
        top = max(layers)
        for d in range(1, top + 1):
            cells = layers[d]
            r = VGroup(T(f"第 {d} 层", 24, C_YELLOW if d == 1 else WHITE),
                       T("全部源点" if d == 1 else f"{len(cells)} 格", 24, C_TEAL if d == 1 else C_GREY))
            r.arrange(RIGHT, buff=0.3).move_to([px, 2.0 - 0.55 * (d - 1), 0], aligned_edge=LEFT)
            rows.add(r)
            anims = [FadeIn(r, shift=LEFT * 0.15)]
            for c in cells:
                nums[c] = mono(str(sd[c[0]][c[1]]), 26, C_YELLOW if d == 1 else WHITE).move_to(B.pos[c]).set_z_index(3)
                anims.append(FadeIn(nums[c], scale=1.3))
                if d == 1:
                    anims.append(FadeOut(zero[c]))
                else:
                    anims.append(B.box[c].animate.set_fill(mix(C_BLUE, 0.08 + 0.07 * d), 1))
            if d == 2:                                   # 连线会压住数字：第二层出现时撤掉，S 旁注明连向全部源点
                anims += [FadeOut(edges), FadeOut(sl), FadeIn(sl2)]
            rt_ = max(0.45, min(1.0, (t_end - self.now) / (top + 1 - d)))
            self.play(*anims, run_time=rt_)
        self.wait_until(self.cue_start("整体多一", self.now))
        md = D.update_matrix(mat)
        minus = MathTex(r"-1", color=C_TEAL).scale(1.0).next_to(rows, DOWN, buff=0.35).align_to(rows, LEFT)
        eq = T("= 多源广搜的 dist", 26, C_TEAL).next_to(minus, RIGHT, buff=0.25)
        new = {c: mono(str(md[c[0]][c[1]]), 26, C_TEAL if md[c[0]][c[1]] == 0 else WHITE).move_to(B.pos[c]).set_z_index(3)
               for c in nums}
        self.play(FadeIn(minus), FadeIn(eq), *[FadeOut(v) for v in nums.values()],
                  *[FadeIn(v) for v in new.values()], run_time=1.0)
        self.wait_until(self.cue_start("其实还是单源", self.now))
        tag = T("多源 = 加一个超级源点的单源", 28, C_YELLOW).move_to([px + 2.4, -2.45, 0])
        if tag.get_right()[0] > 6.9:
            tag.shift(LEFT * (tag.get_right()[0] - 6.9))
        self.play(FadeIn(tag, shift=UP * 0.15), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 水淹七军
    def flood_beat(self):
        self.beat("flood")
        H = D.FL_H
        n, m = len(H), len(H[0])
        head = VGroup(T("水淹七军", 40), mono("M12029", 24, C_GREY)).arrange(RIGHT, buff=0.4).move_to([0, 3.2, 0])
        B = Board(["." * m] * n, [0, 0.75], 1.4, 1.2)
        hnum = {c: mono(str(H[c[0]][c[1]]), 38, WHITE).move_to(B.pos[c]).set_z_index(3) for c in B.box}
        hq = D.FL_HQ
        hql = T("司令部", 24, C_YELLOW).next_to(B.box[hq], DOWN, buff=0.15)
        hint = VGroup(T("格子里：高度", 24, C_GREY), T("左上角：水位", 24, C_BLUE)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        hint.next_to(VGroup(*B.box.values()), LEFT, buff=0.35)
        self.play(FadeIn(head), FadeIn(B.all()), *[FadeIn(v) for v in hnum.values()], FadeIn(hint),
                  B.box[hq].animate.set_stroke(C_YELLOW, 4), FadeIn(hql), run_time=1.0)
        ok, water, ev = D.flood_trace(H, D.FL_SRC, hq)
        tags = {}

        def wet_anim(c, lv):
            a = 0.3 if lv < 6 else 0.6
            tg = mono(str(lv), 24, C_BLUE).move_to(B.box[c].get_corner(UL) + np.array([0.22, -0.22, 0])).set_z_index(4)
            anims = [B.box[c].animate.set_fill(mix(WATER, a), 1)]
            if c in tags:
                anims.append(FadeOut(tags[c]))
            anims.append(FadeIn(tg, scale=1.3))
            tags[c] = tg
            return anims
        self.wait_until(self.cue_start("两个放水点", self.now))
        src_lab = VGroup()
        anims = []
        for e in ev:
            if e[0] == "src":
                c = e[1]
                lb = T("放水", 22, C_BLUE).next_to(B.box[c], UP, buff=0.15)
                src_lab.add(lb)
                anims += [FadeIn(lb)] + wet_anim(c, e[2])
        self.play(*anims, run_time=0.8)
        wets = [e for e in ev if e[0] == "wet"]
        near = (hq[0] - 1, hq[1])
        k_low = next(k for k, e in enumerate(wets) if e[1] == near)          # 司令部旁边先被三淹到
        k_up = next(k for k, e in enumerate(wets) if e[1] == near and e[3] >= 0)   # 再被六抬高
        self.wait_until(self.cue_start("右边的水位", self.now))
        for e in wets[:k_low + 1]:
            self.play(*wet_anim(e[1], e[2]), run_time=0.55)
        self.wait_until(self.cue_start("淹不了", self.now))
        chk = VGroup(mono(f"{H[hq[0]][hq[1]]} < 3 ?", 28, C_RED), T("不成立", 26, C_RED)).arrange(RIGHT, buff=0.2)
        chk.next_to(hql, RIGHT, buff=0.5)
        self.play(FadeIn(chk, shift=LEFT * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("随后赶到", self.now))
        for e in wets[k_low + 1:k_up]:
            self.play(*wet_anim(e[1], e[2]), run_time=0.5)
        self.wait_until(self.cue_start("比三高", self.now))
        e = wets[k_up]
        self.play(*wet_anim(e[1], e[2]), Indicate(B.box[near], color=C_YELLOW), run_time=0.8)
        self.wait_until(self.cue_start("司令部被淹", self.now))
        chk2 = VGroup(mono(f"{H[hq[0]][hq[1]]} < 6", 28, C_GREEN), T("淹了", 26, C_GREEN)).arrange(RIGHT, buff=0.2)
        chk2.move_to(chk, aligned_edge=LEFT)
        rest = wets[k_up + 1:]
        anims = []
        for e in rest:
            anims += wet_anim(e[1], e[2])
        self.play(*anims, FadeOut(chk), FadeIn(chk2), run_time=1.0)
        self.wait_until(self.cue_start("一个道理", self.now))
        line = Code(code_string="if height[nx][ny] < level and water[nx][ny] < level:\n"
                                "    water[nx][ny] = level   # 水位更高才值得再扩展\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 24})
        line.move_to([0, -2.3, 0])
        if line.width > 13.0:
            line.scale_to_fit_width(13.0).move_to([0, -2.25, 0])
        self.play(FadeIn(line, shift=UP * 0.2), FadeOut(hint), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        q = T("状态 = 决定以后还能怎么走的全部信息", 34, C_YELLOW).move_to([0, 2.5, 0])
        self.play(Write(q), run_time=1.2)
        cards = VGroup()
        for name, pid, st, col in (("鸣人和佐助", "04115", "(行, 列, 查克拉)", C_LOW),
                                   ("水淹七军", "M12029", "每格的水位", C_BLUE),
                                   ("变换的迷宫", "T04129", "(行, 列, 时间 % K)", C_PURPLE)):
            box = RoundedRectangle(corner_radius=0.2, width=4.2, height=2.7, stroke_color=col, stroke_width=3)
            body = VGroup(T(name, 34, col), mono(pid, 24, C_GREY), mono(st, 26)).arrange(DOWN, buff=0.3).move_to(box)
            cards.add(VGroup(box, body))
        cards.arrange(RIGHT, buff=0.3).move_to([0, -0.3, 0])
        for k, key in enumerate(("鸣人和佐助", "水淹七军", "变换的迷宫")):
            self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(cards[k], shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("余数", self.now))
        wk = T("第 13 周题单", 22, C_GREY).next_to(cards[2], DOWN, buff=0.2)
        self.play(FadeIn(wk), Indicate(cards[2][1][2], color=C_PURPLE), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 12 周 BFS 2.4–2.6 节", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
