from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.models import RAGAnswerFeedback, RAGAnswerLog


class RAGImprovementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_answer_log(
        self,
        *,
        question: str,
        answer: str,
        top_k: int,
        prompt_version: str,
        model: str,
        source_chunk_ids: list[str],
        retrieval_scores: list[dict[str, object]],
    ) -> RAGAnswerLog:
        answer_log = RAGAnswerLog(
            question=question,
            answer=answer,
            top_k=top_k,
            prompt_version=prompt_version,
            model=model,
            source_chunk_ids=source_chunk_ids,
            retrieval_scores=retrieval_scores,
        )
        self.session.add(answer_log)
        await self.session.commit()
        await self.session.refresh(answer_log)
        return answer_log

    async def get_answer_log(self, answer_id: UUID) -> RAGAnswerLog | None:
        result = await self.session.execute(
            select(RAGAnswerLog).where(RAGAnswerLog.id == answer_id)
        )
        return result.scalar_one_or_none()

    async def create_feedback(
        self,
        *,
        answer_id: UUID,
        rating: str,
        correction: str | None,
    ) -> RAGAnswerFeedback:
        feedback = RAGAnswerFeedback(
            answer_id=answer_id,
            rating=rating,
            correction=correction,
        )
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)
        return feedback

    async def count_answer_logs(self) -> int:
        result = await self.session.execute(select(RAGAnswerLog))
        return len(result.scalars().all())

    async def feedback_stats(self) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(
                RAGAnswerFeedback.rating,
                RAGAnswerFeedback.correction,
            )
        )

        return [{"rating": row.rating, "correction": row.correction} for row in result]
