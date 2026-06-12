import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.rag.service import truncate_answer


@pytest.mark.asyncio
async def test_rag_ask_rejects_invalid_top_k() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/rag/ask",
            json={"question": "what is Shrine of Order?", "top_k": 0},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rag_ask_rejects_question_that_is_too_long() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/rag/ask",
            json={"question": "x" * 2001, "top_k": 8},
        )

    assert response.status_code == 422


def test_truncate_answer_keeps_response_under_limit() -> None:
    answer = truncate_answer("x" * 2500, max_chars=100)

    assert len(answer) <= 100
    assert answer.endswith("[resposta truncada]")
