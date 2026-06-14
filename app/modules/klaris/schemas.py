from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)


class SourceInfo(BaseModel):
    title: str
    url: str
    chunk_id: UUID


class KlarisResponse(BaseModel):
    response: str
    sources: list[SourceInfo]
