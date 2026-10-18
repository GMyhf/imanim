# -*- coding: utf-8 -*-
"""一次性/可重跑脚本：回收 flow v2 各棒 system prompt 到 flow/prompts/。

来源两类（Spec_AgentFlow_v2.md 第 11 节沉淀清单口径：从验证过的审计件回收，不是重写）：
  1. K1/K2 —— 已验证的网关审计件原样复制：
     K1: mvp/out/periodic_trial/reports/K1_gw_prompt_system.md
         （缺失时回退 mvp/out/substitution_trial/reports/K1_gw_prompt_system.md）
     K2: mvp/out/peisu_trial/reports/K2_gw_prompt_system.md
  2. V0/M1/M2/P/A8/S22 —— Spec_AgentFlow_v2.md 第 8 节对应围栏块**程序化抽取**（不手抄）。

用法（cwd 任意）：python mvp/pipeline/flow/tools_extract_prompts.py
Spec 更新后重跑即可刷新 prompts/（K1/K2 只在源审计件更新时变化）。
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # D:\Dev\Project1
SPEC = ROOT / "Projrct_Plan" / "Spec_AgentFlow_v2.md"
PROMPTS = Path(__file__).resolve().parent / "prompts"

# 各棒在 Spec 第 8 节的节标题（正则），抽取标题后的第一个 ``` 围栏块正文
SPEC_HEADERS = {
    "P": r"### P · 图像解读[^\n]*\n",
    "V0": r"### V0 · 视觉编剧[^\n]*\n",
    "M1": r"### M1 · 物理建模[^\n]*\n",
    "M2": r"### M2 · 场景代码[^\n]*\n",
    "A8": r"### A8' · 动态视觉回审[^\n]*\n",
    "S22": r"### S22 · 独立评分[^\n]*\n",
}

# K1/K2 从已验证审计件原样复制（主源, 回退源）
AUDIT_SOURCES = {
    "K1": [ROOT / "mvp/out/periodic_trial/reports/K1_gw_prompt_system.md",
           ROOT / "mvp/out/substitution_trial/reports/K1_gw_prompt_system.md"],
    "K2": [ROOT / "mvp/out/peisu_trial/reports/K2_gw_prompt_system.md"],
}


def fence_after(spec_text: str, header_pat: str, fence: str = "```") -> str:
    """抽取某节标题后的第一个围栏块正文（与 .local/complex_trial/gateway.py 同法）。"""
    m = re.search(header_pat, spec_text)
    if not m:
        raise SystemExit(f"Spec 中找不到节标题 {header_pat}")
    rest = spec_text[m.end():]
    a = rest.find(fence)
    b = rest.find("\n```", a + len(fence))
    if a == -1 or b == -1:
        raise SystemExit(f"{header_pat} 节后找不到围栏块")
    return rest[rest.find("\n", a) + 1:b].strip() + "\n"


def main() -> int:
    PROMPTS.mkdir(parents=True, exist_ok=True)
    spec_text = SPEC.read_text(encoding="utf-8")
    for name, pat in SPEC_HEADERS.items():
        out = PROMPTS / f"{name}_SYSTEM.md"
        out.write_text(fence_after(spec_text, pat), encoding="utf-8")
        print(f"抽取 {name} <- Spec 第 8 节围栏块 -> {out}")
    for name, sources in AUDIT_SOURCES.items():
        src = next((p for p in sources if p.exists()), None)
        if src is None:
            print(f"警告：{name} 审计件全部缺失（{[str(p) for p in sources]}），跳过", file=sys.stderr)
            continue
        out = PROMPTS / f"{name}_SYSTEM.md"
        shutil.copyfile(src, out)
        print(f"复制 {name} <- {src} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
