"""括号区间审计：前缀和与单调栈（11 月月考 T6 精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。括号串用题面样例 2（())(()，四问）：前缀和折线、单调栈每一步的弹出与栈内容、
nxt、四问的判定、两种错误写法的输出全部来自 novbrkdata（讲义 Python 参考代码原样复用 novdata.solve_t6；
test_novbrk.py 用按定义的栈匹配暴力、逐位找更低点独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novbrkdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_ORANGE = "#FF9F43"
DIM = "#3a4050"
X0R = 0.9                                   # 右侧面板左边界


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def fit(m, w):
    if m.width > w:
        m.scale_to_fit_width(w)
    return m


class NovBrkLesson(Lesson):
    S = D.S
    PRE = D.prefix(D.S)

    def construct(self):
        n = len(self.S)
        self.n = n
        self.nxt, self.events = D.next_lower(self.PRE)
        assert self.PRE == [0, 1, 0, -1, 0, 1, 0] and self.nxt == [3, 2, 3, 7, 7, 6, 7]
        assert D.lecture_answers(self.S, D.QUERIES) == D.EXPECT == ["YES", "NO", "NO", "NO"]
        for b in ("title", "task", "mountain", "nxt", "stack", "judge", "pitfall", "code", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    # ---------------------------------------------------------------- 工具
    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novbrk] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6, keep=()):
        rest = [m for m in self.mobjects if m not in self.subs and m not in keep]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)
            self.remove(*rest)

    def tail(self, pad=0.6):
        self.wait(max(0.1, self.left() - pad))

    # 山的坐标：位置 i（0..n）在 px(i)，高度 v 在 py(v)
    @staticmethod
    def px(i):
        return -5.7 + i * 0.95

    @staticmethod
    def py(v):
        return 0.6 + 0.8 * v

    ROW_I, ROW_PRE, ROW_NXT, ROW_BAD = -0.75, -1.2, -1.65, -2.2

    def build_mountain(self):
        """括号串、折线、i / pre 两行表。返回各部件（不播放）。"""
        s, n, pre, px, py = self.S, self.n, self.PRE, self.px, self.py
        chars = VGroup(*[M(ch, 34, C_BLUE if ch == "(" else C_ORANGE).move_to([px(k + 0.5), 2.45, 0])
                         for k, ch in enumerate(s)])
        cidx = VGroup(*[M(str(k + 1), 17, C_GREY).next_to(chars[k], UP, buff=0.1) for k in range(n)])
        base = DashedLine([px(0) - 0.25, py(0), 0], [px(n) + 0.25, py(0), 0], color=DIM, stroke_width=2)
        dots = VGroup(*[Dot([px(i), py(v), 0], radius=0.08, color=WHITE) for i, v in enumerate(pre)])
        segs = VGroup(*[Line(dots[i].get_center(), dots[i + 1].get_center(), color=C_BLUE if s[i] == "(" else C_ORANGE,
                             stroke_width=5) for i in range(n)])
        lab_x = -6.3
        rl = VGroup(M("i", 20, C_GREY), M("pre", 20, C_GREY), M("nxt", 20, C_PURPLE))
        for m_, y in zip(rl, (self.ROW_I, self.ROW_PRE, self.ROW_NXT)):
            m_.move_to([lab_x - m_.width / 2, y, 0])
        irow = VGroup(*[M(str(i), 20, C_GREY).move_to([px(i), self.ROW_I, 0]) for i in range(n + 1)])
        prow = VGroup(*[M(str(v), 22, WHITE).move_to([px(i), self.ROW_PRE, 0]) for i, v in enumerate(pre)])
        rule = Line([lab_x - 0.6, self.ROW_I - 0.22, 0], [px(n) + 0.3, self.ROW_I - 0.22, 0], color=DIM, stroke_width=1.5)
        return dict(chars=chars, cidx=cidx, base=base, dots=dots, segs=segs, rl=rl, irow=irow, prow=prow, rule=rule)

    def span(self, l, r, color=C_BLUE):
        """子串 [l, r] 在山上对应 l-1 → r 一段：底色块 + 起点高度虚线 + 两端圈。"""
        px, py, pre = self.px, self.py, self.PRE
        lo, hi = min(pre[l - 1:r + 1]), max(pre[l - 1:r + 1])
        rect = Rectangle(width=px(r) - px(l - 1) + 0.5, height=py(hi) - py(lo) + 0.6, stroke_width=0)
        rect.set_fill(color, 0.13).move_to([(px(l - 1) + px(r)) / 2, (py(hi) + py(lo)) / 2, 0])
        lvl = DashedLine([px(l - 1), py(pre[l - 1]), 0], [px(r) + 0.25, py(pre[l - 1]), 0], color=C_YELLOW,
                         stroke_width=3, dash_length=0.1)
        eq = pre[r] == pre[l - 1]
        ends = VGroup(Circle(0.17, color=C_YELLOW, stroke_width=3).move_to(self.mt["dots"][l - 1]),
                      Circle(0.17, color=C_YELLOW if eq else C_RED, stroke_width=3).move_to(self.mt["dots"][r]))
        return VGroup(rect, lvl, ends)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("11 月月考讲评 · T6（OpenJudge 31534）", 24, C_BLUE).move_to([0, 2.7, 0])
        title = T("括号区间审计", 60).next_to(kick, DOWN, buff=0.3)
        sub = T("前缀和与单调栈", 32, C_YELLOW).next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.at("二十万次")
        spec = VGroup(T("括号串长", 24, C_GREY), MathTex(r"n \le 2\times10^5", color=WHITE).scale(0.75),
                      T("询问", 24, C_GREY), MathTex(r"q \le 2\times10^5", color=WHITE).scale(0.75),
                      T("：子串 s[l..r] 合法吗？", 24)).arrange(RIGHT, buff=0.2)
        spec.next_to(sub, DOWN, buff=0.55)
        self.play(FadeIn(spec, shift=UP * 0.15), run_time=0.6)
        self.at("前缀和")
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.5)
        chips = VGroup()
        for a, b in (("前缀和", "画成一座山"), ("单调栈", "扫一遍"), ("每问", "O(1)")):
            box = RoundedRectangle(corner_radius=0.12, width=3.0, height=0.9, stroke_color=C_GREY, stroke_width=2)
            chips.add(VGroup(box, VGroup(T(a, 24, C_YELLOW), T(b, 22)).arrange(RIGHT, buff=0.18).move_to(box)))
        chips.arrange(RIGHT, buff=0.5).move_to([0, -1.6, 0])
        self.play(FadeIn(chips[0], shift=UP * 0.15), run_time=0.5)
        self.at("单调栈")
        self.play(FadeIn(chips[1], shift=UP * 0.15), run_time=0.5)
        self.at("常数")
        self.play(FadeIn(chips[2], shift=UP * 0.15), run_time=0.5)
        self.tail()
        self.clear_all()

    # ---------------------------------------------------------------- 题意与暴力
    def scan_row(self, s, y, x):
        """一行括号 + 每个字符读完后的差值；差值为负标红。"""
        diffs = D.running(s)
        dx = 0.62
        cs = VGroup(*[M(ch, 30, C_BLUE if ch == "(" else C_ORANGE).move_to([x + k * dx, y, 0]) for k, ch in enumerate(s)])
        ds = VGroup(*[M(str(d), 20, C_RED if d < 0 else C_GREY).move_to([x + k * dx, y - 0.45, 0]) for k, d in enumerate(diffs)])
        return cs, ds, diffs

    def task_beat(self):
        self.beat("task")
        head = VGroup(T("T6", 26, C_BLUE), T("括号区间审计", 32), T("什么叫合法？", 22, C_GREY)).arrange(RIGHT, buff=0.3)
        left_at(head, -6.6, 2.95)
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)
        rules = [("空串", "合法", "空串"), ("A 合法", "⇒  ( A )  合法", "套一对"), ("A、B 合法", "⇒  A B  合法", "接起来")]
        rows = VGroup()
        for k, (a, b, _) in enumerate(rules):
            r = VGroup(T(f"{k + 1}.", 24, C_GREY), T(a, 26), T(b, 26, C_GREEN)).arrange(RIGHT, buff=0.25)
            rows.add(left_at(r, -6.4, 1.95 - 0.62 * k))
        for r, (*_, key) in zip(rows, rules):
            self.at(key)
            self.play(FadeIn(r, shift=RIGHT * 0.15), run_time=0.5)
        self.at("能检查")
        chk = VGroup(T("能检查的说法：从左往右数", 24, C_YELLOW),
                     T("差 = 左括号数 − 右括号数", 24),
                     T("任何时候 ≥ 0，最后 = 0", 24, C_GREEN)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        left_at(chk, X0R, 1.6)
        self.play(FadeIn(chk, shift=LEFT * 0.15), run_time=0.7)
        c1, d1, v1 = self.scan_row(D.SCAN_OK, -0.35, X0R + 0.2)
        c2, d2, v2 = self.scan_row(D.SCAN_BAD, -1.45, X0R + 0.2)
        assert min(v1) >= 0 and v1[-1] == 0 and min(v2) < 0
        ok1 = T("✓", 30, C_GREEN).next_to(c1, RIGHT, buff=0.45)
        bad = v2.index(min(v2))
        no2 = T(f"✗ 第 {bad + 1} 个字符后差是 {v2[bad]}", 22, C_RED).next_to(c2, RIGHT, buff=0.45)
        self.play(FadeIn(c1), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(d) for d in d1], lag_ratio=0.25), FadeIn(ok1), run_time=1.0)
        self.play(FadeIn(c2), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(d) for d in d2], lag_ratio=0.25), FadeIn(no2), run_time=1.0)
        self.at("现扫")
        assert D.NAIVE == D.N_MAX * D.N_MAX == 4 * 10 ** 10
        naive = VGroup(T("每问现扫", 24, C_GREY), MathTex(r"2\times10^5", color=WHITE).scale(0.8), T("步", 24, C_GREY),
                       MathTex(r"\times\ 2\times10^5", color=WHITE).scale(0.8), T("问", 24, C_GREY))
        naive.arrange(RIGHT, buff=0.18)
        left_at(naive, -6.4, -0.6)
        self.play(FadeIn(naive), run_time=0.6)
        self.at("四百亿")
        tot = VGroup(MathTex(r"=\ 4\times10^{10}", color=C_RED).scale(0.9), T("必然超时", 26, C_RED)).arrange(RIGHT, buff=0.25)
        left_at(tot, -6.4, -1.4)
        self.play(FadeIn(tot, shift=UP * 0.15), run_time=0.6)
        self.tail()
        self.clear_all()

    # ---------------------------------------------------------------- 前缀和画成山
    def mountain_beat(self):
        self.beat("mountain")
        self.mt = mt = self.build_mountain()
        tag = left_at(T("T6 · 样例 2", 22, C_GREY), -6.8, 3.55)
        self.tag = tag
        self.play(FadeIn(tag), FadeIn(mt["chars"]), FadeIn(mt["cidx"]), run_time=0.6)
        up = VGroup(M("(", 26, C_BLUE), T("上坡 +1", 22, C_BLUE), M(")", 26, C_ORANGE), T("下坡 −1", 22, C_ORANGE))
        up.arrange(RIGHT, buff=0.22)
        left_at(up, X0R, 2.45)
        self.play(FadeIn(up), run_time=0.5)
        self.at("折线")
        self.play(Create(mt["base"]), FadeIn(mt["dots"][0]), run_time=0.4)
        for i in range(self.n):
            self.play(Create(mt["segs"][i]), FadeIn(mt["dots"][i + 1]), Indicate(mt["chars"][i], scale_factor=1.3),
                      run_time=0.32)
        self.at("高度依次")
        self.play(FadeIn(mt["rl"][:2]), FadeIn(mt["irow"]), Create(mt["rule"]), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(p, shift=DOWN * 0.1) for p in mt["prow"]], lag_ratio=0.3), run_time=2.2)
        self.at("子串")
        sub = VGroup(T("子串 s[l..r]", 24), T("↔", 24, C_GREY), T("山上从 l−1 走到 r", 24, C_YELLOW)).arrange(RIGHT, buff=0.2)
        left_at(sub, X0R, 1.75)
        self.play(FadeIn(sub, shift=LEFT * 0.15), run_time=0.5)
        self.at("第一")
        c1 = VGroup(T("① 两端同高", 24, C_YELLOW), M("pre[r] == pre[l-1]", 20, C_GREY)).arrange(RIGHT, buff=0.3)
        c2a = T("② 中间不跌破起点", 24, C_YELLOW)
        c2b = M("min pre[l..r] >= pre[l-1]", 20, C_GREY)
        left_at(c1, X0R, 1.1)
        left_at(c2a, X0R, 0.55)
        left_at(c2b, X0R + 0.4, 0.1)
        self.cond = VGroup(c1, c2a, c2b)
        self.play(FadeIn(c1), run_time=0.5)
        self.at("第二")
        self.play(FadeIn(c2a), FadeIn(c2b), run_time=0.5)
        msgs = VGroup()
        for k, ((l, r), key) in enumerate(zip(D.COUNTER, ("四到五", "二到五"))):
            j = D.judge(self.S, l, r)
            self.at(key)
            sp = self.span(l, r, C_RED)
            sub_s = self.S[l - 1:r]
            if not j["c1"]:
                assert j["c2"]
                msg = f"[{l},{r}] {sub_s}：不跌破 ✓②，两端 {j['a']} ≠ {j['b']} ✗①"
                extra = VGroup()
            else:
                assert not j["c2"]
                p = j["nxt"]
                msg = f"[{l},{r}] {sub_s}：两端都是 {j['a']} ✓①，位置 {p} 跌到 {self.PRE[p]} ✗②"
                extra = Circle(0.2, color=C_RED, stroke_width=4).move_to(mt["dots"][p])
            line = fit(left_at(T(msg, 20, C_RED), X0R, -0.65 - 0.5 * k), 7.0 - X0R - 0.15)
            msgs.add(line)
            anims = [FadeIn(sp), FadeIn(line, shift=LEFT * 0.15)]
            if k:
                anims += [FadeOut(self.cur_span)]
            self.play(*anims, run_time=0.6)
            if len(extra):
                self.play(Create(extra), run_time=0.4)
                self.remove(extra)                  # 并进 sp，随它一起淡出（否则顶层留一份）
                sp.add(extra)
            self.cur_span = sp
        self.tail()
        self.play(FadeOut(self.cur_span), FadeOut(msgs), FadeOut(up), FadeOut(sub), run_time=0.5)

    # ---------------------------------------------------------------- 条件 2 → nxt
    def nxt_beat(self):
        self.beat("nxt")
        mt, px, py, pre = self.mt, self.px, self.py, self.PRE
        q1 = left_at(T("这一段的最低点，比起点低吗？", 24), X0R, 2.45)
        self.play(FadeIn(q1, shift=LEFT * 0.15), run_time=0.5)
        self.at("换个问法")
        i0 = 1
        lvl = DashedLine([px(i0), py(pre[i0]), 0], [px(self.n) + 0.25, py(pre[i0]), 0], color=C_YELLOW,
                         stroke_width=3, dash_length=0.1)
        j0 = self.nxt[i0]
        arc = CurvedArrow(mt["dots"][i0].get_center() + DOWN * 0.15, mt["dots"][j0].get_center() + DOWN * 0.15,
                          angle=TAU / 7, color=C_PURPLE, stroke_width=3, tip_length=0.18)
        hit = Circle(0.2, color=C_PURPLE, stroke_width=4).move_to(mt["dots"][j0])
        df = VGroup(M("nxt[i]", 22, C_PURPLE), T("= i 右边第一个比 pre[i] 低的位置", 22)).arrange(RIGHT, buff=0.15)
        fit(left_at(df, X0R, -0.65), 7.0 - X0R - 0.15)
        self.play(Create(lvl), FadeIn(df), run_time=0.6)
        self.play(Create(arc), Create(hit), run_time=0.7)
        ex = left_at(T(f"例：nxt[{i0}] = {j0}；右边没有更低处，记 n+1 = {self.n + 1}", 20, C_GREY), X0R, -1.15)
        self.play(FadeIn(ex), run_time=0.4)
        self.at("后面")
        new2 = M("nxt[l-1] > r", 20, C_GREEN).move_to(self.cond[2], aligned_edge=LEFT)
        why = left_at(T("第一次跌破在 r 之后 ⟺ 区间里不跌破", 20, C_GREEN), X0R, -1.6)
        self.play(Transform(self.cond[2], new2), FadeIn(why), run_time=0.7)
        self.at("只剩一行")
        f = M("ok = pre[r] == pre[l-1] and nxt[l-1] > r", 20, WHITE)
        box = SurroundingRectangle(f, color=C_YELLOW, buff=0.15)
        self.formula = VGroup(box, f)
        left_at(self.formula, X0R, -2.35)
        self.play(Create(box), FadeIn(f), run_time=0.7)
        self.tail()
        self.play(*[FadeOut(m_) for m_ in (q1, lvl, arc, hit, df, ex, why, self.cond)],
                  self.formula.animate.scale(0.9).move_to([X0R + self.formula.width * 0.45, 3.0, 0]), run_time=0.6)

    # ---------------------------------------------------------------- 单调栈
    def stack_item(self, j):
        box = RoundedRectangle(corner_radius=0.08, width=1.5, height=0.46, stroke_color=C_TEAL, stroke_width=3)
        box.set_fill(C_TEAL, 0.18)
        lab = VGroup(T(f"位 {j}", 20), T(f"高 {self.PRE[j]}", 16, C_GREY)).arrange(RIGHT, buff=0.15).move_to(box)
        return VGroup(box, lab)

    def stack_beat(self):
        self.beat("stack")
        mt, px = self.mt, self.px
        cx, base, ih = 5.9, -2.75, 0.5
        frame = VMobject(stroke_color=C_GREY, stroke_width=4).set_points_as_corners(
            [[cx - 0.85, base + 2.0, 0], [cx - 0.85, base, 0], [cx + 0.85, base, 0], [cx + 0.85, base + 2.0, 0]])
        flab = T("栈", 22, C_GREY).next_to(frame, LEFT, buff=0.2).align_to(frame, DOWN)

        def slot(k):
            return [cx, base + 0.08 + ih * (k + 0.5) + 0.05 * k, 0]
        self.play(Create(frame), FadeIn(flab), FadeIn(mt["rl"][2]), run_time=0.6)
        rules = [("栈里：还没找到更低处的位置", WHITE, "栈里存"), ("高度从底到顶不降", C_GREY, "不降"),
                 ("新位置更低 → 弹出栈顶，填 nxt", C_PURPLE, "新位置"), ("弹到栈顶不比它高，再压入", C_TEAL, "一直弹到")]
        rl = VGroup()
        for k, (txt, col, key) in enumerate(rules):
            m_ = fit(left_at(T(txt, 21, col), X0R, 2.3 - 0.47 * k), 7.0 - X0R - 0.15)
            rl.add(m_)
            self.at(key)
            self.play(FadeIn(m_, shift=LEFT * 0.12), run_time=0.45)
        cur = Circle(0.17, color=C_YELLOW, stroke_width=4).move_to(mt["dots"][0])
        info = None
        items: list[VGroup] = []
        ids: list[int] = []
        ncell = {}
        keys = {0: "零、一", 2: "到二", 3: "到三", 6: "到六"}
        for j, popped, stk in self.events:
            if j in keys:
                self.at(keys[j])
            msg = f"j = {j}，高 {self.PRE[j]}：" + (f"弹出 {'、'.join(map(str, popped))}，nxt = {j}" if popped else "不比栈顶低，压入")
            new_info = left_at(T(msg, 21, C_PURPLE if popped else C_GREY), X0R, 0.2)
            fit(new_info, cx - 0.95 - X0R - 0.1)
            anims = [cur.animate.move_to(mt["dots"][j]) if j else Create(cur)]
            anims.append(Transform(info, new_info) if info else FadeIn(new_info))
            info = info or new_info
            self.play(*anims, run_time=0.35)
            if popped:
                pa = []
                for p in popped:
                    it = items.pop()
                    assert ids.pop() == p
                    t = M(str(j), 22, C_PURPLE).move_to([px(p), self.ROW_NXT, 0])
                    ncell[p] = t
                    arc = CurvedArrow(mt["dots"][p].get_center() + DOWN * 0.15, mt["dots"][j].get_center() + DOWN * 0.15,
                                      angle=TAU / 7, color=C_PURPLE, stroke_width=3, tip_length=0.16)
                    pa += [FadeOut(it, shift=RIGHT * 0.4), FadeIn(t, shift=DOWN * 0.15), ShowPassingFlash(arc, time_width=0.9)]
                self.play(*pa, run_time=0.7)
            it = self.stack_item(j).move_to(slot(len(items)))
            items.append(it)
            ids.append(j)
            assert ids == stk
            self.play(FadeIn(it, shift=DOWN * 0.3), run_time=0.35)
        self.at("填七")
        rest = [M(str(self.n + 1), 22, C_GREY).move_to([px(p), self.ROW_NXT, 0]) for p in range(self.n + 1) if p not in ncell]
        left_p = [p for p in range(self.n + 1) if p not in ncell]
        assert ids == left_p
        self.play(*[FadeIn(r) for r in rest], *[Indicate(x, color=C_GREY) for x in items], run_time=0.6)
        for p, r in zip(left_p, rest):
            ncell[p] = r
        self.nrow = VGroup(*[ncell[p] for p in range(self.n + 1)])
        assert [int(m_.text) for m_ in self.nrow] == self.nxt
        self.at("各一次")
        lin = left_at(VGroup(T("每个位置进栈、出栈各一次 →", 22), MathTex(r"O(n)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.2),
                      X0R, -0.45)
        fit(lin, cx - 0.95 - X0R - 0.1)
        left_at(lin, X0R, -0.45)
        self.play(FadeIn(lin), run_time=0.5)
        self.tail()
        self.play(*[FadeOut(m_) for m_ in (frame, flab, rl, cur, info, lin, *items)], run_time=0.5)

    # ---------------------------------------------------------------- 样例 2 四问
    def judge_beat(self):
        self.beat("judge")
        mt = self.mt
        keys = ["一到二", "二到五", "一到六", "三到六"]
        lines = VGroup()
        prev = None
        outs = []
        for k, ((l, r), key) in enumerate(zip(D.QUERIES, keys)):
            j = D.judge(self.S, l, r)
            assert j["c1"]                                  # 样例 2 四问两端都同高（pitfall 段要用）
            self.at(key)
            sp = self.span(l, r, C_GREEN if j["ok"] else C_RED)
            nb = SurroundingRectangle(self.nrow[l - 1], color=C_PURPLE, buff=0.08)
            sp.add(nb)
            if j["nxt"] <= self.n:
                sp.add(Circle(0.2, color=C_RED, stroke_width=4).move_to(mt["dots"][j["nxt"]]))
            ans = "YES" if j["ok"] else "NO"
            outs.append(ans)
            msg = f"[{l},{r}] 两端 {j['a']}、{j['b']}，nxt[{l - 1}] = {j['nxt']} {'>' if j['c2'] else '≤'} {r} → {ans}"
            line = fit(left_at(T(msg, 21, C_GREEN if j["ok"] else C_RED), X0R, 2.2 - 0.55 * k), 7.0 - X0R - 0.15)
            lines.add(line)
            anims = [FadeIn(sp), FadeIn(line, shift=LEFT * 0.15)]
            if prev is not None:
                anims.append(FadeOut(prev))
            self.play(*anims, run_time=0.6)
            prev = sp
        assert outs == D.EXPECT
        self.at("一个 YES")
        out = VGroup(T("输出", 22, C_GREY), M(" ".join(outs), 24, WHITE), T("= 样例输出 ✓", 22, C_GREEN)).arrange(RIGHT, buff=0.2)
        left_at(out, X0R, -0.15)
        self.play(FadeIn(out, shift=UP * 0.15), FadeOut(prev), run_time=0.6)
        self.tail()
        self.play(FadeOut(lines), FadeOut(out), run_time=0.5)

    # ---------------------------------------------------------------- 失分点
    def pitfall_beat(self):
        self.beat("pitfall")
        mt, px = self.mt, self.px
        right = D.EXPECT
        cnt = D.wrong_count_only(self.S, D.QUERIES)
        ge = D.wrong_ge(self.S, D.QUERIES)
        assert cnt == ["YES"] * 4 and ge == ["NO"] * 4
        cols = [X0R + 0.6, X0R + 2.0, X0R + 3.6, X0R + 5.2]
        hdr = VGroup(T("询问", 20, C_GREY), T("正确", 20, C_GREEN), T("只数个数", 20, C_RED), T("弹栈 >=", 20, C_RED))
        for m_, x in zip(hdr, cols):
            m_.move_to([x, 2.3, 0])
        qcol = VGroup(*[M(f"[{l},{r}]", 20, C_GREY).move_to([cols[0], 1.8 - 0.45 * k, 0]) for k, (l, r) in enumerate(D.QUERIES)])

        def col(vals, x):
            return VGroup(*[M(v, 20, C_GREEN if v == w else C_RED).move_to([x, 1.8 - 0.45 * k, 0])
                            for k, (v, w) in enumerate(zip(vals, right))])
        c0, c1, c2 = col(right, cols[1]), col(cnt, cols[2]), col(ge, cols[3])
        self.at("两端同高")
        self.play(FadeIn(hdr[:2]), FadeIn(qcol), FadeIn(c0), run_time=0.5)
        self.play(*[Indicate(mt["dots"][i], color=C_YELLOW) for l, r in D.QUERIES[1:] for i in (l - 1, r)], run_time=0.8)
        self.at("只数括号")
        self.play(FadeIn(hdr[2]), LaggedStart(*[FadeIn(x) for x in c1], lag_ratio=0.3), run_time=1.0)
        self.at("严格大于")
        wrong = D.next_lower_ge(self.PRE)
        lab = M("nxt(>=)", 18, C_RED)
        lab.move_to([-6.3 - lab.width / 2 + 0.25, self.ROW_BAD, 0])
        brow = VGroup(*[M(str(v), 22, C_RED if v != self.nxt[i] else C_GREY).move_to([px(i), self.ROW_BAD, 0])
                        for i, v in enumerate(wrong)])
        diff = [i for i in range(self.n + 1) if wrong[i] != self.nxt[i]]
        assert diff == [0, 4]
        self.at("大于等于")
        self.play(FadeIn(lab), FadeIn(brow), run_time=0.6)
        self.play(*[Create(SurroundingRectangle(brow[i], color=C_RED, buff=0.07)) for i in diff], run_time=0.5)
        self.at("被判错")
        self.play(FadeIn(hdr[3]), LaggedStart(*[FadeIn(x) for x in c2], lag_ratio=0.3), run_time=1.0)
        self.at("输入输出")
        tab = VGroup(hdr, qcol, c0, c1, c2)
        io = VGroup()
        for k, (bad, good) in enumerate((("input() 读 2×10⁵ 次", "sys.stdin.read().split()"),
                                         ("每问 print 一次", "print('\\n'.join(out))"))):
            a = T("✗ " + bad, 20, C_RED)
            b = VGroup(T("✓", 20, C_GREEN), M(good, 19, C_GREEN)).arrange(RIGHT, buff=0.15)
            left_at(a, X0R, 0.0 - 1.0 * k)
            left_at(b, X0R + 0.3, -0.42 - 1.0 * k)
            io.add(VGroup(a, b))
        self.play(tab.animate.set_opacity(0.35), FadeIn(io[0]), run_time=0.6)
        self.at("先收集")
        self.play(FadeIn(io[1]), run_time=0.6)
        self.tail()
        self.clear_all()

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        lines = D.CODE_LINES
        size = 17
        cw = M("x" * 40, size).width / 40
        lh = 0.32
        split = D.SEGMENTS["query"][0]               # 第二栏从读询问开始
        col_x = [-6.85, -0.15]
        mobs = {}
        for k, ln in enumerate(lines):
            if not ln.strip():
                continue
            c = 0 if k < split else 1
            row = k if c == 0 else k - split
            indent = len(ln) - len(ln.lstrip(" "))
            col = C_GREY if ln.lstrip().startswith("#") else WHITE
            m_ = M(ln.strip(), size, col)
            mobs[k] = left_at(m_, col_x[c] + indent * cw, 3.0 - lh * row)
        code = VGroup(*mobs.values())
        assert code.get_right()[0] < 7.0 and code.get_bottom()[1] > -2.9, (code.get_right(), code.get_bottom())
        self.play(FadeIn(code), run_time=0.8)

        def hl(seg, color):
            a, b = D.SEGMENTS[seg]
            g = VGroup(*[mobs[k] for k in range(a, b + 1) if k in mobs])
            return SurroundingRectangle(g, color=color, buff=0.08, stroke_width=3)
        self.at("第一段")
        h1 = hl("pre", C_BLUE)
        self.play(Create(h1), run_time=0.5)
        self.at("第二段")
        h2 = hl("stack", C_PURPLE)
        self.play(ReplacementTransform(h1, h2), run_time=0.5)
        self.at("while")
        cmp_ = SurroundingRectangle(mobs[14], color=C_YELLOW, buff=0.05)
        note = T("严格 > 才弹", 18, C_YELLOW).next_to(mobs[14], RIGHT, buff=0.25)
        self.play(Create(cmp_), FadeIn(note), run_time=0.5)
        self.at("第三段")
        h3 = hl("query", C_GREEN)
        self.play(ReplacementTransform(h2, h3), FadeOut(cmp_), FadeOut(note), run_time=0.5)
        self.at("攒进列表")
        hio = VGroup(SurroundingRectangle(mobs[2], color=C_ORANGE, buff=0.05),
                     SurroundingRectangle(mobs[24], color=C_ORANGE, buff=0.05))
        self.play(Create(hio), run_time=0.5)
        self.at("ST")
        st = VGroup(T("另一种：ST 表做区间最小值", 22, C_YELLOW),
                    VGroup(T("预处理", 20, C_GREY), MathTex(r"O(n\log n)", color=WHITE).scale(0.7),
                           T("，每问", 20, C_GREY), MathTex(r"O(1)", color=WHITE).scale(0.7),
                           T("，代码更长", 20, C_GREY)).arrange(RIGHT, buff=0.12)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        left_at(st, col_x[1], 3.0 - lh * (len(lines) - split) - 0.6)
        mine = VGroup(T("单调栈：预处理", 20, C_GREEN), MathTex(r"O(n)", color=C_GREEN).scale(0.7)).arrange(RIGHT, buff=0.12)
        left_at(mine, col_x[1], st.get_bottom()[1] - 0.4)
        self.play(FadeIn(st, shift=UP * 0.15), FadeIn(mine), run_time=0.7)
        self.tail()
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        head = T("回顾", 34, C_YELLOW).move_to([0, 2.85, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)
        rows = [("合法括号序列", "前缀和：两端同高 + 中间不跌破", "前缀和"),
                ("不跌破", "区间最小值 → nxt[l-1] > r，单调栈一遍", "区间最小值"),
                ("复杂度", "预处理 O(n)，每问 O(1)，答案一次输出", "预处理线性")]
        tab = VGroup()
        for a, b, _ in rows:
            tab.add(VGroup(T(a, 26, C_BLUE), T("→", 26, C_GREY), T(b, 24)))
        wa = max(r[0].width for r in tab)
        for i, r in enumerate(tab):
            y = 1.6 - 0.9 * i
            left_at(r[0], -5.8, y)
            left_at(r[1], -5.8 + wa + 0.3, y)
            left_at(r[2], -5.8 + wa + 1.0, y)
        for r, (*_, key) in zip(tab, rows):
            self.at(key)
            self.play(FadeIn(r, shift=UP * 0.15), run_time=0.5)
        self.tail(0.2)
        src = T("计算概论（B）2026fall · 11 月月考讲评与阶段复习 第 3 节 T6 · OpenJudge 31534", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
