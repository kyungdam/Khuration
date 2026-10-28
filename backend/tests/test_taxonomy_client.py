"""단일 목록(taxonomy.json)과 AI 호출 옵션(생각 토큰·JSON 모드) 처리."""
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import taxonomy
from app.config import settings
from app.llm import client
from app.llm.intent import extract_keywords
from app.main import app
from app.matching.engine import COLLEGE_OF, evaluate


def test_one_department_list_everywhere():
    assert COLLEGE_OF["컴퓨터공학과"] == "소프트웨어융합대학"  # 예전에는 서버만 전자정보대학이었음
    html = (Path(__file__).resolve().parents[2] / "web" / "index.html").read_text(encoding="utf-8")
    for d in taxonomy.DEPARTMENTS:  # 앱의 기본 목록도 같은 단과대·캠퍼스
        assert re.search(rf"\['{d['dept']}', '{d['college']}', '{d['campus']}'\]", html), d


def test_meta_endpoint_serves_taxonomy():
    with TestClient(app) as c:
        m = c.get("/meta").json()
    assert {d["dept"] for d in m["departments"]} == {d["dept"] for d in taxonomy.DEPARTMENTS}
    assert [i["key"] for i in m["interests"]] and "학사" in m["categories"]


def test_judging_uses_college_from_taxonomy():
    status, _ = evaluate({"colleges": ["소프트웨어융합대학"]}, {"dept": "컴퓨터공학과"})
    assert status == "match"


def test_intent_keywords_unchanged():
    assert extract_keywords("방학 때 AI 공모전 나가고 싶어") == ["ai_data", "contest"]


class _Resp:
    def __init__(self, code, data):
        self.status_code, self._d, self.text = code, data, json.dumps(data)

    def json(self):
        return self._d


def test_unsupported_options_are_dropped_once(monkeypatch):
    monkeypatch.setattr(settings, "chatkhu_api_key", "k")
    monkeypatch.setattr(settings, "chatkhu_base_url", "https://example.com/v1")
    monkeypatch.setattr(settings, "chatkhu_reasoning_effort", "low")
    monkeypatch.setattr(client, "_unsupported", set())
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append(sorted(json))
        if "reasoning_effort" in json or "response_format" in json:
            return _Resp(400, {"error": "unknown parameter"})
        return _Resp(200, {"choices": [{"message": {"content": "{}"}}],
                           "usage": {"prompt_tokens": 7, "completion_tokens": 3}})

    monkeypatch.setattr(client.httpx, "post", fake_post)
    assert client.chat([{"role": "user", "content": "x"}], "m", json_mode=True) == "{}"
    assert client._unsupported == {"reasoning_effort", "response_format"} and len(sent) == 2
    client.chat([{"role": "user", "content": "x"}], "m", json_mode=True)
    assert len(sent) == 3 and "reasoning_effort" not in sent[-1]  # 다음부터는 바로 빼고 보냄


def test_options_sent_when_supported(monkeypatch):
    monkeypatch.setattr(settings, "chatkhu_api_key", "k")
    monkeypatch.setattr(settings, "chatkhu_base_url", "https://example.com/v1")
    monkeypatch.setattr(settings, "chatkhu_reasoning_effort", "low")
    monkeypatch.setattr(client, "_unsupported", set())
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append(json)
        return _Resp(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(client.httpx, "post", fake_post)
    client.chat([{"role": "user", "content": "x"}], "m", json_mode=True)
    assert sent[0]["reasoning_effort"] == "low" and sent[0]["response_format"] == {"type": "json_object"}
