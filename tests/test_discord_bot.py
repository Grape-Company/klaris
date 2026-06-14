from bot.formatting import DISCORD_MESSAGE_LIMIT, format_ask_response
from bot.rate_limit import UserRateLimiter


def test_format_ask_response_includes_sources() -> None:
    message = format_ask_response(
        {
            "answer": "Shrine of Order averages your stats.",
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


def test_format_ask_response_uses_portuguese_sources_for_portuguese_answer() -> None:
    message = format_ask_response(
        {
            "answer": "O Shrine of Order reorganiza seus atributos.",
            "sources": [
                {
                    "title": "Deep Shrines/Shrine of Order",
                    "url": "https://deepwoken.fandom.com/wiki/Deep_Shrines/Shrine_of_Order",
                    "chunk_id": "chunk-1",
                }
            ],
        }
    )

    assert "Fontes:" in message


def test_format_ask_response_respects_discord_limit() -> None:
    message = format_ask_response({"answer": "x" * 3000, "sources": []})

    assert len(message) <= DISCORD_MESSAGE_LIMIT
    assert message.endswith("[truncated]")


def test_user_rate_limiter_blocks_until_window_expires() -> None:
    limiter = UserRateLimiter(limit=2, window_seconds=10)

    assert limiter.allow("user-1", now=100)
    assert limiter.allow("user-1", now=101)
    assert not limiter.allow("user-1", now=102)
    assert limiter.allow("user-1", now=111)
