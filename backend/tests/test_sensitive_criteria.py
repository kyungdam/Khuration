"""민감 조건(생년·유학생·새터민): 추출 정제 → 근거 검증 → 서버는 '기기 판정'으로 두고 공지 조건만 내려준다.
학생 값(출생 연도·유학생·새터민 여부)은 서버가 받지 않는다."""
from fastapi.testclient import TestClient

from app.config import settings
from app.crawler import verify as vf
from app.crawler.base import RawNotice
from app.crawler.eval_extract import parse_cell, pred_value, to_cells
from app.crawler.extract import EMPTY_CRITERIA, Extracted
from app.crawler.extract_llm import sanitize_criteria
from app.crawler.store import upsert_notice
from app.db import SessionLocal
from app.main import app
from app.matching.engine import CHECK, DEVICE_KEYS, DEVICE_NOTE, device_criteria, evaluate

SRC = ("2027년 해외 인턴십 장학생 모집 지원 자격: 2001.1.1. 이후 출생자, 만 29세 이하인 자. "
       "외국인 유학생은 지원할 수 없음(대한민국 국적자만). 북한이탈주민(새터민) 가점 부여")


def test_sanitize_new_keys():
    c = sanitize_criteria({"birth_year_min": 2001, "birth_year_max": 2030, "max_age": 29.0,
                           "intl_student": "excluded", "nk_defector": "preferred"})
    assert c["birth_year_min"] == 2001
    assert c["birth_year_max"] is None  # 범위 밖
    assert c["max_age"] == 29
    assert c["intl_student"] == "excluded"
    assert c["nk_defector"] is None  # 'only'·'excluded'만 허용 (우대는 자격 아님)
    assert all(k in EMPTY_CRITERIA for k in DEVICE_KEYS)
    assert sanitize_criteria({"birth_year_min": True, "max_age": 29.5})["birth_year_min"] is None


def test_verify_keeps_grounded_values_and_drops_bad_ones():
    crit = sanitize_criteria({"birth_year_min": 2001, "max_age": 29, "intl_student": "excluded", "nk_defector": "only"})
    ev = {"birth_year_min": "2001.1.1. 이후 출생자", "max_age": "만 29세 이하인 자",
          "intl_student": "외국인 유학생은 지원할 수 없음(대한민국 국적자만)",
          "nk_defector": "북한이탈주민(새터민) 가점 부여"}
    out, _, kept, rep = vf.verify(crit, None, ev, SRC, None)
    assert out["birth_year_min"] == 2001 and out["max_age"] == 29 and out["intl_student"] == "excluded"
    assert {"birth_year_min", "max_age", "intl_student"} <= set(kept)
    # 'only'인데 근거는 '가점 부여'라 지원 대상 한정이 아니다 → 기권(확인 필요)
    assert out["nk_defector"] is None and rep.dropped["nk_defector"] == "근거와 값 불일치"


def test_value_checks_rules():
    chk = vf.VALUE_CHECKS
    assert chk["birth_year_min"]("2001년 이후 출생자", 2001)
    assert chk["birth_year_min"]("2001.1.1. 이후 출생자", 2001)
    assert not chk["birth_year_min"]("12001 출생", 2001)
    assert not chk["birth_year_min"]("2001년 이후 졸업자", 2001)  # 출생 언급이 없으면 출생 연도 조건이 아니다
    assert chk["max_age"]("만 30세 미만", 29)  # 30세 미만 = 29세 이하
    assert not chk["max_age"]("2029년까지", 29)
    assert chk["intl_student"]("외국인 유학생만 지원 가능", "only")
    assert not chk["intl_student"]("외국인 유학생만 지원 가능", "excluded")
    assert chk["intl_student"]("내국인만 지원 가능", "excluded")
    assert chk["nk_defector"]("북한이탈주민 대상 장학금", "only")
    assert not chk["nk_defector"]("저소득층 대상 장학금", "only")
    assert not chk["nk_defector"]("북한이탈주민 우대", "only")  # 우대는 자격 한정이 아니다


def test_engine_leaves_sensitive_conditions_to_device():
    c = {**EMPTY_CRITERIA, "birth_year_min": 2001, "max_age": 29, "intl_student": "only",
         "_evidence": {"birth_year_min": "2001년 이후 출생자", "intl_student": "외국인 유학생 대상"}}
    status, reasons = evaluate(c, {"campus": "global", "grade": 3})
    by = {r["field"]: r for r in reasons}
    assert status == CHECK
    assert by["birth"]["requirement"] == "2001년 이후 출생 · 만 29세 이하" and by["birth"]["note"] == DEVICE_NOTE
    assert by["birth"]["evidence"] == "2001년 이후 출생자"
    assert by["intl_student"]["requirement"] == "외국인 유학생 대상" and by["intl_student"]["status"] == CHECK
    assert "all" not in by  # 조건이 있으니 '조건을 찾지 못함'이 아니다
    assert device_criteria(c) == {"birth_year_min": 2001, "max_age": 29, "intl_student": "only"}
    assert device_criteria({**EMPTY_CRITERIA, "min_gpa": 3.0}) == {}


def test_api_sends_conditions_but_never_accepts_student_values(monkeypatch):
    monkeypatch.setattr(settings, "app_mode", "live")
    raw = RawNotice(source_name="테스트", url="https://example.org/crawled/sensitive-1", title="유학생 전용 장학금", body_text="본문")
    ex = Extracted(category="장학", topics=["scholarship"], deadline=None,
                   criteria={**EMPTY_CRITERIA, "intl_student": "only"}, summary="요약")
    tok = {"X-Device-Token": "web-sensitive-test"}
    with TestClient(app) as c:  # 앱이 켜지며 표를 만든 뒤에 공지를 넣는다
        with SessionLocal() as db:
            nid = upsert_notice(db, raw, ex)[0].id
        # 서버는 출생 연도·유학생·새터민 같은 학생 값을 태그로 받지 않는다 (extra=forbid)
        for bad in ({"birth_year": 2001}, {"intl_student": True}, {"nk_defector": False}):
            r = c.post("/devices", json={"push_token": "web-sensitive-test", "tags": {"campus": "global", **bad}})
            assert r.status_code == 422
        assert c.post("/devices", json={"push_token": "web-sensitive-test", "tags": {"campus": "global"}}).status_code == 200
        item = next(i for i in c.get("/notices", headers=tok).json() if i["id"] == nid)
        assert item["device_criteria"] == {"intl_student": "only"}
        assert item["status"] == "check"
        assert any(r["field"] == "intl_student" and r["note"] == DEVICE_NOTE for r in item["reasons"])
        meta = c.get("/meta").json()
        assert {s["key"] for s in meta["sensitive"]["statuses"]} == {"intl_student", "nk_defector"}
        assert meta["sensitive"]["birth_years"]["min"] < meta["sensitive"]["birth_years"]["max"]


def test_eval_cells_round_trip():
    crit = {"birth_year_min": 2001, "birth_year_max": None, "max_age": 29, "intl_student": "excluded", "nk_defector": "only"}
    cells = to_cells(None, crit)
    assert cells["정답_출생연도이후"] == "2001" and cells["정답_유학생"] == "제외" and cells["정답_새터민"] == "대상"
    ex = Extracted(category="장학", topics=[], deadline=None, criteria=crit, summary="")
    for col, key in (("정답_출생연도이후", "birth_year_min"), ("정답_나이상한", "max_age"),
                     ("정답_유학생", "intl_student"), ("정답_새터민", "nk_defector")):
        assert parse_cell(key, cells[col]) == pred_value(key, ex)
    assert parse_cell("birth_year_max", cells["정답_출생연도이전"]) is None
