from __future__ import annotations

from collections.abc import Mapping, Sequence

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.embeds import build_answer_embed, build_error_embed, build_not_found_embed
from bot.errors import handle_api_error
from bot.feedback_view import FeedbackView
from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient
from bot.pagination import PaginatedResponseView

logger = structlog.get_logger()

MAX_SOURCES_PER_PAGE = 5


async def _suggest_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if len(current) < 2:
        return []
    client: KlarisApiClient = interaction.client.klaris_client  # type: ignore[attr-defined]
    try:
        suggestions = await client.suggest_titles(query=current, limit=10)
    except Exception:
        return []
    seen: set[str] = set()
    results: list[app_commands.Choice[str]] = []
    for item in suggestions:
        title = item.get("title", "")
        if title and title not in seen:
            seen.add(title)
            results.append(app_commands.Choice(name=title[:100], value=title[:100]))
            if len(results) >= 10:
                break
    return results


class AskCog(commands.Cog):
    """Cog that provides the /ask command."""

    def __init__(
        self,
        bot: commands.Bot,
        klaris_client: KlarisApiClient,
    ) -> None:
        self.bot = bot
        self.client = klaris_client

    @app_commands.command(name="ask", description="Ask about Deepwoken")
    @app_commands.describe(question="Your question about Deepwoken")
    @app_commands.autocomplete(question=_suggest_autocomplete)
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        language = bot_settings.bot_default_language

        if len(question) > 2000:
            await interaction.response.send_message(
                gettext(language, "question_too_long"),
                ephemeral=True,
            )
            return

        guard = getattr(self.bot, "bot_guard", None)
        if guard is not None:
            result = guard.check_interaction(interaction)
            if not result.is_allowed():
                await interaction.response.send_message(
                    gettext(language, result.i18n_key),
                    ephemeral=True,
                )
                return

        await interaction.response.defer(thinking=True)

        try:
            payload = await self.client.ask(question, bot_settings.bot_default_top_k)
        except Exception as exc:
            error_key = await handle_api_error(
                exc,
                endpoint="/api/klaris/chat",
            )
            embed = build_error_embed(gettext(language, error_key), language)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        response: str = str(payload.get("response") or payload.get("answer") or "")
        sources_raw: Sequence[Mapping[str, object]] = list(payload.get("sources") or [])
        answer_id_raw: object = payload.get("answer_id")
        answer_id: str | None = str(answer_id_raw) if answer_id_raw else None

        if not response:
            embed = build_not_found_embed(
                gettext(language, "not_found"),
                language,
            )
            await interaction.followup.send(embed=embed)
            return

        color = discord.Color.green()

        pages: list[discord.Embed] = []
        if len(sources_raw) > MAX_SOURCES_PER_PAGE:
            for i in range(0, len(sources_raw), MAX_SOURCES_PER_PAGE):
                chunk = sources_raw[i : i + MAX_SOURCES_PER_PAGE]
                page = build_answer_embed(response, chunk, answer_id, color, language)
                pages.append(page)
        else:
            pages.append(build_answer_embed(response, sources_raw, answer_id, color, language))

        pagination = PaginatedResponseView(pages, answer_id, language)

        if answer_id and bot_settings.bot_api_key:
            feedback = FeedbackView(
                answer_id=answer_id,
                client=self.client,
                language=language,
            )
            for item in feedback.children:
                pagination.add_item(item)

        await interaction.followup.send(embed=pages[0], view=pagination)
