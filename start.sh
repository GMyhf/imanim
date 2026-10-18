#!/usr/bin/env bash
# 创空间 docker 类型的启动命令。平台侧约定：进程必须绑 0.0.0.0、端口 7860（8080 被平台占用）。
set -euo pipefail
cd /app

# 在线生成默认开放（用户 2026-10-18 决定）。密钥 QX_LLM_API_KEY 必须经创空间环境变量注入，
# 不进镜像；没配密钥时生成会如实报错。想临时关闭：环境变量 MVP_GENERATE_DISABLED=1。
# 库外知识点由 K0 起草，需 QX_LLM_K0=1。
export QX_LLM_K0="${QX_LLM_K0:-1}"

exec python mvp/web/server.py --host 0.0.0.0 --port "${PORT:-7860}"
