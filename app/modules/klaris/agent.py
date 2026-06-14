import asyncio
from collections.abc import Sequence
from typing import Any

from openai import APIError, APITimeoutError, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import RAGError
from app.modules.klaris.prompt import KLARIS_SYSTEM_PROMPT
from app.modules.klaris.schemas import KlarisResponse, SourceInfo
from app.modules.klaris.tools import (
    TOOL_DEFINITIONS,
    ToolResult,
    execute_tool_call,
    format_chunks_for_llm,
)
from app.modules.rag.query import not_found_answer
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.source_selection import select_source_chunks

TRUNCATION_SUFFIX = "\n\n[resposta truncada]"


def truncate_answer(answer: str, max_chars: int) -> str:
    if len(answer) <= max_chars:
        return answer
    if max_chars <= len(TRUNCATION_SUFFIX):
        return TRUNCATION_SUFFIX[:max_chars]
    return answer[: max_chars - len(TRUNCATION_SUFFIX)].rstrip() + TRUNCATION_SUFFIX


def collect_sources(raw_chunks: Sequence[RetrievedChunk]) -> list[SourceInfo]:
    selected = select_source_chunks(list(raw_chunks))
    return [
        SourceInfo(
            title=chunk["page_title"],
            url=chunk["page_url"],
            chunk_id=chunk["id"],
        )
        for chunk in selected
    ]


class KlarisAgent:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.retriever = Retriever(session)
        self.llm_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def _chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        tool_choice: str = "auto",
    ) -> ChatCompletion:
        try:
            return await asyncio.wait_for(
                self.llm_client.chat.completions.create(
                    model=settings.llm_model,  # type: ignore[call-overload]
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice=tool_choice,
                    temperature=settings.llm_temperature,
                    max_tokens=settings.rag_max_tokens,
                ),
                timeout=settings.rag_request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RAGError("RAG provider timeout") from exc
        except (APIError, APITimeoutError) as exc:
            raise RAGError("RAG provider unavailable") from exc

    async def _run_tool_loop(
        self,
        assistant_message: Any,
        messages: list[ChatCompletionMessageParam],
        all_chunks: list[RetrievedChunk],
        top_k: int,
    ) -> str:
        while assistant_message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                        "type": "function",
                    }
                    for tc in assistant_message.tool_calls
                ],
            })

            for tool_call in assistant_message.tool_calls:
                try:
                    result: ToolResult = await execute_tool_call(
                        tool_call, self.retriever, top_k
                    )
                except RAGError as exc:
                    result = ToolResult(
                        formatted=f"[Error searching archive: {exc}]",
                        raw_chunks=[],
                    )

                all_chunks.extend(result.raw_chunks)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.formatted,
                })

            response = await self._chat_completion(messages)
            assistant_message = response.choices[0].message

        return assistant_message.content or ""

    async def chat(self, message: str, top_k: int = 8) -> KlarisResponse:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": KLARIS_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        all_chunks: list[RetrievedChunk] = []

        response = await self._chat_completion(messages)
        answer = await self._run_tool_loop(
            response.choices[0].message, messages, all_chunks, top_k
        )

        answer = truncate_answer(answer, settings.rag_max_answer_chars)
        sources = collect_sources(all_chunks) if all_chunks else []

        return KlarisResponse(response=answer, sources=sources)

    async def ask(self, question: str, top_k: int = 8) -> KlarisResponse:
        try:
            chunks = await asyncio.wait_for(
                self.retriever.search(question, top_k),
                timeout=settings.rag_request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RAGError("RAG retrieval timeout") from exc
        except APIError as exc:
            raise RAGError("Embedding provider unavailable") from exc

        if not chunks:
            return KlarisResponse(
                response=not_found_answer(question),
                sources=[],
            )

        context = format_chunks_for_llm(chunks)
        all_chunks: list[RetrievedChunk] = list(chunks)

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": KLARIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"ARCHIVE RESULTS:\n{context}\n\n"
                    f"QUESTION: {question}\n\n"
                    "Using the archive results above, answer my question as yourself, Klaris."
                ),
            },
        ]

        response = await self._chat_completion(messages)
        answer = await self._run_tool_loop(
            response.choices[0].message, messages, all_chunks, top_k
        )

        answer = truncate_answer(answer, settings.rag_max_answer_chars)
        sources = collect_sources(all_chunks)

        return KlarisResponse(response=answer, sources=sources)
