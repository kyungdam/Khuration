"""서버 켤 때 자동 수집.

PC를 계속 켜 둘 수 없어서 정해진 시각(14시·20시) 대신, 서버가 켜질 때 마지막 수집이
AUTO_CRAWL_HOURS(기본 12시간)보다 오래됐으면 뒤에서(스레드) 수집을 시작한다. 화면은 막지 않는다.
- live 모드에서만 돈다 (demo는 시연 공지를 쓰므로 크롤링 불필요)
- 상태는 backend/.crawl_state.json 에 남고 /health 의 "crawl" 로 볼 수 있다
- 끄기: backend/.env 에 AUTO_CRAWL=false
정기 실행(14시·20시)은 scripts/crawl.ps1 + 작업 스케줄러(팀원 문서) 또는 클라우드 배포 후 고도화.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import settings

STATE = Path(__file__).resolve().parents[2] / ".crawl_state.json"
STALE_RUNNING = timedelta(hours=1)  # 서버가 수집 중에 꺼졌으면 '수집 중' 표시를 1시간 뒤 무시
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(d: dict) -> None:
    try:
        STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def status() -> dict:
    """/health 에 붙는 수집 상태"""
    d = _read()
    running = d.get("running_since")
    if running and _now() - (_ts(running) or _now()) > STALE_RUNNING:
        running = None
    return {"enabled": settings.auto_crawl and settings.app_mode == "live", "running": bool(running),
            "last_finished": d.get("last_finished"), "last_result": d.get("last_result")}


def due() -> bool:
    if not settings.auto_crawl or settings.app_mode != "live":
        return False
    d = _read()
    run_since = _ts(d.get("running_since"))
    if run_since and _now() - run_since < STALE_RUNNING:
        return False  # 이미 수집 중 (--reload로 서버가 다시 켜진 경우 등)
    last = _ts(d.get("last_finished"))
    return last is None or _now() - last >= timedelta(hours=settings.auto_crawl_hours)


def _job() -> None:
    from .adapters import ADAPTERS
    from .run import run

    started = time.monotonic()
    print(f"[자동 수집] 시작 (게시판 {len(ADAPTERS)}곳, 최신 {settings.auto_crawl_limit}건씩)")
    result: dict
    try:
        result = run(list(ADAPTERS), settings.auto_crawl_limit, dry_run=False)
    except Exception as e:  # 수집 실패가 서버를 멈추지 않게
        result = {"error": str(e)[:200]}
    d = _read()
    d.pop("running_since", None)
    d["last_finished"] = _now().isoformat()
    d["last_result"] = {**result, "minutes": round((time.monotonic() - started) / 60, 1)}
    _write(d)
    print(f"[자동 수집] 끝: {d['last_result']}")


def maybe_start() -> bool:
    """수집할 때가 됐으면 백그라운드로 시작. 시작했으면 True."""
    with _lock:
        if not due():
            return False
        d = _read()
        d["running_since"] = _now().isoformat()
        _write(d)
    threading.Thread(target=_job, name="auto-crawl", daemon=True).start()
    return True
