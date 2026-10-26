"""원본 공지 → 앱이 쓰는 구조화 정보.
ChatKHU 추출은 extract_llm.py. 실패하거나 키가 없으면 extract_rule_based로 폴백.
LLM은 '조건 추출'만 한다. 학생 정보와 대조(매칭)는 app/matching/engine.py가 한다."""
import re
from dataclasses import dataclass, field
from datetime import datetime

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
}

CATEGORY_RULES = [
    ("장학", ["장학", "등록금", "학자금"]),
    ("현장실습", ["현장실습", "인턴"]),
    ("국제교류", ["교환학생", "해외", "어학연수", "국제교류"]),
    ("공모전", ["공모전", "경진대회", "해커톤", "대회"]),
    ("근로", ["근로"]),
    ("취업", ["채용", "취업", "멘토링"]),
    ("비교과", ["비교과", "특강", "프로그램"]),
]
TOPIC_RULES = {
    "ai_data": ["ai", "인공지능", "데이터"],
    "dev_it": ["sw", "소프트웨어", "개발", "해커톤", "코딩"],
    "design": ["디자인", "ui", "ux"],
    "scholarship": ["장학"],
    "startup": ["창업", "스타트업"],
    "language_abroad": ["교환학생", "어학", "해외"],
    "internship": ["현장실습", "인턴"],
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
