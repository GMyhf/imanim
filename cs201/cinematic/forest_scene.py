"""树与森林：左孩子，右兄弟（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。森林、连线 / 切线、转换后的二叉树、三种周游序列、
带度数后根次序的栈还原快照全部来自 forestdata（讲义图 6.5、OJ24729 解法原样插桩；test_forest.py 对撞
讲义对应表、3.3 节栈表与随机森林往返）。

画面约定：父子线灰，切线前保留的「第一个孩子」线变蓝（= 左枝），兄弟连线黄（= 右枝）；旋转只转结点位置，
字母始终正立，线由 updater 跟着结点重画。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forestdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_KID, C_SIB, C_CUT = C_BLUE, C_YELLOW, C_RED
R = 0.3

# 图 6.5(a) 的森林摆位
P0 = {"A": (-4.0, 2.2), "B": (-5.4, 0.9), "C": (-4.0, 0.9), "D": (-2.6, 0.9), "E": (-4.6, -0.4),
      "F": (-3.4, -0.4), "G": (-0.4, 2.2), "H": (-1.0, 0.9), "I": (0.2, 0.9), "J": (-1.0, -0.4)}


def p3(xy):
    return np.array([xy[0], xy[1], 0.0])


def binary_layout(cx=-3.5, dx=0.62, top=2.3, dy=1.0):
    order = D.BIN_IN
    depth = D.depth_of(D.BIN, D.BIN_ROOT)
    m = len(order)
    return {k: np.array([cx + (i - (m - 1) / 2) * dx, top - dy * depth[k], 0]) for i, k in enumerate(order)}


def node(k, r=R, size=30, color=WHITE):
    return VGroup(Circle(r, stroke_color=color, stroke_width=3).set_fill(BG, 0), T(k, size))


def static_tree(pos: dict, edges: list, r=R, size=30, sw=3):
    """位置固定的小树（迷你森林、片尾对照）：edges = [(a, b, 颜色)]。"""
    nodes = {k: node(k, r, size).move_to(p) for k, p in pos.items()}
    lines = VGroup(*[Line(nodes[a].get_center(), nodes[b].get_center(), buff=r, stroke_color=c, stroke_width=sw)
                     for a, b, c in edges])
    return nodes, VGroup(lines, *nodes.values())


def seq_row(letters, y, x0=2.55, w=0.42, color=WHITE, size=28):
    return VGroup(*[T(c, size, color).move_to([x0 + i * w, y, 0]) for i, c in enumerate(letters)])


class ForestLesson(Lesson):
    def construct(self):
        for b in ("title", "forest", "connect", "cut", "rotate", "pre", "post", "level", "degree", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def wait_cue(self, key, default=None):
        t = self.cue_start(key, default)
        if t is not None:
            self.wait_until(t)

    # ------------------------------------------------------------ 活动的线：跟着结点重画
    def link(self, a, b, color, sw=3.5):
        nodes = self.nodes

        def mk():
            pa, pb = nodes[a].get_center(), nodes[b].get_center()
            if np.linalg.norm(pb - pa) < 2 * R + 0.02:
                return VMobject()
            return Line(pa, pb, buff=R, stroke_color=color, stroke_width=sw)
        ln = mk()
        ln.add_updater(lambda m: m.become(mk()))
        return ln

    # ---------------------------------------------------------------- 片头：孩子不定 → 两个指针
    def title_beat(self):
        self.beat("title")
        title = T("树与森林", 58).move_to([0, 3.2, 0])
        sub = T("左孩子，右兄弟", 30, C_BLUE).move_to([0, 2.55, 0])
        x = node("X").move_to([0, 1.4, 0])
        kids = VGroup(*[Circle(0.24, stroke_color=C_GREY, stroke_width=3).move_to([-2.4 + 1.2 * i, -0.2, 0])
                        for i in range(5)])
        fan = VGroup(*[Line(x.get_center(), k.get_center(), buff=0.3, stroke_color=C_GREY, stroke_width=3)
                       for k in kids])
        q = T("孩子个数不固定：三个、五个……", 28, C_GREY).move_to([0, -1.2, 0])
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.play(GrowFromCenter(x), run_time=0.5)
        self.play(LaggedStart(*[AnimationGroup(Create(f), GrowFromCenter(k)) for f, k in zip(fan, kids)],
                              lag_ratio=0.15), FadeIn(q), run_time=1.4)
        self.wait_cue("只留两个指针")
        first = Line(x.get_center(), kids[0].get_center(), buff=0.3, stroke_color=C_KID, stroke_width=4)
        chain = VGroup(*[Arrow(kids[i].get_center(), kids[i + 1].get_center(), buff=0.28, stroke_width=4,
                               color=C_SIB, max_tip_length_to_length_ratio=0.18) for i in range(4)])
        self.play(FadeOut(fan[1:]), Transform(fan[0], first), run_time=0.9)
        self.play(LaggedStart(*[GrowArrow(a) for a in chain], lag_ratio=0.2), run_time=1.2)
        lab1 = T("一个指向第一个孩子", 26, C_KID).move_to([-3.6, 0.75, 0])
        lab2 = T("一个指向下一个兄弟", 26, C_SIB).move_to([0, -1.2, 0])
        self.play(FadeIn(lab1, shift=RIGHT * 0.2), FadeOut(q), FadeIn(lab2, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.7))
        self.play(FadeOut(VGroup(title, sub, x, kids, fan[0], chain, lab1, lab2)), run_time=0.7)

    # ---------------------------------------------------------------- 图 6.5 的森林
    def forest_beat(self):
        self.beat("forest")
        self.nodes = {k: node(k).move_to(p3(p)) for k, p in P0.items()}
        self.lines = {}
        for a, b in D.parent_edges():
            self.lines[(a, b)] = self.link(a, b, C_GREY)
        for group, cue in (("ABCDEF", None), ("GHIJ", "第二棵树")):
            if cue:
                self.wait_cue(cue)
            es = [ln for (u, v), ln in self.lines.items() if u in group]
            for ln in es:
                ln.suspend_updating()
            self.play(LaggedStart(*[GrowFromCenter(self.nodes[k]) for k in group], lag_ratio=0.12),
                      run_time=1.2)
            self.play(*[Create(ln) for ln in es], run_time=0.6)
            for ln in es:
                ln.resume_updating()
        lab1 = Text("A(B, C(E, F), D)", font=MONO, font_size=24, color=C_GREY).move_to([-4.0, -1.3, 0])
        lab2 = Text("G(H(J), I)", font=MONO, font_size=24, color=C_GREY).move_to([-0.4, -1.3, 0])
        self.wait_cue("森林就是")
        box1 = SurroundingRectangle(VGroup(*[self.nodes[k] for k in "ABCDEF"]), color=C_TEAL, buff=0.2,
                                    corner_radius=0.2)
        box2 = SurroundingRectangle(VGroup(*[self.nodes[k] for k in "GHIJ"]), color=C_PURPLE, buff=0.2,
                                    corner_radius=0.2)
        self.play(Create(box1), Create(box2), FadeIn(lab1), FadeIn(lab2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(box1, box2, lab1, lab2)), run_time=0.6)

    def step_title(self, i, text, color):
        t = T(text, 32, color).move_to([4.3, 2.3 - 0.75 * i, 0])
        if not hasattr(self, "steps"):
            self.steps = VGroup()
        anims = [s.animate.set_opacity(0.4) for s in self.steps]
        self.steps.add(t)
        return t, anims

    # ---------------------------------------------------------------- ① 连线
    def connect_beat(self):
        self.beat("connect")
        t, dim = self.step_title(0, "① 连线：兄弟相连", C_SIB)
        self.play(FadeIn(t, shift=LEFT * 0.2), *dim, run_time=0.7)
        self.wait_cue("连线")
        sibs = D.sibling_edges()
        inner = [e for e in sibs if e != ("A", "G")]
        new = {}
        for a, b in inner:
            ln = self.link(a, b, C_SIB, 4)
            new[(a, b)] = ln
        self.wait_cue("B 连 C", self.now + 1.0)
        for (a, b), ln in new.items():
            ln.suspend_updating()
            self.play(Create(ln), run_time=0.7)
            ln.resume_updating()
            self.lines[(a, b)] = ln
        self.wait_cue("两棵树的根")
        ln = self.link("A", "G", C_SIB, 4)
        ln.suspend_updating()
        self.play(Create(ln), run_time=0.8)
        ln.resume_updating()
        self.lines[("A", "G")] = ln
        self.sib = set(sibs)
        self.wait(max(0.1, self.left()))

    # ---------------------------------------------------------------- ② 切线
    def cut_beat(self):
        self.beat("cut")
        t, dim = self.step_title(1, "② 切线：只留第一个孩子", C_KID)
        self.play(FadeIn(t, shift=LEFT * 0.2), *dim, run_time=0.7)
        kept = [(a, b) for a, b in D.parent_edges() if (a, b) not in D.cut_edges()]
        self.wait_cue("只保留")
        for e in kept:
            self.lines[e].clear_updaters()
        self.play(*[self.lines[e].animate.set_stroke(C_KID, 4) for e in kept], run_time=0.8)
        for e in kept:
            a, b = e
            self.lines[e].add_updater(lambda m, a=a, b=b: m.become(self._mk(a, b, C_KID, 4)))
        self.wait_cue("A 到 C", self.now + 0.6)
        groups = [[("A", "C"), ("A", "D")], [("C", "F")], [("G", "I")]]
        for g in groups:
            for e in g:
                self.lines[e].clear_updaters()
            self.play(*[self.lines[e].animate.set_stroke(C_CUT, 5) for e in g], run_time=0.4)
            self.play(*[FadeOut(self.lines.pop(e)) for e in g], run_time=0.6)
        self.wait(max(0.1, self.left()))

    def _mk(self, a, b, color, sw):
        pa, pb = self.nodes[a].get_center(), self.nodes[b].get_center()
        if np.linalg.norm(pb - pa) < 2 * R + 0.02:
            return VMobject()
        return Line(pa, pb, buff=R, stroke_color=color, stroke_width=sw)

    # ---------------------------------------------------------------- ③ 旋转 → 二叉树
    def rotate_beat(self):
        self.beat("rotate")
        t, dim = self.step_title(2, "③ 旋转：顺时针 45°", WHITE)
        self.play(FadeIn(t, shift=LEFT * 0.2), *dim, run_time=0.7)
        pivot = self.nodes["A"].get_center()
        start = {k: n.get_center() for k, n in self.nodes.items()}
        ring = Circle(R + 0.12, stroke_color=WHITE, stroke_width=4).move_to(pivot)
        self.play(Create(ring), run_time=0.5)
        group = VGroup(*self.nodes.values())

        def place(_, alpha):
            # 动画先于 updater 执行，线的 updater 读到的是本帧的新位置（用 ValueTracker + updater 会慢一帧）
            th = -PI / 4 * alpha
            rot = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
            for k, n in self.nodes.items():
                n.move_to(pivot + rot @ (start[k] - pivot))
        self.play(UpdateFromAlphaFunc(group, place), run_time=2.2, rate_func=smooth, audit=False)
        self.wait_cue("再整理", self.now + 0.3)
        tgt = binary_layout()
        self.play(*[n.animate.move_to(tgt[k]) for k, n in self.nodes.items()], FadeOut(ring), run_time=1.6)
        self.wait_cue("左枝是父子")
        l1 = VGroup(Line(ORIGIN, RIGHT * 0.6, stroke_color=C_KID, stroke_width=5), T("左枝 = 第一个孩子（父子）", 26, C_KID))
        l2 = VGroup(Line(ORIGIN, RIGHT * 0.6, stroke_color=C_SIB, stroke_width=5), T("右枝 = 下一个兄弟", 26, C_SIB))
        for g in (l1, l2):
            g.arrange(RIGHT, buff=0.2)
        legend = VGroup(l1, l2).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to([3.7, -0.3, 0])
        self.play(FadeIn(legend, shift=UP * 0.2), run_time=0.8)
        self.wait_cue("根的右链")
        rings = VGroup(*[Circle(R + 0.12, stroke_color=C_TEAL, stroke_width=5).move_to(self.nodes[k]) for k in "AG"])
        rl = T("根的右链 A → G = 各棵树的根", 26, C_TEAL).move_to([3.7, -1.6, 0])
        self.play(Create(rings), FadeIn(rl), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rings, rl, legend, self.steps)), run_time=0.6)
        for ln in self.lines.values():
            ln.clear_updaters()

    # ---------------------------------------------------------------- 先根 = 前序
    def mini_forest(self):
        cx, cy, s = -2.6, 0.9, 0.55
        pos = {k: np.array([3.75 + (x - cx) * s, 1.55 + (y - cy) * s, 0]) for k, (x, y) in P0.items()}
        edges = [(a, b, C_GREY) for a, b in D.parent_edges()]
        return static_tree(pos, edges, r=R * 0.6, size=18, sw=2.5)

    def walk_rows(self, seq_a, seq_b, la, lb, ca, cb, tree_a, tree_b, dt):
        y1, y2 = -0.45, -1.25
        h1 = T(la, 24, ca).move_to([1.45, y1, 0])
        h2 = T(lb, 24, cb).move_to([1.45, y2, 0])
        r1, r2 = seq_row(seq_a, y1, color=ca), seq_row(seq_b, y2, color=cb)
        self.play(FadeIn(h1), FadeIn(h2), run_time=0.4)
        for i in range(len(seq_a)):
            ka, kb = seq_a[i], seq_b[i]
            ga = Circle(R * 0.6 + 0.08, stroke_color=ca, stroke_width=4).move_to(tree_a[ka])
            gb = Circle(R + 0.1, stroke_color=cb, stroke_width=4).move_to(tree_b[kb])
            self.play(FadeIn(r1[i], scale=1.4), FadeIn(r2[i], scale=1.4), FadeIn(ga), FadeIn(gb), run_time=dt)
            self.remove(ga, gb)
        return VGroup(h1, h2, r1, r2), r1, r2

    def pre_beat(self):
        self.beat("pre")
        mini, self.mini = self.mini_forest()
        self.mini_nodes = mini
        self.play(FadeIn(self.mini, shift=LEFT * 0.3), run_time=0.8)
        self.wait_cue("森林的先根次序")
        dt = max(0.3, min(0.55, (self.left() - 3.0) / 10))
        rows, r1, r2 = self.walk_rows(D.PRE, D.BIN_PRE, "森林先根", "二叉树前序", C_TEAL, C_BLUE,
                                      self.mini_nodes, self.nodes, dt)
        eq = T("一字不差", 28, C_GREEN).move_to([4.4, -2.05, 0])
        self.play(*[Indicate(VGroup(a, b), color=C_GREEN, scale_factor=1.15) for a, b in zip(r1, r2)],
                  FadeIn(eq), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(rows), FadeOut(eq), run_time=0.5)

    # ---------------------------------------------------------------- 后根 = 中序，以及为什么
    def post_beat(self):
        self.beat("post")
        dt = max(0.3, min(0.5, (self.cue_start("道理", self.now + 6) - self.now - 1.0) / 10))
        rows, r1, r2 = self.walk_rows(D.POST, D.BIN_IN, "森林后根", "二叉树中序", C_TEAL, C_YELLOW,
                                      self.mini_nodes, self.nodes, dt)
        self.wait_cue("道理")
        kids_b = SurroundingRectangle(VGroup(*[self.nodes[k] for k in "BCDEF"]), color=C_KID, buff=0.12,
                                      corner_radius=0.15)
        rest_b = SurroundingRectangle(VGroup(*[self.nodes[k] for k in "GHIJ"]), color=C_SIB, buff=0.12,
                                      corner_radius=0.15)
        kids_f = SurroundingRectangle(VGroup(*[self.mini_nodes[k] for k in "BCDEF"]), color=C_KID, buff=0.08,
                                      corner_radius=0.1)
        rest_f = SurroundingRectangle(VGroup(*[self.mini_nodes[k] for k in "GHIJ"]), color=C_SIB, buff=0.08,
                                      corner_radius=0.1)
        self.play(Create(kids_b), Create(kids_f), run_time=0.8)
        self.play(Create(rest_b), Create(rest_f), run_time=0.8)
        self.wait_cue("后根是先走孩子")
        segs = [(0, 5, C_KID, "左：孩子们"), (5, 6, WHITE, "根"), (6, 10, C_SIB, "右：后面的树")]
        marks = VGroup()
        for i, j, c, txt in segs:
            row = VGroup(*r2[i:j])
            ul = Line(row.get_corner(DL) + DOWN * 0.12, row.get_corner(DR) + DOWN * 0.12, stroke_color=c, stroke_width=5)
            tag = T(txt, 22, c).next_to(ul, DOWN, buff=0.12)
            if txt == "根":                          # 根只占一个字母宽，标签放到下一行，免得和右边的标签连成一串
                tag.next_to(ul, DOWN, buff=0.5)
            marks.add(VGroup(ul, tag))
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in marks], lag_ratio=0.35), run_time=1.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rows, marks, kids_b, rest_b, kids_f, rest_f)), run_time=0.6)

    # ---------------------------------------------------------------- 层次次序对不上
    def level_beat(self):
        self.beat("level")
        y1, y2 = -0.45, -1.25
        h1 = T("森林层次", 24, C_TEAL).move_to([1.45, y1, 0])
        h2 = T("二叉树层次", 24, C_PURPLE).move_to([1.45, y2, 0])
        r1, r2 = seq_row(D.LEVEL, y1, color=C_TEAL), seq_row(D.BIN_LEVEL, y2, color=C_PURPLE)
        self.play(FadeIn(h1), LaggedStart(*[FadeIn(x) for x in r1], lag_ratio=0.1), run_time=1.4)
        self.wait_cue("二叉树一层一层")
        self.play(FadeIn(h2), LaggedStart(*[FadeIn(x) for x in r2], lag_ratio=0.1), run_time=1.4)
        bad = [i for i in range(len(D.LEVEL)) if D.LEVEL[i] != D.BIN_LEVEL[i]]
        self.play(*[r2[i].animate.set_color(C_RED) for i in bad], *[r1[i].animate.set_color(C_RED) for i in bad],
                  run_time=0.6)
        self.wait_cue("一般树也没有中序")
        note = T("一般树：只有先根、后根、层次", 26, WHITE).move_to([4.2, -2.05, 0])
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.7))
        everything = VGroup(h1, h2, r1, r2, note, self.mini, *self.nodes.values(), *self.lines.values())
        self.play(FadeOut(everything), run_time=0.7)

    # ---------------------------------------------------------------- 带度数的后根次序：用栈还原
    def degree_beat(self):
        self.beat("degree")
        head = T("带度数的后根次序：不存指针", 30, WHITE).move_to([0, 3.3, 0])
        cells = VGroup()
        for k, d in D.DEG_POST:
            box = Rectangle(width=1.0, height=0.7, stroke_color=C_GREY, stroke_width=2)
            sep = Line(box.get_top() + RIGHT * 0.12, box.get_bottom() + RIGHT * 0.12, stroke_color=C_GREY,
                       stroke_width=1.5)
            lt = T(k, 28).move_to(box.get_center() + LEFT * 0.2)
            dt = T(str(d), 24, C_YELLOW).move_to(box.get_center() + RIGHT * 0.33)
            cells.add(VGroup(box, sep, lt, dt))
        cells.arrange(RIGHT, buff=0.1).move_to([0, 2.45, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(c, shift=DOWN * 0.15) for c in cells], lag_ratio=0.08),
                  run_time=1.6)
        base = Line([-6.4, -1.55, 0], [6.4, -1.55, 0], stroke_color=C_GREY, stroke_width=2)
        bl = T("栈底", 22, C_GREY).move_to([-6.1, -1.85, 0])
        tl = T("栈顶 →", 22, C_GREY).move_to([5.9, -1.85, 0])
        self.play(Create(base), FadeIn(bl), FadeIn(tl), run_time=0.6)
        self.wait_cue("从左往右扫")
        ch, _, snaps = D.REBUILD
        sn, kids_of, stack = {}, {}, []
        lines = []
        cursor = SurroundingRectangle(cells[0], color=C_YELLOW, buff=0.06)
        self.play(Create(cursor), run_time=0.4)
        steps_left = len(snaps)
        finish_by = self.cue_start("扫完", self.now + self.left() - 2.5) - 0.3     # 「扫完」那句之前扫完
        for i, (k, d, kids, after) in enumerate(snaps):
            dt = max(0.8, min(2.4, (finish_by - self.now) / steps_left))
            steps_left -= 1
            if i:
                self.play(cursor.animate.move_to(cells[i]), run_time=0.25 * dt)
            if kids:
                popped = VGroup(*[sn[c] for c in kids])
                self.play(popped.animate.set_color(C_YELLOW), run_time=0.25 * dt)
            kids_of[k] = kids
            new = node(k, 0.26, 24).move_to(cells[i].get_center())
            sn[k] = new
            self.add(new)
            pos = self.stack_layout(after, kids_of)
            self.play(*[m.animate.move_to(pos[x]) for x, m in sn.items()], run_time=0.45 * dt)
            if kids:
                es = [self.stack_edge(sn, k, c) for c in kids]
                self.play(*[Create(e) for e in es], *[sn[c].animate.set_color(WHITE) for c in kids], run_time=0.3 * dt)
                for e, c in zip(es, kids):
                    e.add_updater(lambda m, a=k, b=c: m.become(self.stack_edge(sn, a, b)))
                lines += es
        self.play(FadeOut(cursor), run_time=0.3)
        done = T("栈里剩下 A、G 两棵树 = 原来的森林", 28, C_GREEN).move_to([0, -2.4, 0])
        self.play(FadeIn(done, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        for e in lines:
            e.clear_updaters()
        self.play(FadeOut(VGroup(head, cells, base, bl, tl, done, *sn.values(), *lines)), run_time=0.6)

    @staticmethod
    def stack_edge(sn, a, b):
        pa, pb = sn[a].get_center(), sn[b].get_center()
        return Line(pa, pb, buff=0.26, stroke_color=C_GREY, stroke_width=3)

    @staticmethod
    def stack_layout(stack, kids_of, x0=-5.6, leaf_w=0.78, gap=0.6, top=0.75, dy=0.82):
        """栈里每棵树：叶子等距排开，内部结点居中于孩子之上；树从左（栈底）往右排。"""
        pos = {}
        x = x0

        def width(n):
            ks = kids_of.get(n, [])
            return sum(width(c) for c in ks) if ks else 1

        def place(n, left, depth):
            ks = kids_of.get(n, [])
            if not ks:
                pos[n] = np.array([left + leaf_w / 2, top - dy * depth, 0])
                return
            cur = left
            for c in ks:
                place(c, cur, depth + 1)
                cur += width(c) * leaf_w
            pos[n] = np.array([(pos[ks[0]][0] + pos[ks[-1]][0]) / 2, top - dy * depth, 0])
        for r in stack:
            place(r, x, 0)
            x += width(r) * leaf_w + gap
        return pos

    # ---------------------------------------------------------------- 片尾
    def recap_beat(self):
        self.beat("recap")
        cx, cy, s = -2.6, 0.9, 0.75
        fpos = {k: np.array([-3.6 + (x - cx) * s, 1.2 + (y - cy) * s, 0]) for k, (x, y) in P0.items()}
        kept = [(a, b) for a, b in D.parent_edges() if (a, b) not in D.cut_edges()]
        _, forest = static_tree(fpos, [(a, b, C_GREY) for a, b in D.parent_edges()], r=0.25, size=24)
        bpos = binary_layout(cx=3.4, dx=0.5, top=2.4, dy=0.72)
        _, binary = static_tree(bpos, [(a, b, C_KID) for a, b in kept] + [(a, b, C_SIB) for a, b in D.sibling_edges()],
                                r=0.25, size=24)
        arrow = DoubleArrow([-0.9, 1.0, 0], [0.5, 1.0, 0], stroke_width=4, color=WHITE, buff=0)
        self.play(FadeIn(forest, shift=RIGHT * 0.2), FadeIn(binary, shift=LEFT * 0.2), GrowFromCenter(arrow),
                  run_time=1.2)
        lines = VGroup(T("左枝 = 第一个孩子　　右枝 = 下一个兄弟", 28, WHITE),
                       T("先根 = 前序　　后根 = 中序", 28, C_YELLOW)).arrange(DOWN, buff=0.3).move_to([0, -1.75, 0])
        self.play(FadeIn(lines[0], shift=UP * 0.2), run_time=0.8)
        self.wait_cue("先根对前序")
        self.play(FadeIn(lines[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left()))
        self.play(FadeOut(VGroup(forest, binary, arrow, lines)), run_time=0.8)
