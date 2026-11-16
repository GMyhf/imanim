"""中缀转后缀：调度场算法（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。转换与求值的每一步都来自 infixdata
（讲义五条规则插桩、OJ24591/24588 讲义原版；test_infix.py 对撞讲义输出、eval 与随机表达式）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infixdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

Y_IN, Y_OUT = 2.3, 0.55
ST_CX, ST_BASE, ST_W, ST_H, ITEM_H = 4.9, -2.75, 1.5, 3.1, 0.56
RULES = [("操作数", "直接输出"), ("左括号", "入栈"), ("右括号", "弹出并输出，直到左括号；左括号丢掉"),
         ("运算符", "栈顶不低于自己就弹出，然后入栈"), ("扫描结束", "栈里剩下的全部弹出")]


def tok_color(t):
    if t in "()":
        return C_BLUE
    if t in "+-*/":
        return C_YELLOW
    return WHITE


def tok(t, size=36):
    shown = {"*": "×", "/": "÷", "-": "−"}.get(t, t)
    return Text(shown, font=MONO, font_size=size, color=tok_color(t))


def fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


class InfixLesson(Lesson):
    def construct(self):
        for b in ("title", "yard", "rules", "simple", "run1", "run2", "assoc", "eval", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 调度场的骨架：轨道、侧线（栈）、规则表
    def slot(self, k):
        return np.array([ST_CX, ST_BASE + 0.12 + (ITEM_H + 0.06) * (k + 0.5), 0])

    def build_yard(self):
        l, r = ST_CX - ST_W / 2, ST_CX + ST_W / 2
        frame = VMobject(stroke_color=C_GREY, stroke_width=4).set_points_as_corners(
            [[l, ST_BASE + ST_H, 0], [l, ST_BASE, 0], [r, ST_BASE, 0], [r, ST_BASE + ST_H, 0]])
        slab = T("侧线 = 栈", 22, C_GREY).next_to(frame, LEFT, buff=0.25).align_to(frame, DOWN)
        rail_in = Line([-6.6, Y_IN - 0.42, 0], [6.6, Y_IN - 0.42, 0], stroke_color=C_GREY, stroke_width=2,
                       stroke_opacity=0.5)
        rail_out = Line([-6.6, Y_OUT - 0.42, 0], [3.4, Y_OUT - 0.42, 0], stroke_color=C_GREY, stroke_width=2,
                        stroke_opacity=0.5)
        lin = T("输入", 22, C_GREY).move_to([-6.15, Y_IN + 0.62, 0])
        lout = T("输出", 22, C_GREY).move_to([-6.15, Y_OUT + 0.62, 0])
        spur = CubicBezier([2.6, Y_IN - 0.42, 0], [3.8, Y_IN - 0.42, 0], [ST_CX, Y_IN - 0.42, 0],
                           [ST_CX, ST_BASE + ST_H + 0.1, 0], stroke_color=C_GREY, stroke_width=2).set_stroke(opacity=0.5)
        self.yard = dict(frame=frame, slab=slab, rails=VGroup(rail_in, rail_out, spur), lin=lin, lout=lout)
        return VGroup(frame, slab, rail_in, rail_out, spur, lin, lout)

    def build_rules(self):
        rows = VGroup()
        for k, (a, b) in enumerate(RULES):
            rows.add(VGroup(T(f"{k + 1}", 22, C_YELLOW), T(a, 22, C_BLUE), T(b, 22)))
        for r in rows:
            r[1].next_to(r[0], RIGHT, buff=0.25)
            r[2].next_to(r[0], RIGHT, buff=1.75)
        rows.arrange(DOWN, buff=0.17, aligned_edge=LEFT).move_to([-6.3, -1.95, 0], aligned_edge=LEFT)
        hl = Rectangle(width=8.6, height=0.4, stroke_width=0).set_fill(C_YELLOW, 0.14)
        hl.move_to(rows[0]).align_to(rows, LEFT).shift(LEFT * 0.1).set_fill(C_YELLOW, 0)
        self.rules, self.rule_hl = rows, hl
        return rows

    def light(self, k):
        """规则表第 k 条（0 起）高亮的动画。"""
        target = self.rule_hl.copy().set_y(self.rules[k].get_y()).set_fill(C_YELLOW, 0.14)
        return self.rule_hl.animate.become(target)

    def load_input(self, expr, x_center=-0.9):
        toks = D.tokenize(expr)
        row = VGroup(*[tok(t) for t in toks]).arrange(RIGHT, buff=0.26)
        row.move_to([x_center, Y_IN, 0])
        for m in row:
            m.set_y(Y_IN)
        return toks, row

    def run(self, expr, cue_of=None, step=0.55, row=None, toks=None, light=True, out_x0=-5.5):
        """按 convert_trace 的事件推动画面：输入记号开上输出轨道或拐进侧线。返回 (输出记号列表, 栈余项)。"""
        if row is None:
            toks, row = self.load_input(expr)
            self.play(FadeIn(row, shift=LEFT * 0.3), run_time=0.5)
        _, out, ev = D.convert_trace(expr)
        ptr = Triangle(color=WHITE).scale(0.1).rotate(PI).set_fill(WHITE, 1).next_to(row[0], UP, buff=0.12)
        self.play(FadeIn(ptr), run_time=0.25)
        outs, stack = [], []          # stack: [(框, 记号)]
        cur = -1
        cue_of = cue_of or {}
        x = out_x0
        for e in ev:
            k = e[1] if len(e) > 1 else None
            if k is not None and k != cur and k < len(toks):
                cur = k
                if k in cue_of:
                    self.wait_until(self.cue_start(cue_of[k], self.now))
                self.play(ptr.animate.next_to(row[k], UP, buff=0.12), run_time=step * 0.4)
            kind = e[0]
            if kind == "end":
                if "end" in cue_of:
                    self.wait_until(self.cue_start(cue_of["end"], self.now))
                self.play(FadeOut(ptr), *( [self.light(4)] if light else []), run_time=step * 0.5)
                continue
            if kind == "out":
                m = row[k]
                tgt = np.array([x + m.width / 2, Y_OUT, 0])
                x += m.width + 0.26
                self.play(m.animate.move_to(tgt), *([self.light(0)] if light else []), run_time=step)
                outs.append(m)
            elif kind in ("lpar", "push"):
                m = row[k]
                box = RoundedRectangle(corner_radius=0.08, width=ST_W - 0.26, height=ITEM_H, stroke_width=3,
                                       stroke_color=tok_color(toks[k])).set_fill(tok_color(toks[k]), 0.16)
                box.move_to(self.slot(len(stack)))
                rule = 1 if kind == "lpar" else 3
                self.play(m.animate.move_to(box), FadeIn(box), *([self.light(rule)] if light else []), run_time=step)
                stack.append((box, m))
            elif kind == "pop":
                box, m = stack.pop()
                tgt = np.array([x + m.width / 2, Y_OUT, 0])
                x += m.width + 0.26
                rule = 4 if k >= len(toks) else (2 if toks[k] == ")" else 3)
                self.play(m.animate.move_to(tgt), FadeOut(box), *([self.light(rule)] if light else []),
                          run_time=step)
                outs.append(m)
            elif kind == "drop":
                box, m = stack.pop()
                self.play(FadeOut(m, scale=0.5), FadeOut(box), FadeOut(row[k], scale=0.5),
                          *([self.light(2)] if light else []), run_time=step)
        assert [o.text for o in outs] == [tok(t).text for t in out]
        return outs

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        title = T("中缀转后缀：调度场算法", 44).move_to([0, 3.1, 0])
        ex = MathTex("23", "+", r"(34\times45)", r"\div", "(5+6+7)").scale(1.35).move_to([0, 1.55, 0])
        self.play(Write(title), run_time=1.0)
        self.play(Write(ex), run_time=1.6)
        self.wait_until(self.cue_start("人一眼", self.now))
        order = [(2, C_BLUE, "1"), (4, C_BLUE, "1"), (3, C_TEAL, "2"), (1, C_YELLOW, "3")]
        tags = VGroup()
        for i, col, n in order:
            tag = MathTex(n, color=col).scale(0.7).next_to(ex[i], DOWN, buff=0.18)
            self.play(ex[i].animate.set_color(col), FadeIn(tag, shift=UP * 0.1), run_time=0.6)
            tags.add(tag)
        self.wait_until(self.cue_start("一串字符", self.now))
        chars = list(D.BOOK)
        cells = VGroup()
        for c in chars:
            sq = Square(0.42, stroke_color=C_GREY, stroke_width=2)
            cells.add(VGroup(sq, Text(c, font=MONO, font_size=24).move_to(sq)))
        cells.arrange(RIGHT, buff=0.05).move_to([0, -0.2, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.15) for c in cells], lag_ratio=0.06), run_time=1.6)
        q = T("谁先算？", 26, C_RED).next_to(cells, RIGHT, buff=0.3)
        self.play(FadeIn(q), run_time=0.4)
        self.wait_until(self.cue_start("改写成后缀式", self.now))
        post = " ".join(D.convert_trace(D.BOOK)[1]).replace("*", "×").replace("/", "÷")
        pf = Text(post, font=MONO, font_size=32, color=C_YELLOW).move_to([0, -1.5, 0])
        plab = T("后缀式", 24, C_YELLOW).next_to(pf, LEFT, buff=0.4)
        self.play(TransformFromCopy(cells, pf), FadeIn(plab), FadeOut(q), run_time=1.4)
        self.wait_until(self.cue_start("调度场算法", self.now))
        name = T("调度场算法 · 迪杰斯特拉 1961", 26, C_TEAL).move_to([0, -2.45, 0])
        self.play(FadeIn(name, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ex, tags, cells, pf, plab, name)), title.animate.scale(0.7).move_to([0, 3.3, 0]),
                  run_time=0.6)
        self.title = title

    # ---------------------------------------------------------------- 调度场的比喻
    def yard_beat(self):
        self.beat("yard")
        yard = self.build_yard()
        self.play(Create(self.yard["rails"]), FadeIn(self.yard["lin"]), FadeIn(self.yard["lout"]), run_time=1.2)
        self.wait_until(self.cue_start("记号一节一节", self.now))
        toks, row = self.load_input("1+2", x_center=0.5)
        self.play(FadeIn(row, shift=LEFT * 0.4), run_time=0.6)
        self.play(Create(self.yard["frame"]), FadeIn(self.yard["slab"]), run_time=0.7)
        self.demo_outs = self.run("1+2", step=0.9, row=row, toks=toks, light=False)
        self.wait_until(self.cue_start("侧线只能", self.now))
        self.play(Indicate(self.yard["frame"], color=C_YELLOW, scale_factor=1.05),
                  Indicate(self.yard["slab"], color=C_YELLOW), run_time=1.0)
        self.wait_until(self.cue_start("什么时候", self.now))
        keys = VGroup(T("优先级", 26, C_YELLOW), T("括号", 26, C_BLUE)).arrange(RIGHT, buff=0.6).move_to([0.2, -1.4, 0])
        self.play(FadeIn(keys, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(keys), FadeOut(VGroup(*self.demo_outs)), run_time=0.6)

    # ---------------------------------------------------------------- 五条规则
    def rules_beat(self):
        self.beat("rules")
        rows = self.build_rules()
        self.add(self.rule_hl)
        keys = ["操作数", "左括号", "右括号", "运算符", "扫描结束"]
        for k, row in enumerate(rows):
            self.wait_until(self.cue_start("遇到" + keys[k] if k < 4 else keys[k], self.now))
            anims = [FadeIn(row, shift=RIGHT * 0.2), self.light(k)]
            self.play(*anims, run_time=0.6)
            if k == 3:
                self.wait_until(self.cue_start("不低于", self.now) if self.cue_start("不低于") else self.now)
                self.play(Indicate(row[2], color=C_YELLOW, scale_factor=1.06), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 两个小例子
    def simple_beat(self):
        self.beat("simple")
        keys = ["三加四乘二", "三乘四加二"]
        results = VGroup()
        for i, (expr, key) in enumerate(zip(D.SIMPLE, keys)):
            self.wait_until(self.cue_start(key, self.now))
            outs = self.run(expr, step=0.75)
            done = VGroup(*outs)
            res = VGroup(MathTex(expr.replace("*", r"\times"), color=C_GREY).scale(0.8),
                         MathTex(r"\to", color=C_GREY).scale(0.8),
                         Text(" ".join(D.convert_trace(expr)[1]).replace("*", "×"), font=MONO, font_size=26,
                              color=C_YELLOW)).arrange(RIGHT, buff=0.25)
            res.move_to([-3.3 + 4.6 * i, Y_OUT - 0.9, 0])
            self.play(ReplacementTransform(done, res[2]), FadeIn(res[:2]), run_time=0.7)
            results.add(res)
        self.wait_until(self.cue_start("从下往上", self.now))
        arrow = Arrow([ST_CX + 1.1, ST_BASE + 0.2, 0], [ST_CX + 1.1, ST_BASE + 2.6, 0], color=C_YELLOW,
                      stroke_width=5, buff=0)
        lab = T("优先级递增", 22, C_YELLOW).rotate(PI / 2).next_to(arrow, RIGHT, buff=0.08)
        self.play(GrowArrow(arrow), FadeIn(lab), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(results), FadeOut(arrow), FadeOut(lab), run_time=0.6)

    # ---------------------------------------------------------------- 原书例子
    def run1_beat(self):
        self.beat("run1")
        toks, row = self.load_input(D.BOOK, x_center=-0.6)
        self.wait_until(self.cue_start("回到原书", self.now))
        self.play(FadeIn(row, shift=LEFT * 0.4), run_time=0.8)
        self.book = dict(toks=toks, row=row)
        # 只跑到第一个右括号：把事件切开，第二段留给 run2
        self.book_gen = self.run_split()
        next(self.book_gen)

    def run_split(self):
        """原书例子分两个 beat 跑：用生成器在第一个右括号处暂停。"""
        toks, row = self.book["toks"], self.book["row"]
        _, out, ev = D.convert_trace(D.BOOK)
        ptr = Triangle(color=WHITE).scale(0.1).rotate(PI).set_fill(WHITE, 1).next_to(row[0], UP, buff=0.12)
        self.play(FadeIn(ptr), run_time=0.25)
        cues1 = {0: "二十三直接输出", 2: "左括号入栈", 3: "三十四输出", 6: "右括号来了"}
        cues2 = {7: "除号来了", 8: "又一个左括号", 12: "第二个加号", 13: "七输出", "end": "扫描结束"}
        outs, stack, cur, x = [], [], -1, -5.5
        first_rpar = toks.index(")")
        steps = {0: 0.7}
        paused = False
        for e in ev:
            k = e[1] if len(e) > 1 else None
            if not paused and k is not None and k > first_rpar:
                self.wait(max(0.1, self.left() - 0.2))
                paused = True
                yield
            cue_of = cues2 if paused else cues1
            step = 0.75
            if k is not None and k != cur and k < len(toks):
                cur = k
                if k in cue_of:
                    self.wait_until(self.cue_start(cue_of[k], self.now))
                self.play(ptr.animate.next_to(row[k], UP, buff=0.12), run_time=0.3)
            kind = e[0]
            if kind == "end":
                self.wait_until(self.cue_start(cue_of["end"], self.now))
                self.play(FadeOut(ptr), self.light(4), run_time=0.4)
                continue
            if kind == "out":
                m = row[k]
                tgt = np.array([x + m.width / 2, Y_OUT, 0])
                x += m.width + 0.26
                self.play(m.animate.move_to(tgt), self.light(0), run_time=step)
                outs.append(m)
            elif kind in ("lpar", "push"):
                m = row[k]
                box = RoundedRectangle(corner_radius=0.08, width=ST_W - 0.26, height=ITEM_H, stroke_width=3,
                                       stroke_color=tok_color(toks[k])).set_fill(tok_color(toks[k]), 0.16)
                box.move_to(self.slot(len(stack)))
                self.play(m.animate.move_to(box), FadeIn(box), self.light(1 if kind == "lpar" else 3), run_time=step)
                stack.append((box, m))
                if kind == "lpar" and k == 2:
                    wall = T("墙", 22, C_BLUE).next_to(box, LEFT, buff=0.2)
                    self.play(Indicate(m, color=C_BLUE, scale_factor=1.4), FadeIn(wall), run_time=0.9)
                    self.play(FadeOut(wall), run_time=0.3)
            elif kind == "pop":
                box, m = stack.pop()
                tgt = np.array([x + m.width / 2, Y_OUT, 0])
                x += m.width + 0.26
                rule = 4 if k >= len(toks) else (2 if toks[k] == ")" else 3)
                if rule == 3:
                    same = T("同级，先弹", 22, C_YELLOW).next_to(box, LEFT, buff=0.2)
                    self.play(FadeIn(same), Indicate(m, color=C_YELLOW), run_time=0.7)
                    self.play(m.animate.move_to(tgt), FadeOut(box), FadeOut(same), self.light(rule), run_time=step)
                else:
                    self.play(m.animate.move_to(tgt), FadeOut(box), self.light(rule), run_time=step)
                outs.append(m)
            elif kind == "drop":
                box, m = stack.pop()
                self.play(FadeOut(m, scale=0.5), FadeOut(box), FadeOut(row[k], scale=0.5), self.light(2),
                          run_time=step)
        assert [o.text for o in outs] == [tok(t).text for t in out]
        self.book_outs = outs
        yield

    def run2_beat(self):
        self.beat("run2")
        next(self.book_gen, None)
        done = Text("✓", font=FONT, font_size=30, color=C_GREEN).next_to(self.book_outs[-1], RIGHT, buff=0.3)
        self.play(FadeIn(done), *[Indicate(o, color=C_GREEN, scale_factor=1.1) for o in self.book_outs],
                  run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(done), FadeOut(VGroup(*self.book_outs)), run_time=0.6)

    # ---------------------------------------------------------------- 左结合：「不低于」承重
    def assoc_beat(self):
        self.beat("assoc")
        self.play(Indicate(self.rules[3][2], color=C_YELLOW, scale_factor=1.08), self.light(3), run_time=1.2)
        self.wait_until(self.cue_start("看一减二减三", self.now))
        outs = self.run(D.ASSOC, step=0.6)
        self.wait_until(self.cue_start("按不低于", self.now))
        good_post = D.convert_trace(D.ASSOC)[1]
        bad_post = D.convert_trace(D.ASSOC, strict=True)[1]
        gv, bv = D.eval_trace(good_post)[0], D.eval_trace(bad_post)[0]
        assert (gv, bv) == (-4, 2)
        good = VGroup(T("不低于就弹", 22, C_GREEN),
                      Text(" ".join(good_post).replace("-", "−"), font=MONO, font_size=26),
                      MathTex(rf"=(1-2)-3={fmt(gv)}", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.35)
        bad = VGroup(T("高于才弹", 22, C_RED),
                     Text(" ".join(bad_post).replace("-", "−"), font=MONO, font_size=26),
                     MathTex(rf"=1-(2-3)={fmt(bv)}", color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.35)
        good.move_to([-1.5, Y_OUT, 0])
        bad.move_to([-1.5, Y_OUT - 0.85, 0]).align_to(good, LEFT)
        self.play(ReplacementTransform(VGroup(*outs), good[1]), FadeIn(good[0]), run_time=0.8)
        self.play(Write(good[2]), run_time=0.8)
        self.wait_until(self.cue_start("如果写成高于", self.now))
        self.play(FadeIn(bad[:2], shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("等于二", self.now + 3) if self.cue_start("等于二") else self.now + 3)
        self.play(Write(bad[2]), run_time=0.8)
        cross = Cross(bad, stroke_color=C_RED, stroke_width=4).scale(1.02)
        self.play(Create(cross), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(good, bad, cross, self.rules, self.rule_hl, self.yard["rails"], self.yard["lin"],
                                 self.yard["lout"], self.yard["slab"])), run_time=0.6)

    # ---------------------------------------------------------------- 后缀求值
    def eval_beat(self):
        self.beat("eval")
        post = D.convert_trace(D.BOOK)[1]
        res, ev = D.eval_trace(post)
        row = VGroup(*[tok(t, 34) for t in post]).arrange(RIGHT, buff=0.3).move_to([-0.6, Y_IN, 0])
        slab = T("操作数栈", 22, C_GREY).next_to(self.yard["frame"], LEFT, buff=0.25).align_to(self.yard["frame"], DOWN)
        self.play(FadeIn(row, shift=DOWN * 0.2), FadeIn(slab), run_time=0.8)
        rules = VGroup(T("遇到数：压栈", 24, C_BLUE), T("遇到运算符：弹出两个，算完压回", 24, C_YELLOW))
        rules.arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([-3.2, Y_OUT + 0.2, 0])
        self.play(FadeIn(rules[0]), run_time=0.5)
        self.play(FadeIn(rules[1]), run_time=0.5)
        ptr = Triangle(color=WHITE).scale(0.1).rotate(PI).set_fill(WHITE, 1).next_to(row[0], UP, buff=0.12)
        self.play(FadeIn(ptr), run_time=0.3)
        stack = []
        calc = np.array([-2.2, -1.3, 0])
        seg_end = {2: self.cue_start("三十四乘四十五", self.now + 4), 8: self.cue_start("注意除号", self.now + 10)}
        for j, e in enumerate(ev):
            k = e[1]
            if j == 3:
                self.wait_until(seg_end[2])
            if j == 9:
                self.wait_until(seg_end[8])
            if j == 10:
                self.wait_until(self.cue_start("最后二十三", self.now))
            slow = j == 9
            self.play(ptr.animate.next_to(row[k], UP, buff=0.12), run_time=0.25)
            if e[0] == "num":
                box = RoundedRectangle(corner_radius=0.08, width=ST_W - 0.26, height=ITEM_H, stroke_width=3,
                                       stroke_color=C_BLUE).set_fill(C_BLUE, 0.16).move_to(self.slot(len(stack)))
                lab = Text(fmt(e[2]), font=MONO, font_size=28).move_to(box)
                self.play(TransformFromCopy(row[k], lab), FadeIn(box), row[k].animate.set_opacity(0.3),
                          run_time=0.55)
                stack.append(VGroup(box, lab))
            else:
                _, k, t, a, b, r = e
                ib = stack.pop()
                ia = stack.pop()
                anims = [row[k].animate.set_opacity(0.3)]
                if slow:
                    lb = T("先弹：右", 20, C_RED).next_to(ib, LEFT, buff=0.15)
                    la = T("后弹：左", 20, C_TEAL).next_to(ia, LEFT, buff=0.15)
                    self.play(*anims, FadeIn(lb), run_time=0.8)
                    self.play(FadeIn(la), run_time=0.8)
                    self.wait(1.5)
                    anims = [FadeOut(lb), FadeOut(la)]
                sym = {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[t]
                eq = MathTex(fmt(a), sym, fmt(b), "=", fmt(r)).scale(1.0).move_to(calc)
                eq[0].set_color(C_TEAL)
                eq[2].set_color(C_RED)
                self.play(ReplacementTransform(ia[1], eq[0]), ReplacementTransform(ib[1], eq[2]), FadeIn(eq[1]),
                          FadeIn(eq[3]), FadeOut(ia[0]), FadeOut(ib[0]), *anims, run_time=0.7 if not slow else 1.0)
                self.play(Write(eq[4]), run_time=0.4)
                box = RoundedRectangle(corner_radius=0.08, width=ST_W - 0.26, height=ITEM_H, stroke_width=3,
                                       stroke_color=C_GREEN).set_fill(C_GREEN, 0.16).move_to(self.slot(len(stack)))
                lab = Text(fmt(r), font=MONO, font_size=28, color=C_GREEN).move_to(box)
                self.play(ReplacementTransform(eq[4], lab), FadeIn(box), FadeOut(eq[:4]), run_time=0.6)
                stack.append(VGroup(box, lab))
        assert fmt(res) == "108"
        self.play(FadeOut(ptr), Indicate(stack[-1], color=C_YELLOW, scale_factor=1.3), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(row, rules, slab, self.yard["frame"], *stack)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        def box(txt, col):
            t = T(txt, 26, col)
            r = RoundedRectangle(corner_radius=0.12, width=t.width + 0.5, height=0.85, stroke_color=col,
                                 stroke_width=3).set_fill(col, 0.1)
            return VGroup(r, t.move_to(r))
        a = MathTex(r"23+(34\times45)\div(5+6+7)").scale(0.75)
        b = box("调度场 · 运算符栈", C_YELLOW)
        c = Text("23 34 45 × 5 6 + 7 + ÷ +", font=MONO, font_size=24, color=C_YELLOW)
        d = box("求值 · 操作数栈", C_GREEN)
        e = MathTex("108", color=C_GREEN).scale(1.1)
        chain = VGroup(a, b, c, d, e).arrange(DOWN, buff=0.42).move_to([0, 0.35, 0])
        arrows = VGroup(*[Arrow(chain[i].get_bottom(), chain[i + 1].get_top(), buff=0.06, stroke_width=4,
                                color=C_GREY, tip_length=0.16) for i in range(4)])
        self.play(FadeIn(a), run_time=0.5)
        for i in range(4):
            self.play(GrowArrow(arrows[i]), FadeIn(chain[i + 1], shift=DOWN * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("编译器", self.now))
        comp = T("编译器翻译算式走的也是这条路", 24, C_TEAL).move_to([0, -2.55, 0])
        self.play(FadeIn(comp), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 3 周 栈与队列 1.4–1.5 · OpenJudge 24591、24588", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(VGroup(chain, arrows, comp, src, self.title)), run_time=0.6)
