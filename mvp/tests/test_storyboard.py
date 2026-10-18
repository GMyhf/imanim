"""A3 分镜测试（红线 3）：文本量驱动的秒数分配 / 先修镜头 / kp_refs 非空 / 可复现 / 预算账本。

不测 scene.py，不测渲染；这里只锁 Plan 这一层的确定性行为。
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import knowledge, review, storyboard  # noqa: E402
from pipeline.ir import (FAST_CPS, MIN_SHOT_SECONDS, NATURAL_CPS, SHOT_HEAD, SHOT_TAIL,  # noqa: E402
                         VISUAL_KINDS, Plan, naming_narration, naming_shot_seconds)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _util  # noqa: E402

ACCEL = knowledge.load("physics", "加速度")
_WINDOW = SHOT_HEAD + SHOT_TAIL


def _kp_copy(kp: dict) -> dict:
    return json.loads(json.dumps(kp, ensure_ascii=False))


def _short_kp(texts: list[str], template_seconds: list[float]) -> dict:
    """造一条口径可控的知识点：口播长度与模板秒数故意不成比例（旧算法就在这儿翻车）。"""
    kp = _kp_copy(ACCEL)
    kp["prior"] = []
    kp["sequence"] = kp["sequence"][:len(texts)]
    for blk, t, s in zip(kp["sequence"], texts, template_seconds):
        blk["narration"] = t
        blk["seconds"] = s
    return kp


def _cps(shot) -> float:
    return len(shot.narration) / max(shot.seconds - _WINDOW, 1e-6)


class TestScaling(unittest.TestCase):
    def test_total_equals_target_for_common_targets(self):
        for t in (60, 90, 120, 150, 180, 240):
            plan = storyboard.build(_util.ok_brief(target_seconds=t), ACCEL)
            self.assertAlmostEqual(plan.total_seconds, t, delta=0.05,
                                   msg=f"target={t} 时总时长应等于目标（Spec_Product 第 3 节）")
            # 厘秒分配 + 最大余额法：不靠 ±0.05 的容差兜浮点误差，而是精确等于目标
            self.assertEqual(plan.total_seconds, float(t), msg=f"target={t} 应精确落账")

    def test_longer_narration_never_gets_fewer_seconds(self):
        """① 方向性：秒数跟着口播字数走。模板说「这一镜 5s」也不能把 99 字压成 5s。"""
        texts = ["讲" * 99, "讲" * 60, "讲" * 37]
        kp = _short_kp(texts, [20.0, 10.0, 5.0])   # 模板权重与文本量反着写
        for target in (120, 40):                  # 120=有富余（走权重），40=装不下（走等比压缩）
            plan = storyboard.build(_util.ok_brief(target_seconds=target, prior_knowledge=False), kp)
            secs = [s.seconds for s in plan.shots]
            self.assertEqual(secs, sorted(secs, reverse=True), f"target={target} 时长应随口播字数递减：{secs}")

    def test_compressed_film_shares_one_pace_across_shots(self):
        """讲不进的整片：每镜同一语速，不许出现「这镜 5.7 字/秒、下镜 2.3 字/秒 干等」。"""
        texts = ["讲" * 99, "讲" * 60, "讲" * 37]
        kp = _short_kp(texts, [20.0, 10.0, 5.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=40, prior_knowledge=False), kp)
        rates = [_cps(s) for s in plan.shots]
        self.assertLess(max(rates) - min(rates), 0.1, f"压缩后各镜语速应收敛到同一档：{rates}")
        # 旧算法在同一份文本上的极差（模板秒数说了算）：长口播镜要 5.7 字/秒，短口播镜 2.3 字/秒干等
        self.assertGreater(_cps(plan.shots[0]), NATURAL_CPS)

    def test_slack_follows_template_seconds_as_weight_only(self):
        """文本量相同、模板秒数不同时，多出来的时间按模板秒数当相对权重分（模板只剩权重权）。"""
        kp = _short_kp(["讲" * 40, "讲" * 40, "讲" * 40], [20.0, 10.0, 5.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=120, prior_knowledge=False), kp)
        secs = [s.seconds for s in plan.shots]
        self.assertEqual(secs, sorted(secs, reverse=True), secs)
        for s in plan.shots:                      # 富余预算也不许把任何一镜压到自然需要以下
            self.assertGreaterEqual(s.seconds, len(s.narration) / NATURAL_CPS + _WINDOW - 0.01)

    def test_no_shot_exceeds_fast_cps_ceiling_when_budget_allows(self):
        """单镜上限由 FAST_CPS 兜：预算够得着目标时，等比压缩后的镜速不得越过最快可接受语速。"""
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        for s in plan.shots:
            self.assertLessEqual(_cps(s), FAST_CPS, f"shot {s.index} 预算态已超 FAST_CPS")

    def test_prior_shot_is_budgeted_from_its_own_text(self):
        """点名段曾经写死 8s：四条长标签就成了 9 字/秒，闸门判它说不完。"""
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        s0 = plan.shots[0]
        self.assertEqual(s0.title, "先修：需要什么基础")
        # 秒数 = 文本按 NAME_CPS 念完的可说窗 + 头尾留白，且与 ir 给 prereq 用的那把尺子同一个函数。
        # 旧口径少留这 1.15s，点名段实际被推到 4.9~5.0 字/秒，比这条常数自己声明的 4.5 还快。
        self.assertEqual(s0.seconds, naming_shot_seconds(s0.narration))
        window = s0.seconds - SHOT_HEAD - SHOT_TAIL
        self.assertLessEqual(len(s0.narration) / window, review.FAST_CPS)

    def test_prior_shot_never_eats_more_than_its_share(self):
        """标签再多再长，点名段也只能占 NAME_MAX_SHARE，多出来的由闸门报 OVERLOAD 而不是吞掉正片。"""
        kp = _kp_copy(ACCEL)
        kp["prior"] = ["一条特别长的先修标签" * 5 for _ in range(6)]
        plan = storyboard.build(_util.ok_brief(target_seconds=120), kp)
        self.assertLessEqual(plan.shots[0].seconds, 120 * storyboard.NAME_MAX_SHARE + 0.01)
        # 正片拿剩下的钱，且仍然按字数分：不许被点名段的余量喂给某一只镜
        body = plan.shots[1:]
        self.assertAlmostEqual(sum(s.seconds for s in body), 120 - plan.shots[0].seconds, places=2)
        order = sorted(range(len(body)), key=lambda i: -len(body[i].narration))
        self.assertEqual(order, sorted(order, key=lambda i: -body[i].seconds))

    def test_short_targets_get_clamped_to_floor_not_zero(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=30, prior_knowledge=False), ACCEL)
        for s in plan.shots:
            self.assertGreaterEqual(s.seconds, MIN_SHOT_SECONDS)
        # 夹底下限后总时长只能接近目标，不该炸到天际
        self.assertLessEqual(abs(plan.total_seconds - 30) / 30, 0.10 + 1e-9)

    def test_prereq_and_storyboard_price_the_same_naming_shot(self):
        """点名段有两个东家：A3 的片头与 Spec_PreqChain 的前置链。

        同一段标签在两处算出不同秒数 = 同一支片子的两份账打架（batch_v7 复核 §3 就是这个），
        所以这里直接把两边的数字对齐，而不只是对齐它们各自的说法。
        """
        from pipeline import prereq

        labels = ACCEL["prior"]
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        self.assertEqual(plan.shots[0].narration, naming_narration(labels))
        self.assertEqual(plan.shots[0].seconds, prereq._name_seconds(labels))

    def test_empty_narration_still_gets_a_legal_shot(self):
        """脏文本（空口播）不能让分配器除零，也不能产出 0 秒镜头。"""
        kp = _short_kp(["", "讲的什么", "一个字"], [10.0, 10.0, 10.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=60, prior_knowledge=False), kp)
        for s in plan.shots:
            self.assertGreaterEqual(s.seconds, MIN_SHOT_SECONDS)
        self.assertAlmostEqual(plan.total_seconds, 60, delta=0.05)

    def test_no_shot_exceeds_share_at_default_target(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        for s in plan.shots:
            self.assertLessEqual(s.seconds / plan.total_seconds, review.MAX_SHOT_SHARE)

    def test_index_is_sequential_from_zero(self):
        plan = storyboard.build(_util.ok_brief(), ACCEL)
        self.assertEqual([s.index for s in plan.shots], list(range(len(plan.shots))))

    def test_shot_count_within_spec_range(self):
        """Spec_Workflow A3：4~10 个 shot。"""
        plan = storyboard.build(_util.ok_brief(), ACCEL)
        self.assertTrue(4 <= len(plan.shots) <= 10, len(plan.shots))


class TestPriorShot(unittest.TestCase):
    def test_prior_present_adds_one_lead_shot(self):
        self.assertTrue(ACCEL.get("prior"))
        on = storyboard.build(_util.ok_brief(), ACCEL)
        off = storyboard.build(_util.ok_brief(prior_knowledge=False), ACCEL)
        self.assertEqual(len(on.shots), len(off.shots) + 1)
        self.assertIn("先修", on.shots[0].title)
        self.assertEqual(on.shots[0].emphasis, "先修知识")
        self.assertEqual([v.kind for v in on.shots[0].visuals], ["callout"])
        for item in ACCEL["prior"]:
            self.assertIn(item, on.shots[0].visuals[0].props["text"])
        # 其余镜头与关闭先修时同序
        self.assertEqual([s.title for s in on.shots[1:]], [s.title for s in off.shots])

    def test_flag_off_does_not_emit_prior_shot(self):
        plan = storyboard.build(_util.ok_brief(prior_knowledge=False), ACCEL)
        self.assertFalse(any("先修" in s.title for s in plan.shots))

    def test_kp_without_prior_ignores_flag(self):
        kp = dict(ACCEL, prior=[])
        for flag in (True, False):
            plan = storyboard.build(_util.ok_brief(prior_knowledge=flag), kp)
            self.assertEqual(len(plan.shots), len(kp["sequence"]))
            self.assertFalse(any("先修" in s.title for s in plan.shots))


class TestTraceability(unittest.TestCase):
    def test_every_shot_has_non_empty_kp_refs(self):
        plan = storyboard.build(_util.ok_brief(), ACCEL)
        for s in plan.shots:
            self.assertTrue(s.kp_refs, f"shot {s.index} 无出处")
            for r in s.kp_refs:
                self.assertIsInstance(r, str)
                self.assertTrue(r.strip())

    def test_refs_are_source_and_locator_pairs(self):
        """预算账本挂在 refs 末尾，教材出处一个都不能被挤掉（片尾出处卡取 refs[0]）。"""
        plan = storyboard.build(_util.ok_brief(), ACCEL)
        expected = [f"{r['source']} {r['locator']}" for r in ACCEL["refs"]]
        self.assertEqual(plan.shots[0].kp_refs, expected)
        self.assertEqual(plan.refs[:len(ACCEL["refs"])], ACCEL["refs"])
        self.assertEqual(plan.refs[0], ACCEL["refs"][0])
        self.assertEqual(storyboard.budget_of(plan), plan.refs[-1])

    def test_block_level_kp_refs_override_default(self):
        kp = json.loads(json.dumps(ACCEL))
        kp["sequence"][0]["kp_refs"] = ["自定义出处 第 9 章"]
        plan = storyboard.build(_util.ok_brief(), kp)
        self.assertEqual(plan.shots[1].kp_refs, ["自定义出处 第 9 章"])
        self.assertEqual(plan.shots[2].kp_refs, [f"{r['source']} {r['locator']}" for r in kp["refs"]])


class TestVisualPrimitives(unittest.TestCase):
    def test_only_seven_primitives_are_emitted(self):
        for kp_id in ("physics", "math"):
            for f in sorted((knowledge.DATA_DIR / kp_id).glob("*.json")):
                kp = json.loads(f.read_text(encoding="utf-8"))
                plan = storyboard.build(_util.ok_brief(subject=kp_id), kp)
                for s in plan.shots:
                    for v in s.visuals:
                        self.assertIn(v.kind, VISUAL_KINDS, f"{kp['id']} 用了越界版式 {v.kind}")

    def test_narration_and_title_come_from_knowledge(self):
        """A3 不得引入 A2 之外的事实：MVP 模板下文本必须逐字来自 sequence。"""
        plan = storyboard.build(_util.ok_brief(prior_knowledge=False), ACCEL)
        for b, s in zip(ACCEL["sequence"], plan.shots):
            self.assertEqual(s.title, b["title"])
            self.assertEqual(s.narration, b["narration"])
            self.assertEqual(s.emphasis, b.get("emphasis", ""))


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_hash(self):
        brief = _util.ok_brief()
        a = storyboard.build(brief, ACCEL)
        b = storyboard.build(brief, knowledge.load("physics", "a=Δv/Δt"))
        self.assertEqual(a.hash, b.hash)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_same_input_same_plan_bytes(self):
        """③ 幂等：同一输入连产三次，落盘文本逐字节相同（全链路无 LLM 的卖点就押在这条上）。"""
        dumps = [json.dumps(storyboard.build(_util.ok_brief(), ACCEL).to_dict(),
                             ensure_ascii=False, indent=2) for _ in range(3)]
        self.assertEqual(len(set(dumps)), 1, "同一输入产出了不同的 plan.json")

    def test_allocation_follows_text_not_traversal_order(self):
        """③ 顺序无关：把 sequence 倒过来写，每一镜拿到的秒数只跟着自己的文本走。"""
        brief = _util.ok_brief()
        forward = storyboard.build(brief, ACCEL)
        kp_rev = _kp_copy(ACCEL)
        kp_rev["sequence"] = list(reversed(kp_rev["sequence"]))
        backward = storyboard.build(brief, kp_rev)
        self.assertEqual({s.title: s.seconds for s in forward.shots},
                         {s.title: s.seconds for s in backward.shots})

    def test_centisecond_split_leaves_no_residual(self):
        """③ 无浮点累加误差：整数厘秒 + 最大余额，尾巴恰好分完，总时长精确落到目标。"""
        for total, quotas in ((1000, [1, 1, 1]), (1000, [333, 333, 333]), (7, [1, 1]),
                              (4410, [1692, 1974, 1769, 2872, 1872, 974]), (9977, [1, 1, 1, 1, 1, 1, 1])):
            parts = storyboard._apportion(total, quotas)
            self.assertEqual(sum(parts), total, f"{quotas} 切成 {parts} 后总额不守恒")
            big = max(range(len(quotas)), key=lambda i: quotas[i])
            small = min(range(len(quotas)), key=lambda i: quotas[i])
            if quotas[big] != quotas[small]:
                self.assertGreater(parts[big], parts[small], "份额大的镜不该分到更少秒")

    def test_brief_fields_flow_into_plan(self):
        plan = storyboard.build(_util.ok_brief(style="board", target_seconds=200), ACCEL)
        self.assertEqual(plan.brief.style, "board")
        self.assertEqual(plan.brief.target_seconds, 200)
        self.assertEqual(Plan.from_dict(plan.to_dict()).brief, plan.brief)

    def test_build_does_not_mutate_knowledge_sequence(self):
        before = json.dumps(ACCEL["sequence"], ensure_ascii=False, sort_keys=True)
        storyboard.build(_util.ok_brief(), ACCEL)
        self.assertEqual(json.dumps(ACCEL["sequence"], ensure_ascii=False, sort_keys=True), before)

    def test_visual_props_should_be_copied_not_aliased(self):
        """BUG（记录用，不改源码）：pipeline/storyboard.py:42
        `Visual(v["kind"], v.get("props", {}))` 直接把 kp["sequence"] 里的 props dict 交给 Plan，
        两者共享同一对象。下游（A5 或人工改分镜）一旦改写 props，就污染了 Knowledge，
        破坏 P2「相同输入 → 相同产物」的幂等前提。"""
        plan = storyboard.build(_util.ok_brief(), ACCEL)
        src = ACCEL["sequence"][0]["visuals"][0]["props"]
        self.assertIsNot(plan.shots[1].visuals[0].props, src)


class TestBudgetAccount(unittest.TestCase):
    """②「讲不进」必须在分镜阶段可见：预算态留下一本账，不许默默把口播压成提速。"""

    def test_over_budget_film_leaves_visible_account(self):
        kp = _short_kp(["讲" * 99, "讲" * 60, "讲" * 37], [20.0, 10.0, 5.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=40, prior_knowledge=False), kp)
        account = storyboard.budget_of(plan)
        self.assertIsNotNone(account, "装不下整片时 plan 里必须有预算账本")
        self.assertFalse(account["fits_natural"])
        self.assertGreater(account["min_seconds_for_natural"], 40, "必须给出「需要 ≥N 秒」")
        self.assertAlmostEqual(account["budgeted_seconds"], plan.total_seconds, places=2)
        # 自然需要 = 每镜「字数/NATURAL_CPS + 头尾留白」之和（下限抬到 MIN_SHOT_SECONDS），跟闸门同一把尺子
        expect = sum(max(MIN_SHOT_SECONDS, len(s.narration) / NATURAL_CPS + _WINDOW) for s in plan.shots)
        self.assertAlmostEqual(account["natural_seconds"], expect, delta=0.06)

    def test_account_survives_plan_round_trip(self):
        """账本要能进 plan.json：老师改完口播重跑分镜，前端从落盘的 plan 里读得到这一条。"""
        kp = _short_kp(["讲" * 99, "讲" * 60, "讲" * 37], [20.0, 10.0, 5.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=40, prior_knowledge=False), kp)
        loaded = Plan.from_dict(plan.to_dict())
        self.assertEqual(storyboard.budget_of(loaded), storyboard.budget_of(plan))
        self.assertFalse(storyboard.budget_of(loaded)["fits_natural"])

    def test_fitting_film_is_not_flagged(self):
        """不误伤：目标时长给够时账本仍在，但 fits_natural 为真、不许喊装不下。"""
        kp = _short_kp(["讲" * 20, "讲" * 20], [10.0, 10.0])
        plan = storyboard.build(_util.ok_brief(target_seconds=120, prior_knowledge=False), kp)
        account = storyboard.budget_of(plan)
        self.assertTrue(account["fits_natural"], account)
        self.assertLessEqual(account["natural_seconds"], 120)

    def test_budget_of_returns_none_without_account(self):
        """手改/旧版 plan.json 没有账本时读成 None，不能让闸门或前端炸掉。"""
        self.assertIsNone(storyboard.budget_of(_util.plan_of([_util.shot_dict()])))
        self.assertIsNone(storyboard.budget_of({"shots": [], "refs": []}))


CONTRACT_CODES = {"OVERLOAD", "SAFE_AREA", "DUR_SHARE", "DUR_SHORT", "NO_REF", "TERM", "KIND", "TARGET",
                  "MISSING_QUALIFIER", "NO_FIGURE"}


class TestAllLibraryPassesGate(unittest.TestCase):
    """红线 4 的另一半：库内数据必须过 A4 契约项（①~⑤ + 时长）。

    GLYPH（字形/上下标记法）是后加的检查，不属于 Spec_Workflow A4 的 ①~⑤，
    这里先不并入闸门基线，另用 test_glyph_findings_are_confined_to_electrode 记录。
    """

    def findings_for(self, kp, subject, target):
        plan = storyboard.build(_util.ok_brief(subject=subject, target_seconds=target), kp)
        return review.check(plan, kp)

    def test_every_kp_passes_contract_checks(self):
        for subject in ("math", "physics", "chemistry"):
            for f in sorted((knowledge.DATA_DIR / subject).glob("*.json")):
                kp = json.loads(f.read_text(encoding="utf-8"))
                for target in (120, 150):
                    findings = self.findings_for(kp, subject, target)
                    hits = [x for x in findings if x["code"] in CONTRACT_CODES]
                    self.assertEqual(hits, [], f"{kp['id']} @ {target}s 未过闸门：{hits}")

    def test_every_kp_budget_is_text_driven_at_120s(self):
        """8 条全库逐条锁：被压缩的整片里，任何一镜都不许比全片平均语速更赶（旧算法是 2.3~5.7 字/秒）。"""
        for subject in ("math", "physics", "chemistry"):
            for f in sorted((knowledge.DATA_DIR / subject).glob("*.json")):
                kp = json.loads(f.read_text(encoding="utf-8"))
                plan = storyboard.build(_util.ok_brief(subject=subject, target_seconds=120), kp)
                account = storyboard.budget_of(plan)
                self.assertIsNotNone(account, f"{kp['id']} 没留预算账本")
                body = [s for s in plan.shots if s.title != "先修：需要什么基础"]
                if account["fits_natural"]:
                    continue  # 目标给够时不压缩，富余按模板权重分，镜速允许有差
                avg = sum(len(s.narration) for s in body) \
                    / sum(max(s.seconds - _WINDOW, 1e-6) for s in body)
                for s in body:
                    self.assertLessEqual(_cps(s), avg + 0.15,
                                         f"{kp['id']} shot {s.index} 被要求 {_cps(s):.2f} 字/秒，"
                                         f"而全片平均只要 {avg:.2f} 字/秒——还是在按模板给秒")

    def test_acceleration_at_120s_is_the_golden_case(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), ACCEL)
        findings = review.check(plan, ACCEL)
        self.assertEqual(review.blocking(findings), [])
        # 非阻断的那一条只能是"预算账"这一种记账，别把新的阻断项悄悄放进基线。
        self.assertLessEqual({f["code"] for f in findings if not f.get("blocking", True)},
                             {"BUDGET_TIGHT"})
        self.assertEqual(len(plan.shots), 7)
        # 每镜时长各自四舍五入到 2 位，加回来只能近似目标（点名段不参与缩放，见 build）
        self.assertAlmostEqual(plan.total_seconds, 120.0, delta=0.05)


class TestCorpusPhrasingAfterReview(unittest.TestCase):
    """第五轮 F-14（语料层口径，评审 A D11/D13）：两处"会被学生背下来"的说法钉成回归。

    量纲落点：加速度开场原写「速度每秒只增加几米」——米是位移的量纲，速度变化的量纲是米每秒，
    这句话在屏上读着顺、照着说就错，所以规则做成全库扫描：口播里凡是「几米」必须紧跟「每秒」。
    现行别名：勾股定理那句「也叫商高定理」删掉——现行教材只称勾股定理，「商高」是《周髀算经》
    里的典故，留在 aliases 里供检索命中可以，作为屏上/口播的现行别名断言不行。
    """

    def texts(self):
        out = []
        for subject in ("math", "physics", "chemistry"):
            for f in sorted((knowledge.DATA_DIR / subject).glob("*.json")):
                kp = json.loads(f.read_text(encoding="utf-8"))
                for shot in kp["sequence"]:
                    out.append((kp["id"], "narration", shot["narration"]))
                    out.append((kp["id"], "title", shot.get("title", "")))
        return out

    def test_metres_always_carry_per_second(self):
        bad = [(kid, field, t) for kid, field, t in self.texts()
               if "几米" in t and "几米每秒" not in t and "几米/秒" not in t]
        self.assertEqual(bad, [], f"「几米」没有落在速度量纲上：{bad}")

    def test_historical_alias_never_spoken_as_current_name(self):
        hit = [(kid, field) for kid, field, t in self.texts() if "商高" in t]
        self.assertEqual(hit, [], f"「商高定理」只许留在 aliases 里当检索入口：{hit}")


if __name__ == "__main__":
    unittest.main()
