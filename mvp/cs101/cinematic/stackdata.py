"""栈片的数据层：括号匹配、后缀求值、单调栈接雨水，全部用讲义代码原样插桩记录事件。

约定与课件一致（W07 P4–P18、讲义 1.2 / 1.4 / 1.5 节）。
"""
from __future__ import annotations


def is_valid_trace(s):
    """讲义 is_valid 插桩。事件：("push", i, ch) / ("pop", i, top, ok) / ("empty", i) / ("end", 剩余个数)。"""
    pairs = {')': '(', ']': '[', '}': '{'}
    stack, ev = [], []
    for i, ch in enumerate(s):
        if ch in '([{':
            stack.append(ch)
            ev.append(("push", i, ch))
        elif ch in pairs:
            if not stack:
                ev.append(("empty", i))
                return False, ev
            top = stack.pop()
            ok = top == pairs[ch]
            ev.append(("pop", i, top, ok))
            if not ok:
                return False, ev
    ev.append(("end", len(stack)))
    return not stack, ev


def is_valid(s):
    return is_valid_trace(s)[0]


def eval_postfix_trace(tokens):
    """讲义 eval_postfix 插桩。事件：("num", k, x) / ("op", k, tk, a, b, r)。"""
    stack, ev = [], []
    for k, tk in enumerate(tokens):
        if tk in ('+', '-', '*', '/'):
            b = stack.pop()          # 先弹出的是右操作数
            a = stack.pop()
            if tk == '+':
                r = a + b
            elif tk == '-':
                r = a - b
            elif tk == '*':
                r = a * b
            else:
                r = a / b
            stack.append(r)
            ev.append(("op", k, tk, a, b, r))
        else:
            stack.append(float(tk))
            ev.append(("num", k, float(tk)))
    return stack[-1], ev


def eval_postfix(tokens):
    return eval_postfix_trace(tokens)[0]


RAIN = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]


def trap_trace(height=RAIN):
    """讲义 trap 插桩。事件：("push", i) / ("pop", bottom, i) / ("noleft", bottom, i) /
    ("water", left, i, bottom, width, depth, 累计)。"""
    stack, water, ev = [], 0, []
    for i, h in enumerate(height):
        while stack and height[stack[-1]] < h:
            bottom = stack.pop()
            if not stack:
                ev.append(("noleft", bottom, i))
                break
            ev.append(("pop", bottom, i))
            left = stack[-1]
            width = i - left - 1
            depth = min(height[left], h) - height[bottom]
            water += width * depth
            ev.append(("water", left, i, bottom, width, depth, water))
        stack.append(i)
        ev.append(("push", i))
    return water, ev


def trap(height=RAIN):
    return trap_trace(height)[0]


def next_greater(a):
    """讲义 1.5 节（原样）。"""
    n = len(a)
    ans = [-1] * n
    stack = []
    for i, v in enumerate(a):
        while stack and a[stack[-1]] < v:
            ans[stack.pop()] = i
        stack.append(i)
    return ans
