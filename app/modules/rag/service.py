import asyncio
from typing import cast
from uuid import UUID

from openai import APIError, APITimeoutError, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import RAGError
from app.modules.rag.answer_policy import disambiguation_answer
from app.modules.rag.improvement import FeedbackRating
from app.modules.rag.prompt import RAG_PROMPT_VERSION, build_rag_prompt
from app.modules.rag.query import answer_indicates_not_found, not_found_answer, small_talk_answer
from app.modules.rag.repository import RAGImprovementRepository
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.schemas import (
    ChunkResult,
    RAGAskResponse,
    RAGFeedbackResponse,
    RAGImprovementStatsResponse,
    RAGSearchResponse,
    SourceInfo,
)
from app.modules.rag.source_selection import filter_evidence_chunks, select_source_chunks

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
        self.improvement_repo = RAGImprovementRepository(session)
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

        evidence_chunks = filter_evidence_chunks(chunks)
        selected_chunks = select_source_chunks(evidence_chunks)
        if not evidence_chunks or not selected_chunks:
            return RAGAskResponse(
                answer=not_found_answer(question),
                sources=[],
            )

        if direct_answer := disambiguation_answer(question, evidence_chunks):
            sources = [
                SourceInfo(
                    title=chunk["page_title"],
                    url=chunk["page_url"],
                    chunk_id=chunk["id"],
                )
                for chunk in direct_answer.source_chunks
            ]
            answer_id = await self._record_answer(
                question=question,
                answer=direct_answer.answer,
                top_k=top_k,
                source_chunk_ids=[str(source.chunk_id) for source in sources],
                chunks=chunks,
            )
            return RAGAskResponse(
                answer_id=answer_id,
                answer=direct_answer.answer,
                sources=sources,
            )

        messages = build_rag_prompt(question, evidence_chunks)

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
        for chunk in selected_chunks:
            sources.append(
                SourceInfo(
                    title=chunk["page_title"],
                    url=chunk["page_url"],
                    chunk_id=chunk["id"],
                )
            )

        answer_id = await self._record_answer(
            question=question,
            answer=answer,
            top_k=top_k,
            source_chunk_ids=[str(source.chunk_id) for source in sources],
            chunks=chunks,
        )

        return RAGAskResponse(answer_id=answer_id, answer=answer, sources=sources)

    async def record_feedback(
        self,
        *,
        answer_id: UUID,
        rating: FeedbackRating,
        correction: str | None,
    ) -> RAGFeedbackResponse | None:
        if await self.improvement_repo.get_answer_log(answer_id) is None:
            return None

        feedback = await self.improvement_repo.create_feedback(
            answer_id=answer_id,
            rating=rating,
            correction=correction,
        )
        return RAGFeedbackResponse(
            status="recorded",
            answer_id=feedback.answer_id,
            rating=cast(FeedbackRating, feedback.rating),
        )

    async def improvement_stats(self) -> RAGImprovementStatsResponse:
        summary = await self.improvement_repo.feedback_summary()
        return RAGImprovementStatsResponse(**summary)

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

    async def _record_answer(
        self,
        *,
        question: str,
        answer: str,
        top_k: int,
        source_chunk_ids: list[str],
        chunks: list[RetrievedChunk],
    ) -> UUID:
        answer_log = await self.improvement_repo.create_answer_log(
            question=question,
            answer=answer,
            top_k=top_k,
            prompt_version=RAG_PROMPT_VERSION,
            model=settings.llm_model,
            source_chunk_ids=source_chunk_ids,
            retrieval_scores=[
                {
                    "chunk_id": str(chunk["id"]),
                    "page_title": chunk["page_title"],
                    "score": chunk["score"],
                }
                for chunk in chunks
            ],
        )
        return answer_log.id
