"""ChatKHU(OpenAI 호환 게이트웨이) 호출 래퍼.

- 키/주소/모델 이름은 .env 에서만 읽는다. 코드에 넣지 않는다.
- 키가 없으면 `available()` 이 False -> 호출하는 쪽이 규칙 기반으로 대체한다.
"""
from __future__ import annotations

import base64
import json
import re

import httpx

from ..config import settings


class LLMError(RuntimeError):
    pass


def available() -> bool:
    return bool(settings.chatkhu_api_key and settings.chatkhu_base_url)


def _url() -> str:
    return settings.chatkhu_base_url.rstrip("/") + "/chat/completions"


# 토큰 사용량 (크롤링이 끝나면 합계를 출력한다). 응답의 usage를 그대로 더한다.
USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0}
last_usage: dict = {}
# 게이트웨이가 받아 주지 않는 옵션은 한 번 실패하면 이후로 보내지 않는다
_unsupported: set[str] = set()


def think_tokens(u: dict | None) -> int | None:
    """생각 토큰 수. 게이트웨이가 따로 알려 주면 그 값, 아니면 total − 입력 − 출력 으로 계산
    (ChatKHU는 Gemini의 생각 토큰을 completion_tokens에서 빼고 total_tokens에만 넣는다)."""
    u = u or {}
    d = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if d is not None:
        return int(d)
    t, p, c = u.get("total_tokens"), u.get("prompt_tokens"), u.get("completion_tokens")
    if t is None or p is None or c is None:
        return None
    return max(int(t) - int(p) - int(c), 0)


def _add_usage(u: dict | None) -> None:
    global last_usage
    last_usage = u or {}
    USAGE["calls"] += 1
    USAGE["prompt_tokens"] += int(last_usage.get("prompt_tokens") or 0)
    USAGE["completion_tokens"] += int(last_usage.get("completion_tokens") or 0)
    USAGE["reasoning_tokens"] += think_tokens(last_usage) or 0


def chat(
    messages: list[dict],
    model: str,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float = 90.0,
    json_mode: bool = False,
    reasoning: str | None = None,
) -> str:
    """json_mode: 응답을 JSON 객체로 강제(response_format). reasoning: 모델의 '생각' 양(low 등).
    두 옵션 모두 게이트웨이가 거부하면(HTTP 400/422) 빼고 한 번 다시 보내고, 이후로는 보내지 않는다."""
    if not available():
        raise LLMError("CHATKHU_API_KEY / CHATKHU_BASE_URL 이 .env 에 없습니다.")
    body: dict = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens:
        body["max_tokens"] = max_tokens
    effort = settings.chatkhu_reasoning_effort if reasoning is None else reasoning
    extras: dict = {}
    if effort and "reasoning_effort" not in _unsupported:
        extras["reasoning_effort"] = effort  # 생각 토큰 줄이기 (Gemini·GPT 계열 OpenAI 호환 옵션)
    if json_mode and "response_format" not in _unsupported:
        extras["response_format"] = {"type": "json_object"}
    r = _post({**body, **extras}, timeout)
    if r.status_code in (400, 422) and extras:
        r2 = _post(body, timeout)
        if r2.status_code == 200:  # 옵션 때문이었음 → 이후로는 보내지 않는다
            _unsupported.update(extras)
            print(f"    (게이트웨이가 {', '.join(extras)} 옵션을 받지 않아 빼고 보냄)")
            r = r2
    if r.status_code != 200:
        raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        data = r.json()
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"예상 못한 응답 형식: {r.text[:300]}") from e
    _add_usage(data.get("usage"))
    return content


def _post(body: dict, timeout: float):
    try:
        return httpx.post(
            _url(),
            json=body,
            headers={"Authorization": f"Bearer {settings.chatkhu_api_key}"},
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise LLMError(f"네트워크 오류: {e}") from e


def usage_summary() -> str:
    u = USAGE
    if not u["calls"]:
        return "AI 호출 0회"
    return (f"AI 호출 {u['calls']}회 · 입력 {u['prompt_tokens']:,} · 출력 {u['completion_tokens']:,}"
            f" · 생각 {u['reasoning_tokens']:,} 토큰")


def image_part(data: bytes, mime: str = "image/png") -> dict:
    b64 = base64.b64encode(data).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def parse_json(text: str) -> dict:
    """모델 답에서 JSON 객체만 꺼낸다 (```json 울타리/앞뒤 설명 허용)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{") : text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except ValueError as e:
        raise LLMError(f"JSON 파싱 실패: {text[:200]}") from e
