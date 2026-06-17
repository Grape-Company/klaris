from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class KlarisApiClient:
    def __init__(
        self,
        api_url: str,
        timeout_seconds: float = 30.0,
        bot_api_key: str = "",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.bot_api_key = bot_api_key
        headers: dict[str, str] = {}
        if bot_api_key:
            headers["X-Bot-Api-Key"] = bot_api_key
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout_seconds,
            headers=headers,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def ask(self, question: str, top_k: int) -> dict[str, Any]:
        return await self.chat(question, top_k)

    async def chat(
        self,
        message: str,
        top_k: int,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, object] = {"message": message, "top_k": top_k}
        if history:
            payload["history"] = history

        response = await self._client.post(
            "/api/klaris/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected Klaris API response")
        return data

    async def stats(self) -> dict[str, int | str]:
        response = await self._client.get("/api/klaris/stats")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected stats response")
        return dict(data)

    async def submit_feedback(
        self,
        answer_id: str,
        rating: str,
        correction: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, object] = {"answer_id": answer_id, "rating": rating}
        if correction is not None:
            payload["correction"] = correction
        response = await self._client.post("/api/rag/feedback", json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected feedback response")
        return data
