"""Настройки приложения (читаются из .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация backend-сервиса."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/keitaro_test"

    keitaro_base_url: str = "https://keitaro-for-tests.etolegko.com/admin_api/v1"
    keitaro_api_key: str = ""

    campaign_name_prefix: str = "test_negimatjanov_"
    geo_redirect_url: str = "https://google.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
