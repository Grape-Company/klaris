from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wiki.models import IngestionRun, WikiChunk


class IngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_run(self, run_id: UUID) -> IngestionRun | None:
        result = await self.session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        return result.scalar_one_or_none()

    async def list_runs(self, limit: int = 20) -> list[IngestionRun]:
        result = await self.session.execute(
            select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_chunks_by_page(self, page_id: UUID) -> list[WikiChunk]:
        result = await self.session.execute(select(WikiChunk).where(WikiChunk.page_id == page_id))
        return list(result.scalars().all())

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[WikiChunk]:
        result = await self.session.execute(select(WikiChunk).where(WikiChunk.id.in_(chunk_ids)))
        return list(result.scalars().all())
