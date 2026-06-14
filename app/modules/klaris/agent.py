import asyncio
import json
import re
from collections.abc import Sequence
from typing import Any

import structlog
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
    not_found_answer,
    small_talk_answer,
)
from app.modules.rag.retriever import RetrievedChunk, Retriever
from app.modules.rag.source_selection import filter_evidence_chunks, select_source_chunks

TRUNCATION_SUFFIX = "\n\n[resposta truncada]"
MAX_TOOL_CALL_ROUNDS = 3
logger = structlog.get_logger()
ASK_SEARCH_QUERY_SYSTEM_PROMPT = """You rewrite Deepwoken questions into search queries.

Return only one concise English search query for the Deepwoken Wiki archive.
Preserve canonical Deepwoken terms in English.
Translate non-English wording into likely English Deepwoken terminology.
Correct obvious spelling variants when a canonical term is likely.
If the intended term is uncertain, return the closest likely English term plus
the original important term.
Do not answer the question. Do not add explanations. Do not use quotes."""
STRICT_SEARCH_QUERY_SYSTEM_PROMPT = """You fix failed Deepwoken Wiki search queries.

Return only one concise English search query using likely canonical Deepwoken
Wiki terminology. Translate any non-English words into English game/wiki terms.
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
    extracted_query = extract_text_tool_query(value)
    if extracted_query:
        return extracted_query

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


def extract_text_tool_query(value: str) -> str | None:
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        payload = json.loads(value[start : end + 1])
    except json.JSONDecodeError:
        return None

    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, str):
        return None

    cleaned = " ".join(query.split()).strip(" \"'`?.!,")
    return cleaned or None


def looks_like_text_tool_call(value: str) -> bool:
    normalized = " ".join(value.casefold().split())
    if not normalized:
        return False

    tool_markers = (
        "we need to call search tool",
        "call search tool",
        "search_knowledge_base",
        '"query"',
    )
    search_markers = ("search tool", "search_knowledge_base", '"query"')
    return (
        any(marker in normalized for marker in tool_markers)
        and any(marker in normalized for marker in search_markers)
        and ("{" in value or "tool" in normalized)
    )


def should_retry_search_rewrite(original_question: str, rewritten_query: str) -> bool:
    original_tokens = _meaningful_tokens(original_question)
    rewritten_tokens = _meaningful_tokens(rewritten_query)
    if not original_tokens or not rewritten_tokens:
        return False

    original_has_translation_signal = (
        any(not char.isascii() for char in original_question)
        or "¿" in original_question
        or "¡" in original_question
    )
    if not original_has_translation_signal:
        return False

    overlap = len(rewritten_tokens.intersection(original_tokens)) / len(rewritten_tokens)
    return overlap >= 0.6


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-zÀ-ÿ']+", value)
        if len(token) > 2
    }


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
            kwargs: dict[str, Any] = {
                "model": settings.llm_model,
                "messages": messages,
                "temperature": settings.llm_temperature,
                "max_tokens": settings.rag_max_tokens,
            }
            if tool_choice != "none":
                kwargs["tools"] = TOOL_DEFINITIONS
                kwargs["tool_choice"] = tool_choice

            return await asyncio.wait_for(
                self.llm_client.chat.completions.create(**kwargs),
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
        rounds = 0
        while getattr(assistant_message, "tool_calls", None):
            rounds += 1
            if rounds > MAX_TOOL_CALL_ROUNDS:
                return ""

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

    async def _rewrite_search_query(self, messages: list[ChatCompletionMessageParam]) -> str:
        response = await self._chat_completion(messages, tool_choice="none")
        rewritten = response.choices[0].message.content or ""
        return clean_rewritten_search_query(rewritten, fallback="")

    async def _rewrite_question_for_search(self, question: str) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": ASK_SEARCH_QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        try:
            search_query = await self._rewrite_search_query(messages)
        except RAGError:
            return question

        search_query = search_query or question
        if not should_retry_search_rewrite(question, search_query):
            return search_query

        strict_messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": STRICT_SEARCH_QUERY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original user question:\n{question}\n\n"
                    f"Previous search query that may not be canonical English:\n{search_query}"
                ),
            },
        ]
        try:
            strict_query = await self._rewrite_search_query(strict_messages)
        except RAGError:
            return search_query

        logger.info(
            "klaris_search_query_canonicalized",
            first_query=search_query,
            strict_query=strict_query,
        )
        return strict_query or search_query

    async def chat(self, message: str, top_k: int = 8) -> KlarisResponse:
        if greeting_answer := small_talk_answer(message):
            return KlarisResponse(response=greeting_answer, sources=[])

        return await self.ask(message, top_k)

    async def ask(self, question: str, top_k: int = 8) -> KlarisResponse:
        search_query = await self._rewrite_question_for_search(question)
        logger.info("klaris_search_started", search_query=search_query, top_k=top_k)
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
            logger.warning("klaris_search_no_chunks", search_query=search_query)
            return KlarisResponse(
                response=not_found_answer(question),
                sources=[],
            )

        top_chunk = chunks[0]
        logger.info(
            "klaris_search_completed",
            search_query=search_query,
            chunk_count=len(chunks),
            top_score=top_chunk["score"],
            top_title=top_chunk["page_title"],
        )

        evidence_chunks = filter_evidence_chunks(chunks)
        selected_chunks = select_source_chunks(evidence_chunks)
        if not evidence_chunks or not selected_chunks:
            logger.warning(
                "klaris_search_weak_evidence",
                search_query=search_query,
                chunk_count=len(chunks),
                top_score=top_chunk["score"],
                top_title=top_chunk["page_title"],
            )
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
        answer = (response.choices[0].message.content or "").strip()
        if looks_like_text_tool_call(answer):
            messages.extend(
                [
                    {"role": "assistant", "content": answer},
                    {
                        "role": "user",
                        "content": (
                            "Do not call, describe, or print tool calls. Use the ARCHIVE RESULTS "
                            "already provided above and answer the original question. If those "
                            "results do not answer it, use the required not-found sentence."
                        ),
                    },
                ]
            )
            response = await self._chat_completion(messages, tool_choice="none")
            answer = (response.choices[0].message.content or "").strip()

        answer = truncate_answer(answer, settings.rag_max_answer_chars)
        if not answer or looks_like_text_tool_call(answer):
            return KlarisResponse(response=not_found_answer(question), sources=[])

        if answer_indicates_not_found(answer):
            return KlarisResponse(response=answer, sources=[])

        sources = collect_sources(selected_chunks)

        return KlarisResponse(response=answer, sources=sources)
