"""대표 홈페이지 공지 어댑터 파싱 테스트. tests/fixtures/main_*.html은 실제 게시판에서 저장한 HTML."""
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from app.crawler.adapters import ADAPTERS
from app.crawler.adapters.khu_cms import block_text, parse_detail_board02, parse_list
from app.crawler.adapters.main_site import MAIN_BOARDS
from app.crawler.base import ListItem

FIX = Path(__file__).parent / "fixtures"
AD = MAIN_BOARDS["main"]


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_registered_boards():
    assert {"main", "main_academic", "main_scholarship", "main_work"} <= set(ADAPTERS)
    assert ADAPTERS["main_scholarship"].list_url == "https://www.khu.ac.kr/kor/user/bbs/BMSR00040/list.do?menuNo=200318"


def test_list_date_column_and_clean_title():
    items = parse_list(_html("main_list.html"), 20, AD.detail_url, AD.list_rows)
    assert len(items) == 10
    first = items[0]
    assert first.url == "https://www.khu.ac.kr/kor/user/bbs/BMSR00040/view.do?menuNo=200316&boardId=323360"
    assert first.title == "[국제교육원] ★등록마감임박★ 2026-5차 가을 정규 외국어 강좌 모집 공지"  # "서울" 표시 제거
    assert all(i.posted_at for i in items)  # 마지막 칸은 조회수라 날짜 칸을 따로 찾는다


def test_detail_text_body_keeps_lines_and_campus():
    item = ListItem(url=AD.detail_url("323360"), title="t")
    raw = parse_detail_board02(_html("main_view_text.html"), item, AD.name)
    lines = raw.body_text.splitlines()
    assert lines[0] == "캠퍼스: 서울"
    assert "10월 12일(월)부터 가을 정규 외국어강좌 접수를 진행하고 있습니다." in lines  # span으로 쪼개진 글자가 한 줄로
    assert raw.attachments == [] and len(raw.image_urls) == 2
    assert raw.posted_at == datetime(2026, 10, 26)


def test_detail_hwp_attachments():
    ad = MAIN_BOARDS["main_scholarship"]
    item = ListItem(url=ad.detail_url("323410"), title="t")
    raw = parse_detail_board02(_html("main_view_attach.html"), item, ad.name)
    assert raw.source_name == "경희대 공지(장학)"
    assert [a.kind for a in raw.attachments] == ["hwp", "hwp"]
    assert raw.attachments[0].url.startswith("https://www.khu.ac.kr/kor/cmmn/file/fileDown.do?menuNo=200318&")
    assert raw.body_text.startswith("캠퍼스: 공통")


def test_block_text():
    assert block_text(None) == ""
    html = "<div><p><span>10</span><span>월</span> 12일</p><p>a<br>b</p><p>&nbsp;</p></div>"
    assert block_text(BeautifulSoup(html, "html.parser").div) == "10월 12일\na\nb"
