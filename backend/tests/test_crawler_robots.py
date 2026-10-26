"""robots.txt가 막는 본문 이미지는 어댑터가 image_urls에 넣지 않는다 (네트워크 없이)."""
from pathlib import Path
from types import SimpleNamespace
from urllib import robotparser
from urllib.parse import urlparse

from app.crawler.adapters.engineering import EngineeringAdapter
from app.crawler.adapters.main_site import MAIN_BOARDS
from app.crawler.base import USER_AGENT, ListItem

FIX = Path(__file__).parent / "fixtures"
# com.khu.ac.kr·eng.khu.ac.kr 등 학교 CMS 사이트의 실제 robots.txt 내용
CMS_ROBOTS = ["User-agent: *", "Disallow: /cms/", "Disallow: /upload/"]


class FakeClient:
    """저장된 HTML을 돌려주고, robots 판정은 PoliteClient._allowed와 같은 방식(robotparser)으로 한다."""

    def __init__(self, html, robots_by_host):
        self.html = html
        self.robots = {}
        for host, lines in robots_by_host.items():
            rp = robotparser.RobotFileParser()
            rp.parse(lines)
            self.robots[host] = rp

    def get(self, url):
        return SimpleNamespace(text=self.html, url=url)

    def _allowed(self, url):
        rp = self.robots.get(urlparse(url).netloc)
        return rp is None or rp.can_fetch(USER_AGENT, url)


def test_upload_poster_on_com_khu_is_dropped():
    ad = EngineeringAdapter()
    c = FakeClient((FIX / "eng_view_attach.html").read_text(encoding="utf-8"), {"com.khu.ac.kr": CMS_ROBOTS})
    raw = ad.fetch_detail(c, ListItem(url=ad.detail_url("556333"), title="t"))
    # 이 공지의 포스터는 com.khu.ac.kr/crosseditor/ 라 robots가 허용 → 그대로 남는다
    assert len(raw.image_urls) == 3 and all("/crosseditor/" in u for u in raw.image_urls)

    c = FakeClient((FIX / "eng_view_image.html").read_text(encoding="utf-8"), {"com.khu.ac.kr": CMS_ROBOTS})
    raw = ad.fetch_detail(c, ListItem(url=ad.detail_url("557542"), title="t"))
    assert raw.image_urls == []  # com.khu.ac.kr/upload/ 포스터는 빠진다


def test_allowed_host_keeps_images():
    """www.khu.ac.kr 는 robots.txt가 없다(오류 페이지) → /upload/ 이미지도 그대로"""
    ad = MAIN_BOARDS["main"]
    c = FakeClient((FIX / "main_view_text.html").read_text(encoding="utf-8"), {"com.khu.ac.kr": CMS_ROBOTS})
    raw = ad.fetch_detail(c, ListItem(url=ad.detail_url("323360"), title="t"))
    assert len(raw.image_urls) == 2 and all(u.startswith("https://www.khu.ac.kr/upload/") for u in raw.image_urls)
