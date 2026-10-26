"""화학공학과 어댑터 파싱 테스트. tests/fixtures/chemeng_*.html은 실제 게시판에서 저장한 HTML."""
from datetime import date, datetime
from pathlib import Path

from app.crawler.adapters.chemeng import ChemEngAdapter
from app.crawler.adapters.khu_cms import parse_detail, parse_list
from app.crawler.base import ListItem

FIXTURE_DAY = date(2026, 10, 27)  # 픽스처 HTML을 저장한 날 (90일 필터 기준일 고정)
FIX = Path(__file__).parent / "fixtures"
AD = ChemEngAdapter()


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_list_dedups_pinned_rows():
    items = parse_list(_html("chemeng_list.html"), 50, AD.detail_url, today=FIXTURE_DAY)
    urls = [i.url for i in items]
    # 학과 고정 글 5개 중 2개는 일반 목록에도 있어 한 번만, 2026-02-05 신입생 OT 고정 글은 90일이 넘어 뺀다
    assert len(urls) == len(set(urls)) == 12
    assert not any("신입생 OT" in i.title for i in items)
    assert any("장학금 규정" in i.title for i in items)  # 2026-08-07 고정 글은 81일 → 남는다
    assert all((FIXTURE_DAY - i.posted_at.date()).days <= 90 for i in items)
    assert items[0].url == "https://chemeng.khu.ac.kr/chemeng/user/bbs/BMSR00040/view.do?menuNo=17600017&boardId=557620"
    assert items[0].title == "[공과대학] 공과대학 특성화 장학 프로그램 참여학생 모집 안내"
    assert items[0].posted_at == datetime(2026, 10, 26)
    assert all(u.startswith("https://chemeng.khu.ac.kr/") for u in urls)


def test_detail_hwp_attachments():
    item = ListItem(url=AD.detail_url("557620"), title="t")
    raw = parse_detail(_html("chemeng_view_attach.html"), item, AD.name)
    assert raw.source_name == "화학공학과"
    assert raw.posted_at == datetime(2026, 10, 26, 15, 7, 14)
    assert [a.kind for a in raw.attachments] == ["hwp", "hwp"]
    assert raw.attachments[0].filename == "공과대학 특성화 장학 프로그램 신청서fv.hwp"
    assert raw.attachments[1].url.endswith("fileSn=2&bbsId=BMSR00040")
    assert len(raw.image_urls) == 1
