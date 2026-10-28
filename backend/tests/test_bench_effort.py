"""생각 수준 비교 도구: 가짜 ChatKHU로 두 설정을 번갈아 부르고 보고서를 쓰는지."""
import json
from datetime import datetime


def test_bench_alternates_levels_and_writes_report(monkeypatch, tmp_path):
    from app.db import Base, SessionLocal, engine
    from app.llm import bench_effort, client
    from app.models import Notice

    Base.metadata.create_all(engine)
    body = "장학생 선발 공고\n신청 기간: 11. 3.(월) ~ 11. 14.(금)\n지원 자격: 3~4학년 재학생\n" + "안내 문구입니다. " * 40
    with SessionLocal() as db:
        n = Notice(url="https://example.com/bench/1", title="벤치 장학생 선발", body_text=body,
                   posted_at=datetime(2099, 10, 28), is_demo=False)
        db.add(n)
        db.commit()
        nid = n.id

    seen = []

    def fake_chat(messages, model, **k):
        seen.append(k.get("reasoning"))
        client.last_usage = {"prompt_tokens": 900, "completion_tokens": 300 if k.get("reasoning") else 500}
        return json.dumps({"deadline": "11-14", "criteria": {"grades": [3, 4]},
                           "evidence": {"deadline": "11. 3.(월) ~ 11. 14.(금)", "grades": "지원 자격: 3~4학년 재학생"}})

    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(client, "chat", fake_chat)
    monkeypatch.setattr(bench_effort, "OUT", tmp_path / "bench.md")
    try:
        bench_effort.main(["--n", "1", "--repeat", "2"])
    finally:  # 다른 테스트가 실제(크롤링) 공지 수를 셀 수 있으니 지운다
        with SessionLocal() as db:
            db.delete(db.get(Notice, nid))
            db.commit()

    assert seen == ["", "low", "low", ""]  # 회차마다 순서를 바꿔 부른다
    report = (tmp_path / "bench.md").read_text(encoding="utf-8")
    assert "출력 토큰: low가 40% 적음" in report
    assert "결과(검증 후 마감일·조건) 같음: 1/1건" in report
    assert "게이트웨이가 Gemini의 생각 토큰 수를 알려 주지 않아" in report


def test_think_tokens_from_total_when_not_reported():
    from app.llm import client

    # ChatKHU 실제 응답 모양: 생각 토큰은 total에만 들어 있다
    assert client.think_tokens({"completion_tokens": 488, "prompt_tokens": 3903, "total_tokens": 5453,
                                "completion_tokens_details": None}) == 1062
    assert client.think_tokens({"completion_tokens_details": {"reasoning_tokens": 7}}) == 7
    assert client.think_tokens({"prompt_tokens": 10, "completion_tokens": 5}) is None
