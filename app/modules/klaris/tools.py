import json
from collections.abc import Sequence
from typing import Any, Protocol

from app.modules.rag.retriever import RetrievedChunk


class KnowledgeSearcher(Protocol):
    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        pass


SEARCH_TOOL_DEFINITION: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search your personal archive of Deepwoken knowledge for information "
            "about game mechanics, Oaths, Attunements, Mantras, Talents, items, "
            "locations, lore, bosses, or any Deepwoken-specific topic. "
            "Returns relevant passages from the Deepwoken Wiki with source pages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query describing what you are looking for. "
                        "Be specific to get better results."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (1-15)",
                    "minimum": 1,
                    "maximum": 15,
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_DEFINITIONS: list[dict[str, object]] = [SEARCH_TOOL_DEFINITION]


def format_chunks_for_llm(chunks: Sequence[RetrievedChunk]) -> str:
    parts: list[str] = []

    for i, chunk in enumerate(chunks):
        score = chunk["score"]
        header = f"[Result {i + 1}] (relevance: {score:.2f})"
        header += f"\nPage: {chunk['page_title']}"
        if chunk["heading"]:
            header += f" - Section: {chunk['heading']}"
        parts.append(f"{header}\n{chunk['content']}")

    if not parts:
        return "[No results found in the archive.]"

    return "\n\n---\n\n".join(parts)


class ToolResult:
    def __init__(
        self,
        formatted: str,
        raw_chunks: list[RetrievedChunk],
    ) -> None:
        self.formatted = formatted
        self.raw_chunks = raw_chunks


async def execute_search(
    query: str,
    retriever: KnowledgeSearcher,
    top_k: int = 8,
) -> ToolResult:
    chunks = await retriever.search(query, top_k)
    formatted = format_chunks_for_llm(chunks)
    return ToolResult(formatted=formatted, raw_chunks=chunks)


async def execute_tool_call(
    tool_call: Any,
    retriever: KnowledgeSearcher,
    top_k: int = 8,
) -> ToolResult:
    try:
        args = json.loads(tool_call.function.arguments)
    except (TypeError, json.JSONDecodeError):
        args = {}

    query = args.get("query", "")
    if not isinstance(query, str):
        query = ""

    call_top_k = args.get("top_k", top_k)
    if not isinstance(call_top_k, int):
        call_top_k = top_k
    call_top_k = min(max(call_top_k, 1), 15)

    return await execute_search(query, retriever, call_top_k)
