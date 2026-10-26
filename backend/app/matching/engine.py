"""조건 매칭. LLM이 아니라 코드가 판정한다. 일치 / 확인 필요 / 불일치 3상태."""
MATCH, CHECK, MISMATCH = "match", "check", "mismatch"

CAMPUS_LABEL = {"seoul": "서울캠퍼스", "global": "국제캠퍼스"}

# 앱이 college를 보내지 않을 때를 대비한 보조 매핑 (필요하면 추가)
COLLEGE_OF = {
    "화학공학과": "공과대학",
    "기계공학과": "공과대학",
    "전자공학과": "전자정보대학",
    "컴퓨터공학과": "전자정보대학",
    "산업경영공학과": "공과대학",
    "건축공학과": "공과대학",
}


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

    if not out:
        if c.get("open_to_all") is True:  # 공지에 "누구나/제한 없음"이 명시된 경우만
            out.append(_r("all", MATCH, "별도 지원 조건 없음", "공지에 제한 없음 명시"))
        else:  # 조건을 못 찾은 것과 조건이 없는 것은 다르다 → 모르면 확인 필요
            out.append(_r("all", CHECK, "지원 자격", "공지에서 조건을 찾지 못함 — 원문 확인"))

    statuses = {x["status"] for x in out}
    overall = MISMATCH if MISMATCH in statuses else CHECK if CHECK in statuses else MATCH
    return overall, out


CATEGORY_KEY = {
    "장학": "scholarship",
    "현장실습": "internship",
    "국제교류": "language_abroad",
    "공모전": "contest",
    "학사": "academic",
}


def topic_keys(topics: list | None, category: str | None = None) -> set[str]:
    t = set(topics or [])
    if category in CATEGORY_KEY:
        t.add(CATEGORY_KEY[category])
    return t


def interest_score(topics: list | None, tags: dict, category: str | None = None) -> int:
    t = topic_keys(topics, category)
    return len(t & set(tags.get("interests", []))) + 2 * len(t & set(tags.get("intent_keywords", [])))
