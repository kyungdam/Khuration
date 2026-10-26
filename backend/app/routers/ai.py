from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_device
from ..llm.chat import answer
from ..models import Device
from ..schemas import ChatIn, ChatOut
from .feed import build_feed

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, dev: Device = Depends(require_device), db: Session = Depends(get_db)):
    """질문 원문은 저장하지 않는다."""
    tags = dev.tags or {}
    return answer(body.message, build_feed(db, tags), tags)
