from __future__ import annotations

import structlog
from discord import Color, Embed

logger = structlog.get_logger()


class BotNotifier:
    def __init__(self, bot: object, log_channel_id: int | None = None) -> None:
        self._bot = bot
        self._log_channel_id = log_channel_id

    async def _send(self, embed: Embed) -> None:
        if self._log_channel_id is None:
            return
        try:
            channel = self._bot.get_channel(self._log_channel_id)  # type: ignore[union-attr]
            if channel is None:
                try:
                    channel = await self._bot.fetch_channel(self._log_channel_id)  # type: ignore[union-attr]
                except Exception:
                    logger.warning(
                        "log_channel_not_found",
                        channel_id=self._log_channel_id,
                    )
                    return
            await channel.send(embed=embed)
        except Exception:
            logger.exception(
                "log_channel_send_failed",
                channel_id=self._log_channel_id,
            )

    async def on_bot_started(self) -> None:
        embed = Embed(
            description="Bot iniciado / Bot started",
            color=Color.green(),
        )
        await self._send(embed)

    async def on_backend_error(
        self,
        endpoint: str,
        status: int | None = None,
    ) -> None:
        embed = Embed(
            description=f"Erro no backend: {endpoint}",
            color=Color.red(),
        )
        if status is not None:
            embed.add_field(name="Status", value=str(status))
        await self._send(embed)

    async def on_rate_limit(
        self,
        reason: str,
        user_id: str | None = None,
    ) -> None:
        embed = Embed(
            description=f"Rate limit acionado: {reason}",
            color=Color.orange(),
        )
        if user_id:
            embed.add_field(name="Usuário", value=f"<@{user_id}>")
        await self._send(embed)

    async def on_user_blocked(self, user_id: str, reason: str) -> None:
        embed = Embed(
            description=f"Usuário bloqueado: {reason}",
            color=Color.red(),
        )
        embed.add_field(name="Usuário", value=f"<@{user_id}>")
        await self._send(embed)

    async def on_guild_blocked(self, guild_id: str, reason: str) -> None:
        embed = Embed(
            description=f"Servidor bloqueado: {reason}",
            color=Color.red(),
        )
        embed.add_field(name="Servidor", value=guild_id)
        await self._send(embed)

    async def on_feedback_received(
        self,
        rating: str,
        correction: str | None = None,
    ) -> None:
        embed = Embed(
            description=f"Feedback recebido: {rating}",
            color=Color.blue(),
        )
        if correction:
            embed.add_field(name="Correção", value=correction[:500])
        await self._send(embed)

    async def on_clear_executed(self, user_id: str) -> None:
        embed = Embed(
            description="Contexto limpo",
            color=Color.light_gray(),
        )
        embed.add_field(name="Usuário", value=f"<@{user_id}>")
        await self._send(embed)

    async def on_ping_backend_down(self, duration_ms: float | None = None) -> None:
        embed = Embed(
            description="Backend indisponível via /ping",
            color=Color.red(),
        )
        if duration_ms is not None:
            embed.add_field(name="Tempo", value=f"{duration_ms:.0f}ms")
        await self._send(embed)
