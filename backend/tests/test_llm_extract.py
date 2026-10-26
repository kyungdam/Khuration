"""ChatKHU 호출은 가짜로 바꿔서, 응답 정리·폴백 로직만 검사한다 (네트워크 불필요)."""
from datetime import datetime

from app.crawler import extract as extract_mod
from app.crawler.base import RawNotice
from app.crawler.extract_llm import extract_with_llm, sanitize_criteria, to_extracted
from app.llm import client

RAW = RawNotice(source_name="테스트", url="https://example.com/n/1", title="[SSAFY] 17기 모집", body_text="본문",
                posted_at=datetime(2026, 10, 26))


def test_sanitize_drops_bad_values():
    c = sanitize_criteria({
        "campuses": ["seoul", "mars"], "grades": [3, 4, 99, "x"], "min_gpa": 3.0,
        "income_max": 8.0, "requires_lang_score": "yes", "departments": ["화학공학과", 5],
    })
    assert c["campuses"] == ["seoul"]
    assert c["grades"] == [3, 4]
    assert c["min_gpa"] == 3.0 and c["gpa_basis"] == "overall"  # 기준 없으면 전체 평점으로
    assert c["income_max"] == 8
    assert c["requires_lang_score"] is None
    assert c["departments"] == ["화학공학과"]


def test_sanitize_non_dict_gives_empty():
    assert sanitize_criteria(None)["min_gpa"] is None


def test_deadline_is_kst_end_of_day_in_utc():
    ex = to_extracted({"deadline": "2026-11-09", "category": "공모전"}, RAW)
    assert ex.deadline == datetime(2026, 11, 9, 14, 59)  # KST 23:59 = UTC 14:59
    assert ex.category == "공모전" and ex.engine == "llm"


def test_bad_fields_fall_back():
    ex = to_extracted({"deadline": "내일", "category": "이상한것", "topics": ["ai_data", "xx"], "apply_url": "javascript:x"}, RAW)
    assert ex.deadline is None and ex.category == "학사"
    assert ex.topics == ["ai_data"]
    assert ex.apply_url == RAW.url


def test_extract_with_llm_parses_fenced_json(monkeypatch):
    monkeypatch.setattr(client, "chat", lambda *a, **k: '```json\n{"deadline":"2026-11-09","summary":"요약","summary_points":["a"]}\n```')
    ex = extract_with_llm(RAW, "본문")
    assert ex.summary == "요약" and ex.summary_points == ["a"]


def test_extract_falls_back_when_llm_fails(monkeypatch):
    monkeypatch.setattr(client, "available", lambda: True)

    def boom(*a, **k):
        raise client.LLMError("HTTP 500")

    monkeypatch.setattr(client, "chat", boom)
    ex = extract_mod.extract(RAW, "해커톤 안내")
    assert ex.engine == "rule"


def test_extract_uses_rules_without_key(monkeypatch):
    monkeypatch.setattr(client, "available", lambda: False)
    assert extract_mod.extract(RAW, "x").engine == "rule"
