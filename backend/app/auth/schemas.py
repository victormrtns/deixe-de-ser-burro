from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)


class CurrentAuthor(BaseModel):
    id: UUID
    email: str


class SessionAuthor(BaseModel):
    email: str


class AnonymousSession(BaseModel):
    state: Literal["anonymous"] = "anonymous"


class AuthenticatedSession(BaseModel):
    state: Literal["author"] = "author"
    author: SessionAuthor


SessionState = AnonymousSession | AuthenticatedSession
