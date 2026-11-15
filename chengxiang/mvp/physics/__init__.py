# -*- coding: utf-8 -*-
"""物理仿真引擎（flow v2 核心 rule：画面运动必须由真实物理模型驱动，禁止手填关键帧）。

三个模块的职责边界：
- integrator：时间推进（RK4），只管"给定受力函数，走出轨迹"；
- particle：带电粒子在 E/B 场中的受力（洛伦兹），只管"给定状态，给出力"；
- graphsync：把轨迹同步成图线数据与逐帧点，保证"图-式-体三者同源"。

M2 生成的场景代码只允许走这里的公开 API，签名契约见 pipeline/flow/stages.py 的 M2_BRIEF。
"""

from __future__ import annotations

from .graphsync import AxisMap, Curve, Range, autoscale, bounds, series, shared_time_axis
from .integrator import Trajectory, integrate, rk4_step
from .particle import ELECTRON_MASS, E_CHARGE, PROTON_MASS, Particle, lorentz

__all__ = [
    "AxisMap", "Curve", "ELECTRON_MASS", "E_CHARGE", "PROTON_MASS", "Particle", "Range",
    "Trajectory", "autoscale", "bounds", "integrate", "lorentz", "rk4_step",
    "series", "shared_time_axis",
]
