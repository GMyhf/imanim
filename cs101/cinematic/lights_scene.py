"""熄灯问题：只枚举第一行（例题精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例、每种第一行推到底的结果、成功的第一行、代价数字都来自 lightsdata
（test_lights.py 对撞样例输出、GF(2) 高斯消元、小盘面整表暴力、插桩回放与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lightsdata as L  # noqa: E402
from cine import *  # noqa: E402,F403

LAMP_ON, LAMP_OFF, CELL_BG, CELL_LINE = C_YELLOW, "#2c3140", "#191d27", "#2e3444"
ALL_LEFT = [sum(L.chase(L.P1, m)[2][-1]) for m in range(64)]     # 第一组样例：64 种第一行各自推到底剩几盏
assert ALL_LEFT.count(0) == 1 and ALL_LEFT.index(0) == L.WIN_MASK


class Board(VGroup):
    """R×C 的灯盘：底格 + 灯 + 光晕 + 按下标记（蓝框）。state 跟着动画同步更新。"""

    def __init__(self, light, cell, center):
        super().__init__()
        self.cell, self.rows, self.cols = cell, len(light), len(light[0])
        self.state = [row[:] for row in light]
        center = np.array(center, dtype=float)
        self.bg, self.lamp, self.glow, self.ring = {}, {}, {}, {}
        for r in range(self.rows):
            for c in range(self.cols):
                pos = center + np.array([(c - (self.cols - 1) / 2) * cell, ((self.rows - 1) / 2 - r) * cell, 0])
                self.bg[r, c] = Square(cell * 0.94, stroke_color=CELL_LINE, stroke_width=1).set_fill(CELL_BG, 1).move_to(pos)
                on = self.state[r][c]
                self.glow[r, c] = Circle(cell * 0.44, stroke_width=0).set_fill(LAMP_ON, 0.22 if on else 0).move_to(pos)
                self.lamp[r, c] = Circle(cell * 0.27, stroke_width=0).set_fill(LAMP_ON if on else LAMP_OFF, 1).move_to(pos)
                self.ring[r, c] = Square(cell * 0.82, stroke_color=C_BLUE, stroke_width=4).move_to(pos).set_stroke(opacity=0)
        self.add(*self.bg.values(), *self.glow.values(), *self.lamp.values(), *self.ring.values())

    def _lamp_anims(self, cells):
        out = []
        for r, c in cells:
            on = self.state[r][c]
            out += [self.lamp[r, c].animate.set_fill(LAMP_ON if on else LAMP_OFF, 1),
                    self.glow[r, c].animate.set_fill(LAMP_ON, 0.22 if on else 0)]
        return out

    def press(self, r, c, mark=True):
        """按 (r, c)：翻转自己和四邻；mark 时留下蓝框（按法表）。返回动画列表。"""
        cells = L.neighbors(r, c, self.rows, self.cols)
        for i, j in cells:
            self.state[i][j] ^= 1
        out = self._lamp_anims(cells)
        if mark:
            out.append(self.ring[r, c].animate.set_stroke(opacity=1))
        return out

    def set_state(self, g):
        self.state = [row[:] for row in g]
        return self._lamp_anims([(r, c) for r in range(self.rows) for c in range(self.cols)])

    def snap(self, g, rings=None):
        """无动画地直接设盘面与蓝框（快进用）。"""
        self.state = [row[:] for row in g]
        for r in range(self.rows):
            for c in range(self.cols):
                on = g[r][c]
                self.lamp[r, c].set_fill(LAMP_ON if on else LAMP_OFF, 1)
                self.glow[r, c].set_fill(LAMP_ON, 0.22 if on else 0)
                self.ring[r, c].set_stroke(opacity=1 if rings and rings[r][c] else 0)

    def clear_rings(self):
        return [x.animate.set_stroke(opacity=0) for x in self.ring.values()]

    def row_box(self, r, color=C_BLUE, buff=0.05):
        return SurroundingRectangle(VGroup(*[self.bg[r, c] for c in range(self.cols)]), color=color, buff=buff,
                                    stroke_width=3)


def bitrow(mask, size=0.42):
    """第一行按法的 6 位二进制：方块 + 数字。"""
    g = VGroup()
    for b in L.bits(mask):
        sq = Square(size, stroke_color=C_BLUE, stroke_width=2).set_fill(C_BLUE if b else BG, 0.35 if b else 1)
        g.add(VGroup(sq, Text(str(b), font=MONO, font_size=22, color=WHITE if b else C_GREY).move_to(sq)))
    return g.arrange(RIGHT, buff=0.06)


def digits(mat, size=22, color=WHITE):
    rows = VGroup(*[Text(" ".join(map(str, row)), font=MONO, font_size=size, color=color) for row in mat])
    return rows.arrange(DOWN, buff=0.12, aligned_edge=LEFT)


class LightsLesson(Lesson):
    def construct(self):
        for b in ("title", "read", "model", "key", "walk", "code", "cost", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def chase_anim(self, board, mask, per=0.28):
        """从当前盘面按第一行 mask 推到底，每次按下一段动画。"""
        _, steps, _ = L.chase(board.state, mask)
        for r, c, _snap in steps:
            self.play(*board.press(r, c), run_time=per)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        b = Board(L.P1, 0.72, (-3.3, 0.25, 0))
        self.play(FadeIn(b, lag_ratio=0.02), run_time=1.2)
        kick = T("例题精讲", 26, C_BLUE).move_to([3.4, 2.5, 0])
        title = T("熄灯问题", 72).next_to(kick, DOWN, buff=0.3)
        sub = Text("OpenJudge 02811", font=MONO, font_size=26, color=C_GREY).next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(kick), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.3)
        self.wait_until(self.cue_start("十亿种", self.now))
        brute = VGroup(T("整张表", 26, C_RED), MathTex(r"2^{30}\approx 10^{9}", color=C_RED).scale(0.85))
        brute.arrange(RIGHT, buff=0.25).move_to([3.4, -0.4, 0])
        self.play(FadeIn(brute, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("六十四种", self.now))
        smart = VGroup(T("第一行", 26, C_GREEN), MathTex(r"2^{6}=64", color=C_GREEN).scale(0.85))
        smart.arrange(RIGHT, buff=0.25).next_to(brute, DOWN, buff=0.4)
        self.play(FadeIn(smart, shift=UP * 0.2), run_time=0.7)
        # 用答案把整盘灯按灭（预告结局）
        press = L.solve(L.P1)
        cells = [(r, c) for r in range(L.R) for c in range(L.C) if press[r][c]]
        per = min(0.22, max(0.08, (self.left() - 1.2) / len(cells)))
        for r, c in cells:
            self.play(*b.press(r, c, mark=False), run_time=per)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 读题
    def read_beat(self):
        self.beat("read")
        blank = [[0] * L.C for _ in range(L.R)]
        b = Board(blank, 0.66, (-3.4, 0.4, 0))
        self.play(FadeIn(b), run_time=0.7)
        legend = VGroup(VGroup(Circle(0.12, stroke_width=0).set_fill(LAMP_ON, 1), T("1 亮", 24)).arrange(RIGHT, buff=0.15),
                        VGroup(Circle(0.12, stroke_width=0).set_fill(LAMP_OFF, 1), T("0 灭", 24)).arrange(RIGHT, buff=0.15))
        legend.arrange(RIGHT, buff=0.5).next_to(b, UP, buff=0.25)
        self.play(FadeIn(legend), run_time=0.5)
        self.wait_until(self.cue_start("按一下", self.now))
        note = T("按一下：自己 + 上下左右 翻转", 28).move_to([3.2, 2.2, 0])
        self.play(FadeIn(note, shift=LEFT * 0.2), *b.press(2, 2), run_time=0.9)
        self.wait(0.5)
        self.play(*b.press(2, 2), run_time=0.7)          # 再按一次：恢复
        self.wait_until(self.cue_start("角上", self.now))
        tags = VGroup()
        for (r, c), n, col in (((0, 0), 3, C_TEAL), ((0, 3), 4, C_PURPLE), ((3, 4), 5, C_YELLOW)):
            self.play(*b.press(r, c), run_time=0.6)
            tag = T(f"{'角' if n == 3 else '边' if n == 4 else '中间'}：{n} 盏", 26, col)
            tags.add(tag)
        tags.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([2.2, 0.9, 0])
        self.play(LaggedStart(*[FadeIn(t, shift=LEFT * 0.2) for t in tags], lag_ratio=0.3), run_time=1.0)
        self.wait_until(self.cue_start("输出", self.now))
        self.play(*b.clear_rings(), *b.set_state(L.P1), FadeOut(tags), run_time=0.8)
        inp = VGroup(T("输入", 24, C_GREY), digits(L.P1)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        out = VGroup(T("输出", 24, C_GREY), T("一张 5×6 的按法表", 26, C_BLUE), T("按完以后灯全灭", 26, C_BLUE))
        out.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        io = VGroup(inp, out).arrange(RIGHT, buff=0.7, aligned_edge=UP).move_to([3.0, -0.2, 0])
        self.play(FadeIn(io, shift=LEFT * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 建模：两个观察
    def model_beat(self):
        self.beat("model")
        h1 = T("① 按两次 = 没按", 30).move_to([-3.6, 2.7, 0])
        self.play(FadeIn(h1, shift=DOWN * 0.2), run_time=0.6)
        lamps = VGroup(*[Circle(0.22, stroke_width=0).set_fill(LAMP_ON if s else LAMP_OFF, 1) for s in (0, 1, 0)])
        lamps.arrange(RIGHT, buff=1.1).move_to([-3.6, 1.75, 0])
        arrows = VGroup(*[Arrow(lamps[i].get_right(), lamps[i + 1].get_left(), buff=0.12, color=C_GREY,
                                stroke_width=3, max_tip_length_to_length_ratio=0.25) for i in range(2)])
        labs = VGroup(*[T("按", 20, C_GREY).next_to(a, UP, buff=0.05) for a in arrows])
        self.play(LaggedStart(*[FadeIn(x) for x in (lamps[0], arrows[0], labs[0], lamps[1], arrows[1], labs[1], lamps[2])],
                              lag_ratio=0.25), run_time=1.6)
        self.wait_until(self.cue_start("顺序", self.now))
        h2 = T("② 先后顺序无关", 30).move_to([-3.6, 0.75, 0])
        self.play(FadeIn(h2, shift=DOWN * 0.2), run_time=0.6)
        minis = VGroup()
        for k, order in enumerate((((0, 0), (1, 1)), ((1, 1), (0, 0)))):
            m = Board([[0] * 3 for _ in range(3)], 0.36, (-5.0 + 2.8 * k, -0.6, 0))
            self.play(FadeIn(m), run_time=0.3)
            minis.add(m)
            for (r, c), col in zip(order, (C_YELLOW, C_PURPLE) if k == 0 else (C_PURPLE, C_YELLOW)):
                m.ring[r, c].set_color(col)
                self.play(*m.press(r, c), run_time=0.45)
        eq = MathTex("=", color=C_GREEN).scale(1.2).move_to([-3.6, -0.6, 0])
        caps = VGroup(T("先黄后紫", 20, C_GREY).next_to(minis[0], DOWN, buff=0.15),
                      T("先紫后黄", 20, C_GREY).next_to(minis[1], DOWN, buff=0.15))
        self.play(FadeIn(eq), FadeIn(caps), run_time=0.6)
        self.wait_until(self.cue_start("零一表", self.now))
        cell = 0.46
        qs = VGroup()
        ans = L.solve(L.P1)
        for r in range(L.R):
            for c in range(L.C):
                sq = Square(cell * 0.94, stroke_color=CELL_LINE, stroke_width=1).set_fill(CELL_BG, 1)
                sq.move_to([3.4 + (c - 2.5) * cell, 1.6 + (2 - r) * cell, 0])
                qs.add(VGroup(sq, Text("?", font=MONO, font_size=20, color=C_GREY).move_to(sq)))
        head = T("答案：5×6 的 0/1 表", 26, C_BLUE).next_to(qs, UP, buff=0.2)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(q) for q in qs], lag_ratio=0.02), run_time=1.0)
        new = [Text(str(ans[i // 6][i % 6]), font=MONO, font_size=20,
                    color=C_BLUE if ans[i // 6][i % 6] else C_GREY).move_to(qs[i][0]) for i in range(30)]
        self.play(*[Transform(qs[i][1], new[i]) for i in range(30)], run_time=0.8)
        self.wait_until(self.cue_start("二的三十次方", self.now))
        cnt = MathTex(r"2^{30} = 1\,073\,741\,824", color=C_RED).scale(0.85).next_to(qs, DOWN, buff=0.35)
        self.play(FadeIn(cnt, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("第四周", self.now))
        rule = VGroup(T("第 4 周：", 24, C_GREY), MathTex(r"O(2^n)", color=WHITE).scale(0.8), T("只适合", 24, C_GREY),
                      MathTex(r"n \le 20", color=WHITE).scale(0.8)).arrange(RIGHT, buff=0.15)
        rule.next_to(cnt, DOWN, buff=0.35)
        bad = MathTex(r"30 > 20", color=C_RED).scale(0.8).next_to(rule, DOWN, buff=0.2)
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        self.play(FadeIn(bad, scale=1.3), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 关键观察：第一行定了，后面被逼出来
    def key_beat(self):
        self.beat("key")
        b = Board(L.P1, 0.66, (-3.4, 0.35, 0))
        self.play(FadeIn(b), run_time=0.7)
        mask = 0b100100                             # 随便假设一种第一行
        box0 = b.row_box(0, C_BLUE)
        t0 = T("假设第一行已经定了", 26, C_BLUE).move_to([2.8, 2.3, 0])
        self.play(Create(box0), FadeIn(t0), run_time=0.7)
        for c, bit in enumerate(L.bits(mask)):
            if bit:
                self.play(*b.press(0, c), run_time=0.45)
        self.wait_until(self.cue_start("谁还能", self.now))
        lit = [c for c in range(L.C) if b.state[0][c]]
        rings = VGroup(*[Circle(0.66 * 0.4, color=C_YELLOW, stroke_width=4).move_to(b.lamp[0, c]) for c in lit])
        self.play(LaggedStart(*[Create(x) for x in rings], lag_ratio=0.2), run_time=0.8)
        self.wait_until(self.cue_start("不能再动", self.now))
        lock = T("第一行的按钮：不能再动", 24, C_GREY).next_to(t0, DOWN, buff=0.3).align_to(t0, LEFT)
        self.play(FadeIn(lock), box0.animate.set_color(C_GREY), run_time=0.6)
        self.wait_until(self.cue_start("正下方", self.now))
        c0 = lit[0]
        assert c0 == 0                              # 箭头从盘面左侧绕出去，要求是最左一列
        tgt = Square(0.66 * 0.94, color=C_YELLOW, stroke_width=5).move_to(b.bg[1, c0])
        arr = CurvedArrow(b.bg[0, c0].get_left() + LEFT * 0.05, b.bg[1, c0].get_left() + LEFT * 0.05,
                          angle=PI * 0.9, color=C_YELLOW, stroke_width=5, tip_length=0.18)
        only = T("只剩正下方这个按钮", 26, C_YELLOW).next_to(lock, DOWN, buff=0.45).align_to(t0, LEFT)
        self.play(Create(arr), Create(tgt), FadeIn(only), run_time=0.9)
        self.wait_until(self.cue_start("就必须按", self.now))
        rule = VGroup(T("上方亮 → 必须按", 26, C_GREEN), T("上方灭 → 必须不按", 26, C_GREY))
        rule.arrange(DOWN, buff=0.2, aligned_edge=LEFT).next_to(only, DOWN, buff=0.45).align_to(t0, LEFT)
        self.play(FadeIn(rule, shift=UP * 0.2), FadeOut(arr), FadeOut(tgt), run_time=0.7)
        self.wait_until(self.cue_start("被逼了出来", self.now))
        _, steps, _ = L.chase(L.P1, mask)
        row1 = [(r, c) for r, c, _s in steps if r == 1]
        self.play(FadeOut(rings), run_time=0.3)
        for r, c in row1:
            self.play(*b.press(r, c), run_time=0.4)
        self.wait_until(self.cue_start("一行一行", self.now))
        rest = [(r, c) for r, c, _s in steps if r >= 2]
        per = min(0.35, max(0.12, (self.cue_start("最后只要", self.now + 3) - self.now - 0.3) / max(1, len(rest))))
        for r, c in rest:
            self.play(*b.press(r, c), run_time=per)
        self.wait_until(self.cue_start("最后只要", self.now))
        box4 = b.row_box(L.R - 1, C_RED)
        chk = T("只要检查：第五行全灭？", 26, C_RED).next_to(rule, DOWN, buff=0.45).align_to(t0, LEFT)
        self.play(Create(box4), FadeIn(chk), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 第一组样例：一种一种试
    def walk_beat(self):
        self.beat("walk")
        b = Board(L.P1, 0.62, (-3.6, 0.45, 0))
        cap = T("样例 1", 24, C_GREY).next_to(b, UP, buff=0.2)
        self.play(FadeIn(b), FadeIn(cap), run_time=0.7)
        lab = T("第一行按法", 24, C_GREY).move_to([1.6, 2.6, 0])
        bits = bitrow(0).next_to(lab, DOWN, buff=0.2).align_to(lab, LEFT)
        cnt = T("第 1 种", 26).next_to(bits, RIGHT, buff=0.45)
        self.play(FadeIn(lab), FadeIn(bits), FadeIn(cnt), run_time=0.6)
        # 直方图：每种第一行推到底后，第五行还亮几盏
        base_y, x0, w = -2.55, 0.9, 0.13
        axis = Line([x0 - 0.05, base_y, 0], [x0 + 42 * w + 0.05, base_y, 0], color=C_GREY, stroke_width=2)
        hlab = T("每种推到底后，第五行还亮几盏", 20, C_GREY).next_to(axis, UP, buff=1.55).align_to(axis, LEFT)
        bars = VGroup()

        def bar(i, left):
            col = C_GREEN if left == 0 else C_RED
            h = max(0.04, left * 0.26)
            return Rectangle(width=w * 0.8, height=h, stroke_width=0).set_fill(col, 0.85).move_to(
                [x0 + (i + 0.5) * w, base_y + h / 2, 0])
        self.wait_until(self.cue_start("全不按", self.now))
        self.play(Create(axis), FadeIn(hlab), run_time=0.5)
        self.chase_anim(b, 0, per=0.26)
        box4 = b.row_box(L.R - 1, C_RED)
        fail = VGroup(T(f"第五行还剩 {L.LEFT0} 盏", 26, C_RED), MathTex(r"\times", color=C_RED)).arrange(RIGHT, buff=0.2)
        fail.next_to(bits, DOWN, buff=0.45).align_to(lab, LEFT)
        bars.add(bar(0, L.LEFT0))
        self.play(Create(box4), FadeIn(fail), FadeIn(bars[0]), run_time=0.6)
        self.wait_until(self.cue_start("加一", self.now))
        self.play(FadeOut(fail), FadeOut(box4), run_time=0.3)
        per = min(0.16, max(0.08, (self.cue_start("第四十二种", self.now + 6) - self.now - 0.4) / (L.N_TRIED - 2)))
        for m, left in L.TRIES1[1:-1]:
            press, _st, g = L.chase(L.P1, m)
            b.snap(g, press)
            bits.become(bitrow(m).move_to(bits))
            cnt.become(T(f"第 {m + 1} 种", 26).move_to(cnt, aligned_edge=LEFT))
            bars.add(bar(m, left))
            self.play(FadeIn(bars[-1]), run_time=per)
        self.wait_until(self.cue_start("第四十二种", self.now))
        b.snap(L.P1)
        bits.become(bitrow(L.WIN_MASK).move_to(bits))
        cnt.become(T(f"第 {L.N_TRIED} 种", 26, C_GREEN).move_to(cnt, aligned_edge=LEFT))
        self.play(Indicate(bits, color=C_GREEN), run_time=0.6)
        self.chase_anim(b, L.WIN_MASK, per=0.22)
        ok = VGroup(T("第五行全灭", 26, C_GREEN), MathTex(r"\checkmark", color=C_GREEN)).arrange(RIGHT, buff=0.2)
        ok.next_to(bits, DOWN, buff=0.45).align_to(lab, LEFT)
        bars.add(bar(L.WIN_MASK, 0))
        self.play(FadeIn(ok), FadeIn(bars[-1]), Flash(b.lamp[L.R - 1, 2], color=C_GREEN), run_time=0.7)
        self.wait_until(self.cue_start("样例输出", self.now))
        self.play(FadeOut(bars), FadeOut(axis), FadeOut(hlab), run_time=0.4)
        want = VGroup(T("样例输出", 24, C_GREY), digits(L.SAMPLE_OUT[0], 24, C_BLUE)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        want.next_to(ok, DOWN, buff=0.45).align_to(lab, LEFT)
        assert L.solve(L.P1) == L.SAMPLE_OUT[0]
        self.play(FadeIn(want, shift=LEFT * 0.2), run_time=0.7)
        self.play(*[Indicate(b.ring[r, c], color=C_BLUE) for r in range(L.R) for c in range(L.C)
                    if L.SAMPLE_OUT[0][r][c]], run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        src = ("def solve(light):\n"
               "    for mask in range(64):\n"
               "        g = [row[:] for row in light]\n"
               "        press = [[0] * 6 for _ in range(5)]\n"
               "        for r in range(5):\n"
               "            for c in range(6):\n"
               "                p = mask >> (5 - c) & 1 if r == 0 else g[r - 1][c]\n"
               "                if p:\n"
               "                    press[r][c] = 1\n"
               "                    flip(g, r, c)\n"
               "        if not any(g[4]):\n"
               "            return press\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 18})
        code.move_to([-2.2, 0.35, 0])
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, col):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.04, stroke_width=2)
            tag = T(txt, 22, col).next_to(code, RIGHT, buff=0.25).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
        mark([1], "外层循环", "第一行：64 种", C_YELLOW)
        mark([6], "第一行看", "第一行看枚举位\n其余看正上方", C_BLUE)
        mark([8, 9], "记下来", "记下，翻转五格", C_GREEN)
        mark([10, 11], "最后一行全灭", "最后一行全灭", C_RED)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 代价与唯一性
    def cost_beat(self):
        self.beat("cost")
        l1 = VGroup(T("只枚举第一行", 28, C_GREEN), MathTex(r"64 \times 30 = 1\,920", color=C_GREEN).scale(0.9),
                    T("次", 28, C_GREEN)).arrange(RIGHT, buff=0.25)
        l2 = VGroup(T("直接枚举整张表", 28, C_RED), MathTex(r"2^{30} = 1\,073\,741\,824", color=C_RED).scale(0.9),
                    T("种", 28, C_RED)).arrange(RIGHT, buff=0.25)
        rows = VGroup(l1, l2).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to([0, 2.2, 0])
        self.play(FadeIn(l1, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("快了", self.now))
        self.play(FadeIn(l2, shift=UP * 0.2), run_time=0.7)
        fast = VGroup(MathTex(r"2^{30} / 2^{6} = 2^{24} = 16\,777\,216", color=C_YELLOW).scale(0.85), T("倍", 26, C_YELLOW))
        fast.arrange(RIGHT, buff=0.2).next_to(rows, DOWN, buff=0.4)
        assert L.SPEEDUP == 16777216
        self.play(FadeIn(fast, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("还可以验证", self.now))
        size = 0.36
        grid = VGroup()
        for m in range(64):
            left = ALL_LEFT[m]
            sq = Square(size, stroke_color=CELL_LINE, stroke_width=1).set_fill(
                C_GREEN if left == 0 else interpolate_color(ManimColor(CELL_BG), ManimColor(C_RED), 0.15 + 0.12 * left), 1)
            grid.add(sq)
        grid.arrange_in_grid(4, 16, buff=0.06).move_to([0, -1.25, 0])
        cap = T("样例 1 的 64 种第一行：颜色越红，第五行剩得越多", 20, C_GREY).next_to(grid, UP, buff=0.2)
        self.play(FadeIn(cap), LaggedStart(*[FadeIn(s, scale=0.5) for s in grid], lag_ratio=0.02), run_time=1.6)
        self.wait_until(self.cue_start("恰好只有一种", self.now))
        win = grid[L.WIN_MASK]
        hl = SurroundingRectangle(win, color=C_GREEN, buff=0.04, stroke_width=4)
        one = T("恰好一种 → 答案唯一", 24, C_GREEN).next_to(grid, DOWN, buff=0.2)
        self.play(Create(hl), FadeIn(one), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾 + 同类题
    def recap_beat(self):
        self.beat("recap")
        steps = [("读题", "按一下 = 翻转自己 + 四个邻居", C_BLUE, None),
                 ("建模", "按两次 = 不按，顺序无关 → 0/1 表", C_YELLOW, "建模"),
                 ("关键", "第一行定了，后面每行被逼出来", C_GREEN, "关键观察")]
        rows = VGroup()
        for name, txt, col, _k in steps:
            rows.add(VGroup(T(name, 30, col), T(txt, 28)).arrange(RIGHT, buff=0.45))
        rows.arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 1.7, 0])
        for row, (_n, _t, _c, key) in zip(rows, steps):
            if key:
                self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(row, shift=UP * 0.2), run_time=0.7)
        drop = MathTex(r"2^{30}\ \longrightarrow\ 2^{6}", color=C_GREEN).scale(1.0).next_to(rows, DOWN, buff=0.4)
        self.wait_until(self.cue_start("降到", self.now))
        self.play(FadeIn(drop, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("同类题", self.now))
        sim = VGroup(T("同类题", 24, C_GREY), T("画家问题  OpenJudge 02813", 28, C_PURPLE),
                     T("同一思路 · 求最少次数 · 可能无解", 22, C_GREY)).arrange(DOWN, buff=0.15)
        sim.next_to(drop, DOWN, buff=0.45)
        self.play(FadeIn(sim, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 例题精讲 · OpenJudge 02811 熄灯问题（每日选作 11-02）", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
