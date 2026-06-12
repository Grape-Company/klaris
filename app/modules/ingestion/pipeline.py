import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ingestion.chunker import chunk_page
from app.modules.ingestion.cleaner import clean_html, compute_content_hash
from app.modules.ingestion.embedder import Embedder
from app.modules.ingestion.mediawiki_client import MediaWikiClient
from app.modules.ingestion.repository import IngestionRepository
from app.modules.wiki.models import IngestionRun, WikiChunk, WikiPage
from app.modules.wiki.repository import WikiRepository

logger = structlog.get_logger()


class IngestionPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.wiki_repo = WikiRepository(session)
        self.ingestion_repo = IngestionRepository(session)
        self.client = MediaWikiClient()
        self.embedder = Embedder()

    async def run(self, namespace: int = 0, limit: int = 0) -> IngestionRun:
        run_id = uuid.uuid4()
        run = IngestionRun(
            id=run_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.session.add(run)
        await self.session.commit()

        try:
            pages = await self.client.list_all_pages(namespace=namespace)
            run.pages_found = len(pages)
            await self.session.commit()

            if limit > 0:
                pages = pages[:limit]

            pages_ingested = 0
            pages_failed = 0
            for page_info in pages:
                processed = await self._process_single_page(page_info)
                if processed is True:
                    pages_ingested += 1
                elif processed is False:
                    pages_failed += 1

            run = await self._get_run(run_id)
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.pages_ingested = pages_ingested
            run.pages_failed = pages_failed
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            run = await self._get_run(run_id)
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error_message = str(e)
            await self.session.commit()
            logger.error("ingestion_pipeline_failed", error=str(e))

        finally:
            await self.close()

        return run

    async def ingest_single_page(self, title: str) -> WikiPage | None:
        html = await self.client.get_page_html(title)
        if html is None:
            logger.warning("page_not_found", title=title)
            return None

        page_info = await self.client.get_page_info(title)
        page_id = page_info.get("pageid") if page_info else None
        url = f"{settings.mediawiki_api_url.replace('/api.php', '')}/wiki/{title.replace(' ', '_')}"

        clean_text = clean_html(html)
        content_hash = compute_content_hash(clean_text)

        existing = await self.wiki_repo.get_page_by_title(title)
        if existing and existing.content_hash == content_hash:
            logger.info("page_unchanged", title=title)
            return existing

        page = existing or WikiPage(id=uuid.uuid4())
        page.title = title
        page.url = url
        page.namespace = 0
        page.page_id = page_id
        page.raw_html = html
        page.clean_text = clean_text
        page.content_hash = content_hash
        page.last_ingested_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()

        if existing:
            page = await self.wiki_repo.upsert_page(page)
        else:
            self.session.add(page)

        await self.session.flush()

        await self._reprocess_chunks(page, clean_text)
        await self.session.commit()

        return page

    async def _process_single_page(self, page_info: dict[str, Any]) -> bool | None:
        title = page_info.get("title", "")
        if not title or ":" in title:
            return None

        try:
            await self.ingest_single_page(title)
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error("page_ingestion_failed", title=title, error=str(e))
            return False

    async def _reprocess_chunks(self, page: WikiPage, clean_text: str) -> None:
        chunks = chunk_page(page.title, clean_text)

        existing_chunks = await self.ingestion_repo.get_chunks_by_page(page.id)
        for ec in existing_chunks:
            await self.session.delete(ec)

        if not chunks:
            logger.info("chunks_reprocessed", page=page.title, count=0)
            return

        embeddings = await self.embedder.embed_texts([chunk.content for chunk in chunks])

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            db_chunk = WikiChunk(
                id=uuid.uuid4(),
                page_id=page.id,
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embedding,
                created_at=datetime.utcnow(),
            )
            self.session.add(db_chunk)

        logger.info("chunks_reprocessed", page=page.title, count=len(chunks))

    async def close(self) -> None:
        await self.client.close()

    async def _get_run(self, run_id: uuid.UUID) -> IngestionRun:
        run = await self.session.get(IngestionRun, run_id)
        if run is None:
            raise RuntimeError(f"Ingestion run not found: {run_id}")
        return run
