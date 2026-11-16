"""强连通分量：两遍深度优先搜索（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。第一遍 DFS 的进入 / 考察边 / 结束事件、
发现与结束时间、结束栈，第二遍在转置图上按出栈次序收块的每一步，都来自 sccdata（讲义 kosaraju 原样插桩；
test_scc.py 对撞讲义输出、Tarjan、传递闭包暴力法与随机图）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sccdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

# 三块各占一片：蓝 {0,1,2,3} 绕成方环在左，紫 {4,5} 在右上，黄 {6,7} 在右下
POS = {0: (-5.6, -1.0), 1: (-5.6, 1.4), 2: (-3.0, 1.4), 3: (-3.0, -1.0),
       5: (-0.4, 1.4), 4: (2.2, 1.4), 6: (-0.4, -1.0), 7: (2.2, -1.0)}
R = 0.42
LABEL_DIR = {0: DOWN, 1: LEFT, 2: UP, 3: DOWN, 5: UP, 4: RIGHT, 6: DOWN, 7: DOWN}
COMP_COL = [C_BLUE, C_YELLOW, C_PURPLE]          # 按 Kosaraju 产出次序：{0,3,2,1} {6,7} {5,4}
C_GRAYF, C_BLACKF, C_BLACKS = "#6B7180", "#05060A", "#5C6270"   # 灰：访问中；黑：已结束（描边调暗）
STACK_X = 5.9


def slot(k):
    return np.array([STACK_X, -2.35 + 0.52 * k, 0])


def rot(v, a):
    c, s = np.cos(a), np.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1], 0])


def p(i):
    return np.array([*POS[i], 0])


def geom(u, v, pos=p, r=R, pair=False):
    """弧 u→v 的起止点与弯曲角。1→4 绕上方大弧；成对的往返弧各向右偏，分开画。"""
    cu, cv = pos(u), pos(v)
    d = (cv - cu) / np.linalg.norm(cv - cu)
    if (u, v) == (1, 4):
        return cu + r * rot(RIGHT, 0.95), cv + r * rot(RIGHT, PI - 0.95), -0.95
    if pair:
        return cu + r * rot(d, -0.45), cv + r * rot(-d, 0.45), 0.55
    return cu + r * d, cv - r * d, 0.0


def edge(s, e, ang, color=C_GREY, width=3):
    if abs(ang) < 1e-6:
        return Arrow(s, e, buff=0, stroke_width=width, color=color, tip_length=0.2,
                     max_tip_length_to_length_ratio=0.25, max_stroke_width_to_length_ratio=12)
    return CurvedArrow(s, e, angle=ang, stroke_width=width, color=color, tip_length=0.2)


def make_node(label, pos, col=WHITE):
    c = Circle(R, stroke_color=col, stroke_width=3).set_fill(BG, 0)
    t = MathTex(str(label), color=col).scale(0.85) if isinstance(label, int) else T(label, 30, col)
    return VGroup(c, t).move_to(pos)


def chip(i, col=WHITE):
    box = RoundedRectangle(corner_radius=0.08, width=0.9, height=0.42, stroke_color=col, stroke_width=2).set_fill(BG, 0)
    return VGroup(box, MathTex(str(i), color=col).scale(0.7).move_to(box))


class SCCLesson(Lesson):
    def construct(self):
        for b in ("title", "graph", "condense", "dfs1", "finish", "transpose", "dfs2", "code", "cows", "recap"):
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

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        a = make_node("你", [-1.7, -0.7, 0], C_BLUE)
        b = make_node("我", [1.7, -0.7, 0], C_BLUE)
        s1, e1, g1 = geom(0, 1, pos=lambda i: (a if i == 0 else b).get_center(), pair=True)
        s2, e2, g2 = geom(1, 0, pos=lambda i: (a if i == 0 else b).get_center(), pair=True)
        ab, ba = edge(s1, e1, g1, C_TEAL, 4), edge(s2, e2, g2, C_TEAL, 4)
        self.play(FadeIn(a, scale=0.6), FadeIn(b, scale=0.6), run_time=0.7)
        self.play(Create(ab), run_time=0.8)
        self.wait_key("我也关注你")
        self.play(Create(ba), run_time=0.8)
        hull = RoundedRectangle(corner_radius=0.5, width=5.0, height=2.3, stroke_color=C_BLUE, stroke_width=3)
        hull.set_fill(C_BLUE, 0.07).move_to([0, -0.7, 0])
        self.wait_key("互相能到达的点圈在一起")
        self.play(Create(hull), run_time=0.9)
        title = T("强连通分量", 70).move_to([0, 2.2, 0])
        sub = T("两遍深度优先搜索", 32, C_YELLOW).next_to(title, DOWN, buff=0.28)
        self.wait_key("这一集")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.hold()
        self.play(FadeOut(VGroup(a, b, ab, ba, hull, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 例图与三块
    def graph_beat(self):
        self.beat("graph")
        self.nodes = {i: make_node(i, p(i)) for i in range(D.N)}
        self.arr = {}
        for u, v in D.EDGES:
            s, e, g = geom(u, v, pair=(v, u) in D.KIND)
            self.arr[(u, v)] = edge(s, e, g)
        self.play(LaggedStart(*[FadeIn(self.nodes[i], scale=0.6) for i in range(D.N)], lag_ratio=0.1), run_time=1.4)
        self.play(*[GrowArrow(a) if isinstance(a, Arrow) else Create(a) for a in self.arr.values()], run_time=1.3)
        cnt = VGroup(T("8 个点", 26), T("12 条边", 26)).arrange(DOWN, buff=0.18).move_to([5.3, 2.4, 0])
        self.play(FadeIn(cnt), run_time=0.5)
        self.wait_key("零到一")
        for e in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            self.play(self.arr[e].animate.set_color(C_BLUE).set_stroke(width=5), run_time=0.45)
        self.wait_key("四和五互相指")
        self.play(*[self.arr[e].animate.set_color(C_PURPLE).set_stroke(width=5) for e in [(4, 5), (5, 4)]], run_time=0.7)
        self.wait_key("六和七也互相指")
        self.play(*[self.arr[e].animate.set_color(C_YELLOW).set_stroke(width=5) for e in [(6, 7), (7, 6)]], run_time=0.7)
        self.wait_key("一到四有边")
        one_way = VGroup(MathTex(r"1 \to 4", color=C_GREEN), MathTex(r"4 \to 1", color=C_RED)).arrange(DOWN, buff=0.3)
        marks = VGroup(T("能到", 22, C_GREEN), T("回不来", 22, C_RED))
        for m, r_ in zip(marks, one_way):
            m.next_to(r_, RIGHT, buff=0.25)
        box = VGroup(one_way, marks).move_to([5.3, 0.4, 0])
        self.play(self.arr[(1, 4)].animate.set_color(C_GREEN).set_stroke(width=5), FadeIn(box[0][0]), FadeIn(marks[0]),
                  run_time=0.8)
        self.wait_key("四回不到一")
        self.play(FadeIn(box[0][1]), FadeIn(marks[1]), Indicate(self.nodes[4], color=C_RED), run_time=0.8)
        self.wait_key("恰好分成三块")
        self.hulls = self.make_hulls()
        self.play(*[Create(h) for h in self.hulls], self.arr[(1, 4)].animate.set_color(C_GREY).set_stroke(width=3),
                  FadeOut(box), run_time=1.1)
        self.hold()
        self.play(FadeOut(cnt), *[self.arr[e].animate.set_color(C_GREY).set_stroke(width=3)
                                  for e in self.arr], run_time=0.6)

    def make_hulls(self):
        out = []
        for k, comp in enumerate(D.SCCS):
            xs = [POS[v][0] for v in comp]
            ys = [POS[v][1] for v in comp]
            w, h = max(xs) - min(xs) + 2 * R + 0.3, max(ys) - min(ys) + 2 * R + 0.3
            r_ = RoundedRectangle(corner_radius=0.4, width=w, height=h, stroke_color=COMP_COL[k], stroke_width=3)
            r_.set_fill(COMP_COL[k], 0.07).move_to([(max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0])
            out.append(r_)
        return out

    # ---------------------------------------------------------------- 缩点
    def condense_beat(self):
        self.beat("condense")
        cpos = [np.array([4.3, 1.9, 0]), np.array([4.3, -1.7, 0]), np.array([6.3, 0.1, 0])]
        names = [r"\{0,1,2,3\}", r"\{6,7\}", r"\{4,5\}"]
        blobs = []
        for k in range(3):
            c = Circle(0.62, stroke_color=COMP_COL[k], stroke_width=3).set_fill(COMP_COL[k], 0.15)
            blobs.append(VGroup(c, MathTex(names[k], color=COMP_COL[k]).scale(0.62)).move_to(cpos[k]))
        self.play(*[ReplacementTransform(self.hulls[k].copy(), blobs[k]) for k in range(3)], run_time=1.4)
        cedges = []
        for a, b in D.CEDGES:
            d = (cpos[b] - cpos[a]) / np.linalg.norm(cpos[b] - cpos[a])
            cedges.append(Arrow(cpos[a] + 0.64 * d, cpos[b] - 0.64 * d, buff=0, stroke_width=4, color=WHITE,
                                tip_length=0.22, max_tip_length_to_length_ratio=0.25))
        self.play(*[GrowArrow(e) for e in cedges], run_time=0.9)
        self.wait_key("来回都有路")
        bad = CurvedArrow(cpos[1] + np.array([0.55, 0.3, 0]), cpos[0] + np.array([0.55, -0.3, 0]),
                          angle=0.6, color=C_RED, stroke_width=3, tip_length=0.2)
        cross = T("✗", 40, C_RED).move_to([5.45, 0.1, 0])
        self.play(Create(bad), run_time=0.8)
        self.play(FadeIn(cross, scale=1.5), run_time=0.4)
        self.wait(0.6)
        self.play(FadeOut(bad), FadeOut(cross), run_time=0.5)
        self.wait_key("有向无环图")
        dag = T("有向无环图", 26, C_GREEN).move_to([5.3, -2.6, 0])
        self.play(FadeIn(dag, shift=UP * 0.2), run_time=0.6)
        self.wait_key("蓝色这块是源头")
        src = T("源头", 24, C_BLUE).next_to(blobs[0], LEFT, buff=0.15)
        self.play(FadeIn(src), Indicate(blobs[0], color=C_BLUE), run_time=0.8)
        self.wait_key("紫色这块是终点")
        snk = T("终点", 24, C_PURPLE).next_to(blobs[2], UP, buff=0.15)
        self.play(FadeIn(snk), Indicate(blobs[2], color=C_PURPLE), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(*blobs, *cedges, dag, src, snk)), *[h.animate.set_stroke(opacity=0.35).set_fill(opacity=0.03)
                                                                    for h in self.hulls], run_time=0.6)

    # ---------------------------------------------------------------- 第一遍 DFS
    def dfs1_beat(self):
        self.beat("dfs1")
        legend = VGroup()
        for col, op, st, name in [(BG, 0, WHITE, "未访问"), (C_GRAYF, 0.9, WHITE, "访问中"),
                                  (C_BLACKF, 1, C_BLACKS, "已结束")]:
            c = Circle(0.15, stroke_color=st, stroke_width=2).set_fill(col, op)
            legend.add(VGroup(c, T(name, 18)).arrange(RIGHT, buff=0.1))
        legend.arrange(RIGHT, buff=0.3).move_to([5.0, 3.35, 0])
        tlab = T("time =", 22, C_GREY)
        self.timer = Integer(0, color=WHITE).scale(0.7)
        timer = VGroup(tlab, self.timer).arrange(RIGHT, buff=0.15).move_to([5.0, 2.7, 0])
        head = T("结束栈", 22, C_GREY).move_to([STACK_X, 1.95, 0])
        base = Line([STACK_X - 0.55, -2.65, 0], [STACK_X + 0.55, -2.65, 0], color=C_GREY, stroke_width=3)
        self.play(FadeIn(legend), run_time=0.7)
        self.wait_key("记下发现时间")
        self.play(FadeIn(timer), FadeIn(head), Create(base), run_time=0.7)
        self.panel = VGroup(legend, timer, head, base)
        # 发现/结束时间标签：结束时间先透明，结束时点亮
        self.lab = {}
        for u in range(D.N):
            g = VGroup(Text(str(D.D_TIME[u]), font=MONO, font_size=22, color=WHITE),
                       Text("/", font=MONO, font_size=22, color=C_GREY),
                       Text(str(D.F_TIME[u]), font=MONO, font_size=22, color=C_YELLOW)).arrange(RIGHT, buff=0.05)
            g.next_to(self.nodes[u], LABEL_DIR[u], buff=0.12)
            g[2].set_opacity(0)
            self.lab[u] = g
        self.ring = Circle(R + 0.1, stroke_color=C_YELLOW, stroke_width=4).move_to(self.nodes[0])
        self.chips = {}
        self.nstack = 0
        ev = D.TR["events"]
        cut = lambda pred: next(i for i, e in enumerate(ev) if pred(e))   # noqa: E731
        i_back30 = cut(lambda e: e[:3] == ("edge", 3, 0))
        i_36 = cut(lambda e: e[:3] == ("edge", 3, 6))
        i_back45 = cut(lambda e: e[:3] == ("edge", 4, 5))
        i_f4 = cut(lambda e: e[:2] == ("finish", 4))
        i_76 = cut(lambda e: e[:3] == ("edge", 7, 6))
        i_f3 = cut(lambda e: e[:2] == ("finish", 3))
        i_25 = cut(lambda e: e[:3] == ("edge", 2, 5))
        i_f2 = cut(lambda e: e[:2] == ("finish", 2))
        self.wait_key("从零出发")
        self.play(Create(self.ring), run_time=0.3)
        self.run_events(ev[:i_back30], 0.5)
        self.wait_key("三到零")
        self.run_events([ev[i_back30]], 0.8)
        self.wait_key("三到六")
        self.run_events(ev[i_36:i_back45], 0.42)
        self.wait_key("四到五")
        self.run_events([ev[i_back45]], 0.8)
        self.wait_key("四最先结束")
        self.run_events(ev[i_f4:i_76], 0.6)
        self.wait_key("七到六也是回边")
        self.run_events(ev[i_76:i_25], 0.5)
        self.wait_key("二到五")
        self.run_events([ev[i_25]], 0.8)
        self.wait_key("最后二")
        self.run_events(ev[i_f2:], 0.55)
        self.wait_key("压在栈顶")
        self.play(Indicate(self.chips[0], color=C_YELLOW), Indicate(self.lab[0][2], color=C_YELLOW, scale_factor=1.5),
                  run_time=1.0)
        self.hold()
        self.play(FadeOut(self.ring), run_time=0.4)

    def run_events(self, evs, rt):
        for e in evs:
            self.play(*self.ev_anims(e), run_time=rt)

    def ev_anims(self, e):
        kind = e[0]
        if kind == "enter":
            u, t = e[1], e[2]
            return [self.ring.animate.move_to(self.nodes[u]), self.nodes[u][0].animate.set_fill(C_GRAYF, 0.9),
                    FadeIn(self.lab[u]), ChangeDecimalToValue(self.timer, t)]
        if kind == "edge":
            u, v, k = e[1], e[2], e[3]
            a = self.arr[(u, v)]
            if k == "tree":
                return [a.animate.set_color(C_GREEN).set_stroke(width=5)]
            if k == "back":
                return [a.animate.set_color(C_RED).set_stroke(width=5), Indicate(self.nodes[v][0], color=C_RED)]
            return [a.animate.set_color(C_YELLOW).set_stroke(width=4), Indicate(self.nodes[v][0], color=C_YELLOW)]
        u, t = e[1], e[2]
        c = chip(u).move_to(slot(self.nstack))
        self.chips[u] = c
        self.nstack += 1
        return [self.nodes[u][0].animate.set_fill(C_BLACKF, 1).set_stroke(C_BLACKS), self.lab[u][2].animate.set_opacity(1),
                ChangeDecimalToValue(self.timer, t), self.ring.animate.move_to(self.nodes[u]),
                GrowFromPoint(c, self.nodes[u].get_center())]

    # ---------------------------------------------------------------- 每块最大结束时间
    def finish_beat(self):
        self.beat("finish")
        self.play(*[h.animate.set_stroke(opacity=1).set_fill(opacity=0.07) for h in self.hulls],
                  *[self.arr[e].animate.set_color(C_GREY).set_stroke(width=3) for e in self.arr], run_time=0.8)
        best = [max(comp, key=lambda v: D.F_TIME[v]) for comp in D.SCCS]     # 0, 6, 5
        keys = ["蓝色十六", "黄色十二", "紫色十"]
        boxes = []
        for k, v in enumerate(best):
            self.wait_key(keys[k])
            bx = SurroundingRectangle(self.lab[v][2], color=COMP_COL[k], buff=0.06, stroke_width=3)
            boxes.append(bx)
            self.play(Create(bx), Indicate(self.lab[v][2], color=COMP_COL[k], scale_factor=1.4), run_time=0.7)
        mx = [D.F_TIME[v] for v in best]
        chain = VGroup(*[MathTex(str(m), color=COMP_COL[k]) for k, m in enumerate(mx)])
        chain = VGroup(chain[0], MathTex(">"), chain[1], MathTex(">"), chain[2]).arrange(RIGHT, buff=0.25)
        chain.move_to([-1.6, -2.6, 0])
        self.wait_key("顺着缩点图的边")
        cross = [e for e in D.EDGES if D.COMP[e[0]] != D.COMP[e[1]]]
        self.play(FadeIn(chain, shift=UP * 0.2), *[self.arr[e].animate.set_color(WHITE).set_stroke(width=5) for e in cross],
                  run_time=1.0)
        self.wait_key("只要有边从甲块指向乙块")
        self.play(self.arr[(3, 6)].animate.set_color(C_YELLOW).set_stroke(width=6), run_time=0.6)
        self.play(Indicate(self.hulls[1], color=C_YELLOW, scale_factor=1.03), run_time=1.0)
        self.wait_key("所以栈顶的零")
        self.play(Indicate(self.chips[0], color=C_BLUE, scale_factor=1.3), Indicate(self.nodes[0], color=C_BLUE),
                  self.hulls[0].animate.set_fill(C_BLUE, 0.16), run_time=1.0)
        self.hold()
        self.play(FadeOut(VGroup(chain, *boxes)), self.hulls[0].animate.set_fill(C_BLUE, 0.07),
                  *[self.arr[e].animate.set_color(C_GREY).set_stroke(width=3) for e in cross], run_time=0.6)

    # ---------------------------------------------------------------- 转置
    def transpose_beat(self):
        self.beat("transpose")
        self.play(FadeOut(VGroup(*self.lab.values(), self.panel[0], self.panel[1])),
                  *[self.nodes[u][0].animate.set_fill(BG, 0).set_stroke(WHITE) for u in range(D.N)], run_time=0.7)
        cross = [e for e in D.EDGES if D.COMP[e[0]] != D.COMP[e[1]]]
        flips = []
        for (u, v), a in self.arr.items():
            s, e, g = geom(u, v, pair=(v, u) in D.KIND)
            col = C_YELLOW if (u, v) in cross else C_GREY
            flips.append(Transform(a, edge(e, s, -g, col, 5 if (u, v) in cross else 3)))
        self.play(*flips, run_time=1.6)
        tag = T("全部反向", 24, C_YELLOW).move_to([0.9, 3.25, 0])
        self.play(FadeIn(tag), run_time=0.4)
        self.wait_key("块和块之间的边全部掉头")
        self.play(*[Indicate(self.arr[e], color=C_YELLOW) for e in cross], run_time=1.0)
        self.wait_key("原来的源头变成了终点")
        lab = T("源头 → 终点", 24, C_BLUE).move_to([-4.3, -2.45, 0])
        self.play(FadeIn(lab, shift=UP * 0.2), self.hulls[0].animate.set_fill(C_BLUE, 0.16), run_time=0.8)
        self.wait_key("走不出自己这一块")
        self.play(Indicate(self.hulls[0], color=C_BLUE, scale_factor=1.03), run_time=1.0)
        self.hold()
        self.play(FadeOut(VGroup(tag, lab)), self.hulls[0].animate.set_fill(C_BLUE, 0.07),
                  *[self.arr[e].animate.set_color(C_GREY).set_stroke(width=3) for e in cross], run_time=0.6)

    # ---------------------------------------------------------------- 第二遍 DFS
    def dfs2_beat(self):
        self.beat("dfs2")
        res_y = -2.6
        results = VGroup()

        def pop(u, skip):
            c = self.chips[u]
            if skip:
                return [c.animate.shift(RIGHT * 0.5).set_opacity(0.15)]
            return [c.animate.shift(RIGHT * 0.5).set_color(C_YELLOW), self.ring.animate.move_to(self.nodes[u])]

        def visit(u, k):
            return [self.nodes[u][0].animate.set_fill(COMP_COL[k], 0.35).set_stroke(COMP_COL[k])]

        rounds = D.ROUNDS
        keyed = {0: "弹出零", 6: "弹出六", 5: "弹出五"}
        self.ring.move_to(self.nodes[0])
        k = 0
        first_skip = True
        for r in rounds:
            u = r["start"]
            if r["skip"]:
                if u in (1, 2, 3) and first_skip:
                    self.wait_key("已经访问过，跳过")
                    first_skip = False
                self.play(*pop(u, True), run_time=0.45)
                continue
            self.wait_key(keyed[u])
            if k == 0:
                self.play(FadeIn(self.ring), *pop(u, False), run_time=0.6)
            else:
                self.play(*pop(u, False), run_time=0.6)
            self.play(*visit(u, k), run_time=0.45)
            for x, y, seen in r["looks"]:
                a = self.arr[(y, x)]                     # 转置图的 x→y 就是原图的 y→x（已画成反向）
                if seen:
                    self.play(Indicate(a, color=C_RED, scale_factor=1.0), run_time=0.4)
                else:
                    self.play(a.animate.set_color(COMP_COL[k]).set_stroke(width=5), run_time=0.35)
                    self.play(*visit(y, k), self.ring.animate.move_to(self.nodes[y]), run_time=0.4)
            comp = r["comp"]
            item = VGroup(T(["第一块", "第二块", "第三块"][k], 22, COMP_COL[k]),
                          MathTex(r"\{" + ",".join(map(str, comp)) + r"\}", color=COMP_COL[k]).scale(0.75))
            item.arrange(RIGHT, buff=0.15)
            results.add(item)
            results.arrange(RIGHT, buff=0.6).move_to([-1.9, res_y, 0])
            self.play(FadeIn(item, shift=UP * 0.2), Indicate(self.hulls[k], color=COMP_COL[k], scale_factor=1.02),
                      run_time=0.7)
            k += 1
        self.wait_key("栈空了")
        self.play(FadeOut(self.ring), Indicate(results, color=WHITE, scale_factor=1.06), run_time=0.9)
        self.results = results
        self.hold()

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        graph = VGroup(*self.hulls, *self.arr.values(), *self.nodes.values())
        stack = VGroup(*self.chips.values(), self.panel[2], self.panel[3])
        code = Code(code_string=D.CODE_SHOWN, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 18})
        code.scale_to_fit_height(min(code.height, 6.2))
        if code.width > 7.6:
            code.scale_to_fit_width(7.6)
        code.move_to([2.95, 0.35, 0])
        self.play(FadeOut(stack), FadeOut(self.results), graph.animate.scale(0.42).move_to([-4.7, 1.6, 0]), run_time=1.0)
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        ln = code.code_lines

        def band(i0, i1, col):
            # 上下边放在相邻两行的行距正中：紧贴字形的 SurroundingRectangle 会压到上一行的注释和下一行的字
            g = VGroup(*ln[i0:i1 + 1])
            top = (g.get_top()[1] + ln[i0 - 1].get_bottom()[1]) / 2 if i0 > 0 else g.get_top()[1] + 0.06
            bot = (g.get_bottom()[1] + ln[i1 + 1].get_top()[1]) / 2 if i1 + 1 < len(ln) else g.get_bottom()[1] - 0.06
            left, right = g.get_left()[0] - 0.08, g.get_right()[0] + 0.08
            return Rectangle(width=right - left, height=top - bot, color=col, stroke_width=2.5).set_fill(col, 0.1).move_to(
                [(left + right) / 2, (top + bot) / 2, 0])
        self.wait_key("第一个在原图上走")
        b1 = band(0, 5, C_GREEN)
        self.play(Create(b1), run_time=0.6)
        self.wait_key("第二个在反图上走")
        b2 = band(6, 11, C_BLUE)
        self.play(ReplacementTransform(b1, b2), run_time=0.6)
        self.wait_key("每个点、每条边")
        cx = MathTex(r"O(V+E)", color=C_YELLOW).scale(1.1).move_to([-4.7, -1.4, 0])
        self.play(FadeOut(b2), FadeIn(cx, shift=UP * 0.2), run_time=0.8)
        self.hold()
        self.play(FadeOut(VGroup(graph, code, cx)), run_time=0.6)

    # ---------------------------------------------------------------- 应用：受欢迎的奶牛
    def cows_beat(self):
        self.beat("cows")
        head = T("受欢迎的奶牛", 34, C_YELLOW).move_to([0, 3.2, 0])
        rule = VGroup(MathTex(r"A \to B", color=C_TEAL).scale(0.9), T("A 认为 B 受欢迎，可以传递", 24)).arrange(RIGHT, buff=0.3)
        rule.move_to([0, 2.35, 0])
        self.play(FadeIn(head), run_time=0.6)
        cp = {1: np.array([-4.6, -0.3, 0]), 2: np.array([-2.0, -0.3, 0]), 3: np.array([0.7, -0.3, 0])}
        cows = {i: make_node(i, cp[i]) for i in cp}
        e12 = edge(*geom(1, 2, pos=lambda i: cp[i], pair=True))
        e21 = edge(*geom(2, 1, pos=lambda i: cp[i], pair=True))
        e23 = edge(*geom(2, 3, pos=lambda i: cp[i]))
        sample = VGroup(*[T(s, 20, C_GREY) for s in ["样例", "1 2", "2 1", "2 3"]]).arrange(DOWN, buff=0.12)
        sample.move_to([5.5, 0.2, 0])
        self.wait_key("甲认为乙受欢迎")
        self.play(FadeIn(rule, shift=UP * 0.2), FadeIn(sample), *[FadeIn(c, scale=0.6) for c in cows.values()],
                  run_time=0.8)
        self.play(Create(e12), run_time=0.6)
        self.wait_key("受欢迎可以传递")
        self.play(Create(e21), GrowArrow(e23), run_time=0.9)
        self.wait_key("问有几头牛")
        q = T("被其他所有牛认为受欢迎的，有几头？", 24).move_to([0, 1.55, 0])
        self.play(FadeIn(q), run_time=0.6)
        self.wait_key("缩点以后")
        rule2 = VGroup(T("恰好一块没有出边", 22, C_GREEN), T("→ 答案 = 这块的大小", 22, C_GREEN)).arrange(DOWN, buff=0.1)
        rule2.move_to([5.0, -2.2, 0])
        self.play(FadeIn(rule2), run_time=0.7)
        hull = RoundedRectangle(corner_radius=0.4, width=3.7, height=1.5, stroke_color=C_BLUE, stroke_width=3)
        hull.set_fill(C_BLUE, 0.08).move_to((cp[1] + cp[2]) / 2)
        self.wait_key("一和二是一块")
        self.play(Create(hull), run_time=0.7)
        self.wait_key("三是唯一的终点")
        self.play(cows[3][0].animate.set_fill(C_PURPLE, 0.35).set_stroke(C_PURPLE), Indicate(cows[3], color=C_PURPLE),
                  run_time=0.9)
        self.wait_key("答案是一")
        ans = VGroup(T("答案", 28), MathTex("1", color=C_YELLOW).scale(1.4)).arrange(RIGHT, buff=0.3).move_to([3.0, -0.3, 0])
        self.play(FadeIn(ans, scale=1.2), run_time=0.6)
        self.hold()
        self.play(FadeOut(VGroup(head, rule, q, rule2, sample, *cows.values(), e12, e21, e23, hull, ans)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        title = T("强连通分量 · 两遍深度优先搜索", 34).move_to([0, 2.6, 0])
        rows = VGroup(
            T("① 原图上走一遍，结束时压栈：栈顶在源头那块", 26, C_BLUE),
            T("② 把所有边反过来：源头变成终点", 26, C_YELLOW),
            T("③ 按出栈次序再走一遍：每次被困在一块里", 26, C_PURPLE),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 0.4, 0])
        cx = MathTex(r"O(V+E)", color=C_GREEN).scale(1.0).move_to([0, -1.8, 0])
        self.play(FadeIn(title), run_time=0.6)
        self.wait_key("第一遍记结束顺序")
        self.play(FadeIn(rows[0], shift=RIGHT * 0.2), run_time=0.6)
        self.wait_key("把图反过来")
        self.play(FadeIn(rows[1], shift=RIGHT * 0.2), run_time=0.6)
        self.wait_key("第二遍每次都被困在一块里")
        self.play(FadeIn(rows[2], shift=RIGHT * 0.2), FadeIn(cx), run_time=0.6)
        self.hold(0.9)
        self.play(FadeOut(VGroup(title, rows, cx)), run_time=0.8)
