"""조건 매칭. LLM이 아니라 코드가 판정한다. 일치 / 확인 필요 / 불일치 3상태.
캠퍼스 이름, 학과→단과대(앱이 college를 안 보낼 때 보조), 분류→관심 키는 taxonomy.json 한 곳에서 관리한다."""
from ..taxonomy import CAMPUS_LABEL, CATEGORY_KEY, COLLEGE_OF, STATUS_TEXT

MATCH, CHECK, MISMATCH = "match", "check", "mismatch"

# 판정 항목 → 조건(criteria) 키. 새 조건을 추가하면 여기에도 넣는다 (근거 표시용)
EVIDENCE_KEYS = {
    "campus": ("campuses",), "dept": ("departments", "colleges"), "grade": ("grades",),
    "gpa": ("min_gpa",), "credits": ("min_credits",), "income": ("income_max",),
    "lang": ("requires_lang_score",), "all": ("open_to_all",),
    "birth": ("birth_year_min", "birth_year_max", "max_age"),
    "intl_student": ("intl_student",), "nk_defector": ("nk_defector",),
}
# 기기에서 판정하는 민감 조건. 서버는 학생 값을 모르므로 '확인 필요(기기 판정)'로 두고,
# 공지 조건 값은 device_criteria로 앱에 내려준다 → web/index.html 이 기기에 저장된 값과 비교해 최종 판정
DEVICE_KEYS = ("birth_year_min", "birth_year_max", "max_age", "intl_student", "nk_defector")
DEVICE_NOTE = "내 기기에서 판정 (서버로 보내지 않는 정보)"


def device_criteria(criteria: dict | None) -> dict:
    c = criteria or {}
    return {k: c[k] for k in DEVICE_KEYS if c.get(k) is not None}


def _birth_requirement(c: dict) -> str | None:
    parts = []
    if c.get("birth_year_min") is not None:
        parts.append(f"{c['birth_year_min']}년 이후 출생")
    if c.get("birth_year_max") is not None:
        parts.append(f"{c['birth_year_max']}년 이전 출생")
    if c.get("max_age") is not None:
        parts.append(f"만 {c['max_age']}세 이하")
    return " · ".join(parts) or None


def _r(field: str, status: str, requirement: str, note: str) -> dict:
    return {"field": field, "status": status, "requirement": requirement, "note": note}


def _threshold(field, requirement, need, floor, width, label):
    """floor는 내림 구간의 하한. 실제 값은 [floor, floor+width) 안에 있다."""
    if floor is None:
        return _r(field, CHECK, requirement, f"내 {label} 정보 없음 — 확인 필요")
    if round(floor, 2) >= round(need, 2):
        return _r(field, MATCH, requirement, "충족")
    if round(floor + width, 2) <= round(need, 2):
        return _r(field, MISMATCH, requirement, "기준 미달")
    return _r(field, CHECK, requirement, "기준 경계 구간 — 확인 필요")


def evaluate(criteria: dict | None, tags: dict) -> tuple[str, list[dict]]:
    c = criteria or {}
    out: list[dict] = []

    campuses = c.get("campuses") or []
    if campuses:
        names = "·".join(CAMPUS_LABEL.get(x, x) for x in campuses)
        req = f"{names} 대상"
        v = tags.get("campus")
        if v is None:
            out.append(_r("campus", CHECK, req, "내 캠퍼스 정보 없음 — 확인 필요"))
        elif v in campuses:
            out.append(_r("campus", MATCH, req, "일치"))
        else:
            out.append(_r("campus", MISMATCH, req, f"내 캠퍼스는 {CAMPUS_LABEL.get(v, v)}"))

    depts = c.get("departments") or []
    colleges = c.get("colleges") or []
    if depts or colleges:
        req = "·".join(depts + colleges) + " 대상"
        dept = tags.get("dept")
        college = tags.get("college") or COLLEGE_OF.get(dept)
        if (dept and dept in depts) or (college and college in colleges):
            out.append(_r("dept", MATCH, req, "일치"))
        else:
            known = (not depts or dept) and (not colleges or college)
            if known:
                out.append(_r("dept", MISMATCH, req, "내 학과/단과대 해당 없음"))
            else:
                out.append(_r("dept", CHECK, req, "내 학과 정보로 판정 불가 — 확인 필요"))

    grades = c.get("grades") or []
    if grades:
        req = "·".join(f"{g}학년" for g in grades) + " 대상"
        g = tags.get("grade")
        if g is None:
            out.append(_r("grade", CHECK, req, "내 학년 정보 없음 — 확인 필요"))
        elif g in grades:
            out.append(_r("grade", MATCH, req, "일치"))
        else:
            out.append(_r("grade", MISMATCH, req, f"내 학년은 {g}학년"))

    if c.get("min_gpa") is not None:
        last = c.get("gpa_basis") == "last"
        label = "직전 학기 평점" if last else "평균 학점"
        out.append(
            _threshold(
                "gpa",
                f"{label} {c['min_gpa']} 이상",
                float(c["min_gpa"]),
                tags.get("last_gpa_floor" if last else "gpa_floor"),
                0.5,
                label,
            )
        )

    if c.get("min_credits") is not None:
        out.append(
            _threshold(
                "credits",
                f"취득 학점 {c['min_credits']} 이상",
                float(c["min_credits"]),
                tags.get("credits_floor"),
                10,
                "취득 학점",
            )
        )

    if c.get("income_max") is not None:
        req = f"소득분위 {c['income_max']}분위 이하"
        b = tags.get("income_band")
        if b is None:
            out.append(_r("income", CHECK, req, "내 소득분위 정보 없음 — 확인 필요"))
        elif b <= c["income_max"]:
            out.append(_r("income", MATCH, req, "충족"))
        else:
            out.append(_r("income", MISMATCH, req, "기준 초과"))

    if c.get("requires_lang_score"):
        req = "어학 성적 필요"
        h = tags.get("has_lang_score")
        if h is None:
            out.append(_r("lang", CHECK, req, "어학 성적 보유 여부 확인 필요"))
        elif h:
            out.append(_r("lang", MATCH, req, "보유"))
        else:
            out.append(_r("lang", MISMATCH, req, "미보유"))

    # 민감 조건: 학생 값이 서버에 없으므로 항상 '확인 필요'. 앱이 기기에 있는 값으로 바꿔 판정한다
    birth = _birth_requirement(c)
    if birth:
        out.append(_r("birth", CHECK, birth, DEVICE_NOTE))
    for key in ("intl_student", "nk_defector"):
        if c.get(key) in ("only", "excluded"):
            out.append(_r(key, CHECK, STATUS_TEXT[key][c[key]], DEVICE_NOTE))

    if not out:
        if c.get("open_to_all") is True:  # 공지에 "누구나/제한 없음"이 명시된 경우만
            out.append(_r("all", MATCH, "별도 지원 조건 없음", "공지에 제한 없음 명시"))
        else:  # 조건을 못 찾은 것과 조건이 없는 것은 다르다 → 모르면 확인 필요
            out.append(_r("all", CHECK, "지원 자격", "공지에서 조건을 찾지 못함 — 원문 확인"))

    # 판정 이유마다 공지 원문 근거(추출 단계에서 원문과 대조해 확인된 구절)를 붙인다
    ev = c.get("_evidence") or {}
    for r in out:
        r["evidence"] = next((ev[k] for k in EVIDENCE_KEYS.get(r["field"], ()) if ev.get(k)), None)

    statuses = {x["status"] for x in out}
    overall = MISMATCH if MISMATCH in statuses else CHECK if CHECK in statuses else MATCH
    return overall, out


def topic_keys(topics: list | None, category: str | None = None) -> set[str]:
    t = set(topics or [])
    if category in CATEGORY_KEY:
        t.add(CATEGORY_KEY[category])
    return t


def interest_score(topics: list | None, tags: dict, category: str | None = None) -> int:
    t = topic_keys(topics, category)
    return len(t & set(tags.get("interests", []))) + 2 * len(t & set(tags.get("intent_keywords", [])))
