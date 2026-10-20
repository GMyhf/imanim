"""82-M0 运动原语库 —— 把「过程动画六律」（Plan_82 D4 报告 §1.3，提炼自复数标杆
``.local/complex_trial/m2_generated.py``）沉淀成可复用函数壳，供 82-SD1~SD3 在
scene.py 各 builder 里调用、82-SE 按 motion_contract.py 验收。

设计口径（对齐 D4 报告，逐条有出处）：
- **六律映射**：①来源去向→``token_chain``/``value_flyin``；②一拍一形→所有原语返回
  ``MotionBeat`` 列表，一个 beat 恰好一次 ``play``；③同值源同步→``Clock``+``advance_to``；
  ④轨迹化→``draw``（Create/Write/GrowArrow/wave/flow 族）；⑤落定强调→``emphasis``
  （≤FX_MAX_SEC）；⑥退场让位→``exit_stage``/``yield_to``（transform 或带 shift 淡出，
  画面不留残影）。
- **帧预算/ fps 解耦**：所有 ``run_time`` 一律经 :func:`snap_run_time` 对齐整帧
  （``run_time = 整数帧 / config.frame_rate``），沿用 scene.py ``FX_MAX_SEC`` 借帧纪律——
  动效只借既有 hold 帧，绝不加长镜头；仿真采样步长 ``SIM_DT = 1/120`` 与渲染帧率解耦
  （标杆文件头明文 + D4 §1.2 探针扫描口径）。
- **不 import scene**：scene.py（82-SB 在途）之后由 SD1 反向 import 本模块，本模块只依赖
  manim 核心 API，避免循环依赖。``FX_MAX_SEC`` 与 scene.py 双源同值（沿 CALLOUT_* 的
  既有惯例：改一处必须改两处）。
- **引擎接线协议（给 SD1）**：builder 用 :func:`mount_motion` 把 beats 挂在返回组上
  （``mob._motion_steps``，每项带 ``cue`` 字幕下标），``_render_shot`` 的 cue 循环里用
  :func:`take_motion` 取回、:func:`play_beats` 按 cue 播放——讲到哪动到哪（六律 2）。

每个原语的 docstring 首行回答「这个运动让观众理解了什么」（Plan_82 §3 动画红线）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    YELLOW,
    ApplyMethod,
    Circumscribe,
    Create,
    DecimalNumber,
    Dot,
    FadeIn,
    FadeOut,
    Flash,
    GrowArrow,
    GrowFromCenter,
    Indicate,
    LaggedStart,
    Line,
    NumberLine,
    Rectangle,
    ReplacementTransform,
    Scene,
    ShowPassingFlash,
    Text,
    Transform,
    TransformFromCopy,
    VGroup,
    VMobject,
    ValueTracker,
    Write,
    config,
    linear,
    np,
)

__all__ = [
    "SIM_DT", "FX_MAX_SEC", "PAST_OPACITY", "HIGHLIGHT",
    "frame_rate", "snap_run_time", "MotionBeat",
    "token_chain", "value_flyin", "Clock", "advance_to", "clock_evolve", "draw",
    "reveal", "exit_stage", "yield_to", "emphasize", "play_beats",
    "mount_motion", "take_motion", "PRIMITIVES", "DemoMotion",
]

# ---- 全局纪律常量 ----
SIM_DT = 1.0 / 120.0        # 仿真采样步长：与渲染 fps 解耦（标杆文件头/D4 §1.2）
FX_MAX_SEC = 0.5            # 双源同值：= scene.py FX_MAX_SEC，单个强调动画借帧上限
PAST_OPACITY = 0.55         # M6 过往条压暗不透明度（D4 §4.1-M6 建议值）
HIGHLIGHT = YELLOW          # 落定强调缺省色（scene.py 引擎侧用 th["hi"]，接线时可覆写）


def frame_rate() -> float:
    """当前渲染帧率（供借帧记账；所有时长参数最终换算成整帧）。"""
    return max(1.0, float(config.frame_rate))


def snap_run_time(seconds: float) -> float:
    """把任意秒数对齐到整帧：``帧数 = round(seconds × fps)``，返回 帧数/fps。

    六律 6 的工程兑现——动效借既有 hold 帧必须按整帧记账，这样「每镜帧数 ==
    round(seconds × fps)」音画同轴红线在任何 fps 下不破；时长参数只给秒数，
    帧数由 fps 换算，二者解耦。
    """
    fr = frame_rate()
    frames = max(1, int(round(float(seconds) * fr)))
    return frames / fr


@dataclass
class MotionBeat:
    """一个语义节拍 = 一次 play（六律 2「一拍一形」）。

    :param anims: 并行播放的动画列表（可含 ``.animate`` 构建器，由 play 展开）。
    :param run_time: 期望秒数；播放时经 :func:`snap_run_time` 对齐整帧。
    :param cue: 绑定的字幕 cue 下标；None=引擎按顺序就地播放。SD1 接线后
        ``_render_shot`` 用 cue 实现「讲到哪动到哪」，强调/演化与口播同步。
    :param note: 人读注记（该 beat 承载哪个讲解步骤）；交付报告的
        「运动↔讲解语义」对照表直接引用此字段。
    """

    anims: list
    run_time: float = 0.5
    cue: Optional[int] = None
    note: str = ""


def _as_list(x) -> list:
    return list(x) if not isinstance(x, (list, tuple)) else list(x)



def _read_along_bar(m, color=None):
    """当前条背后的高亮色带（无描边、半透明、压在最底层）。"""
    bar = Rectangle(width=max(float(m.width) + 0.35, 0.6),
                    height=max(float(m.height) + 0.22, 0.42),
                    fill_color=color or HIGHLIGHT, fill_opacity=0.16,
                    stroke_width=0)
    bar.move_to(m)
    bar.set_z_index(-2)
    return bar

# ---------------------------------------------------------------------------
# 律① 来源去向 · M1 公式推导
# ---------------------------------------------------------------------------

def token_chain(old, new, *, pairs=None, path_arc: float = 0.0,
                run_time: float = 0.8, lag_ratio: float = 0.12,
                exits=(), enters=(), fade_shift=DOWN * 0.6,
                landing=None, landing_color=None, cue=None) -> list:
    """逐 token 原位 ReplacementTransform：让观众看见「旧式是怎么一步步变成新式的」，
    而不是两张公式图片的切换（标杆 Shot3 过程4 / Shot2 sub→rep→simp 三拍）。

    最小用法::

        old = VGroup(Text("i"), Text("^2"), Text("+1"), Text("=0"))
        new = VGroup(Text("-1"), Text("+1"), Text("=0"))
        beats = token_chain(old, new,
                            pairs=[(old[0], new[0]), (old[1], new[1]),
                                   (old[2], new[2]), (old[3], new[3])],
                            landing=new)     # → [形变 beat, 落定点名 beat]

    :param pairs: ``[(旧token, 新token), ...]`` 显式映射；缺省按序 zip 两个子 mobject
        序列（对应标杆 ``ReplacementTransform(eq[1:], eq2[1:])`` 的逐位接续）。
    :param path_arc: 换位弧（标杆代入拍用 ±PI/2 表示「从别处搬来」的来路）。
    :param exits: 被顶出的旧 token——``FadeOut(shift=…)`` 带方向退场让位（律⑥）。
    :param enters: 无来源的新 token——同方向 ``FadeIn(shift=…)`` 错开半拍接续
        （有来源的 token 必须走 pairs 而不是 enters，否则违反律①）。
    :param landing: 形变完成后的落定点名对象（新式整体或关键 token），追加一个
        ``emphasis`` beat（律⑤，run_time ≤ FX_MAX_SEC）。
    :return: ``list[MotionBeat]``（1~2 个 beat）。
    """
    plist = _as_list(pairs) if pairs is not None else list(
        zip(_submobs(old), _submobs(new)))
    anims = [ReplacementTransform(o, n, path_arc=path_arc) for o, n in plist]
    anims += [FadeOut(m, shift=fade_shift) for m in _as_list(exits)]
    anims += [FadeIn(m, shift=fade_shift) for m in _as_list(enters)]
    if not anims:
        raise ValueError("token_chain: 没有可执行的形变对（pairs/exits/enters 全空）")
    chain = LaggedStart(*anims, lag_ratio=lag_ratio) if len(anims) > 1 else anims[0]
    beats = [MotionBeat([chain], run_time=run_time, cue=cue, note="逐token推导链（旧式→新式）")]
    if landing is not None:
        beats.append(MotionBeat(_emphasis_anims(landing, color=landing_color),
                                run_time=FX_MAX_SEC, cue=cue,
                                note="落定点名（新值是谁、从哪来）"))
    return beats


def _submobs(m) -> list:
    """token 序列取法：VGroup/VMobject 用 submobjects，裸序列原样返回。"""
    return list(m.submobjects) if hasattr(m, "submobjects") else _as_list(m)


# ---------------------------------------------------------------------------
# 律① 来源去向 · M1 数值飞入
# ---------------------------------------------------------------------------

def value_flyin(pairs, *, path_arc: float = -np.pi / 2, run_time: float = 1.0,
                emphasis_on_landing: bool = True, emphasis_color=None,
                cue=None) -> list:
    """数值飞入：把系数从题面/上一行 ``TransformFromCopy`` 复印到目标槽位，让观众看清
    「这个数字是从哪里取的」——代入不是新写一个数，是把已知量搬进方程（标杆 Shot1
    beat4 系数取出 + scene.py ``_derivation_fly`` 的升级版）。

    最小用法::

        beats = value_flyin([(given_row[2], target_eq[4]),      # "2" → I 的槽位
                             (given_row[4], target_eq[6])],
                            path_arc=-PI/2)                     # → [飞入 beat, 落定强调 beat]

    :param pairs: ``[(来源token, 目标槽位token), ...]``；来源留在原地（复印语义），
        目标槽位由调用方预先摆好；「缺省项显式补 0」这类槽位同样适用（标杆纪律）。
    :param path_arc: 飞行弧；默认 -PI/2（标杆 ARC，自上而下弯入，暗示来路方向）。
    :return: ``list[MotionBeat]``。
    """
    ps = _as_list(pairs)
    anims = [TransformFromCopy(src, dst, path_arc=path_arc) for src, dst in ps]
    if not anims:
        raise ValueError("value_flyin: pairs 为空")
    beats = [MotionBeat(anims, run_time=run_time, cue=cue, note="数值飞入（来源→槽位）")]
    if emphasis_on_landing:
        targets = VGroup(*[dst for _, dst in ps]) if len(ps) > 1 else ps[0][1]
        beats.append(MotionBeat(_emphasis_anims(targets, color=emphasis_color),
                                run_time=FX_MAX_SEC, cue=cue, note="落定强调（代入完成）"))
    return beats


# ---------------------------------------------------------------------------
# 律③ 同值源同步 · M2/M3/M4 连续演化
# ---------------------------------------------------------------------------

class Clock:
    """场景时钟：ValueTracker + 关键帧线性插值的通用壳（标杆 Shot4 拨盘/``_adv`` 移植）。

    服务的理解：物理量不是「切换前后两态」，而是**沿时间连续演化**——公式、游标、
    读数、条件灯全部读同一个值源（``np.interp``），杜绝手填关键帧坐标造成的失同步。
    预采样/自检用 ``SIM_DT``，与渲染 fps 完全解耦。

    最小用法::

        ck = Clock({"v": ((0, 2, 6, 8), (0, 6, 6, 0)),     # 名称→(时刻表, 数值表)
                    "x": ((0, 8), (0, 4))})
        tracker = ck.tracker()
        knob.add_updater(lambda m: m.move_to(line.n2p(ck.value("x", tracker.get_value()))))
        scene.add(tracker)
        for t in (2, 4, 8):                       # 时钟 1 秒 = 场景 1 秒
            scene.play(*advance_to(tracker, t).anims, run_time=advance_to(tracker, t).run_time)
    """

    def __init__(self, channels: Optional[dict] = None, start: float = 0.0):
        self._channels: dict = {}
        self._start = float(start)
        self._tracker: Optional[ValueTracker] = None
        if channels:
            for name, keys in channels.items():
                self.channel(name, keys)

    def channel(self, name: str, keys) -> "Clock":
        """登记一条关键帧通道：``keys = ((t0, t1, …), (v0, v1, …))``，时刻须单调不减。"""
        ts, vs = np.asarray(keys[0], dtype=float), np.asarray(keys[1], dtype=float)
        if ts.ndim != 1 or ts.shape != vs.shape or ts.size < 2:
            raise ValueError(f"Clock.channel({name}): 关键帧表需要等长且 ≥2 点的 (时刻, 数值)")
        if np.any(np.diff(ts) < 0):
            raise ValueError(f"Clock.channel({name}): 时刻必须单调不减")
        self._channels[name] = (ts, vs)
        return self

    def names(self) -> tuple:
        return tuple(self._channels)

    def value(self, name: str, t: Optional[float] = None) -> float:
        """t 时刻的通道值（np.interp，两端外推取端点值）。t=None 时读绑定时钟的现值。"""
        ts, vs = self._channels[name]
        if t is None:
            t = self.current()
        return float(np.interp(t, ts, vs))

    def tracker(self) -> ValueTracker:
        """创建场景时钟载体（初值 = start）并自动绑定。"""
        tr = ValueTracker(self._start)
        self.bind(tr)
        return tr

    def bind(self, tracker: ValueTracker) -> "Clock":
        """绑定一个 tracker：此后 ``current()``/``value(name)`` 直接读时钟现值。"""
        object.__setattr__(self, "_tracker", tracker)
        return self

    def current(self) -> float:
        if self._tracker is None:
            raise RuntimeError("Clock.current(): 未绑定 tracker（先 Clock.bind 或用 tracker()）")
        return float(self._tracker.get_value())

    def sample(self, name: str, t0: float = 0.0, t1: Optional[float] = None,
               dt: float = SIM_DT) -> list:
        """按 SIM_DT 预采样通道值 [(t, v), …]（分析自检/离屏校验用，与渲染帧率无关）。"""
        ts = self._channels[name][0]
        t1 = float(ts[-1]) if t1 is None else t1
        n = max(2, int(round((t1 - t0) / dt)) + 1)
        return [(float(t), self.value(name, t)) for t in np.linspace(t0, t1, n)]


def advance_to(tracker: ValueTracker, t_end: float, extra=(), cue=None,
               note: str = "") -> MotionBeat:
    """把场景时钟线性推进到绝对时刻 ``t_end``，附带强调/显现动画并行（标杆 ``_adv``）。

    服务的理解：演化过程中「看到的就是正在变的量」——游标走到哪，读数/公式/条件灯
    同步变到哪；``run_time = |t_end − 当前时钟值|``（时钟 1 秒 = 场景 1 秒），整帧对齐。

    用法：``beat = advance_to(tracker, 3.0, extra=[Flash(lamp)])``
    """
    cur = float(tracker.get_value())
    run_time = max(1.0 / frame_rate(), abs(t_end - cur))
    # 不能用 tracker.animate.set_value：四拍在装配期同时构造，_AnimationBuilder 共用
    # tracker.target，最后一次 set_value(6) 会把前三拍的目标一并改成 6（实测 cue0 就冲终点）。
    # ApplyMethod 每拍独立持有目标，起值在 begin 时读当前值，四拍自然接成 1.5/3/4.5/6。
    anim = ApplyMethod(tracker.set_value, t_end, rate_func=linear)
    return MotionBeat([anim, *_as_list(extra)], run_time=run_time, cue=cue,
                      note=note or f"时钟演化 → t={t_end}")


def clock_evolve(clock: Clock, t_end: float, extra=(), cue=None) -> list:
    """便捷壳：新建（若未绑定）时钟载体并返回一个演化 beat。多段演化请循环
    ``advance_to(tracker, t)``——同一个 tracker 才是「同值源」（六律 3）。"""
    tracker = clock._tracker if clock._tracker is not None else clock.tracker()
    return [advance_to(tracker, t_end, extra=extra, cue=cue)]


# ---------------------------------------------------------------------------
# 律④ 轨迹化 · 描线出现族
# ---------------------------------------------------------------------------

def draw(mobs, *, mode: str = "create", run_time: float = 1.2, lag_ratio: float = 0.15,
         color=None, time_width: float = 0.6, origin=None, cue=None, note: str = "") -> list:
    """描线出现：线是**描出来的**、箭是**长出来的**、场是**铺开的**——让观众看到
    几何/流向的生成过程，而不是整幅贴上成品图（标杆 Create 收束 / GrowArrow 语义）。

    最小用法::

        draw(magnetic_lines, mode="create")            # 磁感线/轨迹/弯箭头 tail→head 逐条描出
        draw(force_arrows, mode="grow_arrow")          # 力箭从作用点长出
        draw(crosses, mode="wave", origin=source_dot)  # ×/· 从源区成波铺开
        draw(loop, mode="flow")                        # 电流方向沿路闪过 ≤1 圈
        draw(math_line, mode="write")                  # 公式逐符号书写

    :param mode:
        ``"create"``     — 沿子路径 Create：轨迹虚线/磁感线/机理弯箭头 **tail→head**
        （Manim 的 Create 从 start 向 end 行进，弯箭头起点即 tail，描出方向=电子流向本身）；
        ``"write"``      — Write 逐符号书写（formula/title 的 A 级底线：不许整块淡入）；
        ``"grow_arrow"`` — GrowArrow 力箭从对象长出（力「有来源、有方向」）；
        ``"wave"``       — 按到 ``origin`` 的距离排序 GrowFromCenter 波次铺场（field 全系）；
        ``"flow"``       — ShowPassingFlash 沿路径循环 ≤1 次（电流/场强方向，D4 M3 上限）。
    :return: ``[MotionBeat]``（一个 beat；多对象自动 LaggedStart 成波）。
    """
    ms = _as_list(mobs)
    if not ms:
        raise ValueError("draw: mobs 为空")
    if mode == "create":
        anims = [Create(m) for m in ms]
    elif mode == "write":
        anims = [Write(m) for m in ms]
    elif mode == "grow_arrow":
        anims = [GrowArrow(m) for m in ms]
    elif mode == "wave":
        ref = None
        if origin is not None:
            ref = np.asarray(origin.get_center(), dtype=float) \
                if hasattr(origin, "get_center") else np.asarray(origin, dtype=float)
        order = sorted(ms, key=lambda m: float(np.linalg.norm(
            (m.get_center() - ref)[:2])) if ref is not None else m.get_center()[0])
        anims = [GrowFromCenter(m) for m in order]
    elif mode == "flow":
        flashes = [ShowPassingFlash(m.copy().set_color(color or HIGHLIGHT),
                                    time_width=time_width) for m in ms]
        anims = [LaggedStart(*flashes, lag_ratio=0)] if len(flashes) > 1 else flashes
    else:
        raise ValueError(f"draw: 未知 mode={mode!r}（create/write/grow_arrow/wave/flow）")
    one = LaggedStart(*anims, lag_ratio=lag_ratio) if len(anims) > 1 else anims[0]
    return [MotionBeat([one], run_time=run_time, cue=cue, note=note or f"描线出现[{mode}]")]


# ---------------------------------------------------------------------------
# 律②⑤ · M6 文本要点族：逐条揭示 + 当前强调 + 过往压暗
# ---------------------------------------------------------------------------

def reveal(items, *, run_time: float = 0.6, dim_opacity: float = PAST_OPACITY,
           shift=RIGHT * 0.25, emphasis: bool = True, emphasis_color=None,
           cue_from: int = 0, final_flash=None, animate_in: bool = True,
           read_along: bool = False) -> list:
    """逐条揭示 + 当前条强调 + 过往条压暗：让观众的注意力跟着讲解走——正在讲的亮、
    讲过的暗、没讲的还没出现（「每一步都要动」在文字镜的最小兑现，成本≈0，D4 §4.1-M6）。

    最小用法::

        beats = reveal(VGroup(line1, line2, line3, line4), cue_from=0)
        # 第 i 个 beat 绑 cue i：FadeIn(当前) + Indicate(当前) + 上一条 set_opacity(0.55)

    :return: ``list[MotionBeat]``，与 items 等长（六律 2：一条一拍）；每个 beat 的
        ``cue`` 按 ``cue_from + i`` 预绑定，SD1 引擎按 cue 分发即「讲到哪动到哪」。
        ``final_flash`` 传入某对象时在末尾追加结论揭晓 beat。
    :param animate_in: 82-SD1a 接线新增。**默认 True=原行为逐字不变**（DemoMotion/单测
        口径不动）。生产渲染器里「逐条出场」已由 scene.collect_reveals 的 ``_reveal_at``
        机制承担（当前行与字幕**同帧** FadeIn，借既有帧、整帧记账，绝不加时长——scene.py
        评审 D9 红线）；若原语再叠一层 FadeIn 就是同一 mobject 同帧两个 Transform 抢插值
        （_fx_for_reveal 注释明令错开），且出场不再免费。故接线时传 False：
        beat 只携带「压暗过往 + 强调当前」这两个内容运动事件，出场时序交给引擎。
    :param read_along: 82-SD1a 帧差验收新增。给每拍追加 ``Circumscribe``
        框选当前条——与口播同步的「读到哪、框到哪」游标。文字 Indicate 的像素位移只在
        峰值越过帧差阈值，整镜静止帧占比 51~53%；框选描边全程移动，让「正在读这一条」
        在画面上持续可见（语义=朗读位置，不是装饰）。默认 False，DemoMotion/单测口径不变。
    """
    ms = _submobs(items)
    if len(ms) < 1:
        raise ValueError("reveal: items 为空")
    bar = None
    if read_along:
        # 卡拉 OK 式高亮带：半透明色带随口播在条目间平移。「正在读这一条」不再只靠
        # 字形缩放（Indicate 峰值位移小、帧差大半落阈值下），而是整条色带持续移动——
        # 观众视线跟着色带走，语义=朗读位置。色带由调用方负责镜尾清理（beat._aux）。
        bar = _read_along_bar(ms[0], emphasis_color)
    beats = []
    for i, m in enumerate(ms):
        anims = [FadeIn(m, shift=shift)] if animate_in else []
        if i > 0:
            anims.insert(0, ms[i - 1].animate.set_opacity(dim_opacity))  # 过往条压暗
        if emphasis:
            anims.append(_indicate(m, emphasis_color))
        if bar is not None:
            if i == 0:
                anims.insert(0, FadeIn(bar))
            else:
                anims.insert(0, Transform(bar, _read_along_bar(m, emphasis_color)))
        beat = MotionBeat(anims, run_time=run_time,
                          cue=None if cue_from is None else cue_from + i,
                          note=f"揭示第{i + 1}/{len(ms)}条（当前条亮、上一条压暗）")
        if bar is not None:
            beat._aux = [bar]
        beats.append(beat)
    if final_flash is not None:
        beats.append(MotionBeat([Flash(final_flash.get_center(), num_lines=12,
                                       line_length=0.35, flash_radius=0.18,
                                       line_stroke_width=3,
                                       time_width=min(0.3, FX_MAX_SEC))],
                                run_time=FX_MAX_SEC, cue=None, note="结论揭晓"))
    return beats


# ---------------------------------------------------------------------------
# 律⑤ 落定强调 · 律⑥ 退场让位
# ---------------------------------------------------------------------------

def _indicate(mob, color=None, scale_factor: float = 1.2):
    return Indicate(mob, scale_factor=scale_factor, color=color or HIGHLIGHT)


def _emphasis_anims(mob, color=None, scale_factor: float = 1.2) -> list:
    if isinstance(mob, (list, tuple)):
        return [_indicate(m, color, scale_factor) for m in mob]
    return [_indicate(mob, color, scale_factor)]


def emphasize(mob, *, kind: str = "indicate", color=None, run_time: float = FX_MAX_SEC,
              scale_factor: float = 1.2, cue=None) -> MotionBeat:
    """落定强调（律⑤）：形变/演化完成后 ≤FX_MAX_SEC 的 Indicate/Flash/扫光点名——
    告诉观众「刚发生的这一步，看这里」。run_time 超预算自动压到上限（借帧纪律）。

    用法：``play_beats(scene, [emphasize(new_eq, kind="sweep", color=th["hi"])])``
    """
    if run_time > FX_MAX_SEC:
        run_time = FX_MAX_SEC
    if kind == "indicate":
        anims = _emphasis_anims(mob, color, scale_factor)
    elif kind == "flash":
        anims = [Flash(mob.get_center(), num_lines=12, line_length=0.3,
                       flash_radius=0.2, line_stroke_width=3, time_width=0.3)]
    elif kind == "sweep":
        anims = [ShowPassingFlash(mob.copy().set_color(color or HIGHLIGHT), time_width=0.35)]
    else:
        raise ValueError(f"emphasize: 未知 kind={kind!r}（indicate/flash/sweep）")
    return MotionBeat(anims, run_time=run_time, cue=cue, note="落定强调")


def exit_stage(mob, *, direction=DOWN, distance: float = 0.6, run_time: float = 0.4,
               cue=None) -> list:
    """退场让位（律⑥）：旧内容带方向淡出（``FadeOut(shift=direction×distance)``），
    告诉观众「它把位置让给了谁」——画面不留残影，新旧衔接有去向。

    用法：``play_beats(scene, exit_stage(old_eq, direction=DOWN))``
    """
    unit = np.asarray([float(direction[0]), float(direction[1]), 0.0], dtype=float)
    nrm = float(np.linalg.norm(unit))
    if nrm:
        unit = unit / nrm
    ms = _as_list(mob)
    return [MotionBeat([FadeOut(m, shift=unit * distance) for m in ms],
                       run_time=run_time, cue=cue, note="方向性退场让位")]


def yield_to(old, new, *, path_arc: float = 0.0, run_time: float = 0.7, cue=None) -> list:
    """换位让位（律⑥强化版）：旧形态**被变形为**新形态（ReplacementTransform），
    连残影都不产生——「它不是消失了，它是变成了下一个」。

    用法：``play_beats(scene, yield_to(eq_old, eq_new, path_arc=PI/2))``
    """
    return [MotionBeat([ReplacementTransform(old, new, path_arc=path_arc)],
                       run_time=run_time, cue=cue, note="旧式→新式 整体换位")]


# ---------------------------------------------------------------------------
# 引擎接线壳（给 SD1 的 _render_shot motion 播放段）
# ---------------------------------------------------------------------------

def play_beats(scene, beats, *, run_time_cap: Optional[float] = None) -> float:
    """按 D4 帧预算纪律播放 beats：每 beat 一次 play、run_time 整帧对齐、
    可封顶（``run_time_cap``，如 FX_MAX_SEC）。返回实际消耗秒数（供借帧记账）。"""
    spent = 0.0
    if isinstance(beats, MotionBeat):
        beats = [beats]
    for b in _as_list(beats):
        rt = b.run_time if run_time_cap is None else min(b.run_time, run_time_cap)
        rt = snap_run_time(rt)
        scene.play(*b.anims, run_time=rt)
        spent += rt
    return spent


def mount_motion(mob, beats):
    """把 beats 挂到 builder 返回组上（``_motion_steps``）。SD1 约定：builder 只产数据，
    引擎 cue 循环按 ``beat.cue`` 分发；已挂 motion_steps 的块不再走整块淡入接管
    （D4 §4.4-① 的兼容口径）。"""
    mob._motion_steps = list(beats)
    return mob


def take_motion(mob) -> list:
    """引擎侧取回挂载的 beats（未挂载返回空表、不抛错——未接线的 kind 自然降级为现状）。"""
    return list(getattr(mob, "_motion_steps", []))


# ---------------------------------------------------------------------------
# 原语登记册：motion_contract.py 的 primitives 字段按这些 id 引用；SE 闸门交叉校验。
# ---------------------------------------------------------------------------

PRIMITIVES = {
    "token_chain": {"fn": token_chain, "serves": "旧式如何一步步变成新式（推导不是图片切换）"},
    "value_flyin": {"fn": value_flyin, "serves": "代入的数是从哪里取的（来源→槽位可见）"},
    "clock": {"fn": advance_to, "serves": "物理量沿时间连续演化，公式/游标/读数同源同步"},
    "draw": {"fn": draw, "serves": "几何与流向的生成过程（描线/书写/长箭/铺场/环流）"},
    "reveal": {"fn": reveal, "serves": "注意力跟着讲解走：当前亮、过往暗、未讲不现"},
    "exit_stage": {"fn": exit_stage, "serves": "旧内容把位置让给谁（去向可见、无残影）"},
    "yield_to": {"fn": yield_to, "serves": "旧形态变成新形态，不是消失"},
    "emphasis": {"fn": emphasize, "serves": "形变完成后点名（看这一步的新值）"},
}


# ---------------------------------------------------------------------------
# 82-M0 冒烟演示片（三镜：公式代入 / 逐条揭示 / 时钟演化）
# 渲染口径与 D4 基线一致（854x480@15fps、每镜恰好 10s、边界硬切、借帧记账）：
#   cd mvp && python -m manim render -ql --media_dir ../.local/82M0_media render/motion.py DemoMotion
# ---------------------------------------------------------------------------

class DemoMotion(Scene):
    """三镜演示：证明用原语拼出的过程动画能把镜内静止帧占比压到 D4 基线（87~89%）以下。

    每镜帧数 == round(10s × fps)（借帧纪律的示范）；内容全部落在 framediff 内容带
    行窗（y ∈ (-2.95, 3.375)）内。"""

    SHOT_SECONDS = (10.0, 10.0, 10.0)
    TH = {"bg": "#ffffff", "fg": "#1a1a1a", "accent": "#1f5fbf",
          "warn": "#c0392b", "key": "#b06d00", "dim": "#5f6670", "hi": "#d35400"}

    # ---- 借帧记账壳：每镜帧数 == round(seconds × fps)，红线不动 ----
    def _play(self, *anims, run_time):
        rt = snap_run_time(run_time)
        self._frames += int(round(rt * frame_rate()))
        self.play(*anims, run_time=rt)

    def _beats(self, beats):
        if isinstance(beats, MotionBeat):
            beats = [beats]
        for b in _as_list(beats):
            self._play(*b.anims, run_time=b.run_time)

    def _wait_frames(self, frames: int):
        if frames <= 0:
            return
        self._frames += frames
        self.wait(frames / frame_rate())

    def _finish_shot(self, idx: int):
        budget = int(round(self.SHOT_SECONDS[idx] * frame_rate()))
        if self._frames > budget:
            raise RuntimeError(f"DemoMotion 镜{idx} 超帧预算：{self._frames}/{budget}——"
                               "动效不许加长镜头（D4 帧预算红线）")
        self._wait_frames(budget - self._frames)
        self._frames = 0

    def _tokens(self, *words, size=34, color=None):
        th = self.TH
        return VGroup(*[Text(w, font_size=size, color=color or th["fg"])
                        for w in words]).arrange(RIGHT, buff=0.18)

    def construct(self):
        self.camera.background_color = self.TH["bg"]
        self._frames = 0
        self._shot1_substitution()
        self._shot2_reveal()
        self._shot3_clock()

    # ---- 镜1：公式代入（token_chain + value_flyin + yield_to + emphasis + exit_stage）----
    def _shot1_substitution(self):
        th = self.TH
        given = self._tokens("I", "=", "2", "A", size=30, color=th["dim"])
        given.move_to([0, 2.2, 0])
        eq = self._tokens("F", "=", "B", "·", "I", "·", "L")
        eq.move_to([0, 1.0, 0])
        eq2 = self._tokens("F", "=", "B", "·", "2", "·", "L")   # I 槽位换成 2（来源=题面）
        eq2.move_to([0, -0.4, 0])
        eq2[4].set_color(th["warn"])
        result = self._tokens("F", "=", "2", "B", "L")
        result.move_to([0, -1.8, 0])

        self._beats(draw(VGroup(given, eq), mode="write", run_time=1.6,
                         note="题面与公式逐符号写出"))
        self._beats(value_flyin([(given[2], eq2[4])], path_arc=-np.pi / 4, run_time=1.2))
        self._beats(token_chain(eq, eq2,
                                pairs=list(zip(eq.submobjects, eq2.submobjects)),
                                exits=[given[2]], landing=eq2[4], cue=0, run_time=1.4))
        self._beats(yield_to(eq2, result, path_arc=np.pi / 6, run_time=1.2))
        self._beats(emphasize(result, kind="sweep", color=th["hi"]))
        self._finish_shot(0)

    # ---- 镜2：逐条揭示 + 当前强调 + 过往压暗（reveal）----
    def _shot2_reveal(self):
        th = self.TH
        title = self._tokens("楞次定律", "·", "四句理解", size=38, color=th["accent"])
        title.move_to([0, 2.6, 0])
        lines = VGroup(
            Text("① 感应电流的磁场总是阻碍原磁通的变化", font_size=28, color=th["fg"]),
            Text("② “阻碍”不是相反，是延缓", font_size=28, color=th["fg"]),
            Text("③ 增反减同：磁通增大时感应场方向相反", font_size=28, color=th["fg"]),
            Text("④ 从能量角度看：阻碍是做功的代价", font_size=28, color=th["fg"]),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to([0, 0.1, 0])

        self._beats(draw(title, mode="write", run_time=1.2, note="标题写出"))
        beats = reveal(lines, run_time=0.7, emphasis_color=th["hi"], final_flash=lines[3])
        gap = int(round(0.6 * frame_rate()))  # 模拟口播 cue 间隔：讲到哪条，哪条才动
        for i, b in enumerate(beats):
            self._beats([b])
            if i < len(beats) - 1:
                self._wait_frames(gap)
        # 镜尾回扫：四句已被逐条讲完，一条流光带观众按顺序过一遍（复盘动线，M6 收束）
        self._beats(draw(lines, mode="flow", run_time=1.8, time_width=0.45,
                         color=th["hi"], note="镜尾回扫：四句按顺序过一遍"))
        self._finish_shot(1)

    # ---- 镜3：时钟连续演化（Clock + advance_to + 同步显现）----
    def _shot3_clock(self):
        th = self.TH
        caption = Text("v-t 连续演化：游标走到哪，速度条与读数就变到哪",
                       font_size=24, color=th["dim"]).move_to([0, -2.4, 0])
        rail = NumberLine(x_range=[0, 4, 1], length=6.0, color=th["fg"]).move_to([0, 1.6, 0])
        # 刻度数字用 Text（Pango）自加——本管线不装 LaTeX（scene.py 文件头纪律）
        ticks = VGroup(*[Text(str(i), font_size=22, color=th["dim"]) for i in range(5)])
        for i, lab in enumerate(ticks):
            lab.next_to(rail.n2p(i), DOWN, buff=0.12)
        self._beats(draw(VGroup(rail, ticks, caption), mode="create", run_time=1.4))

        ck = Clock({"v": ((0.0, 2.0, 6.0, 8.0), (0.0, 6.0, 6.0, 0.0)),
                    "x": ((0.0, 8.0), (0.0, 4.0))})
        tracker = ck.tracker()
        knob = Dot(color=th["warn"], radius=0.11)
        knob.add_updater(lambda m: m.move_to(rail.n2p(ck.value("x", tracker.get_value()))))
        vbar = Line(UP, DOWN, stroke_color=th["accent"], stroke_width=6)
        vbar.add_updater(lambda m: (
            m.move_to([rail.n2p(ck.value("x", tracker.get_value()))[0], -0.6, 0]),
            m.set_stroke(width=6).scale_to_fit_height(
                max(0.05, 1.6 * ck.value("v", tracker.get_value()) / 6.0))))
        lab = Text("v = 0.0 m/s", font_size=30, color=th["fg"]).move_to([-4.6, -0.4, 0],
                                                                        aligned_edge=LEFT)
        lab.add_updater(lambda m: (m.set_text(f"v = {ck.value('v', tracker.get_value()):.1f} m/s"),
                                   m.move_to([-4.6, -0.4, 0], aligned_edge=LEFT)))
        self.add(knob, vbar, lab)

        for t in (2.0, 4.0, 6.0, 8.0):
            extra = [Flash(knob, color=th["hi"], flash_radius=0.3)] if t in (2.0, 8.0) else []
            self._beats(advance_to(tracker, t, extra=extra))
        self._beats(emphasize(lab, kind="sweep", color=th["hi"]))
        self._finish_shot(2)
