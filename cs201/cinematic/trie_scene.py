"""字典树：一个字母走一步（3B1B 风格）。

由 make.py 驱动，时间轴约定见 cs101/cinematic/cine.py。结点、插入时的新建 / 共用、查找停在哪、前缀补全的
结果、删除拆掉的结点、空间账（17 个结点 × 26 格）全部来自 triedata（2026spring 树讲义附录 B 的 Trie 原样插桩；
test_trie.py 对撞讲义测试输出、Python set / startswith 暴力与随机词典）。

结点用「从根到它的路径」命名（根是 ""）；画面上结点里写最后一个字母。叶子按字典序等距排开，内部结点居中，
所以从左往右读叶子就是字典序。
"""
from __future__ import annotations

import sys
from pathlib import Path

from manim import *  # noqa: F403

sys.path.insert(0, str(Path(__file__).resolve().parent))
import triedata as D  # noqa: E402
from cine import *  # noqa: E402,F403

R = 0.28
C_NEW, C_SHARE, C_WALK, C_END = C_GREEN, C_TEAL, C_YELLOW, C_GREEN
PX = 3.95                                   # 右侧说明栏中心


def layout(paths, x0=-5.6, step=1.05, top=2.55, dy=1.05):
    kids = {p: sorted(q for q in paths if len(q) == len(p) + 1 and q.startswith(p)) for p in paths}
    leaves = [p for p in sorted(paths) if not kids[p]]
    pos = {p: np.array([x0 + i * step, top - dy * len(p), 0]) for i, p in enumerate(leaves)}

    def go(p):
        if p in pos:
            return pos[p][0]
        xs = [go(c) for c in kids[p]]
        pos[p] = np.array([sum(xs) / len(xs), top - dy * len(p), 0])
        return pos[p][0]
    go("")
    return pos, kids


POS, KIDS = layout(list(D.FULL))


def tnode(path):
    if path == "":
        return VGroup(Circle(R, stroke_color=C_GREY, stroke_width=3).set_fill(BG, 0), T("根", 20, C_GREY))
    return VGroup(Circle(R, stroke_color=WHITE, stroke_width=3).set_fill(BG, 0), T(path[-1], 28))


def badge(n, at, color=C_END):
    c = Circle(0.15, stroke_width=0).set_fill(color, 1)
    return VGroup(c, T(str(n), 18, BG)).move_to(at + np.array([0.3, 0.3, 0]))


class TrieLesson(Lesson):
    def construct(self):
        for b in ("title", "build", "mark", "search", "cost", "prefix", "memory", "delete", "recap"):
            getattr(self, f"{b}_beat")()
        self.finish()

    def cue_start(self, key, default=None):
        return next((c["start"] for c in self.cue_times() if key in c["text"]), default)

    def wait_cue(self, key, default=None):
        t = self.cue_start(key, default)
        if t is not None:
            self.wait_until(t)

    def ring(self, path, color=C_WALK, w=5):
        return Circle(R + 0.1, stroke_color=color, stroke_width=w).move_to(POS[path])

    def walk(self, word, dt=0.45, color=C_WALK, upto=None):
        """指针从根沿 word 走下去（只走存在的结点）；返回指针圆，调用方负责淡出。"""
        ring = self.ring("", color)
        self.play(Create(ring), run_time=0.3)
        for k in range(1, len(word) + 1):
            p = word[:k]
            if p not in self.nodes or (upto is not None and k > upto):
                break
            self.play(ring.animate.move_to(POS[p]), self.nodes[p][0].animate.set_stroke(color, 4), run_time=dt)
        return ring

    def reset_strokes(self):
        return [n[0].animate.set_stroke(C_GREY if p == "" else WHITE, 3) for p, n in self.nodes.items()]

    def panel(self, *lines, y=1.6, size=26, colors=None, buff=0.28):
        colors = colors or [WHITE] * len(lines)
        g = VGroup(*[T(s, size, c) for s, c in zip(lines, colors)]).arrange(DOWN, buff=buff, aligned_edge=LEFT)
        return g.move_to([PX, y, 0])

    # ---------------------------------------------------------------- 片头：搜索框
    def title_beat(self):
        self.beat("title")
        title = T("字典树", 60).move_to([0, 3.15, 0])
        sub = T("一个字母走一步", 30, C_BLUE).move_to([0, 2.5, 0])
        box = RoundedRectangle(corner_radius=0.15, width=5.2, height=0.8, stroke_color=C_GREY, stroke_width=3)
        box.move_to([0, 1.2, 0])
        typed = Text("an", font=MONO, font_size=34).move_to(box.get_left() + RIGHT * 0.65)
        caret = Line(UP * 0.25, DOWN * 0.25, stroke_color=WHITE, stroke_width=3).next_to(typed, RIGHT, buff=0.08)
        drop = VGroup(*[VGroup(Rectangle(width=5.2, height=0.62, stroke_color=C_GREY, stroke_width=1.5),
                               Text(w, font=MONO, font_size=28, color=C_YELLOW)) for w in D.COMPLETE["an"]])
        drop.arrange(DOWN, buff=0).next_to(box, DOWN, buff=0.05)
        for r in drop:
            r[1].align_to(r[0], LEFT).shift(RIGHT * 0.45)
        self.play(Create(box), run_time=0.6)
        self.play(AddTextLetterByLetter(typed), run_time=0.6)
        self.add(caret)
        self.play(LaggedStart(*[FadeIn(r, shift=DOWN * 0.15) for r in drop], lag_ratio=0.3), run_time=0.9)
        self.wait_cue("散列表帮不上忙")
        hash_note = T("散列表：只认完整的关键字，前缀得挨个看一遍", 26, C_RED).move_to([0, -1.0, 0])
        self.play(FadeIn(hash_note, shift=UP * 0.2), run_time=0.8)
        self.wait_cue("这一集")
        self.play(Write(title), FadeIn(sub, shift=UP * 0.2), run_time=1.2)
        self.wait(max(0.1, self.left() - 0.7))
        self.play(FadeOut(VGroup(title, sub, box, typed, caret, drop, hash_note)), run_time=0.7)

    # ---------------------------------------------------------------- 插入六个词
    def build_beat(self):
        self.beat("build")
        self.nodes, self.edges, self.labels = {}, {}, {}
        self.nodes[""] = tnode("").move_to(POS[""])
        self.play(GrowFromCenter(self.nodes[""]), run_time=0.5)
        words = VGroup(*[Text(w, font=MONO, font_size=30, color=C_GREY) for w in D.WORDS]).arrange(RIGHT, buff=0.4)
        words.scale_to_fit_width(min(words.width, 5.3)).move_to([PX, 2.95, 0])
        legend = VGroup(VGroup(Dot(color=C_NEW), T("新建", 24, C_NEW)).arrange(RIGHT, buff=0.12),
                        VGroup(Dot(color=C_SHARE), T("共用", 24, C_SHARE)).arrange(RIGHT, buff=0.12))
        legend.arrange(RIGHT, buff=0.6).move_to([PX, 2.2, 0])
        self.play(FadeIn(words), FadeIn(legend), run_time=0.6)
        self.word_row = words
        self.legend = legend
        cue_for = {"and": "插入就是", "ant": "插 ant", "dad": "插 dad"}
        fast = {"do", "geek", "ball"}
        stats = {}
        for i, (w, trace) in enumerate(D.INSERTS):
            if w in cue_for:
                self.wait_cue(cue_for[w])
            dt = 0.32 if w in fast else 0.55
            self.play(words[i].animate.set_color(C_YELLOW), run_time=0.25)
            ring = self.ring("")
            self.add(ring)
            for p, kind in trace:
                if kind == "new":
                    n = tnode(p).move_to(POS[p])
                    e = Line(POS[p[:-1]], POS[p], buff=R, stroke_color=C_GREY, stroke_width=3)
                    self.nodes[p], self.edges[p] = n, e
                    self.play(ring.animate.move_to(POS[p]), Create(e), GrowFromCenter(n),
                              n[0].animate.set_stroke(C_NEW, 4), run_time=dt)
                else:
                    self.play(ring.animate.move_to(POS[p]), self.nodes[p][0].animate.set_stroke(C_SHARE, 5),
                              run_time=dt)
            lab = Text(w, font=MONO, font_size=22, color=C_GREY).next_to(self.nodes[w], DOWN, buff=0.12)
            self.labels[w] = lab
            self.play(FadeIn(lab), FadeOut(ring), words[i].animate.set_color(WHITE), *self.reset_strokes(),
                      run_time=0.35)
            stats[w] = sum(k == "new" for _, k in trace)
        self.wait_cue("公共前缀只存一份")
        note = self.panel(f"{D.N_CHARS} 个字母，只建了 {D.N_NODES - 1} 个结点", y=1.2, size=26, colors=[C_SHARE])
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(note), FadeOut(legend), run_time=0.5)

    # ---------------------------------------------------------------- 结束计数
    def mark_beat(self):
        self.beat("mark")
        ring = self.walk("an", dt=0.4)
        q = T("an 算不算单词？", 28, C_YELLOW).move_to([PX, 1.6, 0])
        self.play(FadeIn(q), run_time=0.5)
        self.wait_cue("所以每个结点")
        self.badges = {p: badge(c, POS[p]) for p, c in D.FULL.items() if c}
        zero = badge(0, POS["an"], C_GREY)
        self.play(LaggedStart(*[FadeIn(b, scale=1.6) for b in self.badges.values()], lag_ratio=0.12),
                  FadeIn(zero, scale=1.6), FadeOut(ring), *self.reset_strokes(), run_time=1.4)
        self.zero = zero
        code = Paragraph("class TrieNode:", "    children = [None] * 26", "    word_count = 0",
                         font=MONO, font_size=22, line_spacing=0.8).move_to([PX, 0.35, 0])
        code[2].set_color(C_END)
        self.wait_cue("讲义用的是计数")
        self.play(q.animate.set_opacity(0.4), FadeIn(code, shift=UP * 0.2), run_time=0.8)
        twice = T("同一个词插两次 → 计数是 2", 24, C_GREY).move_to([PX, -0.9, 0])
        self.play(FadeIn(twice), run_time=0.6)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(q, code, twice)), run_time=0.5)

    # ---------------------------------------------------------------- 查找：do / bat / an
    def search_beat(self):
        self.beat("search")
        rows = []
        specs = [("do", "查 do"), ("bat", "查 bat"), ("an", "查 an")]
        for i, (w, cue) in enumerate(specs):
            self.wait_cue(cue)
            path, broke, found, pre = D.SEARCH[w]
            ring = self.ring("")
            self.play(Create(ring), run_time=0.25)
            for p in path:
                self.play(ring.animate.move_to(POS[p]), self.nodes[p][0].animate.set_stroke(C_WALK, 4), run_time=0.4)
            if broke is not None:
                self.play(ring.animate.set_color(C_RED), self.nodes[path[-1]][0].animate.set_stroke(C_RED, 5),
                          run_time=0.4)
                txt, col = f"查 {w}：{path[-1][-1]} 下面没有 {w[broke]} → 失败", C_RED
            elif found:
                self.play(Indicate(self.badges[w], color=C_END, scale_factor=1.5), run_time=0.5)
                txt, col = f"查 {w}：走到底，计数 {D.FULL[w]} → 找到", C_GREEN
            else:
                self.play(Indicate(self.zero, color=C_GREY, scale_factor=1.5), run_time=0.5)
                txt, col = f"查 {w}：走得通，计数 0 → 只是前缀", C_YELLOW
            row = T(txt, 24, col).move_to([PX, 1.5 - 0.65 * i, 0])
            rows.append(row)
            self.play(FadeIn(row, shift=LEFT * 0.2), FadeOut(ring), *self.reset_strokes(), run_time=0.5)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(*rows)), run_time=0.5)

    # ---------------------------------------------------------------- 代价只和单词长度有关
    def cost_beat(self):
        self.beat("cost")
        ring = self.ring("")
        self.play(Create(ring), run_time=0.3)
        counter = VGroup(T("步数", 26, C_WALK), Integer(0, font_size=40, color=C_WALK)).arrange(RIGHT, buff=0.25)
        counter.move_to([PX, 1.8, 0])
        self.play(FadeIn(counter), run_time=0.3)
        for k, p in enumerate(["a", "an", "ant"], 1):
            self.play(ring.animate.move_to(POS[p]), self.nodes[p][0].animate.set_stroke(C_WALK, 4),
                      ChangeDecimalToValue(counter[1], k), run_time=0.5)
        self.wait_cue("词典里存六个词")
        head = VGroup(T("词典大小", 24, C_GREY), T("查 ant 走几步", 24, C_GREY)).arrange(RIGHT, buff=0.9)
        rows = VGroup(head)
        for n in D.DICT_SIZES:
            r = VGroup(T(f"{n:,}".replace(",", " ") + " 个词", 26), T(f"{D.STEPS_ANT[n]} 步", 26, C_WALK))
            rows.add(r)
        for r in rows:
            r[0].move_to([PX - 1.15, 0, 0])
            r[1].move_to([PX + 1.35, 0, 0])
        for i, r in enumerate(rows):
            r.shift(UP * (0.75 - 0.6 * i))
        self.play(FadeIn(rows[0]), FadeIn(rows[1]), run_time=0.6)
        self.wait_cue("存六百个")
        self.play(LaggedStart(FadeIn(rows[2], shift=UP * 0.15), FadeIn(rows[3], shift=UP * 0.15), lag_ratio=0.5),
                  run_time=1.2)
        self.wait_cue("代价只和单词长度有关")
        concl = T("步数 ≤ 单词长度，与词典大小无关", 26, C_GREEN).move_to([PX, -1.8, 0])
        self.play(FadeIn(concl, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(ring, counter, rows, concl)), *self.reset_strokes(), run_time=0.5)

    # ---------------------------------------------------------------- 前缀补全
    def subtree_box(self, prefix, color):
        members = [self.nodes[p] for p in self.nodes if p.startswith(prefix) and p]
        members += [self.labels[w] for w in self.labels if w.startswith(prefix)]
        return SurroundingRectangle(VGroup(*members), color=color, buff=0.12, corner_radius=0.15)

    def prefix_beat(self):
        self.beat("prefix")
        ring = self.walk("an", dt=0.45)
        box = self.subtree_box("an", C_YELLOW)
        self.play(Create(box), run_time=0.7)
        out1 = VGroup(T("前缀 an →", 26, C_YELLOW),
                      *[Text(w, font=MONO, font_size=28) for w in D.COMPLETE["an"]]).arrange(RIGHT, buff=0.3)
        out1.move_to([PX, 1.5, 0])
        self.wait_cue("孩子按字母顺序")
        self.play(FadeIn(out1[0]), run_time=0.3)
        for w, t in zip(D.COMPLETE["an"], out1[1:]):
            self.play(Indicate(self.labels[w], color=C_YELLOW), FadeIn(t, shift=LEFT * 0.2), run_time=0.7)
        dict_note = T("深度优先、孩子按 a→z：天然字典序", 24, C_GREY).move_to([PX, 0.8, 0])
        self.play(FadeIn(dict_note), run_time=0.5)
        self.wait_cue("前缀 d")
        self.play(FadeOut(ring), FadeOut(box), *self.reset_strokes(), run_time=0.4)
        ring = self.walk("d", dt=0.45, color=C_PURPLE)
        box2 = self.subtree_box("d", C_PURPLE)
        out2 = VGroup(T("前缀 d →", 26, C_PURPLE),
                      *[Text(w, font=MONO, font_size=28) for w in D.COMPLETE["d"]]).arrange(RIGHT, buff=0.3)
        out2.move_to([PX, 0.05, 0])
        self.play(Create(box2), FadeIn(out2), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(ring, box2, out1, out2, dict_note)), *self.reset_strokes(), run_time=0.5)

    # ---------------------------------------------------------------- 空间：26 格的指针数组
    def memory_beat(self):
        self.beat("memory")
        cells = VGroup(*[Square(0.19, stroke_color=C_GREY, stroke_width=1.5) for _ in range(26)]).arrange(RIGHT, buff=0)
        cells.move_to([PX, 1.6, 0])
        lab = T("根结点的 children：26 格", 24, C_GREY).next_to(cells, UP, buff=0.25)
        used = {ch: ord(ch) - ord("a") for ch in D.ROOT_KIDS}
        marks = VGroup(*[T(ch, 20, C_YELLOW).next_to(cells[i], DOWN, buff=0.1) for ch, i in used.items()])
        ring = self.ring("", C_YELLOW)
        self.play(Create(ring), FadeIn(lab), Create(cells), run_time=1.0)
        self.play(*[cells[i].animate.set_fill(C_YELLOW, 0.8) for i in used.values()], FadeIn(marks),
                  *[self.nodes[p][0].animate.set_stroke(C_YELLOW, 4) for p in D.ROOT_KIDS], run_time=0.9)
        self.wait_cue("整棵树")
        acc = VGroup(T(f"{D.N_NODES} 个结点 × 26 格 = {D.SLOTS} 格", 26),
                     T(f"真正用到：{D.USED} 格", 26, C_YELLOW)).arrange(DOWN, buff=0.25).move_to([PX, 0.1, 0])
        self.play(FadeIn(acc[0], shift=UP * 0.2), run_time=0.7)
        self.play(FadeIn(acc[1], shift=UP * 0.2), run_time=0.6)
        self.wait_cue("字母稀疏")
        alt = Text("children = {}  # 只存出现的孩子", font=MONO, font_size=22, color=C_GREEN).move_to([PX, -1.2, 0])
        self.play(FadeIn(alt, shift=UP * 0.2), run_time=0.7)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(cells, lab, marks, ring, acc, alt)), *self.reset_strokes(), run_time=0.5)

    # ---------------------------------------------------------------- 删除：从下往上拆
    def remove_node(self, p):
        anims = [FadeOut(self.nodes.pop(p)), FadeOut(self.edges.pop(p))]
        if p in self.badges:
            anims.append(FadeOut(self.badges.pop(p)))
        if p in self.labels:
            anims.append(FadeOut(self.labels.pop(p)))
        return anims

    def delete_beat(self):
        self.beat("delete")
        head = T("删 geek", 28, C_RED).move_to([PX, 2.3, 0])
        self.play(FadeIn(head), run_time=0.4)
        ring = self.walk("geek", dt=0.35, color=C_RED)
        self.wait_cue("先把 k 的计数")
        zero = badge(0, POS["geek"], C_GREY)
        self.play(Transform(self.badges["geek"], zero), run_time=0.5)
        steps = VGroup()
        why = {"geek": "k：计数 0，没有孩子 → 拆", "gee": "e：不是结尾，没孩子了 → 拆",
               "ge": "e：同上 → 拆", "g": "g：同上 → 拆，回到根"}
        self.play(FadeOut(ring), run_time=0.2)
        for i, p in enumerate(D.DEL_GEEK):
            if i == 1:
                self.wait_cue("回到上一层")
            t = T(why[p], 24, C_RED if i == 0 else WHITE).move_to([PX, 1.6 - 0.55 * i, 0])
            steps.add(t)
            self.play(self.nodes[p][0].animate.set_stroke(C_RED, 5), FadeIn(t, shift=LEFT * 0.2), run_time=0.45)
            self.play(*self.remove_node(p), run_time=0.5)
        self.wait_cue("删 ant")
        self.play(FadeOut(steps), head.animate.become(T("删 ant", 28, C_RED).move_to([PX, 2.3, 0])), run_time=0.5)
        ring = self.walk("ant", dt=0.35, color=C_RED)
        p = D.DEL_ANT[0]
        t1 = T("t：计数 0，没有孩子 → 拆", 24, C_RED).move_to([PX, 1.6, 0])
        self.play(self.nodes[p][0].animate.set_stroke(C_RED, 5), FadeIn(t1), run_time=0.45)
        self.play(*self.remove_node(p), FadeOut(ring), run_time=0.5)
        self.wait_cue("因为 n 下面")
        keep = self.ring("an", C_GREEN)
        t2 = T("n：下面还挂着 and → 留下", 24, C_GREEN).move_to([PX, 1.05, 0])
        self.play(Create(keep), FadeIn(t2), Indicate(self.labels["and"], color=C_GREEN), run_time=0.8)
        self.wait(max(0.1, self.left() - 0.5))
        self.play(FadeOut(VGroup(head, t1, t2, keep)), *self.reset_strokes(), run_time=0.5)

    # ---------------------------------------------------------------- 片尾
    def recap_beat(self):
        self.beat("recap")
        lines = self.panel("一个字母一层，前缀只存一份", "插入、查找：步数 = 单词长度",
                           "前缀查询、字典序输出都顺手", "代价：每个结点一排指针",
                           y=0.9, size=26, colors=[WHITE, C_WALK, C_YELLOW, C_GREY], buff=0.4)
        for i, l in enumerate(lines):
            if i == 1:
                self.wait_cue("插入和查找")
            if i == 3:
                self.wait_cue("代价是")
            self.play(FadeIn(l, shift=UP * 0.2), run_time=0.6)
        self.wait(max(0.1, self.left()))
        rest = VGroup(lines, self.word_row, self.zero, *self.nodes.values(), *self.edges.values(),
                      *self.badges.values(), *self.labels.values())
        self.play(FadeOut(rest), run_time=0.8)
