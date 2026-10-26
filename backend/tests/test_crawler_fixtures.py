"""게시판마다 저장해 둔 실제 목록·상세 HTML(tests/fixtures/crawler/)로 어댑터 파싱을 네트워크 없이 검사한다.
픽스처를 새로 받을 때는 같은 이름(<키>_list.html, <키>_view.html)으로 바꾸고 manifest.json도 같이 갱신한다.
실제 사이트를 부르는 검사는 맨 아래 test_live_* (KHU_LIVE=1 일 때만, 평소엔 skip)."""
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.crawler.adapters import ADAPTERS, aladdin
from app.crawler.adapters.khu_cms import MAX_AGE_DAYS, KhuCmsAdapter, parse_list
from app.crawler.adapters.urls import normalize_url
from app.crawler.base import ListItem, PoliteClient

FIX = Path(__file__).parent / "fixtures" / "crawler"
MANIFEST = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
FIXTURE_DAY = date.fromisoformat(MANIFEST["fixture_day"])
KEYS = sorted(MANIFEST["boards"])
KINDS = {"hwp", "hwpx", "pdf", "image", "other"}


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def _list(key, limit=50):
    ad = ADAPTERS[key]
    if isinstance(ad, KhuCmsAdapter):
        return parse_list(_html(f"{key}_list.html"), limit, ad.detail_url, ad.list_rows, today=FIXTURE_DAY)
    return aladdin.parse_list(_html(f"{key}_list.html"), limit, today=FIXTURE_DAY)


def _detail(key, item):
    ad = ADAPTERS[key]
    parse = ad.parse_detail if isinstance(ad, KhuCmsAdapter) else aladdin.parse_detail
    return parse(_html(f"{key}_view.html"), item, ad.name)


def test_every_registered_board_has_fixtures():
    assert set(KEYS) == set(ADAPTERS)
    for key in KEYS:
        assert (FIX / f"{key}_list.html").exists() and (FIX / f"{key}_view.html").exists()


@pytest.mark.parametrize("key", KEYS)
def test_list_items_are_clean(key):
    ad = ADAPTERS[key]
    items = _list(key)
    exp = MANIFEST["boards"][key]
    assert items, f"{key}: 목록에서 공지를 하나도 못 찾음 (게시판 구조가 바뀌었나?)"
    assert (items[0].url, items[0].title) == (exp["first_url"], exp["first_title"])
    urls = [i.url for i in items]
    assert len(urls) == len(set(urls))  # 고정 글 중복 없음
    host = urlparse(ad.list_url).netloc
    for i in items:
        assert i.url.startswith("https://") and urlparse(i.url).netloc == host
        assert normalize_url(i.url) == i.url and "ssoReChk" not in i.url
        assert i.title.strip()
        assert i.posted_at is not None
        assert (FIXTURE_DAY - i.posted_at.date()).days <= MAX_AGE_DAYS


@pytest.mark.parametrize("key", KEYS)
def test_detail_parses(key):
    ad = ADAPTERS[key]
    exp = MANIFEST["boards"][key]
    item = next((i for i in _list(key) if i.url == exp["view_url"]), None) or ListItem(url=exp["view_url"], title=exp["view_title"])
    raw = _detail(key, item)
    assert raw.source_name == ad.name and raw.url == item.url and raw.title == exp["view_title"]
    assert raw.body_text or raw.image_urls or raw.attachments, f"{key}: 본문·이미지·첨부가 모두 비어 있음"
    assert (len(raw.attachments), len(raw.image_urls)) == (exp["view_attachments"], exp["view_images"])
    for a in raw.attachments:
        assert a.url.startswith("https://") and a.filename and a.kind in KINDS
    assert all(u.startswith("https://") for u in raw.image_urls)


@pytest.mark.skipif(os.environ.get("KHU_LIVE") != "1", reason="실제 사이트 접속 검사는 KHU_LIVE=1 일 때만")
@pytest.mark.parametrize("key", KEYS)
def test_live_list_still_parses(key):
    """게시판 구조가 바뀌었는지 실제 사이트로 확인 (요청 1~2번, PoliteClient로 robots·간격 준수)"""
    c = PoliteClient()
    try:
        items = ADAPTERS[key].fetch_list(c, 1)
    finally:
        c.close()
    assert items and items[0].title.strip()
