"""HWP 5.0(바이너리) 본문 텍스트 추출. 외부 의존성은 olefile 하나.
구조: OLE 안의 BodyText/SectionN 스트림(대개 raw deflate 압축) → 레코드 → PARA_TEXT(태그 67)의 UTF-16LE 문자.
표 안의 글자도 PARA_TEXT 레코드로 들어 있어서 함께 추출된다."""
import io
import re
import struct
import zlib

HWPTAG_PARA_TEXT = 0x10 + 51  # 67

# 1칸짜리 문자 컨트롤 (줄바꿈 등). 나머지 0~31은 8칸(16바이트)짜리 인라인/확장 컨트롤
CHAR_CONTROLS = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}


def para_text(payload: bytes) -> str:
    units = struct.unpack(f"<{len(payload) // 2}H", payload[: len(payload) // 2 * 2])
    out: list[int] = []
    i = 0
    while i < len(units):
        c = units[i]
        if c >= 32:
            out.append(c)
            i += 1
        elif c in CHAR_CONTROLS:
            if c in (10, 13):
                out.append(10)
            i += 1
        else:
            if c == 9:
                out.append(9)  # 탭
            i += 8  # 컨트롤 본체 + 부가정보 + 끝 표시
    return struct.pack(f"<{len(out)}H", *out).decode("utf-16-le", errors="ignore")


def records_to_text(stream: bytes) -> str:
    parts: list[str] = []
    pos, n = 0, len(stream)
    while pos + 4 <= n:
        (h,) = struct.unpack_from("<I", stream, pos)
        pos += 4
        tag, size = h & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF:
            if pos + 4 > n:
                break
            (size,) = struct.unpack_from("<I", stream, pos)
            pos += 4
        if tag == HWPTAG_PARA_TEXT:
            parts.append(para_text(stream[pos : pos + size]))
        pos += size
    return "\n".join(p.rstrip("\n") for p in parts)


def extract_hwp5(data: bytes) -> tuple[str, str]:
    """(텍스트, 비고). 배포용·암호 문서는 본문이 암호화돼 있어 빈 텍스트."""
    import olefile

    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        header = ole.openstream("FileHeader").read()
        (props,) = struct.unpack_from("<I", header, 36)
        compressed, encrypted, distribution = bool(props & 1), bool(props & 2), bool(props & 4)
        if encrypted:
            return "", "password protected"
        if distribution:
            return "", "distribution document (배포용 문서) — 본문 암호화됨"
        sections = sorted(
            ("/".join(p) for p in ole.listdir() if len(p) == 2 and p[0] == "BodyText" and re.fullmatch(r"Section\d+", p[1])),
            key=lambda s: int(s.split("Section")[1]),
        )
        texts = []
        for s in sections:
            raw = ole.openstream(s).read()
            if compressed:
                raw = zlib.decompress(raw, -15)
            texts.append(records_to_text(raw))
        return "\n".join(texts), ""
    finally:
        ole.close()
