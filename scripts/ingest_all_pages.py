#!/usr/bin/env python3
import asyncio
import sys

from app.core.database import async_session_factory
from app.modules.ingestion.pipeline import IngestionPipeline


async def main() -> None:
    namespace = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    async with async_session_factory() as session:
        pipeline = IngestionPipeline(session)
        run = await pipeline.run(namespace=namespace, limit=limit)

        print(f"Run {run.id}: {run.status}")
        print(f"  Found: {run.pages_found}")
        print(f"  Ingested: {run.pages_ingested}")
        print(f"  Failed: {run.pages_failed}")
        if run.error_message:
            print(f"  Error: {run.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
