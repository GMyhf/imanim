#!/usr/bin/env bash
# 创空间 docker 类型的启动命令。平台侧约定：进程必须绑 0.0.0.0、端口 7860（8080 被平台占用）。
set -euo pipefail
cd /app

# 在线生成默认开放（用户 2026-10-18 决定）。两套密钥必须经创空间环境变量注入、不进镜像：
# 推理后端 QX_LLM_API_KEY（缺省 ModelScope，可用 QX_LLM_PROVIDER 切回 gateway），
# 配音网关 QX_TTS_API_KEY（ModelScope 无 TTS 路由）。没配密钥时生成会如实报错。
# 想临时关闭：环境变量 MVP_GENERATE_DISABLED=1。
# 库外知识点由 K0 起草，需 QX_LLM_K0=1；出片后的「改进」需 A3 重写分镜，需 QX_LLM_A3=1；
# 配音稿（朗读稿）按整镜上下文由推理后端改写，需 QX_LLM_VOICEOVER=1（关闭/失败回退 tts 正则兜底）。
# 三个都默认开：没配密钥时生成/改进会如实报错、朗读稿回退正则，画廊不受影响。
export QX_LLM_K0="${QX_LLM_K0:-1}"
export QX_LLM_A3="${QX_LLM_A3:-1}"
export QX_LLM_VOICEOVER="${QX_LLM_VOICEOVER:-1}"

# 阻断项③运行时化：量当前字体栈（Noto Serif CJK SC + TeX Gyre Termes）的字距，
# 落盘 font_metrics_cache.json，font_metrics.metrics_for 未标定时读它。量不出来就如实保持
# "重测前只当画廊"（生成照旧报 FontMetricsError），画廊不受影响。
# 81-W1 冷启动提速：实测要拉起 manim 排版采样，每次开机重测白白多花几十秒。
# 判据与 font_metrics 现码同源（load_cache 只认「pair 齐全 + metrics 五键可转 float」，
# current_pair 读 MVP_TEXT_FONT/MVP_LATIN_FONT）：缓存 JSON 已存在、结构完整、且其中
# 记录的字体对与当前环境变量字体对一致 → 标定已可用，跳过重测；字体对变了（换镜像/换字体）
# 视同版本不匹配，照旧重测覆盖。
CACHE=mvp/font_metrics_cache.json
if python -c '
import sys
sys.path.insert(0, "mvp")
import font_metrics as FM
FM.load_cache()  # 缓存缺失/损坏/键不全 → 不注册，下面判定不到当前字体对
sys.exit(0 if FM.current_pair() in FM.CALIBRATED else 1)
'; then
  echo "[fontmetrics] 缓存标定命中当前字体对，跳过重测（81-W1 冷启动提速）" >&2
else
  python mvp/tools_fontmetrics.py --out "$CACHE" \
    || echo "[fontmetrics] 标定失败：在线生成保持关闭（画廊不受影响）" >&2
fi

exec python mvp/web/server.py --host 0.0.0.0 --port "${PORT:-7860}"
