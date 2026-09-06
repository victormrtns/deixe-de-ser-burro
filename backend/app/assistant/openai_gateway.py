from __future__ import annotations

from collections.abc import AsyncIterator

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.assistant.gateway import GatewayError, ModelEvent, ModelRequest, ModelUsage

# The SDK default timeout is generous; a stalled provider must not hold an
# author's request open indefinitely.
REQUEST_TIMEOUT_SECONDS = 60.0

_MESSAGES = {
    "provider_timeout": "O assistente demorou demais para responder.",
    "provider_rate_limited": "O assistente está sobrecarregado no momento.",
    "ai_unavailable": "O assistente está indisponível no momento.",
    "provider_protocol_error": "O assistente devolveu uma resposta inválida.",
}


def _failure(code: str) -> GatewayError:
    """Build the error from a fixed code and message: no provider payload, no key, no content."""
    return GatewayError(code, _MESSAGES[code])


def _code_for(error: APIError) -> str:
    if isinstance(error, APITimeoutError):
        return "provider_timeout"
    if isinstance(error, RateLimitError):
        return "provider_rate_limited"
    # Connection failures, authentication failures and any other status error
    # are all the same thing to the author: the assistant is not answering.
    return "ai_unavailable"


class OpenAIModelGateway:
    """Responses API adapter. SDK types stop here; callers only see `ModelEvent`."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        started = False
        completed = False
        try:
            stream = await self._client.responses.create(
                model=request.model,
                instructions=request.instructions,
                input=request.input,
                max_output_tokens=request.max_output_tokens,
                store=False,
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            # Closing is deterministic: when the author stops the generation the
            # consumer drops this generator, and the provider connection is
            # released here instead of whenever the collector gets to it.
            async with stream:
                async for event in stream:
                    if event.type == "response.created":
                        if started:
                            raise _failure("provider_protocol_error")
                        started = True
                        yield ModelEvent(type="started", response_id=event.response.id)
                    elif event.type == "response.output_text.delta":
                        if not started or completed:
                            raise _failure("provider_protocol_error")
                        yield ModelEvent(type="text_delta", delta=event.delta)
                    elif event.type in ("response.completed", "response.incomplete"):
                        # `incomplete` means the answer was truncated (max_output_tokens);
                        # the usage is final either way, so it closes the stream too.
                        usage = event.response.usage
                        if not started or completed or usage is None:
                            raise _failure("provider_protocol_error")
                        completed = True
                        yield ModelEvent(
                            type="completed",
                            usage=ModelUsage(
                                input_tokens=usage.input_tokens,
                                output_tokens=usage.output_tokens,
                                total_tokens=usage.total_tokens,
                            ),
                        )
        except APIError as error:
            raise _failure(_code_for(error)) from error
        if not completed:
            raise _failure("provider_protocol_error")
