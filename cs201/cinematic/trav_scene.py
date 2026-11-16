"""二叉树周游：同一圈轮廓，三个时机（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。树、三种序列、层次周游的队列快照、
由中序 + 后序重建的调用轨迹全部来自 travdata（讲义【算法5.3】【算法5.7】与 OJ24750 解法原样插桩；
test_trav.py 对撞讲义表格、随机树往返重建与暴力枚举）。

TreeView 也给 bst_scene 用：结点横坐标取中序名次、纵坐标取深度——于是「中序 = 把树竖直压到地面」
在画面上是字面意思，重建时中序序列的每个字母也正好在它结点的正上方。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import travdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_PRE, C_IN, C_POST = C_BLUE, C_YELLOW, C_GREEN
ORDER_COL = {0: C_PRE, 1: C_IN, 2: C_POST}


class TreeView(VGroup):
    """shape：结点 → (左, 右)。结点横坐标 = 中序名次，纵坐标 = 深度；边随结点位置实时重画。"""

    def __init__(self, shape: dict, root, dx=0.9, dy=0.85, top=2.6, cx=0.0, r=0.3, size=30,
                 text=lambda k: str(k), show=None):
        super().__init__()
        self.shape, self.root = {k: tuple(v) for k, v in shape.items() if k is not None}, root
        self.dx, self.dy, self.top, self.cx, self.r, self.size, self.text = dx, dy, top, cx, r, size, text
        self.nodes, self.edges = {}, {}
        pos = self.layout()
        self.edge_layer = VGroup()
        self.add(self.edge_layer)
        self.pos0 = pos
        for k in self.shape:
            if show is None or k in show:              # show：先只放这些结点，其余之后 add_node(k, pos0[k])
                self.add_node(k, pos[k])

    # ------------------------------------------------------------ 结构
    def parent_of(self, k):
        for p, kids in self.shape.items():
            if k in kids:
                return p
        return None

    def layout(self, shape=None, root=None) -> dict:
        shape = self.shape if shape is None else shape
        root = self.root if root is None else root
        order, depth = [], {}

        def go(n, d):
            if n is None:
                return
            go(shape[n][0], d + 1)
            order.append(n)
            depth[n] = d
            go(shape[n][1], d + 1)
        go(root, 0)
        m = len(order)
        return {k: np.array([self.cx + (i - (m - 1) / 2) * self.dx, self.top - self.dy * depth[k], 0])
                for i, k in enumerate(order)}

    def make_node(self, k):
        c = Circle(self.r, stroke_color=WHITE, stroke_width=3).set_fill(BG, 0)
        return VGroup(c, T(self.text(k), self.size))

    def _edge(self, k):
        p = self.parent_of(k)
        if p is None or k not in self.nodes or p not in self.nodes:
            return VMobject()
        a, b = self.nodes[p].get_center(), self.nodes[k].get_center()
        if np.linalg.norm(b - a) < 2 * self.r + 0.02:
            return VMobject()
        return Line(a, b, buff=self.r, stroke_color=C_GREY, stroke_width=3)

    def add_node(self, k, at):
        self.nodes[k] = self.make_node(k).move_to(at)
        e = self._edge(k)
        e.add_updater(lambda m, k=k: m.become(self._edge(k)))
        self.edges[k] = e
        self.edge_layer.add(e)
        self.add(self.nodes[k])
        return self.nodes[k]

    def drop_node(self, k):
        """从结构里拿掉（调用方负责把它淡出）；它的边一并拿掉。"""
        self.shape.pop(k, None)
        self.shape = {p: tuple(None if c == k else c for c in kids) for p, kids in self.shape.items()}
        e = self.edges.pop(k)
        e.clear_updaters()
        self.edge_layer.remove(e)
        return self.nodes.pop(k)

    def relayout(self, shape: dict | None = None, root=None, keep=()):
        """换结构并返回把结点挪到新布局的动画；keep 里的结点（暂时脱离树的）原地不动。"""
        if shape is not None:
            self.shape = {k: tuple(v) for k, v in shape.items() if k is not None}
            self.root = shape.get(None, root) if root is None else root
        pos = self.layout()
        anims = []
        for k, n in self.nodes.items():
            if k in pos and k not in keep:
                anims.append(n.animate.move_to(pos[k]))
        return anims

    def freeze(self):
        for e in self.edges.values():
            e.clear_updaters()

    def ring(self, k, color=C_YELLOW, w=6):
        return Circle(self.r + 0.1, stroke_color=color, stroke_width=w).move_to(self.nodes[k])


def letter_row(letters, y, x0=-1.6, w=0.62, color=WHITE, size=32):
    return VGroup(*[T(c, size, color).move_to([x0 + i * w, y, 0]) for i, c in enumerate(letters)])


class TravLesson(Lesson):
    def construct(self):
        for b in ("title", "three", "contour", "flatten", "code", "expr", "level", "rebuild", "unique", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def wait_cue(self, key):
        t = self.cue_start(key)
        if t is not None:
            self.wait_until(t)

    # ---------------------------------------------------------------- 片头：树摊成一行
    def title_beat(self):
        self.beat("title")
        self.tree = TreeView(D.FIG55, D.ROOT, top=1.6)
        tree = self.tree
        self.play(Create(tree.edge_layer), *[GrowFromCenter(n) for n in tree.nodes.values()], run_time=1.6)
        forks = VGroup(*[tree.ring(k, C_TEAL, 4) for k in ("A", "B", "C", "E", "F")])
        self.play(LaggedStart(*[Create(f) for f in forks], lag_ratio=0.2), run_time=1.2)
        self.play(FadeOut(forks), run_time=0.5)
        self.wait_cue("周游")
        row = letter_row(D.PRE, -1.9, x0=-(len(D.PRE) - 1) * 0.35, w=0.7, size=34)
        copies = [tree.nodes[c][1].copy() for c in D.PRE]
        self.play(LaggedStart(*[c.animate.move_to(r) for c, r in zip(copies, row)], lag_ratio=0.12), run_time=2.2)
        line = Line([-3.3, -2.35, 0], [3.3, -2.35, 0], stroke_color=C_GREY, stroke_width=2)
        title = T("二叉树周游", 60).move_to([0, 3.15, 0])
        sub = T("同一圈轮廓，三个时机", 30, C_BLUE).move_to([0, 2.5, 0])
        self.play(tree.animate.shift(DOWN * 0.35), Create(line), run_time=0.6)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.8))
        self.play(FadeOut(VGroup(title, sub, line, *copies)), tree.animate.shift(UP * 1.35), run_time=0.8)

    # ---------------------------------------------------------------- 根、左、右：六种排法剩三种
    def three_beat(self):
        self.beat("three")
        tree = self.tree                                       # 现在 top = 2.6
        lbox = SurroundingRectangle(VGroup(*[tree.nodes[k] for k in "BDEG"]), color=C_BLUE, buff=0.15,
                                    corner_radius=0.2)
        rbox = SurroundingRectangle(VGroup(*[tree.nodes[k] for k in "CFHI"]), color=C_GREEN, buff=0.15,
                                    corner_radius=0.2)
        tring = tree.ring("A", C_YELLOW)
        tl = T("t 根", 26, C_YELLOW).next_to(tring, RIGHT, buff=0.2)
        ll = T("L 左子树", 26, C_BLUE).next_to(lbox, DOWN, buff=0.15)
        rl = T("R 右子树", 26, C_GREEN).next_to(rbox, DOWN, buff=0.15)
        self.play(Create(tring), FadeIn(tl), run_time=0.7)
        self.play(Create(lbox), FadeIn(ll), run_time=0.7)
        self.play(Create(rbox), FadeIn(rl), run_time=0.7)
        self.wait_cue("六种")
        col = {"t": C_YELLOW, "L": C_BLUE, "R": C_GREEN}
        perms = ["tLR", "LtR", "LRt", "tRL", "RtL", "RLt"]
        items = VGroup(*[VGroup(*[T(ch, 34, col[ch]) for ch in p]).arrange(RIGHT, buff=0.12) for p in perms])
        items.arrange(RIGHT, buff=0.75).move_to([0, -1.55, 0])
        self.play(LaggedStart(*[FadeIn(i, shift=UP * 0.2) for i in items], lag_ratio=0.12), run_time=1.4)
        bad = VGroup(*items[3:])
        crosses = VGroup(*[Line(i.get_corner(DL), i.get_corner(UR), stroke_color=C_RED, stroke_width=4) for i in bad])
        self.play(Create(crosses), run_time=0.6)
        self.play(FadeOut(bad), FadeOut(crosses), run_time=0.5)
        names = ["前序", "中序", "后序"]
        good = VGroup(*items[:3])
        tgt = VGroup(*[VGroup(items[i].copy(), T(names[i], 28, ORDER_COL[i])).arrange(DOWN, buff=0.18)
                       for i in range(3)]).arrange(RIGHT, buff=1.6).move_to([0, -1.75, 0])
        self.wait_cue("根在最前")
        self.play(*[good[i].animate.move_to(tgt[i][0]) for i in range(3)], run_time=0.8)
        for i in range(3):
            self.play(FadeIn(tgt[i][1], shift=UP * 0.15), Indicate(good[i][i], color=C_YELLOW, scale_factor=1.4),
                      run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(lbox, rbox, tring, tl, ll, rl, good, *[t[1] for t in tgt])), run_time=0.6)

    # ---------------------------------------------------------------- 绕轮廓走一圈
    def contour_points(self):
        tree, ev = self.tree, D.euler()
        off = {0: np.array([-0.5, 0.12, 0]), 1: np.array([0, -0.5, 0]), 2: np.array([0.5, 0.12, 0])}
        return ev, [tree.nodes[n].get_center() + off[s] for n, s in ev]

    def contour_beat(self):
        self.beat("contour")
        tree = self.tree
        ev, pts = self.contour_points()
        path = VMobject().set_points_smoothly([pts[0] + UP * 0.4, *pts, pts[-1] + UP * 0.4])
        path.set_stroke(C_GREY, 2, opacity=0.6)
        dash = DashedVMobject(path, num_dashes=120)
        dot = Dot(pts[0] + UP * 0.4, radius=0.09, color=WHITE)
        self.wait_cue("贴着")
        self.play(FadeIn(dot), run_time=0.3)
        self.play(Create(dash), MoveAlongPath(dot, path), run_time=4.2, rate_func=linear)
        # 一个结点三次经过：以 B 为例
        self.wait_cue("三次")
        b = tree.nodes["B"].get_center()
        marks_b = VGroup(*[Dot(b + o, radius=0.09, color=ORDER_COL[s]) for s, o in
                           ((0, np.array([-0.5, 0.12, 0])), (1, np.array([0, -0.5, 0])), (2, np.array([0.5, 0.12, 0])))])
        names = ["① 左边下来", "② 底下穿过", "③ 右边上去"]
        tags = VGroup(*[VGroup(Dot(radius=0.09, color=ORDER_COL[i]), T(names[i], 26, ORDER_COL[i])).arrange(
            RIGHT, buff=0.15) for i in range(3)]).arrange(RIGHT, buff=0.8).move_to([0, -1.2, 0])
        ring_b = tree.ring("B", WHITE, 3)
        self.play(Create(ring_b), run_time=0.4)
        for i in range(3):
            self.play(FadeIn(marks_b[i], scale=2), FadeIn(tags[i]), run_time=0.7)
        self.wait_cue("第一次")
        self.play(FadeOut(tags), FadeOut(marks_b), FadeOut(ring_b), run_time=0.4)
        heads = VGroup(*[T(n, 26, ORDER_COL[i]) for i, n in enumerate(("前序", "中序", "后序"))])
        ys = [-0.75, -1.5, -2.25]
        for h, y in zip(heads, ys):
            h.move_to([-3.4, y, 0])
        self.rows = [VGroup() for _ in range(3)]
        self.play(FadeIn(heads), run_time=0.4)
        dot.move_to(pts[0] + UP * 0.4)
        stamps = VGroup()
        seg_t = max(0.12, min(0.3, (self.cue_start("三种周游", self.now + 8) - self.now - 0.6) / len(ev)))
        prev = dot.get_center()
        for (n, s), p in zip(ev, pts):
            mk = Dot(p, radius=0.07, color=ORDER_COL[s])
            stamps.add(mk)
            cell = T(n, 32, ORDER_COL[s]).move_to([-2.4 + 0.62 * len(self.rows[s]), ys[s], 0])
            self.rows[s].add(cell)
            src = tree.nodes[n][1].copy()
            self.play(dot.animate.move_to(p), FadeIn(mk, scale=2), Transform(src, cell), run_time=seg_t,
                      rate_func=linear)
            self.remove(src)
            self.add(cell)
            prev = p
        self.heads = heads
        self.wait_cue("三种周游")
        self.play(Indicate(dash, color=WHITE, scale_factor=1.0), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(dot, dash, stamps)), run_time=0.6)

    # ---------------------------------------------------------------- 中序 = 竖直落到地面
    def flatten_beat(self):
        self.beat("flatten")
        tree = self.tree
        pre_row, in_row, post_row = self.rows
        self.play(FadeOut(VGroup(pre_row, post_row, self.heads[0], self.heads[2])),
                  VGroup(in_row, self.heads[1]).animate.shift(DOWN * 0.85), run_time=0.8)
        ground = Line([-4.3, -0.95, 0], [4.3, -0.95, 0], stroke_color=C_GREY, stroke_width=2)
        self.wait_cue("竖直")
        drops = VGroup(*[tree.nodes[k][1].copy() for k in D.IN])
        guides = VGroup(*[DashedLine(tree.nodes[k].get_bottom(), [tree.nodes[k].get_x(), -0.95, 0],
                                     stroke_color=C_GREY, stroke_width=2, dash_length=0.08) for k in D.IN])
        self.play(Create(ground), Create(guides), run_time=0.8)
        self.play(*[d.animate.move_to([tree.nodes[k].get_x(), -1.3, 0]).set_color(C_IN)
                    for d, k in zip(drops, D.IN)], run_time=1.6)
        self.play(*[Indicate(VGroup(d, c), color=C_IN, scale_factor=1.15) for d, c in zip(drops, in_row)],
                  run_time=1.0)
        self.wait_cue("左子树整个")
        root_x = tree.nodes["A"].get_x()
        lb = Rectangle(width=root_x + 4.2 - 0.35, height=0.6, stroke_color=C_BLUE, stroke_width=3).move_to(
            [(-4.2 + root_x - 0.35) / 2, -1.3, 0])
        rb = Rectangle(width=4.2 - root_x - 0.35, height=0.6, stroke_color=C_GREEN, stroke_width=3).move_to(
            [(4.2 + root_x + 0.35) / 2, -1.3, 0])
        self.play(Create(lb), Create(rb), Indicate(tree.nodes["A"], color=C_YELLOW), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ground, guides, drops, lb, rb, in_row, self.heads[1])), run_time=0.6)

    # ---------------------------------------------------------------- 代码：只差 visit 那一行
    def code_beat(self):
        self.beat("code")
        tree = self.tree
        self.play(tree.animate.scale(0.62).move_to([-4.0, 0.9, 0]), run_time=1.0)
        tree.r *= 0.62
        lines = ["if (n == nullptr) return;", "visit(n);", "preorder(n->left);", "preorder(n->right);"]
        head = Text("void preorder(Node* n) {", font=MONO, font_size=26)
        body = [Text(s, font=MONO, font_size=26) for s in lines]
        tail = Text("}", font=MONO, font_size=26)
        x0, y0, lh = -0.6, 2.2, 0.62
        head.move_to([x0, y0, 0], aligned_edge=LEFT)
        for i, b in enumerate(body):
            b.move_to([x0 + 0.5, y0 - lh * (i + 1), 0], aligned_edge=LEFT)
        tail.move_to([x0, y0 - lh * 5, 0], aligned_edge=LEFT)
        body[1].set_color(C_PRE)
        self.play(FadeIn(head), *[FadeIn(b) for b in body], FadeIn(tail), run_time=1.2)
        name = {0: "preorder", 1: "inorder", 2: "postorder"}
        tag = T("前序", 28, C_PRE).move_to([5.3, y0, 0])
        self.play(FadeIn(tag), run_time=0.4)
        self.wait_cue("唯一的差别")
        slots = [y0 - lh * k for k in (2, 3, 4)]                     # visit 在第 2/3/4 行
        cur = body[:]
        for kind in (1, 2):
            # 新顺序：前序 [if, visit, L, R]；中序 [if, L, visit, R]；后序 [if, L, R, visit]
            rec_l = Text(f"{name[kind]}(n->left);", font=MONO, font_size=26)
            rec_r = Text(f"{name[kind]}(n->right);", font=MONO, font_size=26)
            new_head = Text(f"void {name[kind]}(Node* n) {{", font=MONO, font_size=26).move_to([x0, y0, 0],
                                                                                              aligned_edge=LEFT)
            seq = [rec_l, cur[1], rec_r] if kind == 1 else [rec_l, rec_r, cur[1]]
            anims = [Transform(head, new_head),
                     Transform(tag, T("中序" if kind == 1 else "后序", 28, ORDER_COL[kind]).move_to(tag)),
                     cur[1].animate.move_to([x0 + 0.5, slots[seq.index(cur[1])], 0], aligned_edge=LEFT).set_color(
                         ORDER_COL[kind])]
            rec_l.move_to([x0 + 0.5, slots[seq.index(rec_l)], 0], aligned_edge=LEFT)
            rec_r.move_to([x0 + 0.5, slots[seq.index(rec_r)], 0], aligned_edge=LEFT)
            anims += [ReplacementTransform(cur[2], rec_l), ReplacementTransform(cur[3], rec_r)]
            self.play(*anims, run_time=1.1)
            cur = [cur[0], cur[1], rec_l, rec_r]
            self.wait(0.5)
        self.code = VGroup(head, cur[0], cur[1], cur[2], cur[3], tail, tag)
        self.wait_cue("每个结点进出")
        xb = max(n.get_right()[0] for n in tree.nodes.values()) + 0.2
        depth_brace = BraceBetweenPoints([xb, tree.nodes["A"].get_top()[1], 0], [xb, tree.nodes["G"].get_bottom()[1], 0],
                                         direction=RIGHT, color=C_TEAL)
        hl = T(f"递归栈深 = 树高 {D.levels(D.FIG55, D.ROOT)} 层", 24, C_TEAL).move_to([-4.0, -0.75, 0])
        big_o = MathTex(r"T(n)=O(n)", color=WHITE).scale(0.8).move_to([2.2, -1.6, 0])
        self.play(GrowFromCenter(depth_brace), FadeIn(hl), Write(big_o), run_time=1.2)
        self.extra = VGroup(depth_brace, hl, big_o)
        self.wait(max(0.1, self.left() - 0.6))
        tree.freeze()
        self.play(FadeOut(self.code), FadeOut(self.extra), FadeOut(tree), run_time=0.6)

    # ---------------------------------------------------------------- 表达式树
    def expr_beat(self):
        self.beat("expr")
        et = TreeView(D.EXPR, D.EXPR_ROOT, dx=0.85, dy=0.85, top=2.0, cx=-3.2, text=D.label)
        formula = T("A + B × (C + D)", 36).move_to([-3.2, 3.0, 0])
        self.wait_cue("把表达式")
        self.play(Write(formula), run_time=1.0)
        for k in et.nodes:
            et.nodes[k][0].set_stroke(C_RED if k[0] in "+×" else WHITE)
        self.play(Create(et.edge_layer), *[GrowFromCenter(n) for n in et.nodes.values()], run_time=1.4)
        rows = [("前序", "pre", "前缀式", C_PRE), ("中序", "in", "括号丢了", C_RED), ("后序", "post", "后缀式", C_POST)]
        ys = [1.6, 0.4, -0.8]
        self.wait_cue("前序得到")
        built = VGroup()
        for (nm, kind, note, col), y in zip(rows, ys):
            seq = [D.label(x) for x in D.order(kind, D.EXPR, D.EXPR_ROOT)]
            hd = T(nm, 28, ORDER_COL[{"pre": 0, "in": 1, "post": 2}[kind]]).move_to([0.6, y, 0])
            cells = VGroup(*[T(c, 32) for c in seq]).arrange(RIGHT, buff=0.22).next_to(hd, RIGHT, buff=0.4)
            nt = T(note, 24, col).next_to(cells, RIGHT, buff=0.35)
            built.add(VGroup(hd, cells, nt))
            if kind == "in":
                self.wait_cue("中序看着")
            self.play(FadeIn(hd), LaggedStart(*[FadeIn(c, shift=RIGHT * 0.1) for c in cells], lag_ratio=0.12),
                      run_time=1.2)
            self.play(FadeIn(nt), run_time=0.4)
        wrong = T("= A + B×C + D", 26, C_RED).next_to(built[1][1], DOWN, buff=0.25, aligned_edge=LEFT)
        self.play(FadeIn(wrong), Indicate(built[1][2], color=C_RED), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        et.freeze()
        self.play(FadeOut(VGroup(et, formula, built, wrong)), run_time=0.6)

    # ---------------------------------------------------------------- 层次周游：队列
    def level_beat(self):
        self.beat("level")
        tree = TreeView(D.FIG55, D.ROOT, top=2.7, dy=0.8)
        self.tree = tree
        self.play(Create(tree.edge_layer), *[GrowFromCenter(n) for n in tree.nodes.values()], run_time=1.0)
        bands = VGroup(*[Rectangle(width=9.0, height=0.62, stroke_width=0).set_fill(C_TEAL, 0.08).move_to(
            [0, 2.7 - 0.8 * d, 0]) for d in range(4)])
        self.play(FadeIn(bands), run_time=0.6)
        self.wait_cue("要靠队列")
        qlab = T("队列", 26, C_TEAL).move_to([-4.6, -1.0, 0])
        olab = T("访问", 26, C_YELLOW).move_to([-4.6, -2.1, 0])
        qbox = Rectangle(width=7.0, height=0.75, stroke_color=C_TEAL, stroke_width=2).move_to([0.1, -1.0, 0])
        front = T("出", 20, C_GREY).next_to(qbox, LEFT, buff=0.08).shift(UP * 0.25)
        rear = T("入", 20, C_GREY).next_to(qbox, RIGHT, buff=0.08).shift(UP * 0.25)
        self.play(FadeIn(VGroup(qlab, olab, qbox, front, rear)), run_time=0.6)
        w, qx0 = 0.7, -3.0
        qcells = {}
        a = T("A", 30).move_to([qx0, -1.0, 0])
        self.wait_cue("根先入队")
        self.play(TransformFromCopy(tree.nodes["A"][1], a), run_time=0.6)
        qcells["A"] = a
        queue = ["A"]
        out = VGroup()
        steps = D.level_order()
        st = max(0.5, min(1.1, (self.left() - 1.5) / len(steps)))
        for node, pushed, after in steps:
            cell = qcells.pop(node)
            dst = [-3.4 + 0.75 * len(out), -2.1, 0]
            anims = [cell.animate.move_to(dst).set_color(C_YELLOW),
                     tree.nodes[node][0].animate.set_stroke(C_YELLOW, 4)]
            queue.pop(0)
            for i, k in enumerate(queue):
                anims.append(qcells[k].animate.move_to([qx0 + w * i, -1.0, 0]))
            for c in pushed:
                m = T(c, 30).move_to([qx0 + w * len(queue), -1.0, 0])
                queue.append(c)
                qcells[c] = m
                anims.append(TransformFromCopy(tree.nodes[c][1], m))
            self.play(*anims, run_time=st)
            out.add(cell)
            assert queue == after
        self.wait(max(0.1, self.left() - 0.6))
        tree.freeze()
        self.play(FadeOut(VGroup(bands, qlab, olab, qbox, front, rear, out)), FadeOut(tree), run_time=0.6)

    # ---------------------------------------------------------------- 由中序 + 后序重建
    def rebuild_beat(self):
        self.beat("rebuild")
        shape, pre, trace = D.rebuild(D.IN, D.POST)
        tree = TreeView(shape, trace[0]["root"], top=1.1, dy=0.78, show=())
        xs = {k: tree.pos0[k][0] for k in D.IN}
        inrow = VGroup(*[T(c, 32, C_IN).move_to([xs[c], 2.85, 0]) for c in D.IN])
        prow = VGroup(*[T(c, 32, C_POST).move_to([-2.5 + 0.62 * i, 2.15, 0]) for i, c in enumerate(D.POST)])
        ih = T("中序", 24, C_IN).move_to([-5.0, 2.85, 0])
        ph = T("后序", 24, C_POST).move_to([-5.0, 2.15, 0])
        self.wait_cue("中序加后序")
        self.play(FadeIn(VGroup(ih, inrow)), FadeIn(VGroup(ph, prow)), run_time=0.8)
        self.add(tree)

        def seg_box(row, lo, hi, color):
            return SurroundingRectangle(VGroup(*row[lo:hi]), color=color, buff=0.08, corner_radius=0.08,
                                        stroke_width=3)

        def place(t, rt):
            k = t["root"]
            node = tree.add_node(k, tree.pos0[k])
            src = prow[t["post"][1] - 1]
            return [Indicate(src, color=WHITE, scale_factor=1.3), GrowFromCenter(node)]

        t0 = trace[0]
        self.wait_cue("后序的最后")
        self.play(*place(t0, 1.0), run_time=1.2)
        self.wait_cue("在中序里")
        k = t0["k"]
        lb, rb = seg_box(inrow, 0, k, C_BLUE), seg_box(inrow, k + 1, len(D.IN), C_GREEN)
        self.play(Indicate(inrow[k], color=WHITE, scale_factor=1.4), run_time=0.6)
        self.play(Create(lb), Create(rb), run_time=0.8)
        self.wait_cue("左子树有四个")
        plb, prb = seg_box(prow, 0, k, C_BLUE), seg_box(prow, k, len(D.POST) - 1, C_GREEN)
        self.play(TransformFromCopy(lb, plb), TransformFromCopy(rb, prb), run_time=1.0)
        self.wait_cue("对两段")
        self.play(FadeOut(VGroup(lb, rb, plb, prb)), run_time=0.3)
        rt = max(0.45, min(0.9, (self.left() - 2.6) / (len(trace) - 1)))
        boxes = VGroup()
        for t in trace[1:]:
            a, b = t["in"]
            p0, p1 = t["post"]
            bi, bp = seg_box(inrow, a, b, C_TEAL), seg_box(prow, p0, p1, C_TEAL)
            self.play(FadeIn(bi), FadeIn(bp), *place(t, rt), run_time=rt)
            self.remove(bi, bp)
        out = T(f"前序：{' '.join(pre)}", 28, C_PRE).move_to([0, -1.85, 0])
        self.play(FadeIn(out, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        tree.freeze()
        self.play(FadeOut(VGroup(inrow, prow, ih, ph, out)), FadeOut(tree), run_time=0.6)

    # ---------------------------------------------------------------- 为什么非要中序
    def unique_beat(self):
        self.beat("unique")
        left_chain = TreeView({"A": ("B", None), "B": ("C", None), "C": (None, None)}, "A", dx=0.75, dy=0.75,
                              top=2.3, cx=-4.0)
        right_chain = TreeView({"A": (None, "B"), "B": (None, "C"), "C": (None, None)}, "A", dx=0.75, dy=0.75,
                               top=2.3, cx=-1.2)
        cap1 = T("前序都是 A B C", 26, C_PRE).move_to([-2.6, -0.4, 0])
        self.play(*[Create(t.edge_layer) for t in (left_chain, right_chain)],
                  *[GrowFromCenter(n) for t in (left_chain, right_chain) for n in t.nodes.values()], run_time=1.0)
        self.play(FadeIn(cap1), run_time=0.5)
        self.wait_cue("前序加后序")
        t1 = TreeView({"A": ("B", None), "B": (None, None)}, "A", dx=0.8, dy=0.8, top=2.3, cx=2.2)
        t2 = TreeView({"A": (None, "B"), "B": (None, None)}, "A", dx=0.8, dy=0.8, top=2.3, cx=4.6)
        cap2 = T("前序 A B，后序 B A", 26, C_POST).move_to([3.4, -0.4, 0])
        self.play(*[Create(t.edge_layer) for t in (t1, t2)],
                  *[GrowFromCenter(n) for t in (t1, t2) for n in t.nodes.values()], run_time=1.0)
        self.play(FadeIn(cap2), run_time=0.5)
        q = T("B 在左还是在右？", 26, C_RED).move_to([3.4, -1.1, 0])
        self.play(FadeIn(q), run_time=0.5)
        self.wait_cue("必须有中序")
        ins = VGroup(T("中序 C B A", 24, C_IN).move_to([-4.0, -1.1, 0]), T("中序 A B C", 24, C_IN).move_to([-1.2, -1.1, 0]),
                     T("中序 B A", 24, C_IN).move_to([2.2, -1.8, 0]), T("中序 A B", 24, C_IN).move_to([4.6, -1.8, 0]))
        self.play(LaggedStart(*[FadeIn(i, shift=UP * 0.15) for i in ins], lag_ratio=0.15), FadeOut(q), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        for t in (left_chain, right_chain, t1, t2):
            t.freeze()
        self.play(FadeOut(VGroup(left_chain, right_chain, t1, t2, cap1, cap2, ins)), run_time=0.6)

    # ---------------------------------------------------------------- 收束：栈与队列的代价
    def recap_beat(self):
        self.beat("recap")
        tree = TreeView(D.FIG55, D.ROOT, top=2.7, dy=0.8, cx=-1.6)
        self.play(Create(tree.edge_layer), *[GrowFromCenter(n) for n in tree.nodes.values()], run_time=0.9)
        h = D.levels(D.FIG55, D.ROOT)
        wmax = D.widest(D.FIG55, D.ROOT)
        path = ["A", "B", "E", "G"]
        self.wait_cue("深度优先")
        stack = VGroup(*[VGroup(Rectangle(width=0.8, height=0.5, stroke_color=C_BLUE, stroke_width=2),
                                T(k, 26)) for k in path]).arrange(UP, buff=0.05).move_to([4.6, 1.3, 0])
        sl = T(f"栈：最深 {h} 层", 24, C_BLUE).next_to(stack, DOWN, buff=0.2)
        self.play(*[tree.nodes[k][0].animate.set_stroke(C_BLUE, 5) for k in path],
                  LaggedStart(*[FadeIn(s, shift=DOWN * 0.2) for s in stack], lag_ratio=0.2), FadeIn(sl), run_time=1.4)
        widest_level = ["D", "E", "F"]
        qrow = VGroup(*[VGroup(Square(0.55, stroke_color=C_TEAL, stroke_width=2), T(k, 26)) for k in widest_level])
        qrow.arrange(RIGHT, buff=0.05).move_to([4.6, -0.7, 0])
        ql = T(f"队列：最宽一层 {wmax} 个", 24, C_TEAL).next_to(qrow, DOWN, buff=0.2)
        self.play(*[tree.nodes[k][0].animate.set_stroke(C_TEAL, 5) for k in widest_level],
                  FadeIn(qrow), FadeIn(ql), run_time=1.2)
        self.wait_cue("前序、中序、后序")
        summary = VGroup(T("前序 · 中序 · 后序 = 一圈轮廓上的三个时机", 26, WHITE),
                         T("中序 + 前序/后序 → 唯一一棵树", 26, C_YELLOW)).arrange(DOWN, buff=0.22).move_to([0, -2.2, 0])
        self.play(FadeIn(summary[0], shift=UP * 0.2), run_time=0.8)
        self.play(FadeIn(summary[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left()))
        tree.freeze()
        self.play(FadeOut(VGroup(tree, stack, sl, qrow, ql, summary)), run_time=0.8)
