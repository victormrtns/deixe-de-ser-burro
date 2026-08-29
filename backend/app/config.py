from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    AnyHttpUrl,
    NonNegativeInt,
    PositiveInt,
    PostgresDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

ASYNC_POSTGRES_DRIVER = "postgresql+psycopg"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn
    public_origin: AnyHttpUrl
    files_root: Path
    session_cookie_name: str = "entrelinhas_session"
    session_ttl_hours: PositiveInt = 168
    session_touch_interval_seconds: NonNegativeInt = 300
    cookie_secure: bool = False
    max_cover_bytes: PositiveInt = 5_000_000
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def database_uses_async_psycopg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != ASYNC_POSTGRES_DRIVER:
            raise ValueError(f"database URL must use {ASYNC_POSTGRES_DRIVER}")
        return value

    @field_validator("public_origin")
    @classmethod
    def public_origin_is_canonical(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if (
            value.username is not None
            or value.password is not None
            or value.path not in (None, "/")
            or value.query is not None
            or value.fragment is not None
        ):
            raise ValueError("public origin must be an origin without path, query, or fragment")
        return value

    @model_validator(mode="after")
    def production_is_secure(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
