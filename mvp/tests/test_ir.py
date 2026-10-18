"""IR 层契约测试：Brief 校验 / Shot 字幕切句 / Plan 往返与 hash。

对应 Spec_Product.txt 第 2/3/4 节。纯标准库 unittest（本机无 pytest，约定不装包）。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.ir import (  # noqa: E402
    MAX_CAP_UNITS,
    MAX_SECONDS,
    MIN_CAP_UNITS,
    MIN_CUE_SECONDS,
    MIN_SECONDS,
    SHOT_HEAD,
    SHOT_TAIL,
    SUBJECTS,
    VISUAL_KINDS,
    Brief,
    Plan,
    Shot,
    Visual,
    cap_width,
    cue_w,
    split_narration,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _util  # noqa: E402


def sample_shot(seconds: float = 12.0, narration: str = "第一句，第二句。第三句！") -> Shot:
    return Shot(index=0, title="镜头", seconds=seconds, narration=narration,
                visuals=[Visual("callout", {"text": "要点"})], kp_refs=["src 1.3"])


class TestBriefValidate(unittest.TestCase):
    """红线 1：非法 Brief 必须被 validate() 挡住，合法组合必须放行。"""

    def test_default_brief_is_valid(self):
        self.assertEqual(_util.ok_brief().validate(), [])

    def test_boundary_seconds_are_valid(self):
        for t in (MIN_SECONDS, 30, 120, 600):
            self.assertEqual(_util.ok_brief(target_seconds=t).validate(), [], f"target={t} 应合法")

    def test_seconds_below_min_rejected(self):
        for t in (0, 1, 29, -120):
            errs = _util.ok_brief(target_seconds=t).validate()
            self.assertTrue(any("target_seconds" in e for e in errs), f"target={t} 必须报错：{errs}")

    def test_seconds_above_max_rejected(self):
        for t in (601, 1200):
            errs = _util.ok_brief(target_seconds=t).validate()
            self.assertTrue(any("target_seconds" in e for e in errs), f"target={t} 必须报错：{errs}")

    def test_bad_subject_rejected(self):
        for s in ("english", "MATH", "", "  "):
            errs = _util.ok_brief(subject=s).validate()
            self.assertTrue(any("subject" in e for e in errs), f"subject={s!r} 必须报错：{errs}")

    def test_both_legal_subjects_pass(self):
        for s in SUBJECTS:
            self.assertEqual(_util.ok_brief(subject=s).validate(), [])

    def test_bad_grade_rejected(self):
        for g in ("G7", "G12", "初一", ""):
            errs = _util.ok_brief(grade=g).validate()
            self.assertTrue(any("grade" in e for e in errs), f"grade={g!r} 必须报错：{errs}")

    def test_all_legal_grades_pass(self):
        for g in ("G8", "G9", "H1", "H2"):
            self.assertEqual(_util.ok_brief(grade=g).validate(), [])

    def test_bad_style_rejected(self):
        for st in ("cute", "clean2", ""):
            errs = _util.ok_brief(style=st).validate()
            self.assertTrue(any("style" in e for e in errs), f"style={st!r} 必须报错：{errs}")

    def test_both_legal_styles_pass(self):
        for st in ("clean", "board"):
            self.assertEqual(_util.ok_brief(style=st).validate(), [])

    def test_empty_topic_rejected(self):
        for t in ("", "   ", "\t"):
            errs = _util.ok_brief(topic=t).validate()
            self.assertTrue(any("topic" in e for e in errs), f"topic={t!r} 必须报错：{errs}")

    def test_resolution_below_1080p_rejected(self):
        for r in ("1280x720", "854x480", "1920x720", "1280x1080", "1920x1079"):
            errs = _util.ok_brief(resolution=r).validate()
            self.assertTrue(any("resolution" in e for e in errs), f"resolution={r} 必须报错：{errs}")

    def test_legal_resolutions_pass(self):
        for r in ("1920x1080", "2560x1440", "3840x2160"):
            self.assertEqual(_util.ok_brief(resolution=r).validate(), [])

    def test_malformed_resolution_rejected(self):
        for r in ("1080p", "1920", "1920x", "x1080", "abcd", ""):
            errs = _util.ok_brief(resolution=r).validate()
            self.assertTrue(any("resolution" in e for e in errs), f"resolution={r!r} 必须报错：{errs}")

    def test_multiple_violations_reported_together(self):
        errs = Brief(subject="bio", grade="G7", topic="", style="neo",
                     target_seconds=10, resolution="640x360").validate()
        self.assertGreaterEqual(len(errs), 6)

    def test_non_int_target_seconds_should_be_normalized_not_crash(self):
        """pipeline/ir.py Brief.__post_init__ / validate()：
        target_seconds 为字符串（表单/JSON 常见形态）时不得抛 TypeError；
        纯数字归一化为合法，非数字返回错误清单条目。"""
        self.assertEqual(_util.ok_brief(target_seconds="120").validate(), [])  # 表单字符串归一化为合法
        errs = _util.ok_brief(target_seconds="abc").validate()
        self.assertTrue(any("target_seconds" in e for e in errs))               # 非数字要报错，不能抛


class TestShotSubtitles(unittest.TestCase):
    """红线 5：字幕切句。

    口径说明（2026-10 渲染层改造后）：一条字幕的宽度上限由 ir.MAX_CAP_UNITS 定义
    （汉字记 1、拉丁/数字记 0.5），镜头内时间窗口是 [SHOT_HEAD, seconds-SHOT_TAIL]，
    与配音轨的起点（mux.build_track 同样用 SHOT_HEAD）对齐。
    """

    def test_shot_head_matches_audio_lead_in(self):
        self.assertEqual(SHOT_HEAD, 0.45)

    def test_no_chunk_exceeds_width_cap(self):
        narr = ("飞机在跑道上缓慢加速，速度每秒只增加几米每秒；摩托车起步时，速度一秒就能涨好几米每秒。"
                "我们用一个物理量来刻画这种差别，它就是加速度。" + "无标点的超长连写正文" * 3)
        for sec in (8.0, 12.0, 13.5, 22.5):
            for c in sample_shot(seconds=sec, narration=narr).subtitles():
                self.assertLessEqual(cap_width(c["text"]), MAX_CAP_UNITS + 2,
                                     f"{c['text']!r} 宽度超上限，会折行出安全区")

    def test_pure_chinese_chunk_never_exceeds_20_chars(self):
        narr = "速度与加速度没有必然的大小关系，看的是变化的快慢而不是快慢本身。" * 2
        for c in sample_shot(seconds=30.0, narration=narr).subtitles():
            self.assertLessEqual(len(c["text"]), 20)

    def test_never_cuts_inside_a_token(self):
        """术语 / 数值单位（m/s²、v-t）不得被拦腰截断。"""
        subs = sample_shot(seconds=30.0, narration="加速度 a = 2 m/s² 表示速度每秒增加两米。").subtitles()
        self.assertTrue(any("m/s²" in c["text"] for c in subs), [c["text"] for c in subs])
        chunks = split_narration("E=mc222222222222222222222abcdefghijk 是质能方程")
        self.assertTrue(any("mc222222222222222222222abcdefghijk" in c for c in chunks), chunks)

    def test_timestamps_monotonic_and_contiguous(self):
        narr = "加速度等于速度变化量，除以发生这一变化所用时间，单位是米每二次方秒。"
        subs = sample_shot(seconds=13.5, narration=narr).subtitles()
        self.assertGreater(len(subs), 1)
        for i, c in enumerate(subs):
            self.assertEqual(c["i"], i)
            self.assertLess(c["start"], c["end"])
            if i:
                self.assertGreaterEqual(c["start"], subs[i - 1]["start"])
                self.assertAlmostEqual(c["start"], subs[i - 1]["end"], places=2)

    def test_cues_stay_inside_the_shot_window(self):
        for sec in (4.0, 12.0, 13.5, 18.0, 21.0, 22.5):
            subs = sample_shot(seconds=sec).subtitles()
            self.assertEqual(subs[0]["start"], SHOT_HEAD)
            self.assertLessEqual(subs[-1]["end"], sec)

    def test_last_end_is_shot_seconds_minus_tail(self):
        """当前口径：末条止于 seconds - SHOT_TAIL（留淡出静音）。"""
        for sec in (4.0, 12.0, 13.5, 18.0, 19.5, 21.0, 22.5, 6.1, 7.77):
            subs = sample_shot(seconds=sec).subtitles()
            self.assertAlmostEqual(subs[-1]["end"], sec - SHOT_TAIL, places=6,
                                   msg=f"seconds={sec}")

    def test_empty_narration_returns_empty_list(self):
        self.assertEqual(sample_shot(narration="").subtitles(), [])

    def test_punctuation_only_narration_should_yield_no_cue(self):
        """BUG（记录用，不改源码）：pipeline/ir.py:64
        `[c.rstrip("，、：") for c in merged if c]` 先过滤再裁剪，
        narration 为「，、」这类纯标点时产出一条 text 为空串的字幕，
        write_srt 会写出没有文本的空 cue（人工/LLM 改 plan.json 很容易踩到）。"""
        self.assertEqual(sample_shot(narration="，、").subtitles(), [])
        self.assertEqual(sample_shot(narration="  ，、 ").subtitles(), [])

    def test_short_shot_does_not_crash(self):
        for sec in (0.0, 0.5, 1.0, 2.0):
            subs = sample_shot(seconds=sec, narration="一，二。").subtitles()
            self.assertTrue(subs)
            self.assertLessEqual(subs[0]["start"], subs[-1]["end"])

    def test_trailing_punctuation_stripped(self):
        subs = sample_shot(seconds=12.0, narration="只有一句，").subtitles()
        self.assertEqual([c["text"] for c in subs], ["只有一句"])

    def test_time_share_is_weighted_not_uniform(self):
        """长短句按朗读宽度分配时间：长句占更多时间。

        两句都足量（>= MIN_CAP_UNITS），否则短句会先被合并规则吃掉（见下一条测试）。
        """
        subs = sample_shot(seconds=20.0, narration="短句也够长，这是很长的一句话用来占时间。").subtitles()
        self.assertEqual(len(subs), 2)
        d0 = subs[0]["end"] - subs[0]["start"]
        d1 = subs[1]["end"] - subs[1]["start"]
        self.assertGreater(d1, d0)

    def test_fragment_merges_forward_instead_of_flashing(self):
        """两个字的碎片只分到 0.3s，屏幕上是一闪而过的字（评审 N4）：宁可与下一条合成一条。"""
        chunks = split_narration("注意，图线越陡加速度越大。")
        self.assertEqual(chunks, ["注意，图线越陡加速度越大。"])
        self.assertTrue(all(cue_w(c) >= MIN_CAP_UNITS for c in chunks))

    def test_long_list_rebalances_instead_of_leaving_a_tail(self):
        """『…3、4、5 和 5、12、13。』折到装不下会留下『13。』这种 2 字尾巴；要平切。"""
        narr = "常见的正整数组合有 3、4、5 和 5、12、13。"
        chunks = split_narration(narr)
        self.assertTrue(all(MIN_CAP_UNITS <= cue_w(c) <= MAX_CAP_UNITS + 2 for c in chunks), chunks)
        keep = lambda s: "".join(x for x in s if x.isalnum() or "一" <= x <= "鿿")
        self.assertEqual(keep("".join(chunks)), keep(narr))   # 平切不能丢字

    def test_no_cue_is_too_short_to_read(self):
        """镜头再挤也不该出现 1 秒以下的字幕：并得进就并，并不了就把相邻两条平切重排。"""
        narr = ("正着用，知角求边；反着用，知边验角。记住两条：只在直角三角形里 a² + b² = c²，"
                "c 是斜边；常见的正整数组合有 3、4、5 和 5、12、13。")
        subs = sample_shot(seconds=12.8, narration=narr).subtitles()
        self.assertTrue(all(c["end"] - c["start"] >= MIN_CUE_SECONDS for c in subs),
                        [(round(c["end"] - c["start"], 2), c["text"]) for c in subs])
        self.assertTrue(all(cue_w(c["text"]) <= MAX_CAP_UNITS + 2 for c in subs),
                        [c["text"] for c in subs])


class TestPlanRoundTrip(unittest.TestCase):
    """红线 7：to_dict / from_dict 保真 + hash 稳定与敏感。"""

    def setUp(self):
        from pipeline import storyboard
        from pipeline import knowledge

        self.kp = knowledge.load("physics", "加速度")
        self.plan = storyboard.build(_util.ok_brief(target_seconds=120), self.kp)

    def test_dict_round_trip_is_lossless(self):
        d = self.plan.to_dict()
        again = Plan.from_dict(d)
        self.assertEqual(again.to_dict(), d)
        self.assertEqual(again.total_seconds, self.plan.total_seconds)
        self.assertEqual(again.knowledge_id, self.plan.knowledge_id)
        self.assertEqual(again.refs, self.plan.refs)
        self.assertEqual(len(again.shots), len(self.plan.shots))

    def test_round_trip_preserves_subtitles_and_kp_refs(self):
        d = self.plan.to_dict()
        again = Plan.from_dict(d)
        for src, dst in zip(self.plan.shots, again.shots):
            self.assertEqual(dst.subtitles(), src.subtitles())
            self.assertEqual(dst.kp_refs, src.kp_refs)
            self.assertEqual([v.kind for v in dst.visuals], [v.kind for v in src.visuals])
            self.assertEqual([v.props for v in dst.visuals], [v.props for v in src.visuals])
            self.assertEqual(dst.index, src.index)
            self.assertEqual(dst.seconds, src.seconds)
            self.assertEqual(dst.narration, src.narration)
            self.assertEqual(dst.title, src.title)
            self.assertEqual(dst.emphasis, src.emphasis)

    def test_save_load_file_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "plan.json"
            self.plan.save(p)
            loaded = Plan.load(p)
            self.assertEqual(loaded.to_dict(), self.plan.to_dict())
            self.assertEqual(loaded.hash, self.plan.hash)
            # 文件必须是 UTF-8 中文可读
            self.assertIn("加速度", p.read_text(encoding="utf-8"))

    def test_total_seconds_is_sum_of_shots(self):
        self.assertAlmostEqual(self.plan.total_seconds,
                               round(sum(s.seconds for s in self.plan.shots), 2), places=2)

    def test_hash_is_stable_for_same_content(self):
        self.assertEqual(self.plan.hash, self.plan.hash)
        self.assertEqual(self.plan.hash, Plan.from_dict(self.plan.to_dict()).hash)
        self.assertEqual(len(self.plan.hash), 8)
        self.assertTrue(all(c in "0123456789abcdef" for c in self.plan.hash))

    def test_hash_ignores_derived_subtitle_field(self):
        d_no = self.plan.to_dict(include_subtitles=False)
        d_yes = self.plan.to_dict(include_subtitles=True)
        self.assertNotIn("subtitles", d_no["shots"][0])
        self.assertIn("subtitles", d_yes["shots"][0])
        # 字幕是派生字段：同一内容的两种导出必须得到同一个 hash
        self.assertEqual(Plan.from_dict(d_yes).hash, Plan.from_dict(d_no).hash)

    def test_hash_changes_when_content_changes(self):
        base = self.plan.hash
        for mutate in (
            lambda p: setattr(p.shots[0], "narration", p.shots[0].narration + "补充一句。"),
            lambda p: setattr(p.shots[1], "seconds", p.shots[1].seconds + 0.5),
            lambda p: p.shots[2].kp_refs.append("新增出处"),
            lambda p: p.shots[3].visuals.append(Visual("callout", {"text": "x"})),
            lambda p: setattr(p.shots[4], "emphasis", "改了强调点"),
            lambda p: setattr(p, "knowledge_id", p.knowledge_id + ".v2"),
            lambda p: setattr(p.brief, "style", "board"),
            lambda p: setattr(p.brief, "target_seconds", p.brief.target_seconds + 10),
        ):
            clone = Plan.from_dict(self.plan.to_dict())
            mutate(clone)
            self.assertNotEqual(clone.hash, base, "改动后 hash 必须变（P2 回归可比对）")

    def test_from_dict_tolerates_unknown_brief_fields(self):
        d = self.plan.to_dict()
        d["brief"]["operator_note"] = "人工批注"
        again = Plan.from_dict(d)
        self.assertEqual(again.brief.subject, "physics")

    def test_from_dict_defaults_missing_optional_fields(self):
        d = self.plan.to_dict()
        for s in d["shots"]:
            s.pop("kp_refs", None)
            s.pop("emphasis", None)
            for v in s["visuals"]:
                v.pop("props", None)
        d.pop("refs", None)
        again = Plan.from_dict(d)
        self.assertEqual(again.refs, [])
        self.assertTrue(all(s.kp_refs == [] for s in again.shots))
        self.assertTrue(all(s.emphasis == "" for s in again.shots))
        self.assertTrue(all(v.props == {} for s in again.shots for v in s.visuals))

    def test_plan_dict_should_carry_hash_and_version(self):
        """BUG（记录用，不改源码）：pipeline/ir.py:174 to_dict()
        Spec_Product 第 3 节要求 plan JSON "带 version 与 hash"，当前 to_dict() 两者都没有
        （hash 只存在 property 里，version 字段全项目缺失）。"""
        d = self.plan.to_dict()
        self.assertIn("hash", d)
        self.assertIn("version", d)

    def test_brief_should_carry_spec_fields(self):
        """BUG（记录用，不改源码）：pipeline/ir.py:93 Brief
        Spec_Product 第 2 节把 subtitles(bool, 不可关) 与 language(enum {zh}) 列为输入契约字段，
        Brief 里完全没有，web 层无法透传/校验。"""
        fields = set(Brief.__dataclass_fields__)
        self.assertIn("subtitles", fields)
        self.assertIn("language", fields)


class TestVisualKindContract(unittest.TestCase):
    def test_fifteen_primitives_only(self):
        # figure 是批量评审 D8 补的；后七个是 #48 的图形化版式。改动这里必须同步 Spec_MVP 的 A5 清单与 A3 提示词。
        self.assertEqual(set(VISUAL_KINDS),
                         {"title", "formula", "compare", "graph_vt", "figure", "steps", "summary", "callout",
                          "axis_graph", "particle_box", "microstate", "energy_dist", "stat_chart", "mind_map", "table"})

    def test_constants_match_spec(self):
        self.assertEqual((MIN_SECONDS, MAX_SECONDS), (30, 600))


if __name__ == "__main__":
    unittest.main()
