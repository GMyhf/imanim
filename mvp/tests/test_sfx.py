"""音效生成测试（SubTask #60-E）：wave 可打开、规格对齐管线、时长/峰值在预期、无全静音。

只测标准库 wave 能确定的部分，不依赖 ffmpeg。
"""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audio import sfx  # noqa: E402

# 每个音效的规格锚点：文件名 -> (标称时长, 峰值, 时长容差)
SPECS = {
    "ding.wav": (sfx.DING_SECONDS, sfx.DING_PEAK, 0.01),
    "sweep.wav": (sfx.SWEEP_SECONDS, sfx.SWEEP_PEAK, 0.01),
    "tick.wav": (sfx.TICK_SECONDS, sfx.TICK_PEAK, 0.002),
}


class TestSfxGenerate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        cls.files = sfx.generate_all(cls.dir)
        cls.addClassCleanup(cls._tmp.cleanup)

    def read(self, name: str):
        with wave.open(str(self.dir / name), "rb") as w:
            n = w.getnframes()
            raw = w.readframes(n)
            return w, n, raw

    def test_generate_all_writes_all_three_files(self):
        self.assertEqual(sorted(p.name for p in self.files),
                         ["ding.wav", "sweep.wav", "tick.wav"])
        for p in self.files:
            self.assertTrue(p.exists())
            self.assertGreater(p.stat().st_size, 44, "只有 wav 头没有数据？")

    def test_wav_format_matches_pipeline_audio(self):
        for name in SPECS:
            with self.subTest(name=name):
                w, _n, _raw = self.read(name)
                self.assertEqual(w.getframerate(), 24000)
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getcomptype(), "NONE")

    def test_duration_within_expected_range(self):
        for name, (seconds, _peak, tol) in SPECS.items():
            with self.subTest(name=name):
                w, n, _raw = self.read(name)
                self.assertAlmostEqual(n / w.getframerate(), seconds, delta=tol)

    def test_not_silent_and_peak_normalized(self):
        for name, (_seconds, peak, _tol) in SPECS.items():
            with self.subTest(name=name):
                _w, n, raw = self.read(name)
                samples = [int.from_bytes(raw[2 * i:2 * i + 2], "little", signed=True) / 32768
                           for i in range(n)]
                rms = math.sqrt(sum(s * s for s in samples) / len(samples))
                self.assertGreater(rms, 0.01, "音效不能是静音")
                self.assertAlmostEqual(max(abs(s) for s in samples), peak, delta=0.002,
                                       msg="峰值归一要到标称值（量化误差外）")

    def test_samples_are_in_16bit_range(self):
        for name in SPECS:
            with self.subTest(name=name):
                _w, n, raw = self.read(name)
                for i in range(n):
                    v = int.from_bytes(raw[2 * i:2 * i + 2], "little", signed=True)
                    self.assertGreaterEqual(v, -32768)
                    self.assertLessEqual(v, 32767)


if __name__ == "__main__":
    unittest.main()
