from uuid import UUID

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=20)

    def history_as_dicts(self) -> list[dict[str, str]]:
        return [turn.model_dump() for turn in self.history]


class SourceInfo(BaseModel):
    title: str
    url: str
    chunk_id: UUID


class KlarisResponse(BaseModel):
    answer_id: UUID | None = None
    response: str
    sources: list[SourceInfo]
