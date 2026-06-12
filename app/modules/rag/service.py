import asyncio

from openai import APIError, APITimeoutError, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import RAGError
from app.modules.rag.prompt import build_rag_prompt
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.schemas import (
    ChunkResult,
    RAGAskResponse,
    RAGSearchResponse,
    SourceInfo,
)

TRUNCATION_SUFFIX = "\n\n[resposta truncada]"


def truncate_answer(answer: str, max_chars: int) -> str:
    if len(answer) <= max_chars:
        return answer

    if max_chars <= len(TRUNCATION_SUFFIX):
        return TRUNCATION_SUFFIX[:max_chars]

    return answer[: max_chars - len(TRUNCATION_SUFFIX)].rstrip() + TRUNCATION_SUFFIX


class RagService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.retriever = Retriever(session)
        self.llm_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def search(self, query: str, top_k: int = 8) -> RAGSearchResponse:
        results = await self._search_with_timeout(query, top_k)
        return RAGSearchResponse(
            results=[
                ChunkResult(
                    id=r["id"],
                    page_title=r["page_title"],
                    heading=r["heading"],
                    content=r["content"][:500],
                    score=r["score"],
                )
                for r in results
            ]
        )

    async def ask(self, question: str, top_k: int = 8) -> RAGAskResponse:
        chunks = await self._search_with_timeout(question, top_k)

        if not chunks:
            return RAGAskResponse(
                answer="não encontrei essa informação na base atual.",
                sources=[],
            )

        messages = build_rag_prompt(question, chunks)

        try:
            response = await asyncio.wait_for(
                self.llm_client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    temperature=settings.llm_temperature,
                    max_tokens=settings.rag_max_tokens,
                ),
                timeout=settings.rag_request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RAGError("RAG provider timeout") from exc
        except (APIError, APITimeoutError) as exc:
            raise RAGError("RAG provider unavailable") from exc

        answer = truncate_answer(
            response.choices[0].message.content or "",
            settings.rag_max_answer_chars,
        )

        seen = set()
        sources = []
        for chunk in chunks:
            key = (chunk["page_title"], chunk["page_url"])
            if key not in seen:
                seen.add(key)
                sources.append(
                    SourceInfo(
                        title=chunk["page_title"],
                        url=chunk["page_url"],
                        chunk_id=chunk["id"],
                    )
                )

        return RAGAskResponse(answer=answer, sources=sources)

    async def _search_with_timeout(self, query: str, top_k: int) -> list[RetrievedChunk]:
        try:
            return await asyncio.wait_for(
                self.retriever.search(query, top_k),
                timeout=settings.rag_request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RAGError("RAG retrieval timeout") from exc
        except APIError as exc:
            raise RAGError("Embedding provider unavailable") from exc
