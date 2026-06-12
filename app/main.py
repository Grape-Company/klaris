from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import setup_logging
from app.modules.ingestion.router import router as ingestion_router
from app.modules.rag.router import router as rag_router
from app.modules.wiki.router import router as wiki_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield


app = FastAPI(
    title="Deepwoken RAG API",
    description="Deepwoken Knowledge Base with Retrieval-Augmented Generation",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(wiki_router)
app.include_router(ingestion_router)
app.include_router(rag_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
