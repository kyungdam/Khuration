from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import clock
from ..config import settings
from ..db import get_db
from ..deps import require_device
from ..matching.engine import CHECK, MATCH, MISMATCH, device_criteria, evaluate, interest_score, topic_keys
from ..models import Device, Notice
from ..schemas import FeedItem, Reason

router = APIRouter(tags=["feed"])


def demo_mode() -> bool:
    return settings.app_mode == "demo"


def visible_notices(db: Session):
    """실제 모드(live)는 크롤링 공지만, 시연 모드(demo)는 미리 준비한 시연 공지([데모])만 보여준다."""
    return db.query(Notice).filter(Notice.is_demo.is_(demo_mode()))


def is_visible(n: Notice | None) -> bool:
    return n is not None and bool(n.is_demo) == demo_mode()


def _date(dt):
    return clock.kst_date(dt).isoformat() if dt else None


def to_item(n: Notice, tags: dict) -> FeedItem:
    status, reasons = evaluate(n.criteria, tags)
    return FeedItem(
        id=n.id,
        title=n.title,
        source=n.source_name,
        category=n.category,
        summary=n.summary,
        url=n.url,
        posted_date=_date(n.posted_at),
        deadline_date=_date(n.deadline),
        d_day=clock.d_day(n.deadline),
        status=status,
        reasons=[Reason(**r) for r in reasons],
        interest_score=interest_score(n.topics, tags, n.category),
        topics=sorted(topic_keys(n.topics, n.category)),
        device_criteria=device_criteria(n.criteria),
    )


def build_feed(db: Session, tags: dict, include_mismatch=False, category=None) -> list[FeedItem]:
    now = clock.now()
    items = []
    for n in visible_notices(db).all():
        if n.deadline and n.deadline < now:
            continue
        if category and n.category != category:
            continue
        it = to_item(n, tags)
        if it.status == MISMATCH and not include_mismatch:
            continue
        items.append(it)
    order = {MATCH: 0, CHECK: 1, MISMATCH: 2}
    items.sort(key=lambda i: (order[i.status], -i.interest_score, i.d_day if i.d_day is not None else 9999))
    return items


@router.get("/feed", response_model=list[FeedItem])
def feed(
    include_mismatch: bool = False,
    category: str | None = None,
    dev: Device = Depends(require_device),
    db: Session = Depends(get_db),
):
    """맞춤 피드. 일치 → 확인 필요 순. 불일치는 기본 제외."""
    return build_feed(db, dev.tags or {}, include_mismatch, category)
