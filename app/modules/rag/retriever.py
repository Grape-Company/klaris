from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.embedder import Embedder


class RetrievedChunk(TypedDict):
    id: UUID
    chunk_index: int
    heading: str | None
    content: str
    token_count: int | None
    page_title: str
    page_url: str
    score: float


class Retriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedder = Embedder()

    async def search(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        embedding = await self.embedder.embed_query(query)

        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        sql = text("""
            SELECT
                c.id,
                c.chunk_index,
                c.heading,
                c.content,
                c.token_count,
                p.title AS page_title,
                p.url AS page_url,
                1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM wiki_chunks c
            JOIN wiki_pages p ON p.id = c.page_id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = await self.session.execute(
            sql,
            {"embedding": embedding_str, "top_k": top_k},
        )

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "chunk_index": cast(int, row.chunk_index),
                "heading": cast(str | None, row.heading),
                "content": cast(str, row.content),
                "token_count": cast(int | None, row.token_count),
                "page_title": cast(str, row.page_title),
                "page_url": cast(str, row.page_url),
                "score": float(row.score),
            }
            for row in rows
        ]
