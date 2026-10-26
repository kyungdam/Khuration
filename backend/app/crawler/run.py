"""크롤러 실행.
  python -m app.crawler.run --list                 # 등록된 어댑터
  python -m app.crawler.run --source eng --limit 3 --dry-run   # 저장 없이 출력만
  python -m app.crawler.run                        # 전체 실행 후 저장 (live용)
"""
import argparse

from ..db import Base, SessionLocal, engine
from .adapters import ADAPTERS
from .base import PoliteClient
from .extract import extract
from .store import upsert_notice


def run(sources: list[str], limit: int, dry_run: bool) -> dict:
    Base.metadata.create_all(engine)
    client = PoliteClient()
    stats = {"new": 0, "changed": 0, "same": 0, "error": 0}
    try:
        with SessionLocal() as db:
            for key in sources:
                ad = ADAPTERS[key]
                for item in ad.fetch_list(client, limit):
                    try:
                        raw = ad.fetch_detail(client, item)
                        # TODO(파서 담당): 첨부(HWP/PDF)·이미지 텍스트를 parsers/로 뽑아 합치기
                        attachment_texts: dict[str, str] = {}
                        full = "\n".join([raw.body_text, *attachment_texts.values()])
                        ex = extract(raw, full)
                        if dry_run:
                            print(f"[{key}] {raw.title} | {ex.category} | 첨부 {len(raw.attachments)} | 마감 {ex.deadline}")
                            continue
                        _, change = upsert_notice(db, raw, ex, attachment_texts)
                        stats[change] += 1
                        # TODO(푸시 담당): change가 new/changed면 매칭되는 기기에 알림
                    except Exception as e:  # 공지 하나 실패가 전체를 멈추지 않게
                        stats["error"] += 1
                        print(f"[{key}] ERROR {item.url}: {e}")
    finally:
        client.close()
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", help="어댑터 키 (여러 번 가능). 생략하면 전체")
    p.add_argument("--limit", type=int, default=20, help="게시판당 최신 N개")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    if a.list:
        print("\n".join(f"{k}: {v.name} {v.list_url}" for k, v in ADAPTERS.items()) or "(등록된 어댑터 없음)")
        return
    print(run(a.source or list(ADAPTERS), a.limit, a.dry_run))


if __name__ == "__main__":
    main()
