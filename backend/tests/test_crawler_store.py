from datetime import datetime

from app.crawler.base import RawAttachment, RawNotice, guess_kind
from app.crawler.extract import EMPTY_CRITERIA, Extracted, extract_rule_based
from app.crawler.store import upsert_notice
from app.db import Base, SessionLocal, engine


def _ex(deadline=None, criteria=None):
    return Extracted(category="장학", topics=["scholarship"], deadline=deadline,
                     criteria=criteria or dict(EMPTY_CRITERIA), summary="요약")


def test_upsert_new_same_changed():
    Base.metadata.create_all(engine)
    raw = RawNotice(source_name="테스트", url="https://example.com/crawl/1", title="장학금 안내", body_text="본문",
                    attachments=[RawAttachment(url="https://example.com/a.hwp", filename="a.hwp", kind="hwp")])
    with SessionLocal() as db:
        n, c = upsert_notice(db, raw, _ex())
        assert c == "new" and n.is_demo is False and len(n.attachments) == 1
        _, c = upsert_notice(db, raw, _ex())
        assert c == "same"
        _, c = upsert_notice(db, raw, _ex(deadline=datetime(2026, 12, 1, 14, 59)))
        assert c == "changed"
        _, c = upsert_notice(db, raw, _ex(deadline=datetime(2026, 12, 1, 14, 59)))
        assert c == "same"
        n, _ = upsert_notice(db, raw, _ex())
        assert len(n.attachments) == 1  # 첨부 중복 저장 안 함


def test_rule_extract_and_kind():
    raw = RawNotice(source_name="s", url="u", title="2026 AI 해커톤 참가자 모집", body_text="SW 개발")
    ex = extract_rule_based(raw, raw.body_text)
    assert ex.category == "공모전" and "ai_data" in ex.topics and ex.deadline is None
    assert guess_kind("공고문.HWP") == "hwp" and guess_kind("x.hwpx") == "hwpx" and guess_kind("p.jpg") == "image"
