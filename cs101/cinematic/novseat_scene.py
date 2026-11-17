"""图书馆选座：指针为什么不用回头（3B1B 风格，11 月月考 T2 精讲）。

由 make.py 驱动，时间轴约定见 cine.py。两个样例的逐步判定、一排十个座位上朴素模拟每人扫过的格子、
单指针的每一步、讲义代码原文、两种边界错误写法的实跑结果全部来自 novseatdata
（讲义 Python 代码原样复用 novdata.solve_t2；错误写法由讲义源码只改一行生成；test_novseat.py 独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novseatdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

DIM = "#3a4050"
C_ORANGE = "#FF9F43"


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def seat(ch, w):
    sq = Square(w * 0.88, stroke_color=C_GREY, stroke_width=2.5)
    sq.set_fill(C_GREY if ch == "1" else BG, 0.45 if ch == "1" else 0)
    return VGroup(sq, M(ch, int(w * 34), C_GREY if ch == "1" else WHITE).move_to(sq))


def strip(s, w, center):
    seats = VGroup(*[seat(ch, w) for ch in s]).arrange(RIGHT, buff=w * 0.12).move_to(center)
    idx = VGroup(*[M(str(i + 1), int(w * 22), C_GREY).next_to(seats[i], UP, buff=0.1) for i in range(len(s))])
    return seats, idx


def xmark(st):
    return Cross(st[0], stroke_color=C_RED, stroke_width=3.5).scale(0.62)


def sit(st, col=C_GREEN, size=None):
    """把座位改成「1」并涂色，返回动画列表。"""
    sq, tx = st
    new = M("1", size or int(sq.width / 0.88 * 34), col).move_to(sq)
    return [sq.animate.set_fill(col, 0.35).set_stroke(col), Transform(tx, new)]


class NovSeatLesson(Lesson):
    def construct(self):
        for b in ("title", "rule", "naive", "mono", "pointer", "code", "bug", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novseat] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def head(self, name, tag=""):
        g = VGroup(T("T2", 26, C_BLUE), T(name, 32))
        if tag:
            g.add(T(tag, 22, C_GREY))
        g.arrange(RIGHT, buff=0.3)
        return g.move_to([-6.6 + g.width / 2, 2.85, 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("十一月月考讲评 · 第二题", 26, C_BLUE).move_to([0, 2.5, 0])
        title = T("图书馆选座", 60).next_to(kick, DOWN, buff=0.3)
        sub = T("指针为什么不用回头", 32, C_YELLOW).next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)
        self.at("朴素模拟")
        a = VGroup(T("朴素模拟", 26, C_GREY), MathTex(r"O(nm)", color=C_GREY).scale(0.8)).arrange(RIGHT, buff=0.25)
        arr = Arrow(LEFT * 0.7, RIGHT * 0.7, color=C_GREY, buff=0, stroke_width=4)
        b = VGroup(T("一个指针", 26, C_GREEN), MathTex(r"O(n)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.25)
        row = VGroup(a, arr, b).arrange(RIGHT, buff=0.45).move_to([0, -0.85, 0])
        self.play(FadeIn(a), run_time=0.5)
        self.at("指针就够")
        self.play(GrowArrow(arr), FadeIn(b, shift=RIGHT * 0.2), run_time=0.7)
        self.at("边界")
        warn = VGroup(T("⚠", 28, C_RED), M("s[i - 1]", 26, C_RED), T("当 i = 0", 24, C_GREY),
                      T("样例全过，提交却错", 24, C_RED)).arrange(RIGHT, buff=0.3).move_to([0, -1.95, 0])
        self.play(FadeIn(warn, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 题意与样例
    def rule_beat(self):
        self.beat("rule")
        h = self.head("图书馆选座", "E31530 · n, m ≤ 2000")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        r1 = VGroup(T("一排 n 个座位：", 24, C_GREY), M("0", 26), T("空", 24), M("1", 26, C_GREY),
                    T("有人", 24)).arrange(RIGHT, buff=0.15)
        r2 = T("m 人依次来：坐编号最小、左右邻座都空的空位", 24)
        r3 = T("找不到就离开；输出坐下几人和最终状态", 24, C_GREY)
        rules = VGroup(r1, r2, r3).arrange(DOWN, buff=0.16, aligned_edge=LEFT).move_to([-6.4, 1.75, 0], aligned_edge=LEFT)
        rules.shift(RIGHT * (-6.4 - rules.get_left()[0]))
        self.play(FadeIn(r1), run_time=0.5)
        self.at("依次进来")
        self.play(FadeIn(r2), run_time=0.5)
        self.at("找不到")
        self.play(FadeIn(r3), run_time=0.5)

        # 样例一
        (inp1, out1), (inp2, out2) = D.SAMPLES
        assert D.run_io(D.solve, inp1) == out1 and D.run_io(D.solve, inp2) == out2
        tr1, fin1 = D.naive_trace("00000", 2)
        assert [g for _, g in tr1] == [0, 2] and fin1 == "10100"
        w = 0.72
        self.at("样例一")
        s1, i1 = strip("00000", w, [-2.4, 0.05, 0])
        lab1 = T("样例一  m = 2", 24, C_BLUE).next_to(s1, LEFT, buff=0.45)
        self.play(FadeIn(lab1), FadeIn(s1), FadeIn(i1), run_time=0.6)
        self.at("第一人坐一号")
        p1 = T("第 1 人", 20, C_GREEN).next_to(s1[0], DOWN, buff=0.12)
        self.play(*sit(s1[0]), FadeIn(p1), run_time=0.5)
        self.at("二号挨着")
        x1 = xmark(s1[1])
        self.play(Create(x1), run_time=0.4)
        self.at("第二人坐三号")
        p2 = T("第 2 人", 20, C_GREEN).next_to(s1[2], DOWN, buff=0.12)
        self.play(*sit(s1[2]), FadeIn(p2), run_time=0.5)
        o1 = VGroup(T("输出", 22, C_GREY), M(out1.replace("\n", "  "), 26, C_YELLOW)).arrange(RIGHT, buff=0.25)
        o1.move_to([1.0 + o1.width / 2, s1.get_y(), 0])
        self.play(FadeIn(o1, shift=LEFT * 0.15), run_time=0.4)

        # 样例二
        tr2, fin2 = D.naive_trace("0100", 2)
        assert [g for _, g in tr2] == [3, None] and fin2 == "0101"
        self.at("样例二")
        s2, i2 = strip("0100", w, [0, -1.75, 0])
        s2.align_to(s1, LEFT)
        for k in range(4):
            i2[k].next_to(s2[k], UP, buff=0.1)
        lab2 = T("样例二  m = 2", 24, C_BLUE).next_to(s2, LEFT, buff=0.45).align_to(lab1, LEFT)
        self.play(FadeIn(lab2), FadeIn(s2), FadeIn(i2), run_time=0.6)
        self.play(Indicate(s2[1], color=C_YELLOW), run_time=0.5)
        self.at("一号和三号")
        xs = [xmark(s2[k]) for k in (0, 2)]
        self.play(*[Create(x) for x in xs], run_time=0.5)
        self.at("四号在最右边")
        wall = DashedLine(s2[3].get_corner(UR) + RIGHT * 0.12, s2[3].get_corner(DR) + RIGHT * 0.12, color=C_GREY)
        wl = T("没有右邻", 20, C_GREY).next_to(wall, RIGHT, buff=0.12)
        self.play(Create(wall), FadeIn(wl), run_time=0.5)
        self.at("坐下")
        q1 = T("第 1 人", 20, C_GREEN).next_to(s2[3], DOWN, buff=0.12)
        self.play(*sit(s2[3]), FadeIn(q1), run_time=0.5)
        self.at("第二人没有")
        o2 = VGroup(T("输出", 22, C_GREY), M(out2.replace("\n", "  "), 26, C_YELLOW)).arrange(RIGHT, buff=0.25)
        o2.move_to([1.0 + o2.width / 2, s2.get_y(), 0])
        leave = T("第 2 人离开", 20, C_RED).next_to(o2, DOWN, buff=0.15).align_to(o2, LEFT)
        self.play(FadeIn(o2, shift=LEFT * 0.15), FadeIn(leave), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 朴素模拟
    def naive_beat(self):
        self.beat("naive")
        h = self.head("朴素模拟", "每位同学都从 1 号开始找")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        s, m = D.DEMO
        tr, fin = D.naive_trace(s, m)
        per = [len(seen) for seen, _ in tr]
        assert per == [1, 6, 8, 10, 10] and sum(per) == 35 and fin == "1001010101"
        w = 0.8
        self.at("十个座位")
        seats, idx = strip(s, w, [0.4, 1.45, 0])
        lab = T(f"来 {m} 人", 24, C_GREY).next_to(seats, LEFT, buff=0.45)
        self.play(FadeIn(seats), FadeIn(idx), FadeIn(lab), run_time=0.6)
        self.play(Indicate(seats[3], color=C_YELLOW), run_time=0.5)
        x0, step = seats[0].get_left()[0], seats[1].get_x() - seats[0].get_x()
        rows = VGroup()
        self.at("第一人扫")
        for k, (seen, got) in enumerate(tr):
            if k == 4:
                self.at("第五人")
            y = 0.62 - 0.45 * k
            right = seats[seen[-1]].get_right()[0]
            bar = Rectangle(width=right - x0, height=0.26, stroke_width=0).set_fill(C_YELLOW if got is not None else C_RED, 0.55)
            bar.move_to([x0 + bar.width / 2, y, 0])
            who = T(f"第 {k + 1} 人", 20, C_GREY).next_to(bar, LEFT, buff=0.2).align_to(lab, LEFT)
            cnt = T(f"{len(seen)} 格", 20, WHITE).next_to(seats[-1], RIGHT, buff=0.3).set_y(y)
            anims = [GrowFromEdge(bar, LEFT), FadeIn(who), FadeIn(cnt)]
            self.play(*anims, run_time=0.25 + 0.05 * len(seen))
            if got is not None:
                self.play(*sit(seats[got]), run_time=0.3)
            else:
                no = T("没有座位", 20, C_RED).next_to(cnt, RIGHT, buff=0.2)
                cnt.add(no)
                self.play(FadeIn(no), run_time=0.3)
            rows.add(VGroup(bar, who, cnt))
        self.at("三十五格")
        tot = VGroup(T("一共", 24, C_GREY), M(" + ".join(map(str, per)) + f" = {sum(per)}", 26, C_YELLOW),
                     T("格", 24, C_GREY)).arrange(RIGHT, buff=0.2)
        tot.move_to([0.4, -1.75, 0])
        self.play(FadeIn(tot, shift=UP * 0.15), run_time=0.6)
        self.at("每人最多")
        assert D.N_MAX * D.M_MAX == 4 * 10 ** 6
        bound = VGroup(T("每人 ≤ n 格：", 24, C_GREY),
                       MathTex(r"n\times m \le 2000\times 2000 = 4\times10^{6}", color=WHITE).scale(0.75),
                       T("Python 也能过", 24, C_GREEN)).arrange(RIGHT, buff=0.3)
        bound.move_to([0.4, -2.45, 0])
        self.play(FadeIn(bound[:2], shift=UP * 0.15), run_time=0.6)
        self.at("也能过")
        self.play(FadeIn(bound[2]), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 单调性论证
    def mono_beat(self):
        self.beat("mono")
        h = self.head("再想一步", "下一位一定坐在右边")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("第一")
        f1 = VGroup(T("①", 28, C_YELLOW), T("座位只会越坐越满：", 26), M("1", 28, C_GREY), T("不会变回", 24, C_GREY),
                    M("0", 28)).arrange(RIGHT, buff=0.2)
        f1.move_to([-6.4 + f1.width / 2, 1.95, 0])
        self.play(FadeIn(f1), run_time=0.6)
        # 示意：现在不能坐的座位，后来更不能坐
        w = 0.62
        a, _ = strip("0100", w, [-3.6, 0.95, 0])
        b, _ = strip("0101", w, [2.4, 0.95, 0])
        ta = T("现在", 20, C_GREY).next_to(a, LEFT, buff=0.3)
        tb = T("后来", 20, C_GREY).next_to(b, LEFT, buff=0.3)
        arr = Arrow(a.get_right() + RIGHT * 0.2, tb.get_left() + LEFT * 0.2, color=C_GREY, buff=0, stroke_width=3)
        assert not D.ok_at("0100", 0) and not D.ok_at("0101", 0) and not D.ok_at("0101", 2)
        self.at("现在不能坐")
        xa = xmark(a[0])
        self.play(FadeIn(a), FadeIn(ta), Create(xa), run_time=0.6)
        self.at("更不能坐")
        xb = xmark(b[0])
        xb2 = xmark(b[2])
        self.play(GrowArrow(arr), FadeIn(b), FadeIn(tb), Create(xb), Create(xb2), run_time=0.8)

        # ② 某人坐在 i：左边当时都不能坐，i+1 挨着他
        s, m = D.DEMO
        tr, _ = D.naive_trace(s, m)
        state = list(s)
        for seen, got in tr[:2]:
            state[got] = "1"
        i, nxt = tr[1][1], tr[2][1]
        assert (i, nxt) == (5, 7)
        before = list(s)
        before[tr[0][1]] = "1"                       # 第 2 人进来时的状态
        assert not any(D.ok_at(before, k) for k in range(i)) and not any(D.ok_at(state, k) for k in range(i + 2))
        self.at("第二")
        f2 = VGroup(T("②", 28, C_YELLOW), T("某人坐在 i（他选的是编号最小的）", 26)).arrange(RIGHT, buff=0.2)
        f2.move_to([-6.4 + f2.width / 2, -0.1, 0])
        w = 0.78
        seats, idx = strip("".join(state), w, [0.3, -1.25, 0])
        for k in range(len(s)):
            if state[k] == "1" and s[k] == "0":
                seats[k][0].set_fill(C_GREEN, 0.35).set_stroke(C_GREEN)
                seats[k][1].set_color(C_GREEN)
        self.play(FadeIn(f2), FadeIn(seats), FadeIn(idx), run_time=0.7)
        iv = T("i", 26, C_GREEN).next_to(seats[i], DOWN, buff=0.12)
        self.play(FadeIn(iv), Indicate(seats[i], color=C_GREEN), run_time=0.5)
        self.at("当时都不能坐")
        lb = Brace(VGroup(*seats[:i]), DOWN, color=C_GREY, buff=0.12)
        lt = T("当时都不能坐 → 以后也不能", 20, C_GREY).next_to(lb, DOWN, buff=0.1)
        self.play(GrowFromCenter(lb), FadeIn(lt), *[seats[k][0].animate.set_fill(DIM, 0.6) for k in range(i)
                                                    if state[k] == "0"], run_time=0.7)
        self.at("加一挨着")
        x1 = xmark(seats[i + 1])
        x1t = T("i+1", 22, C_RED).next_to(seats[i + 1], DOWN, buff=0.12)
        self.play(Create(x1), FadeIn(x1t), run_time=0.5)
        self.at("一定在")
        rb = Brace(VGroup(*seats[i + 2:]), DOWN, color=C_YELLOW, buff=0.12)
        rt = T("下一位只能在这里", 20, C_YELLOW).next_to(rb, DOWN, buff=0.1)
        self.play(GrowFromCenter(rb), FadeIn(rt), run_time=0.6)
        self.at("不必再看")
        self.play(Indicate(seats[nxt], color=C_YELLOW), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 单指针
    def pointer_beat(self):
        self.beat("pointer")
        h = self.head("一个指针", "能坐就坐，指针不回头")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        s, m = D.DEMO
        steps, sat, fin = D.pointer_trace(s, m)
        assert (len(steps), sat, fin) == (10, 4, "1001010101")
        w = 0.8
        seats, idx = strip(s, w, [0.4, 1.35, 0])
        lab = T(f"来 {m} 人", 24, C_GREY).next_to(seats, LEFT, buff=0.45)
        self.play(FadeIn(seats), FadeIn(idx), FadeIn(lab), run_time=0.6)
        self.at("还是这一排")
        ptr = Arrow(DOWN * 0.55, UP * 0.05, color=C_YELLOW, buff=0, stroke_width=6).next_to(seats[0], DOWN, buff=0.1)
        scan = VGroup(T("指针扫过", 22, C_GREY), Integer(0, font_size=34, color=C_YELLOW), T("格", 22, C_GREY))
        scan.arrange(RIGHT, buff=0.15).move_to([-1.8, -0.15, 0])
        satg = VGroup(T("坐下", 22, C_GREY), Integer(0, font_size=34, color=C_GREEN), T("人", 22, C_GREY))
        satg.arrange(RIGHT, buff=0.15).move_to([1.8, -0.15, 0])
        scan[2].add_updater(lambda m_: m_.next_to(scan[1], RIGHT, buff=0.15))
        satg[2].add_updater(lambda m_: m_.next_to(satg[1], RIGHT, buff=0.15))
        self.play(GrowArrow(ptr), FadeIn(scan), FadeIn(satg), run_time=0.4)
        n_sat = 0
        for k, (i, ok) in enumerate(steps):
            self.play(ptr.animate.next_to(seats[i], DOWN, buff=0.1), ChangeDecimalToValue(scan[1], k + 1), run_time=0.25)
            if ok:
                n_sat += 1
                self.play(*sit(seats[i]), ChangeDecimalToValue(satg[1], n_sat), run_time=0.3)
            else:
                self.play(Indicate(seats[i][0], color=C_RED, scale_factor=1.08), run_time=0.2)
        assert n_sat == sat
        self.at("第五人")
        no = T("第 5 人：扫到头，没有座位", 22, C_RED).next_to(satg, RIGHT, buff=0.4)
        self.play(FadeOut(ptr), FadeIn(no), run_time=0.5)
        self.at("十格对")
        tr, _ = D.naive_trace(s, m)
        naive = sum(len(x) for x, _ in tr)
        assert naive == 35
        nn = D.N_MAX
        worst = D.naive_worst(nn, D.M_MAX)
        big_ptr = len(D.pointer_trace("0" * nn, D.M_MAX)[0])
        assert (worst, big_ptr) == (3 * 10 ** 6, 2000)
        hdr = VGroup(T("", 22), T("朴素模拟", 24, C_GREY), T("一个指针", 24, C_GREEN))
        r1 = VGroup(T("这一排", 22, C_GREY), M(str(naive), 28, C_YELLOW), M(str(len(steps)), 28, C_GREEN))
        r2 = VGroup(T("n = m = 2000，全空", 22, C_GREY), M(f"{worst:,}", 28, C_YELLOW), M(f"{big_ptr:,}", 28, C_GREEN))
        cols = [-3.6, 0.6, 3.6]
        for r, y in ((hdr, -0.95), (r1, -1.5), (r2, -2.05)):
            for c, x in zip(r, cols):
                c.move_to([x, y, 0])
        r1[0].align_to(r2[0], LEFT)
        self.play(FadeIn(hdr[1:]), FadeIn(r1), run_time=0.6)
        self.at("两千")
        self.play(FadeIn(r2), run_time=0.6)
        self.at("复杂度")
        cx = VGroup(MathTex(r"O(nm)", color=C_GREY).scale(0.8), MathTex(r"\to", color=C_GREY).scale(0.8),
                    MathTex(r"O(n)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.25).move_to([0.6, -2.62, 0])
        self.play(FadeIn(cx, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string=D.LECTURE_SRC, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=True, paragraph_config={"font": MONO, "font_size": 20})
        code.scale_to_fit_width(7.8)
        if code.height > 5.4:
            code.scale_to_fit_height(5.4)
        code.move_to([-6.7 + code.width / 2, 0.05, 0])
        ln = code.code_lines
        assert len(ln) == 13
        cap = T("讲义 Python 代码", 22, C_GREY).next_to(code, UP, buff=0.12).align_to(code, LEFT)
        self.play(FadeIn(code, shift=UP * 0.2), FadeIn(cap), run_time=0.8)
        xr = code.get_right()[0] + 0.4

        def hl(lines, col):
            return VGroup(*[SurroundingRectangle(ln[k], color=col, buff=(0.06, 0.03), stroke_width=2) for k in lines])

        def note(lines, *parts, col=WHITE):
            g = VGroup(*parts).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
            y = np.mean([ln[k].get_y() for k in lines])
            return g.move_to([xr + g.width / 2, y, 0])

        cur = VGroup()

        def show(lines, col, *parts, dy=0.0):
            nonlocal cur
            box, nt = hl(lines, col), note(lines, *parts).shift(UP * dy)
            self.play(FadeOut(cur), Create(box), FadeIn(nt, shift=LEFT * 0.15), run_time=0.6)
            cur = VGroup(box, nt)
            return nt

        def left_note():
            return (VGroup(M("i == 0", 22, C_GREEN), T("没有左邻", 20, C_GREY)).arrange(RIGHT, buff=0.2),
                    VGroup(M("or", 22, C_GREY), M("s[i - 1] == '0'", 22, C_GREEN), T("左邻空", 20, C_GREY)).arrange(RIGHT, buff=0.2))
        self.at("原地改")
        show([1], C_BLUE, T("字符串不能原地改 → 先转成列表", 22, C_BLUE))
        self.at("坐满")
        show([4, 5], C_YELLOW, T("坐满 m 人就跳出", 22, C_YELLOW))
        self.at("左边可坐")
        show([6], C_GREEN, *left_note())
        self.at("右边同理")
        show([7], C_GREEN, VGroup(M("i == n - 1", 22, C_GREEN), T("或右邻空", 20, C_GREY)).arrange(RIGHT, buff=0.2))
        self.at("本座空")
        show([8, 9, 10], C_ORANGE, T("三条都满足才坐下，人数加一", 22, C_ORANGE))
        self.at("短路")
        n3 = show([6], C_YELLOW, *left_note())
        sc = VGroup(M("i == 0", 24, C_GREEN), T("为真", 22, C_GREEN), T("→", 22, C_GREY),
                    T("后半句根本不执行", 22, C_YELLOW)).arrange(RIGHT, buff=0.15)
        sc.next_to(n3, DOWN, buff=0.35).align_to(n3, LEFT)
        self.play(FadeIn(sc, shift=UP * 0.15), run_time=0.5)
        self.at("不去读")
        self.play(Indicate(n3[1][1], color=C_YELLOW), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 边界失分点
    def bug_beat(self):
        self.beat("bug")
        h = self.head("失分点", "边界座位的邻座")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        ok = VGroup(T("✓", 24, C_GREEN), M(D.LINE_LEFT, 24, C_GREEN)).arrange(RIGHT, buff=0.25)
        bad = VGroup(T("✗", 24, C_RED), M(D.BAD_LEFT, 24, C_RED)).arrange(RIGHT, buff=0.25)
        pair = VGroup(ok, bad).arrange(DOWN, buff=0.15, aligned_edge=LEFT).move_to([-6.4, 1.95, 0], aligned_edge=LEFT)
        pair.shift(RIGHT * (-6.4 - pair.get_left()[0]))
        self.play(FadeIn(ok), run_time=0.4)
        self.at("删掉")
        self.play(FadeIn(bad, shift=DOWN * 0.15), run_time=0.5)

        s, m = D.BUG_IN
        inp = f"{len(s)} {m}\n{s}\n"
        good_out, bad_out = D.run_io(D.solve, inp), D.run_io(D.solve_bug_left, inp)
        assert (good_out, bad_out) == ("2\n10101", "1\n01001")
        assert all(D.run_io(D.solve_bug_left, a) == b for a, b in D.SAMPLES)
        w = 0.78
        self.at("Python 不报错")
        seats, idx = strip(s, w, [-1.6, 0.35, 0])
        ghost = DashedVMobject(Square(w * 0.88, stroke_color=C_RED, stroke_width=2.5), num_dashes=16)
        ghost.next_to(seats[0], LEFT, buff=w * 0.12)
        gl = M("s[-1]", 20, C_RED).next_to(ghost, UP, buff=0.1)
        self.play(FadeIn(seats), FadeIn(idx), Create(ghost), FadeIn(gl), run_time=0.6)
        arc = CurvedArrow(ghost.get_bottom() + DOWN * 0.06, seats[-1].get_bottom() + DOWN * 0.06,
                          angle=TAU / 7, color=C_RED, stroke_width=3)
        self.play(Create(arc), Indicate(seats[-1], color=C_RED), run_time=0.8)
        self.at("两个样例")
        smp = VGroup(T("样例一 ✓", 22, C_GREEN), T("样例二 ✓", 22, C_GREEN)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        smp.next_to(seats, RIGHT, buff=0.7)
        self.play(FadeIn(smp), run_time=0.5)
        self.at("换五个座位")
        inl = T(f"输入：{s}，来 {m} 人", 22, C_GREY).next_to(smp, RIGHT, buff=0.6)
        if inl.get_right()[0] > 6.6:
            inl.next_to(smp, DOWN, buff=0.2).align_to(smp, LEFT)
        self.play(FadeIn(inl), Indicate(seats[-1], color=C_YELLOW), run_time=0.6)

        def result(out, col, tag):
            k, st = out.split("\n")
            row, _ = strip(st, 0.6, ORIGIN)
            for c, ch, ch0 in zip(row, st, s):
                if ch == "1" and ch0 == "0":
                    c[0].set_fill(col, 0.35).set_stroke(col)
                    c[1].set_color(col)
            g = VGroup(T(tag, 22, col), row, T(f"坐下 {k} 人", 22, col)).arrange(RIGHT, buff=0.35)
            return g
        self.at("正确答案")
        rg = result(good_out, C_GREEN, "正确")
        rg.move_to([-6.4 + rg.width / 2, -1.05, 0])
        self.play(FadeIn(rg, shift=UP * 0.15), run_time=0.6)
        self.at("错误写法")
        rb = result(bad_out, C_RED, "错误")
        rb.move_to([-6.4 + rb.width / 2, -1.85, 0])
        why = T("以为 1 号左邻有人", 20, C_RED).next_to(rb, RIGHT, buff=0.4)
        self.play(FadeIn(rb, shift=UP * 0.15), FadeIn(why), run_time=0.6)

        # 右边：Python 直接报错；C++ 两头都不是座位
        self.at("右边删掉")
        left_part = VGroup(pair, seats, idx, ghost, gl, arc, smp, inl, rg, rb, why)
        self.play(FadeOut(left_part), run_time=0.4)
        with_err = None
        try:
            D.run_io(D.solve_bug_right, D.SAMPLES[1][0])
        except IndexError as e:
            with_err = type(e).__name__
        assert with_err == "IndexError"
        assert D.run_io(D.solve_bug_right, D.SAMPLES[0][0]) == D.SAMPLES[0][1]
        r_ok = VGroup(T("✓", 24, C_GREEN), M(D.LINE_RIGHT, 24, C_GREEN)).arrange(RIGHT, buff=0.25)
        r_bad = VGroup(T("✗", 24, C_RED), M(D.BAD_RIGHT, 24, C_RED)).arrange(RIGHT, buff=0.25)
        rp = VGroup(r_ok, r_bad).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        rp.shift([-6.4 - rp.get_left()[0], 1.95 - rp.get_y(), 0])
        self.play(FadeIn(rp), run_time=0.5)
        self.at("下标越界")
        err = VGroup(T("样例二", 22, C_GREY), M("0100", 24), T("→", 22, C_GREY),
                     M(f"{with_err}: list index out of range", 22, C_RED)).arrange(RIGHT, buff=0.2)
        err.move_to([-6.4 + err.width / 2, 0.75, 0])
        loud = T("运行就报错，反而好查", 22, C_YELLOW).next_to(err, DOWN, buff=0.15).align_to(err, LEFT)
        w = 0.62
        s2, i2 = strip("0100", w, [3.3, -0.05, 0])
        g2 = DashedVMobject(Square(w * 0.88, stroke_color=C_RED, stroke_width=2.5), num_dashes=16)
        g2.next_to(s2[-1], RIGHT, buff=w * 0.12)
        g2l = M("s[4]", 20, C_RED).next_to(g2, UP, buff=0.1)
        self.play(FadeIn(err, shift=UP * 0.15), FadeIn(s2), FadeIn(i2), Create(g2), FadeIn(g2l), run_time=0.6)
        self.at("好查")
        self.play(FadeIn(loud), run_time=0.4)
        self.at("C++")
        sat_c, st_c = D.cpp_right_bug("0100", 2)
        assert (sat_c, st_c) == (0, "0100")
        c1 = VGroup(T("C++", 24, C_BLUE), M("s[-1]", 24, C_RED), T("越界访问，读到什么说不准", 22, C_GREY)).arrange(RIGHT, buff=0.25)
        c2 = VGroup(T("C++", 24, C_BLUE), M("s[n]", 24, C_RED), T("是结尾的空字符", 22, C_GREY), M("'\\0' ≠ '0'", 22, C_RED),
                    T("→ 最后一座永远坐不下", 22, C_RED)).arrange(RIGHT, buff=0.25)
        cg = VGroup(c1, c2).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        cg.move_to([-6.4 + cg.width / 2, -1.25, 0])
        if cg.width > 13.0:
            cg.scale_to_fit_width(13.0).move_to([0, -1.25, 0])
        self.play(FadeIn(c1, shift=UP * 0.15), run_time=0.5)
        self.at("空字符")
        self.play(FadeIn(c2, shift=UP * 0.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        head = T("回顾 · 图书馆选座", 32, C_YELLOW).move_to([0, 2.85, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)
        rows = [("朴素模拟", "每人从头扫", "O(nm) ≤ 4×10⁶", C_GREY, "朴素"),
                ("单调性", "越坐越满，下一位一定在右边", "前面不必再看", C_YELLOW, "越坐越满"),
                ("一个指针", "从左扫到右，坐满 m 人就停", "O(n)", C_GREEN, "一个指针"),
                ("边界", "先判下标再读邻座", "n = 1 要测", C_RED, "边界")]
        tab = VGroup()
        for a, b, c, col, _ in rows:
            tab.add(VGroup(T(a, 28, col), T(b, 24), T(c, 24, C_GREY)))
        widths = [max(r[k].width for r in tab) for k in range(3)]
        xs = [-6.2, -6.2 + widths[0] + 0.6, -6.2 + widths[0] + widths[1] + 1.2]
        for i, r in enumerate(tab):
            y = 1.7 - 0.85 * i
            for k in range(3):
                r[k].move_to([xs[k] + r[k].width / 2, y, 0])
        if tab.width > 13.0:
            tab.scale_to_fit_width(13.0).move_to([0, tab.get_y(), 0])
        for r, (*_, key) in zip(tab, rows):
            self.at(key)
            self.play(FadeIn(r, shift=UP * 0.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 11 月月考讲评 T2 · OpenJudge E31530", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
