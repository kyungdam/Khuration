from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .taxonomy import INTEREST_KEYS  # noqa: E402  (관심 분야 키는 taxonomy.json)


class Tags(BaseModel):
    """서버가 받는 익명 조건 태그. 이름·학번·정확한 학점은 받지 않는다(extra=forbid)."""

    model_config = ConfigDict(extra="forbid")

    campus: Literal["seoul", "global"] | None = None
    college: str | None = Field(None, max_length=50)
    dept: str | None = Field(None, max_length=50)
    grade: int | None = Field(None, ge=1, le=6)
    gpa_floor: float | None = Field(None, ge=0, le=4.5)  # 평균 학점, 0.5 단위 내림 (3.87 → 3.5)
    last_gpa_floor: float | None = Field(None, ge=0, le=4.5)  # 직전 평점, 0.5 단위 내림
    credits_floor: int | None = Field(None, ge=0, le=200)  # 취득 학점, 10 단위 내림 (78 → 70)
    income_band: int | None = Field(None, ge=1, le=10)  # 소득분위 (1~10)
    has_lang_score: bool | None = None
    interests: list[str] = []

    @field_validator("interests")
    @classmethod
    def _check_interests(cls, v: list[str]) -> list[str]:
        bad = [x for x in v if x not in INTEREST_KEYS]
        if bad:
            raise ValueError(f"unknown interests: {bad}")
        return sorted(set(v))


class DeviceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    push_token: str = Field(min_length=3, max_length=200)
    tags: Tags


class DeviceOut(BaseModel):
    id: int
    tags: dict


class IntentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)


class Reason(BaseModel):
    field: str
    status: Literal["match", "check", "mismatch"]
    requirement: str
    note: str
    evidence: str | None = None  # 이 조건의 근거가 된 공지 원문 구절 (AI 추출 + 원문 대조로 확인된 것만)


class FeedItem(BaseModel):
    id: int
    title: str
    source: str
    category: str
    summary: str
    url: str
    posted_date: str | None  # KST 기준 YYYY-MM-DD
    deadline_date: str | None  # KST 기준 YYYY-MM-DD
    d_day: int | None
    status: Literal["match", "check", "mismatch"]
    reasons: list[Reason]
    interest_score: int
    topics: list[str]  # 관심분야 키 + 카테고리 키


class NoticeDetail(FeedItem):
    requirements: list[str]
    summary_points: list[str]
    checklist: list[str]
    apply_url: str
    deadline_evidence: str | None = None  # 마감일의 근거가 된 공지 원문 구절


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)
    # 이어지는 질문용 (기기에만 저장된 대화에서 앞 질문 1개와 앞 답변의 공지 id만 보낸다. 서버는 저장하지 않는다)
    prev: str = Field("", max_length=500)
    context_ids: list[int] = Field(default_factory=list, max_length=6)


class Evidence(BaseModel):
    """답변 근거가 된 공지 조각 (출처 표시용)"""

    notice_id: int
    title: str
    snippet: str


class ChatOut(BaseModel):
    answer: str
    keywords: list[str]
    items: list[FeedItem]
    sources: list[str]
    engine: str  # "rule" | "chatkhu"
    evidence: list[Evidence] = []
    cached: bool = False  # 같은 질문·조건이면 저장된 답을 재사용 (모델 호출 안 함)
