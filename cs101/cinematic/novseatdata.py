"""图书馆选座（E31530）精讲片的数据：讲义 Python 代码复用 novdata.solve_t2（原样），这里只加插桩。

- LECTURE_SRC：讲义代码原文（取 solve_t2 的函数体），片中逐行对照用；
- naive_trace：朴素模拟，每位同学从头扫，记录每人扫过的格子；
- pointer_trace：与讲义代码同逻辑的一遍扫描，记录指针检查过的每一格；
- solve_bug_left / solve_bug_right：讲义代码只改一行（去掉 i == 0 / i == n - 1 的判断）得到的错误写法，
  由讲义源码做字符串替换后 exec 生成，保证除那一行外一字不差；
- cpp_right_bug：C++ 去掉 i == n - 1 判断时的行为（std::string 的 s[n] 读到 '\\0'）。
片中自拟数据：DEMO（一排十个座位、来五人）、BUG_IN（左边界错误写法出错的输入）。
"""
from __future__ import annotations

import inspect
import textwrap

import novdata as N

SAMPLES = N.SAMPLES["t2"]
solve = N.solve_t2
run_io = N.run_io

_FULL = inspect.getsource(N.solve_t2)
LECTURE_SRC = textwrap.dedent(_FULL.split("\n", 1)[1]).rstrip("\n")
LECTURE_LINES = LECTURE_SRC.split("\n")
LINE_LEFT = "left = i == 0 or s[i - 1] == '0'"
LINE_RIGHT = "right = i == n - 1 or s[i + 1] == '0'"
BAD_LEFT = "left = s[i - 1] == '0'"
BAD_RIGHT = "right = s[i + 1] == '0'"


def _variant(old: str, new: str, name: str):
    assert _FULL.count(old) == 1
    ns: dict = {}
    exec(_FULL.replace(old, new).replace("def solve_t2(", f"def {name}("), ns)
    return ns[name]


solve_bug_left = _variant(LINE_LEFT, BAD_LEFT, "solve_bug_left")
solve_bug_right = _variant(LINE_RIGHT, BAD_RIGHT, "solve_bug_right")

DEMO = ("0001000000", 5)          # 一排十个座位，第四个有人；来五人，第五位没座位
BUG_IN = ("00001", 2)             # 左边界错误写法：s[-1] 读到最后一个座位的 1
N_MAX = M_MAX = 2000


def ok_at(s, i) -> bool:
    n = len(s)
    return s[i] == '0' and (i == 0 or s[i - 1] == '0') and (i == n - 1 or s[i + 1] == '0')


def naive_trace(s: str, m: int):
    """朴素模拟：每位同学从头扫。返回 [(扫过的下标列表, 坐下的下标或 None)]、最终串。"""
    s, n, out = list(s), len(s), []
    for _ in range(m):
        seen, got = [], None
        for i in range(n):
            seen.append(i)
            if ok_at(s, i):
                s[i] = '1'
                got = i
                break
        out.append((seen, got))
    return out, "".join(s)


def pointer_trace(s: str, m: int):
    """与讲义代码同逻辑：返回 [(i, 能坐吗)]（指针检查过的每一格）、坐下人数、最终串。"""
    s, n, sat, steps = list(s), len(s), 0, []
    for i in range(n):
        if sat == m:
            break
        left = i == 0 or s[i - 1] == '0'
        right = i == n - 1 or s[i + 1] == '0'
        hit = s[i] == '0' and left and right
        if hit:
            s[i] = '1'
            sat += 1
        steps.append((i, hit))
    return steps, sat, "".join(s)


def naive_worst(n: int, m: int) -> int:
    """全空一排、来 m 人时朴素模拟扫过的格子数（坐不下的人扫满 n 格）。"""
    tr, _ = naive_trace("0" * n, m)
    return sum(len(seen) for seen, _ in tr)


def cpp_right_bug(s: str, m: int):
    """C++ 写成 bool r = s[i + 1] == '0'：i = n - 1 时 s[n] 是 '\\0'，右邻永远「不空」。"""
    t, n, sat = list(s) + ['\0'], len(s), 0
    for i in range(n):
        if sat >= m:
            break
        l = i == 0 or t[i - 1] == '0'
        r = t[i + 1] == '0'
        if t[i] == '0' and l and r:
            t[i] = '1'
            sat += 1
    return sat, "".join(t[:n])


CPP_SRC = r"""#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, m, sat = 0;
    string s;
    cin >> n >> m >> s;
    for (int i = 0; i < n && sat < m; i++) {
        bool l = i == 0 || s[i - 1] == '0';
        bool r = i == n - 1 || s[i + 1] == '0';
        if (s[i] == '0' && l && r)
            s[i] = '1', sat++;
    }
    cout << sat << "\n" << s << "\n";
}
"""
CPP_BAD_RIGHT = CPP_SRC.replace("bool r = i == n - 1 || s[i + 1] == '0';", "bool r = s[i + 1] == '0';")
assert CPP_BAD_RIGHT != CPP_SRC
