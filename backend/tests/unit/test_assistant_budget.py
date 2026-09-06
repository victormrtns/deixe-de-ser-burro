from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest

from app.assistant import budget
from app.assistant.gateway import ModelUsage
from app.config import Settings
from app.errors import AppError

MODEL = "gpt-5-mini"


def _settings(budget_usd: str) -> Settings:
    """Only the budget field matters here; a real Settings needs a database."""
    return cast(Settings, SimpleNamespace(ai_development_budget_usd=Decimal(budget_usd)))


@pytest.mark.parametrize(
    ("spent_and_reserved", "expected"),
    [
        (0, "normal"),
        (790_000, "normal"),
        (799_999, "normal"),
        (800_000, "near_limit"),
        (990_000, "near_limit"),
        (999_999, "near_limit"),
        (1_000_000, "blocked"),
        (1_500_000, "blocked"),
    ],
)
def test_state_boundaries(spent_and_reserved: int, expected: str) -> None:
    assert budget.state_for(spent_and_reserved, 1_000_000) == expected


def test_a_zero_limit_is_always_blocked() -> None:
    assert budget.state_for(0, 0) == "blocked"


def test_worst_case_covers_a_response_that_used_the_whole_output_budget() -> None:
    prompt = "a" * 4_000
    worst_case = budget.worst_case_micros(MODEL, input_chars=len(prompt), max_output_tokens=800)

    actual = budget.actual_cost_micros(
        MODEL, ModelUsage(input_tokens=1_000, output_tokens=800, total_tokens=1_800)
    )

    assert worst_case >= actual


def test_worst_case_rounds_the_partial_token_up() -> None:
    # 1 char is a fraction of a token but must still be paid for.
    assert budget.worst_case_micros("gpt-5-mini", input_chars=1, max_output_tokens=0) == 1


def test_actual_cost_matches_the_price_table() -> None:
    # 4000 * 0.25 USD/Mtok + 500 * 2.00 USD/Mtok = 0.001 + 0.001 USD.
    usage = ModelUsage(input_tokens=4_000, output_tokens=500, total_tokens=4_500)

    assert budget.actual_cost_micros(MODEL, usage) == 2_000


def test_the_fake_model_costs_nothing() -> None:
    usage = ModelUsage(input_tokens=10_000, output_tokens=10_000, total_tokens=20_000)

    assert budget.actual_cost_micros("fake-model", usage) == 0


def test_an_unpriced_model_is_refused() -> None:
    with pytest.raises(AppError) as raised:
        budget.actual_cost_micros("gpt-42", ModelUsage(1, 1, 2))

    assert raised.value.code == "ai_model_not_priced"
    assert "gpt-42" in raised.value.message


def test_limit_rounds_the_configured_budget_down() -> None:
    assert budget.limit_micros(_settings("2.0000009")) == 2_000_000


def test_money_never_becomes_a_float() -> None:
    values = [
        budget.limit_micros(_settings("0.25")),
        budget.worst_case_micros(MODEL, input_chars=999, max_output_tokens=13),
        budget.actual_cost_micros(MODEL, ModelUsage(7, 3, 10)),
    ]

    assert all(type(value) is int for value in values)
