"""渲染层版式回归：图线标签不得压住任何图线、也不得互相重叠（评审 D1/G3 同族）。

这类缺陷只有成片帧才看得见，静态闸门拦不住，所以反向钉死：把全库 8 条知识点的
graph_vt / figure 原语在无渲染状态下真建一遍，读 _place_label 记录的落点残差，
要求每一条都是 0 分（既不压线也不撞标签）。
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "render"))

import scene as S  # noqa: E402
from pipeline import knowledge, storyboard  # noqa: E402
from pipeline.ir import Brief  # noqa: E402

KP_DIR = Path(__file__).resolve().parents[1] / "pipeline" / "data" / "kp"
GRAPHY = ("graph_vt", "figure")
EX = S.Explainer()


def plans():
    out = []
    for f in sorted(KP_DIR.glob("*/*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        entry = knowledge.load(raw["subject"], raw["topic"])
        brief = Brief(subject=entry["subject"], grade=entry["grade"], topic=entry["topic"],
                      target_seconds=120, style="clean", resolution="1920x1080")
        out.append((f.name, storyboard.build(brief, entry).to_dict()))
    return out


class TestLabelPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bad = []
        cls.n = 0
        for name, plan in plans():
            th = S.THEMES[plan["brief"]["style"]]
            for shot in plan["shots"]:
                for v in shot["visuals"]:
                    if v["kind"] not in GRAPHY:
                        continue
                    S.PLACEMENTS.clear()
                    getattr(EX, EX.BUILDERS[v["kind"]])(v["props"], th)
                    for score, text in S.PLACEMENTS:
                        cls.n += 1
                        if score:
                            cls.bad.append(f"{name} 镜{shot['index']} {v['kind']}「{text}」残差 {score}")

    def test_every_graph_label_lands_clean(self):
        self.assertGreater(self.n, 8, "全库应该至少落位 8 个图线标签，一个都没测到说明用例空转")
        self.assertEqual(self.bad, [], "有图线标签压线或互相重叠")

    def test_placement_log_is_wired(self):
        """反向用例：故意造一个放不下的图，确认残差真的会非零（否则上面的断言是空断言）。"""
        S.PLACEMENTS.clear()
        props = {"points": [[0, 0], [10, 20]], "x_label": "x", "y_label": "y",
                 "label": "一条长得放不下也必须压住某条线的图线标签" * 3,
                 "cases": [{"points": [[0, 20], [10, 0]], "label": "情形标签也长" * 12, "at": "情形"}]}
        getattr(EX, EX.BUILDERS["graph_vt"])(props, S.THEMES["clean"])
        self.assertTrue(any(score for score, _ in S.PLACEMENTS), "放不下时残差应为正，否则打分器空转")


class TestFigureGeometry(unittest.TestCase):
    """图形原语里不该出现退化的多边形。

    弦图曾经把四个内顶点算成同一个点（`v += [rot(v[-1]) for _ in range(3)]` 里右侧先整体
    求值，v[-1] 永远是 v[0]），中间那块"洞"塌成一个点，画出来就是正方形加两条对角线，
    和旁白说的完全对不上。这种错只有帧才看得见，所以在这里钉死：任何多边形至少三个不同顶点。
    """

    def distinct(self, poly) -> int:
        return len({tuple(round(c, 4) for c in pt[:2]) for pt in poly.get_vertices()})

    def shapes(self, props):
        out = []
        for m in getattr(EX, EX.BUILDERS["figure"])(props, S.THEMES["clean"]).get_family():
            if type(m).__name__ == "Polygon":
                out.append(m)
        return out

    def test_chord_has_four_distinct_inner_vertices(self):
        """弦图应当恰好有两个四边形：外面那块 c² 和中间那块 (b−a)²。少一个就是洞塌了。"""
        quads = [p for p in self.shapes({"shape": "chord", "a": 3, "b": 4}) if self.distinct(p) >= 4]
        self.assertEqual(len(quads), 2, "外正方形与中间小正方形应当都在，中间那块退化就没有了")

    def test_no_degenerate_polygon_in_any_figure(self):
        for shape in ("chord", "right_triangle", "ellipse"):
            props = {"shape": shape, "a": 3, "b": 4} if shape != "ellipse" else {"shape": shape, "a": 5, "b": 3}
            for poly in self.shapes(props):
                self.assertGreaterEqual(self.distinct(poly), 3, f"{shape} 里有退化多边形")


class TestTickAvoidance(unittest.TestCase):
    """刻度数字是唯一能让位的东西：图线穿过数字、或数字与轴名上下叠成一列，都是坏图。

    前者是数学 B 评审 Q5（抛物线贴着「−2」实测间隙 0.0px），后者是 batch_v7 newton t=24 实测的
    「1 / 1 / m」——末端刻度与轴名各占一行，读起来像一条除法。两种都只有帧看得见，所以把
    _clear_ticks 每次的 (外推个数, 去掉个数) 记下来钉死：避让必须真的发生，也不能把轴读空。
    """

    @classmethod
    def setUpClass(cls):
        cls.graphs = []
        for name, plan in plans():
            th = S.THEMES[plan["brief"]["style"]]
            for shot in plan["shots"]:
                for v in shot["visuals"]:
                    if v["kind"] != "graph_vt":
                        continue
                    S.TICK_ADJUST.clear()
                    g = getattr(EX, EX.BUILDERS["graph_vt"])(v["props"], th)
                    moved, dropped = S.TICK_ADJUST[-1]
                    left = sum(1 for m in g.get_family() if hasattr(m, "_tick_anchor"))
                    cls.graphs.append((f"{name} 镜{shot['index']}", moved, dropped, left))

    def test_extreme_ticks_survive(self):
        """每条轴**末端那一格**刻度必须在屏上（第四轮 F-9 / 评审 A D7、B D-10）。

        v7 的避让把轴名盒按 AXIS_LABEL_PAD 扩过去桥住刻度与轴名之间那道缝，代价是吃掉末端刻度：
        全库实测 6 处，匀变速的 t 轴只标到 8 而面积矩形画到 10、电极电势的 x 轴同时丢了 1.5 和 2 ——
        学生只能外推读数。轴名现在移出平面右缘，这条断言把"少标末端"钉死成回归。
        """
        for name, plan in plans():
            th = S.THEMES[plan["brief"]["style"]]
            for shot in plan["shots"]:
                for v in shot["visuals"]:
                    if v["kind"] != "graph_vt":
                        continue
                    g = getattr(EX, EX.BUILDERS["graph_vt"])(v["props"], th)
                    plane = next(m for m in g.get_family() if isinstance(m, S.NumberPlane))
                    kept = set()
                    for m in g.get_family():
                        if hasattr(m, "_tick_anchor"):
                            try:
                                kept.add(round(float(m.text), 6))
                            except (ValueError, TypeError):
                                pass
                    where = f"{name} 镜{shot['index']}"
                    for lo, hi, step in (plane.x_range[:3], plane.y_range[:3]):
                        vals = [t for t in S._tick_values(lo, hi, step) if t != 0]
                        if not vals:
                            continue
                        for edge in (min(vals), max(vals)):
                            self.assertIn(round(edge, 6), kept,
                                          f"{where} 的轴末端刻度 {edge} 被避让删掉了")

    def test_avoidance_fires(self):
        self.assertGreaterEqual(len(self.graphs), 8, "全库没建出几个坐标系，用例空转")
        self.assertGreater(sum(m + d for _, m, d, _ in self.graphs), 0, "刻度避让从未生效")

    def test_avoidance_never_empties_the_axis(self):
        for where, _moved, dropped, left in self.graphs:
            self.assertLessEqual(dropped, 2, f"{where} 一次丢掉 {dropped} 格刻度，避让过头了")
            self.assertGreaterEqual(left, 3, f"{where} 避让后只剩 {left} 个数字，坐标轴读不出数")


class TestCornerBandClearance(unittest.TestCase):
    """底部角标带（首镜知识点 id / 末镜出处行）与正文之间要隔开一整块的间距。

    评审 P2 / phys-A D39 实测出处行离正文最后一行只有 9px，投影仪上读成正文的第三行。
    正文底缘由 content_bottom_for 从角标上沿往下让 CORNER_CLEAR，而 CORNER_CLEAR = stack 的
    arrange buff（同屏两块内容之间既有的距离），所以这一条断言不是"试出来的数"。
    """

    def test_body_clears_the_corner_band(self):
        corpus = plans()
        checked = 0
        for name, plan in corpus:
            th = S.THEMES[plan["brief"]["style"]]
            for first, last in ((True, False), (False, True)):
                _body, stack, corners = EX._assemble(
                    plan["shots"][-1] if last else plan["shots"][0], plan, th, is_first=first, is_last=last
                )
                self.assertTrue(corners, f"{name} 首/末镜应当带角标")
                gap = stack.get_bottom()[1] - max(c.get_top()[1] for c in corners)
                self.assertGreaterEqual(gap, S.STACK_BUFF - 1e-6, f"{name} 角标离正文只有 {gap:.3f}")
                checked += 1
        self.assertGreaterEqual(checked, 2 * len(corpus), "首末两端的角标都该测到")


class TestHeaderClearance(unittest.TestCase):
    """页眉与正文之间也要隔开一整块（第四轮 F-7 / 评审 A D4）。

    v7 全库 60 镜实测有 6 镜正文上沿越过页眉墨迹下沿 0~6 px（ell/newt 的顶部甚至并成
    一条连通带），最紧的正常镜头也只剩 46 px。根因是 CONTENT_TOP 是个静态数，
    而 26 pt 页眉的实测底缘比它低 —— 净空靠巧合不靠规则。现在从页眉实测位置往下让
    HEADER_CLEAR，与正文块之间的既有间距同源，所以断言里的阈值不是试出来的数。
    """

    def test_every_shot_clears_the_header(self):
        checked = 0
        for name, plan in plans():
            th = S.THEMES[plan["brief"]["style"]]
            for shot in plan["shots"]:
                body, stack, _corners = EX._assemble(shot, plan, th)
                header, tag = body.submobjects[0], body.submobjects[1]
                gap = min(header.get_bottom()[1], tag.get_bottom()[1]) - stack.get_top()[1]
                self.assertGreaterEqual(gap, S.HEADER_CLEAR - 1e-6,
                                        f"{name} 镜{shot['index']} 页眉离正文只有 {-gap:.3f}")
                checked += 1
        self.assertGreaterEqual(checked, 40, "语料太少，这条断言等于没测")


class TestPlainBlockReveals(unittest.TestCase):
    """不带逐行揭示的正文块要按镜内进度依次进场（第四轮 F-5 / 评审 A D3）。

    v7 有 20 个镜次整屏一次铺满、旁白讲到第三句画面仍是第一句那张图（屏上内容占比
    13%~49% 全程不变）。这里钉两条：①≥2 个这种块时必须各拿到不同的揭示键；
    ②自带逐行揭示的块（steps/summary/callout 断行）不得被整块接管。
    """

    def test_plain_blocks_get_staggered_keys(self):
        staggered = 0
        for name, plan in plans():
            th = S.THEMES[plan["brief"]["style"]]
            for shot in plan["shots"]:
                if len(shot["visuals"]) < 2:
                    continue
                _b, stack, _c = EX._assemble(shot, plan, th)
                for m in stack:
                    inner = [x for x in m.get_family()
                             if x is not m and getattr(x, "_reveal_at", None) is not None]
                    self.assertFalse(isinstance(getattr(m, "_reveal_at", None), float) and inner,
                                     f"{name} 镜{shot['index']} 整块接管压掉了它的逐行揭示")
                keys = [getattr(m, "_reveal_at", None) for m in stack]
                if len({k for k in keys if isinstance(k, float)}) > 1:
                    staggered += 1
        self.assertGreater(staggered, 0, "全库没有一个多块镜头拿到分批键，这条断言等于没测")


if __name__ == "__main__":
    unittest.main()
