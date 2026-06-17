from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.i18n import gettext


class InviteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invite", description="Get bot invite link")
    async def invite_command(self, interaction: discord.Interaction) -> None:
        language = bot_settings.bot_default_language

        invite_url = bot_settings.discord_invite_url
        if not invite_url:
            client_id = os.environ.get("DISCORD_CLIENT_ID")
            if client_id:
                invite_url = (
                    f"https://discord.com/oauth2/authorize"
                    f"?client_id={client_id}&scope=bot&permissions=0"
                )

        if invite_url:
            embed = discord.Embed(
                description=gettext(language, "invite_message"),
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(
                content=invite_url,
                embed=embed,
                ephemeral=True,
            )
        else:
            embed = discord.Embed(
                description=gettext(language, "general_failure"),
                color=discord.Color.red(),
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
