"""게시일이 90일보다 오래된 글은 고정 글이어도 목록에서 뺀다 (어댑터 공통)."""
from datetime import date, datetime
from pathlib import Path

from app.crawler.adapters.aladdin import parse_list as aladdin_list
from app.crawler.adapters.chemeng import ChemEngAdapter
from app.crawler.adapters.khu_cms import MAX_AGE_DAYS, parse_list, too_old

FIX = Path(__file__).parent / "fixtures"


def test_too_old_boundary():
    today = date(2026, 10, 27)
    assert MAX_AGE_DAYS == 90
    assert not too_old(datetime(2026, 7, 29), today)  # 정확히 90일 → 남김
    assert too_old(datetime(2026, 7, 28), today)  # 91일 → 뺌
    assert not too_old(None, today)  # 게시일을 모르면 빼지 않는다


def test_old_pinned_post_dropped_and_limit_counts_only_kept():
    html = (FIX / "chemeng_list.html").read_text(encoding="utf-8")
    ad = ChemEngAdapter()
    titles = [i.title for i in parse_list(html, 5, ad.detail_url, today=date(2026, 10, 27))]
    assert len(titles) == 5 and not any("신입생 OT" in t for t in titles)  # 빠진 자리는 다음 글로 채운다
    # 같은 HTML이라도 기준일이 2월이면 OT 글은 최신 글이라 남는다
    assert any("신입생 OT" in i.title for i in parse_list(html, 50, ad.detail_url, today=date(2026, 2, 10)))


def test_aladdin_uses_application_start_as_age():
    html = (FIX / "aladdin_list.html").read_text(encoding="utf-8")
    assert len(aladdin_list(html, 20, today=date(2026, 10, 27))) == 10
    assert aladdin_list(html, 20, today=date(2027, 6, 1)) == []  # 모두 신청 시작이 90일 넘게 지남
