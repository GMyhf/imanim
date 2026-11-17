"""括号区间审计精讲片（T31534）的数据层：讲义 Python 参考代码复用 novdata.solve_t6（原样），这里只补插桩与错误写法。

讲义：2026fall courseware/202611_ADS_November_Exam_Review.md 第 3 节 T6。片中主例用题面样例 2（())(()，四问），
总览片 nov 演示过的样例 1 三问这里不再走。
- prefix / next_lower 复用 novdata（与 solve_t6 逐行同逻辑，交出单调栈每一步的弹出与栈内容）；
- wrong_count_only：只判左右括号数相等（漏了条件 2）；
- next_lower_ge：弹栈条件写成 >=（同高也弹），nxt 变成「右边第一个不高于」的位置；
- definition_brute 不在这里——独立暴力实现放在 test_novbrk.py，不调用本模块。
"""
from __future__ import annotations

import novdata as N

SAMPLE1, SAMPLE2 = N.SAMPLES["t6"]
S = "())(()"                                    # 题面样例 2
QUERIES = [(1, 2), (2, 5), (1, 6), (3, 6)]
EXPECT = SAMPLE2[1].split("\n")                 # YES NO NO NO
assert SAMPLE2[0].split("\n")[0] == S and int(SAMPLE2[0].split("\n")[1]) == len(QUERIES)
assert [tuple(map(int, ln.split())) for ln in SAMPLE2[0].strip().split("\n")[2:]] == QUERIES

COUNTER = [(4, 5), (2, 5)]                      # 两条缺一不可的反例：只满足 ② / 只满足 ①
SCAN_OK, SCAN_BAD = "(())()", "())("           # task 段演示「从左往右数差值」的一好一坏

N_MAX = N.N_MAX                                 # 2×10⁵
NAIVE = N.NAIVE_T6                              # 4×10¹⁰

prefix = N.prefix
next_lower = N.next_lower


def running(s: str) -> list[int]:
    """从左往右数：每读一个字符后，左括号数 − 右括号数。"""
    out, d = [], 0
    for ch in s:
        d += 1 if ch == "(" else -1
        out.append(d)
    return out


def sample_input(s: str, qs) -> str:
    return f"{s}\n{len(qs)}\n" + "".join(f"{l} {r}\n" for l, r in qs)


def lecture_answers(s: str, qs) -> list[str]:
    """讲义 Python 代码原样（novdata.solve_t6）跑出来的答案。"""
    return N.run_io(N.solve_t6, sample_input(s, qs)).split("\n")


def judge(s: str, l: int, r: int) -> dict:
    """片中逐问画的量：两端高度、nxt[l-1]、两条各自是否满足、结论。"""
    pre = prefix(s)
    nxt, _ = next_lower(pre)
    c1 = pre[r] == pre[l - 1]
    c2 = nxt[l - 1] > r
    return {"l": l, "r": r, "a": pre[l - 1], "b": pre[r], "nxt": nxt[l - 1], "c1": c1, "c2": c2,
            "ok": c1 and c2, "min": min(pre[l - 1:r + 1])}


def wrong_count_only(s: str, qs) -> list[str]:
    """常见错误：只看左右括号一样多（漏了「中间不跌破」）。"""
    pre = prefix(s)
    return ["YES" if pre[r] == pre[l - 1] else "NO" for l, r in qs]


def next_lower_ge(pre: list[int]) -> list[int]:
    """常见错误：弹栈条件写成 >=，同高也弹，得到「右边第一个不高于」的位置。"""
    n = len(pre) - 1
    nxt, stk = [n + 1] * (n + 1), []
    for j in range(n + 1):
        while stk and pre[stk[-1]] >= pre[j]:
            nxt[stk.pop()] = j
        stk.append(j)
    return nxt


def wrong_ge(s: str, qs) -> list[str]:
    pre = prefix(s)
    nxt = next_lower_ge(pre)
    return ["YES" if pre[r] == pre[l - 1] and nxt[l - 1] > r else "NO" for l, r in qs]


# 讲义 Python 参考代码（与 novdata.solve_t6 函数体逐行一致，test 里核对），片中按三段高亮
CODE = '''import sys

data = sys.stdin.read().split()
s = data[0]
n = len(s)
# pre[i]：前 i 个字符中 左括号数 - 右括号数
pre = [0] * (n + 1)
for i, ch in enumerate(s):
    pre[i + 1] = pre[i] + (1 if ch == '(' else -1)

# nxt[i]：i 右边第一个 pre 比 pre[i] 小的位置（单调栈）
nxt = [n + 1] * (n + 1)
stk = []
for j in range(n + 1):
    while stk and pre[stk[-1]] > pre[j]:
        nxt[stk.pop()] = j
    stk.append(j)

q = int(data[1])
out = []
for k in range(q):
    l, r = int(data[2 + 2 * k]), int(data[3 + 2 * k])
    ok = pre[r] == pre[l - 1] and nxt[l - 1] > r
    out.append('YES' if ok else 'NO')
print('\\n'.join(out))'''
CODE_LINES = CODE.split("\n")
SEGMENTS = {"pre": (2, 8), "stack": (10, 16), "query": (18, 24)}   # 0-based 闭区间行号
