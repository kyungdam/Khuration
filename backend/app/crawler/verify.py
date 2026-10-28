"""AI 추출 결과 검증 (정확도 개선). LLM 없이 코드만으로 돈다.

이론 (팀 확인 2026-10-28)
1. 근거 기반 추출(Grounding/Attribution): AI가 값마다 공지 속 근거 문장(evidence)을 함께 내고,
   코드가 그 문장이 원문에 실제로 있는지 대조한다. 없으면 그 값은 버린다 → 지어낸 조건 차단.
2. 값-근거 일치: 근거 문장 안에 그 값(숫자·학년·캠퍼스·학과명)이 실제로 들어 있어야 한다.
3. 제약 조건 검사(Constraint validation): 마감일은 게시일 전후 범위 안, 학점·학년 범위 등.
4. 규칙-AI 교차 확인(Agreement): 정규식으로 원문의 날짜 후보를 뽑아, AI 마감일이 후보에 있어야 한다.
5. 기권(Selective prediction): 확인 못 한 값은 null → 앱에서 '확인 필요'. 정밀도를 우선한다.
6. 입력 정제: 신청서·동의서 같은 빈 양식 첨부는 추출 입력에서 뺀다(looks_like_blank_form).

새 조건을 추가할 때 (팀원 참고)
- extract_llm.SYSTEM 스키마의 criteria와 evidence에 같은 키를 넣고,
- 아래 VALUE_CHECKS에 "근거 문장 안에 그 값이 있는지" 확인 함수를 하나 추가하면 된다.
- 민감한 조건(생년·새터민·유학생 등)은 서버 판정 대신 기기 판정을 권장 (루트 CLAUDE.md).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher

MIN_QUOTE = 4  # 정규화 후 이보다 짧은 근거는 근거로 인정하지 않는다
FUZZY_OK = 0.85  # OCR 띄어쓰기·기호 차이 허용: 근거의 85% 이상이 원문에 연속으로 있으면 인정


# ---------- 원문 대조 ----------
def norm(s: str) -> str:
    """대조용 정규화: 전각→반각, 소문자, 글자·숫자·한글만 남김(공백·기호 제거)"""
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[^0-9a-z가-힣]", "", s)


def quote_in_source(quote: str, source_norm: str) -> bool:
    q = norm(quote)
    if len(q) < MIN_QUOTE or not source_norm:
        return False
    if q in source_norm:
        return True
    m = SequenceMatcher(None, q, source_norm, autojunk=False).find_longest_match(0, len(q), 0, len(source_norm))
    return m.size / len(q) >= FUZZY_OK


# ---------- 날짜 후보 (규칙) ----------
_DATE_PATTERNS = [
    r"(?:(\d{4})\s*[.\-/년]\s*)?(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?",
]


# '11. 3.(월) ~ 14.(금)', '11월 3일(월)~14일' 처럼 끝 날짜에 월이 생략된 기간
_RANGE_TAIL = r"(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?\.?\s*(?:\([^)]{0,6}\))?\s*[~∼～\-–]\s*(\d{1,2})\s*(?:일|\.|\(|$|\s)"


def date_candidates(text: str) -> set[tuple[int, int]]:
    """원문에서 (월, 일) 후보를 모두 뽑는다. '10.26(월) - 11.9(월)', '11월 9일', '2026-11-09', '11.3.~14.' 등."""
    out: set[tuple[int, int]] = set()
    t = unicodedata.normalize("NFKC", text or "")
    for pat in _DATE_PATTERNS:
        for m in re.finditer(pat, t):
            mo, d = int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= d <= 31:
                out.add((mo, d))
    for m in re.finditer(_RANGE_TAIL, t):
        mo, d2 = int(m.group(1)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d2 <= 31 and d2 >= int(m.group(2)):
            out.add((mo, d2))
    return out


def month_day(value: str | None) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    nums = [int(n) for n in re.findall(r"\d+", value)]
    if len(nums) >= 3 and nums[0] > 31:
        nums = nums[1:]
    if len(nums) >= 2 and 1 <= nums[0] <= 12 and 1 <= nums[1] <= 31:
        return nums[0], nums[1]
    return None


# ---------- 값-근거 일치 ----------
def _numbers(q: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", unicodedata.normalize("NFKC", q))]


def _has_num(q: str, v) -> bool:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return any(abs(n - v) < 1e-6 for n in _numbers(q))


_ALL_GRADES = ("전학년", "학년무관", "학년제한없", "학년관계없", "학년상관없", "모든학년")


def _grades_ok(q: str, grades: list[int]) -> bool:
    nq = norm(q)
    if any(w in nq for w in _ALL_GRADES):
        return True  # '전 학년' → 어떤 학년 목록이든 근거로 인정
    if set(grades) == {1} and "신입생" in nq:
        return True
    if "졸업예정" in nq and set(grades) <= {4, 5, 6}:
        return True
    nums = {int(n) for n in re.findall(r"([1-6])\s*(?:학년|~|-|,|·|/|\s*이상|\s*이하)", unicodedata.normalize("NFKC", q))}
    nums |= {int(n) for n in re.findall(r"[1-6]", re.sub(r"\d{2,}", "", q))} if "학년" in q else set()
    if not nums:
        return False
    lo, hi = min(nums), max(nums)
    allowed = set(nums)
    if "이상" in q:
        allowed |= set(range(lo, 7))
    if "이하" in q:
        allowed |= set(range(1, hi + 1))
    if re.search(r"[1-6]\s*[~\-]\s*[1-6]|부터", q):
        allowed |= set(range(lo, hi + 1))
    return set(grades) <= allowed


def _names_ok(q: str, names: list[str]) -> bool:
    nq = norm(q)
    for n in names:
        core = norm(re.sub(r"(학과|학부|대학|전공|과)$", "", n)) or norm(n)
        if core not in nq:
            return False
    return True


_LANG_WORDS = ("어학", "토익", "toeic", "토플", "toefl", "ielts", "hsk", "jlpt", "opic", "teps", "공인영어", "외국어성적")
_OPEN_WORDS = ("누구나", "누구든", "제한없", "관계없이", "상관없이", "무관", "전체학생", "전학생", "모든학생", "모든재학생",
               "전체재학생", "재학생전체", "전학년", "전학과", "전공무관", "학과무관", "학년무관", "희망자", "관심있는")

_BIRTH_WORDS = ("출생", "년생", "생년", "태어")
_AGE_WORDS = ("세", "나이", "연령")
_INTL_WORDS = ("유학생", "외국인")
_NK_WORDS = ("북한이탈", "새터민", "탈북")
_EXCLUDE_WORDS = ("제외", "불가", "제한", "내국인", "한국국적", "대한민국국적", "지원할수없")
_ONLY_WORDS = ("대상", "만지원", "만신청", "만해당", "에한함", "에한해", "한정", "전용")  # '우대'·'가점'은 자격 한정이 아니다


def _has_year(q: str, v) -> bool:
    """'2001.1.1.' 처럼 날짜에 붙은 연도도 찾는다 (_has_num은 '2001.1'을 소수로 읽는다)"""
    return isinstance(v, int) and str(v) in re.findall(r"(?<!\d)\d{4}(?!\d)", unicodedata.normalize("NFKC", q))


def _target_ok(q: str, v, topic_words) -> bool:
    """'only'면 근거에 대상 단어 + 한정 표현이, 'excluded'면 대상 단어 + 제외 표현이 있어야 한다"""
    nq = norm(q)
    if not any(w in nq for w in topic_words) and not (v == "excluded" and "내국인" in nq):
        return False
    if v == "only":
        return any(w in nq for w in _ONLY_WORDS)
    return v == "excluded" and any(w in nq for w in _EXCLUDE_WORDS)


VALUE_CHECKS = {
    "campuses": lambda q, v: all(("서울" in q) if c == "seoul" else ("국제" in q or "글로벌" in q) for c in v),
    "colleges": lambda q, v: _names_ok(q, v),
    "departments": lambda q, v: _names_ok(q, v),
    "grades": lambda q, v: _grades_ok(q, v),
    "min_gpa": lambda q, v: _has_num(q, v),
    "min_credits": lambda q, v: _has_num(q, v),
    "income_max": lambda q, v: _has_num(q, v) and "분위" in q,
    "requires_lang_score": lambda q, v: v is True and any(w in norm(q) for w in _LANG_WORDS),
    "open_to_all": lambda q, v: v is True and any(w in norm(q) for w in _OPEN_WORDS),
    # 민감 조건 (값은 서버에 두고 판정은 기기에서)
    "birth_year_min": lambda q, v: _has_year(q, v) and any(w in q for w in _BIRTH_WORDS),
    "birth_year_max": lambda q, v: _has_year(q, v) and any(w in q for w in _BIRTH_WORDS),
    "max_age": lambda q, v: (_has_num(q, v) or ("미만" in q and _has_num(q, v + 1))) and any(w in q for w in _AGE_WORDS),
    "intl_student": lambda q, v: _target_ok(q, v, _INTL_WORDS),
    "nk_defector": lambda q, v: _target_ok(q, v, _NK_WORDS),
}
EMPTY_VALUE = {"campuses": [], "colleges": [], "departments": [], "grades": []}  # 나머지는 None


def _is_empty(v) -> bool:
    return v is None or v == [] or v == ""


@dataclass
class Report:
    kept: list[str] = field(default_factory=list)
    dropped: dict[str, str] = field(default_factory=dict)  # 키 → 버린 이유
    quotes: dict[str, str] = field(default_factory=dict)  # 버린 항목의 AI 근거 문장 (원인 확인용 로그)

    @property
    def uncertain(self) -> bool:
        """AI가 값을 냈는데 확인 못 한 항목이 있으면 True → 상위 모델 재추출 대상"""
        return bool(self.dropped)


def verify(criteria: dict, deadline: str | None, evidence: dict | None, source: str,
           posted: datetime | None) -> tuple[dict, str | None, dict, Report]:
    """조건·마감일을 근거와 대조한다. 반환: (확인된 조건, 확인된 마감일 문자열, 남긴 근거, 보고)"""
    ev = evidence if isinstance(evidence, dict) else {}
    src = norm(source)
    rep = Report()
    out = dict(criteria)
    kept_ev: dict[str, str] = {}

    for key, check in VALUE_CHECKS.items():
        v = out.get(key)
        if _is_empty(v):
            continue
        q = ev.get(key) if isinstance(ev.get(key), str) else ""
        if not q:
            reason = "근거 없음"
        elif not quote_in_source(q, src):
            reason = "근거가 원문에 없음"
        elif not check(q, v):
            reason = "근거와 값 불일치"
        else:
            rep.kept.append(key)
            kept_ev[key] = q.strip()[:160]
            continue
        rep.dropped[key] = reason
        rep.quotes[key] = f"{v} ← “{q[:50]}”" if q else str(v)
        out[key] = EMPTY_VALUE.get(key)
    if out.get("min_gpa") is None:
        out["gpa_basis"] = None

    dl = deadline if isinstance(deadline, str) and deadline.strip() else None
    if dl:
        md = month_day(dl)
        q = ev.get("deadline") if isinstance(ev.get("deadline"), str) else ""
        reason = None
        if md is None:
            reason = "날짜 형식 오류"
        elif md not in date_candidates(source):
            reason = "원문 날짜 후보에 없음"
        elif not q or not quote_in_source(q, src):
            reason = "근거가 원문에 없음"
        elif md not in date_candidates(q):
            reason = "근거와 날짜 불일치"
        elif not _deadline_in_range(dl, posted):
            reason = "게시일 기준 범위 밖"
        if reason:
            rep.dropped["deadline"] = reason
            rep.quotes["deadline"] = f"{dl} ← “{q[:50]}”" if q else dl
            dl = None
        else:
            rep.kept.append("deadline")
            kept_ev["deadline"] = q.strip()[:160]
    return out, dl, kept_ev, rep


def _deadline_in_range(dl: str, posted: datetime | None) -> bool:
    from .extract_llm import resolve_deadline

    d = resolve_deadline(dl, posted)
    if d is None:
        return False
    base = posted or datetime.now()
    return base - timedelta(days=2) <= d <= base + timedelta(days=400)


# ---------- 입력 정제: 빈 양식 ----------
_FORM_TITLES = ("신청서", "동의서", "서약서", "확인서", "추천서", "지원서", "계획서", "신청양식", "서식", "양식")
_NOTICE_WORDS = ("공고", "모집", "선발", "안내", "신청기간", "접수기간", "지원자격", "마감")
_FORM_MARKS = ("☐", "□", "(인)", "서명", "성명", "학번", "연락처", "생년월일", "주소", "동의함", "동의하지", "년월일")


def looks_like_blank_form(text: str) -> bool:
    """신청서·동의서처럼 칸 이름만 있는 양식인지. 앞부분 제목이 양식이고 양식 표시가 2개 이상이면 양식.
    앞부분에 공고·모집·안내 같은 말이 있으면(공고문 + 붙임 양식) 양식으로 보지 않는다."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return False
    head = norm(" ".join(lines[:3]))
    head5 = norm(" ".join(lines[:5]))
    if not any(w in head for w in _FORM_TITLES):
        return False
    if any(w in head5 for w in _NOTICE_WORDS) and not any(w in head for w in ("동의서", "신청서")):
        return False
    marks = sum(1 for m in _FORM_MARKS if m in text or norm(m) in norm(text))
    return marks >= 2


def extraction_source(body: str, attachment_texts: dict[str, str] | list[str]) -> str:
    """추출 입력 = 본문 + (빈 양식이 아닌) 첨부·포스터 글자"""
    texts = attachment_texts.values() if isinstance(attachment_texts, dict) else attachment_texts
    return "\n".join([body or "", *(t for t in texts if t and not looks_like_blank_form(t))])
