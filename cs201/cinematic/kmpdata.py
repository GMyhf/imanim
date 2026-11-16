"""KMP 片的数据：讲义代码原样 + 插桩轨迹。画面和旁白里的每个数字都从这里来。

出处：2026fall-cs201 讲义 202609_DSA_04_String.md 第 3 节（朴素匹配、特征向量、KMP、最小循环节），
2026spring-cs201 讲义 202603_DSA_W03_KMP_InvertedIndex_BitOpt.md 第 1 节（lps 写法、全部出现位置）。
"""
from __future__ import annotations


# ---------------------------------------------------------------- 讲义原样（spring W03 / fall 3.2 节 lps 写法）
def compute_lps(pattern):
    """
    计算 pattern 的最长前缀后缀（Longest Proper Prefix which is also Suffix）表
    """
    m = len(pattern)
    lps = [0] * m       # 初始化 lps 数组
    length = 0          # 当前最长前后缀长度
    for i in range(1, m):   # i 从 1 开始，lps[0] 永远是 0
        while length > 0 and pattern[i] != pattern[length]:
            length = lps[length - 1]   # 回退到上一个有效前后缀长度
        if pattern[i] == pattern[length]:
            length += 1
        lps[i] = length
    return lps


def kmp_search(text, pattern):
    n = len(text)
    m = len(pattern)
    if m == 0:
        return 0
    lps = compute_lps(pattern)
    matches = []

    j = 0  # 模式串指针
    for i in range(n):  # 主串指针，只增不减
        while j > 0 and text[i] != pattern[j]:
            j = lps[j - 1]  # 模式串回退
        if text[i] == pattern[j]:
            j += 1
        if j == m:
            matches.append(i - j + 1)  # 匹配成功
            j = lps[j - 1]  # 查找下一个匹配

    return matches


# ---------------------------------------------------------------- 讲义原样（fall 3.1 节 modern.py#naive）
def naive_search(text: str, pattern: str) -> int | None:
    """朴素匹配：返回首次出现的 0 起始下标。"""
    if not pattern:
        return 0
    i = 0
    j = 0
    while i < len(pattern) and j < len(text):
        if text[j] == pattern[i]:
            i += 1
            j += 1
        else:
            j = j - i + 1
            i = 0
    return j - len(pattern) if i == len(pattern) else None


# ---------------------------------------------------------------- 插桩：轨迹与比较次数
def naive_trace(text, pattern):
    """naive_search 的逐次比较：[(j 目标下标, i 模式下标, 相等?)]，以及返回值。"""
    ev = []
    i = j = 0
    while i < len(pattern) and j < len(text):
        eq = text[j] == pattern[i]
        ev.append((j, i, eq))
        if eq:
            i += 1
            j += 1
        else:
            j = j - i + 1
            i = 0
    return ev, (j - len(pattern) if i == len(pattern) else None)


def naive_all_count(text, pattern):
    """朴素法找全部出现位置：每个起点从头比到失配或配完。返回 (比较次数, 位置表)。"""
    cnt, pos = 0, []
    for s in range(len(text) - len(pattern) + 1):
        for k in range(len(pattern)):
            cnt += 1
            if text[s + k] != pattern[k]:
                break
        else:
            pos.append(s)
    return cnt, pos


def lps_trace(pattern):
    """compute_lps 的轨迹：每个 i 一组 [(length, 相等?)] 比较序列，及写下的 lps[i]。

    讲义代码里 while 条件和 if 会对同一对字符各比一次；这里把同一对 (i, length) 记为一次比较。
    """
    m = len(pattern)
    lps = [0] * m
    length = 0
    steps = []
    for i in range(1, m):
        seq = []
        while True:
            eq = pattern[i] == pattern[length]
            seq.append((length, eq))
            if eq:
                length += 1
                break
            if length == 0:
                break
            length = lps[length - 1]
        lps[i] = length
        steps.append({"i": i, "seq": seq, "lps": length})
    return steps, lps


def kmp_trace(text, pattern):
    """kmp_search 的轨迹：("cmp", i, j, eq) / ("fall", j旧, j新) / ("match", 起点, j新)。

    与讲义代码等价（同一对字符只记一次比较），test_kmp 对撞位置表。
    """
    lps = compute_lps(pattern)
    m = len(pattern)
    ev, j = [], 0
    for i in range(len(text)):
        while True:
            eq = text[i] == pattern[j]
            ev.append(("cmp", i, j, eq))
            if eq:
                j += 1
                break
            if j == 0:
                break
            ev.append(("fall", j, lps[j - 1]))
            j = lps[j - 1]
        if j == m:
            ev.append(("match", i - m + 1, lps[m - 1]))
            j = lps[m - 1]
    return ev


def cmp_count(ev):
    return sum(1 for e in ev if e[0] == "cmp")


def borders(s):
    """s 的全部真前缀与真后缀，以及相等的那些（长度）。"""
    pre = [s[:k] for k in range(1, len(s))]
    suf = [s[len(s) - k:] for k in range(1, len(s))]
    same = [k for k in range(1, len(s)) if s[:k] == s[len(s) - k:]]
    return pre, suf, same


def minimal_period(s):
    """最小周期 p = n − 整串最长真边界（lps 最后一位）。"""
    return len(s) - compute_lps(s)[-1]


def repetition_count(s):
    p = minimal_period(s)
    return len(s) // p if p < len(s) and len(s) % p == 0 else 1


# ---------------------------------------------------------------- 片中用到的例子
SHORT_T, SHORT_P = "abababd", "ababd"                       # fall 3.2 节手算例
LONG_T, LONG_P = "ABABABABCABABABABCABABABABC", "ABABCABAB"  # spring W03 讲义例，输出 [4, 13]
PERIOD_CASES = ["abcabcabc", "ababa"]                       # fall 3.4 节四例里的两个
WORST_N, WORST_M = 20, 5                                    # 朴素最坏：a^n 里找 a^(m-1)b

SHORT_NAIVE, SHORT_NAIVE_RET = naive_trace(SHORT_T, SHORT_P)
SHORT_KMP = kmp_trace(SHORT_T, SHORT_P)
LONG_LPS = compute_lps(LONG_P)
LONG_KMP = kmp_trace(LONG_T, LONG_P)
LONG_MATCHES = kmp_search(LONG_T, LONG_P)
LONG_NAIVE_CNT, _ = naive_all_count(LONG_T, LONG_P)
WORST_T, WORST_P = "a" * WORST_N, "a" * (WORST_M - 1) + "b"
WORST_NAIVE_CNT, _ = naive_all_count(WORST_T, WORST_P)
WORST_KMP_CNT = cmp_count(kmp_trace(WORST_T, WORST_P))

if __name__ == "__main__":
    print("naive short", len(SHORT_NAIVE), SHORT_NAIVE_RET)
    print("kmp short", cmp_count(SHORT_KMP), kmp_search(SHORT_T, SHORT_P), compute_lps(SHORT_P))
    print("long lps", LONG_LPS, "matches", LONG_MATCHES, "kmp cmp", cmp_count(LONG_KMP), "naive", LONG_NAIVE_CNT)
    print("worst", WORST_NAIVE_CNT, WORST_KMP_CNT)
    for s in PERIOD_CASES:
        print(s, compute_lps(s), minimal_period(s), repetition_count(s))
    print(borders("abab"))
    for st in lps_trace(LONG_P)[0]:
        print(st)
