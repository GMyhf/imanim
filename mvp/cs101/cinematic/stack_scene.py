"""栈：后进先出的三种用法（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。括号匹配、后缀求值、接雨水的每一步都来自 stackdata
（讲义代码原样插桩；test_stack.py 对撞讲义输出、暴力判定、eval 与按列求水量）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stackdata as S  # noqa: E402
from cine import *  # noqa: E402,F403

BR_COL = {"(": C_BLUE, ")": C_BLUE, "[": C_YELLOW, "]": C_YELLOW, "{": C_GREEN, "}": C_GREEN}


class StackBox(VGroup):
    """开口朝上的竖直容器；push/pop 返回动画，内部按栈顺序排好元素。"""

    def __init__(self, cx=3.8, base=-2.5, height=3.6, width=1.5, item_h=0.5, label="栈"):
        super().__init__()
        self.cx, self.base, self.item_h, self.width = cx, base, item_h, width
        l, r = cx - width / 2, cx + width / 2
        self.frame = VMobject(stroke_color=C_GREY, stroke_width=4).set_points_as_corners(
            [[l, base + height, 0], [l, base, 0], [r, base, 0], [r, base + height, 0]])
        self.top_label = T(label, 22, C_GREY).next_to(self.frame, DOWN, buff=0.15)
        self.items: list[VGroup] = []
        self.add(self.frame, self.top_label)

    def slot(self, k):
        return np.array([self.cx, self.base + 0.12 + self.item_h * (k + 0.5) + 0.06 * k, 0])

    def make(self, text, color, tex=False, size=30):
        box = RoundedRectangle(corner_radius=0.08, width=self.width - 0.24, height=self.item_h,
                               stroke_color=color, stroke_width=3).set_fill(color, 0.22)
        lab = (MathTex(text, color=WHITE).scale(0.75) if tex else T(text, size)).move_to(box)
        return VGroup(box, lab)

    def push(self, item, src=None, rt=0.5):
        k = len(self.items)
        self.items.append(item)
        if src is not None:
            item.move_to(src)
        else:
            item.move_to(self.slot(k) + UP * 1.0).set_opacity(0)
        return item.animate(run_time=rt).move_to(self.slot(k)).set_opacity(1)

    def pop(self):
        return self.items.pop()


def token_row(tokens, y=2.2, x0=None, dx=0.8, color_of=None, scale=0.9):
    n = len(tokens)
    x0 = -(n - 1) * dx / 2 if x0 is None else x0
    row = VGroup()
    for k, tk in enumerate(tokens):
        col = color_of(tk) if color_of else WHITE
        row.add(Text(tk, font=MONO, font_size=int(40 * scale), color=col).move_to([x0 + dx * k, y, 0]))
    return row


class StackLesson(Lesson):
    def construct(self):
        for b in ("title", "ops", "paren", "fail", "postfix", "evaluate", "mono", "rain", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：一摞盘子
    def title_beat(self):
        self.beat("title")
        st = StackBox(cx=3.2, base=-2.5, height=3.9, width=2.0, item_h=0.55, label="")
        title = T("栈", 96).move_to([-3.2, 1.1, 0])
        sub = T("后进先出", 40, C_BLUE).next_to(title, DOWN, buff=0.3)
        self.play(Create(st.frame), run_time=0.8)
        cols = [C_TEAL, C_YELLOW, C_RED, C_BLUE]
        for k in range(3):
            self.play(st.push(st.make(str(k + 1), cols[k], tex=True), rt=0.55))
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait_until(self.cue_start("压入四", self.now))
        four = st.make("4", cols[3], tex=True)
        self.play(st.push(four, rt=0.7))
        tag = T("push(4)", 24, C_BLUE).next_to(four, RIGHT, buff=0.3)
        self.play(FadeIn(tag), run_time=0.3)
        self.wait_until(self.cue_start("再弹出", self.now) + 0.5)
        top = st.pop()
        tag2 = T("pop() → 4", 24, C_RED).move_to([3.2, 2.2, 0])
        self.play(top.animate.move_to([3.2, 1.75, 0]), FadeOut(tag), FadeIn(tag2), run_time=0.8)
        self.play(Indicate(top, color=C_RED), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(st, *st.items, top, title, sub, tag2)), run_time=0.6)

    # ---------------------------------------------------------------- 列表就是栈
    def ops_beat(self):
        self.beat("ops")
        rows = [("stack.append(x)", "压入", "O(1)", C_GREEN), ("stack.pop()", "弹出", "O(1)", C_GREEN),
                ("stack[-1]", "看栈顶", "O(1)", C_GREEN)]
        grp = VGroup()
        for code, what, cost, col in rows:
            grp.add(VGroup(Text(code, font=MONO, font_size=30), T(what, 28, C_GREY),
                           MathTex(cost, color=col).scale(0.9)))
        for r in grp:
            r[0].move_to([-2.4, 0, 0], aligned_edge=LEFT)
        grp.arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([-0.2, 1.1, 0])
        for r in grp:
            r[1].move_to([2.6, r[0].get_y(), 0])
            r[2].move_to([4.3, r[0].get_y(), 0])
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in grp], lag_ratio=0.35), run_time=1.8)
        self.wait_until(self.cue_start("一定要用尾部", self.now))
        bad = VGroup(Text("stack.pop(0)", font=MONO, font_size=30, color=C_RED),
                     Text("stack.insert(0, x)", font=MONO, font_size=30, color=C_RED))
        bad.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([-1.7, -1.4, 0])
        on = MathTex(r"O(n)", color=C_RED).scale(1.0).move_to([4.3, -1.4, 0])
        cross = Cross(bad, stroke_color=C_RED, stroke_width=5).scale(0.9)
        self.play(FadeIn(bad, shift=UP * 0.2), FadeIn(on), run_time=0.8)
        self.wait_until(self.cue_start("那就不是栈", self.now))
        self.play(Create(cross), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(grp, bad, on, cross)), run_time=0.6)

    # ---------------------------------------------------------------- 括号匹配
    def paren_beat(self):
        self.beat("paren")
        s = "([]{})"
        ok, ev = S.is_valid_trace(s)
        chars = token_row(list(s), y=2.0, x0=-5.0, dx=0.9, color_of=lambda c: BR_COL[c], scale=1.3)
        st = StackBox(cx=4.0, base=-2.6, height=3.6, width=1.5)
        self.play(FadeIn(chars), Create(st.frame), FadeIn(st.top_label), run_time=0.9)
        ptr = Triangle(color=WHITE).scale(0.12).rotate(PI).set_fill(WHITE, 1)
        ptr.next_to(chars[0], UP, buff=0.15)
        self.play(FadeIn(ptr), run_time=0.3)
        open_at = []
        arcs = VGroup()
        self.wait_until(self.cue_start("遇到左括号", self.now))
        step = max(0.6, min(1.3, (self.left() - 2.2) / len(ev)))
        for e in ev:
            if e[0] == "push":
                i, ch = e[1], e[2]
                item = st.make(ch, BR_COL[ch], size=30)
                open_at.append(i)
                self.play(ptr.animate.next_to(chars[i], UP, buff=0.15),
                          st.push(item, src=chars[i].get_center(), rt=step), run_time=step)
            elif e[0] == "pop":
                i, top, good = e[1], e[2], e[3]
                j = open_at.pop()
                item = st.pop()
                arc = ArcBetweenPoints(chars[j].get_bottom() + DOWN * 0.12, chars[i].get_bottom() + DOWN * 0.12,
                                       angle=PI * 0.7, color=BR_COL[top], stroke_width=4)
                self.play(ptr.animate.next_to(chars[i], UP, buff=0.15),
                          item.animate.move_to(chars[i].get_center() + DOWN * 1.1).set_opacity(0),
                          Create(arc), run_time=step)
                self.remove(item)
                arcs.add(arc)
            else:
                res = T("栈空 → True", 28, C_GREEN).move_to([-2.75, -1.6, 0])
                self.play(FadeIn(res, shift=UP * 0.2), Indicate(st.frame, color=C_GREEN), run_time=0.8)
                arcs.add(res)
        self.wait_until(self.cue_start("一层套一层", self.now))
        self.play(LaggedStart(*[Indicate(a, color=WHITE, scale_factor=1.05) for a in arcs[:-1]], lag_ratio=0.3),
                  run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(chars, st, ptr, arcs)), run_time=0.6)

    # ---------------------------------------------------------------- 三个易错点
    def fail_beat(self):
        self.beat("fail")
        cases = [("(]", "第一", "弹出的不配对"), (")", "第二", "右括号时栈已空"), ("((", "第三", "结束时栈有剩余")]
        xs = [-4.4, 0.0, 4.4]
        shown = VGroup()
        for (s, key, why), x in zip(cases, xs):
            self.wait_until(self.cue_start(key, self.now))
            ok, ev = S.is_valid_trace(s)
            chars = token_row(list(s), y=2.3, x0=x - 0.45 * (len(s) - 1), dx=0.9,
                              color_of=lambda c: BR_COL[c], scale=1.2)
            st = StackBox(cx=x, base=-1.35, height=2.4, width=1.3, item_h=0.46, label="")
            self.play(FadeIn(chars), Create(st.frame), run_time=0.5)
            for e in ev:
                if e[0] == "push":
                    self.play(st.push(st.make(e[2], BR_COL[e[2]], size=26), src=chars[e[1]].get_center(),
                                      rt=0.45), run_time=0.45)
                elif e[0] == "pop":
                    top = st.pop()
                    self.play(top.animate.move_to(chars[e[1]].get_center() + DOWN * 0.9), run_time=0.45)
                    bad = Cross(VGroup(top, chars[e[1]]), stroke_color=C_RED, stroke_width=5).scale(0.6)
                    self.play(Create(bad), run_time=0.4)
                    shown.add(top, bad)
                elif e[0] == "empty":
                    self.play(Indicate(st.frame, color=C_RED), chars[e[1]].animate.set_color(C_RED), run_time=0.6)
                else:
                    self.play(*[Indicate(it, color=C_RED) for it in st.items], run_time=0.6)
            res = VGroup(T(why, 24, C_RED), Text("False", font=MONO, font_size=24, color=C_RED))
            res.arrange(DOWN, buff=0.12).move_to([x, -2.15, 0])
            self.play(FadeIn(res, shift=UP * 0.2), run_time=0.4)
            shown.add(chars, st, *st.items, res)
        self.wait_until(self.cue_start("最常被漏", self.now))
        ring = SurroundingRectangle(VGroup(*[m for m in shown if m.get_x() > 2.5]), color=C_YELLOW, buff=0.12,
                                    corner_radius=0.15)
        code = Text("return not stack", font=MONO, font_size=26, color=C_YELLOW).move_to([4.4, 3.25, 0])
        self.play(Create(ring), FadeIn(code), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(shown, ring, code)), run_time=0.6)

    # ---------------------------------------------------------------- 三种写法
    def postfix_beat(self):
        self.beat("postfix")
        infix = VGroup(T("中缀", 26, C_GREY), MathTex(r"(1+2)\times 3").scale(1.2)).arrange(RIGHT, buff=0.6)
        prefix = VGroup(T("前缀", 26, C_GREY), Text("* + 1 2 3", font=MONO, font_size=36)).arrange(RIGHT, buff=0.6)
        post = VGroup(T("后缀", 26, C_YELLOW), Text("1 2 + 3 *", font=MONO, font_size=36, color=C_YELLOW))
        post.arrange(RIGHT, buff=0.6)
        rows = VGroup(infix, prefix, post).arrange(DOWN, buff=0.6, aligned_edge=LEFT).move_to([-0.8, 0.6, 0])
        self.play(FadeIn(infix, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("写成后缀", self.now))
        self.play(FadeIn(prefix, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(post, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("不需要括号", self.now))
        note = VGroup(T("没有括号", 26, C_GREEN), T("不比优先级", 26, C_GREEN)).arrange(DOWN, buff=0.15)
        note.next_to(post, RIGHT, buff=0.9)
        self.play(FadeIn(note, shift=LEFT * 0.2), Indicate(post[1], color=C_YELLOW), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(infix, prefix, note, post[0])), post[1].animate.move_to([-2.5, 2.2, 0]),
                  run_time=0.6)
        self.post_title = post[1]

    # ---------------------------------------------------------------- 后缀求值
    def evaluate_beat(self):
        self.beat("evaluate")
        tokens = "1 2 + 3 *".split()
        res, ev = S.eval_postfix_trace(tokens)
        row = token_row(tokens, y=2.2, x0=-5.0, dx=1.0, scale=1.2,
                        color_of=lambda t: C_YELLOW if t in "+-*/" else WHITE)
        self.play(FadeOut(self.post_title), FadeIn(row), run_time=0.6)
        st = StackBox(cx=4.0, base=-2.6, height=3.6, width=1.5)
        self.play(Create(st.frame), FadeIn(st.top_label), run_time=0.6)
        ptr = Triangle(color=WHITE).scale(0.12).rotate(PI).set_fill(WHITE, 1).next_to(row[0], UP, buff=0.15)
        self.play(FadeIn(ptr), run_time=0.3)
        self.wait_until(self.cue_start("从左往右", self.now))
        fmt = lambda x: str(int(x)) if float(x).is_integer() else f"{x:g}"  # noqa: E731
        calc_y = -0.6
        for e in ev:
            k = e[1]
            if e[0] == "num":
                item = st.make(fmt(e[2]), C_BLUE, tex=True)
                self.play(ptr.animate.next_to(row[k], UP, buff=0.15), st.push(item, src=row[k].get_center(), rt=0.7),
                          run_time=0.7)
            else:
                _, k, tk, a, b, r = e
                ib = st.pop()
                ia = st.pop()
                self.play(ptr.animate.next_to(row[k], UP, buff=0.15), Indicate(row[k], color=C_YELLOW), run_time=0.5)
                lb = T("b（右）", 20, C_RED).next_to(ib, LEFT, buff=0.2)
                la = T("a（左）", 20, C_TEAL).next_to(ia, LEFT, buff=0.2)
                self.play(FadeIn(lb), run_time=0.35)
                self.play(FadeIn(la), run_time=0.35)
                sym = {"+": "+", "-": "-", "*": r"\times", "/": r"\div"}[tk]
                eq = MathTex(fmt(a), sym, fmt(b), "=", fmt(r)).scale(1.1).move_to([-1.2, calc_y, 0])
                eq[0].set_color(C_TEAL)
                eq[2].set_color(C_RED)
                self.play(ReplacementTransform(ia[1].copy(), eq[0]), ReplacementTransform(ib[1].copy(), eq[2]),
                          FadeIn(eq[1]), FadeIn(eq[3]), FadeOut(lb), FadeOut(la),
                          FadeOut(ia), FadeOut(ib), run_time=0.8)
                self.play(Write(eq[4]), run_time=0.4)
                item = st.make(fmt(r), C_GREEN, tex=True)
                self.play(st.push(item, src=eq[4].get_center(), rt=0.7), FadeOut(eq[:4]), run_time=0.7)
                self.remove(eq[4])
        self.wait_until(self.cue_start("最后栈顶", self.now))
        self.play(Indicate(st.items[-1], color=C_YELLOW, scale_factor=1.3), run_time=0.8)
        self.wait_until(self.cue_start("减法弄反", self.now))
        r2, _ = S.eval_postfix_trace("10 3 - 2 -".split())
        ex = VGroup(Text("10 3 - 2 -", font=MONO, font_size=32), MathTex(r"=(10-3)-2=" + fmt(r2), color=C_YELLOW).scale(1.0))
        ex.arrange(RIGHT, buff=0.5).move_to([-1.6, -2.3, 0])
        self.play(FadeIn(ex, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(row, st, *st.items, ptr, ex)), run_time=0.6)

    # ---------------------------------------------------------------- 单调栈：接雨水
    def bars(self):
        h = S.RAIN
        u, dx, x0, base = 0.72, 0.6, -6.3, -2.3
        bars, idx = VGroup(), VGroup()
        for i, v in enumerate(h):
            b = Rectangle(width=dx * 0.86, height=max(0.02, v * u), stroke_color=C_GREY, stroke_width=2)
            b.set_fill(C_GREY, 0.55 if v else 0.0)
            b.move_to([x0 + dx * i, base, 0], aligned_edge=DOWN)
            bars.add(b)
            idx.add(MathTex(str(i), color=C_GREY).scale(0.45).move_to([x0 + dx * i, base - 0.25, 0]))
        floor = Line([x0 - dx / 2, base, 0], [x0 + dx * (len(h) - 0.5), base, 0], stroke_color=C_GREY, stroke_width=3)
        return dict(h=h, u=u, dx=dx, x0=x0, base=base, bars=bars, idx=idx, floor=floor)

    def water_rect(self, B, left, i, bottom, depth):
        x_l = B["x0"] + B["dx"] * (left + 0.5)
        x_r = B["x0"] + B["dx"] * (i - 0.5)
        y0 = B["base"] + B["h"][bottom] * B["u"]
        r = Rectangle(width=x_r - x_l, height=depth * B["u"], stroke_width=0).set_fill(C_BLUE, 0.55)
        return r.move_to([(x_l + x_r) / 2, y0, 0], aligned_edge=DOWN)

    def run_trap(self, B, st, events, step, explain=False):
        mob_of = {}
        for e in events:
            if e[0] == "push":
                i = e[1]
                item = st.make(str(i), C_BLUE, tex=True)
                mob_of[i] = item
                self.play(B["ptr"].animate.next_to(B["bars"][i], UP, buff=0.12),
                          st.push(item, src=B["idx"][i].get_center(), rt=step), run_time=step)
            elif e[0] in ("pop", "noleft"):
                bottom, i = e[1], e[2]
                item = st.pop()
                self.play(B["ptr"].animate.next_to(B["bars"][i], UP, buff=0.12),
                          item.animate.move_to(B["idx"][bottom].get_center() + DOWN * 0.5).set_opacity(0),
                          B["bars"][bottom].animate.set_stroke(C_RED if e[0] == "pop" else C_GREY, 3),
                          run_time=step)
                self.remove(item)
            else:
                _, left, i, bottom, width, depth, total = e
                labs = VGroup()
                if explain:
                    labs = VGroup(T("坑底", 20, C_RED).next_to(B["idx"][bottom], DOWN, buff=0.12),
                                  T("左挡板", 20, C_TEAL).next_to(B["bars"][left], UP, buff=0.75),
                                  T("右挡板", 20, C_YELLOW).next_to(B["bars"][i], UP, buff=0.45))
                    self.play(FadeIn(labs), B["bars"][left].animate.set_stroke(C_TEAL, 3), run_time=0.8)
                anims = [B["cnt"][1].animate.set_value(total)]
                if depth > 0:
                    w = self.water_rect(B, left, i, bottom, depth)
                    B["water"].add(w)
                    anims.append(GrowFromEdge(w, DOWN))
                    expr = MathTex(rf"{width}\times{depth}={width * depth}", color=C_BLUE).scale(0.8)
                    expr.move_to([-0.6, 2.05, 0])                     # 固定位置，不和挡板标签挤在一起
                    anims.append(FadeIn(expr))
                    self.play(*anims, run_time=step * 1.6)
                    self.play(FadeOut(expr), run_time=0.25)
                else:
                    self.play(*anims, run_time=step * 0.6)
                if explain:
                    self.play(FadeOut(labs), B["bars"][left].animate.set_stroke(C_GREY, 2), run_time=0.4)
                for b in B["bars"]:
                    b.set_stroke(C_GREY, 2)

    def mono_beat(self):
        self.beat("mono")
        B = self.bars()
        st = StackBox(cx=4.6, base=-2.6, height=4.6, width=1.3, item_h=0.42, label="栈（下标）")
        B["ptr"] = Triangle(color=WHITE).scale(0.1).rotate(PI).set_fill(WHITE, 1).next_to(B["bars"][0], UP, buff=0.12)
        B["cnt"] = VGroup(T("water", 24, C_GREY), Integer(0, color=C_BLUE).scale(1.0)).arrange(RIGHT, buff=0.25)
        B["cnt"].move_to([4.6, 2.75, 0])
        B["water"] = VGroup()
        self.play(Create(B["floor"]), LaggedStart(*[GrowFromEdge(b, DOWN) for b in B["bars"]], lag_ratio=0.08),
                  FadeIn(B["idx"]), Create(st.frame), FadeIn(st.top_label), FadeIn(B["cnt"]), run_time=1.6)
        self.play(FadeIn(B["ptr"]), run_time=0.3)
        _, ev = S.trap_trace()
        first_water = next(k for k, e in enumerate(ev) if e[0] == "water")
        self.wait_until(self.cue_start("栈里存下标", self.now))
        step = max(0.4, min(0.8, (self.cue_start("弹出的是坑底", self.now + 4) - self.now) / max(1, first_water)))
        self.run_trap(B, st, ev[:first_water], step)
        self.wait_until(self.cue_start("弹出的是坑底", self.now))
        self.run_trap(B, st, ev[first_water:first_water + 1], 0.8, explain=True)
        self.wait(max(0.1, self.left() - 0.2))
        self.B, self.st, self.ev_rest = B, st, ev[first_water + 1:]

    def rain_beat(self):
        self.beat("rain")
        B, st, ev = self.B, self.st, self.ev_rest
        formula = MathTex(r"\text{width}\times\text{depth}", color=C_BLUE).scale(0.9).move_to([-0.6, 2.75, 0])
        self.play(FadeIn(formula), run_time=0.6)
        t_end = self.cue_start("一块一块累加", self.now + 6)
        step = max(0.32, min(0.6, (t_end + 3.0 - self.now) / max(1, len(ev))))
        self.run_trap(B, st, ev, step)
        self.wait_until(self.cue_start("一块一块累加", self.now))
        self.play(Indicate(B["cnt"], color=C_YELLOW, scale_factor=1.3), Indicate(B["water"], color=WHITE), run_time=1.0)
        self.wait_until(self.cue_start("每个下标", self.now))
        lin = VGroup(T("每个下标：入栈 1 次，出栈至多 1 次", 24), MathTex(r"\le 2n \;\Rightarrow\; O(n)", color=C_GREEN))
        lin.arrange(RIGHT, buff=0.4).move_to([-0.6, 1.35, 0])
        self.play(FadeIn(lin, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(B["bars"], B["idx"], B["floor"], B["ptr"], B["cnt"], B["water"], st, *st.items,
                                 formula, lin)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾：栈与队列
    def recap_beat(self):
        self.beat("recap")
        st = StackBox(cx=-3.2, base=-1.9, height=2.9, width=1.5, item_h=0.46, label="栈：后进先出")
        cols = [C_TEAL, C_YELLOW, C_RED]
        for k in range(3):
            st.items.append(st.make(str(k + 1), cols[k], tex=True).move_to(st.slot(k)))
        q_y = -0.4
        qframe = VGroup(Line([1.4, q_y + 0.35, 0], [6.0, q_y + 0.35, 0], stroke_color=C_GREY, stroke_width=4),
                        Line([1.4, q_y - 0.35, 0], [6.0, q_y - 0.35, 0], stroke_color=C_GREY, stroke_width=4))
        qlab = T("队列：先进先出", 22, C_GREY).next_to(qframe, DOWN, buff=0.2)
        qitems = VGroup(*[st.make(str(k + 1), cols[k], tex=True).scale(0.85).move_to([2.4 + 1.2 * k, q_y, 0])
                          for k in range(3)])
        self.play(Create(st.frame), FadeIn(st.top_label), *[FadeIn(i) for i in st.items], run_time=0.8)
        uses = VGroup(T("括号匹配", 26, C_BLUE), T("表达式求值", 26, C_YELLOW), T("单调栈", 26, C_GREEN))
        uses.arrange(RIGHT, buff=0.6).move_to([-3.2, 2.3, 0]).shift(RIGHT * 1.6)
        self.wait_until(self.cue_start("括号匹配", self.now))
        self.play(LaggedStart(*[FadeIn(u, shift=UP * 0.2) for u in uses], lag_ratio=0.3), run_time=1.2)
        self.wait_until(self.cue_start("队列正好相反", self.now))
        self.play(Create(qframe), FadeIn(qlab), FadeIn(qitems), run_time=0.8)
        top = st.items[-1]
        self.play(top.animate.shift(UP * 1.2), qitems[0].animate.shift(LEFT * 1.4), run_time=0.9)
        self.play(top.animate.shift(DOWN * 1.2), qitems[0].animate.shift(RIGHT * 1.4), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 7 周 栈 P4–P18 · LeetCode 20、42 · OpenJudge 24588", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
