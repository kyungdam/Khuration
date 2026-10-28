"""'하고 싶은 활동' 문장 → 관심 키워드.
TODO: ChatKHU API 형식 확인 후 LLM 호출로 교체 (키가 없거나 실패하면 이 규칙 기반이 폴백).
문장 원문은 저장하지 않고 키워드만 남긴다."""

from ..taxonomy import INTENT_RULES as RULES  # 키워드 목록은 taxonomy.json


def extract_keywords(text: str) -> list[str]:
    t = text.lower()
    return sorted(k for k, words in RULES.items() if any(w in t for w in words))
