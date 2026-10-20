# project1（澄象）

把**结构化知识点**直接变成**可上课用的讲解短视频**的最小可演示管线。
定位是 MVP（最小演示），当前聚焦初中—大二学段的数理化知识讲解。

一句话主张：**讲得对 + 讲得完 + 敢直接拿去上课**——不是"更好看"。

## 它解决什么

理科抽象概念在纸面上是静态的，很多学校也没有条件做实验。本项目用一条**确定性**
管线，把教材知识点变成带配音、带字幕、时长可控的动态讲解视频，并且：

- **中间产物可见可改**：分镜脚本（plan.json）是结构化 IR，老师能看到、能改、能重渲；
- **时长是硬约束**：先按自然语速实测配音，再反推每个镜头的秒数，成片落在目标 ±10% 内；
- **不交付赶课的片子**：整片口播量除以可说窗口，反解出需要的 TTS 提速档，超过 +2 档直接打回，
  并给出"精简到 N 字"或"放宽到 M 秒"两个可执行数字——网关中文语音自然讲课实测 4.7 字/秒；
- **定义性限定钉得住**：每个知识点条目用 `must_say` 声明"这条必须说出口的几句"（`a ≠ 0`、
  椭圆定义里的"常数大于两定点间距离"、`F` 是**合**外力……），整片一次都没说即打回。
  精简口播最容易误删的恰好是这些限定，所以由闸门正向钉住，而不是靠人记着。
- **敢自我打回**：渲染前有 18 类静态监督闸门（超载、节奏、安全区、字形、术语、限定缺失……），
  不合格就不出片，而不是默默出一支坏的；
- **零 LLM 依赖**：检索、分镜、渲染、配音全部本地可跑，边际成本接近于电费。

## 管线

```
Brief（学科/学段/知识点/时长/风格）
  → Knowledge（本地资料库检索，命中教材锚点，无 LLM）
  → Plan（分镜 IR：镜头、视觉原语、旁白、提示点）
  → review（静态监督闸门，不过则拒绝出片）
  → ManimCE 渲染（无声画面，逐镜头时长由 IR 决定）
  → TTS（Windows SAPI 离线中文配音）→ 字幕对齐 → subs.srt
  → ffmpeg 混流（1080p30 + 48kHz 立体声 AAC）
  → 时长/音画漂移闸门 → 成片 + sidecar.json
```

八种视觉原语（Spec_Product A5）：`title` `formula` `compare` `graph_vt` `figure`
`steps` `summary` `callout`。学科 `math/physics/chemistry`，学段 `G8/G9/H1/H2`。

## 快速开始

环境（Windows，已实测的组合）：

| 组件 | 版本 / 说明 |
| --- | --- |
| Python | 3.14.8 |
| manimce | 0.22.0（`pip install manim`）|
| ffmpeg | 单文件即可，需带 libass；**不需要 ffprobe** |
| LaTeX | **不需要**——全片用 Text/Pango 排版，公式由管线自己做斜体与上下标 |
| 配音 | Windows SAPI + Huihui Desktop 中文语音（离线，免费）|

```bash
# 路径可通过环境变量覆盖，默认值见 run.py
export MVP_FFMPEG_DIR=/path/to/ffmpeg      # 含 ffmpeg.exe 的目录
export MVP_MANIM_BIN=/path/to/manim        # manim 可执行文件

cd mvp
python run.py --subject physics --grade H1 --topic 加速度 --seconds 120 --style clean
```

产物落在 `mvp/out/<run>/`：`brief.json` `plan.json` `review.json` `subs.srt` `sidecar.json`
与按 `{学科}-{学段}-{知识点}-{秒数}-{hash}.mp4` 命名的成片。过路文件（`silent.mp4`
`track.wav` `final.mp4` `audio/` `media/`）只在失败时留着查问题，出片成功后当场清掉。

其他入口：

```bash
python batch.py --out ../.local/batch --jobs 4 --quality fullhd   # 整份语料库批量出片
python web/server.py                                             # 前端页面（纯标准库 http.server）
python tests/run_tests.py                                        # 测试
```

控制台若为 GBK 编码，先 `export PYTHONIOENCODING=utf-8`，否则中文输出会崩。

## 目录

```
mvp/
  run.py            A0 总控：一条命令 Brief → 成片
  batch.py          批量入口：扫语料库并发出片 + 汇总表
  pipeline/         ir（数据结构与常量）、knowledge（检索）、storyboard（分镜）、
                    review（静态监督闸门）、mux（混流与烧录）
  render/scene.py   ManimCE 渲染层：排版、八原语、揭示节奏
  audio/tts.py      SAPI 配音与时长测量
  web/              前端框体 + 作业执行器（可改分镜后重渲）
  pipeline/data/kp/ 知识点语料（结构化 JSON，含教材锚点 refs）
Projrct_Plan/       计划与规格：Schedule（核心）、Spec_*、Ref_*、Eval_*
corpus/             第三方教材/数据集原件（不入库，见 MANIFEST.txt）
.local/             本机运行时、虚拟环境与渲染产物（不入库）
```

## 当前状态

按 `Projrct_Plan/Project_Schedule.txt` 的 S0→S4 流程推进。S0/S1/S2.1/S2.3/S2.4（前端框体）
已关闭；S2.2（小体量试跑 + 量表验收）正在对 batch_v7 的 8 支 1080p30 成片（数学 4、物理 3、化学 1）
做两名互不知情评审人的独立评分；
S2.4 部署、S2.5 留档、S2.6 交付物料在后头。验收判据来自 `Spec_Scale.txt`：无一票否决项，
S ≥ 4.5、U/A/C ≥ 3.5、总分 ≥ 4.0。

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
