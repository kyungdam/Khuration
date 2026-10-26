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
    chatkhu_model_vision: str = "gemini-3.8-flash"
    chatkhu_model_chat: str = "gemini-3.5-flash-lite"
    chatkhu_model_dev: str = "gpt-5.4-nano"

    @field_validator("app_mode")
    @classmethod
    def _mode(cls, v: str) -> str:
        v = (v or "").strip().strip("\"'").lower()  # " Live", "live " 같은 값도 허용
        if v not in ("demo", "live"):
            raise ValueError(f"APP_MODE는 demo 또는 live 여야 합니다 (지금 값: {v!r})")
        return v


settings = Settings()
