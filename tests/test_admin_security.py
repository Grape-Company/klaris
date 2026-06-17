import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_ingestion_requires_admin_api_key() -> None:
    original_key = settings.admin_api_key
    settings.admin_api_key = "test-admin-key"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/ingestion/runs")
    finally:
        settings.admin_api_key = original_key

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingestion_rejects_when_admin_api_key_is_not_configured() -> None:
    original_key = settings.admin_api_key
    settings.admin_api_key = ""
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/ingestion/runs")
    finally:
        settings.admin_api_key = original_key

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_rag_search_requires_admin_api_key() -> None:
    original_key = settings.admin_api_key
    settings.admin_api_key = "test-admin-key"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/rag/search",
                json={"query": "Shrine of Order", "top_k": 8},
            )
    finally:
        settings.admin_api_key = original_key

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_klaris_chat_requires_bot_or_admin_api_key() -> None:
    original_bot_key = settings.bot_api_key
    original_admin_key = settings.admin_api_key
    settings.bot_api_key = "test-bot-key"
    settings.admin_api_key = ""
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/klaris/chat",
                json={"message": "what is Shrine of Order?", "top_k": 8},
            )
    finally:
        settings.bot_api_key = original_bot_key
        settings.admin_api_key = original_admin_key

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wiki_suggest_rejects_empty_query_and_large_limit() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        empty_query_response = await client.get("/api/wiki/suggest", params={"query": ""})
        large_limit_response = await client.get(
            "/api/wiki/suggest",
            params={"query": "Shrine", "limit": 1000000},
        )

    assert empty_query_response.status_code == 422
    assert large_limit_response.status_code == 422
