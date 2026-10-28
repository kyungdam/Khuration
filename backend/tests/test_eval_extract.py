"""정확도 측정 도구: 정답 칸 ↔ 값 변환과 지표 계산."""
from datetime import datetime

from app.crawler.eval_extract import _metrics, parse_cell, to_cells


def test_cells_round_trip():
    crit = {"campuses": ["global"], "departments": ["화학공학과"], "colleges": ["공과대학"], "grades": [3, 4],
            "min_gpa": 3.5, "min_credits": None, "income_max": 8, "requires_lang_score": True, "open_to_all": None}
    cells = to_cells(datetime(2026, 11, 14, 14, 59), crit)
    assert cells["정답_마감일"] == "2026-11-14" and cells["정답_캠퍼스"] == "국제" and cells["정답_학년"] == "3,4"
    assert parse_cell("campuses", cells["정답_캠퍼스"]) == frozenset({"global"})
    assert parse_cell("grades", "3, 4학년") == frozenset({3, 4})
    assert parse_cell("min_gpa", "3.5") == 3.5 and parse_cell("min_credits", "") is None
    assert parse_cell("requires_lang_score", "O") is True and parse_cell("open_to_all", "") is None
    assert parse_cell("deadline", "2026.11.9") == "2026-11-09"


def test_metrics_count_wrong_confirmations():
    m = _metrics([(3.5, 3.5), (3.0, None), (None, 3.0), (None, None)])
    assert m == {"pred": 2, "gold": 2, "ok": 1, "wrong": 1, "precision": 0.5, "recall": 0.5}


def test_stats_uses_only_cached_answers(monkeypatch, tmp_path):
    import json

    from app.crawler import eval_extract, extract_llm
    from app.db import Base, SessionLocal, engine
    from app.llm import client
    from app.models import Notice

    monkeypatch.setattr(extract_llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(eval_extract, "EVAL_DIR", tmp_path)
    monkeypatch.setattr(eval_extract, "STATS", tmp_path / "stats.md")
    Base.metadata.create_all(engine)
    body = "장학생 선발 공고\n신청 기간: 11. 3.(월) ~ 11. 14.(금)\n지원 자격: 3~4학년"
    with SessionLocal() as db:
        n = Notice(url="https://example.com/stats/1", title="장학생 선발", body_text=body, posted_at=datetime(2026, 10, 28))
        db.add(n)
        db.commit()
        raw, src = eval_extract.rebuild(n)
    answer = {"deadline": "11-14", "criteria": {"grades": [3, 4], "min_credits": 60},
              "evidence": {"deadline": "~ 11. 14.(금)", "grades": "3~4학년", "min_credits": "60학점 이상"}}
    monkeypatch.setattr(client, "chat", lambda *a, **k: json.dumps(answer))
    extract_llm.extract_with_llm(raw, src)  # 크롤링처럼 캐시를 만든다

    def must_not_call(*a, **k):
        raise AssertionError("stats는 새로 호출하면 안 됨")

    monkeypatch.setattr(client, "chat", must_not_call)
    eval_extract.stats()
    text = (tmp_path / "stats.md").read_text(encoding="utf-8")
    assert "자동 차단" in text and "근거가 원문에 없음" in text
