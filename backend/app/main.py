from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (모델 등록)
from .config import settings
from .db import Base, SessionLocal, engine
from .routers import ai, demo, devices, feed, notices
from .seed_loader import load_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.app_mode == "demo":
        with SessionLocal() as db:
            load_seed(db)  # 비어 있을 때만 시드 로드
    yield


app = FastAPI(title="Khuration API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"ok": True, "mode": settings.app_mode}


app.include_router(devices.router)
app.include_router(feed.router)
app.include_router(notices.router)
app.include_router(ai.router)
if settings.app_mode == "demo":
    app.include_router(demo.router, prefix="/demo")
