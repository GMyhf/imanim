"""生成系列入口页 index.html：films.json（周次、简介、出处）+ 各片 sidecar.json（标题、时长）。

python build.py               # Artifact 版（发布时外层自动补 HTML 骨架，用 Google Fonts）
python build.py --standalone [--feedback]  # 独立部署版；--feedback 加每支片的反馈栏（需中转上的 feedback_server.py）
python build.py --site ../../../cs201/cinematic/site --standalone   # 别的课程：读该目录的 films.json 与 sidecars/，产物也写在那里
                              # 独立部署版（完整 HTML 骨架、只用系统字体：国内访问不了 Google Fonts），
                              # 部署在 https://infomall.zhengmao.ltd/cs101-anim/（成都中转 /srv/cs101-anim）
"""
import html
import json
import sys
from pathlib import Path

STANDALONE = "--standalone" in sys.argv
FEEDBACK = STANDALONE and "--feedback" in sys.argv     # 反馈栏要求中转上已部署 feedback_server.py

HERE = Path(__file__).parent
if "--site" in sys.argv:
    HERE = Path(sys.argv[sys.argv.index("--site") + 1])
data = json.loads((HERE / "films.json").read_text(encoding="utf-8"))
PAGE = {   # 页面上的课程文字；films.json 的 "page" 可逐项覆盖（缺省是 CS101）
    "title": "CS101 算法动画", "h1": "CS101 <em>算法动画</em>",
    "description": "计算概论（B）2026fall 算法动画短片，按周次排列，可在页面内直接播放。",
    "kicker": "计算概论（B）· 2026 FALL · 知识点短片",
    "lede": "每支两到四分钟，讲透一个知识点。画面里的每一步都由真实程序的执行轨迹驱动，片中数字都经过测试对照讲义原版代码核验。",
    "footer": "素材依据课程仓库 2026fall-cs101 的讲义与旁白稿（P 为课件页码）。页面内为 720p 压缩版，"
              "1080p60 原片在 GitHub Releases <code>cs101-anim-2026fall</code>。",
    **data.get("page", {})}
# 各片 sidecar：缺省直接读课程的 out/ 目录（<课程>/cinematic/site → <课程>/out），sidecars/ 下的拷贝优先（旧用法）
side = {p.parent.name: json.loads(p.read_text(encoding="utf-8"))
        for d in (HERE.resolve().parent.parent / "out", HERE / "sidecars") for p in d.glob("*/sidecar.json")}


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


RATINGS = [("ok", "看懂了"), ("hard", "有点难"), ("fast", "节奏太快"), ("slow", "节奏太慢")]


def feedback(fid):
    """部署版才有的反馈栏：选项按钮（附可选留言）→ POST api/feedback，计数取 api/summary。"""
    btns = "".join(f'<button type="button" data-r="{k}">{v}<b></b></button>' for k, v in RATINGS)
    return f"""
          <div class="fb" data-film="{fid}">
            <div class="fb-row"><span class="fb-q">这支片</span>{btns}</div>
            <details><summary>附一句建议（可选，点上面的按钮时一起提交）</summary>
              <textarea id="c-{fid}" maxlength="500" rows="2" placeholder="哪里没看懂、哪里太快……"></textarea></details>
            <span class="fb-msg" aria-live="polite"></span>
          </div>"""


def wtag(w):
    """周次标签：缺省 W06；春季专题等可在 films.json 里用 "tag" 自定。"""
    return html.escape(w.get("tag", f"W{w['week']:02d}"))


total = 0.0
n_films = 0
sections = []
for w in data["weeks"]:
    cards = []
    for f in w["films"]:
        sc = side[f["dir"]]
        title = sc.get("title", f["title"])
        total += sc["seconds"]
        n_films += 1
        cards.append(f"""
      <article class="film" id="{f['id']}">
        <video controls preload="none" playsinline poster="posters/{f['id']}.jpg" src="videos/{f['id']}.mp4"
               aria-label="{html.escape(title)}"></video>
        <div class="film-body">
          <h3>{html.escape(title)}</h3>
          <p>{html.escape(f['desc'])}</p>
          <div class="meta"><span class="dur">{mmss(sc['seconds'])}</span><span class="src">讲义 {html.escape(f['src'])}</span></div>{feedback(f['id']) if FEEDBACK else ""}
        </div>
      </article>""")
    sections.append(f"""
    <section class="week" id="w{w['week']}">
      <header class="week-head"><span class="wk">{wtag(w)}</span><h2>{html.escape(w.get('label', f"第 {w['week']} 周"))} · {html.escape(w['topic'])}</h2></header>
      <div class="grid">{''.join(cards)}
      </div>
    </section>""")

nav = "".join(f'<a href="#w{w["week"]}">{wtag(w)}<span>{html.escape(w["topic"])}</span></a>' for w in data["weeks"])
FB_SCRIPT = """<script>
(function () {
  var NAMES = {ok: "看懂了", hard: "有点难", fast: "节奏太快", slow: "节奏太慢"};
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function paint(box, counts) {
    box.querySelectorAll("button[data-r]").forEach(function (b) {
      var n = counts && counts[b.dataset.r];
      b.querySelector("b").textContent = n ? n : "";
    });
  }
  var boxes = document.querySelectorAll(".fb");
  fetch("api/summary").then(function (r) { return r.ok ? r.json() : {}; }).then(function (s) {
    boxes.forEach(function (box) { paint(box, s[box.dataset.film]); });
  }).catch(function () {});
  boxes.forEach(function (box) {
    var film = box.dataset.film, msg = box.querySelector(".fb-msg"), voted = load("fb-" + film);
    function lock(r) {
      box.querySelectorAll("button[data-r]").forEach(function (b) {
        b.disabled = true; if (b.dataset.r === r) b.classList.add("picked");
      });
    }
    if (voted) { lock(voted); msg.textContent = "你选了「" + NAMES[voted] + "」，谢谢。"; }
    box.querySelectorAll("button[data-r]").forEach(function (b) {
      b.addEventListener("click", function () {
        var r = b.dataset.r, ta = box.querySelector("textarea");
        msg.textContent = "提交中…";
        fetch("api/feedback", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({film: film, rating: r, comment: ta ? ta.value : ""})})
          .then(function (res) { return res.json().then(function (j) { return {ok: res.ok, j: j}; }); })
          .then(function (x) {
            if (!x.ok) { msg.textContent = x.j.error || "没提交成功，稍后再试。"; return; }
            save("fb-" + film, r); lock(r); paint(box, x.j.summary);
            msg.textContent = "已收到，谢谢！";
          })
          .catch(function () { msg.textContent = "网络不通，没提交成功，稍后再试。"; });
      });
    });
  });
})();
</script>
"""

head = (f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{PAGE['description']}">
<title>{PAGE['title']}</title>
<style>html,body{{margin:0}}</style>
""" if STANDALONE else f"""<title>{PAGE['title']}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400&display=swap">
""")
page = head + f"""<style>
/* 布局：片子的深色画布延伸成页面——按周次分节，每节一列可直接播放的短片卡；周次编号是真实课程顺序 */
:root {{
  --bg: #f4f5f8; --surface: #ffffff; --fg: #1b1e26; --muted: #5d6475; --line: #dde1ea;
  --blue: #1f86a8; --yellow: #a07a00; --accent: #1f86a8;
  --f-display: "Space Grotesk", "Noto Sans SC", system-ui, sans-serif;
  --f-body: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0f1117; --surface: #171a22; --fg: #e6e8ee; --muted: #9aa2b4; --line: #262b36;
  --blue: #58c4dd; --yellow: #f4d345; --accent: #58c4dd; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0f1117; --surface: #171a22; --fg: #e6e8ee; --muted: #9aa2b4; --line: #262b36;
  --blue: #58c4dd; --yellow: #f4d345; --accent: #58c4dd; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-body); font-size: 16px; line-height: 1.65; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-block: 40px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.hero {{ display: grid; gap: 12px; padding-bottom: 28px; border-bottom: 1px solid var(--line); }}
.kicker {{ font-family: var(--f-mono); font-size: 13px; letter-spacing: .06em; color: var(--muted); }}
.kicker a.home {{ color: var(--accent); text-decoration: none; }}
.kicker a.home:hover, .kicker a.home:focus-visible {{ text-decoration: underline; }}
h1 {{ font-family: var(--f-display); font-size: clamp(34px, 6vw, 56px); line-height: 1.1; margin: 0; text-wrap: balance; }}
h1 em {{ font-style: normal; color: var(--yellow); }}
.lede {{ max-width: 62ch; color: var(--muted); margin: 0; }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px 22px; font-family: var(--f-mono); font-size: 13px; color: var(--muted);
  font-variant-numeric: tabular-nums; }}
.stats b {{ color: var(--fg); font-weight: 400; }}
nav.weeks {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 8px; }}
nav.weeks a {{ display: inline-flex; gap: 8px; align-items: baseline; padding: 6px 12px; border: 1px solid var(--line);
  border-radius: 999px; color: var(--fg); text-decoration: none; font-family: var(--f-mono); font-size: 13px; }}
nav.weeks a span {{ font-family: var(--f-body); color: var(--muted); }}
nav.weeks a:hover, nav.weeks a:focus-visible {{ border-color: var(--accent); outline: none; }}
.week {{ padding-top: 36px; }}
.week-head {{ display: flex; align-items: baseline; gap: 14px; margin-bottom: 16px; }}
.wk {{ font-family: var(--f-display); font-weight: 700; font-size: 15px; color: var(--accent); letter-spacing: .04em; }}
.week-head h2 {{ font-size: 20px; margin: 0; font-weight: 700; text-wrap: balance; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 20px; }}
.film {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  display: grid; grid-template-rows: auto 1fr; min-width: 0; }}
.film video {{ width: 100%; aspect-ratio: 16 / 9; display: block; background: #0f1117; max-width: 100%; }}
.film-body {{ padding: 14px 16px 16px; display: grid; gap: 8px; align-content: start; min-width: 0; }}
.film h3 {{ font-size: 17px; margin: 0; line-height: 1.4; }}
.film p {{ margin: 0; font-size: 14px; color: var(--muted); }}
.meta {{ display: flex; flex-wrap: wrap; gap: 6px 14px; font-family: var(--f-mono); font-size: 12px; color: var(--muted);
  font-variant-numeric: tabular-nums; }}
.meta .dur {{ color: var(--yellow); }}
.fb {{ display: grid; gap: 6px; margin-top: 4px; padding-top: 10px; border-top: 1px dashed var(--line); }}
.fb-row {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
.fb-q {{ font-size: 13px; color: var(--muted); margin-right: 2px; }}
.fb button {{ font: inherit; font-size: 13px; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line);
  background: transparent; color: var(--fg); cursor: pointer; display: inline-flex; gap: 6px; align-items: baseline; }}
.fb button b {{ font-weight: 400; font-family: var(--f-mono); font-size: 11px; color: var(--muted); }}
.fb button:hover, .fb button:focus-visible {{ border-color: var(--accent); outline: none; }}
.fb button.picked {{ border-color: var(--yellow); color: var(--yellow); }}
.fb button:disabled {{ cursor: default; }}
.fb details summary {{ font-size: 12px; color: var(--muted); cursor: pointer; }}
.fb textarea {{ width: 100%; margin-top: 6px; font: inherit; font-size: 13px; padding: 6px 8px; border-radius: 6px;
  border: 1px solid var(--line); background: var(--bg); color: var(--fg); resize: vertical; }}
.fb-msg {{ font-size: 12px; color: var(--muted); min-height: 1em; }}
footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px;
  display: grid; gap: 6px; }}
footer code {{ font-family: var(--f-mono); font-size: 12px; }}
footer a {{ color: var(--accent); }}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
html {{ scroll-behavior: smooth; }}
</style>
{"</head>" + chr(10) + "<body>" if STANDALONE else ""}
<div class="wrap">
  <header class="hero">
    <div class="kicker">{'<a class="home" href="../anim/">← 全部系列</a> · ' if STANDALONE else ''}{PAGE['kicker']}</div>
    <h1>{PAGE['h1']}</h1>
    <p class="lede">{PAGE['lede']}</p>
    <div class="stats"><span><b>{n_films}</b> 支短片</span><span>总时长 <b>{mmss(total)}</b></span><span>1080p · 中文配音 · 画面内字幕</span></div>
  </header>
  <nav class="weeks" aria-label="按周次跳转">{nav}</nav>
  {''.join(sections)}
  <footer>
    <span>{PAGE['footer']}</span>
    <span>制作：Manim Community 0.22 渲染，Edge TTS 配音，每支片附对撞测试与自动画面检查。</span>
  </footer>
</div>
""" + ((FB_SCRIPT if FEEDBACK else "") + "</body>\n</html>\n" if STANDALONE else "")
(HERE / ("index.standalone.html" if STANDALONE else "index.html")).write_text(page, encoding="utf-8")
print(n_films, mmss(total))
