"""全排列：在决策树上走一遍（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。决策树、回溯事件序列与计数来自 permdata
（test_perm.py 用讲义原版代码插桩逐事件对撞，并对撞 itertools、阶乘公式与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import permdata as P  # noqa: E402
from cine import *  # noqa: E402,F403

A = [1, 2, 3]
NUMC = {1: C_BLUE, 2: C_YELLOW, 3: C_RED}
STRIP_Y = -2.25


def path_tex(path, scale=0.62):
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


def tile(v, size=0.6):
    sq = RoundedRectangle(corner_radius=0.1, width=size, height=size, stroke_color=NUMC[v], stroke_width=3)
    sq.set_fill(NUMC[v], 0.25)
    return VGroup(sq, MathTex(str(v), color=WHITE).scale(0.8 * size / 0.6).move_to(sq))


def code_block(src, size=24):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


class PermLesson(Lesson):
    def construct(self):
        for b in ("title", "choose", "tree", "code", "walk", "copy", "count", "implicit", "subsets", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：三张卡片
    def title_beat(self):
        self.beat("title")
        xs = [-1.7, 0, 1.7]
        cards = {}
        for v, x in zip(A, xs):
            r = RoundedRectangle(corner_radius=0.18, width=1.3, height=1.75, stroke_color=NUMC[v], stroke_width=4)
            r.set_fill(NUMC[v], 0.18)
            cards[v] = VGroup(r, MathTex(str(v)).scale(1.6).move_to(r)).move_to([x, 0.5, 0])
        self.play(LaggedStart(*[FadeIn(cards[v], shift=UP * 0.4) for v in A], lag_ratio=0.25), run_time=1.2)
        cnt = VGroup(Integer(1, color=C_YELLOW).scale(1.2), T("种", 34)).arrange(RIGHT, buff=0.15)
        cnt.move_to([0, -1.5, 0])
        self.play(FadeIn(cnt), run_time=0.4)
        orders = [p for p in P.perm_tree(A) if not p.children]
        step = max(0.45, min(0.8, (self.cue_start("六种", self.now + 4) - self.now) / 5))
        for k, leaf in enumerate(orders[1:], 2):
            anims = []
            for pos, v in enumerate(leaf.path):
                tgt = np.array([xs[pos], 0.5, 0])
                if np.linalg.norm(cards[v].get_center() - tgt) > 0.01:
                    anims.append(cards[v].animate(path_arc=PI * 0.6).move_to(tgt))
            self.play(*anims, cnt[0].animate.set_value(k), run_time=step)
        self.play(Indicate(cnt, color=C_YELLOW, scale_factor=1.4), run_time=0.8)
        title = T("全排列", 72).move_to([0, 2.7, 0])
        sub = T("在决策树上走一遍", 34, C_BLUE).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.7))
        self.play(FadeOut(VGroup(*cards.values(), cnt, title, sub)), run_time=0.7)

    # ---------------------------------------------------------------- 决策树：穿衣的例子
    def choose_beat(self):
        self.beat("choose")
        names = {(): "出门", ("T",): "白T恤", ("S",): "衬衫"}
        pos = {(): (-3.6, 2.4), ("T",): (-5.2, 0.9), ("S",): (-2.0, 0.9)}
        for top, x in (("T", -5.2), ("S", -2.0)):
            for pant, dx in (("J", -0.8), ("H", 0.8)):
                names[(top, pant)] = "牛仔裤" if pant == "J" else "短裤"
                pos[(top, pant)] = (x + dx, -0.6)
        boxes, edges = {}, {}
        for key, (x, y) in pos.items():
            t = T(names[key], 24)
            b = RoundedRectangle(corner_radius=0.12, width=max(1.15, t.width + 0.3), height=0.6,
                                 stroke_color=C_GREY, stroke_width=2.5).set_fill(BG, 1)
            boxes[key] = VGroup(b, t).move_to([x, y, 0])
        for key in pos:
            if key:
                p = key[:-1]
                edges[key] = Line(boxes[p].get_bottom(), boxes[key].get_top(), stroke_color=C_GREY, stroke_width=2.5)
        intro = VGroup(T("调用树：形状由公式决定", 26, C_GREY), T("决策树：每层做一次选择", 30, C_YELLOW))
        intro.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([3.4, 2.2, 0])
        self.play(FadeIn(intro[0]), run_time=0.6)
        self.wait_until(self.cue_start("决策树", self.now))
        self.play(FadeIn(intro[1], shift=RIGHT * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("出门穿衣", self.now))
        order = [(), ("T",), ("S",), ("T", "J"), ("T", "H"), ("S", "J"), ("S", "H")]
        self.play(FadeIn(boxes[()]), run_time=0.4)
        self.play(*[AnimationGroup(Create(edges[k]), FadeIn(boxes[k])) for k in order[1:3]], run_time=0.8)
        self.play(*[AnimationGroup(Create(edges[k]), FadeIn(boxes[k])) for k in order[3:]], run_time=0.8)
        leaves = [k for k in order if len(k) == 2]
        four = T("2 × 2 = 4 种", 26, C_GREEN).next_to(VGroup(*[boxes[k] for k in leaves]), DOWN, buff=0.35)
        self.play(FadeIn(four), run_time=0.5)
        self.wait_until(self.cue_start("节点是", self.now))
        rows = [("节点", "做到一半的状态", [boxes[("T",)]]),
                ("边", "一次选择", [edges[("S", "H")]]),
                ("叶子", "全部选完", [boxes[k] for k in leaves]),
                ("根 → 叶子的路径", "一个完整方案", [boxes[()], edges[("T",)], boxes[("T",)],
                                                   edges[("T", "H")], boxes[("T", "H")]])]
        table = VGroup()
        step = max(0.9, (self.left() - 0.8) / 4)
        for i, (k, v, targets) in enumerate(rows):
            row = VGroup(T(k, 26, C_YELLOW), T(v, 26)).arrange(RIGHT, buff=0.4)
            row.move_to([3.4, 0.6 - 0.65 * i, 0]).align_to(intro, LEFT)
            table.add(row)
            hl = [m.animate.set_color(C_YELLOW) if isinstance(m, Line) else m[0].animate.set_stroke(C_YELLOW, 4)
                  for m in targets]
            self.play(FadeIn(row, shift=LEFT * 0.2), *hl, run_time=step * 0.6)
            self.wait(step * 0.4)
        self.play(FadeOut(VGroup(*boxes.values(), *edges.values(), intro, four, table)), run_time=0.6)

    # ---------------------------------------------------------------- 全排列决策树
    def build_tree(self):
        nodes = P.perm_tree(A)
        ys = {0: 2.9, 1: 1.85, 2: 0.8, 3: -0.25}
        mid = (max(n.x for n in nodes) + min(n.x for n in nodes)) / 2
        mobs, edges, elabs = {}, {}, {}
        for nd in nodes:
            lab = path_tex(list(nd.path))
            box = RoundedRectangle(corner_radius=0.12, width=max(0.7, lab.width + 0.3), height=0.52,
                                   stroke_color=C_GREY, stroke_width=2.5)
            mobs[nd.id] = VGroup(box, lab).move_to([(nd.x - mid) * 1.8, ys[nd.depth], 0])
        for nd in nodes:
            if nd.parent is not None:
                v = nd.path[-1]
                e = Line(mobs[nd.parent].get_bottom(), mobs[nd.id].get_top(), stroke_color=C_GREY, stroke_width=2.5)
                edges[nd.id] = e
                elabs[nd.id] = MathTex(str(v), color=NUMC[v]).scale(0.5).move_to(e.point_from_proportion(0.5))
                elabs[nd.id].shift(normalize(rotate_vector(e.get_unit_vector(), PI / 2)) * 0.18)
        return nodes, mobs, edges, elabs

    def tree_beat(self):
        self.beat("tree")
        nodes, mobs, edges, elabs = self.build_tree()
        self.nodes, self.mobs, self.edges, self.elabs = nodes, mobs, edges, elabs
        self.play(FadeIn(mobs[0], scale=1.3), run_time=0.6)
        counts = P.level_counts(3)
        clabs = VGroup()
        tex = {1: "3", 2: r"3\times 2=6", 3: r"3\times 2\times 1=6"}
        for d, key in ((1, "第一层"), (2, "第二层"), (3, "第三层")):
            self.wait_until(self.cue_start(key, self.now))
            lvl = [nd for nd in nodes if nd.depth == d]
            c = MathTex(tex[d], color=C_YELLOW).scale(0.55).move_to([6.3, mobs[lvl[0].id].get_y(), 0])
            assert counts[d] == len(lvl)
            clabs.add(c)
            self.play(LaggedStart(*[AnimationGroup(Create(edges[nd.id]), FadeIn(elabs[nd.id]),
                                                   GrowFromPoint(mobs[nd.id], mobs[nd.parent].get_center()))
                                    for nd in lvl], lag_ratio=0.12), FadeIn(c), run_time=1.6)
        self.wait_until(self.cue_start("最底层", self.now) + 1.0)
        leaves = [mobs[nd.id] for nd in nodes if not nd.children]
        self.play(LaggedStart(*[m[0].animate.set_stroke(C_GREEN, 4) for m in leaves], lag_ratio=0.15),
                  run_time=1.6)
        self.clabs = clabs
        self.tree = VGroup(*mobs.values(), *edges.values(), *elabs.values())

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        code = code_block("def dfs():\n    if len(path) == len(a):\n        res.append(path[:])\n        return\n"
                          "    for i in range(len(a)):\n        if used[i]:\n            continue\n"
                          "        used[i] = True\n        path.append(a[i])\n        dfs()\n"
                          "        path.pop()\n        used[i] = False\n", 22)
        code.move_to([-3.1, 0.15, 0])
        self.tree.save_state()
        self.play(FadeOut(self.clabs), self.tree.animate.scale(0.5).move_to([3.6, 0.9, 0]), run_time=1.0)
        self.play(FadeIn(code, shift=RIGHT * 0.3), run_time=0.8)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.05, stroke_width=2)
            tag = T(txt, 24, col).next_to(hl, RIGHT, buff=0.25)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.7)
            tags.add(hl, tag)
        mark([1, 2, 3], "路径长度", "叶子：收答案", C_GREEN)
        mark([7, 8], "标记", "选择", C_BLUE)
        mark([9], "递归", "递归", C_YELLOW)
        mark([10, 11], "撤销", "撤销", C_RED)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, tags)), Restore(self.tree), run_time=0.8)

    # ---------------------------------------------------------------- 走一遍：选择 / 收答案 / 撤销
    def walk_beat(self):
        self.beat("walk")
        nodes, mobs, edges = self.nodes, self.mobs, self.edges
        for m in mobs.values():
            m[0].set_stroke(C_GREY, 2.5)
        hdr = VGroup(T("path", 24, C_GREY).move_to([-5.0, STRIP_Y + 0.75, 0]),
                     T("used", 24, C_GREY).move_to([-1.3, STRIP_Y + 0.75, 0]),
                     T("res", 24, C_GREY).move_to([4.05, STRIP_Y + 0.75, 0]))
        slots = VGroup(*[Square(0.62, stroke_color=C_GREY, stroke_width=2).move_to([-5.72 + 0.72 * k, STRIP_Y, 0])
                         for k in range(3)])
        pool = {v: tile(v).move_to([-2.02 + 0.72 * (v - 1), STRIP_Y, 0]) for v in A}
        rslots = VGroup(*[RoundedRectangle(corner_radius=0.08, width=0.78, height=0.5, stroke_color=C_GREY,
                                           stroke_width=1.5).move_to([1.9 + 0.86 * k, STRIP_Y, 0]) for k in range(6)])
        self.play(FadeIn(hdr), FadeIn(slots), FadeIn(rslots), *[FadeIn(t) for t in pool.values()], run_time=0.8)
        ptr = SurroundingRectangle(mobs[0], color=C_YELLOW, buff=0.07, corner_radius=0.14)
        self.play(Create(ptr), run_time=0.4)
        ev = P.walk_events(A)
        first_up = next(k for k, e in enumerate(ev) if e[0] == "up")
        t_up = self.cue_start("往回退", self.now + 6)
        t_end = self.cue_start("一共走遍", self.now + 12)
        stack, n_res, undo_tag, self.res_list = [], 0, None, []
        for k, e in enumerate(ev):
            if k < first_up:                              # 第一条路慢慢走，到叶子正好讲到「拷贝」
                rt = 0.9
            else:
                if k == first_up:
                    self.wait_until(t_up)
                rt = max(0.28, min(0.7, (t_end - self.now) / max(1, len(ev) - k)))
            if e[0] == "down":
                nid, i = e[1], e[2]
                v = A[i]
                t = tile(v).move_to(pool[v])
                stack.append(t)
                self.play(ptr.animate.move_to(mobs[nid]), edges[nid].animate.set_stroke(NUMC[v], 4),
                          t.animate.move_to(slots[len(stack) - 1]), pool[v].animate.set_opacity(0.18), run_time=rt)
            elif e[0] == "collect":
                nid = e[1]
                txt = Text("".join(str(x) for x in nodes[nid].path), font=MONO, font_size=22).move_to(rslots[n_res])
                n_res += 1
                self.res_list.append(txt)
                self.play(TransformFromCopy(VGroup(*stack), txt), mobs[nid][0].animate.set_stroke(C_GREEN, 4),
                          Flash(mobs[nid], color=C_GREEN, flash_radius=0.6, line_length=0.15), run_time=rt * 1.1)
            else:
                nid, i = e[1], e[2]
                v = A[i]
                t = stack.pop()
                parent = nodes[nid].parent
                anims = [ptr.animate.move_to(mobs[parent]), edges[nid].animate.set_stroke(C_GREY, 2.5).set_opacity(0.55),
                         t.animate.move_to(pool[v]).set_opacity(0), pool[v].animate.set_opacity(1)]
                if undo_tag is None:
                    undo_tag = T("撤销", 24, C_RED).next_to(hdr[0], RIGHT, buff=0.35)
                    anims.append(FadeIn(undo_tag, shift=DOWN * 0.2))
                self.play(*anims, run_time=rt)
                self.remove(t)
        self.play(FadeOut(ptr), FadeOut(undo_tag), Circumscribe(rslots, color=C_GREEN), run_time=0.9)
        self.strip = VGroup(hdr, slots, rslots, *pool.values())
        self.wait(max(0.1, self.left() - 0.4))

    # ---------------------------------------------------------------- 拷贝的陷阱
    def copy_beat(self):
        self.beat("copy")
        self.play(FadeOut(self.tree), FadeOut(self.strip), FadeOut(VGroup(*self.res_list)), run_time=0.7)
        good_t = VGroup(Text("res.append(path[:])", font=MONO, font_size=26, color=C_GREEN),
                        MathTex(r"\checkmark", color=C_GREEN)).arrange(RIGHT, buff=0.3).move_to([-3.6, 2.8, 0])
        bad_t = VGroup(Text("res.append(path)", font=MONO, font_size=26, color=C_RED),
                       MathTex(r"\times", color=C_RED)).arrange(RIGHT, buff=0.3).move_to([3.6, 2.8, 0])
        leaves = [list(nd.path) for nd in self.nodes if not nd.children]
        good = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.08, width=1.45, height=0.55, stroke_color=C_GREEN,
                                                stroke_width=2), path_tex(p, 0.55)) for p in leaves])
        for g in good:
            g[1].move_to(g[0])
        good.arrange_in_grid(3, 2, buff=(0.35, 0.3)).move_to([-3.6, 0.6, 0])
        self.play(FadeIn(good_t), LaggedStart(*[FadeIn(g, shift=UP * 0.2) for g in good], lag_ratio=0.12),
                  run_time=1.4)
        self.wait_until(self.cue_start("直接存", self.now))
        cells = VGroup(*[RoundedRectangle(corner_radius=0.08, width=0.75, height=0.55, stroke_color=C_RED,
                                          stroke_width=2) for _ in range(6)]).arrange(RIGHT, buff=0.2)
        cells.move_to([3.6, -0.7, 0])
        box = RoundedRectangle(corner_radius=0.1, width=1.9, height=0.7, stroke_color=C_YELLOW, stroke_width=3)
        box.move_to([3.6, 1.35, 0])
        blab = T("path", 22, C_YELLOW).next_to(box, LEFT, buff=0.2)
        content = path_tex([3, 2, 1], 0.7).move_to(box)
        arrows = VGroup(*[Arrow(c.get_top(), box.get_bottom(), buff=0.06, color=C_RED, stroke_width=2.5,
                                max_tip_length_to_length_ratio=0.08) for c in cells])
        self.play(FadeIn(bad_t), FadeIn(cells), Create(box), FadeIn(blab), FadeIn(content), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), run_time=1.2)
        self.wait_until(self.cue_start("弹空", self.now))
        for p in ([3, 2], [3], []):
            new = path_tex(p, 0.7).move_to(box)
            self.play(Transform(content, new), run_time=0.45)
        empties = VGroup(*[MathTex(r"[\;]", color=C_RED).scale(0.6).move_to(c) for c in cells])
        self.play(LaggedStart(*[FadeIn(x, scale=1.5) for x in empties], lag_ratio=0.1), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(good_t, bad_t, good, cells, box, blab, content, arrows, empties)), run_time=0.6)

    # ---------------------------------------------------------------- 数节点：O(n · n!)
    def count_beat(self):
        self.beat("count")
        for nid, m in self.mobs.items():
            m[0].set_stroke(C_GREY, 2.5)
        for e in self.edges.values():
            e.set_stroke(C_GREY, 2.5).set_opacity(1)
        self.play(FadeIn(self.tree), run_time=0.8)
        counts = P.level_counts(3)
        ys = [2.9, 1.85, 0.8, -0.25]
        labs = VGroup(*[MathTex(str(c), color=C_YELLOW).scale(0.8).move_to([6.2, y, 0]) for c, y in zip(counts, ys)])
        self.wait_until(self.cue_start("从下往上", self.now) + 1.2)
        for d in (3, 2, 1, 0):
            lvl = [self.mobs[nd.id] for nd in self.nodes if nd.depth == d]
            self.play(FadeIn(labs[d], scale=1.4), *[Indicate(m, color=C_YELLOW, scale_factor=1.08) for m in lvl],
                      run_time=0.55)
        total = MathTex("=", str(P.node_total(3)), color=C_YELLOW).scale(0.9)
        line = Line([5.8, -0.65, 0], [6.6, -0.65, 0], stroke_color=C_YELLOW, stroke_width=2)
        total.next_to(line, DOWN, buff=0.15)
        self.play(Create(line), FadeIn(total), run_time=0.6)
        f1 = MathTex(r"16", "=", r"3!\left(\frac{1}{0!}+\frac{1}{1!}+\frac{1}{2!}+\frac{1}{3!}\right)").scale(0.8)
        f1.move_to([0, -1.45, 0])
        self.wait_until(self.cue_start("一般地", self.now))
        self.play(Write(f1), run_time=1.6)
        f2 = MathTex(r"n!\sum_{k=0}^{n}\frac{1}{k!}", "<", r"e\cdot n!", r"\quad\Rightarrow\quad",
                     r"O(n\cdot n!)").scale(0.8)
        f2[2].set_color(C_YELLOW)
        f2[4].set_color(C_RED)
        f2.move_to([0, -2.55, 0])
        self.wait_until(self.cue_start("这个和小于", self.now))
        self.play(Write(f2[:3]), run_time=1.4)
        self.wait_until(self.cue_start("每个节点", self.now))
        self.play(Write(f2[3:]), run_time=1.0)
        self.wait_until(self.cue_start("不超过十", self.now))
        ten = MathTex(r"n\le 10", color=C_RED).scale(0.9).next_to(f2, RIGHT, buff=0.4)
        self.play(FadeIn(ten, scale=1.4), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(self.tree, labs, line, total, f1, f2, ten)), run_time=0.6)

    # ---------------------------------------------------------------- 显式与隐式回溯
    def implicit_beat(self):
        self.beat("implicit")
        left = code_block("for i in range(len(a)):\n    if used[i]:\n        continue\n    used[i] = True\n"
                          "    path.append(a[i])\n    dfs()\n    path.pop()\n    used[i] = False\n", 22)
        right = code_block("def dfs(p):\n    if len(p) == len(a):\n        res.append(p)\n        return\n"
                           "    for x in a:\n        if x not in p:\n            dfs(p + [x])\n", 22)
        left.move_to([-3.5, 0.9, 0])
        right.move_to([3.5, 0.9, 0])
        lt = T("显式回溯", 30, C_RED).next_to(left, UP, buff=0.3)
        rt = T("隐式回溯", 30, C_GREEN).next_to(right, UP, buff=0.3)
        self.play(FadeIn(left, shift=RIGHT * 0.2), FadeIn(lt), run_time=0.8)
        self.play(FadeIn(right, shift=LEFT * 0.2), FadeIn(rt), run_time=0.8)
        hr = SurroundingRectangle(right.code_lines[6], color=C_GREEN, buff=0.05, stroke_width=2)
        self.play(Create(hr), run_time=0.6)
        self.wait_until(self.cue_start("栈帧", self.now))
        hl = SurroundingRectangle(VGroup(left.code_lines[6], left.code_lines[7]), color=C_RED, buff=0.05,
                                  stroke_width=2)
        ltag = T("手动撤销", 22, C_RED).next_to(left, DOWN, buff=0.25)
        rtag = T("返回时栈帧丢弃，自动恢复", 22, C_GREEN).next_to(right, DOWN, buff=0.25)
        self.play(Create(hl), FadeIn(ltag), FadeIn(rtag), run_time=0.9)
        self.wait_until(self.cue_start("规律", self.now))
        rule = VGroup(
            VGroup(T("传值的状态", 28, C_GREEN), T("返回后自动恢复", 28)).arrange(RIGHT, buff=0.5),
            VGroup(T("共享且原地修改的状态", 28, C_RED), T("必须手动撤销", 28)).arrange(RIGHT, buff=0.5),
        ).arrange(DOWN, buff=0.28, aligned_edge=LEFT).move_to([0, -2.35, 0])
        self.play(FadeIn(rule[0], shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("共享且", self.now))
        self.play(FadeIn(rule[1], shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(left, right, lt, rt, hr, hl, ltag, rtag, rule)), run_time=0.6)

    # ---------------------------------------------------------------- 子集：选或不选
    def subsets_beat(self):
        self.beat("subsets")
        nodes = P.subset_tree(A)
        mid = (max(n.x for n in nodes) + min(n.x for n in nodes)) / 2
        ys = {0: 2.7, 1: 1.55, 2: 0.4, 3: -0.8}
        mobs, edges = {}, {}
        for nd in nodes:
            lab = path_tex(list(nd.path), 0.55)
            box = RoundedRectangle(corner_radius=0.1, width=max(0.62, lab.width + 0.25), height=0.48,
                                   stroke_color=C_GREY, stroke_width=2)
            mobs[nd.id] = VGroup(box, lab).move_to([(nd.x - mid) * 1.45, ys[nd.depth], 0])
        for nd in nodes:
            for side, ch in enumerate(nd.children):
                v = A[nd.depth]
                col = NUMC[v] if side else C_GREY
                ln = Line(mobs[nd.id].get_bottom(), mobs[ch].get_top(), stroke_color=col, stroke_width=2.5)
                edges[ch] = DashedVMobject(ln, num_dashes=10) if side == 0 else ln
        legend = VGroup(T("左：不选", 24, C_GREY), T("右：选", 24, C_GREEN)).arrange(RIGHT, buff=0.6)
        legend.move_to([-4.6, 3.3, 0])
        self.play(FadeIn(mobs[0], scale=1.3), FadeIn(legend), run_time=0.7)
        step = max(0.9, min(1.6, (self.cue_start("三个元素", self.now + 6) - self.now) / 3))
        for d in (1, 2, 3):
            lvl = [nd for nd in nodes if nd.depth == d]
            self.play(LaggedStart(*[AnimationGroup(Create(edges[nd.id]),
                                                   GrowFromPoint(mobs[nd.id], mobs[nd.parent].get_center()))
                                    for nd in lvl], lag_ratio=0.08), run_time=step)
        leaves = [nd for nd in nodes if not nd.children]
        eight = MathTex(r"2^3 = 8", color=C_GREEN).scale(0.9).move_to([5.3, 3.3, 0])
        self.wait_until(self.cue_start("三个元素", self.now))
        self.play(LaggedStart(*[mobs[nd.id][0].animate.set_stroke(C_GREEN, 3.5) for nd in leaves], lag_ratio=0.1),
                  Write(eight), run_time=1.6)
        self.wait_until(self.cue_start("只在叶子", self.now))
        root, first = mobs[0], mobs[leaves[0].id]
        no = Cross(root, stroke_color=C_RED, stroke_width=5).scale(0.8)
        self.play(Indicate(root, color=C_RED), Indicate(first, color=C_GREEN), run_time=0.9)
        note = T("中间的 [ ] 和叶子的 [ ] 是同一个子集", 24, C_RED).move_to([0, -1.75, 0])
        self.play(Create(no), FadeIn(note), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*mobs.values(), *edges.values(), legend, eight, no, note)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        eq = VGroup(T("回溯", 44, C_YELLOW), MathTex("="), T("DFS", 40), MathTex("+"), T("撤销", 40, C_RED))
        eq.arrange(RIGHT, buff=0.3).move_to([0, 2.6, 0])
        self.play(Write(eq), run_time=1.4)
        names = [("选择", C_BLUE), ("递归", C_YELLOW), ("撤销", C_RED)]
        R = 1.45
        pts = [np.array([R * np.cos(PI / 2 + 2 * PI * k / 3), R * np.sin(PI / 2 + 2 * PI * k / 3) - 0.35, 0])
               for k in range(3)]
        circ = VGroup()
        for (name, col), p in zip(names, pts):
            c = Circle(0.55, stroke_color=col, stroke_width=4).set_fill(col, 0.15).move_to(p)
            circ.add(VGroup(c, T(name, 26, col).move_to(c)))
        arcs = VGroup(*[CurvedArrow(pts[k] + (pts[(k + 1) % 3] - pts[k]) * 0.28,
                                    pts[(k + 1) % 3] - (pts[(k + 1) % 3] - pts[k]) * 0.28,
                                    angle=-PI / 3, color=C_GREY, stroke_width=3, tip_length=0.18) for k in range(3)])
        self.wait_until(self.cue_start("选择，递归", self.now))
        for k in range(3):
            self.play(FadeIn(circ[k], scale=1.3), Create(arcs[k]), run_time=0.7)
        dot = Dot(color=C_YELLOW, radius=0.11)
        loop = Arc(radius=R, start_angle=PI / 2, angle=2 * PI, arc_center=np.array([0, -0.35, 0]))
        self.play(MoveAlongPath(dot, loop, rate_func=linear),
                  Succession(*[Indicate(c, color=WHITE, scale_factor=1.15, run_time=0.7) for c in circ]),
                  run_time=2.1)
        self.play(FadeOut(dot), run_time=0.3)
        self.wait_until(self.cue_start("下一周", self.now))
        nxt = T("第 9 周：八皇后 · 组合 · 子集", 28, C_GREY).move_to([0, -2.6, 0])
        self.play(FadeIn(nxt, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 8 周 递归 P29–P35 · OpenJudge 02748 · LeetCode 78", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeOut(nxt), FadeIn(src), run_time=0.8)
        self.wait(1.5)
