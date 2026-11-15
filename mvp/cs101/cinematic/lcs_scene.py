"""LCS 与编辑距离：同一张二维表（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。整张表、逐格来源与回溯来自 lcsdata
（test_lcs.py 对撞讲义输出、暴力枚举子序列、字符串空间 BFS 求编辑距离与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcsdata as L  # noqa: E402
from cine import *  # noqa: E402,F403

CW, CH = 0.7, 0.54                      # 格子宽高
TX0, TY0 = 0.9, 2.0                     # (i=0, j=0) 格子中心
OPC = {"diag": C_YELLOW, "up": C_TEAL, "left": C_BLUE,
       "keep": C_YELLOW, "del": C_RED, "ins": C_GREEN, "rep": C_PURPLE}
OPNAME = {"del": "删", "ins": "插", "rep": "改"}


def cpos(i, j):
    return np.array([TX0 + CW * j, TY0 - CH * i, 0])


def letter(ch, size=28, color=WHITE):
    return Text(ch, font=MONO, font_size=size, color=color)


class Table:
    """两串的 dp 表：格子、表头字母、值。"""

    def __init__(self, s, t):
        self.s, self.t = s, t
        self.cells = {(i, j): Rectangle(width=CW * 0.94, height=CH * 0.9, stroke_color=C_GREY, stroke_width=1.5)
                      .move_to(cpos(i, j)) for i in range(len(s) + 1) for j in range(len(t) + 1)}
        self.top = VGroup(*[letter(c).move_to(cpos(0, j + 1) + UP * 0.55) for j, c in enumerate(t)])
        self.left = VGroup(*[letter(c).move_to(cpos(i + 1, 0) + LEFT * 0.6) for i, c in enumerate(s)])
        self.vals = {}

    def grid(self):
        return VGroup(*self.cells.values())

    def val(self, i, j, v, color=WHITE):
        m = MathTex(str(v), color=color).scale(0.6).move_to(self.cells[(i, j)])
        self.vals[(i, j)] = m
        return m

    def everything(self):
        return VGroup(self.grid(), self.top, self.left, *self.vals.values())


def schematic(labels, colors, center, size=0.9):
    """2×2 小示意：(i-1,j-1) (i-1,j) / (i,j-1) (i,j)，三个方向的箭头指向 (i,j) 并标注。"""
    sq = {}
    for di in (0, 1):
        for dj in (0, 1):
            sq[(di, dj)] = Square(size, stroke_color=C_GREY, stroke_width=2).move_to(
                np.array(center) + np.array([(dj - 0.5) * size * 1.25, (0.5 - di) * size * 1.25, 0]))
    sq[(1, 1)].set_stroke(WHITE, 3)
    target = sq[(1, 1)].get_center()
    arrows, tags = VGroup(), VGroup()
    for key, lab, col, side in zip(((0, 0), (0, 1), (1, 0)), labels, colors, (UL, UP, LEFT)):
        a = Arrow(sq[key].get_center(), target, buff=size * 0.32, color=col, stroke_width=4,
                  max_tip_length_to_length_ratio=0.3)
        arrows.add(a)
        tags.add(T(lab, 20, col).next_to(sq[key], side, buff=0.12))
    ij = MathTex("(i,j)", color=WHITE).scale(0.5).move_to(target)
    return VGroup(VGroup(*sq.values()), arrows, tags, ij)


class LCSLesson(Lesson):
    def construct(self):
        for b in ("title", "define", "rule", "fill", "back", "edit", "edfill", "align", "same", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：两个串、一条对应线
    def title_beat(self):
        self.beat("title")
        s, t = L.LCS_S, L.LCS_T
        row_s = VGroup(*[letter(c, 40) for c in s]).arrange(RIGHT, buff=0.45).move_to([0, 0.9, 0])
        row_t = VGroup(*[letter(c, 40) for c in t]).arrange(RIGHT, buff=0.45).move_to([0, -0.9, 0])
        self.play(LaggedStart(*[FadeIn(x, shift=DOWN * 0.2) for x in row_s], lag_ratio=0.1),
                  LaggedStart(*[FadeIn(x, shift=UP * 0.2) for x in row_t], lag_ratio=0.1), run_time=1.4)
        _, picks, _ = L.lcs_back()
        links = VGroup(*[Line(row_s[i - 1].get_bottom() + DOWN * 0.08, row_t[j - 1].get_top() + UP * 0.08,
                              stroke_color=C_YELLOW, stroke_width=3) for i, j in picks])
        self.wait_until(self.cue_start("公共子序列", self.now))
        self.play(*[row_s[i - 1].animate.set_color(C_YELLOW) for i, _ in picks],
                  *[row_t[j - 1].animate.set_color(C_YELLOW) for _, j in picks],
                  LaggedStart(*[Create(x) for x in links], lag_ratio=0.25), run_time=1.6)
        self.wait_until(self.cue_start("同一张二维表", self.now))
        title = T("LCS 与编辑距离", 56).move_to([0, 2.7, 0])
        sub = T("同一张二维表", 32, C_BLUE).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(row_s, row_t, links, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 状态与边界
    def define_beat(self):
        self.beat("define")
        tb = Table(L.LCS_S, L.LCS_T)
        self.tb = tb
        demo_s = VGroup(*[letter(c, 34) for c in L.LCS_S]).arrange(RIGHT, buff=0.3).move_to([-4.0, 2.3, 0])
        self.play(FadeIn(demo_s), run_time=0.5)
        pick = [0, 2, 4]                                        # 「a c b」：不连续、顺序不变
        sub = VGroup(*[demo_s[k].copy() for k in pick])
        self.play(*[demo_s[k].animate.set_color(C_YELLOW) for k in pick], run_time=0.5)
        self.play(sub.animate.arrange(RIGHT, buff=0.3).move_to([-4.0, 1.5, 0]).set_color(C_YELLOW), run_time=0.9)
        note = T("不连续，顺序不变", 22, C_GREY).next_to(sub, DOWN, buff=0.2)
        self.play(FadeIn(note), run_time=0.4)
        self.wait_until(self.cue_start("状态是", self.now))
        defn = VGroup(MathTex(r"dp[i][j]", color=C_YELLOW).scale(0.8),
                      T("= 前 i 个 与 前 j 个", 24), T("的最长公共子序列长度", 24))
        defn.arrange(DOWN, buff=0.15, aligned_edge=LEFT).move_to([-4.2, -0.4, 0])
        self.play(FadeOut(VGroup(demo_s, sub, note)), Create(tb.grid()), FadeIn(tb.top), FadeIn(tb.left),
                  Write(defn), run_time=1.6)
        self.wait_until(self.cue_start("边界", self.now))
        zeros = [tb.val(0, j, 0, C_GREY) for j in range(len(L.LCS_T) + 1)]
        zeros += [tb.val(i, 0, 0, C_GREY) for i in range(1, len(L.LCS_S) + 1)]
        self.play(LaggedStart(*[FadeIn(z) for z in zeros], lag_ratio=0.06), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(defn), run_time=0.6)

    # ---------------------------------------------------------------- 转移：三个方向
    def rule_beat(self):
        self.beat("rule")
        eq = MathTex(r"dp[i][j]=\begin{cases}dp[i-1][j-1]+1 & s_i=t_j\\"
                     r"\max(dp[i-1][j],\ dp[i][j-1]) & s_i\neq t_j\end{cases}").scale(0.55)
        eq.move_to([-3.85, 2.2, 0])
        self.play(Write(eq), run_time=1.6)
        sch = schematic(("两串都退一步", "只动第一个串", "只动第二个串"), (C_YELLOW, C_TEAL, C_BLUE), (-3.9, -0.5, 0))
        self.wait_until(self.cue_start("相同，就从左上角", self.now))
        self.play(FadeIn(sch[0]), FadeIn(sch[3]), GrowArrow(sch[1][0]), run_time=0.9)
        self.wait_until(self.cue_start("不相同", self.now))
        self.play(GrowArrow(sch[1][1]), GrowArrow(sch[1][2]), run_time=0.9)
        self.wait_until(self.cue_start("左上角是", self.now))
        for k in range(3):
            self.play(FadeIn(sch[2][k], shift=RIGHT * 0.1), Indicate(sch[1][k], color=WHITE), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(sch), eq.animate.scale(0.85).move_to([-3.85, 2.75, 0]), run_time=0.6)
        self.lcs_eq = eq

    # ---------------------------------------------------------------- 逐格填表
    def fill_beat(self):
        self.beat("fill")
        tb = self.tb
        dp, log = L.lcs_table()
        legend = VGroup(VGroup(Square(0.25, stroke_color=C_YELLOW, stroke_width=3), T("相同：左上 + 1", 22, C_YELLOW))
                        .arrange(RIGHT, buff=0.2),
                        VGroup(Square(0.25, stroke_color=C_TEAL, stroke_width=3), T("不同：抄上/左较大", 22, C_TEAL))
                        .arrange(RIGHT, buff=0.2)).arrange(DOWN, buff=0.2, aligned_edge=LEFT).move_to([-4.0, 1.2, 0])
        self.play(FadeIn(legend), run_time=0.5)
        end = self.cue_start("右下角", self.now + 10)
        step = max(0.22, min(0.5, (end - self.now - 0.4) / len(log)))
        prev = []
        for i, j, src, v in log:
            a = {"diag": (i - 1, j - 1), "up": (i - 1, j), "left": (i, j - 1)}[src]
            col = OPC[src]
            arr = Arrow(tb.cells[a].get_center(), tb.cells[(i, j)].get_center(), buff=0.12, color=col,
                        stroke_width=3, max_tip_length_to_length_ratio=0.35)
            anims = [GrowArrow(arr), FadeIn(tb.val(i, j, v, C_YELLOW if src == "diag" else WHITE), scale=1.3),
                     tb.left[i - 1].animate.set_color(C_YELLOW if src == "diag" else WHITE),
                     tb.top[j - 1].animate.set_color(C_YELLOW if src == "diag" else WHITE)]
            if src == "diag":
                anims.append(tb.cells[(i, j)].animate.set_stroke(C_YELLOW, 3))
            anims += [FadeOut(x) for x in prev]
            self.play(*anims, run_time=step)
            prev = [arr]
        self.play(*[FadeOut(x) for x in prev], *[m.animate.set_color(WHITE) for m in (*tb.top, *tb.left)], run_time=0.3)
        self.wait_until(self.cue_start("右下角", self.now))
        ans = VGroup(T("答案", 26), MathTex(str(dp[-1][-1]), color=C_YELLOW).scale(1.1)).arrange(RIGHT, buff=0.25)
        ans.move_to([-4.0, -0.6, 0])
        self.play(Circumscribe(tb.cells[(len(L.LCS_S), len(L.LCS_T))], color=C_YELLOW), FadeIn(ans), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        self.legend, self.lcs_ans = legend, ans

    # ---------------------------------------------------------------- 回溯
    def back_beat(self):
        self.beat("back")
        tb = self.tb
        path, picks, sub = L.lcs_back()
        self.play(FadeOut(self.legend), run_time=0.4)
        ring = SurroundingRectangle(tb.cells[path[0]], color=WHITE, buff=0.03, stroke_width=4)
        self.play(Create(ring), run_time=0.4)
        trail = VMobject(stroke_color=C_YELLOW, stroke_width=4).set_points_as_corners(
            [tb.cells[p].get_center() for p in path])
        got = VGroup()
        slots = [np.array([-5.0 + 0.6 * k, 1.0, 0]) for k in range(len(picks))]
        head = T("记下的字符（倒着读）", 22, C_GREY).move_to([-4.1, 1.7, 0])
        self.play(FadeIn(head), run_time=0.4)
        step = max(0.45, min(0.9, (self.left() - 3.0) / len(path)))
        k = len(picks) - 1
        for a, b in zip(path, path[1:]):
            anims = [ring.animate.move_to(tb.cells[b])]
            if a in picks:
                i, j = a
                ch = letter(L.LCS_S[i - 1], 34, C_YELLOW).move_to(slots[k])
                k -= 1
                got.add(ch)
                anims += [TransformFromCopy(tb.left[i - 1], ch), tb.left[i - 1].animate.set_color(C_YELLOW),
                          tb.top[j - 1].animate.set_color(C_YELLOW), Flash(tb.cells[a], color=C_YELLOW, flash_radius=0.4)]
            self.play(*anims, run_time=step)
        self.play(Create(trail), run_time=1.0)
        res = VGroup(T("公共子序列", 24), letter(sub, 34, C_YELLOW), MathTex(rf"=\ {len(sub)}", color=C_YELLOW).scale(0.8))
        res.arrange(RIGHT, buff=0.25).move_to([-4.0, -0.6, 0])
        self.play(ReplacementTransform(self.lcs_ans, res), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tb.everything(), ring, trail, got, head, res, self.lcs_eq)), run_time=0.6)

    # ---------------------------------------------------------------- 编辑距离：边界
    def edit_beat(self):
        self.beat("edit")
        tb = Table(L.ED_S, L.ED_T)
        self.et = tb
        q = VGroup(letter("horse", 40), MathTex(r"\to"), letter("ros", 40)).arrange(RIGHT, buff=0.35).move_to([-3.9, 2.4, 0])
        ops = T("插入 · 删除 · 替换，最少几次？", 24, C_GREY).next_to(q, DOWN, buff=0.25)
        self.play(FadeIn(q), FadeIn(ops), run_time=0.8)
        self.play(Create(tb.grid()), FadeIn(tb.top), FadeIn(tb.left), run_time=1.0)
        self.wait_until(self.cue_start("第一列是 i", self.now))
        col = [tb.val(i, 0, i, C_RED) for i in range(len(L.ED_S) + 1)]
        self.play(LaggedStart(*[FadeIn(x) for x in col], lag_ratio=0.12), run_time=1.0)
        lab1 = T("删光", 22, C_RED).next_to(tb.cells[(len(L.ED_S), 0)], DOWN, buff=0.15)
        self.play(FadeIn(lab1), run_time=0.4)
        self.wait_until(self.cue_start("第一行是 j", self.now))
        row = [tb.val(0, j, j, C_GREEN) for j in range(1, len(L.ED_T) + 1)]
        lab2 = T("全插入", 22, C_GREEN).next_to(tb.cells[(0, len(L.ED_T))], RIGHT, buff=0.2)
        self.play(LaggedStart(*[FadeIn(x) for x in row], lag_ratio=0.15), FadeIn(lab2), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(ops), q.animate.scale(0.75).move_to([-3.9, 2.9, 0]), run_time=0.6)
        self.ed_q, self.ed_labs = q, VGroup(lab1, lab2)

    # ---------------------------------------------------------------- 编辑距离：填表
    def edfill_beat(self):
        self.beat("edfill")
        tb = self.et
        dp, log = L.ed_table()
        sch = schematic(("改", "删", "插"), (C_PURPLE, C_RED, C_GREEN), (-3.9, 0.6, 0), size=0.8)
        eq = VGroup(MathTex(r"s_i\neq t_j:").scale(0.6), T("1 + min(上, 左, 左上)", 22)).arrange(RIGHT, buff=0.2)
        eq.move_to([-3.9, -1.2, 0])
        keep = T("末字符相同：抄左上角，不加一", 22, C_YELLOW).move_to([-3.9, -1.75, 0])
        self.play(FadeIn(keep), run_time=0.5)
        self.wait_until(self.cue_start("不相同", self.now))
        self.play(FadeIn(sch), Write(eq), run_time=1.2)
        end = self.cue_start("右下角", self.now + 6)
        step = max(0.3, min(0.6, (end - self.now - 0.4) / len(log)))
        prev = []
        for i, j, src, v in log:
            a = {"keep": (i - 1, j - 1), "rep": (i - 1, j - 1), "del": (i - 1, j), "ins": (i, j - 1)}[src]
            col = OPC[src]
            arr = Arrow(tb.cells[a].get_center(), tb.cells[(i, j)].get_center(), buff=0.12, color=col,
                        stroke_width=3, max_tip_length_to_length_ratio=0.35)
            anims = [GrowArrow(arr), FadeIn(tb.val(i, j, v, C_YELLOW if src == "keep" else WHITE), scale=1.3)]
            if src == "keep":
                anims.append(tb.cells[(i, j)].animate.set_stroke(C_YELLOW, 3))
            anims += [FadeOut(x) for x in prev]
            self.play(*anims, run_time=step)
            prev = [arr]
        self.play(*[FadeOut(x) for x in prev], run_time=0.3)
        self.wait_until(self.cue_start("右下角", self.now))
        ans = VGroup(T("最少", 24), MathTex(str(dp[-1][-1]), color=C_YELLOW).scale(1.1), T("步", 24)).arrange(RIGHT, buff=0.2)
        ans.next_to(tb.cells[(len(L.ED_S), len(L.ED_T))], RIGHT, buff=0.4)
        self.play(Circumscribe(tb.cells[(len(L.ED_S), len(L.ED_T))], color=C_YELLOW), FadeIn(ans), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(sch, eq, keep)), run_time=0.6)
        self.ed_ans = ans

    # ---------------------------------------------------------------- 倒推出三步操作
    def align_beat(self):
        self.beat("align")
        tb = self.et
        path, ops, steps = L.ed_back()
        ring = SurroundingRectangle(tb.cells[path[0]], color=WHITE, buff=0.03, stroke_width=4)
        trail = VMobject(stroke_color=C_YELLOW, stroke_width=4).set_points_as_corners(
            [tb.cells[p].get_center() for p in path])
        self.play(Create(ring), run_time=0.3)
        self.play(Create(trail), MoveAlongPath(ring, trail.copy()), run_time=1.6)
        words = [letter(steps[0], 36)]
        words[0].move_to([-4.6, 1.8, 0])
        self.play(FadeIn(words[0]), run_time=0.4)
        keys = ("先把 h", "再删掉", "最后删掉")
        for k, ((kind, pos, a, b), nxt) in enumerate(zip(ops, steps[1:])):
            self.wait_until(self.cue_start(keys[k], self.now))
            w = letter(nxt, 36).move_to([-4.6, 1.8 - 1.0 * (k + 1), 0]).align_to(words[0], LEFT)
            desc = f"{OPNAME[kind]} {a}" + (f" → {b}" if kind == "rep" else "")
            tag = T(desc, 22, OPC[kind]).next_to(w, RIGHT, buff=0.5)
            arrow = Arrow(words[-1].get_bottom(), w.get_top(), buff=0.08, color=OPC[kind], stroke_width=3,
                          max_tip_length_to_length_ratio=0.25)
            self.play(GrowArrow(arrow), TransformFromCopy(words[-1], w), FadeIn(tag, shift=LEFT * 0.2), run_time=1.0)
            words += [arrow, tag, w]
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tb.everything(), ring, trail, *words, self.ed_q, self.ed_labs, self.ed_ans)),
                  run_time=0.6)

    # ---------------------------------------------------------------- 同一个框架
    def same_beat(self):
        self.beat("same")
        left = VGroup(T("最长公共子序列", 28, C_BLUE),
                      MathTex(r"s_i=t_j:\ dp[i-1][j-1]+1", color=C_YELLOW).scale(0.6),
                      VGroup(MathTex(r"s_i\neq t_j:").scale(0.6), T("max(上, 左)", 22)).arrange(RIGHT, buff=0.2),
                      ).arrange(DOWN, buff=0.3)
        right = VGroup(T("编辑距离", 28, C_PURPLE),
                       MathTex(r"s_i=t_j:\ dp[i-1][j-1]", color=C_YELLOW).scale(0.6),
                       VGroup(MathTex(r"s_i\neq t_j:").scale(0.6), T("1 + min(上, 左, 左上)", 22)).arrange(RIGHT, buff=0.2),
                       ).arrange(DOWN, buff=0.3)
        cards = VGroup()
        for g, col in ((left, C_BLUE), (right, C_PURPLE)):
            box = RoundedRectangle(corner_radius=0.18, width=5.6, height=2.4, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06).move_to(g)
            cards.add(VGroup(box, g))
        cards.arrange(RIGHT, buff=0.6).move_to([0, 1.3, 0])
        self.play(FadeIn(cards[0], shift=RIGHT * 0.3), FadeIn(cards[1], shift=LEFT * 0.3), run_time=1.2)
        common = T("dp[i][j] 定义在两个前缀上 · 末字符相同 / 不同 两种转移", 24, C_YELLOW).move_to([0, -0.6, 0])
        self.wait_until(self.cue_start("同一个框架", self.now) + 1.5)
        self.play(FadeIn(common, shift=UP * 0.2), Indicate(left[1], color=C_YELLOW), Indicate(right[1], color=C_YELLOW),
                  run_time=1.2)
        self.wait_until(self.cue_start("intention", self.now))
        ex = VGroup(letter("intention", 32), MathTex(r"\to"), letter("execution", 32), T("：", 28),
                    MathTex(str(L.edit_distance("intention", "execution")), color=C_YELLOW).scale(1.0), T("步", 26))
        ex.arrange(RIGHT, buff=0.25).move_to([0, -1.7, 0])
        self.play(FadeIn(ex, shift=UP * 0.2), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cards, common, ex)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        sch = schematic(("左上", "上", "左"), (C_YELLOW, C_TEAL, C_BLUE), (0, 0.6, 0), size=1.2)
        self.play(FadeIn(sch[0]), FadeIn(sch[3]), run_time=0.6)
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(t)) for a, t in zip(sch[1], sch[2])],
                              lag_ratio=0.4), run_time=1.6)
        key = T("几乎所有双串动态规划，都长这个样子", 30, C_YELLOW).move_to([0, -1.7, 0])
        self.wait_until(self.cue_start("几乎所有", self.now))
        self.play(Write(key), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 11 周 动态规划 P20–P21 · OpenJudge 02806 · LeetCode 72", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
