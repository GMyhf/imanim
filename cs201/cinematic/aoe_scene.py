"""关键路径：一天也拖不得的活动（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。正向出队与 ve 更新、反向 vl 更新、
每个活动的 e / l / 机动时间、拖延与缩短后的工期，都来自 aoedata（讲义 critical_path 原样插桩；
test_aoe.py 对撞讲义 console、穷举路径、按定义逐天拖延求机动时间、随机 DAG）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aoedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

POS = {0: (-5.7, 0.3), 1: (-2.9, 1.9), 2: (-2.9, -1.9), 3: (0.1, 0.6), 4: (0.1, 2.75), 5: (3.0, 0.3)}
R = 0.4
C_VE, C_VL, C_CRIT = C_TEAL, C_PURPLE, C_RED
PANEL_X = 5.35


def p(i):
    return np.array([*POS[i], 0])


def make_node(i):
    c = Circle(R, stroke_color=WHITE, stroke_width=3).set_fill(BG, 0)
    return VGroup(c, MathTex(str(i)).scale(0.85)).move_to(p(i))


def make_edge(u, v, color=C_GREY, width=3):
    d = (p(v) - p(u)) / np.linalg.norm(p(v) - p(u))
    return Arrow(p(u) + R * d, p(v) - R * d, buff=0, stroke_width=width, color=color, tip_length=0.2,
                 max_tip_length_to_length_ratio=0.2, max_stroke_width_to_length_ratio=12)


def weight_pos(u, v, side=1):
    d = (p(v) - p(u)) / np.linalg.norm(p(v) - p(u))
    n = np.array([-d[1], d[0], 0]) * side
    return (p(u) + p(v)) / 2 + 0.3 * n


# 权值标在边的哪一侧（避开别的边和结点标签）
SIDE = {(0, 1): 1, (0, 2): -1, (1, 3): -1, (1, 4): 1, (2, 3): 1, (2, 5): -1, (3, 5): 1, (4, 5): 1}


def badge(val, col):
    box = RoundedRectangle(corner_radius=0.08, width=0.56, height=0.4, stroke_color=col, stroke_width=2).set_fill(BG, 0)
    num = Integer(val, color=col).scale(0.62).move_to(box)
    return VGroup(box, num)


class AOELesson(Lesson):
    def construct(self):
        for b in ("title", "net", "longest", "ve", "vl", "slack", "share", "shorten", "code", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key, default=None):
        for c in self.cue_times():
            if key in c["text"]:
                k = c["text"].index(key)
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return self.now if default is None else default

    def wait_key(self, key, extra=0.0):
        self.wait_until(self.at(key) + extra)

    def hold(self, keep=0.6):
        self.wait(max(0.1, self.left() - keep))

    # ---------------------------------------------------------------- 片头：甘特图
    def title_beat(self):
        self.beat("title")
        x0, dx = -6.0, 1.0
        rows = sorted(D.ACTS, key=lambda a: (a["e"], a["u"], a["v"]))
        bars = VGroup()
        for k, a in enumerate(rows):
            y = 0.9 - 0.42 * k
            r_ = Rectangle(width=a["w"] * dx, height=0.3, stroke_width=0).set_fill(C_BLUE, 0.75)
            r_.move_to([x0 + (a["e"] + a["w"] / 2) * dx, y, 0])
            bars.add(r_)
        axis = NumberLine(x_range=[0, 8, 1], length=8 * dx, include_numbers=True, font_size=24,
                          color=C_GREY).move_to([x0 + 4 * dx, -2.6, 0])
        self.play(Create(axis), run_time=0.6)
        self.play(LaggedStart(*[GrowFromEdge(b, LEFT) for b in bars], lag_ratio=0.15), run_time=2.0)
        self.wait_key("有的必须等别的做完")
        self.play(*[b.animate.set_fill(C_GREY, 0.6) for b in bars], run_time=0.5)
        q1 = T("最少要多久？", 30, C_YELLOW).move_to([4.6, 0.6, 0])
        q2 = T("哪些活动不能拖？", 30, C_RED).move_to([4.6, -0.3, 0])
        self.wait_key("整个工程最少要多久")
        self.play(FadeIn(q1, shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("哪些活动一拖延")
        crit = [k for k, a in enumerate(rows) if a["slack"] == 0]
        self.play(FadeIn(q2, shift=LEFT * 0.2), *[bars[k].animate.set_fill(C_RED, 0.85) for k in crit], run_time=0.8)
        title = T("关键路径", 66).move_to([0, 2.65, 0])
        self.wait_key("这一集")
        self.play(Write(title), run_time=1.0)
        self.hold()
        self.play(FadeOut(VGroup(bars, axis, q1, q2, title)), run_time=0.6)

    # ---------------------------------------------------------------- AOE 网
    def net_beat(self):
        self.beat("net")
        self.nodes = {i: make_node(i) for i in range(D.N)}
        self.edges = {(u, v): make_edge(u, v) for u, v, _ in D.EDGES}
        self.wlab = {(u, v): MathTex(str(w), color=WHITE).scale(0.75).move_to(weight_pos(u, v, SIDE[(u, v)]))
                     for u, v, w in D.EDGES}
        self.play(LaggedStart(*[FadeIn(self.nodes[i], scale=0.6) for i in range(D.N)], lag_ratio=0.1), run_time=1.2)
        self.wait_key("边是活动")
        self.play(*[GrowArrow(a) for a in self.edges.values()], run_time=1.0)
        self.play(*[FadeIn(t) for t in self.wlab.values()], run_time=0.7)
        self.wait_key("点是事件")
        self.play(*[Indicate(self.nodes[i], color=C_YELLOW) for i in range(D.N)], run_time=1.0)
        self.wait_key("零是开工")
        self.start_lab = T("开工", 22, C_GREEN).next_to(self.nodes[0], DOWN, buff=0.15)
        self.end_lab = T("完工", 22, C_GREEN).next_to(self.nodes[5], DOWN, buff=0.15)
        self.play(FadeIn(self.start_lab), run_time=0.5)
        self.wait_key("五是完工")
        self.play(FadeIn(self.end_lab), run_time=0.5)
        self.wait_key("必须是有向无环图")
        dag = T("有向无环图", 26, C_BLUE).move_to([PANEL_X, 2.6, 0])
        self.play(FadeIn(dag, shift=UP * 0.2), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(dag, self.start_lab, self.end_lab)), run_time=0.5)

    def path_edges(self, path):
        return [(path[i], path[i + 1]) for i in range(len(path) - 1)]

    # ---------------------------------------------------------------- 四条路，最长的定工期
    def longest_beat(self):
        self.beat("longest")
        order = D.PATHS                                    # DFS 枚举次序：0135 0145 0235 025，与旁白一致
        keys = ["零一三五", "零一四五", "零二三五", "零二五"]
        rows = VGroup()
        for k, (path, L) in enumerate(order):
            self.wait_key(keys[k])
            es = self.path_edges(path)
            txt = MathTex(r"\to".join(map(str, path)) + f"={L}", color=WHITE).scale(0.72)
            rows.add(txt)
            rows.arrange(DOWN, buff=0.28, aligned_edge=LEFT).move_to([PANEL_X, 1.0, 0])
            self.play(*[self.edges[e].animate.set_color(C_YELLOW).set_stroke(width=5) for e in es], FadeIn(txt),
                      run_time=0.6)
            self.wait(0.5)
            self.play(*[self.edges[e].animate.set_color(C_GREY).set_stroke(width=3) for e in es], run_time=0.35)
        best = max(range(len(order)), key=lambda k: order[k][1])
        self.wait_key("最长的那条决定工期")
        es = self.path_edges(order[best][0])
        self.play(*[self.edges[e].animate.set_color(C_CRIT).set_stroke(width=6) for e in es],
                  rows[best].animate.set_color(C_CRIT), run_time=0.8)
        self.total_lab = VGroup(T("工期", 28), Integer(D.TOTAL, color=C_YELLOW).scale(0.95)).arrange(RIGHT, buff=0.2)
        self.total_lab.move_to([PANEL_X, -2.65, 0])
        self.play(FadeIn(self.total_lab, shift=UP * 0.2), run_time=0.6)
        self.wait_key("叫关键路径")
        cp = T("关键路径", 26, C_CRIT).move_to([PANEL_X, -1.6, 0])
        self.play(FadeIn(cp), *[Indicate(self.edges[e], color=C_CRIT) for e in es], run_time=0.9)
        self.hold()
        self.play(FadeOut(VGroup(rows, cp)), *[self.edges[e].animate.set_color(C_GREY).set_stroke(width=3) for e in es],
                  run_time=0.6)

    # ---------------------------------------------------------------- 正向：ve 取最大
    def ve_beat(self):
        self.beat("ve")
        self.ve = {i: badge(0, C_VE).next_to(self.nodes[i], UP, buff=0.1) for i in range(D.N)}
        cap = VGroup(T("最早发生时间", 22, C_VE), T("取最大", 22, C_VE)).arrange(DOWN, buff=0.1).move_to([PANEL_X, 2.6, 0])
        orow = VGroup(T("出队", 20, C_GREY)).move_to([PANEL_X, 1.6, 0])
        self.play(FadeIn(cap), FadeIn(orow), *[FadeIn(b) for b in self.ve.values()], run_time=0.8)
        ring = Circle(R + 0.1, stroke_color=C_YELLOW, stroke_width=4).move_to(self.nodes[0])
        fwd = dict(D.TR["fwd"])
        keys = {0: "零是第零天", 1: "一那边是第五天", 2: "二那边是第六天", 4: "依次更新成", 3: None}
        first = True
        for u in D.TR["order"]:
            if keys.get(u):
                self.wait_key(keys[u])
            item = MathTex(str(u), color=WHITE).scale(0.7)
            orow.add(item)
            orow.arrange(RIGHT, buff=0.22).move_to([PANEL_X, 1.6, 0])
            self.play(Create(ring) if first else ring.animate.move_to(self.nodes[u]), FadeIn(item), run_time=0.45)
            first = False
            for v, w, old, new in fwd[u]:
                e = self.edges[(u, v)]
                self.play(e.animate.set_color(C_VE).set_stroke(width=5), run_time=0.3)
                anims = [e.animate.set_color(C_GREY).set_stroke(width=3)]
                if new != old:
                    anims += [ChangeDecimalToValue(self.ve[v][1], new),
                              Indicate(self.ve[v][0], color=C_YELLOW, scale_factor=1.25)]
                self.play(*anims, run_time=0.5)
            if u == 2:
                self.wait_key("四是第六天")
                self.play(Indicate(self.ve[4], color=C_YELLOW, scale_factor=1.3), run_time=0.6)
        self.wait_key("这就是工期")
        self.play(Indicate(self.ve[5], color=C_YELLOW, scale_factor=1.4), Indicate(self.total_lab, color=C_YELLOW),
                  run_time=0.9)
        self.hold()
        self.play(FadeOut(ring), FadeOut(orow), FadeOut(cap), run_time=0.5)

    # ---------------------------------------------------------------- 反向：vl 取最小
    def vl_beat(self):
        self.beat("vl")
        self.vl = {i: badge(D.TOTAL, C_VL).next_to(self.nodes[i], DOWN, buff=0.1) for i in range(D.N)}
        self.vl[4].next_to(self.nodes[4], RIGHT, buff=0.12)
        cap = VGroup(T("最迟发生时间", 22, C_VL), T("取最小", 22, C_VL)).arrange(DOWN, buff=0.1).move_to([PANEL_X, 2.6, 0])
        self.play(FadeIn(cap), *[FadeIn(b) for b in self.vl.values()], run_time=0.8)
        ring = Circle(R + 0.1, stroke_color=C_YELLOW, stroke_width=4).move_to(self.nodes[5])
        self.wait_key("五是第八天")
        self.play(Create(ring), Indicate(self.vl[5], color=C_YELLOW, scale_factor=1.3), run_time=0.7)
        keys = {3: "三最迟第六天", 2: "二有两个活动出去", 1: "一最迟第四天"}
        calc = None
        for u, ups in D.TR["bwd"]:
            if u == 5:
                continue
            if u in keys:
                self.wait_key(keys[u])
            self.play(ring.animate.move_to(self.nodes[u]), run_time=0.35)
            for v, w, old, new in ups:
                e = self.edges[(u, v)]
                cand = D.VL[v] - w
                f = MathTex(f"{D.VL[v]}-{w}={cand}", color=C_VL).scale(0.7).move_to([PANEL_X, 1.4, 0])
                anims = [e.animate.set_color(C_VL).set_stroke(width=5)]
                anims.append(ReplacementTransform(calc, f) if calc is not None else FadeIn(f))
                calc = f
                self.play(*anims, run_time=0.45 if u in (2,) else 0.35)
                if u == 2:
                    self.wait(0.6)
                anims = [e.animate.set_color(C_GREY).set_stroke(width=3)]
                if new != old:
                    anims += [ChangeDecimalToValue(self.vl[u][1], new), Indicate(self.vl[u][0], color=C_YELLOW, scale_factor=1.25)]
                self.play(*anims, run_time=0.45)
        self.wait_key("不能耽误任何一个后继")
        self.play(FadeOut(ring), FadeOut(calc), run_time=0.5)
        self.hold()
        self.play(FadeOut(cap), run_time=0.4)

    # ---------------------------------------------------------------- 机动时间
    def slack_beat(self):
        self.beat("slack")
        f1 = MathTex(r"e=ve(u)", color=C_VE).scale(0.75)
        f2 = MathTex(r"l=vl(v)-w", color=C_VL).scale(0.75)
        form = VGroup(f1, f2).arrange(DOWN, buff=0.15, aligned_edge=LEFT).move_to([PANEL_X, 2.75, 0])
        self.wait_key("最早开工看起点的最早时间")
        self.play(FadeIn(f1), run_time=0.6)
        self.wait_key("最迟开工看终点的最迟时间")
        self.play(FadeIn(f2), run_time=0.6)
        head = VGroup(*[T(s, 18, C_GREY) for s in ["活动", "e", "l", "机动"]])
        xs = [-1.05, -0.05, 0.55, 1.2]
        rows = []
        for a in D.ACTS:
            r_ = VGroup(MathTex(rf"\langle {a['u']},{a['v']}\rangle").scale(0.6), MathTex(str(a["e"]), color=C_VE).scale(0.6),
                        MathTex(str(a["l"]), color=C_VL).scale(0.6), MathTex(str(a["slack"]), color=C_YELLOW).scale(0.65))
            rows.append(r_)
        y0 = 1.65
        for j, h in enumerate(head):
            h.move_to([PANEL_X + xs[j], y0, 0])
        for k, r_ in enumerate(rows):
            for j, c in enumerate(r_):
                c.move_to([PANEL_X + xs[j], y0 - 0.46 * (k + 1), 0])
        self.table, self.trows = VGroup(head, *rows), rows
        self.wait_key("两者之差叫机动时间")
        self.play(FadeIn(head), LaggedStart(*[FadeIn(r_, shift=LEFT * 0.15) for r_ in rows], lag_ratio=0.12), run_time=1.6)
        self.wait_key("机动时间都是零")
        crit = [k for k, a in enumerate(D.ACTS) if a["slack"] == 0]
        self.play(*[self.edges[(D.ACTS[k]["u"], D.ACTS[k]["v"])].animate.set_color(C_CRIT).set_stroke(width=6) for k in crit],
                  *[rows[k].animate.set_color(C_CRIT) for k in crit], run_time=0.9)
        self.wait_key("连成的就是关键路径")
        self.play(*[Indicate(self.nodes[i], color=C_CRIT) for i in (0, 2, 3, 5)], run_time=1.0)
        self.wait_key("二到五能拖五天")
        k25 = next(k for k, a in enumerate(D.ACTS) if (a["u"], a["v"]) == (2, 5))
        self.play(Indicate(rows[k25][3], color=C_YELLOW, scale_factor=1.6),
                  self.edges[(2, 5)].animate.set_color(C_YELLOW).set_stroke(width=5), run_time=0.9)
        self.wait_key("其余的都只能拖一天")
        ones = [k for k, a in enumerate(D.ACTS) if a["slack"] == 1]
        self.play(*[Indicate(rows[k][3], color=C_YELLOW, scale_factor=1.5) for k in ones],
                  self.edges[(2, 5)].animate.set_color(C_GREY).set_stroke(width=3), run_time=0.9)
        self.form = form
        self.hold()

    # ---------------------------------------------------------------- 机动时间是整条路共用的
    def share_beat(self):
        self.beat("share")
        dtr = D.DELAY01
        dacts = D.activities(dtr, D.with_weight(D.EDGES, 0, 4))
        self.wait_key("把零到一拖一天")
        w01 = MathTex("4", color=C_YELLOW).scale(0.75).move_to(self.wlab[(0, 1)])
        self.play(Transform(self.wlab[(0, 1)], w01), self.edges[(0, 1)].animate.set_color(C_YELLOW).set_stroke(width=5),
                  run_time=0.7)
        anims = []
        for i in range(D.N):
            if dtr["ve"][i] != D.VE[i]:
                anims += [ChangeDecimalToValue(self.ve[i][1], dtr["ve"][i]), Indicate(self.ve[i][0], color=C_YELLOW)]
        self.play(*anims, run_time=0.8)
        self.wait_key("工期还是八天")
        self.play(Indicate(self.total_lab, color=C_YELLOW), Indicate(self.ve[5], color=C_YELLOW), run_time=0.8)
        self.wait_key("一后面的两个活动")
        changed = [k for k, a in enumerate(D.ACTS) if a["slack"] != dacts[k]["slack"]]
        new_rows = []
        for k in changed:
            a = dacts[k]
            new = VGroup(MathTex(rf"\langle {a['u']},{a['v']}\rangle", color=C_CRIT).scale(0.6),
                         MathTex(str(a["e"]), color=C_CRIT).scale(0.6), MathTex(str(a["l"]), color=C_CRIT).scale(0.6),
                         MathTex(str(a["slack"]), color=C_CRIT).scale(0.65))
            for j in range(4):
                new[j].move_to(self.trows[k][j])
            new_rows.append(new)
        self.play(*[Transform(self.trows[k], n) for k, n in zip(changed, new_rows)],
                  *[self.edges[(dacts[k]["u"], dacts[k]["v"])].animate.set_color(C_CRIT).set_stroke(width=6) for k in changed],
                  run_time=1.0)
        self.wait_key("变成零")
        self.play(*[Indicate(self.trows[k][3], color=C_CRIT, scale_factor=1.5) for k in changed], run_time=0.8)
        self.hold()
        # 复原：权值回到 3，ve 回到原值；表格和标记在下一 beat 收掉
        w3 = MathTex("3", color=WHITE).scale(0.75).move_to(self.wlab[(0, 1)])
        anims = [Transform(self.wlab[(0, 1)], w3)]
        for i in range(D.N):
            if dtr["ve"][i] != D.VE[i]:
                anims.append(ChangeDecimalToValue(self.ve[i][1], D.VE[i]))
        self.play(*anims, run_time=0.5)

    # ---------------------------------------------------------------- 缩短工期
    def shorten_beat(self):
        self.beat("shorten")
        crit0 = [(u, v) for u, v in D.CRIT]
        self.play(FadeOut(self.table), FadeOut(self.form), *[FadeOut(b) for b in self.ve.values()],
                  *[FadeOut(b) for b in self.vl.values()],
                  *[self.edges[e].animate.set_color(C_CRIT if e in crit0 else C_GREY).set_stroke(width=6 if e in crit0 else 3)
                    for e in self.edges], run_time=0.8)
        self.wait_key("把一到四从三天缩到一天")
        w14 = MathTex("1", color=C_GREEN).scale(0.75).move_to(self.wlab[(1, 4)])
        self.play(Transform(self.wlab[(1, 4)], w14), self.edges[(1, 4)].animate.set_color(C_GREEN).set_stroke(width=5),
                  run_time=0.8)
        self.wait_key("工期还是八")
        assert D.SHORT14["total"] == D.TOTAL
        self.play(Indicate(self.total_lab, color=C_YELLOW, scale_factor=1.3), run_time=0.8)
        w14b = MathTex("3", color=WHITE).scale(0.75).move_to(self.wlab[(1, 4)])
        self.play(Transform(self.wlab[(1, 4)], w14b), self.edges[(1, 4)].animate.set_color(C_GREY).set_stroke(width=3),
                  run_time=0.5)
        self.wait_key("从四天缩到两天")
        w23 = MathTex("2", color=C_GREEN).scale(0.75).move_to(self.wlab[(2, 3)])
        self.play(Transform(self.wlab[(2, 3)], w23), run_time=0.7)
        self.wait_key("工期却只降到七")
        self.play(ChangeDecimalToValue(self.total_lab[1], D.SHORT23["total"]),
                  Indicate(self.total_lab[0], color=C_YELLOW, scale_factor=1.3), run_time=0.9)
        crit1 = set(D.SHORT23["crit"])
        self.wait_key("原来七天的那两条路")
        self.play(*[self.edges[e].animate.set_color(C_CRIT if e in crit1 else C_GREY).set_stroke(width=6 if e in crit1 else 3)
                    for e in self.edges], run_time=1.0)
        new = T("新的关键路径", 24, C_CRIT).move_to([PANEL_X, -1.6, 0])
        self.play(FadeIn(new, shift=UP * 0.2), run_time=0.5)
        self.hold()
        w23b = MathTex("4", color=WHITE).scale(0.75).move_to(self.wlab[(2, 3)])
        self.play(FadeOut(new), Transform(self.wlab[(2, 3)], w23b), ChangeDecimalToValue(self.total_lab[1], D.TOTAL),
                  *[self.edges[e].animate.set_color(C_CRIT if e in crit0 else C_GREY).set_stroke(width=6 if e in crit0 else 3)
                    for e in self.edges], run_time=0.6)

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        graph = VGroup(*self.edges.values(), *self.nodes.values(), *self.wlab.values())
        code = Code(code_string=D.CODE_SHOWN, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 18})
        code.scale_to_fit_height(min(code.height, 6.4))
        if code.width > 7.4:
            code.scale_to_fit_width(7.4)
        code.move_to([3.05, 0.3, 0])
        self.play(FadeOut(self.total_lab), graph.animate.scale(0.5).move_to([-4.6, 1.4, 0]), run_time=1.0)
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        ln = code.code_lines

        def band(i0, i1, col):
            return SurroundingRectangle(VGroup(*ln[i0:i1 + 1]), color=col, buff=0.05, stroke_width=2.5).set_fill(col, 0.1)
        b = band(0, 8, C_VE)
        self.wait_key("正着按拓扑序走")
        self.play(Create(b), run_time=0.6)
        self.wait_key("倒着再走一遍")
        self.play(Transform(b, band(9, 13, C_VL)), run_time=0.6)
        self.wait_key("最后挑出")
        self.play(Transform(b, band(14, 16, C_CRIT)), run_time=0.6)
        self.wait_key("两遍都是点数加边数")
        cx = MathTex(r"O(V+E)", color=C_YELLOW).scale(1.1).move_to([-4.6, -1.5, 0])
        self.play(FadeIn(cx, shift=UP * 0.2), run_time=0.7)
        self.hold()
        self.play(FadeOut(VGroup(graph, code, b, cx)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        title = T("关键路径 = 最长的那条路", 36).move_to([0, 2.5, 0])
        rows = VGroup(
            T("① 正着推最早时间：取最大", 26, C_VE),
            T("② 倒着推最迟时间：取最小", 26, C_VL),
            T("③ 机动时间为零的活动：一天也拖不得", 26, C_CRIT),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 0.2, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.wait_key("正着推")
        self.play(FadeIn(rows[0], shift=RIGHT * 0.2), run_time=0.5)
        self.wait_key("倒着推")
        self.play(FadeIn(rows[1], shift=RIGHT * 0.2), run_time=0.5)
        self.wait_key("机动时间为零的活动")
        self.play(FadeIn(rows[2], shift=RIGHT * 0.2), run_time=0.5)
        self.hold(0.9)
        self.play(FadeOut(VGroup(title, rows)), run_time=0.8)
