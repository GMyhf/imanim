# CS101 知识点短视频 · 3B1B 风格

素材依据《计算概论（B）》课件仓库 `2026fall-cs101`（讲义 `.md`、旁白稿 `content/wNN_narration.md`、课件 `.pptx`）
与 `2025fall-cs101` 讲义。和上一级目录的 `sample.py` 样片相比，这里换了一套视觉语言：

- 深色画布、LaTeX 公式、按参数着色（同一个子问题始终同一种颜色）；
- 对象在镜头间**形变延续**而不是翻页：调用树 → 剪枝 → 合并成依赖链 → 摊平成数组；
- 动画步骤由真实算法驱动：调用树按真实 DFS 先序生长，记忆化按 `lru_cache` 语义剪枝；
- Edge TTS 配音（免密钥），句级时间戳直接排进画面字幕，配音时长反推每个 beat 的时长。

## 已有片目

| 片目 | 依据 | 产物 |
| --- | --- | --- |
| 斐波那契：一棵树怎样塌缩成一行 | 2026fall 第 8 周 递归 P23–P25（OpenJudge 02753），衔接第 10–12 周动态规划 | `mvp/out/cs101_cine_fib/` |
| 汉诺塔：相信更小的自己 | 2026fall 第 8 周 递归 P26–P28 与讲义 3.2 节（OpenJudge 04147） | `mvp/out/cs101_cine_hanoi/` |
| 全排列：在决策树上走一遍 | 2026fall 第 8 周 递归 P29–P35 与讲义 3.3–3.4 节（OpenJudge 02748、LeetCode 78） | `mvp/out/cs101_cine_perm/` |
| 并查集：让森林越查越矮 | 2026fall 第 9 周 并查集 P16–P30 与讲义第 2 节（OpenJudge 02524，期中手算题） | `mvp/out/cs101_cine_dsu/` |
| BFS：一圈一圈往外推 | 2026fall 第 12 周 BFS P9–P21 与讲义 2.1–2.5 节（LeetCode 542） | `mvp/out/cs101_cine_bfs/` |
| 排序：从 n 平方到 n log n | 2026fall 第 6 周 排序 P26–P34 | `mvp/out/cs101_cine_sort/` |
| 区间贪心：先按右端点排序 | 2026fall 第 10 周 区间问题 P4–P12（LeetCode 56、435、452） | `mvp/out/cs101_cine_interval/` |
| 0/1 背包：一张表，两个方向 | 2026fall 第 11 周 背包 P4–P8 | `mvp/out/cs101_cine_knap/` |
| Dijkstra：带权的波纹 | 2026fall 第 12 周 最短路 P17–P20（走山路） | `mvp/out/cs101_cine_dijkstra/` |
| 二分答案：最小化最大值 | 2026fall 第 12 周 二分答案 P22–P26（河中跳房子、月度开销） | `mvp/out/cs101_cine_bsearch/` |

系列入口页（按周次排列、页面内可播放 720p 版）由 `site/build.py` 生成：`site/films.json` 写周次、简介、出处，
标题和时长读各片 `sidecar.json`；页面版视频用 `ffmpeg -vf "scale=1280:-2,fps=30" -crf 30` 转码，封面取 `preview.png`。
`build.py --standalone` 生成独立部署版（完整 HTML、只用系统字体，国内打不开 Google Fonts），部署在
https://infomall.zhengmao.ltd/cs101-anim/（成都中转 `/srv/cs101-anim`，Caddy `handle_path /cs101-anim/*`，换文件无需 reload；中转出口约 5 Mbps，只放 720p 版）。

## 制作

```bash
# 仓库根目录；ffmpeg 在 PATH 上（或设 MVP_FFMPEG_DIR）
export PATH=$PWD/.venv/bin:$HOME/.TinyTeX/bin/x86_64-linux:$PATH
python mvp/cs101/cinematic/make.py --lesson fib --quality draft     # 480p15 预览，约 1 分钟（--lesson fib|hanoi|perm|dsu|bfs|sort|interval|knap|dijkstra|bsearch）
python mvp/cs101/cinematic/make.py --lesson fib                     # 1080p60 成片
python mvp/cs101/cinematic/make.py --lesson fib --tts-only          # 只合成配音、写 timing.json

(cd mvp/cs101/cinematic && python -m unittest test_*.py) # 片中数字的独立对撞
```

依赖：`manim==0.22.0`、`edge-tts`、ffmpeg；公式要 `latex` + `dvisvgm`（TinyTeX 需
`tlmgr install preview dvisvgm`）。中文字体缺省 `Noto Sans CJK SC`，可用 `CINE_FONT` / `CINE_MONO` 覆盖。
macOS（Mac Studio，`~/git/imanim`）：`brew install cairo pango pkgconf` 后 `uv venv .venv && uv pip install --python .venv/bin/python 'manim==0.22.0' edge-tts`，
TeX 用 MacTeX（`/Library/TeX/texbin`）。代码字体统一为 Noto Sans Mono CJK SC：Mac 上把 Linux 的
`NotoSansCJK-Regular.ttc`（OFL）放进 `~/Library/Fonts`，不要再设 `CINE_MONO`。多支片可同时起多个 make.py 并行渲染。
Mac 仓库已设 `git config http.postBuffer 524288000`：一次推多支视频（几十 MB）时，默认缓冲会让 GitHub 回 HTTP 400，
而终端只显示 `Everything up-to-date`，容易误以为推成功了。

## 结构

- `cine.py`：公共骨架。配色、字体，以及 `Lesson` 基类：beat 计时（`beat()` / `left()` / `wait_until()`）、
  画面字幕、`cue_times()`（当前 beat 的句级时间戳，用来把动画对齐到某一句话，如汉诺塔七步各落在对应那句上）。
- `fib.json`：旁白稿，按 beat 切分，配音音色与语速也写在这里。旁白要写成口语（数字、符号写成汉字读法）。
- `fibdata.py`：调用树、记忆化剪枝、计数；画面和旁白里的每个数字都从这里来。
- `test_fib.py`：用带计数器的真实递归和 `functools.lru_cache` 对撞 `fibdata`，并检查旁白稿里写死的数字。
- `fib_scene.py`、`hanoi_scene.py`：各片场景（继承 `cine.Lesson`）。字幕在 beat 开始时一次建好、只靠透明度切换——
  Cairo 渲染器在每次 `play` 开始时就固定了绘制列表，动画中途增删的对象会漏画或叠字。
  另一个坑：`LaggedStart` 作用在子对象上（如 `node[0].animate...`）时，manim 会把这些子对象打包重新加到场景最上层，
  带不透明填充的形状会把同组里的文字永久盖住——节点框用无填充或半透明填充。
- `hanoidata.py` / `test_hanoi.py`：汉诺塔的移动序列、调用树中序编号、步数与年代换算；测试用三根栈逐步模拟验证每一步合法，
  并对撞讲义里的程序输出和旁白数字。
- `permdata.py` / `test_perm.py`：全排列决策树、回溯事件序列、节点计数、子集树；测试把讲义原版代码插桩，逐事件对撞。
- `dsudata.py` / `test_dsu.py`、`bfsdata.py` / `test_bfs.py`：并查集（讲义 DSU 原样、期中题、退化链对比）与 BFS（迷宫事件序列、多源、入队标记反例、DFS/BFS 顺序）；
  测试对撞讲义输出、期中题答案、随机数据连通块、松弛法求的真最短距离。
- `Forest`（dsu_scene）：父指针箭头用 updater 实时重画，改父指针 + `relayout()` 即可动画重排；`.animate.set_value` 在数字位数变少时会报错，改用 `ChangeDecimalToValue`。
- **自动画面检查**（`cine.Lesson._audit`）：每段 `play` 结束后按几何关系查四类问题——文字出画、文字互相重叠、
  文字被后画的不透明形状盖住、内容压字幕带——写进 `audit.json`，make.py 打印并计入 sidecar 的 `audit_issues`，目标 0 处。
  故意的过渡帧（同参节点合并、全屏波纹）用 `self.play(..., audit=False)` 跳过；透明度 < 0.3 的文字视为装饰。
  它查不出「排版挤但没重叠」「箭头太短」这类问题，抽帧目检仍要做。
- `make.py`：TTS（按稿件哈希缓存）→ `timing.json` → 渲染（场景写 `marks.json` 记录各 beat 实际起点）→
  按实际起点摆放配音 → 混流（TTS 每次限时 60 秒；音频比最后一句字幕短视为流中断，丢弃重试——Edge TTS 偶尔断流却不报错，汉诺塔片头曾因此只剩 2 秒），产出成片、`subs.srt`、`sidecar.json`、`preview.png`。动画超出配音时 beat 顺延，音画不会错位。

新增一条片：写 `<lesson>.json` 旁白稿 + `<lesson>_scene.py`（继承 `Lesson`），登记进 `make.py` 的 `LESSONS`，
数字放进可测试的数据模块并写对撞测试。
