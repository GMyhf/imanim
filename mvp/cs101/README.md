# CS101 算法短视频

内容依据本机 `2020fall-cs101/2020fall_cs101.openjudge.cn_problems.md` 中
`04099: 队列和栈`。原题第一组操作为 `push 1, push 3, pop, push 5`，
最终队列为 `[3, 5]`，栈为 `[1, 5]`。旁白、分镜与结尾练习为本样片编写。

这一条先使用独立的算法动画渲染器，复用项目的 Plan/Shot、字幕切分、
音频拼接和时间轴工具；尚未接入网页“在线生成 / 分镜重渲”入口，
也不声称经过数理化专用的 review 闸门。

在 macOS、项目根目录执行：

```sh
uv venv .venv --python python3
uv pip install --python .venv/bin/python 'manim==0.22.0'
.venv/bin/python mvp/cs101/sample.py
```

系统需要 Cairo、Pango、FFmpeg，以及可用的 macOS 中文语音 Tingting。
无需在线模型或配音密钥。配音使用 `/usr/bin/say`，实测音频长度后再安排
镜头时间；音频缓存会随旁白、声线或语速变化失效。

默认产物位于 `mvp/out/cs101_stack_queue/`：

- `cs101-stack-queue.mp4`：1920×1080、30fps、AAC 配音，画面内字幕及可选中文字幕轨。
- `plan.json` / `lesson.json`（源文件位于本目录）：可修改的分镜与口播。
- `subs.srt`：外挂字幕，镜内按文本宽度估算时间，不是逐字语音识别对齐。
- `trace.json`：每一步的容器状态及取出结果，由真实 deque/list 操作得到。
- `review.json`：算法轨迹检查范围与结果。
- `sidecar.json`：实际时长、配音配置、大小、音画时长检查结果。

仅验证轨迹、不调用配音和渲染：

```sh
.venv/bin/python mvp/cs101/sample.py --prepare-only --out .local/cs101-check
```

调整内容从 `lesson.json` 开始。`action` 支持入栈/入队、取出、清空和练习设置。
渲染器同时显示两个容器及实际移出的元素；栈横向摆放，右端为栈顶。
例题样例、空容器与练习结果有独立预期值检查。默认要求成片在 90 秒 ±10% 内，
音视频流长度差不超过 0.1 秒。系统语音版本可能改变时长；可以精简口播或调整 `--rate`。


## 搜索与动态规划

沿用栈与队列的视频布局、中文配音、字幕和随堂练习，生成两个独立视频：

| 视频 | 内容来源 | 演示重点 |
| --- | --- | --- |
| `cs101_search/cs101-search-ponds.mp4` | 18108 池塘数目 | BFS 队列、八邻接、入队即标记、连通区域计数 |
| `cs101_dp/cs101-dp-triangle.mp4` | M02760 数字三角形 | 自底向上更新、状态依赖、贪心反例和最优路径 |

路径均相对于 `mvp/out/`。每个输出目录保留 `plan.json`、`trace.json`、
`subs.srt`、`review.json` 和 `sidecar.json`。

```sh
.venv/bin/python mvp/cs101/sample.py --lesson search
.venv/bin/python mvp/cs101/sample.py --lesson dp
```

搜索的 4×5 主演示网格是自编的小例子（7 个水格、3 个池塘）；结尾对角线
练习使用原题第一组样例。原资料使用 DFS 解题，本片用 BFS 演示同一个八邻接
连通区域问题。二维队列坐标均从 0 开始。不同颜色代表不同池塘，金色边框为当前处理格。

动态规划使用原题五行样例，结果为 30，最优路径为 `7 → 3 → 8 → 7 → 5`。
灰色数值为尚未处理的原值，蓝色为已求得的最大后缀路径和，金色为当前状态及其依赖；
回看路径时切回原始数值，避免把后缀和重复相加。画面中的代码为当前步骤的节选。

修改内容：`search.json` / `dp.json`。`steps` 指向 `algorithms.py` 真实计算出来的
搜索或 DP 状态。渲染器为 `algorithm_scene.py`，复用原有配音、Plan/Shot 和字幕流程。
新片目标均为 120 秒，允许 ±10%；原来的栈与队列仍保持 90 秒目标。

独立算法验证：

```sh
.venv/bin/python -m unittest discover -s mvp/cs101 -p 'test_*.py'
```

验证包含全部 512 种 3×3 水陆网格（以并查集作独立对照）、210 个随机三角形
（完整路径枚举作对照）、原题样例、入队唯一性、最优路径总和及展示代码语法。
测试不依赖 Manim 或 macOS 配音服务。
