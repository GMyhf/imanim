"""#48 新增七种图形化版式：每种用样例 props 能建出对象，且落在安全宽/带内。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "render"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scene as S  # noqa: E402

EX = S.Explainer()
TH = S.THEMES["clean"]

SAMPLES = {
    "axis_graph": {"curves": [{"points": [[0, 0], [1, 1], [2, 4]], "label": "y=x²"}],
                   "marks": [{"xy": [1, 1], "label": "A"}], "x_label": "x", "y_label": "y"},
    "particle_box": {"state": "both", "n": 12, "before_label": "前", "after_label": "后"},
    "microstate": {"cells": 4, "particles": 2, "label": "微观态"},
    "energy_dist": {"levels": [0, 1, 2, 3], "kT": [0.5, 2.0], "n": 20},
    "stat_chart": {"type": "bar", "data": [{"label": "a", "value": 3}, {"label": "b", "value": 5}, {"label": "c", "value": 2}], "x_label": "类", "y_label": "数"},
    "mind_map": {"root": "熵", "branches": [{"h": "宏观", "children": ["热量", "温度"]},
                                           {"h": "微观", "children": ["微观态数 W"]}]},
    "table": {"headers": ["量", "符号"], "rows": [["熵", "S"], ["焓", "H"]]},
}


class TestNewKinds(unittest.TestCase):
    def test_every_new_kind_builds_within_safe_width(self):
        for kind, props in SAMPLES.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, EX.BUILDERS)
                obj = getattr(EX, EX.BUILDERS[kind])(props, TH)
                self.assertGreater(obj.width, 0.5)
                self.assertGreater(obj.height, 0.5)

    def test_stat_chart_types(self):
        for t, data in (("hist", [{"label": "1", "value": 1}, {"label": "2", "value": 3}]), ("pie", [{"label": "a", "value": 1}, {"label": "b", "value": 2}]),
                        ("scatter", [[0, 1], [1, 2], [2, 2.5]])):
            with self.subTest(type=t):
                self.assertGreater(EX._v_stat_chart({"type": t, "data": data}, TH).width, 0.5)


if __name__ == "__main__":
    unittest.main()
