#!/usr/bin/env python3
import asyncio
import sys

import structlog

from app.core.database import async_session_factory
from app.modules.ingestion.mediawiki_client import MediaWikiClient
from app.modules.ingestion.pipeline import IngestionPipeline

logger = structlog.get_logger()


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.ingest_category <category_name>")
        sys.exit(1)

    category = sys.argv[1]

    client = MediaWikiClient()
    members = await client.list_category_members(category)
    await client.close()

    logger.info("category_members_found", category=category, count=len(members))

    async with async_session_factory() as session:
        pipeline = IngestionPipeline(session)
        try:
            for member in members:
                title = member.get("title", "")
                if ":" in title:
                    continue
                logger.info("ingesting_page", title=title)
                try:
                    await pipeline.ingest_single_page(title)
                except Exception as e:
                    logger.error("ingestion_failed", title=title, error=str(e))
        finally:
            await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
