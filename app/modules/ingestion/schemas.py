from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IngestionRunResponse(BaseModel):
    id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    pages_found: int
    pages_ingested: int
    pages_failed: int
    error_message: str | None


class IngestionRunRequest(BaseModel):
    namespace: int = Field(default=0, ge=0)
    limit: int = Field(default=0, ge=0, le=10_000)


class IngestionCategoryRequest(BaseModel):
    limit: int = Field(default=0, ge=0, le=5_000)


class IngestionPageResponse(BaseModel):
    status: str
    title: str


class IngestionCategoryResponse(BaseModel):
    status: str
    category: str
    pages_found: int
    pages_ingested: int
    pages_failed: int
