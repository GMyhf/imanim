"""生成 CS201 各片的看后小测 quiz.json（每片 3 题）。

python quiz_gen.py        # 在 cs201/cinematic/site 下运行 → quiz.json

格式：{"<film_id>": [{"q": 题干, "options": [...], "answer": 正确项下标, "explain": 解析}]}。
每片至少一题是「片中没出现过的小输入，问算法结果或某一步状态」，正确答案调用该片的 <id>data.py
（讲义原版代码插桩）算出，不手写；干扰项由常见错法（换个规则、少一步、错位）算出。
这类题在内存里带 "_check"（题型与输入），test_quiz.py 用独立实现重算核对；写进 JSON 时去掉。
"""
import json
import sys
import zlib
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # cs201/cinematic：各片 <id>data.py

import aoedata  # noqa: E402
import bforddata  # noqa: E402
import bigodata  # noqa: E402
import bitdata  # noqa: E402
import bstdata  # noqa: E402
import floyddata  # noqa: E402
import forestdata  # noqa: E402
import hashdata  # noqa: E402
import heapdata  # noqa: E402
import huffmandata  # noqa: E402
import infixdata  # noqa: E402
import kmpdata  # noqa: E402
import linkeddata  # noqa: E402
import manacherdata  # noqa: E402
import mstdata  # noqa: E402
import qsortdata  # noqa: E402
import radixdata  # noqa: E402
import sccdata  # noqa: E402
import slidemaxdata  # noqa: E402
import topodata  # noqa: E402
import travdata  # noqa: E402
import triedata  # noqa: E402


def fmt_list(a):
    return "[" + ", ".join(str(x) for x in a) + "]"


def mk(film, k, q, correct, wrongs, explain, check=None):
    """正确项按 (片 id, 题号) 的散列放到固定位置，免得总是第一个；干扰项去重、剔除与正确项相同的。"""
    opts = []
    for w in wrongs:
        w = str(w)
        if w != str(correct) and w not in opts:
            opts.append(w)
    opts = opts[:3]
    if len(opts) < 3:
        raise ValueError(f"{film} 第 {k} 题干扰项不足：{wrongs}")
    pos = zlib.crc32(f"{film}-{k}".encode()) % (len(opts) + 1)
    opts.insert(pos, str(correct))
    item = {"q": q, "options": opts, "answer": pos, "explain": explain}
    if check is not None:
        item["_check"] = check
    return item


# ---------------------------------------------------------------- 各片
def q_bigo():
    n = 9
    avg = bigodata.avg_uniform(n)                     # 逐个位置真跑顺序查找取平均
    worst = bigodata.seq_search(list(range(n)), n - 1)[1]
    return [
        mk("bigo", 0, f"在 {n} 个互不相同的数里顺序查找，要找的数在每个位置的概率都是 1/{n}。平均要比较几次？",
           str(avg), [str(worst), str(n / 2), str(n // 2)],
           f"第 i 个位置要比 i 次，平均 (1+2+…+{n})/{n} = {avg}，即 (n+1)/2。", ("seq_avg", n)),
        mk("bigo", 1, "f(n) = 3n² + 50n + 1000，用大 O 记法最贴切的是？",
           "O(n²)", ["O(n)", "O(n³)", "O(1000)"],
           "n 足够大以后 3n² 压过其余各项，常数系数也不计，所以是 O(n²)。"),
        mk("bigo", 2, "求一个长度为 n 的数组的全部前缀和：每个前缀都从头重新累加一遍，总的加法次数是什么量级？",
           "Θ(n²)", ["Θ(n)", "Θ(n log n)", "Θ(2ⁿ)"],
           "第 i 个前缀要加 i 次，合计约 n²/2；改成「上一个前缀和再加一个数」才是 Θ(n)。"),
    ]


def q_linked():
    n = 6
    slow = linkeddata.middle_trace(n)[-1][0]
    return [
        mk("linked", 0, f"链表 1→2→…→{n}，slow、fast 都从表头出发，while fast and fast.next 时 slow 走一步、fast 走两步。"
           "循环结束时 slow 停在哪个结点？", str(slow), [str(n // 2), str(n // 2 + 2), str(n)],
           f"结点数为偶数时，这种写法停在两个中点里靠后的那个，即 {slow}。", ("middle", n)),
        mk("linked", 1, "Floyd 判圈：快慢指针相遇后，把其中一个放回表头，两个都改成每次走一步，它们会在哪里再次相遇？",
           "环的入口", ["第一次相遇的位置", "表尾结点", "环上离入口最远的结点"],
           "设环外长 a，相遇点距入口沿环 b，可推出 a ≡ 环长 − b，两人各走 a 步正好同时到入口。"),
        mk("linked", 2, "反转链表时，为什么要在 curr.next = prev 之前先保存 nxt = curr.next？",
           "掉头后 curr.next 指向前面，原来的后继就找不到了",
           ["为了让 prev 指向表头", "为了少走一轮循环", "Python 不允许连续赋值"],
           "改指针前不存后继，后半条链就断开丢失了。"),
    ]


def q_infix():
    expr = "8-(3+2)*4/2"
    post = infixdata.infix_to_postfix(expr)
    p2 = "5 1 2 + 4 * + 3 -"
    val = infixdata.evaluate_postfix(p2)
    val = int(val) if float(val).is_integer() else val
    return [
        mk("infix", 0, f"用调度场算法把中缀式 {expr} 转成后缀式，结果是？", post,
           ["8 3 2 + 4 2 / * -", "8 3 + 2 4 * 2 / -", "8 3 2 4 * + 2 / -"],
           "括号先算 3 2 +；* 和 / 同级、左结合，先乘后除；最后才轮到最外层的减号。", ("postfix", expr)),
        mk("infix", 1, f"后缀式 {p2} 的值是？", str(val), ["12", "18", "20"],
           "从左往右，遇数入栈，遇运算符弹两个算：1+2=3，3×4=12，5+12=17，17−3=14。", ("evalpost", p2)),
        mk("infix", 2, "读到运算符时，要把栈顶优先级「不低于」它的运算符先弹出。去掉「等于」这一半会怎样？",
           "同级运算变成从右往左算，1−2−3 会算成 1−(2−3)",
           ["括号不再起作用", "乘法会排到加法后面", "没有影响，只是栈更深"],
           "同级先到的先弹，保证左结合。"),
    ]


def q_kmp():
    p = "aabaaab"
    lps = kmpdata.compute_lps(p)
    s = "abcabcabcabc"
    k = kmpdata.repetition_count(s)
    wrong1 = [0] + lps[:-1]                      # 错位一格
    wrong2 = [max(0, x - 1) if i == 5 else x for i, x in enumerate(lps)]   # 回退一次就停（少跳一级）
    wrong3 = [sum(1 for j in range(1, i + 1) if p[j] == p[0]) and lps[i] for i in range(len(p))]
    wrong3[-1] = lps[-1] + 1
    return [
        mk("kmp", 0, f"模式串 {p} 的「最长相等真前后缀」表（lps / next）是？", fmt_list(lps),
           [fmt_list(wrong1), fmt_list(wrong2), fmt_list(wrong3)],
           "lps[i] 是 p[0..i] 最长的、既是真前缀又是后缀的长度；失配时 length 退回 lps[length−1] 再比。",
           ("lps", p)),
        mk("kmp", 1, f"s = {s} 是某个串重复 k 次得到的，k 最大是多少？", str(k), ["2", "3", "6"],
           f"最小周期 = n − lps[n−1] = {len(s)} − {kmpdata.compute_lps(s)[-1]} = {len(s) // k}，能整除 n，所以 k = {k}。",
           ("rep", s)),
        mk("kmp", 2, "目标串长 n，KMP 匹配阶段的字符比较次数最多是多少量级？",
           "不超过 2n", ["不超过 n", "约 n·m（m 为模式长）", "约 n log n"],
           "每次比较要么目标指针前进，要么模式整体右移；两者都至多 n 次。"),
    ]


def q_trav():
    ino, post = "DBEAFC", "DEBFCA"
    pre = travdata.preorder_of(ino, post)
    return [
        mk("trav", 0, f"一棵二叉树中序为 {ino}，后序为 {post}，它的前序是？", pre,
           ["ABDCEF", "ABEDCF", "ADBECF"],
           "后序最后一个 A 是根，在中序里把序列分成左 DBE、右 FC，再递归。", ("pre_from_in_post", ino, post)),
        mk("trav", 1, "下面哪一对周游序列，一般不能唯一确定一棵二叉树？",
           "前序 + 后序", ["前序 + 中序", "中序 + 后序", "中序 + 层次序"],
           "没有中序就分不清只有一个孩子时它在左还是在右。"),
        mk("trav", 2, "层次周游（一层一层从左往右）用哪种辅助结构最自然？",
           "队列", ["栈", "优先队列", "散列表"],
           "先访问的结点，它的孩子也要先访问：先进先出。"),
    ]


def q_bst():
    keys = [40, 20, 60, 10, 30, 50, 70, 25]
    found, path, _ = bstdata.build(keys).contains(25)
    return [
        mk("bst", 0, f"依次插入 {fmt_list(keys)} 建一棵二叉搜索树，再查找 25，一共要和几个结点比较？",
           str(len(path)), [str(len(path) - 1), str(len(path) + 1), str(keys.index(25) + 1)],
           f"比较路径 {'→'.join(map(str, path))}，每比一次扔掉一棵子树。", ("bst_search", keys, 25)),
        mk("bst", 1, "对一棵二叉搜索树做中序周游，得到的序列是？",
           "从小到大的有序序列", ["插入的先后次序", "从大到小的有序序列", "按层排列的次序"],
           "左子树都小、右子树都大，「左根右」正好是升序。"),
        mk("bst", 2, "把 1、2、…、7 按这个顺序依次插入空的二叉搜索树，树有几层？",
           str(bstdata.levels(bstdata.build(range(1, 8)).root)), ["3", "4", "1"],
           "每个新数都比已有的大，一路挂在右边，退化成一条链；这正是要做平衡（AVL）的原因。",
           ("bst_levels", list(range(1, 8)))),
    ]


def q_heap():
    keys = [8, 6, 7, 2, 5, 1, 3]
    built, _ = heapdata.build_heap(keys)
    top = list(keys)                                      # 错法：从根往下逐个下沉
    for i in range(len(top) // 2):
        heapdata.sift_down(top, i, len(top), [])
    h = heapdata.MinHeap()
    for x in keys:
        h.insert(x)
    by_insert = list(h.data)
    base, x = [3, 5, 4, 9, 6, 8], 2
    h2 = heapdata.MinHeap()
    h2.data = list(base)
    h2.insert(x)
    wrong_ins = list(base) + [x]                          # 只放到末尾、忘了上浮
    half = list(base) + [x]
    half[6], half[2] = half[2], half[6]                   # 只上浮一层
    return [
        mk("heap", 0, f"对 {fmt_list(keys)} 用筛选法（从最后一个非叶结点倒着逐个下沉）建最小堆，得到的数组是？",
           fmt_list(built), [fmt_list(by_insert), fmt_list(sorted(keys)), fmt_list(top)],
           "从下标 n//2−1 = 2 开始：7 与 1 换；6 与 2 换；8 先和 1 换、再和 3 换。逐个插入建出的堆一般不同。",
           ("buildheap", keys)),
        mk("heap", 1, f"最小堆 {fmt_list(base)} 插入 {x} 之后，数组是？", fmt_list(h2.data),
           [fmt_list(wrong_ins), fmt_list(half), fmt_list(sorted(base + [x]))],
           f"{x} 放在末尾（下标 6），父亲 4 比它大就交换，再和根 3 比，继续上浮到根。", ("heap_insert", base, x)),
        mk("heap", 2, "取走堆顶后，末尾元素搬到根上下沉。为什么必须和「较小的」那个孩子交换？",
           "换上来的要做另一个孩子的父亲，只有较小者才不破坏堆序",
           ["较小的孩子更靠左，下沉更快", "这样交换次数最少，但换哪个都对", "为了保持完全二叉树的形状"],
           "换上较大的孩子，它会比另一个孩子大，堆序当场就坏了。"),
    ]


def q_huffman():
    w = {"a": 5, "b": 9, "c": 12, "d": 13, "e": 16, "f": 45}
    root, _, _ = huffmandata.build(list(w), list(w.values()))
    total = huffmandata.wpl(root)
    dep = huffmandata.depths(root)
    return [
        mk("huffman", 0, f"字符频率 {', '.join(f'{k}:{v}' for k, v in w.items())}，Huffman 编码后的总位数（带权路径长度）是？",
           str(total), [str(3 * sum(w.values())), str(total + 9), str(total - 12)],
           "每次合并最小的两棵：5+9、12+13、14+16、25+30、45+55；WPL 也等于各次合并结果之和。",
           ("wpl", w)),
        mk("huffman", 1, f"同一组频率下，出现最少的 a（频率 5）的码长是几位？", str(dep["a"]),
           [str(dep["a"] - 1), str(dep["a"] + 1), str(dep["a"] + 2)],
           "a 在最早一次合并里就被放进去，之后它所在的树又被合并了三次。", ("huff_depth", w, "a")),
        mk("huffman", 2, "Huffman 编码不需要分隔符也能唯一译码，靠的是什么性质？",
           "任何一个码字都不是另一个码字的前缀", ["所有码字一样长", "常用字符的码字更短", "码字里 0 和 1 的个数相等"],
           "字符都在叶子上，从根走到叶子就确定了一个字符，不会走到半路又是另一个字符。"),
    ]


def q_forest():
    ch = {"A": ["B", "C", "D"], "B": [], "C": ["F"], "D": [], "F": [], "E": ["G", "H"], "G": [], "H": []}
    roots = ["A", "E"]
    post = "".join(forestdata.forest_order("post", ch, roots))
    pre = "".join(forestdata.forest_order("pre", ch, roots))
    shape, _ = forestdata.to_binary(ch, roots)
    return [
        mk("forest", 0, "森林有两棵树：A 的孩子依次是 B、C、D，C 有孩子 F；E 的孩子依次是 G、H。它的后根次序是？",
           post, [pre, "BCFDAGHE", "FBCDAGHE"],
           "每棵树先依次后根访问各子树、最后访问根；两棵树按先后排。", ("forest_post", ch, roots)),
        mk("forest", 1, "同一个森林按「左孩子、右兄弟」转成二叉树后，A 的右孩子是谁？",
           str(shape["A"][1]), ["B", "D", "无（空）"],
           "各棵树的根互为兄弟，所以第二棵树的根挂在 A 的右边。", ("forest_right", ch, roots, "A")),
        mk("forest", 2, "森林转成二叉树后，森林的先根次序、后根次序分别对应二叉树的哪种周游？",
           "前序、中序", ["前序、后序", "中序、后序", "层次、后序"],
           "右链是兄弟：处理完一个结点的全部孩子（左子树）再转向兄弟（右边），正好是中序。"),
    ]


def topo_valid(n, edges, seq):
    pos = {v: i for i, v in enumerate(seq)}
    return sorted(seq) == list(range(n)) and all(pos[u] < pos[v] for u, v in edges)


def q_topo():
    n, edges = 6, [(0, 2), (1, 2), (1, 3), (2, 4), (3, 4), (4, 5)]
    res, _, _ = topodata.kahn_trace(edges, n)
    valid = [p for p in permutations(range(n)) if topo_valid(n, edges, p)]
    invalid = (1, 3, 4, 0, 2, 5)                         # 4 排到 2 前面，违背 2→4
    others = [p for p in valid if list(p) != res][:3]
    s = lambda p: " ".join(map(str, p))  # noqa: E731
    return [
        mk("topo", 0, f"有向图 6 个点，边为 {', '.join(f'{u}→{v}' for u, v in edges)}。下面哪个「不是」合法的拓扑序？",
           s(invalid), [s(p) for p in others],
           "合法拓扑序里每条边都要从左指向右；2→4 这条边在它里面朝左了。", ("topo_invalid", n, edges)),
        mk("topo", 1, "同一张图用卡恩算法（初始入度为 0 的点按编号入队，出队时按编号顺序给后继减入度），输出顺序是？",
           s(res), [s(others[0]), s(sorted(range(n), reverse=True)), "1 0 3 2 4 5"],
           "先入队 0、1；0 出队后 2 还差 1 的那条边；1 出队后 2、3 入度归零依次入队。", ("kahn", n, edges)),
        mk("topo", 2, "卡恩算法结束时，输出的点比总点数少，说明什么？",
           "图里有环", ["图不连通", "有多个入度为 0 的点", "拓扑序不唯一"],
           "环上每个点入度都不会减到 0，永远进不了队列。"),
    ]


def q_scc():
    adj = [[1], [2], [0, 3], [4], [5], [3]]
    k = len(sccdata.kosaraju(adj))
    return [
        mk("scc", 0, "有向图 6 个点，边为 0→1、1→2、2→0、2→3、3→4、4→5、5→3。它有几个强连通分量？",
           str(k), ["1", "3", "6"],
           "{0,1,2} 和 {3,4,5} 各成一个环，2→3 只有单向，所以是两块。", ("scc_count", adj)),
        mk("scc", 1, "把每个强连通分量缩成一个点后，得到的图一定是？",
           "有向无环图", ["一棵树", "强连通图", "无向图"],
           "缩点后若还有环，环上的几块就能互相到达，本该是同一块。"),
        mk("scc", 2, "Kosaraju 第二遍深度优先搜索在哪张图上进行、按什么次序选起点？",
           "转置图上，按第一遍结束时间从大到小", ["原图上，按编号从小到大", "转置图上，按发现时间从小到大",
                                     "原图上，按第一遍结束时间从小到大"],
           "结束时间最大的点在源头块里；在转置图上从它出发出不去本块。"),
    ]


def q_aoe():
    n = 5
    edges = [(0, 1, 2), (0, 2, 3), (1, 2, 1), (1, 3, 5), (2, 3, 3), (3, 4, 2)]
    tr = aoedata.critical_path_trace(n, edges)
    crit = [e for e in edges if (e[0], e[1]) in tr["crit"]]
    non = [e for e in edges if (e[0], e[1]) not in tr["crit"]]
    acts = {(a["u"], a["v"]): a["slack"] for a in aoedata.activities(tr, edges)}
    lab = lambda e: f"<{e[0]},{e[1]}>（{e[2]} 天）"  # noqa: E731
    slack_e = (1, 2)
    return [
        mk("aoe", 0, f"AOE 网 5 个事件，活动 {', '.join(lab(e) for e in edges)}。整个工程最少要几天？",
           str(tr["total"]), ["7", "16", "8"],
           "工期是从源点到汇点的最长路径长度：0→1→3→4 = 2+5+2 = 9。", ("aoe_total", n, edges)),
        mk("aoe", 1, "同一个网里，下面哪个是关键活动（机动时间为 0）？", lab(crit[1]),
           [lab(e) for e in non], "关键活动满足最早开始 = 最迟开始；0→1→3→4 上的活动都是。",
           ("aoe_crit", n, edges, [crit[1][0], crit[1][1]])),
        mk("aoe", 2, f"同一个网里，活动 <1,2> 的机动时间是几天？", str(acts[slack_e]), ["0", "1", "2", "5"],
           f"最早开始 e = ve[1]，最迟开始 l = vl[2] − 1，差为 {acts[slack_e]}；在这个范围内拖延不影响工期。",
           ("aoe_slack", n, edges, list(slack_e))),
    ]


def q_floyd():
    n = 4
    edges = [(0, 1, 5), (0, 3, 10), (1, 2, 3), (2, 3, 1), (3, 1, 2)]
    d, _, _ = floyddata.floyd_trace(n, edges)
    return [
        mk("floyd", 0, "有向图 4 个点，边 0→1 (5)、0→3 (10)、1→2 (3)、2→3 (1)、3→1 (2)。Floyd 算完后 0 到 3 的最短距离是？",
           str(d[0][3]), ["10", "8", "6"],
           "0→1→2→3 = 5+3+1 = 9，比直达的 10 短。", ("floyd", n, edges, 0, 3)),
        mk("floyd", 1, "Floyd 三重循环里，中转点 k 那一层必须放在哪里？",
           "最外层", ["最内层", "中间层", "放在哪层都一样"],
           "第 k 轮的意思是「只允许经过 0..k 中转」；k 放里层，用到的格子还没被前面的中转点更新过。"),
        mk("floyd", 2, "n 个点的图用 Floyd 求所有点对最短路，时间复杂度是？",
           "O(n³)", ["O(n²)", "O(n² log n)", "O(2ⁿ)"],
           "n 轮中转，每轮把 n×n 的表扫一遍。"),
    ]


def q_bford():
    n = 4
    edges = [(0, 1, 6), (0, 2, 3), (2, 1, -4), (1, 3, 2), (2, 3, 5)]
    dist = bforddata.bellman_ford(n, edges, 0)
    return [
        mk("bford", 0, "有向图 4 个点，边 0→1 (6)、0→2 (3)、2→1 (−4)、1→3 (2)、2→3 (5)。从 0 出发到 3 的最短距离是？",
           str(dist[3]), ["8", "7", "−2"],
           "0→2→1→3 = 3−4+2 = 1；Dijkstra 会先把 1 定成 6 而出错。", ("bf", n, edges, 0, 3)),
        mk("bford", 1, "Bellman-Ford 做完 n−1 轮松弛后，再扫一遍所有边还能让某个距离变小，说明什么？",
           "从源点能到达一个负权环", ["图里有负权边", "图不连通", "边的顺序排得不好，需要再多跑几轮"],
           "没有负环时最短路至多 n−1 条边，n−1 轮后必定稳定。"),
        mk("bford", 2, "Dijkstra 遇到负权边为什么可能算错？",
           "已经「确定」的点，之后还可能经负权边变得更近", ["负数不能放进优先队列", "负权边会形成环",
                                          "Dijkstra 只能处理无向图"],
           "Dijkstra 假设先出队的点距离不会再变小，负权边打破了这个假设。"),
    ]


def q_mst():
    n = 5
    edges = [(0, 1, 4), (0, 2, 1), (1, 2, 2), (1, 3, 5), (2, 3, 8), (2, 4, 9), (3, 4, 3)]
    tree, _ = mstdata.kruskal_trace(n, edges)
    total = mstdata.weight(tree)
    return [
        mk("mst", 0, "无向图 5 个点，边 (0,1) 4、(0,2) 1、(1,2) 2、(1,3) 5、(2,3) 8、(2,4) 9、(3,4) 3。最小生成树的总权是？",
           str(total), ["14", "10", "13"],
           "按权从小到大取：1、2、3 都不成环；4 会让 0-1-2 成环，跳过；再取 5，四条边连通五个点。",
           ("mst", n, edges)),
        mk("mst", 1, "Kruskal 每考虑一条边，要判断它的两端是否已经连通。最常用的数据结构是？",
           "并查集", ["栈", "最小堆", "邻接矩阵"],
           "两端的根相同就会成环，跳过；不同就合并两棵树。"),
        mk("mst", 2, "Prim 与 Kruskal 生长的方式有何不同？",
           "Prim 始终是一棵树向外长；Kruskal 是一片森林逐渐合并", ["Prim 按边权排序；Kruskal 从一个点出发",
                                                 "两者完全一样，只是写法不同", "Prim 只能用于有向图"],
           "两者都靠切分性质保证正确，只是选边的范围不同。"),
    ]


def q_qsort():
    arr = [7, 2, 9, 4, 3, 8, 5]
    a = list(arr)
    p = qsortdata.partition_lomuto(a, 0, len(a) - 1)
    return [
        mk("qsort", 0, f"对 {fmt_list(arr)} 做一次 Lomuto 分割（末元素 5 当基准，小于基准的依次换到前面，最后基准归位），结果是？",
           fmt_list(a), [fmt_list(sorted(arr)), fmt_list([2, 4, 3, 5, 7, 9, 8]), fmt_list([4, 2, 3, 5, 9, 8, 7])],
           f"2、4、3 依次换到前面，基准换到下标 {p}；分割只保证左小右大，两边内部不排序。", ("lomuto", arr)),
        mk("qsort", 1, "总拿第一个元素当基准，输入已经有序时，快速排序的比较次数是什么量级？",
           "Θ(n²)", ["Θ(n log n)", "Θ(n)", "Θ(log n)"],
           "每次只分出一个元素，递归树退化成一条链。"),
        mk("qsort", 2, "为什么快速排序常用随机基准？",
           "让任何固定输入都难以总是分得极不均匀", ["保证排序稳定", "减少额外内存到 O(1)", "保证最坏情况是 O(n log n)"],
           "随机化后期望 O(n log n)，但最坏情况仍可能是 n²，只是概率极小。"),
    ]


def q_radix():
    arr = [329, 457, 657, 839, 436, 720, 355]
    passes = radixdata.radix_passes(arr)
    second = passes[1][2]
    return [
        mk("radix", 0, f"对 {fmt_list(arr)} 做基数排序（先个位、再十位、再百位，桶内保持原次序）。第二趟（按十位）收集后的序列是？",
           fmt_list(second), [fmt_list(sorted(arr, key=lambda x: x // 10 % 10)), fmt_list(passes[0][2]),
                              fmt_list(sorted(arr))],
           "第一趟按个位后是 720 355 436 457 657 329 839；第二趟按十位分桶，同一桶里保持第一趟的次序。",
           ("radix_pass", arr, 2)),
        mk("radix", 1, "只靠两两比较给 4 个数排序，最坏情况下至少要比较几次？",
           str(radixdata.lower_bound(4)), ["4", "6", "3"],
           "判定树至少有 4! = 24 片叶子，二叉树高至少 ⌈log₂24⌉ = 5。", ("lb", 4)),
        mk("radix", 2, "稳定的计数排序用前缀和定位时，为什么要从原数组的末尾往前放？",
           "相同关键字里靠后的先放进靠后的位置，保持原来的相对次序",
           ["这样前缀和不会越界", "从后往前更快", "为了能处理负数"],
           "前缀和给出的是该关键字区间的末尾；从后往前放才不会把相等元素的次序颠倒。"),
    ]


def q_hash():
    keys, m = [22, 33, 7, 18, 44], 11
    pos = hashdata.insert_hash_table(keys, m)
    return [
        mk("hash", 0, f"散列表长 {m}，h(k) = k mod {m}，线性探测。依次插入 {', '.join(map(str, keys))}，44 落在几号槽？",
           str(pos[-1]), ["0", "1", "3"],
           "22 占 0，33 冲突到 1，7 占 7，18 冲突到 8；44 的散列地址 0 被占，探查 1 也被占，落到 2。",
           ("linear", keys, m, 44)),
        mk("hash", 1, "线性探测的主要毛病是什么？", "连续占用的槽连成一片，越长越容易再撞上（聚集）",
           ["删除元素后表长会变", "散列函数必须是取余", "查找时可能找不到已插入的关键字"],
           "落在这一片任何位置的关键字都会接到它的末尾；二次探测、拉链法可以缓解。"),
        mk("hash", 2, "表长 11，线性探测，只有连续的 4 个槽被占，其余 7 个槽都空。下一个关键字（散列地址均匀）恰好让这一段变长的概率是？",
           "5/11", ["4/11", "1/11", "1/2"],
           "散列到这 4 个槽之一，或正好落在它后面那个空槽，都会接在末尾。"),
    ]


def q_trie():
    words = ["tea", "ten", "to", "inn", "in"]
    t = triedata.build(words)
    nodes = len(triedata.snapshot(t))
    comp = triedata.complete(t, "te")
    return [
        mk("trie", 0, f"把 {', '.join(words)} 插入一棵空字典树，连同根一共有几个结点？", str(nodes),
           [str(sum(map(len, words)) + 1), str(nodes - 1), str(nodes + 1)],
           "公共前缀只建一次：t、te、tea、ten、to、i、in、inn，加上根。", ("trie_nodes", words)),
        mk("trie", 1, "同一棵字典树里，前缀 te 的补全结果（按字典序）是？", " ".join(comp),
           ["ten tea", "tea", "tea ten to"], "孩子按 a 到 z 的次序走，补全结果自然是字典序。",
           ("trie_complete", words, "te")),
        mk("trie", 2, "in 和 inn 都在词典里，字典树靠什么区分「in 是一个词」？",
           "结点上的结尾计数（word_count）大于 0", ["in 的结点没有孩子", "额外存一张散列表", "根结点记录所有单词"],
           "in 的结点有孩子 n，光看形状分不出来，要靠结尾标记。"),
    ]


def q_bit():
    i, n = 13, 16
    qp = bitdata.query_path(i)
    up = bitdata.update_path(5, n)
    return [
        mk("bit", 0, f"树状数组求前 {i} 个数的和：从 i = {i} 起反复 i −= lowbit(i)，依次要加哪几格？",
           fmt_list(qp), [fmt_list([13, 12, 10, 8]), fmt_list([13, 14, 16]), fmt_list([13, 9, 1])],
           "13 = 1101₂，每次去掉最低位的 1：13 → 12 → 8 → 0。", ("bit_q", i)),
        mk("bit", 1, f"长度 {n} 的树状数组，给第 5 个数加上 v，要更新哪几格？", fmt_list(up),
           [fmt_list([5, 4]), fmt_list([5, 6, 7, 8]), fmt_list([5, 7, 8, 16])],
           "每次 i += lowbit(i)：5 → 6 → 8 → 16。", ("bit_u", 5, n)),
        mk("bit", 2, "树状数组第 12 格 C[12] 存的是原数组哪一段的和？",
           "a[9] 到 a[12]", ["a[1] 到 a[12]", "a[12] 到 a[15]", "a[11] 到 a[12]"],
           "lowbit(12) = 4，C[i] 管 (i − lowbit(i), i] 这一段。", ("bit_cover", 12)),
    ]


def q_manacher():
    s = "forgeeksskeegfor"
    best = manacherdata.SolutionManacher().longestPalindrome(s)
    return [
        mk("manacher", 0, f"字符串 {s} 的最长回文子串是？", best, ["eeksskee", "forgeeksskeegfor", "ee"],
           "中心落在 ss 之间（插 # 后是一个 # 号），两边一直对称到 g。", ("lps_pal", s)),
        mk("manacher", 1, "Manacher 先在字符之间插入 #，目的是什么？",
           "让奇数、偶数长度的回文都变成以某个位置为中心的奇数长度", ["减少比较次数到一半", "避免下标越界",
                                                     "让字符串长度变成 2 的幂"],
           "abba 的中心原本在两个 b 之间，插 # 后就落在一个 # 上。"),
        mk("manacher", 2, "Manacher 是线性时间，关键原因是？",
           "最右边界 R 只增不减，每次往外比较都会推进 R", ["镜像位置的半径总能直接照抄", "只检查以字符为中心的回文",
                                           "用了散列加速比较"],
           "镜像在 R 内可直接照抄；碰到 R 才往外比，而每次成功比较都让 R 右移。"),
    ]


def q_slidemax():
    a, k, i = [4, 2, 12, 3, 8, 1, 5], 3, 3
    ans = slidemaxdata.Solution().maxSlidingWindow(a, k)
    snap = slidemaxdata.snapshots(a, k)[i]
    return [
        mk("slidemax", 0, f"nums = {fmt_list(a)}，k = {k}，每个窗口的最大值依次是？", fmt_list(ans),
           [fmt_list([min(a[j:j + k]) for j in range(len(a) - k + 1)]),
            fmt_list([max(a[j:j + k - 1]) for j in range(len(a) - k + 1)]),
            fmt_list([max(a[j], a[j + k - 1]) for j in range(len(a) - k + 1)])],
           "窗口每右移一格输出一次队首；12 进来后把前面不比它大的 4、2 都淘汰，直到它滑出窗口。",
           ("slidemax", a, k)),
        mk("slidemax", 1, f"同一组数据，用存下标的单调队列，处理完 i = {i}（值 {a[i]}）之后，队列里的下标是？",
           fmt_list(snap), [fmt_list(list(range(i - k + 1, i + 1))), fmt_list([i]), fmt_list(snap[:1])],
           f"下标 2 的 12 淘汰了前面的 0、1；{a[i]} 比 12 小，排在它后面留着，等 12 滑出窗口后可能成为最大值。",
           ("slidemax_q", a, k, i)),
        mk("slidemax", 2, "单调队列里存下标而不是存值，主要是为了？",
           "判断队首是否已经滑出窗口", ["让队列保持递减", "节省内存", "方便输出最大值"],
           "只存值就看不出它是否已经滑出窗口；存下标，q[0] <= i - k 就说明过期了。"),
    ]


BUILDERS = [q_bigo, q_linked, q_infix, q_kmp, q_trav, q_bst, q_heap, q_huffman, q_forest, q_topo, q_scc,
            q_aoe, q_floyd, q_bford, q_mst, q_qsort, q_radix, q_hash, q_trie, q_bit, q_manacher,
            q_slidemax]


def build_all(with_checks=False) -> dict:
    out = {}
    for b in BUILDERS:
        film = b.__name__[2:]
        qs = b()
        out[film] = qs if with_checks else [{k: v for k, v in q.items() if k != "_check"} for q in qs]
    return out


if __name__ == "__main__":
    quiz = build_all()
    (HERE / "quiz.json").write_text(json.dumps(quiz, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(quiz)} 支片，{sum(map(len, quiz.values()))} 题 → {HERE / 'quiz.json'}")
