from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


async def app_error_handler(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, AppError):
        raise error

    request_id = getattr(request.state, "request_id", None)
    if not isinstance(request_id, str) or not request_id:
        request_id = str(uuid4())

    body: dict[str, Any] = {
        "code": error.code,
        "message": error.message,
        "requestId": request_id,
    }
    if error.details is not None:
        body["details"] = error.details

    return JSONResponse(status_code=error.status_code, content={"error": body})
