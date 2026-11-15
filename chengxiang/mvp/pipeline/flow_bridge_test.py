# -*- coding: utf-8 -*-
"""flow v2 自动化桥单元测试：handoff 状态机 + stages 注册表。

用法（cwd=mvp）：python pipeline/flow_bridge_test.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.flow import handoff
from pipeline.flow.stages import STAGES


def test_handoff_new_state():
    """handoff.new_state 应创建合法的 run 状态字典。"""
    brief = {"subject": "math", "grade": "H2", "topic": "复数的定义", "seconds": 120}
    state = handoff.new_state("test_run", "kp.math.complex_numbers", brief)
    assert state["run"] == "test_run"
    assert state["kp_id"] == "kp.math.complex_numbers"
    assert state["brief"]["topic"] == "复数的定义"
    assert state["route_next"] == "K1"
    print("PASS: test_handoff_new_state")


def test_handoff_stage_ops():
    """handoff.stage/mark 应能读写单个棒次槽位。"""
    brief = {"topic": "test"}
    state = handoff.new_state("test", "kp.test", brief)
    
    slot = handoff.stage(state, "K1")
    assert slot["status"] == "pending"

    handoff.mark(state, "K1", status="pass", verdict="PASS", report="reports/K1.md")
    slot = handoff.stage(state, "K1")
    assert slot["status"] == "pass"
    assert slot["verdict"] == "PASS"
    print("PASS: test_handoff_stage_ops")


def test_stages_registry():
    """STAGES 注册表应包含所有 flow v2 棒次。"""
    expected_names = ["K1", "K2", "P", "V0", "M1", "M2", "A4", "R", "A8", "S22"]
    for name in expected_names:
        assert name in STAGES, f"Stage {name} missing from registry"
        st = STAGES[name]
        assert st.name == name
    print(f"PASS: test_stages_registry ({len(expected_names)} stages)")


def test_deterministic_stages():
    """确定性棒次（A4/R）应标记为 deterministic。"""
    a4 = STAGES["A4"]
    assert a4.deterministic is True

    r = STAGES["R"]
    assert r.deterministic is True
    print("PASS: test_deterministic_stages")


def test_gateway_stages():
    """网关棒次应有 max_tokens 配置（抗 524）。"""
    for name in ["K1", "K2", "V0", "M1", "M2"]:
        st = STAGES[name]
        assert st.max_tokens > 0, f"{name} should have max_tokens config"
    print("PASS: test_gateway_stages")


def test_full_lifecycle():
    """完整生命周期：init_run -> 推进几个棒次 -> 检查状态。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "lifecycle_test"
        
        brief = {"subject": "physics", "grade": "H1", "topic": "牛顿第二定律", "seconds": 120}
        state = handoff.init_run(run_dir, "kp.physics.newton_second", brief)
        assert (run_dir / "handoff.json").exists()
        assert (run_dir / "brief.json").exists()

        reports_dir = run_dir / "reports"
        handoff.mark(state, "K1", status="pass", verdict="PASS", report="reports/K1.md")
        (reports_dir / "K1.md").write_text("# K1 Report\nPASS", encoding="utf-8")
        handoff.save(run_dir, state)

        loaded = handoff.load(run_dir)
        assert loaded["stages"]["K1"]["status"] == "pass"
        assert loaded["stages"]["K1"]["verdict"] == "PASS"

        handoff.mark(state, "A4", status="pass", verdict="PASS", report="reports/A4.md")
        (reports_dir / "A4.md").write_text("# A4 Review", encoding="utf-8")
        handoff.save(run_dir, state)

        loaded = handoff.load(run_dir)
        k1_pass = loaded["stages"]["K1"]["status"] == "pass"
        a4_pass = loaded["stages"]["A4"]["status"] == "pass"
        assert k1_pass and a4_pass
    print("PASS: test_full_lifecycle")


if __name__ == "__main__":
    tests = [
        test_handoff_new_state,
        test_handoff_stage_ops,
        test_stages_registry,
        test_deterministic_stages,
        test_gateway_stages,
        test_full_lifecycle,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            failed.append((t.__name__, e))
            print(f"FAILED {t.__name__}: {e}")

    if failed:
        print(f"\n{len(failed)} test(s) failed:")
        for name, err in failed:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed!")
