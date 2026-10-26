import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from . import clock
from .models import Notice, NotificationLog

SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "notices.json"


def content_hash(title: str, deadline, criteria) -> str:
    raw = f"{title}|{deadline.isoformat() if deadline else ''}|{json.dumps(criteria, sort_keys=True, ensure_ascii=False)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def load_seed(db: Session, replace: bool = False) -> int:
    if replace:
        db.query(NotificationLog).delete()
        db.query(Notice).filter(Notice.is_demo.is_(True)).delete()
        db.commit()
        clock.reset()
    elif db.query(Notice).count() > 0:
        return 0
    items = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    for i, it in enumerate(items, start=1):
        deadline = clock.kst_deadline(it["deadline_in_days"]) if it.get("deadline_in_days") is not None else None
        db.add(
            Notice(
                source_name=it["source"],
                category=it["category"],
                topics=it["topics"],
                title=it["title"],
                url=f"https://example.com/demo/{i}",
                summary=it["summary"],
                posted_at=clock.real_utcnow(),
                deadline=deadline,
                criteria=it.get("criteria"),
                content_hash=content_hash(it["title"], deadline, it.get("criteria")),
                is_demo=True,
            )
        )
    db.commit()
    return len(items)
