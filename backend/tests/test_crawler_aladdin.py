"""알라딘 어댑터 테스트. tests/fixtures/aladdin_*.html은 실제 사이트에서 저장한 HTML (네트워크 없이 돈다)."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.crawler.adapters import ADAPTERS
from app.crawler.adapters.aladdin import AladdinAdapter, fetch, parse_detail, parse_list

FIX = Path(__file__).parent / "fixtures"


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


class FakeClient:
    """요청 URL을 기록하고 정해 둔 응답을 돌려준다."""

    def __init__(self, text="", final_url=None):
        self.text, self.final_url, self.urls = text, final_url, []

    def get(self, url):
        self.urls.append(url)
        return SimpleNamespace(text=self.text, url=self.final_url or url)


def test_list_clean_url_and_card():
    items = parse_list(_html("aladdin_list.html"), 20)
    assert len(items) == 10
    first = items[0]
    assert first.url == ("https://aladdin.khu.ac.kr/portfolio/ptfol/imng/icmpNsbjtPgm/"
                         "findIcmpNsbjtPgmInfo.do?encSddpbSeq=f0127b8880173ddf1712aa3d60d318c0")
    assert all("ssoReChk" not in i.url and "paginationInfo" not in i.url for i in items)
    assert first.title == "KHU-makers 14기 - AI 활용 오픈랩 홍보 기획단"
    assert first.posted_at == datetime(2026, 10, 22)  # 신청 시작일
    assert "캠퍼스: 국제캠퍼스" in first.card.splitlines()
    assert "신청학년: 1학년 2학년 3학년 4학년 5학년" in first.card.splitlines()


def test_detail_body_without_attachments():
    item = parse_list(_html("aladdin_list.html"), 1)[0]
    raw = parse_detail(_html("aladdin_view.html"), item, "알라딘 비교과")
    lines = raw.body_text.splitlines()
    assert raw.attachments == []  # 첨부 다운로드는 로그인 필요
    assert "첨부파일(로그인 필요): 26-2 KHU-Makers 14기 홍보 포스터.png" in lines
    assert "캠퍼스: 국제캠퍼스" in lines and "선정방법: 직접선발" in lines
    assert "2. 장학금 충족 요건 (직전학기 12학점 이상이수 및 평균평점 2.0 이상 필수)" in lines
    assert not any(ln.startswith(("과제제출", "출석관리")) for ln in lines)
    assert len(raw.image_urls) == 4
    assert all(u.startswith("https://aladdin.khu.ac.kr/portfolio/comm/cmfile/image.do?") for u in raw.image_urls)


def test_fetch_adds_sso_param_only_to_request():
    c = FakeClient("ok")
    assert fetch(c, "https://aladdin.khu.ac.kr/x/a.do?encSddpbSeq=1") == "ok"
    assert c.urls == ["https://aladdin.khu.ac.kr/x/a.do?encSddpbSeq=1&ssoReChk=ok"]


@pytest.mark.parametrize("final", [
    "https://aladdin.khu.ac.kr/portfolio/ksign/login_stand.jsp",
    "https://aladdin.khu.ac.kr/portfolio/common/user/ptfolSsoLogin.do?rtnUrl=1",
])
def test_fetch_stops_on_login_page(final):
    with pytest.raises(PermissionError):
        fetch(FakeClient("<html></html>", final_url=final), "https://aladdin.khu.ac.kr/x/a.do")


def test_fetch_list_stops_when_page_repeats():
    c = FakeClient(_html("aladdin_list.html"))
    items = AladdinAdapter().fetch_list(c, 25)
    assert len(items) == 10 and len(c.urls) == 2  # 2페이지가 같은 목록이면 멈춤
    assert c.urls[1].endswith("paginationInfo.currentPageNo=2&ssoReChk=ok")
    assert ADAPTERS["aladdin"].name == "알라딘 비교과"
