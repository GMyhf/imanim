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

## 制作

```bash
# 仓库根目录；ffmpeg 在 PATH 上（或设 MVP_FFMPEG_DIR）
export PATH=$PWD/.venv/bin:$HOME/.TinyTeX/bin/x86_64-linux:$PATH
python mvp/cs101/cinematic/make.py --lesson fib --quality draft     # 480p15 预览，约 1 分钟
python mvp/cs101/cinematic/make.py --lesson fib                     # 1080p60 成片
python mvp/cs101/cinematic/make.py --lesson fib --tts-only          # 只合成配音、写 timing.json

(cd mvp/cs101/cinematic && python -m unittest test_fib)             # 片中数字的独立对撞
```

依赖：`manim==0.22.0`、`edge-tts`、ffmpeg；公式要 `latex` + `dvisvgm`（TinyTeX 需
`tlmgr install preview dvisvgm`）。中文字体缺省 `Noto Sans CJK SC`，可用 `CINE_FONT` / `CINE_MONO` 覆盖。

## 结构

- `fib.json`：旁白稿，按 beat 切分，配音音色与语速也写在这里。旁白要写成口语（数字、符号写成汉字读法）。
- `fibdata.py`：调用树、记忆化剪枝、计数；画面和旁白里的每个数字都从这里来。
- `test_fib.py`：用带计数器的真实递归和 `functools.lru_cache` 对撞 `fibdata`，并检查旁白稿里写死的数字。
- `fib_scene.py`：场景。`Lesson` 基类负责 beat 计时（`beat()` / `left()`）与画面字幕；字幕在 beat 开始时一次建好、
  只靠透明度切换——Cairo 渲染器在每次 `play` 开始时就固定了绘制列表，动画中途增删的对象会漏画或叠字。
- `make.py`：TTS（按稿件哈希缓存）→ `timing.json` → 渲染（场景写 `marks.json` 记录各 beat 实际起点）→
  按实际起点摆放配音 → 混流，产出成片、`subs.srt`、`sidecar.json`、`preview.png`。动画超出配音时 beat 顺延，音画不会错位。

新增一条片：写 `<lesson>.json` 旁白稿 + `<lesson>_scene.py`（继承 `Lesson`），登记进 `make.py` 的 `LESSONS`，
数字放进可测试的数据模块并写对撞测试。
