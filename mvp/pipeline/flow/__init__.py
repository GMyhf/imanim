# -*- coding: utf-8 -*-
"""flow v2 棒次自动化桥（编排器）。

生产形态铁律（Spec_AgentFlow_v2 第 11 节）：网站后端 → 主 agent（O，编排/路由/验收）
→ 子 agent（棒次操作员）→ 网关钉死模型（语义产出）。本包把试制期验证过的派单/路由/审计
规程沉淀为代码：handoff=run 状态机；stages=棒次注册表；bridge=执行器。

CLI（cwd=mvp）：
  python -m pipeline.flow --run <out 下 run 名或绝对路径> --init --subject S --grade G --topic T --seconds N [--kp-id ID]
  python -m pipeline.flow --run <dir> --auto            # 连续推进；遇独立性棒打印 SPAWN_SUBAGENT 停下
  python -m pipeline.flow --run <dir> --stage K2        # 子 agent 上下文里执行指定棒
"""
