"""경희대 공통 CMS 게시판(BMSR00040 등) 어댑터. 공과대학·화학공학과처럼 같은 CMS를 쓰는 게시판은 이걸 상속해
site·board_path·menu_no만 바꾼다.
목록: div.bbs_tbl-st1 table > tbody > tr. 일반 글은 a[href="javascript:view('ID')"]이고 상세는 GET view.do?menuNo=&boardId=로 열린다.
상단 고정 글 중 다른 사이트(예: 대표 홈페이지 www.khu.ac.kr) 공지로 바로 가는 링크는 그 사이트 어댑터 몫이라 건너뛴다.
상세: article.bbs-view (h2.t 제목, header .info 등록일·첨부파일, .bbs-view_c 본문)."""
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Adapter, ListItem, PoliteClient, RawAttachment, RawNotice, guess_kind

VIEW_ID = re.compile(r"view\('(\d+)'")
BLOCKS = ["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "table"]


def parse_date(text: str) -> datetime | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?", text)
    if not m:
        return None
    return datetime.strptime(m.group(0), "%Y-%m-%d %H:%M:%S" if m.group(1) else "%Y-%m-%d")


def block_text(el) -> str:
    """에디터가 글자를 <span>으로 잘게 나눠도 문단(p/div/li…)과 <br> 단위로만 줄을 바꾼다."""
    if el is None:
        return ""
    el = BeautifulSoup(str(el), "html.parser")  # 원본 soup은 건드리지 않음
    for br in el.find_all("br"):
        br.replace_with("\n")
    for b in el.find_all(BLOCKS):
        b.append("\n")
    lines = (re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in el.get_text("").splitlines())
    return "\n".join(ln for ln in lines if ln)


def parse_list(html: str, limit: int, detail_url, rows: str = "div.bbs_tbl-st1 table tbody tr") -> list[ListItem]:
    soup = BeautifulSoup(html, "html.parser")
    items, seen = [], set()
    for row in soup.select(rows):
        a = row.select_one("td.tal a[href]")
        m = VIEW_ID.search(a["href"]) if a else None
        if not m or m.group(1) in seen:  # 고정 글이 일반 목록에도 다시 나온다
            continue
        seen.add(m.group(1))
        for tag in a.select("span.txtBox01"):  # All/Seoul/Global 캠퍼스 표시
            tag.decompose()
        dates = (parse_date(td.get_text(strip=True)) for td in row.select("td"))  # 등록일 칸 위치가 사이트마다 다름
        items.append(ListItem(url=detail_url(m.group(1)), title=a.get_text(" ", strip=True),
                              posted_at=next((d for d in dates if d), None)))
        if len(items) >= limit:
            break
    return items


def drop_disallowed_images(client: PoliteClient, raw: RawNotice) -> RawNotice:
    """robots.txt가 막는 경로(예: com.khu.ac.kr/upload/)의 본문 이미지는 image_urls에서 뺀다.
    넣어 두면 run.py가 내려받으려다 거부되고 글자 없는 빈 행만 남는다. 판정은 PoliteClient가 한다."""
    raw.image_urls = [u for u in raw.image_urls if client._allowed(u)]
    return raw


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
        body_text=block_text(body),
        posted_at=posted or item.posted_at,
        attachments=atts,
        image_urls=[urljoin(item.url, i["src"]) for i in (body.select("img[src]") if body else [])],
    )


def parse_detail_board02(html: str, item: ListItem, source_name: str) -> RawNotice:
    """대표 홈페이지(www.khu.ac.kr)형 상세: div.board02 > .row(제목·날짜) / .row.contents(본문) / .row.addFile(첨부).
    캠퍼스 표시(서울/국제/공통)는 저장할 칸이 없어서 본문 첫 줄에 "캠퍼스: 서울"로 남긴다 (조건 추출에서 사용)."""
    soup = BeautifulSoup(html, "html.parser")
    view = soup.select_one("div.board02")
    body = view.select_one(".row.contents") if view else None
    atts = []
    for a in view.select(".row.addFile a[href*='fileDown.do']") if view else []:
        name = a.get_text(strip=True)
        atts.append(RawAttachment(url=urljoin(item.url, a["href"]), filename=name, kind=guess_kind(name)))
    campus = view.select_one(".tit span.txtBox01") if view else None
    date = view.select_one(".dateBox .date") if view else None
    text = block_text(body)
    if campus and campus.get_text(strip=True):
        text = f"캠퍼스: {campus.get_text(strip=True)}\n{text}".strip()
    return RawNotice(
        source_name=source_name,
        url=item.url,
        title=item.title,
        body_text=text,
        posted_at=(parse_date(date.get_text()) if date else None) or item.posted_at,
        attachments=atts,
        image_urls=[urljoin(item.url, i["src"]) for i in (body.select("img[src]") if body else [])],
    )


class KhuCmsAdapter(Adapter):
    site = ""        # 예: "https://eng.khu.ac.kr"
    board_path = ""  # 예: "/eng_kor/user/bbs/BMSR00040/"
    menu_no = ""
    list_rows = "div.bbs_tbl-st1 table tbody tr"
    parse_detail = staticmethod(parse_detail)

    def __init__(self, name: str | None = None, menu_no: str | None = None):
        """한 사이트에 게시판이 여럿이면 인스턴스마다 이름·menuNo만 바꿔 등록한다."""
        if name:
            self.name = name
        if menu_no:
            self.menu_no = menu_no

    @property
    def list_url(self) -> str:
        return f"{self.site}{self.board_path}list.do?menuNo={self.menu_no}"

    def detail_url(self, board_id: str) -> str:
        """같은 공지는 늘 같은 URL (페이지 번호·검색 조건 등은 넣지 않음)"""
        return f"{self.site}{self.board_path}view.do?menuNo={self.menu_no}&boardId={board_id}"

    def fetch_list(self, client: PoliteClient, limit: int) -> list[ListItem]:
        return parse_list(client.get(self.list_url).text, limit, self.detail_url, self.list_rows)

    def fetch_detail(self, client: PoliteClient, item: ListItem) -> RawNotice:
        return drop_disallowed_images(client, self.parse_detail(client.get(item.url).text, item, self.name))
