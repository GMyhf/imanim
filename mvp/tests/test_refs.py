"""出处角标的可读性回归（第四轮 F-1：唯一改变过线结论的缺陷）。

v7 两条片子（椭圆 12px、匀变速 14px）因为出处行被 `scale_to_fit_width(8.5)` 缩成投影上的灰点，
按 Spec 的 G3 字面判据直接命中一票否决。这条路径当时在静态闸门里没有对应检查，所以 8 条
review.json 全是 []。这里把渲染层的实际几何钉死，并顺手钉住折行纪律：
宁可两行参差、也不把公式从括号里劈开。
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


def ref_lines(plan):
    refs = [f"{r.get('source', '')} {r.get('locator', '')}".strip() for r in plan.get("refs", [])]
    out = []
    for raw in refs:
        text = str(raw)
        probe = S.T(text, font_size=S.REF_FS)
        out += [text] if probe.width <= S.REF_WIDE else S._wrap_ref(text)
    return out


class TestRefLegibility(unittest.TestCase):
    def test_full_corpus_stays_above_the_font_floor(self):
        worst, n = 99.0, 0
        for f in sorted(KP_DIR.glob("*/*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            entry = knowledge.load(doc["subject"], doc["topic"])
            brief = Brief(subject=entry["subject"], grade=entry["grade"], topic=entry["topic"],
                          target_seconds=120, style="clean", resolution="1920x1080")
            plan = storyboard.build(brief, entry).to_dict()
            for seg in ref_lines(plan):
                line = S.T(seg, font_size=S.REF_FS)          # 折行后、缩放前的原始宽
                eff = S.REF_FS * min(1.0, S.REF_WIDE / line.width)
                self.assertGreaterEqual(eff, S.REF_MIN_FS,
                                        f"{f.name} 出处行缩到 {eff:.1f} 号 < {S.REF_MIN_FS}：{seg[:24]}…")
                worst, n = min(worst, eff), n + 1
            band = S.VGroup(*S._ref_texts(
                [f"{r.get('source', '')} {r.get('locator', '')}".strip() for r in plan.get("refs", [])],
                S.THEMES["clean"]["dim"])).arrange(S.DOWN, aligned_edge=S.LEFT, buff=0.08)
            self.assertLessEqual(band.width, S.REF_WIDE + 1e-6, f"{f.name} 出处行整块越安全宽")
        self.assertGreaterEqual(n, 20, "语料太少，这条断言等于没测")
        self.assertGreaterEqual(worst, 16.0, f"全库最差的出处行字号只剩 {worst:.1f} 号，比 v7 修好的那批还小")

    def test_ref_line_renders_ir_markup_as_real_scripts(self):
        """出处里的 `_x` 下标标记必须排成真下标，不能把标记本身画上屏（第四轮 F-11 / 评审 A D8、B D-05）。

        v7 的匀变速那条出处是「…（v_t = v_0 + a t）」，出处行走裸 T() 而正文走 rich()，
        于是同一屏上公式是 vₜ、出处是 v_t——学生读成两种东西，还把 IR 的字段名泄露了出去。
        """
        text = "人教版高中物理必修第一册 第二章 第2节 匀变速直线运动的速度与时间的关系（v_t = v_0 + a t）"
        for ln in S._ref_texts([text], S.GREY_A):
            for leaf in ln.get_family():
                if isinstance(leaf, S.Text):
                    self.assertNotIn("_", leaf.text, f"出处行把 IR 标记原样画上屏：{leaf.text}")

    def test_wrap_keeps_bracketed_formula_intact(self):
        # v7 的真实数据：括号里是公式与页码，断在这里等于把公式劈成两半。
        text = ("人教版高中物理必修第一册 第二章 第2节 匀变速直线运动的速度与时间的关系"
                "（v_t = v_0 + a t）普通高中物理课程标准 内容要求 1.1.3：通过实验，"
                "探究匀变速直线运动的特点，能用公式、图像等方法描述匀变速直线运动")
        for seg in S._wrap_ref(text):
            self.assertEqual(seg.count("（"), seg.count("）"), f"括号被折行劈开：{seg}")
            self.assertEqual(seg.count("("), seg.count(")"), f"括号被折行劈开：{seg}")
            self.assertNotIn("_", seg[:2], f"行首是公式尾巴：{seg}")


if __name__ == "__main__":
    unittest.main()
