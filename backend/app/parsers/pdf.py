"""PDF 텍스트 추출 (PyMuPDF). 반환: (텍스트, 페이지 수). 스캔본 판정은 __init__.parse_attachment에서."""


def extract_pdf(data: bytes) -> tuple[str, int]:
    import pymupdf

    with pymupdf.open(stream=data, filetype="pdf") as doc:
        if doc.needs_pass:
            return "", doc.page_count
        return "\n".join(page.get_text("text") for page in doc), doc.page_count
