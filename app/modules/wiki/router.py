from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.wiki.schemas import (
    WikiCategoryResponse,
    WikiPageDetail,
    WikiPageResponse,
    WikiSearchResults,
)
from app.modules.wiki.service import WikiService

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/pages", response_model=list[WikiPageResponse])
async def list_pages(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[WikiPageResponse]:
    service = WikiService(session)
    return await service.list_pages(skip, limit)


@router.get("/pages/{page_id}", response_model=WikiPageDetail)
async def get_page(page_id: UUID, session: AsyncSession = Depends(get_session)) -> WikiPageDetail:
    service = WikiService(session)
    page = await service.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.get("/search", response_model=WikiSearchResults)
async def search_pages(
    query: str,
    session: AsyncSession = Depends(get_session),
) -> WikiSearchResults:
    service = WikiService(session)
    return await service.search(query)


@router.get("/categories", response_model=list[WikiCategoryResponse])
async def list_categories(
    session: AsyncSession = Depends(get_session),
) -> list[WikiCategoryResponse]:
    service = WikiService(session)
    return await service.list_categories()


@router.get("/categories/{name}/pages", response_model=list[WikiPageResponse])
async def get_category_pages(
    name: str,
    session: AsyncSession = Depends(get_session),
) -> list[WikiPageResponse]:
    service = WikiService(session)
    return await service.get_pages_by_category(name)
