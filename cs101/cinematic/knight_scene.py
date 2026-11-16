"""马走日与数湖泊：回溯要不要撤销（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。走法、调用次数、湖数和「写反了」两个变体的数字都来自 knightdata
（test_knight.py 用简单路径枚举、BFS 连通块对撞讲义输出与旁白数字）。

快进动画用一个 ValueTracker 驱动：棋盘、格子编号、路径折线和计数器放进同一个带 updater 的 VGroup，
Cairo 渲染器才会把它们当成「在动」的对象逐帧重画。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knightdata as K  # noqa: E402
from cine import *  # noqa: E402,F403

SQ_A, SQ_B = "#232836", "#1a1e28"
N, M, SX, SY = K.BOARD
TOTAL = N * M
CNT, CALLS, EV, TOURS = K.knight_trace(*K.BOARD)
SNAPS = K.snapshots(*K.BOARD)
F_CNT, F_CALLS, F_EV, _ = K.knight_trace(*K.BOARD, undo=False)
F_SNAPS = K.snapshots(*K.BOARD, undo=False)
F_DEEP = K.max_step(*K.BOARD, undo=False)
FIRST_TOUR = next(i for i, s in enumerate(SNAPS) if len(s) == TOTAL)          # 下标从 0
CUM = []                                                                     # 前 k 次调用找到的走法数
_c = 0
for _s in SNAPS:
    _c += len(_s) == TOTAL
    CUM.append(_c)
L_CNT, L_CALLS, L_EV, L_LAKES = K.lake_trace(K.LAKE)
U_CNT, U_CALLS, U_EV, _ = K.lake_trace(K.LAKE, undo=True)
S_CNT, S_CALLS = K.lake_trace(K.SAMPLE)[:2]
SU_CNT, SU_CALLS = K.lake_trace(K.SAMPLE, undo=True)[:2]
LAKE_COL = [C_TEAL, C_PURPLE, C_YELLOW]
WATER = "#2F6F9F"


def cell_pos(center, cell, r, c, n=N, m=M):
    return np.array(center, dtype=float) + np.array([(c - (m - 1) / 2) * cell, ((n - 1) / 2 - r) * cell, 0])


def mix(a, b, t):
    return interpolate_color(ManimColor(a), ManimColor(b), t).to_hex()


def setv(m, v):
    if int(m.get_value()) != v:
        m.set_value(v)


def counter(label, col=WHITE, size=26):
    g = VGroup(T(label, 24, C_GREY), Integer(0, color=col).scale(size / 36))
    g.arrange(RIGHT, buff=0.25)
    return g


class KBoard(VGroup):
    """5×4 棋盘 + 每格 1..20 的步数编号（预先建好，只切换透明度）+ 路径折线 + 当前格的圈。"""

    def __init__(self, cell, center, numbers=True):
        super().__init__()
        self.cell, self.center = cell, np.array(center, dtype=float)
        self.sq = {}
        for r in range(N):
            for c in range(M):
                s = Square(cell, stroke_width=0).set_fill(self.base(r, c), 1).move_to(self.pos(r, c))
                self.sq[(r, c)] = s
        self.frame = Square(cell * M, stroke_color=C_GREY, stroke_width=2).stretch_to_fit_height(cell * N)
        self.frame.move_to(self.center)
        self.squares = VGroup(*self.sq.values())
        self.poly = VMobject(stroke_color=C_YELLOW, stroke_width=3, stroke_opacity=0.55)
        self.poly.set_points_as_corners([self.pos(SX, SY), self.pos(SX, SY)])
        self.lab = {}
        labs = VGroup()
        if numbers:
            for key in self.sq:
                row = [Text(str(k), font=MONO, font_size=int(cell * 30), color=WHITE).move_to(self.pos(*key))
                       .set_opacity(0) for k in range(1, TOTAL + 1)]
                self.lab[key] = row
                labs.add(*row)
        self.ring = Square(cell * 0.86, stroke_color=C_YELLOW, stroke_width=4).move_to(self.pos(SX, SY))
        self.ring.set_stroke(opacity=0)
        self.add(self.squares, self.frame, self.poly, labs, self.ring)
        self.shown = {}                        # 格子 -> (编号, 颜色)
        self.fill = {k: self.base(*k) for k in self.sq}

    @staticmethod
    def base(r, c):
        return SQ_A if (r + c) % 2 == 0 else SQ_B

    def pos(self, r, c):
        return cell_pos(self.center, self.cell, r, c)

    def show(self, path, marked=None, head_col=C_YELLOW, path_col=C_BLUE):
        """path：当前路径；marked：{格子: 进入时的步数}，已标记但不在路径上的格子灰着保留编号（忘了撤销）。"""
        on = {p: i + 1 for i, p in enumerate(path)}
        want = {}
        for key in self.sq:
            if key in on:
                want[key] = (on[key], "#FFFFFF", mix(SQ_A, path_col, 0.45))
            elif marked and key in marked:
                want[key] = (marked[key], C_GREY, "#3a3f4c")
            else:
                want[key] = (None, None, self.base(*key))
        for key, (k, col, fill) in want.items():
            if self.lab and self.shown.get(key) != (k, col):
                old = self.shown.get(key)
                if old and old[0]:
                    self.lab[key][old[0] - 1].set_opacity(0)
                if k:
                    self.lab[key][k - 1].set_color(col).set_opacity(1)
                self.shown[key] = (k, col)
            if self.fill[key] != fill:
                self.sq[key].set_fill(fill, 1)
                self.fill[key] = fill
        pts = [self.pos(*p) for p in path] or [self.pos(SX, SY)]
        if len(pts) == 1:
            pts = pts * 2
        self.poly.set_points_as_corners(pts)
        self.ring.move_to(pts[-1]).set_stroke(head_col, opacity=1)


class LBoard(VGroup):
    """数湖泊的 5×4 网格：陆地 / 水 / 各湖的颜色 / 当前递归路径。"""

    def __init__(self, cell, center, grid=K.LAKE):
        super().__init__()
        self.cell, self.center, self.grid = cell, np.array(center, dtype=float), grid
        self.n, self.m = len(grid), len(grid[0])
        self.sq = {}
        for r in range(self.n):
            for c in range(self.m):
                s = Square(cell, stroke_color="#0f1117", stroke_width=2).set_fill(self.base(r, c), 1)
                s.move_to(self.pos(r, c))
                self.sq[(r, c)] = s
        self.frame = Rectangle(width=cell * self.m, height=cell * self.n, stroke_color=C_GREY, stroke_width=2)
        self.frame.move_to(self.center)
        self.poly = VMobject(stroke_color=C_YELLOW, stroke_width=4, stroke_opacity=0.9)
        self.poly.set_points_as_corners([self.center, self.center]).set_stroke(opacity=0)
        self.add(VGroup(*self.sq.values()), self.frame, self.poly)
        self.fill = {k: self.base(*k) for k in self.sq}

    def base(self, r, c):
        return WATER if self.grid[r][c] == 'W' else SQ_B

    def pos(self, r, c):
        return cell_pos(self.center, self.cell, r, c, self.n, self.m)

    def paint(self, colors, path=()):
        for key in self.sq:
            f = colors.get(key, self.base(*key))
            if self.fill[key] != f:
                self.sq[key].set_fill(f, 1)
                self.fill[key] = f
        if path:
            pts = [self.pos(*p) for p in path]
            if len(pts) == 1:
                pts = pts * 2
            self.poly.set_points_as_corners(pts).set_stroke(opacity=0.9)
        else:
            self.poly.set_stroke(opacity=0)


def lake_states(events, undo):
    """回放 lake_trace 的事件：每次进入 dfs 后的 (调用数, 湖数, 已标记格子, 当前路径, 本湖起点)。"""
    out, marked, path, calls, lakes, start = [], {}, [], 0, 0, None
    for e in events:
        if e[0] == "start":
            lakes += 1
            start = (e[1], e[2])
            marked[start] = lakes
        elif e[0] == "in":
            calls += 1
            del path[e[3] - 1:]
            path.append((e[1], e[2]))
            marked[(e[1], e[2])] = lakes
            out.append((calls, lakes, dict(marked), tuple(path), start))
        else:
            marked.pop((e[1], e[2]), None)
    return out


L_STATES = lake_states(L_EV, False)
U_STATES = lake_states(U_EV, True)


class KnightLesson(Lesson):
    def construct(self):
        for b in ("title", "knight", "kcode", "ktour", "kforget", "lake", "lwalk", "lwrong", "why", "recap"):
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
        title = T("马走日与数湖泊", 54).move_to([0, 3.0, 0])
        sub = T("回溯要不要撤销", 30, C_BLUE).next_to(title, DOWN, buff=0.22)
        kb = KBoard(0.6, (-4.0, -0.2, 0), numbers=False)
        lb = LBoard(0.6, (4.0, -0.2, 0))
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), FadeIn(kb), FadeIn(lb), run_time=1.2)
        tour = TOURS[0]
        kb.poly.set_points_as_corners([kb.pos(*tour[0]), kb.pos(*tour[0])])
        path_line = VMobject(stroke_color=C_YELLOW, stroke_width=3).set_points_as_corners([kb.pos(*p) for p in tour])
        colors = {}
        for i, lake in enumerate(L_LAKES):
            for p in lake:
                colors[p] = mix(SQ_B, LAKE_COL[i], 0.75)
        self.play(Create(path_line), run_time=2.4, rate_func=linear)
        self.play(*[lb.sq[p].animate.set_fill(colors[p], 1) for p in colors], run_time=1.0)
        lb.fill.update(colors)
        cap_k = T("马走日：数走法", 26, WHITE).next_to(kb, DOWN, buff=0.25)
        cap_l = T("数湖泊：数连通块", 26, WHITE).next_to(lb, DOWN, buff=0.25)
        self.play(FadeIn(cap_k), FadeIn(cap_l), run_time=0.6)
        self.wait_until(self.cue_start("区别只在一行", self.now))
        line = Text("visited[nx][ny] = False", font=MONO, font_size=22, color=C_YELLOW).move_to([0, 0.2, 0])
        q = T("要不要？", 28, C_YELLOW).next_to(line, DOWN, buff=0.3)
        self.play(FadeIn(line, shift=UP * 0.2), FadeIn(q), run_time=0.8)
        self.wait_until(self.cue_start("马走日必须撤销", self.now))
        yes = T("必须撤销", 26, C_GREEN).next_to(cap_k, DOWN, buff=0.15)
        self.play(FadeIn(yes, shift=UP * 0.15), run_time=0.6)
        self.wait(1.3)
        no = T("绝不能撤销", 26, C_RED).next_to(cap_l, DOWN, buff=0.15)
        self.play(FadeIn(no, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 马走日：规则
    def knight_beat(self):
        self.beat("knight")
        cell = 1.0
        kb = KBoard(cell, (-3.4, 0.1, 0), numbers=False)
        head = T("5 × 4 棋盘", 26, C_GREY).next_to(kb.frame, UP, buff=0.15)
        self.play(FadeIn(kb), FadeIn(head), run_time=0.8)
        cen = (2, 1)
        piece = VGroup(Circle(cell * 0.36, stroke_color=WHITE, stroke_width=2).set_fill(C_YELLOW, 1),
                       T("马", int(cell * 30), BG))
        piece[1].move_to(piece[0])
        piece.move_to(kb.pos(*cen))
        self.play(FadeIn(piece, scale=1.4), run_time=0.6)
        self.wait_until(self.cue_start("日字", self.now))
        tg, outs = VGroup(), VGroup()
        for dx, dy in K.KNIGHT:
            r, c = cen[0] + dx, cen[1] + dy
            p = kb.pos(r, c)
            if 0 <= r < N and 0 <= c < M:
                tg.add(Circle(cell * 0.3, stroke_color=C_GREEN, stroke_width=4).move_to(p))
            else:
                outs.add(DashedVMobject(Circle(cell * 0.3, stroke_color=C_RED, stroke_width=3), num_dashes=12)
                         .move_to(p))
        bend = VGroup(*[Line(kb.pos(*cen), m.get_center(), buff=cell * 0.33, stroke_color=C_GREY, stroke_width=2,
                             stroke_opacity=0.7) for m in [*tg, *outs]])
        self.play(Create(bend), LaggedStart(*[Create(m) for m in [*tg, *outs]], lag_ratio=0.12), run_time=1.6)
        note = VGroup(VGroup(Circle(0.14, stroke_color=C_GREEN, stroke_width=4), T("棋盘内", 22, C_GREEN))
                      .arrange(RIGHT, buff=0.15),
                      VGroup(DashedVMobject(Circle(0.14, stroke_color=C_RED, stroke_width=3), num_dashes=8),
                             T("出界", 22, C_RED)).arrange(RIGHT, buff=0.15)).arrange(DOWN, buff=0.2,
                                                                                      aligned_edge=LEFT)
        note.move_to([1.6, 2.2, 0], aligned_edge=LEFT)
        cnt8 = T(f"{len(tg)} + {len(outs)} = 8 个方向", 24, C_GREY).next_to(note, DOWN, buff=0.3).align_to(note, LEFT)
        self.play(FadeIn(note), FadeIn(cnt8), run_time=0.7)
        self.wait_until(self.cue_start("不重复地走遍", self.now))
        self.play(FadeOut(VGroup(tg, outs, bend)), piece.animate.move_to(kb.pos(SX, SY)), run_time=0.8)
        rules = VGroup(T("从左上角出发", 28), T(f"不重复地走遍全部 {TOTAL} 格", 28),
                       T("一共有多少种走法？", 30, C_YELLOW)).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        rules.move_to([1.6, -0.9, 0], aligned_edge=LEFT)
        self.play(LaggedStart(*[FadeIn(x, shift=LEFT * 0.2) for x in rules], lag_ratio=0.35), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 马走日：讲义代码
    def kcode_beat(self):
        self.beat("kcode")
        src = ("def dfs(x, y, step):\n    nonlocal count\n    if step == total:\n        count += 1\n        return\n"
               "    for dx, dy in KNIGHT:\n        nx, ny = x + dx, y + dy\n"
               "        if 0 <= nx < n and 0 <= ny < m and not visited[nx][ny]:\n"
               "            visited[nx][ny] = True\n            dfs(nx, ny, step + 1)\n"
               "            visited[nx][ny] = False        # 回溯\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 21})
        code.move_to([-1.9, 0.3, 0])
        if code.get_left()[0] < -6.9:
            code.scale_to_fit_width(10.0).move_to([-1.9, 0.3, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.1, 0.03), stroke_width=2)
            tag = T(txt, 22, col).next_to(code, RIGHT, buff=0.25).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
            return hl
        mark([5], "八个方向", "八个方向", C_BLUE)
        mark([7], "没出界", "不出界、没走过", C_TEAL)
        mark([8, 9], "就标记", "标记 + 递归", C_GREEN)
        h = mark([10], "清掉", "撤销标记", C_YELLOW)
        mark([2, 3], "走满二十步", "走满：计数", C_PURPLE)
        self.wait_until(self.cue_start("最后清掉", self.now))
        big = T("这一行 = 回溯", 26, C_YELLOW).next_to(code, DOWN, buff=0.3).align_to(code, RIGHT)
        self.play(Indicate(h, color=C_YELLOW, scale_factor=1.05), FadeIn(big, shift=UP * 0.2), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 马走日：快进整棵搜索
    def ktour_beat(self):
        self.beat("ktour")
        kb = KBoard(1.0, (-3.4, 0.1, 0))
        tr = ValueTracker(0)
        c_calls, c_tours = counter("调用次数"), counter("走法", C_GREEN)
        c_step = counter("当前步数", C_YELLOW)
        panel = VGroup(c_step, c_calls, c_tours).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([2.2, 1.3, 0],
                                                                                                aligned_edge=LEFT)
        live = VGroup(kb, panel)
        state = {"col": C_YELLOW}

        def upd(_m):
            k = int(round(tr.get_value()))
            path = SNAPS[k]
            full = len(path) == TOTAL
            kb.show(path, head_col=C_GREEN if full else state["col"], path_col=C_GREEN if full else C_BLUE)
            setv(c_step[1], len(path))
            setv(c_calls[1], k + 1)
            setv(c_tours[1], CUM[k])
        upd(live)
        self.play(FadeIn(live), run_time=0.6)
        live.add_updater(upd)
        dead = next(i for i in range(1, len(SNAPS)) if len(SNAPS[i]) <= len(SNAPS[i - 1])) - 1   # 第一次卡住
        assert len(SNAPS[dead]) == 14
        self.play(tr.animate.set_value(dead), run_time=0.3 * dead, rate_func=linear)
        self.wait_until(self.cue_start("无路可走", self.now))
        state["col"] = C_RED
        stuck = T(f"第 {len(SNAPS[dead])} 步：无路可走", 24, C_RED).move_to([2.2, -0.5, 0], aligned_edge=LEFT)
        self.play(FadeIn(stuck), Indicate(kb.ring, color=C_RED), run_time=0.8)
        self.wait_until(self.cue_start("只好退一步", self.now))
        state["col"] = C_YELLOW
        self.play(FadeOut(stuck), tr.animate.set_value(dead + 6), run_time=3.0, rate_func=linear)
        self.wait_until(self.cue_start("第一千四百", self.now))
        self.play(tr.animate.set_value(FIRST_TOUR), run_time=3.0, rate_func=rate_functions.ease_in_sine)
        found = T(f"第 {FIRST_TOUR + 1} 次调用：第一条走法", 24, C_GREEN).move_to([2.2, -0.5, 0], aligned_edge=LEFT)
        self.play(FadeIn(found), run_time=0.6)
        self.wait_until(self.cue_start("全部搜完", self.now))
        self.play(FadeOut(found), tr.animate.set_value(len(SNAPS) - 1), run_time=max(3.0, self.left() - 2.2),
                  rate_func=linear)
        live.clear_updaters()
        res = VGroup(T("全部搜完", 24, C_GREY),
                     VGroup(T("调用", 26), MathTex(f"{CALLS:,}".replace(",", r"\,")).scale(0.9), T("次", 26))
                     .arrange(RIGHT, buff=0.15),
                     VGroup(T("走法", 26, C_GREEN), MathTex(str(CNT), color=C_GREEN).scale(0.9), T("种", 26, C_GREEN))
                     .arrange(RIGHT, buff=0.15)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        res.move_to([2.2, -1.2, 0], aligned_edge=LEFT)
        self.play(FadeIn(res, shift=UP * 0.2), Indicate(c_tours, color=C_GREEN), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 马走日：忘了撤销
    def kforget_beat(self):
        self.beat("kforget")
        kb = KBoard(1.0, (-3.4, 0.1, 0))
        tag = Text("# visited[nx][ny] = False", font=MONO, font_size=20, color=C_RED).next_to(kb.frame, UP, buff=0.15)
        tr = ValueTracker(0)
        c_calls, c_tours = counter("调用次数"), counter("走法", C_GREEN)
        c_step = counter("当前步数", C_YELLOW)
        panel = VGroup(c_step, c_calls, c_tours).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([2.2, 1.6, 0],
                                                                                                aligned_edge=LEFT)
        entered = {}
        for s in F_SNAPS:
            entered.setdefault(s[-1], len(s))
        order = [s[-1] for s in F_SNAPS]
        state = {"col": C_YELLOW}

        def upd(_m):
            k = int(round(tr.get_value()))
            marked = {p: entered[p] for p in order[:k + 1]}
            kb.show(F_SNAPS[k], marked=marked, head_col=state["col"])
            setv(c_step[1], len(F_SNAPS[k]))
            setv(c_calls[1], k + 1)
        live = VGroup(kb, panel)
        upd(live)
        self.play(FadeIn(live), FadeIn(tag), run_time=0.6)
        live.add_updater(upd)
        dead = next(i for i in range(1, len(F_SNAPS)) if len(F_SNAPS[i]) <= len(F_SNAPS[i - 1])) - 1
        self.play(tr.animate.set_value(dead), run_time=0.25 * dead, rate_func=linear)
        state["col"] = C_RED
        self.play(Indicate(kb.ring, color=C_RED), run_time=0.6)
        self.wait_until(self.cue_start("退回来时", self.now))
        state["col"] = C_YELLOW
        legend = VGroup(Square(0.3, stroke_width=0).set_fill("#3a3f4c", 1), T("退回后仍标着「走过」", 22, C_GREY))
        legend.arrange(RIGHT, buff=0.15).move_to([2.2, -0.4, 0], aligned_edge=LEFT)
        self.play(FadeIn(legend), run_time=0.5)
        t_end = self.cue_start("一条走法也没找到", self.now + 6)
        self.play(tr.animate.set_value(len(F_SNAPS) - 1), run_time=max(2.5, t_end - self.now - 0.3), rate_func=linear)
        live.clear_updaters()
        self.wait_until(t_end)
        zero = VGroup(T("答案", 26, C_RED), MathTex(str(F_CNT), color=C_RED).scale(1.0)).arrange(RIGHT, buff=0.2)
        zero.move_to([2.2, -0.95, 0], aligned_edge=LEFT)
        cmp = T(f"正确版：{CALLS} 次调用，{CNT} 种", 22, C_GREY).next_to(zero, DOWN, buff=0.2).align_to(zero, LEFT)
        self.play(FadeIn(zero, scale=1.3), FadeIn(cmp), run_time=0.8)
        self.wait_until(self.cue_start("讲义说", self.now))
        quote = VGroup(T("忘了这一行，答案只能是 0 或 1", 24, C_YELLOW),
                       T("每格最多进一次 → 最多一条路能走满", 22, C_GREY)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        quote.move_to([1.3, -2.35, 0], aligned_edge=LEFT)
        self.play(FadeIn(quote, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 数湖泊：规则
    def lake_beat(self):
        self.beat("lake")
        lb = LBoard(1.0, (-3.4, 0.1, 0))
        head = T("5 × 4 网格", 26, C_GREY).next_to(lb.frame, UP, buff=0.15)
        self.play(FadeIn(lb), FadeIn(head), run_time=0.8)
        key = VGroup(VGroup(Square(0.3, stroke_width=0).set_fill(WATER, 1), T("水", 24)).arrange(RIGHT, buff=0.15),
                     VGroup(Square(0.3, stroke_color=C_GREY, stroke_width=1).set_fill(SQ_B, 1), T("陆地", 24))
                     .arrange(RIGHT, buff=0.15)).arrange(RIGHT, buff=0.5).move_to([2.2, 2.4, 0], aligned_edge=LEFT)
        self.play(FadeIn(key), run_time=0.5)
        self.wait_until(self.cue_start("八个方向相连", self.now))
        cen = (1, 1)
        ring = VGroup(*[Square(0.92, stroke_color=C_YELLOW, stroke_width=3).move_to(lb.pos(cen[0] + a, cen[1] + b))
                        for a, b in K.DIRS8])
        mid = Square(0.92, stroke_color=WHITE, stroke_width=5).move_to(lb.pos(*cen))
        rule = T("八连通：斜着挨着也算相连", 24, C_YELLOW).move_to([2.2, 1.5, 0], aligned_edge=LEFT)
        self.play(Create(mid), LaggedStart(*[Create(s) for s in ring], lag_ratio=0.1), FadeIn(rule), run_time=1.4)
        self.wait_until(self.cue_start("逐格扫描", self.now))
        self.play(FadeOut(ring), FadeOut(mid), run_time=0.4)
        scan = Square(0.98, stroke_color=WHITE, stroke_width=5).move_to(lb.pos(0, 0))
        c_lake = counter("湖数", C_TEAL).move_to([2.2, 0.4, 0], aligned_edge=LEFT)
        self.play(Create(scan), FadeIn(c_lake), run_time=0.5)
        self.wait_until(self.cue_start("湖数加一", self.now))
        self.play(ChangeDecimalToValue(c_lake[1], 1), Indicate(scan, color=C_TEAL), run_time=0.7)
        self.wait_until(self.cue_start("把整个湖都标记掉", self.now))
        lake0 = L_LAKES[0]
        self.play(*[lb.sq[p].animate.set_fill(mix(SQ_B, LAKE_COL[0], 0.75), 1) for p in lake0], run_time=1.0)
        note = T("标记过的格子，以后扫到也不再算", 22, C_GREY).move_to([2.2, -0.5, 0], aligned_edge=LEFT)
        self.play(FadeIn(note), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 数湖泊：同构代码，不撤销
    def lake_code(self, undo):
        last = ("            g[nx][ny] = 'W'      # 撤销？" if undo else "            # 不撤销")
        src = ("def dfs(x, y):\n    for dx, dy in DIRS8:\n        nx, ny = x + dx, y + dy\n"
               "        if 0 <= nx < n and 0 <= ny < m and g[nx][ny] == 'W':\n"
               "            g[nx][ny] = '.'\n            dfs(nx, ny)\n" + last + "\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 19})
        if code.width > 9.0:
            code.scale_to_fit_width(9.0)
        code.move_to([2.2, 1.55, 0])
        return code

    def lwalk_beat(self):
        self.beat("lwalk")
        lb = LBoard(0.9, (-4.6, 0.0, 0))
        code = self.lake_code(False)
        self.play(FadeIn(lb), FadeIn(code, shift=UP * 0.2), run_time=0.8)
        ln = code.code_lines
        self.wait_until(self.cue_start("回来以后不撤销", self.now))
        hl = SurroundingRectangle(ln[6], color=C_GREEN, buff=(0.1, 0.04), stroke_width=2)
        self.play(Create(hl), run_time=0.5)
        tr = ValueTracker(0)
        c_lake, c_calls = counter("湖数", C_TEAL), counter("调用次数")
        panel = VGroup(c_lake, c_calls).arrange(RIGHT, buff=0.8).next_to(code, DOWN, buff=0.45).align_to(code, LEFT)

        def upd(_m):
            k = int(round(tr.get_value()))
            calls, lakes, marked, path, start = L_STATES[k]
            cols = {p: mix(SQ_B, LAKE_COL[i - 1], 0.75) for p, i in marked.items()}
            lb.paint(cols, path)
            setv(c_lake[1], lakes)
            setv(c_calls[1], calls)
        live = VGroup(lb, panel)
        upd(live)
        self.play(FadeIn(panel), run_time=0.4)
        self.remove(lb)
        self.add(live)
        live.add_updater(upd)
        n0 = len(L_LAKES[0])
        self.wait_until(self.cue_start("每格只进一次", self.now))
        self.play(tr.animate.set_value(n0 - 1), run_time=0.45 * n0, rate_func=linear)
        self.wait_until(self.cue_start("扫描完毕", self.now))
        self.play(tr.animate.set_value(len(L_STATES) - 1), run_time=1.5, rate_func=linear)
        live.clear_updaters()
        self.remove(live)
        self.add(lb, panel)
        lb.paint({p: mix(SQ_B, LAKE_COL[i - 1], 0.75) for p, i in L_STATES[-1][2].items()})
        res = T(f"{L_CNT} 个湖 · {K.water(K.LAKE)} 格水 · {L_CALLS} 次调用", 26, C_GREEN)
        res.next_to(panel, DOWN, buff=0.45).align_to(panel, LEFT)
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(res, hl, panel, code)), run_time=0.6)
        self.remove(panel, res, hl, code)
        self.lb = lb

    # ---------------------------------------------------------------- 数湖泊：写反了
    def lwrong_beat(self):
        self.beat("lwrong")
        lb = self.lb
        lb.paint({})
        code = self.lake_code(True)
        ln = code.code_lines
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.7)
        hl = SurroundingRectangle(ln[6], color=C_RED, buff=(0.1, 0.04), stroke_width=2)
        self.play(Create(hl), ln[6].animate.set_color(C_RED), run_time=0.5)
        tr = ValueTracker(0)
        c_lake, c_calls = counter("湖数", C_TEAL), counter("调用次数")
        panel = VGroup(c_lake, c_calls).arrange(RIGHT, buff=0.8).next_to(code, DOWN, buff=0.45).align_to(code, LEFT)
        done_col = "#3a3f4c"

        def upd(_m):
            k = int(round(tr.get_value()))
            calls, lakes, marked, path, start = U_STATES[k]
            cols = {p: (mix(SQ_B, C_YELLOW, 0.55) if p in path else done_col) for p in marked}
            lb.paint(cols, path)
            setv(c_lake[1], lakes)
            setv(c_calls[1], calls)
        live = VGroup(lb, panel)
        upd(live)
        self.play(FadeIn(panel), run_time=0.4)
        self.remove(lb)
        self.add(live)
        live.add_updater(upd)
        self.wait_until(self.cue_start("又变回了水", self.now))
        self.play(tr.animate.set_value(16), run_time=4.0, rate_func=linear)
        first = next(i for i, s in enumerate(U_STATES) if s[1] == 2) - 1          # 第一个起点的最后一次调用
        t1 = self.cue_start("外层扫描到下一格", self.now + 4)
        self.play(tr.animate.set_value(first), run_time=max(1.5, t1 - self.now - 1.0), rate_func=linear)
        n608 = T(f"只从左上角出发：{U_STATES[first][0]} 次", 22, C_YELLOW).next_to(panel, DOWN, buff=0.35)
        n608.align_to(panel, LEFT)
        self.play(FadeIn(n608), run_time=0.5)
        self.wait_until(t1)
        self.play(tr.animate.set_value(first + 1), run_time=0.6)
        self.play(Indicate(c_lake, color=C_RED), run_time=0.7)
        t2 = self.cue_start("最后数出", self.now + 3)
        self.play(tr.animate.set_value(len(U_STATES) - 1), run_time=max(1.5, t2 - self.now + 1.5), rate_func=linear)
        live.clear_updaters()
        self.remove(live)
        self.add(lb, panel)
        res = VGroup(T(f"数出 {U_CNT} 个湖", 26, C_RED), T(f"调用 {U_CALLS} 次", 26, C_RED)).arrange(RIGHT, buff=0.5)
        res.next_to(n608, DOWN, buff=0.3).align_to(panel, LEFT)
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("换成讲义的样例", self.now))
        self.play(FadeOut(VGroup(lb, code, hl, panel, n608, res)), run_time=0.6)
        self.remove(lb, panel)
        # 讲义样例 10×12：同一张图，对错两版的数字
        sb = LBoard(0.3, (-3.6, 0.6, 0), grid=K.SAMPLE)
        cap = T(f"讲义样例 {len(K.SAMPLE)} × {len(K.SAMPLE[0])}，{K.water(K.SAMPLE)} 格水", 24, C_GREY)
        cap.next_to(sb.frame, DOWN, buff=0.25)
        self.play(FadeIn(sb), FadeIn(cap), run_time=0.6)
        hdr = VGroup(T("湖数", 24, C_GREY), T("调用次数", 24, C_GREY))
        r1 = VGroup(T("不撤销", 26, C_GREEN), MathTex(str(S_CNT), color=C_GREEN), MathTex(str(S_CALLS), color=C_GREEN))
        r2 = VGroup(T("撤销", 26, C_RED), MathTex(str(SU_CNT), color=C_RED),
                    MathTex(f"{SU_CALLS:,}".replace(",", r"\,"), color=C_RED))
        xs = [0.4, 2.6, 4.6]
        for y, row in ((2.0, hdr), (1.0, r1), (0.0, r2)):
            for x, m in zip(xs[-len(row):], row):
                m.move_to([x, y, 0], aligned_edge=LEFT)
        self.play(FadeIn(hdr), FadeIn(r1), run_time=0.7)
        self.wait_until(self.cue_start("加上撤销", self.now))
        self.play(FadeIn(r2, shift=UP * 0.2), run_time=0.7)
        ratio = T(f"约为 {round(SU_CALLS / S_CALLS)} 倍", 26, C_RED).move_to([xs[2], -0.9, 0], aligned_edge=LEFT)
        self.play(FadeIn(ratio), Indicate(r2[2], color=C_RED), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 为什么
    def why_beat(self):
        self.beat("why")
        hk = T("马走日：问的是路线", 30, C_YELLOW).move_to([-3.4, 2.9, 0])
        hl_ = T("数湖泊：问的是格子", 30, C_TEAL).move_to([3.4, 2.9, 0])
        self.play(FadeIn(hk), FadeIn(hl_), run_time=0.6)
        # 左：同一格在两条走法里出现在不同步数
        t1, t2 = TOURS[0], TOURS[-1]
        probe = next(p for p in t1 if t1.index(p) != t2.index(p) and t1.index(p) > 3)
        boards = VGroup()
        for i, (t, col) in enumerate(((t1, C_BLUE), (t2, C_PURPLE))):
            b = KBoard(0.5, (-4.6 + 2.4 * i, 0.9, 0), numbers=False)
            line = VMobject(stroke_color=col, stroke_width=2.5).set_points_as_corners([b.pos(*p) for p in t])
            ring = Square(0.46, stroke_color=C_YELLOW, stroke_width=4).move_to(b.pos(*probe))
            lab = T(f"第 {t.index(probe) + 1} 步", 22, C_YELLOW).next_to(b.frame, DOWN, buff=0.15)
            boards.add(VGroup(b, line, ring, lab))
        self.wait_until(self.cue_start("同一格", self.now))
        self.play(FadeIn(boards[0]), run_time=0.8)
        self.play(FadeIn(boards[1]), run_time=0.8)
        kmsg = T("离开时必须还回去", 26, C_GREEN).move_to([-3.4, -1.25, 0])
        self.play(FadeIn(kmsg, shift=UP * 0.2), run_time=0.6)
        # 右：每格碰一次
        self.wait_until(self.cue_start("哪些格子连在一起", self.now))
        lb = LBoard(0.55, (3.4, 0.9, 0))
        lb.paint({p: mix(SQ_B, LAKE_COL[i], 0.75) for i, lk in enumerate(L_LAKES) for p in lk})
        ones = VGroup(*[Text("1", font=MONO, font_size=18, color=WHITE).move_to(lb.pos(*p))
                        for lk in L_LAKES for p in lk])
        self.play(FadeIn(lb), run_time=0.6)
        self.play(FadeIn(ones), run_time=0.6)
        lmsg = T("碰一次就够，标记就是答案", 26, C_GREEN).move_to([3.4, -1.25, 0])
        self.play(FadeIn(lmsg, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("讲义用显式栈", self.now))
        snip = Code(code_string="g[nx][ny] = '.'          # 先标记\nstack.append((nx, ny))   # 再入栈\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 18})
        stag = T("讲义：显式栈，不怕爆栈", 22, C_GREY)
        VGroup(stag, snip).arrange(RIGHT, buff=0.35).move_to([0, -2.35, 0])
        self.play(FadeIn(snip, shift=UP * 0.2), FadeIn(stag), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        l1 = VGroup(T("数路线", 36, C_YELLOW), MathTex(r"\Rightarrow"), T("要撤销", 36, C_GREEN)).arrange(RIGHT, buff=0.3)
        l2 = VGroup(T("数格子", 36, C_TEAL), MathTex(r"\Rightarrow"), T("不撤销", 36, C_RED)).arrange(RIGHT, buff=0.3)
        lines = VGroup(l1, l2).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([0, 1.3, 0])
        self.play(FadeIn(l1, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("数格子", self.now))
        self.play(FadeIn(l2, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("连通块还有", self.now))
        nxt = VGroup(T("连通块的另一种数法", 26, C_GREY), T("并查集", 30, C_BLUE)).arrange(RIGHT, buff=0.3)
        nxt.move_to([0, -0.9, 0])
        self.play(FadeIn(nxt, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 9 周 回溯 1.5–1.6 节 · OpenJudge 04123、02386、05585", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
