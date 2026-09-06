from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any, Self, cast

import httpx2
import pytest
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseIncompleteEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
    ResponseUsage,
)
from openai.types.responses.response import IncompleteDetails

from app.assistant.dependencies import get_model_gateway
from app.assistant.fake_gateway import FakeModelGateway
from app.assistant.gateway import GatewayError, ModelEvent, ModelRequest, ModelUsage
from app.assistant.openai_gateway import OpenAIModelGateway
from app.config import Settings
from app.errors import AppError

API_KEY = "sk-test-super-secret-key"
INSTRUCTIONS = "Você é o assistente editorial do Entrelinhas."
MARKDOWN = "# Capítulo secreto\n\nO manuscrito inteiro do autor."
REQUEST = ModelRequest(
    instructions=INSTRUCTIONS, input=MARKDOWN, model="gpt-5-mini", max_output_tokens=800
)
USAGE = ResponseUsage.model_construct(input_tokens=120, output_tokens=45, total_tokens=165)


def _response(usage: ResponseUsage | None, incomplete_reason: str | None = None) -> Response:
    details = (
        IncompleteDetails.model_construct(reason=incomplete_reason) if incomplete_reason else None
    )
    return Response.model_construct(id="resp_123", usage=usage, incomplete_details=details)


def _created() -> ResponseStreamEvent:
    return ResponseCreatedEvent.model_construct(
        type="response.created", response=_response(None), sequence_number=0
    )


def _delta(text: str) -> ResponseStreamEvent:
    return ResponseTextDeltaEvent.model_construct(
        type="response.output_text.delta", delta=text, sequence_number=1
    )


def _completed(usage: ResponseUsage | None = USAGE) -> ResponseStreamEvent:
    return ResponseCompletedEvent.model_construct(
        type="response.completed", response=_response(usage), sequence_number=2
    )


class _FakeResponses:
    def __init__(
        self,
        events: Sequence[ResponseStreamEvent],
        *,
        error: APIError | None = None,
        error_on_create: bool = False,
    ) -> None:
        self._events = list(events)
        self._error = error
        self._error_on_create = error_on_create
        self.kwargs: dict[str, Any] | None = None
        self.stream: _FakeStream | None = None

    async def create(self, **kwargs: Any) -> _FakeStream:
        self.kwargs = kwargs
        if self._error is not None and self._error_on_create:
            raise self._error
        self.stream = _FakeStream(self._events, self._error)
        return self.stream


class _FakeStream:
    """Mirrors the SDK's AsyncStream surface: iterable, closeable, and a context manager."""

    def __init__(self, events: Sequence[ResponseStreamEvent], error: APIError | None) -> None:
        self._events = list(events)
        self._error = error
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        self.closed = True

    async def __aiter__(self) -> AsyncIterator[ResponseStreamEvent]:
        for event in self._events:
            yield event
        if self._error is not None:
            raise self._error


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses


def _gateway(
    events: Sequence[ResponseStreamEvent],
    *,
    error: APIError | None = None,
    error_on_create: bool = False,
) -> tuple[OpenAIModelGateway, _FakeResponses]:
    responses = _FakeResponses(events, error=error, error_on_create=error_on_create)
    client = _FakeClient(responses)
    return OpenAIModelGateway(cast(AsyncOpenAI, client)), responses


async def _drain(gateway: OpenAIModelGateway) -> list[ModelEvent]:
    return [event async for event in gateway.stream(REQUEST)]


async def test_request_carries_the_expected_parameters() -> None:
    gateway, responses = _gateway([_created(), _delta("olá"), _completed()])

    await _drain(gateway)

    assert responses.kwargs is not None
    kwargs = dict(responses.kwargs)
    timeout = kwargs.pop("timeout")
    assert kwargs == {
        "model": "gpt-5-mini",
        "instructions": INSTRUCTIONS,
        "input": MARKDOWN,
        "max_output_tokens": 800,
        "reasoning": {"effort": "low"},
        "stream": True,
        "store": False,
    }
    assert isinstance(timeout, float) and timeout > 0


async def test_sdk_events_become_domain_events_in_order() -> None:
    gateway, _ = _gateway([_created(), _delta("Olá"), _delta(" mundo"), _completed()])

    events = await _drain(gateway)

    assert [event.type for event in events] == ["started", "text_delta", "text_delta", "completed"]
    assert events[0].response_id == "resp_123"
    assert "".join(event.delta or "" for event in events) == "Olá mundo"
    assert all(type(event).__module__ == "app.assistant.gateway" for event in events)
    assert all(type(event.usage).__module__ == "app.assistant.gateway" for event in events[-1:])


async def test_usage_is_captured_exactly_once() -> None:
    gateway, _ = _gateway([_created(), _delta("a"), _completed()])

    events = await _drain(gateway)

    with_usage = [event for event in events if event.usage is not None]
    assert with_usage == [
        ModelEvent(
            type="completed",
            usage=ModelUsage(input_tokens=120, output_tokens=45, total_tokens=165),
        )
    ]


async def test_unknown_sdk_events_are_ignored() -> None:
    noise = cast(ResponseStreamEvent, ResponseCreatedEvent.model_construct(type="response.queued"))
    gateway, _ = _gateway([_created(), noise, _delta("a"), _completed()])

    assert [event.type for event in await _drain(gateway)] == ["started", "text_delta", "completed"]


@pytest.mark.parametrize(
    "events",
    [
        pytest.param([_delta("a"), _completed()], id="delta_before_created"),
        pytest.param([_created(), _created()], id="created_twice"),
        pytest.param([_created(), _completed(), _completed()], id="completed_twice"),
        pytest.param([_created(), _delta("a")], id="stream_ends_without_completed"),
        pytest.param([], id="empty_stream"),
    ],
)
async def test_out_of_order_streams_are_protocol_errors(
    events: Sequence[ResponseStreamEvent],
) -> None:
    gateway, _ = _gateway(events)

    with pytest.raises(GatewayError) as failure:
        await _drain(gateway)

    assert failure.value.code == "provider_protocol_error"


async def test_completed_without_usage_is_a_protocol_error() -> None:
    gateway, _ = _gateway([_created(), _delta("a"), _completed(usage=None)])

    with pytest.raises(GatewayError) as failure:
        await _drain(gateway)

    assert failure.value.code == "provider_protocol_error"


def _request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.openai.com/v1/responses")


def _http_response(status_code: int) -> httpx2.Response:
    return httpx2.Response(status_code, request=_request())


# The provider messages deliberately carry the key and the manuscript: nothing
# from them may reach the error the author sees.
LEAKY = f"{API_KEY} rejected while sending {MARKDOWN} / {INSTRUCTIONS}"


@pytest.mark.parametrize(
    ("error", "code"),
    [
        pytest.param(APITimeoutError(request=_request()), "provider_timeout", id="timeout"),
        pytest.param(
            RateLimitError(LEAKY, response=_http_response(429), body=None),
            "provider_rate_limited",
            id="rate_limit",
        ),
        pytest.param(
            APIConnectionError(message=LEAKY, request=_request()), "ai_unavailable", id="connection"
        ),
        pytest.param(
            APIStatusError(LEAKY, response=_http_response(503), body=None),
            "ai_unavailable",
            id="server_error",
        ),
        pytest.param(
            AuthenticationError(LEAKY, response=_http_response(401), body=None),
            "ai_unavailable",
            id="authentication",
        ),
    ],
)
@pytest.mark.parametrize("error_on_create", [True, False])
async def test_sdk_errors_map_to_safe_codes(
    error: APIError, code: str, error_on_create: bool
) -> None:
    events = [] if error_on_create else [_created(), _delta("parcial")]
    gateway, _ = _gateway(events, error=error, error_on_create=error_on_create)

    with pytest.raises(GatewayError) as failure:
        await _drain(gateway)

    assert failure.value.code == code
    assert failure.value.__cause__ is error


@pytest.mark.parametrize("error_on_create", [True, False])
async def test_errors_never_leak_the_key_the_prompt_or_the_markdown(error_on_create: bool) -> None:
    error = APIStatusError(LEAKY, response=_http_response(500), body={"prompt": MARKDOWN})
    events = [] if error_on_create else [_created(), _delta("parcial")]
    gateway, _ = _gateway(events, error=error, error_on_create=error_on_create)

    with pytest.raises(GatewayError) as failure:
        await _drain(gateway)

    for text in (str(failure.value), repr(failure.value), failure.value.code):
        for secret in (API_KEY, MARKDOWN, INSTRUCTIONS, LEAKY, "sk-"):
            assert secret not in text


def _settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://user:pass@localhost:5432/entrelinhas",
        "public_origin": "http://localhost:5173",
        "files_root": Path("/tmp/files"),
    }
    return Settings(**{**defaults, **overrides})


def test_disabled_gateway_reports_the_assistant_as_unavailable() -> None:
    with pytest.raises(AppError) as failure:
        get_model_gateway(_settings(ai_gateway="disabled"))

    assert failure.value.code == "ai_unavailable"
    assert failure.value.status_code == 503


@pytest.mark.parametrize("environment", ["test", "development"])
def test_fake_gateway_is_served_only_outside_production(environment: str) -> None:
    gateway = get_model_gateway(_settings(environment=environment, ai_gateway="fake"))

    assert isinstance(gateway, FakeModelGateway)


def test_fake_gateway_is_refused_in_production() -> None:
    with pytest.raises(AppError) as failure:
        get_model_gateway(
            _settings(environment="production", cookie_secure=True, ai_gateway="fake")
        )

    assert failure.value.code == "ai_unavailable"


def test_openai_gateway_is_built_from_the_configured_key() -> None:
    gateway = get_model_gateway(_settings(ai_gateway="openai", openai_api_key=API_KEY))

    assert isinstance(gateway, OpenAIModelGateway)


async def test_stopping_the_generation_closes_the_provider_stream() -> None:
    gateway, responses = _gateway([_created(), _delta("parcial"), _delta(" resto"), _completed()])

    # The author pressed stop: the consumer walks away after the first delta.
    generator = gateway.stream(REQUEST)
    seen = []
    async for event in generator:
        seen.append(event.type)
        if event.type == "text_delta":
            break
    await generator.aclose()

    assert seen == ["started", "text_delta"]
    assert responses.stream is not None
    assert responses.stream.closed is True


async def test_a_completed_stream_is_closed_too() -> None:
    gateway, responses = _gateway([_created(), _delta("olá"), _completed()])

    await _drain(gateway)

    assert responses.stream is not None
    assert responses.stream.closed is True


def _incomplete(reason: str | None = "max_output_tokens") -> ResponseStreamEvent:
    return ResponseIncompleteEvent.model_construct(
        type="response.incomplete", response=_response(USAGE, reason), sequence_number=2
    )


async def test_a_cut_answer_is_marked_truncated_with_the_provider_reason() -> None:
    gateway, _ = _gateway([_created(), _delta("metade"), _incomplete()])

    events = await _drain(gateway)

    assert [event.type for event in events] == ["started", "text_delta", "completed"]
    terminal = events[-1]
    assert terminal.truncated is True
    assert terminal.truncation_reason == "max_output_tokens"
    # The usage is final even when the text is not: those tokens were billed.
    assert terminal.usage == ModelUsage(input_tokens=120, output_tokens=45, total_tokens=165)


async def test_a_whole_answer_is_not_marked_truncated() -> None:
    gateway, _ = _gateway([_created(), _delta("inteira"), _completed()])

    terminal = (await _drain(gateway))[-1]

    assert terminal.truncated is False
    assert terminal.truncation_reason is None


async def test_a_missing_incomplete_reason_still_yields_a_safe_token() -> None:
    gateway, _ = _gateway([_created(), _delta("metade"), _incomplete(reason=None)])

    terminal = (await _drain(gateway))[-1]

    assert terminal.truncated is True
    assert terminal.truncation_reason == "unknown"
