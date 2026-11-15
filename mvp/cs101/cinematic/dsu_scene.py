"""并查集：让森林越查越矮（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。所有父指针快照来自 dsudata（讲义 DSU 原样实现；
test_dsu.py 对撞讲义输出、期中题标准答案、随机数据的连通块与树高界）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsudata as D  # noqa: E402
from cine import *  # noqa: E402,F403

PALETTE = [C_BLUE, C_YELLOW, C_RED, C_GREEN, C_PURPLE, C_TEAL, "#FF8E5E", "#C9E265", "#9AA7FF", "#E68FC4"]


def forest_layout(parent: dict, cx=0.0, top=2.2, dx=0.95, dy=1.05, tree_gap=0.6) -> dict:
    """父指针 → 每个结点的坐标。树按根的编号排，孩子按编号排；叶子等距。"""
    kids = {k: [] for k in parent}
    roots = []
    for k in sorted(parent):
        if parent[k] == k:
            roots.append(k)
        else:
            kids[parent[k]].append(k)
    pos, cursor = {}, 0.0

    def place(k, d):
        nonlocal cursor
        if not kids[k]:
            pos[k] = [cursor, top - dy * d]
            cursor += dx
            return
        for c in kids[k]:
            place(c, d + 1)
        xs = [pos[c][0] for c in kids[k]]
        pos[k] = [(min(xs) + max(xs)) / 2, top - dy * d]
    for r in roots:
        place(r, 0)
        cursor += tree_gap
    span = cursor - tree_gap - dx
    out = {k: np.array([x - span / 2 + cx, y, 0]) for k, (x, y) in pos.items()}
    lo, hi = min(p[0] for p in out.values()), max(p[0] for p in out.values())
    shift = max(0.0, -6.5 - lo) - max(0.0, hi - 6.5)       # 合并过程中树横向铺开时，整体夹回画面内
    return {k: p + np.array([shift, 0, 0]) for k, p in out.items()}


class Forest(VGroup):
    """结点 + 指向父亲的箭头（箭头随结点位置和父指针实时重画）。"""

    def __init__(self, parent: dict, r=0.3, **lay):
        super().__init__()
        self.parent, self.r, self.lay = dict(parent), r, lay
        pos = forest_layout(self.parent, **lay)
        self.nodes = {}
        for k in parent:
            c = Circle(r, stroke_color=WHITE, stroke_width=3).set_fill(WHITE, 0.0)
            self.nodes[k] = VGroup(c, MathTex(str(k)).scale(0.75 * min(1.0, r / 0.27))).move_to(pos[k])
        self.arrows = {}
        for k in parent:
            a = self._arrow(k)
            a.add_updater(lambda m, k=k: m.become(self._arrow(k)))
            self.arrows[k] = a
        self.add(*self.arrows.values(), *self.nodes.values())
        self.paint_roots()

    def _arrow(self, k):
        p = self.parent[k]
        if p == k:
            return VMobject()
        a, b = self.nodes[k].get_center(), self.nodes[p].get_center()
        return Arrow(a, b, buff=self.r + 0.03, stroke_width=3, color=C_GREY, tip_length=0.16,
                     max_tip_length_to_length_ratio=0.3)

    def paint_roots(self):
        for k, n in self.nodes.items():
            n[0].set_stroke(C_YELLOW if self.parent[k] == k else WHITE, 4 if self.parent[k] == k else 3)

    def relayout(self, new_parent: dict | None = None, **lay):
        """更新父指针并返回把结点挪到新布局的动画（箭头靠 updater 跟着走）。"""
        if new_parent is not None:
            self.parent = dict(new_parent)
        self.lay.update(lay)
        pos = forest_layout(self.parent, **self.lay)
        anims = []
        for k, n in self.nodes.items():                 # 位置和根的描边放进同一个 target，避免两条动画抢同一对象
            is_root = self.parent[k] == k
            n.generate_target()
            n.target.move_to(pos[k])
            n.target[0].set_stroke(C_YELLOW if is_root else WHITE, 4 if is_root else 3)
            anims.append(MoveToTarget(n))
        return anims

    def freeze(self):
        for a in self.arrows.values():
            a.clear_updaters()


class ArrayRow(VGroup):
    """下标行 + 值行；set() 返回改一格的动画。"""

    def __init__(self, values, label="parent", w=0.7, y=-2.3, x0=None):
        super().__init__()
        n = len(values)
        x0 = -(n - 1) * w / 2 if x0 is None else x0
        self.w, self.cells, self.vals, self.values = w, VGroup(), VGroup(), list(values)
        for i, v in enumerate(values):
            sq = Square(w * 0.92, stroke_color=C_GREY, stroke_width=2).move_to([x0 + w * i, y, 0])
            self.cells.add(sq)
            self.vals.add(MathTex(str(v)).scale(0.65).move_to(sq))
        self.idx = VGroup(*[MathTex(str(i), color=C_GREY).scale(0.45).next_to(c, DOWN, buff=0.1)
                            for i, c in enumerate(self.cells)])
        self.head = T(label, 22, C_GREY).next_to(self.cells, LEFT, buff=0.3)
        self.add(self.cells, self.vals, self.idx, self.head)

    def set(self, i, v, color=C_YELLOW):
        self.values[i] = v
        new = MathTex(str(v), color=color).scale(0.65).move_to(self.cells[i])
        return [Transform(self.vals[i], new), Indicate(self.cells[i], color=color, scale_factor=1.15)]


class DSULesson(Lesson):
    def construct(self):
        for b in ("title", "ops", "forest", "chain", "weight", "compress", "code", "exam", "apps", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def walk(self, forest, path, color=C_YELLOW, rt=0.45):
        """沿父链走到根：光圈逐个结点移动，经过的箭头点亮。"""
        ring = Circle(forest.r + 0.12, stroke_color=color, stroke_width=6).move_to(forest.nodes[path[0]])
        self.play(Create(ring), run_time=rt)
        for k in path[1:]:
            self.play(ring.animate.move_to(forest.nodes[k]), run_time=rt)
        return ring

    # ---------------------------------------------------------------- 片头：谁和谁一伙
    def title_beat(self):
        self.beat("title")
        rng = np.random.default_rng(4)
        n = 14
        pts = [np.array([x, y, 0]) for x, y in zip(rng.uniform(-5.5, 5.5, n), rng.uniform(-1.6, 1.4, n))]
        dots = VGroup(*[Dot(p, radius=0.13, color=WHITE) for p in pts])
        self.play(LaggedStart(*[FadeIn(d, scale=0.3) for d in dots], lag_ratio=0.06), run_time=1.2)
        d = D.DSU(n)
        order = sorted(((float(np.linalg.norm(pts[i] - pts[j])), i, j) for i in range(n) for j in range(i + 1, n)))
        links = VGroup()
        step = max(0.25, min(0.5, (self.left() * 0.5) / 9))
        made = 0
        for _, i, j in order:
            if made >= 9:
                break
            if d.union(i, j):
                made += 1
                ln = Line(pts[i], pts[j], stroke_color=C_GREY, stroke_width=3)
                links.add(ln)
                roots = sorted({d.find(k) for k in range(n)})
                cols = {r: PALETTE[t % len(PALETTE)] for t, r in enumerate(roots)}
                self.play(Create(ln), *[dots[k].animate.set_color(cols[d.find(k)]) for k in range(n)
                                        if d.size[d.find(k)] > 1], run_time=step)
        q = T("在不在同一组？", 30, C_YELLOW).move_to([0, 2.4, 0])
        a, b = 0, max(range(n), key=lambda k: np.linalg.norm(pts[k] - pts[0]))
        rings = VGroup(*[Circle(0.28, stroke_color=C_YELLOW, stroke_width=5).move_to(pts[k]) for k in (a, b)])
        self.play(FadeIn(q), Create(rings), run_time=0.8)
        title = T("并查集", 72).move_to([0, 2.4, 0])
        sub = T("让森林越查越矮", 34, C_BLUE).next_to(title, DOWN, buff=0.2)
        self.wait(max(0.1, self.left() - 2.4))
        self.play(FadeOut(q), FadeOut(rings), Write(title), FadeIn(sub, shift=UP * 0.2),
                  VGroup(dots, links).animate.set_opacity(0.25), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(dots, links, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 两个操作
    def ops_beat(self):
        self.beat("ops")
        sets = [[0, 1, 2], [3, 4], [5, 6, 7]]
        cols = [C_BLUE, C_YELLOW, C_GREEN]
        blobs, labels = VGroup(), {}
        for s, col, cx in zip(sets, cols, (-4.0, 0.0, 4.0)):
            g = VGroup(*[VGroup(Circle(0.3, stroke_color=col, stroke_width=3),
                                MathTex(str(k)).scale(0.7)) for k in s]).arrange(RIGHT, buff=0.3)
            g.move_to([cx, 0.2, 0])
            for k, m in zip(s, g):
                labels[k] = m
            blob = RoundedRectangle(corner_radius=0.45, width=g.width + 0.6, height=1.2, stroke_color=col,
                                    stroke_width=2).set_fill(col, 0.08).move_to(g)
            blobs.add(VGroup(blob, g))
        self.play(LaggedStart(*[FadeIn(b, scale=0.9) for b in blobs], lag_ratio=0.2), run_time=1.2)
        f = VGroup(Text("find(x)", font=MONO, font_size=30, color=C_YELLOW), T("x 在哪个集合？返回代表元", 26))
        f.arrange(RIGHT, buff=0.4).move_to([0, 2.5, 0])
        self.wait_until(self.cue_start("find x", self.now))
        self.play(FadeIn(f, shift=DOWN * 0.2), Indicate(labels[4], color=C_YELLOW, scale_factor=1.4), run_time=1.0)
        u = VGroup(Text("union(x, y)", font=MONO, font_size=30, color=C_GREEN), T("把两个集合合并", 26))
        u.arrange(RIGHT, buff=0.4).move_to([0, 1.75, 0])
        self.wait_until(self.cue_start("union x y", self.now))
        self.play(FadeIn(u, shift=DOWN * 0.2), run_time=0.8)
        merged = RoundedRectangle(corner_radius=0.45, width=blobs[1][0].get_right()[0] - blobs[0][0].get_left()[0],
                                  height=1.2, stroke_color=C_BLUE, stroke_width=2).set_fill(C_BLUE, 0.08)
        merged.move_to([(blobs[0][0].get_left()[0] + blobs[1][0].get_right()[0]) / 2, 0.2, 0])
        self.play(ReplacementTransform(VGroup(blobs[0][0], blobs[1][0]), merged),
                  *[labels[k][0].animate.set_stroke(C_BLUE) for k in (3, 4)], run_time=1.2)
        apps = T("判连通 · 判环 · 等价类划分", 28, C_GREY).move_to([0, -1.6, 0])
        self.wait_until(self.cue_start("判连通", self.now))
        self.play(FadeIn(apps, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(merged, blobs[0][1], blobs[1][1], blobs[2], f, u, apps)), run_time=0.6)

    # ---------------------------------------------------------------- 父指针森林
    def forest_beat(self):
        self.beat("forest")
        snaps = D.forest_snapshots()
        par = {k: k for k in range(D.FOREST_N)}
        fo = Forest(par, top=0.9, dx=1.15, tree_gap=0.5)
        arr = ArrayRow(list(range(D.FOREST_N)), y=-2.25)
        self.play(FadeIn(fo), FadeIn(arr), run_time=1.0)
        roots_note = T("根：父亲就是自己（代表元）", 24, C_YELLOW).move_to([0, 2.9, 0])
        self.wait_until(self.cue_start("树根就是代表元", self.now))
        self.play(FadeIn(roots_note), *[Indicate(n, color=C_YELLOW) for n in fo.nodes.values()], run_time=1.0)
        self.wait_until(self.cue_start("union 先找到", self.now))
        step = max(0.8, min(1.4, (self.cue_start("find 沿着", self.now + 6) - self.now) / len(D.FOREST_UNIONS)))
        for (a, b), snap in zip(D.FOREST_UNIONS, snaps[1:]):
            changed = [i for i in range(D.FOREST_N) if snap[i] != fo.parent[i]]
            cap = Text(f"union({a}, {b})", font=MONO, font_size=26, color=C_GREEN).move_to([0, 2.3, 0])
            anims = fo.relayout({i: snap[i] for i in range(D.FOREST_N)})
            for i in changed:
                anims += arr.set(i, snap[i], C_GREEN)
            self.play(FadeIn(cap), *anims, run_time=step * 0.8)
            self.play(FadeOut(cap), run_time=step * 0.2)
        self.wait_until(self.cue_start("find 沿着", self.now))
        cap = Text("find(3)", font=MONO, font_size=26, color=C_YELLOW).move_to([0, 2.3, 0])
        self.play(FadeIn(cap), run_time=0.3)
        ring = self.walk(fo, D.path_to_root(snaps[-1], 3), rt=0.55)
        self.play(Flash(fo.nodes[0], color=C_YELLOW, flash_radius=0.55), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        fo.freeze()
        self.play(FadeOut(VGroup(fo, arr, roots_note, cap, ring)), run_time=0.6)

    # ---------------------------------------------------------------- 退化成链
    def chain_beat(self):
        self.beat("chain")
        na, gd = D.chain_vs_weighted()
        n = D.CHAIN_N
        fo = Forest({k: k for k in range(n)}, r=0.21, cx=0, top=0.0, dx=0.95, tree_gap=0.0)
        self.play(FadeIn(fo), run_time=0.6)
        title = T("朴素合并", 28, C_RED).move_to([-3.6, 3.2, 0])
        self.play(FadeIn(title), run_time=0.3)
        lay = dict(cx=-3.6, top=2.75, dy=0.74, dx=0.9, tree_gap=0.6)
        step = max(0.45, min(0.9, (self.cue_start("查最底下", self.now + 6) - self.now) / (n - 1)))
        for i, snap in enumerate(na[1:]):
            cap = Text(f"union({i}, {i + 1})", font=MONO, font_size=24, color=C_GREY).move_to([-0.9, 2.0, 0])
            self.play(*fo.relayout({k: snap[k] for k in range(n)}, **lay), FadeIn(cap), run_time=step * 0.8)
            self.remove(cap)
        self.wait_until(self.cue_start("查最底下", self.now))
        ring = self.walk(fo, D.path_to_root(na[-1], 0), color=C_RED, rt=0.32)
        on = MathTex(r"O(n)", color=C_RED).scale(1.2).move_to([-1.4, 0.6, 0])
        self.play(Write(on), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        self.chain = VGroup(fo, title, on, ring)
        self.chain_forest = fo

    # ---------------------------------------------------------------- 按大小合并
    def weight_beat(self):
        self.beat("weight")
        na, gd = D.chain_vs_weighted()
        n = D.CHAIN_N
        self.play(self.chain[3].animate.set_opacity(0), run_time=0.3)
        title = T("按大小合并", 28, C_GREEN).move_to([3.3, 3.2, 0])
        fo = Forest({k: k for k in range(n)}, r=0.27, cx=3.3, top=-0.6, dx=0.78, tree_gap=0.0)
        self.play(FadeIn(title), FadeIn(fo), run_time=0.7)
        lay = dict(cx=3.3, top=1.4, dy=1.6, dx=0.78, tree_gap=0.6)
        step = max(0.4, min(0.8, (self.cue_start("同样这一串", self.now + 5) - self.now + 1.5) / (n - 1)))
        for i, snap in enumerate(gd[1:]):
            self.play(*fo.relayout({k: snap[k] for k in range(n)}, **lay), run_time=step)
        one = T("树高 1", 26, C_GREEN).next_to(fo, DOWN, buff=0.35)
        self.play(FadeIn(one), run_time=0.5)
        self.wait_until(self.cue_start("至少翻一倍", self.now))
        self.chain_forest.freeze()
        fo.freeze()
        self.play(FadeOut(VGroup(self.chain[0], self.chain[1], self.chain[2], fo, title, one)), run_time=0.6)
        bars = VGroup()
        for i, v in enumerate((1, 2, 4, 8)):
            b = Rectangle(width=0.8, height=0.45 * v, stroke_width=0).set_fill(C_GREEN, 0.3 + 0.17 * i)
            b.move_to([-3.0 + 1.6 * i, -1.6, 0], aligned_edge=DOWN)
            bars.add(VGroup(b, MathTex(str(v)).scale(0.7).next_to(b, UP, buff=0.1),
                            T(f"深度 {i}", 22, C_GREY).next_to(b, DOWN, buff=0.15)))
        arrows = VGroup(*[CurvedArrow(bars[i][1].get_top() + UP * 0.05, bars[i + 1][1].get_top() + UP * 0.05,
                                      angle=-PI / 3, color=C_GREY, stroke_width=2, tip_length=0.12) for i in range(3)])
        x2 = VGroup(*[MathTex(r"\times 2", color=C_YELLOW).scale(0.55).next_to(a, UP, buff=0.03) for a in arrows])
        cap = T("深度每加一，所在集合至少翻一倍", 26).move_to([0, 2.9, 0])
        self.play(FadeIn(cap), LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in bars], lag_ratio=0.3), run_time=1.6)
        self.play(LaggedStart(*[AnimationGroup(Create(a), FadeIn(x)) for a, x in zip(arrows, x2)], lag_ratio=0.3),
                  run_time=1.2)
        self.wait_until(self.cue_start("最多翻", self.now))
        res = MathTex(r"\text{height}\le \log_2 n", color=C_GREEN).scale(1.1).move_to([3.9, 1.6, 0])
        self.play(Write(res), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(bars, arrows, x2, cap, res)), run_time=0.6)

    # ---------------------------------------------------------------- 路径压缩
    def compress_beat(self):
        self.beat("compress")
        before, path, root, after = D.compress_demo()
        fo = Forest(before, r=0.3, cx=0, top=2.4, dx=1.05, dy=1.1, tree_gap=0.6)
        self.play(FadeIn(fo, shift=UP * 0.2), run_time=1.0)
        self.wait_until(self.cue_start("对结点七", self.now))
        cap = Text("find(7)", font=MONO, font_size=28, color=C_YELLOW).move_to([-4.8, 2.8, 0])
        self.play(FadeIn(cap), run_time=0.3)
        ring = self.walk(fo, path, rt=0.5)
        hl = VGroup(*[fo.nodes[k][0].copy().set_stroke(C_YELLOW, 6) for k in path])
        self.play(FadeOut(ring), FadeIn(hl), run_time=0.4)
        self.wait_until(self.cue_start("七和五被改挂", self.now))
        self.play(*fo.relayout(after), FadeOut(hl), run_time=1.8, rate_func=rate_functions.ease_in_out_cubic)
        self.play(*[Indicate(fo.nodes[k], color=C_GREEN) for k in (7, 5)], run_time=0.8)
        self.wait_until(self.cue_start("九和十", self.now))
        self.play(*[Indicate(fo.nodes[k], color=C_BLUE) for k in (9, 10)], run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        fo.freeze()
        self.play(FadeOut(VGroup(fo, cap)), run_time=0.6)

    # ---------------------------------------------------------------- 标准实现
    def code_beat(self):
        self.beat("code")
        code = Code(code_string="def find(self, x):\n    root = x\n    while self.parent[root] != root:\n"
                                "        root = self.parent[root]\n    while self.parent[x] != root:\n"
                                "        self.parent[x], x = root, self.parent[x]\n    return root\n"
                                "def union(self, x, y):\n    rx, ry = self.find(x), self.find(y)\n"
                                "    if rx == ry:\n        return False\n"
                                "    if self.size[rx] < self.size[ry]:\n        rx, ry = ry, rx\n"
                                "    self.parent[ry] = rx\n    self.size[rx] += self.size[ry]\n"
                                "    self.count -= 1\n    return True\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 19})
        code.move_to([-1.6, 0.3, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.8)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.04, stroke_width=2)
            tag = T(txt, 22, col).next_to(code, RIGHT, buff=0.3).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
        mark([1, 2, 3], "第一趟", "第一趟：找到根", C_BLUE)
        mark([4, 5], "第二趟", "第二趟：沿途直接指向根", C_YELLOW)
        mark([9, 10], "根相同", "已在一组：False", C_GREY)
        mark([11, 12, 13, 14, 15], "小的挂到大的", "小挂大，count − 1", C_GREEN)
        self.wait_until(self.cue_start("接近常数", self.now))
        alpha = MathTex(r"O(\alpha(n))", color=C_YELLOW).scale(1.1).next_to(tags[-1], DOWN, buff=0.6).align_to(tags[-1], LEFT)
        self.play(Write(alpha), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, tags, alpha)), run_time=0.6)

    # ---------------------------------------------------------------- 期中手算题
    def exam_beat(self):
        self.beat("exam")
        steps = dict(D.exam_steps())
        p = steps["init"]
        arr = ArrayRow(p, label="p", w=0.72, y=-2.2)
        par = {i: v for i, v in enumerate(D.exam_as_parent(p))}
        fo = Forest(par, r=0.27, cx=0, top=2.5, dx=0.85, dy=0.95, tree_gap=0.7)
        rule = T("根存 −(集合大小)，非根存父下标", 22, C_GREY).move_to([0, 3.35, 0])
        self.play(FadeIn(arr), FadeIn(fo), FadeIn(rule), run_time=1.0)
        self.wait_until(self.cue_start("一共四个集合", self.now))
        roots = [i for i, v in enumerate(p) if v < 0]
        four = T(f"{len(roots)} 个集合", 26, C_YELLOW).move_to([5.6, 1.4, 0])
        self.play(*[Indicate(arr.cells[i], color=C_YELLOW) for i in roots],
                  *[Flash(fo.nodes[i], color=C_YELLOW, flash_radius=0.45) for i in roots], FadeIn(four), run_time=1.2)
        self.play(FadeOut(four), run_time=0.3)

        def apply(key, cue, cap_txt, col):
            self.wait_until(self.cue_start(cue, self.now))
            new = steps[key]
            cap = Text(cap_txt, font=MONO, font_size=26, color=col).move_to([-5.2, 1.4, 0])
            cur = list(arr.values)
            anims = [FadeIn(cap)]
            for i in range(10):
                if new[i] != cur[i]:
                    anims += arr.set(i, new[i], col)
            anims += fo.relayout({i: v for i, v in enumerate(D.exam_as_parent(new))})
            self.play(*anims, run_time=1.4)
            self.play(FadeOut(cap), run_time=0.3)
        apply("find2", "先 find 二", "find(2)", C_BLUE)
        apply("find6", "再 find 六", "find(6)", C_BLUE)
        apply("link", "小的挂到大的", "4 → 0", C_GREEN)
        apply("find6b", "最后再 find 六", "find(6)", C_YELLOW)
        self.wait(max(0.1, self.left() - 0.6))
        fo.freeze()
        self.play(FadeOut(VGroup(arr, fo, rule)), run_time=0.6)

    # ---------------------------------------------------------------- 应用：数连通块、判环
    def apps_beat(self):
        self.beat("apps")
        n, pairs = D.RELIGION
        counts = D.religion_counts()
        fo = Forest({k: k for k in range(n)}, r=0.26, cx=-1.2, top=1.6, dx=0.95, dy=0.9, tree_gap=0.0)
        cnt = VGroup(T("count", 24, C_GREY), Integer(counts[0], color=C_YELLOW).scale(1.1)).arrange(RIGHT, buff=0.3)
        cnt.move_to([5.4, 2.9, 0])
        self.play(FadeIn(fo), FadeIn(cnt), run_time=0.8)
        d = D.DSU(n)
        for (a, b), c in zip(pairs, counts[1:]):
            d.union(a, b)
            cap = Text(f"union({a}, {b})", font=MONO, font_size=24, color=C_GREEN).move_to([5.4, 2.3, 0])
            self.play(*fo.relayout({k: d.parent[k] for k in range(n)}, tree_gap=0.45), FadeIn(cap),
                      ChangeDecimalToValue(cnt[1], c), run_time=1.0)  # 位数变少时 .animate.set_value 会报错
            self.remove(cap)
        self.play(Indicate(cnt, color=C_YELLOW, scale_factor=1.3), run_time=0.7)
        self.wait_until(self.cue_start("判环", self.now))
        fo.freeze()
        self.play(FadeOut(fo), FadeOut(cnt), run_time=0.5)
        tri = {0: np.array([-1.6, -1.6, 0]), 1: np.array([1.6, -1.6, 0]), 2: np.array([0, 1.0, 0])}
        vs = {k: VGroup(Circle(0.32, stroke_color=WHITE, stroke_width=3), MathTex(str(k)).scale(0.8)).move_to(p)
              for k, p in tri.items()}
        self.play(*[FadeIn(v) for v in vs.values()], run_time=0.5)
        rets = D.cycle_returns()
        edges = VGroup()
        for (a, b), ok in zip(D.CYCLE_EDGES, rets):
            col = C_GREEN if ok else C_RED
            ln = Line(tri[a], tri[b], buff=0.34, stroke_color=col, stroke_width=4)
            edges.add(ln)
            res = Text(f"union({a}, {b}) → {ok}", font=MONO, font_size=24, color=col)
            res.move_to([4.6, 1.0 - 0.6 * len(edges), 0])
            if not ok:
                self.wait_until(self.cue_start("加入边二零", self.now))
            self.play(Create(ln), FadeIn(res, shift=LEFT * 0.2), run_time=0.9)
            edges.add(res)
        cyc = T("环！", 34, C_RED).move_to([0, -0.5, 0])
        self.play(*[Indicate(m, color=C_RED) for m in vs.values()], FadeIn(cyc, scale=1.5), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*vs.values(), edges, cyc)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(
            VGroup(T("两个操作", 30, C_GREY), Text("find · union", font=MONO, font_size=30)).arrange(RIGHT, buff=0.6),
            VGroup(T("按大小合并", 30, C_GREEN), T("让树长不高", 30)).arrange(RIGHT, buff=0.6),
            VGroup(T("路径压缩", 30, C_YELLOW), T("让树越查越矮", 30)).arrange(RIGHT, buff=0.6),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([0, 0.7, 0])
        step = max(0.7, (self.left() - 1.0) / 3)
        for r in rows:
            self.play(FadeIn(r, shift=UP * 0.2), run_time=step * 0.6)
            self.wait(step * 0.4)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 9 周 并查集 P16–P30 · OpenJudge 02524", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
