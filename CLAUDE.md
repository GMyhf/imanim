# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

澄象：把结构化知识点（数理化，学段 G8–U2）做成带配音、字幕、时长可控的 1080p 讲解短视频的确定性管线（ManimCE 0.22.0 + ffmpeg + 网关 TTS）；`mvp/cs101/` 另有一组独立的算法样片。注释、文档、提交说明一律中文。

本仓库是魔搭创空间部署版（docker，`0.0.0.0:7860`，入口 `start.sh`）。`PROJECT.md` / README 里提到的 `mvp/tests/`、`tests/run_tests.py`、`deploy/`、`Projrct_Plan/`、`corpus/`、`.local/` **都不在本仓库**，不要去找，也别照着跑。

## 命令

除 CS101 外，工作目录都要是 `mvp/`（导入写作 `from pipeline import ...`）。

```bash
cd mvp
python run.py --subject physics --grade H1 --topic 加速度 --seconds 120 --quality draft
#   --quality draft(480p15)|hd|fullhd   --style clean|board   --no-narration   --no-subtitles   --burn
PLAN_JSON=out/<run>/plan.json manim -q l --disable_caching render/scene.py Explainer   # 只重渲一份分镜（无声）
python batch.py --out ../.local/batch --jobs 4                    # 整个知识库批量出片
python web/server.py --port 8123                                  # Web：作品墙 / 改分镜重渲 / 反馈

python pipeline/flow_bridge_test.py                               # flow v2 状态机测试
(cd cs101 && python -m unittest test_algorithms)                  # CS101 轨迹 oracle；单例加 .AlgorithmsTest.<方法>
```

CS101（工作目录为仓库根，配音用 macOS `say`，不需要密钥）：`.venv/bin/python mvp/cs101/sample.py --lesson stack_queue|search|dp`；加 `--prepare-only --out .local/x` 只验证轨迹。

本机（Linux）环境：虚拟环境在仓库根 `.venv/`（`uv venv .venv && uv pip install --python .venv/bin/python 'manim==0.22.0'`，pycairo 编译需要 `libcairo2-dev libpango1.0-dev`）。ffmpeg 在 `~/.local/bin`，跑之前设 `PATH=$PWD/../.venv/bin:$PATH MVP_FFMPEG_DIR=$HOME/.local/bin`。`run.py` 即使加 `--no-narration` 也会读 TTS 密钥；没有密钥时设 `QX_TTS_ENGINE=edge`（见下）即可完整出片。

没有 lint 配置。控制台是 GBK 时先设 `PYTHONIOENCODING=utf-8`。

## 环境变量

- `MVP_FFMPEG_DIR`、`MVP_MANIM_BIN`：缺省值是作者 Windows 机器上的 `D:\...` 路径，Linux 下必须设置，或保证命令在 PATH 上。
- 字体 `MVP_TEXT_FONT` / `MVP_LATIN_FONT` / `MVP_SUB_FONT`：本机 SimSun + Times New Roman；容器用 Noto Serif CJK SC + TeX Gyre Termes。
- LLM：`QX_LLM_PROVIDER=modelscope|gateway`，密钥 `QX_LLM_API_KEY`（或 `QX_LLM_KEY_FILE`）。各环节**默认关**：`QX_LLM_<STAGE>=1` 逐个打开（A1/K0/A3/VOICEOVER/A8/S22…），`QX_LLM_ALL=1` 全开。全关时管线走确定性兜底，照常出片，本地调试优先用这种模式。
- TTS：`QX_TTS_API_KEY`（或 `QX_TTS_KEY_FILE`）、`QX_TTS_BASE_URL`。和 LLM 是两套密钥，不能合并。网关的 speed 参数无效（`tts.SPEED_SUPPORTED`）。
- 免密钥配音：`QX_TTS_ENGINE=edge` 改走 Edge 在线语音（需 `pip install edge-tts`，未写进 requirements.txt；音色 `QX_TTS_EDGE_VOICE`，缺省 `zh-CN-XiaoxiaoNeural`）。MP3 经 ffmpeg 转成与网关同格式的 24kHz/16bit/mono WAV。实测约 4.5 字/秒，略低于标定的 4.7。本地无密钥时用它跑完整出片。
- 密钥只经 env 注入，不进代码、镜像、日志。

## 主链路 `run.generate()`

```
Brief → knowledge.load（data/kp 确定性检索；未命中 → kp_draft K0 起草进 data/kp_auto/）
     → storyboard.build 或 storyboard_llm.build(A3) → Plan IR
     → review.check 预算态（阻断项 → storyboard_llm.adjust 回灌一轮）
     → voiceover.apply（朗读稿；失败回退 tts.speakable 正则）
     → _voice_and_align：TTS 实测每镜时长 → 反写镜头秒数（量化到渲染帧网格 QUALITY_FPS）
     → review.check 终检（阻断项回灌 A3 自愈 FINAL_HEAL_ROUNDS 轮）
     → manim render/scene.py Explainer（PLAN_JSON 指向 plan）→ silent.mp4
     → mux 混音/SFX/字幕 → 时长与音画漂移闸门 → out/<run>/ 成片 + sidecar.json
```

## 改代码前要知道的

- **`pipeline/ir.py` 是常量的单一真源**：`Brief`/`Plan`/`Shot`、`VISUAL_KINDS`（24 种视觉原语）、`GRAPHIC_KINDS`、`FIGURE_SHAPES`、`MOTION_CAPABLE`、语速档位。提示词 `llm_prompts.py`、闸门白名单 `review.py` 都从这里取值。新增一种原语或 shape，要同时改 `ir.py` 和 `render/scene.py` 的 `BUILDERS` 分派。不要在别处再写一份枚举。
- **`pipeline/review.py`**：闸门编码见 `CODES`，每条 finding 都带 `blocking`。阻断类不过就拒绝出片；记账类（如 `BUDGET_TIGHT`）只写进 `review.json`。知识点里的 `must_say` 由闸门正向检查。出处折行规则（`REF_SEPS` 等）与 `scene._wrap_ref` 各写了一份，改一处要同步另一处。
- **失败分类**：用 `DurationNotFeasible`（带实测秒数）或 `GenerationError(kind, msg, hint, findings=...)`，前端靠这些字段给出可照做的建议。新增失败路径也要走这两类，不要裸抛 `RuntimeError`。
- **字距标定**：`font_metrics.CALIBRATED` 按字体对存表，`scene.py` 的 `_DELTA_*` 和 `review` 的估宽都依赖它。遇到未标定的字体对会抛 `FontMetricsError`，不会静默沿用旧值。换字体后跑 `python mvp/tools_fontmetrics.py --out mvp/font_metrics_cache.json`（`start.sh` 启动时会自动跑）；换 manim 版本，这些实测常数同样失效。
- **`render/scene.py`**（约 6900 行）只有一个场景 `Explainer`。`motion.py` / `motion_contract.py` 是动效契约；`physics/` 的定步长 RK4 积分驱动过程动画，靠数值演化，不摆关键帧。
- **Web**（`web/server.py`，纯标准库）：每个任务一个线程，加一个跑 `web/jobrunner.py --mode generate|render|improve` 的子进程，进度写进 `progress.json`。作品墙扫 `mvp/out/` 与 `web/jobs/` 下的 `sidecar.json`，有 `.gallery_ok` 标记的才上墙。任务目录名必须是纯 ASCII。
- **`pipeline/flow/`**：AgentFlow v2 多环节流程，在试行，还没进产品链路；`flow_produce.flow_enabled(subject)` 为假时不导入。
- **`mvp/cs101/`**：复用 Plan/Shot、字幕切分、音频拼接，但不走数理化闸门，也没接入 Web。内容在 `lesson.json` / `search.json` / `dp.json` 里改；`trace.json` 由真实的数据结构操作生成，`test_algorithms.py` 用独立 oracle（并查集、穷举路径）对照验证。

## 数据与产物

- `pipeline/data/kp/<subject>/*.json`：16 条人工核对过的知识点（带出处与 `must_say`）。`kp_auto/` 放 K0 草稿，出处只能来自语料的字面命中。
- `pipeline/data/corpus/`：OCR 得到的教材文本，只供 K0 检索，不进渲染层，也不在 MIT 授权范围内。
- `mvp/out/<run>/`：成片与 `brief/plan/review/sidecar.json`、`subs.srt`。`silent.mp4`、`track.wav`、`audio/`、`media/` 等中间文件只在失败时保留。
- 文档和 sidecar 坚持"如实记账"：没验证过的（比如镜像从未 `docker build` 过）要明写。push 或重新部署创空间 `chengxiang_gallery` 需要用户授权。
