from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    AnyHttpUrl,
    NonNegativeInt,
    PositiveInt,
    PostgresDsn,
    SecretStr,
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

    # The assistant is optional infrastructure: with `ai_gateway="disabled"` the
    # editor, history, reading, and publishing keep working untouched.
    ai_gateway: Literal["disabled", "fake", "openai"] = "disabled"
    openai_api_key: SecretStr | None = None
    ai_model: str = "gpt-5-mini"
    ai_max_output_tokens: PositiveInt = 800
    ai_max_context_chars: PositiveInt = 120_000
    ai_development_budget_usd: Decimal = Decimal("2.00")
    ai_manual_smoke_budget_usd: Decimal = Decimal("0.25")

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

    @field_validator("ai_development_budget_usd", "ai_manual_smoke_budget_usd")
    @classmethod
    def budget_is_nonnegative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("budget must not be negative")
        return value

    @model_validator(mode="after")
    def ai_configuration_is_coherent(self) -> Self:
        if self.ai_manual_smoke_budget_usd > self.ai_development_budget_usd:
            raise ValueError("manual smoke budget must not exceed the development budget")
        if self.ai_gateway == "openai" and self.openai_api_key is None:
            raise ValueError("ai_gateway=openai requires OPENAI_API_KEY")
        return self

    @model_validator(mode="after")
    def production_is_secure(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
