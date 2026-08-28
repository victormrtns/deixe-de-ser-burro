from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import AnyHttpUrl, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn
    public_origin: AnyHttpUrl
    files_root: Path
    session_cookie_name: str = "entrelinhas_session"
    session_ttl_hours: int = 168
    cookie_secure: bool = False
    max_cover_bytes: int = 5_000_000
    log_level: str = "INFO"

    @model_validator(mode="after")
    def production_is_secure(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
