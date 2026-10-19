# -*- coding: utf-8 -*-
"""flow CLI 入口：python -m pipeline.flow --run <dir> [--init ... | --stage X | --auto]。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bridge, handoff
from .stages import ROOT

OUT_ROOT = ROOT / "mvp" / "out"


def resolve_run_dir(run: str) -> Path:
    """--run 接受绝对路径或 mvp/out/ 下的 run 目录名。"""
    p = Path(run)
    return p if p.is_absolute() else OUT_ROOT / run


def resolve_text(value: str) -> str:
    """--focus 一类长中文原文参数：以 @ 开头按文件读（台账原文逐字），否则原样当文本。
    多行中文走命令行极易被 shell 截断/转义，正路是从 Spec/台账文件逐字读。"""
    if value.startswith("@"):
        return Path(value[1:]).read_text(encoding="utf-8").strip()
    return value


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.flow", description="flow v2 棒次自动化桥")
    ap.add_argument("--run", required=True, help="run 目录（绝对路径或 mvp/out/ 下的名字）")
    ap.add_argument("--init", action="store_true", help="建 run：brief.json + handoff.json 初始态")
    ap.add_argument("--subject")
    ap.add_argument("--grade")
    ap.add_argument("--topic")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--kp-id", default="", help="库内已有 KP：<subject>/<文件名>（可空=由 K1 撰写）")
    ap.add_argument("--style", default="{}", help="风格参数 JSON（如 {\"theme\":\"light\"}）")
    ap.add_argument("--focus", default="", help="本题专题/验收点原文（台账 Spec 第 10 节逐字，进 brief.focus；"
                                                "@path 从文件读，避免命令行带多行中文）")
    ap.add_argument("--stage", help="执行指定棒（独立性棒由主 agent 另起的子 agent 上下文调用本入口）")
    ap.add_argument("--dispatch", help="渲染指定棒的操作员派单 reports/<STAGE>_dispatch.md（主 agent 原文粘贴派子 agent）")
    ap.add_argument("--auto", action="store_true", help="从 handoff 当前棒连续推进")
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    run_dir = resolve_run_dir(args.run)

    if args.init:
        missing = [k for k in ("subject", "grade", "topic") if not getattr(args, k)] + \
                  (["seconds"] if args.seconds is None else [])
        if missing:
            ap.error(f"--init 需要 --{' --'.join(missing)}")
        brief = {"subject": args.subject, "grade": args.grade, "topic": args.topic,
                 "seconds": args.seconds, "style": json.loads(args.style),
                 "focus": resolve_text(args.focus)}
        handoff.init_run(run_dir, args.kp_id, brief)
        print(f"INIT: {run_dir}（route_next=K1，brief={json.dumps(brief, ensure_ascii=False)}）")
        return 0

    if not handoff.handoff_path(run_dir).exists():
        print(f"BLOCKED: {run_dir} 没有 handoff.json，先 --init", file=sys.stderr)
        return 1

    if args.dispatch or args.focus:
        state = handoff.load(run_dir)
        if args.focus:                       # 已建 run 补专题要求：写回 brief 再渲染
            state.setdefault("brief", {})["focus"] = resolve_text(args.focus)
            handoff.save(run_dir, state)
        if not args.dispatch:
            print(f"FOCUS: {run_dir} brief.focus 已写入（{len(resolve_text(args.focus))} 字）")
            return 0
        rel = bridge.write_dispatch(run_dir, args.dispatch)
        print(f"DISPATCH: {run_dir / rel} (paste verbatim as subagent prompt)")
        return 0

    if args.stage:
        nxt = bridge.run_stage(run_dir, args.stage, isolated_ok=True)
        state = handoff.load(run_dir)
        slot = handoff.stage(state, args.stage)
        print(f"{args.stage}: verdict={slot.get('verdict')} next={nxt}（报告 {slot.get('report')}）")
        # 下一棒若是独立性棒：把派单指令直接打给主 agent（prompt 文件已落盘可引用）
        if nxt in bridge.STAGES and bridge.STAGES[nxt].needs_isolated_context:
            files = bridge.prepare_isolated(run_dir, nxt)
            print(bridge.spawn_line(run_dir, nxt, files))
        return 0 if slot.get("verdict") == "PASS" else 1

    if args.auto:
        return bridge.auto(run_dir)

    # 无 --stage/--auto：只打印当前态
    state = handoff.load(run_dir)
    print(json.dumps({k: state[k] for k in ("run", "kp_id", "route_next")}, ensure_ascii=False))
    for name, slot in state["stages"].items():
        print(f"  {name:4s} {slot['status']:8s} verdict={slot['verdict']} round={slot['round']} retries={slot['retries']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
