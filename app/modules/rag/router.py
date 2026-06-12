from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import RAGError
from app.modules.rag.schemas import (
    RAGAskRequest,
    RAGAskResponse,
    RAGSearchRequest,
    RAGSearchResponse,
)
from app.modules.rag.service import RagService

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=RAGSearchResponse)
async def search_chunks(
    request: RAGSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> RAGSearchResponse:
    service = RagService(session)
    try:
        return await service.search(request.query, request.top_k)
    except RAGError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask", response_model=RAGAskResponse)
async def ask_question(
    request: RAGAskRequest,
    session: AsyncSession = Depends(get_session),
) -> RAGAskResponse:
    service = RagService(session)
    try:
        return await service.ask(request.question, request.top_k)
    except RAGError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
