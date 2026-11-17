"""食物链：把关系也存进并查集（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例逐句的检查、合并与各结点归属都来自 foodchaindata
（讲义 food_chain 的插桩版；test_foodchain.py 用穷举物种分配、带权模 3 并查集对撞讲义输出与旁白数字）。
结点的颜色 = 它在第三句之后所属的那一类；只有自己一个点的集合不上色。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import foodchaindata as F  # noqa: E402
from cine import *  # noqa: E402,F403

DOM = ("同类域", "猎物域", "天敌域")
DOM_TEX = ("{v}", "{v}+n", "{v}+2n")
SPECIES = [C_BLUE, C_YELLOW, C_GREEN]
NUM = "零一二三四五六七"


def stmt_text(s):
    kind, x, y = s
    return f"{x} 和 {y} 同类" if kind == 1 else f"{x} 吃 {y}"


def tri_diagram(center, r=1.35, labels=("A", "B", "C"), scale=1.0):
    """三类成环：A 在上，B 右下，C 左下；箭头 = 吃。返回 (结点 dict, 箭头 dict)。"""
    cx, cy = center
    pos = {labels[0]: np.array([cx, cy + r, 0]),
           labels[1]: np.array([cx + r * 0.95, cy - r * 0.6, 0]),
           labels[2]: np.array([cx - r * 0.95, cy - r * 0.6, 0])}
    nodes = {k: VGroup(Circle(0.38 * scale, stroke_color=WHITE, stroke_width=3), T(k, int(30 * scale)))
             .move_to(p) for k, p in pos.items()}
    arrows = {}
    for a, b in zip(labels, labels[1:] + labels[:1]):
        arrows[(a, b)] = CurvedArrow(pos[a], pos[b], angle=-PI / 5, color=C_RED, stroke_width=3,
                                     tip_length=0.18).scale(0.62, about_point=(pos[a] + pos[b]) / 2)
    return nodes, arrows


class FoodChainLesson(Lesson):
    def construct(self):
        for b in ("title", "why", "domains", "same", "eat", "check", "run1", "run2", "missing", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def cue_at(self, key, default=None):
        """key 在句中的大致时刻：句起点 + 句长按字数比例。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        nodes, arrows = tri_diagram((-3.6, -0.3), r=1.7)
        eat = T("→ 表示「吃」", 24, C_GREY).move_to([-3.6, -2.5, 0])
        self.play(LaggedStart(*[FadeIn(n, scale=0.8) for n in nodes.values()], lag_ratio=0.2), run_time=0.9)
        self.play(LaggedStart(*[Create(a) for a in arrows.values()], lag_ratio=0.4), FadeIn(eat), run_time=1.4)
        self.wait_until(self.cue_start("一句一句", self.now))
        ex = [("1 吃 2", "真", C_GREEN), ("2 吃 1", "矛盾", C_RED), ("101 和 1 同类", "越界", C_RED),
              ("3 吃 3", "自己吃自己", C_RED)]
        rows = VGroup()
        for k, (s, v, col) in enumerate(ex):
            r = VGroup(T(s, 32), T(("✓ " if col == C_GREEN else "✗ ") + v, 28, col)).arrange(RIGHT, buff=0.4)
            rows.add(r)
        for r in rows:
            r[1].next_to(r[0], RIGHT, buff=0.45)
        rows.arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([3.0, -0.2, 0])
        self.play(FadeIn(rows[0][0], shift=LEFT * 0.2), run_time=0.5)
        self.play(FadeIn(rows[0][1]), FadeIn(rows[1][0], shift=LEFT * 0.2), run_time=0.5)
        self.wait_until(self.cue_start("矛盾", self.now))
        for k in (1, 2, 3):
            anims = [FadeIn(rows[k][1])]
            if k + 1 < len(rows):
                anims.append(FadeIn(rows[k + 1][0], shift=LEFT * 0.2))
            self.play(*anims, run_time=0.6)
        self.wait_until(self.cue_start("一共有几句", self.now))
        title = T("食物链", 72).move_to([0, 0.5, 0])
        sub = VGroup(T("把关系也存进并查集", 34, C_BLUE), Text("OpenJudge 01182", font=MONO, font_size=24, color=C_GREY))
        sub.arrange(DOWN, buff=0.2).next_to(title, DOWN, buff=0.3)
        self.play(FadeOut(VGroup(rows, eat)), VGroup(*nodes.values(), *arrows.values()).animate.set_opacity(0.15),
                  run_time=0.5)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(title, sub, *nodes.values(), *arrows.values())), run_time=0.6)

    # ---------------------------------------------------------------- 为什么普通并查集不够
    def why_beat(self):
        self.beat("why")

        def pair(cx):
            a = VGroup(Circle(0.4, stroke_color=WHITE, stroke_width=3), MathTex("x").scale(0.9))
            b = VGroup(Circle(0.4, stroke_color=WHITE, stroke_width=3), MathTex("y").scale(0.9))
            VGroup(a, b).arrange(RIGHT, buff=1.2).move_to([cx, 1.1, 0])
            return a, b
        a1, b1 = pair(-3.5)
        blob = RoundedRectangle(corner_radius=0.5, width=3.3, height=1.3, stroke_color=C_GREEN, stroke_width=2)
        blob.set_fill(C_GREEN, 0.1).move_to(VGroup(a1, b1))
        h1 = T("x 和 y 同类", 28).move_to([-3.5, 2.6, 0])
        ok = T("同一个集合 ✓", 24, C_GREEN).next_to(blob, DOWN, buff=0.25)
        self.play(FadeIn(h1), FadeIn(a1), FadeIn(b1), run_time=0.7)
        self.play(Create(blob), FadeIn(ok), run_time=0.8)
        self.wait_until(self.cue_start("可是", self.now))
        a2, b2 = pair(3.5)
        h2 = T("x 吃 y", 28).move_to([3.5, 2.6, 0])
        ar = Arrow(a2.get_right(), b2.get_left(), buff=0.08, color=C_RED, stroke_width=4)
        self.play(FadeIn(h2), FadeIn(a2), FadeIn(b2), GrowArrow(ar), run_time=0.8)
        no = T("合并？x 和 y 就成同类了 ✗", 24, C_RED).move_to([3.5, 0.0, 0])
        self.play(FadeIn(no, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("好在", self.now))
        self.play(FadeOut(VGroup(a1, b1, blob, ok, h1, a2, b2, ar, h2, no)), run_time=0.6)
        nodes, arrows = tri_diagram((-2.0, 0.0), r=1.6)
        self.play(*[FadeIn(n) for n in nodes.values()], *[Create(a) for a in arrows.values()], run_time=1.0)
        self.wait_until(self.cue_start("知道了", self.now))
        tag = T("x", 26, C_BLUE).next_to(nodes["A"], UP, buff=0.12)
        self.play(nodes["A"][0].animate.set_stroke(C_BLUE, 5), FadeIn(tag), run_time=0.6)
        facts = VGroup(T("x 吃的：B", 30, C_YELLOW), T("吃 x 的：C", 30, C_GREEN)).arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        facts.move_to([2.6, -0.2, 0])
        self.play(Indicate(arrows[("A", "B")], color=C_YELLOW), nodes["B"][0].animate.set_stroke(C_YELLOW, 5),
                  FadeIn(facts[0], shift=LEFT * 0.2), run_time=0.8)
        self.play(Indicate(arrows[("C", "A")], color=C_GREEN), nodes["C"][0].animate.set_stroke(C_GREEN, 5),
                  FadeIn(facts[1], shift=LEFT * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tag, facts, *nodes.values(), *arrows.values())), run_time=0.6)

    # ---------------------------------------------------------------- 拆成三个域
    COLX, ROWY = (-4.3, -0.9), (1.2, -0.3, -1.8)

    def dom_node(self, v, k, color=WHITE):
        box = RoundedRectangle(corner_radius=0.15, width=1.55, height=0.72, stroke_color=color, stroke_width=3)
        lab = MathTex(DOM_TEX[k].format(v=v)).scale(0.8)
        return VGroup(box, lab)

    def domains_beat(self):
        self.beat("domains")
        cols = (C_BLUE, C_YELLOW, C_GREEN)
        heads = VGroup(*[T(DOM[k], 24, cols[k]).move_to([-6.0, y, 0]) for k, y in enumerate(self.ROWY)])
        xs = VGroup(*[self.dom_node("x", k).move_to([self.COLX[0], y, 0]) for k, y in enumerate(self.ROWY)])
        desc = VGroup(T("x 自己那一类", 26), T("x 吃的那一类", 26), T("吃 x 的那一类", 26))
        for k, d in enumerate(desc):
            d.move_to([0, self.ROWY[k], 0]).align_to([-3.1, 0, 0], LEFT)
        big = VGroup(Circle(0.42, stroke_color=WHITE, stroke_width=3), MathTex("x").scale(0.9)).move_to([self.COLX[0], 2.55, 0])
        self.play(FadeIn(big), run_time=0.5)
        keys = ("x 是同类域", "x 加 n 是", "x 加二 n 是")
        for k in range(3):
            self.wait_until(self.cue_start(keys[k], self.now))
            self.play(TransformFromCopy(big, xs[k]), FadeIn(heads[k]), FadeIn(desc[k], shift=LEFT * 0.2),
                      run_time=0.8)
        self.wait_until(self.cue_start("两个结点", self.now))
        ys = VGroup(*[self.dom_node("y", k).move_to([self.COLX[1], y, 0]) for k, y in enumerate(self.ROWY)])
        bigy = VGroup(Circle(0.42, stroke_color=WHITE, stroke_width=3), MathTex("y").scale(0.9)).move_to([self.COLX[1], 2.55, 0])
        self.play(FadeOut(desc), FadeIn(bigy), FadeIn(ys), run_time=0.7)
        rule = VGroup(T("同一个集合", 28, C_YELLOW), T("=", 28), T("同一类动物", 28, C_YELLOW)).arrange(RIGHT, buff=0.25)
        rule.move_to([3.6, -0.3, 0])
        frame = SurroundingRectangle(rule, color=C_YELLOW, buff=0.25, corner_radius=0.12)
        self.play(FadeIn(rule, shift=LEFT * 0.2), Create(frame), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rule, frame)), run_time=0.6)
        self.heads, self.xs, self.ys, self.bigs = heads, xs, ys, VGroup(big, bigy)

    def link(self, p, q, color, dashed=False, width=4):
        """generic 格子里连两个结点：p、q 是 (列 0/1, 域)。"""
        a = (self.xs if p[0] == 0 else self.ys)[p[1]]
        b = (self.xs if q[0] == 0 else self.ys)[q[1]]
        cls = DashedLine if dashed else Line
        return cls(a.get_right(), b.get_left(), color=color, stroke_width=width, buff=0.05)

    # ---------------------------------------------------------------- x 和 y 同类
    def same_beat(self):
        self.beat("same")
        head = T("x 和 y 同类", 32).move_to([3.6, 2.6, 0])
        self.play(FadeIn(head), run_time=0.5)
        self.wait_until(self.cue_start("自己相同", self.now))
        lines = VGroup(*[self.link((0, k), (1, k), C_TEAL) for k in range(3)])
        for k, key in enumerate(("自己相同", "猎物相同", "天敌也相同")):
            self.wait_until(self.cue_at(key, self.now))
            self.play(Create(lines[k]), run_time=0.5)
        code = VGroup(*[Text(s, font=MONO, font_size=24, color=C_TEAL) for s in
                        ("union(x, y)", "union(x+n, y+n)", "union(x+2n, y+2n)")]).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        code.move_to([3.6, 1.2, 0])
        self.play(FadeIn(code, shift=LEFT * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("什么时候是假话", self.now))
        self.play(lines.animate.set_stroke(opacity=0.25), code.animate.set_opacity(0.4), run_time=0.4)
        bad = VGroup(self.link((0, 0), (1, 1), C_RED, dashed=True), self.link((0, 0), (1, 2), C_RED, dashed=True))
        tags = VGroup(T("x 已在 y 的猎物域", 24, C_RED), T("x 已在 y 的天敌域", 24, C_RED)).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        lie = T("→ 假话", 26, C_RED)
        tags.move_to([3.6, -1.0, 0])
        lie.next_to(tags, DOWN, buff=0.25)
        self.wait_until(self.cue_at("x 已经落在", self.now))
        self.play(Create(bad[0]), FadeIn(tags[0]), run_time=0.7)
        self.wait_until(self.cue_at("天敌域里", self.now))
        self.play(Create(bad[1]), FadeIn(tags[1]), FadeIn(lie), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, lines, code, bad, tags, lie)), run_time=0.6)

    # ---------------------------------------------------------------- x 吃 y
    def eat_beat(self):
        self.beat("eat")
        head = T("x 吃 y", 32).move_to([3.8, 2.75, 0])
        nodes, arrows = tri_diagram((3.8, 0.55), r=1.2, scale=0.85)
        tx = T("x", 24, C_BLUE).next_to(nodes["A"], LEFT, buff=0.15)
        ty = T("y", 24, C_BLUE).next_to(nodes["B"], RIGHT, buff=0.15)
        self.play(FadeIn(head), *[FadeIn(n) for n in nodes.values()], *[Create(a) for a in arrows.values()],
                  FadeIn(tx), FadeIn(ty), run_time=0.9)
        spec = [((0, 1), (1, 0), C_YELLOW, "y 是 x 的猎物", "y 是 x 的猎物", [("A", "B")], "B"),
                ((0, 0), (1, 2), C_TEAL, "x 是 y 的天敌", "x 是 y 的天敌", [("A", "B")], "A"),
                ((0, 2), (1, 1), C_RED, "x 的天敌 = y 的猎物", "第三对", [("C", "A"), ("B", "C")], "C")]
        lines, tags = VGroup(), VGroup()
        for k, (p, q, col, txt, key, arr, hl) in enumerate(spec):
            self.wait_until(self.cue_start(key, self.now))
            ln = self.link(p, q, col)
            tag = T(f"{'①②③'[k]} {txt}", 24, col).move_to([3.8, -1.25 - 0.5 * k, 0])
            lines.add(ln)
            tags.add(tag)
            self.play(Create(ln), FadeIn(tag, shift=LEFT * 0.2), *[Indicate(arrows[a], color=col) for a in arr],
                      nodes[hl][0].animate.set_stroke(col, 5), run_time=0.9)
        self.wait_until(self.cue_start("三类成环", self.now))
        c_lab = T("吃 x，被 y 吃", 22, C_RED).next_to(nodes["C"], LEFT, buff=0.15)
        self.play(Indicate(nodes["C"], color=C_RED, scale_factor=1.25), FadeIn(c_lab),
                  Indicate(lines[2], color=C_RED), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, tx, ty, c_lab, *nodes.values(), *arrows.values(), lines, tags,
                                 self.heads, self.xs, self.ys, self.bigs)), run_time=0.6)

    # ---------------------------------------------------------------- 讲义代码
    def check_beat(self):
        self.beat("check")
        src = ("if x < 1 or x > n or y < 1 or y > n:\n    lies += 1\n    continue\n"
               "if kind == 1:\n"
               "    if d.connected(x, y + n) or d.connected(x, y + 2 * n):\n        lies += 1\n    else:\n"
               "        d.union(x, y)\n        d.union(x + n, y + n)\n        d.union(x + 2 * n, y + 2 * n)\n"
               "else:\n"
               "    if x == y or d.connected(x, y) or d.connected(x, y + n):\n        lies += 1\n    else:\n"
               "        d.union(x + n, y)\n        d.union(x, y + 2 * n)\n        d.union(x + 2 * n, y + n)\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 22})
        if code.height > 6.3:
            code.scale_to_fit_height(6.3)
        if code.width > 9.0:
            code.scale_to_fit_width(9.0)
        code.move_to([0, 0.2, 0]).to_edge(LEFT, buff=0.3)
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.8)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col, at=False):
            self.wait_until((self.cue_at if at else self.cue_start)(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=(0.08, 0.03), stroke_width=2)
            tag = T(txt, 22, col).next_to(code, RIGHT, buff=0.3).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
        mark([11], "判假话也查两对", "吃：查两对", C_RED)
        mark([14, 15, 16], "只有真话才去合并", "真话才合并：连三对", C_YELLOW, at=True)
        mark([0, 1, 2], "越界", "越界", C_GREY, at=True)
        mark([4], "这就是讲义", "同类：查两对、连三对", C_TEAL)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, tags)), run_time=0.6)

    # ---------------------------------------------------------------- 样例走一遍
    GX, GY, GR = (-5.0, -3.3, -1.6), (1.3, -0.2, -1.7), 0.4

    def build_grid(self):
        heads = VGroup(*[T(DOM[k], 22, C_GREY).move_to([-6.4, y, 0]) for k, y in enumerate(self.GY)])
        tops = VGroup(*[T(f"{a} 号", 26).move_to([x, 2.45, 0]) for a, x in zip(F.SHOW, self.GX)])
        nodes = {}
        for a, x in zip(F.SHOW, self.GX):
            for k, y in enumerate(self.GY):
                c = Circle(self.GR, stroke_color=WHITE, stroke_width=3).set_fill(WHITE, 0)
                nodes[(a, k)] = VGroup(c, MathTex(str(a)).scale(0.9)).move_to([x, y, 0])
        return heads, tops, nodes

    def build_list(self):
        rows = VGroup()
        for k, s in enumerate(F.SAMPLE):
            r = VGroup(T(f"{k + 1}.", 24, C_GREY), T(stmt_text(s), 26)).arrange(RIGHT, buff=0.2)
            r.move_to([0, 2.0 - 0.56 * k, 0]).align_to([0.4, 0, 0], LEFT)
            rows.add(r)
        return rows

    def recolor(self, nodes, rec, final):
        """按 rec 的集合归属上色：多于一个点的集合，用成员在 final 里所属那一类的颜色；单点集合不上色。"""
        size = {}
        for key, r in rec["groups"].items():
            size[r] = size.get(r, 0) + 1
        anims = []
        for key, n in nodes.items():
            if size[rec["groups"][key]] > 1:
                col = SPECIES[next(i for i, s in enumerate(final) if key in s)]
                anims.append(n[0].animate.set_fill(col, 0.35).set_stroke(col, 4))
            else:
                anims.append(n[0].animate.set_fill(WHITE, 0).set_stroke(WHITE, 3))
        return anims

    def gline(self, nodes, p, q, color, dashed=False):
        """两个结点之间连线；隔一列且行差为偶数时直线会穿过中间那个结点，改用弧线绕开。"""
        a, b = nodes[p].get_center(), nodes[q].get_center()
        cols = {x: i for i, x in enumerate(F.SHOW)}
        if abs(cols[p[0]] - cols[q[0]]) == 2 and (p[1] - q[1]) % 2 == 0:
            u = (b - a) / np.linalg.norm(b - a)
            arc = ArcBetweenPoints(a + u * (self.GR + 0.04), b - u * (self.GR + 0.04), angle=-1.6,
                                   color=color, stroke_width=4)
            return DashedVMobject(arc, num_dashes=24) if dashed else arc
        cls = DashedLine if dashed else Line
        return cls(a, b, color=color, stroke_width=4, buff=self.GR + 0.04)

    def verdict(self, rows, k, lie, x=3.3, note=None):
        txt = ("✗ " + (note or "假")) if lie else "✓ 真"
        m = T(txt, 24, C_RED if lie else C_GREEN)
        m.move_to([x, rows[k].get_y(), 0]).align_to([x, 0, 0], LEFT)
        return m

    def run1_beat(self):
        self.beat("run1")
        log = F.food_chain_trace()
        final = F.species_sets(log[2])
        heads, tops, nodes = self.build_grid()
        rows = self.build_list()
        hdr = T(f"n = {F.N}", 24, C_GREY).move_to([0.4, 2.65, 0], aligned_edge=LEFT)
        cnt = VGroup(T("假话", 26, C_RED), Integer(0, color=C_RED).scale(0.9)).arrange(RIGHT, buff=0.25)
        cnt.move_to([3.9, -2.4, 0])
        self.play(FadeIn(heads), FadeIn(tops), *[FadeIn(n) for n in nodes.values()], run_time=0.9)
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rows], lag_ratio=0.1), FadeIn(hdr),
                  FadeIn(cnt), run_time=1.2)
        marks = []
        cur = Rectangle(width=6.7, height=0.5, stroke_color=WHITE, stroke_width=2).move_to([3.6, rows[0].get_y(), 0])
        # 第一句：越界
        self.wait_until(self.cue_start("第一句", self.now))
        self.play(Create(cur), run_time=0.4)
        m = self.verdict(rows, 0, True, note="越界")
        self.play(FadeIn(m), ChangeDecimalToValue(cnt[1], 1), run_time=0.6)
        marks.append(m)
        for k, key in ((1, "第二句"), (2, "第三句")):
            self.wait_until(self.cue_start(key, self.now))
            rec = log[k]
            self.play(cur.animate.move_to([3.6, rows[k].get_y(), 0]), run_time=0.4)
            ls = VGroup()
            for p, q, _ in rec["unions"]:
                ln = self.gline(nodes, p, q, C_GREY)
                ls.add(ln)
                self.play(Create(ln), run_time=0.45)
            m = self.verdict(rows, k, False)
            self.play(*self.recolor(nodes, rec, final), FadeIn(m), run_time=0.7)
            self.play(FadeOut(ls), run_time=0.3)
            marks.append(m)
        self.wait_until(self.cue_start("九个结点只剩", self.now))
        self.play(*[Indicate(n, color=WHITE, scale_factor=1.12) for n in nodes.values()], run_time=0.8)
        self.wait_until(self.cue_start("一号、二号的天敌", self.now))
        trio = VGroup(*[nodes[key] for key in final[0]])
        rings = VGroup(*[Circle(self.GR + 0.12, stroke_color=C_BLUE, stroke_width=6).move_to(n) for n in trio])
        self.play(Create(rings), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.4))
        self.play(FadeOut(rings), run_time=0.4)
        self.g = dict(heads=heads, tops=tops, nodes=nodes, rows=rows, hdr=hdr, cnt=cnt, cur=cur, marks=marks,
                      final=final, log=log)

    def run2_beat(self):
        self.beat("run2")
        g = self.g
        nodes, rows, cnt, cur, log, final = g["nodes"], g["rows"], g["cnt"], g["cur"], g["log"], g["final"]
        lies = 1
        for k, key in ((3, "第四句"), (4, "第五句"), (5, "第六句"), (6, "第七句")):
            self.wait_until(self.cue_start(key, self.now))
            rec = log[k]
            self.play(cur.animate.move_to([3.6, rows[k].get_y(), 0]), run_time=0.4)
            if rec["why"] == "self":
                x = rec["stmt"][1]
                cross = Cross(nodes[(x, 0)], stroke_color=C_RED, stroke_width=5).scale(0.8)
                self.play(Create(cross), run_time=0.5)
                lies += 1
                m = self.verdict(rows, k, True, note="自己吃自己")
                self.play(FadeIn(m), ChangeDecimalToValue(cnt[1], lies), FadeOut(cross), run_time=0.7)
            elif rec["stmt"][1] in F.SHOW:
                chk = VGroup()
                for p, q, c in rec["checks"]:
                    ln = self.gline(nodes, p, q, C_RED if c else C_GREY, dashed=True)
                    rings = VGroup(*[Circle(self.GR + 0.1, stroke_color=C_RED if c else WHITE, stroke_width=5)
                                     .move_to(nodes[key]) for key in (p, q)])
                    chk.add(ln, rings)
                    self.play(Create(ln), Create(rings), run_time=0.6)
                    if c:
                        lab = T("已连通", 22, C_RED).next_to(ln.get_center(), DOWN, buff=0.12)
                        chk.add(lab)
                        self.play(FadeIn(lab), run_time=0.4)
                if rec["lie"]:
                    lies += 1
                    m = self.verdict(rows, k, True, note="矛盾")
                    self.play(FadeIn(m), ChangeDecimalToValue(cnt[1], lies), run_time=0.6)
                else:
                    m = self.verdict(rows, k, False)
                    self.play(FadeIn(m), run_time=0.5)
                    self.wait_until(self.cue_start("要连的三对", self.now))
                    self.play(FadeOut(chk), run_time=0.3)
                    chk = VGroup()
                    for p, q, ret in rec["unions"]:
                        ln = self.gline(nodes, p, q, C_GREY)
                        chk.add(ln)
                        self.play(Create(ln), run_time=0.35)
                    note = T(f"union → {rec['unions'][0][2]}，早已同集合", 22, C_GREY).move_to([-3.6, -2.5, 0])
                    chk.add(note)
                    self.play(FadeIn(note), run_time=0.5)
                    self.wait(0.8)
                self.play(FadeOut(chk), run_time=0.4)
            else:
                m = self.verdict(rows, k, rec["lie"])
                self.play(FadeIn(m), run_time=0.5)
            g["marks"].append(m)
        self.wait_until(self.cue_start("一共三句假话", self.now))
        self.play(Indicate(cnt, color=C_RED, scale_factor=1.3),
                  *[Indicate(g["marks"][k], color=C_RED) for k in range(len(log)) if log[k]["lie"]], run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 少连第三对
    def missing_beat(self):
        self.beat("missing")
        g = self.g
        nodes, rows, cur = g["nodes"], g["rows"], g["cur"]
        log2 = F.food_chain_trace(third=False)
        h1 = T("连三对", 20, C_GREY).move_to([3.3, 2.6, 0], aligned_edge=LEFT)
        h2 = T("少第三对", 20, C_PURPLE).move_to([6.3, 2.6, 0])
        self.play(FadeOut(cur), FadeOut(g["hdr"]), FadeIn(h1), FadeIn(h2),
                  *[n[0].animate.set_fill(WHITE, 0).set_stroke(WHITE, 3) for n in nodes.values()], run_time=0.8)
        self.wait_until(self.cue_start("删掉它", self.now))
        marks2 = []
        for k in (0, 1, 2):
            rec = log2[k]
            ls = VGroup(*[self.gline(nodes, p, q, C_PURPLE) for p, q, _ in rec["unions"]])
            m = T("✗" if rec["lie"] else "✓", 26, C_RED if rec["lie"] else C_GREEN).move_to([6.3, rows[k].get_y(), 0])
            anims = [FadeIn(m)] + ([Create(ls)] if len(ls) else [])
            self.play(*anims, run_time=0.6)
            if len(ls):
                self.play(*self.recolor(nodes, rec, g["final"]), FadeOut(ls), run_time=0.6)
            marks2.append(m)
        self.wait_until(self.cue_start("孤零零", self.now))
        lone = nodes[(3, 1)]
        ring = Circle(self.GR + 0.14, stroke_color=C_PURPLE, stroke_width=6).move_to(lone)
        lab = T("孤零零", 22, C_PURPLE).next_to(lone, RIGHT, buff=0.2)
        self.play(Create(ring), FadeIn(lab), run_time=0.7)
        self.wait_until(self.cue_start("一和三同类查不出", self.now))
        m4 = T("✗", 26, C_RED).move_to([6.3, rows[3].get_y(), 0])
        dl = self.gline(nodes, (1, 0), (3, 1), C_GREY, dashed=True)
        self.play(FadeIn(m4), Create(dl), run_time=0.6)
        m5 = T("✓", 26, C_GREEN).move_to([6.3, rows[4].get_y(), 0])
        bad5 = SurroundingRectangle(VGroup(g["marks"][4], m5), color=C_PURPLE, buff=0.08)
        self.play(FadeIn(m5), Create(bad5), run_time=0.7)
        wrong = VGroup(*[self.gline(nodes, p, q, C_PURPLE) for p, q, _ in log2[4]["unions"]])
        self.play(FadeOut(dl), Create(wrong), run_time=0.7)          # 错当真话，又连了三对
        self.play(FadeOut(wrong), run_time=0.4)
        self.wait_until(self.cue_start("接下来第六句", self.now))
        m6 = T("✗", 26, C_RED).move_to([6.3, rows[5].get_y(), 0])
        bad6 = SurroundingRectangle(VGroup(g["marks"][5], m6), color=C_PURPLE, buff=0.08)
        self.play(FadeIn(m6), Create(bad6), run_time=0.7)
        m7 = T("✓", 26, C_GREEN).move_to([6.3, rows[6].get_y(), 0])
        self.play(FadeIn(m7), run_time=0.4)
        self.wait_until(self.cue_start("总数碰巧", self.now))
        c2 = VGroup(T("假话", 26, C_PURPLE), Integer(log2[-1]["lies"], color=C_PURPLE).scale(0.9)).arrange(RIGHT, buff=0.25)
        c2.move_to([6.2, -2.4, 0])
        self.play(FadeIn(c2), run_time=0.6)
        self.wait_until(self.cue_start("可抓错了", self.now))
        self.play(Indicate(bad5, color=C_PURPLE), Indicate(bad6, color=C_PURPLE), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(g["heads"], g["tops"], *nodes.values(), rows, g["cnt"], *g["marks"], h1, h2,
                                 *marks2, ring, lab, m4, m5, m6, m7, bad5, bad6, c2)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        cols = (C_BLUE, C_YELLOW, C_GREEN)
        three = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.15, width=2.2, height=0.9, stroke_color=c, stroke_width=3),
                                T(t, 30, c)) for t, c in zip(("自己", "猎物", "天敌"), cols)]).arrange(RIGHT, buff=0.4)
        head = T("一个动物，三个结点", 36).next_to(three, UP, buff=0.45)
        VGroup(head, three).move_to([0, 1.8, 0])
        self.play(FadeIn(head), LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in three], lag_ratio=0.2), run_time=1.2)
        self.wait_until(self.cue_start("同类连三对", self.now))
        tab = VGroup(
            VGroup(T("同类", 34, C_TEAL), T("连三对", 32), T("查两对", 32)),
            VGroup(T("吃", 34, C_RED), T("连三对", 32), T("查两对", 32)),
        )
        for r, y in zip(tab, (-0.2, -1.2)):
            for m, x in zip(r, (-2.4, 0.0, 2.2)):
                m.move_to([x, y, 0])
        self.play(FadeIn(tab[0], shift=UP * 0.2), run_time=0.7)
        self.play(FadeIn(tab[1], shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 9 周 并查集 2.6 节 · OpenJudge 01182", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
