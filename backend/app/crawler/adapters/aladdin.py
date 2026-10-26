"""알라딘(aladdin.khu.ac.kr) 교내비교과 프로그램. 규칙은 crawler/CLAUDE.md "알라딘 요령" 참고.
- 요청할 때만 ssoReChk=ok를 붙이고 저장 URL에서는 뺀다. 로그인 페이지로 넘어가면 PermissionError로 멈춘다.
- 첨부 다운로드는 로그인이 필요해서 RawAttachment로 넣지 않고 파일 이름만 본문에 남긴다.
- 캠퍼스·신청학년 등은 목록 카드에만 있어서 카드 내용을 본문 앞에 붙인다."""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Adapter, ListItem, PoliteClient, RawNotice
from .khu_cms import block_text, drop_disallowed_images

BASE = "https://aladdin.khu.ac.kr/portfolio/ptfol/imng/icmpNsbjtPgm/"
SSO_PARAM = "ssoReChk=ok"
LOGIN_URL = re.compile(r"/ksign/|login", re.I)
DOT_DATE = re.compile(r"\d{4}\.\d{2}\.\d{2}")
SKIP_ROWS = {"수료 인증서", "마일리지", "출석관리", "과제제출"}  # 신청 조건과 무관하거나 보는 사람마다 다른 칸


@dataclass
class AladdinItem(ListItem):
    card: str = ""  # 목록 카드 텍스트 (캠퍼스·신청대상·신청조건·신청학년 등)


def detail_url(seq: str) -> str:
    return f"{BASE}findIcmpNsbjtPgmInfo.do?encSddpbSeq={seq}"


def fetch(client: PoliteClient, url: str) -> str:
    """ssoReChk=ok는 요청에만 붙인다. 로그인/SSO 확인 페이지로 넘어가면 수집하지 않고 멈춘다."""
    r = client.get(url + ("&" if "?" in url else "?") + SSO_PARAM)
    if LOGIN_URL.search(str(r.url)):
        raise PermissionError(f"알라딘이 로그인 페이지로 보냄: {r.url}")
    return r.text


def _line(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse_list(html: str, limit: int) -> list[AladdinItem]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("div.lica_wrap > ul > li"):
        a = li.select_one("a.tit.detailBtn[data-params]")
        if not a:
            continue
        seq = json.loads(a["data-params"]).get("encSddpbSeq")
        if not seq:
            continue
        info = {_line(dl.dt): _line(dl.dd) for dl in li.select(".info_wrap dl") if dl.dt and dl.dd}
        lines = [f"상태: {_line(li.select_one('.label_box'))}",
                 "운영: " + " / ".join(_line(x) for x in li.select("ul.major_type li")),
                 _line(li.select_one("p.desc")),
                 *(f"{k}: {v}" for k, v in info.items())]
        m = DOT_DATE.search(info.get("신청기간", ""))  # 게시일 칸이 없어 신청 시작일을 쓴다
        items.append(AladdinItem(url=detail_url(seq), title=_line(a),
                                 posted_at=datetime.strptime(m.group(0), "%Y.%m.%d") if m else None,
                                 card="\n".join(ln for ln in lines if ln and not ln.endswith(": "))))
        if len(items) >= limit:
            break
    return items


def parse_detail(html: str, item: ListItem, source_name: str) -> RawNotice:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("#tilesContent")
    lines, imgs = [], []
    for tr in root.select("table.t_view tr") if root else []:
        label = ""
        for cell in tr.find_all(["th", "td"], recursive=False):
            if cell.name == "th":
                label = _line(cell)
                continue
            if label in SKIP_ROWS:
                continue
            if label == "첨부파일":
                names = [_line(a) for a in cell.select("ul.cmnFileLst a")]
                if names:
                    lines.append("첨부파일(로그인 필요): " + ", ".join(names))
            elif cell.select_one(".td_box"):  # 프로그램 주요내용
                lines.append(f"{label}:\n{block_text(cell.select_one('.td_box'))}")
                imgs += [urljoin(item.url, i["src"]) for i in cell.select("img[src]")]
            elif _line(cell):
                lines.append(f"{label}: {_line(cell)}")
    card = getattr(item, "card", "")
    return RawNotice(
        source_name=source_name,
        url=item.url,
        title=item.title,
        body_text="\n".join([card, *lines]).strip(),
        posted_at=item.posted_at,
        attachments=[],  # 첨부 다운로드는 로그인 필요 (CLAUDE.md 알라딘 요령)
        image_urls=imgs,
    )


class AladdinAdapter(Adapter):
    name = "알라딘 비교과"
    list_url = f"{BASE}findIcmpNsbjtPgmList.do?sort=0001"

    def fetch_list(self, client: PoliteClient, limit: int) -> list[ListItem]:
        items, page = [], 1
        while len(items) < limit:
            got = parse_list(fetch(client, f"{self.list_url}&paginationInfo.currentPageNo={page}"), limit - len(items))
            if not got or got[0].url in {i.url for i in items}:  # 마지막 페이지를 넘기면 빈 목록이나 같은 목록이 온다
                break
            items += got
            page += 1
        return items

    def fetch_detail(self, client: PoliteClient, item: ListItem) -> RawNotice:
        return drop_disallowed_images(client, parse_detail(fetch(client, item.url), item, self.name))
