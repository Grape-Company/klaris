from bot.formatting import (
    DISCORD_MESSAGE_LIMIT,
    format_klaris_response,
)
from bot.rate_limit import UserRateLimiter


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
