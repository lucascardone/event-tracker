import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    job_name: str
    source: str | None = None
    metadata: dict[str, Any] | None = None


class FinishRequest(BaseModel):
    status: str = Field(..., pattern="^(success|failed)$")
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class EventResponse(BaseModel):
    id: uuid.UUID
    job_name: str
    source: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    metadata: dict[str, Any] | None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    total: int
    items: list[EventResponse]
