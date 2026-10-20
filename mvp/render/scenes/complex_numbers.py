"""complex_numbers.py —— 复数的概念与几何意义（8 镜，Shot1..Shot8）。

约定：
- 只 import ManimCE 顶层符号 + render.scene 封装 + math/cmath；不改 scene.py。
- style=dark：沿用 THEMES["clean"]，语义色标在本文件内联（a/c 蓝、b/d 橙、i 紫、实数灰白、结论绿）。
- 帧预算：每镜类常量 SECONDS=SHOT_SECONDS[n]，construct 末尾调 finish_shot() 精确补齐。
- 数学驱动：点/向量/旋转/模一律由下方辅助函数实时计算，禁止手填关键帧坐标。
- 仿真采样 SIM_DT 与渲染帧解耦，ValueTracker 驱动时按 alpha 插值取样。
"""
import math
import cmath

from manim import *  # noqa: F401,F403  (ManimCE 核心 API，含 np)

# ---------- T() 文本封装（替代 render.scene.T，避免 deepcopy）----------
def T(content, font_size=32, color=WHITE, **kw):
    """轻量级 Text 封装：默认宋体，字号可调。"""
    return Text(str(content), font="SimSun", font_size=font_size, color=color, **kw)

# ---------- 主题 / 语义色（本镜文件内联，替代 render.scene 导入以避免 deepcopy 问题）----------
SAFE_WIDTH = 12.4
CONTENT_TOP = 4.0 - 0.6       # HEADER_BAND=0.6
CONTENT_BOTTOM = -4.0 + 1.05  # SUBTITLE_BAND=1.05
SUBTITLE_BAND = 1.05
HEADER_BAND = 0.6
BG = "#0b0e14"
INK = WHITE                   # 实数轴 / 实数相关
DIM = GREY_A                  # 变暗、被排除项
C_RE = BLUE_C                 # 实部 a / c
C_IM = ORANGE                 # 虚部 b / d
C_I = PURPLE_B                # 虚数单位 i
C_OK = GREEN_C                # 结论 / =0
C_BAD = RED_C                 # Δ<0 判据
C_HALO = GOLD                 # 强调 halo（_reveal_fx 通道）

# ---------- 每镜时长（秒），与 .local/complex_trial/shot_seconds.json 同步（中文配音重跑版） ----------
SHOT_SECONDS = {1: 16.466667, 2: 15.0, 3: 19.533333, 4: 16.0, 5: 13.0, 6: 17.0, 7: 17.0, 8: 12.0}
SIM_DT = 1 / 120           # 仿真采样步长，与渲染 fps 解耦
EPS_T = 1e-3               # 时长校验容差

# ---------- 几何参数（全部落在安全区内） ----------
PARA_X_RANGE = (-2.5, 2.5, 1)        # Shot1 抛物线坐标系
PARA_Y_RANGE = (-0.5, 6.5, 1)
PARA_SIZE = (6.0, 5.2)
PROBE_X0, PROBE_X1 = -2.0, 2.0       # 探针扫描区间
NUMLINE_RANGE = (-2, 2, 1)           # Shot2/4 实数轴小样
NUMLINE_UNIT = 1.2
PLANE_ORIGIN = np.array([-3.6, -1.7, 0.0])  # Shot6/7 复平面原点（场景坐标）
PLANE_UNIT = 1.1
PLANE_X_RANGE = (-1, 4, 1)
PLANE_Y_RANGE = (-1, 3, 1)
EXAMPLE_Z = complex(3, 2)            # 全片具体例 3+2i


# ---------- 数学辅助（实时计算，不手填坐标） ----------
def cmul(z: complex, w: complex) -> complex:
    """复数乘法 (a+bi)(c+di) = (ac-bd) + (ad+bc)i，显式展开。"""
    return complex(z.real * w.real - z.imag * w.imag,
                   z.real * w.imag + z.imag * w.real)


ROT_I = np.array([[0.0, -1.0], [1.0, 0.0]])  # ×i 的旋转矩阵（逆时针 90°）


def times_i(z: complex, use_matrix: bool = False) -> complex:
    """z·i：逆时针旋转 90°。默认复数乘法，可切旋转矩阵实现（二者等价）。"""
    if use_matrix:
        x, y = ROT_I @ np.array([z.real, z.imag])
        return complex(x, y)
    return cmul(z, 1j)


def modulus(a: float, b: float) -> float:
    """|z| = √(a²+b²)。"""
    return math.sqrt(a * a + b * b)


def c2p(z: complex, origin=PLANE_ORIGIN, unit: float = PLANE_UNIT) -> np.ndarray:
    """复数 → 场景坐标（复平面原点 origin、单位长 unit）。"""
    return origin + np.array([z.real * unit, z.imag * unit, 0.0])


def parabola(x: float) -> float:
    """Shot1：y = x² + 1。"""
    return x * x + 1.0


def discriminant(a: float, b: float, c: float) -> float:
    """Δ = b² − 4ac。"""
    return b * b - 4 * a * c


def finish_shot(scene: Scene) -> None:
    """末尾补齐到 scene.SECONDS；超时直接报错，不许静默截断。"""
    pad = scene.SECONDS - scene.time
    if pad < -EPS_T:
        raise RuntimeError(f"{type(scene).__name__} 超时 {-pad:.3f}s")
    if pad > EPS_T:
        scene.wait(pad)


class Shot1(Scene):
    """x²+1=0：左边→抛物线，探针扫描高度恒≥1，判别式 −4<0，x 轴两端外扩铺垫。"""

    SECONDS = SHOT_SECONDS[1]
    SWEEP_T = 6.0                                   # 探针扫描时长（ModelSpec t∈[0,6]s）
    V_PROBE = (PROBE_X1 - PROBE_X0) / SWEEP_T       # 匀速 ≈0.6667 u/s
    COEFFS = (1, 0, 1)                              # a, b, c
    LEFT_X, RIGHT_X = -3.0, 3.2                     # 左栏坐标系 / 右栏公式中心

    @staticmethod
    def _halo(m: Mobject) -> VMobject:
        """_reveal_fx halo：同形描边光晕，置于原物之下。"""
        return m.copy().set_fill(opacity=0).set_stroke(C_HALO, width=10, opacity=0.35)

    def _probe_samples(self):
        """以 SIM_DT 预采样探针轨迹 x(t)，渲染时按 alpha 插值取样（与 fps 解耦）。"""
        n = int(round(self.SWEEP_T / SIM_DT))
        ts = np.linspace(0.0, self.SWEEP_T, n + 1)
        xs = PROBE_X0 + self.V_PROBE * ts
        return ts, xs

    def construct(self):
        self.camera.background_color = BG

        # ---- beat 1：方程淡入并分色 ----
        eq = MathTex("x", "^2", "+1", "=0").scale(1.2)
        eq[0].set_color(C_RE)
        eq[1:3].set_color(INK)
        eq[3].set_color(C_OK)
        eq.move_to([self.RIGHT_X, CONTENT_TOP - 0.8, 0])
        self.play(FadeIn(eq, shift=0.2 * DOWN), run_time=0.8)

        # ---- beat 2：坐标系 + 左边式 Transform 为抛物线 ----
        axes = Axes(
            x_range=PARA_X_RANGE, y_range=PARA_Y_RANGE,
            x_length=PARA_SIZE[0], y_length=PARA_SIZE[1],
            axis_config={"color": INK, "include_tip": True},
        )
        axes.move_to([self.LEFT_X, CONTENT_BOTTOM + 0.15 + PARA_SIZE[1] / 2, 0])
        axes.x_axis.set_color(C_OK)                  # x 轴 = 方程右边 0
        self.play(Create(axes), run_time=0.8)

        curve = axes.plot(parabola, x_range=[PROBE_X0, PROBE_X1], color=INK)
        x_lab = 1.6
        curve_lab = MathTex("y=x^2+1", color=INK).scale(0.8)
        curve_lab.next_to(axes.c2p(x_lab, parabola(x_lab)), RIGHT, buff=0.15)
        self.play(
            TransformFromCopy(eq[0:3], curve),
            FadeIn(curve_lab, shift=0.1 * LEFT),
            run_time=1.2,
        )

        # ---- beat 3：探针匀速扫描，引线长度 L=x²+1 实时读数 ----
        ts, xs = self._probe_samples()
        xt = ValueTracker(xs[0])

        probe = Dot(color=C_RE, radius=0.07)
        probe.add_updater(lambda m: m.move_to(axes.c2p(xt.get_value(), 0)))
        lead = always_redraw(lambda: Line(
            axes.c2p(xt.get_value(), 0),
            axes.c2p(xt.get_value(), parabola(xt.get_value())),
            color=C_RE, stroke_width=4,
        ))
        tip = always_redraw(lambda: Dot(
            axes.c2p(xt.get_value(), parabola(xt.get_value())), color=INK, radius=0.05,
        ))
        readout = VGroup(MathTex("L=", color=INK), DecimalNumber(
            parabola(xs[0]), num_decimal_places=2, color=INK,
        )).arrange(RIGHT, buff=0.08).scale(0.7)

        def _upd_readout(m):
            m[1].set_value(parabola(xt.get_value()))
            m.next_to(lead.get_center(), RIGHT, buff=0.15)

        readout.add_updater(_upd_readout)
        _upd_readout(readout)
        self.play(FadeIn(probe), FadeIn(lead), FadeIn(tip), FadeIn(readout), run_time=0.4)
        self.play(
            UpdateFromAlphaFunc(
                xt, lambda m, a: m.set_value(float(np.interp(a * self.SWEEP_T, ts, xs))),
            ),
            run_time=self.SWEEP_T, rate_func=linear,
        )
        # 顶点 (0,1)：最小高度 1，与 x 轴之间的"缝"
        vertex = axes.c2p(0, parabola(0))
        self.play(Flash(vertex, color=C_HALO, line_length=0.25), run_time=0.4)

        # ---- beat 4：系数飞入判别式，结果 −4 标红 ----
        a, b, c = self.COEFFS
        delta = int(discriminant(a, b, c))
        disc = MathTex(
            r"\Delta=b^2-4ac=", f"{b}", r"^2-4\cdot", f"{a}", r"\cdot", f"{c}",
            "=", f"{delta}", "<0",
        ).set_color(INK)
        for k in (1, 3, 5):
            disc[k].set_color(C_HALO)
        disc[7:9].set_color(C_BAD)
        disc.scale_to_fit_width(min(disc.width, SAFE_WIDTH / 2 - 0.6))
        disc.move_to([self.RIGHT_X, eq.get_y() - 1.6, 0])

        self.play(FadeIn(disc[0]), FadeIn(disc[2]), FadeIn(disc[4]), FadeIn(disc[6]),
                  run_time=0.6)
        self.play(
            TransformFromCopy(eq[0], disc[1]),       # b：x 项系数（缺省 → 0）
            TransformFromCopy(eq[1], disc[3]),       # a：x² 项系数
            TransformFromCopy(eq[2], disc[5]),       # c：常数项
            run_time=1.0,
        )
        halo = self._halo(disc[7:9])
        self.play(FadeIn(disc[7:9]), FadeIn(halo), run_time=0.5)
        self.play(Indicate(disc[7:9], color=C_BAD), run_time=0.5)

        # ---- beat 5：x 轴两端轻微延展闪烁（向外扩，铺垫下镜） ----
        x_axis = axes.x_axis
        self.play(
            x_axis.animate(rate_func=there_and_back).stretch(1.08, 0),
            Flash(x_axis.get_start(), color=C_HALO, line_length=0.2),
            Flash(x_axis.get_end(), color=C_HALO, line_length=0.2),
            run_time=1.0,
        )

        finish_shot(self)


class Shot2(Scene):
    """扩充数集：数轴外引入 i，i 代入 x²+1=0，i² 换成 −1，相消为 0 亮绿。"""
    SECONDS = SHOT_SECONDS[2]
    # ---- 场景常量（位置均由数轴/复数计算得出，此处只定锚点与节拍时长） ----
    NL_CENTER = np.array([-3.0, -0.6, 0.0])   # 实数轴中心（承接 Shot1 的 x 轴）
    EQ_ANCHOR = np.array([3.0, -0.2, 0.0])    # 方程锚点
    DEF_ANCHOR = np.array([3.0, 1.6, 0.0])    # 定义式锚点
    I_VALUE = 1j                              # 新数 i（单位 u = NUMLINE_UNIT）
    REGION_BUFF = 0.35
    ARC = -PI / 2                             # 代入/替换飞行弧
    BEATS = {"intro": 0.8, "extend": 1.5, "def": 1.2, "sub": 1.6,
             "rep": 1.6, "simp": 1.2, "glow": 1.0, "border": 1.2}

    # ---------- 解析自检（analytic_check） ----------
    def _check(self) -> None:
        i2 = cmul(self.I_VALUE, self.I_VALUE)
        if abs(i2 - (-1)) > EPS_T or abs(i2 + 1) > EPS_T or abs(self.I_VALUE.imag) < EPS_T:
            raise RuntimeError("Shot2 analytic_check 失败：i²≠−1 或 i 落在实数轴上")

    @staticmethod
    def _tex(*parts) -> MathTex:
        return MathTex(*parts, color=INK)

    @staticmethod
    def _align(new: Mobject, old: Mobject, k_new: int, k_old: int) -> Mobject:
        """以等号对齐改写前后两式。"""
        return new.shift(old[k_old].get_center() - new[k_new].get_center())

    def _region(self, mobs, opacity: float) -> RoundedRectangle:
        """数集区域：包络给定对象的圆角框（尺寸由对象实时包围盒算出）。"""
        g = Group(*mobs)
        r = RoundedRectangle(
            width=g.width + 2 * self.REGION_BUFF, height=g.height + 2 * self.REGION_BUFF,
            corner_radius=0.3, stroke_width=0, fill_color=C_RE, fill_opacity=opacity)
        return r.move_to(g.get_center())

    @staticmethod
    def _halo(m: Mobject) -> Mobject:
        return m.copy().set_stroke(C_HALO, width=10, opacity=0.35).set_fill(opacity=0)

    def construct(self):
        self._check()
        self.camera.background_color = BG
        B = self.BEATS

        # ---- 对象：实数轴、区域 R、方程 ----
        numline = NumberLine(x_range=NUMLINE_RANGE, unit_size=NUMLINE_UNIT, color=INK,
                             include_numbers=True, font_size=28).move_to(self.NL_CENTER)
        numline.numbers.set_color(INK)
        region = self._region([numline], 0.08)
        eq = self._tex("x", "^2", "+", "1", "=", "0").scale(1.2).move_to(self.EQ_ANCHOR)
        self.play(FadeIn(region), FadeIn(numline), FadeIn(eq), run_time=B["intro"])

        # ---- 过程1 扩充：i 在数轴外淡入（位置 = 原点 + i·u），区域外扩 ----
        i_pos = c2p(self.I_VALUE, origin=numline.n2p(0), unit=NUMLINE_UNIT)
        i_dot = Dot(i_pos, radius=0.09, color=C_I)
        i_lab = MathTex("i", color=C_I).scale(1.1).next_to(i_dot, UR, buff=0.08)
        region_big = self._region([numline, i_dot, i_lab], 0.08)
        self.play(FadeIn(i_dot, scale=0.5), FadeIn(i_lab),
                  Transform(region, region_big), run_time=B["extend"])
        self.play(Flash(i_dot, color=C_HALO, flash_radius=0.35), run_time=0.5)

        # ---- 定义式 i²=−1（i 紫、−1 灰白） ----
        defn = self._tex("i", "^2", "=", "-1").scale(1.1).move_to(self.DEF_ANCHOR)
        defn[0].set_color(C_I)
        defn[1].set_color(C_I)
        self.play(Write(defn), run_time=B["def"])
        self.play(Indicate(defn[0:2], color=C_HALO), run_time=0.8)
        self.wait(0.6)

        # ---- 过程2 代入：i 沿弧飞入顶替 x，x 被顶出 ----
        eq2 = self._align(self._tex("i", "^2", "+", "1", "=", "0").scale(1.2), eq, 4, 4)
        eq2[0].set_color(C_I)
        self.play(ReplacementTransform(i_lab.copy(), eq2[0], path_arc=self.ARC),
                  FadeOut(eq[0], shift=DOWN * 0.6),
                  ReplacementTransform(eq[1:], eq2[1:]), run_time=B["sub"])
        self.wait(0.8)

        # ---- 过程3 替换：−1 从定义式右侧飞来，i² 被推出 ----
        eq3 = self._align(self._tex("-1", "+", "1", "=", "0").scale(1.2), eq2, 3, 4)
        self.play(ReplacementTransform(defn[3].copy(), eq3[0], path_arc=self.ARC),
                  FadeOut(eq2[0:2], shift=UP * 0.6),
                  ReplacementTransform(eq2[2:], eq3[1:]), run_time=B["rep"])
        self.wait(0.6)

        # ---- 相消：−1+1 合并为 0，整式亮绿（t2c 染色 + halo，不用框） ----
        eq4 = self._align(self._tex("0", "=", "0").scale(1.2), eq3, 1, 3)
        self.play(ReplacementTransform(eq3[0:3], eq4[0]),
                  ReplacementTransform(eq3[3:], eq4[1:]), run_time=B["simp"])
        halo = self._halo(eq4.copy().set_color(C_OK))
        self.play(eq4.animate.set_color(C_OK), FadeIn(halo),
                  Flash(eq4, color=C_HALO, flash_radius=0.8), run_time=B["glow"])
        self.wait(0.5)

        # ---- 收束：外扩数集区域边界淡入 ----
        border = DashedVMobject(region_big.copy().set_fill(opacity=0)
                                .set_stroke(C_RE, width=3, opacity=0.9), num_dashes=48)
        self.play(Create(border), run_time=B["border"])

        finish_shot(self)


class Shot3(Scene):
    """复数定义 z=a+bi：组装 → 实部/虚部括线 → i 剥离出虚部框 → 3+2i 代入 → 集合 C。"""
    SECONDS = SHOT_SECONDS[3]
    EXPR_POS = UP * 0.3
    I_FROM = np.array([3.6, 1.6, 0.0])            # 承接 Shot2 i_pt 的落点（布局常量）
    NL_POS = (np.array([-3.2, 2.7, 0.0]), np.array([-3.2, 1.7, 0.0]))
    NL_PICK = (0.6, -0.4)                         # a、b 在实数轴小样上的取样比例
    TEX_SIZE = 84
    LAB_SIZE = 30
    I_SLIDE = 0.55                                # i 滑出虚部框的距离
    BOX_BUFF = 0.1

    # ---------- 构件 ----------
    def _expr(self, a_s: str, b_s: str) -> MathTex:
        e = MathTex("z", "=", a_s, "+", b_s, "i", font_size=self.TEX_SIZE, color=INK)
        e[2].set_color(C_RE)
        e[4].set_color(C_IM)
        e[5].set_color(C_I)
        return e.move_to(self.EXPR_POS)

    def _tags(self, e: MathTex, re_v=None, im_v=None) -> VGroup:
        br_a = Brace(e[2], DOWN, buff=0.12, color=C_RE)
        br_b = Brace(e[4], DOWN, buff=0.12, color=C_IM)

        def lab(txt, v, col):
            g = VGroup(T(txt, font_size=self.LAB_SIZE, color=col))
            if v is not None:
                g.add(MathTex("=" + v, font_size=self.LAB_SIZE + 6, color=col))
            return g.arrange(RIGHT, buff=0.1)

        la = lab("实部", re_v, C_RE).next_to(br_a, DOWN, buff=0.12).align_to(br_a, RIGHT)
        lb = lab("虚部", im_v, C_IM).next_to(br_b, DOWN, buff=0.12).align_to(br_b, LEFT)
        return VGroup(br_a, br_b, la, lb)

    @staticmethod
    def _check_safe(m: Mobject) -> None:
        """自检：内容不越出安全区、不压字幕带。"""
        if (m.get_top()[1] > CONTENT_TOP or m.get_bottom()[1] < CONTENT_BOTTOM
                or abs(m.get_left()[0]) > SAFE_WIDTH / 2 or abs(m.get_right()[0]) > SAFE_WIDTH / 2):
            raise RuntimeError(f"Shot3 越出安全区: {type(m).__name__}")

    # ---------- 主流程 ----------
    def construct(self):
        self.camera.background_color = BG
        i_src = MathTex("i", font_size=self.TEX_SIZE, color=C_I).move_to(self.I_FROM)
        self.add(i_src)                                   # 上镜的 i 留在画面
        expr = self._expr("a", "b")

        # 过程1：组装 —— a、b 从两条实数轴小样取出，i 平移落位
        nls, picks = VGroup(), []
        for pos, sym, col, frac in zip(self.NL_POS, ("a", "b"), (C_RE, C_IM), self.NL_PICK):
            nl = NumberLine(x_range=NUMLINE_RANGE, unit_size=NUMLINE_UNIT, color=INK).move_to(pos)
            dot = Dot(nl.n2p(frac * NUMLINE_RANGE[1]), radius=0.06, color=col)
            sm = MathTex(sym, font_size=44, color=col).next_to(dot, UP, buff=0.08)
            nls.add(VGroup(nl, dot, sm))
            picks.append(sm)
        self.play(FadeIn(nls, shift=UP * 0.2), run_time=0.8)
        self.play(AnimationGroup(
            ReplacementTransform(i_src, expr[5]),
            ReplacementTransform(picks[0].copy(), expr[2]),
            ReplacementTransform(picks[1].copy(), expr[4]),
            Write(VGroup(expr[0], expr[1], expr[3])),
        ), run_time=1.6)

        note = MathTex(r"(a,b\in\mathbb{R})", font_size=40, color=INK).next_to(expr, RIGHT, buff=0.9)
        note[0][1].set_color(C_RE)
        note[0][3].set_color(C_IM)
        self._check_safe(note)
        self.play(FadeIn(note, shift=LEFT * 0.2), run_time=0.6)
        self.wait(0.6)
        self.play(FadeOut(nls), run_time=0.5)

        # 过程2：标注 —— 蓝/橙括线 + 实部/虚部
        tags = self._tags(expr)
        self.play(GrowFromCenter(tags[0]), GrowFromCenter(tags[1]), FadeIn(tags[2:]), run_time=1.0)
        self.wait(1.2)

        # 过程3：剥离 —— 框先包 bi，i 滑出，框收缩到 b，i 变暗
        box = SurroundingRectangle(VGroup(expr[4], expr[5]), color=C_IM, buff=self.BOX_BUFF)
        self.play(Create(box), run_time=0.6)
        self.wait(0.4)
        box_b = SurroundingRectangle(expr[4], color=C_IM, buff=self.BOX_BUFF)
        self.play(expr[5].animate.shift(RIGHT * self.I_SLIDE).set_color(DIM),
                  Transform(box, box_b), run_time=1.2)
        if box.get_right()[0] >= expr[5].get_left()[0]:   # 约束：最终框内只有 b，必须排除 i
            raise RuntimeError("Shot3 约束失败：虚部框仍包含 i")
        self.play(Flash(box.get_center(), color=C_HALO, flash_radius=box.width / 2 + 0.25),
                  Indicate(expr[4], color=C_HALO), run_time=0.6)
        self.wait(1.0)

        # 过程4：代入 —— 数值槽由 EXAMPLE_Z 实时取 Re/Im
        re_v, im_v = EXAMPLE_Z.real, EXAMPLE_Z.imag
        a_s, b_s = f"{re_v:g}", f"{im_v:g}"
        if complex(float(a_s), float(b_s)) != EXAMPLE_Z or abs(cmath.phase(1j) - PI / 2) > EPS_T:
            raise RuntimeError("Shot3 解析校验失败：z 文本与 Re/Im 不一致")
        new = self._expr(a_s, b_s)
        new_tags = self._tags(new, a_s, b_s)
        self._check_safe(new_tags)
        self.play(
            *[ReplacementTransform(expr[k], new[k]) for k in (0, 1, 3, 5)],
            FadeOut(expr[2], shift=DOWN * 0.3), FadeIn(new[2], shift=DOWN * 0.5),
            FadeOut(expr[4], shift=DOWN * 0.3), FadeIn(new[4], shift=DOWN * 0.5),
            FadeOut(box), FadeOut(note),
            ReplacementTransform(tags, new_tags),
            run_time=1.4,
        )
        self.play(Indicate(new[2], color=C_HALO), Indicate(new[4], color=C_HALO), run_time=0.6)
        self.wait(1.0)

        # 末尾：集合 C 轮廓包住 z
        body = VGroup(new, new_tags)
        region = Ellipse(width=body.width + 2.2, height=body.height + 1.0,
                         color=DIM, stroke_width=3, fill_color=DIM, fill_opacity=0.06)
        region.move_to(body.get_center())
        c_lab = MathTex(r"\mathbb{C}", font_size=56, color=INK)
        c_lab.move_to(region.point_from_proportion(0.375)).shift(UL * 0.3)
        self._check_safe(VGroup(region, c_lab))
        self.play(Create(region), FadeIn(c_lab, scale=0.8), run_time=1.0)

        finish_shot(self)


class Shot4(Scene):
    """同一 z=a+bi：b→0 塌缩成实数；b 长回成虚数；a→0 塌缩成纯虚数；末尾 ℝ ⊂ ℂ。"""
    SECONDS = SHOT_SECONDS[4]
    # 拨盘时间表（关键点 + 线性插值，场景时钟驱动，与渲染 fps 解耦）
    A_KEYS = ((0.0, 11.0, 13.0, 16.0), (EXAMPLE_Z.real, EXAMPLE_Z.real, 0.0, 0.0))
    B_KEYS = ((0.0, 1.0, 3.0, 6.0, 8.0, 16.0),
              (EXAMPLE_Z.imag, EXAMPLE_Z.imag, 0.0, 0.0, EXAMPLE_Z.imag, EXAMPLE_Z.imag))
    A_FULL, B_FULL = 3.0, 2.0          # term_scale 分母：min(1,|a|/3)、min(1,|b|/2)
    ZERO_TOL = 1e-6
    GRAPH_STEP = SIM_DT * 30           # b(t) 曲线采样步长
    EXPR_ANCHOR = np.array([-3.4, 2.5, 0.0])
    TAG_POS = np.array([3.6, 2.45, 0.0])
    SLIDER_X, SLIDER_LEN = -3.2, 3.0
    LAMP_X = 0.8
    GRAPH_CENTER = np.array([4.2, 0.7, 0.0])
    RL_CENTER, RL_LEN = np.array([-1.5, -1.7, 0.0]), 4.8
    TAGS = {"实数": (INK, r"b=0"), "虚数": (C_IM, r"b\neq0"), "纯虚数": (C_I, r"a=0,\ b\neq0")}

    # ---------- 模型 ----------
    def _a(self, t):
        return float(np.interp(t, *self.A_KEYS))

    def _b(self, t):
        return float(np.interp(t, *self.B_KEYS))

    def _is0(self, x):
        return abs(x) < self.ZERO_TOL

    def _classify(self, a, b):
        return "实数" if self._is0(b) else ("纯虚数" if self._is0(a) else "虚数")

    # ---------- 视图 ----------
    def _expr(self, a, b):
        sa, sb = min(1.0, abs(a) / self.A_FULL), min(1.0, abs(b) / self.B_FULL)
        parts = [MathTex("z=", color=INK)]
        if sa > self.ZERO_TOL:
            parts.append(DecimalNumber(a, num_decimal_places=1, color=C_RE).scale(sa))
        if sa > self.ZERO_TOL and sb > self.ZERO_TOL:
            parts.append(MathTex("+", color=INK).scale(min(sa, sb)))
        if sb > self.ZERO_TOL:
            parts.append(VGroup(DecimalNumber(b, num_decimal_places=1, color=C_IM),
                                MathTex("i", color=C_I)).arrange(RIGHT, buff=0.05).scale(sb))
        g = VGroup(*parts).arrange(RIGHT, buff=0.15).scale(1.3)
        return g.move_to(self.EXPR_ANCHOR, aligned_edge=LEFT)

    def _slider(self, name, color, y, get):
        line = NumberLine(x_range=[0, 3, 1], length=self.SLIDER_LEN, color=DIM,
                          include_numbers=True, font_size=22).move_to([self.SLIDER_X, y, 0])
        lab = MathTex(name, color=color).next_to(line, LEFT, buff=0.3)
        knob = always_redraw(lambda: Dot(line.n2p(get()), radius=0.11, color=color))
        return VGroup(line, lab, knob)

    def _lamp(self, tex, y, on):
        bulb = Circle(radius=0.14, stroke_color=INK, stroke_width=2).move_to([self.LAMP_X, y, 0])
        bulb.add_updater(lambda m: m.set_fill(C_OK if on() else DIM, opacity=1.0 if on() else 0.2))
        lab = MathTex(tex, color=INK).scale(0.8).next_to(bulb, RIGHT, buff=0.2)
        return VGroup(bulb, lab)

    # ---------- 镜头 ----------
    def construct(self):
        self.camera.background_color = BG
        clock = ValueTracker(0.0)
        a_keys = self.A_KEYS
        b_keys = self.B_KEYS
        zero_tol = self.ZERO_TOL
        expr_anchor = self.EXPR_ANCHOR
        slider_x = self.SLIDER_X
        slider_len = self.SLIDER_LEN
        tag_pos = self.TAG_POS
        lamp_x = self.LAMP_X
        graph_center = self.GRAPH_CENTER
        graph_step = self.GRAPH_STEP
        rl_center = self.RL_CENTER
        rl_len = self.RL_LEN
        a_full = self.A_FULL
        b_full = self.B_FULL
        tags = self.TAGS

        va = lambda: float(np.interp(clock.get_value(), *a_keys))
        vb = lambda: float(np.interp(clock.get_value(), *b_keys))
        is0 = lambda x: abs(x) < zero_tol
        classify = lambda a, b: "实数" if is0(b) else ("纯虚数" if is0(a) else "虚数")

        def make_expr():
            a, b = va(), vb()
            sa, sb = min(1.0, abs(a) / a_full), min(1.0, abs(b) / b_full)
            parts = [MathTex("z=", color=INK)]
            if sa > zero_tol:
                parts.append(DecimalNumber(a, num_decimal_places=1, color=C_RE).scale(sa))
            if sa > zero_tol and sb > zero_tol:
                parts.append(MathTex("+", color=INK).scale(min(sa, sb)))
            if sb > zero_tol:
                parts.append(VGroup(DecimalNumber(b, num_decimal_places=1, color=C_IM),
                                    MathTex("i", color=C_I)).arrange(RIGHT, buff=0.05).scale(sb))
            g = VGroup(*parts).arrange(RIGHT, buff=0.15).scale(1.3)
            return g.move_to(expr_anchor, aligned_edge=LEFT)

        def make_slider(name, color, y, get_val):
            line = NumberLine(x_range=[0, 3, 1], length=slider_len, color=DIM,
                              include_numbers=True, font_size=22).move_to([slider_x, y, 0])
            lab = MathTex(name, color=color).next_to(line, LEFT, buff=0.3)
            knob = always_redraw(lambda: Dot(line.n2p(get_val()), radius=0.11, color=color))
            return VGroup(line, lab, knob)

        def make_lamp(tex, y, on_fn):
            bulb = Circle(radius=0.14, stroke_color=INK, stroke_width=2).move_to([lamp_x, y, 0])
            bulb.add_updater(lambda m: m.set_fill(C_OK if on_fn() else DIM, opacity=1.0 if on_fn() else 0.2))
            lab = MathTex(tex, color=INK).scale(0.8).next_to(bulb, RIGHT, buff=0.2)
            return VGroup(bulb, lab)

        def make_tag():
            name = classify(va(), vb())
            color, cond = tags[name]
            g = VGroup(T(name, color=color), MathTex(cond, color=color).scale(0.8))
            return g.arrange(DOWN, buff=0.15).move_to(tag_pos)

        expr = always_redraw(make_expr)
        s_a = make_slider("a", C_RE, 1.2, va)
        s_b = make_slider("b", C_IM, 0.3, vb)
        lamp_a0 = make_lamp(r"a=0", 1.2, lambda: is0(va()))
        lamp_bne0 = make_lamp(r"b\neq0", 0.3, lambda: not is0(vb()))
        tag = make_tag()

        ax = Axes(x_range=[0, 16, 4], y_range=[0, 3, 1], x_length=3.6, y_length=1.5, tips=False,
                  axis_config={"color": DIM, "stroke_width": 2}).move_to(graph_center)
        curve = ax.plot(lambda t: float(np.interp(t, *b_keys)), x_range=[0, 16, graph_step], color=C_IM, use_smoothing=False)
        glab = MathTex("b(t)", color=C_IM).scale(0.6).next_to(ax, UP, buff=0.1, aligned_edge=LEFT)
        cursor = always_redraw(lambda: Dot(ax.c2p(clock.get_value(), vb()),
                                           radius=0.07, color=C_HALO))

        rl = NumberLine(x_range=[-4, 4, 1], length=rl_len, color=INK,
                        include_numbers=True, font_size=22).move_to(rl_center)
        rlab = MathTex(r"\mathbb{R}", color=INK).scale(0.8).next_to(rl, RIGHT, buff=0.2)
        mark = always_redraw(lambda: Dot(rl.n2p(va()), radius=0.1, color=C_RE)
                             .set_opacity(1.0 if is0(vb()) else 0.0))
        region = Ellipse(width=rl_len + 1.6, height=1.9, color=C_OK).move_to(rl)
        clab = MathTex(r"\mathbb{C}", color=C_OK).next_to(region, RIGHT, buff=0.15)

        # Helper for time advancement
        def adv(t_end, *anims):
            if t_end - self.time > EPS_T:
                self.play(clock.animate(rate_func=linear).set_value(t_end), *anims,
                          run_time=t_end - self.time)

        def swap_tag(old_tag):
            new = make_tag()
            anim = ReplacementTransform(old_tag, new)
            return new, anim

        # 0–1s：沿用上镜 z=a+bi，数值槽与条件灯就位
        self.add(expr, cursor)
        adv(1, FadeIn(VGroup(s_a, s_b, lamp_a0, lamp_bne0, tag, ax, curve, glab)))
        # 1–3s：b 滑到 0，+bi 塌缩
        adv(3)
        # 3–6s：判为实数，z 落到实数轴小样
        self.add(mark)
        tag, anim = swap_tag(tag)
        adv(4, anim, FadeIn(rl, rlab))
        adv(5, Indicate(tag, color=C_HALO), Flash(mark, color=C_HALO))
        adv(6)
        # 6–9s：b 离开 0，+bi 长回，判为虚数
        adv(8)
        tag, anim = swap_tag(tag)
        adv(9, anim, Flash(lamp_bne0[0], color=C_HALO))
        adv(11)
        # 11–14s：a 滑到 0，a+ 塌缩，双灯同亮判为纯虚数
        adv(13)
        tag, anim = swap_tag(tag)
        adv(14, anim, Flash(lamp_a0[0], color=C_HALO),
                  Flash(lamp_bne0[0], color=C_HALO))
        # 14–15.5s：实数轴小样被 ℂ 包含
        adv(15.5, Create(region), Write(clab), Indicate(rlab, color=C_HALO))
        finish_shot(self)


class Shot5(Scene):
    """复数相等：a↔c、b↔d 两连线同亮，问号才变等号（逻辑态驱动，不手填关键帧）。"""
    SECONDS = SHOT_SECONDS[5]

    # analytic_check 样例：equal(a,b,c,d) = (a==c) ∧ (b==d)
    CHECK_SAMPLES = [
        ((3, 2, 3, 2), True),
        ((3, 2, 3, 5), False),
        ((3, 2, 1, 2), False),
    ]
    Z1_POS = np.array([-2.0, 0.0, 0.0])
    Z2_POS = np.array([2.0, 0.0, 0.0])
    IFF_Y = -1.5
    FS_MAIN = 80
    ARC_UP, ARC_DN = -PI / 3, PI / 4      # 上弧连实部、下弧连虚部

    @staticmethod
    def complex_equal(z: complex, w: complex) -> tuple:
        """返回 (实部相等, 虚部相等)。"""
        return (math.isclose(z.real, w.real), math.isclose(z.imag, w.imag))

    def _self_check(self) -> None:
        for (a, b, c, d), expect in self.CHECK_SAMPLES:
            re_eq, im_eq = self.complex_equal(complex(a, b), complex(c, d))
            assert (re_eq and im_eq) == expect, f"analytic_check 失败: {(a, b, c, d)}"

    def _rel_sign(self, re_lit: bool, im_lit: bool) -> MathTex:
        """rel_sign = (re∧im) ? '=' : '?'；颜色 ink / gray。"""
        both = re_lit and im_lit
        sign = MathTex("=" if both else "?", font_size=self.FS_MAIN)
        sign.set_color(INK if both else DIM)
        return sign.move_to((self.Z1_POS + self.Z2_POS) / 2)

    def construct(self):
        self.camera.background_color = BG
        self._self_check()

        # z2 为 z1 的复制（copy_of），数值取同一例，lit 状态由比较结果决定
        z1_val = EXAMPLE_Z
        z2_val = complex(z1_val.real, z1_val.imag)
        re_equal, im_equal = self.complex_equal(z1_val, z2_val)

        z1 = MathTex("a", "+", "b", "i", font_size=self.FS_MAIN).move_to(self.Z1_POS)
        z2 = MathTex("c", "+", "d", "i", font_size=self.FS_MAIN).move_to(self.Z2_POS)
        for z in (z1, z2):
            z[0].set_color(C_RE)
            z[1].set_color(INK)
            z[2].set_color(C_IM)
            z[3].set_color(C_I)

        # ---- beat 1：唯一确定，a、b 被括线锁定 ----
        self.play(Write(z1), run_time=1.0)
        brace = Brace(VGroup(z1[0], z1[2]), DOWN, color=C_HALO, buff=0.15)
        brace_lb = T("决定 z 的两个数", font_size=26, color=C_HALO).next_to(brace, DOWN, 0.12)
        self.play(GrowFromCenter(brace), FadeIn(brace_lb, shift=UP * 0.1), run_time=1.0)
        self.play(Indicate(z1[0], color=C_HALO), Indicate(z1[2], color=C_HALO), run_time=0.8)

        # ---- beat 2：复制出 c+di，中间灰色问号 ----
        re_lit, im_lit = False, False
        sign = self._rel_sign(re_lit, im_lit)
        self.play(FadeOut(brace), FadeOut(brace_lb), run_time=0.4)
        self.play(TransformFromCopy(z1, z2), run_time=1.0)
        self.play(FadeIn(sign), run_time=0.5)
        self.wait(0.8)

        # ---- beat 3a：a↔c 蓝色连线（仅一条亮，问号保持灰色） ----
        link_re = ArcBetweenPoints(z1[0].get_top() + UP * 0.12, z2[0].get_top() + UP * 0.12,
                                   angle=self.ARC_UP, color=C_RE, stroke_width=5)
        lb_re = MathTex("a=c", font_size=40)
        lb_re[0][0].set_color(C_RE)
        lb_re[0][2].set_color(C_RE)
        lb_re.next_to(link_re.point_from_proportion(0.5), UP, 0.12)
        if re_equal:
            re_lit = True
            self.play(Create(link_re), run_time=0.8)
            self.play(FadeIn(lb_re, shift=DOWN * 0.1),
                      Flash(link_re.point_from_proportion(0.5), color=C_HALO), run_time=0.6)
        self.play(Wiggle(sign), run_time=0.6)  # 单线亮：等号不成立，问号仍灰

        # ---- beat 3b：b↔d 橙色连线 ----
        link_im = ArcBetweenPoints(z1[2].get_bottom() + DOWN * 0.12,
                                   z2[2].get_bottom() + DOWN * 0.12,
                                   angle=self.ARC_DN, color=C_IM, stroke_width=5)
        lb_im = MathTex("b=d", font_size=40)
        lb_im[0][0].set_color(C_IM)
        lb_im[0][2].set_color(C_IM)
        lb_im.next_to(link_im.point_from_proportion(0.5), DOWN, 0.12)
        if im_equal:
            im_lit = True
            self.play(Create(link_im), run_time=0.8)
            self.play(FadeIn(lb_im, shift=UP * 0.1),
                      Flash(link_im.point_from_proportion(0.5), color=C_HALO), run_time=0.6)

        # ---- 两线同亮：问号 → 等号，充要式上屏 ----
        new_sign = self._rel_sign(re_lit, im_lit)
        self.play(Transform(sign, new_sign), run_time=0.6)
        if re_lit and im_lit:
            self.play(Flash(sign, color=C_HALO, flash_radius=0.5), run_time=0.5)
            iff = MathTex("a", "+", "b", "i", "=", "c", "+", "d", "i", r"\iff",
                          "a", "=", "c", r",\ ", "b", "=", "d", font_size=48)
            for idx in (0, 5, 10, 12):
                iff[idx].set_color(C_RE)
            for idx in (2, 7, 14, 16):
                iff[idx].set_color(C_IM)
            for idx in (3, 8):
                iff[idx].set_color(C_I)
            iff[9].set_color(C_OK)
            # 规格 y=-1.5；若与下方标注重叠则顺延，且不得进入字幕带
            y = min(self.IFF_Y, lb_im.get_bottom()[1] - 0.25 - iff.height / 2)
            iff.move_to(np.array([0.0, y, 0.0]))
            assert iff.get_bottom()[1] >= CONTENT_BOTTOM, "iff 越界进入字幕带"
            assert iff.width <= SAFE_WIDTH, "iff 超出安全宽度"
            self.play(Write(iff), run_time=1.0)
            self.play(Indicate(iff[9], color=C_HALO), run_time=0.8)

        finish_shot(self)


class Shot6(Scene):
    """复平面：a→实轴、b→虚轴，虚线交出 Z，长出向量 OZ，再连续滑到 3+2i ↔ (3,2)。"""
    SECONDS = SHOT_SECONDS[6]
    Z0 = complex(1.5, 1.0)            # ModelSpec point_repr: Z.pos0
    SLIDE_T0, SLIDE_T = 13.0, 3.0     # schedule: t∈[13,16]s 线性插值

    def construct(self):
        self.camera.background_color = BG
        z0, z1 = self.Z0, EXAMPLE_Z
        s = ValueTracker(0.0)

        def zt() -> complex:
            """按 alpha 在 SIM_DT 网格上取样（仿真与渲染帧解耦）。"""
            n = round(s.get_value() * self.SLIDE_T / SIM_DT)
            return z0 + (z1 - z0) * (n * SIM_DT / self.SLIDE_T)

        def at(t: float) -> None:
            if t - self.time > EPS_T:
                self.wait(t - self.time)

        def fmt(v: float) -> str:
            return f"{v:.2f}".rstrip("0").rstrip(".")

        def zexpr(z: complex) -> MathTex:
            m = MathTex("z", "=", fmt(z.real), "+", fmt(z.imag), "i", font_size=60)
            m[2].set_color(C_RE); m[4].set_color(C_IM); m[5].set_color(C_I)
            return m.move_to([3.4, 2.0, 0])

        def zread(z: complex) -> MathTex:
            m = MathTex("Z(", fmt(z.real), ",", fmt(z.imag), ")", font_size=34)
            m[1].set_color(C_RE); m[3].set_color(C_IM)
            return m.next_to(c2p(z), UR, buff=0.18)

        # ---- 坐标系：原点/单位与 c2p 严格一致 ----
        axes = Axes(
            x_range=PLANE_X_RANGE, y_range=PLANE_Y_RANGE,
            x_length=(PLANE_X_RANGE[1] - PLANE_X_RANGE[0]) * PLANE_UNIT,
            y_length=(PLANE_Y_RANGE[1] - PLANE_Y_RANGE[0]) * PLANE_UNIT,
            x_axis_config={"color": C_RE, "include_numbers": True, "font_size": 24},
            y_axis_config={"color": C_IM, "include_numbers": True, "font_size": 24},
        )
        axes.shift(PLANE_ORIGIN - axes.c2p(0, 0))
        assert np.allclose(axes.c2p(z1.real, z1.imag), c2p(z1)), "axes/c2p 不一致"

        # 上镜实数轴小样（零点先在画面中线，平移并扩成横轴）
        mini = NumberLine(x_range=NUMLINE_RANGE, unit_size=NUMLINE_UNIT, color=INK,
                          include_numbers=True, font_size=24)
        mini.shift(np.array([0.0, PLANE_ORIGIN[1], 0.0]) - mini.n2p(0))

        expr = MathTex("z", "=", "a", "+", "b", "i", font_size=60)
        expr[2].set_color(C_RE); expr[4].set_color(C_IM); expr[5].set_color(C_I)
        expr.move_to([3.4, 2.0, 0])

        # 过程1：建系
        self.play(FadeIn(mini), Write(expr), run_time=1.0)
        self.play(ReplacementTransform(mini, axes.x_axis),
                  GrowFromPoint(axes.y_axis, PLANE_ORIGIN), run_time=1.5)

        # 过程2：a 飞向横轴、b 飞向纵轴（目标点由 c2p 实时算）
        a_tag, b_tag = expr[2].copy(), expr[4].copy()
        pa = c2p(complex(z0.real, 0)) + DOWN * 0.45
        pb = c2p(complex(0, z0.imag)) + LEFT * 0.75
        self.play(MoveAlongPath(a_tag, ArcBetweenPoints(a_tag.get_center(), pa, angle=PI / 3)),
                  run_time=1.5)
        self.play(MoveAlongPath(b_tag, ArcBetweenPoints(b_tag.get_center(), pb, angle=PI / 4)),
                  run_time=1.5)

        lx = T("实轴", font_size=26, color=C_RE).next_to(axes.x_axis.get_end(), UP, buff=0.2)
        ly = T("虚轴", font_size=26, color=C_IM).next_to(axes.y_axis.get_end(), RIGHT, buff=0.2)
        self.play(FadeIn(lx, shift=UP * 0.1), FadeIn(ly, shift=RIGHT * 0.1), run_time=0.6)
        self.play(Indicate(lx, color=C_HALO), Indicate(ly, color=C_HALO), run_time=0.4)

        # 辅助虚线 + 点 Z（全部绑定 zt()）
        px = always_redraw(lambda: DashedLine(c2p(complex(zt().real, 0)), c2p(zt()),
                                              color=C_RE, dash_length=0.08))
        py = always_redraw(lambda: DashedLine(c2p(complex(0, zt().imag)), c2p(zt()),
                                              color=C_IM, dash_length=0.08))
        self.play(Create(px), Create(py), run_time=1.0)

        dot = always_redraw(lambda: Dot(c2p(zt()), radius=0.08, color=INK))
        zlab = MathTex("Z(", "a", ",", "b", ")", font_size=34)
        zlab[1].set_color(C_RE); zlab[3].set_color(C_IM)
        zlab.next_to(c2p(z0), UR, buff=0.18)
        self.play(GrowFromCenter(dot), FadeIn(zlab),
                  Flash(c2p(z0), color=C_HALO, flash_radius=0.3), run_time=1.0)

        # 过程3：向量 OZ 从原点生长；标签沿法向（= 单位方向 ×i）偏移
        oz = Arrow(c2p(0), c2p(z0), buff=0, color=INK, stroke_width=5)
        ozlab = MathTex(r"\vec{OZ}", font_size=34, color=INK)

        def place_ozlab(m):
            z = zt()
            nrm = times_i(z / abs(z))
            m.move_to(c2p(z / 2) + np.array([nrm.real, nrm.imag, 0.0]) * 0.38)

        place_ozlab(ozlab)
        self.play(GrowArrow(oz), FadeIn(ozlab), run_time=1.2)
        oz.add_updater(lambda m: m.become(
            Arrow(c2p(0), c2p(zt()), buff=0, color=INK, stroke_width=5)))
        ozlab.add_updater(place_ozlab)

        # 过程4：数值槽接管 a、b，Z 连续滑到 (3,2)
        at(12.0)
        expr_num = always_redraw(lambda: zexpr(zt()))
        readout = always_redraw(lambda: zread(zt()))
        self.play(FadeOut(a_tag), FadeOut(b_tag), FadeOut(zlab), FadeIn(readout),
                  FadeOut(expr), FadeIn(expr_num), run_time=1.0)
        at(self.SLIDE_T0)
        self.play(s.animate.set_value(1.0), run_time=self.SLIDE_T, rate_func=linear)

        fa, fb = fmt(z1.real), fmt(z1.imag)
        final = MathTex(fa, "+", fb, "i", r"\leftrightarrow", "(", fa, ",", fb, ")",
                        font_size=44)
        for k in (0, 6):
            final[k].set_color(C_RE)
        for k in (2, 8):
            final[k].set_color(C_IM)
        final[3].set_color(C_I)
        final.next_to(expr_num, DOWN, buff=0.45)
        self.play(Write(final), run_time=0.5)
        self.play(Indicate(final, color=C_HALO),
                  Flash(c2p(z1), color=C_HALO, flash_radius=0.3), run_time=0.4)

        finish_shot(self)


class Shot7(Scene):
    """模 |z|：OZ 作斜边的直角三角形 → 边长映射到 √(a²+b²) → 代入 3、2 得 √13。"""
    SECONDS = SHOT_SECONDS[7]
    FORM_POS = np.array([3.2, 1.4, 0.0])   # 公式锚点（右侧安全区内）
    FLY_ARC = PI / 3                        # 边→字母飞入弧度
    T_SETUP, T_LIFT, T_LEG_B, T_LEG_A, T_MARK = 0.6, 0.8, 1.0, 0.8, 0.4
    T_LABEL, T_FLY, T_SUB, T_RES, T_FX = 1.0, 1.6, 1.8, 1.2, 0.8

    def construct(self):
        self.camera.background_color = BG
        # ---------- 数学量：全部由 EXAMPLE_Z 实时算出 ----------
        z = EXAMPLE_Z
        a, b = z.real, z.imag
        foot = complex(a, 0.0)
        mod = modulus(a, b)
        n_sq = round(a * a + b * b)
        root = math.isqrt(n_sq)
        surd = str(root) if root * root == n_sq else rf"\sqrt{{{n_sq}}}"
        assert abs(a * a + b * b - mod * mod) < 1e-9                    # 勾股
        O, Z, F = c2p(0j), c2p(z), c2p(foot)
        assert abs(np.dot(F - O, Z - F)) < 1e-9                        # hinge 90°

        # ---------- 复平面（继承 Shot6） ----------
        xr, yr = PLANE_X_RANGE, PLANE_Y_RANGE
        axes = Axes(
            x_range=xr, y_range=yr,
            x_length=(xr[1] - xr[0]) * PLANE_UNIT,
            y_length=(yr[1] - yr[0]) * PLANE_UNIT,
            axis_config={"color": DIM, "include_tip": True, "tip_length": 0.18},
        )
        axes.shift(PLANE_ORIGIN - axes.c2p(0, 0))
        ax_lab = VGroup(
            T("实轴", font_size=22, color=DIM).next_to(axes.x_axis.get_end(), DOWN, 0.12),
            T("虚轴", font_size=22, color=DIM).next_to(axes.y_axis.get_end(), RIGHT, 0.12),
        )
        dot = Dot(Z, color=INK, radius=0.07)
        z_lab = MathTex("Z", color=INK, font_size=34).next_to(dot, UR, 0.08)
        oz = Arrow(O, Z, buff=0, color=INK, stroke_width=4,
                   max_tip_length_to_length_ratio=0.12)
        self.play(FadeIn(VGroup(axes, ax_lab, oz, dot, z_lab)), run_time=self.T_SETUP)

        # ---------- 过程1：OZ 提亮 + halo，作垂线成直角三角形 ----------
        halo = Line(O, Z).set_stroke(C_HALO, width=14, opacity=0.25)
        leg_a = Line(O, F, color=C_RE, stroke_width=6)
        leg_b = DashedLine(Z, F, color=C_IM, stroke_width=6)
        mark = RightAngle(Line(O, F), Line(F, Z), length=0.22,
                          quadrant=(-1, 1), color=INK, stroke_width=2)
        self.add(halo, oz, dot)
        self.bring_to_back(halo)
        self.play(oz.animate.set_color(C_HALO), FadeIn(halo), run_time=self.T_LIFT)
        self.play(Create(leg_b), run_time=self.T_LEG_B)
        self.play(Create(leg_a), run_time=self.T_LEG_A)
        self.play(Create(mark), run_time=self.T_MARK)

        # ---------- 标注 |z| / a / b ----------
        nz = times_i(z) / abs(z)                       # OZ 左法向（×i 旋转得到）
        lab_z = MathTex("|z|", color=C_HALO, font_size=38).move_to(
            c2p(z / 2) + 0.55 * np.array([nz.real, nz.imag, 0.0]))
        lab_a = MathTex("a", color=C_RE, font_size=38).next_to(leg_a, DOWN, 0.15)
        lab_b = MathTex("b", color=C_IM, font_size=38).next_to(leg_b, RIGHT, 0.15)
        self.play(Write(lab_z), Indicate(oz, color=C_HALO), run_time=self.T_LABEL)
        self.play(FadeIn(lab_a, shift=UP * 0.2), FadeIn(lab_b, shift=LEFT * 0.2),
                  run_time=0.6)
        self.wait(0.4)

        # ---------- 过程2：边 → 字母 → |z|=√(a²+b²) ----------
        lhs = MathTex("|z|", "=", font_size=48)
        lhs[0].set_color(C_HALO)
        rad = MathTex(r"\sqrt{\phantom{a^2+b^2}}", font_size=48, color=INK)
        rad.next_to(lhs, RIGHT, 0.12)
        rcd = MathTex("a", "^2", "+", "b", "^2", font_size=48)
        rcd[0].set_color(C_RE)
        rcd[3].set_color(C_IM)
        rcd.align_to(rad, RIGHT).align_to(rad, UP).shift(DOWN * 0.08 + LEFT * 0.02)
        form = VGroup(lhs, rad, rcd).move_to(self.FORM_POS)
        self.play(
            ReplacementTransform(leg_a.copy(), rcd[0], path_arc=self.FLY_ARC),
            ReplacementTransform(leg_b.copy(), rcd[3], path_arc=self.FLY_ARC),
            ReplacementTransform(oz.copy(), lhs[0], path_arc=-self.FLY_ARC),
            FadeIn(VGroup(lhs[1], rad, rcd[1], rcd[2], rcd[4])),
            run_time=self.T_FLY,
        )
        self.play(Indicate(form, color=C_HALO, scale_factor=1.08), run_time=self.T_FX)
        self.wait(0.8)

        # ---------- 过程3：3、2 沿蓝/橙边飞入替换 a、b ----------
        rcd2 = MathTex(f"{a:g}", "^2", "+", f"{b:g}", "^2", font_size=48)
        rcd2[0].set_color(C_RE)
        rcd2[3].set_color(C_IM)
        rcd2.align_to(rcd, LEFT).align_to(rcd, DOWN)
        tgt_a, tgt_b = rcd2[0].get_center(), rcd2[3].get_center()
        off_a, off_b = DOWN * 0.45, RIGHT * 0.45
        path_a = VMobject().set_points_as_corners([O + off_a, F + off_a, tgt_a])
        path_b = VMobject().set_points_as_corners([F + off_b, Z + off_b, tgt_b])
        rcd2[0].move_to(path_a.get_start())
        rcd2[3].move_to(path_b.get_start())
        self.play(Indicate(leg_a, color=C_RE), Indicate(leg_b, color=C_IM), run_time=0.6)
        self.play(
            MoveAlongPath(rcd2[0], path_a),
            MoveAlongPath(rcd2[3], path_b),
            FadeOut(rcd[0]), FadeOut(rcd[3]),
            *[ReplacementTransform(rcd[k], rcd2[k]) for k in (1, 2, 4)],
            run_time=self.T_SUB,
        )

        # ---------- 结果 √13 + OZ 旁读数同步 ----------
        res = MathTex("|z|", "=", surd, font_size=48)
        res[0].set_color(C_HALO)
        res[2].set_color(C_OK)
        res.next_to(form, DOWN, 0.5).align_to(form, LEFT)
        readout = MathTex("=" + surd, color=C_OK, font_size=38).next_to(lab_z, UP, 0.1)
        self.play(TransformFromCopy(VGroup(lhs, rad, rcd2), res),
                  Write(readout), run_time=self.T_RES)
        self.play(Flash(readout, color=C_HALO, flash_radius=0.45),
                  Indicate(res[2], color=C_OK), run_time=self.T_FX)

        finish_shot(self)


class Shot8(Scene):
    """镜8 回顾：四张缩略图样一排，随口播依次由暗转亮（消失-出现）+ Indicate/Flash + halo。"""
    SECONDS = SHOT_SECONDS[8]

    PANEL_W, PANEL_H, PANEL_BUFF = 2.8, 3.2, 0.3
    THUMB_UNIT = 0.55                    # 缩略复平面 / 数轴单位长
    DIM_FADE = 0.78                      # 暗态透明衰减
    T_INTRO, T_SWAP, T_FX, T_HOLD = 1.0, 0.8, 0.7, 0.9
    FS_MAIN, FS_SUB = 40, 32

    # ---------- 单张缩略卡 ----------
    def _panel(self, formula, art=None):
        frame = RoundedRectangle(corner_radius=0.15, width=self.PANEL_W,
                                 height=self.PANEL_H, stroke_color=INK, stroke_width=2)
        formula.scale_to_fit_width(min(formula.width, self.PANEL_W - 0.35))
        if art is None:
            formula.move_to(frame.get_center())
            g = VGroup(frame, formula)
        else:
            art.scale_to_fit_width(min(art.width, self.PANEL_W - 0.4))
            art.move_to(frame.get_center() + UP * 0.45)
            formula.move_to(frame.get_bottom() + UP * 0.6)
            g = VGroup(frame, art, formula)
        g.frame = frame
        return g

    # 镜2 末帧：i·i 把 1 送到 −1（落点由复数乘法算出）
    def _thumb_i2(self):
        line = NumberLine(x_range=NUMLINE_RANGE, unit_size=self.THUMB_UNIT,
                          color=INK, tick_size=0.06, stroke_width=2)
        i2 = cmul(1j, 1j)
        arc = CurvedArrow(line.n2p(1.0), line.n2p(i2.real), angle=PI,
                          color=C_I, stroke_width=3, tip_length=0.15)
        dot = Dot(line.n2p(i2.real), radius=0.07, color=C_OK)
        f = MathTex("i", "^2", "=", "-1", font_size=self.FS_MAIN)
        f[0].set_color(C_I)
        f[3].set_color(C_OK)
        return self._panel(f, VGroup(line, arc, dot)), f

    # 镜3 末帧：虚部框只包 b，不包 i
    def _thumb_part(self):
        f = MathTex("z", "=", "a", "+", "b", "i", font_size=self.FS_MAIN + 8)
        f[2].set_color(C_RE)
        f[4].set_color(C_IM)
        f[5].set_color(C_I)
        box = SurroundingRectangle(f[4], color=C_IM, buff=0.08, stroke_width=2.5)
        return self._panel(VGroup(f, box)), VGroup(f[4], box)

    # 镜4 末帧：只剩 bi，双条件灯亮
    def _thumb_pure(self):
        z = MathTex("z", "=", "b", "i", font_size=self.FS_MAIN + 8)
        z[2].set_color(C_IM)
        z[3].set_color(C_I)
        cond = MathTex("a=0", r",\ ", r"b\neq0", font_size=self.FS_SUB)
        cond[0].set_color(C_RE)
        cond[2].set_color(C_IM)
        lamps = VGroup(*[Dot(radius=0.07, color=C_OK).next_to(cond[k], UP, buff=0.12)
                         for k in (0, 2)])
        return self._panel(VGroup(cond, lamps), z), VGroup(cond, lamps)

    # 镜7 末帧：OZ 斜边 + 两直角边（坐标由 c2p 实时算）
    def _thumb_mod(self):
        o, u, z = np.zeros(3), self.THUMB_UNIT, EXAMPLE_Z
        p = c2p(z, o, u)
        px = c2p(complex(z.real, 0.0), o, u)
        ax_x = Arrow(c2p(-0.3, o, u), c2p(z.real + 0.6, o, u), buff=0,
                     color=INK, stroke_width=2, tip_length=0.12)
        ax_y = Arrow(c2p(-0.3j, o, u), c2p(complex(0, z.imag + 0.6), o, u), buff=0,
                     color=INK, stroke_width=2, tip_length=0.12)
        leg_a = Line(o, px, color=C_RE, stroke_width=4)
        leg_b = DashedLine(px, p, color=C_IM, stroke_width=4)
        oz = Arrow(o, p, buff=0, color=C_OK, stroke_width=5, tip_length=0.18)
        assert abs(np.linalg.norm(p - o) - modulus(z.real, z.imag) * u) < 1e-9
        f = MathTex("|z|", "=", r"\sqrt{a^2+b^2}", font_size=self.FS_SUB)
        f[0].set_color(C_OK)
        art = VGroup(ax_x, ax_y, leg_a, leg_b, oz, Dot(p, radius=0.06, color=C_OK))
        return self._panel(f, art), f

    def construct(self):
        self.camera.background_color = BG
        built = [self._thumb_i2(), self._thumb_part(), self._thumb_pure(), self._thumb_mod()]
        panels = [b[0] for b in built]
        targets = [b[1] for b in built]

        row = VGroup(*panels).arrange(RIGHT, buff=self.PANEL_BUFF)
        row.scale_to_fit_width(min(row.width, SAFE_WIDTH))
        row.move_to(UP * (CONTENT_TOP + CONTENT_BOTTOM) / 2)
        assert row.get_top()[1] <= CONTENT_TOP and row.get_bottom()[1] >= CONTENT_BOTTOM

        dims = [p.copy().fade(self.DIM_FADE) for p in panels]
        self.play(FadeIn(VGroup(*dims)), run_time=self.T_INTRO)

        # reveal_beats：i²=−1 → 虚部是 b → 纯虚数 → 模是 OZ 长度
        for k, (panel, tgt) in enumerate(zip(panels, targets)):
            swap = [FadeOut(dims[k]), FadeIn(panel),
                    panel.frame.animate.set_stroke(C_HALO, width=4)]
            if k > 0:
                swap.append(panels[k - 1].frame.animate.set_stroke(INK, width=2))
            self.play(*swap, run_time=self.T_SWAP)
            self.play(Indicate(tgt, color=C_HALO, scale_factor=1.12),
                      Flash(tgt.get_center(), color=C_HALO,
                            flash_radius=max(tgt.width, tgt.height) * 0.6 + 0.1),
                      run_time=self.T_FX)
            self.wait(self.T_HOLD)

        finish_shot(self)
