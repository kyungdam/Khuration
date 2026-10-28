"""추출 정확도: 근거 대조, 값-근거 일치, 날짜 교차 확인, 상위 모델 재추출, 빈 양식 제외 (네트워크 없음)."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.config import settings
from app.crawler import extract_llm, verify as vf
from app.crawler.base import RawNotice
from app.llm import client
from app.matching.engine import evaluate
from app.parsers import parse_attachment
from app.seed_loader import content_hash

FIX = Path(__file__).parent / "fixtures"
BODY = """2026학년도 2학기 성적우수 장학생 선발 공고
1. 신청 기간: 2026. 11. 3.(월) ~ 11. 14.(금)
2. 지원 자격: 국제캠퍼스 재학생 중 직전학기 평점 3.5 이상, 3~4학년
소득분위 8분위 이하"""
RAW = RawNotice("테스트", "https://example.com/v/1", "성적우수 장학생 선발", BODY, posted_at=datetime(2026, 10, 28))
EMPTY = {"campuses": [], "colleges": [], "departments": [], "grades": [], "min_gpa": None, "gpa_basis": None,
         "min_credits": None, "income_max": None, "requires_lang_score": None, "open_to_all": None}


@pytest.fixture(autouse=True)
def _tmp_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(extract_llm, "CACHE_DIR", tmp_path / "cache")


def test_quote_must_exist_in_source():
    src = vf.norm(BODY)
    assert vf.quote_in_source("국제 캠퍼스 재학생 중", src)  # 띄어쓰기 달라도 인정
    assert not vf.quote_in_source("서울캠퍼스 재학생", src)
    assert not vf.quote_in_source("3.5", src)  # 너무 짧은 근거는 근거가 아님


def test_date_candidates_cover_common_formats():
    assert (11, 14) in vf.date_candidates("11. 3.(월) ~ 14.(금) 18:00까지")
    assert (11, 14) in vf.date_candidates("11월 3일(월)~14일(금)")
    assert (11, 9) in vf.date_candidates("10.26(월) - 11.9(월)")
    assert (11, 9) in vf.date_candidates("신청: 10/27~11/9")


def test_grade_ranges():
    assert vf._grades_ok("2학년 이상", [2, 3, 4])
    assert vf._grades_ok("3~4학년", [3, 4])
    assert not vf._grades_ok("3~4학년", [2, 3])
    assert vf._grades_ok("전 학년 재학생", [1, 2, 3, 4])
    assert vf._grades_ok("신입생 대상", [1]) and vf._grades_ok("졸업예정자", [4])
    assert not vf._grades_ok("학부 재학생", [1, 2, 3, 4])  # 학년 근거가 아님


def test_open_to_all_phrases():
    for q in ["재학생 누구나 참여 가능", "학과 무관 모든 재학생", "전공과 관계없이 신청 가능", "관심 있는 학생 누구든지"]:
        assert vf.VALUE_CHECKS["open_to_all"](q, True), q
    assert not vf.VALUE_CHECKS["open_to_all"]("3학년 이상 재학생", True)


def test_verify_keeps_grounded_and_drops_invented_values():
    crit = {**EMPTY, "campuses": ["global"], "grades": [3, 4], "min_gpa": 3.5, "gpa_basis": "last",
            "income_max": 8, "min_credits": 90, "departments": ["화학공학과"]}
    ev = {"campuses": "국제캠퍼스 재학생", "grades": "3~4학년", "min_gpa": "직전학기 평점 3.5 이상",
          "income_max": "소득분위 8분위 이하", "min_credits": "취득 학점 90학점 이상", "departments": "국제캠퍼스 재학생",
          "deadline": "2026. 11. 3.(월) ~ 11. 14.(금)"}
    out, dl, kept, rep = vf.verify(crit, "11-14", ev, BODY, RAW.posted_at)
    assert out["min_credits"] is None and rep.dropped["min_credits"] == "근거가 원문에 없음"
    assert out["departments"] == [] and rep.dropped["departments"] == "근거와 값 불일치"
    assert out["grades"] == [3, 4] and out["min_gpa"] == 3.5 and dl == "11-14"
    assert set(kept) == {"campuses", "grades", "min_gpa", "income_max", "deadline"}


def test_deadline_not_in_source_dates_is_dropped():
    _, dl, _, rep = vf.verify(dict(EMPTY), "11-20", {"deadline": "신청 기간: 2026. 11. 3.(월) ~ 11. 14.(금)"}, BODY, RAW.posted_at)
    assert dl is None and rep.dropped["deadline"] == "원문 날짜 후보에 없음"


def test_cascade_to_strong_model_only_when_uncertain(monkeypatch):
    monkeypatch.setattr(settings, "chatkhu_model_extract_strong", "strong-model")
    calls = []

    def fake(messages, model, **k):
        calls.append(model)
        if model != "strong-model":  # 기본 모델: 근거 없는 이수학점을 지어냄
            return json.dumps({"deadline": "11-14", "criteria": {"grades": [3, 4], "min_credits": 60},
                               "evidence": {"deadline": "~ 11. 14.(금)", "grades": "3~4학년", "min_credits": "60학점 이상"}})
        return json.dumps({"deadline": "11-14", "criteria": {"grades": [3, 4], "income_max": 8},
                           "evidence": {"deadline": "2026. 11. 3.(월) ~ 11. 14.(금)", "grades": "3~4학년",
                                        "income_max": "소득분위 8분위 이하"}})

    monkeypatch.setattr(client, "chat", fake)
    ex = extract_llm.extract_with_llm(RAW, BODY)
    assert calls == [settings.chatkhu_model_extract, "strong-model"] and ex.engine == "llm+strong"
    assert ex.criteria["min_credits"] is None and ex.criteria["grades"] == [3, 4] and ex.criteria["income_max"] == 8
    assert ex.deadline == datetime(2026, 11, 14, 14, 59)
    assert ex.criteria["_evidence"]["income_max"] == "소득분위 8분위 이하"


def test_no_cascade_when_everything_verified(monkeypatch):
    monkeypatch.setattr(settings, "chatkhu_model_extract_strong", "strong-model")
    calls = []

    def fake(messages, model, **k):
        calls.append(model)
        return json.dumps({"deadline": "11-14", "criteria": {"grades": [3, 4]},
                           "evidence": {"deadline": "~ 11. 14.(금)", "grades": "3~4학년"}})

    monkeypatch.setattr(client, "chat", fake)
    ex = extract_llm.extract_with_llm(RAW, BODY)
    assert len(calls) == 1 and ex.engine == "llm+verify" and ex.verification["dropped"] == {}


def test_evidence_reaches_reasons_and_is_ignored_by_change_hash():
    crit = {**EMPTY, "grades": [3, 4], "_evidence": {"grades": "3~4학년"}}
    _, reasons = evaluate(crit, {"grade": 3})
    assert reasons[0]["evidence"] == "3~4학년"
    other = {**crit, "_evidence": {"grades": "3, 4학년 대상"}}
    assert content_hash("t", None, crit) == content_hash("t", None, other)


@pytest.mark.parametrize("name", ["개인정보 수집이용 및 제공 동의서.docx", "삼유장학 신청양식.hwpx"])
def test_real_blank_forms_are_detected(name):
    p = FIX / name
    if not p.exists():
        pytest.skip("샘플 파일 없음")
    assert vf.looks_like_blank_form(parse_attachment(p.read_bytes(), name).text)


def test_notices_are_not_mistaken_for_forms():
    assert not vf.looks_like_blank_form(BODY + "\n붙임 1. 장학금 신청서\n성명\n학번\n연락처\n(인)")
    assert not vf.looks_like_blank_form("삼성청년 SW·AI 아카데미\nSSAFY\n17기 모집\n10.26(월) - 11.9(월)")
    src = vf.extraction_source("본문", {"a": "장학 신청서\n성명\n학번\n(인)", "b": "포스터 글자"})
    assert "포스터 글자" in src and "성명" not in src
