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


def chat(
    messages: list[dict],
    model: str,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float = 90.0,
) -> str:
    if not available():
        raise LLMError("CHATKHU_API_KEY / CHATKHU_BASE_URL 이 .env 에 없습니다.")
    body: dict = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens:
        body["max_tokens"] = max_tokens
    try:
        r = httpx.post(
            _url(),
            json=body,
            headers={"Authorization": f"Bearer {settings.chatkhu_api_key}"},
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise LLMError(f"네트워크 오류: {e}") from e
    if r.status_code != 200:
        raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        return r.json()["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"예상 못한 응답 형식: {r.text[:300]}") from e


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
