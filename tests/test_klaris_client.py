import httpx
import pytest

from bot.klaris_client import KlarisApiClient


@pytest.mark.asyncio
async def test_chat_sends_history_in_payload() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"response": "answer", "sources": []})

    client = KlarisApiClient(api_url="https://klaris.test")
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.api_url,
        transport=httpx.MockTransport(handler),
    )

    try:
        await client.chat(
            "what are its requirements?",
            8,
            history=[{"role": "user", "content": "what is Shrine of Order?"}],
        )
    finally:
        await client.close()

    assert requests[0].url.path == "/api/klaris/chat"
    assert requests[0].read() == (
        b'{"message":"what are its requirements?","top_k":8,'
        b'"history":[{"role":"user","content":"what is Shrine of Order?"}]}'
    )


@pytest.mark.asyncio
async def test_client_sends_bot_api_key_header() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"response": "answer", "sources": []})

    client = KlarisApiClient(api_url="https://klaris.test", bot_api_key="test-bot-key")
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.api_url,
        transport=httpx.MockTransport(handler),
        headers={"X-Bot-Api-Key": client.bot_api_key},
    )

    try:
        await client.chat("what is Shrine of Order?", 8)
    finally:
        await client.close()

    assert requests[0].headers["X-Bot-Api-Key"] == "test-bot-key"


@pytest.mark.asyncio
async def test_client_sends_admin_api_key_header_when_bot_key_is_absent() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"response": "answer", "sources": []})

    client = KlarisApiClient(
        api_url="https://klaris.test",
        admin_api_key="test-admin-key",
    )
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.api_url,
        transport=httpx.MockTransport(handler),
        headers=client.default_headers,
    )

    try:
        await client.chat("what is Shrine of Order?", 8)
    finally:
        await client.close()

    assert requests[0].headers["X-Admin-Api-Key"] == "test-admin-key"
