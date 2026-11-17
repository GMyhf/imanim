"""数的划分：深搜与动态规划（3B1B 风格，例题精讲）。

由 make.py 驱动，时间轴约定见 cine.py。搜索树、剪枝前后节点数、调用次数、DP 表、对拍组数都来自 partitiondata
（test_partition.py 对撞讲义原样输出、穷举、共轭视角的完全背包计数与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import partitiondata as P  # noqa: E402
from cine import *  # noqa: E402,F403

PART_COL = {1: C_RED, 2: C_TEAL, 3: C_YELLOW, 4: C_PURPLE, 5: C_BLUE, 6: C_GREEN}
GROUP_COL = [C_BLUE, C_TEAL, C_YELLOW, C_PURPLE]      # 七分三份的四种分法各一色


def num(v, scale=0.75, color=WHITE):
    return MathTex(str(v), color=color).scale(scale)


def plus(parts):
    return "+".join(map(str, parts))


def bar(parts, u=0.34, gap=0.16):
    """横排小方块：每一份一段，段间留空。半透明填充（LaggedStart 不会盖字）。"""
    segs = VGroup()
    for p in parts:
        seg = VGroup(*[Square(u, stroke_color=PART_COL.get(p, C_GREY), stroke_width=2)
                       .set_fill(PART_COL.get(p, C_GREY), 0.35) for _ in range(p)]).arrange(RIGHT, buff=0.04)
        segs.add(seg)
    return segs.arrange(RIGHT, buff=gap)


def stacks(parts, u=0.3, gap=0.12):
    """竖着摞的小方块：每一份一摞，底对齐。"""
    cols = VGroup()
    for p in parts:
        col = VGroup(*[Square(u, stroke_color=PART_COL.get(p, C_GREY), stroke_width=2)
                       .set_fill(PART_COL.get(p, C_GREY), 0.35) for _ in range(p)]).arrange(UP, buff=0.03)
        cols.add(col)
    cols.arrange(RIGHT, buff=gap, aligned_edge=DOWN)
    return cols


def fmt(v):
    return f"{v:,}"


class PartitionLesson(Lesson):
    def construct(self):
        for b in ("title", "read", "dup", "tree", "prune", "memo", "split", "table", "check", "choose", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def cue_at(self, key, default=None):
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    def fade_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs and m is not self.camera.frame]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)
            self.remove(*rest)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("数的划分", 60).move_to([0, 1.9, 0])
        sub = T("OpenJudge 28906 · 2025-11-06 模拟机考", 28, C_GREY).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        parts = P.partitions()
        b = bar([1] * P.N, u=0.5, gap=0.06).move_to([0, -0.4, 0])
        for sq in b:
            sq[0].set_stroke(C_GREY).set_fill(C_GREY, 0.3)
        self.play(LaggedStart(*[FadeIn(s, shift=DOWN * 0.2) for s in b], lag_ratio=0.1), run_time=1.0)
        lab = T(f"{P.N} 分成 {P.K} 份", 28, C_GREY).next_to(b, DOWN, buff=0.3)
        self.play(FadeIn(lab), run_time=0.4)
        for p in parts:
            nb = bar(list(p), u=0.5, gap=0.32).move_to(b)
            nl = T(plus(p), 30, WHITE).move_to(lab)
            self.play(Transform(b, nb), Transform(lab, nl), run_time=0.6)
            self.wait(0.35)
        self.wait_until(self.cue_start("深搜", self.now))
        tags = VGroup(T("深搜", 30, C_BLUE), T("·", 30, C_GREY), T("动态规划", 30, C_TEAL), T("·", 30, C_GREY),
                      T("对拍", 30, C_YELLOW)).arrange(RIGHT, buff=0.3).move_to([0, -2.4, 0])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.15) for t in tags], lag_ratio=0.25), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 读题
    def read_beat(self):
        self.beat("read")
        head = VGroup(T("把整数 n 分成 k 份", 32), T("每份不能为空 · 不考虑顺序", 28, C_GREY)).arrange(DOWN, buff=0.18)
        head.move_to([0, 3.0, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("一一五和五一一", self.now))
        same = VGroup(MathTex("1+1+5", color=C_BLUE).scale(0.8), MathTex("=", color=C_GREY).scale(0.8),
                      MathTex("1+5+1", color=C_BLUE).scale(0.8), MathTex("=", color=C_GREY).scale(0.8),
                      MathTex("5+1+1", color=C_BLUE).scale(0.8), T("算同一种", 26, C_GREY)).arrange(RIGHT, buff=0.25)
        same.move_to([0, 1.75, 0])
        self.play(FadeIn(same, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("样例一", self.now))
        s1 = VGroup(T("样例一", 26, C_GREY), Text(f"{P.N} {P.K}", font=MONO, font_size=28),
                    MathTex(r"\to").scale(0.8), num(P.run_lecture(P.N, P.K), 0.9, C_YELLOW)).arrange(RIGHT, buff=0.25)
        s1.move_to([-3.6, 0.85, 0])
        self.play(FadeIn(s1), run_time=0.5)
        rows = VGroup()
        for i, p in enumerate(P.partitions()):
            r = VGroup(bar(list(p), u=0.26, gap=0.14), T(plus(p), 24, WHITE)).arrange(RIGHT, buff=0.3)
            rows.add(r)
        rows.arrange(DOWN, buff=0.18, aligned_edge=LEFT).next_to(s1, DOWN, buff=0.3).align_to(s1, LEFT)
        for r in rows:
            r[1].move_to([s1.get_left()[0] + 3.0, r[1].get_y(), 0])
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows], lag_ratio=0.3), run_time=1.6)
        self.wait_until(self.cue_start("样例二", self.now))
        p2 = P.partitions(P.N2, P.K2)
        s2 = VGroup(T("样例二", 26, C_GREY), Text(f"{P.N2} {P.K2}", font=MONO, font_size=28),
                    MathTex(r"\to").scale(0.8), num(P.run_lecture(P.N2, P.K2), 0.9, C_YELLOW)).arrange(RIGHT, buff=0.25)
        s2.move_to([3.4, 0.85, 0])
        rows2 = VGroup(*[VGroup(bar(list(p), u=0.26, gap=0.14), T(plus(p), 24, WHITE)).arrange(RIGHT, buff=0.3)
                         for p in p2]).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        rows2.next_to(s2, DOWN, buff=0.3).align_to(s2, LEFT)
        for r in rows2:
            r[1].move_to([s2.get_left()[0] + 3.0, r[1].get_y(), 0])
        self.play(FadeIn(s2), LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows2], lag_ratio=0.3),
                  run_time=1.2)
        self.wait_until(self.cue_start("不超过两百", self.now))
        rng = MathTex(rf"{P.N_LO - 1} < n \le {P.N_HI},\quad {P.K_LO} \le k \le {P.K_HI}", color=C_YELLOW).scale(0.85)
        rng.move_to([0, -2.45, 0])
        self.play(Write(rng), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 随便填会重复
    def dup_beat(self):
        self.beat("dup")
        comp = P.compositions()
        parts = P.partitions()
        gid = {p: i for i, p in enumerate(parts)}
        head = T(f"一份一份随便填：{len(comp)} 种", 30).move_to([0, 3.0, 0])
        cols = 5
        grid = VGroup(*[MathTex(plus(c), color=GROUP_COL[gid[tuple(sorted(c))]]).scale(0.8) for c in comp])
        for i, m in enumerate(grid):
            m.move_to([(i % cols - (cols - 1) / 2) * 2.4, 1.9 - (i // cols) * 0.75, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(m) for m in grid], lag_ratio=0.06), run_time=1.8)
        self.wait_until(self.cue_start("同一种分法", self.now))
        self.play(*[Indicate(m, color=GROUP_COL[1], scale_factor=1.15) for m, c in zip(grid, comp)
                    if tuple(sorted(c)) == parts[1]], run_time=1.0)
        self.wait_until(self.cue_start("办法是", self.now))
        rule = T("规定：后一份 ≥ 前一份", 30, C_YELLOW).move_to([0, -0.6, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("十五种收拢", self.now) or self.cue_at("收拢", self.now))
        slots = [np.array([(g - 1.5) * 2.9, -1.7, 0]) for g in range(len(parts))]
        keep, drop = [], []
        seen = set()
        for m, c in zip(grid, comp):
            g = gid[tuple(sorted(c))]
            (drop if g in seen else keep).append((m, g))
            seen.add(g)
        tgt = [MathTex(plus(p), color=GROUP_COL[g]).scale(0.9).move_to(slots[g]) for g, p in enumerate(parts)]
        anims = [Transform(m, tgt[g]) for m, g in keep]
        anims += [m.animate.move_to(slots[g]).set_opacity(0) for m, g in drop]
        nh = T(f"排好序：{len(parts)} 种", 30, C_YELLOW).move_to(head)
        self.play(*anims, Transform(head, nh), run_time=1.4, audit=False)
        self.remove(*[m for m, _ in drop])
        boxes = VGroup(*[SurroundingRectangle(t, color=GROUP_COL[g], buff=0.15, corner_radius=0.08)
                         for g, t in enumerate(tgt)])
        self.play(Create(boxes), run_time=0.6)
        self.wait_until(self.cue_start("组合不回头", self.now))
        link = T("和组合「不回头」同一个想法：只往后挑", 26, C_GREY).move_to([0, -2.6, 0])
        self.play(FadeIn(link), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 搜索树
    def node_mob(self, nd, s):
        """节点：圆角框 + (rem, left, low)；叶子成功绿色、死路红色、内部蓝色。"""
        if nd["left"] == 1:
            col = C_GREEN if nd["ok"] else C_RED
        else:
            col = C_BLUE if nd["useful"] else C_RED
        lab = MathTex(f"({nd['rem']},{nd['left']},{nd['low']})", color=WHITE).scale(s)
        box = RoundedRectangle(corner_radius=0.08, width=lab.width + 0.24 * s / 0.6, height=lab.height + 0.2 * s / 0.6,
                               stroke_color=col, stroke_width=3 if s > 0.5 else 2)
        return VGroup(box, lab.move_to(box))

    def layout(self, nodes, xs, top, sp):
        """横向树：根在左。叶子（含没有孩子的内部节点）按先序各占一行，内部节点取孩子的平均高度。"""
        rows, pos = {}, {}
        cnt = [0]

        def go(i):
            nd = nodes[i]
            if not nd["kids"]:
                rows[i] = cnt[0]
                cnt[0] += 1
            else:
                for c in nd["kids"]:
                    go(c)
                rows[i] = sum(rows[c] for c in nd["kids"]) / len(nd["kids"])
        go(0)
        for i, nd in enumerate(nodes):
            pos[i] = np.array([xs[P.K - nd["left"]], top - rows[i] * sp, 0])
        return pos

    def build_tree(self, nodes, xs, top, sp, s):
        pos = self.layout(nodes, xs, top, sp)
        mobs = {}
        for i, nd in enumerate(nodes):
            m = self.node_mob(nd, s).move_to(pos[i])
            mobs[tuple(P.tree_key(nd))] = m
        edges = {}
        for i, nd in enumerate(nodes):
            if nd["parent"] is not None:
                a = mobs[tuple(P.tree_key(nodes[nd["parent"]]))]
                b = mobs[tuple(P.tree_key(nd))]
                col = C_GREY if nd["useful"] else C_RED
                edges[tuple(P.tree_key(nd))] = Line(a.get_right() + RIGHT * 0.04, b.get_left() + LEFT * 0.04,
                                                    color=col, stroke_width=2.5 if s > 0.5 else 1.8)
        tags = {}
        for i, nd in enumerate(nodes):
            if nd["left"] == 1:
                key = tuple(P.tree_key(nd))
                if nd["ok"]:
                    t = VGroup(MathTex(plus(nd["path"]), color=C_GREEN).scale(s * 1.1), T("✓", int(40 * s), C_GREEN))
                else:
                    t = VGroup(T("✗", int(40 * s), C_RED))
                t.arrange(RIGHT, buff=0.15).next_to(mobs[key], RIGHT, buff=0.2)
                tags[key] = t
        return mobs, edges, tags

    def tree_beat(self):
        self.beat("tree")
        code = Code(code_string=P.LECTURE_SRC, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 22})
        if code.width > 5.6:
            code.scale_to_fit_width(5.6)
        code.move_to([3.95, 1.25, 0])
        legend = VGroup(MathTex(r"(\text{rem},\ \text{left},\ \text{low})", color=WHITE).scale(0.7),
                        T("剩多少 · 还分几份 · 这一份至少", 22, C_GREY)).arrange(DOWN, buff=0.12)
        legend.move_to([-3.4, 3.15, 0])
        self.play(FadeIn(code, shift=UP * 0.2), FadeIn(legend), run_time=0.9)
        self.code, self.ln = code, code.code_lines
        hl = self.hl([3], C_YELLOW)
        self.play(Create(hl), run_time=0.5)
        nodes = P.dfs_tree()
        mobs, edges, tags = self.build_tree(nodes, xs=[-6.15, -3.95, -1.75], top=1.35, sp=0.9, s=0.62)
        key = [tuple(P.tree_key(nd)) for nd in nodes]
        self.wait_until(self.cue_start("根节点", self.now))
        self.play(FadeIn(mobs[key[0]], scale=0.8), run_time=0.6)
        self.wait_until(self.cue_start("第一份可以是", self.now))
        d1 = [k for k, nd in zip(key, nodes) if nd["left"] == P.K - 1]
        self.play(*[Create(edges[k]) for k in d1], *[FadeIn(mobs[k]) for k in d1], run_time=0.9)
        self.wait_until(self.cue_start("选了一", self.now))
        self.play(Indicate(mobs[d1[0]], color=C_YELLOW, scale_factor=1.15), run_time=0.8)
        self.wait_until(self.cue_start("只剩一份时", self.now))
        d2 = [k for k, nd in zip(key, nodes) if nd["left"] == 1]
        h2 = self.hl([4, 5], C_GREEN)
        self.play(ReplacementTransform(hl, h2), *[Create(edges[k]) for k in d2], *[FadeIn(mobs[k]) for k in d2],
                  run_time=1.0)
        self.play(LaggedStart(*[FadeIn(tags[k], shift=LEFT * 0.15) for k in d2], lag_ratio=0.25), run_time=1.2)
        self.wait_until(self.cue_start("四个叶子", self.now))
        cnt = T(f"{len(d2)} 个叶子 = {len(d2)} 种分法", 28, C_GREEN).move_to([-3.4, -2.4, 0])
        self.play(FadeOut(h2), FadeIn(cnt, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.3))
        self.play(FadeOut(cnt), run_time=0.3)
        self.tree = (nodes, mobs, edges, tags)
        self.legend = legend

    def hl(self, lines, col):
        return VGroup(*[SurroundingRectangle(self.ln[k], color=col, buff=(0.06, 0.03), stroke_width=2) for k in lines])

    # ---------------------------------------------------------------- 上界剪枝
    def prune_beat(self):
        self.beat("prune")
        nodes, mobs, edges, tags = self.tree
        h = self.hl([7], C_YELLOW)
        why = VGroup(MathTex(r"x + x + x \le 7", color=WHITE).scale(0.75),
                     MathTex(r"\Rightarrow\ x \le 7\ /\!/\ 3 = 2", color=C_YELLOW).scale(0.75)).arrange(RIGHT, buff=0.3)
        why.move_to([4.15, -1.05, 0])
        root_kids = [tuple(P.tree_key(nodes[c])) for c in nodes[0]["kids"]]
        self.play(Create(h), *[Indicate(mobs[k], color=C_YELLOW, scale_factor=1.12) for k in root_kids], run_time=0.9)
        self.wait_until(self.cue_start("三份加起来", self.now))
        self.play(FadeIn(why, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("去掉这个上界", self.now))
        full = P.dfs_tree(bound=False)
        fm, fe, ft = self.build_tree(full, xs=[-5.9, -4.1, -2.3], top=2.65, sp=0.35, s=0.42)
        anims = []
        for k, m in mobs.items():
            anims.append(Transform(m, fm[k]))
        for k, e in edges.items():
            anims.append(Transform(e, fe[k]))
        for k, t in tags.items():
            anims.append(Transform(t, ft[k]))
        new = [k for k in fm if k not in mobs]
        anims += [FadeIn(fm[k]) for k in new] + [Create(fe[k]) for k in new if k in fe]
        anims += [FadeIn(ft[k]) for k in new if k in ft]
        self.play(FadeOut(self.legend), *anims, run_time=1.6)
        self.wait_until(self.cue_start("二十个节点", self.now))
        dead = sum(not nd["useful"] for nd in full)
        stat = VGroup(T(f"不剪枝：{len(full)} 个节点", 26, WHITE), T(f"其中 {dead} 个是死路", 26, C_RED),
                      T(f"加上界：{len(nodes)} 个，个个有用", 26, C_GREEN)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        stat.next_to(why, DOWN, buff=0.3)
        self.play(FadeIn(stat[0]), FadeIn(stat[1]),
                  *[Indicate(fm[k], color=C_RED, scale_factor=1.1) for k in new], run_time=1.0)
        self.play(FadeIn(stat[2]), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.5))
        tree_all = VGroup(*mobs.values(), *edges.values(), *tags.values(), *[fm[k] for k in new],
                          *[fe[k] for k in new if k in fe], *[ft[k] for k in new if k in ft])
        self.play(FadeOut(tree_all), FadeOut(stat), FadeOut(why), FadeOut(h), run_time=0.5)

    # ---------------------------------------------------------------- 记忆化
    def memo_beat(self):
        self.beat("memo")
        h = self.hl([2], C_TEAL)
        self.play(Create(h), run_time=0.6)
        self.wait_until(self.cue_start("最大的数据", self.now))
        n, k = P.BIG
        ans, calls, _ = P.dfs_count(n, k, memo=False)
        _, mcalls, states = P.dfs_count(n, k)
        q = VGroup(Text(f"{n} {k}", font=MONO, font_size=32), MathTex(r"\to").scale(0.85),
                   T(fmt(ans), 36, C_YELLOW)).arrange(RIGHT, buff=0.3).move_to([-3.4, 2.5, 0])
        lab = T("最大数据的答案", 22, C_GREY).next_to(q, UP, buff=0.15)
        self.play(FadeIn(lab), FadeIn(q, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("不加缓存", self.now))
        W, x0 = 5.6, -6.2
        b1 = Rectangle(width=W, height=0.45, stroke_color=C_RED, stroke_width=2).set_fill(C_RED, 0.35)
        b1.move_to([x0 + W / 2, 0.6, 0])
        l1 = VGroup(T("不加缓存", 24, C_RED), T(f"调用 {fmt(calls)} 次", 24, WHITE)).arrange(RIGHT, buff=0.3)
        l1.next_to(b1, UP, buff=0.15).align_to(b1, LEFT)
        self.play(FadeIn(l1), GrowFromEdge(b1, LEFT), run_time=1.2)
        self.wait_until(self.cue_start("加上缓存", self.now))
        w2 = max(0.04, W * mcalls / calls)
        b2 = Rectangle(width=w2, height=0.45, stroke_color=C_TEAL, stroke_width=2).set_fill(C_TEAL, 0.6)
        b2.move_to([x0 + w2 / 2, -1.1, 0])
        l2 = VGroup(T("lru_cache", 24, C_TEAL), T(f"只有 {fmt(states)} 种状态", 24, WHITE)).arrange(RIGHT, buff=0.3)
        l2.next_to(b2, UP, buff=0.15).align_to(b2, LEFT)
        ratio = T(f"约为前者的 1/{round(calls / mcalls)}", 22, C_GREY).next_to(b2, RIGHT, buff=0.25)
        self.play(FadeIn(l2), GrowFromEdge(b2, LEFT), run_time=0.9)
        self.play(FadeIn(ratio), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- DP：两类
    def split_beat(self):
        self.beat("split")
        defn = VGroup(MathTex(r"dp[i][j]", color=C_YELLOW).scale(0.85), T("= 把 i 分成 j 份的分法数", 28))
        defn.arrange(RIGHT, buff=0.2).move_to([0, 3.1, 0])
        self.play(Write(defn), run_time=1.0)
        ones, removed, rest, minus = P.split_classes()
        u = 0.3
        base_y = -0.55
        xa = [-5.2, -3.3, -1.4]
        xb = [3.6]
        sa = [stacks(list(p), u).move_to([x, 0, 0]) for p, x in zip(ones, xa)]
        sb = [stacks(list(p), u).move_to([x, 0, 0]) for p, x in zip(rest, xb)]
        for s in sa + sb:
            s.shift(UP * (base_y - s.get_bottom()[1]))
        la = [MathTex(plus(p), color=WHITE).scale(0.7).next_to(s, DOWN, buff=0.2).set_y(base_y - 0.35)
              for p, s in zip(ones, sa)]
        lb = [MathTex(plus(p), color=WHITE).scale(0.7).next_to(s, DOWN, buff=0.2).set_y(base_y - 0.35)
              for p, s in zip(rest, sb)]
        self.wait_until(self.cue_start("四种分法", self.now))
        self.play(LaggedStart(*[FadeIn(VGroup(s, l), shift=UP * 0.2) for s, l in zip(sa + sb, la + lb)],
                              lag_ratio=0.2), run_time=1.2)
        sep = DashedLine([0.9, 2.3, 0], [0.9, -2.6, 0], color=C_GREY, stroke_width=1.5)
        ha = T("至少有一份是 1", 26, C_RED).move_to([-3.3, 1.95, 0])
        hb = T("每份都 ≥ 2", 26, C_TEAL).move_to([3.6, 1.95, 0])
        self.play(Create(sep), FadeIn(ha), FadeIn(hb), run_time=0.7)
        self.wait_until(self.cue_start("拿掉它", self.now))
        ones_col = [s[0] for s in sa]                     # 非降序列第一份就是 1
        self.play(*[c.animate.set_fill(C_RED, 0.8).set_stroke(WHITE, 3) for c in ones_col], run_time=0.5)
        new_la = [MathTex(plus(p), color=C_RED).scale(0.7).move_to(l) for p, l in zip(removed, la)]
        self.play(*[FadeOut(c, shift=DOWN * 0.3) for c in ones_col],
                  *[VGroup(*s[1:]).animate.shift(LEFT * (u + 0.12) / 2) for s in sa],
                  *[Transform(l, nl) for l, nl in zip(la, new_la)], run_time=0.8)
        ra = VGroup(MathTex(rf"{P.N - 1}", color=WHITE).scale(0.8), T("分", 26), MathTex(rf"{P.K - 1}").scale(0.8),
                    T(f"份：{len(removed)} 种", 26)).arrange(RIGHT, buff=0.12).move_to([-3.3, -1.75, 0])
        ra.set_color(C_RED)
        self.play(FadeIn(ra, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("每份减一", self.now))
        bottoms = [col[0] for s in sb for col in s]
        self.play(*[c.animate.set_fill(C_TEAL, 0.8).set_stroke(WHITE, 3) for c in bottoms], run_time=0.5)
        new_lb = [MathTex(plus(p), color=C_TEAL).scale(0.7).move_to(l) for p, l in zip(minus, lb)]
        self.play(*[FadeOut(c, shift=DOWN * 0.3) for c in bottoms],
                  *[VGroup(*col[1:]).animate.shift(DOWN * (u + 0.03)) for s in sb for col in s],
                  *[Transform(l, nl) for l, nl in zip(lb, new_lb)], run_time=0.8)
        rb = VGroup(MathTex(rf"{P.N - P.K}", color=WHITE).scale(0.8), T("分", 26), MathTex(rf"{P.K}").scale(0.8),
                    T(f"份：{len(minus)} 种", 26)).arrange(RIGHT, buff=0.12).move_to([3.6, -1.75, 0])
        rb.set_color(C_TEAL)
        self.play(FadeIn(rb, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("三加一", self.now))
        tot = MathTex(rf"{len(removed)}", "+", rf"{len(minus)}", "=", rf"{P.dp_count(P.N, P.K)}").scale(1.0)
        tot[0].set_color(C_RED)
        tot[2].set_color(C_TEAL)
        tot[4].set_color(C_YELLOW)
        tot.move_to([0.9, -2.55, 0])
        self.play(FadeIn(tot, shift=UP * 0.2), FadeOut(sep), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- DP 表
    def table_beat(self):
        self.beat("table")
        eq = MathTex(r"dp[i][j]", "=", r"dp[i-1][j-1]", "+", r"dp[i-j][j]").scale(0.8)
        eq[0].set_color(C_YELLOW)
        eq[2].set_color(C_RED)
        eq[4].set_color(C_TEAL)
        eq.move_to([2.7, 2.6, 0])
        notes = VGroup(T("拿掉一个 1", 22, C_RED), T("每份减 1", 22, C_TEAL))
        notes[0].next_to(eq[2], DOWN, buff=0.15)
        notes[1].next_to(eq[4], DOWN, buff=0.15)
        self.play(Write(eq), FadeIn(notes), run_time=1.2)
        n, k = P.N, P.K
        dp = P.dp_table(n, k)
        cw, ch = 0.8, 0.5
        x0, y0 = -4.6, 2.2                                # 左上格 (i=0, j=0) 的中心
        cell = lambda i, j: np.array([x0 + j * cw, y0 - i * ch, 0])  # noqa: E731
        boxes = VGroup(*[Rectangle(width=cw, height=ch, stroke_color=C_GREY, stroke_width=1.5).move_to(cell(i, j))
                         for i in range(n + 1) for j in range(k + 1)])
        jl = VGroup(*[MathTex(rf"j={j}", color=C_GREY).scale(0.5).next_to(cell(0, j), UP, buff=0.3) for j in range(k + 1)])
        il = VGroup(*[MathTex(rf"i={i}", color=C_GREY).scale(0.5).next_to(cell(i, 0), LEFT, buff=0.45)
                      for i in range(n + 1)])
        self.play(Create(boxes), FadeIn(jl), FadeIn(il), run_time=1.0)
        vals = {}

        def val(i, j):
            v = dp[i][j]
            return num(v, 0.6, WHITE if v else C_GREY).move_to(cell(i, j))
        self.wait_until(self.cue_start("边界", self.now) or self.cue_at("边界", self.now))
        row0 = [val(0, j) for j in range(k + 1)]
        for j, m in enumerate(row0):
            vals[(0, j)] = m
        bnd = MathTex(r"dp[0][0]=1", color=C_YELLOW).scale(0.7).move_to([2.7, 1.25, 0])
        self.play(FadeIn(VGroup(*row0)), boxes[0].animate.set_stroke(C_YELLOW, 3), FadeIn(bnd), run_time=0.7)
        self.wait_until(self.cue_start("一行行", self.now))
        end = self.cue_start("七分三份是四", self.now + 4.0)
        step = max(0.25, min(0.6, (end - self.now) / n))
        for i in range(1, n + 1):
            row = [val(i, j) for j in range(k + 1)]
            for j, m in enumerate(row):
                vals[(i, j)] = m
            self.play(LaggedStart(*[FadeIn(m) for m in row], lag_ratio=0.15), run_time=step)
        self.wait_until(self.cue_start("七分三份是四", self.now))
        idx = lambda i, j: i * (k + 1) + j  # noqa: E731
        hl_t = SurroundingRectangle(boxes[idx(n, k)], color=C_YELLOW, buff=0.0, stroke_width=5)
        hl_a = SurroundingRectangle(boxes[idx(n - 1, k - 1)], color=C_RED, buff=0.0, stroke_width=4)
        hl_b = SurroundingRectangle(boxes[idx(n - k, k)], color=C_TEAL, buff=0.0, stroke_width=4)
        calc = MathTex(rf"dp[{n}][{k}]", "=", rf"{dp[n - 1][k - 1]}", "+", rf"{dp[n - k][k]}", "=", rf"{dp[n][k]}")
        calc.scale(0.75).move_to([2.7, 0.2, 0])
        calc[0].set_color(C_YELLOW)
        calc[2].set_color(C_RED)
        calc[4].set_color(C_TEAL)
        calc[6].set_color(C_YELLOW)
        self.play(Create(hl_a), Create(hl_b), Create(hl_t), vals[(n, k)].animate.set_color(C_YELLOW),
                  FadeIn(calc), run_time=0.9)
        self.wait_until(self.cue_at("七分两份是三", self.now))
        k2 = P.K2
        hl_2 = SurroundingRectangle(boxes[idx(P.N2, k2)], color=C_YELLOW, buff=0.0, stroke_width=5)
        s2 = MathTex(rf"dp[{P.N2}][{k2}]={dp[P.N2][k2]}", color=C_YELLOW).scale(0.75).next_to(calc, DOWN, buff=0.3)
        s2.align_to(calc, LEFT)
        self.play(Create(hl_2), vals[(P.N2, k2)].animate.set_color(C_YELLOW), FadeIn(s2), run_time=0.7)
        self.wait_until(self.cue_start("两百乘六", self.now))
        bn, bk = P.BIG
        size = VGroup(MathTex(rf"{bn}\times{bk}={P.dp_cells(bn, bk)}", color=WHITE).scale(0.75), T("格，每格一次加法", 24))
        size.arrange(RIGHT, buff=0.2).move_to([2.7, -1.9, 0])
        self.play(FadeIn(size, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 对拍
    def check_beat(self):
        self.beat("check")
        head = VGroup(T("深搜（讲义）", 28, C_BLUE), T("vs", 26, C_GREY), T("动态规划", 28, C_TEAL)).arrange(RIGHT, buff=0.3)
        head.move_to([0, 3.0, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.7)
        ns = list(range(P.N_LO, P.N_HI + 1))
        ks = list(range(P.K_LO, P.K_HI + 1))
        cw, ch = 0.056, 0.34
        gx0 = -5.1
        cols = VGroup()
        for a, n in enumerate(ns):
            col = VGroup(*[Rectangle(width=cw, height=ch, stroke_width=0).set_fill(C_GREY, 0.25)
                           .move_to([gx0 + a * cw, 1.6 - b * (ch + 0.06), 0]) for b, _ in enumerate(ks)])
            cols.add(col)
        kl = VGroup(*[MathTex(rf"k={kk}", color=C_GREY).scale(0.5).move_to([gx0 - 0.55, 1.6 - b * (ch + 0.06), 0])
                      for b, kk in enumerate(ks)])
        nl = VGroup(MathTex(rf"n={ns[0]}", color=C_GREY).scale(0.5).next_to(cols[0], DOWN, buff=0.15),
                    MathTex(rf"n={ns[-1]}", color=C_GREY).scale(0.5).next_to(cols[-1], DOWN, buff=0.15))
        self.play(FadeIn(cols), FadeIn(kl), FadeIn(nl), run_time=0.7)
        self.wait_until(self.cue_start("九百七十组", self.now) or self.now)
        cnt, bad = P.cross_check()
        tracker = ValueTracker(0)
        counter = VGroup(Integer(0, color=C_GREEN).scale(0.9), T(f"/ {cnt} 组一致", 28, C_GREEN)).arrange(RIGHT, buff=0.2)
        counter.move_to([0, -0.8, 0])
        counter[0].add_updater(lambda m: m.set_value(int(tracker.get_value())).next_to(counter[1], LEFT, buff=0.2))
        self.add(counter)
        self.play(LaggedStart(*[c.animate.set_fill(C_GREEN if not bad else C_RED, 0.85) for c in cols], lag_ratio=0.02),
                  tracker.animate.set_value(cnt), run_time=2.4, rate_func=linear)
        counter[0].clear_updaters()
        self.wait_until(self.cue_start("穷举", self.now))
        bc, bbad = P.brute_check()
        br = VGroup(MathTex(rf"n\le {P.BRUTE_MAX}", color=WHITE).scale(0.75), T("穷举 = 深搜 = 动态规划", 26, C_YELLOW),
                    T(f"（{bc} 组）", 24, C_GREY)).arrange(RIGHT, buff=0.25).move_to([0, -1.75, 0])
        self.play(FadeIn(br, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 考场上怎么选
    def choose_beat(self):
        self.beat("choose")
        n, k = P.BIG
        ans, calls, _ = P.dfs_count(n, k, memo=False)
        _, _, states = P.dfs_count(n, k)
        head = VGroup(T("先估答案多大：", 28), Text(f"{n} {k}", font=MONO, font_size=28), MathTex(r"\to").scale(0.8),
                      T(fmt(ans), 30, C_YELLOW)).arrange(RIGHT, buff=0.25).move_to([0, 3.0, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.8)
        rows_data = [("深搜（不加缓存）", f"调用 {fmt(calls)} 次", "当心超时", C_RED),
                     ("记忆化 lru_cache", f"{fmt(states)} 种状态", "稳", C_GREEN),
                     ("动态规划", f"{fmt(P.dp_cells(n, k))} 格", "稳", C_GREEN)]
        rows = VGroup()
        for a, b, c, col in rows_data:
            r = VGroup(T(a, 26, WHITE), T(b, 26, C_GREY), T(c, 26, col))
            rows.add(r)
        for i, r in enumerate(rows):
            y = 1.9 - i * 0.7
            r[0].move_to([-3.6, y, 0])
            r[1].move_to([1.0, y, 0])
            r[2].move_to([4.4, y, 0])
        self.wait_until(self.cue_start("不加缓存", self.now))
        self.play(FadeIn(rows[0], shift=RIGHT * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("只问方案数", self.now))
        self.play(LaggedStart(FadeIn(rows[1], shift=RIGHT * 0.2), FadeIn(rows[2], shift=RIGHT * 0.2), lag_ratio=0.4),
                  run_time=1.0)
        b1 = VGroup(T("只问方案数", 26, C_YELLOW), MathTex(r"\Rightarrow").scale(0.8), T("动态规划 / 记忆化", 26))
        b1.arrange(RIGHT, buff=0.25).move_to([0, -0.75, 0])
        self.play(FadeIn(b1, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("打印出来", self.now) or self.cue_at("打印", self.now))
        b2 = VGroup(T("要列出每种分法", 26, C_BLUE), MathTex(r"\Rightarrow").scale(0.8), T("只能深搜（数据必然小）", 26))
        b2.arrange(RIGHT, buff=0.25).move_to([0, -1.65, 0])
        self.play(FadeIn(b2, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.5))
        self.fade_all(0.5)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        left = VGroup(T("深搜", 32, C_BLUE), T("low 去重：后一份 ≥ 前一份", 24),
                      T("上界剪枝：x ≤ rem // left", 24), T("lru_cache 记忆化", 24)).arrange(DOWN, buff=0.22)
        right = VGroup(T("动态规划", 32, C_TEAL), T("有一份是 1：拿掉它", 24), T("每份 ≥ 2：每份减 1", 24),
                       MathTex(r"dp[i-1][j-1]+dp[i-j][j]", color=WHITE).scale(0.65)).arrange(DOWN, buff=0.22)
        cards = VGroup()
        for g, col in ((left, C_BLUE), (right, C_TEAL)):
            box = RoundedRectangle(corner_radius=0.18, width=5.6, height=2.9, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06).move_to(g)
            cards.add(VGroup(box, g))
        cards.arrange(RIGHT, buff=0.6).move_to([0, 1.3, 0])
        self.play(FadeIn(cards[0], shift=RIGHT * 0.3), FadeIn(cards[1], shift=LEFT * 0.3), run_time=1.2)
        self.wait_until(self.cue_start("放苹果", self.now))
        more = T("同类题：放苹果（允许盘子空着）", 28, C_YELLOW).move_to([0, -1.25, 0])
        self.play(FadeIn(more, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 例题精讲 · 第 16 周 T4 · OpenJudge 28906 数的划分", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
