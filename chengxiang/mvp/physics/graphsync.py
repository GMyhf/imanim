# -*- coding: utf-8 -*-
"""图-式-体同源：轨迹 → 图线数据 → 逐帧点。

同一物理量在"粒子动画"和"函数图线"里必须来自同一个 Trajectory；本模块负责
共享时间轴、自动取整的坐标范围、以及按渲染帧数取点（画面与图线逐帧对齐）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

from .integrator import Trajectory


def _nice_step(span: float, want: int = 5) -> float:
    if span <= 0:
        return 1.0
    raw = span / max(1, want)
    mag = 10.0 ** float(np.floor(np.log10(raw)))
    for k in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= k * mag:
            return k * mag
    return 10.0 * mag


def bounds(values: Sequence[float], pad_ratio: float = 0.08) -> tuple[float, float]:
    """数据范围 + 相对留白；单点数据对称展开，零范围给 [-1,1] 兜底。"""
    v = np.asarray(values, dtype=float).ravel()
    lo, hi = float(v.min()), float(v.max())
    if hi == lo:
        return (lo - 1.0, hi + 1.0) if lo == 0 else (lo * 0.9, lo * 1.1)
    pad = (hi - lo) * pad_ratio
    return lo - pad, hi + pad


@dataclass(frozen=True)
class Range:
    lo: float
    hi: float
    step: float

    def ticks(self) -> np.ndarray:
        start = float(np.ceil(self.lo / self.step)) * self.step
        n = int(np.floor((self.hi - start) / self.step + 1e-9)) + 1
        return start + self.step * np.arange(n)


def autoscale(values: Sequence[float], want: int = 5, pad_ratio: float = 0.08) -> Range:
    """把数据范围外扩到好看刻度（0 一定在范围内，便于讲"从几开始"）。"""
    lo, hi = bounds(values, pad_ratio)
    step = _nice_step(hi - lo, want)
    lo = min(lo, 0.0) if min(values) <= 0 <= max(values) else lo
    hi = max(hi, 0.0) if min(values) <= 0 <= max(values) else hi
    return Range(float(np.floor(lo / step) * step), float(np.ceil(hi / step) * step), step)


@dataclass(frozen=True)
class AxisMap:
    """仿真单位 → 画面单位的线性映射（图线与粒子共用一个，保证同源）。

    src 是**数据实际范围**：数据端点正好落在 dst 两端，画出来的线恰好铺满给定的
    画面宽度/高度（不靠 padding 猜比例）。刻度用 autoscale() 单独算。
    """
    src: Range
    dst: Range
    origin: Sequence[float] = field(default=(0.0, 0.0))

    @classmethod
    def of(cls, values: Sequence[float], span: float, want: int = 5,
           origin: Sequence[float] = (0.0, 0.0)) -> "AxisMap":
        v = np.asarray(values, dtype=float).ravel()
        lo, hi = float(v.min()), float(v.max())
        # 近常量数据（如磁场中速率守恒，RK4 只剩 ~1e-10 漂移）必须有量程地板：
        # 否则数值噪声被放大成整幅斜线，"速率恒定"渲成一条上升直线（2026-10-18 探针实拍）。
        floor = 1e-5 * max(abs(lo), abs(hi), 1.0)
        if hi - lo < floor:
            mid = 0.5 * (lo + hi)
            lo, hi = mid - 0.5 * floor, mid + 0.5 * floor
        step = _nice_step(hi - lo, want)
        return cls(src=Range(lo, hi, step), dst=Range(0.0, float(span), step), origin=origin)

    @property
    def scale(self) -> float:
        return (self.dst.hi - self.dst.lo) / (self.src.hi - self.src.lo)

    def to_screen(self, value: float, axis: int = 0) -> float:
        """把仿真值映射成相对 origin 的第 axis 个方向坐标（0=x，1=y）。

        不翻转 y：渲染端是 ManimCE（y 轴向上），在这里再翻一次会把图线上下颠倒、
        把粒子转向做成镜像（2026-10-18 探针实拍）。要 SVG 那类 y-向下坐标系请调用方自己处理。
        """
        return float(self.origin[axis]) + (float(value) - self.src.lo) * self.scale

    def screen_span(self) -> float:
        return self.dst.hi - self.dst.lo


@dataclass(frozen=True)
class Curve:
    """一条图线：共享时间轴 x + 物理量 y + 各自的映射。"""
    name: str
    x: np.ndarray
    y: np.ndarray
    x_map: AxisMap
    y_map: AxisMap

    def points(self, n_frames: int) -> list[tuple[float, float]]:
        """按渲染帧数取点（线性插值到帧边界），逐帧画就是"图随体走"。"""
        if n_frames < 2:
            return []
        xq = np.linspace(float(self.x[0]), float(self.x[-1]), n_frames)
        yq = np.interp(xq, self.x, self.y)
        return [(self.x_map.to_screen(a, 0), self.y_map.to_screen(b, 1))
                for a, b in zip(xq, yq)]

    def upto(self, t: float) -> list[tuple[float, float]]:
        """截至时刻 t 的已画部分（描线动画用），含精确端点。"""
        tt = np.clip(float(t), float(self.x[0]), float(self.x[-1]))
        idx = int(np.searchsorted(self.x, tt)) + 1
        xs = np.append(self.x[:idx], tt)
        ys = np.append(self.y[:idx], float(np.interp(tt, self.x, self.y)))
        return [(self.x_map.to_screen(a, 0), self.y_map.to_screen(b, 1)) for a, b in zip(xs, ys)]


def series(traj: Trajectory, y, x: str = "t", name: str = "", width: float = 10.0,
           origin: Sequence[float] = (0.0, 0.0), want: int = 5) -> Curve:
    """从轨迹取一条图线（唯一合法入口，场景里不许手填坐标）。x 只认 "t"——时间轴全片共享。
    y 取物理量：
      "pos" / "speed" / "ek"  → 标量轨迹量
      ("pos", k)              → 第 k 个分量（"v"/"vel"/"a"/"acc" 同理）
      (名字, fn)              → fn(traj) 返回与节点等长的数组
    """
    if x != "t":
        raise ValueError(f"图线横轴只能是共享时间轴 't'，收到 {x!r}")
    xv = np.asarray(traj.t, dtype=float)
    yv = _pick(traj, y)
    xm = AxisMap.of(xv, width, want, origin)
    ym = AxisMap.of(yv, _screen_height(width), want, origin)
    return Curve(name=name or str(y), x=xv, y=yv, x_map=xm, y_map=ym)


def _screen_height(width: float) -> float:
    return max(1.0, width * 0.5)


def _pick(traj: Trajectory, y) -> np.ndarray:
    if isinstance(y, str):
        key = y.strip().lower()
        if key in ("pos", "x"):
            return np.linalg.norm(traj.pos, axis=1) if traj.pos.shape[1] > 1 else traj.pos[:, 0]
        if key == "speed":
            return traj.speed()
        if key in ("ek", "energy"):
            return traj.kinetic_energy()
        raise ValueError(f"未知图线量：{y!r}（可用 pos/speed/ek 或 ('pos', k) 或 (名, fn)）")
    if isinstance(y, tuple):
        kind, sel = y
        if callable(sel):
            out = np.asarray(sel(traj), dtype=float)
            if out.ndim == 0:
                out = np.full(len(traj.t), float(out))
            if len(out) != len(traj.t):
                raise ValueError(f"图线函数返回长度 {len(out)} != 轨迹节点数 {len(traj.t)}")
            return out
        if kind in ("pos", "v", "vel", "a", "acc"):
            arr = {"pos": traj.pos, "v": traj.vel, "vel": traj.vel,
                   "a": traj.acc, "acc": traj.acc}[kind]
            return arr[:, int(sel)]
    raise ValueError(f"未知图线量：{y!r}")


def shared_time_axis(traj: Trajectory) -> np.ndarray:
    """全片图线共用的时间轴（图-式-体同源的硬保证：任何图线都只能画在这条轴上）。"""
    return np.asarray(traj.t, dtype=float)
