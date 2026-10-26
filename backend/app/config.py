from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: str = "demo"  # demo | live
    database_url: str = "sqlite:///./dev.db"
    chatkhu_api_key: str = ""
    chatkhu_base_url: str = ""


settings = Settings()
