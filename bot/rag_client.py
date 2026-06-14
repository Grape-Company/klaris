from typing import Any

import httpx


class RagApiClient:
    def __init__(self, api_url: str, timeout_seconds: float) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def ask(self, question: str, top_k: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.api_url}/api/rag/ask",
                json={"question": question, "top_k": top_k},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected RAG API response")
            return data
