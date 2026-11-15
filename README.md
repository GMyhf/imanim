---
domain: multi-modal
tags: [数学, 物理, 化学, 教学视频, Manim, 可解释中间产物]
datasets: {evaluation: [], test: [], train: []}
models: []
license: MIT
---

# 澄象 · 知识点讲解短视频管线（MVP 演示）

把**结构化知识点**直接变成**可上课用的讲解短视频**：一条命令从教材锚点走到带配音、带字幕、
时长可控的 1080p 成片，中间产物（分镜 IR）可见可改可重渲。

## 这里能看什么

首页是**作品墙**：每条知识点一支成片，卡片上可进分镜查看/修订；成片与中间产物仍可经接口下载核对——

| 文件 | 它是什么 |
| --- | --- |
| `*.mp4` | 成片（1080p30，字幕为独立轨，48kHz AAC）|
| `plan.json` | 分镜 IR：每个镜头的标题、口播、视觉原语、提示点、教材出处 |
| `subs.srt` | 字幕，按实测语音时长对齐生成 |
| `review.json` | 渲染前静态监督闸门的结果（空数组 = 全部通过）|
| `sidecar.json` | 运行元数据：时长偏差、语速、字幕条数、体积、耗时 |

点开任一条可以看到"这句话为什么在这里、画面为什么是这个图"，这是本项目和"给个 prompt 出视频"
最大的区别：**中间产物是一等公民**，老师能改分镜里的一句口播或一个镜头秒数再重渲。

## 管线

```
Brief（学科/学段/知识点/时长/风格）
  → Knowledge（本地资料库检索，命中教材锚点，无 LLM）
  → Plan（分镜 IR：24 种视觉原语）
  → review（24 类静态监督闸门，不过则拒绝出片）
  → ManimCE 渲染（无声画面；公式走 latex+dvisvgm，缺 TeX 自动退回 Pango 排版）
  → TTS（网关 qwen3-tts-flash，HTTP POST /v1/audio/speech）→ 字幕对齐 → subs.srt
  → ffmpeg 混流 → 时长/音画漂移闸门 → 成片 + sidecar.json
```

三条我们认为值得单独说的设计：

1. **时长是硬约束，且按实测反推**。先按自然语速实测每段配音时长，再反写每个镜头的秒数，
   成片落在目标 ±10% 内；不是"先渲染再剪"。
2. **不交付赶课的片子**。整片口播量 ÷ 可说窗口，反解出需要的 TTS 提速档，超过 +2 档直接打回，
   并给出"精简到 N 字"或"放宽到 M 秒"两个可执行数字。网关中文语音自然讲课实测 4.7 字/秒。
   （网关 TTS 的 speed 参数实测无效，现一律按自然语速合成，档位照收但忽略——sidecar 里如实记账。）
3. **定义性限定钉得住**。每个知识点条目用 `must_say` 声明"这条必须说出口的几句"
   （`a ≠ 0`、椭圆定义里的"常数大于两定点间距离"、`F` 是**合**外力……），整片一次都没说即打回。
   精简口播时最容易误删的恰好是这些限定，所以交给闸门正向钉住，而不是靠人记着。

## 当前状态（如实）

- 语料：16 条人工核对的知识点（数学 5 / 物理 6 / 化学 5），学段 G8–U2（学段由可核教材来源定）。
- 验收：按四维量表（科学性/易懂/美学/完成度）做多轮双人独立复评，至今尚未整体过线——**本项目不声称已通过验收**。
- 部署：魔搭创空间 docker 版（`Dockerfile` + `start.sh`，监听 `0.0.0.0:7860`）。镜像**尚未经 `docker build` 验证**；
  在线生成依赖环境变量注入的两套密钥（推理后端 `QX_LLM_API_KEY`、配音网关 `QX_TTS_API_KEY`），
  缺密钥或字体标定失败时如实报错，作品墙浏览不受影响。

## 本地运行

```bash
cd mvp
python run.py --subject physics --grade H1 --topic 加速度 --seconds 120 --quality draft
python web/server.py --port 8123      # 作品墙 / 改分镜重渲 / 反馈
```

需要 ManimCE 0.22.0 与 ffmpeg（Linux 下设 `MVP_FFMPEG_DIR`）。没有配音密钥时设 `QX_TTS_ENGINE=edge`
改用 Edge 在线语音（需 `pip install edge-tts`）即可完整出片；LLM 各环节默认关闭，走确定性兜底。

## 许可与素材

- 代码与结构化数据（含知识点 JSON）：MIT，见 `LICENSE`。
- 字体：开发机用系统字体（Windows 上的 SimSun/Times New Roman，商业授权随系统）；
  Linux 镜像只打包开源替代（Noto Serif CJK / TeX Gyre / Liberation），不含任何商业字体。
- 配音：第三方网关 TTS 服务（qwen3-tts-flash），密钥经 env 注入；不再依赖系统语音。
- 片中只标注教材章节出处、不复制教材原文；知识条目与成片文字均由团队自行撰写。
- 出处定位语料：`mvp/pipeline/data/corpus/` 下为团队自行 OCR 的教材纯文本，**只用于起草环节的
  字面命中**——命中片段（每条 ≤400 字）喂给 K0 作参照并回传书名与页码，语料本身不进渲染层；
  条目与成片措辞由模型据此起草，再走出片闸门与人工核对。该目录不属于本项目的 MIT 开源范围、
  不授权再分发，版权归原出版社所有。赛事演示期随空间镜像一起发布，商用与二次分发前整目录剔除
  并替换为授权语料。

## CS101 算法短视频

**3B1B 风格知识点短片**（[`mvp/cs101/cinematic/`](mvp/cs101/cinematic/README.md)）：依据《计算概论（B）》2026fall 讲义与旁白稿，
共 14 支、约 41 分钟，1080p60，Edge TTS 中文配音、画面内字幕。每支片的数字都由测试对照讲义原版代码核验，
每次渲染自动做画面检查（文字出画、重叠、遮挡、压字幕），配音经 Whisper 转写回文字与旁白稿比对。

- 系列入口页（按周次、可在线播放 720p 版）：**https://infomall.zhengmao.ltd/cs101-anim/**
- 片目：第 6 周排序；第 7 周栈；第 8 周斐波那契、汉诺塔、全排列；第 9 周八皇后、并查集；第 10 周区间贪心、DP 入门；
  第 11 周 0/1 背包、LCS 与编辑距离；第 12 周 BFS、Dijkstra、二分答案。逐支依据见该目录 README。
- 1080p60 成片不进 git，在 GitHub Releases：https://github.com/GMyhf/imanim/releases/tag/cs101-anim-2026fall
- 生成：`python mvp/cs101/cinematic/make.py --lesson <id>`（需要 manim 0.22.0、edge-tts、ffmpeg、LaTeX）。

**早期样片**（[`mvp/cs101/README.md`](mvp/cs101/README.md)）：栈与队列（2020fall OpenJudge 04099）、搜索、动态规划三条，
用 macOS 系统语音配音，`mvp/cs101/sample.py --lesson stack_queue|search|dp` 生成。

以上都是独立脚本，尚未接入在线生成。
