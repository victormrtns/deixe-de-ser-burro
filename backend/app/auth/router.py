from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    AnonymousSession,
    AuthenticatedSession,
    CurrentAuthor,
    LoginRequest,
    SessionAuthor,
    SessionState,
)
from app.auth.service import (
    authenticate,
    normalize_email,
    optional_author,
    revoke_author_session,
)
from app.config import Settings, get_settings
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/session", response_model=AuthenticatedSession)
async def create_session(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedSession:
    issued = await authenticate(
        session,
        payload.email,
        payload.password.get_secret_value(),
        timedelta(hours=settings.session_ttl_hours),
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.token,
        max_age=settings.session_ttl_hours * 60 * 60,
        expires=issued.expires_at,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return AuthenticatedSession(author=SessionAuthor(email=normalize_email(payload.email)))


@router.get("/session", response_model=SessionState)
async def read_session(
    author: Annotated[CurrentAuthor | None, Depends(optional_author)],
) -> SessionState:
    if author is None:
        return AnonymousSession()
    return AuthenticatedSession(author=SessionAuthor(email=author.email))


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    await revoke_author_session(
        session,
        request.cookies.get(settings.session_cookie_name),
    )
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
