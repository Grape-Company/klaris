from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wiki.repository import WikiRepository
from app.modules.wiki.schemas import (
    WikiCategoryResponse,
    WikiPageDetail,
    WikiPageResponse,
    WikiSearchResult,
    WikiSearchResults,
)


class WikiService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = WikiRepository(session)

    async def get_page(self, page_id: UUID) -> WikiPageDetail | None:
        page = await self.repo.get_page_by_id(page_id)
        if page is None:
            return None
        return WikiPageDetail(
            id=page.id,
            title=page.title,
            url=page.url,
            namespace=page.namespace,
            page_id=page.page_id,
            content_hash=page.content_hash,
            last_ingested_at=page.last_ingested_at,
            created_at=page.created_at,
            updated_at=page.updated_at,
            clean_text=page.clean_text,
        )

    async def list_pages(self, skip: int = 0, limit: int = 100) -> list[WikiPageResponse]:
        pages = await self.repo.list_pages(skip, limit)
        return [
            WikiPageResponse(
                id=p.id,
                title=p.title,
                url=p.url,
                namespace=p.namespace,
                page_id=p.page_id,
                content_hash=p.content_hash,
                last_ingested_at=p.last_ingested_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in pages
        ]

    async def search(self, query: str) -> WikiSearchResults:
        pages = await self.repo.search_pages(query)
        results = [
            WikiSearchResult(
                id=p.id,
                title=p.title,
                url=p.url,
                snippet=(p.clean_text or "")[:200],
            )
            for p in pages
        ]
        return WikiSearchResults(results=results, total=len(results))

    async def list_categories(self) -> list[WikiCategoryResponse]:
        categories = await self.repo.list_categories()
        return [
            WikiCategoryResponse(
                id=c.id,
                name=c.name,
                created_at=c.created_at,
            )
            for c in categories
        ]

    async def get_pages_by_category(self, category_name: str) -> list[WikiPageResponse]:
        pages = await self.repo.get_pages_by_category(category_name)
        return [
            WikiPageResponse(
                id=p.id,
                title=p.title,
                url=p.url,
                namespace=p.namespace,
                page_id=p.page_id,
                content_hash=p.content_hash,
                last_ingested_at=p.last_ingested_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in pages
        ]
