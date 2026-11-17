"""双重回文：十进制和二进制都要对称（11 月月考 T1 E31529 精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例逐个检查、忘切 0b 前缀的错误输出、C++ pal 逐步轨迹、
n = 100 的筛选过程、n = 10⁶ 的答案与字符总量全部来自 novpaldata（讲义 Python 参考代码原样复用 novdata.solve_t1；
test_novpal.py 用字符串翻转暴力、int(s, base) 重建独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novpaldata as D  # noqa: E402
from cine import *  # noqa: E402,F403

DIM = "#3a4050"
HL = "#2a3550"


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def ok_mark(ok, size=26):
    return T("✓" if ok else "✗", size, C_GREEN if ok else C_RED)


class NovPalLesson(Lesson):
    def construct(self):
        for b in ("title", "sample1", "strrev", "even", "revnum", "sample2", "cost", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    # ---------------------------------------------------------------- 工具
    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novpal] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def head(self, no, name, tag, pos=(-6.6, 2.95)):
        g = VGroup(T(no, 26, C_BLUE), T(name, 32), *([T(tag, 22, C_GREY)] if tag else [])).arrange(RIGHT, buff=0.3)
        return g.move_to([pos[0] + g.width / 2, pos[1], 0])

    def code_panel(self, lines, size=20, max_w=6.4, top=2.4, left=-6.6, lh=0.42):
        """逐行等宽代码，保留缩进；返回 VGroup（每行一个 Text）。"""
        cw = M("0" * 20, size).width / 20
        rows = VGroup()
        for k, s in enumerate(lines):
            ind = len(s) - len(s.lstrip(" "))
            t = M(s.strip(), size, "#D8DCE6")
            t.move_to([left + ind * cw + t.width / 2, top - k * lh, 0])
            rows.add(t)
        if rows.width > max_w:
            rows.scale(max_w / rows.width, about_point=[left, top, 0])
        return rows

    def hl_box(self, row, panel):
        """代码行的半透明底色条（不透明度 < 0.6，不算遮挡）。"""
        r = Rectangle(width=panel.width + 0.3, height=row.height + 0.16, stroke_width=0)
        r.set_fill(C_YELLOW, 0.16)
        r.move_to([panel.get_left()[0] + panel.width / 2, row.get_y(), 0])
        return r

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("11 月月考 · T1  E31529", 26, C_BLUE).move_to([0, 2.9, 0])
        title = T("双重回文", 60).next_to(kick, DOWN, buff=0.25)
        sub = T("十进制和二进制都要对称", 30, C_YELLOW).next_to(title, DOWN, buff=0.22)
        self.play(FadeIn(kick), Write(title), FadeIn(sub, shift=UP * 0.15), run_time=1.3)
        self.at("十进制写出来")
        x = D.EX_TITLE
        dec, bb = str(x), D.binstr(x)
        assert dec == dec[::-1] and bb == bb[::-1]

        def mirror(s, size, color, label, cx):
            digs = VGroup(*[M(c, size, color) for c in s]).arrange(RIGHT, buff=0.08)
            digs.move_to([cx, -0.55, 0])
            axis = DashedLine(digs.get_top() + UP * 0.18, digs.get_bottom() + DOWN * 0.18, color=C_GREY,
                              dash_length=0.08, stroke_width=2).move_to([digs.get_x(), digs.get_y(), 0])
            lab = T(label, 22, C_GREY).next_to(digs, UP, buff=0.4)
            return VGroup(digs, axis, lab)
        left = mirror(dec, 44, WHITE, "十进制", -3.3)
        right = mirror(bb, 44, C_YELLOW, "二进制", 2.6)
        self.play(FadeIn(left[0]), FadeIn(left[2]), Create(left[1]), run_time=0.7)
        self.at("二进制写出来")
        eq = T("=", 36, C_GREY).move_to([(left[0].get_right()[0] + right[0].get_left()[0]) / 2, -0.55, 0])
        self.play(FadeIn(eq), FadeIn(right[0]), FadeIn(right[2]), Create(right[1]), run_time=0.7)
        self.play(*[Indicate(VGroup(g[0][k], g[0][-1 - k]), color=C_GREEN, scale_factor=1.15)
                    for g in (left, right) for k in range(len(g[0]) // 2)], run_time=0.9)
        self.at("给定")
        spec = VGroup(T("输入", 24, C_GREY), MathTex(r"n\ (1\le n\le 10^{6})", color=WHITE).scale(0.8),
                      T("→", 26, C_GREY), T("输出", 24, C_GREY), T("个数", 26, C_TEAL), T("最大的一个", 26, C_TEAL))
        spec.arrange(RIGHT, buff=0.25).move_to([0, -2.2, 0])
        self.play(FadeIn(spec, shift=UP * 0.15), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 样例一
    def sample1_beat(self):
        self.beat("sample1")
        inp, out = D.SAMPLES[0]
        n = int(inp)
        assert D.run_io(D.SOLVE, inp) == out == "3 5"
        tab = D.scan_table(n)
        h = self.head("样例一", f"n = {n}", "逐个看 1 到 5")
        xs = [-4.6, -2.4, 0.4, 3.0]
        hy, dy = 1.75, 0.68
        hdr = VGroup(*[T(s, 24, C_GREY).move_to([x, hy, 0]) for s, x in zip(["i", "十进制", "二进制", "双重回文？"], xs)])
        rule = Line([-5.5, hy - 0.35, 0], [4.2, hy - 0.35, 0], color=DIM, stroke_width=2)
        ys = [hy - 0.75 - k * dy for k in range(n)]
        idx = VGroup(*[M(str(i), 28, C_GREY).move_to([xs[0], y, 0]) for (i, _, _, _), y in zip(tab, ys)])
        dec = VGroup(*[M(str(i), 30).move_to([xs[1], y, 0]) for (i, _, _, _), y in zip(tab, ys)])
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(hdr), Create(rule), FadeIn(idx), run_time=0.8)
        self.play(FadeIn(dec), run_time=0.5)
        self.at("一位数")
        assert all(d for _, _, d, _ in tab)
        self.play(*[m.animate.set_color(C_GREEN) for m in dec], run_time=0.6)
        bins, marks, verdict = VGroup(), VGroup(), []
        keys = ["一就是一", "二是一零", "三是一一", "四是一零零", "五是一零一"]
        for (i, b, d, bp), y, key in zip(tab, ys, keys):
            self.at(key)
            bm = M(b, 30, C_YELLOW if bp else C_RED).move_to([xs[2], y, 0])
            mk = ok_mark(d and bp, 30).move_to([xs[3], y, 0])
            bins.add(bm)
            marks.add(mk)
            verdict.append(mk)
            anims = [FadeIn(bm, shift=LEFT * 0.15), FadeIn(mk)]
            if not bp:
                rev = M(b[::-1], 22, C_RED).next_to(bm, RIGHT, buff=0.35)
                note = VGroup(T("倒过来", 18, C_GREY), rev).arrange(RIGHT, buff=0.12).next_to(bm, RIGHT, buff=0.3)
                anims.append(FadeIn(note))
                marks.add(note)
            self.play(*anims, run_time=0.5)
        self.at("所以一共三个")
        good = [k for k, (i, _, d, bp) in enumerate(tab) if d and bp]
        assert [tab[k][0] for k in good] == [1, 3, 5]
        boxes = VGroup(*[SurroundingRectangle(VGroup(idx[k], verdict[k]), color=C_GREEN, buff=0.1, stroke_width=2)
                         for k in good])
        res = VGroup(T("输出", 26, C_GREY), M(out, 34, C_GREEN)).arrange(RIGHT, buff=0.3)
        res.move_to([5.4, ys[2], 0])
        self.play(*[Create(b) for b in boxes], run_time=0.6)
        self.play(FadeIn(res, shift=LEFT * 0.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 字符串翻转与 0b 前缀
    def strrev_beat(self):
        self.beat("strrev")
        h = self.head("写法一", "字符串翻转", "讲义 Python 版")
        code = self.code_panel(D.PY_CODE, size=20, max_w=6.6, top=2.15, lh=0.5)
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(code), run_time=0.8)
        x0 = 0.75
        hl = self.hl_box(code[4], code)
        self.play(FadeIn(hl), run_time=0.4)
        rule = VGroup(M("s == s[::-1]", 30, C_TEAL), T("倒过来还是自己", 22, C_GREY)).arrange(RIGHT, buff=0.35)
        rule.move_to([x0, 1.9, 0], aligned_edge=LEFT)
        self.play(FadeIn(rule, shift=UP * 0.1), run_time=0.5)
        self.at("十进制用")
        hl2 = self.hl_box(code[3], code)
        r1 = VGroup(M("str(585)", 24, WHITE), T("→", 24, C_GREY), M("'585'", 24, C_GREEN)).arrange(RIGHT, buff=0.2)
        r2 = VGroup(M("bin(5)", 24, WHITE), T("→", 24, C_GREY),
                    Text("'0b101'", font=MONO, font_size=24, color=C_YELLOW, t2c={"0b": C_RED})
                    ).arrange(RIGHT, buff=0.2)
        assert bin(5) == "0b101" and str(585)[::-1] == "585"
        r1.move_to([x0, 1.05, 0], aligned_edge=LEFT)
        r2.move_to([x0, 0.4, 0], aligned_edge=LEFT)
        self.play(Transform(hl, hl2), FadeIn(r1), run_time=0.5)
        self.play(FadeIn(r2), run_time=0.5)
        self.at("前缀")
        self.play(Indicate(r2[2][1:3], color=C_RED, scale_factor=1.3), run_time=0.7)
        self.at("忘了")
        wrong = VGroup(M("'0b101'[::-1]", 24, WHITE), T("→", 24, C_GREY), M("'101b0'", 24, C_RED),
                       T("≠", 26, C_RED)).arrange(RIGHT, buff=0.2)
        assert bin(5)[::-1] == "101b0"
        wrong.move_to([x0, -0.35, 0], aligned_edge=LEFT)
        fix = VGroup(M("bin(5)[2:]", 24, WHITE), T("→", 24, C_GREY), M("'101'", 24, C_GREEN), ok_mark(True, 24))
        fix.arrange(RIGHT, buff=0.2).move_to([x0, -1.0, 0], aligned_edge=LEFT)
        self.play(FadeIn(wrong, shift=UP * 0.1), run_time=0.6)
        self.play(FadeIn(fix, shift=UP * 0.1), run_time=0.5)
        self.at("样例一会输出")
        bad = D.run_io(D.solve_t1_nostrip, D.SAMPLES[0][0])
        assert bad == "0 1"
        run = VGroup(T("忘切前缀，n = 5 输出", 22, C_GREY), M(bad, 28, C_RED),
                     T(f"（应为 {D.SAMPLES[0][1]}）", 22, C_GREEN)).arrange(RIGHT, buff=0.22)
        run.move_to([x0, -1.75, 0], aligned_edge=LEFT)
        self.play(FadeIn(run, shift=UP * 0.1), run_time=0.6)
        self.at("从小到大")
        hl3 = self.hl_box(code[6], code)
        note = T("从小到大枚举：最后一个满足的就是最大的", 22, C_TEAL).move_to([x0, -2.45, 0], aligned_edge=LEFT)
        self.play(Transform(hl, hl3), FadeIn(note), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 偶数不可能
    def even_beat(self):
        self.beat("even")
        h = self.head("剪枝", "偶数可能是二进制回文吗？", "")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("最高位")
        cells = VGroup(*[Square(0.8, stroke_color=C_GREY, stroke_width=2) for _ in range(6)])
        cells.arrange(RIGHT, buff=0.08).move_to([-2.4, 0.95, 0])
        d_hi = M("1", 32, C_YELLOW).move_to(cells[0])
        d_lo = M("0", 32, C_RED).move_to(cells[5])
        dots = M("…", 28, C_GREY).move_to(VGroup(cells[2], cells[3]))
        lab_hi = T("最高位：一定是 1", 22, C_YELLOW).next_to(cells[0], DOWN, buff=0.3).align_to(cells[0], LEFT)
        self.play(FadeIn(VGroup(*cells[:5])), FadeIn(d_hi), FadeIn(dots), FadeIn(lab_hi), run_time=0.6)
        self.at("末位一定")
        lab_lo = T("偶数：末位是 0", 22, C_RED).next_to(cells[5], DOWN, buff=0.3).align_to(cells[5], RIGHT)
        self.play(FadeIn(cells[5]), FadeIn(d_lo), FadeIn(lab_lo), run_time=0.6)
        self.at("首尾对不上")
        arc = CurvedArrow(cells[0].get_top() + UP * 0.08, cells[5].get_top() + UP * 0.08, angle=-TAU / 6,
                          color=C_RED, stroke_width=3)
        neq = T("1 ≠ 0", 26, C_RED).next_to(arc, UP, buff=0.08)
        self.play(Create(arc), FadeIn(neq), run_time=0.7)
        self.at("比如六")
        ex = VGroup()
        for e, y in zip(D.EX_EVEN, [1.6, 0.8]):
            b = D.binstr(e)
            assert b[0] == "1" and b[-1] == "0"
            digs = VGroup(*[M(c, 30, C_YELLOW if k == 0 else (C_RED if k == len(b) - 1 else WHITE))
                            for k, c in enumerate(b)]).arrange(RIGHT, buff=0.06)
            row = VGroup(M(str(e), 30), T("=", 26, C_GREY), digs, M("₂", 22, C_GREY), ok_mark(False, 26))
            row.arrange(RIGHT, buff=0.2)
            row[3].next_to(digs, RIGHT, buff=0.04).align_to(digs, DOWN)
            row[4].next_to(row[3], RIGHT, buff=0.3)
            row.move_to([2.6, y, 0], aligned_edge=LEFT)
            ex.add(row)
        self.play(FadeIn(ex[0]), run_time=0.5)
        self.play(FadeIn(ex[1]), run_time=0.5)
        self.at("只枚举奇数")
        nums = VGroup()
        for i in range(1, 21):
            sq = Square(0.56, stroke_color=C_GREY, stroke_width=1.5)
            nums.add(VGroup(sq, M(str(i), 20).move_to(sq)))
        nums.arrange(RIGHT, buff=0.08).move_to([0, -1.4, 0])
        code = M("for i in range(1, n + 1, 2):", 26, C_GREEN).move_to([0, -0.65, 0])
        self.play(FadeIn(nums), FadeIn(code), run_time=0.6)
        self.play(*[nums[k].animate.set_opacity(0.18) for k in range(1, 20, 2)],
                  *[nums[k][0].animate.set_stroke(C_GREEN) for k in range(0, 20, 2)], run_time=0.7)
        self.at("减半")
        half = VGroup(MathTex(r"10^{6}", color=WHITE).scale(0.85), T("个数", 24, C_GREY), T("→", 26, C_GREY),
                      MathTex(r"5\times10^{5}", color=C_GREEN).scale(0.85), T("个奇数：工作量减半", 24, C_GREEN))
        half.arrange(RIGHT, buff=0.22).move_to([0, -2.35, 0])
        assert len(range(1, 10 ** 6 + 1, 2)) == 5 * 10 ** 5
        self.play(FadeIn(half, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- C++ 版：把数倒过来
    def revnum_beat(self):
        self.beat("revnum")
        h = self.head("写法二", "把数按进制倒过来", "讲义 C++ 版")
        code = self.code_panel(D.CPP_PAL, size=20, max_w=6.6, top=2.15, lh=0.48)
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(code), run_time=0.8)
        self.at("t 从 x 开始")
        hl = self.hl_box(code[2], code)
        self.play(FadeIn(hl), run_time=0.4)
        self.at("y 乘进制")
        self.play(Transform(hl, self.hl_box(code[3], code)), run_time=0.4)
        self.at("t 变成零")
        self.play(Transform(hl, self.hl_box(code[2], code)), run_time=0.4)

        # 33 按二进制逐步
        self.at("三十三按二进制")
        x = D.EX_YES
        steps = D.pal_trace(x, 2)
        assert D.pal(x, 2) and [y for _, _, y in steps] == [1, 2, 4, 8, 16, 33]
        xs = [1.6, 3.4, 5.4]
        hy, dy = 1.25, 0.45
        title = VGroup(M(f"x = {x} =", 26), M(D.binstr(x), 26, C_YELLOW), M("₂", 20, C_GREY)).arrange(RIGHT, buff=0.15)
        title[2].next_to(title[1], RIGHT, buff=0.04).align_to(title[1], DOWN)
        title.move_to([3.5, 2.05, 0])
        hdr = VGroup(*[M(s, 22, C_GREY).move_to([cx, hy, 0]) for s, cx in zip(["t", "t % 2", "y"], xs)])
        rule = Line([0.8, hy - 0.25, 0], [6.4, hy - 0.25, 0], color=DIM, stroke_width=2)
        self.play(FadeIn(title), FadeIn(hdr), Create(rule), Transform(hl, self.hl_box(code[3], code)), run_time=0.6)
        self.at("余数依次")
        rows = VGroup()
        for k, (t, r, y) in enumerate(steps):
            yy = hy - 0.55 - k * dy
            row = VGroup(M(str(t), 24).move_to([xs[0], yy, 0]), M(str(r), 24, C_YELLOW).move_to([xs[1], yy, 0]),
                         M(str(y), 24, C_TEAL).move_to([xs[2], yy, 0]))
            rows.add(row)
        for row in rows:
            self.play(FadeIn(row[0]), FadeIn(row[1]), run_time=0.3)
        self.at("y 依次长成")
        for row in rows:
            self.play(FadeIn(row[2], shift=LEFT * 0.15), run_time=0.3)
        self.at("最后 y 等于 x")
        yes = VGroup(M(f"y = {steps[-1][2]} = x", 24, C_GREEN), ok_mark(True, 24),
                     T("回文", 22, C_GREEN)).arrange(RIGHT, buff=0.2)
        yes.next_to(rows, DOWN, buff=0.3).align_to(rule, LEFT).shift(RIGHT * 0.3)
        self.play(Transform(hl, self.hl_box(code[4], code)), FadeIn(yes), run_time=0.6)

        # 37 与 585585
        self.at("换成三十七")
        ny = D.pal_trace(D.EX_NO, 2)
        assert not D.pal(D.EX_NO, 2) and ny[-1][2] == 41
        l1 = VGroup(M(f"x = {D.EX_NO} = {D.binstr(D.EX_NO)}₂", 22), T("按 2 进制", 20, C_GREY)).arrange(RIGHT, buff=0.25)
        s1 = VGroup(M("y: " + " → ".join(str(y) for _, _, y in ny), 22, C_TEAL),
                    M(f"≠ {D.EX_NO}", 22, C_RED), ok_mark(False, 22)).arrange(RIGHT, buff=0.2)
        blk1 = VGroup(l1, s1).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([-6.4, -1.0, 0], aligned_edge=LEFT)
        self.play(FadeIn(blk1, shift=UP * 0.1), run_time=0.6)
        self.at("十进制也一样")
        dyy = D.pal_trace(D.EX_DEC, 10)
        assert D.pal(D.EX_DEC, 10)
        l2 = VGroup(M(f"x = {D.EX_DEC}", 22), T("按 10 进制", 20, C_GREY)).arrange(RIGHT, buff=0.25)
        s2 = VGroup(M("y: " + " → ".join(str(y) for _, _, y in dyy), 22, C_TEAL),
                    M("= x", 22, C_GREEN), ok_mark(True, 22)).arrange(RIGHT, buff=0.2)
        blk2 = VGroup(l2, s2).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([-6.4, -2.2, 0], aligned_edge=LEFT)
        for b in (blk1, blk2):
            if b.width > 6.8:
                b.scale(6.8 / b.width, about_edge=LEFT)
        self.play(FadeIn(blk2, shift=UP * 0.1), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 样例二
    def sample2_beat(self):
        self.beat("sample2")
        inp, out = D.SAMPLES[1]
        n = int(inp)
        assert D.run_io(D.SOLVE, inp) == out == "7 99"
        h = self.head("样例二", f"n = {n}", "先筛十进制，再查二进制")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("十进制回文")
        dp = D.dec_pals(n)
        assert len(dp) == 18
        cells = {}
        grid = VGroup()
        for k, v in enumerate(dp):
            sq = Square(0.72, stroke_color=C_GREY, stroke_width=1.5)
            c = VGroup(sq, M(str(v), 24).move_to(sq))
            cells[v] = c
            grid.add(c)
        grid.arrange_in_grid(rows=2, cols=9, buff=0.12).move_to([0, 1.45, 0])
        self.play(FadeIn(grid[:9]), run_time=0.5)
        self.play(FadeIn(grid[9:]), run_time=0.5)
        self.at("只留奇数")
        odd = [v for v in dp if v % 2]
        assert len(odd) == 10
        self.play(*[cells[v].animate.set_opacity(0.15) for v in dp if v % 2 == 0],
                  *[cells[v][0].animate.set_stroke(C_TEAL) for v in odd], run_time=0.6)
        self.at("剩下十个")
        cards = VGroup()
        for v in odd:
            box = RoundedRectangle(corner_radius=0.1, width=1.18, height=1.2, stroke_color=C_GREY, stroke_width=1.5)
            cards.add(box)
        cards.arrange(RIGHT, buff=0.12).move_to([0, -0.55, 0])
        tops = VGroup(*[M(str(v), 26).move_to(c.get_center() + UP * 0.3) for v, c in zip(odd, cards)])
        self.play(*[TransformFromCopy(cells[v][1], t) for v, t in zip(odd, tops)], FadeIn(cards), run_time=0.8)
        self.at("再查二进制")
        bins = VGroup(*[M(D.binstr(v), 20, C_YELLOW).move_to(c.get_center() + DOWN * 0.25) for v, c in zip(odd, cards)])
        for b, c in zip(bins, cards):
            if b.width > c.width - 0.12:
                b.scale_to_fit_width(c.width - 0.12)
        marks = {v: ok_mark(D.pal(v, 2), 24).next_to(c, DOWN, buff=0.12) for v, c in zip(odd, cards)}
        small = [v for v in odd if v < 10]
        assert all(D.pal(v, 2) for v in small)
        self.play(*[FadeIn(bins[k]) for k in range(len(odd))], run_time=0.6)
        self.play(*[FadeIn(marks[v]) for v in small], *[cards[odd.index(v)].animate.set_stroke(C_GREEN) for v in small],
                  run_time=0.5)
        for key, vs in [("十一是", [11]), ("三十三是", [33]), ("五十五", [55, 77]), ("九十九是", [99])]:
            self.at(key)
            anims = []
            for v in vs:
                k = odd.index(v)
                good = D.pal(v, 2)
                anims += [FadeIn(marks[v]), cards[k].animate.set_stroke(C_GREEN if good else C_RED),
                          Indicate(bins[k], color=C_GREEN if good else C_RED, scale_factor=1.15)]
            self.play(*anims, run_time=0.6)
        self.at("一共七个")
        pals = [v for v in odd if D.pal(v, 2)]
        assert pals == D.double_pals(n) == [1, 3, 5, 7, 9, 33, 99]
        res = VGroup(T(f"{len(pals)} 个：", 24, C_GREY), M(" ".join(map(str, pals)), 24, C_GREEN),
                     T("输出", 24, C_GREY), M(out, 30, C_GREEN)).arrange(RIGHT, buff=0.25)
        res.move_to([0, -2.45, 0])
        self.play(FadeIn(res, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 复杂度与大数据
    def cost_beat(self):
        self.beat("cost")
        h = self.head("复杂度", "够不够快？", "")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        n, cnt, best = D.BIG
        tot = D.char_total(n)
        assert round(tot / 1e6) == 12
        x0 = -6.3
        lines = [
            VGroup(MathTex(r"n \le 10^{6}", color=WHITE).scale(0.8)),
            VGroup(T("只枚举奇数：", 24, C_GREY), T("50 万个", 26, C_TEAL)),
            VGroup(T("每个：十进制 ≤ 6 位", 24, C_GREY), T("+", 24, C_GREY), T("二进制 ≤ 20 位", 24, C_GREY)),
            VGroup(T("总共约", 24, C_GREY), MathTex(r"1.2\times10^{7}", color=C_YELLOW).scale(0.8),
                   T(f"个字符（实算 {tot:,}）".replace(",", " "), 22, C_GREY)),
            VGroup(T("线性，Python 来得及", 24, C_GREEN)),
        ]
        keys = [None, "五十万个", "每个数", "一千二百万", "线性"]
        for k, (ln, key) in enumerate(zip(lines, keys)):
            ln.arrange(RIGHT, buff=0.18).move_to([x0, 2.15 - k * 0.55, 0], aligned_edge=LEFT)
            if key:
                self.at(key)
            self.play(FadeIn(ln, shift=RIGHT * 0.15), run_time=0.45)
        assert max(len(str(i)) for i in (999999,)) == 6 and len(D.binstr(999999)) == 20
        self.at("跑满一百万")
        allp = D.double_pals(n)
        assert len(allp) == cnt and allp[-1] == best
        lab = VGroup(T("n = 10⁶：", 22, C_GREY), T(f"共 {cnt} 个", 24, C_YELLOW)).arrange(RIGHT, buff=0.2)
        lab.move_to([x0, -0.65, 0], aligned_edge=LEFT)
        row1 = VGroup(*[M(str(v), 20, "#D8DCE6") for v in allp[:10]]).arrange(RIGHT, buff=0.3)
        row2_items = [M(str(v), 20, C_YELLOW if v == best else "#D8DCE6") for v in allp[10:]]
        row2 = VGroup(*row2_items).arrange(RIGHT, buff=0.3)
        row1.next_to(lab, RIGHT, buff=0.35)
        row2.next_to(row1, DOWN, buff=0.18).align_to(row1, LEFT)
        self.play(FadeIn(lab), FadeIn(row1), FadeIn(row2), run_time=0.8)
        self.at("五十八万")
        bb = D.binstr(best)
        assert len(bb) == 20 and bb == bb[::-1]
        digs = VGroup(*[M(c, 26) for c in bb]).arrange(RIGHT, buff=0.1)
        digs[10:].shift(RIGHT * 0.18)                    # 中轴两侧留出空隙
        digs.move_to([0.7, -2.15, 0])
        tag = VGroup(M(str(best), 26, C_YELLOW), T("=", 24, C_GREY)).arrange(RIGHT, buff=0.18)
        tag.next_to(digs, LEFT, buff=0.25)
        sub2 = M("₂", 18, C_GREY).next_to(digs, RIGHT, buff=0.04).align_to(digs, DOWN)
        self.play(Indicate(row2_items[-1], color=C_YELLOW), FadeIn(tag), FadeIn(digs), FadeIn(sub2), run_time=0.8)
        self.at("二十位")
        axis = DashedLine(digs.get_top() + UP * 0.2, digs.get_bottom() + DOWN * 0.2, color=C_GREY,
                          dash_length=0.08, stroke_width=2).move_to([(digs[9].get_right()[0] + digs[10].get_left()[0]) / 2,
                                                                     digs.get_y(), 0])
        self.play(Create(axis), run_time=0.4)
        pal = [C_BLUE, C_TEAL, C_PURPLE, C_GREEN, C_YELLOW]
        for k in range(10):
            col = pal[k % len(pal)]
            self.play(digs[k].animate.set_color(col), digs[19 - k].animate.set_color(col), run_time=0.18)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        h = T("回顾", 34, C_BLUE).move_to([0, 2.85, 0])
        self.play(FadeIn(h), run_time=0.4)
        items = [
            ("双重回文就是枚举", "枚举 + 两次判回文", WHITE),
            ("字符串写法", "bin(i)[2:]：切掉 0b 前缀", C_RED),
            ("偶数的二进制", "偶数二进制末位是 0 → 只枚举奇数", C_YELLOW),
            ("不转字符串", "y = y * base + t % base：把数倒过来比较", C_TEAL),
            ("最后拿边界", f"边界 n = 1 → 输出 {D.run_io(D.SOLVE, '1' + chr(10))}", C_GREEN),
        ]
        assert D.run_io(D.SOLVE, "1\n") == "1 1"
        rows = VGroup()
        for k, (_, txt, col) in enumerate(items):
            dot = Dot(radius=0.07, color=col)
            t = T(txt, 28, col)
            rows.add(VGroup(dot, t).arrange(RIGHT, buff=0.3))
        rows.arrange(DOWN, buff=0.42, aligned_edge=LEFT).move_to([0, 0.0, 0])
        for (key, _, _), row in zip(items, rows):
            self.at(key)
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.3))
