"""「程序是怎么跑起来的」片的数据层：字节码条数、存储层次换算、缓存行命中、print 与 join 的系统调用次数。

约定与讲义一致（W13 讲义 1.2、3.2、3.3、4.2 节）：
- LOOP_SRC / SUM_SRC 是讲义 1.2 节计时代码里的两段求和，原样编译后用 dis 列字节码、用 sys.settrace 逐条计数
  （不计时；耗时只引用讲义的「典型结果」TYPICAL）。字节码随 Python 版本略有差异，条数由运行机器上现算。
- ROW_SRC / COL_SRC 是讲义 3.2 节按行、按列两重循环原样（N 取 8 作示意），执行时把矩阵换成会记下访问下标的 Rec，
  交出访问顺序；inner_body 用 dis 数两种写法内层每圈的字节码条数；
  缓存行与 LRU 缓存模拟器 simulate 是补写的示意（真实缓存行 64 字节、按组相联，这里只取「一次搬一整行」这一点）。
- LATENCY 是讲义 3.3 节的表；human() 把「1 纳秒 = 1 秒」换算成人类尺度。
- squares_join 是讲义 4.2 节的批量输出原样（范围由 5 改成 N_PRINT）；squares_print 是补写的逐个 print 版本。
  两者都写进一个数 write 调用次数的假 stdout：line_buffering=True 模拟终端（按行刷新），
  False 加固定 8 KB 缓冲模拟重定向到文件（缓冲大小按版本不同，3.14 起缺省是 128 KB，这里固定 8 KB 作示意）。
"""
from __future__ import annotations

import dis
import io
import sys

# ---------------------------------------------------------------- 1.2 字节码
N_SUM = 3_000_000                    # 讲义：n = 3_000_000
TYPICAL = {"loop": 0.2, "sum": 0.03}  # 讲义：典型结果，循环约 0.2s，sum 约 0.03s —— 相差 5~10 倍

LOOP_SRC = "s = 0\nfor i in range(n):                      # 纯 Python 循环\n    s += i\n"
SUM_SRC = "s2 = sum(range(n))                      # 内建 sum，C 实现\n"


def listing(src):
    """源码编译后的字节码：[(opname, argrepr)]，与 dis.dis 打印的一致。"""
    return [(ins.opname, ins.argrepr) for ins in dis.get_instructions(compile(src, "<lecture>", "exec"))]


def loop_body(src=LOOP_SRC):
    """循环体：从 FOR_ITER 到 JUMP_BACKWARD（含两端）这几条，每转一圈执行一遍。"""
    ins = listing(src)
    a = next(k for k, (op, _) in enumerate(ins) if op == "FOR_ITER")
    b = next(k for k, (op, _) in enumerate(ins) if op.startswith("JUMP_BACKWARD"))
    return ins[a:b + 1]


def executed(src, n):
    """用 sys.settrace 的 opcode 事件，数这段代码在 n 下实际执行了多少条字节码（只数这段代码自己的帧）。"""
    code = compile(src, "<lecture>", "exec")
    cnt = 0

    def tr(frame, ev, arg):
        nonlocal cnt
        frame.f_trace_opcodes = True
        if ev == "opcode" and frame.f_code is code:
            cnt += 1
        return tr
    old = sys.gettrace()
    sys.settrace(tr)
    try:
        exec(code, {"n": n})
    finally:
        sys.settrace(old)
    return cnt


def loop_formula():
    """循环版执行条数 = per * n + base：小 n 实测两点定出，test 再用别的 n 验证。"""
    c0, c1 = executed(LOOP_SRC, 0), executed(LOOP_SRC, 1)
    return c1 - c0, c0


def loop_total(n=N_SUM):
    per, base = loop_formula()
    return per * n + base


def sum_total(n=N_SUM):
    """sum 版执行条数与 n 无关（循环在 C 里）；n 大时直接 exec 太慢不必，取小 n 的实测。"""
    return executed(SUM_SRC, min(n, 1000))


# ---------------------------------------------------------------- 3.3 时间层次
LATENCY = [("L1 缓存", 1), ("L2 缓存", 4), ("内存", 100), ("SSD 随机读", 100_000),
           ("网络往返（同城）", 1_000_000), ("磁盘寻道", 10_000_000)]     # 讲义 3.3 表（纳秒），按时间排序

UNITS = [("年", 365 * 86400), ("个月", 30 * 86400), ("天", 86400), ("小时", 3600), ("分钟", 60), ("秒", 1)]


def human(ns):
    """1 纳秒 = 1 秒：返回 (数值, 单位)，取第一个 ≥1 的单位，保留一位小数（整数就不带小数）。"""
    sec = ns
    for name, u in UNITS:
        if sec >= u:
            v = round(sec / u, 1)
            return (int(v) if v == int(v) else v), name
    return sec, "秒"


def real(ns):
    """真实时间的写法：1 ns / 100 μs / 10 ms。"""
    for name, u in (("s", 10 ** 9), ("ms", 10 ** 6), ("μs", 10 ** 3)):
        if ns >= u:
            return f"{ns // u} {name}"
    return f"{ns} ns"


ADDS = 10_000                                 # 「少算一万次加法」：按一次加法约 1 ns（与 L1 同量级）估


# ---------------------------------------------------------------- 3.2 按行 vs 按列
N_GRID = 8                                    # 示意矩阵 8×8（讲义实测 N = 1200）
N_LECTURE = 1200
LINE = 4                                      # 一个缓存行装 4 个数（示意；真实缓存行 64 字节）
WAYS = 4                                      # 缓存只放得下 4 个缓存行（全相联 LRU，示意）

ROW_SRC = """s = 0
for i in range(N):                  # 按行：内层 j 变化，访问连续
    row = a[i]
    for j in range(N):
        s += row[j]
"""
COL_SRC = """s2 = 0
for j in range(N):                  # 按列：内层 i 变化，每次跳一整行
    for i in range(N):
        s2 += a[i][j]
"""


class Rec:
    """会记下访问下标的二维表（元素都是 1，同讲义 [[1] * N for _ in range(N)]）：a[i] 返回一行，行再 [j] 时记 (i, j)。"""

    def __init__(self, log):
        self.log = log

    def __getitem__(self, i):
        return _RecRow(i, self.log)


class _RecRow:
    def __init__(self, i, log):
        self.i, self.log = i, log

    def __getitem__(self, j):
        self.log.append((self.i, j))
        return 1


def _run(src, n):
    log = []
    g = {"a": Rec(log), "N": n}
    exec(compile(src, "<lecture>", "exec"), g)
    return log, g


def row_major(n=N_GRID):
    """讲义 3.2 按行两重循环原样执行，返回访问顺序 [(i, j)]。"""
    return _run(ROW_SRC, n)[0]


def col_major(n=N_GRID):
    """讲义 3.2 按列两重循环原样执行，返回访问顺序 [(i, j)]。"""
    return _run(COL_SRC, n)[0]


def inner_body(src):
    """内层循环每圈执行的字节码：第二个 FOR_ITER 到它之后第一个 JUMP_BACKWARD。"""
    ins = listing(src)
    fi = [k for k, (op, _) in enumerate(ins) if op == "FOR_ITER"]
    a = fi[1]
    b = next(k for k in range(a, len(ins)) if ins[k][0].startswith("JUMP_BACKWARD"))
    return ins[a:b + 1]


def simulate(order, line=LINE, ways=WAYS):
    """按行优先连续存放，地址 = i * 列数 + j；缓存行号 = (i, j // line)。LRU 全相联缓存。

    返回 [(i, j, hit, evicted, cache_after)]：evicted 是被挤掉的缓存行（没有为 None），cache_after 按最近使用从旧到新。
    """
    cache, out = [], []
    for i, j in order:
        key = (i, j // line)
        ev = None
        if key in cache:
            hit = True
            cache.remove(key)
        else:
            hit = False
            if len(cache) == ways:
                ev = cache.pop(0)
        cache.append(key)
        out.append((i, j, hit, ev, list(cache)))
    return out


def misses(order, **kw):
    return sum(not h for _, _, h, _, _ in simulate(order, **kw))


# ---------------------------------------------------------------- 4.2 缓冲
N_PRINT = 10_000
FILE_BUF = 8192                               # 示意的文件缓冲区 8 KB


class CountingRaw(io.RawIOBase):
    """假的底层输出：每次 write 就是一次系统调用，记次数与字节数。"""

    def __init__(self):
        self.calls, self.nbytes = 0, 0

    def writable(self):
        return True

    def write(self, b):
        self.calls += 1
        self.nbytes += len(b)
        return len(b)


def squares_print(n=N_PRINT):                 # 补写：逐个 print
    for i in range(n):
        print(i * i)


def squares_join(n=N_PRINT):                  # 讲义 4.2 原样（range(5) 换成 range(n)）
    out = []
    for i in range(n):
        out.append(str(i * i))
    sys.stdout.write('\n'.join(out) + '\n')


def syscalls(fn, terminal, n=N_PRINT, buf_size=FILE_BUF):
    """把 sys.stdout 换成数 write 次数的假输出，跑 fn(n)；terminal=True 按行刷新，否则 buf_size 字节块缓冲。

    返回 (系统调用次数, 字节数)。
    """
    raw = CountingRaw()
    buf = io.BufferedWriter(raw, buffer_size=buf_size)
    fake = io.TextIOWrapper(buf, encoding="utf-8", line_buffering=terminal)
    fake._CHUNK_SIZE = buf_size              # 文本层自己也攒一块（缺省 8 KB）再交给缓冲层，两层取同样大小
    old = sys.stdout
    sys.stdout = fake
    try:
        fn(n)
        fake.flush()
    finally:
        sys.stdout = old
    return raw.calls, raw.nbytes
