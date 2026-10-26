from fastapi.testclient import TestClient

from app.main import app

TOKEN = "ExponentPushToken[test]"
TAGS = {"campus": "global", "dept": "화학공학과", "college": "공과대학", "grade": 3,
        "gpa_floor": 3.5, "last_gpa_floor": 4.0, "credits_floor": 70, "income_band": 5,
        "interests": ["ai_data", "internship"]}
H = {"X-Device-Token": TOKEN}


def test_flow():
    with TestClient(app) as c:
        assert c.get("/health").json()["mode"] == "demo"
        # 이름·학번은 서버가 거부한다
        r = c.post("/devices", json={"push_token": TOKEN, "tags": {**TAGS, "name": "홍길동"}})
        assert r.status_code == 422
        r = c.post("/devices", json={"push_token": TOKEN, "tags": {**TAGS, "student_id": "2020"}})
        assert r.status_code == 422
        assert c.post("/devices", json={"push_token": TOKEN, "tags": TAGS}).status_code == 200

        feed = c.get("/feed", headers=H).json()
        titles = [i["title"] for i in feed]
        assert not any("마감됨" in t for t in titles)  # 마감 지난 공지 제외
        assert all(i["status"] != "mismatch" for i in feed)
        order = [i["status"] for i in feed]
        assert order == sorted(order, key=["match", "check"].index)  # 일치 → 확인 필요
        assert any(i["status"] == "check" for i in feed)
        # 현장실습 90학점은 불일치라 기본 피드에서 빠지고, include_mismatch면 보인다
        assert not any("하계 현장실습" in t for t in titles)
        allf = c.get("/feed?include_mismatch=true", headers=H).json()
        assert any("하계 현장실습" in i["title"] for i in allf)

        # 문장 → 키워드, 원문은 저장되지 않음
        kw = c.post("/devices/intent", headers=H, json={"text": "방학 때 AI 공모전 나가고 싶어"}).json()
        assert "ai_data" in kw["keywords"] and "contest" in kw["keywords"]
        top = c.get("/feed", headers=H).json()[0]
        assert top["status"] == "match"

        # 상세
        d = c.get(f"/notices/{top['id']}", headers=H).json()
        assert d["requirements"]

        # 데모: 시계 앞당기기 → D-day 감소
        before = {i["id"]: i["d_day"] for i in feed}
        c.post("/demo/advance-clock", json={"days": 2})
        after = {i["id"]: i["d_day"] for i in c.get("/feed", headers=H).json()}
        k = next(k for k in after if k in before and before[k] is not None)
        assert after[k] == before[k] - 2
        c.post("/demo/reset-clock")

        # 푸시: Expo 토큰이 아니면 미리보기, 중복 방지
        t2 = "plain-token"
        c.post("/devices", json={"push_token": t2, "tags": TAGS})
        h2 = {"X-Device-Token": t2}
        p = c.post("/demo/fire-push", headers=h2, json={"kind": "d3"}).json()
        assert p["sent"] is False and "preview" in p
        p2 = c.post("/demo/fire-push", headers=h2, json={"kind": "d3", "force": False}).json()
        assert "중복" in p2["reason"]

        assert c.delete("/devices", headers=h2).json()["deleted"]


def test_notices_list_detail_and_chat(monkeypatch):
    from app.llm import client

    monkeypatch.setattr(client, "available", lambda: False)  # 실제 ChatKHU를 부르지 않는다
    with TestClient(app) as c:
        c.post("/devices", json={"push_token": TOKEN, "tags": TAGS})
        allv = c.get("/notices").json()
        assert len(allv) >= 20 and all(i["posted_date"] for i in allv)
        assert c.get("/notices?q=해커톤").json()[0]["title"].endswith("해커톤 참가자 모집")
        dl = [i["d_day"] for i in c.get("/notices?sort=deadline").json()]
        assert dl == sorted(dl)
        sch = c.get("/notices?category=장학").json()
        assert sch and all(i["category"] == "장학" for i in sch)

        ai = next(i for i in allv if "AI 아이디어" in i["title"])
        d = c.get(f"/notices/{ai['id']}", headers=H).json()
        assert len(d["summary_points"]) == 3 and len(d["checklist"]) == 5 and d["apply_url"]

        r = c.post("/ai/chat", headers=H, json={"message": "AI 관련 공모전 있어?"}).json()
        assert r["items"] and all("contest" in i["topics"] or "ai_data" in i["topics"] for i in r["items"])
        assert r["engine"] == "rule"


def test_chat_uses_llm_text_when_available(monkeypatch):
    from app.llm import chat as chat_mod
    from app.llm import client

    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(client, "chat", lambda *a, **k: "마감이 가까운 공모전부터 보여 드릴게요. 카드에서 확인해 보세요!")
    out = chat_mod.answer("AI 공모전", [], {"interests": ["ai_data"]})
    assert out["engine"] == "chatkhu" and out["answer"].startswith("마감이")


def test_chat_falls_back_when_llm_fails(monkeypatch):
    from app.llm import chat as chat_mod
    from app.llm import client

    def boom(*a, **k):
        raise client.LLMError("HTTP 500")

    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(client, "chat", boom)
    out = chat_mod.answer("AI 공모전", [], {})
    assert out["engine"] == "rule" and "찾지 못했어요" in out["answer"]


def test_web_app_is_served():
    """앱 화면 HTML(web/index.html)을 서버가 /web/ 으로 내려준다."""
    from pathlib import Path

    if not (Path(__file__).resolve().parents[2] / "web" / "index.html").exists():
        import pytest

        pytest.skip("web/index.html 없음")
    with TestClient(app) as c:
        r = c.get("/web/")
        assert r.status_code == 200 and "KHURATION" in r.text
