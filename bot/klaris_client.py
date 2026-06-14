from typing import Any

import httpx


class KlarisApiClient:
    def __init__(self, api_url: str, timeout_seconds: float) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def ask(self, question: str, top_k: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.api_url}/api/klaris/ask",
                json={"question": question, "top_k": top_k},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected Klaris API response")
            return data

    async def chat(self, message: str, top_k: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.api_url}/api/klaris/chat",
                json={"message": message, "top_k": top_k},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected Klaris API response")
            return data
