# 澄象 MVP · 魔搭创空间（docker 类型）镜像
#
# 平台硬约束 [官方 Ref_Deploy §1]：必须监听 0.0.0.0:7860，8080 被平台占用；首个 Docker 构建约 3~5 分钟；
# docker 类型前置条件是账号已完成阿里云绑定 + 实名认证。
#
# 构建上下文 = deploy/build_space.py 组装出来的目录（mvp/ 源码 + mvp/out/ 画廊成片 + 本文件）。
# ★ 本镜像在本机**未经 docker 构建验证**：这台机器上没有 docker（`docker: command not found`），
#   pip/apt 的可安装性按 manim 官方 Linux 依赖列 + Debian bookworm 包名写对，第一次构建就可能在
#   pycairo/manimpango 上翻车，翻车时先看 requirements.txt 顶部注释的两条退路。
#
# 密钥纪律：API 密钥**只经创空间的环境变量注入**，不写进本文件、不 COPY 进镜像、不落任何日志。
# 两套后端互不相串（2026-10-20 换血）：
#   QX_LLM_PROVIDER=modelscope|gateway    —— 缺省 modelscope（DeepSeek/Qwen 推理网关）
#   QX_LLM_API_KEY / QX_LLM_KEY_FILE      —— 活动 LLM 后端密钥
#   QX_TTS_API_KEY / QX_TTS_KEY_FILE      —— 配音 gateway 密钥（ModelScope 无 TTS 路由）
# 下面 ENV 只放非敏感占位/默认值。
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    MVP_FFMPEG_DIR=/usr/bin \
    MPLCONFIGDIR=/tmp/mpl \
    # 字体替代映射（SimSun/Times New Roman 是商业字体，不进镜像，见 README 阻断项②）：
    #   SimSun（中文宋体）      → Noto Serif CJK SC（fonts-noto-cjk）
    #   Times New Roman（拉丁） → TeX Gyre Termes（fonts-texgyre，Times 度量兼容）
    # ★ 换字体是硬依赖触发器：scene.py 的 _DELTA_* 与 review.py 的 UNIT_CJK/UNIT_ASCII
    #   都标定在 SimSun+Times 上，容器换字体后由 start.sh 起服务前自动跑一次字距探针
    #   （tools_fontmetrics.py --out font_metrics_cache.json），font_metrics.metrics_for
    #   未标定时读这份缓存注册进来；探针跑不出就如实保持"重测前只当画廊"（生成报
    #   FontMetricsError），不用人进容器手填表。
    MVP_TEXT_FONT="Noto Serif CJK SC" \
    MVP_LATIN_FONT="TeX Gyre Termes" \
    MVP_SUB_FONT="Noto Serif CJK SC"
    # 在线生成还需要（在创空间"环境变量"页配置，不写在这里）：
    #   QX_LLM_PROVIDER                  —— 可选，缺省 modelscope；回退旧网关写 gateway
    #   QX_LLM_API_KEY=<推理网关密钥>    —— 或 QX_LLM_KEY_FILE=<容器内密钥文件路径>
    #   QX_LLM_BASE_URL                  —— 可选，缺省随 provider；容器需出网可达
    #   QX_TTS_API_KEY=<配音网关密钥>    —— 或 QX_TTS_KEY_FILE；配音固定走 gateway
    #   QX_TTS_BASE_URL                  —— 可选，缺省 https://api.openai-next.com
    #   MVP_ALLOW_GENERATE=1             —— 可选，置 1 才开生成入口（见 start.sh）

# ffmpeg：混流与字幕烧录（mux.py 按 os.name 选 ffmpeg/ffmpeg.exe，Linux 走 PATH）
# fonts-noto-cjk：CJK 字形（含 Noto Serif CJK SC）；fonts-texgyre：TeX Gyre Termes；
#   fonts-liberation：Liberation Serif，Termes 不可用时的兜底替代
# libcairo2-dev / libpango1.0-dev / pkg-config / gcc：pycairo 与 manimpango 在 Linux 上没有现成轮子，
#   pip 会现场编译，这三个 + gcc 是编译前提（manim 官方 Linux 安装说明同源）
# texlive 六件套（Spec_Video_Defaults 缺口 1；82-F1 起公式/推导走 LaTeX）：
#   模板是 xelatex + xeCJK + mathptmx（scene.py 的 _tex_math，中文下标靠 xeCJK 的
#   \hbox{\fontsize{0.5em}...\selectfont 停} 才缩小下沉），所以除了
#   texlive-latex-base（standalone）+ texlive-latex-extra + texlive-fonts-recommended
#   （amssymb/mathptmx）+ dvisvgm，还必须补 texlive-xetex（xelatex 本体）与
#   texlive-lang-chinese（xeCJK、ctex 宏包）。中文字体由 fonts-noto-cjk 提供，容器里
#   没有 SimSun，模板的 \IfFontExistsTF 会自动落到 Noto Serif CJK SC。
#   Linux 走 texlive 全量预装，没有 MiKTeX"渲染时才按需联网下宏包"的问题；
#   缺 TeX / 缺 xelatex / 缺 dvisvgm 时管线自动退回 Pango 排版（rich），不会崩。
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fontconfig \
        fonts-noto-cjk fonts-texgyre fonts-liberation \
        texlive-latex-base texlive-latex-extra texlive-fonts-recommended dvisvgm \
        texlive-xetex texlive-lang-chinese \
        libcairo2-dev libpango1.0-dev pkg-config gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 源码 + 语料 + 已渲染好的画廊成片（画廊模式不依赖 TTS/密钥，见 README）
COPY mvp /app/mvp
COPY start.sh /app/start.sh

EXPOSE 7860
CMD ["bash", "/app/start.sh"]
