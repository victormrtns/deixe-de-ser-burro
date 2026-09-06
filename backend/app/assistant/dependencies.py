from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from app.assistant.fake_gateway import FakeModelGateway
from app.assistant.gateway import ModelGateway
from app.assistant.openai_gateway import OpenAIModelGateway
from app.config import Settings, get_settings
from app.errors import AppError

FAKE_ANSWER = ("Resposta simulada", " do assistente.")


def _unavailable() -> AppError:
    return AppError("ai_unavailable", "O assistente está indisponível nesta instalação.", 503)


@lru_cache
def _openai_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key)


def get_model_gateway(settings: Annotated[Settings, Depends(get_settings)]) -> ModelGateway:
    """Pick the gateway from configuration. There is no runtime fallback to the fake."""
    if settings.ai_gateway == "fake":
        if settings.environment == "production":
            raise _unavailable()
        return FakeModelGateway(FAKE_ANSWER)
    if settings.ai_gateway == "openai":
        api_key = settings.openai_api_key
        if api_key is None:  # settings validation already forbids this combination
            raise _unavailable()
        return OpenAIModelGateway(_openai_client(api_key.get_secret_value()))
    raise _unavailable()
