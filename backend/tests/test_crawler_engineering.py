"""공과대학 어댑터 파싱 테스트. tests/fixtures/eng_*.html은 실제 게시판에서 저장한 HTML (네트워크 없이 돈다)."""
from datetime import datetime
from pathlib import Path

from app.crawler.adapters.engineering import detail_url, parse_detail, parse_list
from app.crawler.base import ListItem

FIX = Path(__file__).parent / "fixtures"


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_list_skips_main_site_links_and_cleans_url():
    items = parse_list(_html("eng_list.html"), 20)
    assert len(items) == 10  # 고정 글 5개는 대표 홈페이지 링크라 제외
    first = items[0]
    assert first.url == "https://eng.khu.ac.kr/eng_kor/user/bbs/BMSR00040/view.do?menuNo=17100020&boardId=557542"
    assert first.title == "2026학년도 동계 계절학기 운영 및 강좌 개설 안내"  # 캠퍼스 표시 "All" 제거
    assert first.posted_at == datetime(2026, 10, 26)
    assert all("eng.khu.ac.kr" in i.url and "pageIndex" not in i.url for i in items)
    assert len(parse_list(_html("eng_list.html"), 3)) == 3


def test_detail_with_attachment():
    item = ListItem(url=detail_url("556333"), title="2026-겨울학기 단기현장실습 시행 안내")
    raw = parse_detail(_html("eng_view_attach.html"), item, "공과대학")
    assert raw.source_name == "공과대학" and raw.url == item.url
    assert raw.posted_at == datetime(2026, 10, 13, 10, 12, 45)
    assert len(raw.attachments) == 1
    att = raw.attachments[0]
    assert att.filename == "현장실습 안내문_2026-겨울학기.pdf" and att.kind == "pdf"
    assert att.url.startswith("https://eng.khu.ac.kr/eng_kor/cmmn/file/fileDown.do?")
    assert len(raw.image_urls) == 3 and all(u.startswith("https://") for u in raw.image_urls)


def test_detail_image_only_body():
    item = ListItem(url=detail_url("557542"), title="2026학년도 동계 계절학기 운영 및 강좌 개설 안내")
    raw = parse_detail(_html("eng_view_image.html"), item, "공과대학")
    assert raw.attachments == [] and raw.body_text == ""  # 본문이 포스터 이미지뿐
    assert len(raw.image_urls) == 1
