from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.wiki.models import WikiCategory, WikiPage, WikiPageCategory


class WikiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_page_by_id(self, page_id: UUID) -> WikiPage | None:
        result = await self.session.execute(select(WikiPage).where(WikiPage.id == page_id))
        return result.scalar_one_or_none()

    async def get_page_by_title(self, title: str) -> WikiPage | None:
        result = await self.session.execute(select(WikiPage).where(WikiPage.title == title))
        return result.scalar_one_or_none()

    async def list_pages(self, skip: int = 0, limit: int = 100) -> list[WikiPage]:
        result = await self.session.execute(
            select(WikiPage).offset(skip).limit(limit).order_by(WikiPage.title)
        )
        return list(result.scalars().all())

    async def suggest_titles(self, query: str, limit: int = 10) -> list[WikiPage]:
        result = await self.session.execute(
            select(WikiPage)
            .where(WikiPage.title.ilike(f"%{query}%"))
            .limit(limit)
            .order_by(WikiPage.title)
        )
        return list(result.scalars().all())

    async def search_pages(self, query: str, limit: int = 20) -> list[WikiPage]:
        result = await self.session.execute(
            select(WikiPage)
            .where(WikiPage.title.ilike(f"%{query}%"))
            .limit(limit)
            .order_by(WikiPage.title)
        )
        return list(result.scalars().all())

    async def upsert_page(self, page: WikiPage) -> WikiPage:
        return await self.session.merge(page)

    async def list_categories(self) -> list[WikiCategory]:
        result = await self.session.execute(select(WikiCategory).order_by(WikiCategory.name))
        return list(result.scalars().all())

    async def get_category_by_name(self, name: str) -> WikiCategory | None:
        result = await self.session.execute(select(WikiCategory).where(WikiCategory.name == name))
        return result.scalar_one_or_none()

    async def get_pages_by_category(self, category_name: str) -> list[WikiPage]:
        result = await self.session.execute(
            select(WikiPage)
            .join(WikiPageCategory)
            .join(WikiCategory)
            .where(WikiCategory.name == category_name)
            .options(selectinload(WikiPage.categories))
        )
        return list(result.scalars().all())
