from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import RAGError
from app.core.security import require_bot_or_admin
from app.modules.klaris.agent import KlarisAgent
from app.modules.klaris.schemas import ChatRequest, KlarisResponse
from app.modules.rag.improvement import summarize_feedback
from app.modules.rag.repository import RAGImprovementRepository

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


@router.get("/stats", dependencies=[Depends(require_bot_or_admin)])
async def klaris_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    repo = RAGImprovementRepository(session)
    total_answers = await repo.count_answer_logs()
    summary = summarize_feedback(await repo.feedback_stats())
    return {
        "total_answers": total_answers,
        "total_feedback": summary.total_feedback,
        "positive_feedback": summary.positive_feedback,
        "negative_feedback": summary.negative_feedback,
        "correction_count": summary.correction_count,
    }
