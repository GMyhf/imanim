# -*- coding: utf-8 -*-
"""A4' 确定性物理闸门（Spec_AgentFlow_v2 §3.3 六码，纯 Python，无 LLM/无网络）。

79-D2a：只建模块与测试，不接线；第二半由别的 agent 接进 bridge.run_deterministic_A4。

接口（保持简单）：
    load_specs(source)          -> [dict]        # source = modelspec/ 目录 或 dict 列表 或单 dict
    run_physics_gates(specs)    -> {"checked": [6 码], "violations": [{code, shot, detail}],
                                    "skips":    [{code, shot, reason}]}
violations 为空 → 闸门 PASS；skips 是"该镜缺对应字段=不适用"的记录，不算失败。
每个闸门也可单独调用：gate_analytic/gate_unit/gate_energy/gate_graph_sync/
gate_force_balance/gate_mb，签名 (spec, **阈值) -> (violation 文本列表, skip 原因列表)。

各闸门读取的 ModelSpec 字段口径（依据 §3.3 + §3.1 schema + 试制 run 实测形态）：
- PHYS_ANALYTIC：analytic_check.samples（caprod 形 {t,v,x}；peisu 形 {body,t_s,x_m,y_m,vx_mps,…}），
  "模拟结果"来源优先序：spec["sim_result"]（R/M2 sidecar：{t,pos,vel[,acc][,energy][,net_force]}
  或多体 {"bodies":{id:…}}）> 用 physics.integrate 对"单一动力体 + 可机械评估恒力
  （gravity 带 g、custom 带 magnitude+direction）"现场重算。两者都不可得 → skip。
- PHYS_UNIT：bodies[].mass 须有 kg 口径（{"value","unit":"kg"} 或 attrs.mass_unit=="kg"），
  v0/pos0 非零时须有 m/s / m 口径（dict unit 或 attrs.v_unit/pos_unit）；
  全 spec 的 {"value":…} 参数 dict 必须带 unit 且 unit 在 SI 登记表内（§3.3"无量纲质量/无单位初速打回"）。
- PHYS_ENERGY：耗散判据 = 任一 force.type∈{friction,drag} 或约束/属性摩擦系数>0；
  能量序列来源：sim_result 的 energy[] > 由 mass+gravity 现算 KE+PE（PE=−F_gravity·pos）。
  无耗散：漂移 (max−min)/|E0| > 1% 打回；有耗散：能量必须单调不增（容差内）。
- PHYS_GRAPH_SYNC：静态同源检查（§3.3 原文）：graph_sync.source 必须形如 <body_id>.<x|v|a|speed|…>
  且 body 存在于 bodies；axes ∈ {v-t,x-t,F-t}；graph_sync 里出现 points/samples/data/series
  手填采样点 = 打回（图数据只能取积分器输出）。无 graph_sync 字段 → skip。
- PHYS_FORCE_BALANCE：需要轨迹 + 合力序列（可机械评估的恒力 或 sim_result.net_force[]）；
  逐节点抽检：①acc·F_net 点积 <0 → "加速度方向与合力不一致"；②|F_net−m·acc| 相对偏差
  > force_tol → 不平衡闭合失败（静止/匀速段 acc≈0，该式即 §3.3 的"合力≈0"判据）。
- PHYS_MB：仅 sim_type=="particle_gas"。初速样本来源：mb_check.speeds / initial_speeds /
  bodies[].v0（≥min_mb_n 个）；理论 σ：mb_check.sigma > sqrt(k_B·T/m)（mb_check/体的 temperature+mass）
  > 由样本自估 σ̂=sqrt(⟨v²⟩/2)（自估时阈值放宽）。2D Maxwell=Rayleigh，自写 KS（不依赖 scipy）：
  D>1.63/√n（α≈0.01，宽松口径）打回；全同速率直接打回（§4.3 防"全同速率假热运动"）。

红线：无 LLM、无网络、不新增依赖（numpy 为 physics 引擎既有依赖）；常量表不含任何具体题目知识点。
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Callable, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
MVP = HERE.parents[1]                       # mvp/（physics 引擎所在，同 stages.py）

PHYS_CODES = ("PHYS_ANALYTIC", "PHYS_UNIT", "PHYS_ENERGY", "PHYS_GRAPH_SYNC",
              "PHYS_FORCE_BALANCE", "PHYS_MB")

# ---------------------------------------------------------------- 公共阈值（§3.3 口径）
REL_TOL = 1e-4          # PHYS_ANALYTIC 相对误差上限
ENERGY_TOL = 0.01       # PHYS_ENERGY 无耗散机械能漂移上限（1%）
MONO_TOL_REL = 1e-3     # PHYS_ENERGY 耗散场景单调不增的相对容差（数值噪声）
FORCE_TOL = 0.02        # PHYS_FORCE_BALANCE |ΣF−m·a| 相对闭合容差（抽检节点用线性插值，留宽松余量）
MB_CRIT_C = 1.63        # KS 临界系数，α≈0.01（§3.3"宽松"口径）
MB_CRIT_C_EST = 1.95    # σ 由样本自估时参数拟合效应不严格成立 → 放宽到 α≈0.001
MIN_MB_N = 8            # 分布检验最小样本数（低于此不适用）
K_B = 1.380649e-23      # 玻尔兹曼常数（SI 定义值，非题目知识）

# SI 量纲登记表（通用单位，不含题目内容）。"1"/"-"/"dimensionless" 视为显式无量纲标记。
SI_UNITS = {
    "m", "kg", "s", "A", "K", "mol", "cd",
    "N", "J", "W", "C", "V", "Ω", "F", "T", "Hz", "Pa",
    "m/s", "m/s^2", "m/s²", "m·s^-1", "s^-1", "1/s", "1/m", "m^-1",
    "N/C", "N·m", "J/C", "V/m", "C/s", "kg/m^3", "m^2", "m^3",
    "1", "-", "dimensionless", "无量纲",
}
MASS_UNITS = {"kg"}
LENGTH_UNITS = {"m"}
SPEED_UNITS = {"m/s", "m·s^-1"}

# §3.3 禁手填：graph_sync 里出现这些键 = 图数据不是积分器输出
_HAND_FILL_KEYS = ("points", "samples", "data", "series", "keyframes")
_STATE_QTY = {"x", "y", "v", "a", "speed", "vx", "vy", "ax", "ay"}
_SRC_RE = re.compile(r"^([A-Za-z_]\w*)\.(x|y|v|a|speed|vx|vy|ax|ay)$")
_DISSIPATIVE_TYPES = {"friction", "drag"}


class _Unsupported(Exception):
    """该 spec 在本闸门不可机械评估 → 记 skip，不算失败。"""


# ---------------------------------------------------------------- 基础小工具


def _num(v, _depth: int = 0) -> float:
    """数值 or {"value":x, "unit":u} 或 2 维向量 → float / np.array。解析不了抛 _Unsupported。"""
    if isinstance(v, dict):
        if "value" not in v:
            raise _Unsupported(f"参数 dict 缺 value：{v!r}")
        return _num(v["value"], _depth + 1)
    if isinstance(v, bool):
        raise _Unsupported(f"布尔不是数值：{v!r}")
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return np.asarray([_num(x, _depth + 1) for x in v], dtype=float)
    raise _Unsupported(f"无法解析数值 {v!r}")


def _unit_of(v) -> Optional[str]:
    return v.get("unit") if isinstance(v, dict) else None


def _body_ids(spec) -> list:
    return [str(b.get("id")) for b in (spec.get("bodies") or []) if isinstance(b, dict)]


def _is_static(body: dict) -> bool:
    if body.get("mass") is None:
        return True
    return bool((body.get("attrs") or {}).get("static"))


def _dynamic_bodies(spec) -> list:
    return [b for b in (spec.get("bodies") or []) if isinstance(b, dict) and not _is_static(b)]


def _first_num(d: dict, keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


# ---------------------------------------------------------------- 力评估（可机械评估的子集）


def _dir_vec(direction, _default=None) -> np.ndarray:
    """方向：'±x/±y' 字符串 / 2 维向量 / dict{value,unit}。解析不了 → _Unsupported。"""
    if isinstance(direction, str):
        return {"+x": np.array([1.0, 0.0]), "-x": np.array([-1.0, 0.0]),
                "+y": np.array([0.0, 1.0]), "-y": np.array([0.0, -1.0])}[direction]
    v = _num(direction)
    if isinstance(v, np.ndarray) and v.size == 2:
        return v
    raise _Unsupported(f"方向不是矢量/轴向标记：{direction!r}")


def _entry_force(f: dict, mass: float) -> np.ndarray:
    """单条力声明 → 常力矢量；非常力（expr/law/弹簧/摩擦…）→ _Unsupported。"""
    t = str(f.get("type") or "")
    p = f.get("params") or {}
    if t == "gravity":
        g = _first_num(p, ("g", "g_mps2", "g_value"))
        if g is None:
            raise _Unsupported("gravity 力缺 g/g_mps2 参数")
        d = _dir_vec(p.get("dir", [0.0, -1.0]))
        return mass * _num(g) * d
    if t == "custom":
        for banned in ("expr", "law", "B_vec_T", "q_C", "component_form"):
            if banned in p:
                raise _Unsupported(f"custom 力含不可机械评估参数 {banned!r}")
        if "magnitude" not in p:
            raise _Unsupported("custom 力缺 magnitude")
        return _num(p["magnitude"]) * _dir_vec(p.get("direction"))
    raise _Unsupported(f"力类型 {t!r} 不在可机械评估子集（gravity/custom 恒力）")


def _net_force_fn(spec, body: dict) -> tuple[Callable, list]:
    """返回 (fn(t,pos,vel)->合力数组, 力条数)。全部力必须可机械评估，否则 _Unsupported。"""
    mass = _num(body.get("mass"))
    fid = str(body.get("id"))
    fs = [f for f in (spec.get("forces") or []) if isinstance(f, dict)
          and str(f.get("body")) == fid]
    consts = [_entry_force(f, mass) for f in fs]

    def fn(_t, _p, _v):
        acc = np.zeros(2)
        for c in consts:
            acc = acc + c
        return acc
    return fn, len(fs)


# ---------------------------------------------------------------- 轨迹获取（sim_result 优先，其次现场重算）


def _as_nodes(a, n: int) -> np.ndarray:
    """把 (n,d) / (d,n) / (n,) 形态的序列统一成 (n, d) 节点数组。"""
    a = np.asarray(a, dtype=float)
    if a.ndim == 1:
        return a.reshape(n, -1)
    if a.shape[0] != n and a.shape[1] == n:
        return a.T
    return a


def _traj_from_arrays(entry: dict, body: Optional[dict] = None) -> dict:
    if "t" not in entry:
        raise _Unsupported("sim_result 缺 t 数组")
    t = np.asarray(_num(entry["t"]), dtype=float).ravel()
    n = len(t)
    if n < 2:
        raise _Unsupported("sim_result.t 少于 2 个节点")
    out = {"t": t,
           "pos": _as_nodes(_num(entry["pos"]), n) if "pos" in entry else None,
           "vel": _as_nodes(_num(entry["vel"]), n) if "vel" in entry else None}
    out["acc"] = _as_nodes(_num(entry["acc"]), n) if "acc" in entry else None
    out["energy"] = np.asarray(_num(entry["energy"]), dtype=float).ravel() if "energy" in entry else None
    out["net_force"] = _as_nodes(_num(entry["net_force"]), n) if "net_force" in entry else None
    mass = entry.get("mass")
    if mass is None and body is not None and body.get("mass") is not None:
        mass = body.get("mass")
    out["mass"] = _num(mass) if mass is not None else None
    return out


def _get_sim(spec) -> dict:
    """{body_id: traj dict}。sim_result（单轨迹或 {"bodies":{id:…}}）优先；
    否则对『单一动力体+可评估恒力』用 physics.integrate 现场重算；不可得 → _Unsupported。"""
    sr = spec.get("sim_result")
    bodies = {str(b.get("id")): b for b in (spec.get("bodies") or []) if isinstance(b, dict)}
    if isinstance(sr, dict):
        if "bodies" in sr:
            return {bid: _traj_from_arrays(tr, bodies.get(bid))
                    for bid, tr in sr["bodies"].items()}
        bid = str(sr.get("body") or (next(iter(bodies)) if bodies else "default"))
        return {bid: _traj_from_arrays(sr, bodies.get(bid))}
    dyn = _dynamic_bodies(spec)
    if len(dyn) != 1:
        raise _Unsupported(f"动力体数量 {len(dyn)}≠1 且无 sim_result，无法机械取得模拟轨迹")
    body = dyn[0]
    fn, _n = _net_force_fn(spec, body)
    solver = spec.get("solver") or {}
    dt = solver.get("dt")
    t_end = solver.get("t_end")
    if dt is None or t_end is None:
        raise _Unsupported("solver 缺 dt/t_end")
    dt_f, te_f = _num(dt), _num(t_end)
    if te_f / dt_f > 500_000:
        raise _Unsupported(f"solver 节点数 {te_f / dt_f:.0f} 过大，跳过现场重算")
    import sys
    if str(MVP) not in sys.path:
        sys.path.insert(0, str(MVP))
    from physics import integrate                      # 确定性引擎，无 LLM
    tr = integrate(pos=_num(body.get("pos0", [0.0, 0.0])), vel=_num(body.get("v0", [0.0, 0.0])),
                   mass=_num(body.get("mass")), force=fn, t_end=te_f, dt=dt_f)
    return {str(body.get("id")): {"t": np.asarray(tr.t), "pos": np.asarray(tr.pos),
                                  "vel": np.asarray(tr.vel), "acc": np.asarray(tr.acc),
                                  "energy": None, "net_force": None, "mass": float(tr.mass)}}


def _pick_traj(spec, sim: dict, want_body: Optional[str] = None) -> tuple[str, dict]:
    if want_body is not None:
        if want_body not in sim:
            raise _Unsupported(f"样本引用的 body {want_body!r} 不在模拟输出里")
        return want_body, sim[want_body]
    if len(sim) == 1:
        bid = next(iter(sim))
        return bid, sim[bid]
    raise _Unsupported(f"多体轨迹（{len(sim)} 个）但样本未标注 body")


# ---------------------------------------------------------------- 插值与逐点比较


def _hermite(t: np.ndarray, knots: np.ndarray, deriv: Optional[np.ndarray], q: float) -> np.ndarray:
    """一维插值：有导数信息（积分器节点 vel/acc）用三次 Hermite，否则线性。"""
    x = float(np.clip(q, t[0], t[-1]))
    i = int(np.clip(np.searchsorted(t, x, side="right") - 1, 0, len(t) - 2))
    h = t[i + 1] - t[i]
    s = (x - t[i]) / h if h else 0.0
    if deriv is None or h == 0:
        return knots[i] + (knots[i + 1] - knots[i]) * s
    d0 = np.asarray(deriv[i], dtype=float) * h
    d1 = np.asarray(deriv[i + 1], dtype=float) * h
    p0, p1 = knots[i], knots[i + 1]
    h00 = 2 * s**3 - 3 * s**2 + 1
    h10 = s**3 - 2 * s**2 + s
    h01 = -2 * s**3 + 3 * s**2
    h11 = s**3 - s**2
    return h00 * p0 + h10 * d0 + h01 * p1 + h11 * d1


def _qty_at(traj: dict, qty: str, idx: Optional[int], t: float) -> float:
    if qty == "speed":
        sp = np.linalg.norm(traj["vel"], axis=1)
        return float(_hermite(traj["t"], sp, None, t))
    arr = traj[qty]
    dv = None
    if qty == "pos" and traj.get("vel") is not None and traj["vel"].shape == arr.shape:
        dv = traj["vel"]
    elif qty == "vel" and traj.get("acc") is not None and traj["acc"].shape == arr.shape:
        dv = traj["acc"]
    val = _hermite(traj["t"], arr, dv, t)
    return float(val if idx is None else val[idx])


# 样本键 → (轨迹量, 分量)；caprod 形 t/v/x + peisu 形 t_s/x_m/vx_mps 都覆盖
_SAMPLE_MAP = {
    "x": ("pos", 0), "x_m": ("pos", 0),
    "y": ("pos", 1), "y_m": ("pos", 1),
    "vx": ("vel", 0), "vx_mps": ("vel", 0),
    "vy": ("vel", 1), "vy_mps": ("vel", 1),
    "ax": ("acc", 0), "ay": ("acc", 1),
    "v": ("speed", None), "v_mps": ("speed", None), "speed": ("speed", None),
    "v_mp": ("speed", None),
}


def _sample_time(s: dict):
    v = _first_num(s, ("t", "t_s", "time"))
    return None if v is None else _num(v)


# ---------------------------------------------------------------- 闸门 1：PHYS_ANALYTIC


def gate_analytic(spec: dict, rel_tol: float = REL_TOL) -> tuple[list, list]:
    viol, skip = [], []
    ac = spec.get("analytic_check")
    if not isinstance(ac, dict) or not isinstance(ac.get("samples"), list) or not ac["samples"]:
        skip.append("无 analytic_check.samples——解析对拍不适用")
        return viol, skip
    try:
        sim = _get_sim(spec)
    except _Unsupported as e:
        skip.append(f"无可用模拟轨迹：{e}")
        return viol, skip

    # 先归集可比样本（同 body 同量），再按该量幅值定相对误差分母
    comp = []           # (qty_key, body_id, t, ana, traj)
    bad_t = 0
    for s in ac["samples"]:
        if not isinstance(s, dict):
            continue
        t = _sample_time(s)
        if t is None:
            continue
        try:
            _bid, traj = _pick_traj(spec, sim, s.get("body"))
        except _Unsupported as e:
            skip.append(f"样本 {s.get('body')!r}：{e}")
            continue
        if not (traj["t"][0] - 1e-12 <= t <= traj["t"][-1] + 1e-12):
            bad_t += 1
            continue
        for k, ana in s.items():
            if k in ("body",) or k not in _SAMPLE_MAP or isinstance(ana, (list, dict)):
                continue
            try:
                comp.append((k, traj, t, float(ana)))
            except (TypeError, ValueError):
                pass
    if not comp:
        if bad_t:
            skip.append("全部样本时刻越出模拟时窗")
        else:
            skip.append("样本里没有可对拍的数值键（t/x/y/v/vx/vy…）")
        return viol, skip
    refs: dict = {}
    for k, _tr, _t, ana in comp:
        refs[k] = max(refs.get(k, 0.0), abs(ana))
    worst, worst_msg = 0.0, ""
    for k, traj, t, ana in comp:
        qty, idx = _SAMPLE_MAP[k]
        need = "vel" if qty == "speed" else qty
        if traj.get(need) is None:
            skip.append(f"样本键 {k!r} 需要 {need} 数据，但 sim_result 未提供")
            continue
        try:
            num = _qty_at(traj, qty, idx, t)
        except (TypeError, ValueError):
            skip.append(f"样本键 {k!r} 的比较失败：轨迹 {qty} 形态异常")
            continue
        ref = max(refs[k], 1e-12)
        delta = abs(num - ana)
        err = delta / ref if ref > 1e-9 else (0.0 if delta <= 1e-9 else 1.0)
        if err > worst:
            worst = err
            worst_msg = (f"解析对拍超差：{k}(t={t:g}) 解析值 {ana:g} vs 模拟值 {num:.6g}，"
                         f"相对误差 {err:.3e} > {rel_tol:g}")
    if worst > rel_tol:
        viol.append(worst_msg)
    return viol, skip


# ---------------------------------------------------------------- 闸门 2：PHYS_UNIT


def _scan_value_dicts(obj, path: str, viol: list) -> None:
    """递归找 {"value":数值[, "unit":u]} 参数 dict：缺 unit 或 unit 不在 SI 登记表 → 违规。
    value 为非数值（如 complex_trial 的 value_slot：{"value":"a",…} 是画面占位标签）不算物理参数。"""
    if isinstance(obj, dict):
        val = obj.get("value")
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if obj.get("unit") is None:
                viol.append(f"参数 {path} 只有数值没登记量纲（SI）：{val!r}")
            elif str(obj["unit"]) not in SI_UNITS:
                viol.append(f"参数 {path} 的单位 {obj['unit']!r} 不在 SI 量纲登记表内")
        for k, v in obj.items():
            if k != "value":
                _scan_value_dicts(v, f"{path}.{k}" if path else str(k), viol)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scan_value_dicts(v, f"{path}[{i}]", viol)


def gate_unit(spec: dict) -> tuple[list, list]:
    viol, skip = [], []
    bodies = spec.get("bodies")
    if isinstance(bodies, list) and bodies:
        for b in bodies:
            if not isinstance(b, dict):
                continue
            bid = str(b.get("id", "?"))
            attrs = b.get("attrs") or {}
            mass = b.get("mass")
            if mass is None:                       # 静态体不要求质量单位
                pass
            else:
                u = _unit_of(mass) or attrs.get("mass_unit")
                if u is None:
                    viol.append(f"body {bid} 的 mass 无量纲（需 {MASS_UNITS}，或 attrs.mass_unit）")
                elif str(u) not in MASS_UNITS:
                    viol.append(f"body {bid} 的 mass 单位 {u!r} 不是 SI 质量单位 kg")
            for key, uattr, allowed in (("pos0", "pos_unit", LENGTH_UNITS),
                                        ("v0", "v_unit", SPEED_UNITS)):
                v = b.get(key)
                if v is None:
                    continue
                u = _unit_of(v) or attrs.get(uattr)
                try:
                    arr = _num(v)
                except _Unsupported:
                    viol.append(f"body {bid} 的 {key} 不是可解析数值：{v!r}")
                    continue
                nonzero = bool(np.any(np.abs(np.atleast_1d(arr)) > 0))
                if nonzero and (u is None or str(u) not in allowed):
                    viol.append(f"body {bid} 的 {key} 非零但单位缺失/非法（需 {allowed}，"
                                f"或 attrs.{uattr}）：实际 {u!r}")
    else:
        skip.append("无 bodies 字段——质量/初速单位检查不适用")
    _scan_value_dicts({k: spec.get(k) for k in ("forces", "constraints", "bodies", "solver")
                       if spec.get(k) is not None}, "", viol)
    return viol, skip


# ---------------------------------------------------------------- 闸门 3：PHYS_ENERGY


def _is_dissipative(spec) -> bool:
    for f in (spec.get("forces") or []):
        if isinstance(f, dict) and str(f.get("type")) in _DISSIPATIVE_TYPES:
            return True
    for c in (spec.get("constraints") or []):
        p = (c.get("params") or {}) if isinstance(c, dict) else {}
        fr = p.get("friction")
        if isinstance(fr, str) and fr.lower() not in ("none", ""):
            return True
        if fr is not None and not isinstance(fr, str):
            try:
                if _num(fr) > 0:
                    return True
            except _Unsupported:
                pass
    return False


def _energy_series(spec, bid: str, traj: dict) -> np.ndarray:
    if traj.get("energy") is not None:
        return traj["energy"]
    if traj.get("vel") is None:
        raise _Unsupported("轨迹无 energy[] 且缺 vel，无法算机械能")
    mass = traj.get("mass")
    if mass is None:
        raise _Unsupported("轨迹无 energy[] 且质量未知，无法算机械能")
    ke = 0.5 * mass * np.sum(np.asarray(traj["vel"], dtype=float) ** 2, axis=1)
    pe = np.zeros(len(traj["t"]))
    if traj.get("pos") is not None:
        for f in (spec.get("forces") or []):
            if isinstance(f, dict) and str(f.get("body")) == bid and str(f.get("type")) == "gravity":
                pe = pe - np.asarray(traj["pos"]) @ _entry_force(f, mass)   # PE = −F_gravity·pos
    return ke + pe


def gate_energy(spec: dict, energy_tol: float = ENERGY_TOL) -> tuple[list, list]:
    viol, skip = [], []
    try:
        sim = _get_sim(spec)
    except _Unsupported as e:
        skip.append(f"无可用模拟轨迹：{e}")
        return viol, skip
    dissipative = _is_dissipative(spec)
    checked = 0
    for bid, traj in sim.items():
        try:
            e = _energy_series(spec, bid, traj)
        except _Unsupported as ex:
            skip.append(f"body {bid} 能量不可评估：{ex}")
            continue
        except KeyError:
            skip.append(f"body {bid} 轨迹缺 vel/pos，能量不可评估")
            continue
        if len(e) < 2:
            skip.append(f"body {bid} 能量序列不足 2 点")
            continue
        checked += 1
        if dissipative:
            tol = max(MONO_TOL_REL * abs(float(e[0])), 1e-12)
            jumps = np.diff(e)
            bad = int(np.argmax(jumps > tol)) if np.any(jumps > tol) else -1
            if bad >= 0:
                viol.append(f"耗散场景机械能增加：t={traj['t'][bad + 1]:g} 处 "
                            f"{e[bad]:.6g} → {e[bad + 1]:.6g}（要求单调不增）")
        else:
            e0 = float(e[0])
            drift = float(np.max(e) - np.min(e))
            den = max(abs(e0), 1e-12)
            rel = drift / den if den > 1e-9 else (0.0 if drift <= 1e-9 else float("inf"))
            if rel > energy_tol:
                viol.append(f"无耗散场景机械能漂移 {rel:.3%} > {energy_tol:.0%}"
                            f"（E0={e0:.6g}，极差 {drift:.6g}）")
    if not checked and not skip:
        skip.append("没有可评估能量的 body")
    return viol, skip


# ---------------------------------------------------------------- 闸门 4：PHYS_GRAPH_SYNC


def gate_graph_sync(spec: dict) -> tuple[list, list]:
    viol, skip = [], []
    gs = spec.get("graph_sync")
    if not isinstance(gs, dict) or not gs:
        skip.append("无 graph_sync 字段——图体联动不适用")
        return viol, skip
    hand = [k for k in _HAND_FILL_KEYS if k in gs]
    if hand:
        viol.append(f"graph_sync 出现手填图数据键 {hand}：图线必须 == 积分器输出（§3.3 同源性）")
    axes = gs.get("axes")
    if axes is not None and str(axes) not in {"v-t", "x-t", "F-t"}:
        viol.append(f"graph_sync.axes={axes!r} 不在 v-t|x-t|F-t 枚举内")
    src = gs.get("source")
    if not src:
        viol.append("graph_sync.source 缺失：必须指向真实 body 状态量")
        return viol, skip
    m = _SRC_RE.match(str(src).strip())
    if not m:
        viol.append(f"graph_sync.source={src!r} 不是 <body_id>.<x|v|a|speed|…> 状态量引用")
        return viol, skip
    bid = m.group(1)
    if bid not in _body_ids(spec):
        viol.append(f"graph_sync.source 引用不存在的 body {bid!r}（非同源于 bodies 积分输出）")
    return viol, skip


# ---------------------------------------------------------------- 闸门 5：PHYS_FORCE_BALANCE


def _net_force_series(spec, bid: str, traj: dict) -> np.ndarray:
    if traj.get("net_force") is not None:
        return traj["net_force"]
    body = next((b for b in (spec.get("bodies") or [])
                 if isinstance(b, dict) and str(b.get("id")) == bid), None)
    if body is None:
        raise _Unsupported(f"合力序列需要 body {bid} 定义，但 bodies 里找不到")
    fn, _n = _net_force_fn(spec, body)
    base = fn(0.0, np.zeros(2), np.zeros(2))
    return np.tile(base, (len(traj["t"]), 1))


def _accel_series(traj: dict) -> np.ndarray:
    if traj.get("acc") is not None:
        return np.asarray(traj["acc"], dtype=float)
    if traj.get("vel") is None:
        raise _Unsupported("轨迹既无 acc 也无 vel，无法评估加速度")
    t, vel = traj["t"], np.asarray(traj["vel"], dtype=float)
    return np.gradient(vel, t, axis=0)


def gate_force_balance(spec: dict, force_tol: float = FORCE_TOL) -> tuple[list, list]:
    viol, skip = [], []
    try:
        sim = _get_sim(spec)
    except _Unsupported as e:
        skip.append(f"无可用模拟轨迹：{e}")
        return viol, skip
    checked = 0
    for bid, traj in sim.items():
        try:
            f_net = _net_force_series(spec, bid, traj)
        except _Unsupported as ex:
            skip.append(f"body {bid} 合力不可评估：{ex}")
            continue
        if len(traj["t"]) < 2:
            skip.append(f"body {bid} 轨迹点数不足")
            continue
        try:
            a = _accel_series(traj)
        except _Unsupported as ex:
            skip.append(f"body {bid} 加速度不可评估：{ex}")
            continue
        mass = traj.get("mass")
        n = len(traj["t"])
        idxs = np.unique(np.linspace(0, n - 1, min(n, 32)).astype(int))
        checked += 1
        dir_bad = mag_bad = None
        for i in idxs:
            f = np.asarray(f_net[i], dtype=float)
            ai = np.asarray(a[i], dtype=float)
            nf, na = float(np.linalg.norm(f)), float(np.linalg.norm(ai))
            if nf > 1e-9 and na > 1e-9 and float(np.dot(f, ai)) < 0.0:
                if dir_bad is None:
                    dir_bad = (i, traj["t"][i])
            if mass is not None:
                resid = float(np.linalg.norm(f - mass * ai))
                scale = max(nf, mass * na, 1e-12)
                if resid / scale > force_tol and mag_bad is None:
                    mag_bad = (i, traj["t"][i], resid / scale)
        if dir_bad is not None:
            viol.append(f"body {bid} 加速度方向与合力不一致（节点 t={dir_bad[1]:g}）")
        if mag_bad is not None:
            viol.append(f"body {bid} 受力不平衡闭合失败：|ΣF−m·a|/scale={mag_bad[2]:.3%}"
                        f" > {force_tol:.0%}（节点 t={mag_bad[1]:g}；静止/匀速段即合力≈0 判据）")
    if not checked and not skip:
        skip.append("没有可评估受力的 body")
    return viol, skip


# ---------------------------------------------------------------- 闸门 6：PHYS_MB


def _mb_speeds(spec):
    mb = spec.get("mb_check") or {}
    raw = mb.get("speeds") if isinstance(mb, dict) else None
    if raw is None:
        raw = spec.get("initial_speeds")
    if raw is None:
        v0s = [b.get("v0") for b in _dynamic_bodies(spec)]
        raw = v0s if len(v0s) >= MIN_MB_N else None
    if raw is None:
        raise _Unsupported("没有初速样本（mb_check.speeds / initial_speeds / bodies.v0）")
    arr = np.asarray(_num(raw), dtype=float)
    if arr.ndim == 2:
        arr = np.linalg.norm(arr, axis=1)
    return arr


def _mb_sigma(spec, speeds: np.ndarray) -> tuple[float, bool]:
    mb = spec.get("mb_check") or {}
    if isinstance(mb, dict) and mb.get("sigma") is not None:
        return float(_num(mb["sigma"])), False
    T = mb.get("temperature") if isinstance(mb, dict) else None
    m = mb.get("mass") if isinstance(mb, dict) else None
    if T is None or m is None:
        for b in _dynamic_bodies(spec):
            at = b.get("attrs") or {}
            T = T if T is not None else at.get("temperature")
            m = m if m is not None else b.get("mass")
    if T is not None and m is not None:
        return math.sqrt(K_B * _num(T) / _num(m)), False
    return float(np.sqrt(np.mean(speeds**2) / 2.0)), True      # 自估，宽松阈值


def _ks_rayleigh(speeds: np.ndarray, sigma: float) -> float:
    """2D Maxwell 速率 = Rayleigh(σ)，CDF F(v)=1−exp(−v²/2σ²)；自写 KS 统计量。"""
    v = np.sort(np.asarray(speeds, dtype=float))
    n = len(v)
    cdf = 1.0 - np.exp(-(v**2) / (2.0 * sigma**2))
    i = np.arange(1, n + 1)
    return float(np.max(np.maximum(np.abs(i / n - cdf), np.abs((i - 1) / n - cdf))))


def gate_mb(spec: dict, min_n: int = MIN_MB_N,
            crit_c: float = MB_CRIT_C, crit_c_est: float = MB_CRIT_C_EST) -> tuple[list, list]:
    viol, skip = [], []
    if str(spec.get("sim_type")) != "particle_gas":
        skip.append("sim_type 非 particle_gas——分子速率分布检验不适用")
        return viol, skip
    try:
        speeds = _mb_speeds(spec)
    except _Unsupported as e:
        skip.append(str(e))
        return viol, skip
    n = int(len(speeds))
    if n < min_n:
        skip.append(f"初速样本仅 {n} 个（<{min_n}），KS 检验不适用")
        return viol, skip
    if float(np.std(speeds)) == 0.0:
        viol.append(f"分子初速全同（n={n}，σ=0 尖峰）——§4.3 防'全同速率假热运动'")
        return viol, skip
    sigma, estimated = _mb_sigma(spec, speeds)
    if not (sigma > 0) or math.isnan(sigma):
        viol.append("MB 理论速率标度 σ 不可得或非正（缺 mb_check.sigma / temperature+mass）")
        return viol, skip
    d = _ks_rayleigh(speeds, sigma)
    c = crit_c_est if estimated else crit_c
    crit = c / math.sqrt(n)
    if d > crit:
        viol.append(f"初速分布与 Maxwell-Boltzmann（Rayleigh, σ={sigma:.4g}"
                    f"{'，自估' if estimated else ''}）KS 距离 D={d:.4f} > 临界 {crit:.4f}")
    return viol, skip


# ---------------------------------------------------------------- 汇总接口

GATES: dict[str, Callable] = {
    "PHYS_ANALYTIC": gate_analytic,
    "PHYS_UNIT": gate_unit,
    "PHYS_ENERGY": gate_energy,
    "PHYS_GRAPH_SYNC": gate_graph_sync,
    "PHYS_FORCE_BALANCE": gate_force_balance,
    "PHYS_MB": gate_mb,
}


def _applicable_thresholds(fn: Callable, thresholds: dict) -> dict:
    """run_physics_gates 的全局阈值按各闸门签名过滤（签名保持简单）。"""
    import inspect
    try:
        accepted = {p.name for p in inspect.signature(fn).parameters.values()}
    except (TypeError, ValueError):
        return {}
    return {k: v for k, v in thresholds.items() if k in accepted}


def load_specs(source) -> list:
    """source = modelspec 目录（Path/str，读 shot*.json 按镜号排序）、dict 列表或单 dict。"""
    if isinstance(source, dict):
        return [source]
    if isinstance(source, (list, tuple)):
        return [s for s in source if isinstance(s, dict)]
    p = Path(source)
    if p.is_dir():
        def _order(f: Path):
            m = re.match(r"shot(\d+)", f.stem)
            return (int(m.group(1)) if m else 10**9, f.name)
        return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(p.glob("shot*.json"), key=_order)]
    if p.suffix == ".json" and p.is_file():
        return [json.loads(p.read_text(encoding="utf-8"))]
    return []


def run_physics_gates(source, **thresholds) -> dict:
    """六闸门全跑一遍。返回 F-8 兼容形状 {checked, violations, skips}；
    violations 条目 {code, shot, detail}，skips 条目 {code, shot, reason}（不算失败）。
    闸门外壳永不抛异常：spec 结构异常记入 skips（gate 内部异常同样吞成 skip，第二半可查 reason）。"""
    specs = load_specs(source)
    violations, skips = [], []
    for spec in specs:
        shot = spec.get("shot_no")
        for code, fn in GATES.items():
            kwargs = _applicable_thresholds(fn, thresholds)
            try:
                vs, sks = fn(spec, **kwargs)
            except Exception as e:                    # 闸门必须对任意畸形 spec 不崩
                skips.append({"code": code, "shot": shot,
                              "reason": f"闸门内部异常（按不适用记录）：{type(e).__name__}: {e}"})
                continue
            violations.extend({"code": code, "shot": shot, "detail": d} for d in vs)
            skips.extend({"code": code, "shot": shot, "reason": r} for r in sks)
    return {"checked": list(PHYS_CODES), "violations": violations, "skips": skips}
