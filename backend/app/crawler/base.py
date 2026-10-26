"""크롤러 공통 타입과 예의 바른 HTTP 클라이언트."""
import time
from dataclasses import dataclass, field
from datetime import datetime
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = "KhurationBot/0.1 (student contest project; contact: repo owner)"
REQUEST_DELAY_SEC = 2.0  # 같은 사이트에 요청 사이 최소 간격


@dataclass
class ListItem:
    """게시판 목록의 한 줄"""
    url: str  # 상세 페이지 절대 URL (공지의 고유 키)
    title: str
    posted_at: datetime | None = None


@dataclass
class RawAttachment:
    url: str
    filename: str
    kind: str  # hwp | hwpx | pdf | image | other


@dataclass
class RawNotice:
    """상세 페이지에서 뽑은 원본. 아직 LLM 추출 전."""
    source_name: str
    url: str
    title: str
    body_text: str
    posted_at: datetime | None = None
    attachments: list[RawAttachment] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)  # 본문 포스터 이미지


def guess_kind(filename: str) -> str:
    f = filename.lower()
    for ext, kind in ((".hwpx", "hwpx"), (".hwp", "hwp"), (".pdf", "pdf")):
        if f.endswith(ext):
            return kind
    if f.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    return "other"


class PoliteClient:
    """robots.txt 확인 + 요청 간격 + 공통 User-Agent. 모든 어댑터는 이것만 쓴다."""

    def __init__(self, delay: float = REQUEST_DELAY_SEC):
        self.delay = delay
        self._last: dict[str, float] = {}
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self.http = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)

    def _allowed(self, url: str) -> bool:
        host = urlparse(url).scheme + "://" + urlparse(url).netloc
        if host not in self._robots:
            rp = robotparser.RobotFileParser()
            try:
                r = self.http.get(urljoin(host, "/robots.txt"))
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                self._robots[host] = rp
            except httpx.HTTPError:
                self._robots[host] = None  # robots.txt를 못 읽으면 허용으로 간주하되 간격은 지킨다
        rp = self._robots[host]
        return rp is None or rp.can_fetch(USER_AGENT, url)

    def get(self, url: str) -> httpx.Response:
        if not self._allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        host = urlparse(url).netloc
        wait = self.delay - (time.monotonic() - self._last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.http.get(url)
        finally:
            self._last[host] = time.monotonic()
        r.raise_for_status()
        return r

    def close(self):
        self.http.close()


class Adapter:
    """게시판 하나 = 어댑터 하나. adapters/ 아래에 만들고 adapters/__init__.py에 등록."""

    name: str = ""  # 앱에 표시될 출처 이름, 예: "공과대학"
    list_url: str = ""

    def fetch_list(self, client: PoliteClient, limit: int) -> list[ListItem]:
        raise NotImplementedError

    def fetch_detail(self, client: PoliteClient, item: ListItem) -> RawNotice:
        raise NotImplementedError
