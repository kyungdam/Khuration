"""화학공학과 어댑터 파싱 테스트. tests/fixtures/chemeng_*.html은 실제 게시판에서 저장한 HTML."""
from datetime import datetime
from pathlib import Path

from app.crawler.adapters.chemeng import ChemEngAdapter
from app.crawler.adapters.khu_cms import parse_detail, parse_list
from app.crawler.base import ListItem

FIX = Path(__file__).parent / "fixtures"
AD = ChemEngAdapter()


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_list_dedups_pinned_rows():
    items = parse_list(_html("chemeng_list.html"), 50, AD.detail_url)
    urls = [i.url for i in items]
    assert len(urls) == len(set(urls)) == 13  # 학과 고정 글 5개 중 2개는 일반 목록에도 있어 한 번만
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
