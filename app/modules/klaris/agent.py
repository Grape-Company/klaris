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
from app.modules.rag.query import (
    answer_indicates_not_found,
    needs_knowledge_search,
    not_found_answer,
    small_talk_answer,
)
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.source_selection import filter_evidence_chunks, select_source_chunks

TRUNCATION_SUFFIX = "\n\n[resposta truncada]"
ASK_SEARCH_QUERY_SYSTEM_PROMPT = """You rewrite Deepwoken questions into search queries.

Return only one concise English search query for the Deepwoken Wiki archive.
Preserve canonical Deepwoken terms in English.
Translate non-English wording into likely English Deepwoken terminology.
Correct obvious spelling variants when a canonical term is likely.
If the intended term is uncertain, return the closest likely English term plus
the original important term.
Do not answer the question. Do not add explanations. Do not use quotes."""


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


def clean_rewritten_search_query(value: str, fallback: str) -> str:
    query = " ".join(value.split()).strip(" \"'`?.!,")
    prefixes = (
        "search query:",
        "query:",
        "english query:",
        "did you mean:",
        "you mean:",
    )
    lowered = query.casefold()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            query = query[len(prefix) :].strip(" \"'`?.!,")
            lowered = query.casefold()
            break
    return query or fallback


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
            messages.append(
                {
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
                }
            )

            for tool_call in assistant_message.tool_calls:
                try:
                    result: ToolResult = await execute_tool_call(tool_call, self.retriever, top_k)
                except RAGError as exc:
                    result = ToolResult(
                        formatted=f"[Error searching archive: {exc}]",
                        raw_chunks=[],
                    )

                all_chunks.extend(result.raw_chunks)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.formatted,
                    }
                )

            response = await self._chat_completion(messages)
            assistant_message = response.choices[0].message

        return assistant_message.content or ""

    async def _rewrite_question_for_search(self, question: str) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": ASK_SEARCH_QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        try:
            response = await self._chat_completion(messages, tool_choice="none")
        except RAGError:
            return question

        rewritten = response.choices[0].message.content or ""
        return clean_rewritten_search_query(rewritten, fallback=question)

    async def chat(self, message: str, top_k: int = 8) -> KlarisResponse:
        if greeting_answer := small_talk_answer(message):
            return KlarisResponse(response=greeting_answer, sources=[])

        if needs_knowledge_search(message):
            return await self.ask(message, top_k)

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": KLARIS_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        all_chunks: list[RetrievedChunk] = []

        response = await self._chat_completion(messages, tool_choice="none")
        answer = await self._run_tool_loop(response.choices[0].message, messages, all_chunks, top_k)

        answer = truncate_answer(answer, settings.rag_max_answer_chars)
        sources = collect_sources(all_chunks) if all_chunks else []

        return KlarisResponse(response=answer, sources=sources)

    async def ask(self, question: str, top_k: int = 8) -> KlarisResponse:
        search_query = await self._rewrite_question_for_search(question)
        try:
            chunks = await asyncio.wait_for(
                self.retriever.search(search_query, top_k),
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

        evidence_chunks = filter_evidence_chunks(chunks)
        selected_chunks = select_source_chunks(evidence_chunks)
        if not evidence_chunks or not selected_chunks:
            return KlarisResponse(
                response=not_found_answer(question),
                sources=[],
            )

        context = format_chunks_for_llm(evidence_chunks)

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": KLARIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"ARCHIVE RESULTS:\n{context}\n\n"
                    f"ORIGINAL QUESTION: {question}\n"
                    f"ENGLISH SEARCH QUERY USED: {search_query}\n\n"
                    "Using the archive results above, answer my question as yourself, Klaris."
                    " Answer in the original question's language. If the English search query "
                    "is a meaningful translation or correction of the user's terms, briefly "
                    "confirm that interpretation in the user's language before answering."
                ),
            },
        ]

        response = await self._chat_completion(messages, tool_choice="none")
        answer = response.choices[0].message.content or ""

        answer = truncate_answer(answer, settings.rag_max_answer_chars)
        if answer_indicates_not_found(answer):
            return KlarisResponse(response=answer, sources=[])

        sources = collect_sources(selected_chunks)

        return KlarisResponse(response=answer, sources=sources)
