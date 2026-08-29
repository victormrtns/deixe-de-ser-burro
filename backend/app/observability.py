from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

SERVICE_NAME = "entrelinhas-api"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")

logger = structlog.get_logger(SERVICE_NAME)


def configure_logging(level: str | None = None) -> None:
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(resolved, logging.INFO)
        ),
        cache_logger_on_first_use=False,
    )


def resolve_request_id(incoming: str | None) -> str:
    if incoming is not None and _REQUEST_ID_PATTERN.fullmatch(incoming):
        return incoming
    return str(uuid4())


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Stamps a request ID and emits one JSON completion event per request.

    Only routing metadata is logged: headers, query values, bodies, and
    exception messages (which can carry SQL or private payloads) never do.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = resolve_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        # The middleware is the last defense: any escape becomes a stable
        # envelope and a typed log event instead of a leaked traceback.
        except Exception as error:  # noqa: BLE001
            self._log(request, request_id, status=500, started=started, failure=error)
            return self._internal_error_response(request_id)

        response.headers["X-Request-ID"] = request_id
        self._log(request, request_id, status=response.status_code, started=started)
        return response

    def _log(
        self,
        request: Request,
        request_id: str,
        *,
        status: int,
        started: float,
        failure: Exception | None = None,
    ) -> None:
        fields = {
            "service": SERVICE_NAME,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "request_id": request_id,
            "method": request.method,
            "route": self._route_template(request),
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        error_code = getattr(request.state, "error_code", None)
        if error_code is not None:
            fields["error_code"] = error_code
        if failure is None:
            logger.info("request_completed", **fields)
        else:
            logger.error("request_failed", failure_kind=type(failure).__name__, **fields)

    @staticmethod
    def _route_template(request: Request) -> str:
        route = request.scope.get("route")
        template = getattr(route, "path", None)
        return template if isinstance(template, str) else request.url.path

    @staticmethod
    def _internal_error_response(request_id: str) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Erro interno.",
                    "requestId": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )
