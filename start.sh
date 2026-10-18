#!/usr/bin/env bash
# 创空间 docker 类型的启动命令。平台侧约定：进程必须绑 0.0.0.0、端口 7860（8080 被平台占用）。
set -euo pipefail
cd /app

# 配音已换网关 HTTP（audio/tts.py，Linux 可用），但字体替代+字距重测、mux 烧录字体写死
# 两条阻断项未清（README「移植阻断项」② ③ ④）→ 默认只出画廊。
# 想开生成入口：先完成 README push 检查单的两个前置步骤（字距重测、QX_LLM_API_KEY 经
# 创空间环境变量注入——密钥不进镜像），再把 MVP_ALLOW_GENERATE 置 1。
if [ "${MVP_ALLOW_GENERATE:-0}" != "1" ]; then
  export MVP_GENERATE_DISABLED=1
fi

exec python mvp/web/server.py --host 0.0.0.0 --port "${PORT:-7860}"
