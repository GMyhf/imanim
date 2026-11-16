"""一键发布：检查 →（可选）Mac 上渲染与配音校对 → 720p 转码 → GitHub Releases → 中转部署 → 公网验证。

python cs101/cinematic/publish.py --course cs201                 # 只检查并重新部署页面、题库、反馈服务（不动视频）
python cs101/cinematic/publish.py --course cs201 kmp heap        # 这几支已在 Mac 渲好：转码、传 Release、部署
python cs101/cinematic/publish.py --course cs201 kmp --render    # 先在 Mac 上 1080p 重渲（含配音校对），再发布
python cs101/cinematic/publish.py --course cs101 --stale --render  # 片目顺序变了：把片尾「下一支」过时的片一起重渲发布
  --check-only 只做检查；--dry-run 只打印远端命令；--no-release / --no-deploy 跳过对应步骤；--jobs N 渲染并发数

新增一支片的完整流程：写四个文件并登记 make.py 的 LESSONS → site/films.json 登记（chapters、href）→
site/quiz_gen.py 加 3 题并重新生成 quiz.json → 本脚本带 --render --stale 发布 → git 提交。
反馈服务的片目取自 quiz.json，不必再改 systemd 单元。

主机：PUBLISH_MAC（缺省 hfyan@100.76.69.33，仓库 ~/git/imanim）、PUBLISH_RELAY（缺省 ubuntu@43.136.172.200）。
720p 文件走 Mac → 本机 .local/publish/ → 中转 ~/anim-deploy/，再 sudo 装进 /srv/<课程>-anim/。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAC = os.environ.get("PUBLISH_MAC", "hfyan@100.76.69.33")
MAC_REPO = os.environ.get("PUBLISH_MAC_REPO", "git/imanim")          # 相对 Mac 家目录
RELAY = os.environ.get("PUBLISH_RELAY", "ubuntu@43.136.172.200")
SITE_URL = "https://infomall.zhengmao.ltd"
MAX_SECONDS = 240
COURSES = {   # 课程 → 反馈服务端口、Release 标签、单元说明
    "cs101": {"port": 8109, "tag": "cs101-anim-2026fall", "name": "CS101"},
    "cs201": {"port": 8110, "tag": "cs201-anim-2026fall", "name": "CS201"},
}
MAC_ENV = "export PATH=$PWD/.venv/bin:/opt/homebrew/bin:/Library/TeX/texbin:$PATH"
TRANSCODE = '-vf "scale=1280:-2,fps=30" -c:v libx264 -crf 30 -preset slow -c:a aac -b:a 80k -movflags +faststart'
DRY = False


def say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def sh(cmd: list[str] | str, *, mutate: bool = True, check: bool = True, capture: bool = False,
       input: str | None = None) -> str:
    """mutate=True 的命令在 --dry-run 时只打印。"""
    shown = cmd if isinstance(cmd, str) else shlex.join(cmd)
    if DRY and mutate:
        print(f"[dry-run] {shown[:400]}")
        if input:
            print("".join(f"    | {ln}\n" for ln in input.splitlines()), end="")
        return ""
    r = subprocess.run(cmd, shell=isinstance(cmd, str), text=True, input=input,
                       capture_output=capture, encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise SystemExit(f"命令失败（{r.returncode}）：{shown[:300]}\n{(r.stderr or '')[-2000:]}")
    return r.stdout if capture else ""


def ssh(host: str, script: str, **kw) -> str:
    """远端用 bash 执行一段脚本（经 stdin 传入，避开多层引号）。"""
    return sh(["ssh", "-o", "ConnectTimeout=20", host, "bash -s"], input="set -e\n" + script, **kw)


def on_mac(script: str, **kw) -> str:
    return ssh(MAC, f"cd ~/{MAC_REPO}\n{MAC_ENV}\n{script}", **kw)


# ---------------------------------------------------------------- 课程元数据

class Course:
    def __init__(self, cid: str):
        self.id, self.cfg = cid, COURSES[cid]
        spec = importlib.util.spec_from_file_location(f"publish_make_{cid}", ROOT / cid / "cinematic" / "make.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.base = getattr(m, "base", m)              # cs201 的 make.py 是壳，endcard() 在 base 上
        self.LESSONS, self.PREFIX = m.LESSONS, m.PREFIX
        self.cine = ROOT / cid / "cinematic"
        self.site = self.cine / "site"
        self.out = ROOT / cid / "out"
        self.films = [f for w in self.read(self.site / "films.json")["weeks"] for f in w["films"]]
        self.ids = [f["id"] for f in self.films]

    @staticmethod
    def read(p: Path):
        return json.loads(p.read_text(encoding="utf-8"))

    def dir(self, fid: str) -> str:
        return f"{self.PREFIX}{fid}"

    def mp4(self, fid: str) -> str:                     # 成片名取旁白稿的 id（如 cs101-fib-tree.mp4）
        return self.read(self.cine / self.LESSONS[fid][0])["id"] + ".mp4"

    def sidecar(self, fid: str) -> dict | None:
        p = self.out / self.dir(fid) / "sidecar.json"
        return self.read(p) if p.exists() else None

    def stale(self) -> list[str]:
        """片尾卡「下一支」与当前 films.json 顺序不符的片。"""
        out = []
        for fid in self.ids:
            sc = self.sidecar(fid)
            if sc and fid in self.LESSONS and sc.get("endcard_info") != self.base.endcard(fid):
                out.append(fid)
        return out


# ---------------------------------------------------------------- 检查

def check(c: Course, skip_videos: set[str]) -> None:
    """发布前的一致性检查；有错误就停。skip_videos：将要重渲的片，旧 sidecar 的问题不算。"""
    say(f"检查 {c.id}")
    errs, warns = [], []
    for fid in c.ids:
        if fid not in c.LESSONS:
            errs.append(f"films.json 有 {fid}，make.py 的 LESSONS 里没有")
    for fid in c.LESSONS:
        if fid not in c.ids:
            warns.append(f"{fid} 已登记 LESSONS 但没进 films.json（页面上不会出现）")
    for f in c.films:
        fid = f["id"]
        if fid not in c.LESSONS or fid in skip_videos:
            continue
        sc = c.sidecar(fid)
        if not sc:
            errs.append(f"{fid} 没有 sidecar.json（还没渲染？加 --render）")
            continue
        if sc.get("quality") != "fullhd":
            errs.append(f"{fid} 的 sidecar 是 {sc.get('quality')} 质量，不是 1080p 成片")
        if sc["seconds"] > MAX_SECONDS:
            errs.append(f"{fid} 时长 {sc['seconds']:.1f}s 超过 {MAX_SECONDS}s")
        if sc.get("audit_issues"):
            errs.append(f"{fid} 画面检查有 {sc['audit_issues']} 处问题")
        if list(f.get("chapters", {})) != list(sc["beats"]):
            errs.append(f"{fid} 的 chapters 键 {list(f.get('chapters', {}))} 与 sidecar beats {list(sc['beats'])} 不一致")
        if not f.get("href"):
            warns.append(f"{fid} 没写讲义链接 href")
    quiz = c.read(c.site / "quiz.json")
    if sorted(quiz) != sorted(c.ids):
        errs.append(f"quiz.json 片目与 films.json 不一致：多 {sorted(set(quiz) - set(c.ids))}，缺 {sorted(set(c.ids) - set(quiz))}")
    sys.path.insert(0, str(c.site))
    spec = importlib.util.spec_from_file_location(f"quiz_gen_{c.id}", c.site / "quiz_gen.py")
    qg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qg)
    sys.path.pop(0)
    fresh = qg.build() if hasattr(qg, "build") else qg.build_all()   # 两门课的生成函数名不同
    if fresh != quiz:
        errs.append(f"quiz.json 不是 quiz_gen.py 的最新输出：先跑 (cd {c.site.relative_to(ROOT)} && python quiz_gen.py)")
    stale = [x for x in c.stale() if x not in skip_videos]
    if stale:
        warns.append(f"片尾「下一支」已过时（片目顺序变了）：{' '.join(stale)}，加 --stale --render 一起重渲")
    # 单元测试（含 test_quiz 的独立重算）
    env_path = [str(c.cine)] + ([str(ROOT / "cs101" / "cinematic")] if c.id != "cs101" else [])
    r = subprocess.run([sys.executable, "-m", "unittest", "-q"] + sorted(p.stem for p in c.cine.glob("test_*.py")),
                       cwd=c.cine, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=os.pathsep.join(env_path)))
    if r.returncode:
        errs.append("单元测试失败：\n" + r.stderr[-3000:])
    else:
        print("单元测试：" + r.stderr.strip().splitlines()[-1])
    for w in warns:
        print(f"[提醒] {w}")
    if errs:
        raise SystemExit("检查没通过：\n" + "\n".join(f"  - {e}" for e in errs))
    print(f"检查通过：{len(c.ids)} 支片，题库 {sum(map(len, quiz.values()))} 题")


# ---------------------------------------------------------------- Mac：渲染、校对、转码、Release

def sync_code(c: Course) -> None:
    say("同步代码到 Mac")
    dirs = {ROOT / "cs101" / "cinematic", c.cine}
    for d in sorted(dirs):
        sh(["rsync", "-a", "--exclude", "__pycache__", "--exclude", "site/index*.html",
            f"{d}/", f"{MAC}:{MAC_REPO}/{d.relative_to(ROOT)}/"])


def render(c: Course, ids: list[str], jobs: int) -> None:
    say(f"Mac 上 1080p 渲染 {len(ids)} 支（并发 {jobs}）：{' '.join(ids)}")
    log = f".local/publish/{c.id}"
    on_mac(f"""mkdir -p {log}
printf '%s\\n' {shlex.join(ids)} | xargs -P {jobs} -I{{}} sh -c \\
  'python {c.id}/cinematic/make.py --lesson {{}} > {log}/{{}}.log 2>&1 && echo "OK {{}}" || echo "FAIL {{}}"' > {log}/status.txt
cat {log}/status.txt""")
    if not DRY:
        st = on_mac(f"cat {log}/status.txt", mutate=False, capture=True)
        bad = [ln.split()[1] for ln in st.splitlines() if ln.startswith("FAIL")]
        if bad:
            raise SystemExit(f"渲染失败：{' '.join(bad)}；日志在 Mac ~/{MAC_REPO}/{log}/<id>.log")
    say("配音校对（Mac，mlx-whisper）")
    on_mac(f"python cs101/cinematic/asr_check.py --course {c.id} {shlex.join(ids)} 2>/dev/null | grep -v '^ *warn' || true")
    pull_out(c, ids)


def pull_out(c: Course, ids: list[str]) -> None:
    say("拉回 sidecar、字幕、校对结果（不拉 mp4）")
    for fid in ids:
        (c.out / c.dir(fid)).mkdir(parents=True, exist_ok=True)
        sh(["rsync", "-a", "--exclude", "*.mp4", "--exclude", "audio/", "--exclude", "track.wav",
            "--exclude", "render.log", "--exclude", "media/",
            f"{MAC}:{MAC_REPO}/{c.id}/out/{c.dir(fid)}/", f"{c.out / c.dir(fid)}/"])


def transcode(c: Course, ids: list[str], jobs: int) -> None:
    say(f"Mac 上转码 720p 页面版与封面：{' '.join(ids)}")
    web = f".local/web/{c.id}-anim"
    lines = "\n".join(f"{c.id}/out/{c.dir(fid)}/{c.mp4(fid)} {fid}" for fid in ids)
    on_mac(f"""mkdir -p {web}/videos {web}/posters
cat > {web}/.jobs <<'EOF'
{lines}
EOF
xargs -P {min(jobs, 6)} -L 1 sh -c 'ffmpeg -nostdin -v error -y -i "$0" {TRANSCODE.replace("'", "")} {web}/videos/"$1".mp4 && \\
  ffmpeg -nostdin -v error -y -i "$(dirname "$0")/preview.png" -vf scale=960:-1 -q:v 4 {web}/posters/"$1".jpg' < {web}/.jobs""")


def release(c: Course, ids: list[str]) -> None:
    say(f"上传 1080p 成片到 GitHub Releases {c.cfg['tag']}")
    files = " ".join(f"{c.id}/out/{c.dir(fid)}/{c.mp4(fid)}" for fid in ids)
    on_mac(f"gh release upload {c.cfg['tag']} -R GMyhf/imanim --clobber {files}")


# ---------------------------------------------------------------- 中转部署

UNIT = """[Unit]
Description={name} 算法动画入口页反馈服务（infomall.zhengmao.ltd/{cid}-anim/api/）
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/cs101-anim/feedback_server.py --host 127.0.0.1 --port {port} --quiz /opt/cs101-anim/quiz-{cid}.json
EnvironmentFile=/etc/cs101-anim/report.env
DynamicUser=yes
StateDirectory={cid}-anim
Restart=on-failure
ProtectSystem=strict
ProtectHome=yes
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
"""


def deploy(c: Course, ids: list[str]) -> None:
    say("生成页面")
    py = sys.executable
    build = ROOT / "cs101" / "cinematic" / "site" / "build.py"
    sh([py, str(build), "--site", str(c.site), "--standalone", "--feedback"], mutate=False)
    sh([py, str(ROOT / "cs101" / "cinematic" / "site" / "home.py")], mutate=False)

    stage = ROOT / ".local" / "publish" / c.id
    (stage / "videos").mkdir(parents=True, exist_ok=True)
    (stage / "posters").mkdir(parents=True, exist_ok=True)
    for p in list(stage.glob("videos/*")) + list(stage.glob("posters/*")):
        p.unlink()                                       # 只带这次要更新的视频
    if ids:
        say("从 Mac 拉 720p 文件")
        web = f"{MAC_REPO}/.local/web/{c.id}-anim"
        for sub, ext in (("videos", "mp4"), ("posters", "jpg")):
            sh(["rsync", "-a", "--partial"] + [f"{MAC}:{web}/{sub}/{fid}.{ext}" for fid in ids] + [f"{stage / sub}/"])
    files = {
        "index.html": c.site / "index.standalone.html",
        "home.html": ROOT / "cs101" / "cinematic" / "site" / "home.html",
        "feedback_server.py": ROOT / "cs101" / "cinematic" / "site" / "feedback_server.py",
        f"quiz-{c.id}.json": c.site / "quiz.json",
    }
    for name, src in files.items():
        (stage / name).write_bytes(src.read_bytes())
    (stage / f"{c.id}-anim-feedback.service").write_text(
        UNIT.format(name=c.cfg["name"], cid=c.id, port=c.cfg["port"]), encoding="utf-8")

    say(f"传到中转 {RELAY}:~/anim-deploy/{c.id}/")
    ssh(RELAY, f"mkdir -p ~/anim-deploy/{c.id}")
    sh(["rsync", "-a", "--partial", "--delete", f"{stage}/", f"{RELAY}:anim-deploy/{c.id}/"])

    say("中转上安装（先备份旧页面、题库、服务）")
    srv, unit, svc = f"/srv/{c.id}-anim", f"/etc/systemd/system/{c.id}-anim-feedback.service", f"{c.id}-anim-feedback"
    ssh(RELAY, f"""cd ~/anim-deploy/{c.id}
BK=/var/backups/anim-$(date +%Y%m%d-%H%M%S)-{c.id}
sudo mkdir -p $BK
sudo cp -a {srv}/index.html /srv/anim/index.html /opt/cs101-anim/feedback_server.py {unit} $BK/ 2>/dev/null || true
sudo cp -a /opt/cs101-anim/quiz-{c.id}.json $BK/ 2>/dev/null || true
sudo rsync -a --chown=root:root --chmod=D755,F644 videos/ {srv}/videos/
sudo rsync -a --chown=root:root --chmod=D755,F644 posters/ {srv}/posters/
RESTART=0
for f in feedback_server.py quiz-{c.id}.json; do
  if ! sudo cmp -s $f /opt/cs101-anim/$f; then sudo install -m 644 $f /opt/cs101-anim/$f; RESTART=1; fi
done
if ! sudo cmp -s {c.id}-anim-feedback.service {unit}; then
  sudo install -m 644 {c.id}-anim-feedback.service {unit}; sudo systemctl daemon-reload; RESTART=1
fi
if [ ! -f /etc/cs101-anim/report.env ]; then
  sudo install -d -m 700 /etc/cs101-anim
  echo "FEEDBACK_REPORT_TOKEN=$(openssl rand -hex 16)" | sudo tee /etc/cs101-anim/report.env >/dev/null
  sudo chmod 600 /etc/cs101-anim/report.env; RESTART=1
fi
if [ $RESTART = 1 ]; then sudo systemctl restart {svc}; sleep 1; echo "反馈服务已重启"; fi
systemctl is-active {svc}
sudo install -m 644 index.html {srv}/index.html
sudo install -m 644 home.html /srv/anim/index.html
echo "备份：$BK"
""")
    verify(c, ids)


def verify(c: Course, ids: list[str]) -> None:
    say("公网验证")
    if DRY:
        print("[dry-run] 跳过")
        return
    base = f"{SITE_URL}/{c.id}-anim/"

    def get(url: str, rng: bool = False) -> tuple[str, str]:
        r = subprocess.run(["curl", "-s", "-o", "-", "-w", "\n%{http_code}"] + (["-r", "0-1023"] if rng else []) + [url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        body, _, code = r.stdout.rpartition("\n")
        return code, body

    bad = []
    code, page = get(base)
    n = page.count('class="film"')
    print(f"{code} 入口页，{n} 支片")
    if code != "200" or n != len(c.ids):
        bad.append(f"入口页 {code}，片数 {n} ≠ {len(c.ids)}")
    for fid in ids:
        for u in (f"videos/{fid}.mp4", f"posters/{fid}.jpg"):
            code, _ = get(base + u, rng=True)
            print(f"{code} {u}")
            if code not in ("200", "206"):
                bad.append(f"{u} → {code}")
    code, _ = get(base + "api/summary")
    print(f"{code} api/summary")
    if code != "200":
        bad.append(f"api/summary → {code}")
    code, _ = get(f"{SITE_URL}/anim/")
    if code != "200":
        bad.append(f"总入口 → {code}")
    if bad:
        raise SystemExit("公网验证没通过：" + "；".join(bad))
    print("公网验证通过")


# ---------------------------------------------------------------- 主流程

def main() -> int:
    global DRY
    ap = argparse.ArgumentParser(description="一键发布算法动画（检查、渲染、转码、Release、部署、验证）")
    ap.add_argument("--course", choices=COURSES, required=True)
    ap.add_argument("ids", nargs="*", help="要发布视频的片子 id；不给就只更新页面、题库与反馈服务")
    ap.add_argument("--render", action="store_true", help="先在 Mac 上 1080p 重渲这些片（含配音校对）")
    ap.add_argument("--stale", action="store_true", help="把片尾「下一支」过时的片也加进来")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-release", action="store_true")
    ap.add_argument("--no-deploy", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    c = Course(a.course)
    ids = list(dict.fromkeys(a.ids + (c.stale() if a.stale else [])))
    unknown = [x for x in ids if x not in c.LESSONS]
    if unknown:
        raise SystemExit(f"不认识的片子 id：{unknown}（见 {c.id}/cinematic/make.py 的 LESSONS）")
    if a.stale and not a.render:
        print("[提醒] --stale 的片要重渲才会更新片尾卡；没加 --render 时只是重新上传旧成片")
    t0 = time.time()
    check(c, set(ids) if a.render else set())
    if a.check_only:
        return 0
    if a.render and ids:
        sync_code(c)
        render(c, ids, a.jobs)
        check(c, set())                                  # 渲完再查一遍：时长、画面检查、章节
    elif ids:
        pull_out(c, ids)                                 # 用 Mac 上现有成片：先拉回最新 sidecar
    if ids:
        transcode(c, ids, a.jobs)
        if not a.no_release:
            release(c, ids)
    if not a.no_deploy:
        deploy(c, ids)
    say(f"完成（{time.time() - t0:.0f}s）。记得 git 提交 {c.id}/out/ 与改动的源文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
