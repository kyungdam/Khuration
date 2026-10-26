from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (모델 등록)
from .config import settings
from .db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Khuration API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"ok": True, "mode": settings.app_mode}


# 라우터는 만들면서 추가
# from .routers import devices, feed, notices, demo
# app.include_router(devices.router)
# app.include_router(feed.router)
# app.include_router(notices.router)
# if settings.app_mode == "demo":
#     app.include_router(demo.router, prefix="/demo")
