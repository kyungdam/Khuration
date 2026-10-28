from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # utf-8-sig: 메모장/VS Code가 .env 앞에 BOM을 붙여도 첫 줄(APP_MODE)을 제대로 읽는다
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", extra="ignore")

    app_mode: str = "demo"  # demo | live
    database_url: str = "sqlite:///./dev.db"
    chatkhu_api_key: str = ""
    chatkhu_base_url: str = ""
    chatkhu_model_extract: str = "gemini-3.8-flash"
    chatkhu_model_extract_strong: str = "gemini-3.1-pro-preview"  # 근거 확인에 실패한 공지만 한 번 더 (비우면 끔)
    chatkhu_model_vision: str = "gemini-3.8-flash"
    chatkhu_model_chat: str = "gemini-3.5-flash-lite"
    chatkhu_model_dev: str = "gpt-5.4-nano"
    # 모델의 '생각' 토큰 양: low(기본, 절약) | medium | high | 빈칸(모델 기본값). 게이트웨이가 거부하면 자동으로 뺀다
    chatkhu_reasoning_effort: str = "low"

    # 서버 켤 때 자동 수집 (live 모드에서만). 마지막 수집이 auto_crawl_hours 보다 오래됐으면 뒤에서 수집 시작
    auto_crawl: bool = True
    auto_crawl_hours: float = 12
    auto_crawl_limit: int = 10  # 게시판당 최신 N건

    @field_validator("app_mode")
    @classmethod
    def _mode(cls, v: str) -> str:
        v = (v or "").strip().strip("\"'").lower()  # " Live", "live " 같은 값도 허용
        if v not in ("demo", "live"):
            raise ValueError(f"APP_MODE는 demo 또는 live 여야 합니다 (지금 값: {v!r})")
        return v


settings = Settings()
