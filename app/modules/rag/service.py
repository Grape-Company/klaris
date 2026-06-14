import asyncio

from openai import APIError, APITimeoutError, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import RAGError
from app.modules.rag.answer_policy import disambiguation_answer
from app.modules.rag.prompt import build_rag_prompt
from app.modules.rag.query import answer_indicates_not_found, not_found_answer, small_talk_answer
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.schemas import (
    ChunkResult,
    RAGAskResponse,
    RAGSearchResponse,
    SourceInfo,
)
from app.modules.rag.source_selection import select_source_chunks

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
        if greeting_answer := small_talk_answer(question):
            return RAGAskResponse(answer=greeting_answer, sources=[])

        chunks = await self._search_with_timeout(question, top_k)

        if not chunks:
            return RAGAskResponse(
                answer=not_found_answer(question),
                sources=[],
            )

        if direct_answer := disambiguation_answer(question, chunks):
            return RAGAskResponse(
                answer=direct_answer.answer,
                sources=[
                    SourceInfo(
                        title=chunk["page_title"],
                        url=chunk["page_url"],
                        chunk_id=chunk["id"],
                    )
                    for chunk in direct_answer.source_chunks
                ],
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

        if answer_indicates_not_found(answer):
            return RAGAskResponse(answer=answer, sources=[])

        sources = []
        for chunk in select_source_chunks(chunks):
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
