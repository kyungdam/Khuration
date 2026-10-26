from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: str = "demo"  # demo | live
    database_url: str = "sqlite:///./dev.db"
    chatkhu_api_key: str = ""
    chatkhu_base_url: str = ""
    chatkhu_model_extract: str = "gemini-3.8-flash"
    chatkhu_model_vision: str = "gemini-3.8-flash"
    chatkhu_model_chat: str = "gemini-3.5-flash-lite"
    chatkhu_model_dev: str = "gpt-5.4-nano"


settings = Settings()
