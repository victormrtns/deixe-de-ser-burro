from __future__ import annotations

import pytest

from app.assistant.fake_gateway import FakeModelGateway
from app.assistant.gateway import GatewayError, ModelRequest, ModelUsage

REQUEST = ModelRequest(
    instructions="regras", input="pedido", model="fake-model", max_output_tokens=800
)


async def _drain(gateway: FakeModelGateway) -> list[str]:
    return [event.type async for event in gateway.stream(REQUEST)]


async def test_fake_gateway_emits_provider_neutral_sequence() -> None:
    gateway = FakeModelGateway(["Olá", " mundo"])

    events = [event async for event in gateway.stream(REQUEST)]

    assert [event.type for event in events] == ["started", "text_delta", "text_delta", "completed"]
    assert "".join(event.delta or "" for event in events) == "Olá mundo"
    assert events[0].response_id is not None
    assert events[-1].usage == ModelUsage(input_tokens=4, output_tokens=3, total_tokens=7)


async def test_fake_gateway_never_reveals_openai_types() -> None:
    events = [event async for event in FakeModelGateway(["a"]).stream(REQUEST)]

    assert all(type(event).__module__.startswith("app.assistant") for event in events)


@pytest.mark.parametrize("code", ["provider_timeout", "provider_rate_limited", "ai_unavailable"])
async def test_fake_gateway_can_fail_after_partial_content(code: str) -> None:
    gateway = FakeModelGateway(["parcial"], fail_with=code)

    seen: list[str] = []
    with pytest.raises(GatewayError) as failure:
        async for event in gateway.stream(REQUEST):
            seen.append(event.type)

    assert seen == ["started", "text_delta"]
    assert failure.value.code == code


async def test_fake_gateway_can_fail_before_any_content() -> None:
    gateway = FakeModelGateway([], fail_with="provider_rate_limited")

    with pytest.raises(GatewayError):
        await _drain(gateway)


async def test_fake_gateway_reports_an_invalid_provider_sequence() -> None:
    gateway = FakeModelGateway(["a"], fail_with="provider_protocol_error")

    with pytest.raises(GatewayError) as failure:
        await _drain(gateway)

    assert failure.value.code == "provider_protocol_error"
