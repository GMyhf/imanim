"""Dijkstra：带权的波纹（3B1B 风格）。BFS 片的续集。

由 make.py 驱动，时间轴约定见 cine.py。出堆 / 松弛 / 过期跳过事件来自 dijkstradata（讲义 dijkstra、
mountain_path 原样插桩；test_dijkstra.py 对撞 Floyd、Bellman-Ford、讲义输出与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dijkstradata as D  # noqa: E402
from cine import *  # noqa: E402,F403

GPOS = {0: (-5.6, 0.3), 1: (-3.6, 2.1), 2: (-3.6, -1.5), 3: (-1.6, 0.3)}
R = 0.38


def dcolor(d, dmax):
    return interpolate_color(ManimColor(C_BLUE), ManimColor(C_YELLOW), min(1.0, d / max(1, dmax)))


def num_tex(v, **kw):
    return MathTex(r"\infty" if v == D.INF else str(v), **kw)


class DijkstraLesson(Lesson):
    def construct(self):
        for b in ("title", "bfswrong", "idea", "code", "run", "result", "mountain", "traps", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 图
    def build_graph(self):
        nodes = {k: VGroup(Circle(R, stroke_color=WHITE, stroke_width=3), MathTex(str(k)).scale(0.85)).move_to([*p, 0])
                 for k, p in GPOS.items()}
        edges, wlabs = {}, {}
        for u, v, w in D.EDGES:
            a = Arrow(nodes[u].get_center(), nodes[v].get_center(), buff=R + 0.04, stroke_width=3, color=C_GREY,
                      tip_length=0.2, max_tip_length_to_length_ratio=0.15)
            edges[(u, v)] = a
            normal = normalize(rotate_vector(a.get_unit_vector(), PI / 2))
            wlabs[(u, v)] = MathTex(str(w), color=C_YELLOW).scale(0.75).move_to(a.get_center() + normal * 0.3)
        return nodes, edges, wlabs

    # ---------------------------------------------------------------- 片头：带权的波纹
    def title_beat(self):
        self.beat("title")
        n, edges, adj = D.title_graph()
        pos = {i: np.array([-5.4 + 1.8 * (i % D.TITLE_COLS), 1.5 - 1.25 * (i // D.TITLE_COLS) - 0.4, 0]) for i in range(n)}
        dots = {i: Dot(pos[i], radius=0.09, color=C_GREY) for i in range(n)}
        lines = {(u, v): Line(pos[u], pos[v], stroke_color=C_GREY, stroke_width=1 + 0.45 * w).set_stroke(opacity=0.45)
                 for u, v, w in edges}
        self.play(FadeIn(VGroup(*lines.values())), FadeIn(VGroup(*dots.values())), run_time=0.8)
        dist, ev = D.dijkstra_trace(n, adj, 0)
        dmax = max(dist)
        parent = {}
        for e in ev:
            if e[0] == "relax":
                parent[e[2]] = e[1]
        pops = [e for e in ev if e[0] == "pop"]
        step = max(0.12, min(0.3, (self.left() * 0.5) / len(pops)))
        for _, d, u in pops:
            anims = [dots[u].animate.set_color(dcolor(d, dmax)).scale(1.6)]
            if u in parent:
                key = (parent[u], u) if (parent[u], u) in lines else (u, parent[u])
                anims.append(lines[key].animate.set_stroke(dcolor(d, dmax), opacity=1))
            self.play(*anims, run_time=step)
        title = T("Dijkstra", 76).move_to([0, 0.3, 0])
        sub = T("带权的波纹", 36, C_YELLOW).next_to(title, DOWN, buff=0.25)
        back = BackgroundRectangle(VGroup(title, sub), color=BG, fill_opacity=0.85, buff=0.35)
        self.play(FadeIn(back), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*lines.values(), *dots.values(), back, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 广搜在带权图上算错
    def bfswrong_beat(self):
        self.beat("bfswrong")
        nodes, edges, wlabs = self.build_graph()
        self.nodes, self.edges, self.wlabs = nodes, edges, wlabs
        self.play(*[FadeIn(n) for n in nodes.values()], *[GrowArrow(a) for a in edges.values()],
                  *[FadeIn(w) for w in wlabs.values()], run_time=1.2)
        self.play(nodes[0][0].animate.set_stroke(C_GREEN, 4), run_time=0.4)
        self.wait_until(self.cue_start("广搜按步数", self.now))
        layer = RoundedRectangle(corner_radius=0.35, width=1.2, height=4.6, stroke_color=C_BLUE, stroke_width=2)
        layer.set_fill(C_BLUE, 0.06).move_to([-3.6, 0.3, 0])
        lab = T("广搜第 1 层", 22, C_BLUE).next_to(layer, DOWN, buff=0.12)
        self.play(FadeIn(layer), FadeIn(lab), run_time=0.8)
        wrong = MathTex(str(D.bfs_hops_cost()[1]), color=C_RED).scale(0.9).next_to(nodes[1], UP, buff=0.12)
        self.wait_until(self.cue_start("记下代价四", self.now))
        self.play(Indicate(edges[(0, 1)], color=C_RED), FadeIn(wrong, scale=1.5), run_time=1.0)
        self.wait_until(self.cue_start("可绕道", self.now))
        right = VGroup(T("绕道 2 号点：", 26), MathTex("1+2=3", color=C_GREEN)).arrange(RIGHT, buff=0.2)
        right.move_to([3.2, 1.0, 0])
        self.play(edges[(0, 2)].animate.set_color(C_GREEN), edges[(2, 1)].animate.set_color(C_GREEN),
                  FadeIn(right, shift=LEFT * 0.2), run_time=1.0)
        cross = Cross(wrong, stroke_color=C_RED, stroke_width=4)
        self.wait_until(self.cue_start("边权不同", self.now))
        note = T("边权不同，广搜会算错", 28, C_RED).move_to([3.2, -0.2, 0])
        self.play(Create(cross), FadeIn(note), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(layer, lab, wrong, cross, right, note)),
                  *[a.animate.set_color(C_GREY) for a in edges.values()], nodes[0][0].animate.set_stroke(WHITE, 3),
                  run_time=0.6)

    # ---------------------------------------------------------------- 队列 → 小根堆，松弛
    def idea_beat(self):
        self.beat("idea")
        swap = VGroup(Text("deque", font=MONO, font_size=30, color=C_GREY), MathTex(r"\Rightarrow"),
                      T("小根堆", 30, C_YELLOW), Text("heapq", font=MONO, font_size=30, color=C_YELLOW))
        swap.arrange(RIGHT, buff=0.3).move_to([2.9, 2.5, 0])
        self.play(FadeIn(swap[0]), run_time=0.4)
        self.play(Write(swap[1]), FadeIn(swap[2:], shift=LEFT * 0.2), run_time=1.0)
        self.wait_until(self.cue_start("每次取出", self.now))
        pick = T("每次取出当前距离最小的点", 26).move_to([2.9, 1.5, 0])
        self.play(FadeIn(pick, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("所谓松弛", self.now))
        rule = MathTex(r"\mathrm{dist}[u]+w", "<", r"\mathrm{dist}[v]").scale(0.9).move_to([2.9, 0.2, 0])
        then = MathTex(r"\Rightarrow\ \mathrm{dist}[v]=\mathrm{dist}[u]+w").scale(0.9).next_to(rule, DOWN, buff=0.3)
        then.set_color(C_GREEN)
        uv = VGroup(MathTex("u", color=C_BLUE).scale(0.7).next_to(self.nodes[2], DOWN, buff=0.12),
                    MathTex("v", color=C_BLUE).scale(0.7).next_to(self.nodes[1], LEFT, buff=0.12))
        self.play(Write(rule), FadeIn(uv), Indicate(self.edges[(2, 1)], color=C_YELLOW), run_time=1.2)
        self.wait_until(self.cue_start("更近，就更新", self.now))
        push = T("新距离压进堆", 24, C_YELLOW).next_to(then, DOWN, buff=0.3)
        self.play(FadeIn(then, shift=UP * 0.2), FadeIn(push), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(swap, pick, rule, then, uv, push)), run_time=0.6)

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="def dijkstra(n, adj, src):\n    INF = float('inf')\n    dist = [INF] * n\n"
                                "    dist[src] = 0\n    pq = [(0, src)]\n    while pq:\n"
                                "        d, u = heapq.heappop(pq)\n        if d > dist[u]:\n            continue\n"
                                "        for v, w in adj[u]:\n            nd = d + w\n            if nd < dist[v]:\n"
                                "                dist[v] = nd\n                heapq.heappush(pq, (nd, v))\n"
                                "    return dist\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 19})
        code.move_to([2.9, 0.3, 0])
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        ln = code.code_lines
        hls = VGroup()

        def mark(lines, key, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.04, stroke_width=2)
            self.play(Create(hl), run_time=0.6)
            hls.add(hl)
        mark([1, 2, 3, 4], "无穷大", C_BLUE)
        mark([6], "弹出一个点", C_YELLOW)
        mark([7, 8], "过期条目", C_RED)
        mark([9, 10, 11, 12, 13], "遍历邻居", C_GREEN)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, hls)), run_time=0.6)

    # ---------------------------------------------------------------- 跑一遍：堆、dist 表
    def chip(self, d, u, col=C_YELLOW):
        box = RoundedRectangle(corner_radius=0.1, width=1.1, height=0.55, stroke_color=col, stroke_width=2.5)
        return VGroup(box, MathTex(f"({d},{u})").scale(0.62).move_to(box))

    def run_beat(self):
        self.beat("run")
        nodes, edges = self.nodes, self.edges
        hhead = VGroup(T("小根堆", 24, C_YELLOW), Text("pq", font=MONO, font_size=22, color=C_GREY)).arrange(RIGHT, buff=0.2)
        hhead.move_to([0.75, 2.75, 0], aligned_edge=LEFT)
        slot = lambda k: np.array([1.35 + 1.3 * k, 2.05, 0])  # noqa: E731
        dhead = Text("dist", font=MONO, font_size=24, color=C_GREY).move_to([0.75, -0.6, 0], aligned_edge=LEFT)
        cells = VGroup(*[Square(0.8, stroke_color=C_GREY, stroke_width=2).move_to([2.3 + 1.0 * i, -0.6, 0])
                         for i in range(D.N)])
        idx = VGroup(*[MathTex(str(i), color=C_GREY).scale(0.5).next_to(c, DOWN, buff=0.12) for i, c in enumerate(cells)])
        vals = [num_tex(0 if i == 0 else D.INF).scale(0.7).move_to(cells[i]) for i in range(D.N)]
        out_lab = T("出堆", 22, C_GREY).move_to([0.95, 0.85, 0])
        heap = [((0, 0), self.chip(0, 0).move_to(slot(0)))]
        self.play(FadeIn(hhead), FadeIn(dhead), FadeIn(cells), FadeIn(idx), *[FadeIn(v) for v in vals],
                  FadeIn(heap[0][1]), FadeIn(out_lab), run_time=1.0)
        _, ev = D.dijkstra_trace()
        keys = ["弹出零号点", "弹出距离最小的二号点", "弹出一号点，距离三", "下一个弹出", "弹出三号点", "最后那个"]
        pops = [k for k, e in enumerate(ev) if e[0] in ("pop", "stale")]
        assert len(pops) == len(keys)
        out_pos = np.array([2.3, 0.85, 0])
        k_pop = 0
        cur = None
        for e in ev:
            if e[0] in ("pop", "stale"):
                self.wait_until(self.cue_start(keys[k_pop], self.now))
                k_pop += 1
                if cur is not None:
                    self.play(FadeOut(cur), run_time=0.2)
                (dd, uu), ch = heap.pop(0)
                anims = [ch.animate.move_to(out_pos)] + [c.animate.move_to(slot(i)) for i, (_, c) in enumerate(heap)]
                self.play(*anims, run_time=0.6)
                cur = ch
                if e[0] == "pop":
                    self.play(nodes[uu][0].animate.set_stroke(C_GREEN, 5), ch[0].animate.set_stroke(C_GREEN),
                              cells[uu].animate.set_stroke(C_GREEN, 3), run_time=0.5)
                else:
                    x = Cross(ch, stroke_color=C_RED, stroke_width=4)
                    tag = T("过期，跳过", 22, C_RED).next_to(ch, RIGHT, buff=0.25)
                    self.play(Create(x), FadeIn(tag), Indicate(vals[uu], color=C_RED), run_time=0.9)
                    self.wait(0.6)
                    self.play(FadeOut(x), FadeOut(tag), run_time=0.3)
            else:
                _, u, v, nd = e
                new = num_tex(nd, color=C_YELLOW).scale(0.7).move_to(cells[v])
                c = self.chip(nd, v).move_to(nodes[v])
                heap.append(((nd, v), c))
                heap.sort(key=lambda t: t[0])
                anims = [Indicate(edges[(u, v)], color=C_YELLOW), Transform(vals[v], new)]
                anims += [c2.animate.move_to(slot(i)) for i, (_, c2) in enumerate(heap) if c2 is not c]
                self.play(*anims, run_time=0.6)
                self.play(c.animate.move_to(slot(heap.index(((nd, v), c)))), run_time=0.5)
        if cur is not None:
            self.play(FadeOut(cur), run_time=0.3)
        self.wait(max(0.1, self.left() - 0.2))
        self.run_ui = VGroup(hhead, dhead, idx, out_lab)
        self.cells, self.vals = cells, vals

    # ---------------------------------------------------------------- 结果：第一次出堆才是最短
    def result_beat(self):
        self.beat("result")
        dist, _ = D.dijkstra_trace()
        box = SurroundingRectangle(self.cells, color=C_GREEN, buff=0.12)
        self.play(Create(box), *[Indicate(v, color=C_GREEN) for v in self.vals], run_time=1.2)
        self.wait_until(self.cue_start("第一次出堆时", self.now))
        key = T("第一次出堆，才是最短", 32, C_YELLOW).move_to([3.1, 1.6, 0])
        self.play(Write(key), Indicate(self.nodes[1], color=C_GREEN), run_time=1.2)
        self.wait_until(self.cue_start("广搜，其实", self.now))
        ones = [MathTex("1", color=C_YELLOW).scale(0.75).move_to(w) for w in self.wlabs.values()]
        eq = T("所有边权都为 1 → 就是 BFS", 26).move_to([3.1, -2.2, 0])
        self.play(*[Transform(w, o) for w, o in zip(self.wlabs.values(), ones)], FadeIn(eq), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*self.nodes.values(), *self.edges.values(), *self.wlabs.values(), self.run_ui,
                                 self.cells, *self.vals, box, key, eq)), run_time=0.6)

    # ---------------------------------------------------------------- 走山路
    def mountain_beat(self):
        self.beat("mountain")
        g = D.GRID
        n, m, cell = len(g), len(g[0]), 1.35
        c0 = np.array([-2.6, 0.2, 0])
        pos = {(i, j): c0 + np.array([(j - 1) * cell, (1 - i) * cell, 0]) for i in range(n) for j in range(m)}
        sq = {k: Square(cell * 0.72, stroke_color=C_GREY, stroke_width=2).move_to(p) for k, p in pos.items()}
        hs = {k: MathTex(str(g[k[0]][k[1]])).scale(0.95).move_to(p) for k, p in pos.items()}
        costs = VGroup()
        for (i, j) in pos:
            for di, dj in ((0, 1), (1, 0)):
                q = (i + di, j + dj)
                if q in pos:
                    c = abs(g[q[0]][q[1]] - g[i][j])
                    costs.add(MathTex(str(c), color=C_YELLOW).scale(0.55).move_to((pos[(i, j)] + pos[q]) / 2))
        sl = T("起", 22, C_GREEN).next_to(sq[D.START], LEFT, buff=0.15)
        gl = T("终", 22, C_RED).next_to(sq[D.GOAL], RIGHT, buff=0.15)
        self.play(*[FadeIn(s) for s in sq.values()], *[FadeIn(h) for h in hs.values()], FadeIn(sl), FadeIn(gl),
                  run_time=1.0)
        self.wait_until(self.cue_start("高度差的绝对值", self.now))
        rule = MathTex(r"\text{cost}=|h_1-h_2|", color=C_YELLOW).scale(0.85).move_to([3.4, 2.4, 0])
        self.play(FadeIn(costs), Write(rule), run_time=1.2)
        self.wait_until(self.cue_start("deque 换成 heapq", self.now))
        diff = VGroup(VGroup(Text("deque", font=MONO, font_size=24, color=C_GREY), MathTex(r"\to"),
                             Text("heapq", font=MONO, font_size=24, color=C_YELLOW)).arrange(RIGHT, buff=0.2),
                      VGroup(MathTex("+1", color=C_GREY), MathTex(r"\to"),
                             MathTex(r"+|\Delta h|", color=C_YELLOW)).arrange(RIGHT, buff=0.2))
        diff.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([3.4, 1.1, 0])
        self.play(FadeIn(diff, shift=LEFT * 0.2), run_time=0.8)
        ans, ev, _ = D.mountain_trace()
        dmax = ans
        tent = {}
        self.wait_until(self.cue_start("波纹按代价", self.now))
        t_goal = self.cue_start("终点出堆", self.now + 6)
        n_ev = len(ev)
        for k, e in enumerate(ev):
            rt = max(0.3, min(0.7, (t_goal - self.now) / max(1, n_ev - k)))
            if e[0] == "relax":
                _, u, v, nd = e
                lab = MathTex(str(nd), color=C_GREY).scale(0.42).move_to(sq[v].get_corner(UR) + np.array([-0.16, -0.15, 0]))
                anims = [FadeIn(lab, scale=1.4)]
                if v in tent:
                    anims.append(FadeOut(tent[v]))
                tent[v] = lab
                self.play(*anims, run_time=rt * 0.6)
            elif e[0] in ("pop", "goal"):
                if e[0] == "goal":
                    self.wait_until(t_goal)
                _, d, u = e
                col = dcolor(d, dmax)
                anims = [sq[u].animate.set_fill(col, 0.45).set_stroke(col, 3)]
                if u in tent:
                    anims.append(tent[u].animate.set_color(WHITE))
                self.play(*anims, run_time=rt)
        path, cost = D.mountain_path()
        line = VMobject(stroke_color=C_GREEN, stroke_width=6).set_points_as_corners([pos[c] for c in path])
        res = VGroup(T("最小代价", 28), MathTex(str(ans), color=C_YELLOW).scale(1.3)).arrange(RIGHT, buff=0.3)
        res.move_to([3.4, -0.6, 0])
        self.play(Flash(sq[D.GOAL], color=C_YELLOW, flash_radius=0.8), FadeIn(res, shift=UP * 0.2),
                  Create(line), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*sq.values(), *hs.values(), costs, sl, gl, rule, diff, *tent.values(), line, res)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 两个坑
    def traps_beat(self):
        self.beat("traps")
        cards = VGroup()
        for i, (head, body, col) in enumerate((("① 跳过过期条目", "if d > dist[u]: continue", C_YELLOW),
                                               ("② 不能有负权边", "负权用 Bellman-Ford", C_RED))):
            box = RoundedRectangle(corner_radius=0.2, width=5.6, height=2.0, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06)
            b = Text(body, font=MONO, font_size=24) if i == 0 else T(body, 26)
            cards.add(VGroup(box, VGroup(T(head, 30, col), b).arrange(DOWN, buff=0.3).move_to(box)))
        cards.arrange(RIGHT, buff=0.6).move_to([0, 0.4, 0])
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.8)
        note = T("漏了这句，复杂度退化", 22, C_GREY).next_to(cards[0], DOWN, buff=0.25)
        self.play(FadeIn(note), run_time=0.5)
        self.wait_until(self.cue_start("第二", self.now))
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cards, note)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(
            VGroup(T("队列", 32, C_GREY), MathTex(r"\to"), T("堆", 32, C_YELLOW)).arrange(RIGHT, buff=0.3),
            VGroup(T("步数", 32, C_GREY), MathTex(r"\to"), T("距离", 32, C_YELLOW)).arrange(RIGHT, buff=0.3),
        ).arrange(DOWN, buff=0.4).move_to([0, 1.4, 0])
        self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in rows], lag_ratio=0.4), run_time=1.4)
        self.wait_until(self.cue_start("第一次出堆", self.now))
        key = T("第一次出堆，就是最短", 40, C_YELLOW).move_to([0, -0.4, 0])
        self.play(Write(key), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 12 周 Dijkstra P17–P19 · OpenJudge M20106", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
