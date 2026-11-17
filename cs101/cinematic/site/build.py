"""生成系列入口页 index.html：films.json（周次、简介、出处、章节标签、讲义链接）+ 各片 sidecar.json（标题、时长、
各段起点）+ 旁白稿 <课程>/cinematic/<id>.json（文字稿）+ 可选的 site/quiz.json（看完测一测）。

每支片卡：章节按钮（sidecar 的 beats 起点，标签取 films.json 的 "chapters"，缺省用 beat id）、讲义链接（"href"）、
可折叠旁白文字稿、小测（quiz.json：{"<id>": [{"q", "options", "answer", "explain"}]}，没有就不显示）、复制链接。
页面级：关键词搜索（标题、简介、文字稿）、看过标记（看到 80% 记一次，存浏览器 localStorage 键
anim-watched-<课程>，总入口 home.html 读同一个键）、#<id> 深链接高亮。

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
COURSE = HERE.resolve().parent.parent.name          # cs101 / cs201：localStorage 键名用
CINE = HERE.resolve().parent                        # 旁白稿 <id>.json 所在目录
QUIZ = json.loads((HERE / "quiz.json").read_text(encoding="utf-8")) if (HERE / "quiz.json").exists() else {}
esc = html.escape


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


def chapters(f, sc):
    """章节按钮：sidecar 的 beats 是各段在成片里的起点（秒）。"""
    labels = f.get("chapters", {})
    return [(bid, labels.get(bid, bid), t) for bid, t in sc["beats"].items()]


def chapter_nav(chs):
    btns = "".join(f'<button type="button" data-t="{t:.2f}"><span class="t">{mmss(t)}</span>{esc(lab)}</button>'
                   for _, lab, t in chs)
    return f'\n        <div class="chap" role="group" aria-label="章节">{btns}</div>'


def srt_cues(fdir):
    """各片 subs.srt（句级字幕，时间轴与成片一致）→ [(起, 止, 句子)]；没有就返回空表。"""
    for d in (HERE.resolve().parent.parent / "out", HERE / "sidecars"):
        p = d / fdir / "subs.srt"
        if p.exists():
            cues = []
            for blk in p.read_text(encoding="utf-8").strip().split("\n\n"):
                ln = blk.strip().splitlines()
                if len(ln) >= 3 and "-->" in ln[1]:
                    a, b = (sum(float(x) * m for x, m in zip(t.strip().replace(",", ".").split(":"), (3600, 60, 1)))
                            for t in ln[1].split("-->"))
                    cues.append((a, b, " ".join(ln[2:])))
            return cues
    return []


def transcript(f, chs):
    """旁白文字稿：按 beat 分段，段首是可点的章节标签；有 subs.srt 时逐句带时间，播放时高亮当前句、点句子跳过去。
    旁白稿缺失就不出。"""
    p = CINE / f"{f['id']}.json"
    if not p.exists():
        return ""
    narr = {b["id"]: b["narration"] for b in json.loads(p.read_text(encoding="utf-8"))["beats"]}
    cues = srt_cues(f["dir"])
    starts = [t for _, _, t in chs] + [float("inf")]
    paras = []
    for k, (bid, lab, t) in enumerate(chs):
        if not narr.get(bid):
            continue
        mine = [c for c in cues if starts[k] - 0.3 <= c[0] < starts[k + 1] - 0.3]
        body = ("".join(f'<span class="s" data-t="{a:.2f}" data-e="{b:.2f}">{esc(x)}</span>' for a, b, x in mine)
                if mine else esc(narr[bid]))
        paras.append(f'<p><button type="button" class="ts-ch" data-t="{t:.2f}">{esc(lab)} · {mmss(t)}</button>{body}</p>')
    return f'\n          <details class="ts"><summary>旁白文字稿</summary><div class="ts-body">{"".join(paras)}</div></details>'


RATES = ["0.75", "1", "1.25", "1.5", "2"]


def rate_select():
    opts = "".join(f'<option value="{r}"{" selected" if r == "1" else ""}>{r}×</option>' for r in RATES)
    return f'<label class="rate" title="播放速度"><span>倍速</span><select aria-label="播放速度">{opts}</select></label>'


def quiz(fid):
    qs = QUIZ.get(fid) or []
    if not qs:
        return ""
    items = []
    for i, q in enumerate(qs):
        opts = "".join(f'<button type="button" data-k="{k}"><b>{"ABCDEFGH"[k]}</b>{esc(str(o))}</button>'
                       for k, o in enumerate(q["options"]))
        items.append(f'<li class="qz" data-i="{i}" data-a="{int(q["answer"])}"><p class="qz-q">{esc(q["q"])}</p>'
                     f'<div class="qz-opts">{opts}</div><p class="qz-ex" hidden>{esc(q.get("explain", ""))}</p></li>')
    return (f'\n          <details class="quiz"><summary>看完测一测 · {len(qs)} 题</summary>'
            f'<ol>{"".join(items)}</ol><p class="qz-score" aria-live="polite"></p></details>')


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
        chs = chapters(f, sc)
        src = (f'<a class="src" href="{esc(f["href"])}" target="_blank" rel="noopener">讲义 {esc(f["src"])}</a>'
               if f.get("href") else f'<span class="src">讲义 {esc(f["src"])}</span>')
        cards.append(f"""
      <article class="film" id="{f['id']}">
        <video controls preload="none" playsinline poster="posters/{f['id']}.jpg" src="videos/{f['id']}.mp4"
               aria-label="{esc(title)}"></video>{chapter_nav(chs)}
        <div class="film-body">
          <h3><span class="seen" title="已看过" aria-label="已看过">✓</span>{esc(title)}</h3>
          <p class="desc">{esc(f['desc'])}</p>
          <div class="meta"><span class="dur">{mmss(sc['seconds'])}</span>{src}{rate_select()}<button type="button" class="copy">复制链接</button></div>{transcript(f, chs)}{quiz(f['id'])}{feedback(f['id']) if FEEDBACK else ""}
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

# 页面交互（两种版本都带）：章节跳转与高亮、看过标记、搜索、深链接、复制链接、小测判分（部署版另把结果 POST 到 api/quiz）
PAGE_SCRIPT = """<script>
(function () {
  var COURSE = "__COURSE__", POST_QUIZ = __POST__, KEY = "anim-watched-" + COURSE;
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  var films = Array.prototype.slice.call(document.querySelectorAll("article.film"));

  // 看过标记：看到 80% 或播完记一次
  var seen = {};
  try { (JSON.parse(load(KEY) || "[]") || []).forEach(function (id) { seen[id] = 1; }); } catch (e) {}
  var seenN = document.querySelector(".seen-n");
  function paintSeen() {
    var n = 0;
    films.forEach(function (a) { var s = !!seen[a.id]; a.classList.toggle("watched", s); if (s) n++; });
    if (seenN && n) { seenN.hidden = false; seenN.querySelector("b").textContent = n; }
  }
  function markSeen(id) {
    if (seen[id]) return;
    seen[id] = 1; save(KEY, JSON.stringify(Object.keys(seen))); paintSeen();
  }
  paintSeen();

  // 倍速：所有片共用，存在 localStorage anim-rate；video.load() 会把 playbackRate 复位，所以连 defaultPlaybackRate 一起设
  var RATE_KEY = "anim-rate";
  function setRate(r) {
    var x = parseFloat(r) || 1;
    films.forEach(function (a) {
      var v = a.querySelector("video"), s = a.querySelector(".rate select");
      v.defaultPlaybackRate = x; v.playbackRate = x; if (s) s.value = String(r);
    });
  }
  (function () { var r = load(RATE_KEY); if (r && r !== "1") setRate(r); })();

  // 章节：点了跳过去并播放；播放时高亮当前章节
  function seek(v, t) {
    function go() { v.currentTime = t; var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    if (v.readyState >= 1) go();
    else { v.addEventListener("loadedmetadata", go, {once: true}); v.preload = "metadata"; v.load(); }
  }
  films.forEach(function (a) {
    var v = a.querySelector("video"), btns = a.querySelectorAll(".chap button");
    a.querySelectorAll("[data-t]").forEach(function (b) {
      b.addEventListener("click", function () {
        seek(v, parseFloat(b.dataset.t));
        if (b.classList.contains("ts-ch")) v.scrollIntoView({block: "nearest"});
      });
    });
    v.addEventListener("timeupdate", function () {
      var cur = -1;
      btns.forEach(function (b, i) { if (v.currentTime + 0.05 >= parseFloat(b.dataset.t)) cur = i; });
      btns.forEach(function (b, i) { b.classList.toggle("on", i === cur); });
      if (v.duration && v.currentTime / v.duration >= 0.8) markSeen(a.id);
    });
    v.addEventListener("ended", function () { markSeen(a.id); });

    // 文字稿逐句：播放时高亮当前句（文字稿展开时把它滚到可见处）；点句子跳过去由上面的 [data-t] 统一处理
    var sents = Array.prototype.slice.call(a.querySelectorAll(".ts-body .s")), tsb = a.querySelector(".ts-body"),
        ts = a.querySelector("details.ts"), curS = null;
    if (sents.length) v.addEventListener("timeupdate", function () {
      var t = v.currentTime, hit = null;
      for (var i = 0; i < sents.length; i++) {
        if (t + 0.05 >= parseFloat(sents[i].dataset.t)) hit = sents[i]; else break;
      }
      if (hit && t > parseFloat(hit.dataset.e) + 1.5) hit = null;      // 句间停顿较长时不高亮
      if (hit === curS) return;
      if (curS) curS.classList.remove("on");
      curS = hit;
      if (hit) {
        hit.classList.add("on");
        if (ts && ts.open) {
          var top = hit.offsetTop - tsb.offsetTop;
          if (top < tsb.scrollTop || top > tsb.scrollTop + tsb.clientHeight - 40) tsb.scrollTop = Math.max(0, top - 60);
        }
      }
    });

    // 倍速：所有片共用一个选择，记在本机
    var sel = a.querySelector(".rate select");
    if (sel) sel.addEventListener("change", function () { setRate(sel.value); save(RATE_KEY, sel.value); });

    // 复制链接
    var cp = a.querySelector("button.copy");
    if (cp) cp.addEventListener("click", function () {
      var url = location.href.split("#")[0] + "#" + a.id;
      function ok() { cp.textContent = "已复制"; setTimeout(function () { cp.textContent = "复制链接"; }, 1500); }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(ok, function () { window.prompt("复制这个链接", url); });
      else window.prompt("复制这个链接", url);
    });

    // 小测：单选，选后立即判分；答过的记在本机，刷新后仍显示，也不重复提交
    var qz = a.querySelectorAll(".qz"), score = a.querySelector(".qz-score");
    function paintScore() {
      if (!score) return;
      var done = 0, right = 0;
      qz.forEach(function (li) { if (li.dataset.got !== undefined) { done++; if (li.dataset.got === li.dataset.a) right++; } });
      score.textContent = done === qz.length ? "答对 " + right + " / " + qz.length + (right === qz.length ? "，全对！" : "，看看解析，或回到相关章节再看一遍。") : "";
    }
    function answer(li, k, post) {
      li.dataset.got = k;
      li.querySelectorAll("button").forEach(function (b) {
        b.disabled = true;
        if (b.dataset.k === li.dataset.a) b.classList.add("right");
        else if (b.dataset.k === k) b.classList.add("wrong");
      });
      li.querySelector(".qz-ex").hidden = false;
      paintScore();
      if (post && POST_QUIZ) fetch("api/quiz", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({film: a.id, q: parseInt(li.dataset.i, 10), ok: k === li.dataset.a})}).catch(function () {});
    }
    qz.forEach(function (li) {
      var qk = "quiz-" + COURSE + "-" + a.id + "-" + li.dataset.i, prev = load(qk);
      if (prev !== null) answer(li, prev, false);
      li.querySelectorAll("button").forEach(function (b) {
        b.addEventListener("click", function () { save(qk, b.dataset.k); answer(li, b.dataset.k, true); });
      });
    });
  });

  // 搜索：标题、简介、讲义出处、文字稿
  var box = document.querySelector(".search input"), msg = document.querySelector(".search-n");
  var hay = films.map(function (a) {
    return Array.prototype.map.call(a.querySelectorAll("h3, .desc, .src, .ts-body"), function (e) { return e.textContent; })
      .join(" ").toLowerCase();
  });
  if (box) box.addEventListener("input", function () {
    var words = box.value.toLowerCase().split(/\\s+/).filter(Boolean), n = 0;
    films.forEach(function (a, i) {
      var hit = words.every(function (w) { return hay[i].indexOf(w) >= 0; });
      a.hidden = !hit; if (hit) n++;
    });
    document.querySelectorAll("section.week").forEach(function (s) {
      s.hidden = !s.querySelector("article.film:not([hidden])");
    });
    msg.textContent = words.length ? (n ? "找到 " + n + " 支" : "没有找到，换个词试试") : "";
  });

  // 深链接：#<片子 id> 滚过去并闪一下
  function flash() {
    var id = decodeURIComponent(location.hash.slice(1)), a = id && document.getElementById(id);
    if (!a || !a.classList.contains("film")) return;
    if (a.hidden && box) { box.value = ""; box.dispatchEvent(new Event("input")); }
    a.scrollIntoView({block: "start"});
    a.classList.remove("flash"); void a.offsetWidth; a.classList.add("flash");
  }
  window.addEventListener("hashchange", flash);
  if (location.hash) setTimeout(flash, 50);
})();
</script>
""".replace("__COURSE__", COURSE).replace("__POST__", "true" if FEEDBACK else "false")

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
  --blue: #1f86a8; --yellow: #a07a00; --accent: #1f86a8; --green: #1d7a46; --red: #b3261e;
  --f-display: "Space Grotesk", "Noto Sans SC", system-ui, sans-serif;
  --f-body: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0f1117; --surface: #171a22; --fg: #e6e8ee; --muted: #9aa2b4; --line: #262b36;
  --blue: #58c4dd; --yellow: #f4d345; --accent: #58c4dd; --green: #83c167; --red: #fc6255; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0f1117; --surface: #171a22; --fg: #e6e8ee; --muted: #9aa2b4; --line: #262b36;
  --blue: #58c4dd; --yellow: #f4d345; --accent: #58c4dd; --green: #83c167; --red: #fc6255; color-scheme: dark; }}
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
  display: grid; grid-template-rows: auto auto 1fr; min-width: 0; }}
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
.film {{ scroll-margin-top: 16px; }}
.film.flash {{ animation: flash 2.4s ease-out; }}
@keyframes flash {{ 0%, 40% {{ border-color: var(--yellow); box-shadow: 0 0 0 2px var(--yellow); }} 100% {{ box-shadow: 0 0 0 0 transparent; }} }}
.film h3 .seen {{ display: none; color: var(--green); margin-right: 6px; font-weight: 700; }}
.film.watched h3 .seen {{ display: inline; }}
.chap {{ display: flex; gap: 6px; overflow-x: auto; padding: 10px 16px 0; scrollbar-width: thin; }}
.chap button {{ flex: none; font: inherit; font-size: 12px; padding: 2px 9px; border-radius: 999px; border: 1px solid var(--line);
  background: transparent; color: var(--muted); cursor: pointer; display: inline-flex; gap: 5px; align-items: baseline; }}
.chap button .t {{ font-family: var(--f-mono); font-size: 11px; font-variant-numeric: tabular-nums; }}
.chap button:hover, .chap button:focus-visible {{ border-color: var(--accent); color: var(--fg); outline: none; }}
.chap button.on {{ border-color: var(--accent); color: var(--accent); }}
.meta a.src {{ color: var(--muted); text-decoration: underline; text-decoration-color: var(--line); text-underline-offset: 3px; }}
.meta a.src:hover, .meta a.src:focus-visible {{ color: var(--accent); text-decoration-color: currentColor; }}
.meta button.copy {{ font: inherit; font-size: 12px; padding: 0; border: 0; background: none; color: var(--accent); cursor: pointer; margin-left: auto; }}
.film details > summary {{ font-size: 13px; color: var(--muted); cursor: pointer; }}
.film details > summary:hover {{ color: var(--fg); }}
.ts-body {{ display: grid; gap: 8px; margin-top: 8px; max-height: 340px; overflow-y: auto; padding-right: 4px; }}
.film .ts-body p {{ font-size: 13px; line-height: 1.7; color: var(--fg); margin: 0; }}
.ts-body .s {{ cursor: pointer; border-radius: 3px; transition: background .2s; }}
.ts-body .s:hover {{ text-decoration: underline; text-decoration-color: var(--line); text-underline-offset: 3px; }}
.ts-body .s.on {{ background: color-mix(in srgb, var(--accent) 22%, transparent); }}
.rate {{ display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--muted, inherit); }}
.rate select {{ font: inherit; font-size: 12px; padding: 1px 4px; border-radius: 6px; border: 1px solid var(--line);
  background: transparent; color: inherit; }}
.ts-ch {{ font: inherit; font-size: 12px; padding: 0; margin-right: 8px; border: 0; background: none; color: var(--accent); cursor: pointer; }}
.quiz ol {{ margin: 8px 0 0; padding-left: 20px; display: grid; gap: 12px; }}
.film .qz-q {{ margin: 0 0 6px; font-size: 14px; color: var(--fg); }}
.qz-opts {{ display: grid; gap: 6px; }}
.qz-opts button {{ font: inherit; font-size: 13px; text-align: left; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--line);
  background: transparent; color: var(--fg); cursor: pointer; display: flex; gap: 8px; }}
.qz-opts button b {{ font-family: var(--f-mono); font-weight: 400; color: var(--muted); }}
.qz-opts button:hover:not(:disabled), .qz-opts button:focus-visible {{ border-color: var(--accent); outline: none; }}
.qz-opts button:disabled {{ cursor: default; }}
.qz-opts button.right {{ border-color: var(--green); color: var(--green); }}
.qz-opts button.right::after {{ content: "✓"; margin-left: auto; }}
.qz-opts button.wrong {{ border-color: var(--red); color: var(--red); }}
.qz-opts button.wrong::after {{ content: "✗"; margin-left: auto; }}
.film .qz-ex {{ margin: 6px 0 0; font-size: 13px; color: var(--muted); }}
.film .qz-score {{ margin: 8px 0 0; font-size: 13px; color: var(--fg); }}
.film .qz-score:empty {{ display: none; }}
.search {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-top: 4px; }}
.search input {{ flex: 1 1 260px; max-width: 420px; min-width: 0; font: inherit; font-size: 15px; padding: 8px 12px; border-radius: 8px;
  border: 1px solid var(--line); background: var(--surface); color: var(--fg); }}
.search input:focus-visible {{ outline: none; border-color: var(--accent); }}
.search-n {{ font-size: 13px; color: var(--muted); }}
[hidden] {{ display: none !important; }}
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
    <div class="stats"><span><b>{n_films}</b> 支短片</span><span>总时长 <b>{mmss(total)}</b></span><span>1080p · 中文配音 · 画面内字幕</span><span class="seen-n" hidden>已看 <b>0</b> / {n_films}</span></div>
    <div class="search"><input type="search" placeholder="搜索标题、简介、旁白：堆、回溯…" aria-label="搜索短片"><span class="search-n" aria-live="polite"></span></div>
  </header>
  <nav class="weeks" aria-label="按周次跳转">{nav}</nav>
  {''.join(sections)}
  <footer>
    <span>{PAGE['footer']}</span>
    <span>制作：Manim Community 0.22 渲染，Edge TTS 配音，每支片附对撞测试与自动画面检查。</span>
  </footer>
</div>
""" + PAGE_SCRIPT + ((FB_SCRIPT if FEEDBACK else "") + "</body>\n</html>\n" if STANDALONE else "")
(HERE / ("index.standalone.html" if STANDALONE else "index.html")).write_text(page, encoding="utf-8")
print(n_films, mmss(total))
