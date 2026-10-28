"""KHU AI 답변 캐시.

키 = sha256(정규화한 질문 + 조건 태그 + 색인 버전 + 오늘 날짜(KST) + 모델)
- 질문 원문은 저장하지 않는다 (해시만).
- 색인이 바뀌거나(새 공지) 날짜가 바뀌면(D-day) 키가 달라져 자동으로 새로 답한다.
- TTL이 지난 항목은 저장할 때 지운다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from sqlalchemy.orm import Session

from .. import clock
from ..config import settings
from ..models import AnswerCache

TTL = timedelta(hours=6)


def make_key(message: str, tags: dict, index_version: tuple, model: str) -> str:
    norm = " ".join(message.lower().split()).rstrip("?!. ")
    t = {k: v for k, v in (tags or {}).items() if k != "intent_keywords"}
    raw = json.dumps([norm, t, list(index_version), clock.kst_date(clock.now()).isoformat(), model, settings.app_mode],
                     sort_keys=True, ensure_ascii=False)  # 모드가 바뀌면 다른 답 (실제/시연 공지가 섞이지 않게)
    return hashlib.sha256(raw.encode()).hexdigest()


def get(db: Session, key: str) -> dict | None:
    row = db.get(AnswerCache, key)
    if row and clock.real_utcnow() - row.created_at < TTL:
        return row.payload
    return None


def put(db: Session, key: str, payload: dict) -> None:
    now = clock.real_utcnow()
    db.query(AnswerCache).filter(AnswerCache.created_at < now - TTL).delete(synchronize_session=False)
    db.merge(AnswerCache(key=key, payload=payload, created_at=now))
    db.commit()
