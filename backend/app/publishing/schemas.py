from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas import ApiModel


class PublishResult(ApiModel):
    slug: str
    published_at: datetime
    cleanup_at: datetime


class PublicationStatusDto(ApiModel):
    slug: str
    state: Literal["published", "withdrawn"]
    published_at: datetime
    cleanup_at: datetime
    cleanup_cancelled_at: datetime | None = None
    cleanup_completed_at: datetime | None = None


class FeaturedSelectionRequest(ApiModel):
    slug: str = Field(min_length=1, max_length=250)
