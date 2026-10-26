"""Word(.docx) 텍스트 추출. 표준 라이브러리만 사용.
word/document.xml 의 <w:t>를 문단(<w:p>) 단위로 모은다 (HWPX와 같은 방식)."""
import io
import zipfile

from .hwpx import section_text


def extract_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return section_text(z.read("word/document.xml"))
