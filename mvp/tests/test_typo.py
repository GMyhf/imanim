"""排版层斜体判定测试（评审 N3 / 五.3）。

物理排版规范：拉丁单字母「变量符号」斜体；CJK、单位（m/s、V、mol）、数字、希腊字母（Δ）正体。
纯标准库 unittest；测 slant 判定纯函数 + rich() 不崩 + 字体标定常量对得上本机字体栈。
最后一类不渲染像素，只读 manim Text 的 SVG 轮廓点（与 .local/typo2/probe.py 同一量法）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "render"))

import scene as S  # noqa: E402


class TestSlantDecision(unittest.TestCase):
    """slant_chars：字符串 → 应斜体的字符集合。"""

    def test_formula_card_exactly_variables(self):
        # 评审给的判据例句：斜体集合必须恰好是 {a, v, t}
        self.assertEqual(S.slant_chars("a = Δv / Δt = (v_t − v₀) / Δt"), {"a", "v", "t"})

    def test_cjk_and_units_stay_upright(self):
        self.assertEqual(S.slant_chars("单位：m/s²（米每二次方秒）"), set())
        self.assertEqual(S.slant_chars("加速度刻画的是速度变化的快慢"), set())

    def test_coefficient_times_variable_is_slanted(self):
        """回归 batch_v4 评审 D1：「y = 2x + 1」里 y 斜体、x 正体，同一表达式两种体例。

        规则边界：数字与字母之间**有空格**才是量纲（20 m/s 正体），**没空格**是系数（2x 斜体）。
        """
        self.assertEqual(S.slant_chars("y = 2x + 1"), {"y", "x"})
        self.assertEqual(S.slant_chars("s = v₀ t + (1/2) a t²"), {"s", "v", "t", "a"})
        self.assertEqual(S.slant_chars("20 m/s"), set())      # 空格隔开的纯数字 → 单位
        self.assertEqual(S.slant_chars("0.5 kg"), set())      # 成词单位白名单
        self.assertEqual(S.slant_chars("0.5 mol"), set())     # 多字母词一律正体

    def test_variable_product_digraph_is_slanted_but_units_are_not(self):
        """两个字母的 run（大小写都算）：变量相乘/两点连线斜体，成词单位与标识符正体。"""
        self.assertEqual(S.slant_chars("F = ma"), {"F", "m", "a"})
        self.assertEqual(S.slant_chars("4 × (1/2)ab + (b−a)² = c²"), {"a", "b", "c"})
        self.assertEqual(S.slant_chars("kp.physics.acceleration"), set())
        # 评审 D1 残留：|PF₁| 的 P、F 与同一行的斜体 F 混排（大写连写此前一律正体）。
        # 欧姆定律 U = IR 同理是 I×R 两个变量，不是叫 "IR" 的一个量。
        self.assertEqual(S.slant_chars("U = IR"), {"U", "I", "R"})
        self.assertEqual(S.slant_chars("|PF₁| 与 |F₁F₂| 之差"), {"P", "F"})
        # 元素符号是驼峰（Na、Cl），两字母既非全小写也非全大写 → 保持正体
        self.assertEqual(S.slant_chars("Na 与 Cl 的浓度"), set())

    def test_algebraic_division_is_variable_not_unit(self):
        # v=s/t 里的 / 是代数除号（同片段含 =），s、t 是变量 → 斜体；而 m/s 无 = → 单位 → 正体
        self.assertEqual(S.slant_chars("比值的定义方法（如速度 v=s/t）"), {"v", "s", "t"})
        self.assertEqual(S.slant_chars("80 m/s"), set())

    def test_number_prefixed_unit_letter_upright(self):
        # "10 s" / "250 m/s" 的 s、m 紧跟独立数字 → 单位，正体；同一行的 t 仍是变量
        self.assertEqual(S.slant_chars("t = 10 s"), {"t"})
        self.assertEqual(S.slant_chars("v = 250 m/s"), {"v"})

    def test_axis_label_idiom_is_quantity_over_unit(self):
        """轴名的标准写法「量 / 单位」：带空格的斜杠只把**右侧**判成单位，左侧仍是量符号。

        分界就是斜杠旁边有没有空格——无空格 m/s 是复合单位（两侧正体），带空格的左侧是被除的量。
        混为一谈时「a / (m·s⁻²)」的 a 丢了斜体、「F / N」的 N 白斜了，同一屏两种体例（评审 D28）。
        """
        self.assertEqual(S.slant_chars("t / s"), {"t"})
        self.assertEqual(S.slant_chars("F / N"), {"F"})
        self.assertEqual(S.slant_chars("a / (m·s⁻²)"), {"a"})
        self.assertEqual(S.slant_chars("v / (m·s⁻¹)"), {"v"})
        self.assertEqual(S.slant_chars("1 / m"), set())
        self.assertEqual(S.slant_chars("(E − E°) / mV"), {"E"})
        self.assertEqual(S.slant_chars("m/s"), set())
        # 有运算符的片段里斜杠是代数除号，两侧都还是变量
        self.assertEqual(S.slant_chars("v=s/t"), {"v", "s", "t"})

    def test_log_operators_stay_upright(self):
        """lg/ln 是对数算子（正体），形状却和「两个变量相乘」的两字母小写 run 撞车。"""
        self.assertEqual(S.slant_chars("lg(氧化型 / 还原型)"), set())
        self.assertEqual(S.slant_chars("lg Q"), {"Q"})

    def test_multiletter_words_and_greek_upright(self):
        self.assertEqual(S.slant_chars("mol"), set())
        self.assertEqual(S.slant_chars("v_max"), {"v"})          # 多字母下标 max 正体
        self.assertEqual(S.slant_chars("Δv 与 Δt"), {"v", "t"})   # Δ 希腊正体，v/t 变量斜体

    def test_element_symbol_before_charge_or_count_is_upright(self):
        """元素符号正体、量符号斜体（IUPAC 体例）。评审 B D-04：v7 的 chem 片同一屏「H 斜、Zn/Cu 正」。

        判据只看单字母 run 右侧紧邻的字符：电荷或计量数字 → 元素符号；
        运算符/空格（物理的单字母变量）→ 仍然斜体，不能把 F = ma 一起正体化。
        """
        self.assertEqual(S.slant_chars("c(H⁺) = 1 mol/L"), {"c"})
        self.assertEqual(S.slant_chars("O₂ 与 H₂"), set())
        self.assertEqual(S.slant_chars("Fe³⁺"), set())
        self.assertEqual(S.slant_chars("F = ma"), {"F", "m", "a"})
        self.assertEqual(S.slant_chars("U_外 = U_内"), {"U"})

    def test_vt_graph_label(self):
        self.assertEqual(S.slant_chars("v-t 图斜率即加速度"), {"v", "t"})

    def test_indices_align_with_string(self):
        s = "a = Δv"
        idx = S.slant_indices(s)
        self.assertEqual(len(idx), len(s))
        self.assertEqual({c for c, it in zip(s, idx) if it}, {"a", "v"})

    def test_subscript_letters_italic_digits_upright(self):
        # 下标内容单独判定：单字母下标（t）斜体，数字下标（0）正体
        self.assertEqual(S.slant_indices("t"), [True])
        self.assertEqual(S.slant_indices("0"), [False])
        self.assertEqual(S.slant_indices("合"), [False])  # CJK 下标正体

    def test_empty_and_none_safe(self):
        self.assertEqual(S.slant_chars(""), set())
        self.assertEqual(S.slant_chars(None), set())


class TestRichComposition(unittest.TestCase):
    """rich() 结构：CJK 行走单 Text；含下标走 VGroup 拼接，且斜体不改变分片数。"""

    def test_plain_cjk_returns_single_text(self):
        mob = S.rich("加速度", 54, "#ffffff")
        self.assertEqual(type(mob).__name__, "Text")

    def test_subscript_line_returns_group(self):
        mob = S.rich("a = (v_t − v₀) / Δt", 54, "#ffffff")
        self.assertEqual(type(mob).__name__, "VGroup")
        self.assertGreater(len(mob), 1)

    def test_formula_still_builds_after_slant(self):
        # 斜体接入后不应崩，且宽度为正
        mob = S.rich("a = Δv / Δt = (v_t − v₀) / Δt", 54, "#ffffff")
        self.assertGreater(mob.width, 0)


class TestUnicodeSuperscript(unittest.TestCase):
    """D27：被下标拆成独立一段的 Unicode 上标（t_{停}² 的 ²）不能落回基线。

    混在长段里时同一次排版会自然抬升，独立成段时 Pango 按墨迹裁剪、底缘被当成基线对齐，
    屏上就读成 `·2`（batch_v6 物理评审实测），所以这一族要显式改走上标道。
    """

    def test_standalone_superscript_is_raised_and_small(self):
        mob = S.rich("v_0²", 54, "#ffffff")
        main, sup = mob[0], mob[-1]
        self.assertLess(sup.height, main.height)
        self.assertAlmostEqual(
            sup.get_bottom()[1] - main.get_bottom()[1], S.SUP_LIFT * 54, delta=0.02)

    def test_ir_brake_line_renders_true_exponent(self):
        mob = S.rich("t_{停}²", 54, "#ffffff")
        self.assertEqual(len(mob), 3)                      # t / 停 / 2
        self.assertGreater(mob[-1].get_bottom()[1], mob[0].get_bottom()[1])

    def test_mixed_long_piece_not_split(self):
        # ² 前后没有上下标标记时整串仍是单 Text，保持既有正确渲染
        mob = S.rich("s = (1/2) a t²", 54, "#ffffff")
        self.assertEqual(type(mob).__name__, "Text")


class TestFontCalibration(unittest.TestCase):
    """字体标定复检（评审 §11 ⑤：让 D27/D28 那一族不再靠人工翻帧发现）。

    scene.py 里那三个 _DELTA_* 与"斜体真的斜"这两件事都不写在代码里能自证的范围之内——
    它们是本机字体栈的实测常量，注释上写着"换 TEXT_FONT 必须重跑一次 .local/typo2/probe.py"。
    这条用例就是那句话的自动化版本：不渲染像素，直接读 manim Text 的 SVG 轮廓点，量当下、比常量。
    字体栈一换（换机器、上创空间的容器）这里先红，而不是等到成片帧里发现下标整体错位。
    """

    FS = 54.0

    def paths(self, mob):
        """每个有点的子物件按弧长采样成一条折线（控制点会越出真实曲线，故采样取极值）。"""
        out = []
        for sub in mob.get_family():
            pts = getattr(sub, "points", None)
            if pts is None or len(pts) < 2:
                continue
            out.append([sub.point_from_proportion(i / (len(pts) - 1)) for i in range(len(pts))])
        return out

    def glyphs(self, text):
        """把 "H" + 待测字形 的一次排版按 x 空隙切成字形框（同一次排版共享基线，跨 Text 不可比）。"""
        boxes = []
        for p in self.paths(S.T(text, font_size=self.FS)):
            xs = [q[0] for q in p]
            ys = [q[1] for q in p]
            boxes.append((min(xs), max(xs), min(ys), max(ys)))
        boxes.sort()
        merged = []
        for b in boxes:
            if merged and b[0] - merged[-1][1] < 0.02:      # 同一字形的多段轮廓（如括号的两笔）
                prev = merged[-1]
                merged[-1] = (min(prev[0], b[0]), max(prev[1], b[1]), min(prev[2], b[2]), max(prev[3], b[3]))
            else:
                merged.append(b)
        return merged

    def drop(self, ch: str) -> float:
        """该字形的墨迹底低于基线多少 × 字号（基线 = 同一行里 H 的墨迹底）。"""
        g = self.glyphs("H" + ch)
        self.assertEqual(len(g), 2, f"H{ch} 没切成两个字形框，标定方法在本机字体栈上失效了")
        return (g[0][2] - g[1][2]) / self.FS

    def left_edge_shear(self, mob) -> float:
        """左缘 dx/dy：正体≈0、斜体明显为正（评审用的同一把尺子——按 y 分带取最左点再最小二乘）。"""
        pts = [q for p in self.paths(mob) for q in p]
        ys = np.array([p[1] for p in pts])
        xs = np.array([p[0] for p in pts])
        edges = np.linspace(ys.min(), ys.max(), 13)
        band_x, band_y = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (ys >= lo) & (ys < hi)
            if m.any():
                band_x.append(xs[m].min())
                band_y.append((lo + hi) / 2)
        return float(np.polyfit(band_y, band_x, 1)[0])

    def test_ink_deltas_still_match_the_font(self):
        self.assertAlmostEqual(self.drop("g"), S._DELTA_DESC, delta=0.0002,
                               msg="降部段下沉量与 _DELTA_DESC 不符：字体栈变了，含 gjpqyQ 的段会错位")
        self.assertAlmostEqual(self.drop("("), S._DELTA_PAREN, delta=0.0002,
                               msg="括号段下沉量与 _DELTA_PAREN 不符：含括号的段会整体抬高、下标反越过括号")
        # _DELTA_CJK 取的是汉字与全角标点里沉得最深的那个，所以对单个字形的关系是"上包络"：
        # 不得低于实测（否则该行按基线对齐时汉字下沿越界），也不得虚高到把整段抬起来。
        cjk = self.drop("学")
        self.assertLessEqual(cjk, S._DELTA_CJK, "汉字段的下沉量已超过 _DELTA_CJK，拼接会错位")
        self.assertGreaterEqual(S._DELTA_CJK, cjk - 0.0002)
        self.assertLess(S._DELTA_CJK - cjk, 0.0006, "_DELTA_CJK 比常见汉字深太多，会把汉字段顶离基线")

    def test_digits_sit_on_the_baseline(self):
        """数字必须落在基线上（旧值标在未指定字体的 Sans 上，那一款是旧式数字，0 只有 x 高、4/7 掉到基线下）。"""
        for d in "0479":
            self.assertLess(abs(self.drop(d)), 0.0005, f"{d} 是旧式数字（下沉 {self.drop(d):.5f}），字体回落了")

    def test_t2s_actually_slants_the_glyph(self):
        """判定说该斜体，轮廓里就得真的斜：本机 Pango 拿不到 oblique 面时 t2s 会静默出正体。

        用 N 而不是 a 做探针：a 的左缘本身是弧线（正体也量出 0.24），只有直杆字形才量得出"倾斜"。
        """
        upright = self.left_edge_shear(S.T("N", font_size=self.FS))
        italic = self.left_edge_shear(S.T("N", font_size=self.FS, t2s={"N": "ITALIC"}))
        self.assertLess(abs(upright), 0.05, f"正体 N 的左缘斜率 {upright:.3f}，本机默认体已是斜体？")
        self.assertGreater(italic - upright, 0.15,
                           f"t2s 只把 N 斜了 {italic - upright:.3f}：字体栈缺 oblique 面，屏上变量与单位会混成一种体")


if __name__ == "__main__":
    unittest.main()
