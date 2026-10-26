"""'하고 싶은 활동' 문장 → 관심 키워드.
TODO: ChatKHU API 형식 확인 후 LLM 호출로 교체 (키가 없거나 실패하면 이 규칙 기반이 폴백).
문장 원문은 저장하지 않고 키워드만 남긴다."""

RULES = {
    "ai_data": ["ai", "인공지능", "데이터", "머신러닝", "딥러닝"],
    "dev_it": ["개발", "코딩", "프로그래밍", "앱", "해커톤", "it", "소프트웨어"],
    "design": ["디자인", "ui", "ux", "그래픽"],
    "scholarship": ["장학", "등록금", "학비"],
    "startup": ["창업", "스타트업", "사업"],
    "language_abroad": ["교환", "어학", "해외", "유학", "토익", "연수"],
    "internship": ["인턴", "현장실습", "실습", "취업"],
    "contest": ["공모전", "대회", "경진", "콘테스트"],
}


def extract_keywords(text: str) -> list[str]:
    t = text.lower()
    return sorted(k for k, words in RULES.items() if any(w in t for w in words))
