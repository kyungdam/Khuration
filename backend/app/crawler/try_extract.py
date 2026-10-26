"""크롤러 없이 파일 하나로 '읽기 → 조건 추출'을 끝까지 시험한다.

    python -m app.crawler.try_extract tests\\fixtures\\포스터.png
    python -m app.crawler.try_extract 공고문.hwp --title "2026 삼유장학 선발 공고"
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from ..llm import client, ocr
from ..parsers import parse_attachment
from .base import RawNotice
from .extract import extract


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--title", default="")
    a = p.parse_args()
    path = Path(a.file)
    data = path.read_bytes()
    res = parse_attachment(data, path.name)
    text = res.text
    if res.needs_ocr:
        text = ocr.ocr_pdf(data) if res.method == "pdf" else ocr.ocr_image(data)
        print(f"[OCR] {len(text)}자 읽음")
    print("---- 읽은 글 (앞 600자) ----\n" + text[:600] + "\n")
    if not client.available():
        print("(.env에 키가 없어 규칙 기반으로 추출합니다)")
    raw = RawNotice("테스트", "https://example.com/test", a.title or path.stem, "", posted_at=datetime.now())
    ex = extract(raw, text)
    print(f"---- 추출 결과 (engine={ex.engine}) ----")
    print(json.dumps({
        "category": ex.category, "topics": ex.topics,
        "deadline_utc": ex.deadline.isoformat() if ex.deadline else None,
        "criteria": ex.criteria, "summary": ex.summary,
        "summary_points": ex.summary_points, "checklist": ex.checklist,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
