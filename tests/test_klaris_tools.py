from uuid import uuid4

import pytest

from app.modules.klaris.tools import execute_tool_call
from app.modules.rag.retriever import RetrievedChunk


class DummyFunction:
    def __init__(self, arguments: str) -> None:
        self.arguments = arguments
        self.name = "search_knowledge_base"


class DummyToolCall:
    def __init__(self, arguments: str) -> None:
        self.function = DummyFunction(arguments)


class DummyRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        self.calls.append((query, top_k))
        return [
            {
                "id": uuid4(),
                "chunk_index": 0,
                "heading": "Usage",
                "content": "Archive result.",
                "token_count": 2,
                "page_title": "Shrine of Order",
                "page_url": "https://example.test/wiki/Shrine_of_Order",
                "score": 0.9,
            }
        ]


@pytest.mark.asyncio
async def test_execute_tool_call_clamps_requested_top_k() -> None:
    retriever = DummyRetriever()

    result = await execute_tool_call(
        DummyToolCall('{"query": "Shrine of Order", "top_k": 999}'),
        retriever, 8
    )

    assert retriever.calls == [("Shrine of Order", 15)]
    assert "Shrine of Order" in result.formatted


@pytest.mark.asyncio
async def test_execute_tool_call_uses_default_for_invalid_json() -> None:
    retriever = DummyRetriever()

    result = await execute_tool_call(DummyToolCall("{invalid"), retriever, 6)

    assert retriever.calls == [("", 6)]
    assert "Archive result." in result.formatted
