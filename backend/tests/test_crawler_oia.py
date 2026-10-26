"""국제교류처 어댑터 파싱 테스트. tests/fixtures/oia_*.html은 실제 게시판에서 저장한 HTML."""
from datetime import date, datetime
from pathlib import Path

from app.crawler.adapters import ADAPTERS
from app.crawler.adapters.khu_cms import parse_detail, parse_list
from app.crawler.adapters.oia import OIA_BOARDS
from app.crawler.base import ListItem

FIXTURE_DAY = date(2026, 10, 27)  # 픽스처 HTML을 저장한 날 (90일 필터 기준일 고정)
FIX = Path(__file__).parent / "fixtures"
AD = OIA_BOARDS["oia_outgoing"]


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_registered_boards():
    assert ADAPTERS["oia"].list_url == "https://oia.khu.ac.kr/oiak_kor/user/bbs/BMSR00040/list.do?menuNo=5800010"
    assert ADAPTERS["oia_outgoing"].name == "국제교류처(파견 프로그램)"


def test_list():
    items = parse_list(_html("oia_list_out.html"), 20, AD.detail_url, AD.list_rows, today=FIXTURE_DAY)
    assert len(items) == 4  # 10건 중 6건(06-05~07-21, 고정 글 포함)은 90일이 넘어 뺀다
    assert items[0].url == "https://oia.khu.ac.kr/oiak_kor/user/bbs/BMSR00040/view.do?menuNo=5800012&boardId=556358"
    assert items[0].title == "[국제교류팀] 2026 동계 SDGs 국제화연수 (Lincoln University) 선발 공고"  # "공통" 표시 제거
    assert items[0].posted_at == datetime(2026, 10, 13)


def test_detail_pdf_and_docx():
    item = ListItem(url=AD.detail_url("556358"), title="t")
    raw = parse_detail(_html("oia_view_out.html"), item, AD.name)
    assert raw.posted_at == datetime(2026, 10, 13, 11, 16, 44)
    assert [a.filename.rsplit(".", 1)[1] for a in raw.attachments] == ["pdf", "docx"]
    assert raw.attachments[0].url.startswith("https://oia.khu.ac.kr/oiak_kor/cmmn/file/fileDown.do?menuNo=5800012&")
    assert "1. 지원 기간 : 2026.10.25.(일) 23:59까지" in raw.body_text.splitlines()


def test_detail_image_attachments():
    ad = OIA_BOARDS["oia"]
    raw = parse_detail(_html("oia_view_notice.html"), ListItem(url=ad.detail_url("556046"), title="t"), ad.name)
    assert [a.kind for a in raw.attachments] == ["image", "image"]  # 포스터 jpg 첨부는 OCR 연결 전까지 건너뜀
    assert raw.body_text
