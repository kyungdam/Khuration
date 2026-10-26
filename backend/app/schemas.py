from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

INTEREST_KEYS = {
    "dev_it",  # 개발·IT
    "ai_data",  # AI·데이터
    "design",  # 디자인
    "scholarship",  # 장학금
    "startup",  # 창업
    "language_abroad",  # 어학·해외
    "internship",  # 현장실습
}


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


class FeedItem(BaseModel):
    id: int
    title: str
    source: str
    category: str
    summary: str
    url: str
    deadline_date: str | None  # KST 기준 YYYY-MM-DD
    d_day: int | None
    status: Literal["match", "check", "mismatch"]
    reasons: list[Reason]
    interest_score: int


class NoticeDetail(FeedItem):
    requirements: list[str]
