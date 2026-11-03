from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://nutrition:nutrition@localhost:5432/nutrition"
    session_cookie_name: str = "nutrition_session"
    session_cookie_secure: bool = False
    session_ttl_days: int = Field(default=30, gt=0)
    openfoodfacts_contact_email: str | None = None
    openfoodfacts_usage_form_completed: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
