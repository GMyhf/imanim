"""LLM 接入层：OpenAI 兼容 chat/completions，纯标准库。

两套后端预设（env QX_LLM_PROVIDER，缺省 modelscope）：
  · modelscope —— ModelScope 推理网关，商用默认。主力生成 DeepSeek-V4-Pro-0813，
    轻量/多模态 Qwen3.8-Flash-Next，视觉与核对 Qwen3.8-27B。
  · gateway    —— 旧赛方网关（api.openai-next.com，claude/gemini/gpt 系列），保留回退。
各棒模型按任务性质分层，不按版本号猜能力；实测可用性见 .local/ms_*_probe 记录。

四个环节各用各的模型 + 各自的提示词（A1 需求分析 / A3 分镜 / A8 终审视觉 / S2.2 独立评审）。
默认全部关闭——确定性实现仍是默认与兜底；开关见 enabled()。

密钥只在请求发出前一刻读入内存：env QX_LLM_API_KEY 优先，其次 QX_LLM_KEY_FILE 指向的文件
（按 provider 缺省：modelscope→D:\\Desktop\\ms_token.txt，gateway→D:\\Desktop\\key.txt）。
不写日志、不入异常信息、不落盘。

TTS 不走本模块的 BASE_URL：ModelScope 没有 /v1/audio/speech 路由，audio/tts.py 固定回退
gateway 网关，端点与密钥独立可配（QX_TTS_BASE_URL / QX_TTS_API_KEY）。
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

# 模型 ID 一律照实测清单原样复制。相同 ID 的棒次是同模型不同上下文（如 K2 与 A8 独立核对），
# S22 与 A3 必须异构——这是防同源盲点的红线，不是可调参数。
PROVIDERS = {
    "modelscope": {
        "base": "https://api-inference.modelscope.cn",
        "key_file": r"D:\Desktop\ms_token.txt",
        "models": {
            "A1": "Qwen/Qwen3.8-Flash-Next",
            "A3": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "A8": "Qwen/Qwen3.8-27B",
            "S22": "Qwen/Qwen3.8-27B",
            "K0": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "K1": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "K2": "Qwen/Qwen3.8-27B",
            "P": "Qwen/Qwen3.8-27B",
            "V0": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "M1": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "M2": "deepseek-ai/DeepSeek-V4-Pro-0813",
            "VOICEOVER": "Qwen/Qwen3.8-Flash-Next",
        },
    },
    "gateway": {
        "base": "https://api.openai-next.com",
        "key_file": r"D:\Desktop\key.txt",
        "models": {
            "A1": "gpt-6.1-sol",
            "A3": "claude-opus-5-5",
            "A8": "gemini-3.1-pro-preview-thinking",
            "S22": "claude-opus-4-8",
            "K0": "claude-opus-5-5",
            "K1": "claude-opus-5-5",
            "K2": "gemini-3.1-pro-preview-thinking",
            "P": "gemini-3.1-pro-preview-thinking",
            "V0": "claude-opus-5-5",
            "M1": "claude-opus-5-5",
            "M2": "claude-opus-5-5",
            "VOICEOVER": "claude-opus-5-5",
        },
    },
}

PROVIDER = (os.environ.get("QX_LLM_PROVIDER", "modelscope").strip().lower() or "modelscope")
if PROVIDER not in PROVIDERS:
    raise RuntimeError(f"QX_LLM_PROVIDER 未知：{PROVIDER}（可选 {'/'.join(PROVIDERS)}）")
_PRESET = PROVIDERS[PROVIDER]
BASE_URL = (os.environ.get("QX_LLM_BASE_URL") or _PRESET["base"]).rstrip("/")
DEFAULT_KEY_FILE = _PRESET["key_file"]
MODELS = dict(_PRESET["models"])

# 可重试的 HTTP 状态码：网关/上游瞬时故障。520~527 是 Cloudflare 系（524=代理读超时，
# 上游在 120s 内没回完），530=源站错误，599=某些 CDN 的网络连接超时——这些都不该一次定生死，
# 退避重试往往能赶上上游缓过劲。不在列表里的（400/401/403/404…）是请求本身的问题，重试无益。
RETRYABLE_HTTP = (408, 429, 500, 502, 503, 504,
                  520, 521, 522, 523, 524, 525, 526, 527, 530, 599)

STAGES = tuple(MODELS)


class LLMError(RuntimeError):
    """调用失败。消息里绝不含密钥或请求头。"""


def model_for(stage: str) -> str:
    return os.environ.get(f"QX_LLM_MODEL_{stage}", MODELS[stage])


def base_url_for(provider: str = "") -> str:
    """指定后端的基础 URL；活动后端受 QX_LLM_BASE_URL 覆盖。"""
    provider = (provider or PROVIDER).lower()
    if provider not in PROVIDERS:
        raise LLMError(f"未知 provider：{provider}")
    if provider == PROVIDER and os.environ.get("QX_LLM_BASE_URL"):
        return os.environ["QX_LLM_BASE_URL"].rstrip("/")
    return PROVIDERS[provider]["base"].rstrip("/")


def api_key_for(provider: str = "", key_file: str = "") -> str:
    """读指定后端的密钥。活动后端认 QX_LLM_API_KEY/QX_LLM_KEY_FILE，非活动后端认
    QX_LLM_<PROVIDER>_API_KEY/QX_LLM_<PROVIDER>_KEY_FILE——TTS 在 modelscope 模式下
    仍要用 gateway 的密钥，两套不能互相串。key_file 非空时优先于一切文件配置。
    """
    provider = (provider or PROVIDER).lower()
    if provider not in PROVIDERS:
        raise LLMError(f"未知 provider：{provider}")
    upper = provider.upper()
    if provider == PROVIDER:
        k = os.environ.get("QX_LLM_API_KEY", "").strip()
        path_s = key_file or os.environ.get("QX_LLM_KEY_FILE", "").strip()
    else:
        k = os.environ.get(f"QX_LLM_{upper}_API_KEY", "").strip()
        path_s = key_file or os.environ.get(f"QX_LLM_{upper}_KEY_FILE", "").strip()
    if k:
        return k
    path = Path(path_s or PROVIDERS[provider]["key_file"])
    try:
        k = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise LLMError(f"读不到 API 密钥（env QX_LLM_API_KEY 或密钥文件 {path}）：{type(e).__name__}") from None
    if not k:
        raise LLMError(f"密钥文件为空：{path}")
    return k


def _api_key(provider: str = "") -> str:
    return api_key_for(provider)


def enabled(stage: str) -> bool:
    """QX_LLM_<STAGE>=1 单独开某一环节；QX_LLM_ALL=1 全开。默认关。"""
    return os.environ.get(f"QX_LLM_{stage}") == "1" or os.environ.get("QX_LLM_ALL") == "1"


def image_part(png: Path) -> dict:
    b64 = base64.b64encode(Path(png).read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def _choice_content(msg: dict) -> str:
    """从一个 choice 的 message/delta 里取文本内容（网关有的给 str、有的给 list）。"""
    c = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def _read_body(r) -> str:
    """读网关响应：优先按 SSE 流式逐 chunk 拼 content；网关无视 stream 直接回整段 JSON 时退回整段解析。

    流式是 Cloudflare 524 的解法：慢模型（opus 长 thinking + 大 JSON）非流式时网关要等全部生成完
    才回第一个字节，Cloudflare 的 120s 读超时先到、直接 524；流式则边生成边回、字节不断，读超时不触发。
    """
    parts: list[str] = []
    raw = b""
    sse = False
    for line in r:
        raw += line
        text = line.decode("utf-8", "replace").strip()
        if text.startswith("data:"):
            sse = True
            data = text[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            try:
                choice = obj["choices"][0]
            except (KeyError, IndexError, TypeError):
                continue
            parts.append(_choice_content(choice.get("delta") or choice.get("message") or {}))
    if sse:
        return "".join(parts)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return ""
    try:
        return _choice_content(payload["choices"][0].get("message") or {})
    except (KeyError, IndexError, TypeError):
        return ""


def chat(stage: str, system: str, user: str, images: list[Path] | None = None, *,
         max_tokens: int = 8000, timeout: float = 300.0, retries: int = 2,
         json_mode: bool = False, thinking: bool = False) -> str:
    """单轮对话，返回文本。images 为 PNG 路径列表（多模态环节用）。

    thinking 只对 modelscope 生效：V4/Qwen3.8 的思考 token 计入 max_tokens，结构化长 JSON
    棒次默认关思考，避免推理吃掉输出预算导致截断；需要长链推理的调用方可显式传 True。
    """
    content: object = user
    if images:
        content = [{"type": "text", "text": user}] + [image_part(p) for p in images]
    body = {
        "model": model_for(stage),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "stream": True,
    }
    if PROVIDER == "modelscope":
        body["enable_thinking"] = bool(thinking)
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    last = "未知错误"
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            f"{BASE_URL}/v1/chat/completions", data=data, method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {_api_key()}",
                     "User-Agent": "chengxiang-mvp/1.0", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = _read_body(r)
            if not text or not text.strip():
                raise LLMError(f"[{stage}] 模型返回空内容")
            return text
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            last = f"HTTP {e.code} {detail}"
            if e.code not in RETRYABLE_HTTP:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"网络错误 {type(e).__name__}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            last = f"响应格式异常 {type(e).__name__}"
        if attempt < retries:
            time.sleep(5 * (attempt + 1) ** 2)
    raise LLMError(f"[{stage}/{model_for(stage)}] 调用失败：{last}")


def extract_json(text: str) -> object:
    """从模型输出里取出 JSON（容忍 ```json 围栏与前后说明文字）。"""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        a, b = s.find(open_c), s.rfind(close_c)
        if a != -1 and b > a:
            try:
                return json.loads(s[a:b + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError("模型输出不是合法 JSON")
