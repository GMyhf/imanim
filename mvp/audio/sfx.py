"""程序生成短音效（转场音/提示音），纯标准库 wave+math，无 numpy、无外部素材。

素材生成后落盘入库（assets/sfx/），mux 混音时直接当 ffmpeg 输入——"即产即用"，
与管线音频同规格：24000Hz / 16-bit / mono WAV。

- ding   强调提示音：880Hz 正弦 + 指数衰减包络，约 0.35s，峰值归一 0.6
- sweep  镜头转场音：300→900Hz 线性扫频 + 淡入淡出包络，约 0.4s，峰值归一 0.4
- tick   轻提示音：1200Hz 正弦 + 指数衰减，30ms，峰值归一 0.3
"""

from __future__ import annotations

import math
import wave
from pathlib import Path

RATE = 24000

DING_SECONDS = 0.35
SWEEP_SECONDS = 0.40
TICK_SECONDS = 0.03

DING_PEAK = 0.6
SWEEP_PEAK = 0.4
TICK_PEAK = 0.3


def _samples_ding() -> list[float]:
    """880Hz 正弦 + 指数衰减（时间常数 70ms），末尾自然衰减到 ~0.7% 幅值。"""
    n = int(round(DING_SECONDS * RATE))
    tau = 0.07
    return [math.sin(2.0 * math.pi * 880.0 * i / RATE) * math.exp(-i / RATE / tau)
            for i in range(n)]


def _samples_sweep() -> list[float]:
    """300→900Hz 线性扫频（相位取频率积分），首尾正弦半波淡入淡出。"""
    n = int(round(SWEEP_SECONDS * RATE))
    total = SWEEP_SECONDS
    rise, fall = 0.02, 0.08
    out = []
    for i in range(n):
        t = i / RATE
        # ∫f dt = 300t + 300t²/T，保证瞬时频率严格从 300Hz 线性走到 900Hz。
        phase = 2.0 * math.pi * (300.0 * t + 300.0 * t * t / total)
        env = 1.0
        if t < rise:
            env = 0.5 - 0.5 * math.cos(math.pi * t / rise)
        if t > total - fall:
            env = min(env, 0.5 + 0.5 * math.cos(math.pi * (t - (total - fall)) / fall))
        out.append(math.sin(phase) * env)
    return out


def _samples_tick() -> list[float]:
    """1200Hz 短促提示音，指数衰减（时间常数 8ms），30ms 内收尾。"""
    n = int(round(TICK_SECONDS * RATE))
    tau = 0.008
    return [math.sin(2.0 * math.pi * 1200.0 * i / RATE) * math.exp(-i / RATE / tau)
            for i in range(n)]


def _normalize(samples: list[float], peak: float) -> list[float]:
    """峰值归一：整体缩放到 max|sample| == peak；全零输入原样返回。"""
    m = max((abs(s) for s in samples), default=0.0)
    if m <= 0.0:
        return samples
    k = peak / m
    return [s * k for s in samples]


def _write_wav(path: Path, samples: list[float]) -> None:
    """写 24kHz/16bit/mono WAV；样本裁剪进 [-1, 1] 后量化为小端 int16。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray(len(samples) * 2)
    for i, s in enumerate(samples):
        v = int(round(max(-1.0, min(1.0, s)) * 32767))
        frames[2 * i] = v & 0xFF
        frames[2 * i + 1] = (v >> 8) & 0xFF
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


def generate_all(assets_dir: Path) -> list[Path]:
    """生成三件套音效并落盘到 assets_dir，返回写入的文件路径列表。"""
    files = [
        ("ding.wav", _normalize(_samples_ding(), DING_PEAK)),
        ("sweep.wav", _normalize(_samples_sweep(), SWEEP_PEAK)),
        ("tick.wav", _normalize(_samples_tick(), TICK_PEAK)),
    ]
    out = []
    for name, samples in files:
        p = Path(assets_dir) / name
        _write_wav(p, samples)
        out.append(p)
    return out


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent / "assets" / "sfx"
    for p in generate_all(here):
        print(p)
