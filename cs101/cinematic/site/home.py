"""改写总入口页 home.html 里两门课的片数、总时长、周次范围（读各课 films.json 与 out/ 下的 sidecar.json）。

用法：python cs101/cinematic/site/home.py   → 原地更新 home.html；部署：拷到中转 /srv/anim/index.html
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
COURSES = {"cs101": ROOT / "cs101", "cs201": ROOT / "cs201"}


def stats(course: Path) -> str:
    data = json.loads((course / "cinematic" / "site" / "films.json").read_text(encoding="utf-8"))
    n, total, weeks, special = 0, 0.0, [], False
    for w in data["weeks"]:
        if "label" in w:
            special = True
        else:
            weeks.append(w["week"])
        for f in w["films"]:
            n += 1
            total += json.loads((course / "out" / f["dir"] / "sidecar.json").read_text(encoding="utf-8"))["seconds"]
    s = int(round(total))
    span = f"第 {min(weeks)}–{max(weeks)} 周" + ("与春季专题" if special else "")
    return f"<b>{n}</b> 支 · 总时长 <b>{s // 60}:{s % 60:02d}</b> · {span}"


page = (HERE / "home.html").read_text(encoding="utf-8")
for cid, path in COURSES.items():
    page, k = re.subn(rf'(<span class="stats" data-course="{cid}">).*?(</span>)',
                      lambda m, s=stats(path): m.group(1) + s + m.group(2), page)
    assert k == 1, cid
(HERE / "home.html").write_text(page, encoding="utf-8")
print(re.findall(r'data-course="(\w+)">(.*?)</span>', page))
