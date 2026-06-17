from typing import Any
from uuid import uuid4

import pytest
from openai.types.chat import ChatCompletionMessageParam

from app.modules.klaris.agent import KlarisAgent
from app.modules.rag.retriever import RetrievedChunk, Retriever


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeRetriever(Retriever):
    def __init__(self, score: float = 0.98) -> None:
        self.calls: list[tuple[str, int]] = []
        self.score = score

    async def search(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        self.calls.append((query, top_k))
        return [
            {
                "id": uuid4(),
                "chunk_index": 0,
                "heading": "Usage",
                "content": "Shrine of Order averages invested points.",
                "token_count": 6,
                "page_title": "Deep Shrines/Shrine of Order",
                "page_url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
                "score": self.score,
            }
        ]


class QueryAwareFakeRetriever(Retriever):
    def __init__(self, chunks_by_query: dict[str, list[RetrievedChunk]]) -> None:
        self.calls: list[tuple[str, int]] = []
        self.chunks_by_query = chunks_by_query

    async def search(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        self.calls.append((query, top_k))
        return self.chunks_by_query.get(query, [])[:top_k]


class FakeKlarisAgent(KlarisAgent):
    retriever: FakeRetriever

    def __init__(self, retriever: FakeRetriever, responses: list[FakeCompletion]) -> None:
        self.retriever = retriever
        self.responses = responses

    async def _chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        tool_choice: str = "auto",
    ) -> Any:
        del messages, tool_choice
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_ask_rewrites_non_english_question_to_english_search_query() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Shrine of Order"),
            FakeCompletion("Você quis dizer Shrine of Order? Ele reorganiza atributos."),
        ],
    )

    response = await agent.ask("o que faz o santuário da ordem?", top_k=8)

    assert retriever.calls == [("Shrine of Order", 8)]
    assert "Shrine of Order" in response.response
    assert response.sources[0].title == "Deep Shrines/Shrine of Order"


@pytest.mark.asyncio
async def test_ask_returns_not_found_when_retrieval_has_no_strong_source() -> None:
    retriever = FakeRetriever(score=0.42)
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Blightsurger Oath requirements"),
            FakeCompletion("Blightsurger is obtained by defeating Titus in a raid."),
        ],
    )

    response = await agent.ask("como conseguir a Oath Blightsurger?", top_k=8)

    assert response.response == "I could not find that information in the current archive."
    assert response.sources == []


@pytest.mark.asyncio
async def test_chat_routes_deepwoken_questions_through_internal_ask() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Shrine of Order"),
            FakeCompletion("Shrine of Order reorganiza atributos."),
        ],
    )

    response = await agent.chat("o que faz o santuário da ordem?", top_k=8)

    assert retriever.calls == [("Shrine of Order", 8)]
    assert "Shrine of Order" in response.response


@pytest.mark.asyncio
async def test_chat_uses_conversation_history_for_contextual_followups() -> None:
    retriever = FakeRetriever()
    captured_messages: list[list[ChatCompletionMessageParam]] = []

    class CapturingKlarisAgent(FakeKlarisAgent):
        async def _chat_completion(
            self,
            messages: list[ChatCompletionMessageParam],
            tool_choice: str = "auto",
        ) -> Any:
            captured_messages.append(messages)
            return await super()._chat_completion(messages, tool_choice)

    agent = CapturingKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Shrine of Order requirements"),
            FakeCompletion("Shrine of Order requires Power 8."),
        ],
    )

    response = await agent.chat(
        "what are its requirements?",
        top_k=8,
        history=[
            {"role": "user", "content": "what is Shrine of Order?"},
            {"role": "assistant", "content": "It averages invested points."},
        ],
    )

    assert retriever.calls == [("Shrine of Order requirements", 8)]
    assert "Power 8" in response.response
    assert any(
        "what is Shrine of Order?" in str(message.get("content", ""))
        for messages in captured_messages
        for message in messages
    )


@pytest.mark.asyncio
async def test_chat_resolves_pronoun_followup_search_query_from_history() -> None:
    duke_loot_chunk: RetrievedChunk = {
        "id": uuid4(),
        "chunk_index": 4,
        "heading": "Drops",
        "content": (
            "Page: Duke Erisia\n"
            "Section: Drops\n"
            "Duke Erisia can drop equipment and items from his boss chest."
        ),
        "token_count": 14,
        "page_title": "Duke Erisia",
        "page_url": "https://deepwoken.fandom.com/wiki/Duke_Erisia",
        "score": 0.98,
    }
    retriever = QueryAwareFakeRetriever(
        {
            "loots": [],
            "descreva seus loots": [],
            "Duke Erisia loots": [duke_loot_chunk],
        }
    )
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("loots"),
            FakeCompletion("Duke Erisia's drops are described by the retrieved archive result."),
        ],
    )

    response = await agent.chat(
        "descreva seus loots",
        top_k=8,
        history=[
            {"role": "user", "content": "quem era Duke of Erisia?"},
            {
                "role": "assistant",
                "content": (
                    "The Duke of Erisia, officially Duke Ishamon Erisia, is a humanoid boss."
                ),
            },
        ],
    )

    assert retriever.calls == [("Duke Erisia loots", 8)]
    assert "Duke Erisia" in response.response
    assert response.sources[0].title == "Duke Erisia"


@pytest.mark.asyncio
async def test_ask_retries_instead_of_returning_text_tool_call() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Duke's Key"),
            FakeCompletion('We need to call search tool.\n{"query": "Duke\'s Key Deepwoken"}'),
            FakeCompletion("Duke's Key is handled by the archive result, not a visible tool call."),
        ],
    )

    response = await agent.ask("what is Duke's Key?", top_k=8)

    assert "We need to call search tool" not in response.response
    assert '{"query"' not in response.response
    assert "Duke's Key" in response.response


@pytest.mark.asyncio
async def test_ask_extracts_query_when_rewrite_returns_tool_json() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion('We need to call search tool.\n{"query": "Duke\'s Key Deepwoken"}'),
            FakeCompletion("Duke's Key is described by the retrieved archive result."),
        ],
    )

    response = await agent.ask("what is Duke's Key?", top_k=8)

    assert retriever.calls == [("Duke's Key Deepwoken", 8)]
    assert "Duke's Key" in response.response


@pytest.mark.asyncio
async def test_ask_retries_search_rewrite_when_first_query_is_not_canonical() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("llave del duque"),
            FakeCompletion("Duke's Key"),
            FakeCompletion("Duke's Key is described by the retrieved archive result."),
        ],
    )

    response = await agent.ask("¿Cómo puedo conseguir la llave del duque?", top_k=8)

    assert retriever.calls == [("Duke's Key", 8)]
    assert "Duke's Key" in response.response


@pytest.mark.asyncio
async def test_ask_falls_back_to_original_question_when_rewritten_query_is_weak() -> None:
    weak_chunk: RetrievedChunk = {
        "id": uuid4(),
        "chunk_index": 0,
        "heading": "Overview",
        "content": "Page: Unrelated\n\nUnrelated archive text.",
        "token_count": 5,
        "page_title": "Unrelated",
        "page_url": "https://example.test/wiki/Unrelated",
        "score": 0.42,
    }
    shrine_chunk: RetrievedChunk = {
        "id": uuid4(),
        "chunk_index": 0,
        "heading": "Usage",
        "content": (
            "Page: Deep Shrines/Shrine of Order\n"
            "Section: Usage\n"
            "Shrine of Order averages invested points."
        ),
        "token_count": 12,
        "page_title": "Deep Shrines/Shrine of Order",
        "page_url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
        "score": 0.98,
    }
    retriever = QueryAwareFakeRetriever(
        {
            "bad verbose rewrite": [weak_chunk],
            "what is Shrine of Order?": [shrine_chunk],
        }
    )
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("bad verbose rewrite"),
            FakeCompletion("Shrine of Order averages invested points."),
        ],
    )

    response = await agent.ask("what is Shrine of Order?", top_k=8)

    assert retriever.calls == [
        ("bad verbose rewrite", 8),
        ("what is Shrine of Order?", 8),
    ]
    assert "Shrine of Order" in response.response
    assert response.sources[0].title == "Deep Shrines/Shrine of Order"


@pytest.mark.asyncio
async def test_ask_returns_not_found_when_model_answer_is_empty() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("Duke's Key"),
            FakeCompletion(""),
        ],
    )

    response = await agent.ask("what is Duke's Key?", top_k=8)

    assert response.response == "I could not find that information in the current archive."
    assert response.sources == []


@pytest.mark.asyncio
async def test_chat_routes_text_tool_call_to_internal_ask() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion('We need to call search tool.\n{"query": "Duke\'s Key Deepwoken"}'),
            FakeCompletion("Duke's Key is described by the retrieved archive result."),
        ],
    )

    response = await agent.chat("Duke's Key", top_k=8)

    assert retriever.calls == [("Duke's Key Deepwoken", 8)]
    assert "We need to call search tool" not in response.response
    assert "Duke's Key" in response.response


@pytest.mark.asyncio
async def test_chat_returns_not_found_when_model_answer_is_empty() -> None:
    retriever = FakeRetriever()
    agent = FakeKlarisAgent(
        retriever=retriever,
        responses=[
            FakeCompletion("obscure Deepwoken detail"),
            FakeCompletion(""),
        ],
    )

    response = await agent.chat("tell me something obscure", top_k=8)

    assert response.response == "I could not find that information in the current archive."
    assert response.sources == []
