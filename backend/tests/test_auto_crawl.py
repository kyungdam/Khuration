"""서버 켤 때 자동 수집: live 모드에서 마지막 수집이 오래됐을 때만 시작."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.crawler import auto
from app.crawler import run as run_mod


@pytest.fixture()
def live(monkeypatch, tmp_path):
    monkeypatch.setattr(auto, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(settings, "app_mode", "live")
    monkeypatch.setattr(settings, "auto_crawl", True)
    monkeypatch.setattr(settings, "auto_crawl_hours", 12)
    return tmp_path / "state.json"


def _ago(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def test_due_rules(live, monkeypatch):
    assert auto.due()  # 수집한 적 없음
    live.write_text(json.dumps({"last_finished": _ago(2)}))
    assert not auto.due()  # 2시간 전에 했음
    live.write_text(json.dumps({"last_finished": _ago(13)}))
    assert auto.due()
    live.write_text(json.dumps({"last_finished": _ago(13), "running_since": _ago(0.1)}))
    assert not auto.due()  # 이미 수집 중
    live.write_text(json.dumps({"last_finished": _ago(13), "running_since": _ago(3)}))
    assert auto.due()  # 수집 중 표시가 오래됨(서버가 꺼졌던 것) → 다시
    monkeypatch.setattr(settings, "app_mode", "demo")
    assert not auto.due()  # 시연 모드에서는 안 함


def test_maybe_start_runs_in_background_and_records(live, monkeypatch):
    monkeypatch.setattr(run_mod, "run", lambda sources, limit, dry_run: {"new": 3, "changed": 0, "same": 1, "error": 0})
    assert auto.maybe_start()
    for t in __import__("threading").enumerate():
        if t.name == "auto-crawl":
            t.join(5)
    st = auto.status()
    assert st["running"] is False and st["last_finished"] and st["last_result"]["new"] == 3
    assert not auto.maybe_start()  # 방금 했으니 다시 안 함
