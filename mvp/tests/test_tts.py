"""A6 网关 TTS（audio/tts.py）回归：全部用假传输，不联网、不读真密钥。

锁住的边界（SubTask #60-A 实测口径）：
- 成功合成：返回实测时长、落盘 WAV 合法（wave 能打开，帧数与文件字节一致）；
- 网关 WAV 头里 RIFF/data 两个 size 是溢出值 → 落盘前必须重写成真实值，否则读出几小时假时长；
- 间歇 403/429/5xx → 重试退避（4 次、3s 起翻倍），重试能成功；
- 重试耗尽 → RuntimeError，消息含状态码与响应体，绝不含密钥/请求头；
- 响应体非 RIFF（网关 JSON 错误页）→ 报错且不落坏文件；
- speed 无效（探测结论）→ rate 照收但忽略、请求体不带 speed 字段。
"""

from __future__ import annotations

import io
import json
import os
import struct
import sys
import tempfile
import unittest
import urllib.error
import wave
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _util import write_wav  # noqa: E402
from audio import tts  # noqa: E402

SECRET = "sk-TESTFAKEKEY123"  # 假密钥：断言里用它反证"绝不出现在消息里"


class FakeResp:
    """urlopen 的假响应：只实现 with + read。"""

    def __init__(self, blob: bytes):
        self._blob = blob

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._blob


def wav_blob(seconds: float = 2.0, corrupt: bool = False) -> bytes:
    """造一段合法 WAV；corrupt=True 时把 RIFF/data 两个 size 写成网关的溢出值。"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.wav"
        write_wav(p, seconds)
        blob = p.read_bytes()
    if not corrupt:
        return blob
    out = bytearray(blob)
    struct.pack_into("<I", out, 4, 0x7FFFFFBF)    # RIFF size：网关溢出值
    struct.pack_into("<I", out, 40, 0x7FFFFF5B)   # data size：fmt 16 字节 → data 在 36，size 在 40
    return bytes(out)


def http_err(code: int, body: bytes = b'{"error": "rate limited"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(body))


def close_fps(case, side):
    """测试结束时关掉 HTTPError 的响应体，别让 ResourceWarning 污染输出。"""
    case.addCleanup(lambda: [getattr(e, "close", lambda: None)() for e in side])


def env_only_key():
    """只给假密钥、清空其余环境变量：不碰机器上任何真实配置。"""
    return mock.patch.dict(os.environ, {"QX_LLM_API_KEY": SECRET}, clear=True)


class TestSynthSuccess(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.out = self.root / "sub" / "shot.wav"  # 顺带验证 synth 会自动建目录

    def test_success_writes_valid_wav_and_repaired_header(self):
        """网关的溢出 size 必须被重写：wave 能打开、getnframes 与文件真实字节一致。"""
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", return_value=FakeResp(wav_blob(2.0, corrupt=True))):
            dur = tts.synth("加速度是速度的变化率。", self.out, self.root)
        self.assertAlmostEqual(dur, 2.0, places=3)
        raw = self.out.read_bytes()
        with wave.open(str(self.out), "rb") as w:
            self.assertEqual(w.getframerate(), 24000)
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 2.0, places=3)
        # 修复后的头：RIFF/data 两个 size 都等于真实字节数，不再是溢出值
        self.assertEqual(struct.unpack("<I", raw[4:8])[0], len(raw) - 8)
        self.assertEqual(struct.unpack("<I", raw[40:44])[0], len(raw) - 44)
        # mux 拼接同款读法：readframes(getnframes()) 不得读到畸形帧数
        with wave.open(str(self.out), "rb") as w:
            self.assertEqual(len(w.readframes(w.getnframes())), w.getnframes() * w.getsampwidth())

    def test_healthy_wav_passes_through_untouched(self):
        blob = wav_blob(1.5)
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", return_value=FakeResp(blob)):
            dur = tts.synth("你好", self.out, self.root)
        self.assertAlmostEqual(dur, 1.5, places=3)
        self.assertEqual(self.out.read_bytes(), blob)

    def test_request_uses_default_model_voice_and_bearer(self):
        calls = []

        def fake(req, timeout=None):
            calls.append(req)
            return FakeResp(wav_blob(1.0))

        with env_only_key(), mock.patch("urllib.request.urlopen", side_effect=fake):
            tts.synth("你好", self.out, self.root)
        self.assertEqual(len(calls), 1)
        body = json.loads(calls[0].data.decode("utf-8"))
        self.assertEqual(body, {"model": "qwen3-tts-flash", "input": "你好", "voice": "cherry"})
        self.assertIn("/v1/audio/speech", calls[0].full_url)
        self.assertEqual(calls[0].headers["Authorization"], f"Bearer {SECRET}")

    def test_env_overrides_voice_and_model(self):
        calls = []

        def fake(req, timeout=None):
            calls.append(req)
            return FakeResp(wav_blob(1.0))

        with mock.patch.dict(os.environ, {"QX_LLM_API_KEY": SECRET,
                                          "QX_TTS_VOICE": "marshmallow",
                                          "QX_TTS_MODEL": "qwen3-tts-flash-v2"}, clear=True), \
                mock.patch("urllib.request.urlopen", side_effect=fake):
            tts.synth("你好", self.out, self.root)
        body = json.loads(calls[0].data.decode("utf-8"))
        self.assertEqual(body["voice"], "marshmallow")
        self.assertEqual(body["model"], "qwen3-tts-flash-v2")

    def test_rate_is_accepted_but_ignored_no_speed_field(self):
        """探测结论：speed 无效。rate=4 照收但忽略，请求体不带 speed，返回自然时长。"""
        self.assertFalse(tts.SPEED_SUPPORTED, "探测结论不该被悄悄改回 True 而 run.py 还在报自然语速")
        calls = []

        def fake(req, timeout=None):
            calls.append(req)
            return FakeResp(wav_blob(2.0))

        with env_only_key(), mock.patch("urllib.request.urlopen", side_effect=fake):
            dur = tts.synth("你好", self.out, self.root, rate=4)
        body = json.loads(calls[0].data.decode("utf-8"))
        self.assertNotIn("speed", body)
        self.assertAlmostEqual(dur, 2.0, places=3)


class TestRetryAndErrors(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.out = self.root / "shot.wav"

    def test_403_then_success_with_backoff(self):
        sleeps = []
        side = [http_err(403), http_err(429), FakeResp(wav_blob(1.0))]
        close_fps(self, side)
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", side_effect=side) as u, \
                mock.patch.object(tts.time, "sleep", side_effect=sleeps.append):
            dur = tts.synth("你好", self.out, self.root)
        self.assertEqual(u.call_count, 3)
        self.assertAlmostEqual(dur, 1.0, places=3)
        self.assertEqual(sleeps, [3.0, 6.0])

    def test_network_error_retries_then_succeeds(self):
        side = [urllib.error.URLError("down"), FakeResp(wav_blob(1.0))]
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", side_effect=side) as u, \
                mock.patch.object(tts.time, "sleep"):
            tts.synth("你好", self.out, self.root)
        self.assertEqual(u.call_count, 2)

    def test_exhausted_retries_raise_with_status_and_body_but_no_secret(self):
        """每次尝试的响应体对象要独立（read 会消耗游标），否则断言会拿到空体。"""
        sleeps = []
        side = [http_err(403, b'{"error": "forbidden by gateway"}') for _ in range(tts.MAX_ATTEMPTS)]
        close_fps(self, side)
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", side_effect=side) as u, \
                mock.patch.object(tts.time, "sleep", side_effect=sleeps.append):
            with self.assertRaises(RuntimeError) as cm:
                tts.synth("你好", self.out, self.root)
        msg = str(cm.exception)
        self.assertEqual(u.call_count, tts.MAX_ATTEMPTS)
        self.assertIn("403", msg)
        self.assertIn("forbidden by gateway", msg)
        self.assertNotIn(SECRET, msg)
        self.assertNotIn("Authorization", msg)
        self.assertFalse(self.out.exists(), "重试耗尽时不许留下半截文件")

    def test_non_retryable_status_fails_fast_without_sleep(self):
        side = [http_err(401)]
        close_fps(self, side)
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", side_effect=side) as u, \
                mock.patch.object(tts.time, "sleep") as sl:
            with self.assertRaises(RuntimeError) as cm:
                tts.synth("你好", self.out, self.root)
        self.assertEqual(u.call_count, 1, "401 重试不会变好，必须一次失败")
        sl.assert_not_called()
        self.assertIn("401", str(cm.exception))
        self.assertFalse(self.out.exists())

    def test_non_riff_response_raises_and_writes_nothing(self):
        """网关返回 JSON 错误页（HTTP 200 但体不是 WAV）时必须报错，不能落坏文件。"""
        with env_only_key(), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResp(b'{"error": "model not found"}')), \
                mock.patch.object(tts.time, "sleep"):
            with self.assertRaises(RuntimeError) as cm:
                tts.synth("你好", self.out, self.root)
        self.assertIn("不是 RIFF/WAV", str(cm.exception))
        self.assertIn("model not found", str(cm.exception))
        self.assertFalse(self.out.exists())

    def test_riff_without_data_chunk_raises(self):
        fmt = struct.pack("<HHIIHH", 1, 1, 24000, 48000, 2, 16)
        bad = b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt)) + b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
        with env_only_key(), \
                mock.patch("urllib.request.urlopen", return_value=FakeResp(bad)), \
                mock.patch.object(tts.time, "sleep"):
            with self.assertRaises(RuntimeError) as cm:
                tts.synth("你好", self.out, self.root)
        self.assertIn("data", str(cm.exception))
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
