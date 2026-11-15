# -*- coding: utf-8 -*-
"""flow v2 的 run 状态机：mvp/out/<run>/handoff.json 的读写与原子落盘。

状态文件结构（Spec_AgentFlow_v2 第 11 节：编排逻辑必须沉淀为代码，不许只留在聊天记录里）：
{
  "run": "<run 目录名>",
  "kp_id": "<subject>/<kp 文件名，可空>",
  "brief": {"subject","grade","topic","seconds","style"},
  "stages": {"<STAGE>": {"status": "pending|running|pass|fail|blocked",
                          "verdict": "PASS|FAIL|BLOCKED|None",
                          "report": "reports/<STAGE>.md",
                          "responses": ["reports/<STAGE>_response.md", ...],
                          "retries": 0, "round": 0}},
  "route_next": "<下一个棒名 | DONE | BLOCKED>"
}
写入一律走 临时文件 + os.replace（同盘原子替换），中断不产生半截 JSON。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

STATUSES = ("pending", "running", "pass", "fail", "blocked")

STAGE_ORDER = ("K1", "K2", "P", "V0", "M1", "M2", "A4", "R", "A8", "S22")


def _stage_init() -> dict:
    return {"status": "pending", "verdict": None, "report": None,
            "responses": [], "retries": 0, "round": 0}


def new_state(run: str, kp_id: str, brief: dict) -> dict:
    """生成初始 handoff 状态：全部棒 pending，route_next=链条第一棒。"""
    return {
        "run": run,
        "kp_id": kp_id,
        "brief": brief,
        "stages": {name: _stage_init() for name in STAGE_ORDER},
        "route_next": STAGE_ORDER[0],
    }


def atomic_write_json(path: Path, obj: dict) -> None:
    """临时文件 + os.replace 原子写（同目录 tmp，保证同盘 rename 原子性）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def handoff_path(run_dir: Path) -> Path:
    return Path(run_dir) / "handoff.json"


def load(run_dir: Path) -> dict:
    p = handoff_path(run_dir)
    if not p.exists():
        raise FileNotFoundError(f"handoff.json 不存在：{p}（先用 --init 建 run）")
    return json.loads(p.read_text(encoding="utf-8"))


def save(run_dir: Path, state: dict) -> None:
    atomic_write_json(handoff_path(run_dir), state)


def init_run(run_dir: Path, kp_id: str, brief: dict) -> dict:
    """建 run 目录 + brief.json + handoff.json 初始态，返回状态。"""
    run_dir = Path(run_dir)
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    state = new_state(run_dir.name, kp_id, brief)
    atomic_write_json(run_dir / "brief.json", brief)
    save(run_dir, state)
    return state


def stage(state: dict, name: str) -> dict:
    """取某棒状态槽；未注册的棒名先补 pending（路由表可引入新棒）。"""
    return state["stages"].setdefault(name, _stage_init())


def mark(state: dict, name: str, *, status: str, verdict: str | None = None,
         report: str | None = None, route_next: str | None = None) -> None:
    """迁移某棒状态并（可选）改写 route_next。不落盘，由调用方 save。"""
    assert status in STATUSES, f"非法状态 {status}"
    st = stage(state, name)
    st["status"] = status
    if verdict is not None:
        st["verdict"] = verdict
    if report is not None:
        st["report"] = report
    if route_next is not None:
        state["route_next"] = route_next


def bump_round(state: dict, name: str) -> int:
    """打回重进某棒时 round+1，返回新值。O 路由表：每环 ≤3 轮。"""
    st = stage(state, name)
    st["round"] = int(st.get("round", 0)) + 1
    return st["round"]
