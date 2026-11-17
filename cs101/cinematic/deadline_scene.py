"""最多能按时完成几个任务：排序加反悔（例题精讲，3B1B 风格）。

由 make.py 驱动，时间轴约定见 cine.py。主例的排序结果、每步的堆（heapq 数组顺序）、总时长、扔掉的任务、
各扔一个后的剩余总时长、不反悔贪心的结果、对拍两百组数据全部来自 deadlinedata
（讲义 max_tasks / max_tasks_brute / 对拍循环原样；test_deadline.py 用子集枚举对撞逐步不变量与旁白数字）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deadlinedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

C_ORANGE = "#FF9F43"
TCOL = {1: C_TEAL, 2: C_BLUE, 3: C_PURPLE, 4: C_GREEN, 5: C_YELLOW, 6: C_ORANGE}   # 按耗时上色（主例耗时互不相同）
DIM = "#3a4050"


def col(c):
    return TCOL.get(c, C_GREY)


def tup(c, d, size=22, color=WHITE):
    return Text(f"({c}, {d})", font=MONO, font_size=size, color=color)


class Gantt(VGroup):
    """一行一个任务的时间轴：左边 (耗时, 截止) 标签，行内截止线，方块按已选任务的先后紧挨着摆。"""

    def __init__(self, tasks, x0=-5.3, u=0.4, y0=1.75, dy=0.68, tmax=13, h=0.42, label_size=22, axis=True):
        super().__init__()
        self.tasks, self.x0, self.u, self.y0, self.dy, self.h = tasks, x0, u, y0, dy, h
        self.labels, self.marks, self.blocks = VGroup(), VGroup(), {}
        for k, (c, d) in enumerate(tasks):
            y = self.ry(k)
            lab = tup(c, d, label_size, col(c))
            self.labels.add(lab.move_to([x0 - 0.25 - lab.width / 2, y, 0]))
            self.marks.add(Line([self.tx(d), y - h * 0.72, 0], [self.tx(d), y + h * 0.72, 0],
                                color=col(c), stroke_width=5))
        self.add(self.labels, self.marks)
        if axis:
            ya = self.ry(len(tasks) - 1) - 0.5
            self.axis = VGroup(Line([x0, ya, 0], [self.tx(tmax) + 0.15, ya, 0], color=C_GREY, stroke_width=2))
            for t in range(tmax + 1):
                self.axis.add(Line([self.tx(t), ya, 0], [self.tx(t), ya - 0.08, 0], color=C_GREY, stroke_width=2))
                self.axis.add(Text(str(t), font=MONO, font_size=18, color=C_GREY).move_to([self.tx(t), ya - 0.25, 0]))
            self.add(self.axis)

    def tx(self, t):
        return self.x0 + t * self.u

    def ry(self, k):
        return self.y0 - k * self.dy

    def block(self, k, start):
        c, _ = self.tasks[k]
        r = Rectangle(width=c * self.u, height=self.h, stroke_color=col(c), stroke_width=2.5)
        r.set_fill(col(c), 0.4).move_to([self.tx(start + c / 2), self.ry(k), 0])
        lab = Text(str(c), font=MONO, font_size=20, color=WHITE).move_to(r)
        return VGroup(r, lab)


class Heap(VGroup):
    """大根堆的树形画法：节点按 heapq 数组下标摆位，节点用耗时作键（主例耗时互不相同）。"""

    def __init__(self, center=(4.3, 1.3, 0), dx=1.3, dy=1.1, r=0.34):
        super().__init__()
        self.c, self.dx, self.dy, self.r = np.array(center, dtype=float), dx, dy, r
        self.nodes, self.edges = {}, VGroup()
        self.add(self.edges)

    def pos(self, i):
        if i == 0:
            return self.c.copy()
        p = self.pos((i - 1) // 2)
        lvl = int(np.floor(np.log2(i + 1)))
        side = -1 if i % 2 == 1 else 1
        return p + np.array([side * self.dx / (2 ** (lvl - 1)), -self.dy, 0])

    def node(self, c):
        circ = Circle(self.r, stroke_color=col(c), stroke_width=4).set_fill(BG, 1)
        return VGroup(circ, Text(str(c), font=MONO, font_size=26, color=WHITE))

    def edge_group(self, n):
        g = VGroup()
        for i in range(1, n):
            a, b = self.pos((i - 1) // 2), self.pos(i)
            v = (b - a) / np.linalg.norm(b - a)
            g.add(Line(a + v * self.r, b - v * self.r, color=C_GREY, stroke_width=2.5))
        return g

    def arrange_to(self, arr):
        """把节点移到 heapq 数组 arr 的位置。返回动画列表。"""
        anims = [self.nodes[c].animate.move_to(self.pos(i)) for i, c in enumerate(arr)]
        old, new = self.edges, self.edge_group(len(arr))
        self.remove(old)
        self.submobjects.insert(0, new)            # 边在节点下面
        self.edges = new
        return anims + [FadeOut(old), FadeIn(new)]


class DeadlineLesson(Lesson):
    def construct(self):
        for b in ("title", "read", "sortkey", "walk", "why", "code", "trap", "check", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        """本 beat 里第一句包含 key、且还没开始太久的字幕的起点。"""
        return next((c["start"] for c in self.cue_times() if key in c["text"] and c["start"] >= self.now - 1.0),
                    default)

    def clear_all(self, rt=0.6):
        rest = [m for m in self.mobjects if m not in self.subs]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=rt)

    def step_tag(self, k, name, pos):
        return VGroup(T(f"第{'一二三四五'[k - 1]}步", 24, C_BLUE), T(name, 30)).arrange(RIGHT, buff=0.25).move_to(pos)

    # ---------------------------------------------------------------- 片头：题面
    def title_beat(self):
        self.beat("title")
        kick = T("例题精讲", 26, C_BLUE).move_to([0, 2.85, 0])
        title = T("最多能按时完成几个任务", 56).next_to(kick, DOWN, buff=0.25)
        sub = T("第 13 周 · 阶段综合练习 5.3", 24, C_GREY).next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(kick), Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.4)
        self.wait_until(self.cue_start("有一批任务", self.now))
        cards = VGroup()
        for c, d in D.TASKS:
            box = RoundedRectangle(corner_radius=0.12, width=1.75, height=1.25, stroke_color=col(c), stroke_width=3)
            txt = VGroup(T(f"耗时 {c}", 30, col(c)), T(f"截止 {d}", 26, C_GREY)).arrange(DOWN, buff=0.14)
            cards.add(VGroup(box, txt.move_to(box)))
        cards.arrange(RIGHT, buff=0.3).move_to([0, -0.35, 0])
        self.play(LaggedStart(*[FadeIn(cd, shift=UP * 0.2) for cd in cards], lag_ratio=0.15), run_time=1.5)
        self.cards = cards
        self.wait_until(self.cue_start("一次只能", self.now))
        rules = VGroup(T("一次做一个", 26), T("开始了不能中断", 26), T("最多按时完成几个？", 28, C_YELLOW))
        rules.arrange(RIGHT, buff=0.7).next_to(cards, DOWN, buff=0.8)
        for r in rules[:2]:
            self.play(FadeIn(r, shift=UP * 0.2), run_time=0.5)
        self.wait_until(self.cue_start("问最多", self.now))
        self.play(FadeIn(rules[2], shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 第一步看范围 + 第二步认题型
    def read_beat(self):
        self.beat("read")
        s1 = self.step_tag(1, "看数据范围", [-3.6, 2.4, 0])
        self.play(FadeIn(s1, shift=DOWN * 0.2), run_time=0.6)
        nmax = MathTex(r"n \le 10^{5}", color=WHITE).scale(1.1).next_to(s1, DOWN, buff=0.45)
        self.play(Write(nmax), run_time=0.6)
        self.wait_until(self.cue_start("平方级", self.now))
        assert D.N2 == 10 ** 10 and D.NLOGN < 2e6
        bad = VGroup(MathTex(r"n^2 = 10^{10}", color=C_RED).scale(0.95), T("一百亿次  超时", 26, C_RED))
        bad.arrange(RIGHT, buff=0.3).next_to(nmax, DOWN, buff=0.55)
        self.play(FadeIn(bad, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("只能是", self.now))
        good = VGroup(MathTex(r"n\log n \approx 1.7\times 10^{6}", color=C_GREEN).scale(0.95), T("可以", 26, C_GREEN))
        good.arrange(RIGHT, buff=0.3).next_to(bad, DOWN, buff=0.45)
        self.play(FadeIn(good, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("先排除", self.now))
        out = T("排除：暴力枚举、平方的 DP", 26, C_GREY).next_to(good, DOWN, buff=0.55)
        self.play(FadeIn(out), run_time=0.5)
        self.wait_until(self.cue_start("第二步", self.now))
        s2 = self.step_tag(2, "认题型", [3.4, 2.4, 0])
        rows = [("「有多少种方案」「最大价值」", "DP"), ("「最多能选几个」", "贪心（先想排序键）"),
                ("「最少几步」「最短路径」", "BFS"), ("「最小的最大值」", "二分答案"), ("「是否连通」", "并查集")]
        tab = VGroup()
        for q, a in rows:
            tab.add(VGroup(T(q, 23, C_GREY), T("→ " + a, 23)).arrange(RIGHT, buff=0.25))
        tab.arrange(DOWN, buff=0.36, aligned_edge=LEFT).next_to(s2, DOWN, buff=0.45)
        cap = T("5.1 题型识别速查表（节选）", 20, C_GREY).next_to(tab, DOWN, buff=0.3)
        self.play(FadeIn(s2, shift=DOWN * 0.2), FadeIn(tab, lag_ratio=0.1), FadeIn(cap), run_time=1.0)
        self.wait_until(self.cue_start("最多能选几个", self.now))
        hit = SurroundingRectangle(tab[1], color=C_YELLOW, buff=0.1, stroke_width=3)
        self.play(Create(hit), tab[1][0].animate.set_color(C_YELLOW), tab[1][1].animate.set_color(C_YELLOW),
                  *[r.animate.set_opacity(0.35) for i, r in enumerate(tab) if i != 1], run_time=0.8)
        self.wait_until(self.cue_start("按什么排序", self.now))
        ask = T("按什么排序？", 30, C_YELLOW).next_to(cap, DOWN, buff=0.35)
        self.play(FadeIn(ask, scale=1.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 第三步：排序键（最早截止优先）
    def sortkey_beat(self):
        self.beat("sortkey")
        s3 = self.step_tag(3, "定排序键", [0, 2.85, 0])
        self.play(FadeIn(s3, shift=DOWN * 0.2), run_time=0.6)
        chosen = [(c, d) for c, d in D.SORTED if c in D.TR[-1]["heap"]]           # 最终选中的四个
        bad_order = [chosen[2], chosen[0], chosen[3], chosen[1]]                  # 随便一个顺序
        q = T("选好的几个任务，能不能全部按时？", 28).next_to(s3, DOWN, buff=0.3)
        self.play(FadeIn(q), run_time=0.6)
        g = Gantt(bad_order, x0=-2.7, u=0.55, y0=1.0, dy=0.72, tmax=12)
        self.play(FadeIn(g), run_time=0.7)
        t, blocks = 0, VGroup()
        for k, (c, d) in enumerate(bad_order):
            b = g.block(k, t)
            t += c
            blocks.add(b)
        late = [k for k, (c, d) in enumerate(bad_order) if sum(x for x, _ in bad_order[:k + 1]) > d]
        self.play(LaggedStart(*[FadeIn(b, shift=RIGHT * 0.2) for b in blocks], lag_ratio=0.3), run_time=1.2)
        xs = VGroup(*[Cross(blocks[k], stroke_color=C_RED, stroke_width=4, scale_factor=0.6) for k in late])
        self.play(*[blocks[k][0].animate.set_stroke(C_RED, 4) for k in late], Create(xs), run_time=0.6)
        self.wait_until(self.cue_start("从早到晚", self.now))
        # 按截止重排：行与方块一起换到排序后的位置
        g2 = Gantt(chosen, x0=-2.7, u=0.55, y0=1.0, dy=0.72, tmax=12)
        t, nb = 0, VGroup()
        for k, (c, d) in enumerate(chosen):
            nb.add(g2.block(k, t))
            t += c
        perm = [chosen.index(x) for x in bad_order]
        self.play(FadeOut(xs), *[Transform(g.labels[k], g2.labels[perm[k]]) for k in range(4)],
                  *[Transform(g.marks[k], g2.marks[perm[k]]) for k in range(4)],
                  *[Transform(blocks[k], nb[perm[k]]) for k in range(4)], run_time=1.4)
        self.wait_until(self.cue_start("右端", self.now))
        assert D.edf_ok(chosen)
        oks = VGroup()
        for k, (c, d) in enumerate(chosen):
            end = sum(x for x, _ in chosen[:k + 1])
            assert end <= d
            oks.add(MathTex(r"\checkmark", color=C_GREEN).scale(0.7).move_to([g2.tx(d) + 0.3, g2.ry(k), 0]))
        self.play(LaggedStart(*[FadeIn(o, scale=1.4) for o in oks], lag_ratio=0.25),
                  *[Indicate(m, color=WHITE, scale_factor=1.2) for m in g.marks], run_time=1.4)
        tip = T("先做快到期的", 26, C_GREEN).move_to([0, -2.55, 0])
        self.play(FadeIn(tip, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("所以按截止", self.now))
        key = T("排序键：截止时间", 30, C_YELLOW).next_to(s3, DOWN, buff=0.3)
        self.play(FadeOut(q, shift=UP * 0.15), FadeIn(key, shift=UP * 0.15), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 第四步：按截止加入，超时扔堆顶
    def walk_beat(self):
        self.beat("walk")
        s4 = self.step_tag(4, "处理冲突", [-3.4, 2.85, 0])
        g = Gantt(D.SORTED, x0=-5.0, u=0.44, label_size=24)
        hp = Heap()
        htitle = T("大根堆：堆顶是最长的", 22, C_GREY).move_to(hp.pos(0) + UP * 0.75)
        bin_lab = T("扔掉：", 22, C_RED).move_to([2.6, -2.35, 0])
        self.play(FadeIn(s4, shift=DOWN * 0.2), FadeIn(g.labels), FadeIn(g.axis), run_time=0.8)
        self.wait_until(self.cue_start("大根堆", self.now))
        self.add(hp)
        self.play(FadeIn(htitle), run_time=0.5)
        readout = None
        self.binx = bin_lab.get_right()[0] + 0.45
        keys = ["耗时一", "耗时五", "耗时二", "耗时六", "耗时四", "最后耗时三"]
        drop_keys = {2: "扔掉堆顶", 4: "再扔"}
        start = {}                                   # 已选任务所在行 → 开始时刻
        placed = {}
        prev_arr = []
        for k, st in enumerate(D.TR):
            c, d = st["cost"], st["deadline"]
            self.wait_until(self.cue_start(keys[k], self.now))
            t0 = sum(D.SORTED[j][0] for j in start)
            blk = g.block(k, t0)
            start[k] = t0
            placed[k] = blk
            nd = hp.node(c).move_to(hp.pos(len(prev_arr)))
            hp.nodes[c] = nd
            hp.add(nd)
            over = st["total_in"] > d
            rd = T(f"总时长 {st['total_in']} {'>' if over else '≤'} 截止 {d}", 28,
                   C_RED if over else C_GREEN).move_to([-3.0, 2.25, 0])
            self.play(FadeIn(g.marks[k]), FadeIn(blk, shift=RIGHT * 0.2), FadeIn(nd, scale=0.6),
                      Transform(readout, rd) if readout else FadeIn(rd), run_time=0.6)
            readout = readout or rd
            self.play(*hp.arrange_to(st["pushed"]), run_time=0.5)
            if over:
                self.play(blk[0].animate.set_stroke(C_RED, 4), Indicate(g.marks[k], color=C_RED, scale_factor=1.3),
                          run_time=0.6)
                self.wait_until(self.cue_start(drop_keys[k], self.now))
                x = st["dropped"]
                j = next(j for j in start if D.SORTED[j][0] == x)
                top = hp.nodes.pop(x)
                ring = Circle(hp.r + 0.08, color=C_RED, stroke_width=5).move_to(top)
                self.play(Create(ring), Indicate(placed[j], color=C_RED), run_time=0.6)
                # 被扔的方块变灰，后面的方块左移补上；堆顶飞进「扔掉」区
                del start[j]
                shift = []
                for jj in sorted(start):
                    if jj > j:
                        start[jj] -= x
                        shift.append(placed[jj].animate.shift(LEFT * x * g.u))
                if not hasattr(self, "binned"):
                    self.binned = VGroup()
                    self.play(FadeIn(bin_lab), run_time=0.3)
                tgt = [self.binx + 0.75 * len(self.binned), bin_lab.get_y(), 0]
                strike = Line(g.labels[j].get_left(), g.labels[j].get_right(), color=C_RED, stroke_width=3)
                self.play(FadeOut(ring), top.animate.scale(0.75).move_to(tgt),
                          placed[j].animate.set_opacity(0.12), Create(strike),
                          g.marks[j].animate.set_opacity(0.25), *shift, run_time=0.9)
                self.binned.add(top)
                rd = T(f"总时长降到 {st['total']}", 28, C_YELLOW).move_to([-3.0, 2.25, 0])
                self.play(*hp.arrange_to(st["heap"]), Transform(readout, rd), blk[0].animate.set_stroke(col(c), 2.5),
                          run_time=0.6)
            prev_arr = st["heap"]
        self.wait_until(self.cue_start("堆里剩四个", self.now))
        assert D.ANSWER == len(D.TR[-1]["heap"]) == 4
        ans = T(f"堆里 {D.ANSWER} 个 → 答案 {D.ANSWER}", 30, C_GREEN).move_to([hp.pos(0)[0], -1.45, 0])
        self.play(FadeIn(ans, scale=1.2), *[Indicate(hp.nodes[c], color=C_GREEN) for c in D.TR[-1]["heap"]],
                  run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 为什么扔最长的不会更差
    def why_beat(self):
        self.beat("why")
        k0 = D.DROPS[0][0]
        first = D.SORTED[:k0 + 1]
        d = first[-1][1]
        st = D.TR[k0]
        head = T("为什么扔最长的不会更差？", 30, C_YELLOW).move_to([0, 2.85, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.6)
        g = Gantt(first, x0=-5.2, u=0.55, y0=1.75, dy=0.62, tmax=9, label_size=20)
        t, blocks = 0, VGroup()
        for k, (c, _) in enumerate(first):
            blocks.add(g.block(k, t))
            t += c
        wall = DashedLine([g.tx(d), g.ry(0) + 0.45, 0], [g.tx(d), g.ry(len(first) - 1) - 0.45, 0],
                          color=C_RED, stroke_width=4)
        wl = T(f"截止都不晚于 {d}", 22, C_RED).next_to(wall.get_top(), RIGHT, buff=0.15).shift(DOWN * 0.1)
        self.play(FadeIn(g), FadeIn(blocks), run_time=0.8)
        self.wait_until(self.cue_start("截止都不晚于", self.now))
        assert all(x <= d for _, x in first) and st["total_in"] > d
        tot = T(f"总时长 {st['total_in']} > {d}", 26, C_RED).move_to([2.9, 1.15, 0])
        self.play(Create(wall), FadeIn(wl), FadeIn(tot), run_time=0.8)
        self.wait_until(self.cue_start("至少要扔一个", self.now))
        must = T("至少扔一个；扔一个就够", 26).next_to(tot, DOWN, buff=0.35)
        self.play(FadeIn(must, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("扔谁", self.now))
        opts = D.drop_options(k0)                      # [(扔掉的耗时, 剩余总时长)]
        u2, x0, y0 = 0.5, -3.6, -1.25
        rows = VGroup()
        for i, (x, rest) in enumerate(opts):
            y = y0 - i * 0.62
            lab = T(f"扔 {x}", 24, col(x)).move_to([x0 - 0.9, y, 0])
            bar = Rectangle(width=rest * u2, height=0.36, stroke_width=0).set_fill(C_GREY, 0.55)
            bar.move_to([x0 + rest * u2 / 2, y, 0])
            num = T(f"剩 {rest}", 24).next_to(bar, RIGHT, buff=0.2)
            rows.add(VGroup(lab, bar, num))
        cap = T("扔掉以后剩下的总时长（都是两个任务）", 20, C_GREY).next_to(rows, UP, buff=0.2).align_to(rows, LEFT)
        self.play(FadeIn(cap), run_time=0.4)
        for r in rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.45)
        best = min(range(len(opts)), key=lambda i: opts[i][1])
        assert opts[best][0] == max(c for c, _ in first) == D.DROPS[0][1]
        self.wait_until(self.cue_start("扔五只剩三", self.now))
        self.play(rows[best][1].animate.set_fill(C_GREEN, 0.8), rows[best][2].animate.set_color(C_GREEN),
                  Create(SurroundingRectangle(rows[best], color=C_GREEN, buff=0.1)), run_time=0.7)
        self.wait_until(self.cue_start("数量一样", self.now))
        moral = VGroup(T("数量一样", 26), T("占的时间最少", 26, C_GREEN), T("后面空间最多", 26, C_GREEN))
        moral.arrange(DOWN, buff=0.25, aligned_edge=LEFT).move_to([3.6, -1.15, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=LEFT * 0.2) for m in moral], lag_ratio=0.4), run_time=1.4)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 代码
    def code_beat(self):
        self.beat("code")
        src = ("def max_tasks(tasks):\n"
               "    tasks = sorted(tasks, key=lambda t: t[1])\n"
               "    heap, total = [], 0          # 存 -耗时\n"
               "    for cost, deadline in tasks:\n"
               "        heapq.heappush(heap, -cost)\n"
               "        total += cost\n"
               "        if total > deadline:\n"
               "            total += heapq.heappop(heap)\n"
               "    return len(heap)\n")
        code = Code(code_string=src, language="python", formatter_style="monokai", background="window",
                    add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 26})
        if code.width > 8.6:
            code.scale_to_fit_width(8.6)
        code.move_to([0, 1.05, 0]).to_edge(LEFT, buff=0.4)
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.9)
        ln = code.code_lines
        tags = VGroup()

        def mark(lines, key, txt, color):
            self.wait_until(self.cue_start(key, self.now))
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=color, buff=0.04, stroke_width=2)
            tag = T(txt, 24, color).next_to(code, RIGHT, buff=0.3).match_y(hl)
            self.play(Create(hl), FadeIn(tag, shift=LEFT * 0.2), run_time=0.6)
            tags.add(hl, tag)
        mark([1], "按截止时间", "按截止排序", C_YELLOW)
        mark([4, 5], "压进堆", "进堆，总时长累加", C_BLUE)
        mark([6, 7], "弹出堆顶", "超时：扔掉堆顶", C_RED)
        mark([8], "答案就是几", "堆里几个，答案几个", C_GREEN)
        self.wait_until(self.cue_start("if", self.now))
        why = VGroup(T("为什么一个 if 就够？", 26, C_YELLOW),
                     T("扔掉的 ≥ 新来的", 24), T("⟹ 总时长 ≤ 上一步 ≤ 上一个截止 ≤ 这次的截止", 24))
        why.arrange(DOWN, buff=0.18, aligned_edge=LEFT).next_to(code, DOWN, buff=0.3).align_to(code, LEFT)
        self.play(FadeIn(why[0]), run_time=0.5)
        self.wait_until(self.cue_start("扔掉的堆顶", self.now))
        self.play(FadeIn(why[1], shift=UP * 0.15), run_time=0.5)
        self.wait_until(self.cue_start("上一步是", self.now))
        self.play(FadeIn(why[2], shift=UP * 0.15), run_time=0.5)
        self.wait_until(self.cue_start("总复杂度", self.now))
        cx = MathTex(r"O(n\log n)", color=C_YELLOW).scale(1.0).next_to(why, RIGHT, buff=0.6).align_to(why, DOWN)
        self.play(FadeIn(cx, scale=1.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 易错点
    def trap_beat(self):
        self.beat("trap")
        head = T("易错点", 32, C_RED).move_to([-3.6, 2.85, 0])
        self.play(FadeIn(head, shift=DOWN * 0.2), run_time=0.5)

        def line(s, color):
            return Text(s, font=MONO, font_size=24, color=color)
        n1 = T("① heapq 是小根堆，存相反数", 27)
        n1.move_to([-6.6 + n1.width / 2, 2.0, 0])
        ok = VGroup(line("total += heapq.heappop(heap)", C_GREEN), MathTex(r"\checkmark", color=C_GREEN).scale(0.7))
        ok.arrange(RIGHT, buff=0.2)
        no = VGroup(line("total -= heapq.heappop(heap)", C_RED), MathTex(r"\times", color=C_RED).scale(0.8),
                    T(f"答案 {D.wrong_sign()}", 22, C_RED)).arrange(RIGHT, buff=0.2)
        VGroup(ok, no).arrange(DOWN, buff=0.22, aligned_edge=LEFT).next_to(n1, DOWN, buff=0.3).align_to(n1, LEFT)
        self.play(FadeIn(n1), run_time=0.5)
        self.wait_until(self.cue_start("加上它", self.now))
        self.play(FadeIn(ok, shift=UP * 0.15), run_time=0.5)
        self.wait_until(self.cue_start("写成减号", self.now))
        self.play(FadeIn(no, shift=UP * 0.15), run_time=0.5)
        self.wait_until(self.cue_start("第二", self.now))
        n2 = T("② 用 >：正好在截止时刻完成也算按时", 27).next_to(no, DOWN, buff=0.45).align_to(n1, LEFT)
        ex = VGroup(T("如", 24, C_GREY), tup(5, 6, 24, col(5)), T(f"：总时长 {D.TR[1]['total_in']}，按时", 24, C_GREY))
        ex.arrange(RIGHT, buff=0.12).next_to(n2, DOWN, buff=0.2).align_to(n1, LEFT)
        assert D.TR[1]["total_in"] == D.TR[1]["deadline"]
        self.play(FadeIn(n2), FadeIn(ex), run_time=0.6)
        self.wait_until(self.cue_start("第三", self.now))
        n3 = T("③ 超时就跳过新任务、不反悔：错", 27).move_to([3.3, 2.0, 0])
        self.play(FadeIn(n3), run_time=0.5)
        took = D.skip_greedy()[1]
        g = Gantt(D.SORTED, x0=2.0, u=0.36, y0=1.2, dy=0.56, tmax=13, h=0.36, label_size=21)
        self.play(FadeIn(g), run_time=0.6)
        t, crosses = 0, VGroup()
        for k, ((c, d), yes) in enumerate(zip(D.SORTED, took)):
            if yes:
                b = g.block(k, t)
                b[1].scale(0.8)
                t += c
                self.play(FadeIn(b, shift=RIGHT * 0.15), run_time=0.3)
            else:
                x = T("跳过", 18, C_RED).move_to([g.tx(t) - 0.45, g.ry(k), 0])
                self.play(FadeIn(x), g.labels[k].animate.set_opacity(0.35), g.marks[k].animate.set_opacity(0.3),
                          run_time=0.3)
                crosses.add(x)
        self.wait_until(self.cue_start("只完成三个", self.now))
        assert D.SKIP_ANSWER == 3 and D.ANSWER == 4
        res = T(f"只完成 {D.SKIP_ANSWER} 个，正确答案 {D.ANSWER} 个", 26, C_RED).next_to(g, DOWN, buff=0.25)
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 第五步：对拍
    def check_beat(self):
        self.beat("check")
        s5 = self.step_tag(5, "对拍", [0, 2.85, 0])
        self.play(FadeIn(s5, shift=DOWN * 0.2), run_time=0.6)
        brute = VGroup(T("暴力", 28, C_BLUE), T("每个子集 × 每种顺序", 26))
        brute_note = T("一定对，只能跑小数据", 24, C_GREY)
        brute.add(brute_note).arrange(RIGHT, buff=0.3).move_to([0, 2.15, 0])
        self.play(FadeIn(brute), run_time=0.6)
        cases = D.lecture_check()
        n, nmax, nbad = D.CHECK
        assert (n, nmax) == (200, 6)
        sz, cell = 0.24, "#262b38"

        def grid(x):
            gr = VGroup(*[Square(sz, stroke_color=cell, stroke_width=1).set_fill(cell, 1) for _ in range(n)])
            return gr.arrange_in_grid(10, 20, buff=0.05).move_to([x, -0.95, 0])
        self.wait_until(self.cue_start("两百组", self.now))
        g1 = grid(-3.4)
        l1 = T("讲义的贪心  vs  暴力", 24, C_GREEN).next_to(g1, UP, buff=0.2)
        info = T(f"随机 {n} 组，每组 1～{nmax} 个任务", 24, C_GREY).move_to([0, 1.5, 0])
        self.play(FadeIn(g1), FadeIn(l1), FadeIn(info), run_time=0.6)
        same = [D.max_tasks(ts) == D.max_tasks_brute(ts) for ts in cases]
        assert all(same)
        self.play(LaggedStart(*[g1[i].animate.set_fill(C_GREEN, 1) for i in range(n)], lag_ratio=0.01),
                  run_time=2.0)
        self.wait_until(self.cue_start("全部一致", self.now))
        ok = T(f"{n} / {n} 一致", 26, C_GREEN).next_to(g1, DOWN, buff=0.2)
        self.play(FadeIn(ok, scale=1.2), run_time=0.5)
        self.wait_until(self.cue_start("换成", self.now))
        g2 = grid(3.4)
        l2 = T("不反悔的贪心  vs  暴力", 24, C_RED).next_to(g2, UP, buff=0.2)
        bad = [D.skip_greedy(ts)[0] != D.max_tasks_brute(ts) for ts in cases]
        assert sum(bad) == nbad == 1
        self.play(FadeIn(g2), FadeIn(l2), run_time=0.5)
        self.play(LaggedStart(*[g2[i].animate.set_fill(C_RED if bad[i] else C_GREEN, 1) for i in range(n)],
                              lag_ratio=0.01), run_time=2.0)
        i_bad = bad.index(True)
        ring = Circle(0.3, color=C_RED, stroke_width=5).move_to(g2[i_bad])
        tb = T(f"只有 {nbad} 组报错", 26, C_RED).next_to(g2, DOWN, buff=0.2)
        self.play(Create(ring), FadeIn(tb), run_time=0.6)
        self.wait_until(self.cue_start("跑够组数", self.now))
        self.play(Indicate(tb, color=C_YELLOW), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.6))
        self.clear_all()

    # ---------------------------------------------------------------- 回顾：考场流程
    def recap_beat(self):
        self.beat("recap")
        steps = [("看范围", r"n \le 10^5 \Rightarrow O(n\log n)", None, "看范围"),
                 ("认题型", None, "最多选几个 → 贪心", "认题型"),
                 ("定排序键", None, "按截止时间", "定排序键"),
                 ("处理冲突", None, "超时扔最长的（大根堆）", "处理冲突"),
                 ("对拍验证", None, "暴力 vs 贪心，随机两百组", "对拍")]
        rows = VGroup()
        colors = [C_BLUE, C_TEAL, C_YELLOW, C_RED, C_GREEN]
        for (name, tex, txt, _k), c in zip(steps, colors):
            rhs = MathTex(tex, color=WHITE).scale(0.8) if tex else T(txt, 26)
            rows.add(VGroup(T(name, 28, c), rhs).arrange(RIGHT, buff=0.45))
        rows.arrange(DOWN, buff=0.38, aligned_edge=LEFT).move_to([0, 0.75, 0])
        for row, (_n, _t, _x, key) in zip(rows, steps):
            self.wait_until(self.cue_start(key, self.now))
            self.play(FadeIn(row, shift=UP * 0.2), run_time=0.6)
        self.wait_until(self.cue_start("每一道题", self.now))
        frame = SurroundingRectangle(rows, color=C_GREY, buff=0.25, stroke_width=2)
        tag = T("考场上每一道题的流程", 24, C_YELLOW).next_to(frame, DOWN, buff=0.2)
        self.play(Create(frame), FadeIn(tag), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("计算概论（B）2026fall · 第 13 周 阶段综合练习 5.3 一道综合例题的完整拆解", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
