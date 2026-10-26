import io
import struct
import zipfile
from pathlib import Path

import pytest

from app.parsers import clean, detect, parse_attachment
from app.parsers.hwp import HWPTAG_PARA_TEXT, para_text, records_to_text
from app.parsers.hwpx import extract_hwpx

FIX = Path(__file__).parent / "fixtures"


def _rec(tag: int, payload: bytes) -> bytes:
    size = len(payload)
    if size < 0xFFF:
        return struct.pack("<I", tag | (size << 20)) + payload
    return struct.pack("<I", tag | (0xFFF << 20)) + struct.pack("<I", size) + payload


def _u16(s: str) -> bytes:
    return s.encode("utf-16-le")


def test_hwp_para_text_controls():
    # 일반 글자 + 확장 컨트롤(표, 8칸) + 탭(8칸) + 문단 끝(13)
    table_ctrl = struct.pack("<8H", 11, 0x7462, 0x6C20, 0, 0, 0, 0, 11)
    tab = struct.pack("<8H", 9, 0, 0, 0, 0, 0, 0, 9)
    payload = _u16("지원 자격") + table_ctrl + _u16("학점") + tab + _u16("3.0 이상") + struct.pack("<H", 13)
    assert para_text(payload) == "지원 자격학점\t3.0 이상\n"


def test_hwp_records_skip_other_tags_and_long_size():
    long_text = "가" * 3000  # 6000바이트 > 0xFFF → 확장 크기 헤더
    stream = (
        _rec(66, b"\x00" * 10)  # PARA_HEADER (무시)
        + _rec(HWPTAG_PARA_TEXT, _u16("2026 장학생 선발") + struct.pack("<H", 13))
        + _rec(68, b"\x01" * 4)  # CHAR_SHAPE (무시)
        + _rec(HWPTAG_PARA_TEXT, _u16(long_text) + struct.pack("<H", 13))
    )
    out = records_to_text(stream)
    assert out.split("\n")[0] == "2026 장학생 선발"
    assert out.split("\n")[1] == long_text


def _hwpx(sections: dict[str, str]) -> bytes:
    ns = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        for name, body in sections.items():
            z.writestr(f"Contents/{name}", f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {ns}>{body}</hs:sec>')
    return buf.getvalue()


def test_hwpx_paragraphs_and_tables():
    body = (
        "<hp:p><hp:run><hp:t>모집 </hp:t></hp:run><hp:run><hp:t>공고</hp:t></hp:run></hp:p>"
        "<hp:p><hp:run><hp:tbl><hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>대상</hp:t></hp:run></hp:p></hp:subList></hp:tc>"
        "<hp:tc><hp:subList><hp:p><hp:run><hp:t>3~4학년</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>"
    )
    data = _hwpx({"section0.xml": body, "section1.xml": "<hp:p><hp:run><hp:t>마감 11월 6일</hp:t></hp:run></hp:p>"})
    assert detect(data, "공고.hwpx") == "hwpx"
    assert extract_hwpx(data).split("\n") == ["모집 공고", "대상", "3~4학년", "마감 11월 6일"]
    res = parse_attachment(data, "공고.hwpx")
    assert res.method == "hwpx" and "3~4학년" in res.text


def test_docx():
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    xml = f'<w:document {ns}><w:body><w:p><w:r><w:t>개인정보 </w:t></w:r><w:r><w:t>동의서</w:t></w:r></w:p><w:p><w:r><w:t>동의함</w:t></w:r></w:p></w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    res = parse_attachment(buf.getvalue(), "동의서.docx")
    assert res.method == "docx" and res.text == "개인정보 동의서\n동의함"


def test_detect_and_unsupported():
    assert detect(b"%PDF-1.7 ...", "a.bin") == "pdf"
    assert detect(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 8, "x.hwp") == "hwp5"
    assert detect(b"\x89PNG\r\n\x1a\n", "poster.png") == "image"
    assert parse_attachment(b"\x89PNG\r\n\x1a\n", "p.png").needs_ocr is True
    assert parse_attachment(b"hello", "a.txt").method == "none"
    assert parse_attachment(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1garbage", "x.hwp").note.startswith("error")


def test_clean():
    assert clean("  a   b \r\n\n\n\nc  ") == "a b\n\nc"


def test_pdf_text_and_scanned():
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Scholarship application deadline 2026-11-06, GPA 3.0 or higher, grade 3-4")
    text_pdf = doc.tobytes()
    blank = pymupdf.open()
    blank.new_page()
    res = parse_attachment(text_pdf, "a.pdf")
    assert res.method == "pdf" and "GPA 3.0" in res.text and res.needs_ocr is False
    assert parse_attachment(blank.tobytes(), "scan.pdf").needs_ocr is True


@pytest.mark.parametrize("name", sorted(p.name for p in FIX.glob("*")) if FIX.exists() else [])
def test_real_fixtures_parse(name):
    """tests/fixtures/ 에 실제 공고 파일(hwp/hwpx/pdf)을 넣으면 자동으로 검사"""
    if name.endswith((".html", ".htm", ".json", ".md")):
        pytest.skip("not an attachment")
    res = parse_attachment((FIX / name).read_bytes(), name)
    assert res.text or res.needs_ocr or res.note, f"{name}: 아무것도 못 읽음"
