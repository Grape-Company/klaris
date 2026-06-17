import time

from bot.cache import LRUCache, ask_cache_key
from bot.cogs.admin import user_blacklist
from bot.cogs.ask import AskCog
from bot.cogs.chat import ChatCog, ConversationStore
from bot.embeds import build_answer_embed
from bot.formatting import (
    DISCORD_MESSAGE_LIMIT,
    format_klaris_response,
)
from bot.guards import BotGuard, WindowRateLimiter
from bot.i18n import gettext
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

    def __init__(self) -> None:
        self.guild_permissions = type(
            "FakePermissions",
            (),
            {"administrator": True},
        )()


class FakeGuild:
    id = 456


class FakeInteraction:
    def __init__(self) -> None:
        self.user = FakeUser()
        self.guild_id = 456
        self.channel_id = 789
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

    async def health(self) -> dict[str, str]:
        return {"status": "ok"}


class FakeBot:
    def __init__(self, guard: BotGuard | None = None) -> None:
        self.klaris_client = FakeKlarisClient()
        self.bot_guard = guard
        self.notifier = None
        self.conversation_store = ConversationStore(max_turns=10)
        self.guilds: list[object] = []

    async def is_owner(self, _user: object) -> bool:
        return False


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


def test_window_rate_limiter_with_different_keys() -> None:
    limiter = WindowRateLimiter(limit=2, window_seconds=10)

    assert limiter.allow("user:1", now=100)
    assert limiter.allow("user:2", now=100)
    assert limiter.allow("user:1", now=101)
    assert not limiter.allow("user:1", now=102)
    assert limiter.allow("user:2", now=102)


def test_window_rate_limiter_remaining() -> None:
    limiter = WindowRateLimiter(limit=5, window_seconds=10)

    assert limiter.remaining("key", now=100) == 5
    limiter.allow("key", now=100)
    assert limiter.remaining("key", now=100) == 4
    limiter.allow("key", now=101)
    limiter.allow("key", now=102)
    assert limiter.remaining("key", now=105) == 2


def test_bot_guard_user_blacklist() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users={"123"},
        blacklisted_guilds=set(),
    )
    interaction = FakeInteraction()
    interaction.user.id = 123

    result = guard.check_interaction(interaction)

    assert not result.is_allowed()
    assert result.reason == "user_blacklisted"


def test_bot_guard_guild_blacklist() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds={"456"},
    )
    interaction = FakeInteraction()
    interaction.guild_id = 456

    result = guard.check_interaction(interaction)

    assert not result.is_allowed()
    assert result.reason == "guild_blacklisted"


def test_bot_guard_global_rate_limit() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=1, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    interaction = FakeInteraction()

    result1 = guard.check_interaction(interaction)
    assert result1.is_allowed()

    result2 = guard.check_interaction(interaction)
    assert not result2.is_allowed()
    assert result2.reason == "global_rate_limit"


def test_bot_guard_channel_rate_limit() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=1, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    interaction = FakeInteraction()

    result1 = guard.check_interaction(interaction)
    assert result1.is_allowed()

    result2 = guard.check_interaction(interaction)
    assert not result2.is_allowed()
    assert result2.reason == "channel_rate_limit"


def test_bot_guard_user_rate_limit() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=1, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    interaction = FakeInteraction()

    result1 = guard.check_interaction(interaction)
    assert result1.is_allowed()

    result2 = guard.check_interaction(interaction)
    assert not result2.is_allowed()
    assert result2.reason == "user_rate_limit"


def test_bot_guard_user_rate_limit_does_not_charge_shared_buckets() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=1, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=2, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=2, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    limited_interaction = FakeInteraction()

    assert guard.check_interaction(limited_interaction).is_allowed()
    assert guard.check_interaction(limited_interaction).reason == "user_rate_limit"
    assert guard.check_interaction(limited_interaction).reason == "user_rate_limit"

    other_interaction = FakeInteraction()
    other_interaction.user.id = 999

    result = guard.check_interaction(other_interaction)

    assert result.is_allowed()


def test_bot_guard_allows_normal_interaction() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    interaction = FakeInteraction()

    result = guard.check_interaction(interaction)

    assert result.is_allowed()


async def test_admin_commands_require_bot_owner_not_guild_admin() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    bot = FakeBot(guard=guard)
    interaction = FakeInteraction()
    interaction.client = bot

    await user_blacklist.callback(interaction, "add", "999")

    assert "999" not in guard._blacklisted_users
    assert (
        interaction.response.messages[0]["content"]
        == "Você não tem permissão para usar este comando."
    )
    assert interaction.response.messages[0]["ephemeral"] is True


async def test_ask_guard_blocks_before_api_call() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=0, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    bot = FakeBot(guard=guard)
    cog = AskCog(bot=bot, klaris_client=bot.klaris_client)
    interaction = FakeInteraction()

    await cog.ask.callback(cog, interaction, "what is Shrine of Order?")

    assert bot.klaris_client.ask_calls == []
    assert interaction.response.messages[0]["ephemeral"] is True
    assert interaction.response.deferred is False


async def test_chat_guard_blocks_before_api_call() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=0, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    bot = FakeBot(guard=guard)
    store = ConversationStore(max_turns=10)
    cog = ChatCog(
        bot=bot,
        klaris_client=bot.klaris_client,
        conversation_store=store,
    )
    interaction = FakeInteraction()

    await cog.chat.callback(cog, interaction, "follow up")

    assert bot.klaris_client.chat_calls == []
    assert store.get_history(str(interaction.user.id)) == []
    assert interaction.response.messages[0]["ephemeral"] is True
    assert interaction.response.deferred is False


async def test_ask_allows_normal_flow() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    bot = FakeBot(guard=guard)
    cog = AskCog(bot=bot, klaris_client=bot.klaris_client)
    interaction = FakeInteraction()

    await cog.ask.callback(cog, interaction, "what is Shrine of Order?")

    assert len(bot.klaris_client.ask_calls) == 1
    assert interaction.response.deferred is True


async def test_chat_sends_existing_conversation_history_to_api() -> None:
    guard = BotGuard(
        user_limiter=WindowRateLimiter(limit=5, window_seconds=60),
        channel_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        global_limiter=WindowRateLimiter(limit=10, window_seconds=60),
        blacklisted_users=set(),
        blacklisted_guilds=set(),
    )
    bot = FakeBot(guard=guard)
    store = ConversationStore(max_turns=10)
    user_id = str(FakeUser.id)
    store.add_message(user_id, "user", "what is Shrine of Order?")
    store.add_message(user_id, "assistant", "It averages invested points.")
    cog = ChatCog(
        bot=bot,
        klaris_client=bot.klaris_client,
        conversation_store=store,
    )
    interaction = FakeInteraction()

    await cog.chat.callback(cog, interaction, "what are its requirements?")

    assert bot.klaris_client.chat_calls == [
        (
            "what are its requirements?",
            8,
            [
                {"role": "user", "content": "what is Shrine of Order?"},
                {"role": "assistant", "content": "It averages invested points."},
            ],
        ),
    ]


def test_conversation_store_clear() -> None:
    store = ConversationStore(max_turns=10)
    store.add_message("user-1", "user", "hello")
    assert len(store.get_history("user-1")) == 1

    store.clear("user-1")
    assert store.get_history("user-1") == []


def test_conversation_store_max_turns() -> None:
    store = ConversationStore(max_turns=2)
    for i in range(5):
        store.add_message("user-1", "user", f"msg {i}")
        store.add_message("user-1", "assistant", f"resp {i}")

    history = store.get_history("user-1")
    assert len(history) <= 4


def test_cache_hit_and_miss() -> None:
    cache = LRUCache(max_size=10, ttl_seconds=60)

    assert cache.get("key1") is None

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.set("key2", "value2")
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"


def test_cache_expires_after_ttl() -> None:
    cache = LRUCache(max_size=10, ttl_seconds=0.01)

    cache.set("key", "value")
    assert cache.get("key") == "value"

    time.sleep(0.02)
    assert cache.get("key") is None


def test_cache_evicts_lru_when_full() -> None:
    cache = LRUCache(max_size=2, ttl_seconds=60)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_cache_size_property() -> None:
    cache = LRUCache(max_size=10, ttl_seconds=60)

    assert cache.size == 0
    cache.set("a", 1)
    assert cache.size == 1
    cache.set("b", 2)
    assert cache.size == 2
    cache.clear()
    assert cache.size == 0


def test_ask_cache_key_deterministic() -> None:
    key1 = ask_cache_key("What is Shrine of Order?", 8)
    key2 = ask_cache_key("  WHAT IS SHRINE OF ORDER?  ", 8)

    assert key1 == key2


def test_ask_cache_key_different_top_k() -> None:
    key1 = ask_cache_key("What is Shrine of Order?", 8)
    key2 = ask_cache_key("What is Shrine of Order?", 5)

    assert key1 != key2


def test_i18n_new_keys_exist() -> None:
    assert gettext("pt-BR", "user_blocked") is not None
    assert gettext("en", "user_blocked") is not None
    assert gettext("pt-BR", "guild_blocked") is not None
    assert gettext("en", "guild_blocked") is not None
    assert gettext("pt-BR", "footer_page", page=1, total=3) is not None
    assert gettext("en", "footer_page", page=1, total=3) is not None


def test_i18n_existing_keys_unmodified() -> None:
    assert gettext("pt-BR", "rate_limit_user") is not None
    assert gettext("pt-BR", "rate_limit_channel") is not None
    assert gettext("pt-BR", "rate_limit_global") is not None
    assert gettext("pt-BR", "context_cleared") is not None
    assert gettext("pt-BR", "no_context") is not None
