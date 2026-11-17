"""箭头迷阵：每格一条出边，路线必定出界或成环（11 月月考 T3 精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例、每次出发的 path 与收尾、状态表、总步数、绕圈网格的路线、
递归写法在一行九百 / 两千个 R 上的结果、讲义代码节选全部来自 novarrowdata（讲义原样代码在 novdata.solve_t3；
test_novarrow.py 用逐格模拟 nm+1 步的暴力独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novarrowdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

DIM = "#3a4050"
ST_COL = {0: DIM, 1: C_YELLOW, 2: C_GREEN, 3: C_RED}         # 四种状态
ST_NAME = {0: "未访问", 1: "在路上", 2: "能逃", 3: "逃不出"}
FILL = 0.5                                                    # 格子填充透明度（< 0.6，不算不透明形状）


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


class Board:
    """网格：格子、箭头、编号。pos(i, j) 对场外坐标也有效。"""

    def __init__(self, g, cs, center, nums=True, arrow_col=WHITE):
        self.g, self.cs, self.c = g, cs, np.array([center[0], center[1], 0.0])
        self.n, self.m = len(g), len(g[0])
        self.cells, self.arrows, self.nums = {}, {}, {}
        for i in range(self.n):
            for j in range(self.m):
                p = self.pos(i, j)
                self.cells[(i, j)] = Square(cs * 0.94, stroke_color=C_GREY, stroke_width=2).set_fill(DIM, 0.3).move_to(p)
                di, dj = D.MOVE[g[i][j]]
                v = np.array([dj, -di, 0]) * cs * 0.27
                self.arrows[(i, j)] = Arrow(p - v, p + v, buff=0, color=arrow_col, stroke_width=6,
                                            max_tip_length_to_length_ratio=0.4)
                if nums:
                    self.nums[(i, j)] = M(str(i * self.m + j), int(17 * cs / 1.1), C_GREY).move_to(
                        p + np.array([-0.34, 0.34, 0]) * cs)
        self.group = VGroup(*self.cells.values(), *self.arrows.values(), *self.nums.values())

    def pos(self, i, j):
        return self.c + np.array([(j - (self.m - 1) / 2) * self.cs, -(i - (self.n - 1) / 2) * self.cs, 0])

    def edge(self, last, hit, k=0.72):
        """从格 last 朝场外格 hit 走到边界外一点。"""
        a, b = self.pos(*last), self.pos(*hit)
        return a + (b - a) * k

    def uid(self, i, j):
        return i * self.m + j


class NovArrowLesson(Lesson):
    def construct(self):
        for b in ("title", "graph", "states", "walk", "wander", "cost", "recur", "code", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    # ---------------------------------------------------------------- 公共
    def cue_start(self, key, default=None):
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novarrow] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def head(self, s, color=WHITE, y=2.85):
        h = T(s, 30, color)
        return h.move_to([-6.6 + h.width / 2, y, 0])

    def left_at(self, m, x, y):
        return m.move_to([x + m.width / 2, y, 0])

    def run_walks(self, b: Board, walks, rt=0.3, on_step=None, on_end=None, keys=None):
        """逐次出发：指针沿 path 走、格子标黄（在路上），收尾后整条 path 回填结论色。"""
        ptr = Dot(radius=0.1, color=WHITE)
        for w_i, w in enumerate(walks):
            if keys:
                self.at(keys[w_i])
            ptr.move_to(b.pos(*w["path"][0]))
            self.play(FadeIn(ptr, scale=0.5), run_time=0.15)
            for k, c in enumerate(w["path"]):
                if k:
                    self.play(ptr.animate.move_to(b.pos(*c)), run_time=rt * 0.7)
                anims = [b.cells[c].animate.set_fill(ST_COL[1], FILL)]
                if on_step:
                    anims += on_step(w, k)
                self.play(*anims, run_time=rt * 0.7)
            hit = w["hit"]
            ring = None
            if w["end"] == "out":
                self.play(ptr.animate.move_to(b.edge(w["path"][-1], hit)), run_time=rt)
            else:
                self.play(ptr.animate.move_to(b.pos(*hit)), run_time=rt)
                ring = Circle(b.cs * 0.42, color=ST_COL[w["res"]], stroke_width=5).move_to(b.pos(*hit))
                self.play(Create(ring), run_time=0.3)
            extra = on_end(w) if on_end else []
            self.play(*[b.cells[c].animate.set_fill(ST_COL[w["res"]], FILL) for c in w["path"]],
                      FadeOut(ptr), *([FadeOut(ring)] if ring else []), *extra, run_time=0.4)

    # ---------------------------------------------------------------- 片头：题意与样例一
    def title_beat(self):
        self.beat("title")
        kick = T("11 月月考 · T3 · M31531", 24, C_BLUE).move_to([0, 3.0, 0])
        title = T("箭头迷阵", 56).move_to([0, 2.3, 0])
        sub = T("每格一条出边，路线必定出界或成环", 28, C_YELLOW).move_to([0, 1.6, 0])
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)
        x0 = -6.4
        l1 = self.left_at(VGroup(T("n × m 网格，每格一个箭头", 26), M("U D L R", 26, C_BLUE)).arrange(RIGHT, buff=0.25), x0, 0.55)
        l2 = self.left_at(T("从一格出发照箭头走，走出场地 = 能逃出", 26), x0, -0.15)
        l3 = self.left_at(T("问：有几格能逃出？", 26, C_YELLOW), x0, -0.85)
        l4 = self.left_at(T("n × m ≤ 2×10⁵", 24, C_GREY), x0, -1.55)
        self.at("上下左右")
        self.play(FadeIn(l1, shift=RIGHT * 0.2), run_time=0.5)
        self.at("一直照箭头")
        self.play(FadeIn(l2, shift=RIGHT * 0.2), run_time=0.5)
        self.at("问有几格")
        self.play(FadeIn(l3, shift=RIGHT * 0.2), FadeIn(l4), run_time=0.5)

        self.at("样例一")
        g = D.SAMPLE1
        walks, st = D.trace(g)
        assert st.count(2) == D.solve(g) == 2
        b = Board(g, 1.0, (4.2, -0.9), nums=False)
        lab = T("样例 1", 24, C_GREY).move_to([4.2, 0.95, 0])
        self.play(FadeIn(b.group), FadeIn(lab), run_time=0.6)
        by_start = {w["start"]: w for w in walks}
        assert [w["end"] for w in walks] == ["out", "cycle", "out"]
        for key, s in (("左上向上", (0, 0)), ("左下向下", (1, 0)), ("右边两格", (0, 1))):
            self.at(key)
            self.run_walks(b, [by_start[s]], rt=0.35)
        self.at("答案是二")
        ans = T(f"答案 {st.count(2)}", 28, C_GREEN).move_to([4.2, -2.45, 0])
        self.play(FadeIn(ans, scale=1.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 结构：每格一条出边，暴力太慢
    def graph_beat(self):
        self.beat("graph")
        g = D.SAMPLE2
        b = Board(g, 1.1, (-3.9, -0.3), nums=True)
        h = self.head("每格恰好一条出边")
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(b.group), run_time=0.8)
        self.at("每格恰好")
        self.play(LaggedStart(*[Indicate(a, color=C_YELLOW, scale_factor=1.3) for a in b.arrows.values()],
                              lag_ratio=0.08), run_time=1.2)
        x0 = 0.3
        r1 = self.left_at(T("从哪出发，路线都唯一确定", 26), x0, 1.9)
        self.play(FadeIn(r1, shift=LEFT * 0.2), run_time=0.5)
        self.at("假如走了")
        nm = b.n * b.m
        r2 = self.left_at(VGroup(T(f"场内 {nm} 格，走 {nm + 1} 步还在场内", 24),
                                 T("⟹ 必有一格到过两次（鸽巢）", 24, C_YELLOW)).arrange(DOWN, buff=0.15, aligned_edge=LEFT),
                          x0, 0.95)
        self.play(FadeIn(r2, shift=LEFT * 0.2), run_time=0.6)

        self.at("回到同一格")
        cells, stop, out = D.route(g, (1, 1))
        assert not out and stop == (1, 1) and cells == [(1, 1), (2, 1)]
        loop = cells + [stop]
        assert [b.uid(*c) for c in cells] == [4, 7]
        ptr = Dot(radius=0.11, color=C_YELLOW).move_to(b.pos(*loop[0]))
        cnt = M("1", 26, C_YELLOW)
        tag = VGroup(T("第", 22, C_GREY), cnt, T("步", 22, C_GREY)).arrange(RIGHT, buff=0.12)
        tag.move_to(b.pos(0, 0) + np.array([-0.1, 0.95, 0]))
        same = self.left_at(T("4 → 7 → 4 → 7 → …  之后一模一样", 24, C_RED), x0, -0.15)
        self.play(FadeIn(ptr), FadeIn(tag), run_time=0.3)
        seq = [loop[k % 2] for k in range(1, 7)]
        for k, c in enumerate(seq):
            new = M(str(k + 2), 26, C_YELLOW).move_to(cnt)
            self.play(ptr.animate.move_to(b.pos(*c)), Transform(cnt, new), run_time=0.32)
            if k == 1:
                self.play(Indicate(b.cells[(1, 1)], color=C_RED, scale_factor=1.08), FadeIn(same), run_time=0.45)
        self.play(FadeOut(ptr), FadeOut(tag), run_time=0.3)

        self.at("所以暴力")
        r3 = self.left_at(VGroup(T("暴力：每格最多走", 24), M("nm+1", 24, C_BLUE), T("步", 24),
                                 M("→ O((nm)²)", 24, C_YELLOW)).arrange(RIGHT, buff=0.15), x0, -1.05)
        self.play(FadeIn(r3, shift=LEFT * 0.2), run_time=0.5)
        self.at("二十万乘")
        assert 3.9e10 < D.BRUTE_STEPS < 4.1e10
        r4 = self.left_at(VGroup(M("nm = 2×10⁵", 24), M("→ 约 4×10¹⁰ 步", 24, C_RED), T("太慢", 24, C_RED)).arrange(RIGHT, buff=0.2),
                          x0, -1.8)
        self.play(FadeIn(r4, shift=LEFT * 0.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 四种状态与 path
    def states_beat(self):
        self.beat("states")
        h = self.head("记住结论：每格只走一次")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("四种状态")
        chips = VGroup()
        for k in range(4):
            sq = Square(0.62, stroke_color=ST_COL[k], stroke_width=2).set_fill(ST_COL[k], FILL)
            chips.add(VGroup(VGroup(sq, M(str(k), 26).move_to(sq)), T(ST_NAME[k], 24)).arrange(RIGHT, buff=0.18))
        chips.arrange(RIGHT, buff=0.7).move_to([0, 1.85, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.15) for c in chips], lag_ratio=0.25), run_time=1.4)

        self.at("边走边标")
        walks, _ = D.trace(D.SAMPLE2)
        demo = walks[1]["ids"]
        assert demo == [1, 2, 5]
        plab = M("path = [", 26).move_to([-4.6, 0.75, 0])
        self.play(FadeIn(plab), run_time=0.3)
        boxes = VGroup()
        for k, u in enumerate(demo):
            sq = Square(0.55, stroke_color=ST_COL[1], stroke_width=2).set_fill(ST_COL[1], FILL)
            bx = VGroup(sq, M(str(u), 24).move_to(sq)).move_to([plab.get_right()[0] + 0.45 + 0.65 * k, 0.75, 0])
            boxes.add(bx)
            self.play(FadeIn(bx, shift=LEFT * 0.2), run_time=0.35)
        close = M("…]", 26).next_to(boxes, RIGHT, buff=0.15)
        note = T("经过的格标 1，按顺序记下", 22, C_GREY).next_to(close, RIGHT, buff=0.4)
        self.play(FadeIn(close), FadeIn(note), run_time=0.4)

        rules = [("走出界", "出界", "res = 2 能逃", 2), ("撞上标一", "撞上 1（本条路线）", "res = 3 成环", 3),
                 ("撞上二或三", "撞上 2 或 3", "res = 照抄，接上结论", None)]
        rows = VGroup()
        for k, (key, a, c, col) in enumerate(rules):
            self.at(key)
            row = VGroup(T(a, 24), T("→", 24, C_GREY), T(c, 24, ST_COL[col] if col else C_BLUE)).arrange(RIGHT, buff=0.25)
            self.left_at(row, -4.6, -0.25 - 0.62 * k)
            rows.add(row)
            self.play(FadeIn(row, shift=LEFT * 0.2), run_time=0.45)
        self.at("回填")
        fill = self.left_at(VGroup(M("for u in path: st[u] = res", 24, C_YELLOW), T("回填", 24, C_YELLOW)).arrange(RIGHT, buff=0.35),
                            -4.6, -2.25)
        self.play(FadeIn(fill, shift=UP * 0.15),
                  *[bx[0].animate.set_fill(ST_COL[2], FILL).set_stroke(ST_COL[2]) for bx in boxes], run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 样例二逐次出发
    def walk_beat(self):
        self.beat("walk")
        g = D.SAMPLE2
        walks, st_final = D.trace(g)
        assert D.solve(g) == st_final.count(2) == 5
        assert [w["sid"] for w in walks] == [0, 1, 3, 4, 6, 8]
        b = Board(g, 1.2, (-3.75, -0.35), nums=True)
        h = self.head("样例 2：3 × 3")
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(b.group), run_time=0.8)

        x0, xb = 0.35, 1.25
        plab = M("path", 24, C_GREY).move_to([x0 + 0.3, 1.95, 0])
        slab = M("st", 24, C_GREY).move_to([x0 + 0.3, -0.35, 0])
        st_box, st_num, st_val = [], [], [0] * 9
        for u in range(9):
            p = np.array([xb + 0.6 * u + 0.27, -0.35, 0])
            sq = Square(0.52, stroke_color=C_GREY, stroke_width=2).set_fill(DIM, 0.3).move_to(p)
            st_box.append(sq)
            st_num.append(M("0", 22).move_to(p))
        st_idx = VGroup(*[M(str(u), 15, C_GREY).next_to(st_box[u], UP, buff=0.08) for u in range(9)])
        self.play(FadeIn(plab), FadeIn(slab), FadeIn(VGroup(*st_box)), FadeIn(VGroup(*st_num)), FadeIn(st_idx), run_time=0.6)

        path_row = VGroup()
        end_txt = [None]

        def set_st(u, v):
            st_val[u] = v
            new = M(str(v), 22).move_to(st_box[u])
            return [Transform(st_num[u], new), st_box[u].animate.set_fill(ST_COL[v], FILL)]

        def on_step(w, k):
            u = w["ids"][k]
            sq = Square(0.5, stroke_color=ST_COL[1], stroke_width=2).set_fill(ST_COL[1], FILL)
            bx = VGroup(sq, M(str(u), 22).move_to(sq)).move_to([xb + 0.27 + 0.6 * k, 1.95, 0])
            path_row.add(bx)
            return [FadeIn(bx, shift=LEFT * 0.15), *set_st(u, 1)]

        def on_end(w):
            hu = b.uid(*w["hit"]) if w["end"] != "out" else None
            txt = {"out": ("出界 → res = 2", C_GREEN),
                   "cycle": (f"撞上 {hu}（st = 1）→ 成环 res = 3", C_RED),
                   "join": (f"撞上 {hu}（st = {w['res']}）→ 接上 res = {w['res']}", C_BLUE)}[w["end"]]
            t = self.left_at(T(txt[0], 24, txt[1]), x0, 1.05)
            out = [FadeIn(t, shift=LEFT * 0.15)]
            if end_txt[0] is not None:
                out.append(FadeOut(end_txt[0]))
            end_txt[0] = t
            for bx in path_row:
                out.append(bx[0].animate.set_fill(ST_COL[w["res"]], FILL).set_stroke(ST_COL[w["res"]]))
            for u in w["ids"]:
                out += set_st(u, w["res"])
            return out

        keys = ["零号向上", "一号向右", "三号向左", "四号向下", "六号向右", "八号向左"]
        for w, key in zip(walks, keys):
            if len(path_row):
                self.play(FadeOut(path_row), run_time=0.25)
                path_row.remove(*path_row.submobjects)
            self.run_walks(b, [w], rt=0.32, on_step=on_step, on_end=on_end, keys=[key])
        assert st_val == st_final

        self.at("已有结论")
        skipped = sorted(set(range(9)) - {w["sid"] for w in walks})
        assert skipped == [2, 5, 7]
        sk = self.left_at(VGroup(T("出发前 st[s] ≠ 0 → 跳过：", 24, C_GREY),
                                 M("、".join(map(str, skipped)), 24, C_YELLOW)).arrange(RIGHT, buff=0.15), x0, -1.25)
        self.play(FadeOut(path_row), FadeIn(sk), *[Indicate(st_box[u], color=C_YELLOW) for u in skipped], run_time=0.7)
        self.at("答案五")
        esc = [u for u in range(9) if st_final[u] == 2]
        ans = self.left_at(VGroup(T("能逃：", 26, C_GREEN), M(" ".join(map(str, esc)), 26, C_GREEN),
                                  T(f"答案 {len(esc)}", 28, C_GREEN)).arrange(RIGHT, buff=0.25), x0, -2.05)
        self.play(FadeIn(ans, scale=1.1), *[Indicate(b.cells[divmod(u, 3)], color=C_GREEN, scale_factor=1.05) for u in esc],
                  run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 「途中可以先绕圈」
    def route_line(self, b, cells, stop, out, cyc_from=None):
        pts = [b.pos(*c) for c in cells]
        end = b.edge(cells[-1], stop) if out else b.pos(*stop)
        lines = VGroup()
        for k in range(len(pts)):
            a = pts[k]
            z = pts[k + 1] if k + 1 < len(pts) else end
            col = C_GREEN if out else (C_RED if cyc_from is not None and k >= cyc_from else C_YELLOW)
            if k + 1 < len(pts):
                lines.add(Line(a, z, color=col, stroke_width=7))
            else:
                lines.add(Arrow(a, z, buff=0, color=col, stroke_width=7, max_tip_length_to_length_ratio=0.3))
        return lines

    def wander_beat(self):
        self.beat("wander")
        h = VGroup(T("「途中可以先绕圈」", 30, C_YELLOW), T("≠ 掉进环", 30)).arrange(RIGHT, buff=0.3)
        h.move_to([0, 2.85, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        cs = 1.0
        b1 = Board(D.SPIRAL, cs, (-3.4, 0.35), nums=False, arrow_col=C_GREY)
        b2 = Board(D.SPIRAL_CYC, cs, (3.4, 0.35), nums=False, arrow_col=C_GREY)
        self.play(FadeIn(b1.group), run_time=0.5)

        self.at("绕着中心")
        cells, stop, out = D.route(D.SPIRAL, D.SPIRAL_START)
        assert out and len(cells) == 9 == len(set(cells)) and D.solve(D.SPIRAL) == 9
        start = Dot(b1.pos(*cells[0]), radius=0.11, color=WHITE)
        r1 = self.route_line(b1, cells, stop, out)
        self.play(FadeIn(start), run_time=0.2)
        self.play(Create(r1), run_time=3.0, rate_func=linear)
        self.at("从左下角")
        t1 = VGroup(T(f"{len(cells)} 格各走一次，从左下角出界", 22, C_GREEN), T("拐来拐去，没有回头 → 能逃", 22, C_GREEN))
        t1.arrange(DOWN, buff=0.12).move_to([-3.4, -1.85, 0])
        self.play(FadeIn(t1, shift=UP * 0.15), *[c.animate.set_fill(C_GREEN, 0.35) for c in b1.cells.values()], run_time=0.6)

        self.at("改成向上")
        self.play(FadeIn(b2.group), run_time=0.5)
        corner = b2.cells[(2, 0)]
        self.play(Indicate(b2.arrows[(2, 0)], color=C_YELLOW, scale_factor=1.6), Indicate(corner, color=C_YELLOW), run_time=0.7)
        cells2, stop2, out2 = D.route(D.SPIRAL_CYC, D.SPIRAL_START)
        assert not out2 and stop2 == (1, 0) and cells2 == cells
        k0 = cells2.index(stop2)
        start2 = Dot(b2.pos(*cells2[0]), radius=0.11, color=WHITE)
        r2 = self.route_line(b2, cells2, stop2, out2, cyc_from=k0)
        self.play(FadeIn(start2), run_time=0.2)
        self.play(Create(r2), run_time=2.4, rate_func=linear)
        ring = Circle(0.42, color=C_RED, stroke_width=5).move_to(b2.pos(*stop2))
        self.play(Create(ring), run_time=0.4)
        self.at("九格全都")
        assert D.solve(D.SPIRAL_CYC) == 0
        t2 = VGroup(T("回到走过的格 → 每圈都一样", 22, C_RED), T(f"{len(cells2)} 格全部逃不出（答案 0）", 22, C_RED))
        t2.arrange(DOWN, buff=0.12).move_to([3.4, -1.85, 0])
        self.play(FadeIn(t2, shift=UP * 0.15), *[c.animate.set_fill(C_RED, 0.35) for c in b2.cells.values()], run_time=0.6)
        self.at("才叫成环")
        self.play(Indicate(t2[0], color=C_YELLOW), Indicate(t1[1], color=C_YELLOW), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 复杂度
    def cost_beat(self):
        self.beat("cost")
        g = D.SAMPLE2
        walks, st = D.trace(g)
        b = Board(g, 1.0, (-4.6, 0.3), nums=True)
        for (i, j), sq in b.cells.items():
            sq.set_fill(ST_COL[st[i * 3 + j]], FILL)
        h = self.head("每格只进一次 path")
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(b.group), run_time=0.7)
        self.at("每格只会")
        once = T("每格只标一次 1", 22, C_YELLOW).move_to([-4.6, -1.6, 0])
        self.play(FadeIn(once), LaggedStart(*[Indicate(c, color=C_YELLOW, scale_factor=1.05) for c in b.cells.values()],
                                            lag_ratio=0.08), run_time=1.2)

        self.at("每次出发")
        x0, y0, dy = -2.3, 2.0, 0.58
        rows = VGroup()
        for r, w in enumerate(walks):
            y = y0 - dy * r
            lab = M(f"s={w['sid']}", 20, C_GREY).move_to([x0 + 0.4, y, 0])
            boxes = VGroup()
            for k, u in enumerate(w["ids"]):
                sq = Square(0.44, stroke_color=ST_COL[w["res"]], stroke_width=2).set_fill(ST_COL[w["res"]], FILL)
                boxes.add(VGroup(sq, M(str(u), 18).move_to(sq)).move_to([x0 + 1.3 + 0.52 * k, y, 0]))
            hit = "界" if w["end"] == "out" else str(b.uid(*w["hit"]))
            ex = DashedVMobject(Square(0.44, stroke_color=C_GREY, stroke_width=2), num_dashes=12)
            exl = (T(hit, 16, C_GREY) if w["end"] == "out" else M(hit, 18, C_GREY)).move_to(ex)
            extra = VGroup(ex, exl).move_to([x0 + 1.3 + 0.52 * len(w["ids"]), y, 0])
            note = T({"out": "出界", "cycle": "成环", "join": "接上"}[w["end"]], 18, ST_COL[w["res"]]).move_to([x0 + 3.55, y, 0])
            rows.add(VGroup(lab, boxes, extra, note))
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.15) for r in rows], lag_ratio=0.3), run_time=2.2)
        side = VGroup(T("实线：path 上的格", 20), T("虚线：停下前多看的一格", 20, C_GREY)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        self.left_at(side, 2.35, 1.4)
        self.play(FadeIn(side), run_time=0.4)

        self.at("十五格")
        p = sum(len(w["path"]) for w in walks)
        tot = D.total_steps(walks)
        assert (p, len(walks), tot) == (9, 6, 15)
        s1 = self.left_at(VGroup(M(f"{p} + {len(walks)} = {tot}", 26, C_YELLOW), T("格", 24, C_YELLOW)).arrange(RIGHT, buff=0.12),
                          2.35, 0.2)
        self.play(FadeIn(s1, scale=1.1), run_time=0.5)
        self.at("两倍")
        s2 = self.left_at(M(f"≤ 2 × {p} = 2nm", 24), 2.35, -0.5)
        s3 = self.left_at(VGroup(T("总时间", 26), M("O(nm)", 28, C_GREEN)).arrange(RIGHT, buff=0.2), 2.35, -1.25)
        self.play(FadeIn(s2), run_time=0.4)
        self.play(FadeIn(s3, scale=1.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 递归为何会炸
    def recur_beat(self):
        self.beat("recur")
        h = self.head("递归写法（自拟对照）", C_RED)
        code = Code(code_string=D.REC_SRC, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 24})
        code.scale_to_fit_height(min(code.height, 4.9))
        if code.width > 6.0:
            code.scale_to_fit_width(6.0)
        code.move_to([-6.7 + code.width / 2, -0.15, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(code, shift=UP * 0.2), run_time=0.8)
        ln = code.code_lines
        k_call = D.REC_SRC.splitlines().index("    st[u] = go(i + di, j + dj)")
        hl = SurroundingRectangle(ln[k_call], color=C_YELLOW, buff=0.04, stroke_width=2)
        self.at("先问下一格")
        self.play(Create(hl), run_time=0.5)

        x0 = 0.6
        self.at("二十万个向右")
        strip = VGroup(*[M("R", 22, C_BLUE) for _ in range(10)], M("…", 22, C_BLUE), M("R", 22, C_BLUE)).arrange(RIGHT, buff=0.09)
        row = self.left_at(VGroup(strip, T("一行 2×10⁵ 个", 22, C_GREY)).arrange(RIGHT, buff=0.3), x0, 2.3)
        self.play(FadeIn(row, shift=LEFT * 0.2), run_time=0.5)

        self.at("深度二十万")
        frames = VGroup()
        labels = ["go(0, 0)", "go(0, 1)", "go(0, 2)", "go(0, 3)"]
        for k, s in enumerate(labels):
            r = Rectangle(width=2.3, height=0.36, stroke_color=C_GREY, stroke_width=2)
            frames.add(VGroup(r, M(s, 18).move_to(r)).move_to([x0 + 1.15, 1.6 - 0.42 * k, 0]))
        dots = M("⋮", 22, C_GREY).move_to([x0 + 1.15, -0.06, 0])
        r = Rectangle(width=2.3, height=0.36, stroke_color=C_RED, stroke_width=2)
        last = VGroup(r, M("go(0, 199999)", 18, C_RED).move_to(r)).move_to([x0 + 1.15, -0.5, 0])
        self.play(LaggedStart(*[FadeIn(f, shift=DOWN * 0.1) for f in frames], lag_ratio=0.3), run_time=1.0)
        self.play(FadeIn(dots), FadeIn(last), run_time=0.4)
        br = Brace(VGroup(frames, last), RIGHT, color=C_GREY)
        depth = T("深度 2×10⁵ 层", 22, C_RED).next_to(br, RIGHT, buff=0.12)
        self.play(GrowFromCenter(br), FadeIn(depth), run_time=0.5)

        self.at("上限约一千")
        lim = sys.getrecursionlimit()
        assert lim == 1000
        cap = self.left_at(T(f"Python 默认上限 sys.getrecursionlimit() = {lim}", 20, C_YELLOW), x0, -1.05)
        self.play(FadeIn(cap), run_time=0.4)
        self.at("九百个")
        ok = D.rec_outcome(D.REC_OK)
        bad = D.rec_outcome(D.REC_BAD)
        assert ok == str(D.REC_OK) and bad == "RecursionError"
        res1 = self.left_at(VGroup(T(f"一行 {D.REC_OK} 个 R", 22), M(f"→ {ok}", 22, C_GREEN), T("✓", 22, C_GREEN)).arrange(RIGHT, buff=0.18),
                            x0, -1.6)
        self.play(FadeIn(res1, shift=LEFT * 0.15), run_time=0.4)
        self.at("两千个")
        res2 = self.left_at(VGroup(T(f"一行 {D.REC_BAD} 个 R", 22), M(f"→ {bad}", 22, C_RED)).arrange(RIGHT, buff=0.18),
                            x0, -2.1)
        self.play(FadeIn(res2, shift=LEFT * 0.15), Indicate(last, color=C_RED), run_time=0.5)
        self.at("调用栈")
        same = self.left_at(T("path 列表 = 显式的调用栈，长度不受限", 22, C_GREEN), x0, -2.6)
        self.play(FadeIn(same, shift=UP * 0.15), run_time=0.5)
        self.at("同一个算法")
        self.play(Indicate(same, color=C_YELLOW, scale_factor=1.05), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 讲义代码对照
    def code_beat(self):
        self.beat("code")
        src = "\n".join(D.CODE)
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 24})
        code.scale_to_fit_height(5.75)
        if code.width > 7.4:
            code.scale_to_fit_width(7.4)
        code.move_to([-6.75 + code.width / 2, 0.15, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        assert len(ln) == len(D.CODE)
        tx = code.get_right()[0] + 0.3

        def mark(key, lines, txt, color):
            self.at(key)
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=color, buff=0.03, stroke_width=2)
            tag = T(txt, 22, color)
            tag.move_to([tx + tag.width / 2, hl.get_y(), 0])
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.5)
            return tag
        mk = D.CODE_MARKS
        mark("外层", mk["skip"], "已有结论：跳过", C_GREY)
        mark("出界得二", mk["out"], "出界 → 2 能逃", C_GREEN)
        mark("撞上一得三", mk["cyc"], "撞上 1 → 3 成环", C_RED)
        mark("照抄", mk["join"], "撞上 2/3 → 照抄", C_BLUE)
        mark("都不是", mk["step"], "标 1、进 path、挪一步", C_YELLOW)
        ft = mark("回填", mk["fill"], "回填结论", C_PURPLE)
        self.at("有几个二")
        pr = M("print(st.count(2))", 22, C_GREEN)
        pr.move_to([ft.get_right()[0] + 0.5 + pr.width / 2, ft.get_y(), 0])
        self.play(FadeIn(pr, shift=UP * 0.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        h = self.head("回顾", C_BLUE)
        g = D.SAMPLE2
        _, st = D.trace(g)
        b = Board(g, 0.95, (-4.4, -0.1), nums=False)
        for (i, j), sq in b.cells.items():
            sq.set_fill(ST_COL[st[i * 3 + j]], FILL)
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(b.group), run_time=0.6)
        items = [("每格一条", "每格一条出边：路线要么出界，要么成环", WHITE),
                 ("四种状态", "四种状态 0/1/2/3 + path 列表", C_YELLOW),
                 ("三种收尾", "三种收尾 → 回填，每格只走一次 O(nm)", C_GREEN),
                 ("用循环", "路线可能长 2×10⁵：用循环，别用递归", C_RED)]
        for k, (key, s, col) in enumerate(items):
            self.at(key)
            t = self.left_at(T(s, 24, col), -1.8, 1.5 - 0.85 * k)
            self.play(FadeIn(t, shift=LEFT * 0.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()
