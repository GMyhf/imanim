"""配音校对：用 Whisper 把每段配音转写回文字，和旁白稿按拼音逐段比对，标出漏读、断流与念错。

用法（Mac Studio，仓库根；需要 mlx-whisper、pypinyin、cn2an）：
  python cs101/cinematic/asr_check.py                 # 所有已出片的 lesson
  python cs101/cinematic/asr_check.py fib hanoi       # 指定 lesson
  python cs101/cinematic/asr_check.py --course cs201 kmp   # 别的课程（读 cs201/cinematic/make.py 的片目）

比对口径：两边先用 cn2an 把中文数字统一成阿拉伯数字（「一八八三」「六十四」写法不同不算错），
再把汉字转成不带声调的拼音、英文转小写，按「音节/单词」序列做 difflib 比对——同音不同字不算错，
念错的字（多音字念错、英文读错）、漏读、断流才会出现在差异里。转写结果缓存在各片 audio/ 下。
结果写 <课程>/out/<前缀><id>/asr.json。只报三类值得复听的差异：漏读/断流（连续 ≥3 个音节没听到，或整段听到的
不足八成）、读音不符（两边都是汉字且 ≥2 个音节对不上）、英文词被听成中文；纯数字/纯英文拼写差异（「1 1」听成「11」、
lo 写成 low）不报。
注意 Whisper 本身也会听错，报告是「值得复听的位置」，不是定论。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
MODEL = "mlx-community/whisper-large-v3-turbo"

sys.path.insert(0, str(HERE))
from make import LESSONS, PREFIX, speakable  # noqa: E402

if len(sys.argv) > 2 and sys.argv[1] == "--course":     # 别的课程：读那门课的 make.py 拿片目、目录与前缀
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        f"{sys.argv[2]}_make", HERE.parent.parent / sys.argv[2] / "cinematic" / "make.py")
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    HERE, OUT, LESSONS, PREFIX = _m.HERE, _m.OUT, _m.LESSONS, _m.PREFIX
    del sys.argv[1:3]


def tokens(text: str) -> list[str]:
    import cn2an
    from pypinyin import lazy_pinyin
    try:
        text = cn2an.transform(text, "cn2an")
    except Exception:  # noqa: BLE001 cn2an 遇到怪格式会抛，退回原文
        pass
    out = []
    for m in re.finditer(r"[一-鿿]|[A-Za-z]+|\d+(?:\.\d+)?", text):
        s = m.group(0)
        out.append("·" + lazy_pinyin(s)[0] if "\u4e00" <= s[0] <= "\u9fff" else s.lower())   # 拼音带前缀 ·，与英文单词区分
    return out


def _cjk(t: str) -> bool:
    return t.startswith("·")


def classify(op: str, r: list[str], h: list[str]) -> str | None:
    """差异段归类；纯数字/纯英文拼写差异（连读合并、low/lo 之类）返回 None 不报。"""
    r_cjk = [t for t in r if _cjk(t)]
    h_cjk = [t for t in h if _cjk(t)]
    if op == "delete" and len(r) >= 3:
        return "漏读/断流"
    if r and not r_cjk and h and len(h_cjk) == len(h) and any(t.isalpha() for t in r):
        return "英文词被听成中文"
    if len(r_cjk) >= 2 and len(h_cjk) >= 2 and r_cjk != h_cjk:
        return "读音不符"
    return None


def transcribe(wav: Path) -> str:
    cache = wav.with_name(wav.stem + f".asr-{hashlib.sha1(MODEL.encode()).hexdigest()[:6]}.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["text"]
    import mlx_whisper
    r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=MODEL, language="zh", condition_on_previous_text=False)
    text = r["text"].strip()
    cache.write_text(json.dumps({"model": MODEL, "text": text}, ensure_ascii=False), encoding="utf-8")
    return text


def check(lesson: str) -> dict:
    script = json.loads((HERE / LESSONS[lesson][0]).read_text(encoding="utf-8"))
    out = OUT / f"{PREFIX}{lesson}"
    timing = {t["id"]: t for t in json.loads((out / "timing.json").read_text(encoding="utf-8"))}
    beats = []
    for b in script["beats"]:
        heard = transcribe(out / timing[b["id"]]["wav"])
        ref, hyp = tokens(speakable(b["narration"])), tokens(heard)   # 对照送 TTS 的文本（读音词典之后）
        sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
        diffs = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            r, h = ref[i1:i2], hyp[j1:j2]
            kind = classify(op, r, h)
            if kind:
                diffs.append({"kind": kind, "稿": " ".join(r).replace("·", ""), "听": " ".join(h).replace("·", "")})
        ratio = round(sm.ratio(), 3)
        if len(hyp) < 0.8 * len(ref):
            diffs.append({"kind": "漏读/断流", "稿": f"{len(ref)} 个音节", "听": f"只听到 {len(hyp)} 个"})
        beats.append({"id": b["id"], "ratio": ratio, "narration": b["narration"], "heard": heard,
                      "diffs": diffs, "flag": bool(diffs)})
    rep = {"lesson": lesson, "model": MODEL, "beats": beats,
           "flagged": [b["id"] for b in beats if b["flag"]], "min_ratio": min(b["ratio"] for b in beats)}
    (out / "asr.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


def main() -> int:
    names = sys.argv[1:] or [k for k in LESSONS if (OUT / f"{PREFIX}{k}" / "timing.json").exists()]
    for name in names:
        rep = check(name)
        print(f"== {name}  最低相似度 {rep['min_ratio']:.3f}  待复听 {len(rep['flagged'])} 段")
        for b in rep["beats"]:
            if not b["flag"]:
                continue
            print(f"  [{b['id']}] {b['ratio']:.3f}")
            for d in b["diffs"]:
                print(f"     {d['kind']}  稿: {d['稿'] or '∅'}  |  听: {d['听'] or '∅'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
