"""Huffman 编码：让常用的字符更短（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。森林怎样一步步并成一棵树、每个字符的编码、
译码时走的每一步，都来自 huffmandata（讲义 teaching.hpp 的 MinHeap + HuffmanTree 逐行移植并插桩；
test_huffman.py 对撞讲义码表、195/228、14 位电文、图 5.18 的三个 WPL，并穷举树形验证最优）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import huffmandata as D  # noqa: E402
from cine import *  # noqa: E402,F403

LCOL = {"a": C_BLUE, "b": C_RED, "c": C_PURPLE, "d": "#FF8E5E", "e": C_YELLOW, "f": C_TEAL, "g": C_GREEN}


def from_nested(t):
    """图 5.18 那种嵌套二元组 → huffmandata.Node 树。"""
    if isinstance(t, int):
        return D.Node(t, "")
    l, r = from_nested(t[0]), from_nested(t[1])
    return D.Node(l.weight + r.weight, "", l, r)


def mono(s, size=30, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


class TreeView:
    """若干棵树（森林）；layout 给出每个结点的位置，edges 用 updater 跟着结点走。"""

    def __init__(self, roots, S=1.0, DY=0.85, top=2.3, cx=0.0, gap=0.6, r=0.3, letters=True, wscale=0.62):
        self.S, self.DY, self.top, self.cx, self.gap, self.r = S, DY, top, cx, gap, r
        self.letters, self.wscale = letters, wscale
        self.circ, self.wlab, self.let, self.edges, self.kids = {}, {}, {}, {}, {}
        self.group = VGroup()
        pos = self.layout(roots)
        for root in roots:
            self._make_rec(root, pos)

    def layout(self, roots):
        pos, cursor = {}, 0.0

        def place(n, d):
            nonlocal cursor
            if n.leaf:
                pos[n.id] = [cursor, self.top - self.DY * d]
                cursor += self.S
                return
            place(n.left, d + 1)
            place(n.right, d + 1)
            pos[n.id] = [(pos[n.left.id][0] + pos[n.right.id][0]) / 2, self.top - self.DY * d]
        for root in roots:
            place(root, 0)
            cursor += self.gap
        span = cursor - self.gap - self.S
        return {k: np.array([x - span / 2 + self.cx, y, 0]) for k, (x, y) in pos.items()}

    def _make_rec(self, n, pos):
        self.make_node(n, pos[n.id])
        if not n.leaf:
            for c in (n.left, n.right):
                self._make_rec(c, pos)
                self.make_edge(n, c)

    def make_node(self, n, p):
        col = LCOL.get(n.symbol, C_GREY) if n.leaf else WHITE
        c = Circle(self.r, stroke_color=col, stroke_width=3).set_fill(col, 0.15 if n.leaf else 0.06).move_to(p)
        w = MathTex(str(n.weight), color=WHITE).scale(self.wscale * (0.85 if n.weight >= 10 else 1.0)).move_to(p)
        w.add_updater(lambda m, c=c: m.move_to(c.get_center()))
        self.circ[n.id], self.wlab[n.id] = c, w
        self.group.add(c, w)
        if n.leaf and n.symbol and self.letters:
            lt = mono(n.symbol, 28, col).next_to(c, DOWN, buff=0.08)
            lt.add_updater(lambda m, c=c: m.next_to(c, DOWN, buff=0.08))
            self.let[n.id] = lt
            self.group.add(lt)
        return c, w

    def make_edge(self, p, ch):
        a, b = self.circ[p.id], self.circ[ch.id]
        r = self.r

        def seg(m):
            s, e = a.get_center(), b.get_center()
            u = (e - s) / max(1e-6, np.linalg.norm(e - s))
            m.put_start_and_end_on(s + u * r, e - u * r)
        ln = Line(a.get_center() + DOWN * 0.01, b.get_center(), stroke_color=C_GREY, stroke_width=3)
        seg(ln)
        ln.add_updater(seg)
        self.edges[ch.id] = ln
        self.kids.setdefault(p.id, []).append(ch.id)
        self.group.add(ln)
        return ln

    def node_group(self, nid):
        g = VGroup(self.circ[nid], self.wlab[nid])
        if nid in self.let:
            g.add(self.let[nid])
        return g

    def moves(self, roots):
        pos = self.layout(roots)
        return [self.circ[k].animate.move_to(p) for k, p in pos.items()]

    def all_ids(self, n):
        out = [n.id]
        if not n.leaf:
            out += self.all_ids(n.left) + self.all_ids(n.right)
        return out

    def subtree(self, n):
        ids = self.all_ids(n)
        g = VGroup(*[self.node_group(k) for k in ids])
        g.add(*[self.edges[k] for k in ids if k in self.edges and k != n.id])
        return g

    def clear_updaters(self):
        for m in self.group:
            m.clear_updaters()


class HuffmanLesson(Lesson):
    def construct(self):
        for b in ("title", "prefix", "wpl", "build1", "build2", "code", "total", "decode", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    # ---------------------------------------------------------------- 片头：一段电文
    def title_beat(self):
        self.beat("title")
        title = T("Huffman 编码", 64).move_to([0, 2.7, 0])
        self.play(Write(title), run_time=1.2)
        msg = D.MSG
        mcol = {"a": C_BLUE, "b": C_RED, "c": C_PURPLE, "d": "#FF8E5E"}
        row = VGroup(*[mono(ch, 52, mcol[ch]) for ch in msg]).arrange(RIGHT, buff=0.55).move_to([0, 1.0, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=DOWN * 0.2) for m in row], lag_ratio=0.12), run_time=1.6)
        self.at("如果每个字符")
        fixed = {"a": "00", "b": "01", "c": "10", "d": "11"}
        codes = VGroup(*[mono(fixed[ch], 30, C_GREY).next_to(m, DOWN, buff=0.35) for ch, m in zip(msg, row)])
        self.play(LaggedStart(*[FadeIn(c) for c in codes], lag_ratio=0.1), run_time=1.2)
        k, total = D.fixed_bits(4, len(msg))
        tot = VGroup(MathTex(rf"{len(msg)}\times{k}=", color=C_GREY).scale(0.9),
                     MathTex(str(total), color=C_YELLOW).scale(1.1)).arrange(RIGHT, buff=0.15).move_to([0, -1.1, 0])
        self.play(FadeIn(tot, shift=UP * 0.2), run_time=0.7)
        self.at("出现得多的")
        cnt = {}
        for ch in msg:
            cnt[ch] = cnt.get(ch, 0) + 1
        a_s = [m for ch, m in zip(msg, row) if ch == "a"]
        tip = VGroup(mono("a", 30, C_BLUE), MathTex(rf"\times {cnt['a']}", color=C_BLUE).scale(0.8),
                     T("→ 码要更短", 26, C_YELLOW)).arrange(RIGHT, buff=0.2).move_to([0, -2.2, 0])
        self.play(*[Indicate(m, color=C_BLUE, scale_factor=1.3) for m in a_s], FadeIn(tip, shift=UP * 0.2),
                  run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, row, codes, tot, tip)), run_time=0.6)

    # ---------------------------------------------------------------- 有歧义的变长码
    def prefix_beat(self):
        self.beat("prefix")
        bad = [("a", "0"), ("b", "1"), ("c", "01"), ("d", "10")]
        mcol = {"a": C_BLUE, "b": C_RED, "c": C_PURPLE, "d": "#FF8E5E"}
        tab = VGroup(*[VGroup(mono(s, 32, mcol[s]), mono("=", 28, C_GREY), mono(c, 32)).arrange(RIGHT, buff=0.25)
                       for s, c in bad]).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([-4.6, 0.6, 0])
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in tab], lag_ratio=0.3), run_time=1.6)
        self.at("电文确实变短")
        rx = mono("011", 64, C_YELLOW).move_to([1.4, 2.0, 0])
        lab = T("收到", 26, C_GREY).next_to(rx, LEFT, buff=0.4)
        self.play(FadeIn(lab), Write(rx), run_time=0.9)
        self.wait(1.0)
        bits = list("011")
        p1 = VGroup(*[mono(b, 40) for b in bits]).arrange(RIGHT, buff=0.6).move_to([0.2, 0.3, 0])
        r1 = VGroup(*[mono(x, 34, mcol[x]) for x in "abb"])
        for m, b in zip(r1, p1):
            m.next_to(b, DOWN, buff=0.25)
        bars1 = VGroup(*[Line(UP * 0.3, DOWN * 0.3, stroke_color=C_GREY).move_to((p1[i].get_right() + p1[i + 1].get_left()) / 2)
                         for i in range(2)])
        p2 = VGroup(mono("01", 40), mono("1", 40)).arrange(RIGHT, buff=0.6).move_to([3.6, 0.3, 0])
        r2 = VGroup(mono("c", 34, mcol["c"]).next_to(p2[0], DOWN, buff=0.25), mono("b", 34, mcol["b"]).next_to(p2[1], DOWN, buff=0.25))
        bars2 = Line(UP * 0.3, DOWN * 0.3, stroke_color=C_GREY).move_to((p2[0].get_right() + p2[1].get_left()) / 2)
        self.play(TransformFromCopy(rx, p1), run_time=0.7)
        self.play(Create(bars1), FadeIn(r1, shift=UP * 0.2), run_time=0.8)
        self.play(TransformFromCopy(rx, p2), run_time=0.7)
        self.play(Create(bars2), FadeIn(r2, shift=UP * 0.2), run_time=0.8)
        q = T("两种读法", 28, C_RED).move_to([1.9, -1.2, 0])
        self.play(FadeIn(q), run_time=0.5)
        self.at("毛病出在")
        self.play(tab[0][2].animate.set_color(C_RED), tab[2][2].animate.set_color(C_RED), run_time=0.6)
        pre = VGroup(mono("0", 34, C_RED), T("是", 26, C_GREY), mono("01", 34, C_RED), T("的前缀", 26, C_GREY))
        pre.arrange(RIGHT, buff=0.2).move_to([1.9, -1.2, 0])
        self.play(ReplacementTransform(q, pre), run_time=0.8)
        self.at("所以要求")
        rule = T("前缀码：任何编码都不是另一个编码的前缀", 30, C_GREEN).move_to([0, -2.3, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tab, rx, lab, p1, r1, bars1, p2, r2, bars2, pre, rule)), run_time=0.6)

    # ---------------------------------------------------------------- 带权路径长度
    def wpl_beat(self):
        self.beat("wpl")
        xs = {"a": -4.6, "b": 0.0, "c": 4.6}
        views, labels = {}, VGroup()
        for k, t in D.FIG518_TREES.items():
            root = from_nested(t)
            v = TreeView([root], S=0.8, DY=0.78, top=2.4, cx=xs[k], r=0.26, letters=False, wscale=0.6)
            views[k] = (v, root)
        v, root = views["a"]
        self.play(*[Create(m) if isinstance(m, Line) else FadeIn(m) for m in v.group], run_time=1.0)
        self.at("权乘深度")
        rows = {}
        for k, t in D.FIG518_TREES.items():
            leaves = []

            def walk(x, d):
                if isinstance(x, int):
                    leaves.append((x, d))
                else:
                    walk(x[0], d + 1)
                    walk(x[1], d + 1)
            walk(t, 0)
            expr = MathTex("+".join(rf"{w}\cdot{d}" for w, d in leaves), color=C_GREY).scale(0.55)
            val = MathTex(str(D.nested_wpl(t)), color=WHITE).scale(1.1)
            g = VGroup(expr, val).arrange(DOWN, buff=0.25).move_to([xs[k], -1.3, 0])
            rows[k] = g
        self.play(FadeIn(rows["a"], shift=UP * 0.2), run_time=0.8)
        self.at("同样四个权")
        for k in ("b", "c"):
            v, root = views[k]
            self.play(*[Create(m) if isinstance(m, Line) else FadeIn(m) for m in v.group], run_time=0.9)
            self.play(FadeIn(rows[k], shift=UP * 0.2), run_time=0.6)
        self.at("权大的叶子")
        v, root = views["c"]
        six = [k for k, c in v.wlab.items() if c.get_tex_string() == "6"][0]
        best = SurroundingRectangle(rows["c"][1], color=C_GREEN, buff=0.12)
        self.play(rows["c"][1].animate.set_color(C_GREEN), Create(best),
                  v.circ[six].animate.set_stroke(C_YELLOW, 6), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        grp = VGroup(*[views[k][0].group for k in views], *rows.values(), best)
        self.play(FadeOut(grp), run_time=0.6)
        for k in views:
            views[k][0].clear_updaters()

    # ---------------------------------------------------------------- 构造：反复合并最小的两棵
    def build_beat_common(self):
        root, leaves, merges = D.fig_tree()
        self.root, self.merges = root, merges
        self.forest = sorted(leaves, key=lambda n: (n.weight, n.id))
        self.tv = TreeView(self.forest, S=1.0, DY=0.85, top=2.3, cx=0.0, gap=0.65)

    def do_merge(self, k, rt=1.0):
        tv = self.tv
        left, right, parent = self.merges[k]
        self.play(tv.circ[left.id].animate.set_stroke(C_YELLOW, 6), tv.circ[right.id].animate.set_stroke(C_YELLOW, 6),
                  run_time=0.35 * rt)
        mid = (tv.circ[left.id].get_center() + tv.circ[right.id].get_center()) / 2
        c, w = tv.make_node(parent, mid + UP * 0.42)      # 新根先冒在两棵中间偏上，别碰到顶部那行字
        e1, e2 = tv.make_edge(parent, left), tv.make_edge(parent, right)
        self.forest = [t for t in self.forest if t not in (left, right)]
        self.forest.append(parent)
        self.forest.sort(key=lambda n: (n.weight, n.id))
        pos = tv.layout(self.forest)
        self.play(FadeIn(c), FadeIn(w), Create(e1), Create(e2), run_time=0.45 * rt)
        lcol = LCOL.get(left.symbol, WHITE) if left.leaf else WHITE
        rcol = LCOL.get(right.symbol, WHITE) if right.leaf else WHITE
        anims = [tv.circ[k].animate.move_to(p) for k, p in pos.items() if k not in (left.id, right.id)]
        anims += [tv.circ[left.id].animate.move_to(pos[left.id]).set_stroke(lcol, 3),
                  tv.circ[right.id].animate.move_to(pos[right.id]).set_stroke(rcol, 3)]
        self.play(*anims, run_time=0.8 * rt)

    def build1_beat(self):
        self.beat("build1")
        self.build_beat_common()
        tv = self.tv
        rule = T("每次取出权最小的两棵，合成一棵", 28, C_YELLOW).move_to([0, 3.3, 0])
        self.play(FadeIn(rule, shift=DOWN * 0.2), run_time=0.8)
        self.at("七个字符")
        self.play(LaggedStart(*[FadeIn(tv.node_group(n.id), shift=DOWN * 0.2) for n in self.forest], lag_ratio=0.15),
                  run_time=1.8)
        pq = T("按权排好：最左边两棵最小", 22, C_GREY).move_to([0, 0.9, 0])
        self.play(FadeIn(pq), run_time=0.5)
        self.at("最小的是")
        self.play(FadeOut(pq), run_time=0.3)
        self.do_merge(0, rt=1.6)
        self.at("接着六和七")
        self.do_merge(1)
        self.do_merge(2)
        self.rule = rule
        self.wait(max(0.1, self.left() - 0.2))

    def build2_beat(self):
        self.beat("build2")
        for k in (3, 4, 5):
            self.do_merge(k, rt=1.2)
        self.at("每一轮")
        cost = VGroup(T("每轮取两次最小：最小堆", 24, C_GREY), MathTex(r"O(\log n)", color=C_BLUE).scale(0.8),
                      MathTex(r"\Rightarrow O(n\log n)", color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.3)
        cost.move_to([0, 3.3, 0])
        self.play(ReplacementTransform(self.rule, cost), run_time=0.9)
        self.cost = cost
        self.wait(max(0.1, self.left() - 0.6))
        tv = self.tv
        self.play(FadeOut(cost), *[m.animate.shift(LEFT * 2.6) for m in tv.circ.values()], run_time=0.6)

    # ---------------------------------------------------------------- 编码：左 0 右 1
    def code_beat(self):
        self.beat("code")
        tv, root = self.tv, self.root
        bits = VGroup()
        for p_id, kids in tv.kids.items():
            for k, cid in enumerate(kids):
                e = tv.edges[cid]
                d = e.get_end() - e.get_start()
                nrm = np.array([-d[1], d[0], 0]) / np.linalg.norm(d)
                if k == 0:
                    nrm = -nrm if nrm[0] > 0 else nrm
                else:
                    nrm = -nrm if nrm[0] < 0 else nrm
                b = MathTex(str(k), color=C_TEAL if k == 0 else C_YELLOW).scale(0.6)
                b.move_to(e.get_center() + nrm * 0.22)
                bits.add(b)
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in bits], lag_ratio=0.05), run_time=1.6)
        codes = D.codes(root)
        order = sorted(codes, key=lambda s: (len(codes[s]), s))
        tab = VGroup()
        for s in ["a", "b", "c", "d", "e", "f", "g"]:
            r = VGroup(mono(s, 28, LCOL[s]), MathTex(str(D.FREQ[s]), color=C_GREY).scale(0.6), mono(codes[s], 28))
            tab.add(r)
        for k, r in enumerate(tab):
            y = 2.5 - 0.52 * k
            r[0].move_to([2.6, y, 0])
            r[1].move_to([3.5, y, 0])
            r[2].move_to([4.4, y, 0], aligned_edge=LEFT)
        head = VGroup(T("字符", 20, C_GREY).move_to([2.6, 3.15, 0]), T("频率", 20, C_GREY).move_to([3.5, 3.15, 0]),
                      T("编码", 20, C_GREY).move_to([4.4, 3.15, 0], aligned_edge=LEFT))
        self.play(FadeIn(head), run_time=0.4)
        leaf_of = {}

        def find(n, path):
            if n.leaf:
                leaf_of[n.symbol] = path + [n.id]
                return
            find(n.left, path + [n.id])
            find(n.right, path + [n.id])
        find(root, [])
        self.at("从根走到叶子")
        row = {s: tab[k] for k, s in enumerate("abcdefg")}
        for k, s in enumerate(order):
            path = leaf_of[s]
            rt = 1.2 if k == 0 else 0.55
            self.play(*[tv.edges[nid].animate.set_stroke(LCOL[s], 5) for nid in path[1:]],
                      FadeIn(row[s][0]), FadeIn(row[s][1]), run_time=rt * 0.5)
            self.play(TransformFromCopy(VGroup(*[tv.edges[nid] for nid in path[1:]]), row[s][2]),
                      *[tv.edges[nid].animate.set_stroke(C_GREY, 3) for nid in path[1:]], run_time=rt * 0.5)
        self.at("出现最多")
        two = [row[s][2] for s in "ega"]
        five = [row[s][2] for s in "bd"]
        self.play(*[Indicate(m, color=C_GREEN) for m in two], run_time=0.9)
        self.play(*[Indicate(m, color=C_RED) for m in five], run_time=0.9)
        self.bits, self.tab, self.head = bits, tab, head
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 总长
    def total_beat(self):
        self.beat("total")
        codes, root = D.codes(self.root), self.root
        tot = sum(D.FREQ[s] * len(codes[s]) for s in codes)
        e1 = VGroup(T("Σ 频率×码长 =", 22, C_GREY),
                    MathTex(str(tot), color=C_YELLOW).scale(0.9)).arrange(RIGHT, buff=0.15).move_to([4.1, -1.75, 0])
        self.play(FadeIn(e1, shift=UP * 0.2), run_time=0.9)
        self.at("七个字符用等长")
        k, fixed = D.fixed_bits(len(codes), root.weight)
        e2 = VGroup(T("等长", 22, C_GREY), MathTex(rf"{root.weight}\times{k}=", color=C_GREY).scale(0.7),
                    MathTex(str(fixed), color=C_RED).scale(0.9)).arrange(RIGHT, buff=0.15).move_to([4.1, -2.5, 0])
        self.play(FadeIn(e2, shift=UP * 0.2), run_time=0.9)
        self.at("再把所有内部")
        internal = [p for _, _, p in self.merges]
        tv = self.tv
        s = "+".join(str(p.weight) for p in internal)
        e3 = VGroup(MathTex(s, color=C_YELLOW).scale(0.7), MathTex("=", str(tot)).scale(0.8))
        e3[1][1].set_color(C_YELLOW)
        e3.arrange(RIGHT, buff=0.15).move_to([-2.6, 3.3, 0])
        step = 0.5
        for p in internal:
            self.play(tv.circ[p.id].animate.set_stroke(C_YELLOW, 5), Indicate(tv.wlab[p.id], color=C_YELLOW),
                      run_time=step)
        self.play(FadeIn(e3, shift=DOWN * 0.2), run_time=0.8)
        self.at("这不是巧合")
        # 叶子 b 的权在它的五个祖先里各出现一次
        target = next(n for n in self._leaves(self.root) if n.symbol == "b")
        path = self._path(self.root, target)
        for nid in path[:-1]:
            self.play(Indicate(tv.circ[nid], color=LCOL["b"], scale_factor=1.25), run_time=0.45)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(e1, e2, e3, self.tab, self.head)),
                  *[tv.circ[p.id].animate.set_stroke(WHITE, 3) for p in internal], run_time=0.6)

    def _leaves(self, n):
        return [n] if n.leaf else self._leaves(n.left) + self._leaves(n.right)

    def _path(self, n, target):
        if n is target:
            return [n.id]
        if n.leaf:
            return None
        for c in (n.left, n.right):
            p = self._path(c, target)
            if p:
                return [n.id] + p
        return None

    # ---------------------------------------------------------------- 前缀性与译码
    def decode_beat(self):
        self.beat("decode")
        tv, root = self.tv, self.root
        leaves = self._leaves(root)
        self.play(*[tv.circ[n.id].animate.set_stroke(LCOL[n.symbol], 6) for n in leaves], run_time=0.8)
        self.at("字符只住在")
        f = next(n for n in leaves if n.symbol == "f")
        c = next(n for n in leaves if n.symbol == "c")
        pc = self._path(root, c)
        self.play(*[tv.edges[k].animate.set_stroke(LCOL["c"], 6) for k in pc[1:]], run_time=0.9)
        self.play(Indicate(tv.circ[f.id], color=LCOL["f"], scale_factor=1.3), run_time=0.9)
        note = T("叶子不在别的叶子的路上", 26, C_GREEN).move_to([3.4, 1.0, 0])
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.at("译码就用")
        self.play(*[tv.edges[k].animate.set_stroke(C_GREY, 3) for k in pc[1:]], FadeOut(note), run_time=0.4)
        codes = D.codes(root)
        bits = "".join(codes[ch] for ch in D.WORD)
        text, steps = D.decode_trace(root, bits)
        row = VGroup(*[mono(b, 36) for b in bits]).arrange(RIGHT, buff=0.12).move_to([3.6, 2.4, 0])
        self.play(FadeIn(row), run_time=0.5)
        dot = Circle(tv.r + 0.09, stroke_color=C_YELLOW, stroke_width=6).move_to(tv.circ[root.id].get_center())   # 空心圈：不盖住结点里的权
        self.add(dot)
        outs = VGroup()
        t_end = self.cue_start("这串比特", self.now + 6) + 1.5
        step = max(0.3, min(0.55, (t_end - self.now) / (len(bits) + 4)))
        start = 0
        for k, nd, out in steps:
            self.play(dot.animate.move_to(tv.circ[nd.id].get_center()), row[k].animate.set_color(C_YELLOW),
                      run_time=step)
            if out:
                ch = mono(out, 48, LCOL[out])
                ch.move_to([1.8 + 0.85 * len(outs), 0.9, 0])
                ul = Line(row[start].get_corner(DL) + DOWN * 0.08, row[k].get_corner(DR) + DOWN * 0.08,
                          stroke_color=LCOL[out], stroke_width=4)
                self.play(TransformFromCopy(tv.let[nd.id], ch), Create(ul), Flash(tv.circ[nd.id], color=LCOL[out]),
                          run_time=step * 1.3)
                outs.add(ch, ul)
                start = k + 1
                self.play(dot.animate.move_to(tv.circ[root.id].get_center()), run_time=step * 0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tv.group, self.bits, row, outs, dot)), run_time=0.6)
        tv.clear_updaters()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        root, leaves, merges = D.msg_tree()
        codes = D.codes(root)
        tv = TreeView([root], S=0.9, DY=0.78, top=2.2, cx=-3.6, r=0.27, wscale=0.6)
        msg = VGroup(*[mono(ch, 34, LCOL[ch]) for ch in D.MSG]).arrange(RIGHT, buff=0.18).move_to([-3.6, 3.3, 0])
        self.play(FadeIn(msg), *[Create(m) if isinstance(m, Line) else FadeIn(m) for m in tv.group], run_time=1.2)
        tab = VGroup(*[VGroup(mono(s, 26, LCOL[s]), mono(codes[s], 26)).arrange(RIGHT, buff=0.3)
                       for s in sorted(codes)]).arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([-1.2, 0.6, 0])
        self.play(LaggedStart(*[FadeIn(r) for r in tab], lag_ratio=0.2), run_time=1.2)
        bits = "".join(codes[c] for c in D.MSG)
        k, fixed = D.fixed_bits(len(codes), len(D.MSG))
        res = VGroup(MathTex(str(len(bits)), color=C_GREEN).scale(1.0), T("位", 24), MathTex("<", str(fixed)).scale(0.9),
                     T("位", 24)).arrange(RIGHT, buff=0.15).move_to([-3.6, -1.6, 0])
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.8)
        wl = VGroup(MathTex(r"=\text{WPL}", color=C_GREEN).scale(0.8)).next_to(res, DOWN, buff=0.25)
        self.play(FadeIn(wl), run_time=0.6)
        self.at("但如果八个")
        eq = [D.Node(1, s) for s in "stuvwxyz"]
        r8, _, _ = D.build([n.symbol for n in eq], [1] * 8)
        tv8 = TreeView([r8], S=0.62, DY=0.8, top=2.2, cx=3.6, r=0.22, letters=False, wscale=0.5)
        self.play(*[Create(m) if isinstance(m, Line) else FadeIn(m) for m in tv8.group], run_time=1.2)
        c8 = D.codes(r8)
        n3 = VGroup(T("每个", 24), MathTex(str(len(next(iter(c8.values())))), color=C_RED).scale(0.9),
                    T("位：一位也省不下", 24)).arrange(RIGHT, buff=0.12).move_to([3.6, -1.6, 0])
        self.play(FadeIn(n3, shift=UP * 0.2), run_time=0.8)
        self.at("压缩的收益")
        moral = T("收益来自频率的不均匀", 30, C_YELLOW).move_to([3.6, -2.4, 0])
        self.play(FadeIn(moral, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 5 周 二叉树 6.1–6.2 节 · OpenJudge 04080", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
