"""HWPX(한글 2014+ XML 형식) 텍스트 추출. 표준 라이브러리만 사용.
Contents/sectionN.xml 의 <hp:t> 글자를 문단(<hp:p>) 단위로 모은다."""
import io
import re
import zipfile
import xml.etree.ElementTree as ET


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def section_text(xml_bytes: bytes) -> str:
    root = ET.fromstring(xml_bytes)
    parent = {c: p for p in root.iter() for c in p}
    lines: list[str] = []
    last_p = None
    for el in root.iter():
        if _local(el.tag) != "t":
            continue
        txt = "".join(el.itertext())
        if not txt:
            continue
        p = parent.get(el)
        while p is not None and _local(p.tag) != "p":
            p = parent.get(p)
        if p is last_p and lines:
            lines[-1] += txt
        else:
            lines.append(txt)
            last_p = p
    return "\n".join(lines)


def extract_hwpx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(
            (n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n, re.I)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)),
        )
        return "\n".join(section_text(z.read(n)) for n in names)
