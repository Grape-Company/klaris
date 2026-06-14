from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import RAGError
from app.modules.klaris.agent import KlarisAgent
from app.modules.klaris.schemas import AskRequest, ChatRequest, KlarisResponse

router = APIRouter(prefix="/api/klaris", tags=["klaris"])


@router.post("/chat", response_model=KlarisResponse)
async def chat_with_klaris(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> KlarisResponse:
    agent = KlarisAgent(session)
    try:
        return await agent.chat(request.message, request.top_k)
    except RAGError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask", response_model=KlarisResponse)
async def ask_klaris(
    request: AskRequest,
    session: AsyncSession = Depends(get_session),
) -> KlarisResponse:
    agent = KlarisAgent(session)
    try:
        return await agent.ask(request.question, request.top_k)
    except RAGError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
