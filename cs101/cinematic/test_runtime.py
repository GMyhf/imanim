"""「程序是怎么跑起来的」片数字的独立对撞：字节码条数、时间层次换算、缓存命中、系统调用次数与旁白数字。

独立实现：字节码条数用逐条单步的 sys.settrace 在别的 n 上重数、并与 dis 列出的循环体长度对照；
缓存用「直接映射的集合 + 时间戳」另写一个 LRU；按行 / 按列访问顺序用推导式另行生成；
系统调用次数按行数（按行刷新）与字节数 / 缓冲区大小（块缓冲）推算。

用法（cwd = cs101/cinematic）：python -m unittest test_runtime
"""
import json
import math
from pathlib import Path
import sys
import unittest

import runtimedata as D


def lru_misses(order, line, ways):
    """独立方法：字典记每个缓存行最近一次被用的时刻，满了就踢掉时刻最小的。"""
    last, miss = {}, 0
    for t, (i, j) in enumerate(order):
        key = (i, j // line)
        if key not in last:
            miss += 1
            if len(last) == ways:
                del last[min(last, key=last.get)]
        last[key] = t
    return miss


def lines_written_terminal(n):
    """终端按行刷新：每个 print 一行、一次 write。"""
    return n


def block_writes(nbytes, buf):
    """块缓冲：攒满 buf 字节写一次，最后不满的一块在 flush 时再写一次。"""
    return math.ceil(nbytes / buf)


class RuntimeFacts(unittest.TestCase):
    @unittest.skipUnless(sys.version_info[:2] in ((3, 11), (3, 14)),
                         "字节码条数随 CPython 版本变；旁白的「七条」在 3.11（本机、CI）与 3.14（渲染机）上实测")
    def test_bytecode(self):
        body = D.loop_body()
        self.assertEqual(len(body), 7)                                    # 七条：取数、存 i、读 s、读 i、加、存 s、跳回
        self.assertEqual(body[0][0], "FOR_ITER")
        self.assertEqual([op for op, _ in body].count("BINARY_OP"), 1)
        per, base = D.loop_formula()
        self.assertEqual(per, len(body))
        for n in (2, 5, 37, 200):                                         # 公式在别的 n 上重数
            self.assertEqual(D.executed(D.LOOP_SRC, n), per * n + base)
        self.assertEqual(D.loop_total(), 7 * 3_000_000 + base)
        self.assertEqual(D.loop_total() // 10 ** 6, 21)                    # 两千一百万条（多出的是循环外的十几条）
        s0 = D.executed(D.SUM_SRC, 0)
        for n in (1, 10, 1000, 5000):                                     # sum 的条数与 n 无关
            self.assertEqual(D.executed(D.SUM_SRC, n), s0)
        self.assertTrue(8 <= D.sum_total() <= 15)                         # 「十来条」
        self.assertEqual(D.N_SUM, 3_000_000)
        self.assertEqual(D.TYPICAL, {"loop": 0.2, "sum": 0.03})

    def test_inner_bytecode(self):
        r, c = D.inner_body(D.ROW_SRC), D.inner_body(D.COL_SRC)
        self.assertEqual((len(r), len(c)), (9, 11))
        self.assertEqual(len(c) - len(r), 2)                              # 少两条：读 i、取一行

    def test_ladder(self):
        ns = dict(D.LATENCY)
        self.assertEqual([ns[k] for k in ("L1 缓存", "L2 缓存", "内存", "SSD 随机读", "网络往返（同城）", "磁盘寻道")],
                         [1, 4, 100, 10 ** 5, 10 ** 6, 10 ** 7])
        self.assertEqual(D.human(1), (1, "秒"))
        self.assertEqual(D.human(4), (4, "秒"))
        self.assertEqual(D.human(100), (1.7, "分钟"))                     # 一百秒，将近两分钟
        self.assertTrue(1 < 10 ** 5 / 86400 < 2)                          # 一天多
        self.assertEqual(D.human(10 ** 5), (1.2, "天"))
        self.assertTrue(11 < 10 ** 6 / 86400 < 12)                        # 十一天多
        self.assertTrue(3.5 < 10 ** 7 / (30 * 86400) < 4)                 # 将近四个月
        self.assertEqual(D.human(10 ** 7), (3.9, "个月"))
        self.assertLess(D.ADDS * ns["L1 缓存"], ns["磁盘寻道"] / 100)    # 一万次加法远小于一次寻道
        self.assertEqual([D.real(ns) for _, ns in D.LATENCY], ["1 ns", "4 ns", "100 ns", "100 μs", "1 ms", "10 ms"])

    def test_cache(self):
        n = D.N_GRID
        self.assertEqual(D.row_major(), [(i, j) for i in range(n) for j in range(n)])
        self.assertEqual(D.col_major(), [(i, j) for j in range(n) for i in range(n)])
        for order, want in ((D.row_major(), 16), (D.col_major(), 64)):
            self.assertEqual(len(order), 64)
            self.assertEqual(D.misses(order), want)
            self.assertEqual(lru_misses(order, D.LINE, D.WAYS), want)
        for line in (1, 2, 4, 8):                                         # 别的参数下两种 LRU 一致
            for ways in (1, 2, 3, 8, 16):
                for order in (D.row_major(), D.col_major(), D.row_major(5)):
                    self.assertEqual(D.misses(order, line=line, ways=ways), lru_misses(order, line, ways))
        sim = D.simulate(D.row_major())
        self.assertEqual([h for _, _, h, _, _ in sim[:4]], [False, True, True, True])                       # 第一次缺失，后三次命中
        self.assertTrue(all(len(c) <= D.WAYS for *_, c in sim))
        g = D._run(D.ROW_SRC, 7)[1]
        self.assertEqual(g["s"], 49)
        self.assertEqual(D._run(D.COL_SRC, 7)[1]["s2"], 49)

    def test_buffer(self):
        calls_p, nbytes = D.syscalls(D.squares_print, True)
        self.assertEqual(nbytes, sum(len(str(i * i)) + 1 for i in range(D.N_PRINT)))
        self.assertEqual(calls_p, lines_written_terminal(D.N_PRINT))     # 一万次
        self.assertEqual(D.syscalls(D.squares_join, True), (1, nbytes))   # 一次
        self.assertEqual(D.syscalls(D.squares_join, False), (1, nbytes))
        calls_f, _ = D.syscalls(D.squares_print, False)
        self.assertEqual(calls_f, block_writes(nbytes, D.FILE_BUF))       # 十一次
        self.assertEqual(calls_f, 11)
        self.assertEqual(D.FILE_BUF, 8 * 1024)
        for n, buf in ((2000, 4096), (6000, 8192), (777, 1024)):           # 别的缓冲区大小也按向上取整
            c, b = D.syscalls(D.squares_print, False, n, buf)
            self.assertEqual(c, block_writes(b, buf))
            self.assertEqual(D.syscalls(D.squares_print, True, n, buf)[0], n)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in json.loads(
            Path(__file__).with_name("runtime.json").read_text(encoding="utf-8"))["beats"]}
        self.assertIn("三百万个数", beats["title"])
        self.assertIn("零点二秒", beats["title"])
        self.assertIn("零点零三秒", beats["title"])
        self.assertIn("十到一百倍", beats["compile"])
        self.assertIn("七条字节码", beats["bytecode"])
        self.assertIn("三百万圈，就是两千一百万条", beats["bytecode"])
        self.assertIn("只执行十来条", beats["bytecode"])
        for s in ("一级缓存，一秒", "二级缓存，四秒", "一百秒，将近两分钟", "一天多", "十一天多", "将近四个月",
                  "少算一万次加法"):
            self.assertIn(s, beats["ladder"])
        self.assertIn("一个缓存行装四个数", beats["cache"])
        self.assertIn("真实的缓存行是六十四字节", beats["cache"])
        self.assertIn("比一级缓存慢一百倍", beats["ladder"])
        self.assertEqual(dict(D.LATENCY)["内存"] // dict(D.LATENCY)["L1 缓存"], 100)
        self.assertIn("平方级", beats["compile"])
        self.assertIn("只放得下四个缓存行", beats["cache"])
        self.assertIn("后面三次都命中", beats["cache"])
        self.assertIn("六十四次访问，只缺失十六次", beats["cache"])
        self.assertIn("六十四次全部缺失", beats["cache"])
        self.assertIn("一千二百乘一千二百", beats["python"])
        self.assertIn("少两条字节码", beats["python"])
        self.assertIn("一万次 print", beats["buffer"])
        self.assertIn("进出内核一万次", beats["buffer"])
        self.assertIn("只写一次", beats["buffer"])
        self.assertIn("八 KB，一万次 print 也只写十一次", beats["buffer"])
        self.assertEqual((D.N_GRID ** 2, D.LINE, D.WAYS, D.N_LECTURE, D.N_PRINT), (64, 4, 4, 1200, 10000))


if __name__ == "__main__":
    unittest.main()
