"""测试公共工具（纯标准库）。

注意：Windows 控制台是 GBK，测试一律不靠 stdout 验证，只用断言。
临时目录/wav 文件名保持 ASCII。
"""

from __future__ import annotations

import wave
from pathlib import Path

from pipeline.ir import Brief, Plan

# 真实库里的干净数据（红线用例：0 findings）
ACCEL = "physics/acceleration"


def ok_brief(**over) -> Brief:
    base = dict(subject="physics", grade="H1", topic="加速度", target_seconds=120,
                style="clean", resolution="1920x1080")
    base.update(over)
    return Brief(**base)


def shot_dict(index: int = 0, seconds: float = 10.0, narration: str = "",
              visuals: list[dict] | None = None, kp_refs: list[str] | None = None,
              title: str = "镜头", emphasis: str = "") -> dict:
    # 默认版面带一张图：真实条目全都有 figure/graph_vt，而 NO_FIGURE 闸门按**整片**算，
    # 基线必须与真实数据同构，否则每条"只该命中一个码"的用例都会被它污染成两个。
    default_visuals = [{"kind": "callout", "props": {"text": "提示"}},
                       {"kind": "figure", "props": {"shape": "right_triangle", "a": 3, "b": 4}}]
    return {
        "index": index,
        "title": title,
        "seconds": seconds,
        "narration": narration,
        "emphasis": emphasis,
        "kp_refs": kp_refs if kp_refs is not None else ["人教版高中物理必修第一册 第一章 1.3"],
        "visuals": visuals if visuals is not None else default_visuals,
    }


def plan_of(shots: list[dict], target_seconds: int = 120, **brief_over) -> Plan:
    """从 dict 列表构造 Plan，绕开 storyboard（用于喂给 review）。"""
    return Plan.from_dict({
        "knowledge_id": "kp.test.demo",
        "refs": [{"source": "测试教材", "locator": "第 1 章"}],
        "brief": {**ok_brief(target_seconds=target_seconds, **brief_over).__dict__},
        "shots": shots,
    })


def codes_of(findings: list[dict]) -> set[str]:
    return {f["code"] for f in findings}


def shots_of(findings: list[dict]) -> set:
    return {f["shot"] for f in findings}


def write_wav(path: Path, seconds: float, rate: int = 24000, channels: int = 1,
              width: int = 2, value: int = 1200) -> float:
    """写一段恒定幅度的 wav，返回文件里的实际时长（受整帧取整影响）。"""
    total_frames = max(0, int(round(seconds * rate)))
    if width == 2:
        payload = int(value).to_bytes(2, "little", signed=True) * (total_frames * channels)
    elif width == 1:
        payload = bytes([min(255, abs(int(value)))]) * (total_frames * channels)
    else:
        raise NotImplementedError("只造 8/16bit 测试音频")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(payload)
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def voiced_spans(path: Path, gap_frames: int | None = None) -> list[tuple[float, float]]:
    """把 wav 按连续非零采样切成 [(起秒, 止秒)]，用于验证偏移与拼接。"""
    with wave.open(str(path), "rb") as w:
        rate, width, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        n = w.getnframes()
        raw = w.readframes(n)
    assert width == 2 and ch == 1, "voiced_spans 只解析 16bit mono"
    voiced = [i for i in range(n) if int.from_bytes(raw[2 * i:2 * i + 2], "little", signed=True) != 0]
    if not voiced:
        return []
    spans = []
    start = prev = voiced[0]
    for i in voiced[1:]:
        if i - prev > 1:
            spans.append((start / rate, (prev + 1) / rate))
            start = i
        prev = i
    spans.append((start / rate, (prev + 1) / rate))
    return spans
