"""拓扑排序：先修课怎么排（3B1B 风格）。

由 cs201/cinematic/make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。出队 / 入度减一 / 入队、DFS 进入与结束
事件都来自 topodata（讲义 topological_sort、dfs_topo_sort 原样插桩；test_topo.py 对撞讲义手算表、穷举、随机 DAG）。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import topodata as D  # noqa: E402
from cine import *  # noqa: E402,F403

# 按最长路分层排版（D.layers()：c0 c1 | c2 c4 c7 | c3 c8 | c5 c6）
POS = {0: (-6.0, 1.9), 1: (-6.0, -0.3), 7: (-3.2, 2.8), 2: (-3.2, 0.8), 4: (-3.2, -1.2),
       8: (-0.4, 2.8), 3: (-0.4, 0.1), 6: (2.4, 1.9), 5: (2.4, -0.7)}
NODE_H = 0.62
QX = 5.35                                   # 队列面板
OUT_Y, OUT_X0, OUT_DX = -2.45, -5.4, 1.42   # 输出行
C_DONE, C_STUCK = C_GREEN, C_RED
C_GRAYST, C_BLACKST = "#6B7180", "#252932"  # DFS 三色：灰（访问中）、黑（已结束）


def box_point(node, toward):
    """从结点框中心朝 toward 方向射出，与框边界的交点。"""
    c = node.get_center()
    d = np.array(toward) - c
    w, h = node[0].width / 2, node[0].height / 2
    tx = w / abs(d[0]) if abs(d[0]) > 1e-6 else np.inf
    ty = h / abs(d[1]) if abs(d[1]) > 1e-6 else np.inf
    return c + d * min(tx, ty)


def make_node(i):
    t = T(D.NAMES[i], 22)
    box = RoundedRectangle(corner_radius=0.14, width=max(1.45, t.width + 0.34), height=NODE_H,
                           stroke_color=WHITE, stroke_width=2.5).set_fill(BG, 0)
    return VGroup(box, t).move_to([*POS[i], 0])


def make_arrow(nodes, u, v, color=C_GREY):
    a, b = nodes[u], nodes[v]
    s, e = box_point(a, b.get_center()), box_point(b, a.get_center())
    return Arrow(s, e, buff=0.05, stroke_width=3, color=color, tip_length=0.18,
                 max_tip_length_to_length_ratio=0.3, max_stroke_width_to_length_ratio=12)


def badge(node, n, col=WHITE):
    c = Circle(0.2, stroke_color=col, stroke_width=2).set_fill(BG, 1)
    return VGroup(c, MathTex(str(n), color=col).scale(0.5)).move_to(node[0].get_corner(UR) + np.array([0.06, 0.08, 0]))


def chip(i, w=1.32, size=18, col=WHITE):
    t = T(D.NAMES[i], size)
    if t.width > w - 0.14:
        t.scale_to_fit_width(w - 0.14)
    box = RoundedRectangle(corner_radius=0.1, width=w, height=0.5, stroke_color=col, stroke_width=2).set_fill(BG, 0)
    return VGroup(box, t.move_to(box))


def out_slot(k):
    return np.array([OUT_X0 + OUT_DX * k, OUT_Y, 0])


def q_slot(k):
    return np.array([QX, 2.2 - 0.68 * k, 0])


class TopoLesson(Lesson):
    def construct(self):
        for b in ("title", "dag", "indeg", "code", "run", "line", "cycle", "dfs", "why", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def at(self, key, default=None):
        """旁白里 key 这几个字大约在什么时刻念到（句级时间戳内按字数插值）。"""
        for c in self.cue_times():
            if key in c["text"]:
                k = c["text"].index(key)
                return c["start"] + (c["end"] - c["start"]) * k / max(1, len(c["text"]))
        return self.now if default is None else default

    def wait_key(self, key):
        self.wait_until(self.at(key))

    # ---------------------------------------------------------------- 图
    def build_graph(self, edges=D.EDGES):
        nodes = {i: make_node(i) for i in range(D.N)}
        arrows = {(u, v): make_arrow(nodes, u, v) for u, v in edges}
        return nodes, arrows

    # ---------------------------------------------------------------- 片头：一团乱麻拉成一行
    def title_beat(self):
        self.beat("title")
        rng = random.Random(7)
        n = 12
        pts = [np.array([rng.uniform(-6.0, 6.0), rng.uniform(-2.2, 2.6), 0]) for _ in range(n)]
        perm = list(range(n))
        rng.shuffle(perm)                       # perm[k] = 第 k 个点的拓扑位次
        edges = [(a, b) for a in range(n) for b in range(n)
                 if perm[a] < perm[b] and perm[b] - perm[a] <= 4 and rng.random() < 0.45]
        dots = [Dot(p, radius=0.12, color=C_BLUE) for p in pts]

        def arc(a, b):
            def f():
                p, q = dots[a].get_center(), dots[b].get_center()
                d = q - p
                L = np.linalg.norm(d)
                if L < 1e-3:
                    return VMobject()
                u = d / L
                return ArcBetweenPoints(p + u * 0.17, q - u * 0.17, angle=-PI / 4, stroke_width=2.5,
                                        color=C_GREY).add_tip(tip_length=0.14, tip_width=0.12)
            return always_redraw(f)
        arcs = [arc(a, b) for a, b in edges]
        self.play(*[FadeIn(a) for a in arcs], *[FadeIn(d, scale=0.5) for d in dots], run_time=1.0)
        line = [np.array([-5.5 + 11.0 * perm[k] / (n - 1), -1.3, 0]) for k in range(n)]
        self.wait_until(self.at("一大堆课") + 0.6)
        self.play(*[d.animate.move_to(line[k]) for k, d in enumerate(dots)], run_time=2.6,
                  rate_func=smooth)
        self.play(*[a.animate.set_color(C_GREEN) for a in arcs], run_time=0.6)
        title = T("拓扑排序", 72).move_to([0, 2.0, 0])
        sub = T("先修课怎么排", 34, C_YELLOW).next_to(title, DOWN, buff=0.25)
        self.wait_key("这一集")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.6))
        for a in arcs:
            a.clear_updaters()
        self.play(FadeOut(VGroup(*arcs, *dots, title, sub)), run_time=0.6)

    # ---------------------------------------------------------------- 课程图
    def dag_beat(self):
        self.beat("dag")
        nodes, arrows = self.build_graph()
        self.nodes, self.arrows = nodes, arrows
        self.play(LaggedStart(*[FadeIn(nodes[i], shift=UP * 0.15) for i in sorted(nodes, key=lambda i: POS[i][0])],
                              lag_ratio=0.12), run_time=1.6)
        self.play(*[GrowArrow(a) for a in arrows.values()], run_time=1.2)
        self.wait_key("高等数学指向")
        self.play(arrows[(0, 2)].animate.set_color(C_YELLOW).set_stroke(width=5),
                  Indicate(nodes[0], color=C_YELLOW), Indicate(nodes[2], color=C_YELLOW), run_time=1.0)
        tip = T("先学 → 后学", 24, C_YELLOW).move_to([QX, 2.6, 0])
        self.play(FadeIn(tip, shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("这里有九门课")
        cnt = VGroup(T("9 门课", 26), T(f"{len(D.EDGES)} 条边", 26)).arrange(DOWN, buff=0.2).move_to([QX, 1.3, 0])
        self.play(FadeIn(cnt), arrows[(0, 2)].animate.set_color(C_GREY).set_stroke(width=3), run_time=0.8)
        self.wait_key("排成一行")
        topo = VGroup(T("拓扑序", 28, C_GREEN), T("每条边都从左指向右", 20)).arrange(DOWN, buff=0.15)
        topo.move_to([QX, -0.1, 0])
        self.play(FadeIn(topo, shift=UP * 0.2), *[a.animate.set_color(C_GREEN) for a in arrows.values()], run_time=1.0)
        self.wait_key("能排出来")
        dag = VGroup(T("有向无环图", 26, C_BLUE), Text("DAG", font=MONO, font_size=24, color=C_BLUE)).arrange(DOWN, buff=0.12)
        dag.move_to([QX, -1.5, 0])
        self.play(FadeIn(dag, shift=UP * 0.2), *[a.animate.set_color(C_GREY) for a in arrows.values()], run_time=0.9)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(tip, cnt, topo, dag)), run_time=0.6)

    # ---------------------------------------------------------------- 入度
    def indeg_beat(self):
        self.beat("indeg")
        deg = D.indegrees()
        self.badges = {i: badge(self.nodes[i], deg[i], C_GREEN if deg[i] == 0 else WHITE) for i in range(D.N)}
        self.wait_key("看入度")
        lab = VGroup(T("入度", 28, C_YELLOW), T("指向它的边数", 20)).arrange(DOWN, buff=0.15).move_to([QX, 2.4, 0])
        self.play(FadeIn(lab), LaggedStart(*[FadeIn(self.badges[i], scale=1.5) for i in range(D.N)], lag_ratio=0.08),
                  run_time=1.6)
        self.wait_key("高等数学和程序设计")
        zero = [i for i in range(D.N) if deg[i] == 0]
        self.play(*[self.nodes[i][0].animate.set_stroke(C_GREEN, 4) for i in zero],
                  *[Indicate(self.badges[i][1], color=C_GREEN, scale_factor=1.4) for i in zero], run_time=1.0)
        free = T("无先修课：直接学", 20, C_GREEN).move_to([QX, 1.2, 0])
        self.play(FadeIn(free), run_time=0.5)
        self.wait_key("离散数学入度是二")
        ins = [self.arrows[e] for e in D.EDGES if e[1] == 2]
        self.play(*[a.animate.set_color(C_YELLOW).set_stroke(width=5) for a in ins],
                  Indicate(self.badges[2][1], color=C_YELLOW, scale_factor=1.4), run_time=1.0)
        wait2 = T("要等两门先修课", 20, C_YELLOW).move_to([QX, 0.3, 0])
        self.play(FadeIn(wait2), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(lab, free, wait2)), *[a.animate.set_color(C_GREY).set_stroke(width=3) for a in ins],
                  *[self.nodes[i][0].animate.set_stroke(WHITE, 2.5) for i in zero], run_time=0.6)

    # ---------------------------------------------------------------- 讲义代码
    def code_beat(self):
        self.beat("code")
        graph = VGroup(*self.arrows.values(), *self.nodes.values(), *self.badges.values())
        graph.save_state()
        code = Code(code_string=D.KAHN_CODE.rstrip("\n"), language="python", formatter_style="monokai",
                    background="window", add_line_numbers=False, paragraph_config={"font": MONO, "font_size": 18})
        code.scale_to_fit_height(min(code.height, 6.5)).move_to([2.6, 0.45, 0])
        self.play(graph.animate.scale(0.42).move_to([-4.7, 2.3, 0]), run_time=1.0)
        self.play(FadeIn(code, shift=LEFT * 0.3), run_time=0.8)
        ln = code.code_lines
        hls = VGroup()

        def mark(lines, key, col):
            self.wait_key(key)
            hl = SurroundingRectangle(VGroup(*[ln[i] for i in lines]), color=col, buff=0.04, stroke_width=2)
            self.play(Create(hl), run_time=0.6)
            hls.add(hl)
        mark([2, 3, 4, 5], "先数出", C_BLUE)
        mark([6], "放进队列", C_GREEN)
        mark([9, 10], "反复出队", C_YELLOW)
        mark([11, 12], "入度减一", C_RED)
        mark([13, 14], "减到零", C_GREEN)
        mark([15], "输出不足", C_PURPLE)
        self.wait(max(0.1, self.left() - 1.6))
        self.play(FadeOut(VGroup(code, hls)), run_time=0.6)
        self.play(Restore(graph), run_time=1.0)

    # ---------------------------------------------------------------- 跟着跑一遍
    def setup_queue(self):
        head = T("队列", 26, C_YELLOW).move_to([QX, 3.0, 0])
        hint = T("队头", 18, C_GREY).next_to(q_slot(0), LEFT, buff=0.85)
        out_lab = T("输出", 22, C_GREY).move_to([-6.55, OUT_Y, 0])
        self.queue: list[VGroup] = []
        self.output: list[VGroup] = []
        return VGroup(head, hint), out_lab

    def push_chip(self, v, rt=0.5):
        c = chip(v).move_to(q_slot(len(self.queue)))
        self.queue.append(c)
        self.play(FadeIn(c, target_position=self.nodes[v].get_center()), run_time=rt + 0.1)

    def pop_chip(self, u, arrows, rt=0.6):
        c = self.queue.pop(0)
        self.output.append(c)
        outs = [a for (x, _), a in arrows.items() if x == u]
        self.play(c.animate.move_to(out_slot(len(self.output) - 1)),
                  *[q.animate.move_to(q_slot(k)) for k, q in enumerate(self.queue)],
                  self.nodes[u][0].animate.set_stroke(C_DONE, 3).set_fill(C_DONE, 0.22),
                  *[a.animate.set_opacity(0.15) for a in outs], run_time=rt)

    def dec_badge(self, v, new, rt=0.4):
        col = C_GREEN if new == 0 else WHITE
        nb = badge(self.nodes[v], new, col)
        self.play(Transform(self.badges[v], nb), Flash(self.badges[v], color=col, flash_radius=0.35, line_length=0.12),
                  run_time=rt)

    def run_kahn(self, steps, keys, arrows):
        for (u, decs, pushes, _), key in zip(steps, keys):
            if key:
                self.wait_key(key)
            self.pop_chip(u, arrows)
            for v, _, new in decs:
                self.dec_badge(v, new)
                if v in pushes:
                    self.push_chip(v, rt=0.4)

    def run_beat(self):
        self.beat("run")
        self.qhead, self.out_lab = self.setup_queue()
        self.play(FadeIn(self.qhead), FadeIn(self.out_lab), run_time=0.6)
        _, ev, _ = D.kahn_trace()
        for v in ev[0][2]:
            self.push_chip(v, rt=0.4)
        keys = ["高数出队", "程序设计出队", "物理出队", "离散出队", "算法语言出队", "计算机原理出队", "数据结构出队",
                "编译、", "操作系统依次"]
        steps = D.kahn_steps()
        assert len(steps) == len(keys)
        self.run_kahn(steps, keys, self.arrows)
        done = T("9 门全部输出", 24, C_GREEN).move_to([QX, 0.4, 0])
        self.play(FadeIn(done, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.4))
        self.done_lab = done

    # ---------------------------------------------------------------- 摆成一行
    def line_beat(self):
        self.beat("line")
        order = [c for c in self.output]
        self.play(FadeOut(VGroup(*self.arrows.values(), *self.nodes.values(), *self.badges.values(), self.qhead,
                                 self.done_lab, self.out_lab)), run_time=0.8)
        res, _, _ = D.kahn_trace()
        pos = {v: k for k, v in enumerate(res)}
        y = 0.55
        self.play(*[c.animate.move_to([OUT_X0 + OUT_DX * k - 0.28, y, 0]) for k, c in enumerate(order)], run_time=1.0)
        arcs = VGroup()
        for u, v in D.EDGES:
            a, b = order[pos[u]], order[pos[v]]
            s = a.get_top() + np.array([0.14, 0.02, 0])
            e = b.get_top() + np.array([-0.14, 0.02, 0])
            dist = pos[v] - pos[u]
            arcs.add(CurvedArrow(s, e, angle=-min(2.0, 0.45 + 0.28 * dist), color=C_GREEN, stroke_width=2.5,
                                 tip_length=0.16))
        self.wait_key("十一条边")
        self.play(LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.12), run_time=2.4)
        ok = T("11 条边全部朝右", 24, C_GREEN).move_to([0, 3.3, 0])
        self.play(FadeIn(ok), run_time=0.5)
        self.wait_key("讲义图注")
        rows = VGroup()
        for seq in ([0, 1, 2, 3, 4, 5, 7, 8, 6], [0, 7, 8, 1, 4, 2, 3, 6, 5]):
            r = VGroup(*[chip(v, w=1.05, size=15, col=C_GREY) for v in seq]).arrange(RIGHT, buff=0.08)
            rows.add(r)
        rows.arrange(DOWN, buff=0.22).move_to([0.6, -1.45, 0])
        tag = T("讲义图注", 20, C_GREY).next_to(rows, LEFT, buff=0.3)
        self.play(FadeIn(rows, shift=UP * 0.2), FadeIn(tag), run_time=0.9)
        self.wait_key("拓扑序并不唯一")
        uniq = T("拓扑序不唯一", 30, C_YELLOW).move_to([0, 3.3, 0])
        self.play(ReplacementTransform(ok, uniq), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(arcs, rows, tag, uniq, *order)), run_time=0.6)

    # ---------------------------------------------------------------- 加一条反向边：有环
    def cycle_beat(self):
        self.beat("cycle")
        nodes, arrows = self.build_graph()
        self.nodes, self.arrows = nodes, arrows
        self.play(FadeIn(VGroup(*arrows.values(), *nodes.values())), run_time=0.8)
        u, v = D.CYCLE_EDGE
        s, e = nodes[u][0].get_top(), nodes[v][0].get_top()
        top = 3.62                                  # 从所有结点和入度圈上方绕过去
        rail = VMobject(stroke_color=C_RED, stroke_width=3.5).set_points_as_corners(
            [s, [s[0], top, 0], [e[0], top, 0], [e[0], e[1] + 0.55, 0]])
        back = VGroup(rail, Arrow([e[0], e[1] + 0.6, 0], e, buff=0.02, color=C_RED, stroke_width=3.5,
                                  tip_length=0.2, max_tip_length_to_length_ratio=0.5))
        self.wait_key("比如让操作系统")
        self.play(Create(back), Indicate(nodes[u], color=C_RED), run_time=1.2)
        arrows[D.CYCLE_EDGE] = back
        edges = D.EDGES + [D.CYCLE_EDGE]
        deg = D.indegrees(edges)
        self.badges = {i: badge(nodes[i], deg[i], C_GREEN if deg[i] == 0 else WHITE) for i in range(D.N)}
        self.wait_key("高数的入度变成一")
        self.play(LaggedStart(*[FadeIn(self.badges[i], scale=1.5) for i in range(D.N)], lag_ratio=0.06), run_time=1.0)
        self.play(Indicate(self.badges[0][1], color=C_RED, scale_factor=1.5), run_time=0.6)
        self.qhead, self.out_lab = self.setup_queue()
        self.play(FadeIn(self.qhead), FadeIn(self.out_lab), run_time=0.4)
        _, ev, _ = D.kahn_trace(edges)
        for x in ev[0][2]:
            self.push_chip(x, rt=0.4)
        steps = D.kahn_steps(edges)
        self.run_kahn(steps, ["开局只有", "接着是算法语言"], arrows)
        self.wait_key("然后队列就空了")
        empty = T("队列空了", 24, C_RED).move_to(q_slot(0))
        self.play(FadeIn(empty, scale=1.2), run_time=0.6)
        _, out, stuck = D.stuck_after_cycle()
        self.wait_key("剩下七门课")
        self.play(*[nodes[i][0].animate.set_stroke(C_STUCK, 3.5) for i in stuck],
                  *[Indicate(self.badges[i][1], color=C_STUCK, scale_factor=1.3) for i in stuck], run_time=1.0)
        self.wait_key("它们要么在环上")
        cyc = D.cycle_edges()
        self.play(*[arrows[e].animate.set_color(C_RED).set_stroke(width=4.5) for e in cyc], run_time=1.0)
        self.wait_key("输出不足九个")
        res = VGroup(T(f"输出 {len(out)} 门 < 9", 24, C_RED), T("有环", 30, C_RED)).arrange(DOWN, buff=0.15)
        res.move_to([QX, 0.3, 0])
        self.play(FadeIn(res, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(empty, res, self.qhead, self.out_lab, *self.output, *self.badges.values(),
                                 *arrows.values())),
                  *[n[0].animate.set_stroke(WHITE, 2.5).set_fill(BG, 0) for n in nodes.values()], run_time=0.8)
        self.arrows = {e: make_arrow(nodes, *e) for e in D.EDGES}     # 淡掉过的箭头重建，不去恢复透明度
        self.play(*[GrowArrow(a) for a in self.arrows.values()], run_time=0.6)

    # ---------------------------------------------------------------- 第二种做法：DFS 结束逆序
    def dfs_beat(self):
        self.beat("dfs")
        legend = VGroup()
        for name, fill, op, stroke in (("白：未访问", BG, 0, WHITE), ("灰：访问中", C_GRAYST, 1, WHITE),
                                       ("黑：已结束", C_BLACKST, 1, C_GREY)):
            sw = RoundedRectangle(corner_radius=0.06, width=0.42, height=0.3, stroke_color=stroke, stroke_width=2)
            sw.set_fill(fill, op)
            legend.add(VGroup(sw, T(name, 20)).arrange(RIGHT, buff=0.18))
        legend.arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([QX, 2.3, 0])
        self.play(FadeIn(legend), run_time=0.8)
        self.legend = legend
        fin_lab = T("结束顺序", 20, C_GREY).move_to([-5.6, OUT_Y + 0.52, 0])
        self.play(FadeIn(fin_lab), run_time=0.4)
        topo, finish, ev = D.dfs_topo_trace()
        keys = {("enter", 0): "从高数出发", ("enter", 2): "离散、", ("enter", 3): "数据结构、编译", ("enter", 5): "编译。",
                ("finish", 5): "第一个结束", ("enter", 6): "操作系统第二", ("finish", 6): "第二个结束",
                ("finish", 3): "接着数据结构", ("finish", 2): "离散也结束", ("enter", 7): "再走物理",
                ("enter", 8): "这条线", ("finish", 8): "计算机原理、物理", ("finish", 7): "物理、高数",
                ("finish", 0): "高数依次", ("enter", 1): "最后从程序设计", ("enter", 4): "只剩算法语言",
                ("finish", 4): "没去过", ("finish", 1): "没去过"}
        stack = []
        self.fin_badges, chips = {}, []
        g = D.graph_dict()
        for e in ev:
            k = keys[e]
            t = self.at(k) if k != "编译。" else self.at("编译") + 0.3
            if e == ("finish", 1):
                t += 0.7
            self.wait_until(t)
            kind, u = e
            box = self.nodes[u][0]
            if kind == "enter":
                anims = [box.animate.set_fill(C_GRAYST, 1).set_stroke(C_YELLOW, 3.5)]
                if stack:
                    anims.append(self.arrows[(stack[-1], u)].animate.set_color(C_YELLOW).set_stroke(width=4.5))
                self.play(*anims, run_time=0.45)
                stack.append(u)
            else:
                stack.pop()
                k_fin = len(chips)
                fb = badge(self.nodes[u], k_fin + 1, C_BLUE)
                c = chip(u, col=C_BLUE).move_to(out_slot(k_fin))
                chips.append(c)
                self.fin_badges[u] = fb
                self.play(box.animate.set_fill(C_BLACKST, 1).set_stroke(C_GREY, 2.5), FadeIn(fb, scale=1.5),
                          FadeIn(c, target_position=self.nodes[u].get_center()), run_time=0.7)
        self.wait_key("倒过来")
        n = len(chips)
        self.play(*[c.animate(path_arc=PI / 2).move_to(out_slot(n - 1 - k)) for k, c in enumerate(chips)],
                  Transform(fin_lab, T("拓扑序", 20, C_GREEN).move_to(fin_lab)), run_time=1.4)
        self.play(*[c[0].animate.set_stroke(C_GREEN) for c in chips], run_time=0.5)
        self.dfs_chips, self.fin_lab = chips, fin_lab
        self.wait(max(0.1, self.left() - 0.2))

    # ---------------------------------------------------------------- 为什么倒过来就对
    def why_beat(self):
        self.beat("why")
        u, v = 3, 6
        self.play(FadeOut(self.legend), run_time=0.5)
        self.wait_key("任取一条边")
        ar = self.arrows[(u, v)]
        lu = T("起点", 20, C_YELLOW).next_to(self.nodes[u], DOWN, buff=0.12)
        lv = T("终点", 20, C_YELLOW).next_to(self.nodes[v], RIGHT, buff=0.15)
        self.play(ar.animate.set_color(C_RED).set_stroke(width=6), FadeIn(lu), FadeIn(lv), run_time=0.8)
        cases = VGroup(T("终点是白：", 22), T("在起点里先结束", 20, C_GREEN),
                       T("终点是黑：", 22), T("早已结束", 20, C_GREEN),
                       T("终点是灰：", 22), T("有环！", 20, C_RED))
        for k in range(0, 6, 2):
            cases[k + 1].next_to(cases[k], DOWN, buff=0.1, aligned_edge=LEFT)
        rows = VGroup(*[VGroup(cases[k], cases[k + 1]) for k in range(0, 6, 2)]).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        rows.move_to([QX, 1.7, 0])
        self.wait_key("终点要么还没访问")
        self.play(FadeIn(rows[0], shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("要么早已结束")
        self.play(FadeIn(rows[1], shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("终点不可能是灰色")
        self.play(FadeIn(rows[2], shift=LEFT * 0.2), run_time=0.6)
        self.wait_key("所以终点总比")
        concl = VGroup(T("终点先结束", 22, C_YELLOW), T("倒过来：起点在前", 22, C_YELLOW)).arrange(DOWN, buff=0.12)
        concl.move_to([QX, -0.9, 0])
        self.play(FadeIn(concl, shift=UP * 0.2), Indicate(self.fin_badges[v][1], color=C_YELLOW, scale_factor=1.5),
                  Indicate(self.fin_badges[u][1], color=C_YELLOW, scale_factor=1.5), run_time=1.0)
        self.wait(max(0.1, self.left() - 0.6))
        self.play(FadeOut(VGroup(*self.arrows.values(), *self.nodes.values(), *self.fin_badges.values(), lu, lv,
                                 rows, concl, *self.dfs_chips, self.fin_lab)), run_time=0.6)

    # ---------------------------------------------------------------- 回顾
    def recap_beat(self):
        self.beat("recap")
        cplx = MathTex(r"O(V+E)", color=C_YELLOW).scale(1.2).move_to([0, 2.6, 0])
        self.play(Write(cplx), run_time=0.8)
        cards = VGroup()
        for head, lines, col in (("卡恩算法", ["入度为零就出队", "输出不够 → 有环"], C_GREEN),
                                 ("深度优先", ["结束顺序倒过来", "撞上灰点 → 有环"], C_BLUE)):
            box = RoundedRectangle(corner_radius=0.2, width=5.2, height=2.4, stroke_color=col, stroke_width=3)
            box.set_fill(col, 0.06)
            body = VGroup(T(head, 32, col), *[T(s, 26) for s in lines]).arrange(DOWN, buff=0.25).move_to(box)
            cards.add(VGroup(box, body))
        cards.arrange(RIGHT, buff=0.7).move_to([0, 0.0, 0])
        self.wait_key("卡恩算法")
        self.play(FadeIn(cards[0], shift=UP * 0.2), run_time=0.8)
        self.wait_key("深度优先")
        self.play(FadeIn(cards[1], shift=UP * 0.2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.2))
        src = T("数据结构与算法（B）2026fall · 第 7 周 图 4.3–4.5 节 · sunnywhy 403", 20, C_GREY).to_edge(DOWN, buff=0.2)
        self.clear_subs()
        self.play(FadeIn(src), run_time=0.6)
        self.wait(1.5)
