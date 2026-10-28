from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import clock, models  # noqa: F401  (모델 등록)
from .config import settings
from .crawler import auto as auto_crawl
from .db import Base, SessionLocal, engine
from .routers import ai, demo, devices, feed, notices
from .seed_loader import load_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.app_mode == "demo":
        with SessionLocal() as db:
            load_seed(db)  # 비어 있을 때만 시드 로드
    if auto_crawl.maybe_start():  # live 모드: 마지막 수집이 오래됐으면 뒤에서 수집 (화면은 막지 않음)
        print("[자동 수집] 마지막 수집이 오래돼서 백그라운드 수집을 시작했어요. 진행 상태: /health")
    yield


app = FastAPI(title="Khuration API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health():
    """mode로 앱이 시연 패널을 보일지 정하고, today(KST, 시연 시계 반영)로 D-day를 계산한다."""
    return {"ok": True, "mode": settings.app_mode, "today": clock.kst_date(clock.now()).isoformat(),
            "offset_days": clock.offset_days(), "crawl": auto_crawl.status()}


app.include_router(devices.router)
app.include_router(feed.router)
app.include_router(notices.router)
app.include_router(ai.router)
if settings.app_mode == "demo":
    app.include_router(demo.router, prefix="/demo")

# 앱 화면(HTML). 폰의 Expo Go(WebView)나 브라우저에서 http://<PC IP>:8000/web/ 으로 연다.
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if WEB_DIR.is_dir():
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/web/")
