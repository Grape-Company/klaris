from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import RAGError
from app.core.security import require_admin
from app.modules.rag.schemas import (
    RAGFeedbackRequest,
    RAGFeedbackResponse,
    RAGImprovementStatsResponse,
    RAGSearchRequest,
    RAGSearchResponse,
)
from app.modules.rag.service import RagService

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    dependencies=[Depends(require_admin)],
)
async def search_chunks(
    request: RAGSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> RAGSearchResponse:
    service = RagService(session)
    try:
        return await service.search(request.query, request.top_k)
    except RAGError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/feedback",
    response_model=RAGFeedbackResponse,
    dependencies=[Depends(require_admin)],
)
async def record_feedback(
    request: RAGFeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> RAGFeedbackResponse:
    service = RagService(session)
    response = await service.record_feedback(
        answer_id=request.answer_id,
        rating=request.rating,
        correction=request.correction,
    )
    if response is None:
        raise HTTPException(status_code=404, detail="Answer log not found")
    return response


@router.get(
    "/improvement/stats",
    response_model=RAGImprovementStatsResponse,
    dependencies=[Depends(require_admin)],
)
async def improvement_stats(
    session: AsyncSession = Depends(get_session),
) -> RAGImprovementStatsResponse:
    service = RagService(session)
    return await service.improvement_stats()
