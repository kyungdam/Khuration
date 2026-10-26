"""공과대학(국문) 공대마당 공지사항 어댑터.
목록: table.bbs_tbl-st1 > tbody > tr. 일반 글은 a[href="javascript:view('ID')"]이고 상세는 GET view.do?menuNo=&boardId=로 열린다.
상단 고정 글 중 대표 홈페이지(www.khu.ac.kr) 공지로 바로 가는 링크는 "main" 어댑터 몫이라 건너뛴다.
상세: article.bbs-view (h2.t 제목, .info 등록일·첨부파일, .bbs-view_c 본문)."""
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Adapter, ListItem, PoliteClient, RawAttachment, RawNotice, guess_kind

BASE = "https://eng.khu.ac.kr/eng_kor/user/bbs/BMSR00040/"
MENU_NO = "17100020"
VIEW_ID = re.compile(r"view\('(\d+)'\)")


def detail_url(board_id: str) -> str:
    """같은 공지는 늘 같은 URL (페이지 번호·검색 조건 등은 넣지 않음)"""
    return f"{BASE}view.do?menuNo={MENU_NO}&boardId={board_id}"


def parse_date(text: str) -> datetime | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?", text)
    if not m:
        return None
    return datetime.strptime(m.group(0), "%Y-%m-%d %H:%M:%S" if m.group(1) else "%Y-%m-%d")


def parse_list(html: str, limit: int) -> list[ListItem]:
    soup = BeautifulSoup(html, "html.parser")
    items, seen = [], set()
    for row in soup.select("div.bbs_tbl-st1 table tbody tr"):
        a = row.select_one("td.tal a[href]")
        m = VIEW_ID.search(a["href"]) if a else None
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        for tag in a.select("span.txtBox01"):  # All/Seoul/Global 캠퍼스 표시
            tag.decompose()
        items.append(ListItem(url=detail_url(m.group(1)), title=a.get_text(" ", strip=True),
                              posted_at=parse_date(row.select("td")[-1].get_text(strip=True))))
        if len(items) >= limit:
            break
    return items


def parse_detail(html: str, item: ListItem, source_name: str) -> RawNotice:
    soup = BeautifulSoup(html, "html.parser")
    view = soup.select_one("article.bbs-view")
    body = view.select_one(".bbs-view_c") if view else None
    atts = []
    for a in view.select("header .info a[href*='fileDown.do']") if view else []:
        name = a.get_text(strip=True)
        atts.append(RawAttachment(url=urljoin(item.url, a["href"]), filename=name, kind=guess_kind(name)))
    posted = None
    for info in view.select("header .info .item") if view else []:
        if info.strong and "등록일" in info.strong.get_text():
            posted = parse_date(info.get_text(" ", strip=True))
    return RawNotice(
        source_name=source_name,
        url=item.url,
        title=item.title,
        body_text=body.get_text("\n", strip=True) if body else "",
        posted_at=posted or item.posted_at,
        attachments=atts,
        image_urls=[urljoin(item.url, i["src"]) for i in (body.select("img[src]") if body else [])],
    )


class EngineeringAdapter(Adapter):
    name = "공과대학"
    list_url = f"{BASE}list.do?menuNo={MENU_NO}"

    def fetch_list(self, client: PoliteClient, limit: int) -> list[ListItem]:
        return parse_list(client.get(self.list_url).text, limit)

    def fetch_detail(self, client: PoliteClient, item: ListItem) -> RawNotice:
        return parse_detail(client.get(item.url).text, item, self.name)
