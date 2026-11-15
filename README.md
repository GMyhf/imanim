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

> ⚠️ **在线生成默认开放，但有两道先决条件没满足前不保证能出片。**
> 移植阻断项 ①②③④ 都已从代码层面解除（配音走网关 HTTP、字体开源替代、字距运行时标定、
> 字幕字体 env 化，见下表），但镜像尚未经 `docker build` 验证、生成还依赖创空间环境变量注入的
> 两套密钥：推理后端 `QX_LLM_API_KEY`（缺省 ModelScope）与配音网关 `QX_TTS_API_KEY`。
> 密钥没配、或字体探针没跑出标定缓存时，生成会如实报错而不是假装在跑；画廊浏览不受影响。
> 要现场跑一条，请在 Windows 上按 `PROJECT.md` 的命令执行。

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

- 语料：16 条知识点（数学 5 / 物理 6 / 化学 5），学段 G8–U2（学段由可核教材来源定）。
- 测试：905 项全绿（`mvp/tests/`，含每条闸门的"必然命中"反向用例，也含字体标定这类
  不渲染像素、直接读 SVG 轮廓的复检用例）。
- 验收：**正在按四维量表做第五轮独立复评**（batch_v8），两名互不知情的评审人各自读图打分后交叉裁定
  （科学性/易懂/美学/完成度，通过线 S ≥ 4.5、U/A/C ≥ 3.5、总分 ≥ 4.0，
  且 G1–G5 一票否决项无一命中）。
  前四轮均未过线（数学批在第三轮达到过线判据、物理批未过；第四轮 8 条里 6 条过线、
  因出处角标 12~23 px 命中 G3 一票否决而整体未过，见 `Eval_batch_v7_*.md` 与 `Audit_batch_v7_cross.md`）。
  每轮的评审原文与交叉裁定都随仓库留档——**本项目不声称已通过验收**。

## 在容器里复现渲染（移植阻断项台账，2026-10-18 按源码逐条重核）

| # | 阻断项 | 现状（已核对源码） | 结论 / 需要的改动 |
| --- | --- | --- | --- |
| ① | 配音 | **已解除（#60-A）**。`audio/tts.py` 不再走 Windows SAPI/powershell，改为第三方网关 HTTP：`POST {QX_TTS_BASE_URL}/v1/audio/speech`（缺省 `https://api.openai-next.com`），模型 `qwen3-tts-flash`，voice `cherry`。ModelScope 推理网关**没有** TTS 路由（实测 404），所以配音端点/密钥与活动 LLM 后端解耦：`QX_TTS_API_KEY` / `QX_TTS_KEY_FILE`。间歇性 403/408/429/5xx 已内置重试：共 5 次尝试、间隔 3s 起翻倍（3/6/12/24s）。网关 WAV 头 size 字段溢出、speed 参数无效两个坑均已在代码内处理/如实记账 | Linux 容器可用，但有三个前提：**(a)** 密钥经 env 注入——`QX_TTS_API_KEY` 直接给值，或 `QX_TTS_KEY_FILE` 指向容器内可读的密钥文件（代码缺省的 `D:\Desktop\key.txt` 在 Linux 不存在，必须二选一，**密钥只走创空间的环境变量配置，不进镜像、不进仓库**）；**(b)** 容器出网可达 `api.openai-next.com`（可用 `QX_TTS_BASE_URL` 换网关）；**(c)** 接受 403/429 抖动——重试已内置，但网关持续不可用时配音会失败 |
| ② | 中文字体 | `scene.py` 默认已不是 YaHei：`T()` 中文走 `SimSun`（宋体）、拉丁/数字走 `Times New Roman`，分别可用 env `MVP_TEXT_FONT` / `MVP_LATIN_FONT` 覆盖 | **两款都是商业字体，不能打进 Linux 镜像**。替代映射：SimSun → `Noto Serif CJK SC`（衬线、全量 CJK，`fonts-noto-cjk` 提供）；Times New Roman → `TeX Gyre Termes`（Times 度量兼容，`fonts-texgyre`）或 `Liberation Serif`（`fonts-liberation`）。Dockerfile 已按此装包并设 env |
| ③ | 字号/字距标定 | 标定值与字体**强绑定**：`scene.py` 的 `_DELTA_DESC/_DELTA_CJK/_DELTA_PAREN`（分段基线拼接）与 `review.py` 的 `UNIT_CJK/UNIT_ASCII`（LEGIBLE 闸门估宽）都是量着 SimSun+Times 实测的，唯一事实源在 `mvp/font_metrics.py` 的 `CALIBRATED` 表（键=字体对），未标定字体对会抛 `FontMetricsError` 硬拒、绝不静默沿用旧值 | **已运行时化（#9）**。容器换字体后不用人进容器手填：`start.sh` 起服务前自动跑 `python mvp/tools_fontmetrics.py --out mvp/font_metrics_cache.json`，`font_metrics.metrics_for()` 未标定时读这份缓存把实测值注册进表；探针跑不出就如实保持"只当画廊"（生成报 `FontMetricsError`），画廊不受影响 |
| ④ | 字幕烧录 | `pipeline/mux.py` 的 ASS Style 里 `FontName` **写死 `Microsoft YaHei`**，Linux 容器没有这款字 | **已解除**。`SUB_FONT` 改读 env `MVP_SUB_FONT`（缺省仍是 YaHei，Windows 行为不变）；Dockerfile 已设 `MVP_SUB_FONT="Noto Serif CJK SC"` 与画面字体同源。默认不出烧录版（画面内已排字幕），要外挂/烧录版才走这条 |
| ⑤ | 公式 TeX | `scene.py` 已接入 LaTeX：`formula.props.tex` 走 MathTex（latex → dvisvgm），探测不到 TeX 时自动退回 Pango 排版（`rich()`），不会渲染失败 | 新增项（原台账写"本项目不需要 LaTeX"已过期）。要容器内出公式版，镜像需装 texlive（包清单见 Dockerfile：`texlive-latex-base` + `texlive-latex-extra` + `texlive-fonts-recommended` + `dvisvgm`，覆盖 TexTemplate 用的 amsmath/amssymb/mathptmx 与 standalone）。Linux 走 texlive 全量预装，**不存在 MiKTeX 那种渲染时才联网下宏包的问题**；不装 TeX 也能出片，只是公式退回 Unicode 排版 |

另外两条待实测确认（本机没有 docker，`docker: command not found`，**这个镜像尚未经过构建验证**——
texlive/字体包清单同样只是按 Debian bookworm 包名写对，未经 `docker build` 证实）：

- `pycairo` / `manimpango` 在 Linux 上通常没有预编译轮子，需要 `libcairo2-dev`、
  `libpango1.0-dev`、`pkg-config`、`gcc` 现场编译；Dockerfile 已按此写，第一次构建要盯这一步。
- 免费档只有 2vCPU/8G、无 GPU，一条 60–120s 的片子在容器里的墙钟时间未实测；
  磁盘配额（系统盘 / `/mnt/workspace`）也没有官方数字，直接决定能预置多少条成片
  （当前画廊 2 条约 18.5MB，最大单文件 11.5MB，无 >100MB 文件、不触 LFS）。

## push 检查单（一步到位版；远端为 sprwli/chengxiang_gallery，push/重新部署需用户授权）

按 SubTask #45③ 底稿，补上本轮新增的两个前置步骤（**加粗**项）：

1. **[前置] 字体替代 + 字距自动标定**：确认镜像内 `MVP_TEXT_FONT="Noto Serif CJK SC"`、
   `MVP_LATIN_FONT="TeX Gyre Termes"`、`MVP_SUB_FONT="Noto Serif CJK SC"` 生效（`fc-match` 核对）。
   字距标定已运行时化：`start.sh` 起服务前自动跑 `tools_fontmetrics.py --out mvp/font_metrics_cache.json`，
   `font_metrics.metrics_for()` 未标定时读它注册（阻断项 ③）；探针跑不出就如实保持"只当画廊"。
   首次构建后应核对容器启动日志里探针是否成功落盘（这是生成入口能开的先决条件）。
2. **[前置] 两套密钥注入**：推理后端配 `QX_LLM_API_KEY`（或 `QX_LLM_KEY_FILE`），产物配音配
   `QX_TTS_API_KEY`（或 `QX_TTS_KEY_FILE`）——**密钥只经 env 注入，绝不写进镜像/仓库/日志**；
   ModelScope 无 TTS 路由，两套不能合并成一个。配好后在容器内跑一次最短文本的 TTS 合成验证
   出网与密钥（阻断项 ① 的三个前提逐项打勾）。
   朗读稿改写走推理后端（与 TTS 不同端点）：`start.sh` 已默认 `QX_LLM_VOICEOVER=1`（可 env 覆盖为 0 关闭），
   未配密钥/改写失败时自动回退 tts 正则兜底，画廊与出片不受影响。
   反馈持久化（创空间无持久盘，容器重建会丢本地文件）：另配 `QX_FEEDBACK_REPO`（私有 ModelScope
   数据集 id）与 `QX_FEEDBACK_REPO_TOKEN`（该数据集写 token），两者同时设置才启用写穿——
   提交时异步传到数据集 `feedback/`，启动时回拉缺失条目；可选 `QX_FEEDBACK_TOKEN` 让
   `GET /api/feedback?token=` 额外显示联系方式。token 同样只经 env 注入。
3. 账号完成阿里云绑定 + 实名认证。
4. 建 docker 类型空间，visibility 先 private；服务端设 sdk_type=docker、
   硬件 platform/2v-cpu-8g-mem。
5. 推 `.local/space/`（`deploy/build_space.py` 组装，产物已 gitignore；>100MB 单文件必须走
   LFS——当前最大 10.0MB，不触发）。
6. 盯首次构建：pycairo/manimpango 现场编译 + texlive 安装（本机无 docker，镜像未经构建验证）。
7. 构建通过、画廊页面核对无误后，再谈公开与生成入口（生成入口的阻断项 ①~④ 已全部从代码层面解除，
   只差：密钥 env 注入 + 字体探针在容器内跑出标定缓存，两者都满足即可开）。

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
- 项目根 `corpus/`（232MB 参考原件）仍不进仓库，只留 `corpus/MANIFEST.txt` 清单。

*空间内容每次整改后重新生成；成片与中间产物一一对应，欢迎逐帧核对。*

## CS101 算法短视频样片

新增“栈与队列”本地样片，依据 `2020fall-cs101` 的 OpenJudge 04099。
支持并排状态动画、中文配音、代码展示和练习题；生成方式与产物说明见
[`mvp/cs101/README.md`](mvp/cs101/README.md)。此入口为独立样片脚本，尚未接入在线生成。

搜索与动态规划两条短视频也已加入；通过 `--lesson search` 和 `--lesson dp` 生成，详见上述说明。

3B1B 风格的知识点短视频见 [`mvp/cs101/cinematic/`](mvp/cs101/cinematic/README.md)：首支《斐波那契：一棵树怎样塌缩成一行》
（2026fall 第 8 周递归 P23–P25），1080p60、Edge TTS 配音，成片在 `mvp/out/cs101_cine_fib/`；
第二支《汉诺塔：相信更小的自己》（P26–P28）在 `mvp/out/cs101_cine_hanoi/`；
第三支《全排列：在决策树上走一遍》（P29–P35）在 `mvp/out/cs101_cine_perm/`；
第 9 周《并查集：让森林越查越矮》在 `mvp/out/cs101_cine_dsu/`，第 12 周《BFS：一圈一圈往外推》在 `mvp/out/cs101_cine_bfs/`。
