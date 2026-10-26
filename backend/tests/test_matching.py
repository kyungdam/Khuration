from app.matching.engine import CHECK, MATCH, MISMATCH, evaluate

T = {"campus": "global", "dept": "화학공학과", "grade": 3, "gpa_floor": 3.5,
     "last_gpa_floor": 4.0, "credits_floor": 70, "income_band": 5, "interests": []}


def st(c, tags=T):
    return evaluate(c, tags)[0]


def test_no_criteria_is_check_unless_open_to_all():
    assert st({}) == CHECK  # 조건을 못 찾은 공지는 '확인 필요'
    assert st(None) == CHECK
    assert st({"open_to_all": True}) == MATCH  # 공지에 제한 없음이 명시된 경우만 일치
    assert st({"open_to_all": True, "campuses": ["seoul"]}) == MISMATCH  # 다른 조건이 있으면 그 조건으로


def test_gpa():
    assert st({"min_gpa": 3.5}) == MATCH
    assert st({"min_gpa": 3.7}) == CHECK  # 3.5~4.0 구간 안에서 갈림
    assert st({"min_gpa": 4.0}) == MISMATCH
    assert st({"min_gpa": 4.0, "gpa_basis": "last"}) == MATCH


def test_credits():
    assert st({"min_credits": 60}) == MATCH
    assert st({"min_credits": 90}) == MISMATCH
    assert st({"min_credits": 75}) == CHECK


def test_income():
    assert st({"income_max": 8}) == MATCH
    assert st({"income_max": 3}) == MISMATCH
    assert st({"income_max": 3}, {}) == CHECK


def test_dept_and_college():
    assert st({"departments": ["화학공학과"]}) == MATCH
    assert st({"colleges": ["공과대학"]}) == MATCH  # 학과→단과대 보조 매핑
    assert st({"departments": ["기계공학과"]}) == MISMATCH
    assert st({"departments": ["기계공학과"]}, {}) == CHECK


def test_campus_grade():
    assert st({"campuses": ["seoul"]}) == MISMATCH
    assert st({"grades": [3, 4]}) == MATCH
    assert st({"grades": [1, 2]}) == MISMATCH


def test_lang_unknown_is_check():
    assert st({"requires_lang_score": True}) == CHECK


def test_mismatch_beats_check():
    assert st({"campuses": ["seoul"], "requires_lang_score": True}) == MISMATCH
