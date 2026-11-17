"""程序是怎么跑起来的：字节码、内存与缓存（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。字节码列表与条数、时间层次换算、缓存命中序列、系统调用次数全部来自 runtimedata
（讲义 1.2 / 3.2 / 4.2 节代码原样编译或执行；test_runtime.py 用独立实现对撞，并检查旁白数字）。
字节码随 Python 版本略有差异，画面上的列表取渲染机器上的 dis 结果。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtimedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

CODE_C = "#D8DCE6"


def code_block(lines, size=24, color=CODE_C, buff=0.16):
    """等宽代码块：Text 会吃掉行首空格，缩进手工补。"""
    cw = Text("x" * 20, font=MONO, font_size=size).width / 20
    g = VGroup(*[Text(s.strip() or " ", font=MONO, font_size=size, color=color) for s in lines])
    g.arrange(DOWN, aligned_edge=LEFT, buff=buff)
    for ln, s in zip(g, lines):
        ln.shift(RIGHT * cw * (len(s) - len(s.lstrip())))
    return g


def strip_comment(src):
    return [ln.split("#")[0].rstrip() for ln in src.splitlines() if ln.strip()]


def gloss(op, arg):
    """字节码的中文注解（按操作名，不按位置，版本不同也能对上）。"""
    if op == "FOR_ITER":
        return "取下一个数"
    if op.startswith("JUMP_BACKWARD"):
        return "跳回开头"
    if op == "BINARY_OP" and "+" in arg:
        return "相加"
    if op.startswith("STORE"):
        return f"存进 {arg}" if arg == "i" else f"存回 {arg}"
    if op.startswith("LOAD"):
        return f"读出 {arg}"
    return ""


def show_arg(op, arg):
    return "" if op in ("FOR_ITER",) or op.startswith("JUMP") else arg


class RuntimeLesson(Lesson):
    def construct(self):
        for b in ("title", "compile", "bytecode", "ladder", "cache", "python", "buffer", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key, default=None):
        """含 key 的那句字幕里，key 大约开始念的时刻（按字数比例插值）。"""
        for c in self.cue_times():
            k = c["text"].find(key)
            if k >= 0:
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return default

    def hold(self, key, fallback=0.0):
        self.wait_until(self.at(key, self.now + fallback))

    def outro(self, *mobs):
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*mobs)), run_time=0.6)

    # ---------------------------------------------------------------- 片头：循环与 sum
    def title_beat(self):
        self.beat("title")
        head = VGroup(T("把", 30), Text("n = 3_000_000", font=MONO, font_size=30, color=C_YELLOW),
                      T("个数加起来", 30)).arrange(RIGHT, buff=0.2).move_to([0, 3.35, 0])
        loop = code_block(strip_comment(D.LOOP_SRC), 28)
        summ = code_block(strip_comment(D.SUM_SRC), 28)
        pl = VGroup(RoundedRectangle(corner_radius=0.15, width=5.4, height=2.0, stroke_color=C_BLUE, stroke_width=3),
                    loop).move_to([-3.4, 1.35, 0])
        loop.move_to(pl[0])
        ps = VGroup(RoundedRectangle(corner_radius=0.15, width=5.4, height=2.0, stroke_color=C_TEAL, stroke_width=3),
                    summ).move_to([3.4, 1.35, 0])
        summ.move_to(ps[0])
        tl = T("Python 循环", 24, C_BLUE).next_to(pl, UP, buff=0.12).align_to(pl, LEFT)
        ts = T("内建 sum（C 实现）", 24, C_TEAL).next_to(ps, UP, buff=0.12).align_to(ps, LEFT)
        self.play(FadeIn(head), run_time=0.6)
        self.hold("写一个")
        self.play(FadeIn(pl, shift=UP * 0.2), FadeIn(tl), run_time=0.8)
        scale = 4.5 / D.TYPICAL["loop"]
        y = -0.35
        b1 = Rectangle(width=D.TYPICAL["loop"] * scale, height=0.4, stroke_width=0).set_fill(C_BLUE, 0.85)
        b1.move_to([-5.9 + b1.width / 2, y, 0])
        l1 = T(f"约 {D.TYPICAL['loop']} 秒", 26, C_BLUE).next_to(b1, RIGHT, buff=0.2)
        self.hold("零点二秒")
        self.play(GrowFromEdge(b1, LEFT), FadeIn(l1), run_time=0.9)
        self.hold("换成内建")
        self.play(FadeIn(ps, shift=UP * 0.2), FadeIn(ts), run_time=0.8)
        b2 = Rectangle(width=D.TYPICAL["sum"] * scale, height=0.4, stroke_width=0).set_fill(C_TEAL, 0.85)
        b2.move_to([-5.9 + b2.width / 2, y - 0.7, 0])
        l2 = T(f"约 {D.TYPICAL['sum']} 秒", 26, C_TEAL).next_to(b2, RIGHT, buff=0.2)
        note = T("讲义给的典型结果，随机器而异", 20, C_GREY).move_to([3.4, y - 0.35, 0])
        self.hold("零点零三秒")
        self.play(GrowFromEdge(b2, LEFT), FadeIn(l2), FadeIn(note), run_time=0.9)
        self.hold("程序到底")
        title = T("程序是怎么跑起来的", 52).move_to([0, -1.75, 0])
        sub = T("字节码 · 存储层次 · 缓存 · 缓冲", 28, C_YELLOW).next_to(title, DOWN, buff=0.22)
        self.play(VGroup(head, pl, ps, tl, ts, b1, b2, l1, l2, note).animate.fade(0.7),
                  Write(title), run_time=1.2)
        self.hold("今天从")
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.7)
        self.outro(head, pl, ps, tl, ts, b1, b2, l1, l2, note, title, sub)

    # ---------------------------------------------------------------- 编译型与解释型
    def pipeline(self, names, y, color, widths):
        boxes, arrows = VGroup(), VGroup()
        x = -3.3
        for k, (nm, w) in enumerate(zip(names, widths)):
            b = RoundedRectangle(corner_radius=0.12, width=w, height=0.95, stroke_color=color, stroke_width=3)
            b.move_to([x + w / 2, y, 0])
            t = T(nm, 24, WHITE if k else CODE_C, line_spacing=0.8).move_to(b)
            boxes.add(VGroup(b, t))
            if k:
                prev = boxes[k - 1][0]
                arrows.add(Arrow(prev.get_right(), b.get_left(), buff=0.06, stroke_width=4, color=C_GREY,
                                 max_tip_length_to_length_ratio=0.35))
            x += w + 0.6
        return boxes, arrows

    @staticmethod
    def interleave(boxes, arrows):
        out = [boxes[0]]
        for a, b in zip(arrows, boxes[1:]):
            out += [a, b]
        return out

    def compile_beat(self):
        self.beat("compile")
        lc = VGroup(T("编译型", 32, C_BLUE), T("C / C++", 24, C_GREY)).arrange(DOWN, buff=0.12)
        lc.move_to([-5.4, 1.6, 0])
        bc, ac = self.pipeline(["源码", "编译器", "机器码", "CPU"], 1.6, C_BLUE, [1.4, 1.6, 1.6, 1.3])
        self.play(FadeIn(lc), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(m) for m in self.interleave(bc, ac)], lag_ratio=0.25), run_time=1.8)
        self.hold("CPU 直接执行")
        dot = Dot(color=C_YELLOW, radius=0.09).move_to(bc[2][0].get_right())
        self.play(MoveAlongPath(dot, Line(bc[2][0].get_right(), bc[3][0].get_center())), run_time=0.6)
        self.play(Indicate(bc[3], color=C_YELLOW), FadeOut(dot), run_time=0.6)
        lp = VGroup(T("解释型", 32, C_TEAL), T("Python", 24, C_GREY)).arrange(DOWN, buff=0.12)
        lp.move_to([-5.4, -0.6, 0])
        bp, ap = self.pipeline(["源码", "字节码", "虚拟机\n逐条解释", "C 函数", "CPU"], -0.6, C_TEAL,
                               [1.3, 1.5, 1.9, 1.5, 1.2])
        self.hold("Python 是解释型")
        self.play(FadeIn(lp), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(m) for m in self.interleave(bp, ap)], lag_ratio=0.25), run_time=2.0)
        self.hold("一条一条")
        loop = Arc(radius=0.35, start_angle=PI * 0.75, angle=-1.5 * PI, color=C_YELLOW, stroke_width=4)
        loop.add_tip(tip_length=0.15, tip_width=0.15)
        loop.next_to(bp[2], UP, buff=0.1)
        ltxt = T("每条一次分派", 22, C_YELLOW).next_to(loop, RIGHT, buff=0.15)
        self.play(Create(loop), FadeIn(ltxt), run_time=0.8)
        self.hold("每一条都要")
        self.play(Indicate(bp[3], color=C_YELLOW), Indicate(ap[2], color=C_YELLOW), run_time=0.9)
        self.hold("所以同样的算法")
        slow = VGroup(T("同样的算法，Python 常常慢", 30), T("10–100 倍", 34, C_RED)).arrange(RIGHT, buff=0.2)
        slow.move_to([0, -2.05, 0])
        self.play(FadeIn(slow, shift=UP * 0.2), run_time=0.8)
        self.hold("C++ 能过")
        tip = VGroup(T("C++ 能过的平方级做法，Python 可能超时：", 24, C_GREY),
                     T("换更好的算法", 26, C_GREEN)).arrange(RIGHT, buff=0.1).move_to([0, -2.7, 0])
        self.play(FadeIn(tip[0], shift=UP * 0.15), run_time=0.7)
        self.hold("而是换")
        self.play(FadeIn(tip[1], shift=UP * 0.15), run_time=0.6)
        self.outro(lc, bc, ac, lp, bp, ap, loop, ltxt, slow, tip)

    # ---------------------------------------------------------------- 字节码：七条 vs 十来条
    def bytecode_beat(self):
        self.beat("bytecode")
        src = code_block(strip_comment(D.LOOP_SRC), 26).move_to([-4.1, 2.35, 0])
        sbox = SurroundingRectangle(src, color=C_BLUE, buff=0.2, corner_radius=0.1)
        cap = Text("import dis", font=MONO, font_size=22, color=C_GREY).next_to(sbox, DOWN, buff=0.18).align_to(sbox, LEFT)
        body = D.loop_body()
        rows = VGroup()
        for op, arg in body:
            a = show_arg(op, arg)
            r = VGroup(Text(op, font=MONO, font_size=24, color=CODE_C),
                       Text(a or " ", font=MONO, font_size=24, color=C_YELLOW),
                       T(gloss(op, arg), 22, C_GREY))
            rows.add(r)
        x0 = 0.0
        for k, r in enumerate(rows):
            y = 2.55 - 0.6 * k
            r[0].move_to([x0, y, 0], aligned_edge=LEFT)
            r[1].move_to([x0 + 3.3, y, 0], aligned_edge=LEFT)
            r[2].move_to([x0 + 4.4, y, 0], aligned_edge=LEFT)
        rows[0][0].set_color(C_TEAL)
        bracket = Brace(VGroup(*[r[0] for r in rows]), LEFT, color=C_BLUE, buff=0.35)
        btxt = T(f"每圈 {len(body)} 条", 26, C_BLUE).next_to(bracket, LEFT, buff=0.15)
        self.play(FadeIn(src), Create(sbox), FadeIn(cap), run_time=0.8)
        self.hold("每转一圈")
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rows], lag_ratio=0.12), run_time=1.4)
        self.play(GrowFromCenter(bracket), FadeIn(btxt), run_time=0.6)
        ptr = Triangle(color=C_YELLOW, fill_opacity=1, stroke_width=0).scale(0.1).rotate(-PI / 2)
        ptr.next_to(rows[0], LEFT, buff=0.1)
        cnt = [0]
        ctr = VGroup(T("已执行", 26, C_GREY), Integer(0, color=C_YELLOW).scale(0.9), T("条", 26, C_GREY))
        ctr.arrange(RIGHT, buff=0.15).move_to([-4.1, 0.2, 0])
        self.play(FadeIn(ptr), FadeIn(ctr), run_time=0.4)
        keys = ["取下一个数", "存进 i", "读出 s", "读出 s", "相加", "存回 s", "跳回开头"]

        def step(k, rt):
            cnt[0] += 1
            new = Integer(cnt[0], color=C_YELLOW).scale(0.9).move_to(ctr[1], aligned_edge=LEFT)
            self.play(ptr.animate.next_to(rows[k], LEFT, buff=0.1).set_x(rows[k][0].get_left()[0] - 0.2),
                      rows[k][2].animate.set_color(WHITE), Transform(ctr[1], new), run_time=rt)
            ctr[2].next_to(ctr[1], RIGHT, buff=0.15)
        for k in range(len(rows)):
            key = keys[k] if k < len(keys) else None
            if key and k != 3:
                self.hold(key)
            step(k, 0.35)
        for _ in range(2):                                     # 再快转两圈
            for k in range(len(rows)):
                step(k, 0.09)
        self.hold("三百万圈")
        per, base = D.loop_formula()
        total = D.loop_total()
        eq = VGroup(MathTex(rf"{per}\times 3{{,}}000{{,}}000 + {base}", color=C_GREY).scale(0.75),
                    MathTex(r"=", color=C_GREY).scale(0.75),
                    MathTex(f"{total:,}".replace(",", "{,}"), color=C_YELLOW).scale(0.9)).arrange(RIGHT, buff=0.15)
        eq.move_to([-3.6, -0.55, 0])
        self.play(FadeOut(ptr), ctr.animate.set_opacity(0.35), Write(eq), run_time=1.1)
        self.hold("一次分派")
        disp = T("每一条：解释器里的一次分派", 24, C_BLUE).move_to([-3.6, -1.3, 0])
        self.play(FadeIn(disp, shift=UP * 0.15), run_time=0.6)
        self.hold("sum 那一行")
        sl = D.listing(D.SUM_SRC)
        srow = VGroup(*[Text(f"{op} {show_arg(op, a)}".rstrip(), font=MONO, font_size=24, color=C_TEAL) for op, a in sl])
        srow.arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        if srow.height > 5.2:
            srow.scale_to_fit_height(5.2)
        srow.move_to([2.4, 0.2, 0], aligned_edge=LEFT).align_to(rows[0], UP)
        ssrc = code_block(strip_comment(D.SUM_SRC), 26).move_to([-4.1, 2.35, 0])
        self.play(FadeOut(VGroup(rows, bracket, btxt)), FadeOut(src), Transform(sbox, SurroundingRectangle(
            ssrc, color=C_TEAL, buff=0.2, corner_radius=0.1)), FadeIn(ssrc), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.15) for r in srow], lag_ratio=0.08), run_time=1.2)
        n_sum = D.sum_total()
        stot = VGroup(T("sum 版：一共执行", 26, C_TEAL), MathTex(str(n_sum), color=C_TEAL).scale(0.9),
                      T("条", 26, C_TEAL)).arrange(RIGHT, buff=0.15).move_to([-3.6, -2.05, 0])
        self.hold("不管 n 多大")
        self.play(FadeIn(stot, shift=UP * 0.15), run_time=0.7)
        self.hold("循环在 C 里面")
        inc = T("range 的循环在 C 里跑", 22, C_GREY).next_to(srow, DOWN, buff=0.25).align_to(srow, LEFT)
        self.play(FadeIn(inc), run_time=0.6)
        self.hold("所以能交给")
        self.play(Indicate(stot, color=C_YELLOW, scale_factor=1.08), run_time=0.9)
        self.outro(sbox, cap, ctr, eq, disp, srow, ssrc, stot, inc)

    # ---------------------------------------------------------------- 时间层次：1 纳秒 = 1 秒
    def ladder_beat(self):
        self.beat("ladder")
        h1 = T("真实时间", 22, C_GREY).move_to([-3.3, 3.3, 0])
        h2 = VGroup(T("放大：1 纳秒", 26, C_YELLOW), MathTex(r"\to", color=C_YELLOW).scale(0.8),
                    T("1 秒", 26, C_YELLOW)).arrange(RIGHT, buff=0.15).move_to([0.6, 3.3, 0])
        self.play(FadeIn(h1), FadeIn(h2), run_time=0.7)
        keys = ["一级缓存", "二级缓存", "内存，一百秒", "固态硬盘", "同城网络", "机械硬盘"]
        cols = [C_TEAL, C_TEAL, C_BLUE, C_PURPLE, C_YELLOW, C_RED]
        X0, U = -2.6, 0.84
        rows = VGroup()
        for k, ((name, ns), key, col) in enumerate(zip(D.LATENCY, keys, cols)):
            y = 2.5 - 0.8 * k
            nm = T(name, 24).move_to([-6.6, y, 0], aligned_edge=LEFT)
            rl = Text(D.real(ns), font=MONO, font_size=22, color=C_GREY).move_to([-2.8, y, 0], aligned_edge=RIGHT)
            w = U * (math.log10(ns) + 1)
            bar = Rectangle(width=w, height=0.38, stroke_width=0).set_fill(col, 0.85)
            bar.move_to([X0 + w / 2, y, 0])
            v, unit = D.human(ns)
            hm = T(f"{v} {unit}", 26, col).next_to(bar, RIGHT, buff=0.2)
            self.hold(key)
            self.play(FadeIn(nm), FadeIn(rl), GrowFromEdge(bar, LEFT), FadeIn(hm, shift=LEFT * 0.1), run_time=0.7)
            rows.add(VGroup(nm, rl, bar, hm))
        axis = Line([X0, 2.95, 0], [X0, -1.95, 0], color=C_GREY, stroke_width=1.5)
        scale_note = T("条长按对数刻度", 20, C_GREY).move_to([5.6, -2.0, 0])
        self.play(Create(axis), FadeIn(scale_note), run_time=0.5)
        self.hold("所以少读")
        v1, u1 = D.human(D.ADDS)
        v2, u2 = D.human(dict(D.LATENCY)["磁盘寻道"])
        cmp_ = VGroup(T("少读一次磁盘", 28, C_RED), T(f"（{v2} {u2}）", 24, C_GREY), MathTex(r"\gg", color=WHITE).scale(0.9),
                      T("少算一万次加法", 28, C_TEAL), T(f"（约 {v1} {u1}）", 24, C_GREY)).arrange(RIGHT, buff=0.15)
        cmp_.move_to([0, -2.6, 0])
        self.play(FadeIn(cmp_, shift=UP * 0.15), Indicate(rows[-1][2], color=C_RED, scale_factor=1.03), run_time=0.9)
        self.outro(h1, h2, rows, axis, scale_note, cmp_)

    # ---------------------------------------------------------------- 缓存行：按行 vs 按列
    CS = 0.52                                   # 矩阵格宽
    MX, MY = -3.75, 0.55                        # 矩阵中心

    def cpos(self, i, j):
        n = D.N_GRID
        return np.array([self.MX + (j - (n - 1) / 2) * self.CS, self.MY + ((n - 1) / 2 - i) * self.CS, 0])

    def cache_beat(self):
        self.beat("cache")
        n, L, W = D.N_GRID, D.LINE, D.WAYS
        cells = {(i, j): Square(self.CS * 0.9, stroke_color=C_GREY, stroke_width=1.5).move_to(self.cpos(i, j))
                 for i in range(n) for j in range(n)}
        groups = VGroup()
        for i in range(n):
            for c in range(n // L):
                a, b = self.cpos(i, c * L), self.cpos(i, c * L + L - 1)
                g = RoundedRectangle(corner_radius=0.06, width=b[0] - a[0] + self.CS * 0.98, height=self.CS * 0.98,
                                     stroke_color=C_BLUE, stroke_width=2.5).move_to((a + b) / 2)
                groups.add(g)
        grid = VGroup(*cells.values())
        mh = T("内存：矩阵按行连续存放", 24, C_GREY).next_to(grid, UP, buff=0.25)
        self.play(FadeIn(mh), Create(grid), run_time=1.2)
        self.hold("一整个缓存行")
        self.play(Create(groups), run_time=1.0)
        lt = T(f"一个缓存行 = {L} 个数", 24, C_BLUE).next_to(grid, DOWN, buff=0.25)
        real = T("（示意；真实缓存行 64 字节）", 18, C_GREY).next_to(lt, DOWN, buff=0.1)
        self.play(FadeIn(lt), FadeIn(real), run_time=0.6)
        # 缓存面板
        SX, SY = 1.3, 1.75
        ch = T(f"缓存：只放得下 {W} 个缓存行", 24, C_GREY).move_to([SX + 1.9, 2.65, 0])
        slots, slot_lab = VGroup(), VGroup()
        for s in range(W):
            y = SY - 0.62 * s
            sl = VGroup(*[Square(self.CS * 0.9, stroke_color=C_GREY, stroke_width=1.5).move_to(
                [SX + k * self.CS, y, 0]) for k in range(L)])
            slots.add(sl)
            slot_lab.add(T("空", 22, C_GREY).move_to([SX + L * self.CS + 0.9, y, 0]))
        self.hold("缓存一共")
        self.play(FadeIn(ch), Create(slots), FadeIn(slot_lab), run_time=0.9)
        hc = VGroup(T("命中", 26, C_GREEN), Integer(0, color=C_GREEN).scale(0.85),
                    T("缺失", 26, C_RED), Integer(0, color=C_RED).scale(0.85))
        hc[0].move_to([SX + 0.3, -1.0, 0])
        hc[1].next_to(hc[0], RIGHT, buff=0.2)
        hc[2].move_to([SX + 2.6, -1.0, 0])
        hc[3].next_to(hc[2], RIGHT, buff=0.2)
        mode = T("按行遍历", 30, C_YELLOW).move_to([SX + 1.6, -1.75, 0])
        cur = Square(self.CS, stroke_color=C_YELLOW, stroke_width=4).move_to(self.cpos(0, 0))
        fills = {}

        def run(order, fast_after, rt_slow, rt_fast, key_hits=None):
            where = {}                                  # 缓存行 -> 槽位
            nh = nm = 0
            sim = D.simulate(order)
            pend, pend_cur = [], [None]
            for k, (i, j, hit, ev, _) in enumerate(sim):
                if k == 1 and key_hits:
                    self.hold(key_hits)
                key = (i, j // L)
                anims = [cur.animate.move_to(self.cpos(i, j))]
                col = C_GREEN if hit else C_RED
                fills[(i, j)] = cells[(i, j)]
                anims.append(cells[(i, j)].animate.set_fill(col, 0.5))
                if hit:
                    nh += 1
                    new = Integer(nh, color=C_GREEN).scale(0.85).move_to(hc[1], aligned_edge=LEFT)
                    anims.append(Transform(hc[1], new))
                    anims.append(Indicate(slots[where[key]][j % L], color=C_GREEN, scale_factor=1.0))
                else:
                    nm += 1
                    new = Integer(nm, color=C_RED).scale(0.85).move_to(hc[3], aligned_edge=LEFT)
                    anims.append(Transform(hc[3], new))
                    if ev is not None:
                        s = where.pop(ev)
                    else:
                        s = len(where)
                    where[key] = s
                    lab = T(f"第{i + 1}行 {key[1] * L + 1}–{key[1] * L + L}列", 22, WHITE).move_to(slot_lab[s])
                    anims.append(Transform(slot_lab[s], lab))
                    anims += [slots[s][q].animate.set_fill(C_BLUE, 0.35) for q in range(L)]
                    g = groups[i * (n // L) + key[1]]
                    anims.append(Indicate(g, color=C_RED, scale_factor=1.0))
                if k < fast_after:
                    self.play(*anims, run_time=rt_slow)
                else:                                   # 快放：每 4 次访问并成一段动画（帧数不够逐个放）
                    pend.extend(anims[1:])
                    pend_cur[0] = anims[0]
                    if (k - fast_after) % 4 == 3 or k == len(sim) - 1:
                        self.play(pend_cur[0], *pend, run_time=rt_fast)
                        pend.clear()
            return nh, nm
        self.hold("按行遍历")
        self.play(FadeIn(hc), FadeIn(mode), FadeIn(cur), run_time=0.5)
        run(D.row_major(), 4, 0.5, 0.3, key_hits="后面三次")
        self.hold("六十四次访问")
        r1 = T(f"按行：{len(D.row_major())} 次访问，缺失 {D.misses(D.row_major())} 次", 24, C_GREEN)
        r1.move_to([SX + 1.6, -2.4, 0])
        self.play(FadeIn(r1), run_time=0.5)
        self.hold("按列遍历")
        reset = [cells[k].animate.set_fill(BLACK, 0) for k in cells]
        reset += [slots[s][q].animate.set_fill(BLACK, 0) for s in range(W) for q in range(L)]
        reset += [Transform(slot_lab[s], T("空", 22, C_GREY).move_to(slot_lab[s])) for s in range(W)]
        reset += [Transform(hc[1], Integer(0, color=C_GREEN).scale(0.85).move_to(hc[1], aligned_edge=LEFT)),
                  Transform(hc[3], Integer(0, color=C_RED).scale(0.85).move_to(hc[3], aligned_edge=LEFT)),
                  Transform(mode, T("按列遍历", 30, C_YELLOW).move_to(mode)), r1.animate.set_opacity(0.45)]
        self.play(*reset, run_time=0.6)
        run(D.col_major(), 8, 0.3, 0.3)
        r2 = T(f"按列：{len(D.col_major())} 次访问，缺失 {D.misses(D.col_major())} 次", 24, C_RED)
        r2.next_to(r1, DOWN, buff=0.15)
        r1.set_opacity(1)
        self.play(FadeIn(r2), FadeOut(cur), run_time=0.5)
        self.outro(mh, grid, groups, lt, real, ch, slots, slot_lab, hc, mode, r1, r2)

    # ---------------------------------------------------------------- Python 里：指针数组与少两条字节码
    def python_beat(self):
        self.beat("python")
        title = T("空间局部性：顺序访问连续的内存", 34, C_YELLOW).move_to([0, 3.1, 0])
        self.play(FadeIn(title, shift=DOWN * 0.15), run_time=0.7)
        self.hold("讲义里")
        lec = VGroup(T(f"讲义实测 N = {D.N_LECTURE}：", 26),
                     T("按行明显更快（典型结果）", 26, C_GREEN)).arrange(RIGHT, buff=0.1).move_to([0, 2.35, 0])
        self.play(FadeIn(lec), run_time=0.7)
        self.hold("列表存的是指针")
        ptrs = VGroup(*[Square(0.58, stroke_color=C_BLUE, stroke_width=2.5) for _ in range(6)]).arrange(RIGHT, buff=0)
        ptrs.move_to([3.8, 1.5, 0])
        plab = T("列表：一排指针", 22, C_BLUE).next_to(ptrs, LEFT, buff=0.2)
        spots = [(-1.6, -0.5), (-0.7, -1.4), (0.1, -0.4), (1.0, -1.5), (1.8, -0.6), (2.5, -1.3)]
        objs = VGroup(*[Circle(0.26, stroke_color=C_TEAL, stroke_width=2.5).move_to([ptrs.get_x() + dx, dy, 0])
                        for dx, dy in spots])
        arrows = VGroup(*[Arrow(ptrs[k].get_center(), objs[k].get_center(), buff=0.2, stroke_width=2.5, color=C_GREY,
                                max_tip_length_to_length_ratio=0.15) for k in range(6)])
        heap = T("元素散在堆上", 22, C_TEAL).move_to([ptrs.get_x(), -2.45, 0])
        self.play(Create(ptrs), FadeIn(plab), run_time=0.7)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), FadeIn(objs), FadeIn(heap), run_time=1.3)
        self.hold("差距没有")
        weak = T("缓存效应不如 C 明显", 22, C_GREY).next_to(heap, UP, buff=0.12)
        self.play(FadeIn(weak), run_time=0.5)
        self.hold("但把取出")
        rsrc = strip_comment(D.ROW_SRC)[1:]
        csrc = strip_comment(D.COL_SRC)[1:]
        rb = code_block(rsrc, 22, buff=0.12).move_to([-4.0, 1.05, 0]).align_to([-6.6, 0, 0], LEFT)
        cb = code_block(csrc, 22, buff=0.12).move_to([-4.0, -1.3, 0]).align_to([-6.6, 0, 0], LEFT)
        rbox = SurroundingRectangle(rb, color=C_GREEN, buff=0.12, corner_radius=0.08)
        cbox = SurroundingRectangle(cb, color=C_RED, buff=0.12, corner_radius=0.08)
        nr, nc = len(D.inner_body(D.ROW_SRC)), len(D.inner_body(D.COL_SRC))
        rt = T(f"内层每圈 {nr} 条字节码", 22, C_GREEN).next_to(rbox, DOWN, buff=0.1).align_to(rbox, LEFT)
        ct = T(f"内层每圈 {nc} 条字节码", 22, C_RED).next_to(cbox, DOWN, buff=0.1).align_to(cbox, LEFT)
        self.play(FadeIn(rb), Create(rbox), FadeIn(cb), Create(cbox), run_time=0.9)
        self.play(Indicate(rb[1], color=C_YELLOW, scale_factor=1.05), run_time=0.7)
        self.hold("少两条")
        self.play(FadeIn(rt), FadeIn(ct), run_time=0.7)
        self.hold("在 Python 里")
        self.play(Indicate(rt, color=C_YELLOW, scale_factor=1.08), Indicate(ct, color=C_YELLOW, scale_factor=1.08),
                  run_time=1.0)
        self.outro(title, lec, ptrs, plab, objs, arrows, heap, weak, rb, cb, rbox, cbox, rt, ct)

    # ---------------------------------------------------------------- 缓冲：print 与 join
    def buffer_beat(self):
        self.beat("buffer")
        KX = 1.9                                   # 内核边界
        head = T("系统调用：进出一次内核", 30, C_YELLOW).move_to([0, 3.15, 0])
        wall = DashedLine([KX, 2.6, 0], [KX, -2.45, 0], color=C_GREY, stroke_width=2.5, dash_length=0.12)
        wl = VGroup(T("用户程序", 20, C_GREY).next_to([KX, 2.6, 0], LEFT, buff=0.2),
                    T("内核", 20, C_GREY).next_to([KX, 2.6, 0], RIGHT, buff=0.2))
        self.play(FadeIn(head), Create(wall), FadeIn(wl), run_time=0.8)
        ys = [1.75, 0.05, -1.65]

        def label(lines, y, col):
            return VGroup(*[T(s, 24 if k == 0 else 20, col if k == 0 else C_GREY) for k, s in enumerate(lines)]
                          ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to([-6.6, y, 0], aligned_edge=LEFT)

        def counter(y, col):
            num = DecimalNumber(0, num_decimal_places=0, color=col, group_with_commas=True).scale(0.85)
            num.move_to([4.5, y, 0], aligned_edge=LEFT)
            return VGroup(num, T("次", 24, col).move_to([6.3, y, 0]))
        n = D.N_PRINT
        c_term, _ = D.syscalls(D.squares_print, True)
        c_join, _ = D.syscalls(D.squares_join, True)
        c_file, nbytes = D.syscalls(D.squares_print, False)
        self.hold("一万次 print")
        l1 = label(["print × 1 万", "终端：按行刷新"], ys[0], C_RED)
        k1 = counter(ys[0], C_RED)
        self.play(FadeIn(l1), FadeIn(k1), run_time=0.6)
        packets = VGroup(*[Rectangle(width=0.22, height=0.3, stroke_width=0).set_fill(C_RED, 0.8) for _ in range(14)])
        for p in packets:
            p.move_to([-2.4, ys[0], 0])
        self.add(packets)
        moves = [p.animate.move_to([KX + 1.4, ys[0], 0]).set_opacity(0) for p in packets]
        self.play(LaggedStart(*moves, lag_ratio=0.18),
                  ChangeDecimalToValue(k1[0], c_term), run_time=2.6, rate_func=linear)
        self.remove(packets)
        self.hold("先把字符串")
        l2 = label(["join 后写一次", "讲义 4.2 的写法"], ys[1], C_GREEN)
        k2 = counter(ys[1], C_GREEN)
        buf = Rectangle(width=3.4, height=0.42, stroke_color=C_GREEN, stroke_width=2.5).move_to([-0.05, ys[1], 0])
        blab = Text("out", font=MONO, font_size=20, color=C_GREY).next_to(buf, UP, buff=0.08).align_to(buf, LEFT)
        fill = Rectangle(width=3.4, height=0.42, stroke_width=0).set_fill(C_GREEN, 0.55).move_to(buf)
        self.play(FadeIn(l2), FadeIn(k2), Create(buf), FadeIn(blab), run_time=0.6)
        self.play(GrowFromEdge(fill, LEFT), run_time=1.6)
        self.hold("只写一次")
        self.play(fill.animate.move_to([KX + 1.4, ys[1], 0]).stretch_to_fit_width(0.6).set_opacity(0),
                  ChangeDecimalToValue(k2[0], c_join), run_time=0.9)
        self.hold("重定向到文件")
        l3 = label(["print × 1 万", f"文件：{D.FILE_BUF // 1024} KB 缓冲"], ys[2], C_BLUE)
        k3 = counter(ys[2], C_BLUE)
        buf3 = Rectangle(width=3.4, height=0.42, stroke_color=C_BLUE, stroke_width=2.5).move_to([-0.05, ys[2], 0])
        b3l = T(f"{D.FILE_BUF // 1024} KB", 18, C_GREY).next_to(buf3, UP, buff=0.08).align_to(buf3, LEFT)
        self.play(FadeIn(l3), FadeIn(k3), Create(buf3), FadeIn(b3l), run_time=0.6)
        full = math.ceil(nbytes / D.FILE_BUF)
        for q in range(c_file):
            frac = min(1.0, (nbytes - q * D.FILE_BUF) / D.FILE_BUF)
            f3 = Rectangle(width=3.4 * frac, height=0.42, stroke_width=0).set_fill(C_BLUE, 0.55)
            f3.move_to(buf3.get_left() + RIGHT * 3.4 * frac / 2)
            self.play(GrowFromEdge(f3, LEFT), run_time=0.22, rate_func=linear)
            new = DecimalNumber(q + 1, num_decimal_places=0, color=C_BLUE).scale(0.85).move_to(k3[0], aligned_edge=LEFT)
            self.play(f3.animate.move_to([KX + 1.4, ys[2], 0]).stretch_to_fit_width(0.3).set_opacity(0),
                      Transform(k3[0], new), run_time=0.16)
            self.remove(f3)
        assert full == c_file
        self.hold("可一万次")
        still = T("但一万次 print 调用的开销还在", 20, C_GREY).next_to(buf3, DOWN, buff=0.15).align_to(buf3, LEFT)
        self.play(FadeIn(still), run_time=0.6)
        self.hold("输入也一样")
        inp = VGroup(T("输入也一次读完：", 22, C_GREY),
                     Text("sys.stdin.read().split()", font=MONO, font_size=22, color=C_TEAL)).arrange(RIGHT, buff=0.15)
        inp.move_to([0, -2.72, 0])
        self.play(FadeIn(inp, shift=UP * 0.1), run_time=0.6)
        self.outro(head, wall, wl, l1, k1, l2, k2, buf, blab, l3, k3, buf3, b3l, still, inp)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        cards = VGroup()
        for name, body, col in (("字节码", "逐条解释、逐条分派\n循环交给内建函数", C_BLUE),
                                ("存储层次", "一层比一层慢\n顺序访问吃到缓存", C_TEAL),
                                ("缓冲", "输出攒起来\n一次写出去", C_YELLOW)):
            bx = RoundedRectangle(corner_radius=0.2, width=4.1, height=2.6, stroke_color=col, stroke_width=3)
            txt = VGroup(T(name, 34, col), T(body, 26, CODE_C, line_spacing=1.0)).arrange(DOWN, buff=0.35).move_to(bx)
            cards.add(VGroup(bx, txt))
        cards.arrange(RIGHT, buff=0.35).move_to([0, 0.6, 0])
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.8)
        self.hold("存储一层")
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.8)
        self.hold("输出攒起来")
        self.play(FadeIn(cards[2], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 13 周 计算机原理（2/2）1.1–1.2、3.2–3.3、4.2 节", 20, C_GREY)
        src.to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
