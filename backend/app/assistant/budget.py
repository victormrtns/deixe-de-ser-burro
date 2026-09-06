from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.gateway import ModelUsage
from app.assistant.models import AiUsageEntry
from app.assistant.schemas import UsageSummaryDto
from app.clock import utc_now
from app.config import Settings
from app.errors import AppError

BudgetState = Literal["normal", "near_limit", "blocked"]

USD_MICROS = 1_000_000
TOKENS_PER_MTOK = 1_000_000
CHARS_PER_TOKEN = 4
NEAR_LIMIT_PERCENT = 80

# Provider list prices, in USD micros per million tokens: (input, output).
MODEL_PRICES_USD_MICROS_PER_MTOK: dict[str, tuple[int, int]] = {
    "gpt-5-mini": (250_000, 2_000_000),
    "fake-model": (0, 0),
}

# One cluster-wide key: reservations are rare and must serialise against the
# single global budget, so a finer lock would buy nothing.
_BUDGET_LOCK_KEY = 4_301_991_001


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def _prices(model: str) -> tuple[int, int]:
    try:
        return MODEL_PRICES_USD_MICROS_PER_MTOK[model]
    except KeyError:
        raise AppError(
            "ai_model_not_priced",
            f"Modelo sem tabela de preços: {model}.",
            500,
        ) from None


def _cost_micros(model: str, *, input_tokens: int, output_tokens: int) -> int:
    input_price, output_price = _prices(model)
    return _ceil_div(input_tokens * input_price + output_tokens * output_price, TOKENS_PER_MTOK)


def state_for(spent_and_reserved: int, limit: int) -> BudgetState:
    if limit <= 0 or spent_and_reserved >= limit:
        return "blocked"
    if spent_and_reserved * 100 >= limit * NEAR_LIMIT_PERCENT:
        return "near_limit"
    return "normal"


def limit_micros(settings: Settings) -> int:
    """Round the configured budget down: never spend a micro that was not granted."""
    return int(settings.ai_development_budget_usd * USD_MICROS)


def worst_case_micros(model: str, *, input_chars: int, max_output_tokens: int) -> int:
    """Price the most expensive answer the request could produce."""
    return _cost_micros(
        model,
        input_tokens=_ceil_div(input_chars, CHARS_PER_TOKEN),
        output_tokens=max_output_tokens,
    )


def actual_cost_micros(model: str, usage: ModelUsage) -> int:
    return _cost_micros(model, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)


async def totals(session: AsyncSession) -> tuple[int, int]:
    """Return `(settled_micros, reserved_micros)`; released entries count zero."""
    settled = func.coalesce(
        func.sum(case((AiUsageEntry.state == "settled", AiUsageEntry.actual_usd_micros), else_=0)),
        0,
    )
    reserved = func.coalesce(
        func.sum(
            case((AiUsageEntry.state == "reserved", AiUsageEntry.reserved_usd_micros), else_=0)
        ),
        0,
    )
    row = (await session.execute(select(settled, reserved))).one()
    return int(row[0]), int(row[1])


async def reserve(
    session: AsyncSession,
    *,
    writing_id: UUID,
    attempt_id: UUID,
    worst_case: int,
    limit: int,
) -> AiUsageEntry:
    """Hold the worst-case cost before any external call, or refuse the call."""
    # Held until this transaction ends, so a concurrent reservation cannot read
    # the totals between our check and our insert.
    await session.execute(select(func.pg_advisory_xact_lock(_BUDGET_LOCK_KEY)))
    settled, reserved = await totals(session)
    if settled + reserved + worst_case > limit:
        raise AppError("ai_budget_exceeded", "O orçamento de IA desta fase foi atingido.", 429)

    entry = AiUsageEntry(
        writing_id=writing_id,
        generation_attempt_id=attempt_id,
        state="reserved",
        reserved_usd_micros=worst_case,
    )
    session.add(entry)
    await session.flush()
    return entry


async def _close(session: AsyncSession, attempt_id: UUID, *, state: str, micros: int) -> None:
    await session.execute(
        update(AiUsageEntry)
        .where(
            AiUsageEntry.generation_attempt_id == attempt_id,
            AiUsageEntry.state == "reserved",
        )
        .values(state=state, actual_usd_micros=micros, settled_at=utc_now())
    )


async def settle(session: AsyncSession, attempt_id: UUID, *, actual_micros: int) -> None:
    """Replace the reservation with the real cost, exactly once."""
    await _close(session, attempt_id, state="settled", micros=actual_micros)


async def release(session: AsyncSession, attempt_id: UUID) -> None:
    """Give an unspent reservation back, exactly once."""
    await _close(session, attempt_id, state="released", micros=0)


async def summary(session: AsyncSession, *, limit: int) -> UsageSummaryDto:
    settled, reserved = await totals(session)
    return UsageSummaryDto(
        period=utc_now().strftime("%Y-%m"),
        spent_usd_micros=settled,
        reserved_usd_micros=reserved,
        limit_usd_micros=limit,
        limit_state=state_for(settled + reserved, limit),
    )
