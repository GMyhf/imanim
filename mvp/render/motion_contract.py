"""82-M0 动画契约表 —— kind→必备动效 的机器可读登记表（Plan_82 D4 §4.1 M1~M6 + §4.2 闸门口径）。

用途分工（本棒只落数据+查询函数，不做接线）：
- **82-SD1~SD3**：按表逐 kind 认领，用 ``mvp/render/motion.py`` 的 ``PRIMITIVES`` 原语
  把 ``primitives`` 字段要求的动效落进各 builder；
- **82-SE**：把 :func:`check_shot` / :func:`missing_fields` 接进 review.py 当 ANIMATION
  blocking 闸门——「该 kind 缺哪个字段、渲染层会怎样退化」由 ``message`` 直接给出。

条目口径（A 级判据三件套，Plan_82 §2 动画化覆盖口径）：
1. ``primitives``：该 kind 必备的运动原语 id（须存在于 motion.PRIMITIVES；纯入场淡入
   不在列——B 级不算过）；
2. ``min_events``：镜内最少**内容运动事件**数（= MotionBeat 语义事件，不含入场与
   硬切边界；framediff 口径下即内容带动事件，D4 §2.1 主判据「墨迹阶梯」之上的形变事件）；
3. ``at``：与口播 cue 绑定的 at 语义（讲到哪动到哪；不绑定=缺陷，Plan_82 §3）。
``fields`` 是该 kind 的 props 必备动效字段规则（机检谓词，见 :func:`missing_fields`
的微型词汇表）；``serves`` 回答「这个运动让观众理解了什么」（动画服务于理解）。

豁免口径（Plan_82 §2：豁免候选仅纯转场/页眉页脚类无信息元素）：
- **kind 级：24 kind 全部登记为必备，零豁免**（``KIND_EXEMPT`` 为空 dict——
  「全流程全视频」「每一步都要动」不允许「这类不适用」）；
- **元素级白名单 ``ELEMENT_EXEMPT``**：仅页眉条/角标带/字幕带/边界硬切四类无信息
  结构件不计入动效要求，每条必须写明 ``reason``（SE 棒接 review 时同源引用）。
"""

from __future__ import annotations

from typing import Iterable, Optional

__all__ = [
    "MOTION_FAMILIES", "MOTION_REQUIRED", "KIND_EXEMPT", "ELEMENT_EXEMPT",
    "NARRATION_TRIGGERS", "contract_for", "families_of", "is_kind_exempt",
    "min_content_events", "primitives_for", "at_semantics", "missing_fields",
    "check_shot", "describe",
]

# ---- M1~M6 分类（D4 §4.1 原文口径；M2 收编几何拼合/图表生长，见各条目 serves）----
MOTION_FAMILIES = {
    "M1": "公式推导：逐 token 原位形变 + 数值飞入（标杆 Shot1/2/3）",
    "M2": "物理动态与图线：连续演化/描线/长箭/拼合/柱生长（标杆 Shot4 时钟 + D4 §4.1-M2）",
    "M3": "场与磁电：波次铺场 + 方向流动 + 指针连续旋转（D4 §4.1-M3）",
    "M4": "电路与光学：合闸动作 + 表针连续偏转 + 光线按因果顺序画出（D4 §4.1-M4）",
    "M5": "化学机理与微观：弯箭头 tail→head 描出 + 断键/态迁移逐粒子形变（D4 §4.1-M5）",
    "M6": "文本要点：逐条揭示 + 当前条强调 + 过往条压暗（D4 §4.1-M6）",
}

# ---- kind 级豁免：空。24 kind 无一例外全部必备（覆盖口径钉死）。----
KIND_EXEMPT: dict = {}

# ---- 元素级豁免白名单（仅纯转场/页眉页脚类无信息元素；每条必须带 reason）----
ELEMENT_EXEMPT = {
    "header_bar": {
        "what": "页眉（标题条 + 学科/学段标签，scene._assemble 固定件）",
        "reason": "全片固定的版面结构件、不承载本镜讲解步骤；给它加动效会抢正文注意力，"
                  "违反「动画服务于理解」——豁免的是无信息结构件，不是任何 kind。",
    },
    "corner_badge": {
        "what": "角标带（首镜 id / 末镜出处角标，scene._corner_tags）",
        "reason": "账目信息（出处/编号）只需可读不需动效；Plan_82 §2 明确豁免候选仅"
                  "页眉页脚类无信息元素，本条属之。",
    },
    "subtitle_band": {
        "what": "字幕带（mux ASS 道，内容带行窗之外）",
        "reason": "字幕逐字显示由配音时序驱动且已在 mux/review 各自校验；帧差分口径"
                  "本就排除字幕带（D4 §2.1），不计入镜内动效事件。",
    },
    "hard_cut_boundary": {
        "what": "镜头边界硬切（INTRO/OUTRO=0）",
        "reason": "硬切是转场不是动效（第四轮 F-2 决策）；差分统计排除边界 ±0.3s，"
                  "不得用「切镜闪变」充抵内容运动事件。",
    },
}

# ---- 口播触发词（D4 §4.2-1：口播含「代入/化简/联立」而镜内无 derivation ⇒ 打回）----
NARRATION_TRIGGERS = {
    "SUBSTITUTION_NEEDS_DERIVATION": {
        "keywords": ("代入", "化简", "联立", "解得"),
        "require_kind": ("derivation",),
        "message": "口播在讲代入/化简/联立，画面却用静态版式——推导类讲解必须落在 "
                   "derivation（token_chain/value_flyin 的载体），否则 A 级无从谈起。",
    },
}

# ---------------------------------------------------------------------------
# MOTION_REQUIRED：24 kind 逐一登记（键与 ir.VISUAL_KINDS 全等，test_motion 钉死）。
# 字段：family / serves(服务于什么理解) / primitives(motion.py id 元组) /
#       min_events(镜内最少内容运动事件) / fields(props 机检规则) /
#       at(与口播 cue 绑定的语义) / exempt+reason(本表全为 False，kind 级零豁免) /
#       note(存量定级与退化提示，来自 D4 §2 矩阵)。
# fields 规则语法（谓词词汇表见 _eval_when/_require_missing 实现）：
#   {"when": <条件>, "require": [<require...>], "message": str}
#   条件：always | mode==compass | mode:wire|solenoid | vt==true | state==both |
#         switch_present | meter_present | cases_present | forces_present |
#         arrows_present | steps>=2 | lines>=2 | n>=4 | n_cues>=2 | pairs_true
#   require：props.X（props 顶层字段在场）| lines>=2 / n>=4（长度/数值比较）|
#            any_step:sub|transform（任一步带其一）| each_case:at / each_arrow:at /
#            each_meter:reading（每个条目都带）
# ---------------------------------------------------------------------------

MOTION_REQUIRED = {
    # ---- M1 公式推导 ----
    "derivation": {
        "family": "M1",
        "serves": "逐步推导链让观众看见每个式子从上一个怎么变来、每个数从哪取——"
                  "复数标杆同款「推导过程」，杜绝整屏贴公式。",
        "primitives": ("token_chain", "value_flyin", "emphasis", "exit_stage"),
        "min_events": 2,
        "fields": (
            {"when": "steps>=2", "require": ["any_step:sub|transform"],
             "message": "steps≥2 时至少一步带 sub（数值飞入）或 transform"
                        "（本步由前第 k 步原位形变而来），否则退化为逐行淡入=B 级。"},
            {"when": "n_cues>=2", "require": ["any_step:at"],
             "message": "多 cue 镜须至少一步声明 at（cue 下标），否则推导与口播脱节。"},
        ),
        "at": "step.at=字幕 cue 下标，一拍一形（步 i 的形变在口播讲到步 i 时播）；"
              "sub 目标字母落定 ≤0.5s 强调。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B→A-：无 sub 时=逐行淡入；最新生产 plan sub 使用率 0，闸门倒逼。",
    },
    "formula": {
        "family": "M1",
        "serves": "公式逐符号书写（Write）让观众跟着读式子的结构，而不是闪一下的静图。",
        "primitives": ("draw", "emphasis"),
        "min_events": 1,
        "fields": (),
        "at": "Write 打在 cue0（公式即本镜主角）；既有 ShowPassingFlash 扫光保留为落定强调。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 C 级：整块瞬间出现+一次扫光；A 底线=逐符号书写。口播含代入/"
                "化简而版式仍是 formula ⇒ 触发 SUBSTITUTION_NEEDS_DERIVATION。",
    },
    # ---- M2 物理动态与图线 ----
    "incline": {
        "family": "M2",
        "serves": "斜面滑块由 a=g(sinθ−μcosθ) 公式驱动连续演化，观众看到「为什么这样滑」；"
                  "力箭从物体长出，力的来源与方向可见。",
        "primitives": ("clock", "draw", "token_chain", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "vt==true", "require": ["props.n>=4"],
             "message": "vt（频闪/演化）镜 n<4 时演化过程无从插值，必须给 n≥4"
                        "（与 review 现有 incline n 整数校验同尺）。"},
        ),
        "at": "演化段借 hold 帧随时钟推进；力箭揭示随对应 cue（每条力=一句口播）。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B/B-：incline_vt 频闪分批淡入是现存唯一「会动」范式，升 A=连续位移"
                "+Φ/I/F 同步显现（82-SC rod_rails 复用同壳）。",
    },
    "rod_rails": {
        "family": "M2",
        "serves": "同一时钟驱动杆的连续位移、速度/安培力箭头与 Φ/E/I/Q 实时读数——"
                  "观众看到「杆在动、量在变」，且读数是从同一时刻真值算出来的。",
        "primitives": ("clock", "draw", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["props.beats"],
             "message": "必须声明 beats（2~6 时钟拍数）：一拍一段运动，"
                        "缺省值虽能出片，但镜头与口播拍数无契约。"},
            {"when": "n_cues>=2", "require": ["props.at"],
             "message": "多 cue 镜须给 at（长度=beats）：杆的运动/读数按口播拍推进，"
                        "否则整段掉到镜尾兜底、与讲解脱同步。"},
        ),
        "at": "beat k ↔ at[k]：位移、箭头、读数在同一拍一起推进；讲到哪动到哪。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵：单杆模型曾只有文字卡；82-SC 起装置本体连续演化+同值源读数。",
    },
    "trajectory": {
        "family": "M2",
        "serves": "小球沿抛物线/圆轨道连续运动、速度箭随位置同步变向变长——观众看到"
                  "「轨迹是运动留下的痕迹」，不是点位清单。",
        "primitives": ("clock", "draw"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["props.n>=4"],
             "message": "n≥4 才够描述一条连续轨迹（D4 §4.2 闸门口径）。"},
        ),
        "at": "小球 MoveAlongPath/时钟演化跨全镜 cue 均匀铺；虚线轨迹 Create 与口播"
              "「它沿着这条线走」同步。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：位置点逐个淡入、轨迹整条静态。",
    },
    "graph_vt": {
        "family": "M2",
        "serves": "图线是描出来的（Create）、动点是走出来的——观众看到函数关系在生成，"
                  "cases 联动时「讲到哪段、哪段亮」。",
        "primitives": ("draw", "clock", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "cases_present", "require": ["each_case:at"],
             "message": "cases[].at 必须逐条给（review 已有同码；ANIMATION 闸门同源复用，"
                        "cases 与口播段一一对应才能做联动强调）。"},
        ),
        "at": "主线 Create 起于 cue0；cases[i].at 绑定强调/描点事件；面积/斜率注记跟 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 C（无 cases）/B-（有 cases）：主线/面积/描点全在 t=0 一次出现。",
    },
    "axis_graph": {
        "family": "M2",
        "serves": "每条曲线逐条描出，观众跟着笔走——「这条线是怎么长出来的」即坐标系的读法。",
        "primitives": ("draw", "emphasis"),
        "min_events": 2,
        "fields": (),
        "at": "曲线 i 的 Create 绑定其说明 cue（现有逐曲线 reveal 通道升级为 Create）；"
              "marks/guides 跟所属曲线同拍。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B-：仅第 2 条起曲线逐个淡入，首曲线/marks 静态。",
    },
    "force_diagram": {
        "family": "M2",
        "serves": "力箭从物体上**长出来**（GrowArrow），合成/分解按平行四边形逐边画出——"
                  "观众看到力有作用点、有方向、合力是「拼」出来的。",
        "primitives": ("draw", "token_chain", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "n_cues>=2", "require": ["forces>=1"],
             "message": "多 cue 镜力箭逐条揭示须 forces 与口播句对应"
                        "（每箭=一句，讲到哪个力哪个箭长出）。"},
        ),
        "at": "forces[i] 揭示绑定其点名 cue；synthesize/decompose 的辅助线 Create 先行、"
              "合力箭最后长出（因果序）。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：力箭头逐条淡入非生长；平行四边形整块出现。",
    },
    "figure": {
        "family": "M2",
        "serves": "几何图形的边是描出来的、拼图块是 Transform 搬过去的——a²+b²=c² 的"
                  "「拼合」必须被看见，否则勾股弦图只是装饰。",
        "primitives": ("draw", "token_chain", "yield_to"),
        "min_events": 1,
        "fields": (),
        "at": "构造步骤（画边/移块）绑定对应讲解 cue；结论标注落定强调。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 C：right_triangle/chord/ellipse 三 builder 零 tag 整幅静态。",
    },
    "stat_chart": {
        "family": "M2",
        "serves": "柱从基线长高、扇区从圆心扫开——「高度/角度=数值」这条编码规则"
                  "在生长瞬间被理解，而不是读成品图。",
        "primitives": ("draw", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["data>=2"],
             "message": "至少 2 个数据条目才有「逐柱/逐扇生长」的对比语义。"},
        ),
        "at": "bar/pie 条目 i 的生长绑定其数据 cue；点阵逐行铺。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：扇区/柱/点逐个淡入（非 GrowBar 生长）。",
    },
    # ---- M3 场与磁电 ----
    "field": {
        "family": "M3",
        "serves": "场从源区成波铺开×/· 渐次显现（场的「弥漫」被看见）、磁感线逐条描出、"
                  "电流/场强方向沿路流过、小磁针从旧指向**连续转**到新指向——"
                  "「看不见的场」变成看得见的生成与指向。",
        "primitives": ("draw", "clock", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "mode==compass", "require": ["props.from_angle", "props.to_angle"],
             "message": "compass 必须给 from_angle/to_angle（指针 Rotate 的初末态），"
                        "否则「指向」退化为定格贴图——这是 D4 点名最该有的 Rotate。"},
            {"when": "mode:wire|solenoid", "require": ["props.current"],
             "message": "wire/solenoid 必须给 current 方向（out/in/顺逆），"
                        "flow 描向才有依据；缺流向上的感线图仍是静图。"},
        ),
        "at": "铺场波次起于 cue0（场是背景）；指针旋转/环流循环绑定口播讲到该行为的 cue；"
              "flow 循环 ≤1 次（炫技上限）。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵：8 个 mode 全 C（零 tag、零 reveal、整屏一次铺满）——重灾区。",
    },
    # ---- M4 电路与光学 ----
    "circuit": {
        "family": "M4",
        "serves": "开关**合上**（闸臂 Rotate）、电流沿回路分时点亮、表针从 0 **连续偏转**"
                  "到读数——「闭合回路才有电流」的因果被走完，而不是看三个定格形态。",
        "primitives": ("clock", "draw", "emphasis", "yield_to"),
        "min_events": 2,
        "fields": (
            {"when": "switch_present", "require": ["props.close_at"],
             "message": "含开关元件必须声明合闸拍 close_at（cue 下标）——合闸动作与"
                        "「一合闸灯就亮」的口播同拍，closed 布尔定格不算。"},
            {"when": "meter_present", "require": ["each_meter:reading"],
             "message": "电表条目须带 reading（偏转终点），表针 Rotate 从 0 连续转到"
                        "reading/full_scale 角才成立。"},
        ),
        "at": "close_at=合闸动作拍；合闸后电流箭头按回路顺序 LaggedStart；表针偏转绑定"
              "读数讲解 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B-：导线/电流箭头/读数静态；开关/滑片/表针全是定格形态。",
    },
    "optics": {
        "family": "M4",
        "serves": "光线沿路画出且按 法线→入射→反射/折射→像 的因果顺序——观众看到像"
                  "是光线行为的结果；讲「折射角随入射角变」时角度连续转、折射线同步重算。",
        "primitives": ("draw", "clock", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "angle_range_present", "require": ["props.angle"],
             "message": "angle 给区间 [from,to] 时走 Rotate 连续演化（公式驱动、禁手填）；"
                        "单值 angle 至少光线 Create 按因果序。"},
        ),
        "at": "光线 i 的 Create 绑定其讲解 cue（入射先于折射、物先于像）。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：物→光线→像三拍淡入，光线不是沿路 Create 画出的。",
    },
    # ---- M5 化学机理与微观 ----
    "mechanism": {
        "family": "M5",
        "serves": "弯箭头 tail→head 按口播时序逐条描出（描的方向=电子流向本身）、断键用 "
                  "Transform 演「键变成孤电子对」——机理不是标注图，是事件序列。",
        "primitives": ("draw", "token_chain", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "arrows_present", "require": ["each_arrow:at"],
             "message": "每条弯箭头必须带 at（cue 下标）且口播一句=一箭（review 已有 "
                        "at 长度=箭数校验，ANIMATION 沿用同一把尺）。"},
        ),
        "at": "arrows[i].at 绑定第 i 条箭的描出事件；断键/成键 Transform 跟对应 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：弯箭头逐条淡入非 tail→head 描出（82-SB 锚点表落地后本条直接复用）。",
    },
    "particle_box": {
        "family": "M5",
        "serves": "before→after 是**逐粒子 Transform 到新位置**——「所有粒子都动了」被看见，"
                  "而不是两幅静图加一支箭头。",
        "primitives": ("token_chain", "draw", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "state==both", "require": ["n>=2"],
             "message": "双态镜 n≥2 才谈得上逐粒子迁移（LaggedStart 波次）。"},
        ),
        "at": "前态随 cue0 铺（wave 描法）；粒子迁移绑定「变化发生」的 cue；后态落定强调。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B-/C：单态=C 级；单态 A 底线=粒子波次生长+一次脉动强调（无后态可迁）。",
    },
    "microstate": {
        "family": "M5",
        "serves": "「点一个数一个」的递增计数让观众真的把微观态**数出来**，"
                  "排列数不是背的。",
        "primitives": ("reveal", "clock", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["cells>=2"],
             "message": "cells≥2 才有点数递进的计数语义。"},
        ),
        "at": "面板/格子 i 与计数器读数同拍（时钟计数通道驱动），绑定「怎么数」的 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：面板逐个淡入，微观态「数出来」无逐步计数。",
    },
    "energy_dist": {
        "family": "M5",
        "serves": "kT 变了粒子怎么重新分布——逐粒子迁移到新能级（LaggedStart）+温度拨盘"
                  "连续演化，「分布随温度流」被看见。",
        "primitives": ("token_chain", "clock", "reveal"),
        "min_events": 1,
        "fields": (
            {"when": "always", "require": ["levels>=2", "kT>=1"],
             "message": "levels≥2 且 kT 给出（或给区间）才能演「升温→重分布」的迁移过程。"},
        ),
        "at": "各 kT 面板揭示绑定各自 cue；粒子重分布在「升温」口播拍上演化。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：kT 面板逐个淡入，粒子重分布无演化。",
    },
    # ---- M6 文本要点 ----
    "steps": {
        "family": "M6",
        "serves": "逐条揭示+当前条强调+过往条压暗——观众的注意力跟着讲解走，"
                  "「每一步都要动」在文字镜的兑现（成本≈0）。",
        "primitives": ("reveal", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["lines>=2"],
             "message": "lines≥2 才成立逐条揭示；单行要点请改用 callout。"},
            {"when": "n_cues>=2", "require": ["props.at"],
             "message": "多 cue 镜须给 at 数组（行→cue 下标映射；与 props.lines 等长），"
                        "否则揭示与口播脱节（引擎 _tag_progressive 只是按进度兜底）。"},
        ),
        "at": "行 i 揭示=第 i 个 cue；揭示瞬间当前条 Indicate、上一条压暗 0.55（reveal 壳）。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：逐行裸 FadeIn，无当前强调/过往压暗。",
    },
    "summary": {
        "family": "M6",
        "serves": "同 steps：收束镜的每条结论逐个点亮、讲过的压暗退到背景——"
                  "回顾有动线，不是成品清单。",
        "primitives": ("reveal", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["points>=2"],
             "message": "points≥2（summary 的条目字段名）才成立逐条揭示。"},
            {"when": "n_cues>=2", "require": ["props.at"],
             "message": "多 cue 镜条目须绑定 at（口径同 steps：at 数组与条目等长）。"},
        ),
        "at": "同 steps：条目 i ↔ cue i。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B。",
    },
    "compare": {
        "family": "M6",
        "serves": "逐栏逐行揭示之外，同下标左右项**同拍出现**（pairs）或用 "
                  "TransformFromCopy 拉对应线——「对照」的对应关系被看见。",
        "primitives": ("reveal", "value_flyin", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "n_cues>=2", "require": ["props.at"],
             "message": "多 cue 镜须揭示节拍绑定 at；pairs:true 时左右同拍（可选加强）。"},
        ),
        "at": "栏/行揭示绑定 cue；pairs 同下标项同拍，对应线落在两者都被讲到的 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：逐栏逐行淡入、无左右对应关系动画。",
    },
    "table": {
        "family": "M6",
        "serves": "逐行揭示、行内单元格按列错峰——表格是「一行一行读」的，"
                  "揭示节奏即阅读节奏。",
        "primitives": ("reveal", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["rows>=2"],
             "message": "rows≥2 才有逐行揭示；单行数据请改用 callout/formula。"},
        ),
        "at": "行 i ↔ cue i（或引擎按字幕进度分批兜底）；表头 cue0 先行。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：逐行淡入、无列错峰。",
    },
    "mind_map": {
        "family": "M6",
        "serves": "连线从根**生长**、子项跟着连线到位——知识树的「由根及枝」结构"
                  "在延展瞬间被理解。",
        "primitives": ("draw", "reveal", "emphasis"),
        "min_events": 2,
        "fields": (
            {"when": "always", "require": ["branches>=1"],
             "message": "至少一条分支才成立「由根生长」；根+0 枝请改用 title/callout。"},
        ),
        "at": "分支 i 的连线 Create 先行、子项 FadeIn 跟随，绑定分支讲解 cue。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：分支逐块淡入，连线不延展。",
    },
    "callout": {
        "family": "M6",
        "serves": "分段逐条揭示已有，升级为「当前条强调+过往条压暗」——结论卡的揭晓"
                  "节奏与口播句一一对应。",
        "primitives": ("reveal", "emphasis"),
        "min_events": 1,
        "fields": (),
        "at": "分段 i 沿用 _reveal_at cue 绑定；flash/wiggle/indicate 语气点名保留。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 B：分段逐条+FX 已有，A=补过往压暗（reveal 壳直接复用）。",
    },
    "title": {
        "family": "M6",
        "serves": "主标题**写出来**（Write）、副标题自主标题 TransformFromCopy 接续——"
                  "开场也在「生成」，给全片定下过程动画的基调（B 级都不许开场即静）。",
        "primitives": ("draw", "value_flyin", "emphasis"),
        "min_events": 1,
        "fields": (),
        "at": "主标题 cue0 Write；副标题在 cue0 末或 cue1 从主标题复印接续。",
        "exempt": False, "reason": "",
        "note": "D4 矩阵 C：无任何 tag、单块镜 t=0 整块出现。",
    },
}


# ---------------------------------------------------------------------------
# 查询/机检函数（SE 接 review.py 用；本棒交付只含数据+这些纯函数）
# ---------------------------------------------------------------------------

_COUNT_KEYS = {
    # props 里取「条目数」的字段名 → 计数法
    "steps": "steps", "lines": "lines", "points": "points", "rows": "rows",
    "cases": "cases", "curves": "curves", "forces": "forces", "elements": "elements",
    "arrows": "arrows", "branches": "branches", "data": "data", "species": "species",
    "bonds": "bonds",
}


def _count(name: str, props: dict) -> int:
    """props 某条目集合的规模；int 值字段（n/cells）直接取值。"""
    if name == "n":
        v = props.get("n", 0)
        return int(v) if isinstance(v, (int, float)) else 0
    if name == "cells":
        return int(props.get("cells", 0) or 0)
    if name == "levels":
        return len(props.get("levels", []) or [])
    if name == "kT":
        return 1 if props.get("kT") else 0
    key = _COUNT_KEYS.get(name, name)
    v = props.get(key)
    return len(v) if isinstance(v, (list, tuple)) else (1 if v else 0)


def _cmp(lhs: int, op: str, rhs: float) -> bool:
    return {"<=": lhs <= rhs, ">=": lhs >= rhs, "==": lhs == rhs,
            "<": lhs < rhs, ">": lhs > rhs}[op]


def _eval_when(cond: str, props: dict, n_cues: int) -> bool:
    """微型谓词词汇表（见模块 docstring）。未知条件按不满足处理（保守：不误伤）。"""
    if not cond or cond == "always":
        return True
    if cond == "n_cues>=2":
        return n_cues >= 2
    if cond.endswith("_present"):
        base = cond[: -len("_present")]
        if base == "switch":
            return any(e.get("type") == "switch" for e in props.get("elements", []) or []
                       if isinstance(e, dict))
        if base == "meter":
            return any(e.get("type") in ("ammeter", "voltmeter", "galvanometer", "meter")
                       for e in props.get("elements", []) or [] if isinstance(e, dict))
        if base == "angle_range":
            v = props.get("angle")
            return isinstance(v, (list, tuple)) and len(v) == 2
        return _count(base, props) > 0
    if cond.endswith("_true"):
        return bool(props.get(cond[: -len("_true")]))
    if "==" in cond:
        key, val = (s.strip() for s in cond.split("==", 1))
        if val == "true":
            return bool(props.get(key))
        return props.get(key) == val
    if cond.startswith("mode:") or ":" in cond.split("==")[0]:
        key, alts = cond.split(":", 1)
        return props.get(key) in tuple(a.strip() for a in alts.split("|"))
    for op in (">=", "<=", "==", ">", "<"):
        if op in cond:
            key, num = cond.split(op, 1)
            return _cmp(_count(key.strip(), props), op, float(num.strip()))
    return False


def _require_missing(tok: str, props: dict) -> Optional[str]:
    """require 词条是否未满足；满足返回 None，否则返回人类可读缺口描述。"""
    if tok.startswith("props."):
        rhs = tok[len("props."):]
        for op in (">=", "<=", "==", ">", "<"):
            if op in rhs:
                key, num = rhs.split(op, 1)
                return None if _cmp(_count(key.strip(), props), op, float(num.strip())) else tok
        return None if props.get(rhs) not in (None, "", [], {}) else f"{rhs}（props 顶层字段缺失）"
    for op in (">=", "<=", ">", "<", "=="):
        if op in tok:
            key, num = tok.split(op, 1)
            return None if _cmp(_count(key.strip(), props), op, float(num.strip())) \
                else tok
    if ":" in tok:  # any_step:sub|transform / each_case:at / each_meter:reading / any_line:at
        head, keys = tok.split(":", 1)
        cands = tuple(k.strip() for k in keys.split("|"))
        if head.startswith("any_"):
            coll = props.get("steps" if head == "any_step" else
                             "lines" if head == "any_line" else
                             head[4:] + "s", []) or []
            return None if any(isinstance(x, dict) and any(x.get(c) not in (None, "", [], {})
                              for c in cands) for x in coll) else tok
        if head.startswith("each_"):
            coll = props.get("cases" if head == "each_case" else
                             "arrows" if head == "each_arrow" else head[5:] + "s", []) or []
            if head == "each_meter":
                coll = [e for e in props.get("elements", []) or [] if isinstance(e, dict)
                        and e.get("type") in ("ammeter", "voltmeter", "galvanometer", "meter")]
            if not coll:
                return tok
            return None if all(isinstance(x, dict) and any(x.get(c) not in (None, "", [], {})
                             for c in cands) for x in coll) else tok
    return None  # 未知 token 保守放行，SE 扩词汇表时显式登记


def missing_fields(kind: str, props: dict, n_cues: int = 0) -> list:
    """该 kind 的 props 缺哪些必备动效字段；返回 [(规则 message, 缺口), …]，空表=合规。"""
    entry = contract_for(kind)
    out = []
    for rule in entry.get("fields", ()):
        if _eval_when(rule.get("when", "always"), props or {}, n_cues):
            gaps = [g for g in (_require_missing(t, props or {}) for t in rule["require"]) if g]
            if gaps:
                out.append((rule["message"], gaps))
    return out


def contract_for(kind: str) -> dict:
    """取某 kind 的契约条目；未知 kind 抛 KeyError（提示先对齐 ir.VISUAL_KINDS）。"""
    if kind not in MOTION_REQUIRED:
        raise KeyError(f"motion_contract: kind {kind!r} 未登记（须与 ir.VISUAL_KINDS 同步，"
                       f"24 kind 全覆盖是 Plan_82 覆盖口径）")
    return MOTION_REQUIRED[kind]


def families_of(family: str) -> tuple:
    """按 M1~M6 反查 kind（SD 棒认领靶子用）。"""
    return tuple(k for k, v in MOTION_REQUIRED.items() if v["family"] == family)


def is_kind_exempt(kind: str) -> bool:
    return bool(KIND_EXEMPT.get(kind)) or bool(contract_for(kind).get("exempt"))


def min_content_events(kind: str) -> int:
    return int(contract_for(kind)["min_events"])


def primitives_for(kind: str) -> tuple:
    return tuple(contract_for(kind)["primitives"])


def at_semantics(kind: str) -> str:
    return contract_for(kind)["at"]


def check_shot(visuals: Iterable[dict], narration: str = "", n_cues: int = 0) -> list:
    """ANIMATION 闸门的最小核：对一镜的 visuals 列表给出违规文本（空=合规）。

    校验面：①kind 已登记；②必备 props 动效字段（:func:`missing_fields`）；
    ③口播触发词（代入/化简/联立 ⇒ derivation 在场）。SE 接线 review.py 时以本函数
    为唯一事实源；返回的字符串直接可作为 review finding 的 message。
    """
    vs = list(visuals or [])
    kinds = {v.get("kind") for v in vs}
    out = []
    for v in vs:
        kind = v.get("kind")
        if kind not in MOTION_REQUIRED:
            out.append(f"ANIMATION/UNKNOWN_KIND: {kind!r} 不在 24 kind 契约表内")
            continue
        if is_kind_exempt(kind):
            continue
        for message, gaps in missing_fields(kind, v.get("props") or {}, n_cues):
            out.append(f"ANIMATION/{kind.upper()}: {message} 缺口={gaps}")
    text = narration or ""
    for code, rule in NARRATION_TRIGGERS.items():
        if any(kw in text for kw in rule["keywords"]) \
                and not (set(rule["require_kind"]) & kinds):
            out.append(f"ANIMATION/{code}: {rule['message']}")
    return out


def describe(kind: str) -> str:
    """单 kind 契约的可读打印（报告/回灌文案用）。"""
    e = contract_for(kind)
    lines = [f"[{kind}] {e['family']}  exempt={e['exempt']}"]
    lines.append(f"  serves: {e['serves']}")
    lines.append(f"  primitives: {', '.join(e['primitives'])}")
    lines.append(f"  min_events: {e['min_events']}   at: {e['at']}")
    for r in e["fields"]:
        lines.append(f"  field-rule when({r['when']}) require{list(r['require'])}: {r['message']}")
    if e.get("note"):
        lines.append(f"  D4 基线: {e['note']}")
    return "\n".join(lines)
