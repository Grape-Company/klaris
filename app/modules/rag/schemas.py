from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_RAG_QUESTION_CHARS = 2000
MAX_RAG_TOP_K = 20
MAX_RAG_FEEDBACK_CORRECTION_CHARS = 4000


class RAGSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_RAG_QUESTION_CHARS)
    top_k: int = Field(default=8, ge=1, le=MAX_RAG_TOP_K)


class ChunkResult(BaseModel):
    id: UUID
    page_title: str
    heading: str | None
    content: str
    score: float


class RAGSearchResponse(BaseModel):
    results: list[ChunkResult]


class RAGAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_RAG_QUESTION_CHARS)
    top_k: int = Field(default=8, ge=1, le=MAX_RAG_TOP_K)


class SourceInfo(BaseModel):
    title: str
    url: str
    chunk_id: UUID


class RAGAskResponse(BaseModel):
    answer_id: UUID | None = None
    answer: str
    sources: list[SourceInfo]


class RAGFeedbackRequest(BaseModel):
    answer_id: UUID
    rating: Literal["positive", "negative"]
    correction: str | None = Field(
        default=None,
        max_length=MAX_RAG_FEEDBACK_CORRECTION_CHARS,
    )


class RAGFeedbackResponse(BaseModel):
    status: str
    answer_id: UUID
    rating: Literal["positive", "negative"]


class RAGImprovementStatsResponse(BaseModel):
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    correction_count: int
