from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_admin
from app.modules.ingestion.schemas import (
    IngestionCategoryRequest,
    IngestionCategoryResponse,
    IngestionPageResponse,
    IngestionRunRequest,
    IngestionRunResponse,
)
from app.modules.ingestion.service import IngestionService

router = APIRouter(
    prefix="/api/ingestion",
    tags=["ingestion"],
    dependencies=[Depends(require_admin)],
)


@router.post("/run", response_model=IngestionRunResponse)
async def run_ingestion(
    request: IngestionRunRequest = IngestionRunRequest(),
    session: AsyncSession = Depends(get_session),
) -> IngestionRunResponse:
    service = IngestionService(session)
    return await service.run(namespace=request.namespace, limit=request.limit)


@router.post("/pages/{title}", response_model=IngestionPageResponse)
async def ingest_page(
    title: str,
    session: AsyncSession = Depends(get_session),
) -> IngestionPageResponse:
    service = IngestionService(session)
    response = await service.ingest_page(title)
    if response is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return response


@router.post("/category/{category}", response_model=IngestionCategoryResponse)
async def ingest_category(
    category: str,
    request: IngestionCategoryRequest = IngestionCategoryRequest(),
    session: AsyncSession = Depends(get_session),
) -> IngestionCategoryResponse:
    service = IngestionService(session)
    return await service.ingest_category(category, request.limit)


@router.get("/runs", response_model=list[IngestionRunResponse])
async def list_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[IngestionRunResponse]:
    service = IngestionService(session)
    return await service.list_runs(limit)


@router.get("/runs/{run_id}", response_model=IngestionRunResponse)
async def get_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> IngestionRunResponse:
    service = IngestionService(session)
    response = await service.get_run(run_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return response
