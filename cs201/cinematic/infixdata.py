"""中缀转后缀片的数据：讲义 1.4–1.5 节的程序原样搬来（OJ24591 转换、OJ24588 求值），
另写插桩版按讲义「五条规则」逐记号记录栈与输出，画面与旁白里的每个数字都从这里来。

讲义：数据结构与算法（B）2026fall 第 3 周《栈与队列》1.4 表达式求值、1.5 中缀表达式到后缀表达式的转换。
test_infix.py 对撞讲义原版输出、Python eval、OJ 样例与随机表达式。
"""
from __future__ import annotations

import re

BOOK = "23+(34*45)/(5+6+7)"        # 原书例子
SIMPLE = ["3+4*2", "3*4+2"]         # 优先级高的压在上面 / 先到的高优先级先弹
ASSOC = "1-2-3"                     # 「不低于」三个字承重：左结合


# ------------------------------------------------------------------ 讲义原版：OJ24591 中序表达式转后序表达式
def infix_to_postfix(expression):
    precedence = {'+':1, '-':1, '*':2, '/':2}
    stack = []
    postfix = []
    number = ''

    for char in expression:
        if char.isnumeric() or char == '.':
            number += char
        else:
            if number:
                num = float(number)
                postfix.append(int(num) if num.is_integer() else num)
                number = ''
            if char in '+-*/':
                while stack and stack[-1] in '+-*/' and precedence[char] <= precedence[stack[-1]]:
                    postfix.append(stack.pop())
                stack.append(char)
            elif char == '(':
                stack.append(char)
            elif char == ')':
                while stack and stack[-1] != '(':
                    postfix.append(stack.pop())
                stack.pop()

    if number:
        num = float(number)
        postfix.append(int(num) if num.is_integer() else num)

    while stack:
        postfix.append(stack.pop())

    return ' '.join(str(x) for x in postfix)


# ------------------------------------------------------------------ 讲义原版：OJ24588 后序表达式求值
def evaluate_postfix(expression):
    stack = []
    tokens = expression.split()

    for token in tokens:
        if token in '+-*/':
            # 弹出栈顶的两个元素
            right_operand = stack.pop()
            left_operand = stack.pop()
            # 执行运算
            if token == '+':
                stack.append(left_operand + right_operand)
            elif token == '-':
                stack.append(left_operand - right_operand)
            elif token == '*':
                stack.append(left_operand * right_operand)
            elif token == '/':
                stack.append(left_operand / right_operand)
        else:
            # 将操作数转换为浮点数后入栈
            stack.append(float(token))

    # 栈顶元素就是表达式的结果
    return stack[0]


# ------------------------------------------------------------------ 插桩版
PREC = {'+': 1, '-': 1, '*': 2, '/': 2}


def tokenize(s):
    return [t for t in re.split(r'([()+\-*/])', s.replace(" ", "")) if t]


def convert_trace(expr, strict=False):
    """按五条规则逐记号转换，返回 (tokens, 后缀记号列表, 事件)。

    事件：("out", k, tok) 操作数直接输出；("lpar", k) 左括号入栈；("pop", k, op) 弹出并输出；
    ("drop", k) 弹掉左括号不输出；("push", k, op) 运算符入栈；("end",) 扫描结束开始清栈。
    strict=True 是写错的版本：只有栈顶优先级「高于」当前才弹（同级不弹，变成右结合）。
    """
    toks = tokenize(expr)
    stack, out, ev = [], [], []
    for k, t in enumerate(toks):
        if t == '(':
            stack.append(t)
            ev.append(("lpar", k))
        elif t == ')':
            while stack[-1] != '(':
                op = stack.pop()
                out.append(op)
                ev.append(("pop", k, op))
            stack.pop()
            ev.append(("drop", k))
        elif t in PREC:
            while stack and stack[-1] != '(' and (PREC[stack[-1]] > PREC[t] if strict else PREC[stack[-1]] >= PREC[t]):
                op = stack.pop()
                out.append(op)
                ev.append(("pop", k, op))
            stack.append(t)
            ev.append(("push", k, t))
        else:
            out.append(t)
            ev.append(("out", k, t))
    ev.append(("end",))
    while stack:
        op = stack.pop()
        out.append(op)
        ev.append(("pop", len(toks), op))
    return toks, out, ev


def eval_trace(post):
    """后缀求值：事件 ("num", k, x) 压栈；("op", k, tok, a, b, r) 先弹 b（右）再弹 a（左），压回 r。"""
    st, ev = [], []
    for k, t in enumerate(post):
        if t in PREC:
            b = st.pop()
            a = st.pop()
            r = {'+': a + b, '-': a - b, '*': a * b, '/': a / b}[t]
            st.append(r)
            ev.append(("op", k, t, a, b, r))
        else:
            x = float(t)
            st.append(x)
            ev.append(("num", k, x))
    return st[0], ev


if __name__ == "__main__":
    for e in [BOOK, *SIMPLE, ASSOC]:
        toks, out, ev = convert_trace(e)
        print(e, "→", " ".join(out), "|", infix_to_postfix(e), "=", eval_trace(out)[0])
    print("strict:", " ".join(convert_trace(ASSOC, strict=True)[1]), eval_trace(convert_trace(ASSOC, True)[1])[0])
    print(eval_trace(convert_trace(BOOK)[1])[1])
