"""背包的三个变形：拆捆、装满、多一维（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。二进制拆分与可达集合、两种初值的逐件整行、Coins 的布尔行、
宠物小精灵的结果与方案、分数背包切分、0/1 贪心反例都来自 knapvardata（test_knapvar.py 用穷举与讲义输出对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knapvardata as K  # noqa: E402
from cine import *  # noqa: E402,F403

NEG = float("-inf")
PART_COL = [C_TEAL, C_YELLOW, C_RED, C_PURPLE]          # 二进制拆分的各捆


def num(x, size=0.68, color=WHITE):
    s = r"-\infty" if x == NEG else str(x)
    return MathTex(s, color=C_GREY if x == NEG else color).scale(size)


def code(src, size=20):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


class KnapVarLesson(Lesson):
    def construct(self):
        for b in ("title", "split", "why", "exact", "trap", "coins", "twodim", "frac", "greedy", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def close(self, *mobs):
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*mobs)), run_time=0.6)

    # ---------------------------------------------------------------- 片头：四张卡片
    def title_beat(self):
        self.beat("title")
        title = T("背包的三个变形", 60).move_to([0, 2.5, 0])
        sub = T("接着 0/1 背包与完全背包", 26, C_GREY).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(sub), run_time=1.2)
        defs = [("数量有限", "二进制拆分", C_BLUE, "数量有限"), ("必须装满", "初值 −∞", C_GREEN, "必须装满"),
                ("费用两种", "状态多一维", C_PURPLE, "费用两种"), ("能切开", "贪心", C_YELLOW, "能切开")]
        cards = VGroup()
        for k, (a, b, col, _) in enumerate(defs):
            box = RoundedRectangle(corner_radius=0.15, width=2.8, height=1.7, stroke_color=col,
                                   stroke_width=3).set_fill(col, 0.1)
            if k == 3:
                box = DashedVMobject(box, num_dashes=36)
            g = VGroup(T(a, 32, col), T(b, 24)).arrange(DOWN, buff=0.25)
            cards.add(VGroup(box, g.move_to(box)))
        cards.arrange(RIGHT, buff=0.35).move_to([0, -0.5, 0])
        for card, d in zip(cards, defs):
            self.at(d[3])
            self.play(FadeIn(card, shift=UP * 0.25), run_time=0.6)
        self.close(title, sub, cards)

    # ---------------------------------------------------------------- 多重背包：13 个拆成 4 捆
    def split_beat(self):
        self.beat("split")
        k = K.SPLIT_K
        parts = K.binary_split(k)
        head = T(f"多重背包：这种物品有 {k} 个", 34).move_to([0, 3.2, 0])
        self.play(FadeIn(head), run_time=0.6)
        s = 0.55
        sq = VGroup(*[Square(s, stroke_color=C_BLUE, stroke_width=2).set_fill(C_BLUE, 0.3)
                      for _ in range(k)]).arrange(RIGHT, buff=0.08).move_to([0, 2.0, 0])
        self.at("朴素做法")
        naive = T(f"朴素：{k} 件单品，各做一遍 0/1 背包", 24, C_GREY).next_to(sq, DOWN, buff=0.35)
        self.play(LaggedStart(*[FadeIn(x, shift=DOWN * 0.2) for x in sq], lag_ratio=0.08), FadeIn(naive),
                  run_time=1.4)
        self.at("二进制拆分")
        gap, cell = 0.55, s + 0.08
        width = k * cell - 0.08 + gap * (len(parts) - 1)
        x, idx, anims, groups = -width / 2 + s / 2, 0, [], []
        for g, p in enumerate(parts):
            grp = []
            for _ in range(p):
                anims.append(sq[idx].animate.move_to([x, 2.0, 0]).set_fill(PART_COL[g], 0.35)
                             .set_stroke(PART_COL[g]))
                grp.append(sq[idx])
                x += cell
                idx += 1
            x += gap
            groups.append(grp)
        self.play(*anims, FadeOut(naive), run_time=1.4)
        braces, labs = VGroup(), VGroup()
        for g, grp in enumerate(groups):
            br = Brace(VGroup(*grp), DOWN, buff=0.12, color=PART_COL[g])
            braces.add(br)
            labs.add(MathTex(str(parts[g]), color=PART_COL[g]).scale(0.75).next_to(br, DOWN, buff=0.1))
        self.at("十三拆成")
        note = T(f"{len(parts)} 捆，每捆当一件 0/1 物品", 26).move_to([0, 0.15, 0])
        self.play(LaggedStart(*[AnimationGroup(GrowFromCenter(b), FadeIn(l)) for b, l in zip(braces, labs)],
                              lag_ratio=0.3), run_time=1.4)
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.6)
        self.at("五拆成")
        cap = T("讲义里的例子", 22, C_GREY).move_to([0, -0.85, 0])
        ex = VGroup()
        for kk in K.SPLIT_KS:
            ex.add(MathTex(rf"{kk}\ \to\ " + r",\,".join(map(str, K.binary_split(kk))),
                           color=C_YELLOW if kk == k else WHITE).scale(0.75))
        ex.arrange(RIGHT, buff=0.5).move_to([0, -1.6, 0])
        self.play(FadeIn(cap), LaggedStart(*[FadeIn(e, shift=UP * 0.2) for e in ex], lag_ratio=0.25), run_time=1.6)
        self.close(head, sq, braces, labs, note, cap, ex)

    # ---------------------------------------------------------------- 为什么能凑出 0..k
    def why_beat(self):
        self.beat("why")
        k = K.SPLIT_K
        parts = K.binary_split(k)
        steps = K.reach_steps(k)
        head = T(f"四捆为什么能凑出 0 到 {k}", 34).move_to([0, 3.35, 0])
        cw, x0 = 0.66, -3.3
        ys = [2.0, 1.22, 0.44, -0.34, -1.12]

        def cx(c):
            return x0 + cw * c
        idx = VGroup(*[MathTex(str(c), color=C_GREY).scale(0.5).move_to([cx(c), 2.62, 0]) for c in range(k + 1)])
        frames = VGroup(*[VGroup(*[Square(cw * 0.9, stroke_color=C_GREY, stroke_width=1, stroke_opacity=0.35)
                                   .move_to([cx(c), y, 0]) for c in range(k + 1)]) for y in ys])
        names = ["起点"] + [f"+{p}" for p in parts]
        rl = VGroup(*[T(n, 24, C_GREY if r == 0 else PART_COL[r - 1]).move_to([x0 - 1.0, y, 0])
                      for r, (n, y) in enumerate(zip(names, ys))])
        self.play(FadeIn(head), FadeIn(idx), FadeIn(frames), FadeIn(rl[0]), run_time=1.0)

        def block(cols, y, col):
            return VGroup(*[Square(cw * 0.9, stroke_width=0).set_fill(col, 0.5).move_to([cx(c), y, 0]) for c in cols])
        rows = [block(steps[0], ys[0], C_GREY)]
        self.play(FadeIn(rows[0]), run_time=0.5)
        self.at("像二进制")
        bit = T("每捆只有 拿 / 不拿：像二进制的一位", 24, C_BLUE).move_to([1.0, -1.85, 0])
        self.play(FadeIn(bit), run_time=0.6)
        keys = ["加上一", "加上二", "加上四", "最后一捆"]
        spans = VGroup()
        for r, p in enumerate(parts, start=1):
            self.at(keys[r - 1])
            prev = steps[r - 1]
            keep = block(prev, ys[r], C_GREY)
            shift = block([c + p for c in prev], ys[r], PART_COL[r - 1])
            span = MathTex(rf"0..{steps[r][-1]}", color=PART_COL[r - 1]).scale(0.7).move_to([cx(k) + 1.05, ys[r], 0])
            spans.add(span)
            rt = 1.6 if r == len(parts) else 1.0
            self.play(FadeIn(rl[r]), TransformFromCopy(rows[-1], keep), run_time=rt * 0.5)
            self.play(TransformFromCopy(rows[-1], shift), FadeIn(span), run_time=rt)
            rows.append(VGroup(keep, shift))
        last = rows[-1][1]
        ring = SurroundingRectangle(VGroup(last[0], last[1]), color=WHITE, buff=0.04, stroke_width=3)
        self.play(Create(ring), run_time=0.5)
        self.at("余数")
        rest = parts[-1]
        bound = MathTex(rf"{rest}\ \le\ " + "+".join(map(str, parts[:-1])) + r"\ +\ 1", color=C_YELLOW).scale(0.75)
        tail = T("余数不超过前面总和加一 → 不断档", 24, C_YELLOW)
        VGroup(bound, tail).arrange(RIGHT, buff=0.4).move_to([1.0, -2.6, 0])
        self.play(FadeIn(bound), FadeIn(tail), run_time=0.8)
        self.close(head, idx, frames, rl, *rows, spans, bit, ring, bound, tail)

    # ---------------------------------------------------------------- 恰好装满：同一组数据跑两遍
    def exact_row(self, y, cap):
        cells = VGroup(*[Rectangle(width=1.05, height=0.7, stroke_color=C_GREY, stroke_width=2)
                         .move_to([-2.0 + 1.25 * c, y, 0]) for c in range(cap + 1)])
        idx = VGroup(*[MathTex(str(c), color=C_GREY).scale(0.5).next_to(cells[c], UP, buff=0.08)
                       for c in range(cap + 1)])
        return cells, idx

    def exact_beat(self):
        self.beat("exact")
        ws, vs, cap = K.EX_W, K.EX_V, K.EX_CAP
        loose = K.fill_rows(ws, vs, cap, exact=False)
        tight = K.fill_rows(ws, vs, cap, exact=True)
        head = T("恰好装满", 36, C_GREEN).move_to([-5.0, 3.3, 0])
        self.play(FadeIn(head), run_time=0.5)
        self.at("体积二价值十")
        cards = VGroup()
        for w, v in zip(ws, vs):
            box = RoundedRectangle(corner_radius=0.12, width=2.4, height=0.6, stroke_color=C_BLUE,
                                   stroke_width=2.5).set_fill(C_BLUE, 0.12)
            cards.add(VGroup(box, MathTex(rf"w={w},\ v={v}").scale(0.6).move_to(box)))
        cards.add(T(f"容量 {cap}", 26, C_GREY))
        cards.arrange(RIGHT, buff=0.4).move_to([1.6, 3.3, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.2) for c in cards], lag_ratio=0.3), run_time=1.2)
        ya, yb = 1.4, -1.0
        ca, ia = self.exact_row(ya, cap)
        cb, ib = self.exact_row(yb, cap)
        la = VGroup(T("不超过", 30, C_TEAL), Text("dp = [0] * (C+1)", font=MONO, font_size=20, color=C_GREY))
        lb = VGroup(T("恰好", 30, C_GREEN), Text("dp = [-inf] * (C+1)", font=MONO, font_size=20, color=C_GREY),
                    Text("dp[0] = 0", font=MONO, font_size=20, color=C_GREY))
        for g, y in ((la, ya), (lb, yb)):
            g.arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to([-5.1, y, 0])
        self.at("不超过型全填零")
        va = [num(x).move_to(ca[c]) for c, x in enumerate(loose[0])]
        self.play(FadeIn(la), Create(ca), FadeIn(ia), *[FadeIn(x) for x in va], run_time=1.0)
        self.at("恰好型只有")
        vb = [num(x).move_to(cb[c]) for c, x in enumerate(tight[0])]
        self.play(FadeIn(lb), Create(cb), FadeIn(ib), *[FadeIn(x) for x in vb], run_time=1.0)
        self.at("两件放完")
        for it in range(len(ws)):
            ring = SurroundingRectangle(cards[it], color=C_YELLOW, buff=0.06)
            self.play(Create(ring), run_time=0.4)
            anims = []
            for vals, cells, rows, col in ((va, ca, loose, C_TEAL), (vb, cb, tight, C_GREEN)):
                for c in range(cap + 1):
                    if rows[it + 1][c] != rows[it][c]:
                        anims.append(Transform(vals[c], num(rows[it + 1][c], color=col).move_to(cells[c])))
                        anims.append(Indicate(cells[c], color=col, scale_factor=1.08))
            self.play(*anims, run_time=1.1)
            self.play(FadeOut(ring), run_time=0.3)
        self.at("其实只装了")
        ha = SurroundingRectangle(ca[cap], color=C_TEAL, buff=0.05, stroke_width=4)
        na = T(f"{loose[-1][cap]}：只装了 {ws[1]}，空着 {cap - ws[1]}", 22, C_TEAL)
        na.next_to(ca, DOWN, buff=0.3).align_to(ca, RIGHT)
        self.play(Create(ha), FadeIn(na), run_time=0.8)
        self.at("仍是负无穷")
        hb = SurroundingRectangle(cb[cap], color=C_GREEN, buff=0.05, stroke_width=4)
        nb = T(f"到不了：{ws[0]} 和 {ws[1]} 凑不出 {cap} → 输出 {K.exact_fill_max(ws, vs, cap)}", 22, C_GREEN)
        nb.next_to(cb, DOWN, buff=0.3).align_to(cb, RIGHT)
        self.play(Create(hb), FadeIn(nb), run_time=0.8)
        self.close(head, cards, ca, ia, cb, ib, la, lb, *va, *vb, ha, na, hb, nb)

    # ---------------------------------------------------------------- 初值速查表
    def trap_beat(self):
        self.beat("trap")
        warn = VGroup(T("忘了改初值", 30, C_RED), T("恰好型 → 退化成不超过型：答案偏大，不报错", 28))
        warn.arrange(DOWN, buff=0.25).move_to([0, 2.4, 0])
        self.play(FadeIn(warn, shift=UP * 0.2), run_time=0.8)
        rows = [("目标", "初值", C_GREY), ("不超过 C 的最大价值", "全 0", C_TEAL),
                ("恰好装满 C 的最大价值", "dp[0] = 0，其余 −∞", C_GREEN),
                ("恰好装满 C 的最小代价", "dp[0] = 0，其余 +∞", C_YELLOW)]
        tab = VGroup()
        for r, (a, b, col) in enumerate(rows):
            y = 0.6 - 0.75 * r
            ma = T(a, 26, col if r else C_GREY).move_to([-1.6, y, 0])
            mb = T(b, 26, col if r else C_GREY).move_to([2.8, y, 0])
            tab.add(VGroup(ma, mb))
        rule = Line([-4.6, 0.25, 0], [5.0, 0.25, 0], color=C_GREY, stroke_width=1.5)
        self.play(FadeIn(tab[0]), Create(rule), *[FadeIn(r) for r in tab[1:3]], run_time=1.0)
        self.at("最小代价")
        tag = T("NBA 门票", 22, C_YELLOW).next_to(tab[3], DOWN, buff=0.25)
        self.play(FadeIn(tab[3], shift=UP * 0.2), FadeIn(tag), run_time=0.8)
        self.close(warn, tab, rule, tag)

    # ---------------------------------------------------------------- 作业 Coins
    def coins_beat(self):
        self.beat("coins")
        A, C, m = K.COIN_A, K.COIN_C, K.COIN_M
        bundles, rows, ans = K.coins_steps(A, C, m)
        head = T("作业 Coins：多重背包 + 恰好凑出", 34).move_to([0, 3.3, 0])
        self.play(FadeIn(head), run_time=0.6)
        self.at("面值一的")
        coins = VGroup()
        for a, c in zip(A, C):
            for _ in range(c):
                coins.add(VGroup(Circle(0.36, stroke_color=C_YELLOW, stroke_width=3).set_fill(C_YELLOW, 0.15),
                                 MathTex(str(a), color=C_YELLOW).scale(0.75)))
        coins.arrange(RIGHT, buff=0.3).move_to([0, 2.1, 0])
        self.play(LaggedStart(*[FadeIn(c, scale=0.6) for c in coins], lag_ratio=0.2), run_time=1.0)
        self.at("拆成")
        chips = VGroup()
        for g, (_, _, ww) in enumerate(bundles):
            box = RoundedRectangle(corner_radius=0.1, width=0.95, height=0.55, stroke_color=PART_COL[g],
                                   stroke_width=2.5).set_fill(PART_COL[g], 0.15)
            chips.add(VGroup(box, MathTex(str(ww), color=PART_COL[g]).scale(0.65).move_to(box)))
        chips.arrange(RIGHT, buff=0.3).move_to([0, 1.05, 0])
        clab = T(f"{len(bundles)} 捆", 24, C_GREY).next_to(chips, RIGHT, buff=0.4)
        self.play(FadeIn(chips, shift=DOWN * 0.2), FadeIn(clab), run_time=0.8)
        cw = 0.85
        cells = VGroup(*[Rectangle(width=cw * 0.92, height=0.7, stroke_color=C_GREY, stroke_width=2)
                         .move_to([(c - m / 2) * cw, -0.6, 0]) for c in range(m + 1)])
        idx = VGroup(*[MathTex(str(c), color=C_GREY).scale(0.5).next_to(cells[c], UP, buff=0.08) for c in range(m + 1)])
        self.at("表里只记")
        fills = {0: cells[0].copy().set_stroke(width=0).set_fill(C_TEAL, 0.55)}
        self.play(Create(cells), FadeIn(idx), FadeIn(fills[0]), run_time=0.8)
        step = max(0.6, min(1.2, (self.cue_start("零到八", self.now) - self.now) / len(bundles) - 0.1))
        for g in range(len(bundles)):
            new = [c for c in range(m + 1) if rows[g + 1][c] and not rows[g][c]]
            add = [cells[c].copy().set_stroke(width=0).set_fill(PART_COL[g], 0.55) for c in new]
            for c, f in zip(new, add):
                fills[c] = f
            self.play(Indicate(chips[g], scale_factor=1.15), *[FadeIn(f, scale=0.6) for f in add], run_time=step)
        self.at("零到八")
        bad = [c for c in range(1, m + 1) if not rows[-1][c]]
        xs = VGroup(*[Cross(cells[c], stroke_color=C_RED, stroke_width=4, scale_factor=0.5) for c in bad])
        res = VGroup(T(f"1 到 {m} 里能凑出", 28), MathTex(str(ans), color=C_YELLOW).scale(1.1), T("个", 28))
        res.arrange(RIGHT, buff=0.2).move_to([0, -1.95, 0])
        self.play(Create(xs), run_time=0.6)
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.close(head, coins, chips, clab, cells, idx, *fills.values(), xs, res)

    # ---------------------------------------------------------------- 二维费用
    def twodim_beat(self):
        self.beat("twodim")
        pets, balls, hp = K.PK_PETS, K.PK_BALLS, K.PK_HP
        best, left = K.pokemon(balls, hp, pets)
        pick = K.pokemon_pick(balls, hp, pets)
        head = T("二维费用：宠物小精灵之收服", 34, C_PURPLE).move_to([0, 3.35, 0])
        self.play(FadeIn(head), run_time=0.6)
        self.at("收服一只")
        rows = VGroup()
        for i, (b, h) in enumerate(pets):
            box = RoundedRectangle(corner_radius=0.1, width=3.9, height=0.5, stroke_color=C_GREY,
                                   stroke_width=1.5).set_fill(C_GREY, 0.08)
            lab = T(f"精灵 {i + 1}：{b} 个球 · {h} 体力", 22).move_to(box)
            rows.add(VGroup(box, lab))
        rows.arrange(DOWN, buff=0.14).move_to([3.9, -0.7, 0])
        lim = T(f"上限：{balls} 个球，{hp} 体力", 22, C_GREY).next_to(rows, UP, buff=0.25)
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rows], lag_ratio=0.15), FadeIn(lim),
                  run_time=1.4)
        self.at("状态多一维")
        st = MathTex(r"dp[c]", r"\ \to\ ", r"dp[b][h]", color=WHITE).scale(0.8).move_to([-3.6, 1.05, 0])
        st[2].set_color(C_PURPLE)
        n, g = 6, 0.48
        ox, oy = -5.3, -2.15                       # 网格左下角格子中心
        grid = VGroup(*[Square(g * 0.92, stroke_color=C_GREY, stroke_width=1.2).move_to([ox + g * b, oy + g * h, 0])
                        for b in range(n) for h in range(n)])
        xl = T("球数 b →", 20, C_GREY).next_to(grid, DOWN, buff=0.15)
        yl = T("体力 h ↑", 20, C_GREY).rotate(PI / 2).next_to(grid, LEFT, buff=0.15)
        cell_txt = T("格子：最多收服几只", 20, C_GREY).next_to(grid, RIGHT, buff=0.3).align_to(grid, UP)
        self.play(Write(st), Create(grid), FadeIn(xl), FadeIn(yl), FadeIn(cell_txt), run_time=1.4)
        self.at("两层都倒序")
        src = ("for b in range(balls, cost_b - 1, -1):\n"
               "    for h in range(hp, cost_h - 1, -1):\n"
               "        dp[b][h] = max(dp[b][h], dp[b - cost_b][h - cost_h] + 1)\n")
        cd = code(src, 22).move_to([0, 2.55, 0])
        if cd.width > 13.2:
            cd.scale_to_fit_width(13.2)
        self.play(FadeOut(head), FadeIn(cd), run_time=0.8)
        self.at("往回退")
        tb, th, db, dh = 4, 5, 2, 3
        tgt = Square(g * 0.92, stroke_color=C_YELLOW, stroke_width=3).set_fill(C_YELLOW, 0.3).move_to(grid[tb * n + th])
        srcc = Square(g * 0.92, stroke_color=C_TEAL, stroke_width=3).set_fill(C_TEAL, 0.3).move_to(grid[(tb - db) * n + th - dh])
        arr = Arrow(srcc.get_center(), tgt.get_center(), buff=0.12, color=C_YELLOW, stroke_width=4,
                    max_tip_length_to_length_ratio=0.25)
        plus = MathTex("+1", color=C_YELLOW).scale(0.6).next_to(tgt, UP, buff=0.08)
        hl = SurroundingRectangle(cd.code_lines[2], color=C_YELLOW, buff=0.04)
        self.play(FadeIn(srcc), FadeIn(tgt), GrowArrow(arr), FadeIn(plus), Create(hl), run_time=1.2)
        self.at("十个球")
        anims = [rows[i][0].animate.set_stroke(C_PURPLE, 3).set_fill(C_PURPLE, 0.25) for i in pick]
        anims += [rows[i].animate.set_opacity(0.35) for i in range(len(pets)) if i not in pick]
        self.play(*anims, run_time=0.9)
        used_b = sum(pets[i][0] for i in pick)
        res = T(f"最多 {best} 只，用 {used_b} 个球，剩 {left} 体力", 24, C_YELLOW).next_to(rows, DOWN, buff=0.25)
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.close(rows, lim, st, grid, xl, yl, cell_txt, cd, tgt, srcc, arr, plus, hl, res)

    # ---------------------------------------------------------------- 分数背包
    def bar(self, value, weight, u, col, h=0.85):
        r = Rectangle(width=weight * u, height=h, stroke_color=col, stroke_width=2.5).set_fill(col, 0.25)
        lab = T(f"重 {weight} · 值 {value}", 22).move_to(r)
        return VGroup(r, lab)

    def frac_beat(self):
        self.beat("frac")
        items, cap = K.FR_ITEMS, K.FR_CAP
        tr = K.fractional_trace(items, cap)
        u = 0.7
        head = T("分数背包：圣诞老人的礼物", 34, C_YELLOW).move_to([0, 3.35, 0])
        self.play(FadeIn(head), run_time=0.6)
        cols = [C_RED, C_BLUE, C_BLUE]
        bars = VGroup(*[self.bar(v, w, u, cols[i]) for i, (v, w) in enumerate(items)]).arrange(RIGHT, buff=0.35)
        bars.move_to([0, 1.9, 0])
        prices = VGroup(*[T(f"单价 {v // w}", 22, cols[i]).next_to(bars[i], DOWN, buff=0.15)
                          for i, (v, w) in enumerate(items)])
        bag = Rectangle(width=cap * u, height=0.95, stroke_color=C_GREY, stroke_width=3).move_to([0.6, -0.6, 0])
        ticks = VGroup(*[Line(bag.get_left() + RIGHT * u * t + UP * 0.47, bag.get_left() + RIGHT * u * t + DOWN * 0.47,
                              stroke_color=C_GREY, stroke_width=1, stroke_opacity=0.4) for t in range(1, cap)])
        blab = T(f"容量 {cap}", 24, C_GREY).next_to(bag, LEFT, buff=0.3)
        self.at("能切开")
        self.play(LaggedStart(*[FadeIn(b, shift=DOWN * 0.2) for b in bars], lag_ratio=0.3), run_time=1.2)
        self.at("按单价")
        self.play(LaggedStart(*[FadeIn(p, shift=UP * 0.15) for p in prices], lag_ratio=0.3), run_time=1.0)
        self.at("容量十")
        self.play(Create(bag), FadeIn(ticks), FadeIn(blab), run_time=0.8)
        self.at("先整件装")
        first = bars[0]
        self.play(first.animate.move_to(bag.get_left() + RIGHT * tr[0][1] * u / 2), FadeOut(prices[0]), run_time=1.0)
        rest = cap - tr[0][2]
        gapr = Rectangle(width=rest * u, height=0.95, stroke_width=0).move_to(bag.get_right() + LEFT * rest * u / 2)
        br = Brace(gapr, DOWN, buff=0.08, color=C_GREY)
        bt = T(f"剩 {rest}", 22, C_GREY).next_to(br, DOWN, buff=0.08)
        self.play(GrowFromCenter(br), FadeIn(bt), run_time=0.6)
        self.at("切下")
        v2, w2, got_w, got_v = tr[1]
        b2 = bars[1]
        piece = Rectangle(width=got_w * u, height=0.85, stroke_color=C_BLUE, stroke_width=2.5).set_fill(C_BLUE, 0.25)
        piece.align_to(b2, LEFT).align_to(b2, UP)
        stub = Rectangle(width=(w2 - got_w) * u, height=0.85, stroke_color=C_GREY, stroke_width=2,
                         stroke_opacity=0.6).set_fill(C_GREY, 0.1).next_to(piece, RIGHT, buff=0.12)
        cut = DashedLine(b2.get_left() + RIGHT * got_w * u + UP * 0.6, b2.get_left() + RIGHT * got_w * u + DOWN * 0.6,
                         color=C_YELLOW)
        self.play(Create(cut), run_time=0.4)
        frac = MathTex(rf"\frac{{{got_w}}}{{{w2}}}", color=C_YELLOW).scale(0.7).move_to(piece)
        self.play(FadeOut(b2), FadeOut(cut), FadeIn(piece), FadeIn(stub), FadeIn(frac), run_time=0.5)
        gv = MathTex(f"{got_v:g}", color=C_BLUE).scale(0.7)
        tgt = bag.get_left() + RIGHT * (tr[0][1] + got_w / 2) * u
        self.play(FadeOut(br), FadeOut(bt), FadeOut(frac), piece.animate.move_to(tgt), FadeOut(prices[1]), run_time=0.8)
        gv.move_to(piece)
        total = K.fractional_knapsack(items, cap)
        eq = MathTex(f"{tr[0][3]}", "+", f"{got_v:g}", "=", f"{total:g}", color=WHITE).scale(0.9)
        eq[4].set_color(C_YELLOW)
        eq.move_to([0.6, -2.1, 0])
        self.play(FadeIn(gv), Write(eq), run_time=0.8)
        self.frac_keep = dict(head=head)
        self.close(bars[0], bars[2], prices[2], stub, bag, ticks, blab, piece, gv, eq)

    # ---------------------------------------------------------------- 0/1 不能贪心
    def greedy_beat(self):
        self.beat("greedy")
        items, cap = K.FR_ITEMS, K.FR_CAP
        u = 0.7
        old = self.frac_keep["head"]
        head = T("不能切：0/1 背包还能贪心吗", 34, C_RED).move_to([0, 3.35, 0])
        self.play(FadeOut(old), FadeIn(head), run_time=0.6)
        g_val, took = K.greedy_01(items, cap)
        best = K.knap01(items, cap)
        cols = [C_RED, C_BLUE, C_BLUE]

        def bag_at(y):
            bag = Rectangle(width=cap * u, height=0.95, stroke_color=C_GREY, stroke_width=3).move_to([0.2, y, 0])
            return bag
        ya, yb = 1.75, -0.15
        bag_a, bag_b = bag_at(ya), bag_at(yb)
        la = T("按单价贪心", 26, C_RED).next_to(bag_a, LEFT, buff=0.35)
        lb = T("背包 DP", 26, C_GREEN).next_to(bag_b, LEFT, buff=0.35)
        self.play(Create(bag_a), FadeIn(la), run_time=0.6)
        self.at("先装单价五")
        x = bag_a.get_left()[0]
        fill_a = VGroup()
        for i in took:
            v, w = items[i]
            b = self.bar(v, w, u, cols[i], h=0.85).move_to([x + w * u / 2, ya, 0])
            fill_a.add(b)
            x += w * u
        used = sum(items[i][1] for i in took)
        empty = DashedVMobject(Rectangle(width=(cap - used) * u, height=0.85, stroke_color=C_RED, stroke_width=2),
                               num_dashes=24).move_to([x + (cap - used) * u / 2, ya, 0])
        et = T(f"空 {cap - used}", 22, C_RED).move_to(empty)
        self.play(FadeIn(fill_a, shift=RIGHT * 0.3), run_time=0.8)
        self.play(Create(empty), FadeIn(et), run_time=0.6)
        ra = MathTex(str(g_val), color=C_RED).scale(0.9).next_to(bag_a, RIGHT, buff=0.35)
        self.play(FadeIn(ra), run_time=0.5)
        self.at("两件重五")
        self.play(Create(bag_b), FadeIn(lb), run_time=0.5)
        x = bag_b.get_left()[0]
        fill_b = VGroup()
        for i in (1, 2):
            v, w = items[i]
            b = self.bar(v, w, u, cols[i], h=0.85).move_to([x + w * u / 2, yb, 0])
            fill_b.add(b)
            x += w * u
        rb = MathTex(str(best), color=C_GREEN).scale(0.9).next_to(bag_b, RIGHT, buff=0.35)
        self.play(LaggedStart(*[FadeIn(b, shift=RIGHT * 0.3) for b in fill_b], lag_ratio=0.4), FadeIn(rb), run_time=1.0)
        self.at("能切时")
        why = T("能切时空隙可以用碎片补满，不能切就空着", 24, C_GREY).move_to([0, -1.25, 0])
        self.play(Indicate(empty, color=C_RED), FadeIn(why), run_time=0.8)
        self.at("所以可分割")
        rule = VGroup(T("可分割 → 贪心", 30, C_YELLOW), T("不可分割 → 背包 DP", 30, C_GREEN)).arrange(RIGHT, buff=0.8)
        rule.move_to([0, -2.3, 0])
        self.play(FadeIn(rule, shift=UP * 0.2), run_time=0.7)
        self.close(head, bag_a, bag_b, la, lb, fill_a, empty, et, ra, fill_b, rb, why, rule)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        defs = [("数量有限", "二进制拆分，再当 0/1 背包", C_BLUE), ("恰好装满", "初值 −∞（最小代价用 +∞）", C_GREEN),
                ("费用两种", "状态多一维，两层都倒序", C_PURPLE), ("能切开", "按单价贪心，不用 DP", C_YELLOW)]
        rows = VGroup(*[VGroup(T(a, 30, col), T(b, 30)).arrange(RIGHT, buff=0.5) for a, b, col in defs])
        rows.arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 0.5, 0])
        keys = ["数量有限", "恰好装满", "费用两种", "能切开"]
        for r, key in zip(rows, keys):
            self.at(key)
            self.play(FadeIn(r, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 11 周 动态规划 讲义 1.4–1.6 · OpenJudge M01742、21458、04102、04110",
                20, C_GREY)
        if src.width > 13.4:
            src.scale_to_fit_width(13.4)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.0)
