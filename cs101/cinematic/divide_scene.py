"""分治，递归的另一种用法：快速幂与最大公约数（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。调用链、每层乘法、二进制位、反例的调用次数、辗转相除链与
长方形切正方形都来自 dividedata（test_divide.py 对撞讲义输出、内建 pow / math.gcd、暴力与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dividedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

SQ_COLOR = [C_BLUE, C_TEAL, C_YELLOW, C_RED, C_PURPLE]


def mono(s, size=24, color=WHITE):
    return Text(s, font=MONO, font_size=size, color=color)


def arc(p, q, color, angle=-PI / 3, width=3, tip=True):
    a = ArcBetweenPoints(p, q, angle=angle, color=color, stroke_width=width)
    if tip:
        a.add_tip(tip_length=0.16, tip_width=0.14)
    return a


def mini_tree(factors, width, height, color=C_GREY, r=0.08):
    """小调用树：factors[l] = 第 l 层每个节点的孩子数。返回 VGroup(边, 点)，叶子均分宽度。"""
    sizes = [1]
    for f in factors:
        sizes.append(sizes[-1] * f)
    depth = len(sizes) - 1
    pos = [[None] * s for s in sizes]
    n = sizes[-1]
    for j in range(n):
        x = -width / 2 + width * (j + 0.5) / n if n > 1 else 0.0
        pos[-1][j] = np.array([x, -height / 2, 0])
    for lv in range(depth - 1, -1, -1):
        f = factors[lv]
        for j in range(sizes[lv]):
            kids = pos[lv + 1][j * f:(j + 1) * f]
            x = sum(k[0] for k in kids) / len(kids)
            pos[lv][j] = np.array([x, height / 2 - height * lv / max(1, depth), 0])
    edges = VGroup(*[Line(pos[lv][j // factors[lv]], pos[lv + 1][j], color=color, stroke_width=2)
                     for lv in range(depth) for j in range(sizes[lv + 1])])
    dots = VGroup(*[Dot(p, radius=r, color=color) for row in pos for p in row])
    return VGroup(edges, dots)


class DivideLesson(Lesson):
    def construct(self):
        for b in ("title", "naive", "code", "chain", "binary", "twice", "gcd", "rect", "why", "halving",
                  "contrast", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def cue_at(self, key, default=None):
        """key 在句中的大致时刻：句起点 + 句长按字数比例（同一句里先后几件事时用）。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    def three_trees(self, y=0.3):
        """汉诺塔（二叉）、全排列（3·2·1）、单链三棵小调用树。"""
        hanoi = mini_tree([2, 2, 2], 3.2, 2.4)
        perm = mini_tree([3, 2, 1], 3.4, 2.4)
        chain = mini_tree([1, 1, 1, 1], 0.1, 2.4, C_YELLOW, 0.1)
        for t, x in ((hanoi, -4.6), (perm, 0.0), (chain, 4.6)):
            t.move_to([x, y, 0])
        return hanoi, perm, chain

    # ---------------------------------------------------------------- 片头
    def title_beat(self):
        self.beat("title")
        hanoi, perm, chain = self.three_trees()
        labs = VGroup(T("汉诺塔：分两支", 26, C_GREY), T("全排列：分好几支", 26, C_GREY),
                      T("今天：一条链", 26, C_YELLOW))
        for lab, t in zip(labs, (hanoi, perm, chain)):
            lab.next_to(t, DOWN, buff=0.35)
        self.play(Create(hanoi[0]), FadeIn(hanoi[1]), FadeIn(labs[0]), run_time=1.2)
        self.wait_until(self.cue_at("全排列", self.now))
        self.play(Create(perm[0]), FadeIn(perm[1]), FadeIn(labs[1]), run_time=1.2)
        self.wait_until(self.cue_start("今天", self.now))
        self.play(Create(chain[0]), FadeIn(chain[1]), FadeIn(labs[2]), run_time=1.2)
        self.wait_until(self.cue_start("这也是分治", self.now))
        title = T("分治：递归的另一种用法", 50).move_to([0, 3.0, 0])
        steps = VGroup(T("分", 30, C_BLUE), MathTex(r"\to").scale(0.8), T("递归解决", 30, C_TEAL),
                       MathTex(r"\to").scale(0.8), T("合", 30, C_YELLOW)).arrange(RIGHT, buff=0.3)
        steps.move_to([0, -2.55, 0])
        self.play(Write(title), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.15) for s in steps], lag_ratio=0.25), run_time=1.2)
        sub = T("快速幂 · 最大公约数", 30, C_BLUE).next_to(title, DOWN, buff=0.2)
        self.play(FadeIn(sub), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(hanoi, perm, chain, labs, title, sub, steps)), run_time=0.6)

    # ---------------------------------------------------------------- 连乘与对半拆
    def naive_beat(self):
        self.beat("naive")
        a, b = D.A, D.B
        head = MathTex(rf"{a}^{{{b}}}", color=C_YELLOW).scale(1.4).move_to([0, 2.8, 0])
        self.play(Write(head), run_time=0.6)
        self.wait_until(self.cue_start("连乘", self.now))
        _, cnt = D.naive_pow(a, b)
        dots = VGroup(*[VGroup(Circle(0.32, color=C_BLUE, stroke_width=3), MathTex(str(a)).scale(0.8))
                        for _ in range(b)]).arrange(RIGHT, buff=0.32).move_to([0, 1.4, 0])
        for c in dots:
            c[1].move_to(c[0])
        lab = VGroup(T("连乘：", 28), MathTex(rf"{cnt}", color=C_RED).scale(0.9), T("次乘法", 28))
        lab.arrange(RIGHT, buff=0.15).move_to([0, 0.35, 0])
        self.play(LaggedStart(*[FadeIn(c, shift=DOWN * 0.2) for c in dots], lag_ratio=0.15), run_time=1.6)
        self.play(FadeIn(lab), run_time=0.4)
        self.wait_until(self.cue_start("十亿", self.now))
        big = VGroup(T("指数到十亿", 28), MathTex(r"\Rightarrow\ 10^9", color=C_RED).scale(0.9), T("次乘法", 28))
        big.arrange(RIGHT, buff=0.2).move_to([0, -0.55, 0])
        self.play(FadeIn(big, shift=UP * 0.2), run_time=0.7)
        self.wait_until(self.cue_start("换个分法", self.now))
        self.play(FadeOut(VGroup(dots, lab, big)), run_time=0.5)
        _, lv = D.pow_trace(a, b)
        e1 = MathTex(rf"{a}^{{{lv[0]['b']}}}", "=", rf"\left({a}^{{{lv[1]['b']}}}\right)^2").scale(1.0)
        e2 = MathTex(rf"{a}^{{{lv[1]['b']}}}", "=", rf"\left({a}^{{{lv[2]['b']}}}\right)^2", r"\times", str(a))
        e2[3:].set_color(C_YELLOW)
        VGroup(e1, e2).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 1.2, 0])
        self.play(Write(e1), run_time=1.0)
        self.wait_until(self.cue_start("二的五次方，是", self.now))
        self.play(Write(e2), run_time=1.2)
        self.wait_until(self.cue_start("指数每次减半", self.now))
        bs = [x["b"] for x in lv]
        row = VGroup()
        for k, x in enumerate(bs):
            col = C_YELLOW if x & 1 else WHITE
            row.add(MathTex(str(x), color=col).scale(1.0))
            if k + 1 < len(bs):
                row.add(MathTex(r"\to", color=C_GREY).scale(0.9))
        row.arrange(RIGHT, buff=0.35).move_to([0, -1.1, 0])
        odd_tag = VGroup(*[T("奇数：多乘一个 2", 22, C_YELLOW).next_to(row[2 * k], DOWN, buff=0.2)
                           for k, x in enumerate(bs) if x & 1][:1])
        self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.15) for m in row], lag_ratio=0.12), run_time=1.4)
        self.play(FadeIn(odd_tag), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, e1, e2, row, odd_tag)), run_time=0.6)

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        code = Code(code_string='def fast_pow(a, b, mod=None):\n    """计算 a^b（可选取模），O(log b)。"""\n'
                                "    if b == 0:\n        return 1 % mod if mod else 1\n"
                                "    half = fast_pow(a, b // 2, mod)\n    res = half * half\n"
                                "    if b & 1:\n        res *= a\n    return res % mod if mod else res\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 24})
        code.scale_to_fit_width(8.0)
        code.move_to([-2.55, 0.4, 0])
        self.play(FadeIn(code, shift=UP * 0.2), run_time=0.8)
        ln = code.code_lines

        def hl(lines, col):
            return VGroup(*[SurroundingRectangle(ln[k], color=col, buff=(0.08, 0.03), stroke_width=2) for k in lines])

        def note(s, col):
            return T(s, 26, col).move_to([4.45, 0.4, 0])
        steps = (("指数为零", [2, 3], C_GREY, "基例：返回 1"), ("half", [4, 5], C_YELLOW, "一半的结果，平方"),
                 ("奇数", [6, 7], C_TEAL, "奇数：再乘 a"), ("mod", [8], C_BLUE, "可选：取模"))
        box = lab = None
        for key, lines, col, txt in steps:
            self.wait_until(self.cue_at(key, self.now))
            nb, nl = hl(lines, col), note(txt, col)
            if box is None:
                self.play(Create(nb), FadeIn(nl), run_time=0.6)
            else:
                self.play(ReplacementTransform(box, nb), FadeOut(lab), FadeIn(nl), run_time=0.6)
            box, lab = nb, nl
        self.wait_until(self.cue_start("Python", self.now))
        v = pow(3, 100, D.MOD)
        py = VGroup(mono("pow(3, 100, 10**9+7)", 24, C_BLUE), mono(f"= {v}", 24, WHITE),
                    mono(f"fast_pow 也是 {D.fast_pow(3, 100, D.MOD)}", 22, C_GREY)).arrange(DOWN, buff=0.2)
        py.move_to([4.45, -1.2, 0])
        self.play(FadeIn(py, shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(code, box, lab, py)), run_time=0.6)

    # ---------------------------------------------------------------- 调用链
    def chain_beat(self):
        self.beat("chain")
        a, b = D.A, D.B
        _, lv = D.pow_trace(a, b)
        ys = [2.7 - 1.18 * k for k in range(len(lv))]
        boxes = VGroup()
        for x, y in zip(lv, ys):
            t = mono(f"fast_pow({a}, {x['b']})", 24)
            r = RoundedRectangle(corner_radius=0.12, width=3.3, height=0.62, stroke_color=C_BLUE, stroke_width=2.5)
            boxes.add(VGroup(r, t.move_to(r)).move_to([-3.9, y, 0]))
        down = VGroup(*[arc(boxes[k][0].get_left() + LEFT * 0.05, boxes[k + 1][0].get_left() + LEFT * 0.05,
                            C_GREY, angle=PI / 2.2) for k in range(len(lv) - 1)])
        self.play(FadeIn(boxes[0]), run_time=0.4)
        for k in range(1, len(lv)):
            self.play(Create(down[k - 1]), FadeIn(boxes[k], shift=DOWN * 0.15), run_time=0.45)
        self.wait_until(self.cue_at("零返回一", self.now))
        r0 = MathTex(r"\text{return } 1", color=C_YELLOW).scale(0.8).next_to(boxes[-1], RIGHT, buff=0.8)
        self.play(FadeIn(r0), boxes[-1][0].animate.set_stroke(C_YELLOW, 3), run_time=0.5)
        cnt_t = T("乘法次数", 26, C_GREY).move_to([4.6, 1.6, 0])
        total = 0
        cnt = MathTex(str(total), color=C_YELLOW).scale(1.2).next_to(cnt_t, DOWN, buff=0.25)
        self.play(FadeIn(cnt_t), FadeIn(cnt), run_time=0.4)
        ups = VGroup()
        rets = VGroup(r0)
        keys = ("一的平方乘二", "二的平方", "四的平方乘二", "三十二的平方")
        for k, key in zip(range(len(lv) - 2, -1, -1), keys):
            x = lv[k]
            self.wait_until(self.cue_at(key, self.now))
            up = arc(boxes[k + 1][0].get_right() + RIGHT * 0.05, boxes[k][0].get_right() + RIGHT * 0.05,
                     C_YELLOW, angle=PI / 2.2)
            tex = rf"{x['half']}^2" + (rf"\times {a}" if x["odd"] else "") + rf"={x['res']}"
            ex = MathTex(tex, color=WHITE).scale(0.85).next_to(boxes[k], RIGHT, buff=0.8)
            if x["odd"]:
                ex[0][len(str(x['half'])) + 1:len(str(x['half'])) + 3].set_color(C_YELLOW)
            total += x["mults"]
            ncnt = MathTex(str(total), color=C_YELLOW).scale(1.2).move_to(cnt)
            self.play(Create(up), FadeIn(ex, shift=UP * 0.1), boxes[k][0].animate.set_stroke(C_YELLOW, 3),
                      Transform(cnt, ncnt), run_time=0.7)
            ups.add(up)
            rets.add(ex)
        self.wait_until(self.cue_start("一共", self.now))
        _, nv = D.naive_pow(a, b)
        cmp = VGroup(T(f"快速幂 {total} 次", 26, C_YELLOW), T(f"连乘 {nv} 次", 26, C_RED)).arrange(DOWN, buff=0.25)
        cmp.next_to(cnt, DOWN, buff=0.45)
        self.play(FadeIn(cmp, shift=UP * 0.2), Indicate(cnt, color=C_YELLOW), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(ups, rets, cnt_t, cnt, cmp)),
                  *[bx[0].animate.set_stroke(C_BLUE, 2.5) for bx in boxes], run_time=0.6)
        self.boxes, self.down = boxes, down

    # ---------------------------------------------------------------- 指数的二进制
    def binary_beat(self):
        self.beat("binary")
        _, lv = D.pow_trace(D.A, D.B)
        boxes = self.boxes
        head = T("指数的二进制", 26, C_GREY).move_to([0.2, 3.45, 0])
        bits = VGroup()
        for x, bx in zip(lv, boxes):
            s = bin(x["b"])[2:] if x["b"] else ""
            g = VGroup(*[mono(ch, 30, WHITE) for ch in s]).arrange(RIGHT, buff=0.06) if s else VGroup()
            if s:
                g.move_to([0, bx.get_y(), 0]).align_to(np.array([-0.6, 0, 0]), LEFT)
            bits.add(g)
        self.play(FadeIn(head), LaggedStart(*[FadeIn(g) for g in bits if len(g)], lag_ratio=0.2), run_time=1.2)
        self.wait_until(self.cue_start("往下走一层", self.now))
        lows = [g[-1] for g in bits if len(g)]
        self.play(*[m.animate.set_color(C_YELLOW if m.text == "1" else C_GREY) for m in lows], run_time=0.6)
        drops = VGroup(*[arc(bits[k][-1].get_right() + RIGHT * 0.12, bits[k + 1][-1].get_right() + RIGHT * 0.12,
                             C_GREY, angle=-PI / 2.4, width=2) for k in range(len(lv) - 2)])
        drop_l = T("去掉最低位", 22, C_GREY).next_to(drops[0], RIGHT, buff=0.15)
        self.play(Create(drops), FadeIn(drop_l), run_time=0.8)
        self.wait_until(self.cue_at("最低位是一", self.now))
        tags = VGroup(*[MathTex(r"\times a", color=C_YELLOW).scale(0.8).move_to([2.6, boxes[k].get_y(), 0])
                        for k, x in enumerate(lv) if x["odd"]])
        self.play(FadeIn(tags, shift=LEFT * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("所以层数", self.now))
        nbits = D.B.bit_length()
        rule = VGroup(T(f"层数 = 位数 = {nbits}", 26, WHITE), T("乘法 ≤ 2 × 位数", 26, C_YELLOW))
        rule.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([4.9, 1.3, 0])
        self.play(FadeIn(rule, shift=LEFT * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("十亿", self.now))
        self.play(FadeOut(VGroup(head, bits, drops, drop_l, tags, rule, boxes, self.down)), run_time=0.6)
        bb = bin(D.BIG_B)[2:]
        l1 = MathTex(r"10^9 =", color=WHITE).scale(0.9)
        l2 = VGroup(*[mono(ch, 30, C_YELLOW if ch == "1" else C_GREY) for ch in bb]).arrange(RIGHT, buff=0.05)
        top = VGroup(l1, l2).arrange(RIGHT, buff=0.25).move_to([0, 1.2, 0])
        if top.width > 13:
            top.scale_to_fit_width(13)
        br = Brace(l2, DOWN, buff=0.1, color=C_GREY)
        bl = T(f"{len(bb)} 位", 24, C_GREY).next_to(br, DOWN, buff=0.1)
        res = VGroup(T(f"{len(bb)} 位 + {bb.count('1')} 个 1 =", 30), T(f"{D.pow_mults(D.BIG_B)} 次乘法", 30, C_YELLOW))
        res.arrange(RIGHT, buff=0.2).move_to([0, -0.8, 0])
        vs = VGroup(T("连乘：", 26, C_RED), MathTex(r"10^9", color=C_RED).scale(0.85), T("次", 26, C_RED))
        vs.arrange(RIGHT, buff=0.12).next_to(res, DOWN, buff=0.4)
        self.play(FadeIn(top), run_time=0.6)
        self.play(GrowFromCenter(br), FadeIn(bl), run_time=0.5)
        self.play(FadeIn(res, shift=UP * 0.2), FadeIn(vs), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(top, br, bl, res, vs)), run_time=0.6)

    # ---------------------------------------------------------------- 反例：两次调用
    def twice_beat(self):
        self.beat("twice")
        good = mono("half = fast_pow(a, b // 2, mod)\nres = half * half", 24, C_GREEN)
        good.move_to([0, 2.9, 0])
        self.play(FadeIn(good), run_time=0.6)
        self.wait_until(self.cue_start("如果写成", self.now))
        bad = mono("res = fast_pow(a, b // 2) * fast_pow(a, b // 2)", 24, C_RED).move_to([0, 3.15, 0])
        self.play(ReplacementTransform(good, bad), run_time=0.8)
        # 调用树：每层两个孩子，参数 b → b // 2，到 0 为叶子
        _, calls, mults = D.twice_counts()
        lvls, b = [], D.B
        while True:
            lvls.append(b)
            if b == 0:
                break
            b //= 2
        n_leaf = 2 ** (len(lvls) - 1)
        sp, y0, dy = 0.8, 2.15, 1.05
        pos = [[np.array([-sp * (n_leaf - 1) / 2 + sp * j, y0 - dy * (len(lvls) - 1), 0]) for j in range(n_leaf)]]
        for _ in range(len(lvls) - 1):
            prev = pos[0]
            pos.insert(0, [(prev[2 * j] + prev[2 * j + 1]) / 2 + UP * dy for j in range(len(prev) // 2)])
        nodes, edges = [], VGroup()
        for lv_i, row in enumerate(pos):
            g = VGroup()
            for p in row:
                c = Circle(0.22, color=C_RED if lv_i else C_YELLOW, stroke_width=2.5).move_to(p)
                g.add(VGroup(c, T(str(lvls[lv_i]), 18, WHITE).move_to(p)))
            nodes.append(g)
            if lv_i:
                for j, p in enumerate(row):
                    q = pos[lv_i - 1][j // 2]
                    edges.add(Line(q, p, color=C_GREY, stroke_width=1.5, buff=0.22))
        self.play(FadeIn(nodes[0]), run_time=0.3)
        k = 0
        for lv_i in range(1, len(lvls)):
            m = len(pos[lv_i])
            self.play(Create(VGroup(*edges[k:k + m])), FadeIn(nodes[lv_i]), run_time=0.5)
            k += m
        self.wait_until(self.cue_start("算二的十次方", self.now))
        _, nv = D.naive_pow(D.A, D.B)
        cnt = VGroup(T(f"调用 {calls} 次", 28, C_RED), T("·", 28, C_GREY), T(f"乘法 {mults} 次", 28, C_RED),
                     T("·", 28, C_GREY), T(f"连乘才 {nv} 次", 28, C_GREY)).arrange(RIGHT, buff=0.3)
        cnt.move_to([0, -2.7, 0])
        self.play(FadeIn(cnt, shift=LEFT * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(bad, edges, *nodes, cnt)), run_time=0.6)

    # ---------------------------------------------------------------- 辗转相除
    def gcd_beat(self):
        self.beat("gcd")
        code = Code(code_string="def gcd(a, b):\n    return a if b == 0 else gcd(b, a % b)\n",
                    language="python", formatter_style="monokai", background="window", add_line_numbers=False,
                    paragraph_config={"font": MONO, "font_size": 26})
        code.move_to([0, 2.3, 0])
        head = T("最大公约数 · OpenJudge 03248", 26, C_GREY).next_to(code, UP, buff=0.2)
        self.play(FadeIn(head), FadeIn(code, shift=UP * 0.2), run_time=0.8)
        self.wait_until(self.cue_start("辗转相除", self.now))
        rule = MathTex(r"\gcd(a,b)=\gcd(b,\ a \bmod b)", color=C_YELLOW).scale(0.95).move_to([0, 0.75, 0])
        self.play(Write(rule), run_time=1.2)
        self.wait_until(self.cue_start("讲义的例子", self.now))
        tr = D.gcd_trace(D.G12, D.G18)
        items = VGroup()
        for k, (x, y) in enumerate(tr):
            items.add(MathTex(rf"({x},\ {y})", color=WHITE).scale(0.9))
            items.add(MathTex(r"\to", color=C_GREY).scale(0.9))
        items.add(MathTex(str(D.gcd(D.G12, D.G18)), color=C_YELLOW).scale(1.2))
        items.arrange(RIGHT, buff=0.35).move_to([0, -0.9, 0])
        keys = ("十二和十八", "换成", "再到十二和六", "六和零", "答案是六")
        for k, key in enumerate(keys):
            self.wait_until(self.cue_at(key, self.now))
            grp = [items[2 * k]] + ([items[2 * k - 1]] if k else [])
            self.play(*[FadeIn(m, shift=RIGHT * 0.15) for m in grp], run_time=0.45)
        lc = VGroup(mono(f"lcm({D.L4}, {D.L6}) = {D.L4} // gcd * {D.L6} = {D.lcm(D.L4, D.L6)}", 22, C_GREY))
        lc.move_to([0, -2.2, 0])
        self.play(Circumscribe(items[-1], color=C_YELLOW), FadeIn(lc), run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(head, code, rule, items, lc)), run_time=0.6)

    # ---------------------------------------------------------------- 长方形切正方形
    def rect_beat(self):
        self.beat("rect")
        w, h = D.RECT
        s = 12.0 / w
        origin = np.array([-6.0, 0.15 - h * s / 2, 0])
        frame = Rectangle(width=w * s, height=h * s, color=WHITE, stroke_width=3)
        frame.move_to(origin + np.array([w * s / 2, h * s / 2, 0]))
        lw = MathTex(str(w), color=C_GREY).scale(0.8).next_to(frame, UP, buff=0.12)
        lh = MathTex(str(h), color=C_GREY).scale(0.8).next_to(frame, LEFT, buff=0.12)
        self.play(Create(frame), FadeIn(lw), FadeIn(lh), run_time=1.0)
        tiles = D.square_tiles(w, h)
        groups = D.squares(w, h)
        keys = ("先切下", "切一个", "切三个", "再切两个")
        sq_all = VGroup()
        rem_lab = None
        k = 0
        rw, rh = w, h
        for gi, ((side, cntk), key) in enumerate(zip(groups, keys)):
            self.wait_until(self.cue_at(key, self.now))
            col = SQ_COLOR[gi % len(SQ_COLOR)]
            g = VGroup()
            for x, y, sd in tiles[k:k + cntk]:
                sq = Square(sd * s, stroke_color=col, stroke_width=3).set_fill(col, 0.22)
                sq.move_to(origin + np.array([(x + sd / 2) * s, (y + sd / 2) * s, 0]))
                lab = MathTex(str(sd), color=col).scale(min(1.0, 0.25 + 0.03 * sd))
                lab.move_to(sq)
                g.add(VGroup(sq, lab))
            k += cntk
            if rw >= rh:
                rw -= cntk * rh
            else:
                rh -= cntk * rw
            anims = [LaggedStart(*[FadeIn(q, scale=0.9) for q in g], lag_ratio=0.3)]
            if rw and rh:
                nl = T(f"剩下 {max(rw, rh)} × {min(rw, rh)}", 26, WHITE).move_to([0, -2.55, 0])
            else:
                nl = T("正好切完", 26, C_GREEN).move_to([0, -2.55, 0])
            anims.append(FadeIn(nl) if rem_lab is None else Transform(rem_lab, nl))
            self.play(*anims, run_time=0.9)
            if rem_lab is None:
                rem_lab = nl
            sq_all.add(g)
        self.wait_until(self.cue_start("最后的边长", self.now))
        last = sq_all[-1]
        ans = VGroup(MathTex(rf"\gcd({w},\ {h})=", color=WHITE).scale(0.9),
                     MathTex(str(D.gcd(w, h)), color=C_RED).scale(1.1)).arrange(RIGHT, buff=0.12)
        ans.move_to([0, -2.55, 0])
        self.play(*[Indicate(q[0], color=C_RED, scale_factor=1.6) for q in last], Transform(rem_lab, ans),
                  run_time=1.0)
        self.wait(max(0.1, self.left() - 0.2))
        self.rect = VGroup(frame, lw, lh, sq_all)
        self.rem_lab, self.rect_s, self.rect_origin = rem_lab, s, origin

    # ---------------------------------------------------------------- 为什么对
    def why_beat(self):
        self.beat("why")
        w, h = D.RECT
        sc = 0.72
        self.play(self.rect.animate.scale(sc).move_to([0, 1.25, 0]), FadeOut(self.rem_lab), run_time=0.8)
        f1 = MathTex(r"a = k\,b + r", color=WHITE).scale(0.95)
        f2 = VGroup(MathTex(r"d\mid b,\ d\mid r", color=C_TEAL).scale(0.85), MathTex(r"\Longleftrightarrow").scale(0.85),
                    MathTex(r"d\mid a,\ d\mid b", color=C_TEAL).scale(0.85)).arrange(RIGHT, buff=0.3)
        VGroup(f1, f2).arrange(RIGHT, buff=1.0).move_to([0, -1.55, 0])
        self.play(Write(f1), run_time=0.8)
        self.wait_until(self.cue_start("同时整除", self.now))
        self.play(FadeIn(f2[0]), FadeIn(f2[1]), FadeIn(f2[2]), run_time=0.9)
        self.wait_until(self.cue_start("两对数", self.now))
        same = T("两对数的公约数完全相同", 28, C_YELLOW).move_to([0, -2.45, 0])
        self.play(FadeIn(same, shift=UP * 0.15), run_time=0.6)
        self.wait_until(self.cue_start("在图上", self.now))
        frame = self.rect[0]
        g = D.gcd(w, h)
        step = frame.width / (w / g)
        x0, x1, y0, y1 = frame.get_left()[0], frame.get_right()[0], frame.get_bottom()[1], frame.get_top()[1]
        grid = VGroup(*[Line([x0 + step * i, y0, 0], [x0 + step * i, y1, 0]) for i in range(1, w // g)],
                      *[Line([x0, y0 + step * j, 0], [x1, y0 + step * j, 0]) for j in range(1, h // g)])
        grid.set_stroke(WHITE, 1, 0.45)
        tile = T(f"边长 {g} 的小方块", 24, C_RED).next_to(frame, DOWN, buff=0.2)
        self.play(Create(grid), FadeIn(tile), run_time=1.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(self.rect, grid, tile, f1, f2, same)), run_time=0.6)

    # ---------------------------------------------------------------- 每两步至少减半
    def halving_beat(self):
        self.beat("halving")
        c1 = MathTex(r"b \le \tfrac{a}{2}:", r"\quad r < b \le \tfrac{a}{2}").scale(0.85)
        c2 = MathTex(r"b > \tfrac{a}{2}:", r"\quad r = a-b < \tfrac{a}{2}").scale(0.85)
        for c in (c1, c2):
            c[0].set_color(C_BLUE)
        VGroup(c1, c2).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to([0, 2.7, 0])
        firsts, _ = D.halving(*D.RECT)
        base, hs = -2.25, 3.0 / max(firsts)
        xs = [-4.4 + 2.2 * k for k in range(len(firsts))]
        bars = VGroup()
        for v, x in zip(firsts, xs):
            r = Rectangle(width=0.9, height=max(0.04, v * hs), stroke_color=C_BLUE, stroke_width=2)
            r.set_fill(C_BLUE, 0.25).move_to([x, base + v * hs / 2, 0])
            bars.add(VGroup(r, MathTex(str(v), color=WHITE).scale(0.75).move_to([x, base - 0.32, 0])))
        cap = T("辗转相除的第一个数", 24, C_GREY).move_to([3.2, 0.9, 0])
        self.play(FadeIn(c1, shift=UP * 0.15), FadeIn(cap),
                  LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in bars], lag_ratio=0.15), run_time=1.2)
        self.wait_until(self.cue_start("b 超过一半", self.now))
        self.play(FadeIn(c2, shift=UP * 0.15), run_time=0.7)
        self.wait_until(self.cue_start("两种情况", self.now))
        box = SurroundingRectangle(VGroup(c1[1], c2[1]), color=C_YELLOW, buff=0.12)
        self.play(Create(box), run_time=0.6)
        keys = ("所以每走两步", "二十一")
        for k in range(0, len(firsts) - 2, 2):
            self.wait_until(self.cue_at(keys[k // 2], self.now))
            y = base + firsts[k] * hs / 2
            half = DashedLine([xs[k] - 0.45, y, 0], [xs[k + 2] + 0.45, y, 0], color=C_YELLOW, stroke_width=2.5)
            hl = MathTex(rf"\frac{{{firsts[k]}}}{{2}}", color=C_YELLOW).scale(0.6).next_to(half, UP, buff=0.08)
            hl.set_x((xs[k] + xs[k + 1]) / 2 + 0.5)
            self.play(Create(half), FadeIn(hl), bars[k + 2][0].animate.set_fill(C_GREEN, 0.6).set_stroke(C_GREEN),
                      Indicate(bars[k + 2][1], color=C_GREEN), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(Group(*self.mobjects_without_subs())), run_time=0.6)

    def mobjects_without_subs(self):
        sub_ids = {id(s) for s in self.subs}
        frame = getattr(self.camera, "frame", None)
        return [m for m in self.mobjects if id(m) not in sub_ids and m is not frame]

    # ---------------------------------------------------------------- 分支递归与单链递归
    def contrast_beat(self):
        self.beat("contrast")
        hanoi, perm, chain = self.three_trees(0.5)
        heads = VGroup(T("汉诺塔", 28), T("全排列", 28), VGroup(T("快速幂 · 辗转相除", 26, C_YELLOW), T("二分查找", 26, C_YELLOW)).arrange(DOWN, buff=0.12))
        cx = VGroup(MathTex(r"2^n", color=C_RED).scale(1.0), MathTex(r"n\cdot n!", color=C_RED).scale(1.0),
                    MathTex(r"\log n", color=C_GREEN).scale(1.0))
        for hd, c, t in zip(heads, cx, (hanoi, perm, chain)):
            hd.next_to(t, UP, buff=0.35)
            c.next_to(t, DOWN, buff=0.35)
        keys = ("汉诺塔", "全排列", "快速幂")
        for t, hd, c, key in zip((hanoi, perm, chain), heads, cx, keys):
            self.wait_until(self.cue_at(key, self.now))
            self.play(Create(t[0]), FadeIn(t[1]), FadeIn(hd), FadeIn(c, shift=UP * 0.15), run_time=1.0)
        self.wait_until(self.cue_start("链长", self.now))
        note = T("链长 = 规模减半的次数", 26, C_GREEN).move_to([0, -2.6, 0])
        self.play(FadeIn(note), Circumscribe(VGroup(chain, cx[2]), color=C_GREEN), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(hanoi, perm, heads[:2], cx[:2], note)),
                  VGroup(chain, heads[2], cx[2]).animate.move_to([0, 0.6, 0]), run_time=0.6)
        self.keep = VGroup(chain, heads[2], cx[2])

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        key = VGroup(T("每次砍掉一半，只往一边走", 34, C_YELLOW), T("一条链就够了", 30)).arrange(DOWN, buff=0.25)
        key.move_to([0, -2.05, 0])
        self.play(self.keep.animate.move_to([0, 1.55, 0]), run_time=0.5)
        self.play(Write(key[0]), run_time=1.0)
        self.wait_until(self.cue_start("一条链", self.now))
        self.play(FadeIn(key[1]), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 8 周 递归 第 4 节 分治 · OpenJudge 03248", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
