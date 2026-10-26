"""시연(demo)/실제(live) 모드 분리: 실제 모드엔 [데모] 공지가 안 나오고, 시연 모드엔 크롤링 공지가 안 나온다."""
from fastapi.testclient import TestClient

from app.config import settings
from app.crawler.base import RawNotice
from app.crawler.extract import EMPTY_CRITERIA, Extracted
from app.crawler.store import upsert_notice
from app.db import SessionLocal
from app.main import app

CRAWLED_URL = "https://example.org/crawled/mode-test"


def _add_crawled():
    raw = RawNotice(source_name="테스트 게시판", url=CRAWLED_URL, title="실제 장학 공지", body_text="본문")
    ex = Extracted(category="장학", topics=["scholarship"], deadline=None, criteria=dict(EMPTY_CRITERIA), summary="요약")
    with SessionLocal() as db:
        n, _ = upsert_notice(db, raw, ex)
        return n.id


def test_demo_mode_hides_crawled_and_live_hides_demo(monkeypatch):
    with TestClient(app) as c:  # demo 모드로 시작 → 시연 공지가 들어간다
        crawled_id = _add_crawled()
        demo_list = c.get("/notices").json()
        assert demo_list and all(i["title"].startswith("[데모]") for i in demo_list)
        assert c.get(f"/notices/{crawled_id}").status_code == 404
        demo_id = demo_list[0]["id"]

        monkeypatch.setattr(settings, "app_mode", "live")
        live_list = c.get("/notices").json()
        assert CRAWLED_URL in [i["url"] for i in live_list]  # 다른 테스트의 크롤링 공지도 같은 DB에 있을 수 있다
        assert not any(i["title"].startswith("[데모]") or "/demo/" in i["url"] for i in live_list)
        assert c.get(f"/notices/{demo_id}").status_code == 404
        assert c.get(f"/notices/{crawled_id}").status_code == 200


def test_health_today_follows_demo_clock():
    with TestClient(app) as c:
        h0 = c.get("/health").json()
        assert h0["mode"] == "demo" and h0["offset_days"] == 0
        c.post("/demo/advance-clock", json={"days": 3})
        h1 = c.get("/health").json()
        assert h1["offset_days"] == 3 and h1["today"] > h0["today"]
        c.post("/demo/reset-clock")
        assert c.get("/health").json()["today"] == h0["today"]


def test_change_notice_counts_from_demo_clock():
    """시계를 앞당긴 뒤 마감을 D-2로 바꾸면 앞당긴 날짜 기준 D-2 → 변경 알림을 보낼 수 있다."""
    tags = {"campus": "global", "grade": 3, "interests": ["ai_data"]}
    h = {"X-Device-Token": "web-mode-test"}
    with TestClient(app) as c:
        c.post("/demo/reseed")
        c.post("/devices", json={"push_token": "web-mode-test", "tags": tags})
        top = c.get("/feed", headers=h).json()[0]
        c.post("/demo/advance-clock", json={"days": 5})
        c.post("/demo/change-notice", json={"notice_id": top["id"], "deadline_in_days": 2})
        assert c.get(f"/notices/{top['id']}", headers=h).json()["d_day"] == 2
        p = c.post("/demo/fire-push", headers=h, json={"kind": "changed", "notice_id": top["id"]}).json()
        assert p["preview"]["title"] == "공지가 변경됐어요"
        c.post("/demo/reset-clock")


def test_seed_loads_even_when_only_crawled_notices_exist():
    from app.models import Notice
    from app.seed_loader import load_seed

    with SessionLocal() as db:
        db.query(Notice).filter(Notice.is_demo.is_(True)).delete()
        db.commit()
        _add_crawled()
        assert load_seed(db) > 0  # 크롤링 공지만 있어도 시연 공지는 넣는다
