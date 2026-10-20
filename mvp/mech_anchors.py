"""82-SB mechanism 坐标真源：原子/键/孤对电子锚点表 + 箭头端点引用解析（纯标准库）。

渲染侧（render/scene.py `_v_mechanism`）与闸门侧（pipeline/review.py `_mech_findings`）
共用这一份锚点语义与容差——闸门不 import scene/manim（纪律同 font_metrics），
两侧各算各的坐标就会各说各话，这里把"锚点表怎么建、引用怎么解、错位怎么量"钉成唯一事实源。

锚点引用语法（arrows[].from/to；bonds[].from/to 额外支持裸原子下标引用 {"atom": i}）：
  {"atom": i, "side": "top"|"bottom"|"left"|"right", "gap": 额外留空(可选)}
      —— 第 i 个物种字形盒的缘点；不给 side 时自动选**朝向对端**的那一侧
         （箭尾朝箭头方向出、箭头朝箭尾方向入，读起来才是"钩着电子走"）。
  {"bond": j, "frac": t(默认 0.5), "offset": [dx,dy](缺省不给)}
      —— 第 j 条键的中心连线按 frac 取样，再整体加 offset；键中点=成键电子对的天然锚。
  {"lp": k}  —— 第 k 组孤对电子的中心点（均裂/单电子源的天然锚）。
裸 [x,y] 仍是兜底通道：距最近锚点缘 < MECH_SNAP_RADIUS 自动吸附（how="snap"）；
吸附不上原样保留（how="raw"），闸门按 MECH_ANCHOR_THRESH 判超差并记 warning。
"""

from __future__ import annotations

import math

# ---------------- 容差（单位=场景单位；1080p 下 1 单位 ≈ 135px，按 FULLHD_PX≈135 换算） ----------------
MECH_X_LIMIT = 6.2          # |x| 值域：安全画宽量级（_fit 之前不许越出，越出=脏坐标）
MECH_Y_LIMIT = 3.4          # |y| 值域：内容带量级
MECH_ANCHOR_THRESH = 0.35   # 弧端点距所绑锚点的容差（82D3_rebase §3.2-③ 口径）
MECH_SNAP_RADIUS = 0.30     # 裸坐标自动吸附半径：贴得上就不算错位
MECH_BOND_GAP = 0.06        # 键线端点离字形缘的留空（键不再中心到中心、不再穿字形）
MECH_ATOM_PAD = 0.05        # 原子缘点锚在字形盒外的额外留空
MECH_SPREAD_BUFF = 0.08     # 布局阶段两个物种字形盒之间的最小净距

_SIDES = {"top": (0.0, 1.0), "bottom": (0.0, -1.0), "right": (1.0, 0.0), "left": (-1.0, 0.0)}
_SIDE_ALIASES = {"up": "top", "down": "bottom", "left": "left", "right": "right",
                 "t": "top", "b": "bottom", "r": "right", "l": "left"}


def as_point(v):
    """裸 [x,y] → (x, y)（有限数）；脏值/标量/引用 dict 一律 None——绝不静默把下标当坐标。"""
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        try:
            x, y = float(v[0]), float(v[1])
        except (TypeError, ValueError):
            return None
        if math.isfinite(x) and math.isfinite(y):
            return (x, y)
    return None


def ref_of(v):
    """引用式端点 → ("atom"|"bond"|"lp", 下标, ref字典)；不是引用或下标脏 → None。"""
    if not isinstance(v, dict):
        return None
    for key in ("atom", "bond", "lp"):
        if key in v:
            a = v.get(key)
            if isinstance(a, bool) or not isinstance(a, int) or a < 0:
                return None
            return (key, a, v)
    return None


def species_pos(species):
    """物种位置解析（含缺 pos 的横排兜底），与 _v_mechanism 建表口径逐字一致。
    返回 (每条目 pos|None 列表, 兜底排位列表)；text 为空的条目 pos 记 None 不参与兜底计数。"""
    auto_row = [s for s in species if isinstance(s, dict) and as_point(s.get("pos")) is None]
    out, used = [], 0
    for s in species:
        if not isinstance(s, dict) or not str(s.get("text") or "").strip():
            out.append(None)
            continue
        q = as_point(s.get("pos"))
        if q is None:
            q = ((used - (len(auto_row) - 1) / 2.0) * 2.6, 1.6)
            used += 1
        else:
            used += 1
        out.append(q)
    return out


def box_distance(xy, center, half_w, half_h):
    """点到矩形盒（中心+半宽半高）的最短距离：盒内=0。"""
    dx = max(abs(xy[0] - center[0]) - half_w, 0.0)
    dy = max(abs(xy[1] - center[1]) - half_h, 0.0)
    return math.hypot(dx, dy)


def seg_distance(xy, a, b):
    """点到线段最短距离。"""
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = xy[0] - a[0], xy[1] - a[1]
    ln2 = vx * vx + vy * vy
    if ln2 < 1e-12:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / ln2))
    return math.hypot(wx - t * vx, wy - t * vy)


def _match_atom(xy, atoms, pad=MECH_ATOM_PAD):
    """裸坐标落在哪个原子的字形盒（+pad）里 → 该原子下标；没有 → None。"""
    for i, a in enumerate(atoms):
        if box_distance(xy, a["pos"], a["half_w"] + pad, a["half_h"] + pad) <= 1e-9:
            return i
    return None


def atom_edge(atom, toward=None, side=None, gap=0.0):
    """原子锚点缘：字形盒某侧外缘（含 MECH_ATOM_PAD+gap）；不给 side 时取朝向 toward 的侧。"""
    x, y = atom["pos"]
    hw, hh = atom["half_w"] + MECH_ATOM_PAD + gap, atom["half_h"] + MECH_ATOM_PAD + gap
    s = str(side or "").strip().lower()
    s = _SIDE_ALIASES.get(s, s)
    if s not in _SIDES:
        if toward is not None:
            dx, dy = toward[0] - x, toward[1] - y
            s = ("right" if dx >= 0 else "left") if abs(dx) >= abs(dy) else \
                ("top" if dy >= 0 else "bottom")
        else:
            s = "top"
    ux, uy = _SIDES[s]
    return (x + ux * hw, y + uy * hh)


def build_table(atoms, bonds, lps):
    """锚点表 = 机理图坐标的唯一真源。
    atoms: [{"text", "pos":(x,y), "half_w", "half_h"}]（半宽半高由调用方供：
           渲染侧=实测字形、闸门侧=font_metrics 估算）；
    bonds/lps: props 原样列表（已过滤为 dict）。
    键端点若是裸坐标且落在某原子字形盒内，自动归到该原子中心；
    键线画线端点 p0/p1 按两端字形缘+MECH_BOND_GAP 截短（不再中心穿字）。
    返回 {"atoms": [...], "bonds": [...], "lps": [...]}；脏条目原样留位（下标不漂移）。"""
    tab_atoms = [dict(a) for a in atoms]
    tab_bonds = []
    for b in bonds:
        e0, e1 = b.get("from"), b.get("to")
        ia = ib = None
        p0 = p1 = None
        kind0 = ref_of(e0)
        kind1 = ref_of(e1)
        if kind0 and kind0[0] == "atom" and kind0[1] < len(tab_atoms):
            ia = kind0[1]
            p0 = tab_atoms[ia]["pos"]
        elif kind0:                              # 键端点引用 bond/lp：解成点（罕见但合法）
            p0, _ = _ref_point(kind0, {"atoms": tab_atoms, "bonds": [], "lps": _lp_points(lps)})
        if kind1 and kind1[0] == "atom" and kind1[1] < len(tab_atoms):
            ib = kind1[1]
            p1 = tab_atoms[ib]["pos"]
        elif kind1:
            p1, _ = _ref_point(kind1, {"atoms": tab_atoms, "bonds": [], "lps": _lp_points(lps)})
        if p0 is None:
            p0 = as_point(e0)
            if p0 is not None:
                ia = _match_atom(p0, tab_atoms)
                if ia is not None:
                    p0 = tab_atoms[ia]["pos"]
        if p1 is None:
            p1 = as_point(e1)
            if p1 is not None:
                ib = _match_atom(p1, tab_atoms)
                if ib is not None:
                    p1 = tab_atoms[ib]["pos"]
        entry = {"ia": ia, "ib": ib, "a": p0, "b": p1,
                 "mid": None, "dir": None, "norm": None, "draw": (None, None), "valid": False}
        if p0 is not None and p1 is not None:
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            ln = math.hypot(dx, dy)
            if ln > 1e-9:
                ux, uy = dx / ln, dy / ln
                entry.update(mid=((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0),
                             dir=(ux, uy), norm=(-uy, ux), valid=True)
                t0 = _trim(p0, (ux, uy), ia, ib, tab_atoms) if ia is not None else 0.0
                t1 = _trim(p1, (-ux, -uy), ib, ia, tab_atoms) if ib is not None else 0.0
                g0 = MECH_BOND_GAP if ia is not None else 0.0
                g1 = MECH_BOND_GAP if ib is not None else 0.0
                if t0 + g0 + t1 + g1 < ln * 0.9:
                    q0 = (p0[0] + ux * (t0 + g0), p0[1] + uy * (t0 + g0))
                    q1 = (p1[0] - ux * (t1 + g1), p1[1] - uy * (t1 + g1))
                    entry["draw"] = (q0, q1)
                else:                            # 两原子几乎重叠：不截短，退回全段（布局阶段会先分开它们）
                    entry["draw"] = (p0, p1)
        tab_bonds.append(entry)
    tab_lps = []
    for l in lps:
        tab_lps.append({"pos": as_point(l.get("pos") if isinstance(l, dict) else l)})
    return {"atoms": tab_atoms, "bonds": tab_bonds, "lps": tab_lps}


def _lp_points(lps):
    return [as_point(l.get("pos") if isinstance(l, dict) else l) for l in lps]


def _trim(center_pt, unit_dir, own_i, other_i, atoms):
    """沿 unit_dir 从原子中心走到字形盒缘所需的距离（含留空）。"""
    if own_i is None or own_i >= len(atoms):
        return 0.0
    a = atoms[own_i]
    ux, uy = unit_dir
    cand = []
    if abs(ux) > 1e-6:
        cand.append((a["half_w"] + MECH_ATOM_PAD) / abs(ux))
    if abs(uy) > 1e-6:
        cand.append((a["half_h"] + MECH_ATOM_PAD) / abs(uy))
    return min(cand) if cand else 0.0


def _ref_point(kind_ref, table, toward=None):
    """已拆好的引用三元组 → (点, how)。"""
    key, idx, ref = kind_ref
    if key == "atom":
        atoms = table.get("atoms") or []
        if idx >= len(atoms) or atoms[idx].get("pos") is None:
            return (None, "bad")
        try:
            g = float(ref.get("gap") or 0.0)
        except (TypeError, ValueError):
            g = 0.0
        return (atom_edge(atoms[idx], toward=toward, side=ref.get("side"), gap=g), "atom")
    if key == "bond":
        bonds = table.get("bonds") or []
        if idx >= len(bonds) or not bonds[idx].get("valid"):
            return (None, "bad")
        bd = bonds[idx]
        try:
            fr = float(ref.get("frac") if ref.get("frac") is not None else 0.5)
        except (TypeError, ValueError):
            return (None, "bad")
        fr = max(0.0, min(1.0, fr))
        off = as_point(ref.get("offset")) or (0.0, 0.0)
        a, b = bd["a"], bd["b"]
        return ((a[0] + (b[0] - a[0]) * fr + off[0], a[1] + (b[1] - a[1]) * fr + off[1]), "bond")
    if key == "lp":
        lps = table.get("lps") or []
        if idx >= len(lps) or lps[idx].get("pos") is None:
            return (None, "bad")
        return (lps[idx]["pos"], "lp")
    return (None, "none")


def anchor_candidates(table):
    """吸附/锚定判定用的锚点集：原子四缘点+中心、有效键中点+画线端点、孤对中心。"""
    pts = []
    for a in table.get("atoms") or []:
        if a.get("pos") is None:
            continue
        for s in _SIDES:
            pts.append(atom_edge(a, side=s))
        pts.append(a["pos"])
    for bd in table.get("bonds") or []:
        if bd.get("valid"):
            pts.append(bd["mid"])
            pts.extend(bd["draw"])
    for l in table.get("lps") or []:
        if l.get("pos") is not None:
            pts.append(l["pos"])
    return pts


def snap_point(xy, table, radius=MECH_SNAP_RADIUS):
    """裸坐标吸附：距最近锚点 < radius 就贴过去。返回 (点|None, 吸附距离)。"""
    best, bd = None, float("inf")
    for q in anchor_candidates(table):
        d = math.hypot(q[0] - xy[0], q[1] - xy[1])
        if d < bd:
            best, bd = q, d
    if best is not None and bd < radius:
        return best, bd
    return None, bd


def resolve_endpoint(v, table, toward=None):
    """arrows/bonds 端点统一解析 → (坐标|None, how)；
    how ∈ "atom"|"bond"|"lp"（引用命中）| "snap"（裸坐标被吸附）| "raw"（裸坐标兜底）
    | "bad"（引用下标越界/脏）| "none"（无有效坐标）。"""
    kr = ref_of(v)
    if kr:
        return _ref_point(kr, table, toward=toward)
    xy = as_point(v)
    if xy is None:
        return (None, "none")
    hit, _d = snap_point(xy, table)
    return (hit, "snap") if hit is not None else (xy, "raw")


def resolve_arrow(a, table):
    """一支箭的 from/to 统一解析（渲染侧与闸门侧同一入口）→ (p0, p1, how0, how1)。
    原子引用要给「朝向对端」的缘点：第一轮裸解拿对端近似坐标，第二轮再按 toward 精化侧向。"""
    v0, v1 = a.get("from"), a.get("to")
    q0, h0 = resolve_endpoint(v0, table)
    q1, h1 = resolve_endpoint(v1, table)
    if h0 == "atom" and q1 is not None:
        q0, h0 = resolve_endpoint(v0, table, toward=q1)
    if h1 == "atom" and q0 is not None:
        q1, h1 = resolve_endpoint(v1, table, toward=q0)
    return q0, q1, h0, h1


def anchor_distance(xy, table):
    """点到锚点集的最近距离（原子按盒缘算，盒内=0）——端点锚定断言的尺子。"""
    best = float("inf")
    for a in table.get("atoms") or []:
        if a.get("pos") is not None:
            best = min(best, box_distance(xy, a["pos"], a["half_w"], a["half_h"]))
    for bd in table.get("bonds") or []:
        if bd.get("valid"):
            best = min(best, seg_distance(xy, bd["a"], bd["b"]))
    for l in table.get("lps") or []:
        if l.get("pos") is not None:
            best = min(best, math.hypot(xy[0] - l["pos"][0], xy[1] - l["pos"][1]))
    return 0.0 if best == float("inf") else best


def spread_atoms(atoms, bonds=None, iters=24):
    """结构式布局阶段的整体避让：字形盒互相重叠的原子沿连线对推开（净距≥MECH_SPREAD_BUFF）。
    挪字机器的"错位根源"就在这里被拆除——键线/孤对/箭头全部在避让**之后**才从锚点表取坐标，
    所以推开的是一整张图，而不是把字从键上撕下来。返回新 pos 列表 [(x,y)]。"""
    pos = [list(a["pos"]) if a.get("pos") is not None else [0.0, 0.0] for a in atoms]
    hw = [a.get("half_w", 0.4) for a in atoms]
    hh = [a.get("half_h", 0.25) for a in atoms]
    for _ in range(iters):
        moved = False
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                ox = (hw[i] + hw[j] + MECH_SPREAD_BUFF) - abs(pos[i][0] - pos[j][0])
                oy = (hh[i] + hh[j] + MECH_SPREAD_BUFF) - abs(pos[i][1] - pos[j][1])
                if ox <= 0 or oy <= 0:
                    continue
                moved = True
                dx = pos[j][0] - pos[i][0]
                dy = pos[j][1] - pos[i][1]
                if abs(dx) >= abs(dy):
                    sgn = 1.0 if dx >= 0 else -1.0
                    shift = ox / 2.0 + 1e-4
                    pos[i][0] -= sgn * shift
                    pos[j][0] += sgn * shift
                else:
                    sgn = 1.0 if dy >= 0 else -1.0
                    shift = oy / 2.0 + 1e-4
                    pos[i][1] -= sgn * shift
                    pos[j][1] += sgn * shift
        if not moved:
            break
    return [tuple(p) for p in pos]


def in_range(xy):
    return xy is not None and abs(xy[0]) <= MECH_X_LIMIT and abs(xy[1]) <= MECH_Y_LIMIT


def validate_props(species, bonds, lps, arrows, at_given, n_at, half_est=None):
    """闸门侧机理校验（82-SB 任务 3）：坐标合法性/值域、端点锚定、at 按**有效**箭数。
    返回 (errors, warnings)——errors 打回（阻断，走既有回灌 A3），warnings 记账（裸坐标兜底通道）。
    half_est: 可选 [(hw,hh)]，闸门侧的字体估算；缺省用通用估算 (0.5,0.25)。"""
    errors, warns = [], []
    pos_list = species_pos(species)
    # 锚点真源是否真的存在：species 里至少一条写了 pos，才算「作者用坐标钉结构式」的新写法。
    # 旧 props（species 只有 text/attach、坐标全是裸 [x,y]）没有真源，锚定判定毫无意义——
    # 81-G 的旧口径（裸坐标放行、只在形状上拦）逐字不变，只对带 pos 的写法开 MECH_COORD 通道。
    anchored = any(isinstance(s, dict) and as_point(s.get("pos")) is not None for s in species)
    # 引用语法一旦出现（哪怕 species 没写 pos），坐标校验同样开——脏下标是真错。
    refs_in_use = any(ref_of(x.get(k)) for x in list(arrows) + list(bonds) for k in ("from", "to"))
    check_coords = anchored or refs_in_use
    atoms = []
    for i, s in enumerate(species):
        if not isinstance(s, dict) or not str(s.get("text") or "").strip():
            continue
        q = pos_list[i]
        # 只判「作者亲手写的坐标」：没给 pos 的条目走横排兜底，位置是算出来的，不该被值域打回。
        if check_coords and as_point(s.get("pos")) is not None and not in_range(q):
            errors.append(f"mechanism species[{i}]「{str(s.get('text'))[:12]}」坐标 {list(q)} "
                          f"越出值域（|x|≤{MECH_X_LIMIT}、|y|≤{MECH_Y_LIMIT}）")
        h = half_est[i] if (half_est and i < len(half_est) and half_est[i]) else (0.5, 0.25)
        hw, hh = h
        atoms.append({"text": str(s.get("text")), "pos": q, "half_w": hw, "half_h": hh})
    table = build_table(atoms, bonds, lps)
    n_eff = len(arrows)                      # 非锚点写法沿用 81-G 旧口径：at 长度=声明箭数
    if check_coords:
        for j, bd in enumerate(bonds):
            if not isinstance(bd, dict):
                continue
            e = table["bonds"][j] if j < len(table["bonds"]) else None
            if e is None or e["a"] is None or e["b"] is None:
                errors.append(f"mechanism bonds[{j}] 端点解不出坐标（from={bd.get('from')!r} to={bd.get('to')!r}）")
            elif not (in_range(e["a"]) and in_range(e["b"])):
                errors.append(f"mechanism bonds[{j}] 端点越出值域（|x|≤{MECH_X_LIMIT}、|y|≤{MECH_Y_LIMIT}）")
        for k, l in enumerate(lps):
            q = as_point(l.get("pos") if isinstance(l, dict) else l)
            if q is None:
                errors.append(f"mechanism lps[{k}] 缺有效 pos")
            elif not in_range(q):
                errors.append(f"mechanism lps[{k}] 坐标 {list(q)} 越出值域")
        n_eff = 0
        for i, a in enumerate(arrows):
            if not isinstance(a, dict):
                continue
            q0, q1, h0, h1 = resolve_arrow(a, table)
            pts = []
            for key, v, xy, how in (("from", a.get("from"), q0, h0), ("to", a.get("to"), q1, h1)):
                if how in ("bad", "none"):
                    errors.append(f"mechanism arrows[{i}].{key}={v!r} 解不出有效坐标"
                                  f"（引用须是 {{\"atom\":i}}/{{\"bond\":j}}/{{\"lp\":k}} 或裸 [x,y]）")
                    continue
                if not in_range(xy):
                    errors.append(f"mechanism arrows[{i}].{key} 端点 {list(round2(xy))} 越出值域")
                if how in ("raw", "snap"):
                    d = anchor_distance(xy, table)
                    way = ("已自动吸附到最近锚点" if how == "snap" else "未吸附（离最近锚点偏）")
                    warns.append(f"mechanism arrows[{i}].{key} 用裸坐标兜底（{way}，距锚点 {d:.2f}u）——"
                                 f"建议改锚点引用 {{\"atom\"/\"bond\"/\"lp\": 下标}}；超差会被渲染期 MECH_ARROW_DRIFT 记账")
                    if how == "raw" and d > MECH_ANCHOR_THRESH:
                        errors.append(f"mechanism arrows[{i}].{key} 端点 {list(round2(xy))} 离一切锚点 "
                                      f"{d:.2f}u > 容差 {MECH_ANCHOR_THRESH}u（弯箭头会指向空处——"
                                      f"电子源/汇必须落在原子缘、键中点或孤对点上）")
                pts.append(xy)
            if len(pts) == 2 and pts[0] is not None and pts[1] is not None \
                    and math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]) > 1e-9:
                n_eff += 1
    if n_at and arrows and n_at != n_eff:
        if check_coords:
            errors.append(f"mechanism 的 at 长度 {n_at} ≠ 有效箭数 {n_eff}"
                          f"（端点解得出、两针不重合的箭才占揭示位；脏坐标箭被渲染层静默跳过，"
                          f"按声明箭数对齐会让 at 与口播错位——先修箭端点再对齐 at）")
        else:
            errors.append(f"mechanism 的 at 长度 {n_at} ≠ 箭头数 {n_eff}（一箭一条，长度必须相等；"
                          f"不等时渲染层退化为均匀铺批，揭示与口播脱钩）")
    return errors, warns


def round2(xy):
    return (round(xy[0], 2), round(xy[1], 2))
