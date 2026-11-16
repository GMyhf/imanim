# imanim · CS101 / CS201 算法动画短片

用 [Manim](https://www.manim.community/)（ManimCE 0.22.0）制作的 3B1B 风格算法讲解短片，1080p60，中文配音、画面内字幕。两门课的总入口：**https://infomall.zhengmao.ltd/anim/**（页面源文件 `cs101/cinematic/site/home.html`）。

- **CS101**《计算概论（B）》2026fall：14 支、约 41 分钟。
  在线观看 **https://infomall.zhengmao.ltd/cs101-anim/** ·
  1080p 成片 [Releases `cs101-anim-2026fall`](https://github.com/GMyhf/imanim/releases/tag/cs101-anim-2026fall) ·
  说明 [`cs101/cinematic/README.md`](cs101/cinematic/README.md)
- **CS201**《数据结构与算法（B）》2026fall：21 支、约 74 分钟。
  在线观看 **https://infomall.zhengmao.ltd/cs201-anim/** ·
  1080p 成片 [Releases `cs201-anim-2026fall`](https://github.com/GMyhf/imanim/releases/tag/cs201-anim-2026fall) ·
  说明 [`cs201/cinematic/README.md`](cs201/cinematic/README.md)

## CS101 片目

| 周次 | 片目 |
| --- | --- |
| 第 6 周 | 排序：从 n 平方到 n log n |
| 第 7 周 | 栈：后进先出的三种用法 |
| 第 8 周 | 斐波那契：一棵树怎样塌缩成一行 · 汉诺塔：相信更小的自己 · 全排列：在决策树上走一遍 |
| 第 9 周 | 八皇后：回溯与剪枝 · 并查集：让森林越查越矮 |
| 第 10 周 | 区间贪心：先按右端点排序 · 动态规划入门：状态少了一维 |
| 第 11 周 | 0/1 背包：一张表，两个方向 · LCS 与编辑距离：同一张二维表 |
| 第 12 周 | BFS：一圈一圈往外推 · Dijkstra：带权的波纹 · 二分答案：最小化最大值 |

## CS201 片目

| 周次 | 片目 |
| --- | --- |
| 第 1 周 | 渐进分析：只看 n 变大以后 |
| 第 2 周 | 链表：三根指针的舞蹈 |
| 第 3 周 | 中缀转后缀：调度场算法 |
| 第 4 周 | KMP：目标指针不回头 |
| 第 5 周 | 二叉树周游：同一圈轮廓，三个时机 · 二叉搜索树：左小右大，再加一点平衡 · 堆：一棵藏在数组里的树 · Huffman 编码：让常用的字符更短 |
| 第 6 周 | 树与森林：左孩子，右兄弟 |
| 第 7 周 | 拓扑排序：先修课怎么排 · 强连通分量：两遍深度优先搜索 · 关键路径：一天也拖不得的活动 · Floyd：一次算出所有点对 · Bellman-Ford：负权边与负环 · 最小生成树：一棵树和一片森林 |
| 第 8 周 | 快速排序：力气花在分上 · 分配排序：不比较，直接算位置 |
| 春季专题 | 散列表：把关键字算成地址 · 字典树：一个字母走一步 · 树状数组：最低位的一 · Manacher：照镜子找回文 |

## 怎么保证内容对

- **数字由真实算法产生**：每支片有一个数据模块（如 `fibdata.py`），把讲义原版代码插桩运行，画面和旁白里的每个数字都从这里取；
  对应的 `test_*.py` 再用独立实现对撞讲义输出、算法结果和旁白稿里写死的数字。
- **自动画面检查**：每次渲染按几何关系查文字出画、互相重叠、被遮挡、压字幕，结果写进 `audit.json`，目标 0 处。
- **配音校对**：Whisper 把配音转写回文字，与旁白稿逐句比对，找漏读、断流和读错的位置。

## 快速开始

```bash
# 仓库根目录；需要 manim==0.22.0、edge-tts、ffmpeg，公式需要 latex + dvisvgm
uv venv .venv && uv pip install --python .venv/bin/python 'manim==0.22.0' edge-tts
export PATH=$PWD/.venv/bin:$PATH

python cs101/cinematic/make.py --lesson fib --quality draft   # 480p15 预览
python cs101/cinematic/make.py --lesson fib                   # 1080p60 成片
(cd cs101/cinematic && python -m unittest test_*.py)          # 数字对撞测试
python cs201/cinematic/make.py --lesson kmp                   # CS201 同一套流程
(cd cs201/cinematic && PYTHONPATH=../../cs101/cinematic python -m unittest test_*.py)
```

Linux 编译 pycairo 需要先装 `libcairo2-dev libpango1.0-dev`；macOS 用 `brew install cairo pango pkgconf`。
片子 id 见 `make.py` 的 `LESSONS`。

配音用 [edge-tts](https://github.com/rany2/edge-tts)：一个很小的 pip 包，调用微软 Edge 的在线朗读服务，**免费、不需要密钥**，
只要能联网。

## 目录结构

```
cs101/cinematic/   3B1B 风格系列（本仓库主体）
cs101/out/         各片的 sidecar、字幕、画面检查与配音校对结果（mp4 在 Releases）
cs201/cinematic/   CS201 系列：只放各片四个文件，复用 cs101/cinematic 的 make.py、cine.py、入口页生成器
cs201/out/         同上，CS201 各片产物
cs101/sample.py    早期 CS101 样片（栈与队列、搜索、动态规划），macOS 系统语音配音，已被上面的系列取代
chengxiang/        本项目的前身「澄象」：数理化知识点讲解视频的自动管线
```

`chengxiang/` 里是一条把数理化知识点自动生成讲解视频的管线（分镜 IR → 监督闸门 → Manim 渲染 → TTS → 混流），
附带作品墙 Web 服务；`Dockerfile` / `start.sh` 是它的魔搭创空间部署版，用法见 `chengxiang/PROJECT.md`。
CS101 系列不依赖它（早期样片 `sample.py` 复用了它的分镜结构与混流代码）。
它的配音缺省走第三方网关的 qwen3-tts-flash（云端 API，需密钥），设 `QX_TTS_ENGINE=edge` 可改用 edge-tts。

## 许可

- 代码与结构化数据：MIT，见 `LICENSE`。
- `chengxiang/mvp/pipeline/data/corpus/` 是团队自行 OCR 的教材文本，只供数理化管线检索出处，**不在 MIT 范围内、不授权再分发**，版权归原出版社所有。
