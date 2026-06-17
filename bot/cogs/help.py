from __future__ import annotations

from collections.abc import Sequence

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import build_help_embed
from bot.i18n import DEFAULT_LANG


class HelpCog(commands.Cog):
    """Cog that provides the /help command."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Shows available commands")
    async def help_command(self, interaction: discord.Interaction) -> None:
        language = DEFAULT_LANG

        commands_list: Sequence[tuple[str, str]] = [
            ("help_ask", "help_ask"),
            ("help_chat", "help_chat"),
            ("help_help", "help_help"),
            ("help_stats", "help_stats"),
            ("help_invite", "help_invite"),
            ("help_feedback", "help_feedback"),
        ]

        embed = build_help_embed(commands_list, language)
        await interaction.response.send_message(embed=embed, ephemeral=True)
