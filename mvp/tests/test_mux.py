"""A7 合成层测试（红线 6）：build_track 拼轨 + write_srt 字幕。

只测标准库 wave 能确定的部分（采样率/时长/偏移/序号/时间戳格式），
不跑 ffmpeg（mux() 用假 subprocess 观察调用参数）。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import knowledge, mux, storyboard  # noqa: E402
from pipeline.ir import SHOT_HEAD, SHOT_TAIL, Plan, Shot  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _util  # noqa: E402

TS_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "mux"
        self.dir.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def wav(self, name: str, seconds: float, **kw) -> Path:
        p = self.dir / f"{name}.wav"
        _util.write_wav(p, seconds, **kw)
        return p


class TestBuildTrack(TmpCase):
    def test_output_format_and_duration(self):
        a, b = self.wav("a", 1.0), self.wav("b", 1.5)
        out = self.dir / "track.wav"
        ret = mux.build_track([(0.0, a), (3.0, b)], 6.0, out)
        self.assertEqual(ret, 6.0)
        self.assertTrue(out.exists())
        with wave.open(str(out), "rb") as w:
            self.assertEqual(w.getframerate(), 24000)
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 6.0, places=6)

    def test_each_clip_is_offset_by_045s_after_shot_start(self):
        a, b = self.wav("a", 1.0), self.wav("b", 1.0)
        out = self.dir / "track.wav"
        mux.build_track([(0.0, a), (3.0, b)], 6.0, out)
        spans = _util.voiced_spans(out)
        self.assertEqual(len(spans), 2)
        self.assertAlmostEqual(spans[0][0], 0.45, places=4)
        self.assertAlmostEqual(spans[0][1], 1.45, places=4)
        self.assertAlmostEqual(spans[1][0], 3.45, places=4)
        self.assertAlmostEqual(spans[1][1], 4.45, places=4)

    def test_silence_between_segments_is_preserved(self):
        a, b = self.wav("a", 1.0), self.wav("b", 1.0)
        out = self.dir / "track.wav"
        mux.build_track([(0.0, a), (3.0, b)], 6.0, out)
        with wave.open(str(out), "rb") as w:
            raw = w.readframes(w.getnframes())
        # 1.45s ~ 3.45s 之间必须是纯静音
        lo, hi = int(1.5 * 24000), int(3.4 * 24000)
        self.assertEqual(raw[2 * lo:2 * hi], b"\x00\x00" * (hi - lo))

    def test_tail_is_zero_padded_to_total_seconds(self):
        a = self.wav("a", 1.0)
        out = self.dir / "track.wav"
        mux.build_track([(0.0, a)], 4.0, out)
        spans = _util.voiced_spans(out)
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0][1], 1.45, places=4)

    def test_no_clips_yields_silent_track_of_requested_length(self):
        out = self.dir / "track.wav"
        mux.build_track([], 3.0, out)
        with wave.open(str(out), "rb") as w:
            self.assertEqual(w.getframerate(), mux.RATE)
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 3.0, places=6)
        self.assertEqual(_util.voiced_spans(out), [])

    def test_last_clip_longer_than_track_is_truncated_not_extended(self):
        a = self.wav("a", 4.0)
        out = self.dir / "track.wav"
        mux.build_track([(0.0, a)], 2.0, out)
        with wave.open(str(out), "rb") as w:
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 2.0, places=6)

    def test_creates_parent_directory(self):
        a = self.wav("a", 0.5)
        out = self.dir / "nested" / "deep" / "track.wav"
        mux.build_track([(0.0, a)], 2.0, out)
        self.assertTrue(out.exists())

    def test_sample_rate_mismatch_is_rejected(self):
        a, b = self.wav("a", 1.0), self.wav("b", 1.0, rate=22050)
        with self.assertRaises(ValueError):
            mux.build_track([(0.0, a), (3.0, b)], 6.0, self.dir / "bad.wav")

    def test_sample_rate_mismatch_is_caught_before_any_output_is_written(self):
        a, b = self.wav("a", 1.0), self.wav("b", 1.0, rate=16000)
        out = self.dir / "never.wav"
        with self.assertRaises(ValueError):
            mux.build_track([(0.0, a), (3.0, b)], 6.0, out)
        self.assertFalse(out.exists())

    def test_channel_mismatch_should_be_rejected_too(self):
        """BUG（记录用，不改源码）：pipeline/mux.py build_track() 的预检（现 mux.py:74-76）
        只比较 getframerate()，不比较 getnchannels()/getsampwidth()。
        立体声（或 8bit）片段会被当作单声道字节流塞进轨道，产生咔哒/变速的杂音且毫无报错。"""
        a, st = self.wav("a", 1.0), self.wav("st", 1.0, channels=2)
        with self.assertRaises(ValueError):
            mux.build_track([(0.0, a), (3.0, st)], 6.0, self.dir / "mix.wav")

    def test_clip_starting_beyond_total_seconds_must_be_dropped_not_appended(self):
        """BUG（记录用，不改源码）：pipeline/mux.py:81-86 build_track().put()
        `end = min(i+len(data), len(frames))` 当 i 已越界时 end < i，
        于是 `frames[i:end] = data[:end-i]` 变成「空切片 + 负数长度前缀」→ bytearray 被撑大。
        结果：输出 wav 时长 > total_seconds（实测 2.0s 请求变成 3.55s），
        而函数仍 return total_seconds，sidecar 记录的时长与实际音轨不符。"""
        a = self.wav("a", 3.0)
        out = self.dir / "over.wav"
        mux.build_track([(3.0, a)], 2.0, out)
        with wave.open(str(out), "rb") as w:
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 2.0, places=6)
        self.assertEqual(_util.voiced_spans(out), [])


class TestTimestampFormat(TmpCase):
    def test_ts_basic(self):
        self.assertEqual(mux._ts(0.0), "00:00:00,000")
        self.assertEqual(mux._ts(0.45), "00:00:00,450")
        self.assertEqual(mux._ts(61.234), "00:01:01,234")
        self.assertEqual(mux._ts(3661.5), "01:01:01,500")

    def test_ts_over_one_hour_keeps_four_digit_free_hours(self):
        self.assertEqual(mux._ts(3600.0), "01:00:00,000")
        self.assertEqual(mux._ts(7325.25), "02:02:05,250")


class TestWriteSrt(TmpCase):
    def plan_dict(self):
        return {
            "shots": [
                {"index": 0, "seconds": 10.0, "subtitles": [
                    {"i": 0, "start": 0.0, "end": 5.0, "text": "第一句"},
                    {"i": 1, "start": 5.0, "end": 10.0, "text": "第二句"}]},
                {"index": 1, "seconds": 8.0, "subtitles": [
                    {"i": 0, "start": 0.0, "end": 4.0, "text": "第三句"},
                    {"i": 1, "start": 4.0, "end": 8.0, "text": "第四句"}]},
                {"index": 2, "seconds": 6.0, "subtitles": []},
                {"index": 3, "seconds": 5.0, "subtitles": [
                    {"i": 0, "start": 0.0, "end": 5.0, "text": "第五句"}]},
            ]
        }

    def parse(self, out: Path) -> list[tuple[str, str, str]]:
        blocks = [b for b in out.read_text(encoding="utf-8").split("\n\n") if b.strip()]
        return [tuple(b.strip("\n").split("\n")) for b in blocks]

    def test_returns_count_and_numbering_is_consecutive(self):
        out = self.dir / "subs.srt"
        n = mux.write_srt(self.plan_dict(), out)
        self.assertEqual(n, 5)
        blocks = self.parse(out)
        self.assertEqual(len(blocks), n)
        self.assertEqual([b[0] for b in blocks], [str(i) for i in range(1, n + 1)])

    def test_timestamp_line_format(self):
        out = self.dir / "subs.srt"
        mux.write_srt(self.plan_dict(), out)
        for _idx, times, _text in self.parse(out):
            start, _, end = times.partition(" --> ")
            self.assertRegex(start, TS_RE)
            self.assertRegex(end, TS_RE)

    def test_offsets_accumulate_across_shots(self):
        out = self.dir / "subs.srt"
        mux.write_srt(self.plan_dict(), out)
        times = [b[1] for b in self.parse(out)]
        self.assertEqual(times[0], "00:00:00,000 --> 00:00:05,000")
        self.assertEqual(times[1], "00:00:05,000 --> 00:00:10,000")
        # 第二个镜头从 10s 起
        self.assertEqual(times[2], "00:00:10,000 --> 00:00:14,000")
        self.assertEqual(times[3], "00:00:14,000 --> 00:00:18,000")
        # 空字幕镜头只推进偏移：第五句从 10+8+6=24s 起
        self.assertEqual(times[4], "00:00:24,000 --> 00:00:29,000")

    def test_text_and_timeline_are_monotonic(self):
        out = self.dir / "subs.srt"
        mux.write_srt(self.plan_dict(), out)
        prev = ""
        for _idx, times, text in self.parse(out):
            start = times[:12]
            self.assertGreaterEqual(start, prev)
            prev = start
            self.assertTrue(text)

    def test_empty_plan_writes_empty_file_and_returns_zero(self):
        out = self.dir / "empty.srt"
        self.assertEqual(mux.write_srt({"shots": []}, out), 0)
        self.assertEqual(out.read_text(encoding="utf-8"), "")

    def test_real_plan_covers_whole_video_without_gaps(self):
        plan = storyboard.build(_util.ok_brief(target_seconds=120), knowledge.load("physics", "加速度"))
        out = self.dir / "real.srt"
        n = mux.write_srt(plan.to_dict(), out)
        self.assertEqual(n, sum(len(s.subtitles()) for s in plan.shots))
        blocks = self.parse(out)
        self.assertEqual([b[0] for b in blocks], [str(i) for i in range(1, n + 1)])
        first = blocks[0][1].split(" --> ")[0]
        last = blocks[-1][1].split(" --> ")[1]
        # 口径：字幕与配音都从镜头起点后 SHOT_HEAD 秒开始，末条止于 seconds-SHOT_TAIL
        self.assertEqual(first, mux._ts(SHOT_HEAD))
        self.assertEqual(last, mux._ts(plan.total_seconds - SHOT_TAIL))

    def test_srt_and_audio_track_share_the_same_lead_in(self):
        """字幕偏移必须与 build_track 的配音落点一致，否则整条字幕相对语音恒差 SHOT_HEAD。"""
        a = self.wav("a", 1.0)
        track = self.dir / "track.wav"
        mux.build_track([(0.0, a)], 3.0, track)
        speech_start = _util.voiced_spans(track)[0][0]
        srt = self.dir / "s.srt"
        shot = Shot(index=0, title="t", seconds=3.0, narration="这里是口播文本", visuals=[])
        mux.write_srt(Plan(brief=_util.ok_brief(), knowledge_id="kp.t", shots=[shot]).to_dict(), srt)
        first_start = self.parse(srt)[0][1].split(" --> ")[0]
        self.assertEqual(first_start, mux._ts(speech_start))
        self.assertAlmostEqual(speech_start, SHOT_HEAD, places=4)


    def test_overlapping_cues_are_trimmed_not_dropped(self):
        """手改 plan.json 绕过 review 闸门后，write_srt 兜底：前一条 end 裁到后一条 start。
        条数不变、文本顺序不变，只有时间轴被修平；输入 dict 不被改写。"""
        plan = {"shots": [{"index": 0, "seconds": 10.0, "subtitles": [
            {"i": 0, "start": 0.0, "end": 5.0, "text": "第一条"},
            {"i": 1, "start": 4.0, "end": 6.0, "text": "第二条"},
            {"i": 2, "start": 6.0, "end": 8.0, "text": "第三条"}]}]}
        out = self.dir / "overlap.srt"
        n = mux.write_srt(plan, out)
        self.assertEqual(n, 3)
        blocks = self.parse(out)
        self.assertEqual([b[2] for b in blocks], ["第一条", "第二条", "第三条"])
        self.assertEqual([b[1] for b in blocks], [
            "00:00:00,000 --> 00:00:04,000",
            "00:00:04,000 --> 00:00:06,000",
            "00:00:06,000 --> 00:00:08,000"])
        self.assertEqual(plan["shots"][0]["subtitles"][0]["end"], 5.0,
                         "兜底只修落盘那份，不许改写输入 plan dict")

    def test_unsorted_cues_are_written_in_start_order(self):
        plan = {"shots": [{"index": 0, "seconds": 10.0, "subtitles": [
            {"i": 0, "start": 6.0, "end": 8.0, "text": "后一条"},
            {"i": 1, "start": 0.0, "end": 3.0, "text": "前一条"}]}]}
        out = self.dir / "sorted.srt"
        n = mux.write_srt(plan, out)
        self.assertEqual(n, 2)
        blocks = self.parse(out)
        self.assertEqual([b[2] for b in blocks], ["前一条", "后一条"])
        self.assertEqual([b[1] for b in blocks],
                         ["00:00:00,000 --> 00:00:03,000", "00:00:06,000 --> 00:00:08,000"])


class TestMuxInvocation(TmpCase):
    """mux() 只用假 subprocess 观察参数，不真的调 ffmpeg（渲染/scene 不在本套测试范围）。"""

    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, mux, "last_burn", dict(mux.last_burn))

    def _patch(self, on_burn=None):
        calls = []

        def fake_run(cmd, *a, **kw):
            calls.append((list(cmd), kw))
            if "-vf" in cmd and on_burn is not None:
                on_burn(Path(cmd[-1]), kw.get("cwd"))
            return mock.Mock(returncode=0 if (on_burn or True) else 1, stdout="", stderr="")

        fake_bin = str(self.dir / "ffmpeg-resolved")
        which = mock.patch.object(mux.shutil, "which", lambda name: fake_bin)
        run = mock.patch.object(mux.subprocess, "run", fake_run)
        self.addCleanup(which.__exit__, None, None, None)
        self.addCleanup(run.__exit__, None, None, None)
        which.__enter__()
        run.__enter__()
        return calls, fake_bin

    def test_mux_uses_resolved_ffmpeg_binary(self):
        """回归守卫：mux() 必须走 _ffmpeg_bin()（早期版本硬编码 "ffmpeg"，
        ffmpeg 不在 PATH 上时直接 FileNotFoundError）。"""
        calls, fake_bin = self._patch()
        result = mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4", srt=None)
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], fake_bin)
        self.assertEqual(calls[0][0][0], mux._ffmpeg_bin())

    def test_mux_without_srt_runs_exactly_one_pass(self):
        calls, _ = self._patch()
        result = mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4", srt=None)
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 1)
        cmd = calls[0][0]
        self.assertIn("-c:a", cmd)
        self.assertIn("aac", cmd)
        self.assertIn("-shortest", cmd)
        self.assertNotIn("-vf", cmd, "未给 srt 就不该跑烧录第二遍")
        self.assertFalse(mux.last_burn["attempted"])

    def test_burn_pass_when_ffmpeg_produces_file(self):
        srt = self.dir / "subs.srt"
        mux.write_srt({"shots": [{"index": 0, "seconds": 3.0,
                                  "subtitles": [{"i": 0, "start": 0.45, "end": 2.3, "text": "你好"}]}]}, srt)
        seen = {}

        def on_burn(p, cwd):
            seen["cwd"] = cwd
            p.write_bytes(b"\x00fake")

        calls, fake_bin = self._patch(on_burn)
        result = mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4", srt=srt)
        self.assertEqual(len(calls), 2, "给 srt 应再跑一次烧录")
        burn_cmd = calls[1][0]
        self.assertEqual(burn_cmd[0], fake_bin)
        self.assertEqual(result, self.dir / "f_burned.mp4")
        self.assertTrue(mux.last_burn["attempted"] and mux.last_burn["ok"])
        # 烧录滤镜：字幕用相对文件名 + force_style 必须整体加引号（逗号会被当滤镜分隔符）
        vf = burn_cmd[burn_cmd.index("-vf") + 1]
        self.assertIn(f"subtitles=filename='{srt.name}'", vf)
        self.assertIn("force_style='", vf)
        self.assertEqual(seen["cwd"], str(srt.parent))
        self.assertIn("-c:v", burn_cmd)
        self.assertIn("libx264", burn_cmd)

    def test_failed_burn_is_reported_not_swallowed(self):
        srt = self.dir / "subs.srt"
        mux.write_srt({"shots": [{"index": 0, "seconds": 3.0,
                                  "subtitles": [{"i": 0, "start": 0.45, "end": 2.3, "text": "你好"}]}]}, srt)

        def fake_run(cmd, *a, **kw):
            calls.append(list(cmd))
            return mock.Mock(returncode=1, stdout="", stderr="过滤链解析错误")

        calls = []
        with mock.patch.object(mux.subprocess, "run", fake_run), \
             mock.patch.object(mux.shutil, "which", lambda name: "ffmpeg-x"):
            result = mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4", srt=srt)

        self.assertEqual(result, self.dir / "f.mp4", "烧录失败要退回未烧录版本")
        self.assertTrue(mux.last_burn["attempted"])
        self.assertFalse(mux.last_burn["ok"])
        self.assertIn("过滤链解析错误", mux.last_burn["detail"])


class TestMuxSfx(TmpCase):
    """SFX 混音（SubTask #60-E）：默认关闭必须与旧命令一致；开启走 filter_complex 多输入
    +adelay/volume/amix；混入失败降级到无音效路径、不抛错。同样只观察参数，不真调 ffmpeg。"""

    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, mux, "last_burn", dict(mux.last_burn))

    def _patch(self):
        calls = []

        def fake_run(cmd, *a, **kw):
            calls.append((list(cmd), kw))
            return mock.Mock(returncode=0, stdout="", stderr="")

        fake_bin = str(self.dir / "ffmpeg-resolved")
        which = mock.patch.object(mux.shutil, "which", lambda name: fake_bin)
        run = mock.patch.object(mux.subprocess, "run", fake_run)
        self.addCleanup(which.__exit__, None, None, None)
        self.addCleanup(run.__exit__, None, None, None)
        which.__enter__()
        run.__enter__()
        return calls, fake_bin

    def test_default_off_command_is_identical_to_legacy(self):
        """sfx=None 且无 MVP_SFX 时，命令必须与旧版逐项一致（不许新增 -i / filter_complex）。"""
        calls, fake_bin = self._patch()
        with mock.patch.dict(os.environ, {}, clear=True):
            result = mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4")
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 1)
        cmd = calls[0][0]
        self.assertEqual(cmd[0], fake_bin)
        self.assertEqual(cmd.count("-i"), 2, "默认路径只有视频+配音两个输入")
        self.assertNotIn("-filter_complex", cmd)
        self.assertNotIn("-map", cmd)

    def test_explicit_false_stays_off_even_when_env_says_on(self):
        calls, _ = self._patch()
        with mock.patch.dict(os.environ, {"MVP_SFX": "1"}):
            mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4", sfx=False)
        self.assertNotIn("-filter_complex", calls[0][0])

    def test_env_var_mvp_sfx_turns_it_on(self):
        calls, _ = self._patch()
        with mock.patch.dict(os.environ, {"MVP_SFX": "yes"}):
            mux.mux(self.dir / "v.mp4", self.dir / "a.wav", self.dir / "f.mp4",
                    shot_seconds=[3.0, 2.0])
        self.assertIn("-filter_complex", calls[0][0])

    def test_sfx_on_adds_inputs_and_mix_graph(self):
        """两个 shot（3s+2s）：切换点 3.0s、5.0s 各一份 sweep，片尾 5.0s 处一份 ding。"""
        audio = self.wav("a", 5.0)
        calls, _ = self._patch()
        result = mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4",
                         sfx=True, shot_seconds=[3.0, 2.0])
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 1)
        cmd = calls[0][0]
        self.assertEqual(cmd.count("-i"), 5, "视频+配音+2 份 sweep+1 份 ding")
        self.assertIn(str(mux.SFX_SWEEP), cmd)
        self.assertIn(str(mux.SFX_DING), cmd)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("volume=0.15", graph)
        self.assertIn("volume=0.25", graph)
        self.assertIn("adelay=3000", graph)
        self.assertIn("adelay=5000", graph)
        self.assertIn("amix=inputs=4", graph)
        self.assertIn("duration=first", graph)
        self.assertIn("normalize=0", graph)
        self.assertIn("[aout]", graph)
        # 音频映射：视频流直拷 + 混音输出
        first_map = cmd.index("-map")
        self.assertEqual(cmd[first_map + 1], "0:v")
        self.assertEqual(cmd[cmd.index("-map", first_map + 1) + 1], "[aout]")

    def test_ding_lands_at_track_tail(self):
        """ding 应在片尾收尾：4.0s 音轨 → adelay=4000-350=3650ms。"""
        audio = self.wav("a", 4.0)
        calls, _ = self._patch()
        mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4", sfx=True)
        cmd = calls[0][0]
        self.assertEqual(cmd.count("-i"), 3, "没有切换点：只有视频+配音+ding")
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("amix=inputs=2", graph)
        self.assertIn("volume=0.25", graph)
        self.assertNotIn("volume=0.15", graph)
        self.assertIn("adelay=3650", graph)

    def test_sfx_on_with_nothing_to_mix_runs_plain_pass(self):
        """音轨读不出时长且无 shot_seconds 时，SFX 图为空 → 直接跑普通命令，不报错。"""
        calls, _ = self._patch()
        result = mux.mux(self.dir / "v.mp4", self.dir / "missing.wav",
                         self.dir / "f.mp4", sfx=True)
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("-filter_complex", calls[0][0])

    def test_sfx_mix_failure_degrades_to_plain_path(self):
        """ffmpeg 混 SFX 失败：退回无音效命令重跑并打 warning，不能因音效毁掉整片。"""
        audio = self.wav("a", 5.0)
        calls = []

        def fake_run(cmd, *a, **kw):
            calls.append(list(cmd))
            if "-filter_complex" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(mux.subprocess, "run", fake_run), \
             mock.patch.object(mux.shutil, "which", lambda name: "ffmpeg-x"), \
             self.assertLogs("mux", level="WARNING"):
            result = mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4",
                             sfx=True, shot_seconds=[3.0])
        self.assertEqual(result, self.dir / "f.mp4")
        self.assertEqual(len(calls), 2, "先混 SFX 失败，再退无音效路径")
        self.assertIn("-filter_complex", calls[0])
        self.assertNotIn("-filter_complex", calls[1])

    def _srt(self) -> Path:
        srt = self.dir / "subs.srt"
        mux.write_srt({"shots": [{"index": 0, "seconds": 3.0, "subtitles":
                                  [{"i": 0, "start": 0.45, "end": 2.3, "text": "你好"}]}]}, srt)
        return srt

    def _patch_with_burn_file(self, fail_sfx=False):
        """记录两次调用，并在烧录那遍伪造出 burned.mp4（mux 以文件存在判定烧录成功）。"""
        calls = []

        def fake_run(cmd, *a, **kw):
            calls.append(list(cmd))
            if fail_sfx and "-filter_complex" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            if "-filter_complex" in cmd and "-map" in cmd and "[v]" in cmd:
                Path(cmd[-1]).write_bytes(b"\x00fake")   # 烧录版命令的落点是最后一个参数
            elif "-vf" in cmd:
                Path(cmd[-1]).write_bytes(b"\x00fake")
            return mock.Mock(returncode=0, stdout="", stderr="")

        which = mock.patch.object(mux.shutil, "which", lambda name: "ffmpeg-x")
        run = mock.patch.object(mux.subprocess, "run", fake_run)
        self.addCleanup(which.__exit__, None, None, None)
        self.addCleanup(run.__exit__, None, None, None)
        which.__enter__()
        run.__enter__()
        return calls

    def test_burned_version_carries_the_same_sfx_mix(self):
        """烧录版不许比主版本少音效：SFX 混入成功时，烧录命令必须把字幕滤镜与混音图并进同一条 filter_complex。"""
        audio = self.wav("a", 5.0)
        srt = self._srt()
        calls = self._patch_with_burn_file()
        result = mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4", srt=srt,
                         sfx=True, shot_seconds=[3.0, 2.0])
        self.assertEqual(result, self.dir / "f_burned.mp4")
        self.assertEqual(len(calls), 2)
        burn = calls[1]
        self.assertNotIn("-vf", burn, "带音效的烧录走 filter_complex，不再用 -vf")
        self.assertIn("-filter_complex", burn)
        fc = burn[burn.index("-filter_complex") + 1]
        self.assertIn(f"subtitles=filename='{srt.name}'", fc)
        self.assertIn("amix=", fc)
        self.assertIn("[aout]", fc)
        self.assertEqual(burn[burn.index("-map") + 1], "[v]")
        self.assertEqual(burn.count("-i"), 5, "视频+配音+2 sweep+1 ding")

    def test_burned_version_stays_plain_when_sfx_failed(self):
        """SFX 混入失败时两份都不带音效：烧录命令退回旧的 -vf 形态，命令里不出现 filter_complex。"""
        audio = self.wav("a", 5.0)
        srt = self._srt()
        calls = self._patch_with_burn_file(fail_sfx=True)
        with self.assertLogs("mux", level="WARNING"):
            result = mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4", srt=srt,
                             sfx=True, shot_seconds=[3.0, 2.0])
        self.assertEqual(result, self.dir / "f_burned.mp4")
        self.assertEqual(len(calls), 3, "SFX 失败 → base → 烧录")
        burn = calls[2]
        self.assertIn("-vf", burn)
        self.assertNotIn("-filter_complex", burn)

    def test_burn_command_unchanged_when_sfx_off(self):
        """默认关闭时烧录命令必须与改造前逐项一致（不许提前引入 filter_complex）。"""
        audio = self.wav("a", 5.0)
        srt = self._srt()
        calls = self._patch_with_burn_file()
        with mock.patch.dict(os.environ, {}, clear=True):
            mux.mux(self.dir / "v.mp4", audio, self.dir / "f.mp4", srt=srt)
        burn = calls[1]
        self.assertEqual(burn.count("-i"), 2)
        self.assertIn("-vf", burn)
        self.assertNotIn("-filter_complex", burn)
        self.assertNotIn("-map", burn)
        self.assertIn("libx264", burn)
        self.assertIn("-shortest", burn)


class TestProbeDuration(TmpCase):
    def test_parses_duration_from_stderr(self):
        with mock.patch.object(mux.subprocess, "run",
                               lambda *a, **kw: mock.Mock(stderr="Duration: 00:02:03.45, bitrate: ...")):
            self.assertAlmostEqual(mux.probe_duration(self.dir / "x.mp4"), 123.45, places=6)

    def test_returns_none_when_unparsable(self):
        with mock.patch.object(mux.subprocess, "run", lambda *a, **kw: mock.Mock(stderr="no info")):
            self.assertIsNone(mux.probe_duration(self.dir / "x.mp4"))

    def test_probe_over_one_hour(self):
        with mock.patch.object(mux.subprocess, "run",
                               lambda *a, **kw: mock.Mock(stderr="Duration: 01:01:01.50")):
            self.assertAlmostEqual(mux.probe_duration(self.dir / "x.mp4"), 3661.5, places=6)


class TestCleanupWork(TmpCase):
    """交付目录卫生（评审 B D43）：出片成功后中间产物必须清掉，成片与留档一个都不能少。

    实测一条 3.5 MiB 的片子旁边躺着 15.6 MiB 过路文件（占目录 84%），留档目录看着像
    "一个知识点四份视频"。这条闸门是删除操作，所以两端都要钉死：删什么、不删什么。
    """

    def test_only_intermediates_are_removed(self):
        for name in ("silent.mp4", "track.wav", "final.mp4"):
            (self.dir / name).write_bytes(b"x" * 100)
        (self.dir / "media" / "videos").mkdir(parents=True)
        (self.dir / "media" / "videos" / "c.png").write_bytes(b"y" * 50)
        (self.dir / "audio").mkdir()
        (self.dir / "audio" / "shot_00.wav").write_bytes(b"z" * 50)
        artifact = self.dir / "physics-H1-加速度-120s-abcd.mp4"
        artifact.write_bytes(b"k" * 700)
        (self.dir / "sidecar.json").write_text("{}", encoding="utf-8")

        freed = mux.cleanup_work(self.dir)

        self.assertEqual(freed, 400, "只该清掉 silent/track/final 与两个中间目录")
        self.assertTrue(artifact.exists(), "成片被删了")
        self.assertTrue((self.dir / "sidecar.json").exists(), "留档被删了")
        for name in mux.WORK_FILES + mux.WORK_DIRS:
            self.assertFalse((self.dir / name).exists(), f"{name} 没清掉")

    def test_partial_run_cleans_what_it_left(self):
        """任一步失败的那次跑不会留下全部中间产物，清理不得因此抛错。"""
        (self.dir / "silent.mp4").write_bytes(b"x" * 10)
        self.assertEqual(mux.cleanup_work(self.dir), 10)
        self.assertEqual(mux.cleanup_work(self.dir), 0, "重复清理应当无事发生")


if __name__ == "__main__":
    unittest.main()
