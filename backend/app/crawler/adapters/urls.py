"""공지 URL 정규화. ListItem.url은 공지의 고유 키라서, 같은 공지는 늘 같은 문자열이 돼야 한다.
- 세션·추적·목록 상태 파라미터(ssoReChk, jsessionid, utm_*, 페이지 번호, 검색 조건 등)와 빈 값은 뺀다
- 남은 파라미터 순서는 그대로 둔다 (정렬하면 이미 저장된 공지 URL이 모두 바뀌어 한 번씩 중복 저장된다)
- #조각은 버리고, 호스트는 소문자로
- 공지를 가리키는 값(boardId, menuNo, encSddpbSeq 등)은 그대로 둔다"""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DROP = {
    "ssorechk", "paramstart", "jsessionid", "phpsessid", "sid",
    "pageindex", "pageunit", "page", "listuserdisplaycount", "userdisplaycount",
    "searchcategory", "searchcondition", "searchkeyword", "searchword", "searchvalue",
    "fbclid", "gclid",
}
DROP_PREFIX = ("utm_", "paginationinfo.")


def normalize_url(url: str) -> str:
    s = urlsplit(url.strip())
    path = re.sub(r";jsessionid=[^/?#]*", "", s.path, flags=re.I)
    params = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True)
              if v != "" and k.lower() not in DROP and not k.lower().startswith(DROP_PREFIX)]
    return urlunsplit((s.scheme.lower(), s.netloc.lower(), path, urlencode(params), ""))
