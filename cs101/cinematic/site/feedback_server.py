"""CS101 算法动画入口页的反馈服务（纯标准库，部署在成都中转，经 Caddy 转发 /cs101-anim/api/*）。

接口（Caddy 用 handle_path 剥掉 /cs101-anim/api 前缀后转到这里）：
  POST /feedback   {"film": "<id>", "rating": "ok|hard|fast|slow", "comment": "可选，≤500 字"}
  GET  /summary    各片各选项的票数（只给汇总，不给留言）
  POST /quiz       {"film": "<id>", "q": 题号（从 0 起）, "ok": true|false}   小测答题结果（页面每题只提交一次）
  GET  /report?token=…   给老师看的汇总页（HTML：各片评分计数、留言、小测每题正确率）；
                   token 取环境变量 FEEDBACK_REPORT_TOKEN 或 --token，没配就 404
隐私：不收姓名；IP 只在内存里用于限频（每 IP 每小时 600 次，校园网共用出口 IP），不落盘。
数据：每条一行 JSON 追加到 $STATE_DIRECTORY/feedback.jsonl（systemd StateDirectory，缺省 ./feedback.jsonl），
      小测记在同目录 quiz.jsonl。

运行：python3 feedback_server.py --port 8109 --films fib,hanoi,... [--quiz quiz.json] [--token …]
      （--quiz 给出时按各片题数校验题号，否则只要求 0 ≤ q < 20）
查看：python3 feedback_server.py --report [--data /var/lib/cs101-anim/feedback.jsonl]
"""
from __future__ import annotations

import argparse
import hmac
import html
import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

RATINGS = {"ok": "看懂了", "hard": "有点难", "fast": "节奏太快", "slow": "节奏太慢"}
MAX_BODY, MAX_COMMENT, PER_HOUR = 4096, 500, 600   # 校园网常共用出口 IP，按 IP 限频不能太紧
QUIZ_PER_HOUR = 6000   # 每人每支约 3 题，一个班共用出口 IP 时答题量远大于评分量，单独计数
MAX_Q = 20
DATA = Path(os.environ.get("STATE_DIRECTORY", ".")) / "feedback.jsonl"
FILMS: list[str] = []
QUIZ_N: dict[str, int] = {}        # 片子 → 题数（--quiz 给出时）
TOKEN = os.environ.get("FEEDBACK_REPORT_TOKEN", "")
LOCK = threading.Lock()
HITS: dict[str, deque] = defaultdict(deque)
QHITS: dict[str, deque] = defaultdict(deque)


def quiz_path() -> Path:
    return DATA.with_name("quiz.jsonl")


def load(path: Path | None = None) -> list[dict]:
    path = path or DATA
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def summary() -> dict:
    s: dict = {}
    for r in load():
        s.setdefault(r["film"], {k: 0 for k in RATINGS})[r["rating"]] += 1
    return s


def quiz_summary() -> dict:
    """{film: {题号: [答对数, 作答数]}}"""
    s: dict = {}
    for r in load(quiz_path()):
        c = s.setdefault(r["film"], {}).setdefault(int(r["q"]), [0, 0])
        c[0] += bool(r["ok"])
        c[1] += 1
    return s


def limited(table: dict, ip: str, per_hour: int, now: float) -> bool:
    q = table[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= per_hour:
        return True
    q.append(now)
    return False


def report_html() -> str:
    rows, s, qs = load(), summary(), quiz_summary()
    e = html.escape
    films = list(FILMS) + sorted((set(s) | set(qs)) - set(FILMS))
    head = "".join(f"<th>{v}</th>" for v in RATINGS.values())
    body = []
    for f in films:
        c = s.get(f, {})
        quiz = " ".join(f"{i + 1}: {ok}/{n}（{ok * 100 // n}%）" for i, (ok, n) in sorted(qs.get(f, {}).items())) or "—"
        body.append(f"<tr><td>{e(f)}</td>" + "".join(f"<td>{c.get(k, 0) or ''}</td>" for k in RATINGS)
                    + f"<td class=q>{e(quiz)}</td></tr>")
    comments = "".join(f"<li><span>{e(r['t'])} · {e(r['film'])} · {e(RATINGS.get(r['rating'], r['rating']))}</span>"
                       f"{e(r['comment'])}</li>" for r in reversed(rows) if r.get("comment")) or "<li>还没有留言</li>"
    nq = sum(n for f in qs.values() for _, n in f.values())
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>反馈汇总</title><style>
:root {{ --bg:#f4f5f8; --fg:#1b1e26; --muted:#5d6475; --line:#dde1ea; --surface:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1117; --fg:#e6e8ee; --muted:#9aa2b4; --line:#262b36; --surface:#171a22; color-scheme: dark; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.6 "PingFang SC","Noto Sans SC","Microsoft YaHei",system-ui,sans-serif; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:32px 16px 48px; }}
h1 {{ font-size:24px; margin:0 0 4px; }} p.m {{ color:var(--muted); margin:0 0 20px; font-size:13px; }}
.tbl {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
table {{ border-collapse:collapse; width:100%; font-size:13px; font-variant-numeric:tabular-nums; }}
th, td {{ padding:6px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }}
td.q {{ white-space:normal; color:var(--muted); }}
ul {{ padding-left:18px; }} li {{ margin:6px 0; }} li span {{ color:var(--muted); font-size:12px; margin-right:8px; }}
</style></head><body><div class="wrap">
<h1>反馈汇总</h1><p class="m">评分 {len(rows)} 条 · 小测作答 {nq} 次 · 生成于 {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
<div class="tbl"><table><thead><tr><th>片子</th>{head}<th>小测正确率（题号: 对/答）</th></tr></thead>
<tbody>{"".join(body)}</tbody></table></div>
<h2>留言（新的在前）</h2><ul>{comments}</ul></div></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "cs101-anim-feedback"

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _client(self) -> str:
        xff = self.headers.get("X-Forwarded-For", "")
        return xff.split(",")[-1].strip() or self.client_address[0]   # Caddy 追加的最后一项是真实来源

    def do_GET(self):  # noqa: N802
        u = urlsplit(self.path)
        if u.path == "/summary":
            with LOCK:
                return self._send(200, summary())
        if u.path == "/report":
            got = parse_qs(u.query).get("token", [""])[0]
            if TOKEN and hmac.compare_digest(got.encode(), TOKEN.encode()):
                with LOCK:
                    body = report_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Robots-Tag", "noindex")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path not in ("/feedback", "/quiz"):
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(413, {"error": "请求太大"})
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"error": "格式不对"})
        if path == "/quiz":
            return self._quiz(data)
        film, rating = str(data.get("film", "")), str(data.get("rating", ""))
        comment = str(data.get("comment", "")).strip()[:MAX_COMMENT]
        if film not in FILMS or rating not in RATINGS:
            return self._send(400, {"error": "片目或选项不对"})
        now, ip = time.time(), self._client()
        with LOCK:
            if limited(HITS, ip, PER_HOUR, now):
                return self._send(429, {"error": "提交太频繁，过一会儿再试"})
            with DATA.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "film": film, "rating": rating,
                                    "comment": comment}, ensure_ascii=False) + "\n")
            return self._send(200, {"ok": True, "summary": summary().get(film, {})})

    def _quiz(self, data: dict):
        film, q, ok = str(data.get("film", "")), data.get("q"), data.get("ok")
        limit = QUIZ_N.get(film, MAX_Q) if QUIZ_N else MAX_Q
        if film not in FILMS or type(q) is not int or not 0 <= q < limit or type(ok) is not bool:
            return self._send(400, {"error": "片目或题号不对"})
        now, ip = time.time(), self._client()
        with LOCK:
            if limited(QHITS, ip, QUIZ_PER_HOUR, now):
                return self._send(429, {"error": "提交太频繁，过一会儿再试"})
            with quiz_path().open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "film": film, "q": q, "ok": ok},
                                   ensure_ascii=False) + "\n")
        return self._send(200, {"ok": True})

    def log_message(self, fmt, *args):   # 不记 IP
        pass


def report() -> None:
    rows = load()
    s = summary()
    print(f"共 {len(rows)} 条反馈")
    for film, c in sorted(s.items()):
        print(f"  {film:10s} " + "  ".join(f"{RATINGS[k]} {v}" for k, v in c.items()))
    print("留言：")
    for r in rows:
        if r.get("comment"):
            print(f"  [{r['t']}] {r['film']} / {RATINGS[r['rating']]}：{r['comment']}")
    qs = quiz_summary()
    print("小测正确率（题号: 答对/作答）：")
    for film, c in sorted(qs.items()):
        print(f"  {film:10s} " + "  ".join(f"{i + 1}: {ok}/{n}" for i, (ok, n) in sorted(c.items())))


def main() -> None:
    global DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8109)
    ap.add_argument("--films", default="")
    ap.add_argument("--data")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quiz", help="入口页同一份 quiz.json，用来校验题号")
    ap.add_argument("--token", help="汇总页 /report 的口令（也可用环境变量 FEEDBACK_REPORT_TOKEN）")
    a = ap.parse_args()
    if a.data:
        DATA = Path(a.data)
    if a.report:
        return report()
    global TOKEN
    TOKEN = a.token or TOKEN
    FILMS.extend(x for x in a.films.split(",") if x)
    if a.quiz:
        QUIZ_N.update({k: len(v) for k, v in json.loads(Path(a.quiz).read_text(encoding="utf-8")).items()})
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
