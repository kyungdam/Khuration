from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import clock
from ..db import get_db
from ..deps import require_device
from ..llm.intent import extract_keywords
from ..models import Device, NotificationLog
from ..schemas import DeviceIn, DeviceOut, IntentIn

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceOut)
def upsert_device(body: DeviceIn, db: Session = Depends(get_db)):
    """푸시 토큰 + 익명 조건 태그 등록/갱신. 이름·학번은 받지 않는다."""
    new_tags = body.tags.model_dump()
    dev = db.query(Device).filter_by(push_token=body.push_token).first()
    if dev:
        keep = (dev.tags or {}).get("intent_keywords", [])
        dev.tags = {**new_tags, "intent_keywords": keep}
        dev.updated_at = clock.real_utcnow()
    else:
        dev = Device(push_token=body.push_token, tags={**new_tags, "intent_keywords": []})
        db.add(dev)
    db.commit()
    db.refresh(dev)
    return DeviceOut(id=dev.id, tags=dev.tags)


@router.post("/intent")
def set_intent(body: IntentIn, dev: Device = Depends(require_device), db: Session = Depends(get_db)):
    """'하고 싶은 활동' 문장 → 키워드. 문장 원문은 저장하지 않는다."""
    kws = extract_keywords(body.text)
    dev.tags = {**(dev.tags or {}), "intent_keywords": kws}
    db.commit()
    return {"keywords": kws}


@router.delete("")
def delete_device(dev: Device = Depends(require_device), db: Session = Depends(get_db)):
    db.query(NotificationLog).filter_by(device_id=dev.id).delete()
    db.delete(dev)
    db.commit()
    return {"deleted": True}
