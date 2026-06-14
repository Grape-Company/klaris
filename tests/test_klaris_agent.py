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

    assert response.response == "não encontrei essa informação na base atual."
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
