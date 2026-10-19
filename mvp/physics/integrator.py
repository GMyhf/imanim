# -*- coding: utf-8 -*-
"""时间推进：定步长 RK4。受力函数与质量在这里与"物理是什么"解耦——
particle.py 负责给 E/B 场里的合力，本模块只负责把它积分成轨迹。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

ForceFn = Callable[[float, np.ndarray, np.ndarray], Sequence[float]]
PhiFn = Callable[[np.ndarray], float]


@dataclass(frozen=True)
class Trajectory:
    """一次仿真的全部真相：等间隔 dt 的节点数组。渲染端只能插值读取，不得再手填坐标。"""
    t: np.ndarray
    pos: np.ndarray
    vel: np.ndarray
    acc: np.ndarray
    mass: float
    dt: float

    @property
    def t_end(self) -> float:
        return float(self.t[-1])

    def sample(self, times: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
        """三次 Hermite 插值（节点上 pos/vel 都精确），返回 (pos, vel)；越界钳到端点。"""
        q = np.asarray(times, dtype=float)
        return self._interp(q, self.pos), self._interp(q, self.vel)

    def _interp(self, q: np.ndarray, knots: np.ndarray) -> np.ndarray:
        x = np.clip(q, self.t[0], self.t[-1])
        i = np.clip(np.searchsorted(self.t, x, side="right") - 1, 0, len(self.t) - 2)
        h = (self.t[i + 1] - self.t[i])[:, None]
        s = (x - self.t[i])[:, None] / h
        p0, p1 = knots[i], knots[i + 1]
        v0, v1 = self.vel[i] * h, self.vel[i + 1] * h
        h00 = 2 * s**3 - 3 * s**2 + 1
        h10 = s**3 - 2 * s**2 + s
        h01 = -2 * s**3 + 3 * s**2
        h11 = s**3 - s**2
        return h00 * p0 + h10 * v0 + h01 * p1 + h11 * v1

    def speed(self) -> np.ndarray:
        return np.linalg.norm(self.vel, axis=1)

    def kinetic_energy(self) -> np.ndarray:
        return 0.5 * self.mass * np.sum(self.vel**2, axis=1)

    def total_energy(self, phi: PhiFn | None = None, charge: float = 0.0) -> np.ndarray:
        """Ek + q·φ；φ=None 时即纯动能（磁场不做功，洛伦兹情形下 total 应当守恒）。"""
        ek = self.kinetic_energy()
        if phi is None:
            return ek
        return ek + charge * np.array([float(phi(p)) for p in self.pos])

    def crossing(self, cond: Callable[[np.ndarray], bool]) -> float | None:
        """第一次满足 cond(pos) 的时刻：节点间线性定位 + 20 步二分细化；不满足返回 None。"""
        prev_t, prev_ok, prev_p = float(self.t[0]), bool(cond(self.pos[0])), self.pos[0]
        if prev_ok:
            return prev_t
        for k in range(1, len(self.t)):
            t, p = float(self.t[k]), self.pos[k]
            ok = bool(cond(p))
            if ok:
                lo_t, hi_t, lo_p, hi_p = prev_t, t, prev_p, p
                for _ in range(20):
                    mid = 0.5 * (lo_t + hi_t)
                    pm = lo_p + (hi_p - lo_p) * (mid - lo_t) / (hi_t - lo_t)
                    if cond(pm):
                        hi_t, hi_p = mid, pm
                    else:
                        lo_t, lo_p = mid, pm
                return 0.5 * (lo_t + hi_t)
            prev_t, prev_p = t, p
        return None

    def speed_below(self, threshold: float) -> float | None:
        """速率第一次降到 threshold 的时刻（节点间线性定位）；从未低于则 None。"""
        sp = self.speed()
        for k in range(1, len(sp)):
            if sp[k] < threshold:
                t0, t1 = float(self.t[k - 1]), float(self.t[k])
                s0, s1 = float(sp[k - 1]), float(sp[k])
                if s1 == s0:
                    return t1
                return t0 + (t1 - t0) * (s0 - threshold) / (s0 - s1)
        return None


def rk4_step(force: ForceFn, mass: float, t: float, pos: np.ndarray, vel: np.ndarray,
             dt: float) -> tuple[np.ndarray, np.ndarray]:
    """单步定步长 RK4（状态 = pos/vel，加速度 = F/m）。"""
    m = float(mass)

    def a(tt, pp, vv):
        return np.asarray(force(tt, pp, vv), dtype=float) / m

    k1x, k1v = vel, a(t, pos, vel)
    k2x, k2v = vel + 0.5 * dt * k1v, a(t + 0.5 * dt, pos + 0.5 * dt * k1x, vel + 0.5 * dt * k1v)
    k3x, k3v = vel + 0.5 * dt * k2v, a(t + 0.5 * dt, pos + 0.5 * dt * k2x, vel + 0.5 * dt * k2v)
    k4x, k4v = vel + dt * k3v, a(t + dt, pos + dt * k3x, vel + dt * k3v)
    new_pos = pos + dt / 6.0 * (k1x + 2 * k2x + 2 * k3x + k4x)
    new_vel = vel + dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)
    return new_pos, new_vel


def integrate(*, pos: Sequence[float], vel: Sequence[float], mass: float = 1.0,
              force: ForceFn | None = None, particle=None,
              t_end: float = 1.0, dt: float = 0.01) -> Trajectory:
    """从初态积分到 t_end。两种给力方式二选一：
      force=fn(t, pos, vel) -> 合力；particle=Particle -> 用其 net_force(t, pos, vel)。
    节点数 = round(t_end/dt)+1，渲染端按帧数插值即可。"""
    if (force is None) == (particle is None):
        raise ValueError("integrate 需要且只能指定 force 或 particle 之一")
    fn = force if force is not None else particle.net_force
    m = float(mass if force is not None else particle.mass)
    n = max(1, int(round(t_end / dt)))
    h = t_end / n
    p = np.asarray(pos, dtype=float)
    v = np.asarray(vel, dtype=float)
    ts = np.zeros(n + 1)
    ps = np.zeros((n + 1, p.size))
    vs = np.zeros((n + 1, v.size))
    accs = np.zeros((n + 1, p.size))
    ts[0], ps[0], vs[0] = 0.0, p, v
    accs[0] = np.asarray(fn(0.0, p, v), dtype=float) / m
    for k in range(n):
        p, v = rk4_step(fn, m, ts[k], p, v, h)
        ts[k + 1], ps[k + 1], vs[k + 1] = ts[k] + h, p, v
        accs[k + 1] = np.asarray(fn(ts[k + 1], p, v), dtype=float) / m
    return Trajectory(t=ts, pos=ps, vel=vs, acc=accs, mass=m, dt=h)
