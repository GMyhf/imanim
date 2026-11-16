"""矩阵：补一圈零，转一个弯（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。浅拷贝陷阱、保护圈邻居和、生存游戏、旋转、螺旋矩阵的每个数字
都来自 matrixdata（讲义第 6 周 1.1–1.3 节代码原样插桩；test_matrix.py 用判越界写法、下标公式与题库样例代码对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matrixdata as S  # noqa: E402
from cine import *  # noqa: E402,F403


def code(s, size=24, color=C_BLUE):
    return Text(s, font=MONO, font_size=size, color=color)


class Grid(VGroup):
    """m×n 方格 + 数字。vals 里 None 表示空格；num_color 可按值给颜色。"""

    def __init__(self, vals, size=0.8, center=ORIGIN, stroke=C_GREY, num_scale=None, num_color=None):
        super().__init__()
        self.m, self.n, self.size = len(vals), len(vals[0]), size
        self.center = np.array(center, dtype=float)
        self.ns = num_scale or 0.62 * size / 0.8
        self.num_color = num_color or (lambda v: WHITE)
        self.cells, self.nums = {}, {}
        cg, ng = VGroup(), VGroup()
        for i in range(self.m):
            for j in range(self.n):
                c = Square(size, stroke_color=stroke, stroke_width=2).move_to(self.pos(i, j))
                self.cells[i, j] = c
                cg.add(c)
        for i in range(self.m):
            for j in range(self.n):
                v = vals[i][j]
                if v is not None:
                    t = self.make_num(v, i, j)
                    self.nums[i, j] = t
                    ng.add(t)
        self.cell_group, self.num_group = cg, ng
        self.add(cg, ng)

    def pos(self, i, j):
        return self.center + np.array([(j - (self.n - 1) / 2) * self.size, ((self.m - 1) / 2 - i) * self.size, 0])

    def make_num(self, v, i, j, color=None):
        return MathTex(str(v), color=color or self.num_color(v)).scale(self.ns).move_to(self.pos(i, j))


class MatrixLesson(Lesson):
    def construct(self):
        for b in ("title", "trap", "pad", "life", "rotate", "spiral", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        """key 在字幕句里出现的时刻：同一句里有好几个关键词（「填到四……填到七……」）时按字数位置插值。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    # ---------------------------------------------------------------- 片头：二维列表
    def title_beat(self):
        self.beat("title")
        vals = [[i * 4 + j for j in range(4)] for i in range(3)]
        g = Grid(vals, size=0.8, center=[0.6, 0.0, 0])
        rows = VGroup(*[code(f"a[{i}]", 22, C_GREY).next_to(g.cells[i, 0], LEFT, buff=0.35) for i in range(3)])
        self.play(Create(g.cell_group), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(t) for t in g.num_group], lag_ratio=0.06), FadeIn(rows), run_time=1.2)
        self.wait_until(self.cue_start("下标先行后列", self.now))
        hl = SurroundingRectangle(g.cells[1, 2], color=C_YELLOW, buff=0.02, stroke_width=4)
        lab = code("a[1][2] = 6", 26, C_YELLOW).next_to(g.cell_group, RIGHT, buff=0.5)
        self.play(Create(hl), FadeIn(lab), run_time=0.7)
        self.wait_until(self.cue_start("四个小技巧", self.now))
        title = T("矩阵", 72).move_to([0, 2.7, 0])
        chips = VGroup(*[T(s, 28, c) for s, c in (("建表", C_BLUE), ("保护圈", C_TEAL), ("旋转", C_PURPLE),
                                                    ("螺旋填数", C_YELLOW))]).arrange(RIGHT, buff=0.7)
        chips.move_to([0, -2.3, 0])
        self.play(Write(title), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in chips], lag_ratio=0.3), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(g, rows, hl, lab, title, chips)), run_time=0.6)

    # ---------------------------------------------------------------- 浅拷贝陷阱
    def _rows_view(self, x_slot, x_list, ys, shared, size=0.62):
        """三个行槽 a[0..2] 指向内层列表：shared=True 时三个箭头指向同一个列表。"""
        slots = VGroup(*[code(f"a[{i}]", 22, C_GREY).move_to([x_slot, y, 0]) for i, y in enumerate(ys)])
        lists = [Grid([[0] * 4], size=size, center=[x_list, ys[1] if shared else y, 0]) for y in (ys if not shared else [0])]
        arrows = VGroup()
        for i, y in enumerate(ys):
            tgt = lists[0] if shared else lists[i]
            arrows.add(Arrow([x_slot + 0.45, y, 0], tgt.cell_group.get_left(), buff=0.08, stroke_width=3,
                             max_tip_length_to_length_ratio=0.12, color=C_RED if shared else C_GREEN))
        return slots, lists, arrows

    def _printed(self, vals, center, bad):
        g = Grid(vals, size=0.5, center=center, stroke=C_GREY,
                 num_color=lambda v: (C_RED if bad else C_YELLOW) if v == 9 else C_GREY)
        return g

    def trap_beat(self):
        self.beat("trap")
        bad, good, _ = S.alias_trap()
        ys = [1.3, 0.5, -0.3]
        c1 = code("a = [[0] * 4] * 3", 24).move_to([-3.6, 2.7, 0])
        div = DashedLine([0, 3.1, 0], [0, -2.9, 0], color=C_GREY, stroke_width=2)
        self.wait_until(self.cue_start("很多人", self.now))
        self.play(FadeIn(c1, shift=DOWN * 0.2), Create(div), run_time=0.7)
        s1, l1, a1 = self._rows_view(-6.0, -3.2, ys, shared=True)
        self.play(FadeIn(s1), Create(l1[0]), run_time=0.6)
        self.play(LaggedStart(*[GrowArrow(a) for a in a1], lag_ratio=0.2), run_time=0.8)
        self.wait_until(self.cue_start("左上角改成九", self.now))
        set1 = code("a[0][0] = 9", 22, C_YELLOW).move_to([-3.6, 2.15, 0])
        nine = l1[0].make_num(9, 0, 0, C_RED)
        self.play(FadeIn(set1), Transform(l1[0].nums[0, 0], nine), Flash(l1[0].cells[0, 0], color=C_RED), run_time=0.8)
        p1 = self._printed(bad, [-3.2, -1.95, 0], bad=True)
        pcap1 = code("print", 18, C_GREY).next_to(p1, LEFT, buff=0.3)
        self.play(FadeIn(p1), FadeIn(pcap1), run_time=0.6)
        self.wait_until(self.cue_start("乘号复制的是引用", self.now))
        same = T("同一个列表", 24, C_RED).next_to(l1[0], UP, buff=0.25)
        self.play(FadeIn(same), Indicate(a1, color=C_RED, scale_factor=1.05), run_time=0.9)
        # 正确写法
        self.wait_until(self.cue_start("正确写法", self.now))
        c2 = code("a = [[0] * 4 for _ in range(3)]", 22, C_GREEN).move_to([3.5, 2.7, 0])
        s2, l2, a2 = self._rows_view(0.8, 4.0, ys, shared=False)
        self.play(FadeIn(c2, shift=DOWN * 0.2), FadeIn(s2), *[Create(x) for x in l2], run_time=0.9)
        self.play(LaggedStart(*[GrowArrow(a) for a in a2], lag_ratio=0.2), run_time=0.7)
        self.wait_until(self.cue_start("只有第一行变了", self.now))
        set2 = code("a[0][0] = 9", 22, C_YELLOW).move_to([3.5, 2.15, 0])
        self.play(FadeIn(set2), Transform(l2[0].nums[0, 0], l2[0].make_num(9, 0, 0, C_YELLOW)), run_time=0.6)
        p2 = self._printed(good, [4.0, -1.95, 0], bad=False)
        pcap2 = code("print", 18, C_GREY).next_to(p2, LEFT, buff=0.3)
        self.play(FadeIn(p2), FadeIn(pcap2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(c1, div, s1, *l1, a1, set1, p1, pcap1, same, c2, s2, *l2, a2, set2, p2, pcap2)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 保护圈 + 方向表
    def pad_beat(self):
        self.beat("pad")
        A = S.A
        size = 0.8
        padded = S.pad(A)
        big = Grid([[None] * 5 for _ in range(5)], size=size, center=[-3.4, 0.2, 0])
        inner = Grid(A, size=size, center=[-3.4, 0.2, 0])
        head = T("求每格上下左右邻居之和", 28).move_to([-3.4, 3.0, 0])
        self.play(FadeIn(head), Create(inner.cell_group), FadeIn(inner.num_group), run_time=1.0)
        # 角上的格子：两个方向出界
        self.wait_until(self.cue_start("角上的格子", self.now))
        corner = SurroundingRectangle(inner.cells[0, 0], color=C_YELLOW, buff=0.02, stroke_width=4)
        outs = VGroup()
        for di, dj in ((-1, 0), (0, -1)):
            p0, p1 = inner.pos(0, 0), inner.pos(di, dj)
            outs.add(Arrow(p0, p1, buff=0.25, color=C_RED, stroke_width=4, max_tip_length_to_length_ratio=0.3))
        q = code("0 <= ni < m and 0 <= nj < n", 22, C_RED).move_to([3.3, 2.2, 0])
        self.play(Create(corner), GrowArrow(outs[0]), GrowArrow(outs[1]), FadeIn(q), run_time=0.9)
        # 补一圈零
        self.wait_until(self.cue_start("补一圈零", self.now))
        ring = [(i, j) for i in range(5) for j in range(5) if i in (0, 4) or j in (0, 4)]
        ring_cells = VGroup(*[big.cells[p].copy().set_stroke(C_TEAL, 2).set_fill(C_TEAL, 0.12) for p in ring])
        ring_nums = VGroup(*[MathTex("0", color=C_TEAL).scale(0.55).move_to(big.pos(*p)) for p in ring])
        self.play(FadeOut(outs), FadeOut(q), LaggedStart(*[FadeIn(c) for c in ring_cells], lag_ratio=0.03),
                  run_time=1.2)
        self.play(FadeIn(ring_nums), run_time=0.5)
        dims = T("5 × 5", 26, C_TEAL).next_to(ring_cells, DOWN, buff=0.15)
        self.play(FadeIn(dims), run_time=0.4)
        # 结果矩阵（右下）与算式（右上）
        res = S.neighbor_sum()
        out = Grid([[None] * 3 for _ in range(3)], size=0.7, center=[3.3, -1.4, 0])
        out_cap = T("结果", 22, C_GREY).next_to(out, LEFT, buff=0.3)

        def show(i, j, key):
            self.wait_until(self.cue_start(key, self.now))
            terms = S.neighbor_terms(i, j)
            hl = SurroundingRectangle(inner.cells[i, j], color=C_YELLOW, buff=0.02, stroke_width=4)
            nbs = VGroup(*[SurroundingRectangle(big.cells[i + 1 + di, j + 1 + dj], color=C_BLUE, buff=0.02,
                                                stroke_width=3) for di, dj in S.DIRS])
            eq = MathTex("+".join(map(str, terms)), "=", str(res[i][j]), color=WHITE).scale(0.9)
            eq[2].set_color(C_YELLOW)
            eq.move_to([3.3, 1.5, 0])
            return hl, nbs, eq

        hl, nbs, eq = show(0, 0, "角上的一")
        self.play(ReplacementTransform(corner, hl), Create(nbs), FadeIn(out.cell_group), FadeIn(out_cap), run_time=0.8)
        self.play(Write(eq), run_time=0.8)
        n00 = out.make_num(res[0][0], 0, 0, C_YELLOW)
        self.play(TransformFromCopy(eq[2], n00), run_time=0.6)
        hl2, nbs2, eq2 = show(1, 1, "中心的五")
        self.play(ReplacementTransform(hl, hl2), ReplacementTransform(nbs, nbs2), FadeOut(eq), run_time=0.6)
        self.play(Write(eq2), run_time=0.8)
        n11 = out.make_num(res[1][1], 1, 1, C_YELLOW)
        self.play(TransformFromCopy(eq2[2], n11), run_time=0.6)
        # 方向表 + 一个循环填满
        self.wait_until(self.cue_start("四个方向写成一张表", self.now))
        dirs = code("DIRS = ((-1,0), (1,0), (0,-1), (0,1))", 20, C_TEAL).move_to([3.3, 2.4, 0])
        rest = VGroup(*[out.make_num(res[i][j], i, j) for i in range(3) for j in range(3) if (i, j) not in ((0, 0), (1, 1))])
        self.play(FadeIn(dirs), FadeOut(eq2), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(t) for t in rest], lag_ratio=0.12), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, inner, ring_cells, ring_nums, dims, hl2, nbs2, out, out_cap, n00, n11, rest, dirs)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 生存游戏：八邻域 + 新矩阵
    def life_beat(self):
        self.beat("life")
        cells = S.LIFE
        out, cnt = S.life_step()
        wrong = S.life_inplace_wrong()
        alive = lambda v: C_GREEN if v else C_GREY  # noqa: E731
        old = Grid(cells, size=0.85, center=[-3.9, 0.3, 0], num_color=alive)
        for (i, j), c in old.cells.items():
            if cells[i][j]:
                c.set_fill(C_GREEN, 0.25)
        ring = DashedVMobject(Rectangle(width=0.85 * 6, height=0.85 * 5, color=C_TEAL, stroke_width=2),
                              num_dashes=40).move_to(old.center)
        head = VGroup(T("生存游戏", 30), code("M12560", 22, C_GREY)).arrange(RIGHT, buff=0.3).move_to([-3.9, 3.0, 0])
        dirs8 = VGroup()
        for di, dj in S.DIRS8:
            dirs8.add(Arrow(ORIGIN, np.array([dj, -di, 0]) * 0.55, buff=0, stroke_width=3, color=C_TEAL,
                            max_tip_length_to_length_ratio=0.3))
        dirs8.move_to([4.6, 2.3, 0])
        d8 = code("DIRS8", 20, C_TEAL).next_to(dirs8, LEFT, buff=0.3)
        self.play(FadeIn(head), Create(old.cell_group), FadeIn(old.num_group), Create(ring), run_time=1.0)
        self.play(FadeIn(dirs8), FadeIn(d8), run_time=0.6)
        self.wait_until(self.cue_start("活细胞有两个", self.now))
        rules = VGroup(T("活：2 或 3 个活邻居 → 继续活", 22), T("死：恰 3 个活邻居 → 复活", 22)).arrange(
            DOWN, aligned_edge=LEFT, buff=0.15).move_to([2.6, 0.9, 0])
        self.play(FadeIn(rules, shift=LEFT * 0.2), run_time=0.8)

        def probe(i, j, key, verdict_color, verdict):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(old.cells[i, j], color=C_YELLOW, buff=0.02, stroke_width=4)
            nb = VGroup(*[SurroundingRectangle(old.cells[i + di, j + dj], color=C_BLUE, buff=0.04, stroke_width=3)
                          for di, dj in S.DIRS8 if 0 <= i + di < 3 and 0 <= j + dj < 4 and cells[i + di][j + dj]])
            lab = VGroup(T("活邻居", 22, C_GREY), MathTex(str(cnt[i][j]), color=C_YELLOW).scale(0.8),
                         T(verdict, 22, verdict_color)).arrange(RIGHT, buff=0.2).move_to([-3.9, -2.2, 0])
            self.play(Create(hl), Create(nb), run_time=0.6)
            self.play(FadeIn(lab), run_time=0.5)
            return VGroup(hl, nb, lab)

        # 同时更新：原矩阵不动，判定结果只记下来，最后一起写进新矩阵
        p1 = probe(1, 1, "第二行第二列", C_RED, "→ 死去")
        self.play(FadeOut(p1), run_time=0.3)
        p2 = probe(0, 1, "第一行第二列", C_GREEN, "→ 复活")
        self.play(FadeOut(p2), run_time=0.3)
        # 写进新矩阵 vs 原地改
        self.wait_until(self.cue_start("新矩阵", self.now))
        self.play(FadeOut(rules), run_time=0.3)
        new = Grid(out, size=0.62, center=[1.9, 0.5, 0], num_color=alive)
        for (i, j), c in new.cells.items():
            if out[i][j]:
                c.set_fill(C_GREEN, 0.25)
        ok = T("新矩阵：正确", 22, C_GREEN).next_to(new, DOWN, buff=0.25)
        arr = Arrow(old.cell_group.get_right(), new.cell_group.get_left(), buff=0.2, color=C_GREY, stroke_width=3)
        marks = VGroup(*[SurroundingRectangle(new.cells[p], color=C_YELLOW, buff=0.02, stroke_width=3)
                         for p in ((1, 1), (0, 1))])
        self.play(GrowArrow(arr), FadeIn(new), FadeIn(ok), run_time=0.8)
        self.play(Create(marks), run_time=0.5)
        self.wait_until(self.cue_start("边算边改", self.now))
        bad = Grid(wrong, size=0.5, center=[5.3, 0.5, 0], num_color=lambda v: C_RED if v else C_GREY)
        nok = T("原地改：错", 22, C_RED).next_to(bad, DOWN, buff=0.25)
        diff = VGroup(*[SurroundingRectangle(bad.cells[i, j], color=C_RED, buff=0.02, stroke_width=3)
                        for i in range(3) for j in range(4) if wrong[i][j] != out[i][j]])
        self.play(FadeIn(bad), FadeIn(nok), run_time=0.7)
        self.play(Create(diff), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, old, ring, dirs8, d8, arr, new, marks, ok, bad, nok, diff)), run_time=0.6)

    # ---------------------------------------------------------------- 转置与旋转
    def rotate_beat(self):
        self.beat("rotate")
        A = S.A
        X = [-4.7, 0.0, 4.7]
        Y = 0.3
        g0 = Grid(A, size=0.8, center=[X[0], Y, 0])
        cap0 = code("a", 24, C_GREY).next_to(g0, UP, buff=0.25)
        self.play(Create(g0.cell_group), FadeIn(g0.num_group), FadeIn(cap0), run_time=0.9)

        def move_to_grid(src, dst_vals, center, mapping, color=WHITE):
            """src 的数字按 mapping((i,j)->(i',j')) 飞到新格子。"""
            dst = Grid([[None] * 3 for _ in range(3)], size=0.8, center=center)
            flies = []
            for (i, j), t in src.nums.items():
                ni, nj = mapping(i, j)
                tgt = dst.make_num(dst_vals[ni][nj], ni, nj, color)
                dst.nums[ni, nj] = tgt
                flies.append(TransformFromCopy(t, tgt, path_arc=-0.6))
            return dst, flies

        # 转置
        self.wait_until(self.cue_start("星号", self.now))
        T1 = S.transpose(A)
        c_t = code("zip(*a)", 26, C_BLUE).move_to([X[1], 2.4, 0])
        gt, fl = move_to_grid(g0, T1, [X[1], Y, 0], lambda i, j: (j, i))
        diag = DashedLine(g0.cells[0, 0].get_corner(UL), g0.cells[2, 2].get_corner(DR), color=C_YELLOW, stroke_width=3)
        self.play(FadeIn(c_t), Create(diag), Create(gt.cell_group), run_time=0.7)
        self.play(*fl, run_time=1.4)
        self.wait_until(self.cue_start("顺时针转九十度", self.now))
        self.play(FadeOut(VGroup(gt.cell_group, *gt.nums.values(), c_t, diag)), run_time=0.5)
        # 顺时针：先上下翻转再转置
        flip = A[::-1]
        cw = S.rotate_cw(A)
        self.wait_until(self.cue_start("先上下翻转", self.now))
        c_f = code("a[::-1]", 24, C_BLUE).move_to([X[1], 2.4, 0])
        gf, fl1 = move_to_grid(g0, flip, [X[1], Y, 0], lambda i, j: (2 - i, j))
        ar1 = Arrow([X[0] + 1.35, Y, 0], [X[1] - 1.35, Y, 0], buff=0.05, color=C_GREY, stroke_width=3)
        self.play(FadeIn(c_f), GrowArrow(ar1), Create(gf.cell_group), run_time=0.6)
        self.play(*fl1, run_time=1.2)
        row1 = SurroundingRectangle(VGroup(*[gf.cells[0, j] for j in range(3)]), color=C_YELLOW, buff=0.03)
        self.play(Create(row1), run_time=0.4)
        self.wait_until(self.cue_start("再转置", self.now))
        c_c = code("zip(*a[::-1])", 24, C_BLUE).move_to([X[2], 2.4, 0])
        gc, fl2 = move_to_grid(gf, cw, [X[2], Y, 0], lambda i, j: (j, i))
        ar2 = Arrow([X[1] + 1.35, Y, 0], [X[2] - 1.35, Y, 0], buff=0.05, color=C_GREY, stroke_width=3)
        self.play(FadeIn(c_c), GrowArrow(ar2), Create(gc.cell_group), FadeOut(row1), run_time=0.6)
        self.play(*fl2, run_time=1.2)
        cwlab = T("顺时针 90°", 24, C_YELLOW).next_to(gc, DOWN, buff=0.25)
        rowc = SurroundingRectangle(VGroup(*[gc.cells[0, j] for j in range(3)]), color=C_YELLOW, buff=0.03)
        self.play(FadeIn(cwlab), Create(rowc), run_time=0.5)
        self.wait_until(self.cue_start("从下往上读", self.now))
        up = Arrow(g0.pos(2, 0) + DOWN * 0.45 + LEFT * 0.55, g0.pos(0, 0) + UP * 0.45 + LEFT * 0.55, buff=0,
                   color=C_YELLOW, stroke_width=5, max_tip_length_to_length_ratio=0.12)
        col = SurroundingRectangle(VGroup(*[g0.cells[i, 0] for i in range(3)]), color=C_YELLOW, buff=0.03)
        self.play(GrowArrow(up), Create(col), run_time=0.8)
        self.wait_until(self.cue_start("逆时针反过来", self.now))
        ccw = VGroup(T("逆时针：先转置，再上下翻转", 24, C_PURPLE), code("[list(r) for r in zip(*a)][::-1]", 20, C_PURPLE))
        ccw.arrange(DOWN, buff=0.15).move_to([0, -2.3, 0])
        self.play(FadeIn(ccw, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(g0, cap0, c_f, gf.cell_group, *gf.nums.values(), ar1, c_c, gc.cell_group,
                                 *gc.nums.values(), ar2, cwlab, rowc, up, col, ccw)), run_time=0.6)

    # ---------------------------------------------------------------- 螺旋矩阵：方向表 + 保护圈
    def spiral_beat(self):
        self.beat("spiral")
        n = S.SPIRAL_N
        final, turns, path = S.spiral()
        size = 0.82
        board = Grid([[None] * (n + 2) for _ in range(n + 2)], size=size, center=[-3.3, 0.15, 0])
        walls = VGroup(*[board.cells[i, j].copy().set_stroke(C_GREY, 1.5).set_fill(C_GREY, 0.35)
                         for i in range(n + 2) for j in range(n + 2) if i in (0, n + 1) or j in (0, n + 1)])
        inner = VGroup(*[board.cells[i, j] for i in range(1, n + 1) for j in range(1, n + 1)])
        head = VGroup(T("螺旋矩阵", 30), code("M18106", 22, C_GREY)).arrange(RIGHT, buff=0.3).move_to([3.3, 3.0, 0])
        self.play(FadeIn(head), Create(inner), run_time=0.9)
        # 方向表
        self.wait_until(self.cue_start("右、下、左、上", self.now))
        vecs = [RIGHT, DOWN, LEFT, UP]
        names = ["右", "下", "左", "上"]
        dir_items = VGroup()
        for k, (v, nm) in enumerate(zip(vecs, names)):
            box = RoundedRectangle(corner_radius=0.1, width=1.1, height=1.1, stroke_color=C_GREY, stroke_width=2)
            ar = Arrow(-v * 0.3, v * 0.3, buff=0, stroke_width=5, color=C_TEAL, max_tip_length_to_length_ratio=0.35)
            lab = T(nm, 20, C_GREY)
            item = VGroup(box, ar.move_to(box), lab.next_to(box, DOWN, buff=0.08))
            dir_items.add(item)
        dir_items.arrange(RIGHT, buff=0.3).move_to([3.3, 1.6, 0])
        self.play(LaggedStart(*[FadeIn(d) for d in dir_items], lag_ratio=0.2), run_time=1.0)
        self.wait_until(self.cue_start("补一圈墙", self.now))
        wall_lab = T("墙", 22, C_GREY).next_to(walls, LEFT, buff=0.15)
        self.play(LaggedStart(*[FadeIn(w) for w in walls], lag_ratio=0.02), FadeIn(wall_lab), run_time=1.0)
        rule = code("if g[i+di][j+dj] != 0:\n    d = (d + 1) % 4", 22, C_BLUE).move_to([3.3, -0.3, 0])
        self.wait_until(self.cue_start("不是空格", self.now))
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        cur = SurroundingRectangle(dir_items[0][0], color=C_YELLOW, buff=0.04, stroke_width=4)
        cnt = VGroup(T("填到", 22, C_GREY), Integer(0, color=C_YELLOW).scale(0.8)).arrange(RIGHT, buff=0.2)
        cnt.move_to([3.3, -1.7, 0])
        self.wait_until(self.cue_start("等于四", self.now))
        self.play(Create(cur), FadeIn(cnt), run_time=0.5)
        nums = {}
        d = 0
        # 每一段：填若干个数，然后在旁白提到的时刻转弯
        keys = {4: "填到四", 7: "填到七", 10: "填到十，", 12: "填到十二"}
        seg_start = 0
        stops = turns[:4] + [n * n]
        for stop in stops:
            if stop == n * n:                    # 十二处转弯讲完再接着填
                self.wait_until(self.cue_start("再右转", self.now) + 0.5)
            run = path[seg_start:stop]
            vals = list(range(seg_start + 1, stop + 1))
            if stop in keys:
                t_turn = self.cue_start(keys[stop], self.now + 2)
            else:
                t_turn = self.cue_start("最后一个数", self.now + 3)
            step = max(0.18, min(0.45, (t_turn - self.now - 0.2) / max(1, len(run))))
            for (i, j), v in zip(run, vals):
                t = MathTex(str(v), color=WHITE).scale(0.62).move_to(board.pos(i + 1, j + 1))
                nums[v] = t
                anims = [FadeIn(t, scale=1.3), cnt[1].animate.set_value(v)]
                if v in turns[4:]:
                    d = (d + 1) % 4
                    anims.append(cur.animate.move_to(dir_items[d][0]))
                self.play(*anims, run_time=step)
            seg_start = stop
            if stop in keys:
                self.wait_until(t_turn)
                i, j = path[stop - 1]
                di, dj = S.RIGHT_DOWN_LEFT_UP[d]
                ahead = board.cells[i + 1 + di, j + 1 + dj]
                hit = SurroundingRectangle(ahead, color=C_RED, buff=0.02, stroke_width=4)
                d = (d + 1) % 4
                self.play(Create(hit), cur.animate.move_to(dir_items[d][0]), run_time=0.5)
                self.play(FadeOut(hit), run_time=0.3)
        self.wait_until(self.cue_start("最后一个数", self.now))
        last = SurroundingRectangle(board.cells[path[-1][0] + 1, path[-1][1] + 1], color=C_YELLOW, buff=0.02,
                                    stroke_width=5)
        self.play(Create(last), Indicate(nums[n * n], color=C_YELLOW), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, inner, walls, wall_lab, dir_items, rule, cur, cnt, last, *nums.values())),
                  run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(
            VGroup(T("建表", 30, C_BLUE), code("[[0] * n for _ in range(m)]", 24, C_GREY)),
            VGroup(T("看邻居", 30, C_TEAL), T("保护圈 + 方向表", 26, C_GREY)),
            VGroup(T("旋转", 30, C_PURPLE), T("翻转 + 转置", 26, C_GREY)),
        )
        for r in rows:
            r.arrange(RIGHT, buff=0.5)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.45).move_to([0, 0.9, 0])
        for r, k in zip(rows, ("建表", "看邻居", "旋转")):
            self.wait_until(self.cue_start(k, self.now))
            self.play(FadeIn(r, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("螺旋填数", self.now))
        b = T("螺旋填数 = 这几招合在一起", 32, C_YELLOW).move_to([0, -1.3, 0])
        self.play(Write(b), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 6 周 矩阵 1.1–1.3 节 P12–P17 · OpenJudge M12560 · M18106", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
