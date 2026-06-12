#!/usr/bin/env python3
import asyncio

import structlog
from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.ingestion.embedder import Embedder
from app.modules.wiki.models import WikiChunk

logger = structlog.get_logger()


async def main() -> None:
    embedder = Embedder()

    async with async_session_factory() as session:
        result = await session.execute(select(WikiChunk).where(WikiChunk.embedding.is_(None)))
        chunks = list(result.scalars().all())

        logger.info("rebuilding_embeddings", count=len(chunks))

        for chunk in chunks:
            embedding = await embedder.embed_text(chunk.content)
            chunk.embedding = embedding
            session.add(chunk)

        await session.commit()
        logger.info("embeddings_rebuilt", count=len(chunks))


if __name__ == "__main__":
    asyncio.run(main())
