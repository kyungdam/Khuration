from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import clock
from ..db import get_db
from ..deps import require_device
from ..matching.engine import CHECK, MATCH, MISMATCH, evaluate, interest_score
from ..models import Device, Notice
from ..schemas import FeedItem, Reason

router = APIRouter(tags=["feed"])


def to_item(n: Notice, tags: dict) -> FeedItem:
    status, reasons = evaluate(n.criteria, tags)
    dl = n.deadline
    return FeedItem(
        id=n.id,
        title=n.title,
        source=n.source_name,
        category=n.category,
        summary=n.summary,
        url=n.url,
        deadline_date=clock.kst_date(dl).isoformat() if dl else None,
        d_day=clock.d_day(dl),
        status=status,
        reasons=[Reason(**r) for r in reasons],
        interest_score=interest_score(n.topics, tags),
    )


def build_feed(db: Session, tags: dict, include_mismatch=False, category=None) -> list[FeedItem]:
    now = clock.now()
    items = []
    for n in db.query(Notice).all():
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
