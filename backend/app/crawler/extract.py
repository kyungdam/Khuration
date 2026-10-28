"""원본 공지 → 앱이 쓰는 구조화 정보.
ChatKHU 추출은 extract_llm.py. 실패하거나 키가 없으면 extract_rule_based로 폴백.
LLM은 '조건 추출'만 한다. 학생 정보와 대조(매칭)는 app/matching/engine.py가 한다."""
import re
from dataclasses import dataclass, field
from datetime import datetime

from ..taxonomy import CATEGORY_RULES, TOPIC_RULES  # noqa: F401  (분류·관심 분야 키워드는 taxonomy.json)
from .base import RawNotice

# matching/engine.py가 읽는 조건 스키마. 모르면 None/빈 리스트로 둔다 (추측 금지).
EMPTY_CRITERIA = {
    "campuses": [],  # "seoul" | "global"
    "colleges": [],  # 예: "공과대학"
    "departments": [],  # 예: "화학공학과"
    "grades": [],  # 예: [3, 4]
    "min_gpa": None,  # 예: 3.0
    "gpa_basis": None,  # "overall" | "last"(직전 학기)
    "min_credits": None,
    "income_max": None,  # 예: 8 (8분위 이하)
    "requires_lang_score": None,
    "open_to_all": None,  # 공지에 "누구나/제한 없음"이 명시되면 True. 모르면 None → 판정은 '확인 필요'
    # 민감 조건: 서버는 공지 조건만 갖고, 학생 값과의 비교는 기기(web/index.html)가 한다 (matching.DEVICE_KEYS)
    "birth_year_min": None,  # 예: 2001 ("2001년 이후 출생")
    "birth_year_max": None,  # 예: 1997 ("1997년 이전 출생")
    "max_age": None,  # 예: 29 ("만 29세 이하")
}


@dataclass
class Extracted:
    category: str
    topics: list[str]
    deadline: datetime | None  # naive UTC (KST 23:59 → UTC로 변환해서 넣기)
    criteria: dict
    summary: str
    summary_points: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    apply_url: str = ""
    engine: str = "rule"
    verification: dict = field(default_factory=dict)  # {"kept": [...], "dropped": {항목: 이유}} (AI 추출일 때)


def extract_rule_based(raw: RawNotice, full_text: str) -> Extracted:
    t = f"{raw.title}\n{full_text}".lower()
    category = next((c for c, ws in CATEGORY_RULES if any(w in t for w in ws)), "학사")
    topics = sorted(k for k, ws in TOPIC_RULES.items() if any(w in t for w in ws))
    first = re.sub(r"\s+", " ", full_text).strip()[:120]
    return Extracted(
        category=category,
        topics=topics,
        deadline=None,  # 규칙 기반으로는 마감일을 확정하지 않는다 → LLM 담당
        criteria=dict(EMPTY_CRITERIA),
        summary=first,
        summary_points=[first] if first else [],
        apply_url=raw.url,
    )


def extract(raw: RawNotice, full_text: str) -> Extracted:
    """키가 있으면 ChatKHU로, 없거나 실패하면 규칙 기반으로."""
    from ..llm import client

    if client.available():
        try:
            from .extract_llm import extract_with_llm

            return extract_with_llm(raw, full_text)
        except Exception as e:  # 모델 오류가 크롤링 전체를 멈추지 않게
            print(f"    LLM 추출 실패 → 규칙 기반으로 대체: {e}")
    return extract_rule_based(raw, full_text)
