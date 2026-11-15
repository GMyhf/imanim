# -*- coding: utf-8 -*-
"""带电粒子：状态 + 场（E/B）+ 洛伦兹合力。速度允许二维，此时 B 必须是三维（z 分量即垂直纸面）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

E_CHARGE = 1.602176634e-19     # 元电荷 e（C）
ELECTRON_MASS = 9.1093837015e-31
PROTON_MASS = 1.67262192369e-27


def _as3(u: Sequence[float], what: str) -> np.ndarray:
    """二维按 (x, y, 0) 升维；只接受 2/3 分量，避免广播错位悄悄算错力。"""
    a = np.asarray(u, dtype=float).ravel()
    if a.size == 2:
        return np.array([a[0], a[1], 0.0])
    if a.size != 3:
        raise ValueError(f"{what} 需要 2 或 3 个分量，收到 {a.size}")
    return a


def lorentz(q: float, vel: Sequence[float], e_field: Sequence[float] = (0.0, 0.0, 0.0),
            b_field: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """F = q(E + v×B)。二维速度（纸面内）→ 二维力；B 的 z 分量即垂直纸面的磁场。"""
    v = np.asarray(vel, dtype=float).ravel()
    v3 = _as3(v, "vel")
    f = float(q) * (_as3(e_field, "e_field") + np.cross(v3, _as3(b_field, "b_field")))
    return f[:2] if v.size == 2 else f


@dataclass(frozen=True)
class Particle:
    mass: float
    charge: float
    pos: np.ndarray
    vel: np.ndarray
    e_field: np.ndarray = field(default_factory=lambda: np.zeros(3))
    b_field: np.ndarray = field(default_factory=lambda: np.zeros(3))
    extra_force: Callable[[float, np.ndarray, np.ndarray], np.ndarray] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pos", np.asarray(self.pos, dtype=float))
        object.__setattr__(self, "vel", np.asarray(self.vel, dtype=float))
        object.__setattr__(self, "e_field", np.asarray(self.e_field, dtype=float))
        object.__setattr__(self, "b_field", np.asarray(self.b_field, dtype=float))
        if self.pos.size != self.vel.size:
            raise ValueError(f"pos/vel 维数不一致：{self.pos.size} vs {self.vel.size}")
        if self.pos.size == 2 and self.b_field.size == 3:
            if self.b_field[0] != 0.0 or self.b_field[1] != 0.0:
                raise ValueError("二维粒子只能有垂直纸面的 Bz，Bx/By 请用三维粒子")
        if self.pos.size == 2 and self.e_field.size == 3:
            object.__setattr__(self, "e_field", self.e_field[:2])

    def net_force(self, t: float, pos: np.ndarray, vel: np.ndarray) -> np.ndarray:
        """洛伦兹 + extra_force（重力/阻力等场景附加力）；直接喂给 integrator.integrate(particle=…)。"""
        p = np.asarray(pos, dtype=float)
        v = np.asarray(vel, dtype=float)
        f = lorentz(self.charge, v, self.e_field, self.b_field)
        if self.extra_force is not None:
            add = np.asarray(self.extra_force(t, p, v), dtype=float).ravel()
            if add.size != f.size:
                raise ValueError(f"extra_force 返回 {add.size} 分量，粒子是 {f.size} 维")
            f = f + add
        return f

    def at(self, pos: Sequence[float], vel: Sequence[float]) -> "Particle":
        """同一粒子换状态（场与质量/电荷不变）——轨迹回读成画面元素时用。"""
        return Particle(mass=self.mass, charge=self.charge, pos=pos, vel=vel,
                        e_field=self.e_field, b_field=self.b_field,
                        extra_force=self.extra_force)
