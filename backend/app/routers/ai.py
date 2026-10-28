from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_device
from ..llm.chat import answer
from ..models import Device
from ..schemas import ChatIn, ChatOut

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, dev: Device = Depends(require_device), db: Session = Depends(get_db)):
    """질문 원문은 저장하지 않는다 (답변 캐시 키는 해시)."""
    return answer(body.message, db, dev.tags or {}, body.prev, body.context_ids)
