"""Bellman-Ford：负权边与负环（3B1B 风格）。cs101 Dijkstra 片与 cs201 Floyd 片之间的一环。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。Dijkstra 的错误答案、每轮松弛成功的边、
dp[k][v] 表、负环三轮的 dist 与第 n 轮检查、SPFA 的入队出队全部来自 bforddata（讲义 bellman_ford 原样插桩；
test_bford.py 用穷举简单路径、讲义原版函数与 SPFA 对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bforddata as D  # noqa: E402
from cine import *  # noqa: E402,F403

INF = D.INF
GPOS = {0: (-5.9, 0.2), 1: (-4.0, 2.0), 2: (-4.0, -1.6), 3: (-2.1, 0.2)}
R = 0.36
WOFF = {(0, 1): (-0.32, 0.3), (0, 2): (-0.32, -0.3), (2, 1): (0.38, 0.0), (1, 3): (0.32, 0.3), (3, 2): (0.34, -0.3)}
DOFF = {0: (-0.72, 0), 1: (0, 0.62), 2: (0, -0.62), 3: (0.72, 0)}
BF_CODE = (
    "def bellman_ford(n, edges, source):\n"
    "    INF = float('inf')\n"
    "    dist = [INF] * n\n"
    "    dist[source] = 0\n"
    "    for _ in range(n - 1):\n"
    "        changed = False\n"
    "        for u, v, w in edges:\n"
    "            if dist[u] != INF and dist[u] + w < dist[v]:\n"
    "                dist[v] = dist[u] + w\n"
    "                changed = True\n"
    "        if not changed:\n"
    "            break\n"
    "    for u, v, w in edges:\n"
    "        if dist[u] != INF and dist[u] + w < dist[v]:\n"
    "            return None\n"
    "    return dist")


def val_tex(v, color=C_YELLOW, s=0.75):
    return MathTex(r"\infty" if v == INF else str(int(v)), color=color).scale(s)


def edge_tex(u, v, w, s=0.7, color=WHITE):
    return MathTex(rf"\langle {u},{v}\rangle", rf"\;{{{w}}}", color=color).scale(s)


class Table(VGroup):
    """小表格：行标签 + 四个 dist 值，按行追加。列中心 xs，行高 dy。"""

    def __init__(self, x0, y0, head, xs, dy=0.62, s=0.62):
        super().__init__()
        self.x0, self.y0, self.xs, self.dy, self.s = x0, y0, xs, dy, s
        self.head = VGroup(*[(MathTex(h, color=C_GREY).scale(s) if h.isascii() else T(h, 22, C_GREY)).move_to([x, y0, 0])
                             for h, x in zip(head, [x0, *xs])])
        self.line = Line([x0 - 0.35, y0 - dy / 2, 0], [xs[-1] + 0.35, y0 - dy / 2, 0], stroke_color=C_GREY, stroke_width=1.5)
        self.add(self.head, self.line)
        self.rows = []

    def row(self, label, vals, color=WHITE, lab_color=C_GREY):
        y = self.y0 - self.dy * (len(self.rows) + 1)
        lab = (MathTex(label, color=lab_color) if label.isascii() else T(label, 22, lab_color)).scale(1).move_to([self.x0, y, 0])
        if isinstance(lab, MathTex):
            lab.scale(self.s)
        cells = VGroup(*[val_tex(v, color, self.s).move_to([x, y, 0]) for v, x in zip(vals, self.xs)])
        r = VGroup(lab, cells)
        self.rows.append(r)
        self.add(r)
        return r


class BFordLesson(Lesson):
    def construct(self):
        for b in ("title", "wrong", "shift", "idea", "rounds", "order", "why", "negcycle", "spfa"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key):
        for c in self.cue_times():
            if key in c["text"]:
                k = c["text"].index(key)
                self.wait_until(c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"])))
                return
        raise KeyError(key)

    def hold(self, tail=0.6):
        self.wait(max(0.1, self.left() - tail))

    # ---------------------------------------------------------------- 图
    def build_graph(self):
        self.nodes = {k: VGroup(Circle(R, stroke_color=WHITE, stroke_width=3).set_fill(BG, 0),
                                MathTex(str(k)).scale(0.8)).move_to([*p, 0]) for k, p in GPOS.items()}
        self.arrows, self.wlabs = {}, {}
        for u, v, w in D.EDGES:
            self.add_edge(u, v, w)
        self.dlabs = {k: val_tex(INF).move_to(self.dpos(k)) for k in GPOS}

    def add_edge(self, u, v, w, color=C_GREY):
        a = Arrow(self.nodes[u].get_center(), self.nodes[v].get_center(), buff=R + 0.04, stroke_width=3, color=color,
                  tip_length=0.2, max_tip_length_to_length_ratio=0.15)
        lab = MathTex(str(w), color=C_RED if w < 0 else C_YELLOW).scale(0.72)
        lab.move_to(a.get_center() + np.array([*WOFF[(u, v)], 0]))
        self.arrows[(u, v)], self.wlabs[(u, v)] = a, lab
        return a, lab

    def dpos(self, k):
        return self.nodes[k].get_center() + np.array([*DOFF[k], 0])

    def set_dist(self, k, v, color=C_YELLOW):
        return Transform(self.dlabs[k], val_tex(v, color).move_to(self.dpos(k)))

    def reset_dists(self):
        return [self.set_dist(k, 0 if k == 0 else INF) for k in GPOS]

    def path_edges(self, path):
        return [self.arrows[(a, b)] for a, b in zip(path, path[1:])]

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        self.build_graph()
        self.play(*[FadeIn(n) for n in self.nodes.values()], *[GrowArrow(a) for a in self.arrows.values()],
                  *[FadeIn(w) for w in self.wlabs.values()], run_time=1.2)
        rule = VGroup(T("迪杰斯特拉的前提", 28, C_GREY), MathTex(r"w \ge 0", color=C_GREEN).scale(1.0)).arrange(RIGHT, buff=0.3)
        rule.move_to([2.6, 2.0, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        self.at("它每次把")
        fixed = T("当前最近 = 永久最近", 28).move_to([2.6, 1.1, 0])
        self.play(FadeIn(fixed, shift=UP * 0.2), run_time=0.7)
        self.at("可一旦")
        self.play(Indicate(self.wlabs[(2, 1)], color=C_RED, scale_factor=1.6),
                  self.arrows[(2, 1)].animate.set_color(C_RED), run_time=1.0)
        cross = Line(fixed.get_left() + LEFT * 0.1, fixed.get_right() + RIGHT * 0.1, stroke_color=C_RED, stroke_width=5)
        self.play(Create(cross), run_time=0.5)
        self.at("这一集")
        title = Text("Bellman-Ford", font=FONT, font_size=64).move_to([2.6, -0.5, 0])
        sub = T("负权边与负环", 34, C_YELLOW).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.hold()
        self.play(FadeOut(VGroup(rule, fixed, cross, title, sub)), self.arrows[(2, 1)].animate.set_color(C_GREY),
                  run_time=0.6)

    # ---------------------------------------------------------------- Dijkstra 在负权上算错
    def wrong_beat(self):
        self.beat("wrong")
        self.at("零到一是四")
        for e, key in (((0, 1), "零到一是四"), ((0, 2), "零到二是五"), ((2, 1), "二到一是负三"), ((1, 3), "一到三是二")):
            self.at(key)
            self.play(Indicate(self.wlabs[e], scale_factor=1.5), self.arrows[e].animate.set_color(WHITE), run_time=0.6)
        self.play(*[a.animate.set_color(C_GREY) for a in self.arrows.values()], run_time=0.3)
        D_, order = D.dijkstra_S()
        self.dlabs[0] = val_tex(0).move_to(self.dpos(0))
        self.play(FadeIn(self.dlabs[0]), run_time=0.3)
        self.at("迪杰斯特拉先选出")
        lock = T("进入 S 即定死", 24, C_GREEN).move_to([2.6, 2.6, 0])
        self.play(FadeIn(lock), run_time=0.4)
        for u, d in order:
            anims = [self.nodes[u][0].animate.set_stroke(C_GREEN, 4).set_fill(C_GREEN, 0.18)]
            if u != 0:
                lab = val_tex(d).move_to(self.dpos(u))
                self.dlabs[u] = lab
                anims.append(FadeIn(lab, scale=1.4))
            if u == 3:
                self.at("再用它算出")
                anims.append(Indicate(self.arrows[(1, 3)], color=C_YELLOW))
            self.play(*anims, run_time=0.7)
        tbl = Table(0.6, 1.6, ["顶点", "Dijkstra", "真实最短"], [2.5, 4.5], dy=0.7, s=0.7)
        tbl.head[1].become(Text("Dijkstra", font=FONT, font_size=22, color=C_GREY).move_to(tbl.head[1]))
        truth = D.shortest_paths_brute(D.N, D.EDGES)
        r1 = tbl.row("1", [D_[1], truth[1][0]])
        r3 = tbl.row("3", [D_[3], truth[3][0]])
        for r in (r1, r3):
            r[1][1].set_opacity(0)
        self.play(FadeIn(tbl.head), Create(tbl.line), FadeIn(r1[0]), FadeIn(r1[1][0]), FadeIn(r3[0]), FadeIn(r3[1][0]),
                  run_time=0.7)
        self.at("可是先到二号点")
        p1 = self.path_edges(truth[1][1])
        calc = MathTex("5+(-3)=2", color=C_GREEN).scale(0.8).move_to([2.6, -0.6, 0])
        self.play(*[a.animate.set_color(C_GREEN) for a in p1], FadeIn(calc), run_time=0.6)
        self.at("到一号点只要二")
        self.play(r1[1][1].animate.set_opacity(1).set_color(C_GREEN), run_time=0.4)
        self.at("到三号点")
        self.play(self.arrows[(1, 3)].animate.set_color(C_GREEN), r3[1][1].animate.set_opacity(1).set_color(C_GREEN),
                  run_time=0.5)
        self.at("两个答案都错了")
        crosses = VGroup(*[Line(r[1][0].get_left() + LEFT * 0.12, r[1][0].get_right() + RIGHT * 0.12,
                                stroke_color=C_RED, stroke_width=4) for r in (r1, r3)])
        self.play(r1[1][0].animate.set_color(C_RED), r3[1][0].animate.set_color(C_RED), Create(crosses), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(tbl, crosses, calc, lock, *[self.dlabs[k] for k in GPOS])),
                  *[a.animate.set_color(C_GREY) for a in self.arrows.values()],
                  *[self.nodes[k][0].animate.set_stroke(WHITE, 3).set_fill(BG, 0) for k in GPOS], run_time=0.6)

    # ---------------------------------------------------------------- 统一加常数为什么不行
    def shift_beat(self):
        self.beat("shift")
        plus = T(f"每条边都 +{D.SHIFT}", 30, C_PURPLE).move_to([2.6, 2.4, 0])
        self.play(FadeIn(plus, shift=UP * 0.2), run_time=0.6)
        old = {e: lab.copy() for e, lab in self.wlabs.items()}
        new = {(u, v): MathTex(str(w), color=C_PURPLE).scale(0.72).move_to(self.wlabs[(u, v)])
               for u, v, w in D.shifted()}
        self.play(*[Transform(self.wlabs[e], new[e]) for e in new], run_time=1.0)
        self.at("边数多的路径")
        why = VGroup(T("直走 1 条边：+3", 26), T("绕道 2 条边：+6", 26)).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        why.move_to([2.6, 1.1, 0])
        self.play(FadeIn(why, shift=UP * 0.2), run_time=0.8)
        self.at("零到一直走是七")
        sh = D.shortest_paths_brute(D.N, D.shifted())
        direct = MathTex(r"0\to1:\ 7", color=C_PURPLE).scale(0.8).move_to([1.6, -0.3, 0])
        detour = MathTex(r"0\to2\to1:\ 8+0=8", color=C_GREY).scale(0.8).move_to([2.6, -1.1, 0])
        direct.align_to(detour, LEFT)
        self.play(self.arrows[(0, 1)].animate.set_color(C_PURPLE), FadeIn(direct), run_time=0.7)
        self.at("绕道是八")
        self.play(FadeIn(detour), *[a.animate.set_color(C_GREY) for a in self.path_edges([0, 2, 1])], run_time=0.6)
        self.at("最短路变成了")
        assert sh[1][1] == [0, 1]
        verdict = T("最短路换了一条，答案变了", 28, C_RED).move_to([2.6, -2.1, 0])
        self.play(Indicate(direct, color=C_PURPLE), FadeIn(verdict, shift=UP * 0.2), run_time=0.9)
        self.hold()
        self.play(FadeOut(VGroup(plus, why, direct, detour, verdict)),
                  *[Transform(self.wlabs[e], old[e]) for e in old], self.arrows[(0, 1)].animate.set_color(C_GREY),
                  run_time=0.6)

    # ---------------------------------------------------------------- 思路 + 讲义代码
    def idea_beat(self):
        self.beat("idea")
        head = T("每一轮：所有边按顺序松弛一遍", 28, C_YELLOW).move_to([2.9, 3.1, 0])
        code = Code(code_string=BF_CODE, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 18})
        code.scale_to_fit_width(6.6)
        if code.height > 4.9:
            code.scale_to_fit_height(4.9)
        code.move_to([3.15, -0.45, 0])
        ln = code.code_lines
        self.play(FadeIn(head, shift=UP * 0.2), FadeIn(code, shift=LEFT * 0.3), run_time=0.9)
        hl = SurroundingRectangle(VGroup(ln[6], ln[7], ln[8]), color=C_YELLOW, buff=0.04, stroke_width=2)
        self.play(Create(hl), *[Indicate(a, color=C_YELLOW, scale_factor=1.0) for a in self.arrows.values()], run_time=1.0)
        self.at("理由是")
        self.play(hl.animate.become(SurroundingRectangle(ln[4], color=C_GREEN, buff=0.04, stroke_width=2)), run_time=0.6)
        self.at("最多经过")
        simple = T("最短路是简单路径：至多 V−1 条边", 24, C_GREEN).move_to([2.9, 2.45, 0])
        self.play(FadeIn(simple, shift=UP * 0.15), run_time=0.7)
        self.at("四个点")
        cnt = T("4 个点 ⇒ 至多 3 轮", 30, C_YELLOW).move_to(head)
        self.play(Transform(head, cnt), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(head, code, hl, simple)), run_time=0.6)

    # ---------------------------------------------------------------- 按讲义边序跑
    def edge_list(self, edges, title="边序"):
        cap = T(title, 24, C_GREY).move_to([0.3, 2.6, 0])
        items = VGroup(*[edge_tex(u, v, w, 0.72, C_RED if w < 0 else WHITE) for u, v, w in edges])
        for i, it in enumerate(items):
            it.move_to([0.3, 1.9 - 0.65 * i, 0])
        return cap, items

    def sweep(self, items, edges, ok_set, cursor, step=0.45, on_ok=None):
        for i, (u, v, w) in enumerate(edges):
            self.play(cursor.animate.next_to(items[i], LEFT, buff=0.15), run_time=step * 0.5)
            if (u, v) in ok_set:
                new = ok_set[(u, v)]
                self.play(items[i].animate.set_color(C_GREEN), self.arrows[(u, v)].animate.set_color(C_YELLOW),
                          self.set_dist(v, new), run_time=step)
                self.play(self.arrows[(u, v)].animate.set_color(C_GREY), run_time=step * 0.4)
            else:
                self.play(Indicate(items[i], color=C_GREY, scale_factor=1.0), run_time=step * 0.5)

    def rounds_beat(self):
        self.beat("rounds")
        cap, items = self.edge_list(D.EDGES)
        self.items, self.cap = items, cap
        for k in GPOS:
            self.dlabs[k] = val_tex(0 if k == 0 else INF).move_to(self.dpos(k))
        tbl = Table(2.4, 2.6, ["轮", "d_0", "d_1", "d_2", "d_3"], [3.4, 4.3, 5.2, 6.1], dy=0.65, s=0.68)
        r0 = tbl.row("初", [0, INF, INF, INF])
        self.tbl = tbl
        self.play(FadeIn(cap), FadeIn(items), *[FadeIn(self.dlabs[k]) for k in GPOS], FadeIn(tbl.head),
                  Create(tbl.line), FadeIn(r0), run_time=0.9)
        cursor = Triangle(color=C_YELLOW, fill_opacity=1).scale(0.1).rotate(-PI / 2).next_to(items[0], LEFT, buff=0.15)
        self.cursor = cursor
        rounds, _, res = D.bf_trace()
        keys = ["第一轮", "第二轮", "第三轮"]
        for r, (rd, key) in enumerate(zip(rounds, keys)):
            self.at(key)
            self.play(FadeIn(cursor) if r == 0 else items.animate.set_color(WHITE), run_time=0.3)
            ok = {(u, v): new for u, v, w, old, new in rd["ok"]}
            step = 0.5 if r == 0 else 0.35
            self.sweep(items, D.EDGES, ok, cursor, step=step)
            row = tbl.row(str(r + 1), rd["dist"])
            self.play(FadeIn(row, shift=DOWN * 0.1), run_time=0.4)
        done = T("一整轮没改动 → 提前结束", 24, C_GREEN).move_to([4.75, -0.65, 0])
        self.play(FadeIn(done), run_time=0.5)
        self.at("答案是")
        final = tbl.rows[-1][1]
        self.play(final.animate.set_color(C_GREEN), *[self.set_dist(k, res[k], C_GREEN) for k in GPOS], run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(done, cursor)), items.animate.set_color(WHITE), run_time=0.5)

    # ---------------------------------------------------------------- 边序决定轮数
    def order_beat(self):
        self.beat("order")
        items, tbl = self.items, self.tbl
        hl = SurroundingRectangle(VGroup(items[2], items[3]), color=C_YELLOW, buff=0.1, stroke_width=2)
        note = VGroup(T("用的还是旧的", 22, C_YELLOW), MathTex("d_1=4", color=C_YELLOW).scale(0.65)).arrange(RIGHT, buff=0.12)
        note.next_to(hl, DOWN, buff=0.15)
        self.play(Create(hl), FadeIn(note), Indicate(tbl.rows[1][1][3], color=C_YELLOW), run_time=0.9)
        self.at("把二到一排到前面")
        self.play(FadeOut(note), FadeOut(hl), run_time=0.3)
        y2, y3 = items[2].get_y(), items[3].get_y()
        self.play(items[2].animate.set_y(y3), items[3].animate.set_y(y2), run_time=0.8)
        items.submobjects[2], items.submobjects[3] = items.submobjects[3], items.submobjects[2]
        rows_old = VGroup(*[r for r in tbl.rows[1:]])
        self.play(FadeOut(rows_old), *self.reset_dists(), run_time=0.5)
        tbl.remove(*rows_old)
        tbl.rows = tbl.rows[:1]
        rounds, _, _ = D.bf_trace(edges=D.REORDER)
        ok = {(u, v): new for u, v, w, old, new in rounds[0]["ok"]}
        self.cursor.next_to(items[0], LEFT, buff=0.15)
        self.play(FadeIn(self.cursor), run_time=0.2)
        self.sweep(items, D.REORDER, ok, self.cursor, step=0.3)
        row = tbl.row("1", rounds[0]["dist"], C_GREEN)
        good = T("一轮就全对", 24, C_GREEN).move_to([4.75, 0.45, 0])
        self.play(FadeIn(row), FadeIn(good), run_time=0.5)
        self.at("轮数随边序变化")
        bound = T("轮数随边序变；上界始终是 V−1", 26, C_YELLOW).move_to([3.5, -1.0, 0])
        self.play(FadeIn(bound, shift=UP * 0.2), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(self.cap, items, tbl, good, bound, self.cursor)), run_time=0.6)

    # ---------------------------------------------------------------- 为什么 V−1 轮够：dp[k][v]
    def why_beat(self):
        self.beat("why")
        self.play(*self.reset_dists(), run_time=0.4)
        self.at("换个角度看")
        claim = MathTex(r"\text{dist}_k[v]", r"\le", r"\text{dp}[k][v]", color=WHITE).scale(0.85).move_to([2.9, 3.05, 0])
        claim[2].set_color(C_BLUE)
        expl = T("dp[k][v]：至多 k 条边到 v 的最短长", 22, C_BLUE).move_to([2.9, 2.45, 0])
        self.play(Write(claim), FadeIn(expl), run_time=1.0)
        xs_l = [0.4, 1.0, 1.6, 2.2]
        xs_r = [3.9, 4.5, 5.1, 5.7]
        y0 = 1.75
        hl = T("第 k 轮后", 20, C_GREY).move_to([1.3, y0, 0])
        hr = T("dp[k]", 20, C_BLUE).move_to([4.8, y0, 0])
        kh = MathTex("k", color=C_GREY).scale(0.65).move_to([-0.35, y0, 0])
        line = Line([-0.6, y0 - 0.3, 0], [6.0, y0 - 0.3, 0], stroke_color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(VGroup(hl, hr, kh)), Create(line), run_time=0.5)
        dp = D.dp_table()
        paths = D.dp_paths()
        rounds, _, _ = D.bf_trace()
        bf_rows = [[0, INF, INF, INF]] + [r["dist"] for r in rounds]
        keys = ["零条边", "一条边到得了", "两条边", "三条边"]
        prev = []
        for k in range(4):
            self.at(keys[k])
            y = y0 - 0.6 * (k + 1)
            lab = MathTex(str(k), color=C_GREY).scale(0.65).move_to([-0.35, y, 0])
            left = VGroup(*[val_tex(v, WHITE, 0.62).move_to([x, y, 0]) for v, x in zip(bf_rows[k], xs_l)])
            le = MathTex(r"\le", color=C_GREY).scale(0.7).move_to([3.05, y, 0])
            right = VGroup(*[val_tex(v, C_BLUE, 0.62).move_to([x, y, 0]) for v, x in zip(dp[k], xs_r)])
            es = set()
            for p in paths[k]:
                if p:
                    es |= set(zip(p, p[1:]))
            anims = [self.arrows[e].animate.set_color(C_BLUE) for e in es]
            anims += [a.animate.set_color(C_GREY) for e, a in self.arrows.items() if e not in es and e in prev]
            anims += [self.set_dist(v, dp[k][v], C_BLUE) for v in GPOS]
            self.play(FadeIn(VGroup(lab, left, le, right), shift=DOWN * 0.1), *anims, run_time=0.8)
            prev = es
        self.at("最短路有几条边")
        last = VGroup(MathTex(r"0\to2\to1\to3", color=C_GREEN).scale(0.75), T("3 条边 → 第 3 轮前定下", 24, C_GREEN))
        last.arrange(RIGHT, buff=0.3).move_to([2.9, -1.35, 0])
        self.play(*[a.animate.set_color(C_GREEN) for a in self.path_edges([0, 2, 1, 3])], FadeIn(last, shift=UP * 0.15),
                  run_time=0.8)
        self.hold()
        self.play(FadeOut(Group(*[m for m in self.mobjects if m not in self.subs and m not in self.graph_parts()])),
                  *[a.animate.set_color(C_GREY) for a in self.arrows.values()], run_time=0.6)

    def graph_parts(self):
        return [*self.nodes.values(), *self.arrows.values(), *self.wlabs.values(), *self.dlabs.values()]

    # ---------------------------------------------------------------- 负环
    def negcycle_beat(self):
        self.beat("negcycle")
        self.play(*self.reset_dists(), run_time=0.4)
        u, v, w = D.NEG_EDGE
        a, lab = self.add_edge(u, v, w, C_RED)
        self.play(GrowArrow(a), FadeIn(lab, scale=1.4), run_time=0.9)
        self.at("二到一到三")
        cyc = [(2, 1), (1, 3), (3, 2)]
        self.play(*[self.arrows[e].animate.set_color(C_RED) for e in cyc], run_time=0.7)
        s = MathTex(r"-3+2-4=-5", color=C_RED).scale(0.85).move_to([2.9, 2.7, 0])
        self.play(Write(s), run_time=0.8)
        self.at("每绕一圈")
        lap = T("每绕一圈，距离再少 5", 26, C_RED).move_to([2.9, 2.05, 0])
        self.play(FadeIn(lap, shift=UP * 0.15), run_time=0.6)
        edges = D.EDGES + [D.NEG_EDGE]
        rounds, check, res = D.bf_trace(edges=edges)
        assert res is None
        tbl = Table(0.9, 1.3, ["轮", "d_0", "d_1", "d_2", "d_3"], [1.9, 2.8, 3.7, 4.6], dy=0.55, s=0.64)
        r0 = tbl.row("初", [0, INF, INF, INF])
        self.play(FadeIn(tbl.head), Create(tbl.line), FadeIn(r0), run_time=0.5)
        self.at("跑满三轮")
        for i, rd in enumerate(rounds):
            row = tbl.row(str(i + 1), rd["dist"])
            self.play(FadeIn(row, shift=DOWN * 0.1), *[self.set_dist(k, rd["dist"][k]) for k in GPOS], run_time=0.7)
        self.at("第四轮检查")
        bad = VGroup(*[self.arrows[(x, y)] for x, y, _ in check])
        chk = T("第 4 轮检查：仍可松弛", 24, C_RED).move_to([2.9, -1.55, 0])
        ret = VGroup(T("⇒ 有负环，返回", 24, C_RED), Text("None", font=MONO, font_size=24, color=C_RED)).arrange(RIGHT, buff=0.15)
        ret.move_to([2.9, -2.2, 0])
        self.play(FadeIn(chk), *[Indicate(b, color=C_YELLOW, scale_factor=1.0) for b in bad], run_time=1.0)
        self.at("就说明有负环")
        self.play(FadeIn(ret, shift=UP * 0.15), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(s, lap, tbl, chk, ret, self.arrows.pop((3, 2)), self.wlabs.pop((3, 2)))),
                  *[self.arrows[e].animate.set_color(C_GREY) for e in [(2, 1), (1, 3)]], *self.reset_dists(),
                  run_time=0.7)

    # ---------------------------------------------------------------- 队列优化 + 三种最短路对比
    def spfa_beat(self):
        self.beat("spfa")
        waste = T("每轮扫全部 m 条边", 26, C_GREY).move_to([2.9, 2.8, 0])
        self.play(FadeIn(waste), run_time=0.5)
        self.at("队列优化")
        idea = T("只有 dist 刚变小的点，才再看它的出边", 24, C_YELLOW).move_to([2.9, 2.2, 0])
        qcap = T("队列", 22, C_GREY).move_to([0.0, 1.2, 0])
        self.play(FadeIn(idea, shift=UP * 0.15), FadeIn(qcap), run_time=0.6)
        dist, checks, pushes, ev = D.spfa()
        cells = []          # 队列里的格子（从头到尾）
        x0, cw = 0.8, 0.62

        def cell(v):
            return VGroup(Square(0.52, stroke_color=C_BLUE, stroke_width=2), MathTex(str(v)).scale(0.65))

        step = 0.28
        for e in ev:
            if e[0] == "push":
                c = cell(e[1]).move_to([x0 + cw * len(cells), 1.2, 0])
                cells.append(c)
                self.play(FadeIn(c, shift=LEFT * 0.2), run_time=step)
            elif e[0] == "pop":
                c = cells.pop(0)
                self.play(FadeOut(c, shift=UP * 0.3), Indicate(self.nodes[e[1]], color=C_BLUE),
                          *[x.animate.shift(LEFT * cw) for x in cells], run_time=step * 1.2)
            else:
                _, u, v, nv = e
                self.play(self.arrows[(u, v)].animate.set_color(C_YELLOW), self.set_dist(v, nv), run_time=step)
                self.play(self.arrows[(u, v)].animate.set_color(C_GREY), run_time=step * 0.4)
        self.at("讲义的写法一共")
        rounds, _, _ = D.bf_trace()
        n_bf = D.edge_checks(rounds, len(D.EDGES))
        cmp = VGroup(VGroup(T("检查边：讲义写法", 24), MathTex(str(n_bf), color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.2),
                     VGroup(T("检查边：队列版", 24), MathTex(str(checks), color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.2))
        cmp.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([2.9, 0.0, 0])
        self.play(FadeIn(cmp[0]), run_time=0.5)
        self.at("队列版只检查")
        self.play(FadeIn(cmp[1]), run_time=0.5)
        self.at("不过最坏情况")
        worst = VGroup(T("最坏仍是", 24, C_GREY), MathTex(r"O(VE)", color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.2)
        worst.move_to([2.9, -1.2, 0])
        self.play(FadeIn(worst), run_time=0.5)
        self.at("三种最短路")
        self.play(FadeOut(VGroup(waste, idea, qcap, cmp, worst, *cells)), run_time=0.5)
        rows = [("Dijkstra", "贪心", False, r"O(E\log V)"),
                ("Bellman-Ford", "动态规划", True, r"O(VE)"),
                ("Floyd", "动态规划", True, r"O(V^3)")]
        xs = [0.55, 2.55, 3.95, 5.6]
        head = VGroup(*[T(h, 22, C_GREY).move_to([x, 2.5, 0]) for h, x in zip(["算法", "思想", "负权边", "时间"], xs)])
        hline = Line([-0.6, 2.2, 0], [6.8, 2.2, 0], stroke_color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(head), Create(hline), run_time=0.5)
        keys = ["迪杰斯特拉靠贪心", "贝尔曼-福特和", "负权也能算"]
        for i, (name, how, neg, t) in enumerate(rows):
            y = 1.6 - 0.75 * i
            r = VGroup(Text(name, font=FONT, font_size=24).move_to([xs[0], y, 0]),
                       T(how, 24, C_YELLOW if how == "贪心" else C_BLUE).move_to([xs[1], y, 0]),
                       MathTex(r"\checkmark" if neg else r"\times", color=C_GREEN if neg else C_RED).scale(0.8).move_to([xs[2], y, 0]),
                       MathTex(t).scale(0.7).move_to([xs[3], y, 0]))
            if i < 2:
                self.at(keys[i])
            self.play(FadeIn(r, shift=UP * 0.1), run_time=0.6)
        self.hold(0.3)
