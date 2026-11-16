# CS201 知识点短视频 · 3B1B 风格

素材依据《数据结构与算法（B）》课件仓库 `2026fall-cs201` 的讲义（含 `2026spring-cs201/` 下的春季专题）与
`dsa-modernization` 教材。制作流程、视觉约定、自动画面检查、配音校对与 CS101 系列完全相同，见
[`cs101/cinematic/README.md`](../../cs101/cinematic/README.md)；本目录只放各片自己的四个文件。

## 已有片目

| 片目 | 依据 | 时长 |
| --- | --- | --- |
| 渐进分析：只看 n 变大以后 | 第 1 周 ADT 与复杂度 3.1–3.3 节 | 3:20 |
| 链表：三根指针的舞蹈 | 第 2 周 线性表 附录 A（LeetCode 21、206、876、141、142） | 3:27 |
| 中缀转后缀：调度场算法 | 第 3 周 栈与队列 1.4–1.5（OpenJudge 24591、24588） | 3:34 |
| KMP：目标指针不回头 | 第 4 周 字符串 3.1–3.4 节 · 2026spring 第 3 周 KMP · OpenJudge 02406 | 3:57 |
| 二叉树周游：同一圈轮廓，三个时机 | 第 5 周 二叉树 2.2–2.3 节（图 5.5、5.6）· OpenJudge 24750 | 3:34 |
| 二叉搜索树：左小右大，再加一点平衡 | 第 5 周 二叉树 第 4 节（图 5.11–5.13）· 2026spring 树讲义 AVL · OpenJudge 22275 | 3:21 |
| 堆：一棵藏在数组里的树 | 第 5 周 二叉树 5.1–5.3 节（图 5.14–5.17）· OpenJudge 04078 | 3:36 |
| Huffman 编码：让常用的字符更短 | 第 5 周 二叉树 6.1–6.2 节（图 5.18–5.20）· OpenJudge 04080 | 3:25 |
| 树与森林：左孩子，右兄弟 | 第 6 周 树 1.2、1.4、3.3 节（图 6.3–6.5、6.16）· OpenJudge 24729 | 3:02 |
| 拓扑排序：先修课怎么排 | 第 7 周 图 4.3–4.5 节（图 7.17 课程先修关系）· sunnywhy 403 | 3:56 |
| 强连通分量：两遍深度优先搜索 | 第 7 周 图 4.1、4.6 节（Kosaraju）· 2026spring 图讲义 DFS · OpenJudge 02186 | 3:51 |
| 关键路径：一天也拖不得的活动 | 第 7 周 图 4.7 节（AOE 网）· sunnywhy 404、406 | 3:19 |
| Floyd：一次算出所有点对 | 第 1 周 2.1–2.2 节「股市的传言」· 第 7 周 图 5.2 节（图 7.20、7.21） | 3:21 |
| Bellman-Ford：负权边与负环 | 第 7 周 图 5.3 节 · OpenJudge 01860 | 3:13 |
| 最小生成树：一棵树和一片森林 | 第 7 周 图 第 6 节（图 7.23–7.25、6.3 节）· OpenJudge 01258 | 3:55 |
| 快速排序：力气花在分上 | 第 8 周 排序 5.1–5.2、5.4、5.6 节 | 3:18 |
| 分配排序：不比较，直接算位置 | 第 8 周 排序 7.1、7.3 节 · 10.3 节 比较排序的下界 | 3:16 |
| 散列表：把关键字算成地址 | 2026spring 散列表 1.2–1.5 节 · 练习 17968、17975 · dsa-modernization 10.3 | 3:55 |
| 字典树：一个字母走一步 | 2026spring 第 6–8 周 树讲义 附录 B 前缀树 · LeetCode 2452 | 2:58 |
| 树状数组：最低位的一 | 2026spring 第 2 周 树状数组 第 3 节与附录 A（LeetCode 307、OpenJudge 20018） | 3:55 |
| Manacher：照镜子找回文 | 2026spring LC_top-100-liked M5 · 第 3 周讲义附录 B · LeetCode 5 | 3:17 |

成片 mp4 不进 git，放 GitHub Releases `cs201-anim-2026fall`；`cs201/out/cs201_cine_<id>/` 里提交 sidecar、timing、
marks、audit、asr、字幕与 preview.png。21 支画面检查均 0 处、都在 4 分钟以内；配音校对只在 KMP、渐进分析里标出几处单个英文字母（i、j、n、O）
被 Whisper 转写成「ai、距、嗯、欧」，判断为转写误差，未人工复听。

## 制作

```bash
# 仓库根目录，环境同 CS101（Mac Studio 上：export PATH=$PWD/.venv/bin:/opt/homebrew/bin:/Library/TeX/texbin:$PATH）
python cs201/cinematic/make.py --lesson kmp --quality draft    # 480p15 预览（id 见 make.py 的 LESSONS，共 21 支）
python cs201/cinematic/make.py --lesson kmp                    # 1080p60 成片 → cs201/out/cs201_cine_kmp/
(cd cs201/cinematic && PYTHONPATH=../../cs101/cinematic python -m unittest test_*.py)   # 148 个对撞测试
python cs101/cinematic/asr_check.py --course cs201 kmp         # 配音校对（Mac，mlx-whisper）
```

`make.py` 只是一层壳：登记片目，把 `cs101/cinematic/make.py` 的 `HERE / OUT / LESSONS / PREFIX` 换成本课程的再调用它；
渲染时 `cine.py` 所在目录经 `PYTHONPATH` 传给 manim，所以各片场景照常 `from cine import *`。
`bst_scene.py` 从 `trav_scene.py` 复用 `TreeView`（结点横坐标 = 中序名次，纵坐标 = 深度），两者要一起改。

## 入口页

`site/films.json` 写周次、简介、出处和页面文字（`page` 字段覆盖 CS101 的缺省文案；春季专题用 `tag` / `label` 自定周次标签），
生成器与 CS101 共用：

```bash
cd cs201/cinematic/site
python ../../../cs101/cinematic/site/build.py --site . --standalone --feedback   # → index.standalone.html（部署版；时长读 ../../out/*/sidecar.json）
python ../../../cs101/cinematic/site/home.py                                     # 更新总入口 home.html 的片数与总时长
```

部署位置：成都中转 `/srv/cs201-anim`（720p 视频与封面转码参数同 CS101），对外 https://infomall.zhengmao.ltd/cs201-anim/；
反馈接口用同一个 `cs101/cinematic/site/feedback_server.py` 另起一个实例（`--films` 换成本系列 21 个 id，新增片子要同步改 systemd 单元并重启）。
