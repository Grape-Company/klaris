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
