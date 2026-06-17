from bot.cogs.ask import AskCog
from bot.cogs.chat import ChatCog, ConversationStore
from bot.embeds import build_answer_embed
from bot.formatting import (
    DISCORD_MESSAGE_LIMIT,
    format_klaris_response,
)
from bot.rate_limit import UserRateLimiter


class FakeResponse:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.deferred = False

    async def send_message(
        self,
        content: str | None = None,
        *,
        embed: object | None = None,
        ephemeral: bool = False,
    ) -> None:
        self.messages.append(
            {"content": content, "embed": embed, "ephemeral": ephemeral},
        )

    async def defer(self, *, thinking: bool = False) -> None:
        self.deferred = thinking


class FakeFollowup:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(
        self,
        content: str | None = None,
        *,
        embed: object | None = None,
        view: object | None = None,
        ephemeral: bool = False,
    ) -> None:
        self.messages.append(
            {
                "content": content,
                "embed": embed,
                "view": view,
                "ephemeral": ephemeral,
            },
        )


class FakeUser:
    id = 123


class FakeInteraction:
    def __init__(self) -> None:
        self.user = FakeUser()
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeKlarisClient:
    def __init__(self) -> None:
        self.ask_calls: list[tuple[str, int]] = []
        self.chat_calls: list[tuple[str, int, list[dict[str, str]] | None]] = []

    async def ask(self, question: str, top_k: int) -> dict[str, object]:
        self.ask_calls.append((question, top_k))
        return {"response": "answer", "sources": []}

    async def chat(
        self,
        message: str,
        top_k: int,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        self.chat_calls.append((message, top_k, history))
        return {"response": "answer", "sources": []}


def test_format_klaris_response_includes_sources() -> None:
    message = format_klaris_response(
        {
            "response": "Shrine of Order averages your stats.",
            "sources": [
                {
                    "title": "Deep Shrines/Shrine of Order",
                    "url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
                    "chunk_id": "chunk-1",
                }
            ],
        }
    )

    assert "Shrine of Order averages your stats." in message
    assert "Sources:" in message
    assert "Deep Shrines/Shrine of Order" in message


def test_format_klaris_response_accepts_legacy_rag_answer_key() -> None:
    message = format_klaris_response({"answer": "Shrine of Order averages your stats."})

    assert "Shrine of Order averages your stats." in message


def test_format_klaris_response_uses_portuguese_sources_for_portuguese_response() -> None:
    message = format_klaris_response(
        {
            "response": "O Shrine of Order reorganiza seus atributos.",
            "sources": [
                {
                    "title": "Deep Shrines/Shrine of Order",
                    "url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
                    "chunk_id": "chunk-1",
                }
            ],
        },
        source_language_text="o que o Shrine of Order faz?",
    )

    assert "Fontes:" in message


def test_format_klaris_response_uses_user_language_for_sources_heading() -> None:
    message = format_klaris_response(
        {
            "response": "O Shrine of Order reorganiza seus atributos.",
            "sources": [
                {
                    "title": "Deep Shrines/Shrine of Order",
                    "url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
                    "chunk_id": "chunk-1",
                }
            ],
        },
        source_language_text="what does Shrine of Order do?",
    )

    assert "Sources:" in message
    assert "Fontes:" not in message


def test_format_klaris_response_respects_discord_limit() -> None:
    message = format_klaris_response({"response": "x" * 3000, "sources": []})

    assert len(message) <= DISCORD_MESSAGE_LIMIT
    assert message.endswith("[truncated]")


def test_format_klaris_response_with_empty_sources() -> None:
    message = format_klaris_response({"response": "Hello, I am Klaris.", "sources": []})

    assert "Hello, I am Klaris." in message
    assert "Sources" not in message
    assert "Fontes" not in message


def test_user_rate_limiter_blocks_until_window_expires() -> None:
    limiter = UserRateLimiter(limit=2, window_seconds=10)

    assert limiter.allow("user-1", now=100)
    assert limiter.allow("user-1", now=101)
    assert not limiter.allow("user-1", now=102)
    assert limiter.allow("user-1", now=111)


def test_answer_embed_shows_full_answer_id_for_manual_feedback() -> None:
    answer_id = "123e4567-e89b-12d3-a456-426614174000"

    embed = build_answer_embed("answer", [], answer_id, None, "en-US")

    assert answer_id in embed.footer.text


async def test_ask_rate_limit_blocks_before_api_call() -> None:
    limiter = UserRateLimiter(limit=0, window_seconds=60)
    client = FakeKlarisClient()
    cog = AskCog(bot=object(), klaris_client=client, rate_limiter=limiter)  # type: ignore[arg-type]
    interaction = FakeInteraction()

    await cog.ask.callback(cog, interaction, "what is Shrine of Order?")  # type: ignore[misc]

    assert client.ask_calls == []
    assert interaction.response.messages[0]["ephemeral"] is True
    assert interaction.response.deferred is False


async def test_chat_rate_limit_blocks_before_api_call() -> None:
    limiter = UserRateLimiter(limit=0, window_seconds=60)
    client = FakeKlarisClient()
    store = ConversationStore(max_turns=10)
    cog = ChatCog(
        bot=object(),
        klaris_client=client,
        conversation_store=store,
        rate_limiter=limiter,
    )  # type: ignore[arg-type]
    interaction = FakeInteraction()

    await cog.chat.callback(cog, interaction, "follow up")  # type: ignore[misc]

    assert client.chat_calls == []
    assert store.get_history(str(interaction.user.id)) == []
    assert interaction.response.messages[0]["ephemeral"] is True
    assert interaction.response.deferred is False


async def test_chat_sends_existing_conversation_history_to_api() -> None:
    limiter = UserRateLimiter(limit=5, window_seconds=60)
    client = FakeKlarisClient()
    store = ConversationStore(max_turns=10)
    user_id = str(FakeUser.id)
    store.add_message(user_id, "user", "what is Shrine of Order?")
    store.add_message(user_id, "assistant", "It averages invested points.")
    cog = ChatCog(
        bot=object(),
        klaris_client=client,
        conversation_store=store,
        rate_limiter=limiter,
    )  # type: ignore[arg-type]
    interaction = FakeInteraction()

    await cog.chat.callback(cog, interaction, "what are its requirements?")  # type: ignore[misc]

    assert client.chat_calls == [
        (
            "what are its requirements?",
            8,
            [
                {"role": "user", "content": "what is Shrine of Order?"},
                {"role": "assistant", "content": "It averages invested points."},
            ],
        ),
    ]
