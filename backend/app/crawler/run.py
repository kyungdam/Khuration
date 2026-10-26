"""크롤러 실행.
  python -m app.crawler.run --list                 # 등록된 어댑터
  python -m app.crawler.run --source eng --limit 3 --dry-run   # 저장 없이 출력만
  python -m app.crawler.run                        # 전체 실행 후 저장 (live용)
"""
import argparse

from ..db import Base, SessionLocal, engine
from ..parsers import parse_attachment
from .adapters import ADAPTERS
from .base import PoliteClient
from .extract import extract
from .store import upsert_notice


READABLE = (".hwp", ".hwpx", ".pdf", ".docx")


MAX_OCR_PER_NOTICE = 4  # 공지 하나에서 비전 모델에 보내는 이미지 상한 (비용 보호)


def read_attachments(client: PoliteClient, raw) -> dict[str, str]:
    """첨부·본문 이미지를 텍스트로. HWP/HWPX/DOCX/PDF는 파서, 이미지·스캔 PDF는 비전 모델(키 있을 때)."""
    from ..llm import ocr

    texts: dict[str, str] = {}
    ocr_used = 0
    targets = [(a.url, a.filename, a.kind) for a in raw.attachments]
    targets += [(u, u.rsplit("/", 1)[-1] or "image", "image") for u in raw.image_urls]
    for url, filename, kind in targets:
        is_image = kind == "image"
        if not is_image and not filename.lower().endswith(READABLE):
            continue
        try:
            data = client.get(url).content
            res = parse_attachment(data, filename)
        except Exception as e:
            print(f"    첨부 실패 {filename}: {e}")
            continue
        text = res.text
        if res.needs_ocr and ocr_used < MAX_OCR_PER_NOTICE:
            ocr_used += 1
            text = ocr.ocr_pdf(data) if res.method == "pdf" else ocr.ocr_image(data)
            print(f"    OCR {filename}: {len(text)}자")
        elif res.needs_ocr:
            print(f"    OCR 건너뜀(상한) {filename}")
        elif res.note:
            print(f"    첨부 {filename}: {res.method} {res.note}")
        if text:
            texts[url] = text
    return texts


def run(sources: list[str], limit: int, dry_run: bool) -> dict:
    Base.metadata.create_all(engine)
    client = PoliteClient()
    stats = {"new": 0, "changed": 0, "same": 0, "error": 0}
    try:
        with SessionLocal() as db:
            for key in sources:
                ad = ADAPTERS[key]
                try:
                    listing = ad.fetch_list(client, limit)
                except Exception as e:  # 게시판 하나(로그인 요구·구조 변경 등)가 다른 게시판을 멈추지 않게
                    stats["error"] += 1
                    print(f"[{key}] LIST ERROR {ad.list_url}: {e}")
                    continue
                for item in listing:
                    try:
                        raw = ad.fetch_detail(client, item)
                        attachment_texts = read_attachments(client, raw)
                        full = "\n".join([raw.body_text, *attachment_texts.values()])
                        ex = extract(raw, full)
                        if dry_run:
                            print(f"[{key}] {raw.title} | {ex.category} | 첨부 {len(raw.attachments)}(읽음 {len(attachment_texts)}) | 마감 {ex.deadline}")
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
