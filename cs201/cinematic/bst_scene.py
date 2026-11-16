"""二叉搜索树：左小右大，再加一点平衡（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。插入路径、查找比较、三种删除、AVL 旋转的每一步
都来自 bstdata（讲义教学版 BinarySearchTree 逐句翻成 Python、春季讲义 AVL 原样插桩；test_bst.py 对撞
sorted 集合、随机插删、晴问 9.5 样例与暴力平衡检查）。树的画法沿用 trav_scene.TreeView：
横坐标 = 中序名次，所以「中序 = 升序 = 竖直落到地面」在画面上是字面意思。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bstdata as B  # noqa: E402
from cine import *  # noqa: E402,F403
from trav_scene import TreeView  # noqa: E402

F = B.film()


def plain_insert(shape: dict, v) -> dict:
    """不旋转的 BST 插入（AVL 片段里「旋转之前」那一帧）。"""
    s = {k: (x if k is None else tuple(x)) for k, x in shape.items()}
    if s.get(None) is None:
        s[None] = v
        s[v] = (None, None)
        return s
    cur = s[None]
    while True:
        l, r = s[cur]
        if v < cur:
            if l is None:
                s[cur] = (v, r)
                break
            cur = l
        else:
            if r is None:
                s[cur] = (l, v)
                break
            cur = r
    s[v] = (None, None)
    return s


def subtree(shape: dict, k) -> list:
    if k is None:
        return []
    l, r = shape[k]
    return [k] + subtree(shape, l) + subtree(shape, r)


class DimTree(TreeView):
    """边的透明度跟着孩子结点走（查找时整棵子树一起变暗）。"""

    def _edge(self, k):
        e = super()._edge(k)
        if k in self.nodes and len(e.points):
            e.set_stroke(opacity=self.nodes[k][0].get_stroke_opacity())
        return e


class BSTLesson(Lesson):
    def construct(self):
        for b in ("title", "build", "search", "inorder", "del1", "del2", "chain", "avl", "lr", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    @staticmethod
    def dim(node, a):
        """只改描边和文字的透明度：结点圆的填充一直是 0，不能用 set_opacity（会把被 set_color 改白的填充亮出来）。"""
        return [node[0].animate.set_stroke(opacity=a), node[1].animate.set_opacity(a)]

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def wait_cue(self, key):
        t = self.cue_start(key)
        if t is not None:
            self.wait_until(t)

    def mk_tree(self, shape, **kw):
        kw.setdefault("dx", 0.95)
        kw.setdefault("dy", 0.8)
        kw.setdefault("top", 2.6)
        kw.setdefault("size", 26)
        return DimTree(shape, shape[None], **kw)

    # ---------------------------------------------------------------- 片头：两种表各缺一样
    def title_beat(self):
        self.beat("title")
        keys = B.KEYS
        w = 0.82

        def row(vals, y, col):
            return VGroup(*[VGroup(Square(0.68, stroke_color=col, stroke_width=2), T(str(v), 24))
                            .move_to([-4.1 + w * i, y, 0]) for i, v in enumerate(vals)])
        un = row(keys, 1.5, C_GREY)
        so = row(sorted(keys), -0.4, C_BLUE)
        cu = T("无序表：插入快，查找要一个个比", 26, C_GREY).next_to(un, UP, buff=0.25)
        cs = T("有序表：能二分查找，插入要挪一大片", 26, C_BLUE).next_to(so, UP, buff=0.25)
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.15) for c in un], lag_ratio=0.05), FadeIn(cu), run_time=1.0)
        self.wait_cue("无序")
        self.play(LaggedStart(*[Indicate(c, color=C_YELLOW, scale_factor=1.1) for c in un], lag_ratio=0.08),
                  run_time=1.8)
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.15) for c in so], lag_ratio=0.05), FadeIn(cs), run_time=1.0)
        # 插入 60：右边的都要挪
        new = VGroup(Square(0.68, stroke_color=C_YELLOW, stroke_width=3), T("60", 24, C_YELLOW)).move_to(
            [-4.1 + w * 8, -1.5, 0])
        idx = sorted(keys).index(88)
        self.play(FadeIn(new, shift=UP * 0.2), run_time=0.5)
        self.play(*[so[i].animate.shift(RIGHT * w) for i in range(idx, len(keys))],
                  new.animate.move_to([-4.1 + w * idx, -0.4, 0]), run_time=1.2)
        self.wait_cue("二叉搜索树想")
        self.play(FadeOut(VGroup(un, so, cu, cs, new)), run_time=0.6)
        title = T("二叉搜索树", 64).move_to([0, 2.7, 0])
        node = VGroup(Circle(0.42, stroke_color=WHITE, stroke_width=3), T("50", 30)).move_to([0, 0.9, 0])
        lt = Polygon([-0.3, 0.45, 0], [-3.0, -1.8, 0], [-0.15, -1.8, 0], stroke_color=C_BLUE, stroke_width=3)
        rt = Polygon([0.3, 0.45, 0], [3.0, -1.8, 0], [0.15, -1.8, 0], stroke_color=C_GREEN, stroke_width=3)
        lt.set_fill(C_BLUE, 0.12)
        rt.set_fill(C_GREEN, 0.12)
        lt.shift(DOWN * 0.1)
        rt.shift(DOWN * 0.1)
        ltx = T("左子树都比它小", 24, C_BLUE).move_to([-1.25, -1.5, 0])
        rtx = T("右子树都比它大", 24, C_GREEN).move_to([1.25, -1.5, 0])
        self.play(Write(title), GrowFromCenter(node), run_time=1.0)
        self.play(DrawBorderThenFill(lt), DrawBorderThenFill(rt), FadeIn(ltx), FadeIn(rtx), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, node, lt, rt, ltx, rtx)), run_time=0.6)

    # ---------------------------------------------------------------- 逐个插入
    def build_beat(self):
        self.beat("build")
        ins = F["inserts"]
        k0, _, s0 = ins[0]
        tree = self.mk_tree(s0)
        self.tree = tree
        self.add(tree)
        self.play(GrowFromCenter(tree.nodes[k0]), run_time=0.6)
        seq = T("插入次序：" + " ".join(str(k) for k in B.KEYS), 24, C_GREY).move_to([0, -2.4, 0])
        self.play(FadeIn(seq), run_time=0.4)
        budget = self.cue_start("十一个数插完", self.now + 15) - self.now - 0.3
        hops = sum(len(p) for _, p, _ in ins[1:])
        hop = max(0.1, min(0.45, budget / (hops + 10 * 4.0)))
        for k, path, shape in ins[1:]:
            fn = tree.make_node(k).set_color(C_YELLOW).move_to(tree.nodes[path[0]].get_center() + UP * 0.9)
            self.play(FadeIn(fn, scale=0.6), run_time=hop * 1.2)
            for p in path:
                side = -1 if k < p else 1
                tgt = tree.nodes[p].get_center() + np.array([0.62 * side, 0.32, 0])
                self.play(fn.animate.move_to(tgt), Indicate(tree.nodes[p], color=C_BLUE if side < 0 else C_GREEN,
                                                            scale_factor=1.15), run_time=hop)
            self.remove(fn)
            n = tree.add_node(k, fn.get_center())
            n.set_color(C_YELLOW)
            self.play(*tree.relayout(shape), run_time=hop * 2)
            self.play(n.animate.set_color(WHITE), run_time=hop * 0.8)
        self.wait_cue("十一个数插完")
        self.play(FadeOut(seq), *[Indicate(n, color=C_TEAL, scale_factor=1.1) for n in tree.nodes.values()],
                  run_time=1.0)

    # ---------------------------------------------------------------- 查找：每比一次扔掉一棵子树
    def search_beat(self):
        self.beat("search")
        tree = self.tree
        shape = {None: tree.root, **tree.shape}
        found, path, _ = F["search"][53]
        head = T("找 53", 30, C_YELLOW).move_to([5.2, 3.35, 0])
        self.wait_cue("找五十三")
        self.play(FadeIn(head), run_time=0.4)
        ring = tree.ring(path[0], C_YELLOW)
        cmp_txt = VGroup()
        self.play(Create(ring), run_time=0.4)
        step = max(0.5, min(1.4, (self.cue_start("每比一次", self.now + 8) - self.now - 0.5) / len(path)))
        for i, p in enumerate(path):
            if p == 53:
                line = T(f"53 = {p}  找到", 26, C_YELLOW)
            else:
                line = T(f"53 {'<' if 53 < p else '>'} {p}  往{'左' if 53 < p else '右'}", 26, WHITE)
            line.move_to([5.2, 2.9 - 0.4 * i, 0])
            cmp_txt.add(line)
            anims = [ring.animate.move_to(tree.nodes[p]), FadeIn(line, shift=LEFT * 0.1)]
            if p != 53:
                other = shape[p][1] if 53 < p else shape[p][0]
                anims += [a for k in subtree(shape, other) for a in self.dim(tree.nodes[k], 0.2)]
                if 53 > p:                                  # 往右走：根本身也比较完了，左子树整棵扔掉
                    pass
            self.play(*anims, run_time=step)
        cnt = T(f"比较 {len(path)} 次", 26, C_TEAL).move_to([5.2, 2.9 - 0.4 * len(path), 0])
        self.play(FadeIn(cnt), Flash(tree.nodes[53], color=C_YELLOW), run_time=0.6)
        self.wait_cue("再找六十")
        self.play(FadeOut(VGroup(cmp_txt, cnt, head)), *[a for n in tree.nodes.values() for a in self.dim(n, 1)],
                  run_time=0.5)
        found, path, last = F["search"][60]
        head = T("找 60", 30, C_RED).move_to([5.2, 3.35, 0])
        self.play(FadeIn(head), ring.animate.move_to(tree.nodes[path[0]]).set_color(C_RED), run_time=0.5)
        for p in path[1:]:
            self.play(ring.animate.move_to(tree.nodes[p]), run_time=0.45)
        par, side = last
        hole = tree.nodes[par].get_center() + np.array([-0.48 if side == "left" else 0.48, -tree.dy, 0])
        empty = DashedVMobject(Circle(0.3, stroke_color=C_RED, stroke_width=3).move_to(hole), num_dashes=12)
        etx = T("空", 24, C_RED).move_to(hole)
        stub = DashedLine(tree.nodes[par].get_center(), hole, buff=0.3, stroke_color=C_RED, stroke_width=2)
        self.play(Create(stub), Create(empty), FadeIn(etx), ring.animate.move_to(hole), run_time=0.8)
        no = T("60 不在树里", 26, C_RED).move_to([5.2, 2.9, 0])
        self.play(FadeIn(no), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(head, ring, empty, etx, stub, no)), run_time=0.5)

    # ---------------------------------------------------------------- 中序 = 升序
    def inorder_beat(self):
        self.beat("inorder")
        tree = self.tree
        ground = Line([-5.4, -1.15, 0], [5.4, -1.15, 0], stroke_color=C_GREY, stroke_width=2)
        self.wait_cue("竖直落到")
        order = F["sorted"]
        guides = VGroup(*[DashedLine(tree.nodes[k].get_bottom(), [tree.nodes[k].get_x(), -1.15, 0], stroke_width=2,
                                     stroke_color=C_GREY, dash_length=0.08) for k in order])
        self.play(Create(ground), Create(guides), run_time=0.7)
        drops = VGroup(*[tree.nodes[k][1].copy() for k in order])
        self.play(*[d.animate.move_to([tree.nodes[k].get_x(), -1.55, 0]).set_color(C_YELLOW)
                    for d, k in zip(drops, order)], run_time=1.6)
        arrow = Arrow([-5.0, -2.15, 0], [5.0, -2.15, 0], stroke_color=C_YELLOW, stroke_width=3, buff=0)
        lab = T("升序", 24, C_YELLOW).next_to(arrow, UP, buff=0.05).shift(RIGHT * 4.6)
        self.play(GrowArrow(arrow), LaggedStart(*[Indicate(d, color=C_YELLOW) for d in drops], lag_ratio=0.1),
                  run_time=2.0)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(ground, guides, drops, arrow)), run_time=0.5)
        del lab

    # ---------------------------------------------------------------- 删叶子、删只有右孩子的
    def delete(self, v, info, shape, rt=1.0):
        tree = self.tree
        node = tree.nodes[v]
        self.play(node.animate.set_color(C_RED), run_time=0.5)
        tree.drop_node(v)
        self.play(FadeOut(node, scale=0.4), *tree.relayout(shape), run_time=rt)

    def del1_beat(self):
        self.beat("del1")
        (v1, i1, s1), (v2, i2, s2), _ = F["deletes"]
        tag = T("叶子：直接摘掉", 28, C_RED).move_to([-4.4, 3.3, 0])
        self.wait_cue("删一个叶子")
        self.play(FadeIn(tag), run_time=0.4)
        self.delete(v1, i1, s1)
        self.wait_cue("没有左孩子")
        tag2 = T("没有左孩子：右孩子顶上", 28, C_RED).move_to([-3.9, 3.3, 0])
        self.play(ReplacementTransform(tag, tag2), Indicate(self.tree.nodes[i2["replacement"]], color=C_TEAL),
                  run_time=0.6)
        self.delete(v2, i2, s2, rt=1.4)
        self.tag = tag2
        self.wait(max(0.1, self.left() - 0.4))
        self.play(FadeOut(tag2), run_time=0.4)

    # ---------------------------------------------------------------- 两个孩子：中序前驱顶替
    def del2_beat(self):
        self.beat("del2")
        tree = self.tree
        v, info, final = F["deletes"][2]
        tag = T("两个孩子：中序前驱顶替", 28, C_RED).move_to([-4.85, 3.3, 0])
        self.play(FadeIn(tag), tree.nodes[v].animate.set_color(C_RED), run_time=0.6)
        self.wait_cue("一路往右")
        ring = tree.ring(info["walk"][0], C_YELLOW)
        self.play(Create(ring), run_time=0.4)
        for k in info["walk"][1:]:
            self.play(ring.animate.move_to(tree.nodes[k]), run_time=0.6)
        rep = info["replacement"]
        self.play(tree.nodes[rep].animate.set_color(C_YELLOW), run_time=0.4)
        self.wait_cue("它比左子树")
        ls = VGroup(*[tree.nodes[k] for k in subtree({None: tree.root, **tree.shape}, tree.shape[v][0]) if k != rep])
        rs = VGroup(*[tree.nodes[k] for k in subtree({None: tree.root, **tree.shape}, tree.shape[v][1])])
        lb = SurroundingRectangle(ls, color=C_BLUE, buff=0.12, corner_radius=0.15)
        rb = SurroundingRectangle(rs, color=C_GREEN, buff=0.12, corner_radius=0.15)
        ineq = T(f"左子树其余 < {rep} < 右子树", 26, C_YELLOW).move_to([4.2, 3.3, 0])
        self.play(Create(lb), Create(rb), FadeIn(ineq), run_time=1.0)
        self.wait_cue("注意三十五")
        self.play(FadeOut(lb), FadeOut(rb), run_time=0.3)
        code = Text("*predecessor_link = replacement->left;", font=MONO, font_size=22, color=C_TEAL).move_to(
            [0, -2.3, 0])
        pl = info["pred_left"]
        self.play(FadeIn(code), tree.nodes[pl].animate.set_color(C_TEAL), run_time=0.6)
        # 第一步：前驱 35 摘下，它的左孩子 20 接到 35 原来的位置（19 的右边）
        mid = {k: tuple(x) for k, x in tree.shape.items()}
        mid[info["pred_parent"]] = (mid[info["pred_parent"]][0], pl)
        mid.pop(rep)
        mid[None] = tree.root
        anims = tree.relayout(mid, keep=(rep,))
        self.play(*anims, tree.nodes[rep].animate.move_to(tree.nodes[v].get_center() + np.array([-1.3, 0.55, 0])),
                  ring.animate.move_to(tree.nodes[v].get_center() + np.array([-1.3, 0.55, 0])), run_time=1.2)
        # 第二步：35 顶替 50
        node50 = tree.drop_node(v)
        self.play(FadeOut(node50, scale=0.4), FadeOut(ring), *tree.relayout(final), run_time=1.2)
        self.play(tree.nodes[rep].animate.set_color(WHITE), tree.nodes[pl].animate.set_color(WHITE), run_time=0.4)
        self.wait_cue("漏了这一步")
        warn = T("漏了这一句 → 二十还挂在三十五下面，树上成环", 24, C_RED).next_to(code, DOWN, buff=0.2)
        self.play(FadeIn(warn, shift=UP * 0.1), Indicate(code, color=C_RED), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        tree.freeze()
        self.play(FadeOut(VGroup(tree, tag, ineq, code, warn)), run_time=0.6)

    # ---------------------------------------------------------------- 有序插入：退化成链
    def chain_beat(self):
        self.beat("chain")
        shp = F["chain"]
        self.wait_cue("一到七")
        shapes, s = [], {None: None}
        for v in range(1, 8):
            s = plain_insert(s, v)
            shapes.append(s)
        chain = DimTree(shapes[-1], 1, dx=0.68, dy=0.68, top=2.75, cx=-3.7, size=26, show=())
        self.add(chain)
        rt = max(0.3, min(0.9, (self.cue_start("查找又变回", self.now + 7) - self.now - 0.8) / 7))
        for v in range(1, 8):
            n = chain.add_node(v, chain.pos0[v])
            self.play(GrowFromCenter(n), run_time=rt)
        assert {None: chain.root, **chain.shape} == shp
        lv = T(f"{F['chain_levels']} 层", 30, C_RED).move_to([-5.3, -1.3, 0])
        self.play(FadeIn(lv), run_time=0.5)
        self.wait_cue("查找又变回")
        ring = chain.ring(1, C_RED)
        self.play(Create(ring), run_time=0.3)
        for v in range(2, 8):
            self.play(ring.animate.move_to(chain.nodes[v]), run_time=0.25)
        self.play(FadeOut(ring), run_time=0.3)
        self.chain, self.chain_lv = chain, lv

    # ---------------------------------------------------------------- AVL：失衡就转
    def avl_beat(self):
        self.beat("avl")
        head = T("AVL 树", 34, C_TEAL).move_to([3.3, 3.35, 0])
        bf = T("平衡因子 = 左高 − 右高，只许 −1、0、1", 22, WHITE).move_to([3.3, 2.75, 0])
        self.play(FadeIn(head), Write(bf), run_time=1.2)
        self.wait_cue("还是依次插入")
        steps = F["avl_steps"]
        prev = {None: None}
        avl = None
        cx, top = 3.3, 1.95
        rot = 0
        for v, rots, after, bfs in steps:
            pre = plain_insert(prev, v)
            if avl is None:
                avl = DimTree(pre, v, dx=0.7, dy=0.68, top=top, cx=cx, size=26)
                self.add(avl)
                self.play(GrowFromCenter(avl.nodes[v]), run_time=0.4)
            else:
                pos = avl.layout(pre, pre[None])
                n = avl.add_node(v, pos[v])
                n.set_color(C_YELLOW)
                self.play(GrowFromCenter(n), *avl.relayout(pre), run_time=0.4)
                self.play(n.animate.set_color(WHITE), run_time=0.12)
            if rots:
                # 失衡结点：AVL 里第一次旋转所绕的结点（RR/LL 型就是它本身）
                bad = rots[-1][1]
                tagv = B.balance_factors(self._to_nodes(pre))[bad]
                tg = T(f"{tagv:+d}".replace("+", ""), 26, C_RED).next_to(avl.nodes[bad], LEFT, buff=0.12)
                self.play(avl.nodes[bad].animate.set_color(C_RED), FadeIn(tg, scale=1.5), run_time=0.4)
                rot += len(rots)
                cnt = T(f"旋转 {rot} 次", 24, C_YELLOW).move_to([5.6, -1.6, 0])
                self.play(FadeOut(tg), *avl.relayout(after),
                          FadeIn(cnt) if rot == 1 else Transform(self.cnt, cnt), run_time=0.8)
                self.play(avl.nodes[bad].animate.set_color(WHITE), run_time=0.2)
                if rot == 1:
                    self.cnt = cnt
            prev = after
        lv = T(f"{F['avl_levels']} 层", 30, C_GREEN).move_to([1.4, -1.3, 0])
        self.play(FadeIn(lv), *[Indicate(n, color=C_GREEN, scale_factor=1.1) for n in avl.nodes.values()], run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        avl.freeze()
        self.chain.freeze()
        self.play(FadeOut(VGroup(avl, lv, self.cnt, head, bf, self.chain, self.chain_lv)), run_time=0.6)

    @staticmethod
    def _to_nodes(shape):
        def mk(k):
            if k is None:
                return None
            return B.Node(k, mk(shape[k][0]), mk(shape[k][1]))
        return mk(shape[None])

    # ---------------------------------------------------------------- LR 型：拐弯要转两次
    def lr_beat(self):
        self.beat("lr")
        steps = F["lr_steps"]
        kw = dict(dx=1.2, dy=1.05, top=2.2, cx=0.0, r=0.38, size=32)
        tree = None
        self.wait_cue("依次插入")
        for v, rots, after, mids, bfs in steps[:2]:
            if tree is None:
                tree = DimTree(after, v, **kw)
                self.add(tree)
                self.play(GrowFromCenter(tree.nodes[v]), run_time=0.5)
            else:
                pos = tree.layout(after, after[None])
                n = tree.add_node(v, pos[v])
                self.play(GrowFromCenter(n), *tree.relayout(after), run_time=0.6)
        v, rots, after, mids, bfs = steps[2]
        pre = plain_insert(steps[1][2], v)
        pos = tree.layout(pre, pre[None])
        n = tree.add_node(v, pos[v])
        self.play(GrowFromCenter(n), *tree.relayout(pre), run_time=0.6)
        bfs_pre = B.balance_factors(self._to_nodes(pre))
        t5 = T(str(bfs_pre[5]), 30, C_RED).next_to(tree.nodes[5], RIGHT, buff=0.15)
        t2 = T(str(bfs_pre[2]), 30, C_YELLOW).next_to(tree.nodes[2], LEFT, buff=0.15)
        self.play(tree.nodes[5].animate.set_color(C_RED), FadeIn(t5, scale=1.4), run_time=0.6)
        self.play(tree.nodes[2].animate.set_color(C_YELLOW), FadeIn(t2, scale=1.4), run_time=0.6)
        self.wait_cue("转一次不够")
        s1 = T(f"① 绕 {rots[0][1]} 左旋：拉直", 28, C_YELLOW).move_to([4.2, 1.4, 0])
        self.play(FadeOut(t2), FadeIn(s1), *tree.relayout(mids[0]), run_time=1.2)
        self.play(tree.nodes[2].animate.set_color(WHITE), run_time=0.3)
        s2 = T(f"② 绕 {rots[1][1]} 右旋：{after[None]} 升为根", 28, C_GREEN).move_to([4.2, 0.6, 0])
        self.wait(0.5)
        self.play(FadeOut(t5), FadeIn(s2), *tree.relayout(after), run_time=1.2)
        self.play(tree.nodes[5].animate.set_color(WHITE), run_time=0.3)
        self.play(Indicate(tree.nodes[after[None]], color=C_GREEN), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        tree.freeze()
        self.play(FadeOut(VGroup(tree, s1, s2)), run_time=0.6)

    # ---------------------------------------------------------------- 收束
    def recap_beat(self):
        self.beat("recap")
        cost = T("查找 / 插入 / 删除：代价 = 树高 h", 34).move_to([0, 3.0, 0])
        self.play(Write(cost), run_time=1.2)
        chain = DimTree(F["chain"], 1, dx=0.42, dy=0.42, top=1.9, cx=-3.4, r=0.2, size=18)
        avl_shape = F["avl_steps"][-1][2]
        bal = DimTree(avl_shape, avl_shape[None], dx=0.6, dy=0.7, top=1.6, cx=3.2, r=0.24, size=20)
        self.wait_cue("随手插")
        l1 = MathTex(r"h = n", color=C_RED).scale(0.9).move_to([-3.4, -1.5, 0])
        l2 = MathTex(r"h \le 1.44\log_2 n", color=C_GREEN).scale(0.9).move_to([3.2, -1.5, 0])
        self.play(FadeIn(chain), FadeIn(l1), run_time=0.8)
        self.play(FadeIn(bal), FadeIn(l2), run_time=0.8)
        self.wait_cue("左小右大")
        fin = T("左小右大 + 一点平衡", 34, C_YELLOW).move_to([0, -2.4, 0])
        self.play(FadeIn(fin, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left()))
        chain.freeze()
        bal.freeze()
        self.play(FadeOut(VGroup(cost, chain, bal, l1, l2, fin)), run_time=0.8)
