"""F-10：渲染后自检——全片时间轴扫描 + 每镜首末帧拼图（第四轮整改轮，Audit_batch_v7_cross.md §6）。

动机：batch_v7 两轮独立评审分别抽了 335 张 1920×1080 网格帧（3s 间隔）与 148 张定点帧
（每镜 a/b/c 三点），**没有一帧落在镜头边界的 0.20~0.63s 黑段上**——时间点抽样在结构上看
不见边界现象，只有全片时间轴扫一遍滤镜才能抓到（SubTask 48 教训）。本模块把这件事做成
出片后自动跑的一步，而不是靠评审 agent 下一轮再抽样撞运气。

两件事：
  * `scan_boundaries()`：逐帧读 RGB，找"画面上什么都没有"的帧（max(RGB) <= ink 阈值），
    按帧号聚成区间，再与 Plan 的镜头累积秒数对齐，标出每个区间是"落在镜头边界/片头片尾"
    还是"镜内异常空白"（后者才是新缺陷——边界黑场在当前设计里不存在，F-2 之后 INTRO/OUTRO
    归零，若扫到任何边界区间，这本身就是回归信号）。
  * `contact_sheet()`：抓每镜头的首帧与末帧，拼成一张网格 PNG（评审 brief 里要求的
    "9~12 格/张、每格缩到 640×360"同一套口径），供人工或评审 agent 一次 Read 看完全片。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from . import mux

INK_THRESHOLD = 60     # 与 .local/f2_check/blankscan.py 同一把尺：max(RGB) > 60 才算"有墨"
BOUNDARY_TOL = 0.12     # 判定"区间落在镜头边界上"的秒级容差（半帧误差 + 取整余量）
# 81-G3 裁定：保留 0.12s 不收紧。边界时刻改走 mux.cumulative_offsets 的帧网格口径后，
# 逐镜累积漂移这一路误差源已经消失，剩下的 0.12s 覆盖的是 ffmpeg 自己报帧率/时间戳的
# 取整（15fps 下一帧 0.067s，0.12s ≈ 1.8 帧）；收紧到 1 帧以内会让正常边界黑段被误判成
# 镜内异常，而 F-2 之后边界本不该有黑段——误报噪声比漏报更难复盘，故不动。
CELL_SIZE = (640, 360)  # 拼图单格像素，与评审 brief 的批量判读口径一致


def _ffprobe_resolution_fps(video: Path) -> tuple[int, int, float]:
    """从 ffmpeg -i 的 stderr 里解析 WxH 与 fps（本构建无 ffprobe，口径与 mux.probe_duration 一致）。"""
    r = subprocess.run(
        [mux._ffmpeg_bin(), "-hide_banner", "-i", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"Video:.*?,\s*(\d+)x(\d+)(?:\s*\[[^\]]*\])?.*?([\d.]+)\s*fps", r.stderr or "")
    if not m:
        raise RuntimeError(f"无法从 ffmpeg 输出解析分辨率/帧率：{video}")
    return int(m.group(1)), int(m.group(2)), float(m.group(3))


def _frames(video: Path, w: int, h: int):
    """按 rgb24 原始帧流式读取，不落盘（与 .local/f2_check/blankscan.py 同一口径）。

    batch_v8 实测：fullhd 单帧 6.2MB（1920×1080×3），按"每帧一次 `readinto` 循环补满"读
    120s/3603 帧要 87s，改成**大块顺序读取**（4MB 一块，攒够再切帧）只要 32s——逐帧切分
    本身的调用开销才是瓶颈，不是管道缓冲区大小（纯 ffmpeg 解码同一条片子只要 2.2s，
    Python 侧消费管道才是大头）。draft 480p 单帧仅 1.2MB，没有暴露这个量级的差异。
    """
    size = w * h * 3
    chunk = 1024 * 1024 * 4
    p = subprocess.Popen(
        [mux._ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-i", str(video),
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, bufsize=chunk * 2,
    )
    n = 0
    assert p.stdout is not None
    pending = bytearray()
    pos = 0  # pending[:pos] 是已切出去的帧，攒到一定量再整体回收，避免逐帧 O(n) 搬移
    try:
        while True:
            buf = p.stdout.read(chunk)
            if not buf:
                break
            pending += buf
            while len(pending) - pos >= size:
                # 必须拷贝断开与 pending 的内存关联：np.frombuffer 是零拷贝视图，
                # 调用方 yield 消费完之后这里还会继续 `pending += buf` 做扩张，
                # bytearray 在仍有视图引用它时拒绝 resize（BufferError），实测验证过。
                frame = np.frombuffer(pending, np.uint8, count=size, offset=pos).reshape(h, w, 3).copy()
                yield n, frame
                n += 1
                pos += size
            if pos > chunk * 4:  # 已消费部分攒多了才整体丢弃一次，把搬移摊薄
                del pending[:pos]
                pos = 0
    finally:
        p.stdout.close()
        p.wait()


def _quantize_sec(sec: float, grid: int | None) -> float:
    """单镜时长量化，与 `mux.cumulative_offsets` 内部同口径：给 grid 按整帧、否则按整数微秒。"""
    g = grid or 1_000_000
    return int(round(float(sec) * g)) / g


def _shot_bounds(plan: dict, fps: float | None = None) -> list[tuple[float, float]]:
    """逐镜 [起点, 终点) 秒。

    81-G3（A2 移交）：累加口径改走 `mux.cumulative_offsets`——此前三处裸浮点 `offset += sec`
    已经统一收成这一个真源，只有这里还各走各的。边界时刻不是装饰：`scan_boundaries` 是拿
    它去对**帧号**（n/fps）的，而 scene.py 的每镜帧数 == round(seconds×fps)，两条轴各自取整
    会随镜数线性错开（实测 49 镜 × 3.34s 在 15fps 下差到 0.32s = 5 帧 > BOUNDARY_TOL），
    本该判"落在边界"的黑段会被算成镜内异常、反之漏报。
    给 fps（ffmpeg 实测帧率，本构建全是整数帧率：`-q l`=15、`-q m`/fullhd=30）时按帧网格
    量化，与渲染轴逐帧重合；不给时按整数微秒累加，数值与旧裸累加在浮点残差内一致（≤1e-9，
    逐镜取整噪声归零），兼容无渲染上下文的调用（单测、只拿 Plan 算账）。
    """
    secs = [float(shot["seconds"]) for shot in plan["shots"]]
    if not secs:
        return []
    grid = int(round(fps)) if fps else None
    starts = mux.cumulative_offsets(secs, fps=grid)
    bounds = []
    for i, sec in enumerate(secs):
        start = starts[i]
        # 末镜终点没有"下一镜起点"可借，按同一口径量化该镜时长后加在起点上
        end = starts[i + 1] if i + 1 < len(starts) else start + _quantize_sec(sec, grid)
        bounds.append((start, end))
    return bounds


def _boundary_times(plan: dict, fps: float | None = None) -> list[float]:
    bounds = _shot_bounds(plan, fps)
    total = sum(b[1] - b[0] for b in bounds) if bounds else 0.0
    return sorted({0.0, total, *(t for pair in bounds for t in pair)})


def _group_runs(frame_numbers: list[int]) -> list[list[int]]:
    """把连续帧号聚成闭区间 [a, b]（纯函数，不碰 I/O，方便单测）。"""
    runs: list[list[int]] = []
    for n in frame_numbers:
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return runs


def classify_runs(runs: list[list[int]], fps: float, boundary_times: list[float]) -> list[dict]:
    """逐个空白帧区间判定"是否落在镜头边界上"（纯函数：输入帧号区间+帧率+边界时刻，不碰 I/O）。

    "落在边界上"要同时满足两条，缺一条都当异常上报：
      ①区间本身足够短（≤BOUNDARY_TOL，正常边界黑场最多几帧）；
      ②区间**跨住**某个边界点（边界点落在 [start_s, end_s] 内，不是只沾到一个端点）——
        否则一个起点刚好对上边界、但一路黑到镜尾的区间会被误判成"正常"，那正是真正的回归。
    边界本身在当前渲染（F-2 硬切）下不应再出现任何黑段，所以哪怕边界区间命中也要如实报出来，
    不能因为"是边界"就假装正常——F-2 之前的旧片正是边界有黑段，这条判定要能把回归抓回来。
    """
    out = []
    for a, b in runs:
        start_s, end_s = a / fps, (b + 1) / fps
        short_enough = (end_s - start_s) <= BOUNDARY_TOL
        at_boundary = short_enough and any(start_s - BOUNDARY_TOL <= t <= end_s + BOUNDARY_TOL
                                           for t in boundary_times)
        out.append({"start_s": round(start_s, 3), "end_s": round(end_s, 3),
                   "frames": b - a + 1, "at_boundary": at_boundary})
    return out


def _is_blank(frame: np.ndarray, ink_threshold: int) -> bool:
    """判定"画面上什么都没有"：有任何像素任一通道超过阈值就不是空白（纯函数，方便单测）。

    实测（batch_v8 fullhd）：原来的 `frame.max(axis=2) > thr).sum() == 0` 要精确数出
    着墨像素数再判等于零，对 3603 帧跑了 187.6s；改成 `.any()` 短路（一旦某通道任意像素
    超阈值就立即为真，不必算完整幅）后同样数据集只要数秒——绝大多数帧都不是空白，
    短路带来的收益远大于黑帧那极少数情况下仍要扫完三个通道的代价。
    """
    gt = frame > ink_threshold
    return not (gt[:, :, 0].any() or gt[:, :, 1].any() or gt[:, :, 2].any())


def scan_boundaries(video: Path, plan: dict, ink_threshold: int = INK_THRESHOLD) -> dict:
    """扫全片，返回空白帧区间与"是否落在镜头边界/片头片尾"的判定。

    返回 {fps, total_frames, blank_runs:[{start_s,end_s,at_boundary}], unexpected: bool}。
    `unexpected` 为 True 时代表存在**不落在任何镜头边界上**的空白区间——这才是需要人去看的信号。
    """
    w, h, fps = _ffprobe_resolution_fps(video)
    boundary_times = _boundary_times(plan, fps)

    blanks: list[int] = []
    n_frames = 0
    for n, frame in _frames(video, w, h):
        n_frames += 1
        if _is_blank(frame, ink_threshold):
            blanks.append(n)

    out_runs = classify_runs(_group_runs(blanks), fps, boundary_times)
    return {
        "fps": fps, "resolution": f"{w}x{h}", "total_frames": n_frames,
        "blank_runs": out_runs,
        "unexpected": any(not r["at_boundary"] for r in out_runs),
        "any_blank": bool(out_runs),
    }


def contact_sheet(video: Path, plan: dict, out_png: Path, cols: int = 4) -> Path:
    """每镜头首帧+末帧各抓一张，拼成网格 PNG（评审批量判读同一口径：一张 sheet 一次 Read）。

    末帧取"该镜最后一帧之前 1/fps 秒"而不是镜头终点本身——终点秒正好是下一镜的第一帧，
    `-ss <终点>` 在部分 ffmpeg 构建上会寻到下一个关键帧，抓到的其实是下一镜画面。
    """
    _, _, fps = _ffprobe_resolution_fps(video)
    bounds = _shot_bounds(plan, fps)
    # 尾帧退让 1.5 帧而不是半帧：`-ss` 落在最后一帧的后半区间时，部分 ffmpeg 构建解不出
    # 完整帧（已验证：半帧退让在片尾那一镜稳定抓不到帧，1.5 帧退让稳定可抓）。
    # 全片最后一个时间点还要额外退让：封装 Duration 是四舍五入到帧的近似值，紧贴它的
    # 时间戳可能已经过了最后一个可解码帧——Duration−3 帧这个区间仍会稳定抓空（batch_v8
    # 实测 math_linear_function/physics_acceleration/math_ellipse 三条片子齐齐命中），
    # 退让到 5 帧才稳定可抓，所以末镜的尾帧改成"末镜起点"与"全片末尾退 5 帧"两者取较早
    # ——宁可离镜尾远一点，也不要抓空。
    tail_back = 1.5 / fps
    last_safe = max(0.0, (bounds[-1][1] if bounds else 0.0) - 5.0 / fps)
    cells, labels = [], []
    for i, (start, end) in enumerate(bounds):
        is_last = i == len(bounds) - 1
        tail_t = min(max(start, end - tail_back), last_safe) if is_last else max(start, end - tail_back)
        for tag, t in (("头", start + tail_back), ("尾", tail_t)):
            img = _grab_frame(video, t)
            cells.append(img.resize(CELL_SIZE))
            labels.append(f"镜{i} {tag} {t:.2f}s")

    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (CELL_SIZE[0] * cols, CELL_SIZE[1] * rows), "black")
    for idx, img in enumerate(cells):
        r, c = divmod(idx, cols)
        sheet.paste(img, (c * CELL_SIZE[0], r * CELL_SIZE[1]))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    (out_png.with_suffix(".txt")).write_text("\n".join(labels), encoding="utf-8")
    return out_png


def _grab_frame(video: Path, t: float) -> Image.Image:
    r = subprocess.run(
        [mux._ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-ss", f"{max(t, 0):.3f}",
         "-i", str(video), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True,
    )
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"抓帧失败 @ {t:.3f}s：{video}")
    import io
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


# ---- 82-SE：framediff 密度复检收编（D4/#28 同一把尺）----
# 判据逐字对齐 .local/82D4_evidence/framediff.py：内容带行 [40,410)、相邻帧 |Δ|>16 的像素
# 数 >50 记动帧、每镜去首尾 5 帧。解码走 PyAV（渲染环境无 ffmpeg 二进制也能跑；
# 若 PyAV 缺失则如实抛错，闸门不许静默放行）。
DIFF_BAND = (40, 410)   # 内容带（去掉页眉/字幕带），854×480 冒烟口径；fullhd 由调用方给
DIFF_GRAY = 16
DIFF_MIN_PX = 50
DIFF_TRIM = 5           # 每镜首尾各排除 5 帧（边界装配帧）
STATIC_SHARE_MAX = 0.40
STATIC_SHARE_TEXT_MAX = 0.70   # 纯文字/公式镜豁免阈值（Phase B 书面豁免口径：SD1b 实测 62.5/66%）


def animation_density(video: Path, plan: dict, band: tuple[int, int] = DIFF_BAND,
                      fps: float | None = None) -> dict:
    """逐镜静止帧占比复检。返回 {shots:[{shot,frames,static_share,text_only,over_limit}], unexpected:bool}。

    `text_only`：本镜全部 visual.kind 都在 TEXT_ONLY_KINDS（纯文字版式）→ 用豁免阈值。
    阈值口径来自 ir.MOTION_CAPABLE 批次（#82）：动画化镜头 ≤40%，纯文字镜 ≤70%。
    """
    import av

    from .ir import TEXT_ONLY_KINDS

    bounds = _shot_bounds(plan, fps)
    total_frames = sum(int(round((e - b) * (fps or 0))) for b, e in bounds) if fps else None
    prev = None
    per_frame_changed: list[int] = []
    n = 0
    with av.open(str(video)) as c:
        stream = c.streams.video[0]
        rate = float(stream.average_rate)
        fps = fps or rate
        for frame in c.decode(video=0):
            gray = frame.to_image().convert("L")
            a = np.asarray(gray, dtype=np.int16)[band[0]:band[1], :]
            if prev is not None:
                d = np.abs(a - prev)
                per_frame_changed.append(int((d > DIFF_GRAY).sum()))
            else:
                per_frame_changed.append(0)
            prev = a
            n += 1
    if total_frames and abs(n - total_frames) > len(bounds):
        # 帧数与 Plan 轴对不上（差超过每镜一帧的取整余量）：不能装作检过。
        raise RuntimeError(f"帧数不符：解码 {n}，按 plan 期望 ~{total_frames}（fps={fps}）")

    out = []
    for i, (start, end) in enumerate(bounds):
        lo = int(round(start * fps)) + DIFF_TRIM
        hi = min(int(round(end * fps)) - DIFF_TRIM, n)
        seg = per_frame_changed[max(lo, 1):max(hi, lo + 1)]
        static = sum(1 for x in seg if x <= DIFF_MIN_PX)
        share = round(static / len(seg), 3) if seg else 0.0
        shot = plan["shots"][i]
        kinds = [v.get("kind") for v in shot.get("visuals", []) if isinstance(v, dict)]
        text_only = bool(kinds) and all(k in TEXT_ONLY_KINDS for k in kinds)
        limit = STATIC_SHARE_TEXT_MAX if text_only else STATIC_SHARE_MAX
        out.append({"shot": i, "frames": len(seg), "static_share": share,
                    "text_only": text_only, "limit": limit, "over_limit": share > limit})
    return {"fps": round(fps, 3), "total_frames": n, "shots": out,
            "unexpected": any(s["over_limit"] for s in out)}

