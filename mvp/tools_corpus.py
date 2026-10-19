# -*- coding: utf-8 -*-
"""把 OCR 后的教材 PDF 抽成语料纯文本（供 pipeline/corpus.py 检索）。

用法（在 mvp/ 下）：
    python tools_corpus.py --subject chem --map map.json [--src-dir DIR] [--out-dir DIR]

map.json：[{"file": "OCR后的pdf路径（相对 --src-dir 或绝对）", "slug": "英文短名", "title": "书名"}, ...]

每本书输出 <out-dir>/<subject>/<slug>.txt（页与页用「===== 第 N 页 =====」隔开）与 <slug>.meta.json。
没有文字层的 PDF（没做 OCR，或 OCR 失败）不写文件，只在报告里列出；不会产出空语料冒充"已入库"。
依赖 poppler 的 pdftotext，每本 PDF 只调用一次。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent / "pipeline" / "data" / "corpus"
MIN_CHARS_PER_PAGE = 20   # 平均每页有效字符低于此值，视为没有文字层


def extract_pages(pdf: Path) -> list[str]:
    """返回每页文本（pdftotext 以 \\f 分页，末尾多出的空串去掉）。"""
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("找不到 pdftotext（需要 poppler）")
    r = subprocess.run([exe, "-enc", "UTF-8", "-layout", str(pdf), "-"],
                       capture_output=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"pdftotext 失败：{r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def has_text_layer(pages: list[str]) -> bool:
    if not pages:
        return False
    total = sum(len("".join(p.split())) for p in pages)
    return total / len(pages) >= MIN_CHARS_PER_PAGE


def render(pages: list[str]) -> str:
    return "\n".join(f"===== 第 {i} 页 =====\n{p.strip()}\n" for i, p in enumerate(pages, 1))


def convert(pdf: Path, subject: str, slug: str, title: str, out_dir: Path) -> tuple[bool, str]:
    """成功返回 (True, 摘要)；无文字层返回 (False, 原因)。"""
    pages = extract_pages(pdf)
    if not has_text_layer(pages):
        return False, f"无文字层（{len(pages)} 页）——先做 OCR"
    d = out_dir / subject
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.txt").write_text(render(pages), encoding="utf-8")
    (d / f"{slug}.meta.json").write_text(
        json.dumps({"title": title, "pages": len(pages)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return True, f"{len(pages)} 页"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", required=True, help="学科目录名，如 chem / physics / math / bio")
    ap.add_argument("--map", required=True, type=Path, help="文件→slug/书名映射 JSON")
    ap.add_argument("--src-dir", type=Path, default=Path("."))
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    items = json.loads(a.map.read_text(encoding="utf-8"))
    ok = bad = 0
    for it in items:
        pdf = Path(it["file"])
        if not pdf.is_absolute():
            pdf = a.src_dir / pdf
        slug, title = str(it["slug"]), str(it["title"])
        if not pdf.is_file():
            print(f"[缺文件] {pdf}")
            bad += 1
            continue
        try:
            done, msg = convert(pdf, a.subject, slug, title, a.out_dir)
        except RuntimeError as e:
            done, msg = False, str(e)
        print(f"[{'ok' if done else '跳过'}] {slug}《{title}》{msg}")
        ok, bad = ok + done, bad + (not done)
    print(f"完成：{ok} 本入语料，{bad} 本未入")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
