from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Device


def optional_device(
    x_device_token: str | None = Header(None), db: Session = Depends(get_db)
) -> Device | None:
    if not x_device_token:
        return None
    return db.query(Device).filter_by(push_token=x_device_token).first()


def require_device(
    x_device_token: str | None = Header(None), db: Session = Depends(get_db)
) -> Device:
    if not x_device_token:
        raise HTTPException(401, "X-Device-Token 헤더가 필요합니다")
    dev = db.query(Device).filter_by(push_token=x_device_token).first()
    if not dev:
        raise HTTPException(404, "등록되지 않은 기기입니다. POST /devices 먼저 호출하세요")
    return dev
