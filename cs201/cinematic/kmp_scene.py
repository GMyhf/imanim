"""KMP：目标指针不回头（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。朴素匹配、lps 表的构造、KMP 匹配、
指针曲线与最小循环节的每一步都来自 kmpdata（讲义代码原样插桩；test_kmp.py 对撞讲义输出、str.find 与暴力）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmpdata as K  # noqa: E402
from cine import *  # noqa: E402,F403

C_OK, C_BAD, C_HI = C_GREEN, C_RED, C_YELLOW


def cell_row(s, x0, y, w=0.8, size=34, color=C_GREY):
    """一排字符格：每格 VGroup(方框, 字符)。方框只描边，避免盖住字。"""
    row = VGroup()
    for k, ch in enumerate(s):
        sq = Square(w * 0.9, stroke_color=color, stroke_width=2.5).set_fill(color, 0.0)
        lab = Text(ch, font=MONO, font_size=size, color=WHITE)
        sq.move_to([x0 + k * w, y, 0])
        lab.move_to(sq)
        row.add(VGroup(sq, lab))
    return row


def idx_row(n, x0, y, w=0.8, size=18, start=0):
    return VGroup(*[Text(str(k), font=MONO, font_size=size, color=C_GREY).move_to([x0 + k * w, y, 0])
                    for k in range(start, n)])


def tint(cell, color, op=0.35):
    """把一格染成比较结果的颜色（返回动画）。"""
    return cell[0].animate.set_stroke(color, 3.5).set_fill(color, op)


def untint(cell):
    return cell[0].animate.set_stroke(C_GREY, 2.5).set_fill(C_GREY, 0.0)


def move_cell(c, pos, op=None):
    """把一格移到 pos；op 给定时只改描边与字符的透明度（填充保持原样，不会变成实心）。"""
    c.generate_target()
    c.target.move_to(pos)
    if op is not None:
        c.target[0].set_stroke(opacity=op)
        if op == 0:
            c.target[0].set_fill(opacity=0)
        c.target[1].set_opacity(op)
    return MoveToTarget(c)


def pointer(color=WHITE, down=True):
    tri = Triangle(color=color).scale(0.13).set_fill(color, 1).set_stroke(width=0)
    return tri.rotate(PI) if down else tri


def counter(label, x, y, color=WHITE, size=28):
    lab = T(label, size, C_GREY)
    num = DecimalNumber(0, num_decimal_places=0, font_size=size + 8, color=color)
    lab.move_to([x, y, 0], aligned_edge=RIGHT)
    num.next_to(lab, RIGHT, buff=0.2)
    return VGroup(lab, num)


class KMPLesson(Lesson):
    def construct(self):
        for b in ("title", "naive", "waste", "lps", "build", "search", "all", "linear", "period", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def fade_all(self, rt=0.6):
        keep = set(map(id, self.subs))
        mobs = [m for m in self.mobjects if id(m) not in keep]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=rt, audit=False)

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        s = "GATTACAGATCGGATTACAGGT"
        row = cell_row(s, -6.3, -1.3, w=0.6, size=26)
        for c in row:
            c[1].set_color(C_GREY)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.15) for c in row], lag_ratio=0.04), run_time=1.6)
        pat = cell_row("GATTACA", -6.3, -0.45, w=0.6, size=26, color=C_BLUE)
        self.play(FadeIn(pat, shift=DOWN * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("最直接的办法", self.now))
        for s0 in (1, 2, 3, 4):
            self.play(pat.animate.shift(RIGHT * 0.6), run_time=0.45)
        self.wait_until(self.cue_start("克努特", self.now))
        names = T("克努特 · 莫里斯 · 普拉特", 30, C_GREY).move_to([0, 1.0, 0])
        ptr = pointer(C_HI).next_to(row[0], UP, buff=1.05)
        self.play(FadeIn(names, shift=UP * 0.2), pat.animate.move_to(row[12:19]).shift(UP * 0.85),
                  FadeIn(ptr), run_time=1.0)
        self.play(ptr.animate.next_to(row[18], UP, buff=1.05), run_time=3.0, rate_func=linear)
        self.wait_until(self.cue_start("这就是", self.now))
        title = T("KMP", 96).move_to([0, 2.5, 0])
        sub = T("目标指针不回头", 36, C_HI).next_to(title, DOWN, buff=0.15)
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), names.animate.shift(DOWN * 0.2).set_opacity(0.6),
                  run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 朴素匹配
    def naive_beat(self):
        self.beat("naive")
        w, x0 = 0.9, -4.2
        tt = cell_row(K.SHORT_T, x0, 1.1, w=w)
        pp = cell_row(K.SHORT_P, x0, -0.05, w=w, color=C_BLUE)
        ti = idx_row(len(K.SHORT_T), x0, 1.85, w=w)
        lt = T("目标", 26, C_GREY).next_to(tt, LEFT, buff=0.35)
        lp = T("模式", 26, C_BLUE).move_to([lt.get_x(), -0.05, 0])
        cnt = counter("比较次数", 4.6, 2.6)
        self.play(FadeIn(tt), FadeIn(ti), FadeIn(lt), run_time=0.7)
        self.play(FadeIn(pp, shift=DOWN * 0.2), FadeIn(lp), FadeIn(cnt), run_time=0.7)
        dots = VGroup()
        tally = [0] * len(K.SHORT_T)
        ev = K.SHORT_NAIVE
        self.wait_until(self.cue_start("第一趟", self.now))
        n = 0

        def compare(j, i, eq, rt):
            nonlocal n
            n += 1
            col = C_OK if eq else C_BAD
            d = Dot(radius=0.07, color=col).move_to([x0 + j * w, -0.75 - 0.22 * tally[j], 0])
            tally[j] += 1
            dots.add(d)
            self.play(tint(tt[j], col), tint(pp[i], col), FadeIn(d, scale=0.5),
                      ChangeDecimalToValue(cnt[1], n), run_time=rt)
        # 第一趟：五次比较
        for (j, i, eq) in ev[:5]:
            compare(j, i, eq, 0.85)
        self.wait_until(self.cue_start("朴素算法把模式右移", self.now))
        back = CurvedArrow(ti[4].get_top() + UP * 0.08, ti[1].get_top() + UP * 0.08, angle=PI * 0.6,
                           color=C_BAD, stroke_width=5)
        back_t = T("目标指针 4 → 1", 24, C_BAD).move_to([x0 + 2.5 * w, 3.45, 0])
        self.play(Create(back), FadeIn(back_t), run_time=1.0)
        self.play(*[untint(c) for c in tt], *[untint(c) for c in pp], run_time=0.3)
        self.play(pp.animate.shift(RIGHT * w), run_time=0.6)
        self.wait_until(self.cue_start("第二趟", self.now))
        j, i, eq = ev[5]
        compare(j, i, eq, 0.7)
        self.play(*[untint(c) for c in tt], *[untint(c) for c in pp], FadeOut(back), FadeOut(back_t), run_time=0.3)
        self.play(pp.animate.shift(RIGHT * w), run_time=0.4)
        for (j, i, eq) in ev[6:]:
            compare(j, i, eq, 0.6)
        found = T(f"起点 {K.SHORT_NAIVE_RET}", 26, C_OK).next_to(pp, RIGHT, buff=0.35)
        self.play(FadeIn(found), run_time=0.4)
        self.wait_until(self.cue_start("一共比较", self.now))
        twice = VGroup(*[d for d in dots if d.get_y() < -0.85])
        self.play(Indicate(cnt[1], color=C_HI), Indicate(twice, color=C_HI, scale_factor=1.6), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 浪费在哪
    def waste_beat(self):
        self.beat("waste")
        w, x0 = 0.9, -4.2
        tt = cell_row(K.SHORT_T, x0, 2.6, w=w)
        pp = cell_row(K.SHORT_P, x0, 1.7, w=w, color=C_BLUE)
        for k in range(4):
            tt[k][0].set_stroke(C_OK, 3.5).set_fill(C_OK, 0.3)
            pp[k][0].set_stroke(C_OK, 3.5).set_fill(C_OK, 0.3)
        tt[4][0].set_stroke(C_BAD, 3.5).set_fill(C_BAD, 0.3)
        pp[4][0].set_stroke(C_BAD, 3.5).set_fill(C_BAD, 0.3)
        self.play(FadeIn(tt), FadeIn(pp), run_time=0.7)
        self.wait_until(self.cue_start("失配之前", self.now))
        known = cell_row("abab", -5.6, -0.6, w=0.7, size=30, color=C_OK)
        self.play(TransformFromCopy(VGroup(*[c[1] for c in tt[:4]]), VGroup(*[c[1] for c in known])),
                  FadeIn(VGroup(*[c[0] for c in known])), run_time=1.0)
        self.wait_until(self.cue_start("真前缀", self.now))
        pre, suf, same = K.borders("abab")
        ph = T("真前缀", 24, C_GREY).move_to([-0.8, 0.1, 0])
        sh = T("真后缀", 24, C_GREY).move_to([2.6, 0.1, 0])
        prs = VGroup(*[Text(" ".join(p), font=MONO, font_size=28).move_to([-0.8, -0.5 - 0.55 * k, 0])
                       for k, p in enumerate(pre)])
        sfs = VGroup(*[Text(" ".join(s), font=MONO, font_size=28).move_to([2.6, -0.5 - 0.55 * k, 0])
                       for k, s in enumerate(suf)])
        self.play(FadeIn(ph), LaggedStart(*[FadeIn(p, shift=RIGHT * 0.2) for p in prs], lag_ratio=0.5),
                  run_time=1.8)
        self.play(FadeIn(sh), LaggedStart(*[FadeIn(s, shift=LEFT * 0.2) for s in sfs], lag_ratio=0.5),
                  run_time=1.8)
        k = same[-1] - 1
        link = Line(prs[k].get_right() + RIGHT * 0.2, sfs[k].get_left() + LEFT * 0.2, color=C_HI, stroke_width=4)
        best = T(f"最长相等：长度 {same[-1]}", 26, C_HI).move_to([0.9, -2.45, 0])
        self.play(prs[k].animate.set_color(C_HI), sfs[k].animate.set_color(C_HI), Create(link), run_time=0.8)
        self.play(FadeIn(best, shift=UP * 0.2), run_time=0.5)
        # 已知串上画出：前两个 = 后两个
        b1 = Brace(known[:2], DOWN, color=C_HI, buff=0.08)
        b2 = Brace(known[2:], DOWN, color=C_HI, buff=0.08)
        self.play(FadeIn(b1), FadeIn(b2), run_time=0.5)
        self.wait_until(self.cue_start("所以模式可以", self.now))
        shift = T(f"右移 4 − {same[-1]} = {4 - same[-1]} 位", 28, C_HI).move_to([4.8, 1.7, 0])
        self.play(FadeIn(shift), run_time=0.5)
        self.play(*[untint(c) for c in pp], *[untint(c) for c in tt[4:]], run_time=0.4)
        self.play(pp.animate.shift(RIGHT * w * (4 - same[-1])), run_time=1.0)
        for c in pp[:2]:
            c[0].set_stroke(C_HI, 3.5)
        self.play(*[c[0].animate.set_fill(C_HI, 0.3) for c in pp[:2]],
                  *[tt[2 + q][0].animate.set_stroke(C_HI, 3.5).set_fill(C_HI, 0.3) for q in range(2)], run_time=0.6)
        self.wait_until(self.cue_start("这两个字符不用再比", self.now))
        skip = T("不用再比", 22, C_HI).next_to(pp[:2], DOWN, buff=0.15)
        go = pointer(C_OK, down=False).next_to(pp[2], DOWN, buff=0.15)
        go_t = T("接着比", 22, C_OK).next_to(go, RIGHT, buff=0.1)
        self.play(FadeIn(skip), FadeIn(go), FadeIn(go_t), run_time=0.6)
        self.play(tint(pp[2], C_OK), tint(tt[4], C_OK), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- lps 表的定义
    def lps_beat(self):
        self.beat("lps")
        P = K.LONG_P
        w, x0 = 0.8, -4.2
        self.pw, self.px0 = w, x0
        pp = cell_row(P, x0, 2.0, w=w, color=C_BLUE)
        pi = idx_row(len(P), x0, 2.7, w=w)
        lab = T("lps", 28, C_HI).move_to([x0 - 1.0, 0.9, 0])
        boxes = VGroup(*[Square(w * 0.9, stroke_color=C_HI, stroke_width=2, stroke_opacity=0.6)
                         .move_to([x0 + k * w, 0.9, 0]) for k in range(len(P))])
        self.play(FadeIn(pp), FadeIn(pi), run_time=0.8)
        self.play(FadeIn(lab), LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.08), run_time=1.2)
        self.wait_until(self.cue_start("表里第", self.now))
        defin = T("第 i 格 = 前 i+1 个字符里，最长的「相等真前缀 = 真后缀」的长度", 26).move_to([0, -0.5, 0])
        self.play(FadeIn(defin, shift=UP * 0.2), run_time=0.8)
        L = K.LONG_LPS[-1]
        n = len(P)
        bp = Brace(pp[:L], DOWN, color=C_HI, buff=0.06)
        bs = Brace(pp[n - L:], DOWN, color=C_HI, buff=0.06)
        whole = SurroundingRectangle(pp, color=WHITE, buff=0.08, stroke_width=2)
        self.play(Create(whole), run_time=0.6)
        self.play(FadeIn(bp), FadeIn(bs), *[pp[k][0].animate.set_fill(C_HI, 0.25) for k in
                                           list(range(L)) + list(range(n - L, n))], run_time=0.9)
        v = Text(str(L), font=MONO, font_size=32, color=C_HI).move_to(boxes[-1])
        self.play(FadeIn(v, scale=1.4), run_time=0.5)
        self.wait_until(self.cue_start("真，就是", self.now))
        no = T("不能取整个串本身", 24, C_BAD).next_to(whole, RIGHT, buff=0.2).shift(UP * 0.2)
        no.move_to([5.4, 2.0, 0])
        self.play(FadeIn(no), Indicate(whole, color=C_BAD), run_time=0.9)
        self.wait_until(self.cue_start("只依赖模式", self.now))
        note = T("只依赖模式，与目标串无关：算一次，反复用", 26, C_TEAL).move_to([0, -1.5, 0])
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(defin, note, no, whole, bp, bs, v)),
                  *[pp[k][0].animate.set_fill(C_BLUE, 0) for k in range(n)], run_time=0.6)
        self.lps_obj = (pp, pi, lab, boxes)

    # ---------------------------------------------------------------- 模式自己匹配自己
    def build_beat(self):
        self.beat("build")
        pp, pi, lab, boxes = self.lps_obj
        P, w, x0 = K.LONG_P, self.pw, self.px0
        cy = 0.95
        self.play(lab.animate.move_to([x0 - 1.0, -0.7, 0]), boxes.animate.shift(DOWN * 1.6), run_time=0.8)
        z = Text("0", font=MONO, font_size=30, color=C_HI).move_to(boxes[0])
        self.play(FadeIn(z), run_time=0.4)
        vals = [z]
        copy = cell_row(P, x0, cy, w=w, color=C_PURPLE)
        for c in copy:
            c[0].set_stroke(opacity=0)
            c[1].set_opacity(0)
        copy_lab = T("副本", 24, C_PURPLE).move_to([x0 - 1.0, cy, 0])
        len_box = counter("长度", 5.0, 0.2, color=C_PURPLE)
        steps, lps = K.lps_trace(P)

        def place(i, length, rt):
            """副本右移到「副本[length] 正对 模式[i]」，只显示副本里 ≤ length 的格。"""
            off = i - length
            anims = []
            for k, c in enumerate(copy):
                target = np.array([x0 + (k + off) * w, cy, 0])
                anims.append(move_cell(c, target, 1.0 if k <= length else 0.0))
            return AnimationGroup(*anims, ChangeDecimalToValue(len_box[1], length), run_time=rt)

        self.wait_until(self.cue_start("下面这一行", self.now))
        self.play(FadeIn(copy_lab), FadeIn(len_box), place(1, 0, 0.9))
        sched = {1: self.cue_start("下一个字符相等", self.now), 4: self.cue_start("到了 C", None),
                 5: self.cue_start("之后 A B", None)}
        slow = 0.75
        for st in steps:
            i = st["i"]
            if i in sched and sched[i]:
                self.wait_until(sched[i])
            fast = i >= 5
            rt = 0.4 if fast else slow
            for q, (length, eq) in enumerate(st["seq"]):
                self.play(place(i, length, rt))
                col = C_OK if eq else C_BAD
                self.play(tint(pp[i], col), tint(copy[length], col), run_time=rt)
                if not eq and length > 0:
                    nl = lps[length - 1]
                    hint = T(f"退到 lps[{length - 1}] = {nl}", 24, C_PURPLE).next_to(boxes[length - 1], DOWN,
                                                                                     buff=0.25)
                    self.play(Indicate(boxes[length - 1], color=C_PURPLE), FadeIn(hint), run_time=0.8)
                    self.play(FadeOut(hint), untint(pp[i]), untint(copy[length]), run_time=0.4)
            v = Text(str(st["lps"]), font=MONO, font_size=30, color=C_HI).move_to(boxes[i])
            self.play(FadeIn(v, scale=1.4), untint(pp[i]), *[untint(c) for c in copy], run_time=rt)
            vals.append(v)
        self.wait_until(self.cue_start("整张表只扫", self.now))
        self.play(Indicate(VGroup(*vals), color=C_HI, scale_factor=1.1), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 用表匹配
    def search_beat(self):
        self.beat("search")
        w, x0 = 0.9, -4.6
        T_, P_ = K.SHORT_T, K.SHORT_P
        lps = K.compute_lps(P_)
        tt = cell_row(T_, x0, 1.3, w=w)
        pp = cell_row(P_, x0, 0.1, w=w, color=C_BLUE)
        ti = idx_row(len(T_), x0, 2.0, w=w)
        tb = cell_row(P_, 3.0, -1.55, w=0.7, size=28, color=C_BLUE)
        tl = VGroup(*[Text(str(v), font=MONO, font_size=26, color=C_HI).move_to([3.0 + k * 0.7, -2.3, 0])
                      for k, v in enumerate(lps)])
        tlab = T("lps", 24, C_HI).next_to(tl, LEFT, buff=0.3)
        tidx = idx_row(len(P_), 3.0, -0.95, w=0.7, size=16)
        cnt = counter("比较次数", 4.6, 2.6)
        self.play(FadeIn(tt), FadeIn(ti), FadeIn(pp), FadeIn(tb), FadeIn(tl), FadeIn(tlab), FadeIn(tidx),
                  FadeIn(cnt), run_time=0.9)
        ip = pointer(C_HI).next_to(ti[0], UP, buff=0.12)
        il = T("i", 26, C_HI).next_to(ip, RIGHT, buff=0.1)
        jp = pointer(C_TEAL, down=False).next_to(pp[0], DOWN, buff=0.12)
        jl = T("j", 26, C_TEAL).next_to(jp, RIGHT, buff=0.1)
        il.add_updater(lambda m: m.next_to(ip, RIGHT, buff=0.1))
        jl.add_updater(lambda m: m.next_to(jp, RIGHT, buff=0.1))
        self.wait_until(self.cue_start("目标指针 i", self.now))
        self.play(FadeIn(ip), FadeIn(il), run_time=0.5)
        self.play(FadeIn(jp), FadeIn(jl), run_time=0.5)
        trail = VGroup()
        n = 0
        self.wait_until(self.cue_start("前四个字符", self.now))
        state = {"i": 0, "j": 0}

        rt = 0.8
        for e in K.SHORT_KMP:
            if e[0] == "cmp":
                _, i, j, eq = e
                n += 1
                off = i - j
                pp_target = x0 + off * w
                col = C_OK if eq else C_BAD
                self.play(pp.animate.set_x(pp_target + (len(P_) - 1) * w / 2),
                          ip.animate.next_to(ti[i], UP, buff=0.12),
                          jp.animate.move_to([x0 + i * w, pp.get_bottom()[1] - 0.12 - jp.height / 2, 0]),
                          ChangeDecimalToValue(cnt[1], n), run_time=0.35)
                self.play(tint(tt[i], col), tint(pp[j], col), run_time=rt - 0.35)
                if i == 4 and not eq:
                    self.wait(0.6)
            elif e[0] == "fall":
                _, jo, jn = e
                hl = SurroundingRectangle(VGroup(tb[jo - 1], tl[jo - 1]), color=C_TEAL, buff=0.06)
                note = T(f"j = lps[{jo - 1}] = {jn}，i 不动", 26, C_TEAL).move_to([-1.0, -1.35, 0])
                self.play(Create(hl), FadeIn(note), run_time=0.9)
                self.wait(1.4)
                self.play(*[untint(c) for c in tt], *[untint(c) for c in pp], run_time=0.3)
                self.play(pp.animate.shift(RIGHT * w * (jo - jn)), run_time=0.7)
                for c in pp[:jn]:
                    c[0].set_stroke(C_HI, 3.5)
                self.play(*[c[0].animate.set_fill(C_HI, 0.25) for c in pp[:jn]], FadeOut(hl), run_time=0.5)
                self.wait_until(self.cue_start("接着比", self.now))
                self.play(FadeOut(note), run_time=0.3)
            else:
                _, start, _ = e
                br = Brace(tt[start:start + len(P_)], UP, color=C_OK, buff=0.45)
                bt = T(f"起点 {start}", 24, C_OK).next_to(br, UP, buff=0.08)
                self.play(FadeIn(br), FadeIn(bt), FadeOut(ip), FadeOut(il), run_time=0.6)
        self.wait_until(self.cue_start("这次只比较", self.now))
        self.play(Indicate(cnt[1], color=C_HI), run_time=0.8)
        path = Arrow([x0 - 0.2, 2.45, 0], [x0 + 6 * w + 0.3, 2.45, 0], color=C_HI, buff=0, stroke_width=4)
        path_t = T("i：0 → 6，只增不减", 22, C_HI).move_to([4.6, 1.9, 0])
        self.play(GrowArrow(path), FadeIn(path_t), run_time=1.0, audit=False)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 全部出现位置
    def all_beat(self):
        self.beat("all")
        w, x0 = 0.47, -6.1
        T_, P_ = K.LONG_T, K.LONG_P
        tt = cell_row(T_, x0, 1.2, w=w, size=22)
        pp = cell_row(P_, x0, 0.55, w=w, size=22, color=C_BLUE)
        idx = VGroup(*[Text(str(k), font=MONO, font_size=13, color=C_GREY).move_to([x0 + k * w, 1.62, 0])
                       for k in range(0, len(T_))])
        kc = counter("KMP 比较", -0.6, -1.0, color=C_HI)
        self.play(FadeIn(tt), FadeIn(pp), FadeIn(idx), FadeIn(kc), run_time=0.8)
        n = 0
        ev = K.LONG_KMP
        total = self.dur.get("all", 20) - 4.5
        rt = max(0.12, min(0.35, total / (len(ev) + 3) - 0.14))
        found = VGroup()
        prev = None
        for e in ev:
            if e[0] == "cmp":
                _, i, j, eq = e
                n += 1
                col = C_OK if eq else C_BAD
                off = i - j
                anims = [move_cell(pp[k], [x0 + (off + k) * w, 0.55, 0], 1.0 if off + k < len(T_) else 0.0)
                         for k in range(len(P_))]
                anims += [tint(tt[i], col), ChangeDecimalToValue(kc[1], n)]
                if prev is not None:
                    self.play(untint(prev[0]), untint(prev[1]), run_time=0.06)
                self.play(*anims, run_time=rt)
                self.play(tint(pp[j], col), run_time=0.08)
                prev = (tt[i], pp[j])
            elif e[0] == "match":
                _, s, _ = e
                br = Brace(tt[s:s + len(P_)], UP, color=C_OK, buff=0.4)
                bt = T(f"位置 {s}", 24, C_OK).next_to(br, UP, buff=0.06)
                self.play(FadeIn(br), FadeIn(bt), run_time=0.5)
                found.add(br, bt)
        self.play(untint(prev[0]), untint(prev[1]), run_time=0.2)
        self.wait_until(self.cue_start("KMP 找到", self.now))
        nc = counter("朴素 比较", 4.4, -1.0, color=C_GREY)
        self.play(FadeIn(nc), run_time=0.4)
        self.play(ChangeDecimalToValue(nc[1], K.LONG_NAIVE_CNT), run_time=1.0)
        self.play(Indicate(kc[1], color=C_HI), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 线性：两条指针曲线
    def linear_beat(self):
        self.beat("linear")
        cmps = [e for e in K.LONG_KMP if e[0] == "cmp"]
        N = len(cmps)
        ax = Axes(x_range=[0, N + 1, 5], y_range=[0, 28, 5], x_length=6.6, y_length=4.4,
                  axis_config={"color": C_GREY, "stroke_width": 2, "include_ticks": False},
                  tips=False).move_to([-3.1, 0.1, 0])
        xl = T("第几次比较", 22, C_GREY).next_to(ax.x_axis, DOWN, buff=0.15)
        self.play(Create(ax), FadeIn(xl), run_time=0.8)
        pi_ = [ax.c2p(k + 1, e[1]) for k, e in enumerate(cmps)]
        pj_ = [ax.c2p(k + 1, e[2]) for k, e in enumerate(cmps)]

        def stairs(pts):
            out = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                out += [np.array([b[0], a[1], 0]), b]
            return VMobject(stroke_width=4).set_points_as_corners(out)
        ci = stairs(pi_).set_color(C_HI)
        cj = stairs(pj_).set_color(C_TEAL)
        li = T("目标指针 i", 24, C_HI).next_to(ci.get_end(), UP, buff=0.15).shift(LEFT * 0.6)
        lj = T("模式指针 j", 24, C_TEAL).move_to([-4.9, 1.9, 0])
        self.wait_until(self.cue_start("把两个指针", self.now))
        self.play(Create(ci), FadeIn(li), run_time=2.5)
        self.play(Create(cj), FadeIn(lj), run_time=3.0)
        self.wait_until(self.cue_start("所以比较次数", self.now))
        bound = MathTex(r"\#\text{cmp}\le 2|T|", color=WHITE).scale(0.9).move_to([3.9, 2.4, 0])
        self.play(Write(bound), run_time=1.0)
        self.wait_until(self.cue_start("最坏的例子", self.now))
        wt = T("20 个 a 里找 aaaab", 24, C_GREY).move_to([3.9, 1.4, 0])
        scale = 3.2 / 80
        b1 = Rectangle(width=K.WORST_NAIVE_CNT * scale, height=0.42, stroke_width=0).set_fill(C_GREY, 0.8)
        b2 = Rectangle(width=K.WORST_KMP_CNT * scale, height=0.42, stroke_width=0).set_fill(C_HI, 0.8)
        b1.move_to([2.4, 0.55, 0], aligned_edge=LEFT)
        b2.move_to([2.4, -0.25, 0], aligned_edge=LEFT)
        l1 = T("朴素", 22, C_GREY).next_to(b1, LEFT, buff=0.15)
        l2 = T("KMP", 22, C_HI).next_to(b2, LEFT, buff=0.15)
        v1 = Text(str(K.WORST_NAIVE_CNT), font=MONO, font_size=24, color=C_GREY).next_to(b1, RIGHT, buff=0.12)
        v2 = Text(str(K.WORST_KMP_CNT), font=MONO, font_size=24, color=C_HI).next_to(b2, RIGHT, buff=0.12)
        self.play(FadeIn(wt), run_time=0.4)
        self.play(GrowFromEdge(b1, LEFT), FadeIn(l1), run_time=0.8)
        self.play(FadeIn(v1), run_time=0.3)
        self.play(GrowFromEdge(b2, LEFT), FadeIn(l2), run_time=0.8)
        self.play(FadeIn(v2), run_time=0.3)
        self.wait_until(self.cue_start("总代价", self.now))
        big = MathTex(r"O(|T|+|P|)", color=C_HI).scale(1.1).move_to([3.9, -1.5, 0])
        self.play(Write(big), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 最小循环节
    def period_case(self, s, y, color):
        w = 0.72
        x0 = -5.2
        row = cell_row(s, x0, y, w=w, size=30)
        lps = K.compute_lps(s)
        n, p = len(s), K.minimal_period(s)
        vals = VGroup(*[Text(str(v), font=MONO, font_size=20, color=C_GREY).move_to([x0 + k * w, y + 0.6, 0])
                        for k, v in enumerate(lps)])
        return row, vals, lps, n, p, w, x0

    def period_beat(self):
        self.beat("period")
        s1, s2 = K.PERIOD_CASES
        row, vals, lps, n, p, w, x0 = self.period_case(s1, 2.0, C_BLUE)
        self.play(FadeIn(row), run_time=0.6)
        self.wait_until(self.cue_start("最后一格是", self.now))
        self.play(FadeIn(vals), run_time=0.6)
        self.play(vals[-1].animate.set_color(C_HI).scale(1.4), run_time=0.5)
        self.wait_until(self.cue_start("把串错开", self.now))
        cp = cell_row(s1, x0 + p * w, 1.15, w=w, size=30, color=C_PURPLE)
        for k in range(n - p, n):
            cp[k].set_opacity(0.2)
        self.play(TransformFromCopy(row, cp), run_time=1.0)
        eq = [tint(row[k + p], C_OK, 0.3) for k in range(n - p)] + [tint(cp[k], C_OK, 0.3) for k in range(n - p)]
        self.play(*eq, run_time=0.7)
        f1 = T(f"错开 {n} − {lps[-1]} = {p} 位，重叠处全相同", 24, C_OK).move_to([3.4, 1.15, 0])
        f1.move_to([0, 0.45, 0])
        self.play(FadeIn(f1), run_time=0.5)
        self.wait_until(self.cue_start("三能整除九", self.now))
        cols = [C_BLUE, C_TEAL, C_PURPLE]
        blk = VGroup(*[SurroundingRectangle(row[b * p:(b + 1) * p], color=cols[b], buff=0.04, stroke_width=4)
                       for b in range(n // p)])
        v1 = T(f"{p} 整除 {n}：「abc」重复 {K.repetition_count(s1)} 次", 26, C_HI).move_to([3.6, 2.0, 0])
        self.play(FadeOut(cp), *[untint(c) for c in row], run_time=0.5)
        self.play(LaggedStart(*[Create(b) for b in blk], lag_ratio=0.4), FadeIn(v1), run_time=1.4)
        # 第二例
        self.wait_until(self.cue_start("再看", self.now))
        row2, vals2, lps2, n2, p2, _, _ = self.period_case(s2, -0.9, C_BLUE)
        self.play(FadeIn(row2), FadeIn(vals2), run_time=0.7)
        cp2 = cell_row(s2, x0 + p2 * w, -1.75, w=w, size=30, color=C_PURPLE)
        for k in range(n2 - p2, n2):
            cp2[k].set_opacity(0.2)
        self.play(TransformFromCopy(row2, cp2), run_time=0.9)
        self.play(*[tint(row2[k + p2], C_OK, 0.3) for k in range(n2 - p2)],
                  *[tint(cp2[k], C_OK, 0.3) for k in range(n2 - p2)], run_time=0.6)
        f2 = T(f"{n2} − {lps2[-1]} = {p2}，对得上", 24, C_OK).move_to([3.6, -0.9, 0])
        self.play(FadeIn(f2), run_time=0.5)
        self.wait_until(self.cue_start("但二不整除五", self.now))
        blk2 = VGroup(*[SurroundingRectangle(row2[b * p2:min(n2, (b + 1) * p2)], color=C_TEAL if b < 2 else C_BAD,
                                             buff=0.04, stroke_width=4) for b in range((n2 + p2 - 1) // p2)])
        blk2[-1].set_stroke(C_BAD)
        v2 = T(f"{p2} 不整除 {n2}：有周期，不是整数次重复", 24, C_BAD).move_to([2.6, -2.55, 0])
        self.play(FadeOut(cp2), *[untint(c) for c in row2], run_time=0.5)
        self.play(LaggedStart(*[Create(b) for b in blk2], lag_ratio=0.4), FadeIn(v2), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = [("朴素匹配", "失配 → 目标指针后退", r"O(|T|\cdot|P|)", C_GREY),
                ("KMP", "先算 lps 表；失配只动模式指针", r"O(|T|+|P|)", C_HI)]
        grp = VGroup()
        for k, (a, b, c, col) in enumerate(rows):
            y = 1.6 - 1.3 * k
            grp.add(VGroup(T(a, 32, col).move_to([-4.6, y, 0]), T(b, 26).move_to([-0.3, y, 0]),
                           MathTex(c, color=col).scale(0.9).move_to([4.6, y, 0])))
        self.wait_until(self.cue_start("朴素匹配", self.now))
        self.play(FadeIn(grp[0], shift=RIGHT * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("KMP 先花", self.now))
        self.play(FadeIn(grp[1], shift=RIGHT * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("next 数组", self.now))
        P = "ABABCABAB"
        lps = K.compute_lps(P)
        x0, w = -3.2, 0.62
        r1 = VGroup(*[Text(str(v), font=MONO, font_size=24, color=C_HI).move_to([x0 + k * w, -1.3, 0])
                      for k, v in enumerate(lps)])
        r2 = VGroup(*[Text(str(v), font=MONO, font_size=24, color=C_TEAL).move_to([x0 + (k + 1) * w, -2.1, 0])
                      for k, v in enumerate(lps[:-1])])
        m1 = Text("-1", font=MONO, font_size=24, color=C_TEAL).move_to([x0, -2.1, 0])
        l1 = T("lps", 22, C_HI).move_to([x0 - 1.0, -1.3, 0])
        l2 = T("next", 22, C_TEAL).move_to([x0 - 1.0, -2.1, 0])
        self.play(FadeIn(r1), FadeIn(l1), run_time=0.6)
        self.play(TransformFromCopy(r1[:-1], r2), FadeIn(m1), FadeIn(l2), run_time=1.2)
        opt = T("右移一格，再优化一步", 24, C_TEAL).move_to([4.2, -1.7, 0])
        self.play(FadeIn(opt), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()
