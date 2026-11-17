"""十一月月考讲评：把题面翻译成熟悉的结构（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。六题的样例、选座一排十个座位的逐格判定、箭头迷阵每次出发的路径与结论、
牌堆倒推每一步、渗透每一步的连通块、括号串的前缀和 / nxt / 三问的判定全部来自 novdata
（讲义六段 Python 参考代码原样；test_nov.py 用暴力模拟、BFS、栈匹配独立对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novdata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_ORANGE = "#FF9F43"
DIM = "#3a4050"
ST_COL = {0: DIM, 1: C_YELLOW, 2: C_GREEN, 3: C_RED}         # 箭头迷阵四种状态
COMP = [C_BLUE, C_PURPLE, C_ORANGE, C_TEAL, C_YELLOW, "#E07AB4"]


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


class NovLesson(Lesson):
    def construct(self):
        for b in ("title", "warm", "arrows", "cards", "perc", "brackets", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[nov] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def head(self, no, name, tag, pos=(-6.6, 2.85)):
        g = VGroup(T(no, 26, C_BLUE), T(name, 32), T(tag, 22, C_GREY)).arrange(RIGHT, buff=0.3)
        return g.move_to([pos[0] + g.width / 2, pos[1], 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("月考讲评", 26, C_BLUE).move_to([0, 2.9, 0])
        title = T("十一月月考", 56).next_to(kick, DOWN, buff=0.22)
        sub = T("把题面翻译成熟悉的结构", 30, C_YELLOW).next_to(title, DOWN, buff=0.22)
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.at("十月")
        oct_ = VGroup(T("10 月", 26, C_GREY), T("语法关", 30, C_GREY)).arrange(RIGHT, buff=0.25)
        nov = VGroup(T("11 月", 26, C_YELLOW), T("建模关", 30, C_YELLOW)).arrange(RIGHT, buff=0.25)
        arr = Arrow(LEFT * 0.6, RIGHT * 0.6, color=C_GREY, buff=0, stroke_width=4)
        lv = VGroup(oct_, arr, nov).arrange(RIGHT, buff=0.4).next_to(sub, DOWN, buff=0.45)
        self.play(FadeIn(oct_), run_time=0.5)
        self.at("建模关")
        self.play(GrowArrow(arr), FadeIn(nov, shift=RIGHT * 0.2), run_time=0.7)
        self.at("翻译")
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)
        self.at("六道题")
        probs = [("T1", "双重回文", "枚举·进制", 1), ("T2", "图书馆选座", "一遍扫描", 2),
                 ("T3", "箭头迷阵", "找环·记忆化", 3), ("T4", "牌堆魔术", "双端队列·倒推", 3),
                 ("T5", "渗透实验", "并查集·虚拟结点", 3), ("T6", "括号区间审计", "前缀和·单调栈", 4)]
        cards = VGroup()
        for no, name, tag, star in probs:
            box = RoundedRectangle(corner_radius=0.12, width=2.05, height=1.5, stroke_color=C_GREY, stroke_width=2)
            txt = VGroup(T(no, 22, C_BLUE), T(name, 24), T(tag, 17, C_GREY),
                         T("★" * star + "☆" * (5 - star), 17, C_YELLOW)).arrange(DOWN, buff=0.1)
            cards.add(VGroup(box, txt.move_to(box)))
        cards.arrange(RIGHT, buff=0.18).move_to([0, -1.75, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cards], lag_ratio=0.15), run_time=1.6)
        spec = T("6 题 / 112 分钟", 24, C_GREY).next_to(cards, UP, buff=0.22)
        self.play(FadeIn(spec), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- T1 + T2 热身
    def warm_beat(self):
        self.beat("warm")
        h1 = self.head("T1", "双重回文", "十进制、二进制都回文")
        self.play(FadeIn(h1, shift=DOWN * 0.2), run_time=0.5)
        self.at("偶数")
        even = VGroup(T("偶数", 26), M("6", 28), T("→", 26, C_GREY),
                      VGroup(M("1", 30, C_YELLOW), M("1", 30), M("0", 30, C_RED)).arrange(RIGHT, buff=0.06),
                      M("₂", 22, C_GREY)).arrange(RIGHT, buff=0.22)
        even[4].next_to(even[3], RIGHT, buff=0.04).align_to(even[3], DOWN)
        even.move_to([-6.3 + even.width / 2, 2.0, 0])
        why = T("开头 1，末位 0：不可能回文", 24, C_RED).next_to(even, RIGHT, buff=0.5)
        self.play(FadeIn(even), run_time=0.5)
        self.play(Indicate(even[3][0], color=C_YELLOW), Indicate(even[3][2], color=C_RED), FadeIn(why), run_time=0.8)
        self.at("只枚举")
        odd = M("for i in range(1, n + 1, 2)", 24, C_GREEN).next_to(why, RIGHT, buff=0.5)
        if odd.get_right()[0] > 6.8:
            odd.next_to(even, DOWN, buff=0.25).align_to(even, LEFT)
        self.play(FadeIn(odd, shift=LEFT * 0.2), run_time=0.5)
        self.at("十九个")
        n, cnt, best = D.T1_BIG
        assert D.run_io(D.solve_t1, f"{n}\n") == f"{cnt} {best}"
        bb = bin(best)[2:]
        assert bb == bb[::-1] and str(best) == str(best)[::-1]
        res = VGroup(MathTex(r"n=10^{6}", color=WHITE).scale(0.75), T(f"共 {cnt} 个，最大", 24),
                     M(str(best), 26, C_YELLOW), T("=", 24, C_GREY), M(bb + "₂", 22, C_YELLOW)).arrange(RIGHT, buff=0.2)
        res.next_to(odd if odd.get_y() < 1.9 else even, DOWN, buff=0.3).align_to(even, LEFT)
        self.play(FadeIn(res, shift=UP * 0.15), run_time=0.6)
        top = VGroup(h1, even, why, odd, res)

        # T2：一排十个座位，一个指针从左扫到右
        self.at("图书馆")
        h2 = self.head("T2", "图书馆选座", "坐编号最小、左右都空的座位")
        h2.move_to([-6.6 + h2.width / 2, 0.15, 0])
        line = Line([-6.6, 0.62, 0], [6.6, 0.62, 0], color=DIM, stroke_width=2)
        s0, m = D.SEATS
        steps, sat, final = D.seats_trace(s0, m)
        assert D.run_io(D.solve_t2, f"{len(s0)} {m}\n{s0}\n") == f"{sat}\n{final}"
        w = 0.78
        seats = VGroup()
        for i, ch in enumerate(s0):
            sq = Square(w * 0.88, stroke_color=C_GREY, stroke_width=2.5)
            sq.set_fill(C_GREY if ch == "1" else BG, 0.45 if ch == "1" else 0)
            seats.add(VGroup(sq, M(ch, 26, C_GREY if ch == "1" else WHITE).move_to(sq)))
        seats.arrange(RIGHT, buff=w * 0.12).move_to([0.6, -1.05, 0])
        idx = VGroup(*[M(str(i + 1), 18, C_GREY).next_to(seats[i], UP, buff=0.12) for i in range(len(s0))])
        cnt_t = T(f"来 {m} 人", 24, C_GREY).next_to(seats, LEFT, buff=0.45)
        self.play(Create(line), FadeIn(h2), FadeIn(seats), FadeIn(idx), FadeIn(cnt_t), run_time=0.7)
        self.at("一个指针")
        ptr = Arrow(DOWN * 0.55, UP * 0.05, color=C_YELLOW, buff=0, stroke_width=6).next_to(seats[0], DOWN, buff=0.1)
        self.play(GrowArrow(ptr), run_time=0.3)
        n_sat = 0
        sat_t = T("坐下 0 人", 24, C_GREEN).next_to(seats, RIGHT, buff=0.3)
        self.add(sat_t)
        for i, ok, why_ in steps:
            anims = [ptr.animate.next_to(seats[i], DOWN, buff=0.1)]
            self.play(*anims, run_time=0.22)
            if ok:
                n_sat += 1
                new = M("1", 26, C_GREEN).move_to(seats[i])
                nt = T(f"坐下 {n_sat} 人", 24, C_GREEN).move_to(sat_t)
                self.play(seats[i][0].animate.set_fill(C_GREEN, 0.35).set_stroke(C_GREEN),
                          Transform(seats[i][1], new), Transform(sat_t, nt), run_time=0.3)
            else:
                self.play(Indicate(seats[i][0], color=C_RED, scale_factor=1.08), run_time=0.22)
        assert n_sat == sat == m - 1 and "".join(final) == "1010101010"
        self.at("第四位")
        left = T(f"第 {m} 位：没有座位，离开", 24, C_RED).next_to(seats, DOWN, buff=0.75)
        self.play(FadeOut(ptr), FadeIn(left, shift=UP * 0.15), run_time=0.5)
        self.at("小心边界")
        ghost = DashedVMobject(Square(w * 0.88, stroke_color=C_RED, stroke_width=2.5), num_dashes=16)
        ghost.next_to(seats[0], LEFT, buff=w * 0.12)
        gl = M("s[-1]", 20, C_RED).next_to(ghost, UP, buff=0.12)
        self.play(FadeOut(cnt_t), FadeOut(left), Create(ghost), FadeIn(gl), run_time=0.5)
        self.at("悄悄")
        arc = CurvedArrow(ghost.get_bottom() + DOWN * 0.08, seats[-1].get_bottom() + DOWN * 0.08,
                          angle=TAU / 7, color=C_RED, stroke_width=3)
        note = T("不报错，读到的是最后一个座位", 24, C_RED).move_to([0.6, -2.55, 0])
        self.play(Create(arc), Indicate(seats[-1], color=C_RED), FadeIn(note), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- T3 箭头迷阵
    def arrows_beat(self):
        self.beat("arrows")
        h = self.head("T3", "箭头迷阵", "每格恰好一条出边")
        g = D.ARROWS
        n, m = len(g), len(g[0])
        walks, st_final = D.arrows_trace(g)
        assert D.run_io(D.solve_t3, f"{n} {m}\n" + "\n".join(g) + "\n") == str(st_final.count(2)) == "5"
        cs, cx, cy = 1.25, -3.4, -0.35

        def pos(i, j):
            return np.array([cx + (j - (m - 1) / 2) * cs, cy - (i - (n - 1) / 2) * cs, 0])
        cells, arrows = {}, VGroup()
        for i in range(n):
            for j in range(m):
                sq = Square(cs * 0.94, stroke_color=C_GREY, stroke_width=2).set_fill(DIM, 0.35).move_to(pos(i, j))
                di, dj = D.MOVE[g[i][j]]
                v = np.array([dj, -di, 0]) * cs * 0.28
                a = Arrow(pos(i, j) - v, pos(i, j) + v, buff=0, color=WHITE, stroke_width=6,
                          max_tip_length_to_length_ratio=0.4)
                cells[(i, j)] = sq
                arrows.add(a)
        grid = VGroup(*cells.values())
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(grid), LaggedStart(*[GrowArrow(a) for a in arrows],
                                                                         lag_ratio=0.06), run_time=1.4)
        self.at("要么走出")
        x0 = 0.9
        rules = VGroup(T("路线是定的：", 24, C_GREY),
                       VGroup(T("走出边界", 24, C_GREEN), T("或", 24, C_GREY), T("掉进一个环", 24, C_RED)).arrange(RIGHT, buff=0.2))
        rules.arrange(RIGHT, buff=0.15).move_to([x0, 2.05, 0], aligned_edge=LEFT)
        self.play(FadeIn(rules), run_time=0.6)
        legend = VGroup()
        for k, name in ((0, "未访问"), (1, "在路上"), (2, "能逃"), (3, "逃不出")):
            legend.add(VGroup(Square(0.28, stroke_width=0).set_fill(ST_COL[k], 0.8), T(name, 21)).arrange(RIGHT, buff=0.12))
        legend.arrange(RIGHT, buff=0.3).move_to([x0, 1.35, 0], aligned_edge=LEFT)
        self.play(FadeIn(legend), run_time=0.5)
        st = {}
        lines = VGroup()
        keys = {0: "从一格出发", 1: "走出界", 3: "撞上本条路", 4: "撞上已有"}
        rule_txt = {"out": ("出界 → 整条路能逃", C_GREEN), "cycle": ("撞上「在路上」→ 成环，整条路逃不出", C_RED),
                    "join": ("撞上已有结论 → 直接接上", C_BLUE)}
        shown = set()
        ptr = Dot(radius=0.1, color=C_YELLOW)
        for w_i, wk in enumerate(walks):
            if w_i in keys:
                self.at(keys[w_i])
            fast = w_i in (2, 5)
            rt = 0.22 if fast else 0.35
            p0 = wk["path"][0]
            ptr.move_to(pos(*p0))
            self.play(FadeIn(ptr, scale=0.5), run_time=0.15)
            for k, (i, j) in enumerate(wk["path"]):
                if k:
                    self.play(ptr.animate.move_to(pos(i, j)), run_time=rt * 0.7)
                self.play(cells[(i, j)].animate.set_fill(ST_COL[1], 0.55), run_time=rt * 0.6)
            hi, hj = wk["hit"]
            end = pos(hi, hj)
            self.play(ptr.animate.move_to(end), run_time=rt * 0.8)
            ring = None
            if wk["end"] != "out":
                ring = Circle(cs * 0.42, color=ST_COL[wk["res"]], stroke_width=5).move_to(end)
                self.play(Create(ring), run_time=0.3)
            if wk["end"] not in shown:
                shown.add(wk["end"])
                txt, c = rule_txt[wk["end"]]
                ln = T(txt, 24, c)
                ln.move_to([x0 + ln.width / 2, 0.55 - 0.6 * len(lines), 0])
                lines.add(ln)
                self.play(FadeIn(ln, shift=LEFT * 0.2), run_time=0.35)
            self.play(*[cells[c].animate.set_fill(ST_COL[wk["res"]], 0.55) for c in wk["path"]],
                      FadeOut(ptr), *([FadeOut(ring)] if ring else []), run_time=0.35)
            for c in wk["path"]:
                st[c] = wk["res"]
        assert [st[(i, j)] for i in range(n) for j in range(m)] == st_final
        self.at("样例答案")
        ans = T(f"能逃 {st_final.count(2)} 格 · 每格只走一次 O(nm)", 26, C_GREEN)
        ans.move_to([x0 + ans.width / 2, 0.55 - 0.6 * len(lines) - 0.15, 0])
        self.play(FadeIn(ans, scale=1.1), *[Indicate(cells[c], color=C_GREEN, scale_factor=1.05)
                                            for c, v in st.items() if v == 2], run_time=0.8)
        self.at("别写递归")
        strip = VGroup(*[M("R", 20, C_GREY) for _ in range(12)], M("…", 20, C_GREY)).arrange(RIGHT, buff=0.08)
        rec = VGroup(strip, T("长 2×10⁵ 的路线", 22, C_GREY)).arrange(RIGHT, buff=0.25)
        rec.move_to([x0 + rec.width / 2, -1.95, 0])
        bad = VGroup(T("递归：超过深度上限", 22, C_RED), T("循环 + path 列表：同一个算法", 22, C_GREEN)).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        bad.next_to(rec, DOWN, buff=0.2).align_to(rec, LEFT)
        self.play(FadeIn(rec), run_time=0.5)
        self.at("超过递归")
        self.play(FadeIn(bad, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- T4 牌堆魔术
    def card(self, v, color=WHITE):
        box = RoundedRectangle(corner_radius=0.08, width=0.7, height=0.95, stroke_color=color, stroke_width=3)
        box.set_fill(color, 0.15)
        return VGroup(box, M(str(v), 30, color).move_to(box))

    def row_pos(self, k, total, y, x_left=-4.6, dx=0.9):
        return np.array([x_left + k * dx, y, 0])

    def cards_beat(self):
        self.beat("cards")
        n = 4
        steps = D.cards_reverse_trace(n)
        order = steps[-1]["moved"]
        assert D.run_io(D.solve_t4, f"{n}\n") == " ".join(map(str, order)) and D.cards_forward(order) == list(range(1, n + 1))
        h = self.head("T4", "牌堆魔术", "已知结果，求开头")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("每轮")
        rule = VGroup(T("每轮：", 24, C_GREY), T("① 顶牌移到底", 24), T("② 翻开顶牌拿走", 24),
                      T("要翻出 1 2 3 4", 24, C_YELLOW)).arrange(RIGHT, buff=0.35)
        rule.move_to([-6.6 + rule.width / 2, 2.1, 0])
        self.play(FadeIn(rule, lag_ratio=0.2), run_time=1.0)
        self.at("倒着做")
        y1 = 0.75
        lab1 = T("倒着做", 26, C_BLUE).move_to([-5.9, y1, 0])
        topl = T("牌顶", 20, C_GREY).move_to(self.row_pos(0, n, y1 + 0.78))
        undo = VGroup(T("撤销②：牌 i 放回牌顶", 22, C_TEAL), T("撤销①：底牌移回牌顶", 22, C_PURPLE)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        undo.move_to([1.5 + undo.width / 2, y1 + 0.05, 0])
        self.play(FadeIn(lab1), FadeIn(topl), FadeIn(undo), run_time=0.6)
        self.at("从四倒数")
        deck = []                                    # 当前从上到下的牌对象
        for stp in steps:
            c = self.card(stp["card"], C_TEAL).move_to(self.row_pos(0, n, y1))
            new_deck = [c] + deck
            self.play(FadeIn(c, shift=DOWN * 0.5),
                      *[d.animate.move_to(self.row_pos(k + 1, n, y1)) for k, d in enumerate(deck)],
                      Indicate(undo[0], color=C_TEAL, scale_factor=1.03), run_time=0.45)
            deck = new_deck
            assert [int(d[1].text) for d in deck] == stp["put"]
            if len(deck) > 1:
                last = deck[-1]
                rest = deck[:-1]
                self.play(last.animate(path_arc=-PI * 0.6).move_to(self.row_pos(0, n, y1)),
                          *[d.animate.move_to(self.row_pos(k + 1, n, y1)) for k, d in enumerate(rest)],
                          Indicate(undo[1], color=C_PURPLE, scale_factor=1.03), run_time=0.5)
                deck = [last] + rest
            assert [int(d[1].text) for d in deck] == stp["moved"]
        self.at("得到")
        box = SurroundingRectangle(VGroup(*deck), color=C_YELLOW, buff=0.12)
        self.play(Create(box), *[d[0].animate.set_stroke(C_YELLOW) for d in deck], run_time=0.6)
        self.at("正着验")
        y2 = -1.05
        lab2 = T("正着验", 26, C_GREEN).move_to([-5.9, y2, 0])
        fdeck = [self.card(int(d[1].text), WHITE).move_to(self.row_pos(k, n, y2)) for k, d in enumerate(deck)]
        outl = T("翻出：", 24, C_GREY).move_to([1.6, y2, 0])
        self.play(FadeIn(lab2), *[TransformFromCopy(d, f) for d, f in zip(deck, fdeck)], FadeIn(outl), run_time=0.6)
        got = []
        while fdeck:
            fdeck = fdeck[1:] + fdeck[:1]
            if len(fdeck) > 1:
                self.play(fdeck[-1].animate(path_arc=PI * 0.6).move_to(self.row_pos(len(fdeck) - 1, n, y2)),
                          *[d.animate.move_to(self.row_pos(k, n, y2)) for k, d in enumerate(fdeck[:-1])], run_time=0.3)
            top = fdeck.pop(0)
            got.append(top)
            self.play(top.animate.move_to([outl.get_right()[0] + 0.55 + 0.85 * (len(got) - 1), y2, 0]).set_color(C_GREEN),
                      *[d.animate.move_to(self.row_pos(k, n, y2)) for k, d in enumerate(fdeck)], run_time=0.3)
        assert [int(g[1].text) for g in got] == list(range(1, n + 1))
        self.at("两端")
        good = VGroup(M("dq.appendleft(x)", 24, C_GREEN), MathTex(r"O(1)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.3)
        bad = VGroup(M("lst.insert(0, x)", 24, C_RED), MathTex(r"O(n)", color=C_RED).scale(0.8),
                     T("× 2×10⁵ 次 → 超时", 22, C_RED)).arrange(RIGHT, buff=0.3)
        VGroup(good, bad).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([-6.3, -2.35, 0], aligned_edge=LEFT)
        self.play(FadeIn(good, shift=UP * 0.15), run_time=0.5)
        self.at("插到开头")
        self.play(FadeIn(bad, shift=UP * 0.15), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- T5 渗透实验
    def perc_beat(self):
        self.beat("perc")
        n, m, ops = D.PERC
        steps = D.perc_trace(n, m, ops)
        ans = steps[-1]["k"]
        inp = f"{n} {m} {len(ops)}\n" + "".join(f"{r} {c}\n" for r, c in ops)
        assert D.run_io(D.solve_t5, inp) == str(ans) == "6"
        h = self.head("T5", "渗透实验", "只开不关", pos=(0.6, 2.85))
        cs, cx, cy = 0.9, -3.6, -0.15

        def pos(i, j):
            return np.array([cx + (j - (m - 1) / 2) * cs, cy - (i - (n - 1) / 2) * cs, 0])
        cells = {}
        for i in range(n):
            for j in range(m):
                cells[(i, j)] = Square(cs * 0.92, stroke_color=C_GREY, stroke_width=2).set_fill("#20242e", 0.9).move_to(pos(i, j))
        grid = VGroup(*cells.values())
        bw = m * cs
        topb = RoundedRectangle(corner_radius=0.1, width=bw, height=0.42, stroke_color=C_GREY, stroke_width=2.5)
        topb.move_to(pos(0, 0) + np.array([(m - 1) / 2 * cs, 0.85, 0]))
        botb = topb.copy().move_to(pos(n - 1, 0) + np.array([(m - 1) / 2 * cs, -0.85, 0]))
        topl = M("TOP", 22, C_GREY).move_to(topb)
        botl = M("BOT", 22, C_GREY).move_to(botb)
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(grid), run_time=0.8)
        x0 = 0.6
        notes = VGroup()

        def note(txt, color=WHITE, size=24):
            t = T(txt, size, color)
            t.move_to([x0 + t.width / 2, 2.05 - 0.62 * len(notes), 0])
            notes.add(t)
            return t
        self.at("只合并")
        self.play(FadeIn(note("连通块只合并不拆分 → 并查集", C_YELLOW)), run_time=0.6)
        self.at("任意一格")
        rows = VGroup(SurroundingRectangle(VGroup(*[cells[(0, j)] for j in range(m)]), color=C_BLUE, buff=0.04),
                      SurroundingRectangle(VGroup(*[cells[(n - 1, j)] for j in range(m)]), color=C_BLUE, buff=0.04))
        self.play(Create(rows), run_time=0.6)
        self.at("虚拟结点")
        self.play(FadeOut(rows), FadeIn(topb), FadeIn(topl), FadeIn(botb), FadeIn(botl),
                  FadeIn(note("加两个虚拟结点 TOP、BOT", WHITE)), run_time=0.7)
        colors = {}                                  # 根 → 颜色
        links = VGroup()
        self.add(links)
        step_t = None

        def paint(st, rt):
            roots = st["roots"]
            for r in sorted(set(roots.values())):
                if r not in colors:
                    colors[r] = COMP[len(colors) % len(COMP)]
            anims = []
            for c, r in roots.items():
                col = colors[r]
                if c == "TOP":
                    anims.append(topb.animate.set_stroke(col if any(roots.get((0, j)) == r for j in range(m)) else C_GREY, 3))
                elif c == "BOT":
                    anims.append(botb.animate.set_stroke(col if any(roots.get((n - 1, j)) == r for j in range(m)) else C_GREY, 3))
                else:
                    anims.append(cells[c].animate.set_fill(col, 0.6).set_stroke(col, 2.5))
            return anims

        def do_step(st, rt=0.45):
            nonlocal step_t
            i, j = st["cell"]
            new_links = []
            if st["top"]:
                new_links.append(Line(cells[(i, j)].get_top(), [pos(i, j)[0], topb.get_bottom()[1], 0], color=WHITE, stroke_width=4))
            if st["bot"]:
                new_links.append(Line(cells[(i, j)].get_bottom(), [pos(i, j)[0], botb.get_top()[1], 0], color=WHITE, stroke_width=4))
            for (a, b) in st["nbr"]:
                p, q = pos(i, j), pos(a, b)
                v = (q - p) / np.linalg.norm(q - p)
                new_links.append(Line(p + v * cs * 0.3, q - v * cs * 0.3, color=WHITE, stroke_width=6))
            t = T(f"第 {st['k']} 步：打开 ({i + 1}, {j + 1})", 24, C_GREY).move_to([x0, -2.1, 0], aligned_edge=LEFT)
            self.play(cells[(i, j)].animate.set_fill(WHITE, 0.6), Transform(step_t, t) if step_t else FadeIn(t), run_time=rt * 0.6)
            step_t = step_t or t
            if new_links:
                links.add(*new_links)
                self.play(*[Create(ln) for ln in new_links], run_time=rt * 0.6)
            self.play(*paint(st, rt), run_time=rt * 0.6)
        do_step(steps[0])
        self.at("连底")
        do_step(steps[1])
        self.at("同根")
        same = note("渗透 ⟺ find(TOP) == find(BOT)", C_GREEN)
        self.play(FadeIn(same, shift=UP * 0.15), run_time=0.6)
        self.at("每开一格")
        self.play(FadeIn(note("每开一格：和打开的邻格合并，再判一次", WHITE, 22)), run_time=0.5)
        for st in steps[2:-1]:
            do_step(st, 0.5)
            assert not st["done"]
        self.at("第六步")
        do_step(steps[-1], 0.6)
        assert steps[-1]["done"] and steps[-1]["roots"]["TOP"] == steps[-1]["roots"]["BOT"]
        win = T(f"第 {ans} 步：TOP 与 BOT 同根，渗透", 24, C_GREEN).move_to(step_t, aligned_edge=LEFT)
        self.play(Transform(step_t, win), Indicate(topb, color=C_GREEN), Indicate(botb, color=C_GREEN), run_time=0.7)
        self.at("只有一行")
        self.play(FadeOut(notes[2:]), FadeOut(step_t), run_time=0.4)
        bug = D.perc_elif_bug(1, 3, [(1, 2)])
        good = D.perc_answer(1, 3, [(1, 2)])
        assert (bug, good) == (-1, 1)
        code_ok = VGroup(M("if r == 0:     union(u, TOP)", 21, C_GREEN), M("if r == n - 1: union(u, BOT)", 21, C_GREEN))
        code_ok.arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        code_bad = VGroup(M("if r == 0:       union(u, TOP)", 21, C_RED), M("elif r == n - 1: union(u, BOT)", 21, C_RED))
        code_bad.arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        lab_ok = T(f"n = 1 时答案 {good}", 22, C_GREEN)
        lab_bad = T(f"n = 1 时输出 {bug}", 22, C_RED)
        blk = VGroup(VGroup(code_ok, lab_ok).arrange(DOWN, buff=0.12, aligned_edge=LEFT),
                     VGroup(code_bad, lab_bad).arrange(DOWN, buff=0.12, aligned_edge=LEFT)).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        blk.move_to([x0, -0.85, 0], aligned_edge=LEFT)
        self.play(FadeIn(blk[0], shift=UP * 0.15), run_time=0.6)
        self.at("elif")
        self.play(FadeIn(blk[1], shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- T6 括号区间审计
    def brackets_beat(self):
        self.beat("brackets")
        s = D.BRACKETS
        n = len(s)
        pre = D.prefix(s)
        nxt, events = D.next_lower(pre)
        inp = f"{s}\n{len(D.QUERIES)}\n" + "".join(f"{l} {r}\n" for l, r in D.QUERIES)
        want = "\n".join("YES" if D.judge(s, l, r)[0] else "NO" for l, r in D.QUERIES)
        assert D.run_io(D.solve_t6, inp) == want == D.SAMPLES["t6"][0][1]
        h = self.head("T6", "括号区间审计", "子串 s[l..r] 合法吗？")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("二十万次")
        assert D.NAIVE_T6 == 4 * 10 ** 10
        naive = VGroup(T("每问现扫：", 24, C_GREY), MathTex(r"2\times10^5 \times 2\times10^5 = 4\times10^{10}", color=C_RED).scale(0.75),
                       T("超时", 24, C_RED)).arrange(RIGHT, buff=0.2)
        naive.move_to([-6.6 + naive.width / 2, 2.15, 0])
        self.play(FadeIn(naive), run_time=0.6)
        xL, dx, yb, dy = -5.4, 0.95, -1.75, 0.72

        def px(i):
            return xL + i * dx

        def py(v):
            return yb + v * dy
        chars = VGroup(*[M(ch, 34, C_BLUE if ch == "(" else C_ORANGE).move_to([px(k + 0.5), 1.25, 0]) for k, ch in enumerate(s)])
        cidx = VGroup(*[M(str(k + 1), 17, C_GREY).next_to(chars[k], UP, buff=0.08) for k in range(n)])
        self.at("前缀和")
        self.play(FadeIn(chars), FadeIn(cidx), run_time=0.5)
        base = DashedLine([px(0) - 0.2, py(0), 0], [px(n) + 0.2, py(0), 0], color=DIM, stroke_width=2)
        dots = VGroup(*[Dot([px(i), py(v), 0], radius=0.08, color=WHITE) for i, v in enumerate(pre)])
        vals = VGroup(*[M(str(v), 20, C_GREY).next_to(dots[i], UP, buff=0.1) for i, v in enumerate(pre)])
        segs = VGroup(*[Line(dots[i].get_center(), dots[i + 1].get_center(), color=C_BLUE if s[i] == "(" else C_ORANGE,
                             stroke_width=4) for i in range(n)])
        plab = M("pre", 22, C_GREY).move_to([px(0) - 0.75, py(1), 0])
        self.play(Create(base), FadeIn(plab), FadeIn(dots[0]), FadeIn(vals[0]), run_time=0.4)
        for i in range(n):
            self.play(Create(segs[i]), FadeIn(dots[i + 1]), FadeIn(vals[i + 1]), run_time=0.28)
        self.at("两条")
        x0 = 1.15
        c1 = VGroup(T("① 两端一样高", 24, C_YELLOW), M("pre[r] == pre[l-1]", 20, C_GREY)).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        c2 = VGroup(T("② 中间不跌破起点", 24, C_YELLOW), M("nxt[l-1] > r", 20, C_GREY)).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        conds = VGroup(c1, c2).arrange(RIGHT, buff=0.45, aligned_edge=UP).move_to([x0, 1.2, 0], aligned_edge=LEFT)
        self.play(FadeIn(c1[0]), FadeIn(c1[1]), run_time=0.5)
        self.at("跌破")
        self.play(FadeIn(c2[0]), run_time=0.5)
        self.at("单调栈")
        self.play(FadeIn(c2[1]), run_time=0.4)
        nl = M("nxt", 22, C_GREY).move_to([px(0) - 0.75, -2.55, 0])
        ncells = [None] * (n + 1)
        self.play(FadeIn(nl), run_time=0.3)
        stk_t = None
        for j, popped, stk in events:
            anims = [Indicate(dots[j], color=C_YELLOW, scale_factor=1.6)]
            for p in popped:
                t = M(str(j), 22, C_PURPLE).move_to([px(p), -2.55, 0])
                ncells[p] = t
                arc = CurvedArrow(dots[p].get_center() + DOWN * 0.12, dots[j].get_center() + DOWN * 0.12, angle=TAU / 8,
                                  color=C_PURPLE, stroke_width=2.5, tip_length=0.15)
                anims += [FadeIn(t, shift=DOWN * 0.1), ShowPassingFlash(arc, time_width=0.8)]
            st = M("栈 " + str(stk), 20, C_GREY).move_to([x0, 0.25, 0], aligned_edge=LEFT)
            anims.append(Transform(stk_t, st) if stk_t else FadeIn(st))
            stk_t = stk_t or st
            self.play(*anims, run_time=0.32)
        rest = [M(str(n + 1), 22, DIM).move_to([px(p), -2.55, 0]) for p in range(n + 1) if ncells[p] is None]
        assert [int(ncells[p].text) if ncells[p] else n + 1 for p in range(n + 1)] == nxt
        self.play(*[FadeIn(r) for r in rest], FadeOut(stk_t), run_time=0.3)
        it = iter(rest)
        nmob = [ncells[p] if ncells[p] is not None else next(it) for p in range(n + 1)]
        res_y = 0.25
        out_lines = VGroup()
        self.span = None
        keys = {(2, 5): "问二到五", (1, 5): "问一到五", (3, 4): "问三到四"}
        for qi, (l, r) in enumerate(D.SHOWN):
            ok, eq, nx = D.judge(s, l, r)
            self.at(keys[(l, r)])
            rect = Rectangle(width=(r - l + 1) * dx, height=py(2) - py(0) + 0.9, stroke_width=0).set_fill(C_BLUE, 0.12)
            rect.move_to([(px(l - 1) + px(r)) / 2, (py(0) + py(2)) / 2 + 0.05, 0])
            lvl = DashedLine([px(l - 1), py(pre[l - 1]), 0], [px(n) + 0.15, py(pre[l - 1]), 0], color=C_YELLOW, stroke_width=3)
            ends = VGroup(Circle(0.17, color=C_YELLOW, stroke_width=3).move_to(dots[l - 1]),
                          Circle(0.17, color=C_YELLOW if eq else C_RED, stroke_width=3).move_to(dots[r]))
            anims = [FadeIn(rect), Create(lvl), Create(ends)]
            if self.span:
                anims += [FadeOut(m_) for m_ in self.span]
            self.play(*anims, run_time=0.6)
            extra = VGroup()
            if eq:
                hit = Circle(0.2, color=C_PURPLE, stroke_width=4).move_to(dots[nx]) if nx <= n else VGroup()
                box_n = SurroundingRectangle(nmob[l - 1], color=C_PURPLE, buff=0.06)
                self.play(Create(hit), Create(box_n), run_time=0.45)
                extra.add(hit, box_n)
            if ok:
                msg = f"[{l}, {r}]：两端都是 {pre[r]}，nxt[{l - 1}] = {nx} > {r}，合法"
            elif not eq:
                msg = f"[{l}, {r}]：pre[{r}] = {pre[r]} ≠ pre[{l - 1}] = {pre[l - 1]}，不合法"
            else:
                msg = f"[{l}, {r}]：两端都是 {pre[r]}，nxt[{l - 1}] = {nx} ≤ {r}，不合法"
            line = T(msg, 20, C_GREEN if ok else C_RED).move_to([x0, res_y - 0.5 * qi, 0], aligned_edge=LEFT)
            out_lines.add(line)
            self.play(FadeIn(line, shift=LEFT * 0.15), run_time=0.5)
            self.span = [rect, lvl, ends, extra]
        assert [D.judge(s, l, r)[0] for l, r in D.SHOWN] == [True, False, False]
        self.at("预处理线性")
        cx_ = VGroup(T("预处理", 24), MathTex(r"O(n)", color=C_GREEN).scale(0.8), T("每问", 24),
                     MathTex(r"O(1)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.2)
        cx_.move_to([x0, res_y - 0.5 * len(D.SHOWN) - 0.2, 0], aligned_edge=LEFT)
        self.play(FadeIn(cx_, scale=1.1), *[FadeOut(m_) for m_ in self.span], run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        head = T("常见失分点", 32, C_YELLOW).move_to([0, 2.85, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)
        rows = [("边界下标", "T2 座位 1 / n、T5 只有一行", "n = 1 必测", "边界"),
                ("递归太深", "T3 一行全是 R", "显式维护 path 的循环", "递归太深"),
                ("O(n) 操作进循环", "T4 list.insert(0, x)", "两端进出用 deque", "线性操作"),
                ("每次询问重算", "T5 每次 BFS、T6 每次扫子串", "并查集 / 前缀和 + 单调栈", "每次询问")]
        tab = VGroup()
        for a, b, c, _ in rows:
            tab.add(VGroup(T(a, 26, C_RED), T(b, 22, C_GREY), T("→ " + c, 24, C_GREEN)))
        widths = [max(r[k].width for r in tab) for k in range(3)]
        xs = [-6.4, -6.4 + widths[0] + 0.5, -6.4 + widths[0] + widths[1] + 1.0]
        for i, r in enumerate(tab):
            y = 1.85 - 0.72 * i
            for k in range(3):
                r[k].move_to([xs[k] + r[k].width / 2, y, 0])
        if tab.width > 13.2:
            tab.scale_to_fit_width(13.2).move_to([0, tab.get_y(), 0])
        for r, (*_, key) in zip(tab, rows):
            self.at(key)
            self.play(FadeIn(r, shift=UP * 0.15), run_time=0.5)
        self.at("订正三步")
        steps = VGroup(T("订正：", 26, C_BLUE), T("分类", 26), T("→", 26, C_GREY), T("关掉题解，从空文件重写", 26),
                       T("→", 26, C_GREY), T("错误类型写进 cheat sheet", 26)).arrange(RIGHT, buff=0.22)
        if steps.width > 13.2:
            steps.scale_to_fit_width(13.2)
        steps.move_to([0, -1.55, 0])
        self.play(FadeIn(steps[:2]), run_time=0.5)
        self.at("关掉")
        self.play(FadeIn(steps[2:4]), run_time=0.5)
        self.at("小抄")
        self.play(FadeIn(steps[4:]), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 11 月月考讲评与阶段复习 · OpenJudge 31529–31534", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
