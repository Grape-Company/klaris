from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.mediawiki_client import MediaWikiClient
from app.modules.ingestion.pipeline import IngestionPipeline
from app.modules.ingestion.repository import IngestionRepository
from app.modules.ingestion.schemas import (
    IngestionCategoryResponse,
    IngestionPageResponse,
    IngestionRunResponse,
)

logger = structlog.get_logger()


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IngestionRepository(session)

    async def run(self, namespace: int = 0, limit: int = 0) -> IngestionRunResponse:
        pipeline = IngestionPipeline(self.session)
        run = await pipeline.run(namespace=namespace, limit=limit)
        return self._run_response(run)

    async def ingest_page(self, title: str) -> IngestionPageResponse | None:
        pipeline = IngestionPipeline(self.session)
        page = await pipeline.ingest_single_page(title)
        if page is None:
            return None
        return IngestionPageResponse(status="ok", title=page.title)

    async def ingest_category(
        self,
        category: str,
        limit: int = 0,
    ) -> IngestionCategoryResponse:
        client = MediaWikiClient()
        try:
            members = await client.list_category_members(category)
        finally:
            await client.close()

        if limit > 0:
            members = members[:limit]

        pipeline = IngestionPipeline(self.session)
        pages_ingested = 0
        pages_failed = 0

        for member in members:
            title = member.get("title", "")
            if not title or ":" in title:
                continue
            try:
                page = await pipeline.ingest_single_page(title)
                if page is not None:
                    pages_ingested += 1
            except Exception as exc:
                pages_failed += 1
                logger.error("category_page_ingestion_failed", title=title, error=str(exc))

        await pipeline.close()

        return IngestionCategoryResponse(
            status="completed",
            category=category,
            pages_found=len(members),
            pages_ingested=pages_ingested,
            pages_failed=pages_failed,
        )

    async def list_runs(self, limit: int = 20) -> list[IngestionRunResponse]:
        runs = await self.repo.list_runs(limit)
        return [self._run_response(run) for run in runs]

    async def get_run(self, run_id: UUID) -> IngestionRunResponse | None:
        run = await self.repo.get_run(run_id)
        if run is None:
            return None
        return self._run_response(run)

    def _run_response(self, run: object) -> IngestionRunResponse:
        return IngestionRunResponse.model_validate(run, from_attributes=True)
