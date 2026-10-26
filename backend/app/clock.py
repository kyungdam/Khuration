"""시간 관리. demo 모드에서는 가상 시계를 앞당겨 D-3 상황을 재현한다."""
from datetime import date, datetime, timedelta, timezone

KST = timedelta(hours=9)
_offset = timedelta(0)


def real_utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now() -> datetime:
    """naive UTC + 데모 오프셋"""
    return real_utcnow() + _offset


def advance(days: int = 0, hours: int = 0) -> None:
    global _offset
    _offset += timedelta(days=days, hours=hours)


def reset() -> None:
    global _offset
    _offset = timedelta(0)


def offset_days() -> float:
    return round(_offset.total_seconds() / 86400, 2)


def kst_date(dt: datetime) -> date:
    return (dt + KST).date()


def d_day(deadline: datetime | None) -> int | None:
    if deadline is None:
        return None
    return (kst_date(deadline) - kst_date(now())).days


def kst_deadline(days_from_today: int) -> datetime:
    """오늘(KST)로부터 N일 뒤 23:59 KST를 naive UTC로 반환"""
    d = kst_date(real_utcnow()) + timedelta(days=days_from_today)
    return datetime(d.year, d.month, d.day, 23, 59) - KST
