# project1（澄象）

把**结构化知识点**直接变成**可上课用的讲解短视频**的最小可演示管线。
定位是 MVP（最小演示），当前覆盖初中至大学基础课的数理化讲解（学段 G8–U2，按可核教材来源标注）。

一句话主张：**讲得对 + 讲得完 + 敢直接拿去上课**——不是"更好看"。

## 它解决什么

理科抽象概念在纸面上是静态的，很多学校也没有条件做实验。本项目用一条**确定性**
管线，把教材知识点变成带配音、带字幕、时长可控的动态讲解视频，并且：

- **中间产物可见可改**：分镜脚本（plan.json）是结构化 IR，老师能看到、能改、能重渲；
- **时长是硬约束**：先按自然语速实测配音，再反推每个镜头的秒数，成片落在目标 ±10% 内；
- **不交付赶课的片子**：整片口播量除以可说窗口，反解出需要的 TTS 提速档，超过 +2 档直接打回，
  并给出"精简到 N 字"或"放宽到 M 秒"两个可执行数字——网关中文语音自然讲课实测 4.7 字/秒
  （网关 TTS 的 speed 参数实测无效，一律按自然语速合成，sidecar 里如实记账）；
- **定义性限定钉得住**：每个知识点条目用 `must_say` 声明"这条必须说出口的几句"（`a ≠ 0`、
  椭圆定义里的"常数大于两定点间距离"、`F` 是**合**外力……），整片一次都没说即打回。
  精简口播最容易误删的恰好是这些限定，所以由闸门正向钉住，而不是靠人记着；
- **敢自我打回**：渲染前有 24 类静态监督码（超载、节奏、安全区、字形、术语、限定缺失、
  动效缺位……），阻断类不合格就不出片，而不是默默出一支坏的；
- **物理是真算出来的**：`physics/` 的定步长 RK4 积分模块驱动过程动画（斜面、轨迹、粒子盒、场线……），
  画面随数值演化，不是摆关键帧；
- **检索、校验、渲染、合成零 LLM 依赖**，全部本地可跑，边际成本接近电费；
  模型棒次集中在少数起草与表达环节（见下），关闭时管线走确定性兜底照常出片。

## 管线

```
Brief（学科/学段/知识点/时长/风格）
  → Knowledge（本地资料库检索，命中教材锚点，无 LLM）
  → Plan（分镜 IR：24 种视觉原语）
  → review（24 类静态监督码，含动效闸与记账码；阻断类不过即拒绝出片）
  → ManimCE 渲染（无声画面；公式走 LaTeX(xelatex+dvisvgm)，缺 TeX 自动退回 Pango 排版）
  → TTS（网关 qwen3-tts-flash）→ 字幕对齐 → subs.srt
  → ffmpeg 混流（1080p30 + 48kHz AAC）→ 时长/音画漂移闸门 → 成片 + sidecar.json
```

模型使用纪律（如实）：大模型棒次集中在**库外条目的起草（K0）、分镜生成与改写（A3）、
朗读稿转写（VOICEOVER）、成片视觉回审（A8）**等少数环节，另有独立评分的模型辅助判分（S22，
只依据分镜文本打分、不产内容，扣分须带分镜原文引文方可生效）。`pipeline/llm_client.py`
统一管理：两套 provider（缺省 ModelScope API-Inference，可 `QX_LLM_PROVIDER=gateway` 切回
旧网关），各棒次默认关闭、按环境变量逐棒开启（部署侧 `deploy/start.sh` 缺省开 K0/A3/VOICEOVER）。
`pipeline/flow/` 另有一版多棒次视觉化流程（K1→K2→P→V0→M1→M2→…→A8→S22，AgentFlow v2）
在试行，尚未进入产品链路。

知识分两层：

- **已核对知识库** `pipeline/data/kp/`：16 条（数学 5 / 物理 6 / 化学 5），逐条人工核对并带
  教材章节与课标出处；学段按可核教材来源标注——12 条覆盖初二至高二，化学另有 4 条为大学
  基础课（U2）。
- **草稿库** `pipeline/data/kp_auto/`：库外知识点由 K0 起草，出处只允许来自语料字面命中并
  写明书名页码，未命中则显式标记"模型起草、未核对出处"；人工逐字核对后才晋升进已核对知识库。

## 快速开始

环境（Windows，已实测的组合）：

| 组件 | 版本 / 说明 |
| --- | --- |
| Python | 3.14.8 |
| manimce | 0.22.0（`pip install manim`）|
| ffmpeg | 单文件即可，需带 libass；**不需要 ffprobe** |
| LaTeX | **可选**——公式版走 `xelatex` + `dvisvgm`；探测不到自动退回 Unicode/Pango 排版，不挡出片 |
| 字体 | 本机默认 SimSun / Times New Roman（可用 `MVP_TEXT_FONT` / `MVP_LATIN_FONT` 覆盖），容器走开源替代 |
| 配音 | 网关 TTS（`qwen3-tts-flash`），需 `QX_TTS_API_KEY`；不配则生成如实报错，画廊不受影响 |

```bash
# 路径与密钥均通过环境变量配置，密钥绝不入库
set MVP_FFMPEG_DIR=D:\path\to\ffmpeg       # 含 ffmpeg.exe 的目录
set MVP_MANIM_BIN=D:\path\to\manim         # manim 可执行文件
set QX_TTS_API_KEY=...                     # 配音网关密钥（必需）
set QX_LLM_API_KEY=...                     # 推理后端密钥（缺省 ModelScope API-Inference）

cd mvp
python run.py --subject physics --grade H1 --topic 加速度 --seconds 120 --style clean
```

产物落在 `mvp/out/<run>/`：`brief.json` `plan.json` `review.json` `subs.srt` `sidecar.json`
与按 `{学科}-{学段}-{知识点}-{秒数}-{hash}.mp4` 命名的成片。过路文件（`silent.mp4`
`track.wav` `final.mp4` `audio/` `media/`）只在失败时留着查问题，出片成功后当场清掉。

其他入口：

```bash
python batch.py --out ../.local/batch --jobs 4 --quality fullhd   # 整份语料库批量出片
python web/server.py                                             # Web 端（改分镜重渲、应用内反馈）
python tests/run_tests.py                                        # 测试
```

控制台若为 GBK 编码，先 `set PYTHONIOENCODING=utf-8`，否则中文输出会崩。

容器与魔搭创空间部署（Docker、字体替代、密钥注入、重建检查单）见 `deploy/README.md`。

## 目录

```
mvp/
  run.py            A0 总控：一条命令 Brief → 成片
  batch.py          批量入口：扫语料库并发出片 + 汇总表
  pipeline/         ir（数据结构与常量）、knowledge（确定性检索）、storyboard（分镜）、
                    review（静态监督）、mux（混流与烧录）、kp_draft（K0 起草通道）、
                    llm_client（模型棒次与双 provider）、scoring_llm（独立评分辅助）、
                    flow/（AgentFlow v2 试行桥接，未进产品链路）
  render/           ManimCE 渲染层：scene.py 过程动画 + motion_contract（动效契约）
  physics/          定步长 RK4 物理积分模块（integrator/particle/replay/graphsync，共 564 行）
  audio/tts.py      网关 TTS 配音与时长测量（重试、语速记账）
  web/              前端框体 + 作业执行器（改分镜重渲、反馈落盘与数据集同步）
  tests/            全量回归（含每条监督码的"必然命中"反向用例与字体检索级复检）
  pipeline/data/kp/       已核对知识点（结构化 JSON，带教材/课标出处）
  pipeline/data/kp_auto/  K0 草稿条目（强制来源标记，未核对出处显式标注）
deploy/             Dockerfile、start.sh、build_space.py 与部署 README
Projrct_Plan/       计划与规格：BP（商业计划书）、Spec_*、Eval_*/Audit_*（评审原件）、SubTask 台账
corpus/             第三方教材/数据集原件（不入库，见 MANIFEST.txt）
.local/             本机运行时、日志与渲染产物（不入库）
```

## 当前状态（如实）

- 线上版本（#81）已部署魔搭创空间 `chengxiang_gallery`：画廊 + 在线生成 + 分镜编辑重渲。
- #82 动画化整改在途：全链路 builder 过程动画化已铺开（电路/斜面/轨迹/粒子盒等），
  静态监督码扩至 24 类（含 ANIMATION 动效闸与 TEXT_ONLY 记账码）；模型后端已切换为
  ModelScope API-Inference（TTS 仍走原网关）。**尚未重新部署。**
- 验收：五轮独立复评已完成，最新一批（batch_v8）批均总分 4.55、可核验维度 8/8、
  判定"有条件通过"；评审原文与交叉裁定见 `Projrct_Plan/Eval_*` 与 `Audit_*`，
  未过线的历史轮次同样公开——本项目不替自己发奖状。
- 回归：全量测试 905 项（`tests/run_tests.py`，收口复核日志见 `.local/`）。

## 版权声明

- **代码与结构化数据**（`mvp/` 全树，含知识点 JSON；**不含下方语料目录**）：MIT，见 `LICENSE`。
  版权持有人署名当前写作 `project1（澄象）`，正式发布前需替换为实际署名的作者/团队名。
- **参考原件**：项目根 `corpus/`（教材扫描、数据集等 232MB）**不进版本库**，只留
  `corpus/MANIFEST.txt` 清单；逐条来源与可外发体积见该清单。学习与研究性使用无碍，商用需先逐项确认授权。
- **出处定位语料** `mvp/pipeline/data/corpus/`：团队自行 OCR 的教材纯文本，是起草环节（K0）的检索工具，
  命中片段（每条 ≤400 字）只作参照并回传书名与页码，语料本身不进渲染层。该目录**不在 MIT 开源范围内**、
  不授权再分发，版权归原出版社；赛事演示期随创空间镜像发布，商用与二次分发前整目录剔除并替换为授权语料。
- **生成的视频**：字体走开源替代（Noto Serif CJK / TeX Gyre / Liberation），配音走第三方网关 TTS，
  画面与文字中不复制教材原文——片中只标注章节与课标出处。因此成片的可分性问题收敛为"出处引用是否规范"，
  而非"是否携带教材内容"。商用授权策略待定，当前按**非商业演示**使用。
