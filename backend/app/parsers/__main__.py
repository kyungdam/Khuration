"""로컬 파일로 파서 시험:  python -m app.parsers 공고문.hwp [다른파일.pdf ...]"""
import sys
from pathlib import Path

from . import parse_attachment


def main():
    if len(sys.argv) < 2:
        print("사용법: python -m app.parsers <파일> [파일 ...]")
        return
    for f in sys.argv[1:]:
        p = Path(f)
        res = parse_attachment(p.read_bytes(), p.name)
        print(f"===== {p.name} | {res.method} | {len(res.text)}자 | OCR필요={res.needs_ocr} {res.note}")
        print(res.text[:1500] + ("\n..." if len(res.text) > 1500 else ""))


if __name__ == "__main__":
    main()
