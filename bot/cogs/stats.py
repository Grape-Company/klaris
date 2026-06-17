from __future__ import annotations

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.embeds import build_error_embed, build_stats_embed
from bot.errors import handle_api_error
from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient

logger = structlog.get_logger()


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="stats", description="Show archive statistics")
    async def stats_command(self, interaction: discord.Interaction) -> None:
        language = bot_settings.bot_default_language

        await interaction.response.defer(thinking=True)

        client: KlarisApiClient = self.bot.klaris_client  # type: ignore[attr-defined]

        try:
            data = await client.stats()
        except Exception as exc:
            error_key = await handle_api_error(exc, endpoint="/api/klaris/stats")
            embed = build_error_embed(gettext(language, error_key), language)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = build_stats_embed(data, language)
        await interaction.followup.send(embed=embed)
