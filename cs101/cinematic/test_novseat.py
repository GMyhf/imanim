"""图书馆选座精讲片的独立对撞：题面样例、暴力参照随机对拍、片中画出的每个数字、旁白数字、错误写法实跑。

独立实现不调用 novseatdata 的算法：seats_brute 逐人从头找（另写一遍），scan_count 按「第 m 人坐下的位置」
直接推指针走过的格子数，naive_count 逐人数格子；C++ 两份代码有 g++ 时真的编译运行。
用法（cwd = cs101/cinematic）：python -m unittest test_novseat
"""
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

import novseatdata as D

HERE = Path(__file__).resolve().parent


def can_sit(s, i):
    n = len(s)
    if s[i] != '0':
        return False
    if i > 0 and s[i - 1] != '0':
        return False
    if i < n - 1 and s[i + 1] != '0':
        return False
    return True


def seats_brute(s, m):
    s, sat = list(s), 0
    for _ in range(m):
        free = [i for i in range(len(s)) if can_sit(s, i)]
        if free:
            s[free[0]] = '1'
            sat += 1
    return sat, "".join(s)


def naive_count(s, m):
    """逐人数格子：坐下的人扫到自己座位为止，坐不下的扫满 n 格。"""
    s, per = list(s), []
    for _ in range(m):
        free = [i for i in range(len(s)) if can_sit(s, i)]
        if free:
            s[free[0]] = '1'
            per.append(free[0] + 1)
        else:
            per.append(len(s))
    return per


def scan_count(s, m):
    """单指针检查过的格子数：第 m 人坐在 j 就是 j + 1 格，否则整排 n 格。"""
    t, seated = list(s), []
    for _ in range(m):
        free = [i for i in range(len(t)) if can_sit(t, i)]
        if not free:
            break
        t[free[0]] = '1'
        seated.append(free[0])
    return seated[-1] + 1 if len(seated) == m and m > 0 else len(s)


def narration():
    return "".join(b["narration"] for b in json.loads((HERE / "novseat.json").read_text(encoding="utf-8"))["beats"])


class NovSeatFacts(unittest.TestCase):
    def test_samples(self):
        self.assertEqual(D.SAMPLES, [("5 2\n00000\n", "2\n10100"), ("4 2\n0100\n", "1\n0101")])
        for inp, out in D.SAMPLES:
            self.assertEqual(D.run_io(D.solve, inp), out)
            n, m = map(int, inp.split()[:2])
            sat, fin = seats_brute(inp.split()[2], m)
            self.assertEqual(f"{sat}\n{fin}", out)

    def test_sample_walk(self):
        """片中样例逐步：样例一坐 1、3 号（2 号挨着）；样例二 1、3 号挨着 2 号，坐 4 号，第二人离开。"""
        tr, fin = D.naive_trace("00000", 2)
        self.assertEqual([g for _, g in tr], [0, 2])
        self.assertEqual(fin, "10100")
        self.assertFalse(can_sit("10000", 1))
        tr, fin = D.naive_trace("0100", 2)
        self.assertEqual([g for _, g in tr], [3, None])
        self.assertEqual(fin, "0101")
        self.assertEqual([can_sit("0100", i) for i in range(4)], [False, False, False, True])

    def test_random(self):
        rnd = random.Random(31530)
        for _ in range(800):
            n = rnd.randint(1, 13)
            s = "".join(rnd.choice("0001") for _ in range(n))
            m = rnd.randint(1, 9)
            sat, fin = seats_brute(s, m)
            self.assertEqual(D.run_io(D.solve, f"{n} {m}\n{s}\n"), f"{sat}\n{fin}")
            tr, fin2 = D.naive_trace(s, m)
            self.assertEqual(fin2, fin)
            self.assertEqual([len(seen) for seen, _ in tr], naive_count(s, m))
            steps, sat3, fin3 = D.pointer_trace(s, m)
            self.assertEqual((sat3, fin3), (sat, fin))
            self.assertEqual(len(steps), scan_count(s, m))
            self.assertLessEqual(len(steps), n)

    def test_monotone(self):
        """单调性：朴素模拟里每人坐的位置严格递增，且相邻两人至少隔一个座位。"""
        rnd = random.Random(2)
        for _ in range(500):
            n = rnd.randint(1, 14)
            s = "".join(rnd.choice("0001") for _ in range(n))
            got = [g for _, g in D.naive_trace(s, rnd.randint(1, 9))[0] if g is not None]
            self.assertTrue(all(b >= a + 2 for a, b in zip(got, got[1:])))

    def test_demo(self):
        s, m = D.DEMO
        self.assertEqual((s, m), ("0001000000", 5))
        self.assertEqual(naive_count(s, m), [1, 6, 8, 10, 10])
        self.assertEqual(sum(naive_count(s, m)), 35)
        tr, fin = D.naive_trace(s, m)
        self.assertEqual([g for _, g in tr], [0, 5, 7, 9, None])
        self.assertEqual(fin, "1001010101")
        steps, sat, fin2 = D.pointer_trace(s, m)
        self.assertEqual((len(steps), sat, fin2), (10, 4, fin))
        self.assertEqual([i for i, ok in steps if ok], [0, 5, 7, 9])

    def test_scale(self):
        n = m = 2000
        self.assertEqual((D.N_MAX, D.M_MAX), (n, m))
        self.assertEqual(n * m, 4 * 10 ** 6)
        self.assertEqual(sum(naive_count("0" * n, m)), 3 * 10 ** 6)
        self.assertEqual(D.naive_worst(n, m), 3 * 10 ** 6)
        self.assertEqual(scan_count("0" * n, m), 2000)
        self.assertEqual(len(D.pointer_trace("0" * n, m)[0]), 2000)

    def test_lecture_src(self):
        self.assertEqual(len(D.LECTURE_LINES), 13)
        self.assertEqual(D.LECTURE_LINES[6].strip(), D.LINE_LEFT)
        self.assertEqual(D.LECTURE_LINES[7].strip(), D.LINE_RIGHT)
        self.assertEqual(D.LECTURE_LINES[4].strip(), "if sat == m:")
        self.assertNotIn("", D.LECTURE_LINES)                               # 无空行，Code 的 code_lines 下标不乱

    def test_bug_left(self):
        """删掉 i == 0：两个样例都过，BUG_IN 上答案错（s[-1] 读到最后一个座位的 1）。"""
        for inp, out in D.SAMPLES:
            self.assertEqual(D.run_io(D.solve_bug_left, inp), out)
        s, m = D.BUG_IN
        self.assertEqual(s[-1], "1")
        inp = f"{len(s)} {m}\n{s}\n"
        self.assertEqual(D.run_io(D.solve, inp), "2\n10101")
        self.assertEqual(seats_brute(s, m), (2, "10101"))
        self.assertEqual(D.run_io(D.solve_bug_left, inp), "1\n01001")

    def test_bug_right(self):
        """删掉 i == n - 1：Python 读 s[n] 抛 IndexError，样例二就过不去；样例一在扫到末尾前已坐满。"""
        self.assertEqual(D.run_io(D.solve_bug_right, D.SAMPLES[0][0]), D.SAMPLES[0][1])
        with self.assertRaises(IndexError):
            D.run_io(D.solve_bug_right, D.SAMPLES[1][0])
        self.assertEqual(D.cpp_right_bug("0100", 2), (0, "0100"))         # C++：s[n] 是 '\0'，最后一座永远坐不下

    @unittest.skipUnless(shutil.which("g++"), "没有 g++")
    def test_cpp(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = {}
            for name, src in (("ok", D.CPP_SRC), ("bad", D.CPP_BAD_RIGHT)):
                cpp, exe = Path(tmp) / f"{name}.cpp", Path(tmp) / name
                cpp.write_text(src)
                subprocess.run(["g++", "-O2", "-std=c++17", "-o", str(exe), str(cpp)], check=True)
                outs[name] = [subprocess.run([str(exe)], input=inp, capture_output=True, text=True).stdout.strip()
                              for inp, _ in D.SAMPLES]
            self.assertEqual(outs["ok"], [o for _, o in D.SAMPLES])
            self.assertEqual(outs["bad"][1], "0\n0100")                    # 四号坐不下，样例二错
            rnd = random.Random(7)
            exe = Path(tmp) / "ok"
            for _ in range(100):
                n = rnd.randint(1, 10)
                s = "".join(rnd.choice("001") for _ in range(n))
                m = rnd.randint(1, 6)
                got = subprocess.run([str(exe)], input=f"{n} {m}\n{s}\n", capture_output=True, text=True).stdout.strip()
                sat, fin = seats_brute(s, m)
                self.assertEqual(got, f"{sat}\n{fin}")

    def test_narration_numbers(self):
        txt = narration()
        self.assertIn("第一人坐一号", txt)
        self.assertIn("第二人坐三号", txt)
        self.assertIn("四号在最右边", txt)
        self.assertIn("答案是一", txt)
        self.assertIn("这一排十个座位，四号有人，来五个人", txt)
        self.assertEqual(D.DEMO[0][3], "1")
        self.assertIn("第一人扫一格，第二人六格，第三人八格，第四人十格", txt)
        self.assertIn("第五人扫完十格", txt)
        self.assertIn("一共三十五格", txt)
        self.assertIn("最大四百万", txt)
        self.assertIn("指针只走十格，四人坐下", txt)
        self.assertIn("十格对三十五格", txt)
        self.assertIn("两千格对三百万格", txt)
        self.assertIn("换五个座位，最右边有人，来两人", txt)
        self.assertEqual((len(D.BUG_IN[0]), D.BUG_IN[1]), (5, 2))
        self.assertIn("正确答案坐下两人", txt)
        self.assertIn("只坐下一人", txt)
        self.assertIn("两个样例都能过", txt)
        self.assertIn("样例二就过不去", txt)


if __name__ == "__main__":
    unittest.main()
