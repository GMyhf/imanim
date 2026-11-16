"""散列表：把关键字算成地址（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。每个关键字的落点、探查路径、
聚集概率、查找比较次数、二次探测与拉链结果都来自 hashdata（讲义代码原样插桩；test_hash.py 对撞讲义输出）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hashdata as H  # noqa: E402
from cine import *  # noqa: E402,F403

C_KEY, C_OK, C_BAD, C_HI = C_BLUE, C_GREEN, C_RED, C_YELLOW


def slot_row(n, x0, y, w=1.0, h=0.8, idx_size=18):
    boxes = VGroup(*[Rectangle(width=w * 0.92, height=h, stroke_color=C_GREY, stroke_width=2.5)
                     .move_to([x0 + k * w, y, 0]) for k in range(n)])
    idx = VGroup(*[Text(str(k), font=MONO, font_size=idx_size, color=C_GREY)
                   .next_to(boxes[k], DOWN, buff=0.12) for k in range(n)])
    return boxes, idx


def key_tok(k, color=C_KEY, w=0.78, h=0.56, size=28):
    box = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=3)
    box.set_fill(color, 0.2)
    return VGroup(box, Text(str(k), font=MONO, font_size=size, color=WHITE).move_to(box))


def flash(box, color, op=0.3):
    return box.animate.set_stroke(color, 4).set_fill(color, op)


def unflash(box):
    return box.animate.set_stroke(C_GREY, 2.5).set_fill(C_GREY, 0)


class HashLesson(Lesson):
    def construct(self):
        for b in ("title", "modfn", "collide", "cluster", "lookup", "quad", "chain", "load", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def fade_all(self, rt=0.6, keep=()):
        keep_ids = set(map(id, self.subs)) | set(map(id, keep))
        mobs = [m for m in self.mobjects if id(m) not in keep_ids]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=rt, audit=False)

    # ---------------------------------------------------------------- 片头：比较 vs 计算
    def title_beat(self):
        self.beat("title")
        arr = [3, 8, 15, 21, 30, 42, 54, 67, 71, 88, 93]
        boxes, _ = slot_row(len(arr), -5.0, 1.6, w=1.0, h=0.7)
        nums = VGroup(*[Text(str(v), font=MONO, font_size=26).move_to(b) for v, b in zip(arr, boxes)])
        lab = T("比较：一次次缩小范围", 26, C_GREY).move_to([0, 2.55, 0])
        self.play(FadeIn(boxes), FadeIn(nums), FadeIn(lab), run_time=0.8)
        lo, hi, probes = 0, len(arr) - 1, []
        while lo <= hi:
            mid = (lo + hi) // 2
            probes.append(mid)
            if arr[mid] == 54:
                break
            lo, hi = (mid + 1, hi) if arr[mid] < 54 else (lo, mid - 1)
        for k, mid in enumerate(probes):
            col = C_OK if arr[mid] == 54 else C_BAD
            self.play(flash(boxes[mid], col), run_time=0.55)
        self.wait_until(self.cue_start("散列换了个思路", self.now))
        key = key_tok(54).move_to([-4.6, -1.0, 0])
        fbox = RoundedRectangle(corner_radius=0.15, width=1.8, height=1.0, stroke_color=C_HI, stroke_width=3)
        fbox.move_to([-1.2, -1.0, 0])
        fl = MathTex(r"H(\text{key})", color=C_HI).scale(0.8).move_to(fbox)
        dest = Rectangle(width=0.92, height=0.8, stroke_color=C_GREY, stroke_width=2.5).move_to([2.6, -1.0, 0])
        dl = Text("10", font=MONO, font_size=20, color=C_GREY).next_to(dest, DOWN, buff=0.12)
        a1 = Arrow([-4.1, -1.0, 0], fbox.get_left(), buff=0.1, color=C_GREY)
        a2 = Arrow(fbox.get_right(), dest.get_left(), buff=0.1, color=C_GREY)
        self.play(FadeIn(key), Create(fbox), Write(fl), FadeIn(dest), FadeIn(dl), GrowArrow(a1), GrowArrow(a2),
                  run_time=1.2)
        self.play(key.animate.move_to(fbox), run_time=0.7, audit=False)    # 关键字穿过函数框：故意的过渡
        self.play(key.animate.move_to(dest), run_time=0.7)
        self.play(flash(dest, C_OK), run_time=0.4)
        one = T("一步到位", 26, C_OK).next_to(dest, RIGHT, buff=0.4)
        self.play(FadeIn(one), run_time=0.4)
        self.wait_until(self.cue_start("这个函数叫", self.now))
        title = T("散列表", 72).move_to([4.3, -2.35, 0])
        self.play(Write(title), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 除留余数法
    def build_table(self):
        self.tw, self.tx0, self.ty = 1.0, -5.0, -0.2
        self.boxes, self.idx = slot_row(H.M, self.tx0, self.ty, w=self.tw)
        self.in_slot = {}

    def above(self, s, dy=1.15):
        return np.array([self.tx0 + s * self.tw, self.ty + dy, 0])

    def modfn_beat(self):
        self.beat("modfn")
        self.build_table()
        f = MathTex(r"H(\text{key}) = \text{key} \bmod 11", color=C_HI).scale(0.95).move_to([0, 2.9, 0])
        self.play(Write(f), run_time=1.0)
        self.wait_until(self.cue_start("表长是十一", self.now))
        self.play(LaggedStart(*[Create(b) for b in self.boxes], lag_ratio=0.06), FadeIn(self.idx), run_time=1.2)
        self.wait_until(self.cue_start("五十四除以", self.now))
        span = (self.cue_start("这六个关键字", self.now + 10) - self.now - 0.3) / len(H.DIRECT)
        rt = max(0.6, min(1.6, span))
        for k in H.DIRECT:
            s = k % H.M
            tok = key_tok(k).move_to(self.above(s) + UP * 0.6).set_opacity(0)
            calc = MathTex(rf"{k} \bmod 11 = {s}", color=WHITE).scale(0.7).move_to([0, 1.95, 0])
            self.play(tok.animate.move_to(self.above(s)).set_opacity(1), FadeIn(calc), run_time=rt * 0.45)
            self.play(tok.animate.move_to(self.boxes[s]), FadeOut(calc), run_time=rt * 0.55)
            self.in_slot[s] = tok
        self.wait_until(self.cue_start("这六个关键字", self.now))
        self.play(*[Indicate(t, color=C_OK, scale_factor=1.12) for t in self.in_slot.values()], run_time=1.0)
        self.formula = f
        self.wait(max(0.1, self.left() - 0.3))

    # ---------------------------------------------------------------- 冲突与线性探测
    def probe(self, tok, path, rt=0.45, land=True, color=C_KEY):
        """令牌沿探查路径在槽位上方跳；被占的槽闪红，最后落入空槽（land=True）。"""
        prev = path[0]
        for s in path[1:]:
            if s < prev:                               # 绕回表头
                self.play(tok.animate.move_to(self.above(H.M - 1) + RIGHT * 1.0).set_opacity(0), run_time=rt * 0.6)
                tok.move_to(self.above(0) + LEFT * 1.0)
                self.play(tok.animate.move_to(self.above(s)).set_opacity(1), run_time=rt * 0.6)
            else:
                arc = ArcBetweenPoints(self.above(prev) + UP * 0.32, self.above(s) + UP * 0.32, angle=-PI * 0.7,
                                       color=C_HI, stroke_width=3)
                self.play(tok.animate.move_to(self.above(s)), Create(arc), run_time=rt)
                self.play(FadeOut(arc), run_time=0.15)
            if self.in_slot.get(s) is not None and s != path[-1]:
                self.play(flash(self.boxes[s], C_BAD), run_time=0.25)
                self.play(unflash(self.boxes[s]), run_time=0.15)
            prev = s
        if land:
            self.play(tok.animate.move_to(self.boxes[path[-1]]), run_time=0.45)
            self.in_slot[path[-1]] = tok

    def collide_beat(self):
        self.beat("collide")
        cols = dict(H.COLLIDED)
        k = 44
        s = k % H.M
        tok = key_tok(k, C_PURPLE).move_to(self.above(s) + UP * 0.6).set_opacity(0)
        calc = MathTex(rf"{k} \bmod 11 = {s}", color=WHITE).scale(0.7).move_to([0, 1.95, 0])
        self.play(tok.animate.move_to(self.above(s)).set_opacity(1), FadeIn(calc), run_time=0.8)
        self.play(flash(self.boxes[s], C_BAD), Indicate(self.in_slot[s], color=C_BAD), run_time=0.8)
        self.wait_until(self.cue_start("这叫冲突", self.now) if self.cue_start("这叫冲突") else self.now)
        word = T("冲突", 34, C_BAD).move_to([3.6, 1.95, 0])
        self.play(FadeIn(word, scale=1.3), run_time=0.5)
        self.wait_until(self.cue_start("线性探测的办法", self.now))
        rule = MathTex(r"H_i = (H(\text{key}) + i) \bmod 11", color=C_HI).scale(0.8).move_to([0, 2.9, 0])
        self.play(FadeOut(word), FadeOut(calc), unflash(self.boxes[s]), ReplacementTransform(self.formula, rule),
                  run_time=0.8)
        self.formula = rule
        self.wait_until(self.cue_start("往后挪一格", self.now))
        self.probe(tok, cols[44], rt=0.6)
        self.wait_until(self.cue_start("五十五也余零", self.now))
        tok = key_tok(55, C_PURPLE).move_to(self.above(0) + UP * 0.6).set_opacity(0)
        self.play(tok.animate.move_to(self.above(0)).set_opacity(1), run_time=0.5)
        self.play(flash(self.boxes[0], C_BAD), run_time=0.3)
        self.play(unflash(self.boxes[0]), run_time=0.2)
        self.probe(tok, cols[55], rt=0.5)
        self.wait_until(self.cue_start("二十余九", self.now))
        tok = key_tok(20, C_PURPLE).move_to(self.above(9) + UP * 0.6).set_opacity(0)
        cnt = VGroup(T("看了", 26, C_GREY), DecimalNumber(1, num_decimal_places=0, font_size=36, color=C_HI),
                     T("个槽", 26, C_GREY)).arrange(RIGHT, buff=0.15).move_to([3.6, 1.95, 0])
        self.play(tok.animate.move_to(self.above(9)).set_opacity(1), FadeIn(cnt), run_time=0.5)
        self.play(flash(self.boxes[9], C_BAD), run_time=0.3)
        self.play(unflash(self.boxes[9]), run_time=0.2)
        path = cols[20]
        for q in range(1, len(path)):
            self.probe(tok, path[q - 1:q + 1], rt=0.5, land=False)
            self.play(ChangeDecimalToValue(cnt[1], q + 1), run_time=0.2)
        self.play(tok.animate.move_to(self.boxes[path[-1]]), run_time=0.45)
        self.in_slot[path[-1]] = tok
        self.play(Indicate(cnt[1], color=C_HI), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(cnt), run_time=0.4)

    # ---------------------------------------------------------------- 聚集
    def cluster_beat(self):
        self.beat("cluster")
        full = [s for s in range(H.M) if H.TABLE[s] is not None]
        segs = [VGroup(self.boxes[9], self.boxes[10]), VGroup(*[self.boxes[s] for s in range(0, 7)])]
        rects = VGroup(*[SurroundingRectangle(g, color=C_BAD, buff=0.08, stroke_width=4) for g in segs])
        lab = T(f"连续 {len(full)} 个槽：聚集", 28, C_BAD).move_to([0, 1.95, 0])
        self.play(Create(rects), FadeIn(lab), run_time=1.0)
        self.wait_until(self.cue_start("下一个关键字", self.now))
        self.play(FadeOut(lab), run_time=0.3)
        homes = {7: [], 8: []}
        for h in range(H.M):
            p = h
            while H.TABLE[p] is not None:
                p = (p + 1) % H.M
            homes[p].append(h)
        dots = VGroup(*[Dot(radius=0.09, color=C_HI).move_to(self.boxes[h].get_bottom() + DOWN * 0.55)
                        for h in homes[7]])
        self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.12), run_time=1.6)
        bmax = 1.4
        b7 = Rectangle(width=0.6, height=bmax * H.ODDS[7] / H.M, stroke_width=0).set_fill(C_HI, 0.75)
        b8 = Rectangle(width=0.6, height=bmax * H.ODDS[8] / H.M, stroke_width=0).set_fill(C_TEAL, 0.75)
        b7.move_to(self.boxes[7].get_top() + UP * 0.12, aligned_edge=DOWN)
        b8.move_to(self.boxes[8].get_top() + UP * 0.12, aligned_edge=DOWN)
        f7 = MathTex(rf"\frac{{{H.ODDS[7]}}}{{{H.M}}}", color=C_HI).scale(0.75).next_to(b7, UP, buff=0.1)
        self.play(GrowFromEdge(b7, DOWN), run_time=0.8)
        self.play(FadeIn(f7), run_time=0.4)
        self.wait_until(self.cue_start("而八号槽", self.now))
        d8 = Dot(radius=0.09, color=C_TEAL).move_to(self.boxes[8].get_bottom() + DOWN * 0.55)
        f8 = MathTex(rf"\frac{{{H.ODDS[8]}}}{{{H.M}}}", color=C_TEAL).scale(0.75).next_to(b8, UP, buff=0.1)
        self.play(FadeIn(d8, scale=0.5), GrowFromEdge(b8, DOWN), run_time=0.8)
        self.play(FadeIn(f8), run_time=0.4)
        self.wait_until(self.cue_start("块越大", self.now))
        grow = SurroundingRectangle(VGroup(*[self.boxes[s] for s in range(0, 8)]), color=C_BAD, buff=0.08,
                                    stroke_width=4)
        self.play(Transform(rects[1], grow), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(rects, dots, d8, b7, b8, f7, f8)), run_time=0.6)

    # ---------------------------------------------------------------- 查找
    def lookup_beat(self):
        self.beat("lookup")
        cnt = VGroup(T("比较", 26, C_GREY), DecimalNumber(0, num_decimal_places=0, font_size=36, color=C_HI),
                     T("次", 26, C_GREY)).arrange(RIGHT, buff=0.15).move_to([5.0, 1.95, 0])
        self.wait_until(self.cue_start("找二十", self.now))
        q = key_tok("20?", C_TEAL, w=1.0).move_to(self.above(H.FIND20[0]) + UP * 0.6).set_opacity(0)
        self.play(q.animate.move_to(self.above(H.FIND20[0])).set_opacity(1), FadeIn(cnt), run_time=0.5)

        def walk(q, path, found):
            prev = None
            for n, s in enumerate(path, 1):
                if prev is not None:
                    if s < prev:
                        self.play(q.animate.move_to(self.above(H.M - 1) + RIGHT).set_opacity(0), run_time=0.25)
                        q.move_to(self.above(0) + LEFT)
                        self.play(q.animate.move_to(self.above(s)).set_opacity(1), run_time=0.25)
                    else:
                        self.play(q.animate.move_to(self.above(s)), run_time=0.3)
                hit = found and n == len(path)
                self.play(flash(self.boxes[s], C_OK if hit else C_BAD), ChangeDecimalToValue(cnt[1], n),
                          run_time=0.3)
                if not hit:
                    self.play(unflash(self.boxes[s]), run_time=0.12)
                prev = s
        walk(q, H.FIND20, True)
        self.play(Indicate(cnt[1], color=C_HI), run_time=0.6)
        self.wait_until(self.cue_start("找九十九", self.now))
        self.play(FadeOut(q), unflash(self.boxes[H.FIND20[-1]]), ChangeDecimalToValue(cnt[1], 0), run_time=0.4)
        q = key_tok("99?", C_TEAL, w=1.0).move_to(self.above(0) + UP * 0.6).set_opacity(0)
        self.play(q.animate.move_to(self.above(0)).set_opacity(1), run_time=0.4)
        walk(q, H.FIND99, False)
        empty = H.FIND99[-1] + 1
        self.play(q.animate.move_to(self.above(empty)), run_time=0.3)
        self.play(flash(self.boxes[empty], C_HI, 0.15), run_time=0.4)
        no = T("空槽：不在表里", 24, C_HI).move_to(self.above(empty) + UP * 0.75)
        self.play(FadeIn(no), run_time=0.4)
        self.wait_until(self.cue_start("表里九个元素", self.now))
        alpha = MathTex(r"\alpha = \frac{" + str(H.LOAD_N) + "}{" + str(H.M) + "}", color=C_HI).scale(0.9)
        alpha.move_to([0, -2.1, 0])
        self.play(Write(alpha), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 二次探测
    def quad_beat(self):
        self.beat("quad")
        w, x0 = 0.9, -4.0
        # 增量示意
        cb, ci = slot_row(H.Q_M, x0, 0.2, w=w)
        self.play(FadeIn(cb), FadeIn(ci), run_time=0.6)
        c = 5
        self.play(flash(cb[c], C_BAD), run_time=0.4)
        labels = []
        for d, txt in [(1, "+1"), (-1, "−1"), (4, "+4"), (-4, "−4")]:
            arc = ArcBetweenPoints(cb[c].get_top() + UP * 0.1, cb[c + d].get_top() + UP * 0.1,
                                   angle=-PI * 0.6 * np.sign(d), color=C_HI, stroke_width=3)
            lt = Text(txt, font=MONO, font_size=24, color=C_HI).next_to(arc, UP, buff=0.12)
            if abs(d) == 1:
                lt.shift(RIGHT * 0.25 * d)
            self.play(Create(arc), FadeIn(lt), flash(cb[c + d], C_HI, 0.2), run_time=0.7)
            labels += [arc, lt]
        self.wait_until(self.cue_start("讲义练习里", self.now))
        self.play(FadeOut(VGroup(cb, ci, *labels)), run_time=0.5)
        keys = VGroup(*[key_tok(k, size=24, w=0.7, h=0.5) for k in H.Q_KEYS]).arrange(RIGHT, buff=0.25)
        keys.move_to([0, 3.0, 0])
        lb, li = slot_row(H.Q_M, x0, 1.4, w=w)
        qb, qi = slot_row(H.Q_M, x0, -1.3, w=w)
        tl = T("线性", 26, C_GREY).next_to(lb, LEFT, buff=0.35)
        tq = T("二次", 26, C_HI).next_to(qb, LEFT, buff=0.35)
        self.play(FadeIn(keys), FadeIn(lb), FadeIn(li), FadeIn(qb), FadeIn(qi), FadeIn(tl), FadeIn(tq), run_time=0.9)
        # 线性：直接落位（每个关键字的探查路径都来自 hashdata）
        lt_toks = []
        for k, path in zip(H.Q_KEYS, H.QL_PATHS):
            tok = key_tok(k, size=24, w=0.7, h=0.5).move_to(keys[H.Q_KEYS.index(k)])
            self.play(tok.animate.move_to(lb[path[-1]]), run_time=0.45)
            lt_toks.append(tok)
        self.wait_until(self.cue_start("用线性探测", self.now))
        run = sorted(p[-1] for p in H.QL_PATHS)
        rr = SurroundingRectangle(VGroup(*[lb[s] for s in run]), color=C_BAD, buff=0.07, stroke_width=4)
        rl = T(f"{run[0]}–{run[-1]} 号连成一块", 24, C_BAD).next_to(rr, UP, buff=0.12)
        self.play(Create(rr), FadeIn(rl), run_time=0.8)
        # 二次：带增量的跳跃
        for k, path, inc in zip(H.Q_KEYS, H.Q_PATHS, H.Q_INCS):
            tok = key_tok(k, size=24, w=0.7, h=0.5).move_to(keys[H.Q_KEYS.index(k)])
            hover = lambda s: np.array([x0 + s * w, -0.45, 0])  # noqa: E731
            self.play(tok.animate.move_to(hover(path[0])), run_time=0.35)
            for a, b, d in zip(path, path[1:], inc[1:]):
                arc = ArcBetweenPoints(hover(a) + UP * 0.3, hover(b) + UP * 0.3, angle=-PI * 0.55 * np.sign(b - a),
                                       color=C_HI, stroke_width=3)
                dl = Text(f"{d:+d}".replace("-", "−"), font=MONO, font_size=20, color=C_HI).next_to(arc, UP, buff=0.03)
                self.play(flash(qb[a], C_BAD), run_time=0.15)
                self.play(tok.animate.move_to(hover(b)), Create(arc), FadeIn(dl), unflash(qb[a]), run_time=0.4)
                self.play(FadeOut(arc), FadeOut(dl), run_time=0.15)
            self.play(tok.animate.move_to(qb[path[-1]]), run_time=0.3)
        self.wait_until(self.cue_start("块被打散", self.now) or self.now)
        holes = [s for s in range(min(p[-1] for p in H.Q_PATHS), max(p[-1] for p in H.Q_PATHS) + 1)
                 if s not in {p[-1] for p in H.Q_PATHS}]
        hl = VGroup(*[SurroundingRectangle(qb[s], color=C_OK, buff=0.05, stroke_width=4) for s in holes])
        ql = T("块被打散", 24, C_OK).next_to(qb, DOWN, buff=0.55)
        self.play(Create(hl), FadeIn(ql), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 拉链法
    def chain_beat(self):
        self.beat("chain")
        w, x0, y0 = 0.95, -5.7, 2.3
        boxes, idx = slot_row(H.C_M, x0, y0, w=w, h=0.6, idx_size=16)
        for t in idx:
            t.next_to(boxes[int(t.text)], UP, buff=0.1)
        self.play(FadeIn(boxes), FadeIn(idx), run_time=0.8)
        heads = [[] for _ in range(H.C_M)]
        node_h, gap = 0.5, 0.82
        m13 = MathTex(r"H(\text{key}) = \text{key} \bmod 13", color=C_HI).scale(0.75).move_to([4.0, -2.4, 0])
        self.play(FadeIn(m13), run_time=0.4)
        span = (self.cue_start("讲义例题", self.now + 8) - self.now) / len(H.C_KEYS)
        rt = max(0.35, min(0.7, span))
        arrows = VGroup()
        for k in H.C_KEYS:
            s = k % H.C_M
            n = len(heads[s])
            pos = np.array([x0 + s * w, y0 - gap * (n + 1), 0])
            tok = key_tok(k, C_KEY, w=0.78, h=node_h, size=24).move_to(pos + UP * 0.4).set_opacity(0)
            src = boxes[s].get_bottom() if n == 0 else heads[s][-1].get_bottom()
            arr = Arrow(src, pos + UP * node_h / 2, buff=0.04, color=C_GREY, stroke_width=3,
                        max_tip_length_to_length_ratio=0.35)
            self.play(tok.animate.move_to(pos).set_opacity(1), GrowArrow(arr), run_time=rt)
            heads[s].append(tok)
            arrows.add(arr)
        self.wait_until(self.cue_start("都余一", self.now) if self.cue_start("都余一") else self.now)
        ch = VGroup(boxes[1], *heads[1])
        rect = SurroundingRectangle(ch, color=C_HI, buff=0.1)
        lab = T(f"长度 {len(heads[1])}", 24, C_HI).next_to(rect, DOWN, buff=0.15)
        self.play(Create(rect), FadeIn(lab), run_time=0.8)
        self.wait_until(self.cue_start("拉链法没有聚集", self.now))
        al = VGroup(MathTex(r"\alpha=\frac{" + str(len(H.C_KEYS)) + "}{" + str(H.C_M) + "}", color=C_TEAL).scale(0.8),
                    T("（可以超过 1）", 22, C_TEAL)).arrange(RIGHT, buff=0.15).move_to([4.0, -1.35, 0])
        self.play(FadeIn(al), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 装填因子与平均比较次数
    def load_beat(self):
        self.beat("load")
        ax = Axes(x_range=[0, 1, 0.1], y_range=[1, 6, 1], x_length=7.0, y_length=4.6,
                  axis_config={"color": C_GREY, "stroke_width": 2, "include_tip": False},
                  x_axis_config={"numbers_to_include": [0.5, 1.0], "decimal_number_config": {"num_decimal_places": 1},
                                 "font_size": 24},
                  y_axis_config={"numbers_to_include": [1, 2, 3, 4, 5, 6], "font_size": 24}).move_to([-2.4, 0.15, 0])
        xl = MathTex(r"\alpha", color=C_GREY).scale(0.8).next_to(ax.x_axis, RIGHT, buff=0.15)
        yl = T("平均比较次数", 22, C_GREY).next_to(ax.y_axis, UP, buff=0.12)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), run_time=1.0)
        self.wait_until(self.cue_start("线性探测成功", self.now))
        lin = ax.plot(H.asl_linear_hit, x_range=[0, 0.905, 0.005], color=C_BAD, stroke_width=4)
        ll = T("线性探测", 24, C_BAD).move_to(ax.c2p(0.62, 5.2))
        self.play(Create(lin), FadeIn(ll), run_time=2.0)
        dots = VGroup()
        for a in H.ASL_POINTS:
            v = H.asl_linear_hit(a)
            d = Dot(ax.c2p(a, v), color=C_HI, radius=0.07)
            t = Text(f"{v:g}", font=MONO, font_size=24, color=C_HI).next_to(d, UL, buff=0.06)
            self.play(FadeIn(d, scale=0.5), FadeIn(t), run_time=0.6)
            dots.add(d, t)
            self.wait(1.0)
        self.wait_until(self.cue_start("拉链法只是", self.now))
        chn = ax.plot(H.asl_chain_hit, x_range=[0, 1, 0.01], color=C_TEAL, stroke_width=4)
        cl = T("拉链法", 24, C_TEAL).next_to(ax.c2p(1, H.asl_chain_hit(1)), UP, buff=0.15)
        self.play(Create(chn), FadeIn(cl), run_time=1.4)
        self.wait_until(self.cue_start("所以实际系统", self.now))
        th = DashedLine(ax.c2p(0.5, 1), ax.c2p(0.5, 6), color=C_GREY)
        r = VGroup(T("超过阈值", 26, C_HI), T("→ 扩表", 26, C_HI), T("→ 按新表长", 26, C_HI), T("   重新散列", 26, C_HI))
        r.arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([4.9, 0.6, 0])
        self.play(Create(th), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(x, shift=RIGHT * 0.2) for x in r], lag_ratio=0.35), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        rows = [("散列函数", "关键字 → 地址，比较次数只看装填因子", C_HI, "散列用函数"),
                ("线性探测", "简单，但会聚集", C_BAD, "冲突躲不开"),
                ("二次探测", "左右跳，打散聚集", C_YELLOW, "二次探测"),
                ("拉链法", "同义词串成链", C_TEAL, "拉链法"),
                ("扩表", "装填因子一大就重新散列", C_GREEN, "装填因子一大")]
        y = 2.3
        for a, b, col, key in rows:
            g = VGroup(T(a, 30, col).move_to([-3.6, y, 0]), T(b, 26).move_to([-1.8, y, 0], aligned_edge=LEFT))
            self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(g, shift=RIGHT * 0.2), run_time=0.6)
            y -= 1.0
        self.wait(max(0.1, self.left() - 0.6))
        self.fade_all()
