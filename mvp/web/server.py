"""澄象 MVP · 演示用 HTTP 服务（纯标准库，无 Flask/FastAPI）

职责：
  1. 静态服务 index.html / app.js / styles.css（与 API 同源，前端不需要处理 CORS）
  2. 结构化输入契约（Spec_Product 第 2 节）→ 落 brief.json → 子进程跑 mvp/run.py 的链路
  3. 任务异步：每个 job 一个后台线程 + 一个子进程，GET /api/status/<job> 读 progress.json 报阶段与耗时
  4. 分镜可改（Spec 第 4 节，我们相对竞品的核心差异）：改过的 plan.json 交给 jobrunner --mode render 重出片
  5. 作品墙：扫 mvp/out/ 与本目录 jobs/ 下的 sidecar.json

约定：任务目录名一律纯 ASCII（D:\\Dev\\Project1\\mvp\\web\\jobs\\<id>），
中文只出现在 JSON 内容里 —— 这台机器的 PowerShell/ffmpeg 对中文路径不稳。

启动：cd mvp/web && <t314 python> server.py --port 8123
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

WEB_DIR = Path(__file__).resolve().parent
MVP_DIR = WEB_DIR.parent
JOBS_DIR = WEB_DIR / "jobs"
OUT_DIR = MVP_DIR / "out"
# 画廊白名单哨兵：run 目录下存在该标记文件（内容不限、可为空）才允许上墙。
# 旧稿批量更换期间一律不放行——换新稿/验收合格后由人工在对应 run 目录放置此文件。
# 只影响 /api/gallery 列表；已有产物文件一个都不删、不移、不改名。
GALLERY_OK_SENTINEL = ".gallery_ok"
KP_DIR = MVP_DIR / "pipeline" / "data" / "kp"
RUNNER = WEB_DIR / "jobrunner.py"
PY = sys.executable
MAX_JOB_SECONDS = 30 * 60
# 81-W1 超时分级：≤300s 旧档维持 30 分钟上限（行为不变）；长片档（600/1200s）的渲染墙钟
# 按目标时长×画质系数外推（短片 120s@1080p 实测约 100s，1080p 取 6×、720p 3×、480p 1.5×，
# 另加 600s 固定余量给检索/配音/合成段）。语义不变：
# 超时 = 杀掉子进程、失败原因用人话报出该档上限分钟数。
QUALITY_TIMEOUT_FACTOR = {"draft": 1.5, "hd": 3.0, "fullhd": 6.0}
LONG_TIERS = (600, 1200)   # 新时长档：只有它们走分级放宽，与 DURATIONS 的新档同口径
FEEDBACK_DIR = Path(os.environ.get("QX_FEEDBACK_DIR") or (WEB_DIR / "feedback"))
FEEDBACK_READ_TOKEN = os.environ.get("QX_FEEDBACK_TOKEN", "").strip()
# 容器文件系统重启即清空，反馈另外写穿到一个 ModelScope 私有数据集；两项都配了才启用。
FEEDBACK_REPO = os.environ.get("QX_FEEDBACK_REPO", "").strip()
FEEDBACK_REPO_TOKEN = os.environ.get("QX_FEEDBACK_REPO_TOKEN", "").strip()
FEEDBACK_TYPES = ("bug", "content", "suggestion", "other")
FEEDBACK_LABELS = {"bug": "功能问题 / 报错", "content": "内容 / 科学性", "suggestion": "功能建议", "other": "其他"}
FEEDBACK_MAX_TEXT = 5000
FEEDBACK_MAX_CONTACT = 200

# 在线生成需要的模型网关（文案 + 配音都走 HTTP）在创空间容器里没有可用配置：
# 密钥不入镜像、网络策略未定，所以启动脚本把这个开关置 1，空间只出画廊（见 deploy/start.sh）。
# 配音早已不是 Windows SAPI（SubTask #60-A 换成网关 TTS），移植服务器时按网关可用性重开。
# 前端不需要特判：返回的就是它已经在显示的 error 字段。
GENERATE_DISABLED = os.environ.get("MVP_GENERATE_DISABLED") == "1"
GENERATE_DISABLED_MSG = (
    "在线生成在当前部署里已关闭：未配置模型网关密钥或网络，文案与配音生成不可用。"
    "本空间提供已渲染成片的画廊、分镜脚本与全部技术文档。")

# 并发上限：generate/improve 都会连发 claude-opus-5-5（K0 起草 + A3 分镜），同时跑多条会把
# 同一个网关打满。超出上限的任务进 FIFO 队列，名额空出来自动起跑，不拒绝用户。
# regenerate 只走 TTS+渲染、不打 LLM 文案模型，不占这个名额。
MAX_LLM_JOBS = max(1, int(os.environ.get("QX_MAX_LLM_JOBS", "3")))

# 复用管线的输入契约层做「单一真源」校验：知识点检索走 knowledge.load(subject, topic, grade)（带学段过滤），
# Brief 校验走 Brief.validate()（返回错误清单而非抛异常，__post_init__ 会把字符串数字归一化）。
# 只 import 纯标准库的 ir/knowledge，不会把 manim/渲染依赖拖进 HTTP 线程。
sys.path.insert(0, str(MVP_DIR))
from pipeline import knowledge  # noqa: E402
from pipeline.ir import (  # noqa: E402
    MIN_SHOT_SECONDS, SHOT_HEAD, SHOT_TAIL, SPEC_VERSION, Brief,
)

SUBJECTS = [("math", "数学"), ("physics", "物理"), ("chemistry", "化学")]
GRADES = [("G8", "初二"), ("G9", "初三"), ("H1", "高一"), ("H2", "高二"), ("H3", "高三"), ("U1", "大一"), ("U2", "大二")]
STYLES = [("clean", "clean · 白底板书"), ("board", "board · 深色黑板")]
DURATIONS = [60, 120, 180, 300, 600, 1200]
# 选择器只写目标时长与画质本身；渲染耗时随机器负载和内容波动，不做逐档承诺。
DURATION_LABELS = {
    60: "60 秒 · 1 分钟", 120: "120 秒 · 2 分钟", 180: "180 秒 · 3 分钟",
    300: "300 秒 · 5 分钟", 600: "600 秒 · 10 分钟", 1200: "1200 秒 · 20 分钟",
}
QUALITIES = [("draft", "480p 草稿"), ("hd", "720p 高清"), ("fullhd", "1080p 正式")]
STAGE_LABELS = {"retrieve": "检索知识点库", "draft": "起草知识点（库外）", "storyboard": "生成分镜", "narration": "配音合成",
                "review": "静态监督检查", "render": "画面渲染", "mux": "音幕合成",
                "done": "已完成", "failed": "失败", "queued": "排队中", "starting": "启动中"}

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".mp4": "video/mp4", ".wav": "audio/wav", ".srt": "text/plain; charset=utf-8",
        ".txt": "text/plain; charset=utf-8", ".png": "image/png"}

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _llm_busy() -> int:
    """在跑的 LLM 型任务数（generate/improve）。regenerate 只走 TTS+渲染、不发文案模型，不占名额。"""
    return sum(1 for j in _jobs.values()
               if j.get("kind") in ("generate", "improve") and j.get("state") == "running")


def _queued() -> list[dict]:
    return sorted((j for j in _jobs.values() if j.get("state") == "queued"), key=lambda j: j["created"])


def dispatch() -> None:
    """名额有空就按提交顺序起排队任务。超出上限的任务只排队、不拒绝。"""
    while True:
        with _lock:
            q = _queued()
            if not q or _llm_busy() >= MAX_LLM_JOBS:
                return
            j = q[0]
            j.update(state="running", started=time.time())
            persist(j["id"])
            job_id, argv = j["id"], list(j["argv"])
        spawn(job_id, argv, JOBS_DIR / job_id)


def _enqueue(job: dict, argv: list[str]) -> None:
    with _lock:
        _jobs[job["id"]] = {**job, "state": "queued", "argv": argv}
        persist(job["id"])
    dispatch()


# --------------------------------------------------------------------------- 知识点库
def kp_entries(subject: str | None = None) -> list[dict]:
    out = []
    for subj in [s for s, _ in SUBJECTS] if subject is None else [subject]:
        d = KP_DIR / subj
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                e = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            out.append({
                "id": e.get("id"), "subject": e.get("subject", subj), "grade": e.get("grade"),
                "topic": e.get("topic"), "aliases": e.get("aliases", []),
                "has_prior": bool(e.get("prior")),
                "refs": [f"{r.get('source','')} {r.get('locator','')}".strip() for r in e.get("refs", [])],
                "shots": len(e.get("sequence", [])),
            })
    return out


# --------------------------------------------------------------------------- 产物目录
def run_dir_for(key: str) -> Path | None:
    """key 形如 "out:<目录名>" 或 "job:<任务id>"；只接受单层 ASCII 目录名，防目录穿越。"""
    root, sep, name = key.partition(":")
    # NAME_RE 允许 "." / ".."（字符类含点号），但它们能指回上级目录，必须单独挡掉
    if not sep or not NAME_RE.match(name) or name in (".", ".."):
        return None
    if root == "job":
        base = JOBS_DIR / name
        cand = base / "run"
        return cand if cand.is_dir() else (base if base.is_dir() else None)
    if root == "out":
        return OUT_DIR / name if (OUT_DIR / name).is_dir() else None
    return None


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 产物可能半写状态，读不到就当作缺省
        return None


def run_meta(rd: Path, key: str) -> dict:
    """把一个 run 目录的 sidecar/brief/plan 汇总成作品墙卡片需要的字段（只读，不写回）。"""
    sidecar = read_json(rd / "sidecar.json") or {}
    brief = read_json(rd / "brief.json") or {}
    plan = read_json(rd / "plan.json") or {}
    files = run_files(rd, key)
    artifact = Path(sidecar.get("artifact", ""))
    subject = brief.get("subject") or (plan.get("brief") or {}).get("subject")
    grade = brief.get("grade") or (plan.get("brief") or {}).get("grade")
    topic = brief.get("topic") or (plan.get("brief") or {}).get("topic")
    if subject is None and artifact.name:
        m = re.match(r"^(math|physics|chemistry)-(G8|G9|H1|H2|H3|U1|U2)-(.+)-(\d+)s-[0-9a-f]{8}", artifact.name)
        if m:
            subject, grade, topic = m.group(1), m.group(2), m.group(3)
    src = rd.stat().st_mtime
    for cand in ("sidecar.json", "plan.json"):
        if (rd / cand).is_file():
            src = (rd / cand).stat().st_mtime
            break
    return {
        "key": key,
        "source": "生成任务" if key.startswith("job:") else "示例库",
        "subject": subject, "grade": grade,
        "grade_label": dict(GRADES).get(grade, grade),
        "topic": topic,
        "style": brief.get("style") or (plan.get("brief") or {}).get("style"),
        "target_seconds": (plan.get("brief") or {}).get("target_seconds") or brief.get("target_seconds"),
        "seconds": (sidecar.get("duration") or {}).get("actual"),
        "size_mb": sidecar.get("size_mb"),
        "shots": sidecar.get("shots") or len(plan.get("shots", [])),
        "knowledge_id": sidecar.get("knowledge_id") or plan.get("knowledge_id"),
        "refs": sidecar.get("refs") or plan.get("refs") or [],
        "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(src)),
        "mtime": src,
        "video": files.get("video", {}).get("url"),
        "plan_url": f"/api/plan/{key}" if (rd / "plan.json").is_file() else None,
        "files": file_list(files),
    }


# 产物按「角色」暴露，URL 里只出现 ASCII 角色名：主产物文件名带中文（{学科}-{学段}-{知识点}-…），
# 拼进 URL 在 Windows 上会退化成代理对，播放/下载直接坏掉，所以一律服务端解析真实路径。
ROLE_ORDER = {
    "video": ["burned.mp4", "final_burned.mp4", "final.mp4", "MAIN"],
    "final": ["final.mp4", "burned.mp4", "MAIN"],
    "burned": ["burned.mp4", "final_burned.mp4"],
    "srt": ["subs.srt"],
    "plan": ["plan.json"],
    "sidecar": ["sidecar.json"],
    "brief": ["brief.json"],
    "review": ["review.json"],
    "named": ["MAIN"],
}
ROLE_LABEL = {
    "video": "播放用主片",
    "final": "final.mp4 · 成片（1080p，字幕为独立轨）",
    "burned": "burned.mp4 · 字幕已烧录（手机/课件直看）",
    "srt": "subs.srt · 字幕文件",
    "plan": "plan.json · 分镜脚本",
    "sidecar": "sidecar.json · 运行元数据",
    "brief": "brief.json · 输入契约",
    "review": "review.json · 静态监督结果",
    "named": "按命名规范落盘的成片",
}
DISPLAY_ORDER = ["final", "burned", "srt", "plan", "named", "sidecar", "brief", "review"]


def run_files(rd: Path, key: str) -> dict:
    """role -> {name,size,url,path,label}；缺某角色就跳过（例如烧录失败时没有 burned）。"""
    stat = {p.name: p.stat().st_size for p in rd.glob("*") if p.is_file()}
    main = Path((read_json(rd / "sidecar.json") or {}).get("artifact", "")).name
    if main and main not in stat:
        main = None
    if main is None:
        cands = sorted(n for n in stat if n.endswith(".mp4") and n != "silent.mp4")
        main = cands[0] if cands else None
    out = {}
    for role, order in ROLE_ORDER.items():
        for want in order:
            name = main if want == "MAIN" else want
            if name and name in stat:
                out[role] = {"role": role, "name": name, "size": stat[name],
                             "label": ROLE_LABEL[role], "url": f"/api/file/{key}/{role}",
                             "path": str(rd / name)}
                break
    return out


def file_list(files: dict) -> list[dict]:
    """四个必取产物（成片/烧录版/srt/plan）排在前面，其余按角色补。"""
    taken = set()
    out = []
    for role in DISPLAY_ORDER:
        f = files.get(role)
        if not f or f["name"] in taken:
            continue
        taken.add(f["name"])
        out.append({k: f[k] for k in ("role", "name", "label", "size", "url")})
    return out


def gallery() -> list[dict]:
    items = []
    for base, prefix in ((OUT_DIR, "out"), (JOBS_DIR, "job")):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            rd = d / "run" if (d / "run").is_dir() else d
            if not (rd / "sidecar.json").is_file():   # 没跑完/被闸门打回的不出现在墙上
                continue
            if not (rd / GALLERY_OK_SENTINEL).is_file():  # 未标记「已换稿/合格」的（旧稿）不上墙
                continue
            items.append(run_meta(rd, f"{prefix}:{d.name}"))
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


# --------------------------------------------------------------------------- 任务管理
def new_id(mode: str) -> str:
    return f"{mode}{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(3).hex()}"


def job_timeout_seconds(brief: dict | None, quality: str | None) -> int:
    """任务超时上限（秒）：旧档（<600s）保持 30 分钟口径；长档按目标时长×画质系数分级放宽。"""
    tgt = (brief or {}).get("target_seconds")
    try:
        tgt = int(float(tgt))
    except (TypeError, ValueError):
        tgt = 0
    if not any(tgt >= t for t in LONG_TIERS):
        return MAX_JOB_SECONDS
    factor = QUALITY_TIMEOUT_FACTOR.get(quality or "", QUALITY_TIMEOUT_FACTOR["fullhd"])
    return int(tgt * factor) + 600


def spawn(job_id: str, argv: list[str], job_dir: Path) -> None:
    logf = open(job_dir / "runner.log", "wb")
    try:
        proc = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT, cwd=str(WEB_DIR))
    except OSError as e:  # 起进程就失败
        with _lock:
            _jobs[job_id].update(state="failed", error=f"子进程启动失败：{e}", finished=time.time())
            persist(job_id)
        return
    with _lock:
        j = _jobs.get(job_id) or {}
        limit = job_timeout_seconds(j.get("brief"), j.get("quality"))

    def watch() -> None:
        deadline = time.time() + limit
        while proc.poll() is None:
            if time.time() > deadline:
                proc.kill()
                break
            time.sleep(1)
        rc = proc.returncode
        result = read_json(job_dir / "result.json") or {}
        with _lock:
            j = _jobs[job_id]
            if result.get("ok"):
                j.update(state="done", finished=time.time(), result=result)
            elif rc == -9 or time.time() > deadline:
                j.update(state="failed", finished=time.time(),
                         error=f"任务超时被终止（本档上限 {limit // 60} 分钟）："
                               f"长片在演示机渲染很慢，建议降低画质或缩短目标时长后重试")
            else:
                err = result.get("error")
                if not err and (job_dir / "runner.log").is_file():
                    err = (job_dir / "runner.log").read_text(encoding="utf-8", errors="replace")[-1500:]
                j.update(state="failed", finished=time.time(), error=err or f"子进程退出码 {rc}", rc=rc)
            persist(job_id)
        dispatch()

    threading.Thread(target=watch, daemon=True).start()


def persist(job_id: str) -> None:
    j = dict(_jobs.get(job_id, {}))
    j.pop("proc", None)
    tmp = JOBS_DIR / f"{job_id}.json.tmp"
    tmp.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, JOBS_DIR / f"{job_id}.json")


def start_generate(brief: dict, quality: str) -> str:
    if GENERATE_DISABLED:
        raise ValueError(GENERATE_DISABLED_MSG)
    job_id = new_id("g")
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    _enqueue({"id": job_id, "kind": "generate", "key": f"job:{job_id}",
              "created": time.time(), "brief": brief, "quality": quality},
             [PY, str(RUNNER), "--mode", "generate", "--job-dir", str(job_dir),
              "--brief-file", str(job_dir / "brief.json"), "--quality", quality])
    return job_id


def start_regenerate(source_key: str, shots: list[dict], quality: str) -> str:
    """把源成片 plan.json 拷到新任务目录，套用用户改的 narration/seconds，再重跑后半段。"""
    if GENERATE_DISABLED:
        raise ValueError(GENERATE_DISABLED_MSG)
    rd = run_dir_for(source_key)
    plan = read_json(rd / "plan.json") if rd else None
    if not plan:
        raise ValueError("源任务没有 plan.json，无法改分镜")
    by_index = {int(s["index"]): s for s in shots}
    for s in plan["shots"]:
        u = by_index.get(s["index"])
        if not u:
            continue
        if isinstance(u.get("narration"), str) and u["narration"].strip():
            s["narration"] = u["narration"].strip()
        if u.get("seconds") not in (None, ""):
            # 编辑的是镜头总时长（含 SHOT_HEAD/SHOT_TAIL 前后留白），下限用库内 MIN_SHOT_SECONDS
            s["seconds"] = max(MIN_SHOT_SECONDS, round(float(u["seconds"]), 2))
        if isinstance(u.get("title"), str) and u["title"].strip():
            s["title"] = u["title"].strip()
    plan["total_seconds"] = round(sum(float(x["seconds"]) for x in plan["shots"]), 2)

    job_id = new_id("r")
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    plan_file = job_dir / "plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    with _lock:
        _jobs[job_id] = {"id": job_id, "kind": "regenerate", "key": f"job:{job_id}", "state": "running",
                         "created": time.time(), "source_key": source_key, "quality": quality,
                         "brief": plan.get("brief", {})}
        persist(job_id)
    spawn(job_id, [PY, str(RUNNER), "--mode", "render", "--job-dir", str(job_dir),
                   "--plan-file", str(plan_file), "--quality", quality,
                   "--source-key", source_key], job_dir)
    return job_id


def start_improve(source_key: str, instruction: str, quality: str) -> str:
    """把用户写在成片下的改进意见交给 A3，在源 plan 上重写一版再重出片。"""
    if GENERATE_DISABLED:
        raise ValueError(GENERATE_DISABLED_MSG)
    rd = run_dir_for(source_key)
    plan = read_json(rd / "plan.json") if rd else None
    if not plan:
        raise ValueError("源任务没有 plan.json，无法改进")
    job_id = new_id("i")
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    plan_file = job_dir / "plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (job_dir / "instruction.txt").write_text(instruction, encoding="utf-8")
    _enqueue({"id": job_id, "kind": "improve", "key": f"job:{job_id}",
              "created": time.time(), "source_key": source_key, "quality": quality,
              "brief": plan.get("brief", {}), "instruction": instruction},
             [PY, str(RUNNER), "--mode", "improve", "--job-dir", str(job_dir),
              "--plan-file", str(plan_file), "--instruction-file", str(job_dir / "instruction.txt"),
              "--quality", quality, "--source-key", source_key])
    return job_id


def status(job_id: str) -> dict | None:
    with _lock:
        j = _jobs.get(job_id)
        j = dict(j) if j else None
        ahead = next((i for i, q in enumerate(_queued()) if q["id"] == job_id), None)
    if j is None:
        return None
    job_dir = JOBS_DIR / job_id
    prog = read_json(job_dir / "run" / "progress.json") or {}
    finished = j.get("state") in ("done", "failed")
    elapsed = (j.get("finished", time.time()) - j["created"]) if finished else (time.time() - j["created"])
    stages = []
    for s in prog.get("stages", []):
        secs = round(s["ended"] - s["started"], 1) if s.get("ended") else None
        stages.append({"key": s["key"], "label": s.get("label") or STAGE_LABELS.get(s["key"], s["key"]),
                       "status": "done" if s.get("ended") else "running", "seconds": secs})
    known = [k for k in STAGE_LABELS if k not in ("done", "failed", "queued", "starting")]
    started_keys = {s["key"] for s in stages}
    for k in known:
        if k not in started_keys:
            stages.append({"key": k, "label": STAGE_LABELS[k], "status": "pending", "seconds": None})
    stage = prog.get("stage") or ("done" if j["state"] == "done" else
                                  "failed" if j["state"] == "failed" else
                                  "starting" if j["state"] == "running" else "queued")
    out = {"job": job_id, "key": j["key"], "kind": j["kind"], "brief": j.get("brief"),
           "state": j["state"], "stage": stage, "stage_label": STAGE_LABELS.get(stage, stage),
           "elapsed": round(elapsed, 1), "stages": stages, "error": j.get("error"),
           "created": j["created"]}
    if j["state"] == "queued":
        out["queue_ahead"] = ahead or 0
        out["stage_label"] = f"排队中（前面还有 {ahead} 个）" if ahead else "排队中（下一个就是你）"
    rd = job_dir / "run"
    if not rd.is_dir():   # jobs/ 被手工清理过：状态照给，产物部分留空，别让接口 500
        return out
    if j["state"] == "done":
        res = j.get("result") or read_json(job_dir / "result.json") or {}
        out["result"] = {"sidecar": res.get("sidecar") or read_json(rd / "sidecar.json") or {},
                         "names": res.get("names") or {},
                         "meta": run_meta(rd, j["key"]),
                         "plan": read_json(rd / "plan.json")}
    elif j["state"] == "failed":
        out["error"] = parse_error(j.get("error") or "")
        out["result"] = {"meta": run_meta(rd, j["key"]),
                         "plan": read_json(rd / "plan.json")}
    return out


# --------------------------------------------------------------------------- 问题反馈
def submit_feedback(payload: dict) -> dict:
    """落盘一条用户反馈（本地演示无账号：只存文件，不联网、不回显敏感信息）。"""
    ftype = str(payload.get("type") or "other")
    text = str(payload.get("text") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    if ftype not in FEEDBACK_TYPES:
        raise ValueError("反馈类型不合法")
    if not text:
        raise ValueError("反馈内容不能为空")
    if len(text) > FEEDBACK_MAX_TEXT:
        raise ValueError(f"反馈内容过长（>{FEEDBACK_MAX_TEXT} 字）")
    if len(contact) > FEEDBACK_MAX_CONTACT:
        raise ValueError(f"联系方式过长（>{FEEDBACK_MAX_CONTACT} 字）")
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    fid = f"fb{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(3).hex()}"
    body = json.dumps({
        "id": fid, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": ftype, "text": text, "contact": contact,
    }, ensure_ascii=False, indent=2)
    (FEEDBACK_DIR / f"{fid}.json").write_text(body, encoding="utf-8")
    threading.Thread(target=_feedback_push, args=(fid, body), daemon=True).start()
    return {"ok": True, "id": fid}


def _feedback_api():
    from modelscope_hub.api import HubApi
    return HubApi(token=FEEDBACK_REPO_TOKEN)


def _feedback_push(fid: str, body: str) -> None:
    """写穿到远端数据集；失败只记一行（不含密钥），本地文件已经落盘，不影响访客提交。"""
    if not (FEEDBACK_REPO and FEEDBACK_REPO_TOKEN):
        return
    try:
        _feedback_api().upload_file(
            FEEDBACK_REPO, "dataset", body.encode("utf-8"), f"feedback/{fid}.json",
            commit_message=f"feedback {fid}", disable_tqdm=True)
    except Exception as e:  # noqa: BLE001 - 网络/权限问题都只降级为本地存储
        print(f"[feedback] 写穿失败 {fid}: {type(e).__name__}", flush=True)


def feedback_restore() -> int:
    """启动时把远端数据集里本地缺的反馈拉回来；返回拉回条数。"""
    if not (FEEDBACK_REPO and FEEDBACK_REPO_TOKEN):
        return 0
    n = 0
    try:
        api = _feedback_api()
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        for fi in api.list_repo_files(FEEDBACK_REPO, "dataset"):
            name = Path(fi.path).name
            if not (fi.path.startswith("feedback/") and re.fullmatch(r"fb[\w-]+\.json", name)):
                continue
            if (FEEDBACK_DIR / name).exists():
                continue
            got = api.download_file(FEEDBACK_REPO, "dataset", fi.path, local_dir=FEEDBACK_DIR / ".restore")
            (FEEDBACK_DIR / name).write_bytes(Path(got).read_bytes())
            n += 1
    except Exception as e:  # noqa: BLE001
        print(f"[feedback] 恢复失败: {type(e).__name__}", flush=True)
    return n


def list_feedback(token: str = "") -> list[dict]:
    """反馈默认公开可读；联系方式只在口令配置且吻合时返回，免得访客填的邮箱/微信被所有人看到。"""
    show_contact = bool(FEEDBACK_READ_TOKEN) and hmac.compare_digest(
        token.encode(), FEEDBACK_READ_TOKEN.encode())
    items = []
    if FEEDBACK_DIR.is_dir():
        for f in sorted(FEEDBACK_DIR.glob("fb*.json"), reverse=True):
            d = read_json(f)
            if d:
                if not show_contact:
                    d.pop("contact", None)
                items.append(d)
    return items


def parse_error(raw: str) -> object:
    """jobrunner 把闸门未通过/知识点未命中编成 JSON 字符串透传，前端要能结构化显示。"""
    try:
        d = json.loads(raw)
        if isinstance(d, dict):
            return d
    except (TypeError, json.JSONDecodeError):
        pass
    return {"error": raw[:1200]}


# --------------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "ChengXiangMVP/0.1"
    protocol_version = "HTTP/1.1"
    head = False              # curl -I / 播放器探测用：只回头，不回体

    def log_message(self, fmt, *args):  # 只留一行式访问日志
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # ---- 基础输出
    def send_json(self, obj, code=200):
        # backslashreplace：子进程日志里混进的非法码点（manim/PowerShell 的中文输出）不能让接口 500
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8", "backslashreplace")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.head:
            return
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_text(self, text, code=400):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not self.head:
            self.wfile.write(body)

    def send_file(self, path: Path, download=False):
        if not path.is_file():
            return self.send_text("not found", 404)
        st = path.stat()
        size = st.st_size
        # 81-W1 加载优化：内容指纹 ETag（mtime+size）+ 可缓存 Cache-Control。
        # 产物媒体按角色 key 取到的是各自 run 目录里的文件，内容稳定，给 7 天新鲜期；
        # 页面三件套每次带 If-None-Match 回源校验，命中走 304——部署后不会用脏的旧 JS/CSS，
        # 二次打开也几乎零字节。旧片被手改覆盖时 mtime 变、ETag 变，缓存自动失效。
        etag = f'"{st.st_mtime_ns:x}-{size:x}"'
        suffix = path.suffix.lower()
        cache = "public, max-age=604800" if suffix in (".mp4", ".wav", ".png", ".jpg", ".srt") \
            else "no-cache"
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        start, end, partial = 0, size - 1, False
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                a, b = m.group(1), m.group(2)
                if not a and b:
                    # RFC 7233 后缀区间 bytes=-N：取文件**末尾** N 字节（原实现误当成 0..N）
                    start = max(0, size - int(b))
                    end = size - 1
                else:
                    start = int(a) if a else 0
                    end = int(b) if b else size - 1
                    end = min(end, size - 1)
                partial = start > 0 or end < size - 1
        if start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(end - start + 1))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download:
            self.send_header("Content-Disposition",
                             "attachment; filename*=UTF-8''" + quote(path.name))
        self.end_headers()
        if self.head:
            return
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---- 路由
    def do_GET(self):
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.split("/") if p]
        try:
            if not parts or parts[0] in ("index.html", "app.js", "styles.css"):
                name = "index.html" if not parts else parts[0]
                if not (WEB_DIR / name).is_file():
                    return self.send_text("not found", 404)
                return self.send_file(WEB_DIR / name)
            if parts[0] == "api" and len(parts) > 1:
                return self.api_get(parts[1:])
            self.send_text("not found", 404)
        except Exception as e:  # noqa: BLE001 演示页面宁可得 500 也别让线程挂掉
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)
            return

    def do_HEAD(self):
        self.head = True
        try:
            self.do_GET()
        finally:
            self.head = False

    def do_POST(self):
        parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
        try:
            if parts[:2] == ["api", "generate"]:
                return self.api_generate()
            if parts[:2] == ["api", "regenerate"]:
                return self.api_regenerate()
            if parts[:2] == ["api", "improve"]:
                return self.api_improve()
            if parts[:2] == ["api", "feedback"]:
                return self.api_feedback()
            self.send_json({"error": "unknown endpoint"}, 404)
        except Exception as e:  # noqa: BLE001
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def api_get(self, sub: list[str]):
        if sub[0] == "topics":
            return self.send_json({
                "subjects": [{"value": v, "label": l} for v, l in SUBJECTS],
                "grades": [{"value": v, "label": l} for v, l in GRADES],
                "styles": [{"value": v, "label": l} for v, l in STYLES],
                "durations": DURATIONS,
                "duration_labels": {str(k): v for k, v in DURATION_LABELS.items()},
                "qualities": [{"value": v, "label": l} for v, l in QUALITIES],
                "topics": kp_entries(),
                # 时间轴常量随枚举一起下发，前端不再各写一份 —— 改 SHOT_HEAD/SHOT_TAIL 不必动 app.js。
                "spec_version": SPEC_VERSION,
                "shot_head": SHOT_HEAD, "shot_tail": SHOT_TAIL,
                "min_shot_seconds": MIN_SHOT_SECONDS,
                # 生成开关如实下发：前端据此在表单里显示「仅展映 / 生成未开放」横幅，不在前端特判环境变量。
                "generate_disabled": GENERATE_DISABLED,
                "generate_disabled_msg": GENERATE_DISABLED_MSG if GENERATE_DISABLED else "",
                "note": "知识点可自由填写：库内命中走库内条目，库外由模型起草（有教材检索命中时标注命中出处，未经人工核对；没命中则如实标注未核对出处）。"})
        if sub[0] == "gallery":
            return self.send_json({"items": gallery()})
        if sub[0] == "feedback":
            token = (parse_qs(urlparse(self.path).query).get("token") or [""])[0]
            return self.send_json({"items": list_feedback(token)})
        if sub[0] == "status" and len(sub) == 2:
            st = status(sub[1])
            if st is None:
                st = self.restore_from_disk(sub[1])
            return self.send_json(st or {"error": "no such job"}, 404 if st is None else 200)
        if sub[0] == "plan" and len(sub) == 2:
            key = sub[1] if ":" in sub[1] else ":".join(sub[1:2])
            rd = run_dir_for(key)
            plan = read_json(rd / "plan.json") if rd else None
            if not plan:
                return self.send_json({"error": "该 run 没有 plan.json"}, 404)
            return self.send_json({"key": sub[1], "plan": plan, "meta": run_meta(rd, sub[1])})
        if sub[0] == "file" and len(sub) == 3:
            rd = run_dir_for(sub[1])
            if rd is None:
                return self.send_text("bad key", 400)
            role = sub[2]
            if role not in ROLE_ORDER:
                return self.send_text("bad role", 400)
            f = run_files(rd, sub[1]).get(role)
            if not f:
                return self.send_text("该 run 没有这个产物", 404)
            target = Path(f["path"]).resolve()
            if not str(target).startswith(str(rd.resolve())):
                return self.send_text("bad path", 400)
            return self.send_file(target, download=bool(re.search(r"[?&]download", self.path)))
        return self.send_json({"error": "unknown endpoint"}, 404)

    @staticmethod
    def restore_from_disk(job_id: str):
        """服务重启后内存表为空，但 jobs/<id>.json 还在：至少让状态查询不 404。"""
        f = JOBS_DIR / f"{job_id}.json"
        if not f.is_file() or not NAME_RE.match(job_id):
            return None
        j = read_json(f) or {}
        with _lock:
            _jobs[job_id] = j
        return status(job_id)

    def read_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > 4_000_000:
            raise ValueError("请求体过大")
        raw = self.rfile.read(n) if n else b"{}"
        # 浏览器一律 UTF-8；但这台机器上 curl/PowerShell 常按 GBK 送中文，兜一下免得演示当场报错
        for enc in ("utf-8", "cp936"):
            try:
                return json.loads(raw.decode(enc) or "{}")
            except UnicodeDecodeError:
                continue
        return json.loads(raw.decode("utf-8", "replace") or "{}")

    def api_generate(self):
        b = self.read_body()
        quality = b.get("quality", "fullhd")
        if quality not in dict(QUALITIES):
            quality = "fullhd"

        # 只把 Brief 认识的字段交给它：quality 等运行参数不进契约。
        # Brief.__post_init__ 会把表单/JSON 里的数字字符串归一化，所以 target_seconds 传字符串不会 500。
        fields = {k: v for k, v in b.items() if k in Brief.__dataclass_fields__}
        try:
            brief = Brief(**fields)
        except TypeError as e:
            return self.send_json({"error": f"输入契约字段不合法：{e}", "findings": [], "candidates": []}, 400)

        errs = brief.validate()
        if errs:
            return self.send_json({"error": "输入契约校验未通过", "findings": errs, "candidates": []}, 400)

        # 知识点口径（2026-10-18）：库内命中就用库内容并把 topic 归一化成条目正式名；
        # 库里没有不再拒绝请求——任务里由 K0 起草一条 origin=model_draft、refs 为空的条目
        # 再走同一条链路（pipeline/kp_draft.py）。起草需要模型，未开 K0/没配密钥时任务会
        # 以人话错误结束，不在这里假装能生成。
        hit = None
        try:
            hit = knowledge.load(brief.subject, brief.topic, brief.grade)
        except knowledge.KnowledgeNotFound:
            pass
        except ValueError as e:  # 库文件损坏/缺字段：也归为 4xx，不把 traceback 抛给用户
            return self.send_json({"error": f"知识点库校验失败：{e}", "findings": [], "candidates": []}, 400)
        if hit:
            brief.topic = hit["topic"]  # 归一化为库内正式条目名
        brief_dict = brief.__dict__
        try:
            job_id = start_generate(brief_dict, quality)
        except ValueError as e:  # 只有 GENERATE_DISABLED 会走到这里
            return self.send_json({"error": str(e), "findings": [], "candidates": []}, 409)
        self.send_json({"job": job_id, "key": f"job:{job_id}", "state": _jobs.get(job_id, {}).get("state", "running"),
                        "brief": brief_dict, "knowledge": hit,
                        "draft": hit is None, "quality": quality})

    def api_regenerate(self):
        b = self.read_body()
        source = str(b.get("source_key") or b.get("job") or "")
        shots = b.get("shots")
        if not isinstance(shots, list) or not shots:
            return self.send_json({"error": "shots 不能为空"}, 400)
        quality = b.get("quality", "fullhd")
        if quality not in dict(QUALITIES):
            quality = "fullhd"
        try:
            job_id = start_regenerate(source, shots, quality)
        except (ValueError, TypeError) as e:
            return self.send_json({"error": str(e)}, 400)
        self.send_json({"job": job_id, "key": f"job:{job_id}", "state": "running", "source_key": source})


    def api_improve(self):
        b = self.read_body()
        source = str(b.get("source_key") or b.get("job") or "")
        instruction = str(b.get("instruction") or "").strip()
        if not instruction:
            return self.send_json({"error": "改进意见不能为空"}, 400)
        if len(instruction) > 200:
            return self.send_json({"error": "改进意见太长（最多 200 字）"}, 400)
        quality = b.get("quality", "fullhd")
        if quality not in dict(QUALITIES):
            quality = "fullhd"
        try:
            job_id = start_improve(source, instruction, quality)
        except (ValueError, TypeError) as e:
            return self.send_json({"error": str(e)}, 400)
        self.send_json({"job": job_id, "key": f"job:{job_id}", "state": _jobs.get(job_id, {}).get("state", "running"),
                        "source_key": source})


    def api_feedback(self):
        try:
            return self.send_json(submit_feedback(self.read_body()))
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)


def warm_cache() -> None:
    """把磁盘上已有的任务记录读进内存，重启服务后仍能查状态。"""
    if not JOBS_DIR.is_dir():
        return
    for f in sorted(JOBS_DIR.glob("*.json")):
        j = read_json(f)
        if j and j.get("id"):
            with _lock:
                _jobs[j["id"]] = j
                # 重启前在跑的任务子进程已随旧服务消失，不收尾就会永远占着并发名额
                if j.get("state") == "running":
                    j.update(state="failed", finished=time.time(),
                             error="服务重启时该任务仍在运行，已中断；请重新发起")
                    persist(j["id"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    warm_cache()
    dispatch()  # 重启前排着队的任务（argv 已落盘）接着跑
    if FEEDBACK_REPO:
        print(f"[feedback] 从远端恢复 {feedback_restore()} 条", flush=True)
    httpd = ThreadingHTTPServer((a.host, a.port), Handler)
    httpd.daemon_threads = True
    print(f"澄象 MVP 演示服务： http://{a.host}:{a.port}  (jobs -> {JOBS_DIR})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
