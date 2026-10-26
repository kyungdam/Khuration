from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import clock
from ..db import get_db
from ..deps import optional_device
from ..matching.engine import evaluate
from ..models import Device, Notice
from ..schemas import FeedItem, NoticeDetail
from .feed import to_item

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=list[FeedItem])
def list_notices(
    q: str | None = None,
    category: str | None = None,
    sort: Literal["latest", "deadline", "ai"] = "latest",
    dev: Device | None = Depends(optional_device),
    db: Session = Depends(get_db),
):
    """공지사항 탭: 맞춤 필터 없이 전체 공지. 검색(제목·기관), 카테고리, 정렬."""
    tags = (dev.tags if dev else {}) or {}
    now = clock.now()
    rows = db.query(Notice).all()
    out = []
    for n in rows:
        if n.deadline and n.deadline < now:
            continue
        if category and n.category != category:
            continue
        if q and q.strip() and q.strip().lower() not in f"{n.title} {n.source_name} {n.summary}".lower():
            continue
        out.append((n, to_item(n, tags)))
    if sort == "deadline":
        out.sort(key=lambda x: x[1].d_day if x[1].d_day is not None else 9999)
    elif sort == "ai":
        rank = {"match": 0, "check": 1, "mismatch": 2}
        out.sort(key=lambda x: (rank[x[1].status], -x[1].interest_score))
    else:
        out.sort(key=lambda x: x[0].posted_at or x[0].created_at, reverse=True)
    return [i for _, i in out]


@router.get("/{notice_id}", response_model=NoticeDetail)
def notice_detail(notice_id: int, dev: Device | None = Depends(optional_device), db: Session = Depends(get_db)):
    """요약 + 지원 자격 + 원문 링크. 기기 토큰이 있으면 내 조건과의 판정 포함."""
    n = db.get(Notice, notice_id)
    if not n:
        raise HTTPException(404, "공지를 찾을 수 없습니다")
    tags = (dev.tags if dev else {}) or {}
    item = to_item(n, tags)
    _, rs = evaluate(n.criteria, {})
    return NoticeDetail(
        **item.model_dump(),
        requirements=[r["requirement"] for r in rs],
        summary_points=n.summary_points or ([n.summary] if n.summary else []),
        checklist=n.checklist or [],
        apply_url=n.apply_url or n.url,
    )
