"""回溯三形态：子集、组合、排列共用一个模板（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。三棵决策树、组合总和剪枝前后的树与比较次数都来自 subsetsdata
（讲义原版代码插桩；test_subsets.py 用 itertools、另写的计数与旁白稿对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subsetsdata as S  # noqa: E402
from cine import *  # noqa: E402,F403

NUMC = {1: C_BLUE, 2: C_YELLOW, 3: C_RED}
CSC = {2: C_BLUE, 3: C_TEAL, 6: C_PURPLE, 7: C_YELLOW}          # 组合总和的候选数配色
KIND = {"subset": ("子集", C_BLUE), "combine": ("组合", C_PURPLE), "perm": ("排列", C_YELLOW)}
F = S.facts()


def path_tex(path, scale=0.55):
    if not path:
        return MathTex(r"[\;]").scale(scale)
    parts = ["["]
    for i, v in enumerate(path):
        parts += [str(v)] + ([","] if i < len(path) - 1 else [])
    parts.append("]")
    m = MathTex(*parts).scale(scale)
    for part in m:
        tex = part.get_tex_string()
        if tex.isdigit():
            part.set_color(NUMC.get(int(tex), WHITE))
    return m


def code_block(src, size=24):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


def positions(nodes, cx, top, dx, dy):
    mid = (max(n.x for n in nodes) + min(n.x for n in nodes)) / 2
    return {nd.id: np.array([cx + (nd.x - mid) * dx, top - nd.depth * dy, 0]) for nd in nodes}


def box_tree(nodes, cx, top, dx, dy, scale=0.55, edge_col=lambda nd: C_GREY):
    """节点 = 圆角框 + 路径（子集两种树用）。"""
    pos = positions(nodes, cx, top, dx, dy)
    mobs, edges = {}, {}
    for nd in nodes:
        lab = path_tex(list(nd.path), scale)
        box = RoundedRectangle(corner_radius=0.1, width=max(0.6, lab.width + 0.24), height=0.46 * scale / 0.55,
                               stroke_color=C_GREY, stroke_width=2)
        mobs[nd.id] = VGroup(box, lab).move_to(pos[nd.id])
    for nd in nodes:
        if nd.parent is not None:
            edges[nd.id] = Line(mobs[nd.parent].get_bottom(), mobs[nd.id].get_top(),
                                stroke_color=edge_col(nd), stroke_width=2.5)
    return mobs, edges


def dot_tree(nodes, cx, top, dx, dy, r=0.22, label=True, colors=NUMC):
    """节点 = 圆圈 + 这一步选的数（根是空心小圆）。"""
    pos = positions(nodes, cx, top, dx, dy)
    mobs, edges = {}, {}
    for nd in nodes:
        if nd.path and label:
            v = nd.path[-1]
            c = Circle(r, stroke_color=colors[v], stroke_width=2.5)
            mobs[nd.id] = VGroup(c, MathTex(str(v), color=WHITE).scale(r * 2.3).move_to(c)).move_to(pos[nd.id])
        else:
            c = Circle(r * (0.6 if nd.path else 0.8), stroke_color=C_GREY, stroke_width=2.5)
            if nd.path:
                c.set_stroke(colors[nd.path[-1]])
            mobs[nd.id] = VGroup(c).move_to(pos[nd.id])
    for nd in nodes:
        if nd.parent is not None:
            a, b = mobs[nd.parent][0], mobs[nd.id][0]
            d = normalize(b.get_center() - a.get_center())
            edges[nd.id] = Line(a.get_center() + d * a.width / 2, b.get_center() - d * b.width / 2,
                                stroke_color=C_GREY, stroke_width=2.5)
    return mobs, edges


class SubsetsLesson(Lesson):
    def construct(self):
        for b in ("title", "template", "pick", "start", "three", "csum", "prune", "kinds", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def grow_levels(self, nodes, mobs, edges, depths, run_time):
        for d in depths:
            lvl = [nd for nd in nodes if nd.depth == d]
            self.play(LaggedStart(*[AnimationGroup(Create(edges[nd.id]),
                                                   GrowFromPoint(mobs[nd.id], mobs[nd.parent].get_center()))
                                    for nd in lvl], lag_ratio=0.1), run_time=run_time)

    # ---------------------------------------------------------------- 片头：三棵小树
    def title_beat(self):
        self.beat("title")
        title = T("回溯三形态", 68).move_to([0, 2.6, 0])
        sub = T("子集 · 组合 · 排列，共用一个模板", 32, C_BLUE).next_to(title, DOWN, buff=0.25)
        minis = VGroup()
        for cx, (kind, tree) in zip((-4.4, 0, 4.4), (("subset", S.start_tree()), ("combine", S.combine_tree()),
                                                     ("perm", S.perm_tree()))):
            mobs, edges = dot_tree(tree, cx, 0.6, 0.5, 0.75, r=0.12, label=False)
            name, col = KIND[kind]
            for nd in tree:
                if nd.collected:
                    mobs[nd.id][0].set_stroke(C_GREEN).set_fill(C_GREEN, 0.5)
            lab = T(name, 32, col).move_to([cx, -2.0, 0])
            minis.add(VGroup(VGroup(*edges.values(), *mobs.values()), lab))
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.3) for m in minis], lag_ratio=0.3), run_time=1.8)
        self.wait_until(self.cue_start("这支片", self.now))
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.4)
        self.play(*[Indicate(m[0], color=C_YELLOW, scale_factor=1.06) for m in minis], run_time=1.2)
        self.wait(max(0.1, self.left() - 0.7))
        self.play(FadeOut(VGroup(minis, title, sub)), run_time=0.7)

    # ---------------------------------------------------------------- 通用模板
    def template_beat(self):
        self.beat("template")
        code = code_block("def backtrack(path, choices):\n    if 满足结束条件:\n        result.append(path[:])\n"
                          "        return\n    for choice in choices:\n        if 不合法:\n            continue\n"
                          "        做出选择(choice)\n        backtrack(path, 新的choices)\n        撤销选择(choice)\n", 24)
        code.move_to([-2.4, 0.2, 0])
        head = T("讲义的通用模板", 30, C_GREY).next_to(code, UP, buff=0.3).align_to(code, LEFT)
        self.play(FadeIn(head), FadeIn(code, shift=RIGHT * 0.3), run_time=1.0)
        ln = code.code_lines
        marks = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.1, 0.03), stroke_width=2)
            tag = T(txt, 24, col).next_to(code, RIGHT, buff=0.3).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.7)
            marks.add(hl, tag)
            return hl, tag
        mark([0], "路径是", "路径：已做的选择", C_TEAL)
        mark([1, 2, 3], "结束条件", "结束条件：何时收答案", C_GREEN)
        loop, loop_tag = mark([4], "中间的循环", "选择列表：当前节点的孩子", C_YELLOW)
        mark([7, 8, 9], "选择、递归", "选择 · 递归 · 撤销", C_BLUE)
        self.wait_until(self.cue_start("要变的", self.now))
        big = SurroundingRectangle(ln[4], color=C_YELLOW, buff=(0.14, 0.06), stroke_width=4)
        only = T("只改这一行", 30, C_YELLOW).move_to([0, -2.55, 0])
        dim = [m for m in marks if m is not loop and m is not loop_tag]
        self.play(Transform(loop, big), *[m.animate.set_opacity(0.25) for m in dim],
                  FadeIn(only, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, head, marks, only)), run_time=0.6)

    # ---------------------------------------------------------------- 子集看法一：选或不选
    def pick_beat(self):
        self.beat("pick")
        nodes = S.pick_tree()
        mobs, edges = box_tree(nodes, 0, 2.55, 1.45, 1.1, 0.5)
        for nd in nodes:
            if nd.parent is not None and nodes[nd.parent].children[0] == nd.id:
                edges[nd.id] = DashedVMobject(edges[nd.id], num_dashes=9)
            elif nd.parent is not None:
                edges[nd.id].set_color(NUMC[S.NUMS[nodes[nd.parent].depth]])
        legend = VGroup(T("左：不选", 24, C_GREY), T("右：选", 24, C_GREEN)).arrange(RIGHT, buff=0.5)
        legend.move_to([-4.6, 3.3, 0])
        self.play(FadeIn(mobs[0], scale=1.3), FadeIn(legend), run_time=0.6)
        step = max(0.7, min(1.4, (self.cue_start("三个元素", self.now + 5) - self.now) / 3 - 0.05))
        self.grow_levels(nodes, mobs, edges, (1, 2, 3), step)
        self.wait_until(self.cue_start("三个元素", self.now))
        cnt = VGroup(T(f"{F['pick_nodes']} 个节点", 26), T(f"{F['pick_leaves']} 个叶子是答案", 26, C_GREEN))
        cnt.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([4.7, 2.75, 0])
        self.play(FadeIn(cnt[0]), *[Indicate(m, color=WHITE, scale_factor=1.06) for m in mobs.values()], run_time=1.0)
        leaves = [nd for nd in nodes if not nd.children]
        self.play(LaggedStart(*[mobs[nd.id][0].animate.set_stroke(C_GREEN, 3.5) for nd in leaves], lag_ratio=0.1),
                  FadeIn(cnt[1]), run_time=1.4)
        self.pick = (nodes, mobs, edges)
        self.pick_extra = VGroup(legend, cnt)

    # ---------------------------------------------------------------- 子集看法二：往后挑
    def start_beat(self):
        self.beat("start")
        nodes, mobs, edges = self.pick
        left = VGroup(*edges.values(), *mobs.values())
        self.play(FadeOut(self.pick_extra), left.animate.scale(0.5).move_to([-3.6, 0.9, 0]), run_time=0.9)
        ltag = T(f"选或不选：{F['pick_nodes']} 个节点", 24, C_GREY).move_to([-3.6, -0.75, 0])
        self.play(FadeIn(ltag), run_time=0.4)
        st = S.start_tree()
        smobs, sedges = box_tree(st, 3.4, 2.6, 1.3, 1.1, 0.55,
                                 edge_col=lambda nd: NUMC[nd.path[-1]])
        head = T("往后挑", 30, C_BLUE).move_to([0.6, 3.3, 0])
        self.play(FadeIn(smobs[0], scale=1.3), FadeIn(head), run_time=0.6)
        self.wait_until(self.cue_start("可以挑一", self.now))
        self.grow_levels(st, smobs, sedges, (1,), 1.0)
        self.wait_until(self.cue_start("挑了一之后", self.now))
        one = st[0].children[0]
        kids = st[one].children
        self.play(Indicate(smobs[one], color=C_BLUE), run_time=0.6)
        self.play(*[AnimationGroup(Create(sedges[c]), GrowFromPoint(smobs[c], smobs[one].get_center())) for c in kids],
                  run_time=0.9)
        nb = T("不回头", 24, C_BLUE).next_to(smobs[kids[0]], LEFT, buff=0.3)
        self.play(FadeIn(nb, shift=LEFT * 0.2), run_time=0.5)
        rest = [nd for nd in st if nd.id != 0 and nd.parent != 0 and nd.id not in kids]
        self.play(*[AnimationGroup(Create(sedges[nd.id]), GrowFromPoint(smobs[nd.id], smobs[nd.parent].get_center()))
                    for nd in rest], run_time=0.9)
        self.wait_until(self.cue_start("每个节点都是", self.now))
        badges = VGroup()
        for nd in sorted(st, key=lambda d: d.order):
            b = VGroup(Circle(0.15, stroke_color=C_GREEN, stroke_width=2),
                       MathTex(str(nd.order), color=C_GREEN).scale(0.42))
            b[1].move_to(b[0])
            b.next_to(smobs[nd.id], UL, buff=0.02).shift(RIGHT * 0.12 + DOWN * 0.1)
            badges.add(b)
        step = max(0.25, min(0.45, (self.cue_start("八个节点", self.now + 4) - self.now - 0.4) / 8))
        for nd, b in zip(sorted(st, key=lambda d: d.order), badges):
            self.play(smobs[nd.id][0].animate.set_stroke(C_GREEN, 3.5), FadeIn(b, scale=1.4), run_time=step)
        self.wait_until(self.cue_start("八个节点", self.now))
        rtag = T(f"往后挑：{F['start_nodes']} 个节点", 24, C_GREEN).move_to([3.4, -1.45, 0])
        self.play(FadeIn(rtag), Indicate(ltag, color=C_RED), run_time=0.8)
        self.wait_until(self.cue_start("同一个问题", self.now))
        cap = T("同一个问题，换了一棵树", 30, C_YELLOW).move_to([0, -2.5, 0])
        self.play(FadeIn(cap, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(left, ltag, head, nb, rtag, cap, badges, *smobs.values(), *sedges.values())),
                  run_time=0.6)

    # ---------------------------------------------------------------- 三棵树并排
    def three_beat(self):
        self.beat("three")
        cxs = {"subset": -4.65, "combine": -0.2, "perm": 4.35}
        trees = {"subset": S.start_tree(), "combine": S.combine_tree(), "perm": S.perm_tree()}
        dxs = {"subset": 0.85, "combine": 0.85, "perm": 0.68}
        built, heads = {}, VGroup()
        for kind, tree in trees.items():
            mobs, edges = dot_tree(tree, cxs[kind], 1.9, dxs[kind], 0.95)
            built[kind] = (tree, mobs, edges)
            name, col = KIND[kind]
            heads.add(T(name if kind != "combine" else "组合（选两个）", 30, col).move_to([cxs[kind], 2.95, 0]))
        self.play(FadeIn(heads), *[FadeIn(built[k][1][0], scale=1.3) for k in built], run_time=0.7)
        for d in (1, 2, 3):
            anims = []
            for kind, (tree, mobs, edges) in built.items():
                anims += [AnimationGroup(Create(edges[nd.id]), GrowFromPoint(mobs[nd.id], mobs[nd.parent].get_center()))
                          for nd in tree if nd.depth == d]
            self.play(LaggedStart(*anims, lag_ratio=0.03), run_time=0.9)
        # 同一个节点 [2]
        self.wait_until(self.cue_start("看同一个节点", self.now))
        node2 = {k: next(nd for nd in t if nd.path == (2,)) for k, (t, _, _) in built.items()}
        rings = VGroup(*[Circle(0.33, stroke_color=WHITE, stroke_width=4).move_to(built[k][1][node2[k].id])
                         for k in built])
        self.play(Create(rings), run_time=0.8)
        nxt_y = -1.55

        def show_next(kinds, key, txts):
            self.wait_until(self.cue_start(key, self.now))
            anims, labs = [], VGroup()
            for k, txt in zip(kinds, txts):
                tree, mobs, edges = built[k]
                kids = node2[k].children
                assert [tree[c].path[-1] for c in kids] == S.next_choices(k, (2,))
                anims += [edges[c].animate.set_stroke(C_YELLOW, 5) for c in kids]
                anims += [mobs[c][0].animate.set_stroke(C_YELLOW, 4) for c in kids]
                lab = VGroup(T("下一层：", 24, C_GREY), T(txt, 24, C_YELLOW)).arrange(RIGHT, buff=0.1)
                labs.add(lab.move_to([cxs[k], nxt_y, 0]))
            self.play(*anims, FadeIn(labs, shift=UP * 0.2), run_time=0.9)
            return labs
        l1 = show_next(["subset", "combine"], "子集和组合", ["往后挑 → 3", "往后挑 → 3"])
        l2 = show_next(["perm"], "排列不讲先后", ["没用过的 → 1、3"])
        self.remove(l1, l2)                      # 合成一组再加回去：同一个对象挂在两个顶层组里会被画两次
        nl = VGroup(*l1, *l2)
        self.add(nl)
        used = T("used[ ] 记谁用过", 22, C_YELLOW).move_to([cxs["perm"], nxt_y - 0.5, 0])
        self.wait_until(self.cue_start("used", self.now))
        self.play(FadeIn(used, shift=UP * 0.2), run_time=0.6)
        # 收答案的条件
        self.wait_until(self.cue_start("收答案的条件", self.now))
        coll = {"subset": "每个节点都收", "combine": "凑够两个才收", "perm": "选满三个才收"}
        cl = VGroup()
        t_end = self.cue_start("三者的差别", self.now + 5)
        step = max(0.6, (t_end - self.now - 0.3) / 3)
        for k in built:
            tree, mobs, edges = built[k]
            lab = T(coll[k], 24, C_GREEN).move_to([cxs[k], nxt_y - (1.0 if k == "perm" else 0.5), 0])
            if k == "perm":
                lab.move_to([cxs[k], nxt_y - 0.95, 0])
            cl.add(lab)
            self.play(*[mobs[nd.id][0].animate.set_fill(C_GREEN, 0.35) for nd in tree if nd.collected],
                      FadeIn(lab), run_time=min(step, 1.0))
        self.wait_until(t_end)
        core = T("三者的差别，只在下一层能选哪些数", 32, C_YELLOW)
        frame = SurroundingRectangle(core, color=C_YELLOW, buff=0.18, corner_radius=0.1)
        cg = VGroup(core, frame).move_to([0, 3.0, 0])
        self.play(FadeOut(heads), FadeOut(cl), FadeIn(cg, shift=DOWN * 0.2),
                  Indicate(nl, color=C_YELLOW, scale_factor=1.1), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        allm = VGroup(rings, nl, used, cg, *[VGroup(*m.values(), *e.values()) for _, m, e in built.values()])
        self.play(FadeOut(allm), run_time=0.6)

    # ---------------------------------------------------------------- 组合总和：传 i
    def csum_tree_mobs(self, mode, cx, top, dx, dy, r=0.25):
        nodes = S.csum_tree(mode=mode)
        pos = positions(nodes, cx, top, dx, dy)
        mobs, edges, elabs = {}, {}, {}
        for nd in nodes:
            col = C_RED if nd.rest < 0 else C_GREEN if nd.rest == 0 else C_GREY
            c = Circle(r, stroke_color=col, stroke_width=2.5)
            if nd.rest == 0:
                c.set_fill(C_GREEN, 0.3)
            mobs[nd.path] = VGroup(c, MathTex(str(nd.rest), color=WHITE).scale(0.5 * r / 0.25).move_to(c)).move_to(pos[nd.id])
        for nd in nodes:
            if nd.parent is None:
                continue
            a, b = mobs[nodes[nd.parent].path][0], mobs[nd.path][0]
            d = normalize(b.get_center() - a.get_center())
            v = nd.path[-1]
            e = Line(a.get_center() + d * r, b.get_center() - d * r, stroke_color=CSC[v], stroke_width=2.5)
            edges[nd.path] = e
            lab = MathTex(str(v), color=CSC[v]).scale(0.5 * r / 0.25)
            side = 1 if d[0] >= 0 else -1
            lab.move_to(e.point_from_proportion(0.55) + np.array([side * 0.14, 0.06, 0]))
            elabs[nd.path] = lab
        return nodes, mobs, edges, elabs

    def csum_beat(self):
        self.beat("csum")
        head = VGroup(T("组合总和", 32, C_PURPLE),
                      T(f"候选 {S.CANDS}，目标 {S.TARGET}，可重复用", 26)).arrange(RIGHT, buff=0.4)
        head.move_to([0, 3.3, 0])
        code = code_block("def dfs(start, rest):\n    if rest == 0:\n        res.append(path[:])\n        return\n"
                          "    for i in range(start, len(candidates)):\n        if candidates[i] > rest:\n"
                          "            break\n        path.append(candidates[i])\n        dfs(i, rest - candidates[i])\n"
                          "        path.pop()\n", 17)
        code.move_to([-3.55, 0.2, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), FadeIn(code, shift=RIGHT * 0.3), run_time=1.0)
        nodes, mobs, edges, elabs = self.csum_tree_mobs("break", 3.75, 2.25, 0.95, 1.25)
        root = nodes[0].path
        self.play(FadeIn(mobs[root], scale=1.3), run_time=0.5)
        self.wait_until(self.cue_start("能重复", self.now))
        ln = code.code_lines
        hl = SurroundingRectangle(ln[8], color=C_YELLOW, buff=(0.08, 0.03), stroke_width=2.5)
        tag = T("传 i：还能再选自己", 24, C_YELLOW).next_to(code, DOWN, buff=0.25).align_to(code, LEFT)
        self.play(Create(hl), FadeIn(tag), run_time=0.8)
        t_end = self.cue_start("节点里写的", self.now + 4)
        depths = max(nd.depth for nd in nodes)
        step = max(0.6, min(1.1, (t_end - self.now) / depths))
        for d in range(1, depths + 1):
            lvl = [nd for nd in nodes if nd.depth == d]
            self.play(LaggedStart(*[AnimationGroup(Create(edges[nd.path]), FadeIn(elabs[nd.path]),
                                                   GrowFromPoint(mobs[nd.path], mobs[nodes[nd.parent].path].get_center()))
                                    for nd in lvl], lag_ratio=0.1), run_time=step)
        self.wait_until(self.cue_start("节点里写的", self.now))
        rlab = T("圈里：还差多少", 22, C_GREY).next_to(mobs[root], LEFT, buff=0.3)
        hl2 = SurroundingRectangle(VGroup(ln[1], ln[2]), color=C_GREEN, buff=(0.08, 0.03), stroke_width=2.5)
        self.play(FadeIn(rlab), Create(hl2), Indicate(mobs[root], color=C_YELLOW), run_time=0.9)
        self.wait_until(self.cue_start("答案只有", self.now))
        ans = [nd for nd in nodes if nd.rest == 0]
        assert [list(nd.path) for nd in ans] == F["csum_answers"]
        alabs = VGroup(*[T("+".join(map(str, nd.path)), 22, C_GREEN).next_to(mobs[nd.path], DOWN, buff=0.15)
                         for nd in ans])
        self.play(*[Flash(mobs[nd.path], color=C_GREEN, flash_radius=0.45, line_length=0.15) for nd in ans],
                  FadeIn(alabs), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.5))
        self.csum = (nodes, mobs, edges, elabs)
        self.play(FadeOut(VGroup(code, hl, hl2, tag, rlab, alabs)), run_time=0.5)
        self.csum_head = head

    # ---------------------------------------------------------------- 剪枝：28 → 10
    def prune_beat(self):
        self.beat("prune")
        _, mobs, edges, elabs = self.csum
        fn, fmobs, fedges, felabs = self.csum_tree_mobs("none", 0, 2.25, 0.66, 1.08, r=0.23)
        cnt = VGroup(T("节点", 26, C_GREY), Integer(F["csum_break"], color=WHITE).scale(0.8)).arrange(RIGHT, buff=0.2)
        cnt.move_to([5.6, 2.6, 0])
        # 先把现有十个节点挪到「不剪枝」的位置，再长出死节点
        self.play(*[Transform(mobs[p], fmobs[p]) for p in mobs], *[Transform(edges[p], fedges[p]) for p in edges],
                  *[Transform(elabs[p], felabs[p]) for p in elabs], FadeIn(cnt), run_time=1.2)
        dead = [nd for nd in fn if nd.rest < 0]
        assert len(dead) == F["csum_dead"] and len(fn) == F["csum_none"]
        self.play(LaggedStart(*[AnimationGroup(Create(fedges[nd.path]), FadeIn(felabs[nd.path]),
                                               FadeIn(fmobs[nd.path], scale=0.6)) for nd in dead], lag_ratio=0.06),
                  ChangeDecimalToValue(cnt[1], F["csum_none"]), run_time=2.2)
        self.wait_until(self.cue_start("十八个", self.now))
        dl = T(f"死路 {F['csum_dead']}", 26, C_RED).next_to(cnt, DOWN, buff=0.2).align_to(cnt, LEFT)
        self.play(FadeIn(dl), *[Indicate(fmobs[nd.path], color=C_RED, scale_factor=1.25) for nd in dead], run_time=1.0)
        self.wait_until(self.cue_start("排好序", self.now))
        rule = Text("if candidates[i] > rest: break", font=MONO, font_size=22, color=C_YELLOW)
        rule.move_to([-3.6, -2.55, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        # 每个 break 点画一道剪刀线：第一个超额的孩子起，右边全部剪掉
        self.wait_until(self.cue_start("全部剪掉", self.now))
        cuts = VGroup()
        for nd in fn:
            kids = [fn[c] for c in nd.children if fn[c].rest < 0]
            if not kids:
                continue
            y = fedges[kids[0].path].point_from_proportion(0.3)[1]       # 靠近父节点、在边上的数字之上横切
            xs = []
            for k in kids:
                e = fedges[k.path]
                a, b = e.get_start(), e.get_end()
                xs.append(a[0] + (b[0] - a[0]) * (a[1] - y) / (a[1] - b[1]))
            cuts.add(Line([min(xs) - 0.15, y + 0.04, 0], [max(xs) + 0.15, y - 0.04, 0], color=C_RED, stroke_width=6))
        assert len(cuts) == F["breaks"]
        self.play(LaggedStart(*[Create(c) for c in cuts], lag_ratio=0.15), run_time=1.2)
        dead_m = VGroup(*[VGroup(fmobs[nd.path], fedges[nd.path], felabs[nd.path]) for nd in dead])
        self.play(FadeOut(dead_m), FadeOut(cuts), ChangeDecimalToValue(cnt[1], F["csum_break"]),
                  FadeOut(dl), run_time=1.0)
        # 剪完的十个节点重新排开（与上一段同一种画法，只是居中放大）
        _, cmobs, cedges, celabs = self.csum_tree_mobs("break", 0, 2.25, 1.5, 1.08, r=0.25)
        self.play(*[Transform(mobs[p], cmobs[p]) for p in mobs], *[Transform(edges[p], cedges[p]) for p in edges],
                  *[Transform(elabs[p], celabs[p]) for p in elabs], run_time=0.9)
        self.wait_until(self.cue_start("换成 continue", self.now))
        bars = VGroup()
        unit = 2.7 / F["cmp_continue"]
        for i, (name, n, col) in enumerate((("continue", F["cmp_continue"], C_GREY), ("break", F["cmp_break"], C_YELLOW))):
            lab = Text(name, font=MONO, font_size=22, color=col)
            bar = Rectangle(width=n * unit, height=0.3, stroke_width=0).set_fill(col, 0.6)
            num = T(f"比较 {n} 次", 22, col)
            row = VGroup(lab, bar, num)
            lab.move_to([0.9, -1.95 - 0.5 * i, 0], aligned_edge=LEFT)
            bar.next_to([2.25, lab.get_y(), 0], RIGHT, buff=0)
            num.next_to(bar, RIGHT, buff=0.15)
            bars.add(row)
        self.play(FadeIn(bars[0][0]), GrowFromEdge(bars[0][1], LEFT), FadeIn(bars[0][2]), run_time=1.0)
        self.wait_until(self.cue_start("只比较", self.now))
        self.play(FadeIn(bars[1][0]), GrowFromEdge(bars[1][1], LEFT), FadeIn(bars[1][2]), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        live = VGroup(*mobs.values(), *edges.values(), *elabs.values())
        self.play(FadeOut(VGroup(live, cnt, rule, bars, self.csum_head)), run_time=0.6)

    # ---------------------------------------------------------------- 三类剪枝
    def kinds_beat(self):
        self.beat("kinds")
        rows = [("可行性剪枝", "这一步违反约束", "continue / return", "八皇后的冲突检查", C_TEAL, "可行性"),
                ("最优性剪枝", "已经比已知最好的差", "放弃这棵子树", "求最优解时用", C_PURPLE, "最优性"),
                ("顺序剪枝", "排好序后一个不行", "break：后面全不行", "组合总和", C_YELLOW, "顺序剪枝")]
        cards = {}
        for i, (name, cond, act, eg, col, key) in enumerate(rows):
            box = RoundedRectangle(corner_radius=0.15, width=4.2, height=3.4, stroke_color=col, stroke_width=3)
            box.move_to([-4.5 + 4.5 * i, -0.1, 0])
            body = VGroup(T(name, 32, col), T(cond, 24), T(act, 24, col), T(eg, 22, C_GREY)).arrange(DOWN, buff=0.35)
            body.move_to(box)
            cards[key] = VGroup(box, body)
        head = T("三类剪枝：剪掉一整棵子树", 32).move_to([0, 2.55, 0])
        self.play(FadeIn(head), FadeIn(cards["顺序剪枝"], shift=UP * 0.2), run_time=0.8)
        for key in ("可行性", "最优性"):
            self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(cards[key], shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("顺序剪枝，是", self.now))
        self.play(Indicate(cards["顺序剪枝"], color=C_YELLOW, scale_factor=1.05), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, *cards.values())), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = [("形态", "下一层能选", "递归传", "何时收答案"),
                ("子集", "往后挑", "dfs(i + 1)", "每个节点"),
                ("组合", "往后挑", "dfs(i + 1)", "凑够 k 个"),
                ("组合总和", "往后挑，含自己", "dfs(i, rest - x)", "还差 0"),
                ("排列", "没用过的", "used[ ]", "选满 n 个")]
        cols = [C_GREY, C_BLUE, C_PURPLE, C_PURPLE, C_YELLOW]
        xs = [-4.9, -2.1, 1.3, 4.6]
        table = VGroup()
        for r, (row, col) in enumerate(zip(rows, cols)):
            y = 2.3 - 0.75 * r
            cells = VGroup()
            for c, (txt, x) in enumerate(zip(row, xs)):
                if c == 2 and r > 0:
                    m = Text(txt, font=MONO, font_size=22, color=WHITE)
                else:
                    m = T(txt, 26 if r else 24, col if c == 0 or r == 0 else (C_YELLOW if c == 1 else WHITE))
                    if r == 0:
                        m.set_color(C_GREY)
                cells.add(m.move_to([x, y, 0]))
            table.add(cells)
        rule = Line([-6.2, 1.95, 0], [6.2, 1.95, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(table[0]), Create(rule), run_time=0.6)
        t_end = self.cue_start("差别只在", self.now + 6)
        step = max(0.5, min(1.2, (t_end - self.now) / 4 - 0.1))
        for r in range(1, 5):
            self.play(FadeIn(table[r], shift=UP * 0.15), run_time=step)
        self.wait_until(self.cue_start("差别只在", self.now))
        col1 = SurroundingRectangle(VGroup(*[table[r][1] for r in range(5)]), color=C_YELLOW, buff=0.15)
        self.play(Create(col1), run_time=0.8)
        self.wait_until(self.cue_start("再配上", self.now))
        tail = T("+ 合适的剪枝 = 跑得完的指数级搜索", 28, C_GREEN).move_to([0, -1.85, 0])
        self.play(FadeIn(tail, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 9 周 回溯 1.1–1.3 节 · 第 8 周 3.4 节 · LeetCode 78 / 39", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeOut(tail), FadeIn(src), run_time=0.8)
        self.wait(1.5)
