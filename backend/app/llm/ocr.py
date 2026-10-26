"""이미지·스캔 PDF → 글자 (ChatKHU 비전 모델).

결과는 sha256 으로 디스크에 캐시한다. 같은 포스터를 하루 2번 크롤링해도 모델은 한 번만 부른다.
키가 없거나 호출이 실패하면 빈 문자열을 돌려주고, 호출하는 쪽은 그냥 건너뛴다."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import settings
from . import client

CACHE_DIR = Path(__file__).resolve().parents[2] / ".ocr_cache"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 6

PROMPT = (
    "이 이미지는 대학 공지 포스터/공고문입니다. 이미지에 보이는 글자를 빠짐없이 읽어서 "
    "위에서 아래, 왼쪽에서 오른쪽 순서로 그대로 옮겨 적으세요. "
    "날짜·숫자·기수·금액·자격 조건은 특히 정확히 옮기세요. "
    "보이지 않거나 흐릿해서 확실하지 않은 글자는 추측하지 말고 [불명]이라고 쓰세요. "
    "설명이나 인사 없이 옮긴 글자만 출력하세요."
)


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _cache_path(data: bytes) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(data).hexdigest()}.txt"


def ocr_image(data: bytes) -> str:
    if not client.available() or len(data) > MAX_IMAGE_BYTES:
        return ""
    cp = _cache_path(data)
    if cp.exists():
        return cp.read_text(encoding="utf-8")
    try:
        text = client.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        client.image_part(data, sniff_mime(data)),
                    ],
                }
            ],
            settings.chatkhu_model_vision,
            max_tokens=6000,  # 생각(thinking)에 쓰는 토큰이 있어 넉넉히
            timeout=120,
        ).strip()
    except client.LLMError as e:
        print(f"    OCR 실패: {e}")
        return ""
    if text:
        CACHE_DIR.mkdir(exist_ok=True)
        cp.write_text(text, encoding="utf-8")
    return text


def ocr_pdf(data: bytes, max_pages: int = MAX_PDF_PAGES) -> str:
    """스캔 PDF: 앞쪽 페이지를 그림으로 바꿔 한 장씩 읽는다."""
    if not client.available():
        return ""
    import pymupdf

    parts: list[str] = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        if doc.needs_pass:
            return ""
        for page in list(doc)[:max_pages]:
            png = page.get_pixmap(dpi=130).tobytes("png")
            t = ocr_image(png)
            if t:
                parts.append(t)
    return "\n\n".join(parts)
