"""CS101 算法动画入口页的反馈服务（纯标准库，部署在成都中转，经 Caddy 转发 /cs101-anim/api/*）。

接口（Caddy 用 handle_path 剥掉 /cs101-anim/api 前缀后转到这里）：
  POST /feedback   {"film": "<id>", "rating": "ok|hard|fast|slow", "comment": "可选，≤500 字"}
  GET  /summary    各片各选项的票数（只给汇总，不给留言）
隐私：不收姓名；IP 只在内存里用于限频（每 IP 每小时 600 次，校园网共用出口 IP），不落盘。
数据：每条一行 JSON 追加到 $STATE_DIRECTORY/feedback.jsonl（systemd StateDirectory，缺省 ./feedback.jsonl）。

运行：python3 feedback_server.py --port 8109 --films fib,hanoi,...
查看：python3 feedback_server.py --report [--data /var/lib/cs101-anim/feedback.jsonl]
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RATINGS = {"ok": "看懂了", "hard": "有点难", "fast": "节奏太快", "slow": "节奏太慢"}
MAX_BODY, MAX_COMMENT, PER_HOUR = 4096, 500, 600   # 校园网常共用出口 IP，按 IP 限频不能太紧
DATA = Path(os.environ.get("STATE_DIRECTORY", ".")) / "feedback.jsonl"
FILMS: set[str] = set()
LOCK = threading.Lock()
HITS: dict[str, deque] = defaultdict(deque)


def load() -> list[dict]:
    if not DATA.exists():
        return []
    out = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
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
        if self.path.split("?")[0] == "/summary":
            with LOCK:
                return self._send(200, summary())
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path.split("?")[0] != "/feedback":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(413, {"error": "请求太大"})
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"error": "格式不对"})
        film, rating = str(data.get("film", "")), str(data.get("rating", ""))
        comment = str(data.get("comment", "")).strip()[:MAX_COMMENT]
        if film not in FILMS or rating not in RATINGS:
            return self._send(400, {"error": "片目或选项不对"})
        now, ip = time.time(), self._client()
        with LOCK:
            q = HITS[ip]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= PER_HOUR:
                return self._send(429, {"error": "提交太频繁，过一会儿再试"})
            q.append(now)
            with DATA.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "film": film, "rating": rating,
                                    "comment": comment}, ensure_ascii=False) + "\n")
            return self._send(200, {"ok": True, "summary": summary().get(film, {})})

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


def main() -> None:
    global DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8109)
    ap.add_argument("--films", default="")
    ap.add_argument("--data")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.data:
        DATA = Path(a.data)
    if a.report:
        return report()
    FILMS.update(x for x in a.films.split(",") if x)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
