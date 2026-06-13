from typing import Any, TypedDict, cast
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


def merge_ranked_chunks(
    keyword_chunks: list[RetrievedChunk],
    vector_chunks: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    merged: list[RetrievedChunk] = []
    seen: set[UUID] = set()

    for chunk in [*keyword_chunks, *vector_chunks]:
        if chunk["id"] in seen:
            continue
        merged.append(chunk)
        seen.add(chunk["id"])
        if len(merged) >= top_k:
            break

    return merged


class Retriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedder = Embedder()

    async def search(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        keyword_chunks = await self._keyword_search(query, top_k)
        vector_chunks = await self._vector_search(query, top_k)

        return merge_ranked_chunks(keyword_chunks, vector_chunks, top_k)

    async def _keyword_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        pattern = f"%{query}%"
        sql = text("""
            SELECT
                c.id,
                c.chunk_index,
                c.heading,
                c.content,
                c.token_count,
                p.title AS page_title,
                p.url AS page_url,
                CASE
                    WHEN lower(p.title) = lower(:query) THEN 1.0
                    WHEN lower(p.title) LIKE lower(:pattern) THEN 0.98
                    WHEN lower(c.content) LIKE lower(:pattern) THEN 0.92
                    ELSE 0.0
                END AS score
            FROM wiki_chunks c
            JOIN wiki_pages p ON p.id = c.page_id
            WHERE
                lower(p.title) LIKE lower(:pattern)
                OR lower(c.content) LIKE lower(:pattern)
            ORDER BY score DESC, p.title ASC, c.chunk_index ASC
            LIMIT :top_k
        """)

        result = await self.session.execute(
            sql,
            {"query": query, "pattern": pattern, "top_k": top_k},
        )

        rows = result.fetchall()
        return [self._row_to_chunk(row) for row in rows]

    async def _vector_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
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
        return [self._row_to_chunk(row) for row in rows]

    def _row_to_chunk(self, row: Any) -> RetrievedChunk:
        return {
            "id": row.id,
            "chunk_index": cast(int, row.chunk_index),
            "heading": cast(str | None, row.heading),
            "content": cast(str, row.content),
            "token_count": cast(int | None, row.token_count),
            "page_title": cast(str, row.page_title),
            "page_url": cast(str, row.page_url),
            "score": float(row.score),
        }
