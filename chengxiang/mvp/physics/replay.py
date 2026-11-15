# -*- coding: utf-8 -*-
"""81-E2 T1b（G5 裁定方案的本体重放器）：从 ModelSpec 内存重放积分，填充 sim_result sidecar。

背景（.local/81G_report.md §6 + .local/79D2a_report.md）：flow A4 的 physics_gates 六闸门
读 `spec["sim_result"]`（t/pos/vel/acc/energy/net_force）做逐帧物理反证；没有 sidecar 时
只有「单一动力体+可评估恒力」的现算兜底，且 solver 缺 dt/t_end 时直接退化成 skip。
接线位置裁定为 A4（bridge.run_deterministic_A4 在 run_physics_gates 之前）：本模块用
physics.integrate（定步长 RK4）从 ModelSpec 重放一遍，把结果**只写进内存 dict**
（不落盘、不改 modelspec 文件），闸门随后按「真实模拟源」口径比对。

支持子集（与 pipeline/flow/physics_gates._entry_force 同一口径，解析不了就报不支持、不抛错）：
- bodies 恰好一个动力体（mass 非空且非 attrs.static）；
- forces 里该体的全部力都是 gravity（带 g/g_mps2/g_value）或 custom 恒力（magnitude+direction）；
  含 expr/law/B_vec_T/q_C/component_form 等非常力参数 = 不支持；
- 总时长 t_end：spec.solver.t_end 优先，其次调用方给的镜秒（Plan 反灌），都没有 = 不支持；
- 步长 dt：spec.solver.dt 优先，其次调用方/缺省 DEFAULT_DT=0.01；节点数 > MAX_NODES = 不支持。

分层纪律：physics 层不 import pipeline（force 解析子集在这里自带一份小实现，口径注释同源）；
sim_result 里带 replay_source 标记（81G §6 要求「来源可辨：重放 vs 现算」）。
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .integrator import integrate

DEFAULT_DT = 0.01         # solver/调用方都不给步长时的缺省（与 79D2a 现算兜底同口径）
MAX_NODES = 500_000       # 节点上限，超过只记 skip（闸门阈值同源，防重放把内存打爆）

# custom 力里出现这些键 = 力不是常矢量，重放子集不支持（与 physics_gates._entry_force 同步）。
_BANNED_CUSTOM_KEYS = ("expr", "law", "B_vec_T", "q_C", "component_form")


class ReplayUnsupported(Exception):
    """该 spec 不在可机械重放子集内 → 调用方记 skip，不算失败、不炸 A4。"""


def _num(v):
    """数值 or {"value":x, unit} or 2 维向量 → float / np.ndarray。解析不了抛 ReplayUnsupported。"""
    if isinstance(v, dict):
        if "value" not in v:
            raise ReplayUnsupported(f"参数 dict 缺 value：{v!r}")
        return _num(v["value"])
    if isinstance(v, bool):
        raise ReplayUnsupported(f"布尔不是数值：{v!r}")
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return np.asarray([_num(x) for x in v], dtype=float)
    raise ReplayUnsupported(f"无法解析数值 {v!r}")


def _dir_vec(direction) -> np.ndarray:
    """方向：'±x/±y' 字符串或 2 维向量；其余不支持（口径同 physics_gates._dir_vec）。"""
    if isinstance(direction, str):
        try:
            return {"+x": np.array([1.0, 0.0]), "-x": np.array([-1.0, 0.0]),
                    "+y": np.array([0.0, 1.0]), "-y": np.array([0.0, -1.0])}[direction]
        except KeyError:
            raise ReplayUnsupported(f"方向轴标记 {direction!r} 不在 ±x/±y") from None
    v = _num(direction)
    if isinstance(v, np.ndarray) and v.size == 2:
        return v
    raise ReplayUnsupported(f"方向不是矢量/轴向标记：{direction!r}")


def _entry_force(f: dict, mass: float) -> np.ndarray:
    """单条力声明 → 常力矢量；非常力 = ReplayUnsupported（口径同 physics_gates._entry_force）。"""
    t = str(f.get("type") or "")
    p = f.get("params") or {}
    if t == "gravity":
        g = p.get("g", p.get("g_mps2", p.get("g_value")))
        if g is None:
            raise ReplayUnsupported("gravity 力缺 g/g_mps2 参数")
        d = p.get("dir", [0.0, -1.0])
        return mass * _num(g) * _dir_vec(d)
    if t == "custom":
        for banned in _BANNED_CUSTOM_KEYS:
            if banned in p:
                raise ReplayUnsupported(f"custom 力含不可机械评估参数 {banned!r}（非常力）")
        if "magnitude" not in p:
            raise ReplayUnsupported("custom 力缺 magnitude")
        return _num(p["magnitude"]) * _dir_vec(p.get("direction"))
    raise ReplayUnsupported(f"力类型 {t!r} 不在可重放子集（gravity/custom 恒力）")


def _dynamic_bodies(spec) -> list:
    out = []
    for b in (spec.get("bodies") or []):
        if isinstance(b, dict) and b.get("mass") is not None \
                and not (b.get("attrs") or {}).get("static"):
            out.append(b)
    return out


def replay_spec(spec: dict, *, t_end: Optional[float] = None,
                dt: Optional[float] = None) -> dict:
    """就地把重放轨迹写进 spec["sim_result"]（内存，不落盘）。返回记账 dict：
      {"injected": bool, "shot": shot_no, "reason": str, "nodes": int}
    任何不支持/解析失败都只是 injected=False，绝不抛异常（A4 不许被重放炸掉）。"""
    shot = spec.get("shot_no")
    try:
        res = _replay(spec, t_end=t_end, dt=dt)
        res["shot"] = shot
        return res
    except ReplayUnsupported as e:
        return {"injected": False, "shot": shot, "reason": str(e), "nodes": 0}
    except Exception as e:  # noqa: BLE001 重放是增强件不是闸门：任何异常降为 skip，不许上抛
        return {"injected": False, "shot": shot,
                "reason": f"重放内部异常（按不适用记录）：{type(e).__name__}: {e}", "nodes": 0}


def _replay(spec: dict, *, t_end=None, dt=None) -> dict:
    if spec.get("sim_result") is not None:
        return {"injected": False, "reason": "spec 已带 sim_result（R/M2 sidecar 优先，重放不覆盖）",
                "nodes": 0}
    dyn = _dynamic_bodies(spec)
    if len(dyn) != 1:
        return {"injected": False, "nodes": 0,
                "reason": f"重放子集只支持单一动力体（实际 {len(dyn)} 个）"}
    body = dyn[0]
    bid = str(body.get("id"))
    mass = _num(body.get("mass"))
    fs = [f for f in (spec.get("forces") or [])
          if isinstance(f, dict) and str(f.get("body")) == bid]
    consts = [_entry_force(f, mass) for f in fs]

    def force(_t, _p, _v):
        acc = np.zeros(2)
        for c in consts:
            acc = acc + c
        return acc

    solver = spec.get("solver") or {}
    te: Optional[float]
    try:
        te = _num(solver["t_end"]) if solver.get("t_end") is not None else \
            (float(t_end) if t_end is not None else None)
    except (ReplayUnsupported, TypeError, ValueError):
        te = None
    if te is None or not np.isfinite(te) or te <= 0:
        return {"injected": False, "nodes": 0,
                "reason": "拿不到重放总时长（solver.t_end 与镜秒都没有/非法）"}
    try:
        h = _num(solver["dt"]) if solver.get("dt") is not None else \
            (float(dt) if dt is not None else DEFAULT_DT)
    except (ReplayUnsupported, TypeError, ValueError):
        h = float(dt) if dt else DEFAULT_DT
    if not np.isfinite(h) or h <= 0:
        return {"injected": False, "nodes": 0, "reason": f"步长 dt={h!r} 非法"}
    if te / h > MAX_NODES:
        return {"injected": False, "nodes": 0,
                "reason": f"重放节点数 {te / h:.0f} 超过上限 {MAX_NODES}"}

    pos0 = body.get("pos0")
    v0 = body.get("v0")
    p0 = _num(pos0) if pos0 is not None else np.zeros(2)
    u0 = _num(v0) if v0 is not None else np.zeros(2)
    if int(np.atleast_1d(p0).size) != 2 or int(np.atleast_1d(u0).size) != 2:
        return {"injected": False, "nodes": 0, "reason": "重放子集只支持 2 维初态"}
    tr = integrate(pos=p0, vel=u0, mass=mass, force=force, t_end=float(te), dt=float(h))

    spec["sim_result"] = {
        "body": bid,
        "t": np.asarray(tr.t).tolist(),
        "pos": np.asarray(tr.pos).tolist(),
        "vel": np.asarray(tr.vel).tolist(),
        "acc": np.asarray(tr.acc).tolist(),
        "net_force": (np.asarray(tr.acc) * float(tr.mass)).tolist(),
        "mass": float(tr.mass),
        "replay_source": "physics.replay:rk4",
    }
    return {"injected": True, "nodes": int(len(tr.t)),
            "reason": f"重放成功：t_end={te:g}s、dt={h:g}s、{len(tr.t)} 节点（内存注入，未改文件）"}
