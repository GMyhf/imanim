"""最小生成树：一棵树和一片森林（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。Prim 每一步的候选跨界边、distance 更新，
Kruskal 每条边的取舍，都来自 mstdata（讲义 modern.py#prim / #kruskal 原样插桩；test_mst.py 枚举全部生成树对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mstdata as M  # noqa: E402
from cine import *  # noqa: E402,F403

GPOS = {0: (-5.8, 1.7), 1: (-3.3, 2.2), 2: (-0.9, 1.4), 3: (-3.0, 0.0),
        4: (-5.6, -1.4), 5: (-3.5, -2.1), 6: (-1.1, -1.2)}
R = 0.34
COMP = [C_BLUE, C_TEAL, C_YELLOW, C_RED, C_PURPLE, C_GREEN, "#E59A5B"]


def key(u, v):
    return (min(u, v), max(u, v))


def vlab(i, **kw):
    return MathTex(f"v_{i}", **kw)


class MSTLesson(Lesson):
    def construct(self):
        for b in ("title", "problem", "cut", "prim", "code", "kruskal", "same", "spt", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, k, default=None):
        return next((c["start"] for c in self.cue_times() if k in c["text"]), default)

    def at(self, k):
        self.wait_until(self.cue_start(k, self.now))

    def hold(self, tail=0.6):
        self.wait(max(0.1, self.left() - tail))

    # ---------------------------------------------------------------- 图
    def build_graph(self):
        nodes = {}
        for k, p in GPOS.items():
            c = Circle(R, stroke_color=WHITE, stroke_width=3).set_fill(BG, 0)
            nodes[k] = VGroup(c, vlab(k).scale(0.7)).move_to([*p, 0])
        edges, wl = {}, {}
        for u, v, w in M.EDGES:
            a, b = np.array([*GPOS[u], 0]), np.array([*GPOS[v], 0])
            d = normalize(b - a)
            ln = Line(a + d * (R + 0.03), b - d * (R + 0.03), stroke_color=C_GREY, stroke_width=3)
            edges[key(u, v)] = ln
            nrm = rotate_vector(d, PI / 2)
            if nrm[1] < 0 or (abs(nrm[1]) < 1e-6 and nrm[0] < 0):
                nrm = -nrm
            wl[key(u, v)] = MathTex(str(w), color=C_YELLOW).scale(0.68).move_to(ln.get_center() + nrm * 0.27)
        return nodes, edges, wl

    def reset_graph(self, rt=0.6):
        anims = [e.animate.set_stroke(C_GREY, 3, opacity=1) for e in self.edges.values()]
        anims += [n[0].animate.set_stroke(WHITE, 3).set_fill(BG, 0) for n in self.nodes.values()]
        anims += [w.animate.set_opacity(1) for w in self.wl.values()]
        self.play(*anims, run_time=rt)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        self.nodes, self.edges, self.wl = self.build_graph()
        nodes, edges, wl = self.nodes, self.edges, self.wl
        self.play(LaggedStart(*[GrowFromCenter(n) for n in nodes.values()], lag_ratio=0.1), run_time=1.2)
        self.play(*[Create(e) for e in edges.values()], *[FadeIn(w) for w in wl.values()], run_time=1.4)
        self.at("至少要六条线")
        tree, _ = M.prim_trace()
        tk = {key(e.source, e.target) for e in tree}
        self.play(*[edges[k].animate.set_stroke(C_GREEN, 6) for k in tk],
                  *[edges[k].animate.set_stroke(opacity=0.25) for k in edges if k not in tk],
                  *[wl[k].animate.set_opacity(0.3) for k in edges if k not in tk], run_time=1.4)
        self.at("这就是最小生成树")
        title = T("最小生成树", 64).move_to([3.4, 0.7, 0])
        sub = T("一棵树和一片森林", 32, C_YELLOW).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.hold()
        self.play(FadeOut(VGroup(title, sub)), run_time=0.4)
        self.reset_graph(0.3)

    # ---------------------------------------------------------------- 生成树：n-1 条边；随手连 60，最省 38
    def sum_tex(self, tree, col):
        ws = [str(w) for *_, w in tree]
        return MathTex("+".join(ws), "=", str(sum(w for *_, w in tree)), color=col).scale(0.85)

    def problem_beat(self):
        self.beat("problem")
        defn = VGroup(T("生成树", 32, C_GREEN),
                      T("· 包含全部顶点", 26), T("· 没有环", 26),
                      VGroup(T("· 恰好", 26), MathTex("n-1", color=C_YELLOW).scale(0.85), T("条边", 26)).arrange(RIGHT, buff=0.12))
        defn.arrange(DOWN, aligned_edge=LEFT, buff=0.22).move_to([3.0, 1.7, 0])
        self.play(FadeIn(defn, shift=LEFT * 0.2), run_time=1.0)
        self.at("随手连一棵")
        naive = {key(u, v) for u, v, _ in M.NAIVE}
        s1 = self.sum_tex(M.NAIVE, C_BLUE).move_to([3.0, -0.4, 0])
        self.play(*[self.edges[k].animate.set_stroke(C_BLUE, 6) for k in naive], run_time=0.9)
        self.play(Write(s1), run_time=0.9)
        self.at("最便宜的那棵")
        tree, _ = M.prim_trace()
        tk = {key(e.source, e.target) for e in tree}
        s2 = self.sum_tex([(e.source, e.target, e.weight) for e in tree], C_GREEN).move_to([3.0, -1.3, 0])
        self.play(*[self.edges[k].animate.set_stroke(C_GREEN if k in tk else C_GREY, 6 if k in tk else 3)
                    for k in self.edges], run_time=0.9)
        self.play(Write(s2), run_time=0.9)
        self.at("靠一条性质")
        self.play(Indicate(s2[2], color=C_GREEN, scale_factor=1.3), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(defn, s1, s2)), run_time=0.4)
        self.reset_graph(0.3)

    # ---------------------------------------------------------------- 切分性质与反证
    def cut_beat(self):
        self.beat("cut")
        U = M.CUT_U
        anims = [self.nodes[k][0].animate.set_fill(C_BLUE if k in U else C_YELLOW, 0.3)
                 .set_stroke(C_BLUE if k in U else C_YELLOW, 3) for k in self.nodes]
        labU = T("一堆", 24, C_BLUE).move_to([-6.15, -0.1, 0])
        labV = T("另一堆", 24, C_YELLOW).move_to([0.25, 0.15, 0])
        self.play(*anims, FadeIn(labU), FadeIn(labV), run_time=1.0)
        self.at("横跨两堆的边")
        cross = M.crossing(U)
        lu, lv, lw = M.light_crossing(U)
        self.play(*[self.edges[key(u, v)].animate.set_stroke(C_YELLOW, 5) for u, v, _ in cross], run_time=0.8)
        self.play(self.edges[key(lu, lv)].animate.set_stroke(C_GREEN, 7),
                  Indicate(self.wl[key(lu, lv)], color=C_GREEN, scale_factor=1.5), run_time=0.9)
        claim = VGroup(T("跨界最轻的边", 28, C_GREEN), T("一定能放进某棵最小生成树", 26)).arrange(DOWN, buff=0.15)
        claim.move_to([3.4, 2.3, 0])
        self.play(FadeIn(claim, shift=LEFT * 0.2), run_time=0.8)
        self.at("假设某棵")
        pt = {key(u, v) for u, v, _ in M.PROOF_T}
        self.play(*[self.edges[k].animate.set_stroke(C_BLUE if k in pt else C_GREY, 6 if k in pt else 2, opacity=1 if k in pt else 0.4)
                    for k in self.edges], run_time=1.0)
        tlab = VGroup(T("不含它的生成树", 24, C_BLUE), MathTex("=" + str(sum(w for *_, w in M.PROOF_T)), color=C_BLUE).scale(0.8))
        tlab.arrange(RIGHT, buff=0.15).move_to([3.4, 0.9, 0])
        self.play(FadeIn(tlab), run_time=0.6)
        self.at("把它加进去")
        path = M.tree_path([M.Edge(*e) for e in M.PROOF_T], lu, lv)
        cyc = [key(a, b) for a, b in zip(path, path[1:])]
        self.play(self.edges[key(lu, lv)].animate.set_stroke(C_GREEN, 7, opacity=1), run_time=0.6)
        self.play(*[Indicate(self.edges[k], color=C_PURPLE, scale_factor=1.0) for k in cyc],
                  *[self.edges[k].animate.set_stroke(C_PURPLE, 6) for k in cyc], run_time=1.0)
        ring = T("成环", 26, C_PURPLE).move_to([-1.6, 0.7, 0])
        self.play(FadeIn(ring), run_time=0.4)
        self.at("环上另有一条")
        other = next(k for k in cyc if (k[0] in U) != (k[1] in U))
        self.play(self.edges[other].animate.set_stroke(C_RED, 7), Indicate(self.wl[other], color=C_RED, scale_factor=1.5),
                  run_time=0.9)
        self.at("删掉那一条")
        ow = next(w for u, v, w in M.EDGES if key(u, v) == other)
        cmp_ = MathTex(f"{lw}", r"\le", f"{ow}").scale(0.9).move_to([3.4, -0.1, 0])
        cmp_[0].set_color(C_GREEN)
        cmp_[2].set_color(C_RED)
        new_total = sum(w for *_, w in M.PROOF_T) - ow + lw
        after = VGroup(T("换完总权", 24), MathTex(str(new_total), color=C_GREEN).scale(0.9)).arrange(RIGHT, buff=0.15)
        after.move_to([3.4, -1.0, 0])
        self.play(FadeOut(self.edges[other]), FadeOut(self.wl[other]), FadeIn(cmp_), run_time=0.9)
        newt = {k for k in pt if k != other} | {key(lu, lv)}
        self.play(*[self.edges[k].animate.set_stroke(C_GREEN, 6) for k in newt], FadeOut(ring), FadeIn(after), run_time=0.9)
        self.hold()
        self.play(FadeOut(VGroup(claim, tlab, cmp_, after, labU, labV)), FadeIn(self.edges[other]),
                  FadeIn(self.wl[other]), run_time=0.4)
        self.reset_graph(0.3)

    # ---------------------------------------------------------------- Prim：一棵树往外长
    def prim_beat(self):
        self.beat("prim")
        head = T("Prim：始终一棵树", 28, C_GREEN).move_to([3.5, 2.85, 0])
        xs = [0.95 + 0.86 * i for i in range(M.N)]
        hdr = VGroup(*[vlab(i, color=C_GREY).scale(0.62).move_to([x, 2.05, 0]) for i, x in enumerate(xs)])
        boxes = VGroup(*[Square(0.72, stroke_color=C_GREY, stroke_width=2).move_to([x, 1.4, 0]) for x in xs])
        cap = T("distance：到当前树的最近边", 20, C_GREY).move_to([3.5, 0.75, 0])

        def num(v, col=WHITE):
            return MathTex(r"\infty" if v == M.INF else ("0" if v == 0 else str(v)), color=col).scale(0.62)
        vals = [num(M.INF).move_to(b) for b in boxes]
        self.play(FadeIn(head), FadeIn(hdr), FadeIn(boxes), FadeIn(cap), *[FadeIn(v) for v in vals], run_time=0.9)
        tree, ev = M.prim_trace()
        keys = [None, "先取权为一", "只能取十五", "接着取十", "然后取二", "再取六", "最后取四"]
        inside, total, parts = set(), 0, []
        tot = MathTex("0", color=C_GREEN).scale(0.85)
        tot_lab = T("总权", 24, C_GREEN)
        tot_g = VGroup(tot_lab, tot).arrange(RIGHT, buff=0.2).move_to([3.5, -0.4, 0])
        steps = None
        self.play(FadeIn(tot_g), run_time=0.4)
        cand_keys = set()
        k_pick = 0
        for e in ev:
            if e[0] == "pick":
                _, v, te, _ = e
                if keys[k_pick]:
                    self.at(keys[k_pick])
                k_pick += 1
                if te is not None:
                    kk = key(te.source, te.target)
                    total += te.weight
                    parts.append(str(te.weight))
                    new_tot = MathTex(str(total), color=C_GREEN).scale(0.85).move_to(tot, aligned_edge=LEFT)
                    new_steps = MathTex("+".join(parts), color=C_GREEN).scale(0.75).move_to([3.5, -1.2, 0])
                    self.play(*[self.edges[c].animate.set_stroke(C_GREY, 3) for c in cand_keys if c != kk],
                              self.edges[kk].animate.set_stroke(C_GREEN, 7),
                              Indicate(self.wl[kk], color=C_GREEN, scale_factor=1.4), run_time=0.7)
                    self.play(self.nodes[v][0].animate.set_fill(C_GREEN, 0.3).set_stroke(C_GREEN, 4),
                              Transform(vals[v], MathTex(r"\checkmark", color=C_GREEN).scale(0.7).move_to(boxes[v])),
                              boxes[v].animate.set_stroke(C_GREEN, 3),
                              Transform(tot, new_tot),
                              FadeIn(new_steps) if steps is None else Transform(steps, new_steps), run_time=0.6)
                    if steps is None:
                        steps = new_steps
                else:
                    self.play(self.nodes[v][0].animate.set_fill(C_GREEN, 0.3).set_stroke(C_GREEN, 4),
                              Transform(vals[v], MathTex(r"\checkmark", color=C_GREEN).scale(0.7).move_to(boxes[v])),
                              boxes[v].animate.set_stroke(C_GREEN, 3), run_time=0.6)
                inside.add(v)
                cand_keys = {key(a, b) for a, b, _ in M.crossing(inside)}
                if len(inside) < M.N:
                    self.play(*[self.edges[c].animate.set_stroke(C_YELLOW, 5) for c in cand_keys], run_time=0.5)
            else:
                _, t, old, new, frm = e
                self.play(Transform(vals[t], num(new, C_YELLOW).move_to(boxes[t])), run_time=0.35)
        self.at("六步，六条边")
        self.play(Indicate(tot, color=C_GREEN, scale_factor=1.4), run_time=0.8)
        self.hold()
        self.prim_ui = VGroup(head, hdr, boxes, cap, *vals, tot_g, steps)
        self.play(FadeOut(self.prim_ui), run_time=0.5)

    # ---------------------------------------------------------------- 代码：和 Dijkstra 只差一处
    def code_beat(self):
        self.beat("code")
        src = ("def prim(n, w):\n    INF = float('inf')\n    dist = [INF] * n\n    used = [False] * n\n"
               "    dist[0] = 0\n    total = 0\n    for _ in range(n):\n"
               "        u = min((v for v in range(n) if not used[v]),\n                key=lambda v: dist[v])\n"
               "        used[u] = True\n        total += dist[u]\n        for v in range(n):\n"
               "            if not used[v] and w[u][v] < dist[v]:\n                dist[v] = w[u][v]\n"
               "    return total\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 15})
        code.move_to([3.7, 1.05, 0])
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        ln = code.code_lines
        self.at("距离数组")
        h1 = SurroundingRectangle(ln[2], color=C_BLUE, buff=0.04, stroke_width=2)
        self.play(Create(h1), run_time=0.5)
        self.at("每并入一个点")
        h2 = SurroundingRectangle(VGroup(ln[7], ln[8], ln[9]), color=C_GREEN, buff=0.04, stroke_width=2)
        h3 = SurroundingRectangle(VGroup(ln[12], ln[13]), color=C_YELLOW, buff=0.04, stroke_width=2)
        self.play(Create(h2), run_time=0.5)
        self.play(Create(h3), run_time=0.5)
        self.at("只差一处")
        dj = VGroup(T("Dijkstra", 22, C_GREY),
                    MathTex(r"d[u]+w(u,v)", "<", r"d[v]").scale(0.7)).arrange(RIGHT, buff=0.25)
        pr = VGroup(T("Prim", 22, C_YELLOW),
                    MathTex(r"w(u,v)", "<", r"d[v]", color=C_YELLOW).scale(0.7)).arrange(RIGHT, buff=0.25)
        cmpg = VGroup(dj, pr).arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to([3.4, -2.05, 0])
        self.play(FadeIn(dj, shift=UP * 0.15), run_time=0.6)
        self.at("普里姆比的")
        self.play(FadeIn(pr, shift=UP * 0.15), run_time=0.6)
        self.at("用邻接矩阵")
        cx = VGroup(MathTex("O(n^2)", color=C_GREEN).scale(0.8), T("稠密图", 24, C_GREEN)).arrange(RIGHT, buff=0.2)
        cx.move_to([-0.9, 2.85, 0])
        self.play(FadeIn(cx), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(code, h1, h2, h3, cmpg, cx)), run_time=0.5)

    # ---------------------------------------------------------------- Kruskal：一片森林
    def kruskal_beat(self):
        self.beat("kruskal")
        self.reset_graph(0.5)
        head = T("Kruskal：先是一片森林", 28, C_PURPLE).move_to([3.5, 2.85, 0])
        self.play(FadeIn(head), *[n[0].animate.set_fill(COMP[k], 0.3).set_stroke(COMP[k], 3)
                                  for k, n in self.nodes.items()], run_time=0.8)
        self.at("按权从小到大")
        order = M.sorted_edges()
        rows = VGroup()
        for i, e in enumerate(order):
            y = 2.15 - 0.5 * i
            r = VGroup(MathTex(f"v_{e.source}", "-", f"v_{e.target}").scale(0.62).move_to([2.2, y, 0]),
                       MathTex(str(e.weight), color=C_YELLOW).scale(0.66).move_to([3.4, y, 0]))
            rows.add(r)
        self.play(LaggedStart(*[TransformFromCopy(self.wl[key(e.source, e.target)], rows[i][1]) for i, e in enumerate(order)],
                              lag_ratio=0.08), LaggedStart(*[FadeIn(r[0]) for r in rows], lag_ratio=0.08), run_time=1.6)
        self.at("并查集")
        dsu = VGroup(T("并查集：", 22, C_GREY), MathTex(r"\mathrm{find}(u)=\mathrm{find}(v)", r"\Rightarrow", color=C_GREY).scale(0.62),
                     T("成环", 22, C_RED)).arrange(RIGHT, buff=0.12).move_to([3.6, -2.55, 0])
        self.play(FadeIn(dsu), run_time=0.6)
        comp = {k: k for k in self.nodes}
        taken, marks = [], VGroup()
        keys = {0: "一、二、四、六", 4: "八，三号点", 5: "十，收下", 6: "十二，又成环", 7: "十五，收下", 8: "最后的二十"}
        _, ev = M.kruskal_trace()
        ptr = Triangle(color=WHITE, fill_opacity=1).scale(0.09).rotate(-PI / 2)
        for i, (act, e) in enumerate(ev):
            if i in keys:
                self.at(keys[i])
            k = key(e.source, e.target)
            pos = rows[i].get_left() + LEFT * 0.25
            if i == 0:
                ptr.move_to(pos)
                self.play(FadeIn(ptr), run_time=0.2)
            else:
                self.play(ptr.animate.move_to(pos), run_time=0.2)
            if act == "take":
                a, b = comp[e.source], comp[e.target]
                members = [x for x in comp if comp[x] == a]
                for x in members:
                    comp[x] = b
                mark = MathTex(r"\checkmark", color=C_GREEN).scale(0.6).move_to([4.2, rows[i].get_y(), 0])
                self.play(self.edges[k].animate.set_stroke(C_GREEN, 7), FadeIn(mark),
                          rows[i].animate.set_color(C_GREEN),
                          *[self.nodes[x][0].animate.set_fill(COMP[b], 0.3).set_stroke(COMP[b], 3) for x in members],
                          run_time=0.55)
                taken.append(e)
            else:
                path = M.tree_path(taken, e.source, e.target)
                cyc = [key(a, b) for a, b in zip(path, path[1:])]
                mark = VGroup(MathTex(r"\times", color=C_RED).scale(0.7), T("成环", 18, C_RED)).arrange(RIGHT, buff=0.08)
                mark.move_to([4.5, rows[i].get_y(), 0])
                self.play(self.edges[k].animate.set_stroke(C_RED, 5),
                          *[Indicate(self.edges[c], color=C_RED, scale_factor=1.0) for c in cyc],
                          FadeIn(mark), run_time=0.9)
                self.play(self.edges[k].animate.set_stroke(C_GREY, 2, opacity=0.35),
                          rows[i].animate.set_opacity(0.45), run_time=0.4)
            marks.add(mark)
        self.hold()
        self.kr_ui = VGroup(head, rows, marks, dsu, ptr)
        self.order = order

    # ---------------------------------------------------------------- 两种算法同一棵树
    def same_beat(self):
        self.beat("same")
        self.play(FadeOut(self.kr_ui), run_time=0.5)
        tree, _ = M.prim_trace()
        po = MathTex(*[str(e.weight) + (r",\," if i < 5 else "") for i, e in enumerate(tree)]).scale(0.8)
        ko = MathTex(*[str(e.weight) + (r",\," if i < 5 else "") for i, e in enumerate(M.kruskal_trace()[0])]).scale(0.8)
        lp = T("Prim", 26, C_GREEN)
        lk = T("Kruskal", 26, C_PURPLE)
        rp = VGroup(lp, po, MathTex("=38", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.25)
        rk = VGroup(lk, ko, MathTex("=38", color=C_PURPLE).scale(0.8)).arrange(RIGHT, buff=0.25)
        rows = VGroup(rp, rk).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to([3.3, 2.2, 0])
        self.play(FadeIn(rp, shift=LEFT * 0.2), run_time=0.6)
        self.play(FadeIn(rk, shift=LEFT * 0.2), *[n[0].animate.set_fill(C_GREEN, 0.3).set_stroke(C_GREEN, 3)
                                                  for n in self.nodes.values()], run_time=0.6)
        self.at("中间过程")
        hdr = VGroup(T("Prim", 24, C_GREEN), T("Kruskal", 24, C_PURPLE))
        cells = [("一棵树", "一片森林"), (r"O(n^2)", r"O(e\log e)"), ("稠密图", "稀疏图")]
        names = ["中间过程", "时间", "适合"]
        y0 = 0.7
        hdr[0].move_to([3.1, y0, 0])
        hdr[1].move_to([5.2, y0, 0])
        tab = VGroup(hdr)
        for r, (nm, (a, b)) in enumerate(zip(names, cells)):
            y = y0 - 0.65 * (r + 1)
            mk = (lambda s, c: MathTex(s, color=c).scale(0.72)) if r == 1 else (lambda s, c: T(s, 24, c))
            tab.add(VGroup(T(nm, 22, C_GREY).move_to([1.2, y, 0]), mk(a, WHITE).move_to([3.1, y, 0]),
                           mk(b, WHITE).move_to([5.2, y, 0])))
        self.play(FadeIn(hdr), FadeIn(tab[1]), run_time=0.7)
        self.at("边集可能不同")
        note = T("等权边 → 边集可不同，总权必相同", 22, C_YELLOW).move_to([3.3, -2.45, 0])
        self.play(FadeIn(note), run_time=0.6)
        self.at("普里姆适合稠密图")
        self.play(FadeIn(tab[2]), FadeIn(tab[3]), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(rows, tab, note, *self.nodes.values(), *self.edges.values(), *self.wl.values())),
                  run_time=0.6)

    # ---------------------------------------------------------------- 最短路树 ≠ 最小生成树
    def triangle(self, cx, keep, col):
        pos = {0: np.array([cx, 1.6, 0]), 1: np.array([cx - 1.9, -1.0, 0]), 2: np.array([cx + 1.9, -1.0, 0])}
        names = "ABC"
        nodes = {i: VGroup(Circle(0.36, stroke_color=WHITE, stroke_width=3), T(names[i], 28)).move_to(p)
                 for i, p in pos.items()}
        eds, labs = {}, {}
        for u, v, w in M.TRI:
            d = normalize(pos[v] - pos[u])
            ln = Line(pos[u] + d * 0.4, pos[v] - d * 0.4, stroke_width=3, color=C_GREY)
            nrm = rotate_vector(d, PI / 2)
            if nrm[1] < 0:
                nrm = -nrm
            if abs(nrm[1]) < 1e-6:
                nrm = DOWN
            eds[key(u, v)] = ln
            labs[key(u, v)] = MathTex(str(w), color=C_YELLOW).scale(0.8).move_to(ln.get_center() + nrm * 0.32)
        g = VGroup(*eds.values(), *labs.values(), *nodes.values())
        return g, eds, labs, nodes

    def spt_beat(self):
        self.beat("spt")
        self.at("三个点")
        g1, e1, l1, n1 = self.triangle(-3.4, None, C_BLUE)
        g2, e2, l2, n2 = self.triangle(3.4, None, C_GREEN)
        self.play(FadeIn(g1), FadeIn(g2), run_time=1.0)
        self.at("从 A 出发")
        sp, dist = M.spt(3, M.TRI)
        cap1 = T("最短路树", 28, C_BLUE).move_to([-3.4, 2.6, 0])
        dl = VGroup(*[MathTex(f"d={dist[i]}", color=C_BLUE).scale(0.65).next_to(n1[i], DOWN, buff=0.15) for i in (1, 2)])
        self.play(FadeIn(cap1), n1[0][0].animate.set_stroke(C_BLUE, 4), run_time=0.6)
        self.play(*[e1[key(u, v)].animate.set_stroke(C_BLUE, 7) for u, v, _ in sp], FadeIn(dl), run_time=1.0)
        s1 = MathTex("+".join(str(w) for *_, w in sp), "=", str(sum(w for *_, w in sp)), color=C_BLUE).scale(0.85)
        s1.move_to([-3.4, -2.2, 0])
        self.play(Write(s1), run_time=0.8)
        self.at("最小生成树选")
        mst, _ = M.kruskal_trace(3, M.TRI)
        cap2 = T("最小生成树", 28, C_GREEN).move_to([3.4, 2.6, 0])
        s2 = MathTex("+".join(str(e.weight) for e in mst), "=", str(M.weight(mst)), color=C_GREEN).scale(0.85)
        s2.move_to([3.4, -2.2, 0])
        self.play(FadeIn(cap2), *[e2[key(e.source, e.target)].animate.set_stroke(C_GREEN, 7) for e in mst], run_time=1.0)
        self.play(Write(s2), run_time=0.8)
        self.at("目标不同")
        neq = MathTex(r"\neq", color=C_RED).scale(1.6).move_to([0, 0.3, 0])
        self.play(FadeIn(neq, scale=1.5), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(g1, g2, cap1, cap2, dl, s1, s2, neq)), run_time=0.6)

    # ---------------------------------------------------------------- 小结
    def recap_beat(self):
        self.beat("recap")
        top = VGroup(T("切分性质", 36, C_YELLOW), T("跨界最轻的边，放心选", 24, C_GREY)).arrange(DOWN, buff=0.15)
        top.move_to([0, 2.0, 0])
        left = VGroup(T("Prim", 34, C_GREEN), T("从点出发，长一棵树", 24)).arrange(DOWN, buff=0.15).move_to([-3.2, -0.1, 0])
        right = VGroup(T("Kruskal", 34, C_PURPLE), T("从边出发，并查集判环", 24)).arrange(DOWN, buff=0.15).move_to([3.2, -0.1, 0])
        a1 = Arrow(top.get_bottom(), left.get_top(), buff=0.2, color=C_GREY, stroke_width=3)
        a2 = Arrow(top.get_bottom(), right.get_top(), buff=0.2, color=C_GREY, stroke_width=3)
        self.play(FadeIn(top, shift=DOWN * 0.2), run_time=0.8)
        self.at("普里姆从点出发")
        self.play(GrowArrow(a1), FadeIn(left), run_time=0.8)
        self.play(GrowArrow(a2), FadeIn(right), run_time=0.8)
        self.at("走的路不同")
        bottom = T("总权一定相同", 32, C_GREEN).move_to([0, -1.9, 0])
        self.play(FadeIn(bottom, shift=UP * 0.2), run_time=0.8)
        self.hold(0.8)
        self.play(FadeOut(VGroup(top, left, right, a1, a2, bottom)), run_time=0.8)
