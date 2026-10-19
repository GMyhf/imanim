"""LLM 接入层：OpenAI 兼容 chat/completions，纯标准库。

四个环节各用各的模型 + 各自的提示词（A1 需求分析 / A3 分镜 / A8 终审视觉 / S2.2 独立评审）。
默认全部关闭——确定性实现仍是默认与兜底；开关见 enabled()。

密钥只在请求发出前一刻读入内存：env QX_LLM_API_KEY 优先，其次 QX_LLM_KEY_FILE 指向的文件
（缺省 D:\\Desktop\\key.txt）。不写日志、不入异常信息、不落盘。
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("QX_LLM_BASE_URL", "https://api.openai-next.com").rstrip("/")
DEFAULT_KEY_FILE = r"D:\Desktop\key.txt"

# 可重试的 HTTP 状态码：网关/上游瞬时故障。520~527 是 Cloudflare 系（524=代理读超时，
# 上游在 120s 内没回完），530=源站错误，599=某些 CDN 的网络连接超时——这些都不该一次定生死，
# 退避重试往往能赶上上游缓过劲。不在列表里的（400/401/403/404…）是请求本身的问题，重试无益。
RETRYABLE_HTTP = (408, 429, 500, 502, 503, 504,
                  520, 521, 522, 523, 524, 525, 526, 527, 530, 599)

# 模型 ID 一律照 guide/resources 原样复制，不按版本号改写。各环节任务性质不同，模型分开选。
# flow v2（Spec_AgentFlow_v2.md §2）：生成型棒次钉死 claude-opus-5-5；核对/视觉棒异构 gemini；S22 异构 opus-4-8。
MODELS = {
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
}
STAGES = tuple(MODELS)


class LLMError(RuntimeError):
    """调用失败。消息里绝不含密钥或请求头。"""


def model_for(stage: str) -> str:
    return os.environ.get(f"QX_LLM_MODEL_{stage}", MODELS[stage])


def enabled(stage: str) -> bool:
    """QX_LLM_<STAGE>=1 单独开某一环节；QX_LLM_ALL=1 全开。默认关。"""
    return os.environ.get(f"QX_LLM_{stage}") == "1" or os.environ.get("QX_LLM_ALL") == "1"


def _api_key() -> str:
    k = os.environ.get("QX_LLM_API_KEY", "").strip()
    if k:
        return k
    path = Path(os.environ.get("QX_LLM_KEY_FILE", DEFAULT_KEY_FILE))
    try:
        k = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise LLMError(f"读不到 API 密钥（env QX_LLM_API_KEY 或密钥文件 {path}）：{type(e).__name__}") from None
    if not k:
        raise LLMError(f"密钥文件为空：{path}")
    return k


def image_part(png: Path) -> dict:
    b64 = base64.b64encode(Path(png).read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def chat(stage: str, system: str, user: str, images: list[Path] | None = None, *,
         max_tokens: int = 8000, timeout: float = 300.0, retries: int = 2,
         json_mode: bool = False) -> str:
    """单轮对话，返回文本。images 为 PNG 路径列表（多模态环节用）。"""
    content: object = user
    if images:
        content = [{"type": "text", "text": user}] + [image_part(p) for p in images]
    body = {
        "model": model_for(stage),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "max_tokens": max_tokens,
    }
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
                payload = json.loads(r.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            if isinstance(text, list):
                text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
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
