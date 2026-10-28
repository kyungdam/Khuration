"""KHU AI 검색(RAG) + 캐시. 시드 공지([데모])로 검사하고, ChatKHU는 가짜로 바꾼다."""
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.llm import client
from app.main import app
from app.models import Notice
from app.rag import index

TOKEN = "ExponentPushToken[rag-test]"
H = {"X-Device-Token": TOKEN}
TAGS = {"campus": "global", "dept": "화학공학과", "college": "공과대학", "grade": 3, "interests": ["dev_it"]}


@pytest.fixture()
def c():
    with TestClient(app) as tc:
        tc.post("/demo/reseed")
        tc.post("/devices", json={"push_token": TOKEN, "tags": TAGS})
        yield tc


def test_tokens_use_korean_bigrams():
    assert index.tokens("인정돼요 AI") == ["인정", "정돼", "돼요", "ai"]
    assert index.tokens("팀") == ["팀"]


def test_split_chunks_keeps_everything_with_overlap():
    text = "\n".join(f"{i}번째 문단입니다. " * 8 for i in range(30))
    chunks = index.split_chunks(text)
    assert len(chunks) > 1 and all(len(ch) <= index.CHUNK_CHARS + index.OVERLAP_CHARS + 50 for ch in chunks)
    assert "29번째" in chunks[-1]


def test_search_finds_notice_by_body_words(c):
    with SessionLocal() as db:
        hits = index.search(db, "해커톤 팀 매칭 어떻게 돼?")
        assert hits and "해커톤" in hits[0].title


def test_expired_notices_are_not_searched_by_default(c):
    with SessionLocal() as db:
        expired = db.query(Notice).filter(Notice.title.contains("마감됨")).one()
        q = "지난 학기 장학금 추가 신청"
        assert expired.id not in {h.notice_id for h in index.search(db, q)}
        assert expired.id in {h.notice_id for h in index.search(db, q, include_expired=True)}


def test_sync_only_rebuilds_changed_notices(c):
    with SessionLocal() as db:
        index.sync(db)
        assert index.sync(db) == 0  # 그대로면 다시 만들지 않음
        n = db.query(Notice).filter(Notice.title.contains("해커톤")).one()
        n.body_text = "본선 장소는 국제캠퍼스 전자정보대학관입니다."
        db.commit()
        assert index.sync(db) == 1
        assert any("전자정보대학관" in h.text for h in index.search(db, "본선 장소 어디야"))


def test_chat_uses_evidence_and_caches_answer(c, monkeypatch):
    calls = []

    def fake_chat(messages, model, **k):
        calls.append(messages[-1]["content"])
        return "해커톤은 개인 신청 시 팀을 매칭해 줘요 [1]."

    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(client, "chat", fake_chat)
    q = {"message": "해커톤 팀 매칭 어떻게 돼?"}
    r1 = c.post("/ai/chat", headers=H, json=q).json()
    assert r1["engine"] == "chatkhu" and not r1["cached"]
    assert r1["evidence"] and "해커톤" in r1["evidence"][0]["title"]
    assert "[근거]" in calls[0] and "팀 매칭" in calls[0]
    assert "화학공학과" not in calls[0] and "3.5" not in calls[0]  # 조건 태그는 LLM에 안 보냄

    r2 = c.post("/ai/chat", headers=H, json={"message": "  해커톤 팀 매칭 어떻게 돼  "}).json()
    assert r2["cached"] and r2["answer"] == r1["answer"]
    assert len(calls) == 1  # 두 번째는 모델을 부르지 않음


def test_chat_falls_back_to_rule_when_llm_fails(c, monkeypatch):
    def boom(*a, **k):
        raise client.LLMError("HTTP 500")

    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(client, "chat", boom)
    r = c.post("/ai/chat", headers=H, json={"message": "해커톤 팀 매칭 방식이 궁금해"}).json()
    assert r["engine"] == "rule" and "해커톤" in r["answer"] and r["items"]


def test_search_only_returns_current_mode_notices(c):
    """시연 모드에서는 크롤링 공지가, 실제 모드에서는 [데모] 공지가 검색되지 않는다."""
    with SessionLocal() as db:
        crawled = Notice(url="https://example.com/rag/live-1", title="실시간 해커톤 팀 매칭 안내", is_demo=False,
                         body_text="해커톤 팀 매칭 방식 안내")
        db.add(crawled)
        db.commit()
        ids = {h.notice_id for h in index.search(db, "해커톤 팀 매칭 어떻게 돼?")}
        assert crawled.id not in ids and ids  # 지금은 demo 모드
        db.delete(crawled)
        db.commit()


def test_chat_needs_both_kind_and_field(c):
    """'AI 공모전'이면 공모전이면서 AI·데이터인 공지만 (예전엔 AI 강좌나 다른 공모전이 섞였음)"""
    r = c.post("/ai/chat", headers=H, json={"message": "AI 공모전 나가고싶어"}).json()
    assert r["items"] and all("contest" in i["topics"] and "ai_data" in i["topics"] for i in r["items"])
    assert all(e["notice_id"] in {i["id"] for i in r["items"]} for e in r["evidence"])


def test_chat_says_so_when_nothing_fits_both(c):
    """AI 장학금은 없으니 그렇다고 먼저 말하고 장학 공지를 보여 준다"""
    r = c.post("/ai/chat", headers=H, json={"message": "AI 장학금 있어?"}).json()
    assert r["answer"].startswith("AI·데이터 분야의 장학 공지는 지금 없어요")
    assert r["items"] and all("scholarship" in i["topics"] for i in r["items"])


def test_follow_up_question_uses_previous_cards(c):
    """'그거 마감 언제야?'는 앞 답변에 나온 공지 안에서만 답한다"""
    first = c.post("/ai/chat", headers=H, json={"message": "해커톤 팀 매칭 어떻게 돼?"}).json()
    ids = [i["id"] for i in first["items"]]
    r = c.post("/ai/chat", headers=H, json={"message": "그거 마감 언제야?", "prev": "해커톤 팀 매칭 어떻게 돼?",
                                            "context_ids": ids}).json()
    assert r["items"] and {i["id"] for i in r["items"]} <= set(ids)


def test_search_text_drops_filler():
    from app.llm.chat import search_text

    assert search_text("AI 공모전 나가고싶어") == "AI 공모전"
    assert search_text("국제캠퍼스 근로장학 알려줘") == "국제캠퍼스 근로장학"
    assert search_text("있어?") == "있어?"  # 다 지워지면 원문 그대로
