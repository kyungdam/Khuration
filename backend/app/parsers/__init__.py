"""첨부 파일 → 텍스트. 형식은 확장자가 아니라 파일 앞부분(매직 바이트)으로 판별한다.

    from app.parsers import parse_attachment
    res = parse_attachment(data, "공고문.hwp")
    res.text, res.method, res.needs_ocr
"""
from dataclasses import dataclass

MAX_BYTES = 20 * 1024 * 1024  # 20MB 넘는 첨부는 건너뜀
SCANNED_CHARS_PER_PAGE = 40  # PDF 페이지당 글자가 이보다 적으면 스캔본으로 본다


@dataclass
class ParseResult:
    text: str
    method: str  # hwp5 | hwpx | docx | pdf | image | none
    needs_ocr: bool = False  # 스캔 PDF·이미지: 비전 모델(ChatKHU)로 읽어야 함
    note: str = ""  # 배포용 문서, 암호, 손상 등 실패 사유


def detect(data: bytes, filename: str) -> str:
    head = data[:8]
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "hwp5"  # OLE 복합 문서 (HWP 5.0)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK"):
        if filename.lower().endswith(".hwpx") or b"hwpml" in data[:4096].lower() or _zip_has(data, "Contents/"):
            return "hwpx"
        return "docx" if _zip_has(data, "word/document.xml") else "zip"
    if head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8")) or (head[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "image"
    return "unknown"


def _zip_has(data: bytes, prefix: str) -> bool:
    import io
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return any(n.startswith(prefix) for n in z.namelist())
    except zipfile.BadZipFile:
        return False


def clean(text: str) -> str:
    """빈 줄·공백 정리 (내용은 바꾸지 않음)"""
    lines = [" ".join(line.split()) for line in text.replace("\r", "\n").split("\n")]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def parse_attachment(data: bytes, filename: str) -> ParseResult:
    if len(data) > MAX_BYTES:
        return ParseResult("", "none", note=f"too large ({len(data)} bytes)")
    kind = detect(data, filename)
    try:
        if kind == "hwp5":
            from .hwp import extract_hwp5

            text, note = extract_hwp5(data)
            return ParseResult(clean(text), "hwp5", note=note)
        if kind == "hwpx":
            from .hwpx import extract_hwpx

            return ParseResult(clean(extract_hwpx(data)), "hwpx")
        if kind == "docx":
            from .docx import extract_docx

            return ParseResult(clean(extract_docx(data)), "docx")
        if kind == "pdf":
            from .pdf import extract_pdf

            text, pages = extract_pdf(data)
            text = clean(text)
            scanned = pages > 0 and len(text.replace("\n", "").replace(" ", "")) / pages < SCANNED_CHARS_PER_PAGE
            return ParseResult(text, "pdf", needs_ocr=scanned, note="scanned" if scanned else "")
        if kind == "image":
            return ParseResult("", "image", needs_ocr=True)
    except Exception as e:  # 파일 하나 실패가 크롤링 전체를 멈추지 않게
        return ParseResult("", kind, note=f"error: {type(e).__name__}: {e}")
    return ParseResult("", "none", note=f"unsupported ({kind})")


def extract_text(data: bytes, filename: str) -> str:
    """crawler/CLAUDE.md 약속 시그니처: 실패하면 빈 문자열"""
    return parse_attachment(data, filename).text
