#!/usr/bin/env bash
# 创空间 docker 类型的启动命令。平台侧约定：进程必须绑 0.0.0.0、端口 7860（8080 被平台占用）。
set -euo pipefail
cd /app

# 在线生成默认开放（用户 2026-10-18 决定）。密钥 QX_LLM_API_KEY 必须经创空间环境变量注入，
# 不进镜像；没配密钥时生成会如实报错。想临时关闭：环境变量 MVP_GENERATE_DISABLED=1。
# 库外知识点由 K0 起草，需 QX_LLM_K0=1；出片后的「改进」需 A3 重写分镜，需 QX_LLM_A3=1。
# 两个都默认开：没配密钥时生成/改进会各自如实报错，画廊不受影响。
export QX_LLM_K0="${QX_LLM_K0:-1}"
export QX_LLM_A3="${QX_LLM_A3:-1}"

# 阻断项③运行时化：起服务前量一次当前字体栈（Noto Serif CJK SC + TeX Gyre Termes）的字距，
# 落盘 font_metrics_cache.json，font_metrics.metrics_for 未标定时读它。量不出来就如实保持
# "重测前只当画廊"（生成照旧报 FontMetricsError），画廊不受影响。
python mvp/tools_fontmetrics.py --out mvp/font_metrics_cache.json \
  || echo "[fontmetrics] 标定失败：在线生成保持关闭（画廊不受影响）" >&2

exec python mvp/web/server.py --host 0.0.0.0 --port "${PORT:-7860}"
