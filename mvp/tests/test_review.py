"""A4 静态监督闸门测试（红线 4）：每条检查各造一个必然命中的用例。

同时锁两条元规则：
  · 干净数据（真实 acceleration 库）必须 0 findings —— 闸门不许误伤；
  · 闸门只打回不改写（Spec_Workflow 第 1 节：A4 不能改写内容）。
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import knowledge, review, storyboard  # noqa: E402
from pipeline.ir import BUDGET_REF_KIND, Plan, SHOT_HEAD, SHOT_TAIL  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _util  # noqa: E402

ACCEL = knowledge.load("physics", "加速度")


def rushed_chars(mult: float, window: float) -> int:
    """把"这一镜讲得多赶"表达成**自然语速的倍数**，反推口播字数。

    语速尺子（ir.NATURAL_CPS）跟着配音引擎标定，写死字面字数的测试在换引擎后会整批失效
    （SubTask #60-A 换网关 TTS 时就撞过一次）；按倍数写，档位语义与尺子同源。
    """
    return int(round(review.NATURAL_CPS * mult * window))


def balanced(n: int = 5, each: float = 12.0) -> list[dict]:
    """每 shot 时长均衡、口播为空、出处齐全 —— 在此基线上加一项才应命中一项。"""
    return [_util.shot_dict(index=i, seconds=each, narration="") for i in range(n)]


def target_of(shots: list[dict]) -> int:
    return int(round(sum(s["seconds"] for s in shots)))


class TestCleanBaseline(unittest.TestCase):
    def test_real_acceleration_plan_yields_zero_findings(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        # 红线是"没有阻断级发现"。记账级发现（BUDGET_TIGHT）按设计就该存在：这条 458 字讲不进 120s。
        self.assertEqual(review.blocking(review.check(plan, ACCEL)), [])

    def test_clean_plan_without_kp_argument(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        self.assertEqual(review.blocking(review.check(plan)), [])

    def test_constructed_baseline_is_quiet(self):
        shots = balanced()
        self.assertEqual(review.check(_util.plan_of(shots, target_seconds=target_of(shots))), [])

    def test_finding_shape_is_structured(self):
        shots = balanced()
        shots[1]["kp_refs"] = []
        f = review.check(_util.plan_of(shots, target_seconds=target_of(shots)))[0]
        self.assertEqual(set(f.keys()), {"shot", "code", "msg"})
        self.assertEqual(f["shot"], 1)
        self.assertEqual(f["code"], "NO_REF")
        self.assertTrue(f["msg"])


class TestGateCodes(unittest.TestCase):
    def run_case(self, mutate, kp=None, n=5, each=12.0, target=None):
        shots = balanced(n=n, each=each)
        mutate(shots)
        target = target if target is not None else target_of(shots)
        return review.check(_util.plan_of(shots, target_seconds=target), kp)

    # ① 字数/秒 超载
    def test_overload_hits(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "narration", "速" * int(review.FAST_CPS * (12 - SHOT_HEAD - SHOT_TAIL) + 10)))
        self.assertEqual(_util.codes_of(f), {"OVERLOAD"})
        self.assertIn("字每秒", f[0]["msg"])

    def test_overload_boundary_is_the_speakable_window(self):
        """12s 镜头扣掉头尾两段静音才是可说窗口：边界按窗口算，不按整镜算。"""
        window = 12 - SHOT_HEAD - SHOT_TAIL
        at_limit = self.run_case(lambda s: s[0].__setitem__("narration", "速" * int(review.FAST_CPS * window)))
        self.assertEqual(at_limit, [])
        over = self.run_case(lambda s: s[0].__setitem__("narration", "速" * (int(review.FAST_CPS * window) + 1)))
        self.assertEqual(_util.codes_of(over), {"OVERLOAD"})

    def test_pacing_hits_when_the_whole_film_would_be_rushed(self):
        """单镜都不超载，但总量压不进目标时长：成片会被 TTS 提速到赶课，这是内容层缺陷。"""
        # 5 镜 × 12s，可说窗 10.85s/镜；整片需要 1.35× 自然语速（PACING 判据 ≈1.244×）
        chars = rushed_chars(1.35, 12 - SHOT_HEAD - SHOT_TAIL)
        f = self.run_case(lambda s: [sh.__setitem__("narration", "速" * chars) for sh in s])
        codes = _util.codes_of(f)
        self.assertIn("PACING", codes)
        if review.SPEED_LADDER:
            self.assertEqual(codes, {"PACING"}, "有提速档时整片赶课应只命中 PACING")
        else:
            # 没有档可提时，天花板就是自然语速本身，"整片赶课"必然同时表现为逐镜超载，两码同报才对。
            self.assertIn("OVERLOAD", codes)

    def test_pacing_silent_at_natural_pace(self):
        f = self.run_case(lambda s: [sh.__setitem__("narration", "速" * 30) for sh in s])
        self.assertEqual(f, [])

    def test_pacing_message_offers_only_actionable_advice(self):
        """消息里的建议必须是执行得了的：有提速档时给"+2 档过线最小值"与"自然语速"两个数；
        没有档时不许出现"提档"字样，只给"精简到 N 字 / 放宽到 ≥Ns"两条真能做的路。"""
        chars = rushed_chars(1.35, 12 - SHOT_HEAD - SHOT_TAIL)
        f = self.run_case(lambda s: [sh.__setitem__("narration", "速" * chars) for sh in s])
        msg = next(x["msg"] for x in f if x["code"] == "PACING")
        self.assertIn("字每秒", msg)
        if review.SPEED_LADDER:
            self.assertIn("过线最小值", msg)
            self.assertIn("（自然语速）", msg)
            floor, relaxed = (int(x) for x in re.findall(r"[≥~](\d+)s", msg))
            self.assertLess(floor, relaxed, "自然语速需要的时长必须比 +2 档过线最小值更长")
        else:
            self.assertNotIn("档", msg, "配音没有提速档时不能给提档建议")
            self.assertIn("只有一个语速", msg)
            self.assertIn("精简到", msg)
            self.assertTrue(re.findall(r"放宽到 ≥\d+s", msg), "必须给出放宽到的秒数")

    # ② 字幕安全区 / 版面高度
    def test_safe_area_hits(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "graph_vt", "props": {"points": [[0, 0], [1, 1]]}} for _ in range(2)]))
        self.assertEqual(_util.codes_of(f), {"SAFE_AREA"})
        self.assertEqual(f[0]["shot"], 0)

    def test_safe_area_usable_height_is_frame_minus_two_bands(self):
        self.assertAlmostEqual(review.USABLE_H,
                               review.FRAME_H - review.SUBTITLE_BAND - review.HEADER_BAND, places=6)

    def test_visual_height_model_matches_kind_rules(self):
        def h(visuals):
            shot = _util.shot_dict(index=0, seconds=20, narration="", visuals=visuals)
            return review._visual_height(Plan.from_dict({
                "knowledge_id": "kp.t", "refs": [],
                "brief": _util.ok_brief().__dict__, "shots": [shot]}).shots[0])

        self.assertAlmostEqual(h([{"kind": "title", "props": {}}]), 1.6, places=6)
        self.assertAlmostEqual(h([{"kind": "formula", "props": {"expr": "a=Δv/Δt"}}]), 1.2, places=6)
        self.assertAlmostEqual(h([{"kind": "formula", "props": {"expr": "a", "note": "单位"}}]), 1.6, places=6)
        self.assertAlmostEqual(h([{"kind": "callout", "props": {}}]), 0.8, places=6)
        self.assertAlmostEqual(h([{"kind": "graph_vt", "props": {"points": [[0, 0], [1, 1]]}}]), 3.6, places=6)
        self.assertAlmostEqual(h([{"kind": "steps", "props": {"lines": ["1"] * 3}}]), 0.8 + 1.65, places=6)
        self.assertAlmostEqual(h([{"kind": "summary", "props": {"points": ["1"] * 4}}]), 0.8 + 2.2, places=6)
        self.assertAlmostEqual(
            h([{"kind": "compare", "props": {"left": {"items": ["a"]}, "right": {"items": ["b", "c"]}}}]),
            1.0 + 0.5 * 2, places=6)

    # ③ 版式原语参数
    def test_kind_hits_on_unknown_primitive(self):
        f = self.run_case(lambda s: s[0].__setitem__("visuals", [{"kind": "hologram", "props": {}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})
        self.assertIn("未知版式原语", f[0]["msg"])

    def test_kind_hits_on_formula_without_expr(self):
        f = self.run_case(lambda s: s[0].__setitem__("visuals", [{"kind": "formula", "props": {"expr": "  "}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})
        self.assertIn("expr", f[0]["msg"])

    def test_kind_hits_on_graph_vt_with_one_point(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "graph_vt", "props": {"points": [[0, 0]]}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})

    def test_kind_hits_on_steps_with_seven_lines(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "steps", "props": {"lines": [f"第{i}步" for i in range(7)]}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})
        self.assertIn("6 条", f[0]["msg"])

    def test_kind_hits_on_summary_with_seven_points(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "summary", "props": {"points": [f"要点{i}" for i in range(7)]}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})

    def test_six_items_is_allowed(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "steps", "props": {"lines": [f"第{i}步" for i in range(6)]}}]))
        self.assertEqual(f, [])

    # ④ 时长分配
    def test_dur_share_hits(self):
        shots = [{"index": 0, "title": "一镜到底", "seconds": 40.0, "narration": "",
                  "emphasis": "", "kp_refs": ["出处"], "visuals": []},
                 *[balanced()[i] for i in range(4)]]
        # 40 + 12*4 = 88 → 40/88 = 45% > 25%
        findings = review.check(_util.plan_of(shots, target_seconds=88))
        self.assertEqual(_util.codes_of(findings), {"DUR_SHARE"})
        self.assertEqual(findings[0]["shot"], 0)

    def test_dur_share_boundary_exactly_25_percent_passes(self):
        # 4 个等长镜头，每个恰好 25%（严格大于才命中）
        f = self.run_case(lambda s: s, n=4, each=15.0)
        self.assertEqual(f, [])

    def test_dur_share_hits_just_above_25_percent(self):
        f = self.run_case(lambda s: s[0].__setitem__("seconds", 16.0), n=4, each=15.0)
        self.assertEqual(_util.codes_of(f), {"DUR_SHARE"})

    def test_dur_short_hits(self):
        f = self.run_case(lambda s: s[0].__setitem__("seconds", 3.9))
        self.assertEqual(_util.codes_of(f), {"DUR_SHORT"})
        self.assertIn("4.0", f[0]["msg"])

    # ⑤ 出处 / 术语
    def test_no_ref_hits(self):
        f = self.run_case(lambda s: s[0].__setitem__("kp_refs", []))
        self.assertEqual(_util.codes_of(f), {"NO_REF"})

    def test_no_ref_hits_when_refs_missing_from_dict(self):
        shots = balanced()
        shots[2].pop("kp_refs")
        self.assertEqual(_util.codes_of(review.check(_util.plan_of(shots, target_seconds=60))), {"NO_REF"})

    def test_term_hits_on_forbidden_word(self):
        kp = dict(ACCEL, forbidden=["速度就是加速度"], must_say=[])
        f = self.run_case(lambda s: s[1].__setitem__("narration", "别忘了：速度就是加速度。"), kp=kp)
        self.assertEqual(_util.codes_of(f), {"TERM"})
        self.assertEqual(f[0]["shot"], 1)
        self.assertIn("速度就是加速度", f[0]["msg"])

    def test_forbidden_word_in_real_library_terms_is_caught(self):
        f = self.run_case(lambda s: s[0].__setitem__("narration", ACCEL["forbidden"][1]),
                          kp=dict(ACCEL, must_say=[]))
        self.assertEqual(_util.codes_of(f), {"TERM"})

    # ⑥ 定义性限定：条目声明"必须说出口的那几句"，一句都没说就打回
    def test_missing_qualifier_hits_once_per_unsaid_phrase(self):
        """合成口播只说了第一句，第二句必须单独打回，且报出的是缺的那句。"""
        f = self.run_case(lambda s: s[0].__setitem__("narration", "加速度是速度的变化率"),
                          kp=dict(ACCEL, must_say=["速度的变化率", "而不是与速度同向"]))
        self.assertEqual(_util.codes_of(f), {"MISSING_QUALIFIER"})
        self.assertEqual([x["shot"] for x in f], [-1])
        self.assertIn("而不是与速度同向", f[0]["msg"])

    def test_qualifier_matches_ignore_whitespace(self):
        """口播排版会在短语中间留下空格或换行，匹配按去空白原文，不能因此误报。"""
        f = self.run_case(lambda s: s[0].__setitem__("narration", "加速度是 速度\n的变化率"),
                          kp=dict(ACCEL, must_say=["速度的变化率"]))
        self.assertEqual(f, [])

    def test_no_term_finding_when_kp_omitted(self):
        f = self.run_case(lambda s: s[0].__setitem__("narration", "速度就是加速度。"))
        self.assertEqual(f, [])

    # ⑥ 总时长目标
    def test_target_hits_when_total_deviates_over_10_percent(self):
        f = self.run_case(lambda s: s, target=80)  # 60 vs 80 → 25%
        self.assertEqual(_util.codes_of(f), {"TARGET"})
        self.assertEqual(f[0]["shot"], -1)

    def test_target_boundary_10_percent_passes(self):
        # 60s 实际 vs 55s 目标 → 9.09%
        f = self.run_case(lambda s: s, target=55)
        self.assertEqual(f, [])

    def test_zero_target_is_a_finding_not_a_free_pass(self):
        """口径改过：这里曾断言"target=0 就跳过时长检查、返回 0 findings"，
        而 C16 复评审计指出那等于给脏 brief 开免检通道（TARGET 与 PACING 双双静默失效）。
        目标时长不可用时必须显式打回，由人先修 Brief。"""
        f = self.run_case(lambda s: s, target=0)
        self.assertEqual(_util.codes_of(f), {"TARGET"})
        self.assertIn("无法判定", f[0]["msg"])


class TestGateIsReadOnly(unittest.TestCase):
    """A4 只打回、不改写。"""

    def test_check_does_not_mutate_plan(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        before = plan.to_dict()
        review.check(plan, ACCEL)
        self.assertEqual(plan.to_dict(), before)

    def test_check_does_not_mutate_knowledge(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        before = json.dumps(ACCEL, ensure_ascii=False, sort_keys=True)
        review.check(plan, copy.deepcopy(ACCEL))
        self.assertEqual(json.dumps(ACCEL, ensure_ascii=False, sort_keys=True), before)

    def test_empty_plan_is_not_a_crash(self):
        plan = _util.plan_of([], target_seconds=120)
        codes = _util.codes_of(review.check(plan, ACCEL))
        # 空片既偏目标时长，又是一句限定都没说出口——两条都该报，但都不能崩
        self.assertEqual(codes, {"TARGET", "MISSING_QUALIFIER"})

    def test_findings_are_ordered_by_shot_index(self):
        shots = balanced()
        shots[3]["kp_refs"] = []
        shots[0]["narration"] = "速" * 200
        f = review.check(_util.plan_of(shots, target_seconds=60))
        self.assertEqual([x["shot"] for x in f], sorted(x["shot"] for x in f))
        self.assertEqual(_util.codes_of(f), {"OVERLOAD", "NO_REF"})


class TestGateInputResilience(unittest.TestCase):
    def run_case_static(self, mutate):
        shots = balanced()
        mutate(shots)
        return review.check(_util.plan_of(shots, target_seconds=target_of(shots)))

    def test_formula_with_none_expr_should_report_not_crash(self):
        """已修（C14）：A3 是 LLM 产出，props 里 expr: null 完全可能出现；
        当时 review.py 裸用 .strip()/len(None) 会崩，现在归一化后按 KIND 打回。"""
        f = self.run_case_static(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "formula", "props": {"expr": None}}]))
        self.assertEqual(_util.codes_of(f), {"KIND"})

    def test_narration_non_string_should_report_not_crash(self):
        """已修（C14）：narration 为 None 时闸门曾直接 TypeError，现在走 _text 归一化。"""
        f = self.run_case_static(lambda s: s[0].__setitem__("narration", None))
        self.assertIsInstance(f, list)

    def test_non_numeric_seconds_should_report_not_crash(self):
        """C16 复评审计的 P0：seconds 是 None / "8" / True 时 check 在**第一行**读
        plan.total_seconds 就崩，一条闸门都没跑完。归一化现在住在 ir.num，
        数值层（total_seconds、Shot.subtitles）与闸门共用一把尺子。"""
        for bad in (None, "8", True):
            with self.subTest(seconds=bad):
                shots = balanced()                      # 目标时长按干净基线算，别跟着一起变脏
                bad_shot = shots[1]
                bad_shot["seconds"] = bad
                f = review.check(_util.plan_of(shots, target_seconds=target_of(balanced())))
                self.assertIn("DUR_SHORT", _util.codes_of(f), f"seconds={bad!r} 该打回，不该崩")

    def test_zero_target_seconds_hits_instead_of_bypassing_gates(self):
        """target_seconds=0 曾同时旁路 TARGET 与 PACING（`if tgt:` 静默跳过）→ 必须显式打回。"""
        shots = balanced()
        codes = _util.codes_of(review.check(_util.plan_of(shots, target_seconds=0)))
        self.assertIn("TARGET", codes)


class TestGateCoverageC14AndLegible(unittest.TestCase):
    """C14 扩充的三条闸门 + 本轮新增 LEGIBLE：每条都要有"必然命中"的用例（红线 4）。"""

    def run_case(self, mutate, n=5, each=12.0, **brief_over):
        shots = balanced(n=n, each=each)
        mutate(shots)
        return review.check(_util.plan_of(shots, target_seconds=target_of(shots), **brief_over))

    def test_axis_label_hits_for_non_physics_graph(self):
        """数学片不写轴名就会套用物理的 t/s、v/(m·s⁻¹)（批量 D3，一票否决级）。"""
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "graph_vt", "props": {"points": [[-1, -1], [0, 1], [1, 3]]}}]),
            subject="math")
        self.assertIn("AXIS_LABEL", _util.codes_of(f))

    def test_axis_label_silent_for_physics(self):
        """物理片不写轴名是合法的：v-t 就是这套图的默认轴名，闸门不能反过来把物理片也拦死。"""
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "graph_vt", "props": {"points": [[0, 0], [1, 1]]}}]))
        self.assertNotIn("AXIS_LABEL", _util.codes_of(f))

    def test_axis_label_passes_when_labels_given(self):
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "graph_vt", "props": {"points": [[0, 1], [1, 3]],
                                                       "x_label": "x", "y_label": "y"}}]))
        self.assertNotIn("AXIS_LABEL", _util.codes_of(f))

    def test_count_hits_when_title_promises_more_items(self):
        f = self.run_case(lambda s: (
            s[0].__setitem__("title", "三个最容易混的概念"),
            s[0].__setitem__("visuals", [{"kind": "steps", "props": {"lines": ["其一", "其二"]}}])))
        self.assertIn("COUNT", _util.codes_of(f))

    def test_sub_width_is_wired(self):
        """SUB_WIDTH 是纵深防御：正常切句折行不会产出超宽字幕，所以这里把上限临时压低，
        证明"一旦真的超宽，闸门确实拦得住"，而不是让它静默空转。"""
        saved = review.MAX_CAP_UNITS
        try:
            review.MAX_CAP_UNITS = 2.0
            f = self.run_case(lambda s: s[0].__setitem__("narration", "这是一句明显超过两个字的旁白。"))
            self.assertIn("SUB_WIDTH", _util.codes_of(f))
        finally:
            review.MAX_CAP_UNITS = saved

    def test_legible_hits_on_unbreakable_long_callout(self):
        """先修条实测：60 字挤一行，字号掉到 18px，投影读不见（batch_v4 评审）。"""
        long_one = "这是一条没有分隔符的超长结论文字用来验证可读性闸门确实会拦住它而不是默默把字号缩到看不见为止"
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "callout", "props": {"text": long_one}}]))
        self.assertIn("LEGIBLE", _util.codes_of(f))
        self.assertIn("18px", f[0]["msg"])

    def test_legible_passes_when_split_by_separator(self):
        """渲染层会按「 · 」断行；断完之后每条都够大，闸门就该放行（与 _v_callout 同规则）。"""
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "callout", "props": {
                "text": "先修：a = Δv / Δt 与匀变速的含义 · v-t 图像的读法与斜率 · 以直代曲的极限思想"}}]))
        self.assertNotIn("LEGIBLE", _util.codes_of(f))

    def test_legible_hits_on_overlong_ref_line(self):
        """第四轮 F-1：出处行走的是另一条排版路径，当时完全没有闸门，8 条 review.json 全为 []。

        渲染层折两行是上限，折完仍超安全宽就要缩字号；缩到 REF_MIN_FS 以下必须被拦下来改文案，
        而不是让它在投影上变成一片灰点（v7 的椭圆 12px / 匀变速 14px 就是这么命中 G3 的）。
        """
        monster = "测试教材出处" * 30
        f = self.run_case(lambda s: s[-1].__setitem__("kp_refs", [monster]))
        self.assertIn("LEGIBLE", _util.codes_of(f))

    def test_legible_passes_for_real_batch_v7_citations(self):
        """v7 真实数据必须放行：椭圆那条 116 字课标引用当年被缩到 12px，现在折两行后仍 ≥ 下限。"""
        real = ("普通高中数学课程标准（2017年版2020年修订） 选择性必修主题二 2.平面解析几何（3）"
                "圆锥曲线与方程 ②：经历从具体情境中抽象出椭圆的过程，"
                "掌握椭圆的定义、标准方程及简单几何性质（课标 PDF 第 52 页，正文第 44 页）")
        f = self.run_case(lambda s: s[-1].__setitem__("kp_refs", [real]))
        self.assertNotIn("LEGIBLE", _util.codes_of(f))


class TestQualifierLossAndOnScreenTerms(unittest.TestCase):
    """第四轮 F-3：摘要把限定词压没了，而闸门只查口播、不查屏上文字。"""

    def run_case(self, mutate, n=5, each=12.0, kp=None, **brief_over):
        shots = balanced(n=n, each=each)
        mutate(shots)
        return review.check(_util.plan_of(shots, target_seconds=target_of(shots), **brief_over), kp)

    def test_hit_when_summary_drops_the_qualifier_prefix(self):
        """v7 真实形状：emphasis 写「氧化型浓度升高，电极电势增大」，摘要只留后半截。"""
        f = self.run_case(lambda s: (
            s[1].__setitem__("emphasis", "氧化型浓度升高，电极电势增大"),
            s[-1].__setitem__("visuals", [{"kind": "summary", "props": {
                "points": ["界面形成双电层，产生电势差", "浓度升高，电极电势增大"]}}])))
        self.assertIn("QUALIFIER_LOSS", _util.codes_of(f))
        self.assertIn("氧化型", f[0]["msg"])

    def test_no_hit_when_the_dropped_prefix_is_a_formula(self):
        """摘要丢掉公式前缀是正常压缩（v7 语料里的加速度条就是这形状），不许误伤。"""
        f = self.run_case(lambda s: (
            s[1].__setitem__("emphasis", "a = Δv / Δt，矢量，方向沿Δv"),
            s[-1].__setitem__("visuals", [{"kind": "summary", "props": {
                "points": ["矢量，方向沿Δv"]}}])))
        self.assertNotIn("QUALIFIER_LOSS", _util.codes_of(f))

    def test_forbidden_term_now_covers_screen_text(self):
        """TERM 原来只查 narration：同一句错话写在屏上就漏过去了。"""
        f = self.run_case(lambda s: s[0].__setitem__(
            "visuals", [{"kind": "callout", "props": {"text": "电动势就是电极电势"}}]),
            kp=dict(ACCEL, forbidden=["电动势就是电极电势"], must_say=[]))
        self.assertEqual(_util.codes_of(f), {"TERM"})


class TestBudgetStateBeforeNarration(unittest.TestCase):
    """闸门必须跑在配音**之前**（C19 ③）。

    A6 用实测语音时长反写每镜 seconds，只在反写之后检查等于拿"已经被提速抹平"的账去验收——
    batch_v6 就是这样"全绿"却有 6/8 条靠 +1/+2 档过关（C18 更正一）。这条测试锁的是顺序，
    所以把 _synthesize 换成一个"被调用就炸"的替身：绿了才证明超标文本真的没走到配音。
    """

    def bloated(self):
        """每镜 336 字：120s 的总预算无论怎么分配秒数都超 FAST_CPS，与分镜的分配策略无关。"""
        kp = copy.deepcopy(ACCEL)
        for s in kp["sequence"]:
            s["narration"] = "这一段口播在预算态下明显讲不进这一镜" * 24
        return kp

    def test_generate_rejects_before_any_audio_work(self):
        import unittest.mock
        import run

        reached = []
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "budget_gate"

            def no_narration(*a, **k):
                reached.append("synthesize")
                raise AssertionError("预算态闸门没拦住，已经跑到配音")

            with unittest.mock.patch.object(run.knowledge, "load", return_value=self.bloated()), \
                 unittest.mock.patch.object(run, "_synthesize", no_narration):
                with self.assertRaises(RuntimeError) as ctx:
                    run.generate(_util.ok_brief(target_seconds=120), out_dir, quality="draft")

            self.assertEqual(reached, [], "超预算的文本不该走到配音")
            self.assertIn("预算态", str(ctx.exception))
            self.assertFalse((out_dir / "audio").exists(), "配音目录都不该被创建")
            artifact = json.loads((out_dir / "review.json").read_text(encoding="utf-8"))
            findings = artifact["violations"]
            self.assertEqual(sorted(artifact["checked"]), sorted(review.CODES),
                             "交付件要写明跑过哪些码（第四轮 F-8：[] 不能再同时表示「全绿」和「没跑」）")
            self.assertTrue({"OVERLOAD", "PACING"} <= {f["code"] for f in findings},
                            f"该报超字与整片节奏，实际 {[f['code'] for f in findings]}")

    def test_codes_registry_matches_the_emitted_codes(self):
        """CODES 是交付契约：加了检查忘登记、或登记了却没人发，都要被测出来。"""
        src = (Path(__file__).resolve().parents[1] / "pipeline" / "review.py").read_text(encoding="utf-8")
        emitted = set(re.findall(r'add\([^,]+,\s*"([A-Z_]+)"', src))
        self.assertEqual(emitted, set(review.CODES),
                         f"源码里发出的码与登记清单不一致：只在源码 {sorted(emitted - set(review.CODES))} / "
                         f"只在清单 {sorted(set(review.CODES) - emitted)}")

    def test_gate_is_what_stops_it_positive_control(self):
        """反向对照：把闸门本身摘掉，同一个替身必须被调用到。
        没有这条，上面那条可能只是"generate 在别处提前抛了个 RuntimeError"而在空转。"""
        import unittest.mock
        import run

        reached = []

        def no_narration(*a, **k):
            reached.append("synthesize")
            raise AssertionError("闸门被摘掉后确实走到了配音（本条为预期）")

        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(run.knowledge, "load", return_value=self.bloated()), \
                 unittest.mock.patch.object(run.review, "check", lambda *a, **k: []), \
                 unittest.mock.patch.object(run, "_synthesize", no_narration):
                with self.assertRaises(AssertionError):
                    run.generate(_util.ok_brief(target_seconds=120), Path(td) / "control",
                                 quality="draft")
            self.assertEqual(reached, ["synthesize"])


class TestContentCoverageGates(unittest.TestCase):
    """C15/C16 遗留三维里最后两维：图形原语配额（阻断）与预算账（记账）。"""

    def test_no_figure_hits_when_the_whole_film_is_text_only(self):
        """勾股讲弦图却一行字到底（batch_v4 U1=2）——这类片子从此出不了门。"""
        shots = balanced()
        for s in shots:
            s["visuals"] = [{"kind": "callout", "props": {"text": "提示"}}]
        f = review.check(_util.plan_of(shots, target_seconds=target_of(shots)))
        self.assertIn("NO_FIGURE", _util.codes_of(f))

    def test_no_figure_silent_when_one_shot_has_a_graph(self):
        shots = balanced()
        shots[2]["visuals"] = [{"kind": "graph_vt", "props": {"points": [[0, 0], [1, 1]]}}]
        f = review.check(_util.plan_of(shots, target_seconds=target_of(shots)))
        self.assertNotIn("NO_FIGURE", _util.codes_of(f))

    def test_new_graphic_kinds_satisfy_the_figure_quota(self):
        shots = balanced()
        shots[2]["visuals"] = [{"kind": "particle_box", "props": {"state": "both", "n": 10}}]
        f = review.check(_util.plan_of(shots, target_seconds=target_of(shots)))
        self.assertNotIn("NO_FIGURE", _util.codes_of(f))

    def test_new_kinds_with_bad_props_hit_kind(self):
        bad = [("axis_graph", {"curves": [], "x_label": "x", "y_label": "y"}),
               ("particle_box", {"state": "mid"}),
               ("microstate", {"cells": 3, "particles": 5}),
               ("energy_dist", {"levels": [0]}),
               ("stat_chart", {"type": "radar", "data": [1]}),
               ("mind_map", {"root": "熵", "branches": []}),
               ("table", {"headers": ["a"], "rows": []})]
        for kind, props in bad:
            with self.subTest(kind=kind):
                shots = balanced()
                shots[2]["visuals"] = [{"kind": kind, "props": props}]
                f = review.check(_util.plan_of(shots, target_seconds=target_of(shots)))
                self.assertIn("KIND", _util.codes_of(f))

    def test_no_figure_does_not_judge_an_empty_plan(self):
        """空 Plan 不是"一部没图的片子"，它还没分镜；该由 TARGET 那类码去喊，别混进内容闸。"""
        self.assertNotIn("NO_FIGURE", _util.codes_of(review.check(_util.plan_of([]))))

    def paced_plan(self, chars_per_shot: int, n_shots: int = 6, each: float = 12.5):
        """纯构造的整片：语速完全由 chars_per_shot 控制，不依赖语料库当前写了多少字
        （用真实条目做断言会被并行改稿漂移打断，batch_v7 就踩过一次）。"""
        shots = [_util.shot_dict(index=i, seconds=each, narration="字" * chars_per_shot)
                 for i in range(n_shots)]
        return _util.plan_of(shots, target_seconds=int(round(n_shots * each)))

    def with_account(self, plan, **over):
        """把 A3 账本挂/改到 plan.refs 上：就地改，闸门读的是第一条同 kind 的账本。"""
        acct = storyboard.budget_of(plan)
        if acct is None:
            acct = {"kind": BUDGET_REF_KIND}
            plan.refs.append(acct)
        acct.update({"source": "A3 分镜预算", "locator": "target=75s",
                     "narration_chars": 282, "natural_seconds": 77.4,
                     "budgeted_seconds": plan.total_seconds, "fits_natural": False,
                     "min_seconds_for_natural": 78})
        acct.update(over)
        return acct

    def test_budget_tight_is_advisory_not_blocking(self):
        """装不下又只超一档：这句话要说给老师听，但不拦出片（+1 档仍是讲课，不是赶课）。"""
        plan = self.paced_plan(rushed_chars(1.06, 12.5 - SHOT_HEAD - SHOT_TAIL))  # 略快于自然语速 → +1 档
        acct = self.with_account(plan)
        f = review.check(plan)
        soft = [x for x in f if x["code"] == "BUDGET_TIGHT"]
        self.assertEqual(len(soft), 1)
        self.assertIs(soft[0]["blocking"], False)
        self.assertEqual(review.blocking(f), [], "记账级发现不该拦出片")
        self.assertIn("+1 档" if review.SPEED_LADDER else "没有提速档", soft[0]["msg"])
        self.assertIn(f"{acct['min_seconds_for_natural']}s", soft[0]["msg"])

    def test_budget_tight_silent_when_a3_says_it_fits(self):
        """装不装得下以 A3 的账为准：点名段是固定开销、不进正片预算，
        而 A4 的全片平均语速把它算进去了 —— 账本说装得下时 A4 不该喊（batch_v7 实测：匀变速）。"""
        plan = self.paced_plan(rushed_chars(1.06, 12.5 - SHOT_HEAD - SHOT_TAIL))
        self.with_account(plan, fits_natural=True)
        self.assertNotIn("BUDGET_TIGHT", _util.codes_of(review.check(plan)))

    def test_budget_tight_silent_when_no_boost_is_needed(self):
        """A4 自己算出 +0 档时也不能喊：那条消息会说"靠提速到 +0 档讲完"，是自相矛盾的假话。"""
        plan = self.paced_plan(rushed_chars(0.6, 12.5 - SHOT_HEAD - SHOT_TAIL))  # 慢于自然语速，绰绰有余
        self.with_account(plan)
        self.assertNotIn("BUDGET_TIGHT", _util.codes_of(review.check(plan)))

    def test_budget_tight_silent_above_the_acceptable_rate(self):
        """>+2 档由 PACING 阻断打回，同一条片子不该再收到一句轻描淡写的记账。"""
        plan = self.paced_plan(rushed_chars(1.35, 12.5 - SHOT_HEAD - SHOT_TAIL))  # 1.35× 自然语速 → +3 档
        self.with_account(plan)
        codes = _util.codes_of(review.check(plan))
        self.assertNotIn("BUDGET_TIGHT", codes)
        self.assertIn("PACING", codes)

    def test_budget_tight_silences_itself_after_a6_rewrote_seconds(self):
        """A6 用实测配音反写秒数之后，成片总长已不等于分镜预算，这句「压进 75s」就不再成立。"""
        plan = self.paced_plan(rushed_chars(1.06, 12.5 - SHOT_HEAD - SHOT_TAIL))
        self.with_account(plan)
        self.assertIn("BUDGET_TIGHT", _util.codes_of(review.check(plan)))
        plan.shots[0].seconds += 10.0
        self.assertNotIn("BUDGET_TIGHT", _util.codes_of(review.check(plan)))

    def test_blocking_treats_unmarked_findings_as_blocking(self):
        """缺 blocking 键的旧形状发现默认阻断——闸门新增的记账级出口必须是显式的。"""
        legacy = {"shot": -1, "code": "WHATEVER", "msg": "m"}
        self.assertEqual(review.blocking([legacy]), [legacy])
        self.assertEqual(review.blocking([{**legacy, "blocking": False}]), [])


class TestSpokenWindowAfterAlignment(unittest.TestCase):
    """A6 反写：镜头秒数取分镜预算与实测语音的**较大值**，字幕只铺在有声音的那一段。

    batch_v7 首跑炸在这里：口播比目标薄时，实测时长把整片拉到 106/108s（目标 120s），
    ±10% 闸门把一条讲得从容的片子判成"放不下"，报错还写着"放宽到 ≥72s"。
    """

    def synthesize_with(self, plan, cps: float, floors):
        """用"实测比预算薄"的假配音走一遍 A6：每条口播按 cps 字/秒出声。

        cps 取 4.5（比自然语速快）是有意的：分镜预算按 3.9 字/秒铺满了 120s，实测就会每镜都短
        一截，正好检验那截余量是留在镜头末尾当留白，还是被抹掉变成"整片比目标短"。
        """
        import unittest.mock

        import run
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(
                    run.tts, "synth",
                    side_effect=lambda text, wav, audio_dir, rate=0: round(len(text) / cps, 2)):
                run._synthesize(plan, Path(td), 0, floors)

    def test_thin_content_still_lands_near_target_without_freezing_one_shot(self):
        """F-4 之后：每镜缺口各自封顶在 MAX_SHOT_IDLE，没缺口的镜头一秒都不多给，
        封顶后仍摊不下的那部分还给总时长（不再堆在一镜冻屏，也不再凑单镜没有的缺口）。

        这条夹具（physics/加速度）镜0 缺口为零、其余六镜缺口超过 MAX_SHOT_IDLE=1.5s 的那部分
        被截掉，所以总时长**不再**精确回到 120.0（那是旧版"整块堆给单镜"才能凑出的数字）；
        它该落在 TARGET 闸门的 ±10% 带内且不阻断。
        """
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        floors = [s.seconds for s in plan.shots]
        self.synthesize_with(plan, 4.5, floors)
        self.assertAlmostEqual(plan.total_seconds, 113.86, places=1,
                               msg="封顶后的总时长漂了：检查 MAX_SHOT_IDLE 或 _spread_surplus 是否改动")
        self.assertLessEqual(abs(plan.total_seconds - 120.0) / 120.0, 0.10,
                             "封顶后仍不能越过 TARGET 闸门的 ±10% 带")
        self.assertEqual(review.blocking(review.check(plan, ACCEL)), [])

    def test_cues_stop_at_the_audio_not_at_the_padded_shot(self):
        """镜头被拉长时字幕窗口仍按语音时长算，否则越到镜末字幕拖得越后（音画同轴红线）。"""
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        floors = [s.seconds for s in plan.shots]
        self.synthesize_with(plan, 4.5, floors)
        padded = [s for s in plan.shots if s.spoken < s.seconds]
        self.assertGreaterEqual(len(padded), 4, "这条用例得真的留下留白才有意义")
        for s in padded:
            self.assertAlmostEqual(s.speak_window, s.spoken - SHOT_HEAD - SHOT_TAIL, places=2)
            cues = s.subtitles()
            self.assertLessEqual(cues[-1]["end"], s.spoken - SHOT_TAIL + 0.01)

    def test_without_floors_alignment_still_collapses_to_measured(self):
        """不传 floors 时 A6 的行为不变：秒数就是实测语音——提速那一遍靠的就是它会缩。"""
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        self.synthesize_with(plan, 4.5, None)
        self.assertLess(plan.total_seconds, 115.0)


class TestSubOverlapGate(unittest.TestCase):
    """SubTask #60-C：相邻字幕 cue 重叠必须被拦下（手改 plan.json / 脏 IR 的形状）。

    Shot.subtitles() 正常铺排逐条相接、不会重叠，所以这里把镜头的方法换成脏 IR 里
    可能出现的重叠时间轴，证明闸门真的拦得住，而不是静默空转。
    """

    def run_case(self, cues, n=5, each=12.0):
        shots = balanced(n=n, each=each)
        plan = _util.plan_of(shots, target_seconds=target_of(shots))
        plan.shots[0].subtitles = lambda: cues
        return review.check(plan)

    def test_overlapping_cues_hit(self):
        cues = [
            {"i": 0, "start": 0.45, "end": 5.0, "text": "第一条字幕的内容"},
            {"i": 1, "start": 4.0, "end": 8.0, "text": "第二条字幕的内容"},
            {"i": 2, "start": 8.0, "end": 11.3, "text": "第三条字幕的内容"},
        ]
        f = self.run_case(cues)
        self.assertEqual(_util.codes_of(f), {"SUB_OVERLAP"})
        msg = f[0]["msg"]
        self.assertIn("字幕 0 与 1 重叠", msg)
        self.assertIn("0.45–5.00 与 4.00–8.00", msg)
        self.assertIn("第一条字幕的内容", msg)
        self.assertIn("请缩短口播或放宽镜头时长", msg)

    def test_adjacent_and_gapped_cues_do_not_hit(self):
        """恰好相接（end == start）与留有空隙都不判重叠：0.01s 容差只吸收浮点噪声。"""
        cues = [
            {"i": 0, "start": 0.45, "end": 4.0, "text": "第一条字幕的内容"},
            {"i": 1, "start": 4.0, "end": 8.0, "text": "第二条字幕的内容"},
            {"i": 2, "start": 8.5, "end": 11.3, "text": "第三条字幕的内容"},
        ]
        self.assertEqual(self.run_case(cues), [])

    def test_sub_overlap_is_registered_in_codes_contract(self):
        """F-8 契约：新码必须进 CODES（checked 清单与源码 add() 双向对撞都靠它）。"""
        self.assertIn("SUB_OVERLAP", review.CODES)


if __name__ == "__main__":
    unittest.main()
