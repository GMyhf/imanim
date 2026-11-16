"""堆：一棵藏在数组里的树（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。上浮、下沉、建堆的每一次交换都来自 heapdata
（讲义 OJ04078 的 MinHeap 原样插桩；test_heap.py 对撞 heapq、讲义图 5.15–5.17 的文字结果与旁白数字）。
画面上数组和树是同一份数据的两种画法：每次交换，树上的结点和数组里的格子同时换位。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heapdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

LEVEL_COL = [C_YELLOW, C_TEAL, C_BLUE, C_PURPLE]


def num(v, scale=0.72, color=WHITE):
    return MathTex(str(v), color=color).scale(scale)


class HeapView:
    """数组 + 完全二叉树；下标 i 的结点在树上的位置由 i 唯一决定（第 d 层第 k 个）。"""

    def __init__(self, vals, cap, tree_w=11.0, cx=0.0, top=1.35, dy=1.05, r=0.32, arr_y=2.7, cell=0.72,
                 show_array=True):
        self.vals = list(vals)
        self.cap, self.tree_w, self.cx, self.top, self.dy, self.r = cap, tree_w, cx, top, dy, r
        self.arr_y, self.cell, self.show_array = arr_y, cell, show_array
        self.circles, self.tlabels, self.edges = [], [], []
        self.cells, self.alabels, self.idx = [], [], []
        for i, v in enumerate(self.vals):
            self._make(i, v)

    # 几何 ------------------------------------------------------------------
    def pos(self, i):
        d = (i + 1).bit_length() - 1
        k = i - (2 ** d - 1)
        x = self.cx - self.tree_w / 2 + (k + 0.5) * self.tree_w / 2 ** d
        return np.array([x, self.top - d * self.dy, 0])

    def cpos(self, i):
        return np.array([-(self.cap - 1) * self.cell / 2 + i * self.cell, self.arr_y, 0])

    def _edge(self, i):
        a, b = self.pos((i - 1) // 2), self.pos(i)
        u = (b - a) / np.linalg.norm(b - a)
        return Line(a + u * self.r, b - u * self.r, stroke_color=C_GREY, stroke_width=3)

    def _make(self, i, v):
        c = Circle(self.r, stroke_color=WHITE, stroke_width=3).set_fill(C_BLUE, 0.12).move_to(self.pos(i))
        self.circles.append(c)
        self.tlabels.append(num(v).move_to(self.pos(i)) if v is not None else VMobject())
        self.edges.append(self._edge(i) if i else VMobject())
        sq = Square(self.cell * 0.92, stroke_color=C_GREY, stroke_width=2.5).set_fill(C_BLUE, 0.08).move_to(self.cpos(i))
        self.cells.append(sq)
        self.alabels.append(num(v, 0.62).move_to(self.cpos(i)) if v is not None else VMobject())
        self.idx.append(MathTex(str(i), color=C_GREY).scale(0.42).next_to(sq, UP, buff=0.08))

    # 分组 ------------------------------------------------------------------
    def tree(self):
        return VGroup(*self.edges, *self.circles, *self.tlabels)

    def array(self):
        return VGroup(*self.cells, *self.idx, *self.alabels)

    def all(self):
        return VGroup(self.tree(), self.array()) if self.show_array else self.tree()

    def slot(self, i):
        """新增一个下标的空位（树上的圈、边，数组里的格子），返回出现动画。"""
        self._make(i, None)
        self.vals.append(None)
        anims = [Create(self.edges[i]), Create(self.circles[i])]
        if self.show_array:
            anims += [FadeIn(self.cells[i]), FadeIn(self.idx[i])]
        return anims

    def swap(self, i, j):
        """交换下标 i、j 的值：树上和数组里的数字同时沿弧线换位。"""
        tl, al = self.tlabels, self.alabels
        anims = [tl[i].animate(path_arc=-PI / 3).move_to(self.pos(j)),
                 tl[j].animate(path_arc=-PI / 3).move_to(self.pos(i))]
        if self.show_array:
            anims += [al[i].animate(path_arc=-PI / 2).move_to(self.cpos(j)),
                      al[j].animate(path_arc=-PI / 2).move_to(self.cpos(i))]
        tl[i], tl[j] = tl[j], tl[i]
        al[i], al[j] = al[j], al[i]
        self.vals[i], self.vals[j] = self.vals[j], self.vals[i]
        return anims

    def ring(self, i, color):
        return [self.circles[i].animate.set_stroke(color, 5), self.cells[i].animate.set_stroke(color, 4)]

    def unring(self, *ids):
        return [m.animate.set_stroke(WHITE, 3) for m in (self.circles[i] for i in ids)] + \
               [m.animate.set_stroke(C_GREY, 2.5) for m in (self.cells[i] for i in ids)]


class HeapLesson(Lesson):
    def construct(self):
        for b in ("title", "array", "order", "insert", "remove", "build", "cost", "compare", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def note(self, s, color=WHITE, size=26, pos=(3.6, -1.75)):
        return T(s, size, color).move_to([pos[0], pos[1], 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("堆", 96).move_to([0, 0.9, 0])
        sub = T("最小的永远在最上面", 36, C_YELLOW).next_to(title, DOWN, buff=0.35)
        q = T("现在最小的是哪个？", 30, C_GREY).move_to([0, 2.8, 0])
        self.play(FadeIn(q, shift=DOWN * 0.2), run_time=0.8)
        self.at("堆的回答")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.at("而这棵树")
        self.V = V = HeapView(D.FIG514, cap=11)
        arr = V.array()
        arr.shift(DOWN * 4.0)
        self.play(FadeOut(q), title.animate.scale(0.5).move_to([-5.6, 3.3, 0]), FadeOut(sub),
                  LaggedStart(*[FadeIn(VGroup(V.cells[i], V.alabels[i], V.idx[i]), shift=UP * 0.3)
                                for i in range(len(V.vals))], lag_ratio=0.08), run_time=1.6)
        self.title_mob = title
        self.wait(max(0.1, self.left() - 0.3))

    # ---------------------------------------------------------------- 数组即树
    def array_beat(self):
        self.beat("array")
        V = self.V
        self.play(V.array().animate.shift(UP * 4.0), FadeOut(self.title_mob), run_time=0.8)
        # 按层把格子里的数字「拎」到树上
        for d in range(4):
            ids = [i for i in range(len(V.vals)) if (i + 1).bit_length() - 1 == d]
            self.play(*[Create(V.edges[i]) for i in ids if i], *[Create(V.circles[i]) for i in ids],
                      *[TransformFromCopy(V.alabels[i], V.tlabels[i]) for i in ids],
                      *[V.cells[i].animate.set_stroke(LEVEL_COL[d], 3) for i in ids], run_time=0.9)
        self.play(*[c.animate.set_stroke(C_GREY, 2.5) for c in V.cells], run_time=0.4)
        self.at("下标 i 的")
        f = VGroup(MathTex(r"\text{left}=2i+1", color=C_TEAL), MathTex(r"\text{right}=2i+2", color=C_BLUE),
                   MathTex(r"\text{parent}=\lfloor (i-1)/2 \rfloor", color=C_YELLOW))
        f.scale(0.66).arrange(DOWN, buff=0.18, aligned_edge=LEFT).move_to([3.9, -2.25, 0])
        self.play(LaggedStart(*[FadeIn(x, shift=LEFT * 0.2) for x in f], lag_ratio=0.4), run_time=1.6)
        self.at("比如下标一")
        arcs = VGroup()
        for j, col in ((3, C_TEAL), (4, C_BLUE), (0, C_YELLOW)):
            a = CurvedArrow(V.cells[1].get_bottom() + DOWN * 0.04, V.cells[j].get_bottom() + DOWN * 0.04,
                            angle=PI / 2.4 if j > 1 else -PI / 2.4, color=col, stroke_width=3, tip_length=0.14)
            arcs.add(a)
        self.play(*V.ring(1, C_YELLOW), run_time=0.4)
        for k, j in enumerate((3, 4, 0)):
            col = (C_TEAL, C_BLUE, C_YELLOW)[k]
            self.play(Create(arcs[k]), V.circles[j].animate.set_stroke(col, 5), Indicate(f[k], color=col),
                      run_time=0.8)
        self.at("一根指针")
        self.play(*[Indicate(e, color=C_YELLOW) for e in V.edges[1:]], run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(arcs), FadeOut(f), *V.unring(0, 1, 3, 4), run_time=0.6)

    # ---------------------------------------------------------------- 堆序：局部有序
    def order_beat(self):
        self.beat("order")
        V = self.V
        rule = MathTex(r"K_{\text{parent}} \le K_{\text{child}}", color=C_GREEN).scale(0.8).move_to([3.7, -1.95, 0])
        self.play(FadeIn(rule), LaggedStart(*[e.animate.set_stroke(C_GREEN, 4) for e in V.edges[1:]],
                                            lag_ratio=0.1), run_time=1.6)
        self.at("所以根一定")
        crown = T("最小", 24, C_YELLOW).next_to(V.circles[0], LEFT, buff=0.25)
        self.play(V.circles[0].animate.set_stroke(C_YELLOW, 6), FadeIn(crown), Indicate(V.tlabels[0]),
                  run_time=0.9)
        self.at("但兄弟之间")
        self.play(*[e.animate.set_stroke(C_GREY, 3) for e in V.edges[1:]], run_time=0.4)
        self.play(V.circles[3].animate.set_stroke(C_RED, 5), V.circles[5].animate.set_stroke(C_RED, 5),
                  run_time=0.5)
        cmp_ = MathTex(str(V.vals[3]), ">", str(V.vals[5]), color=C_RED).scale(0.8).move_to([3.7, -2.6, 0])
        self.play(TransformFromCopy(V.tlabels[3], cmp_[0]), FadeIn(cmp_[1]),
                  TransformFromCopy(V.tlabels[5], cmp_[2]), run_time=0.9)
        self.at("堆只是局部")
        tag = T("局部有序", 30, C_GREEN).move_to([-3.9, -2.6, 0])
        self.play(FadeIn(tag, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rule, crown, cmp_, tag)), *V.unring(0, 3, 5), run_time=0.6)

    # ---------------------------------------------------------------- 插入：上浮
    def insert_beat(self):
        self.beat("insert")
        V = self.V
        _, log = D.insert_trace()
        self.at("先放在")
        i = log[0][1]
        anims = V.slot(i)
        self.play(*anims, run_time=0.7)
        V.tlabels[i] = num(D.NEW_KEY, color=C_YELLOW).move_to(V.pos(i))
        V.alabels[i] = num(D.NEW_KEY, 0.62, C_YELLOW).move_to(V.cpos(i))
        V.vals[i] = D.NEW_KEY
        self.play(FadeIn(V.tlabels[i], shift=DOWN * 0.3), FadeIn(V.alabels[i], shift=DOWN * 0.3),
                  *V.ring(i, C_YELLOW), run_time=0.6)
        cnt = VGroup(T("交换", 24, C_GREY), Integer(0, color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.2)
        cnt.move_to([3.7, -1.85, 0])
        self.play(FadeIn(cnt), run_time=0.3)
        keys = ["它比父亲", "又比新的", "父亲成了根"]
        n = 0
        for k, e in enumerate(log[1:]):
            self.at(keys[min(k, 2)])
            if e[0] == "swap":
                a, p = e[1], e[2]
                self.play(Indicate(V.tlabels[p], color=C_BLUE), V.circles[p].animate.set_stroke(C_BLUE, 5),
                          run_time=0.5)
                n += 1
                self.play(*V.swap(a, p), *V.unring(a), *V.ring(p, C_YELLOW),
                          ChangeDecimalToValue(cnt[1], n), run_time=0.9)
            else:
                a, p = e[1], e[2]
                stop = MathTex(f"{V.vals[p]}", "<", f"{V.vals[a]}", r"\;\Rightarrow\;", r"\text{stop}").scale(0.7)
                stop[0].set_color(C_BLUE)
                stop[2].set_color(C_YELLOW)
                stop.move_to([3.7, -2.55, 0])
                self.play(Indicate(V.tlabels[p], color=C_BLUE), FadeIn(stop), run_time=0.8)
                self.stop_note = stop
        self.at("只交换了")
        self.play(Indicate(cnt, color=C_YELLOW, scale_factor=1.3), run_time=0.7)
        self.at("一路最多")
        hb = DoubleArrow([-6.3, V.pos(0)[1], 0], [-6.3, V.pos(10)[1], 0], color=C_YELLOW, buff=0, stroke_width=3,
                         tip_length=0.16)
        bl = VGroup(T("树高", 22, C_YELLOW), MathTex(r"\log n", color=C_YELLOW).scale(0.75)).arrange(DOWN, buff=0.1)
        bl.move_to([-5.5, (V.pos(0)[1] + V.pos(1)[1]) / 2, 0])
        self.play(Create(hb), FadeIn(bl), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cnt, self.stop_note, hb, bl)), *V.unring(*range(len(V.vals))), run_time=0.6)
        V.tlabels[1].set_color(WHITE)
        V.alabels[1].set_color(WHITE)

    # ---------------------------------------------------------------- 删除堆顶：下沉
    def remove_beat(self):
        self.beat("remove")
        V = self.V
        got, after, log = D.remove_trace()
        out_box = VGroup(T("取出", 22, C_GREY), num(got, 0.85, C_YELLOW)).arrange(DOWN, buff=0.15).move_to([-5.6, 0.9, 0])
        self.play(V.tlabels[0].animate.move_to(out_box[1]).set_color(C_YELLOW), FadeOut(V.alabels[0], shift=UP * 0.3),
                  FadeIn(out_box[0]), run_time=1.0)
        self.taken = VGroup(out_box[0], V.tlabels[0])
        self.at("拿最后一个")
        last = len(V.vals) - 1
        self.play(*V.ring(last, C_YELLOW), Indicate(V.tlabels[last], color=C_YELLOW), run_time=0.6)
        t_lab, a_lab = V.tlabels[last], V.alabels[last]
        self.play(t_lab.animate(path_arc=PI / 3).move_to(V.pos(0)).set_color(C_YELLOW),
                  a_lab.animate(path_arc=PI / 2).move_to(V.cpos(0)).set_color(C_YELLOW),
                  FadeOut(VGroup(V.circles[last], V.edges[last], V.cells[last], V.idx[last])),
                  *V.ring(0, C_YELLOW), run_time=1.2)
        V.tlabels[0], V.alabels[0] = t_lab, a_lab
        V.vals[0] = V.vals[last]
        for lst in (V.circles, V.tlabels, V.edges, V.cells, V.alabels, V.idx, V.vals):
            lst.pop()
        keys = ["二十往下沉", "再和孩子"]
        k = 0
        for e in log[1:]:
            if e[0] == "swap":
                a, m = e[1], e[2]
                self.at(keys[k])
                kids = [c for c in (2 * a + 1, 2 * a + 2) if c < len(V.vals)]
                self.play(*[V.circles[c].animate.set_stroke(C_BLUE, 5) for c in kids],
                          *[Indicate(V.tlabels[c], color=C_BLUE) for c in kids], run_time=0.7)
                if k == 0:
                    self.play(V.circles[m].animate.set_stroke(C_GREEN, 6), run_time=0.4)
                    self.at("必须换较小")
                    other = [c for c in kids if c != m][0]
                    bad = MathTex(f"{V.vals[other]}", ">", f"{V.vals[m]}", color=C_RED).scale(0.8)
                    why = VGroup(T("若换较大的", 24, C_RED), bad).arrange(RIGHT, buff=0.3).move_to([3.7, -2.3, 0])
                    self.play(FadeIn(why), Indicate(V.tlabels[other], color=C_RED), run_time=0.9)
                    self.wait(1.4)
                    self.play(FadeOut(why), run_time=0.4)
                self.play(*V.swap(a, m), *V.unring(*kids, a), *V.ring(m, C_YELLOW), run_time=0.9)
                k += 1
            else:
                a = e[1]
                kids = [c for c in (2 * a + 1, 2 * a + 2) if c < len(V.vals)]
                self.play(*[Indicate(V.tlabels[c], color=C_BLUE) for c in kids], run_time=0.7)
                done = T("停", 26, C_GREEN).next_to(V.circles[a], RIGHT, buff=0.2)
                self.play(FadeIn(done), run_time=0.4)
                self.done = done
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(V.all(), self.taken, self.done)), run_time=0.6)

    # ---------------------------------------------------------------- 建堆
    def build_beat(self):
        self.beat("build")
        V = HeapView(D.BUILD, cap=len(D.BUILD), tree_w=10.0, top=1.35)
        self.play(FadeIn(V.array(), shift=DOWN * 0.2), run_time=0.7)
        self.play(*[Create(e) for e in V.edges[1:]], *[Create(c) for c in V.circles],
                  *[TransformFromCopy(V.alabels[i], V.tlabels[i]) for i in range(len(V.vals))], run_time=1.0)
        self.at("从最后一个")
        n = len(V.vals)
        leaves = range(n // 2, n)
        lt = T("叶子：已经是堆", 22, C_GREEN).move_to([3.6, -2.3, 0])
        self.play(*[V.circles[i].animate.set_fill(C_GREEN, 0.18).set_stroke(C_GREEN, 3) for i in leaves],
                  FadeIn(lt), run_time=0.8)
        _, rounds = D.build_heap(D.BUILD)
        keys = {3: "从下标三", 2: "下标二", 1: "下标一", 0: "最后是根"}
        for start, log in rounds:
            self.at(keys[start])
            self.play(*V.ring(start, C_YELLOW), Indicate(V.tlabels[start], color=C_YELLOW), run_time=0.5)
            cur = start
            for e in log:
                if e[0] == "swap":
                    a, m = e[1], e[2]
                    self.play(*V.swap(a, m), *V.unring(a), *V.ring(m, C_YELLOW), run_time=0.8)
                    cur = m
                else:
                    self.play(Indicate(V.circles[cur], color=C_GREEN), run_time=0.4)
            self.play(*V.unring(cur), *[V.circles[i].animate.set_fill(C_GREEN, 0.18).set_stroke(C_GREEN, 3)
                                        for i in range(start, n) if self._in_sub(start, i)], run_time=0.4)
        self.at("叶子本身")
        self.play(Indicate(lt, color=C_GREEN, scale_factor=1.15), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(V.all(), lt)), run_time=0.6)

    @staticmethod
    def _in_sub(root, i):
        while i > root:
            i = (i - 1) // 2
        return i == root

    # ---------------------------------------------------------------- 建堆代价：下沉
    def perfect(self):
        V = HeapView(list(range(D.N_PERFECT)), cap=D.N_PERFECT, tree_w=9.6, cx=-1.3, top=1.75, dy=1.15, r=0.3,
                     show_array=False)
        for i in range(D.N_PERFECT):
            d = (i + 1).bit_length() - 1
            V.circles[i].set_stroke(LEVEL_COL[d], 3).set_fill(LEVEL_COL[d], 0.15)
        V.tlabels = [VMobject() for _ in range(D.N_PERFECT)]     # 这棵树只看形状，结点里写的是距离
        return V

    def level_y(self, V, d):
        return V.pos(2 ** d - 1)[1]

    def cost_beat(self):
        self.beat("cost")
        rough = MathTex(r"\tfrac{n}{2}\times\log n", r"\;?").scale(0.9).move_to([-1.3, 3.0, 0])
        self.at("粗看")
        self.play(FadeIn(rough, shift=DOWN * 0.2), run_time=0.8)
        self.at("细算一下")
        V = self.P = self.perfect()
        self.play(*[Create(e) for e in V.edges[1:]], *[Create(c) for c in V.circles], run_time=1.2)
        self.at("下沉的距离")
        h = D.H
        dist = []
        for i in range(D.N_PERFECT):
            d = (i + 1).bit_length() - 1
            dist.append(num(h - d, 0.7, LEVEL_COL[d]).move_to(V.pos(i)))
        arrow = Arrow(V.pos(0) + RIGHT * 0.45, V.pos(7) + RIGHT * 0.45 + UP * 0.1, color=C_GREY, buff=0.0,
                      stroke_width=3, max_tip_length_to_length_ratio=0.08)
        self.play(FadeIn(arrow), run_time=0.4)
        self.play(FadeOut(arrow), run_time=0.3)
        sums = VGroup()
        cost = D.sink_cost(h)
        keys = ["根只有一个", "第二层", "第三层", "最底层"]
        for d in range(h + 1):
            self.at(keys[d])
            ids = range(2 ** d - 1, 2 ** (d + 1) - 1)
            s = MathTex(rf"{2 ** d}\times{h - d}", "=", str(cost[d]), color=LEVEL_COL[d]).scale(0.75)
            s.move_to([5.3, self.level_y(V, d), 0])
            sums.add(s)
            self.play(*[FadeIn(dist[i], scale=0.6) for i in ids], FadeIn(s, shift=LEFT * 0.2), run_time=0.8)
        self.at("加起来")
        tot = MathTex(r"\Sigma", "=", str(sum(cost)), color=C_GREEN).scale(0.95).move_to([5.3, -2.5, 0])
        line = Line([4.3, -2.05, 0], [6.4, -2.05, 0], stroke_color=C_GREY, stroke_width=2)
        self.play(Create(line), FadeIn(tot, shift=UP * 0.2), FadeOut(rough), run_time=0.9)
        self.cost_mobs = dict(dist=VGroup(*dist), sums=sums, tot=tot, line=line)
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 对比：逐个插入上浮
    def compare_beat(self):
        self.beat("compare")
        V, M, h = self.P, self.cost_mobs, D.H
        fc = D.float_cost(h)
        sink_tot = M["tot"]
        keep = VGroup(T("下沉", 22, C_GREEN), MathTex(str(sum(D.sink_cost(h))), color=C_GREEN).scale(0.8))
        keep.arrange(RIGHT, buff=0.2).move_to([-5.4, 3.1, 0])
        self.play(ReplacementTransform(sink_tot, keep), run_time=0.8)
        self.at("上浮的距离")
        new_d, new_s = [], VGroup()
        for i in range(D.N_PERFECT):
            d = (i + 1).bit_length() - 1
            new_d.append(num(d, 0.7, LEVEL_COL[d]).move_to(V.pos(i)))
        for d in range(h + 1):
            s = MathTex(rf"{2 ** d}\times{d}", "=", str(fc[d]), color=LEVEL_COL[d]).scale(0.75)
            new_s.add(s.move_to([5.3, self.level_y(V, d), 0]))
        self.play(*[Transform(M["dist"][i], new_d[i]) for i in range(D.N_PERFECT)],
                  *[Transform(M["sums"][d], new_s[d]) for d in range(h + 1)], run_time=1.4)
        bottom = VGroup(*[V.circles[i] for i in range(7, 15)])
        self.play(Indicate(M["sums"][3], color=C_RED, scale_factor=1.25),
                  *[c.animate.set_stroke(C_RED, 5) for c in bottom], run_time=1.0)
        tot = VGroup(T("上浮", 22, C_RED), MathTex(str(sum(fc)), color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.2)
        tot.move_to([5.3, -2.5, 0])
        self.play(FadeIn(tot, shift=UP * 0.2), run_time=0.6)
        self.at("一般地")
        f = MathTex(r"\sum_{i=0}^{h} 2^{i}(h-i)", r"<", r"2^{h+1}", r"\le", r"2n").scale(0.8).move_to([-0.2, 3.05, 0])
        f[0].set_color(C_GREEN)
        f[4].set_color(C_YELLOW)
        on = MathTex(r"\Rightarrow\; O(n)", color=C_YELLOW).scale(0.85).next_to(f, RIGHT, buff=0.35)
        self.play(Write(f), run_time=1.6)
        self.play(FadeIn(on, shift=LEFT * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(V.tree(), M["dist"], M["sums"], M["line"], keep, tot, f, on)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = [("看堆顶", r"O(1)", C_GREEN), ("插入", r"O(\log n)", C_BLUE), ("取最小", r"O(\log n)", C_BLUE),
                ("建堆", r"O(n)", C_YELLOW)]
        grp = VGroup()
        for name, cost, col in rows:
            r = VGroup(T(name, 30), MathTex(cost, color=col).scale(0.95))
            grp.add(r)
        grp.arrange(DOWN, buff=0.4).move_to([-2.6, 0.6, 0])
        for r in grp:
            r[0].move_to([-3.8, r.get_y(), 0])
            r[1].move_to([-1.3, r.get_y(), 0])
        head = T("优先队列", 34, C_YELLOW).move_to([-2.6, 2.7, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in grp], lag_ratio=0.3),
                  run_time=2.0)
        self.at("堆排序")
        hs = VGroup(T("堆排序", 28, C_TEAL), T("建堆 + 反复取堆顶", 24, C_GREY)).arrange(DOWN, buff=0.2)
        hs.move_to([3.4, 1.4, 0])
        self.play(FadeIn(hs, shift=LEFT * 0.2), run_time=0.8)
        # 「下一支」交给 cine.Lesson 的通用片尾卡，这里不再自制
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 5 周 二叉树 5.1–5.3 节 · OpenJudge 04078", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
