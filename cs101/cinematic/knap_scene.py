"""0/1 背包：一张表，两个方向（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。dp 表、倒推结果、一维正序/倒序逐格记录来自 knapdata
（test_knap.py 用暴力枚举子集、讲义输出与旁白数字对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knapdata as K  # noqa: E402
from cine import *  # noqa: E402,F403

ICOL = {1: C_BLUE, 2: C_RED, 3: C_GREEN}
CW, CH = 1.25, 0.62                     # 二维表格子宽高
TX0, TY0 = -1.7, 1.55                   # 二维表 (i=0, c=0) 格子中心


def cell_pos(i, c):
    return np.array([TX0 + CW * c, TY0 - CH * i, 0])


def item_card(i, scale=1.0):
    w, v = K.WEIGHTS[i - 1], K.VALUES[i - 1]
    box = RoundedRectangle(corner_radius=0.12, width=2.75 * scale, height=0.62 * scale, stroke_color=ICOL[i],
                           stroke_width=3).set_fill(ICOL[i], 0.12)
    lab = MathTex(rf"\#{i}:\ w={w},\ v={v}", color=WHITE).scale(0.55 * scale).move_to(box)
    return VGroup(box, lab)


class KnapLesson(Lesson):
    def construct(self):
        for b in ("title", "kinds", "state", "fill", "back", "roll", "wrong", "full", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    # ---------------------------------------------------------------- 片头：小偷与背包
    def title_beat(self):
        self.beat("title")
        unit = 0.9
        bag = DashedVMobject(Rectangle(width=4 * unit, height=1.1, stroke_color=C_GREY, stroke_width=3),
                             num_dashes=40).move_to([0, -1.2, 0])
        ticks = VGroup(*[Line([bag.get_left()[0] + unit * k, -1.75, 0], [bag.get_left()[0] + unit * k, -0.65, 0],
                              stroke_color=C_GREY, stroke_width=1, stroke_opacity=0.4) for k in range(1, 4)])
        cap = T("背包容量 4", 24, C_GREY).next_to(bag, DOWN, buff=0.2)
        blocks = {}
        xs = {1: -4.2, 2: 0.0, 3: 4.0}
        for i in (1, 2, 3):
            w, v = K.WEIGHTS[i - 1], K.VALUES[i - 1]
            r = Rectangle(width=w * unit, height=1.0, stroke_color=ICOL[i], stroke_width=3).set_fill(ICOL[i], 0.22)
            lab = VGroup(MathTex(f"w={w}").scale(0.6), MathTex(f"v={v}", color=ICOL[i]).scale(0.6))
            lab.arrange(DOWN, buff=0.08)
            blocks[i] = VGroup(r, lab.next_to(r, DOWN, buff=0.15)).move_to([xs[i], 1.0, 0])
        title = T("0/1 背包", 64).move_to([0, 3.0, 0])
        self.play(Write(title), run_time=1.0)
        self.play(Create(bag), FadeIn(ticks), FadeIn(cap), run_time=0.8)
        self.wait_until(self.cue_start("面前有三件", self.now))
        self.play(LaggedStart(*[FadeIn(blocks[i], shift=DOWN * 0.3) for i in (1, 2, 3)], lag_ratio=0.5), run_time=2.4)
        self.wait_until(self.cue_start("怎么拿最值钱", self.now))
        q = T("？", 60, C_YELLOW).move_to(bag)
        self.play(FadeIn(q, scale=1.6), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(bag, ticks, cap, *blocks.values(), title, q)), run_time=0.6)

    # ---------------------------------------------------------------- 背包三兄弟
    def kinds_beat(self):
        self.beat("kinds")
        head = T("0/1 背包", 40, C_YELLOW).move_to([0, 3.0, 0])
        self.play(FadeIn(head), run_time=0.6)
        rows_def = [("0/1 背包", "每种最多 1 个", "倒序", C_BLUE, "零一背包，每种"),
                    ("完全背包", "每种无限个", "正序", C_GREEN, "完全背包"),
                    ("多重背包", "每种最多 k 个", "二进制拆分 → 0/1", C_PURPLE, "多重背包")]
        rows = VGroup()
        for k, (a, b, c, col, key) in enumerate(rows_def):
            r = VGroup(T(a, 30, col), T(b, 28), T(c, 30, col))
            for m, x in zip(r, (-4.0, -0.4, 3.6)):
                m.move_to([x, 1.4 - 1.0 * k, 0])
            self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(r, shift=UP * 0.2), run_time=0.8)
            rows.add(r)
        self.wait_until(self.cue_start("前两种的差别", self.now))
        box = SurroundingRectangle(VGroup(rows[0][2], rows[1][2]), color=C_YELLOW, buff=0.2)
        self.play(Create(box), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, rows, box)), run_time=0.6)

    # ---------------------------------------------------------------- 状态与转移
    def build_table(self):
        cells, vals = {}, {}
        for i in range(4):
            for c in range(5):
                cells[(i, c)] = Rectangle(width=CW * 0.94, height=CH * 0.9, stroke_color=C_GREY,
                                          stroke_width=1.5).move_to(cell_pos(i, c))
        heads = VGroup(*[MathTex(f"c={c}", color=C_GREY).scale(0.55).move_to(cell_pos(0, c) + UP * 0.6)
                         for c in range(5)])
        rlabs = VGroup()
        for i in range(4):
            col = ICOL.get(i, C_GREY)
            txt = "i=0" if i == 0 else rf"i={i}\ (w={K.WEIGHTS[i - 1]})"
            rlabs.add(MathTex(txt, color=col).scale(0.55).next_to(cells[(i, 0)], LEFT, buff=0.25))
        return cells, vals, heads, rlabs

    def state_beat(self):
        self.beat("state")
        cards = VGroup(*[item_card(i, 0.9) for i in (1, 2, 3)]).arrange(RIGHT, buff=0.4).move_to([0.8, 3.3, 0])
        cells, vals, heads, rlabs = self.build_table()
        self.cells, self.vals, self.cards = cells, vals, cards
        defn = VGroup(MathTex(r"dp[i][c]", color=C_YELLOW).scale(0.75), T("= 只考虑前 i 个物品、容量为 c 时的最大价值", 24))
        defn.arrange(RIGHT, buff=0.2).move_to([0.6, -1.4, 0])
        self.play(FadeIn(cards), Create(VGroup(*cells.values())), FadeIn(heads), FadeIn(rlabs), run_time=1.2)
        self.play(Write(defn), run_time=1.2)
        self.wait_until(self.cue_start("第零行全是零", self.now))
        for c in range(5):
            vals[(0, c)] = MathTex("0", color=C_GREY).scale(0.6).move_to(cells[(0, c)])
        self.play(LaggedStart(*[FadeIn(vals[(0, c)]) for c in range(5)], lag_ratio=0.15), run_time=0.8)
        rule = MathTex(r"dp[i][c]=\max(", r"dp[i-1][c]", ",", r"dp[i-1][c-w_i]+v_i", ")").scale(0.75)
        rule[1].set_color(C_TEAL)
        rule[3].set_color(C_YELLOW)
        rule.move_to([0.6, -2.35, 0])
        self.wait_until(self.cue_start("两个选择", self.now))
        self.play(Write(rule), run_time=1.4)
        tgt = cells[(3, 4)]
        self.wait_until(self.cue_start("不拿第 i 个", self.now))
        # 竖箭头只跨一行，buff 大了只剩一个箭头尖；两个说明都放到表格右侧，别压在格线上
        a1 = Arrow(cells[(2, 4)].get_center(), tgt.get_center(), buff=0.06, color=C_TEAL, stroke_width=4,
                   max_tip_length_to_length_ratio=0.35)
        l1 = T("不拿：抄上面", 20, C_TEAL).next_to(cells[(2, 4)], RIGHT, buff=0.25)
        hl = tgt.copy().set_stroke(WHITE, 3)
        self.play(Create(hl), GrowArrow(a1), FadeIn(l1), Indicate(rule[1]), run_time=1.0)
        self.wait_until(self.cue_start("往左退", self.now))
        a2 = Arrow(cells[(2, 1)].get_center(), tgt.get_center(), buff=0.25, color=C_YELLOW, stroke_width=4)
        l2 = T("拿：左退 w，再加 v", 20, C_YELLOW).next_to(tgt, RIGHT, buff=0.25)
        self.play(GrowArrow(a2), FadeIn(l2), Indicate(rule[3]), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(a1, l1, a2, l2, defn, hl)), run_time=0.6)
        self.rule, self.heads, self.rlabs = rule, heads, rlabs

    # ---------------------------------------------------------------- 逐格填表
    def fill_beat(self):
        self.beat("fill")
        cells, vals = self.cells, self.vals
        log = K.fill_log()
        keys = {1: "第一行", 2: "第二行", 3: "第三行"}
        for i in (1, 2, 3):
            self.wait_until(self.cue_start(keys[i], self.now))
            row = [x for x in log if x[0] == i]
            slow = i == 3
            step = 0.75 if not slow else 0.6
            self.play(Indicate(self.cards[i - 1], color=ICOL[i]), self.rlabs[i].animate.set_color(WHITE), run_time=0.5)
            self.play(self.rlabs[i].animate.set_color(ICOL[i]), run_time=0.2)
            for (_, c, skip, take, res) in row:
                arrows = [Arrow(cells[(i - 1, c)].get_center(), cells[(i, c)].get_center(), buff=0.16,
                                color=C_TEAL, stroke_width=3)]
                if take is not None:
                    w = K.WEIGHTS[i - 1]
                    arrows.append(Arrow(cells[(i - 1, c - w)].get_center(), cells[(i, c)].get_center(), buff=0.22,
                                        color=C_YELLOW, stroke_width=3))
                use_take = take is not None and take > skip
                col = C_YELLOW if use_take else C_TEAL
                v = MathTex(str(res), color=col if res else C_GREY).scale(0.6).move_to(cells[(i, c)])
                vals[(i, c)] = v
                big = slow and c == 4
                if big:
                    cmp = MathTex(rf"\max({skip},\ {take - K.VALUES[i - 1]}+{K.VALUES[i - 1]})={res}",
                                  color=WHITE).scale(0.7).move_to([0.6, -1.4, 0])
                    self.wait_until(self.cue_start("容量四的那一格", self.now))
                    self.play(*[GrowArrow(a) for a in arrows], FadeIn(cmp), run_time=1.4)
                    self.play(FadeIn(v, scale=1.5), Flash(cells[(i, c)], color=C_YELLOW, flash_radius=0.6), run_time=0.8)
                    self.cmp = cmp
                else:
                    self.play(*[GrowArrow(a) for a in arrows], run_time=step * 0.5)
                    self.play(FadeIn(v, scale=1.3), run_time=step * 0.3)
                self.play(*[FadeOut(a) for a in arrows], run_time=step * 0.2 if not big else 0.4)
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 倒推选了哪些
    def back_beat(self):
        self.beat("back")
        cells = self.cells
        ans = VGroup(T("答案", 26), MathTex(str(K.knapsack_2d()[-1][-1]), color=C_YELLOW).scale(1.0))
        ans.arrange(RIGHT, buff=0.25).move_to([5.6, TY0, 0])
        self.play(FadeOut(self.cmp), Circumscribe(cells[(3, 4)], color=C_YELLOW), FadeIn(ans), run_time=1.0)
        self.wait_until(self.cue_start("从右下角往回看", self.now))
        ring = SurroundingRectangle(cells[(3, 4)], color=WHITE, buff=0.04, stroke_width=4)
        self.play(Create(ring), run_time=0.4)
        steps = K.backtrack()
        tags = VGroup()
        for i, c, took in steps:
            up = cells[(i - 1, c)]
            self.play(Indicate(up, color=C_TEAL, scale_factor=1.1), run_time=0.6)
            # 标签左对齐贴在表格右侧：按中心摆时，较长的「没拿第 2 件」会压到表格边线
            if took:
                nc = c - K.WEIGHTS[i - 1]
                tag = T(f"拿第 {i} 件", 22, ICOL[i]).next_to(cells[(i, 4)], RIGHT, buff=0.22)
                self.play(FadeIn(tag), self.cards[i - 1][0].animate.set_stroke(ICOL[i], 6).set_fill(ICOL[i], 0.35),
                          ring.animate.move_to(cells[(i - 1, nc)]), run_time=0.9)
            else:
                tag = T(f"没拿第 {i} 件", 22, C_GREY).next_to(cells[(i, 4)], RIGHT, buff=0.22)
                self.play(FadeIn(tag), self.cards[i - 1].animate.set_opacity(0.35),
                          ring.animate.move_to(cells[(i - 1, c)]), run_time=0.9)
            tags.add(tag)
        self.wait_until(self.cue_start("最后拿的是", self.now))
        sel = K.chosen()
        res = MathTex(" + ".join(str(K.VALUES[i - 1]) for i in sel), "=", str(sum(K.VALUES[i - 1] for i in sel)),
                      color=C_YELLOW).scale(0.8).move_to([0.6, -1.4, 0])
        self.play(Write(res), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*cells.values(), *self.vals.values(), self.heads, self.rlabs, self.rule, ring, tags,
                                 ans, res, self.cards)), run_time=0.6)

    # ---------------------------------------------------------------- 一维滚动：倒序
    def row1d(self, y, label, col):
        cells = VGroup(*[Rectangle(width=1.3, height=0.72, stroke_color=C_GREY, stroke_width=2)
                         .move_to([-2.0 + 1.45 * c, y, 0]) for c in range(5)])
        idx = VGroup(*[MathTex(str(c), color=C_GREY).scale(0.5).next_to(cells[c], UP, buff=0.08) for c in range(5)])
        lab = T(label, 24, col).next_to(cells, LEFT, buff=0.35)
        vals = [MathTex("0", color=C_GREY).scale(0.7).move_to(cells[c]) for c in range(5)]
        return cells, idx, lab, vals

    def run_pass(self, cells, vals, forward, col, step):
        w, v = K.WEIGHTS[0], K.VALUES[0]
        _, log = K.one_pass(w, v, [0] * 5, forward)
        ptr = SurroundingRectangle(cells[log[0][0]], color=WHITE, buff=0.05, stroke_width=4)
        self.play(Create(ptr), run_time=0.3)
        for c, old, src, new in log:
            arc = CurvedArrow(cells[c - w].get_top() + UP * 0.05, cells[c].get_top() + UP * 0.05, angle=-PI / 2.2,
                              color=col, stroke_width=3, tip_length=0.15)
            nv = MathTex(str(new), color=col).scale(0.7).move_to(cells[c])
            self.play(ptr.animate.move_to(cells[c]), Create(arc), Indicate(vals[c - w], color=col), run_time=step * 0.6)
            self.play(Transform(vals[c], nv), FadeOut(arc), run_time=step * 0.4)
        self.play(FadeOut(ptr), run_time=0.3)

    def roll_beat(self):
        self.beat("roll")
        card = item_card(1).move_to([0, 3.2, 0])
        code = Code(code_string="for c in range(cap, w - 1, -1):\n    dp[c] = max(dp[c], dp[c - w] + v)\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 22}).move_to([0, 2.05, 0])
        cells, idx, lab, vals = self.row1d(0.3, "倒序", C_GREEN)
        self.play(FadeIn(card), FadeIn(code), Create(cells), FadeIn(idx), FadeIn(lab), *[FadeIn(x) for x in vals],
                  run_time=1.2)
        self.wait_until(self.cue_start("必须从大到小", self.now))
        self.run_pass(cells, vals, False, C_GREEN, step=1.0)
        self.wait_until(self.cue_start("倒序时", self.now))
        note = T("读到的左边格子还是上一行的值", 24, C_GREEN).next_to(cells, DOWN, buff=0.35)
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.2))
        self.roll = dict(card=card, code=code, top=VGroup(cells, idx, lab, *vals), note=note)

    # ---------------------------------------------------------------- 正序的错误
    def wrong_beat(self):
        self.beat("wrong")
        self.play(FadeOut(self.roll["note"]), run_time=0.4)
        cells, idx, lab, vals = self.row1d(-1.55, "正序", C_RED)
        self.play(Create(cells), FadeIn(idx), FadeIn(lab), *[FadeIn(x) for x in vals], run_time=0.8)
        self.wait_until(self.cue_start("容量一", self.now))
        self.run_pass(cells, vals, True, C_RED, step=max(0.9, min(1.6, (self.left() - 2.0) / 4)))
        twice = T("同一件拿了两次", 24, C_RED).next_to(cells, DOWN, buff=0.3)
        self.play(FadeIn(twice), Indicate(vals[4], color=C_RED, scale_factor=1.4), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(cells, idx, lab, *vals, twice, self.roll["top"], self.roll["code"],
                                 self.roll["card"])), run_time=0.6)

    # ---------------------------------------------------------------- 完全背包
    def full_beat(self):
        self.beat("full")
        left = Code(code_string="for c in range(cap, w - 1, -1):", language="python", formatter_style="monokai",
                    background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 24}).move_to([0, 1.9, 0])
        right = Code(code_string="for c in range(w, cap + 1):", language="python", formatter_style="monokai",
                     background="window", add_line_numbers=False,
                     paragraph_config={"font": MONO, "font_size": 24}).move_to([0, -0.4, 0])
        l1 = VGroup(T("0/1 背包 · 倒序", 28, C_GREEN), MathTex(str(K.knapsack_1d()), color=C_GREEN).scale(0.9))
        l2 = VGroup(T("完全背包 · 正序", 28, C_BLUE), MathTex(str(K.unbounded_knapsack()), color=C_BLUE).scale(0.9))
        for g, code in ((l1, left), (l2, right)):
            g.arrange(RIGHT, buff=0.4).next_to(code, UP, buff=0.25)
        self.play(FadeIn(left), FadeIn(l1), run_time=0.8)
        self.wait_until(self.cue_start("恰好就是完全背包", self.now) + 0.5)
        self.play(FadeIn(right), FadeIn(l2), run_time=0.8)
        self.wait_until(self.cue_start("拿四个", self.cue_start("零一背包是", self.now)))
        unit = 0.75
        blocks = VGroup(*[Rectangle(width=unit, height=0.6, stroke_color=C_BLUE, stroke_width=2).set_fill(C_BLUE, 0.25)
                          for _ in range(4)]).arrange(RIGHT, buff=0.06).move_to([0, -1.9, 0])
        bl = MathTex(r"4\times 1500=6000", color=C_BLUE).scale(0.7).next_to(blocks, RIGHT, buff=0.4)
        self.play(LaggedStart(*[FadeIn(b, shift=DOWN * 0.3) for b in blocks], lag_ratio=0.25), FadeIn(bl), run_time=1.4)
        self.wait_until(self.cue_start("只差", self.now))
        h1 = SurroundingRectangle(left.code_lines[0], color=C_YELLOW, buff=0.05)
        h2 = SurroundingRectangle(right.code_lines[0], color=C_YELLOW, buff=0.05)
        self.play(Create(h1), Create(h2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(left, right, l1, l2, blocks, bl, h1, h2)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = VGroup(
            VGroup(T("不拿", 30, C_TEAL), T("抄上面", 30)).arrange(RIGHT, buff=0.5),
            VGroup(T("拿", 30, C_YELLOW), T("看左上：左退 w，再加 v", 30)).arrange(RIGHT, buff=0.5),
            VGroup(T("倒序", 30, C_GREEN), T("0/1 背包", 30)).arrange(RIGHT, buff=0.5),
            VGroup(T("正序", 30, C_BLUE), T("完全背包", 30)).arrange(RIGHT, buff=0.5),
        ).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to([0, 0.6, 0])
        step = max(0.6, (self.left() - 0.8) / 4)
        for r in rows:
            self.play(FadeIn(r, shift=UP * 0.2), run_time=step * 0.6)
            self.wait(step * 0.4)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 11 周 动态规划 P4–P8 · OpenJudge 23421、02773", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
