from __future__ import annotations

from time import monotonic

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from bot.config import bot_settings
from bot.i18n import gettext
from bot.klaris_client import KlarisApiClient

logger = structlog.get_logger()


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot and backend latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        discord_ms = round(interaction.client.latency * 1000, 1)

        client: KlarisApiClient = self.bot.klaris_client  # type: ignore[attr-defined]
        backend_ok = False
        backend_ms: float | None = None

        try:
            t0 = monotonic()
            await client.health()
            backend_ms = round((monotonic() - t0) * 1000, 1)
            backend_ok = True
        except Exception:
            backend_ms = None

        if backend_ok:
            status_text = f"✅ Backend OK ({backend_ms}ms)"
            color = discord.Color.green()
        else:
            status_text = "❌ Backend indisponível"
            color = discord.Color.red()
            notifier = getattr(self.bot, "notifier", None)
            if notifier is not None:
                await notifier.on_ping_backend_down(duration_ms=backend_ms)

        embed = discord.Embed(
            description=(
                f"🏓 Pong!\n"
                f"**Discord:** {discord_ms}ms\n"
                f"**Backend:** {status_text}"
            ),
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear", description="Clear your conversation context")
    async def clear(
        self,
        interaction: discord.Interaction,
    ) -> None:
        language = bot_settings.bot_default_language
        user_id = str(interaction.user.id)

        store = getattr(self.bot, "conversation_store", None)
        if store is not None:
            store.clear(user_id)

        notifier = getattr(self.bot, "notifier", None)
        if notifier is not None:
            await notifier.on_clear_executed(user_id)

        await interaction.response.send_message(
            gettext(language, "context_cleared"),
            ephemeral=True,
        )

    @app_commands.command(name="context", description="Show your conversation context stats")
    async def context(self, interaction: discord.Interaction) -> None:
        language = bot_settings.bot_default_language
        user_id = str(interaction.user.id)

        store = getattr(self.bot, "conversation_store", None)
        if store is None:
            await interaction.response.send_message(
                gettext(language, "no_context"),
                ephemeral=True,
            )
            return

        history = store.get_history(user_id)
        turn_count = len(history) // 2

        embed = discord.Embed(
            description="📋 **Contexto de conversa**",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Turnos", value=str(turn_count), inline=True)
        embed.add_field(
            name="TTL",
            value=f"{bot_settings.bot_context_ttl_seconds}s",
            inline=True,
        )
        embed.add_field(
            name="Máximo",
            value=f"{bot_settings.bot_context_max_turns} turnos",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
