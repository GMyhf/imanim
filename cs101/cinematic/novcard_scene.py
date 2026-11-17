"""牌堆魔术：倒着撤销每一步（T4 M31532 精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。样例 1 正着表演的每一轮、样例 2 倒推的每一步牌堆、位置队列每一轮、
两步撤销写反的错误输出、list.insert 的搬动次数全部来自 novcarddata / novdata
（讲义 Python 参考代码原样；test_novcard.py 用暴力枚举排列、独立模拟对撞）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import novcarddata as C  # noqa: E402
import novdata as N  # noqa: E402
from cine import *  # noqa: E402,F403

C_ORANGE = "#FF9F43"
DIM = "#3a4050"


def M(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def mkcode(src, size=20):
    return Code(code_string=src, language="python", formatter_style="monokai", background="window",
                add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size})


def hl(code, k, col, sw=2.5):
    return SurroundingRectangle(code.code_lines[k], color=col, buff=(0.08, 0.04), stroke_width=sw)


def card(v, color=WHITE, s=1.0):
    box = RoundedRectangle(corner_radius=0.08 * s, width=0.7 * s, height=0.95 * s, stroke_color=color, stroke_width=3)
    box.set_fill(color, 0.15)
    return VGroup(box, M(str(v), int(30 * s), color).move_to(box))


def back(s=1.0):
    box = RoundedRectangle(corner_radius=0.08 * s, width=0.7 * s, height=0.95 * s, stroke_color=C_GREY, stroke_width=3)
    box.set_fill(C_GREY, 0.2)
    return VGroup(box, M("?", int(30 * s), C_GREY).move_to(box))


def val(c) -> int:
    return int(c[1].text)


class NovCardLesson(Lesson):
    def construct(self):
        for b in ("title", "rule", "undo", "sample2", "pos", "code", "bug", "cost", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    # ---------------------------------------------------------------- 工具
    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        hit = next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0), None)
        if hit is None and self.cue_times():
            print(f"[novcard] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
        return default if hit is None else hit

    def at(self, key):
        self.wait_until(self.cue_start(key, self.now))

    def cue_seq(self, keys):
        """按顺序找一串关键词所在字幕句的起点（后一个不早于前一个所在的句子），用于旁白里重复出现的说法。"""
        cues, out, k = self.cue_times(), [], 0
        for key in keys:
            j = next((i for i in range(k, len(cues)) if key in cues[i]["text"]), None)
            if j is None:
                print(f"[novcard] 找不到字幕关键词：{self.cur} / {key}", file=sys.stderr)
                out.append(None)
                continue
            out.append(cues[j]["start"])
            k = j
        return out

    def until(self, t):
        if t is not None:
            self.wait_until(t)

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def head(self, text, tag=""):
        g = VGroup(T(text, 32))
        if tag:
            g.add(T(tag, 22, C_GREY))
        g.arrange(RIGHT, buff=0.3)
        return g.move_to([-6.6 + g.width / 2, 2.95, 0])

    @staticmethod
    def rp(k, y, x0=-4.6, dx=0.9):
        return np.array([x0 + k * dx, y, 0])

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        kick = T("11 月月考讲评 · T4  M31532", 26, C_BLUE).move_to([0, 2.9, 0])
        title = T("牌堆魔术", 60).next_to(kick, DOWN, buff=0.25)
        self.play(FadeIn(kick), Write(title), run_time=1.2)
        self.at("一张一张")
        order = C.answer(C.SAMPLE1)
        rounds = C.forward_rounds(order)
        shown = [r["shown"] for r in rounds]
        assert shown == [1, 2, 3, 4]
        backs = VGroup(*[back() for _ in order]).arrange(RIGHT, buff=0.2).move_to([-3.0, 0.2, 0])
        lab = T("开头？", 26, C_GREY).next_to(backs, UP, buff=0.3)
        arr = Arrow([-0.9, 0.2, 0], [0.9, 0.2, 0], color=C_GREY, buff=0, stroke_width=5)
        alab = T("魔术", 22, C_GREY).next_to(arr, UP, buff=0.12)
        outs = VGroup(*[card(v, C_GREEN) for v in shown]).arrange(RIGHT, buff=0.2).move_to([3.2, 0.2, 0])
        olab = T("翻出", 26, C_GREEN).next_to(outs, UP, buff=0.3)
        self.play(FadeIn(backs), FadeIn(lab), GrowArrow(arr), FadeIn(alab), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(o, shift=UP * 0.2) for o in outs], lag_ratio=0.3), FadeIn(olab), run_time=1.4)
        self.at("怎么叠")
        self.play(*[Indicate(b, color=C_YELLOW) for b in backs], run_time=0.8)
        self.at("倒着做")
        sub = T("倒着做，把每一步撤销", 34, C_YELLOW).move_to([0, -1.8, 0])
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 题意 + 样例 1 正着表演
    def rule_beat(self):
        self.beat("rule")
        n = C.SAMPLE1
        order = C.answer(n)
        assert order == [4, 1, 3, 2]
        rounds = C.forward_rounds(order)
        h = self.head("题意", "n 张牌叠成一摞，重复 n 轮")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("先把顶牌")
        rule = VGroup(T("每轮：", 26, C_GREY), T("① 顶牌移到底", 26, C_TEAL), T("② 翻开顶牌拿走", 26, C_PURPLE)
                      ).arrange(RIGHT, buff=0.35)
        rule.move_to([-6.6 + rule.width / 2, 2.15, 0])
        self.play(FadeIn(rule, lag_ratio=0.2), run_time=0.9)
        self.at("要求")
        goal = T("要求翻出 1, 2, …, n，求开头从上到下的顺序", 24, C_YELLOW)
        goal.move_to([-6.6 + goal.width / 2, 1.5, 0])
        self.play(FadeIn(goal), run_time=0.6)
        self.at("样例一")
        y1 = -0.05
        samp = T("样例 1：n = 4", 26, C_BLUE)
        samp.move_to([-6.6 + samp.width / 2, 0.85, 0])
        deck = [card(v).move_to(self.rp(k, y1)) for k, v in enumerate(order)]
        topl = T("牌顶", 20, C_GREY).next_to(deck[0], DOWN, buff=0.15)
        botl = T("牌底", 20, C_GREY).next_to(deck[-1], DOWN, buff=0.15)
        self.play(FadeIn(samp), *[FadeIn(d, shift=DOWN * 0.2) for d in deck], FadeIn(topl), FadeIn(botl), run_time=0.8)
        y2 = -1.75
        outl = T("翻出：", 24, C_GREY).move_to([-5.6, y2, 0])
        self.at("正着表演")
        self.play(FadeIn(outl), run_time=0.4)
        words = ["一", "二", "三", "四"]
        keys = []
        for k, r in enumerate(rounds):
            keys += [("只剩一张" if k == n - 1 else f"{'零一二三四'[r['moved']]}移到底"), f"翻开{words[r['shown'] - 1]}"]
        ts = self.cue_seq(keys)
        got = []
        for k, r in enumerate(rounds):
            self.until(ts[2 * k])
            top, rest = deck[0], deck[1:]
            assert val(top) == r["moved"]
            deck = rest + [top]
            if rest:
                self.play(top.animate(path_arc=PI * 0.55).move_to(self.rp(len(deck) - 1, y1)),
                          *[d.animate.move_to(self.rp(i, y1)) for i, d in enumerate(rest)], run_time=0.55)
            else:
                self.play(Indicate(top, color=C_TEAL, scale_factor=1.08), run_time=0.5)
            assert [val(d) for d in deck] == r["after_move"]
            self.until(ts[2 * k + 1])
            top, deck = deck[0], deck[1:]
            assert val(top) == r["shown"]
            got.append(top)
            new = card(r["shown"], C_GREEN).move_to(self.rp(len(got) - 1, y2, x0=-4.2))
            extra = []
            if len(deck) >= 2:
                extra = [botl.animate.next_to(self.rp(len(deck) - 1, y1), DOWN, buff=0.15 + 0.475)]
            elif botl in self.mobjects:
                extra = [FadeOut(botl)]
            self.play(Transform(top, new), *[d.animate.move_to(self.rp(i, y1)) for i, d in enumerate(deck)],
                      *extra, run_time=0.5)
            if len(deck) < 2:
                self.remove(botl)
            assert [val(d) for d in deck] == r["after"]
        ok = T("正好 1 2 3 4", 26, C_GREEN).next_to(VGroup(*got), RIGHT, buff=0.5)
        self.play(FadeIn(ok, shift=LEFT * 0.15), FadeOut(topl), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 撤销顺序
    def undo_beat(self):
        self.beat("undo")
        h = self.head("已知结果求开头", "从最后一轮往前撤销")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("两件事")
        fx, bx, y0 = -5.0, 1.6, 1.85
        fwd = VGroup(T("正着（每轮）", 24, C_GREY), T("① 顶牌移到底", 26, C_TEAL), T("② 翻开顶牌拿走", 26, C_PURPLE)
                     ).arrange(DOWN, buff=0.28, aligned_edge=LEFT).move_to([fx, y0, 0], aligned_edge=LEFT)
        self.play(FadeIn(fwd), run_time=0.6)
        self.at("后做的先撤")
        bwd = VGroup(T("倒着（每轮）", 24, C_GREY), T("先撤销②：牌放回牌顶", 26, C_PURPLE),
                     T("再撤销①：底牌移回牌顶", 26, C_TEAL)).arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        bwd.move_to([bx, y0, 0], aligned_edge=LEFT)
        a1 = Arrow(fwd[2].get_right() + RIGHT * 0.1, bwd[1].get_left() + LEFT * 0.1, color=C_PURPLE, buff=0,
                   stroke_width=4, max_tip_length_to_length_ratio=0.12)
        a2 = Arrow(fwd[1].get_right() + RIGHT * 0.1, bwd[2].get_left() + LEFT * 0.1, color=C_TEAL, buff=0,
                   stroke_width=4, max_tip_length_to_length_ratio=0.12)
        self.play(FadeIn(bwd[0]), GrowArrow(a1), FadeIn(bwd[1], shift=RIGHT * 0.2), run_time=0.7)
        self.play(GrowArrow(a2), FadeIn(bwd[2], shift=RIGHT * 0.2), run_time=0.7)
        self.at("袜子")
        sock = VGroup(T("穿：袜子 → 鞋", 24, C_GREY), T("脱：鞋 → 袜子", 24, C_YELLOW)).arrange(RIGHT, buff=0.9)
        sock.move_to([0, 0.15, 0])
        self.play(FadeIn(sock[0]), run_time=0.4)
        self.play(FadeIn(sock[1], shift=LEFT * 0.2), run_time=0.5)
        # 小演示：样例 1 的最后一轮倒推（牌 1）
        st = N.cards_reverse_trace(C.SAMPLE1)[-1]
        prev = N.cards_reverse_trace(C.SAMPLE1)[-2]["moved"]
        assert st["card"] == 1 and st["put"] == [1] + prev
        y = -1.55
        self.at("翻开是")
        self.play(sock.animate.set_opacity(0.35), run_time=0.3)
        deck = [card(v, WHITE, 0.8).move_to(self.rp(k + 1, y, x0=-4.2, dx=0.72)) for k, v in enumerate(prev)]
        c1 = card(st["card"], C_PURPLE, 0.8).move_to([-4.2, y + 1.0, 0])
        l1 = T("撤销翻开", 24, C_PURPLE).move_to([-0.2, y + 0.45, 0])
        self.play(*[FadeIn(d) for d in deck], FadeIn(c1), run_time=0.5)
        self.play(c1.animate.move_to(self.rp(0, y, x0=-4.2, dx=0.72)), FadeIn(l1), run_time=0.7)
        deck = [c1] + deck
        assert [val(d) for d in deck] == st["put"]
        self.at("移到底是")
        bot = deck[-1]
        l2 = T("撤销移到底", 24, C_TEAL).move_to(l1.get_center() + DOWN * 0.7)
        tgt = bot.copy().move_to(self.rp(0, y, x0=-4.2, dx=0.72))
        tgt[0].set_stroke(C_TEAL)
        self.play(Transform(bot, tgt, path_arc=-PI * 0.55),
                  *[d.animate.move_to(self.rp(k + 1, y, x0=-4.2, dx=0.72)) for k, d in enumerate(deck[:-1])],
                  FadeIn(l2), run_time=0.8)
        deck = [bot] + deck[:-1]
        assert [val(d) for d in deck] == st["moved"] == C.answer(C.SAMPLE1)
        res = T("= 样例 1 的答案", 24, C_GREEN).next_to(l2, RIGHT, buff=0.4)
        self.play(FadeIn(res), run_time=0.4)
        self.at("从空牌堆")
        loop = M("for i = n, n-1, …, 1：先放牌 i，再移底牌", 22, C_YELLOW).move_to([0, -2.75, 0])
        self.play(FadeIn(loop, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 样例 2 完整倒推
    def sample2_beat(self):
        self.beat("sample2")
        n = C.SAMPLE2
        steps = N.cards_reverse_trace(n)
        assert N.run_io(N.solve_t4, f"{n}\n") == "3 1 5 2 4" == " ".join(map(str, steps[-1]["moved"]))
        h = self.head("样例 2：n = 5", "每行：放牌 i → 底牌回到牌顶")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        s, dx = 0.62, 0.52
        xa, xb = -4.9, 0.4
        ys = [2.05 - 0.95 * k for k in range(n)]
        cn = "零一二三四五"
        keys = []
        for k, stp in enumerate(steps):
            i = stp["card"]
            keys.append(f"放{cn[i]}")
            keys.append("不用特判" if k == 0 else ("底牌五回到顶" if k == 1 else "变成" + "".join(cn[v] for v in stp["moved"])))
        ts = self.cue_seq(keys)
        prev = []
        last = None
        for k, stp in enumerate(steps):
            y = ys[k]
            self.until(ts[2 * k])
            lab = M(f"i={stp['card']}", 22, C_YELLOW).move_to([-6.2, y, 0])
            put = [card(v, C_PURPLE if j == 0 else WHITE, s).move_to(self.rp(j, y, xa, dx)) for j, v in enumerate(stp["put"])]
            anims = [FadeIn(lab), FadeIn(put[0], shift=DOWN * 0.3)]
            anims += [TransformFromCopy(p, q) for p, q in zip(prev, put[1:])]
            self.play(*anims, run_time=0.55)
            assert [val(p) for p in put] == stp["put"]
            self.until(ts[2 * k + 1])
            arr = Arrow([xa + dx * n - 0.1, y, 0], [xb - 0.45, y, 0], color=C_GREY, buff=0, stroke_width=3,
                        max_tip_length_to_length_ratio=0.25)
            moved = [card(v, C_TEAL if j == 0 else WHITE, s) for j, v in enumerate(stp["moved"])]
            for j, m in enumerate(moved):
                m.move_to(self.rp(j, y, xb, dx))
            src = [put[-1]] + put[:-1]
            assert [val(p) for p in src] == stp["moved"]
            anims = [GrowArrow(arr), TransformFromCopy(src[0], moved[0], path_arc=-PI * 0.4)]
            anims += [TransformFromCopy(p, q) for p, q in zip(src[1:], moved[1:])]
            self.play(*anims, run_time=0.6)
            if k == 0:
                note = T("只有一张：底牌就是顶牌，不用特判", 22, C_GREEN).move_to([3.0 + 1.0, y, 0])
                note.move_to([xb + 0.6 + note.width / 2, y, 0])
                self.play(FadeIn(note), run_time=0.4)
            prev = moved
            last = moved
        self.at("和样例输出")
        box = SurroundingRectangle(VGroup(*last), color=C_YELLOW, buff=0.1)
        ok = T("= 样例输出 3 1 5 2 4", 24, C_GREEN).next_to(box, RIGHT, buff=0.3)
        self.play(Create(box), FadeIn(ok), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 另一种思路：正着模拟位置
    def pos_beat(self):
        self.beat("pos")
        n = C.SAMPLE2
        steps, deck = C.position_trace(n)
        assert deck == C.answer(n)
        h = self.head("另一种思路", "正着模拟「位置」")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        self.at("只看位置")
        why = T("移牌、翻牌只看位置，不看牌面：先追踪位置，最后填牌", 24, C_GREY)
        why.move_to([-6.6 + why.width / 2, 2.2, 0])
        self.play(FadeIn(why), run_time=0.6)
        self.at("排成队列")
        yq, ys = 0.9, -1.35
        qx, qdx = -4.2, 0.95
        qlab = T("位置队列", 22, C_GREY).move_to([-5.9, yq, 0])
        q = []
        for p in range(n):
            sq = Square(0.7, stroke_color=C_BLUE, stroke_width=2.5).set_fill(C_BLUE, 0.12)
            q.append(VGroup(sq, M(str(p), 26, C_BLUE).move_to(sq)).move_to(self.rp(p, yq, qx, qdx)))
        front = T("队首", 18, C_GREY).next_to(q[0], UP, buff=0.12)
        sx, sdx = -1.8, 1.0
        slab = T("牌堆", 22, C_GREY).move_to([-3.4, ys, 0])
        slots = VGroup(*[RoundedRectangle(corner_radius=0.08, width=0.7, height=0.95, stroke_color=DIM,
                                          stroke_width=2.5).move_to(self.rp(p, ys, sx, sdx)) for p in range(n)])
        sidx = VGroup(*[M(f"{p}号位", 16, C_GREY).next_to(slots[p], DOWN, buff=0.12) for p in range(n)])
        self.play(FadeIn(qlab), *[FadeIn(x) for x in q], FadeIn(front), FadeIn(slab), FadeIn(slots), FadeIn(sidx),
                  run_time=0.8)
        cn = "零一二三四五"
        keys = ["第一次弹出", "接着弹出", f"{cn[steps[2]['pos']]}号位填三", f"{cn[steps[3]['pos']]}号位填四",
                f"{cn[steps[4]['pos']]}号位填五"]
        self.until(self.cue_start("先把队首"))
        ts = self.cue_seq(keys)
        filled = []
        for k, stp in enumerate(steps):
            assert [val(x) for x in q] == stp["queue"]
            if len(q) > 1:
                top, rest = q[0], q[1:]
                q = rest + [top]
                self.play(top.animate(path_arc=PI * 0.55).move_to(self.rp(len(q) - 1, yq, qx, qdx)),
                          *[x.animate.move_to(self.rp(i, yq, qx, qdx)) for i, x in enumerate(rest)], run_time=0.45)
            assert [val(x) for x in q] == stp["rotated"]
            self.until(ts[k])
            top, q = q[0], q[1:]
            assert val(top) == stp["pos"]
            c = card(stp["k"], C_YELLOW).move_to(slots[stp["pos"]])
            self.play(top.animate.move_to(slots[stp["pos"]]).set_opacity(0), FadeIn(c),
                      *[x.animate.move_to(self.rp(i, yq, qx, qdx)) for i, x in enumerate(q)], run_time=0.55,
                      audit=False)
            self.remove(top)
            filled.append(c)
            if k + 1 < n:
                self.play(Indicate(c, color=C_YELLOW, scale_factor=1.06), run_time=0.3)
        self.at("拼起来")
        self.play(FadeOut(front), FadeOut(qlab), run_time=0.3)
        box = SurroundingRectangle(VGroup(slots, sidx), color=C_GREEN, buff=0.12)
        ok = T("还是 3 1 5 2 4，两种做法都是 O(n)", 24, C_GREEN).move_to([0, 0.4, 0])
        self.play(Create(box), FadeIn(ok), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 讲义代码对照
    def code_beat(self):
        self.beat("code")
        h = self.head("讲义代码", "Python")
        code = mkcode(C.CODE, 20)
        code.move_to([6.6 - code.width / 2, 2.45 - code.height / 2, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(code), run_time=0.7)
        # 片中小演示：样例 2 倒推 i = 2 这一轮
        stp = next(s for s in N.cards_reverse_trace(C.SAMPLE2) if s["card"] == 2)
        before = stp["put"][1:]
        y, x0, dx = 0.45, -6.0, 0.85
        self.at("倒数")
        box = hl(code, 3, C_YELLOW)
        self.play(Create(box), run_time=0.5)
        deck = [card(v).move_to(self.rp(k + 1, y, x0, dx)) for k, v in enumerate(before)]
        dlab = T("dq：左端是牌顶，右端是牌底", 20, C_GREY).move_to([x0 - 0.35, y - 0.8, 0], aligned_edge=LEFT)
        il = M("i = 2", 22, C_YELLOW).move_to([x0 + 1.4, y + 1.25, 0])
        self.play(FadeIn(dlab), FadeIn(il), *[FadeIn(d) for d in deck], run_time=0.5)
        self.at("第一行")
        c = card(stp["card"], C_PURPLE).move_to(self.rp(0, y + 1.25, x0, dx))
        nx = code.get_left()[0]
        note1 = T("左端加入 = 放回牌顶", 24, C_PURPLE).move_to([nx, -1.15, 0], aligned_edge=LEFT)
        self.play(Transform(box, hl(code, 4, C_PURPLE)), FadeIn(c), run_time=0.5)
        self.play(c.animate.move_to(self.rp(0, y, x0, dx)), FadeIn(note1), run_time=0.6)
        deck = [c] + deck
        assert [val(d) for d in deck] == stp["put"]
        self.at("第二行")
        bot = deck[-1]
        note2 = T("右端弹出，再左端加入 = 底牌回到牌顶", 24, C_TEAL).move_to([nx, -1.8, 0], aligned_edge=LEFT)
        self.play(Transform(box, hl(code, 5, C_TEAL)), run_time=0.4)
        self.play(bot.animate.shift(UP * 1.25), run_time=0.4)
        self.play(bot.animate.move_to(self.rp(0, y + 1.25, x0, dx)),
                  *[d.animate.move_to(self.rp(k + 1, y, x0, dx)) for k, d in enumerate(deck[:-1])], run_time=0.6)
        self.play(bot.animate.move_to(self.rp(0, y, x0, dx)), FadeIn(note2), run_time=0.4)
        deck = [bot] + deck[:-1]
        assert [val(d) for d in deck] == stp["moved"]
        self.at("打印")
        out = N.run_io(N.solve_t4, f"{C.SAMPLE2}\n")
        res = VGroup(M("n = 5 → 输出", 22, C_GREY), M(out, 26, C_GREEN)).arrange(RIGHT, buff=0.3)
        res.move_to([nx, -2.5, 0], aligned_edge=LEFT)
        self.play(Transform(box, hl(code, 6, C_GREEN)), FadeIn(res), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 典型错误：两步撤销写反
    def bug_beat(self):
        self.beat("bug")
        n = C.SAMPLE1
        h = self.head("典型错误", "两步撤销写反")
        bad_src = ("for i in range(n, 0, -1):\n"
                   "    dq.appendleft(dq.pop())  # 先移底牌\n"
                   "    dq.appendleft(i)  # 再放回牌 i")
        code = mkcode(bad_src, 19)
        code.move_to([-6.6 + code.width / 2, 2.45 - code.height / 2, 0])
        self.play(FadeIn(h, shift=DOWN * 0.2), FadeIn(code), run_time=0.7)
        rx = 1.4
        self.at("直接报错")
        try:
            C.swapped_naive(n)
            msg = None
        except IndexError as e:
            msg = str(e)
        assert msg == "pop from an empty deque"
        err = VGroup(T("第一轮牌堆是空的", 22, C_GREY), M(f"IndexError: {msg}", 20, C_RED)).arrange(DOWN, buff=0.15,
                                                                                                    aligned_edge=LEFT)
        err.move_to([rx + err.width / 2, 2.3, 0])
        self.play(Create(hl(code, 1, C_RED)), FadeIn(err), run_time=0.6)
        self.at("加个判空")
        good_src = ("for i in range(n, 0, -1):\n"
                    "    if dq:\n"
                    "        dq.appendleft(dq.pop())\n"
                    "    dq.appendleft(i)")
        code2 = mkcode(good_src, 19)
        code2.move_to([-6.6 + code2.width / 2, 2.45 - code2.height / 2, 0])
        old = [m for m in self.mobjects if m not in self.subs and m not in (h, err)]
        self.play(*[FadeOut(m) for m in old], FadeIn(code2), err.animate.set_opacity(0.3), run_time=0.6)
        self.remove(*old)
        wrong = C.swapped_guarded(n)
        right = C.answer(n)
        assert wrong == [1, 3, 2, 4] and right == [4, 1, 3, 2]
        self.at("却输出")
        outw = VGroup(M(f"n = {n} → 输出", 22, C_GREY), M(" ".join(map(str, wrong)), 26, C_RED)).arrange(RIGHT, buff=0.3)
        outw.move_to([rx + outw.width / 2, 1.2, 0])
        self.play(FadeOut(err), FadeIn(outw), run_time=0.5)
        # 正着验：翻出顺序
        self.at("正着验")
        y1, y2 = -0.8, -2.15
        deck = [card(v, WHITE, 0.8).move_to(self.rp(k, y1, -5.4, 0.72)) for k, v in enumerate(wrong)]
        vl = T("正着验", 22, C_GREY).move_to([-6.1, y1 + 0.75, 0])
        ol = T("翻出", 22, C_GREY).move_to([-6.1, y2, 0])
        self.play(FadeIn(vl), FadeIn(ol), *[TransformFromCopy(outw[1], d) for d in deck], run_time=0.6)
        rounds = C.forward_rounds(wrong)
        got = []
        for r in rounds:
            top, rest = deck[0], deck[1:]
            deck = rest + [top]
            if rest:
                self.play(top.animate(path_arc=PI * 0.55).move_to(self.rp(len(deck) - 1, y1, -5.4, 0.72)),
                          *[d.animate.move_to(self.rp(i, y1, -5.4, 0.72)) for i, d in enumerate(rest)], run_time=0.3)
            top, deck = deck[0], deck[1:]
            ok = r["shown"] == len(got) + 1
            new = card(r["shown"], C_GREEN if ok else C_RED, 0.8).move_to(self.rp(len(got), y2, -5.4, 0.72))
            got.append(top)
            self.play(Transform(top, new), *[d.animate.move_to(self.rp(i, y1, -5.4, 0.72)) for i, d in enumerate(deck)],
                      run_time=0.3)
        shown = [r["shown"] for r in rounds]
        assert shown == [3, 4, 2, 1]
        xm = T("不是 1 2 3 4", 24, C_RED).next_to(VGroup(*got), RIGHT, buff=0.4)
        self.play(FadeIn(xm), run_time=0.4)
        # 牌 i 的位置：正确是第二张，写反是第一张
        self.at("本该排在")
        cmp_ = VGroup()
        for lab, seq, col in (("正确", right, C_GREEN), ("写反", wrong, C_RED)):
            row = VGroup(T(lab, 22, col), *[card(v, C_YELLOW if v == 1 else WHITE, 0.6) for v in seq])
            row.arrange(RIGHT, buff=0.15)
            cmp_.add(row)
        cmp_.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([rx, -0.55, 0], aligned_edge=LEFT)
        assert right.index(1) == 1 and wrong.index(1) == 0
        self.play(FadeIn(cmp_), run_time=0.6)
        tip = T("牌 1 该在第二张：第一张移到底，它正好被翻开", 22, C_YELLOW)
        tip.move_to([rx + tip.width / 2, -2.15, 0])
        if tip.get_right()[0] > 6.7:
            tip.scale_to_fit_width(6.7 - rx)
            tip.move_to([rx + tip.width / 2, -2.15, 0])
        self.play(FadeIn(tip), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 复杂度：deque vs list.insert
    def cost_beat(self):
        self.beat("cost")
        h = self.head("复杂度", "两端都要进出")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        cells = [5, 2, 4, 3]
        w = 0.62

        def row(y, col):
            g = VGroup(*[VGroup(Square(w, stroke_color=col, stroke_width=2.5).set_fill(col, 0.12),
                                M(str(v), 22, col)) for v in cells])
            for k, c in enumerate(g):
                c.move_to([-3.2 + k * (w + 0.08), y, 0])
                c[1].move_to(c[0])
            return g
        ya, yb = 1.75, 0.35
        self.at("双端队列两端")
        la = M("deque", 24, C_GREEN).move_to([-5.6, ya, 0])
        ra = row(ya, C_GREEN)
        new_a = VGroup(Square(w, stroke_color=C_YELLOW, stroke_width=2.5).set_fill(C_YELLOW, 0.12),
                       M("1", 22, C_YELLOW)).move_to(ra[0].get_center() + LEFT * (w + 0.08) + UP * 0.8)
        new_a[1].move_to(new_a[0])
        ta = VGroup(M("appendleft", 20, C_GREEN), MathTex(r"O(1)", color=C_GREEN).scale(0.8)).arrange(RIGHT, buff=0.3)
        ta.move_to([0.6 + ta.width / 2, ya, 0])
        self.play(FadeIn(la), FadeIn(ra), FadeIn(new_a), run_time=0.5)
        self.play(new_a.animate.shift(DOWN * 0.8), FadeIn(ta), run_time=0.6)
        self.at("换成列表")
        lb = M("list", 24, C_RED).move_to([-5.6, yb, 0])
        rb = row(yb, C_RED)
        new_b = new_a.copy().move_to(rb[0].get_center() + UP * 0.8)
        self.play(FadeIn(lb), FadeIn(rb), FadeIn(new_b), run_time=0.5)
        tb = VGroup(M("insert(0, x)", 20, C_RED), MathTex(r"O(n)", color=C_RED).scale(0.8)).arrange(RIGHT, buff=0.3)
        tb.move_to([0.6 + tb.width / 2, yb, 0])
        self.at("全部挪一位")
        self.play(*[c.animate.shift(RIGHT * (w + 0.08)) for c in rb], run_time=0.7)
        self.play(new_b.animate.shift(DOWN * 0.8), FadeIn(tb), run_time=0.5)
        n = C.N_MAX
        dq, mv = C.DEQUE_OPS_BIG, C.LIST_MOVES_BIG
        assert dq == 600000 and mv == n * (n - 1) and round(mv / 1e10) == 4
        self.at("二十万")
        nl = T("n = 2×10⁵", 26, C_YELLOW).move_to([-6.6, -0.75, 0], aligned_edge=LEFT)
        self.play(FadeIn(nl), run_time=0.4)
        y1, y2 = -1.5, -2.35
        r1 = VGroup(M("deque", 22, C_GREEN), T("每轮 3 次两端操作，共", 22, C_GREY),
                    MathTex(r"3n = 6\times10^{5}", color=C_GREEN).scale(0.75), T("次", 22, C_GREY)).arrange(RIGHT, buff=0.2)
        r1.move_to([-6.6, y1, 0], aligned_edge=LEFT)
        self.play(FadeIn(r1, shift=UP * 0.1), run_time=0.5)
        self.at("光挪元素")
        r2 = VGroup(M("list ", 22, C_RED), T("挪动元素", 22, C_GREY),
                    MathTex(r"2(0+1+\cdots+(n-1)) = n(n-1)\approx 4\times10^{10}", color=C_RED).scale(0.75),
                    T("次", 22, C_GREY)).arrange(RIGHT, buff=0.2)
        r2.move_to([-6.6, y2, 0], aligned_edge=LEFT)
        self.play(FadeIn(r2, shift=UP * 0.1), run_time=0.5)
        self.at("超时")
        tle = T("TLE", 30, C_RED).next_to(tb, RIGHT, buff=0.5)
        self.play(FadeIn(tle, scale=1.3), run_time=0.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        h = self.head("回顾", "牌堆魔术")
        self.play(FadeIn(h, shift=DOWN * 0.2), run_time=0.5)
        items = [("已知结果求开头", "倒着撤销，后做的先撤", "回顾", C_YELLOW),
                 ("每轮撤销", "牌放回牌顶 → 底牌移回牌顶", "每一轮", C_PURPLE),
                 ("数据结构", "两端进出用 deque，整体 O(n)", "两端进出", C_GREEN),
                 ("验算", "正着模拟一遍，翻出 1 2 … n", "写完", C_BLUE)]
        y = 1.8
        for a, b, key, col in items:
            self.at(key)
            g = VGroup(T(a, 26, col), T(b, 26)).arrange(RIGHT, buff=0.5)
            g[1].move_to([-2.4 + g[1].width / 2, y, 0])
            g[0].move_to([-6.2 + g[0].width / 2, y, 0])
            self.play(FadeIn(g, shift=RIGHT * 0.2), run_time=0.6)
            y -= 1.1
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()
