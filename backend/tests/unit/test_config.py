from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.config import Settings


def build(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://user:pass@localhost:5432/entrelinhas",
        "public_origin": "http://localhost:5173",
        "files_root": Path("/tmp/files"),
    }
    return Settings(**{**defaults, **overrides})


def test_openai_key_is_optional_but_budget_is_bounded() -> None:
    settings = build(openai_api_key=None, ai_development_budget_usd="2.00")

    assert settings.openai_api_key is None
    assert settings.ai_model == "gpt-5-mini"
    assert settings.ai_max_output_tokens == 800
    assert settings.ai_gateway == "disabled"
    assert settings.ai_development_budget_usd == Decimal("2.00")
    assert settings.ai_manual_smoke_budget_usd == Decimal("0.25")


def test_manual_smoke_budget_cannot_exceed_the_development_budget() -> None:
    with pytest.raises(ValidationError):
        build(ai_development_budget_usd="0.10", ai_manual_smoke_budget_usd="0.25")


def test_budgets_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        build(ai_development_budget_usd="-1")


def test_openai_gateway_requires_a_key() -> None:
    with pytest.raises(ValidationError):
        build(ai_gateway="openai", openai_api_key=None)


def test_the_key_never_renders_in_plain_text() -> None:
    settings = build(ai_gateway="openai", openai_api_key="sk-secret-value")

    assert "sk-secret-value" not in repr(settings)
    assert "sk-secret-value" not in str(settings.model_dump())
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-secret-value"
