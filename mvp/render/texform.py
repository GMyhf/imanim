# -*- coding: utf-8 -*-
"""82-F1：公式文本 → LaTeX 的纯函数层（scene.py 的 LaTeX 通道唯一入口）。

从 .local/82F_probe/convert.py 移植（该原型已通过全部用例、并出过实拍样片）。只服务
公式卡片与推导行，不碰正文标签/字幕（正文仍走 scene.rich()/T()）。

口径（与实拍结论一致，改这里等于改全片公式样式）：
  · 中文在数学态用 ``\\text{...}``（xeCJK 下正常字号）；
  · 上下标里的中文必须写成 ``\\hbox{\\fontsize{0.5em}{0.6em}\\selectfont 停}``——直接
    ``_{\\text{停}}`` 的汉字按全字号落在基线上，既不缩小也不下沉（0.5em 是 0.4/0.5/0.6/
    7pt/6pt 实拍对比后的选型，见 .local/82F_probe/out_hd/images/sub_visual/）；
  · 命令映射一律带尾随空格（math 模式忽略空格），Δv 不会被拼成 ``\\Deltav``；
  · 数字分数 ``1/2`` → ``\\tfrac{1}{2}``；``a/b`` 保持斜杠语义（变量除式）；
  · Unicode 上下标（₀…₉、⁺⁻、ₐₑ…）转真上下标；
  · 中文相邻的空格转 ``\\ ``（math 模式吞空格，否则「速度 v」会粘成「速度v」）。
"""
from __future__ import annotations

import re

_CJK = r"\u4e00-\u9fff\u3400-\u4dbf"
# 命令映射一律带尾随空格：math 模式忽略空格，同时终止命令名（Δv 不能拼成 \Deltav）
_MAP = {
    "×": r"\times ", "÷": r"\div ", "·": r"\cdot ", "−": "-", "–": "-", "—": "-",
    "≤": r"\leq ", "≥": r"\geq ", "≠": r"\neq ", "≈": r"\approx ", "±": r"\pm ",
    "→": r"\to ", "⇒": r"\Rightarrow ", "⇌": r"\rightleftharpoons ",
    "∞": r"\infty ", "°": r"^\circ ", "√": r"\surd ", "∝": r"\propto ",
    "℃": r"^\circ\text{C}", "%": r"\%", "&": r"\&", "#": r"\#", "$": r"\$",
    "Δ": r"\Delta ", "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ", "θ": r"\theta ",
    "λ": r"\lambda ", "μ": r"\mu ", "π": r"\pi ", "ρ": r"\rho ", "σ": r"\sigma ",
    "τ": r"\tau ", "φ": r"\varphi ", "ω": r"\omega ", "Ω": r"\Omega ", "ε": r"\varepsilon ",
}
_SUB = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7",
        "₈": "8", "₉": "9", "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
        "ₐ": "a", "ₑ": "e", "ₔ": "e", "ₕ": "h", "ᵢ": "i", "ⱼ": "j", "ₖ": "k", "ₗ": "l",
        "ₘ": "m", "ₙ": "n", "ₚ": "p", "ₛ": "s", "ₜ": "t", "ᵤ": "u", "ᵥ": "v", "ₓ": "x"}
_SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
        "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")", "ⁿ": "n",
        "ⁱ": "i"}
_SUB_SET, _SUP_SET = set(_SUB), set(_SUP)
_CMD = re.compile(r"\[A-Za-z]+|\.")

# 上下标内的中文：0.5em 字号 + 显式 hbox，既缩小又随下标下沉（见模块 docstring）。
_SUB_WRAP = r"\hbox{\fontsize{0.5em}{0.6em}\selectfont %s}"


def _brace_end(s: str, i: int) -> int:
    """s[i]=='{'，返回匹配的 '}' 下标；不匹配则返回 -1。"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _cjk(text: str, in_script: bool) -> str:
    # xeCJK 在数学下标里不认 \text 的字号：直接 \text{停} 会按全字号落在基线上。
    # 显式 \hbox+\fontsize 才既缩小又随下标下沉（实拍见 .local/82F_probe/sub_visual.py）。
    return (_SUB_WRAP % text) if in_script else (r"\text{" + text + "}")


def _convert_plain(s: str, *, keep_commands: bool = False, in_script: bool = False) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in "_^":
            k, i = c, i + 1
            if i < len(s) and s[i] == "{":
                j = _brace_end(s, i)
                if j < 0:
                    out.append(k + "{")
                    continue
                payload, i = s[i + 1:j], j + 1
            elif i < len(s):
                payload, i = s[i], i + 1
            else:
                out.append(r"\_" if c == "_" else r"\^")
                continue
            out.append(k + "{" + _convert_plain(payload, keep_commands=keep_commands,
                                                in_script=True) + "}")
            continue
        if c in _SUB_SET or c in _SUP_SET:
            is_sub = c in _SUB_SET
            table = _SUB if is_sub else _SUP
            j = i
            while j < len(s) and s[j] in table:
                j += 1
            out.append(("_" if is_sub else "^") + "{" + "".join(table[x] for x in s[i:j]) + "}")
            i = j
            continue
        if c == " ":
            left_cjk = i > 0 and re.match("[" + _CJK + "]", s[i - 1])
            right_cjk = i + 1 < len(s) and re.match("[" + _CJK + "]", s[i + 1])
            out.append(r"\ " if (left_cjk or right_cjk) else " ")
            i += 1
            continue
        if re.match("[" + _CJK + "]", c):
            j = i
            while j < len(s) and re.match("[" + _CJK + "]", s[j]):
                j += 1
            out.append(_cjk(s[i:j], in_script))
            i = j
            continue
        if s.startswith(("\\text", "\\mathrm"), i):
            cmd = "\\text" if s.startswith("\\text", i) else "\\mathrm"
            j = i + len(cmd)
            if j < len(s) and s[j] == "{":
                k = _brace_end(s, j)
                if k > 0:
                    body = s[j + 1:k]
                    out.append(_cjk(body, in_script) if in_script and cmd == "\\text"
                               else cmd + "{" + body + "}")
                    i = k + 1
                    continue
        m = _CMD.match(s, i) if keep_commands else None
        if m:
            out.append(m.group())
            i = m.end()
            continue
        out.append(_MAP.get(c, c))
        i += 1
    return "".join(out)


def to_latex(text: str, *, keep_commands: bool = False) -> str:
    """公式文本 → LaTeX 片段（不含外层 $）。空串返回 ``\\,``（占位，不让 MathTex 空参数崩）。"""
    s = str(text or "").strip()
    if not s:
        return r"\," 
    if not keep_commands:
        # 简单数字分数 1/2 → \tfrac{1}{2}；变量 a/b 保持斜杠语义
        s = re.sub(r"(?<![\w\)\]}])(\d+)/(\d+)(?![\w\(\[\{])",
                   lambda m: r"\tfrac{" + m.group(1) + "}{" + m.group(2) + "}", s)
    return _convert_plain(s, keep_commands=keep_commands)


_SUB_CHARS = "".join(_SUB)
_SUP_CHARS = "".join(_SUP)
_TOKEN_RE = re.compile(
    r"[A-Za-zΑ-ωΔ](?:[" + _SUB_CHARS + r"]+|[" + _SUP_CHARS + r"]+)+"
    r"|[A-Za-zΑ-ωΔ](?:[_\^](?:\{[^{}]*\}|[0-9]+(?:\.[0-9]+)?|[" + _CJK + r"A-Za-z]+))?"
    r"(?:[_\^](?:\{[^{}]*\}|[0-9]+(?:\.[0-9]+)?|[" + _CJK + r"A-Za-z]+))?"
    r"|\d+/\d+"
    r"|\d+(?:\.\d+)?(?:[_\^](?:\{[^{}]*\}|[0-9]+(?:\.[0-9]+)?|[" + _CJK + r"A-Za-z]+))?"
    r"|[" + _CJK + r"]+"
    r"|[^\sA-Za-z0-9]"
)


def tokens(text: str) -> list[str]:
    """字母级切分（CJK 词与数字保持整段），与 scene._v_derivation 的 tok_re 同口径。"""
    return [t for t in _TOKEN_RE.findall(str(text or "")) if t.strip()]


def tokens_latex(text: str) -> list[str]:
    """切分并逐 token 转 LaTeX：MathTex(*tokens_latex(line)) 的输入。"""
    return [to_latex(t) for t in tokens(text)]
