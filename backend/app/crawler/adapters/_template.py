"""새 게시판 어댑터 템플릿. 복사해서 파일 이름을 바꾸고 CSS 선택자를 실제 HTML에 맞춘다.
선택자는 추측하지 말고 브라우저 개발자도구(F12)로 실제 게시판 HTML을 보고 정한다."""
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Adapter, ListItem, PoliteClient, RawAttachment, RawNotice, guess_kind


class TemplateAdapter(Adapter):
    name = "게시판 이름"
    list_url = "https://example.khu.ac.kr/board/list"

    def fetch_list(self, client: PoliteClient, limit: int) -> list[ListItem]:
        soup = BeautifulSoup(client.get(self.list_url).text, "html.parser")
        items = []
        for row in soup.select("table tbody tr")[:limit]:  # TODO 실제 선택자
            a = row.select_one("a")
            if not a or not a.get("href"):
                continue
            date_el = row.select_one(".date")  # TODO 실제 선택자
            posted = None
            if date_el:
                try:
                    posted = datetime.strptime(date_el.get_text(strip=True), "%Y-%m-%d")
                except ValueError:
                    pass
            items.append(ListItem(url=urljoin(self.list_url, a["href"]), title=a.get_text(strip=True), posted_at=posted))
        return items

    def fetch_detail(self, client: PoliteClient, item: ListItem) -> RawNotice:
        soup = BeautifulSoup(client.get(item.url).text, "html.parser")
        body = soup.select_one(".view-content")  # TODO 실제 선택자
        atts = [
            RawAttachment(url=urljoin(item.url, a["href"]), filename=a.get_text(strip=True), kind=guess_kind(a.get_text(strip=True)))
            for a in soup.select(".attach a[href]")  # TODO 실제 선택자
        ]
        imgs = [urljoin(item.url, i["src"]) for i in (body.select("img[src]") if body else [])]
        return RawNotice(
            source_name=self.name,
            url=item.url,
            title=item.title,
            body_text=body.get_text("\n", strip=True) if body else "",
            posted_at=item.posted_at,
            attachments=atts,
            image_urls=imgs,
        )
