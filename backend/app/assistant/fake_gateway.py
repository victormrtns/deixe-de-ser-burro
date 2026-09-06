from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from uuid import uuid4

from app.assistant.gateway import GatewayError, ModelEvent, ModelRequest, ModelUsage

# A cheap, deterministic stand-in for the provider's tokenizer. It only has to
# be stable, since automated tests never spend money.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN) if text else 0


class FakeModelGateway:
    """Deterministic gateway used by every automated test: zero network, zero cost."""

    def __init__(
        self,
        chunks: Sequence[str],
        *,
        fail_with: str | None = None,
        truncated: bool = False,
    ) -> None:
        self._chunks = list(chunks)
        self._fail_with = fail_with
        self._truncated = truncated
        self.requests: list[ModelRequest] = []

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        self.requests.append(request)
        yield ModelEvent(type="started", response_id=f"fake_{uuid4().hex}")
        for chunk in self._chunks:
            yield ModelEvent(type="text_delta", delta=chunk)
        if self._fail_with is not None:
            raise GatewayError(self._fail_with)
        answer = "".join(self._chunks)
        input_tokens = estimate_tokens(request.instructions) + estimate_tokens(request.input)
        output_tokens = estimate_tokens(answer)
        yield ModelEvent(
            type="completed",
            usage=ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            truncated=self._truncated,
            truncation_reason="max_output_tokens" if self._truncated else None,
        )
