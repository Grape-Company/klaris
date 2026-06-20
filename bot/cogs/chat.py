from __future__ import annotations

from collections.abc import Sequence
from time import monotonic

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.embeds import build_answer_embed, build_error_embed
from bot.errors import handle_api_error
from bot.feedback_view import FeedbackView
from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient

logger = structlog.get_logger()

MAX_MESSAGE_LENGTH = 2000
MIN_MESSAGE_LENGTH = 1


def build_memory_content(response: str, sources: Sequence[dict[str, object]]) -> str:
    titles: list[str] = []
    for source in sources:
        title = source.get("title")
        if isinstance(title, str) and title and title not in titles:
            titles.append(title)

    if not titles:
        return response

    source_line = f"Source pages: {', '.join(titles[:5])}"
    content = f"{response}\n{source_line}"
    if len(content) <= MAX_MESSAGE_LENGTH:
        return content

    available_response_chars = MAX_MESSAGE_LENGTH - len(source_line) - 1
    if available_response_chars <= 0:
        return source_line[:MAX_MESSAGE_LENGTH]
    return f"{response[:available_response_chars].rstrip()}\n{source_line}"


class ConversationStore:
    """Simple in-memory conversation history store with TTL support."""

    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        # Store entries as list of (timestamp, message_dict)
        self._histories: dict[str, list[tuple[float, dict[str, str]]]] = {}

    def _prune_expired(self, user_id: str) -> None:
        """Remove entries older than the configured TTL."""
        from bot.config import bot_settings
        ttl = bot_settings.bot_context_ttl_seconds
        now = monotonic()
        if user_id in self._histories:
            self._histories[user_id] = [
                (ts, msg) for ts, msg in self._histories[user_id] if now - ts <= ttl
            ]

    def get_history(self, user_id: str) -> list[dict[str, str]]:
        # Ensure expired messages are removed before returning
        self._prune_expired(user_id)
        return [msg for _ts, msg in self._histories.get(user_id, [])]

    def add_message(self, user_id: str, role: str, content: str) -> None:
        # Add new message with timestamp
        entry: tuple[float, dict[str, str]] = (monotonic(), {"role": role, "content": content})
        self._histories.setdefault(user_id, []).append(entry)
        # Enforce max turns (each turn has user+assistant)
        if len(self._histories[user_id]) > self._max_turns * 2:
            self._histories[user_id] = self._histories[user_id][-self._max_turns * 2 :]

    def clear(self, user_id: str) -> None:
        self._histories.pop(user_id, None)


_conversation_store = ConversationStore(max_turns=bot_settings.bot_context_max_turns)


class ChatCog(commands.Cog):
    """Cog that provides the /chat command with conversation memory."""

    def __init__(
        self,
        bot: commands.Bot,
        klaris_client: KlarisApiClient,
        conversation_store: ConversationStore | None = None,
    ) -> None:
        self.bot = bot
        self.client = klaris_client
        self.conversation_store = conversation_store or _conversation_store

    @app_commands.command(name="chat", description="Chat with Klaris")
    @app_commands.describe(message="Your message to Klaris")
    async def chat(self, interaction: discord.Interaction, message: str) -> None:
        language = bot_settings.bot_default_language

        content = message.strip()
        if len(content) > MAX_MESSAGE_LENGTH:
            await interaction.response.send_message(
                gettext(language, "question_too_long"),
                ephemeral=True,
            )
            return

        if len(content) < MIN_MESSAGE_LENGTH:
            await interaction.response.send_message(
                gettext(language, "general_failure"),
                ephemeral=True,
            )
            return

        user_id = str(interaction.user.id)

        guard = getattr(self.bot, "bot_guard", None)
        if guard is not None:
            result = guard.check_interaction(interaction)
            if not result.is_allowed():
                await interaction.response.send_message(
                    gettext(language, result.i18n_key),
                    ephemeral=True,
                )
                return

        history = list(self.conversation_store.get_history(user_id))
        self.conversation_store.add_message(user_id, "user", content)

        await interaction.response.defer(thinking=True)

        try:
            payload = await self.client.chat(content, bot_settings.bot_default_top_k, history)
        except Exception as exc:
            error_key = await handle_api_error(
                exc,
                endpoint="/api/klaris/chat",
            )
            embed = build_error_embed(gettext(language, error_key), language)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        response: str = str(payload.get("response") or payload.get("answer") or "")
        sources_raw: Sequence[dict[str, object]] = list(payload.get("sources") or [])
        answer_id_raw: object = payload.get("answer_id")
        answer_id: str | None = str(answer_id_raw) if answer_id_raw else None

        self.conversation_store.add_message(
            user_id,
            "assistant",
            build_memory_content(response, sources_raw),
        )

        if not response:
            embed = build_error_embed(
                gettext(language, "not_found"),
                language,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = build_answer_embed(
            response,
            sources_raw,
            answer_id,
            discord.Color.green(),
            language,
        )

        feedback_view = None
        if answer_id and bot_settings.bot_api_key:
            feedback_view = FeedbackView(
                answer_id=answer_id,
                client=self.client,
                language=language,
            )

        if feedback_view:
            await interaction.followup.send(embed=embed, view=feedback_view)
        else:
            await interaction.followup.send(embed=embed)
