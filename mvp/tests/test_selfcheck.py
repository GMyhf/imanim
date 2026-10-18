"""F-10 自检工具的回归（第四轮整改轮，SubTask 48⑥）。

batch_v7 两轮独立评审分别抽样 335/148 帧都没抓到镜头边界的 0.20~0.63s 黑段——时间点抽样
在结构上看不见边界现象。这里锁住两类纯逻辑（不碰 ffmpeg/渲染，跑得快）：
①ffmpeg stderr 的分辨率/帧率解析正则，覆盖 batch_v8 实际两种构建输出过的格式；
②空白帧区间与镜头边界的归类判据——"落在边界上"要同时短且跨住边界点，否则一路黑到镜尾
  的异常区间会被误判成正常（这正是 F-2 修复前的真实回归形状）。
真正读视频文件的 scan_boundaries()/contact_sheet() 留给 .local 的手工验证脚本覆盖
（起渲染环境的集成测试不适合跑进单测套件，但纯逻辑部分必须有回归）。
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import selfcheck  # noqa: E402


class TestIsBlank(unittest.TestCase):
    """batch_v8 实测：原来的 max(axis=2).sum()==0 写法在 fullhd 上 3603 帧要 187.6s，
    换成按通道 .any() 短路后同样数据集几秒内跑完。这里锁住新写法与旧写法在边界阈值上
    的判定结果必须一致，不能为了快而悄悄改变"什么算空白"的定义。
    """

    def test_all_zero_frame_is_blank(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        self.assertTrue(selfcheck._is_blank(frame, ink_threshold=60))

    def test_single_bright_pixel_is_not_blank(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frame[5, 5, 1] = 61
        self.assertFalse(selfcheck._is_blank(frame, ink_threshold=60))

    def test_pixel_exactly_at_threshold_is_still_blank(self):
        """阈值判据是"> threshold"，不是">="——与旧版 max(axis=2) > thr 的严格不等式对齐。"""
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frame[0, 0, 0] = 60
        self.assertTrue(selfcheck._is_blank(frame, ink_threshold=60))

    def test_pixel_one_above_threshold_is_not_blank(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frame[0, 0, 0] = 61
        self.assertFalse(selfcheck._is_blank(frame, ink_threshold=60))

    def test_matches_legacy_max_axis_formula_on_random_frames(self):
        """新旧两种写法在随机帧上逐一核对结果一致，不只是挑边界用例。"""
        rng = np.random.default_rng(42)
        for _ in range(20):
            frame = rng.integers(0, 90, size=(16, 16, 3), dtype=np.uint8)
            legacy = int((frame.max(axis=2) > 60).sum()) == 0
            self.assertEqual(selfcheck._is_blank(frame, ink_threshold=60), legacy)


class TestResolutionFpsRegex(unittest.TestCase):
    """覆盖 batch_v8 实测会撞到的两种 ffmpeg Video 行格式。"""

    def _match(self, line: str):
        m = re.search(
            r"Video:.*?,\s*(\d+)x(\d+)(?:\s*\[[^\]]*\])?.*?([\d.]+)\s*fps", line)
        self.assertIsNotNone(m, line)
        return m.groups()

    def test_draft_quality_line(self):
        line = ("Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), "
                "yuv420p(progressive), 854x480, 152 kb/s, 15 fps, 15 tbr, 15360 tbn (default)")
        self.assertEqual(self._match(line), ("854", "480", "15"))

    def test_fullhd_with_sar_dar_annotation(self):
        line = ("Stream #0:0: Video: h264 (High), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], "
                "485 kb/s, 29.97 fps, 30 tbr, 1k tbn")
        self.assertEqual(self._match(line), ("1920", "1080", "29.97"))

    def test_codec_tag_hex_is_not_mistaken_for_resolution(self):
        """0x31637661 这类编码器 hex 标签长得像 WxH，正则必须认到真正的分辨率而不是它。"""
        line = ("Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), "
                "yuv420p(progressive), 1280x720, 300 kb/s, 30 fps, 30 tbr")
        self.assertEqual(self._match(line), ("1280", "720", "30"))

    def test_real_ffprobe_resolution_fps_raises_on_garbage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "not_a_video.mp4"
            fake.write_bytes(b"not a real video")
            with self.assertRaises(RuntimeError):
                selfcheck._ffprobe_resolution_fps(fake)


class TestShotBounds(unittest.TestCase):
    def test_cumulative_offsets_match_mux_write_srt_convention(self):
        plan = {"shots": [{"seconds": 10.0}, {"seconds": 15.5}, {"seconds": 8.25}]}
        self.assertEqual(selfcheck._shot_bounds(plan),
                         [(0.0, 10.0), (10.0, 25.5), (25.5, 33.75)])

    def test_empty_plan_is_empty_bounds(self):
        self.assertEqual(selfcheck._shot_bounds({"shots": []}), [])


class TestClassifyRuns(unittest.TestCase):
    """这组是 F-10 的核心判据：区分"正常的瞬时边界误差"与"真实的边界黑场回归"。"""

    def test_short_run_touching_a_boundary_is_not_flagged(self):
        # fps=30：3 帧 = 0.1s，落在边界 t=10.0 上，属于取整误差级别的瞬时波动
        runs = [[299, 301]]  # 9.967s..10.033s
        out = selfcheck.classify_runs(runs, fps=30.0, boundary_times=[0.0, 10.0, 20.0])
        self.assertTrue(out[0]["at_boundary"])

    def test_long_run_starting_at_a_boundary_is_still_flagged(self):
        """F-2 修复前的真实形状：起点刚好对上边界，但一路黑到镜尾——起点对上不能免责。"""
        runs = [[300, 318]]  # 10.0s..10.633s，跨度 0.633s，与 v7 实测的黑段时长同量级
        out = selfcheck.classify_runs(runs, fps=30.0, boundary_times=[0.0, 10.0, 20.0])
        self.assertFalse(out[0]["at_boundary"])

    def test_run_far_from_any_boundary_is_flagged(self):
        runs = [[449, 450]]  # 14.97s..15.03s，离最近边界（10 或 20）有 5s
        out = selfcheck.classify_runs(runs, fps=30.0, boundary_times=[0.0, 10.0, 20.0])
        self.assertFalse(out[0]["at_boundary"])

    def test_no_runs_means_nothing_to_classify(self):
        self.assertEqual(selfcheck.classify_runs([], fps=30.0, boundary_times=[0.0, 10.0]), [])

    def test_scan_result_shape_marks_unexpected_only_for_non_boundary_runs(self):
        runs = selfcheck._group_runs([299, 300, 301])  # 单个短区间，落在边界上
        classified = selfcheck.classify_runs(runs, fps=30.0, boundary_times=[0.0, 10.0])
        unexpected = any(not r["at_boundary"] for r in classified)
        self.assertFalse(unexpected, "落在边界上的短区间不该被判成异常")


class TestGroupRuns(unittest.TestCase):
    def test_consecutive_frames_merge_into_one_run(self):
        self.assertEqual(selfcheck._group_runs([5, 6, 7, 20, 21]), [[5, 7], [20, 21]])

    def test_empty_input_is_empty_output(self):
        self.assertEqual(selfcheck._group_runs([]), [])

    def test_all_isolated_frames_stay_separate(self):
        self.assertEqual(selfcheck._group_runs([1, 5, 9]), [[1, 1], [5, 5], [9, 9]])


if __name__ == "__main__":
    unittest.main()
