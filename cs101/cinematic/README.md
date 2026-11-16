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
| 斐波那契：一棵树怎样塌缩成一行 | 2026fall 第 8 周 递归 P23–P25（OpenJudge 02753），衔接第 10–12 周动态规划 | `cs101/out/cs101_cine_fib/` |
| 汉诺塔：相信更小的自己 | 2026fall 第 8 周 递归 P26–P28 与讲义 3.2 节（OpenJudge 04147） | `cs101/out/cs101_cine_hanoi/` |
| 全排列：在决策树上走一遍 | 2026fall 第 8 周 递归 P29–P35 与讲义 3.3–3.4 节（OpenJudge 02748、LeetCode 78） | `cs101/out/cs101_cine_perm/` |
| 并查集：让森林越查越矮 | 2026fall 第 9 周 并查集 P16–P30 与讲义第 2 节（OpenJudge 02524，期中手算题） | `cs101/out/cs101_cine_dsu/` |
| BFS：一圈一圈往外推 | 2026fall 第 12 周 BFS P9–P21 与讲义 2.1–2.5 节（LeetCode 542） | `cs101/out/cs101_cine_bfs/` |
| 排序：从 n 平方到 n log n | 2026fall 第 6 周 排序 P26–P34 | `cs101/out/cs101_cine_sort/` |
| 区间贪心：先按右端点排序 | 2026fall 第 10 周 区间问题 P4–P12（LeetCode 56、435、452） | `cs101/out/cs101_cine_interval/` |
| 0/1 背包：一张表，两个方向 | 2026fall 第 11 周 背包 P4–P8 | `cs101/out/cs101_cine_knap/` |
| Dijkstra：带权的波纹 | 2026fall 第 12 周 最短路 P17–P20（走山路） | `cs101/out/cs101_cine_dijkstra/` |
| 二分答案：最小化最大值 | 2026fall 第 12 周 二分答案 P22–P26（河中跳房子、月度开销） | `cs101/out/cs101_cine_bsearch/` |
| 栈：后进先出的三种用法 | 2026fall 第 7 周 栈 P4–P18（括号匹配、后缀求值、单调栈接雨水） | `cs101/out/cs101_cine_stack/` |
| 八皇后：回溯与剪枝 | 2026fall 第 9 周 回溯 P5–P6、P11–P13 | `cs101/out/cs101_cine_queens/` |
| 动态规划入门：状态少了一维 | 2026fall 第 10 周 DP 入门 P13–P24 | `cs101/out/cs101_cine_dpintro/` |
| LCS 与编辑距离：同一张二维表 | 2026fall 第 11 周 序列 DP P20–P21 | `cs101/out/cs101_cine_lcs/` |
| 二进制与补码：减法变成加法 | 2026fall 第 3 周 计算机原理 4.1–4.3 节 P26–P37（OpenJudge 02734） | `cs101/out/cs101_cine_binary/` |
| 浮点数：0.1 + 0.2 为什么不等于 0.3 | 2026fall 第 3 周 计算机原理 4.4 节 · 第 4 周 浮点开方偏 1 | `cs101/out/cs101_cine_float/` |
| 矩阵：补一圈零，转一个弯 | 2026fall 第 6 周 矩阵 1.1–1.3 节 P12–P17（OpenJudge 12560、18106） | `cs101/out/cs101_cine_matrix/` |
| 熄灯问题：只枚举第一行（例题精讲） | OpenJudge 02811（每日选作 11-02、往年机考）；同类题 02813 画家问题 | `cs101/out/cs101_cine_lights/` |
| 回溯三形态：子集、组合、排列共用一个模板 | 2026fall 第 9 周 回溯 1.1–1.3 节 · 第 8 周 3.4 节（LeetCode 78、39；组合 LeetCode 77 的代码为按讲义补写） | `cs101/out/cs101_cine_subsets/` |
| 马走日与数湖泊：回溯要不要撤销 | 2026fall 第 9 周 1.5–1.6 节（OpenJudge 04123、02386、05585） | `cs101/out/cs101_cine_knight/` |
| 从递归到 DP：爬楼梯与数字三角形 | 2026fall 第 10 周 2.3–2.6 节（LeetCode 70、OpenJudge 02760；爬楼梯递归与记忆化版、三角形记忆化版为按讲义补写） | `cs101/out/cs101_cine_triangle/` |
| 最大子段和：从一维到二维 | 2026fall 第 10 周 2.7 节 · 第 11 周 2.3–2.4 节（M02766、LeetCode 198） | `cs101/out/cs101_cine_kadane/` |
| 背包的三个变形：拆捆、装满、多一维 | 2026fall 第 11 周 1.4–1.6 节（M01742、21458、04102、04110；Coins 代码与 0/1 不能贪心的反例为自拟） | `cs101/out/cs101_cine_knapvar/` |
| 最长上升子序列：两种写法 | 2026fall 第 11 周 2.1 节（OpenJudge 02533、M02945、03532） | `cs101/out/cs101_cine_lis/` |
| 网格上走：DP 还是搜索 | 2026fall 第 12 周 第 6 节（与第 2–3 节 BFS、Dijkstra 衔接） | `cs101/out/cs101_cine_grid/` |

**成片 mp4 不进 git**（`.gitignore` 排除 `cs101/out/cs101_cine_*/*.mp4`），放在 GitHub Releases：
https://github.com/GMyhf/imanim/releases/tag/cs101-anim-2026fall
下载：`gh release download cs101-anim-2026fall -R GMyhf/imanim -D <目录>`。各片目录里仍提交 `sidecar.json`、`timing.json`、
`marks.json`、`audit.json`、`asr.json`、`subs.srt`、`preview.png`；重渲后用 `gh release upload cs101-anim-2026fall <mp4> --clobber` 覆盖。

系列入口页（按周次排列、页面内可播放 720p 版）由 `site/build.py` 生成：`site/films.json` 写周次、简介、出处，
标题和时长读各片 `sidecar.json`；页面版视频用 `ffmpeg -vf "scale=1280:-2,fps=30" -crf 30` 转码，封面取 `preview.png`。
`build.py --standalone` 生成独立部署版（完整 HTML、只用系统字体，国内打不开 Google Fonts；加 `--feedback` 带每支片的反馈栏，
需先在中转上部署 `site/feedback_server.py`，见该文件说明），部署在
https://infomall.zhengmao.ltd/cs101-anim/（成都中转 `/srv/cs101-anim`，Caddy `handle_path /cs101-anim/*`，换文件无需 reload；中转出口约 5 Mbps，只放 720p 版）。

每张片卡还有：章节按钮（sidecar 的 `beats` 起点，标签写在 films.json 的 `chapters`，缺省显示 beat id；播放时高亮当前章节）、
讲义链接（films.json 的 `href`，指向课程仓库 GitHub 上的讲义小节）、可折叠的旁白文字稿（读 `<id>.json`）、
「看完测一测」（读 `site/quiz.json`，`{"<id>": [{"q", "options", "answer", "explain"}]}`，没有题就不显示）和复制链接。
页面顶部可按关键词搜索（标题、简介、出处、文字稿）；看到 80% 的片子在本机 localStorage `anim-watched-<课程>` 记为看过，
系列页和总入口都显示已看数；`#<id>` 深链接会滚到该片并闪一下。新增片子时记得在 films.json 补 `chapters` 与 `href`。

## 一键发布 `publish.py`

检查、渲染、转码、Release、部署、验证一条命令走完（两门课通用，`--course cs101|cs201`）：

```bash
python cs101/cinematic/publish.py --course cs201 --check-only            # 只检查
python cs101/cinematic/publish.py --course cs201 kmp --render            # Mac 上重渲 kmp（含配音校对）→ 转码 → Release → 部署 → 公网验证
python cs101/cinematic/publish.py --course cs101 binary --render --stale # 新片：连带片尾「下一支」过时的相邻片一起重渲
python cs101/cinematic/publish.py --course cs201                         # 只更新页面、题库、反馈服务（改了 films.json、quiz、build.py 之后）
python cs101/cinematic/publish.py --course cs201 kmp --dry-run           # 打印要在 Mac、中转上执行的脚本，不真改
```

检查项：films.json 与 LESSONS 对得上；各片 sidecar 是 1080p、≤ 4 分钟、画面检查 0 处、`chapters` 键与 beats 一致；
`quiz.json` 片目与 films.json 一致且是 `quiz_gen.py` 的最新输出；两门课单元测试；片尾卡是否过时（sidecar 的 `endcard_info`
与按当前 films.json 算出的不同）。中转上先把旧页面、题库、服务文件备份到 `/var/backups/anim-<时间>-<课程>/`，
只有 `feedback_server.py`、`quiz-<课程>.json` 或 systemd 单元变了才重启反馈服务。反馈服务的片目取自 quiz.json，单元里不再写 `--films`。
跑完记得 git 提交 `<课程>/out/` 和源文件。

反馈服务（`site/feedback_server.py`）除评分外还收小测结果 `POST /quiz`（只记片子、题号、对错；`--quiz quiz.json` 时按题数校验题号），
存同目录 `quiz.jsonl`；`GET /report?token=…` 是给老师看的 HTML 汇总页（各片评分、留言、每题正确率），
口令来自环境变量 `FEEDBACK_REPORT_TOKEN` 或 `--token`，没配就 404。命令行 `--report` 同样会打印小测正确率。

## 制作

```bash
# 仓库根目录；ffmpeg 在 PATH 上（或设 MVP_FFMPEG_DIR）
export PATH=$PWD/.venv/bin:$HOME/.TinyTeX/bin/x86_64-linux:$PATH
python cs101/cinematic/make.py --lesson fib --quality draft     # 480p15 预览，约 1 分钟（id 见 make.py 的 LESSONS，共 25 支）
python cs101/cinematic/make.py --lesson fib                     # 1080p60 成片
python cs101/cinematic/make.py --lesson fib --tts-only          # 只合成配音、写 timing.json

(cd cs101/cinematic && python -m unittest test_*.py) # 片中数字的独立对撞
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
- **配音校对**（`asr_check.py`，Mac 上跑，需 mlx-whisper、pypinyin、cn2an）：Whisper 把每段配音转写回文字，两边统一数字写法后
  按拼音比对，只报漏读/断流、读音不符、英文词被听成中文三类，写 `asr.json`。首轮查出并查集片的 union 被念成「永远」一类
  （已改口语「合并」），以及一段整句缺失的断流。Whisper 也会听错，报告是「值得复听的位置」。
- `make.py`：TTS（按稿件哈希缓存）→ `timing.json` → 渲染（场景写 `marks.json` 记录各 beat 实际起点）→
  按实际起点摆放配音 → 混流（TTS 每次限时 60 秒；断流校验两条：音频比最后一句字幕短，或句子时间轴拼起来覆盖不到旁白的 95%——Edge TTS 偶尔断流却不报错，
汉诺塔片头曾只剩 2 秒，并查集「应用」段曾连音频带时间轴一起少了一整句），产出成片、`subs.srt`、`sidecar.json`、`preview.png`。动画超出配音时 beat 顺延，音画不会错位。
- **读音词典**（`make.py` 的 `PRON`）：只改送去合成的文本，字幕仍是旁白稿原句（按「。？！」切句与 Edge 的句级时间戳逐句对应，
  句数不一致直接报错）；缓存键用替换后的文本，改词典会自动重新合成相关段落，`asr_check.py` 也对照替换后的文本。
  依据 2026-11 的 A/B（51 句含孤立 i/j/n 的旁白，各合成几种写法让 Whisper 回听）：句首/分句首的 n 原样常被读成「嗯」，写成 `en`；
  句中的 n 保持原样（写成 en 或 N 反而被听成 m）；i 原样偶尔整个吞掉，写成 `eye`；j 写成 `jay`。字母被正确听出 76/87 → 82/87，
  没有变差的句子。大写字母与「大 O」（读「欧」本就是字母名）不动。试听小样在 Mac `~/git/imanim/.local/pron/ab/`。
- **片尾卡**（`Lesson.finish()` → `_endcard()`）：最后约 3 秒静默卡片「下一支：<标题>」+ 系列网址，下一支按本课程
  `site/films.json` 的周次顺序取（标题以下一支旁白稿为准），最后一支显示「本系列完」，没登记进 films.json 的片只显示网址。
  make.py 经 `CINE_ENDCARD` 传给场景，起点记进 marks 的 `_endcard` 与 sidecar 的 `endcard`；直接用 manim 渲染场景时不加。
  各片场景不要再自制「下一支」画面。

新增一条片：写 `<lesson>.json` 旁白稿 + `<lesson>_scene.py`（继承 `Lesson`），登记进 `make.py` 的 `LESSONS`，
数字放进可测试的数据模块并写对撞测试。
