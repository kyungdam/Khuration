"""시연 전용. APP_MODE=demo 일 때만 등록된다."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import clock
from ..db import get_db
from ..deps import require_device
from ..models import Device, Notice, NotificationLog
from ..push import expo
from ..seed_loader import content_hash, load_seed
from .feed import build_feed, is_visible

router = APIRouter(tags=["demo"])


class Advance(BaseModel):
    days: int = 0
    hours: int = 0


class ChangeNotice(BaseModel):
    notice_id: int
    deadline_in_days: int


class FirePush(BaseModel):
    kind: Literal["new", "d3", "changed"] = "d3"
    notice_id: int | None = None
    force: bool = True  # 시연 중 버튼 반복 허용. False면 중복 방지 로직 확인 가능


@router.get("/clock")
def get_clock():
    return {"now_utc": clock.now().isoformat(), "offset_days": clock.offset_days()}


@router.post("/advance-clock")
def advance_clock(body: Advance):
    clock.advance(days=body.days, hours=body.hours)
    return get_clock()


@router.post("/reset-clock")
def reset_clock():
    clock.reset()
    return get_clock()


@router.post("/reseed")
def reseed(db: Session = Depends(get_db)):
    return {"loaded": load_seed(db, replace=True)}


@router.post("/change-notice")
def change_notice(body: ChangeNotice, db: Session = Depends(get_db)):
    """공지 마감일 변경 → content_hash 변경 → 'changed' 알림 대상이 된다."""
    n = db.get(Notice, body.notice_id)
    if not is_visible(n):  # 시연 공지만 바꾼다 (크롤링 공지는 건드리지 않음)
        raise HTTPException(404, "공지를 찾을 수 없습니다")
    # 시계를 앞당긴 상태에서도 "지금부터 N일 뒤"가 되도록 시연 오프셋을 더한다
    n.deadline = clock.kst_deadline(body.deadline_in_days) + (clock.now() - clock.real_utcnow())
    n.content_hash = content_hash(n.title, n.deadline, n.criteria)
    db.commit()
    return {"id": n.id, "content_hash": n.content_hash}


@router.post("/fire-push")
def fire_push(body: FirePush, dev: Device = Depends(require_device), db: Session = Depends(get_db)):
    items = build_feed(db, dev.tags or {})
    if body.notice_id is not None:
        pick = next((i for i in items if i.id == body.notice_id), None)
    elif body.kind == "d3":
        near = [i for i in items if i.d_day is not None and 0 <= i.d_day <= 3]
        pick = min(near, key=lambda i: i.d_day) if near else None
    else:
        pick = items[0] if items else None
    if not pick:
        return {"sent": False, "reason": "조건에 맞는 공지가 없습니다"}

    n = db.get(Notice, pick.id)
    exists = (
        db.query(NotificationLog)
        .filter_by(device_id=dev.id, notice_id=n.id, kind=body.kind, content_hash=n.content_hash)
        .first()
    )
    if exists and not body.force:
        return {"sent": False, "reason": "이미 보낸 알림 (중복 방지)", "notice_id": n.id}

    title = {"d3": f"마감 D-{pick.d_day}", "new": "새 맞춤 공지", "changed": "공지가 변경됐어요"}[body.kind]
    msg = {"to": dev.push_token, "title": title, "body": n.title, "data": {"notice_id": n.id}}
    if not exists:
        db.add(NotificationLog(device_id=dev.id, notice_id=n.id, kind=body.kind, content_hash=n.content_hash))
        db.commit()
    if not expo.is_expo_token(dev.push_token):
        return {"sent": False, "reason": "Expo 푸시 토큰 형식이 아님 (미리보기)", "preview": msg}
    return {"sent": True, "preview": msg, "expo": expo.send([msg])}
