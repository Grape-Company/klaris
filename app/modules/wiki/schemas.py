from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WikiPageResponse(BaseModel):
    id: UUID
    title: str
    url: str
    namespace: int
    page_id: int | None
    content_hash: str
    last_ingested_at: datetime
    created_at: datetime
    updated_at: datetime


class WikiPageDetail(WikiPageResponse):
    clean_text: str | None


class WikiCategoryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class WikiSearchResult(BaseModel):
    id: UUID
    title: str
    url: str
    snippet: str


class WikiSearchResults(BaseModel):
    results: list[WikiSearchResult]
    total: int
