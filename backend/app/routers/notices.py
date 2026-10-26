from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import optional_device
from ..matching.engine import evaluate
from ..models import Device, Notice
from ..schemas import NoticeDetail
from .feed import to_item

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("/{notice_id}", response_model=NoticeDetail)
def notice_detail(notice_id: int, dev: Device | None = Depends(optional_device), db: Session = Depends(get_db)):
    """요약 + 지원 자격 + 원문 링크. 기기 토큰이 있으면 내 조건과의 판정 포함."""
    n = db.get(Notice, notice_id)
    if not n:
        raise HTTPException(404, "공지를 찾을 수 없습니다")
    tags = (dev.tags if dev else {}) or {}
    item = to_item(n, tags)
    _, rs = evaluate(n.criteria, {})
    return NoticeDetail(**item.model_dump(), requirements=[r["requirement"] for r in rs])
