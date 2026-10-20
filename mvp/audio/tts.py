"""A6 配音：网关模型 TTS（qwen3-tts-flash，OpenAI 风格 /v1/audio/speech）。

换掉 Windows SAPI 的理由：SAPI 只能跑在装了中文语音包的 Windows 桌面上，创空间容器
（Linux）跑不了；网关 TTS 走 HTTP，任何部署环境都能出中文语音。语音时长用 wave 头直接
读，不额外依赖 ffprobe。

TTS 固定在赛方 gateway 网关：ModelScope 推理网关没有 /v1/audio/speech 路由（实测 404）。
LLM 后端切到 modelscope 后，配音仍用 gateway 的端点与密钥——QX_TTS_BASE_URL /
QX_TTS_API_KEY（或 QX_TTS_KEY_FILE）独立覆盖，与 llm_client 的活动 provider 解耦。

SubTask #60-A 实测口径（照此实现，勿凭文档改）：
1. 响应头 Content-Type 写 audio/mpeg，实际返回体是 RIFF/WAV（pcm_s16le、24000Hz、mono、
   16bit）——按字节解析，别信头。
2. 网关 WAV 头里 RIFF/data 两个 size 字段是 2^31 量级的溢出值：wave 模块按它算 nframes
   会读出几小时的假时长（getnframes 直读实测 44739s），mux 拼接也会拿到畸形帧数。落盘前
   必须把这两个字段重写成真实字节数。
3. speed 参数无效：同文本带 speed=2.0 的返回时长与自然语速一样长（甚至更长，同参数多次
   调用时长抖动 ±17%），所以 rate 档位不映射 speed——照收但忽略，一律按自然语速合成。
   run.py 依据 SPEED_SUPPORTED 在 log["tts"]["note"] 里如实说明。
4. /v1/audio/speech 有间歇性 403/429/5xx（连续重试 3~6 次能成功）→ 合成带 4 次重试、
   间隔 3s 起翻倍退避，否则演示现场会随机挂。
"""

from __future__ import annotations

import http.client
import json
import os
import re
import struct
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

from pipeline import ir, llm_client

VOICE = "cherry"
MODEL = "qwen3-tts-flash"
# ModelScope 无 TTS 路由，配音固定回退赛方 gateway；密钥/端点不再借用活动 LLM provider。
TTS_PROVIDER = "gateway"
# 2026-10-18 T0 实测：auto 语言判定把含数学术语（x²、i、ℂ）的中文口播判成日语。
# 钉死 language_type=zh（qwen3-tts 文档字段名），env QX_TTS_LANGUAGE 可覆盖。
LANGUAGE = "zh"
# speed 探测结论见模块 docstring：网关不支持提速档，rate 照收但忽略。
# 唯一事实源是 ir.SPEED_LADDER——A4 闸门的语速天花板由它派生，配音引擎与闸门不许各说各话。
SPEED_SUPPORTED = ir.SPEED_LADDER
MAX_ATTEMPTS = 5            # 首请求 + 4 次重试
BACKOFF_BASE = 3.0          # 间隔 3s 起翻倍：3 / 6 / 12 / 24
TIMEOUT = 30.0
RETRYABLE = (403, 408, 429, 500, 502, 503, 504)


def _voice() -> str:
    return os.environ.get("QX_TTS_VOICE", VOICE)


def _language() -> str:
    return os.environ.get("QX_TTS_LANGUAGE", LANGUAGE)


def _model() -> str:
    return os.environ.get("QX_TTS_MODEL", MODEL)


def _base() -> str:
    return (os.environ.get("QX_TTS_BASE_URL") or llm_client.base_url_for(TTS_PROVIDER)).rstrip("/")


def _key() -> str:
    k = os.environ.get("QX_TTS_API_KEY", "").strip()
    if k:
        return k
    return llm_client.api_key_for(TTS_PROVIDER, os.environ.get("QX_TTS_KEY_FILE", "").strip())


def _repair_wav(blob: bytes) -> bytes:
    """重写 RIFF/data 两个 size 字段为真实值，返回修复后的字节（音频数据原样不动）。

    网关头里这两个字段是溢出值（见模块 docstring），wave 模块与 mux 拼接都按它们记账，
    不修会读出错到离谱的时长/帧数。只改 8 个字节，其余原样保留。
    """
    if len(blob) < 12 or blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        raise RuntimeError(
            "TTS 响应不是 RIFF/WAV（网关可能返回了错误页）："
            + blob[:200].decode("utf-8", "replace"))
    out = bytearray(blob)
    pos = 12
    while pos + 8 <= len(out):
        cid = bytes(out[pos:pos + 4])
        size = struct.unpack("<I", out[pos + 4:pos + 8])[0]
        if cid == b"data":
            actual = len(out) - pos - 8   # 网关格式：data 是最后一个块
            if actual != size:
                struct.pack_into("<I", out, pos + 4, actual)
            break
        pos += 8 + size + (size & 1)
    else:
        raise RuntimeError("TTS 响应里没有 data 块，不是可用的 WAV")
    if struct.unpack("<I", out[4:8])[0] != len(out) - 8:
        struct.pack_into("<I", out, 4, len(out) - 8)
    return bytes(out)


def _post(body: dict) -> bytes:
    """POST /v1/audio/speech，带 403/429/5xx 重试退避，返回原始响应体字节。

    密钥只在构造请求头前一刻读入内存；任何日志/异常消息都不含密钥或请求头。
    """
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    key = _key()
    last = "未知错误"
    for attempt in range(MAX_ATTEMPTS):
        req = urllib.request.Request(
            f"{_base()}/v1/audio/speech", data=data, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}",
                     # Accept 必须 */*：网关对 audio/wav 回 400 InvalidParameter（实测）
                     "User-Agent": "chengxiang-mvp/1.0", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            # 只截响应体，绝不把请求头（Authorization）拼进消息
            last = f"HTTP {e.code}：{e.read().decode('utf-8', 'replace')[:200]}"
            if e.code not in RETRYABLE:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as e:
            last = f"网络错误 {type(e).__name__}"
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(BACKOFF_BASE * (2 ** attempt))
    raise RuntimeError(f"TTS 合成失败（重试 {MAX_ATTEMPTS} 次后仍不可用）：{last}")


# 口播里的公式片段：不含汉字、至少带一个运算符/上标，才当公式改写成念法
_FORMULA = re.compile(r"[A-Za-z0-9²³√|()\[\]+\-−=×÷/<>≤≥.^ ]*[A-Za-z0-9²³)]"
                      r"[A-Za-z0-9²³√|()\[\]+\-−=×÷/<>≤≥.^ ]*")
_OPS = {"+": " 加 ", "=": " 等于 ", "×": " 乘 ", "÷": " 除以 ", "/": " 除以 ",
        "<": " 小于 ", ">": " 大于 ", "≤": " 小于等于 ", "≥": " 大于等于 ", "√": " 根号 "}


def _speak_formula(seg: str) -> str:
    if not re.search(r"[+\-−=×÷/<>≤≥²³√^]", seg) or not re.search(r"[A-Za-z]", seg):
        return seg
    s = re.sub(r"\|\s*([A-Za-z])\s*\|", r" \1 的模 ", seg)
    s = re.sub(r"√\s*\(([^()]*)\)", r" 根号下 \1 ", s)
    s = s.replace("²", " 的平方 ").replace("³", " 的立方 ")
    # 减号：句首/运算符/左括号后是「负」，其余是「减」；字母间无空格的连字符（如 Q-U）不动
    s = re.sub(r"(^|[=(+×÷/<>]\s*)[−-]\s*", lambda m: m.group(1) + " 负 ", s)
    s = re.sub(r"\s*−\s*|\s+-\s+|-(?=\d)", " 减 ", s)
    for k, v in _OPS.items():
        s = s.replace(k, v)
    # 相邻字母是相乘的单字母变量（bi、qvB、ax），拆开念，免得 TTS 当成一个词
    s = re.sub(r"(?<=[A-Za-z])(?=[A-Za-z])", " ", s)
    return re.sub(r"\s+", " ", s)


# 多音字：TTS 只按字形猜读音，数学语境里的「奇」（jī，奇数/奇函数/奇偶）常被念成 qí。
# 只改发给 TTS 的文本；字幕走原始 narration（ir.Shot.subtitles），屏上仍是「奇函数」。
# 「积」只有 jī 一个读音，且逐整词替换，不会误伤「积分」里的积。
_POLYPHONE = {
    "奇函数": "积函数",
    "奇偶": "积偶",
    "奇数": "积数",
    "奇次": "积次",
}


def _fix_polyphone(text: str) -> str:
    for src, dst in _POLYPHONE.items():
        text = text.replace(src, dst)
    return text


# 化学名里的定位连字符（如 2-碘辛烷、1,3-丁二烯）不念「减」：数字与汉字之间的短杠直接去掉。
# 只碰「数字—汉字」相邻这一种，破折号（汉字—汉字）与字母键（C–Br）不动——后者要靠朗读稿（pipeline/voiceover.py）。
_LOCANT = re.compile(r"(?<=\d)\s*[-–−]\s*(?=[\u4e00-\u9fff])")
_LOCANT_REV = re.compile(r"(?<=[\u4e00-\u9fff])\s*[-–−]\s*(?=\d)")


def speakable(text: str) -> str:
    """把口播里的公式改写成按上下文的中文念法（a+bi → a 加 b i），其余文字原样。

    这是离线兜底：真正的朗读稿（化学式、σ*、SN2 等正则认不出的记号）由网关模型按整镜上下文
    生成（pipeline/voiceover.py），TTS 优先用那个，这里只负责没有网关时的降级。
    """
    text = _LOCANT.sub("", text)
    text = _LOCANT_REV.sub("", text)
    return _FORMULA.sub(lambda m: _speak_formula(m.group(0)), _fix_polyphone(text))


def synth(text: str, out_wav: Path, workdir: Path, rate: int = 0) -> float:
    """把一段口播合成成 wav，返回实测时长（秒）。

    rate 保留 SAPI 时代的档位语义以兼容调用方：网关 qwen3-tts-flash 的 speed 参数实测
    无效（见模块 docstring），所以照收但忽略，一律按自然语速合成；run.py 会依据
    SPEED_SUPPORTED 如实记账。workdir 不再使用（HTTP 无中间文件），仅为兼容签名保留。
    """
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    blob = _post({"model": _model(), "input": speakable(text), "voice": _voice(),
                  "language_type": _language()})
    out_wav.write_bytes(_repair_wav(blob))
    with wave.open(str(out_wav), "rb") as w:
        return round(w.getnframes() / w.getframerate(), 3)
