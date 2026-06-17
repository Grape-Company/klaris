from __future__ import annotations

from typing import Literal

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.embeds import build_error_embed
from bot.errors import handle_api_error
from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient

logger = structlog.get_logger()


class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="feedback", description="Submit feedback about an answer")
    @app_commands.describe(
        answer_id="The answer ID shown in the response footer",
        rating="Whether the answer was helpful or not",
        correction="Optional correction or additional information",
    )
    async def feedback_command(
        self,
        interaction: discord.Interaction,
        answer_id: str,
        rating: Literal["positive", "negative"],
        correction: str | None = None,
    ) -> None:
        language = bot_settings.bot_default_language

        await interaction.response.defer(thinking=True, ephemeral=True)

        client: KlarisApiClient = self.bot.klaris_client  # type: ignore[attr-defined]

        try:
            await client.submit_feedback(
                answer_id=answer_id,
                rating=rating,
                correction=correction,
            )
        except Exception as exc:
            error_key = await handle_api_error(exc, endpoint="/api/rag/feedback")
            embed = build_error_embed(gettext(language, error_key), language)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await interaction.followup.send(
            gettext(language, "feedback_recorded"),
            ephemeral=True,
        )
