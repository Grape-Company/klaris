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
