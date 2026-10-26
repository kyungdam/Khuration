"""크롤링 결과 저장. 크롤러는 DB를 직접 만지지 말고 반드시 upsert_notice만 쓴다."""
from typing import Literal

from sqlalchemy.orm import Session

from .. import clock
from ..models import Attachment, Notice
from ..seed_loader import content_hash
from .base import RawNotice
from .extract import Extracted

Change = Literal["new", "changed", "same"]


def upsert_notice(db: Session, raw: RawNotice, ex: Extracted, attachment_texts: dict[str, str] | None = None) -> tuple[Notice, Change]:
    """url이 같으면 같은 공지. 제목·마감일·조건이 바뀌면 'changed'(→ 변경 알림 대상).
    반환값의 Change로 푸시 단계가 new/changed 알림을 보낸다."""
    h = content_hash(raw.title, ex.deadline, ex.criteria)
    n = db.query(Notice).filter_by(url=raw.url).first()
    change: Change
    if n is None:
        n = Notice(url=raw.url, is_demo=False, created_at=clock.real_utcnow())
        db.add(n)
        change = "new"
    elif n.content_hash != h:
        change = "changed"
    else:
        change = "same"

    n.source_name = raw.source_name
    n.title = raw.title
    n.body_text = raw.body_text
    n.posted_at = raw.posted_at
    n.deadline = ex.deadline
    n.category = ex.category
    n.topics = ex.topics
    n.criteria = ex.criteria
    n.summary = ex.summary
    n.summary_points = ex.summary_points
    n.checklist = ex.checklist
    n.apply_url = ex.apply_url or raw.url
    n.content_hash = h
    db.flush()

    texts = attachment_texts or {}
    existing = {a.file_url for a in n.attachments}
    for a in raw.attachments:
        if a.url not in existing:
            db.add(Attachment(notice_id=n.id, file_url=a.url, kind=a.kind, extracted_text=texts.get(a.url, "")))
    db.commit()
    return n, change
