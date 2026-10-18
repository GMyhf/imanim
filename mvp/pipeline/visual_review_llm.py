"""A8 成片回审的 VLM 部分：看接触表，只报告视觉缺陷，不改内容、不评科学性。

确定性部分（selfcheck.scan_boundaries）照旧；这里是它之外的增强。模型不可用时返回 verdict=unavailable，
不拦出片也不冒充 pass。
"""

from __future__ import annotations

from pathlib import Path

from . import llm_client, llm_prompts

CODES = {"G3_CLIP", "G3_SMALL", "BLANK", "STATIC", "OVERLAP", "GLYPH", "AXIS"}


def review(contact_png: Path) -> dict:
    png = Path(contact_png)
    labels_file = png.with_suffix(".txt")
    labels = labels_file.read_text(encoding="utf-8") if labels_file.exists() else "（无标签文件，按从左到右、从上到下，每镜 头/尾 两格）"
    user = "接触表每格的标签（从左到右、从上到下）：\n" + labels
    model = llm_client.model_for("A8")
    try:
        got = llm_client.extract_json(llm_client.chat("A8", llm_prompts.A8_SYSTEM, user, [png], max_tokens=4000))
    except llm_client.LLMError as e:
        return {"verdict": "unavailable", "issues": [], "summary": str(e), "model": model}
    if not isinstance(got, dict):
        return {"verdict": "unavailable", "issues": [], "summary": "模型输出不是对象", "model": model}
    issues = [i for i in (got.get("issues") or [])
              if isinstance(i, dict) and i.get("code") in CODES and isinstance(i.get("shot"), int)]
    return {"verdict": "fail" if issues else "pass", "issues": issues,
            "summary": str(got.get("summary") or ""), "model": model}
