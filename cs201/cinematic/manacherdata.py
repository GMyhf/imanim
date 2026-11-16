"""Manacher 片的数据：讲义代码原样 + 插桩轨迹。画面和旁白里的每个数字都从这里来。

出处：2026spring-cs201 讲义 LC_top-100-liked.md「M5 最长回文子串」方法二（中心扩展）、方法三（Manacher），
202603_DSA_W03_KMP_InvertedIndex_BitOpt.md 附录 B「KMP, Manacher: Symmetry Power」（盯住最右边界 R）。
"""
from __future__ import annotations


# ---------------------------------------------------------------- 讲义原样（LC_top-100-liked M5 方法二）
class SolutionExpand:
    def longestPalindrome(self, s: str) -> str:
        if not s:
            return ""

        start, end = 0, 0

        def expandAroundCenter(left: int, right: int) -> int:
            while left >= 0 and right < len(s) and s[left] == s[right]:
                left -= 1
                right += 1
            # 退出循环时，s[left] != s[right]，实际回文长度为 (right - 1) - (left + 1) + 1
            return right - left - 1

        for i in range(len(s)):
            # 奇数长度，中心是一个字符
            len1 = expandAroundCenter(i, i)
            # 偶数长度，中心是两个字符之间
            len2 = expandAroundCenter(i, i + 1)

            max_len = max(len1, len2)
            if max_len > end - start:
                start = i - (max_len - 1) // 2
                end = i + max_len // 2

        return s[start : end + 1]


# ---------------------------------------------------------------- 讲义原样（LC_top-100-liked M5 方法三）
class SolutionManacher:
    def longestPalindrome(self, s: str) -> str:
        if not s:
            return ""

        # 预处理：插入 "#" 以处理偶数长度的回文
        t = "#" + "#".join(s) + "#"
        n = len(t)
        p = [0] * n  # p[i] 存储以 t[i] 为中心的回文半径

        center = 0
        max_right = 0
        max_len = 0
        start = 0

        for i in range(n):
            if i < max_right:
                mirror = 2 * center - i
                p[i] = min(max_right - i, p[mirror])
            else:
                p[i] = 1

            # 尝试向两边扩展
            while i - p[i] >= 0 and i + p[i] < n and t[i - p[i]] == t[i + p[i]]:
                p[i] += 1

            # 更新中心和最右边界
            if i + p[i] - 1 > max_right:
                center = i
                max_right = i + p[i] - 1

            # 记录最长回文子串在原字符串中的起始位置和长度
            if p[i] - 1 > max_len:
                max_len = p[i] - 1
                start = (i - p[i] + 1) // 2

        return s[start : start + max_len]


# ---------------------------------------------------------------- 插桩
def expand_count(s: str) -> int:
    """中心扩展（方法二）做的字符比较次数：while 条件里真正比到 s[left] == s[right] 的次数。"""
    cmp = 0
    for i in range(len(s)):
        for left, right in ((i, i), (i, i + 1)):
            while left >= 0 and right < len(s):
                cmp += 1
                if s[left] != s[right]:
                    break
                left -= 1
                right += 1
    return cmp


def manacher_trace(s: str) -> dict:
    """方法三逐个 i 的记录：init（初值）、case（'out' 在 R 外 / 'in' 镜像在内 / 'edge' 镜像顶到边界）、
    mirror、center/max_right（处理前）、cmps（[(左下标, 右下标, 相等?)]）、p_final、以及处理后的 center/max_right。"""
    t = "#" + "#".join(s) + "#"
    n = len(t)
    p = [0] * n
    center = max_right = max_len = start = 0
    steps = []
    for i in range(n):
        st = {"i": i, "C": center, "R": max_right, "mirror": None}
        if i < max_right:
            mirror = 2 * center - i
            p[i] = min(max_right - i, p[mirror])
            st["mirror"] = mirror
            st["case"] = "in" if p[mirror] <= max_right - i else "edge"   # 镜像回文严格落在 L 之内 / 顶到或越过 L
        else:
            p[i] = 1
            st["case"] = "out"
        st["init"] = p[i]
        cmps = []                  # 第一次比较若落在 max_right 上（edge 情形），是讲义初值少取一格带来的复核
        while i - p[i] >= 0 and i + p[i] < n:
            eq = t[i - p[i]] == t[i + p[i]]
            cmps.append((i - p[i], i + p[i], eq))
            if not eq:
                break
            p[i] += 1
        st["cmps"] = cmps
        st["p"] = p[i]
        if i + p[i] - 1 > max_right:
            center = i
            max_right = i + p[i] - 1
        if p[i] - 1 > max_len:
            max_len = p[i] - 1
            start = (i - p[i] + 1) // 2
        st["C2"], st["R2"] = center, max_right
        steps.append(st)
    return {"t": t, "p": p, "steps": steps, "answer": s[start:start + max_len],
            "cmps": sum(len(x["cmps"]) for x in steps),
            "hits": sum(sum(1 for c in x["cmps"] if c[2]) for x in steps),
            "misses": sum(sum(1 for c in x["cmps"] if not c[2]) for x in steps)}


# ---------------------------------------------------------------- 片中用到的例子
BABAD = "babad"                 # LeetCode 5 示例 1
ABBA = "abba"                   # 偶数长度回文：插 # 后中心落在 # 上
DEMO = "abacabacab"             # 主例：一个长回文罩住后半段，三种情况都出现
GROW = [10, 20, 40, 80]         # 全 a 串的长度：比较次数曲线


def grow_table():
    """全 a 串：中心扩展 vs Manacher 的比较次数。"""
    return [(n, expand_count("a" * n), manacher_trace("a" * n)["cmps"]) for n in GROW]


def case_examples(s: str = DEMO):
    """主例里三种情况各取第一次出现的步。"""
    tr = manacher_trace(s)
    out = {}
    for st in tr["steps"]:
        out.setdefault(st["case"], st)
    return out


if __name__ == "__main__":
    tr = manacher_trace(DEMO)
    print(tr["t"], tr["p"], tr["answer"], tr["cmps"], tr["hits"], tr["misses"])
    print(expand_count(DEMO))
    for st in tr["steps"]:
        print(st["i"], tr["t"][st["i"]], st["case"], st["mirror"], st["init"], st["p"], len(st["cmps"]), st["C2"], st["R2"])
    print(grow_table())
    print(manacher_trace(BABAD)["p"], SolutionManacher().longestPalindrome(BABAD), SolutionExpand().longestPalindrome(BABAD))
