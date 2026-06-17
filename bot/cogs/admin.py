from __future__ import annotations

import discord
import structlog
from discord import app_commands
from discord.ext import commands

logger = structlog.get_logger()

ADMIN_PERMISSION_ERROR = "Você não tem permissão para usar este comando."


class AdminGroup(app_commands.Group):
    pass


_admin_group = AdminGroup(name="admin", description="Administrative commands")


@_admin_group.command(name="user-blacklist", description="Manage user blacklist")
@app_commands.describe(action="add, remove, or list", user_id="User ID (required for add/remove)")
async def user_blacklist(
    interaction: discord.Interaction,
    action: str,
    user_id: str | None = None,
) -> None:
    if not interaction.user.guild_permissions.administrator:  # type: ignore[union-attr]
        await interaction.response.send_message(ADMIN_PERMISSION_ERROR, ephemeral=True)
        return

    guard = getattr(interaction.client, "bot_guard", None)
    if guard is None:
        await interaction.response.send_message("Guard system not available.", ephemeral=True)
        return

    if action == "list":
        users = list(guard._blacklisted_users)
        if users:
            msg = "**Usuários bloqueados:**\n" + "\n".join(f"• {u}" for u in users)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message("Nenhum usuário bloqueado.", ephemeral=True)
    elif action == "add":
        if not user_id:
            await interaction.response.send_message("Informe o user_id.", ephemeral=True)
            return
        guard._blacklisted_users.add(user_id)
        await interaction.response.send_message(
            f"Usuário {user_id} adicionado à blacklist (runtime).",
            ephemeral=True,
        )
        notifier = getattr(interaction.client, "notifier", None)
        if notifier is not None:
            await notifier.on_user_blocked(user_id, "admin_command")
    elif action == "remove":
        if not user_id:
            await interaction.response.send_message("Informe o user_id.", ephemeral=True)
            return
        guard._blacklisted_users.discard(user_id)
        await interaction.response.send_message(
            f"Usuário {user_id} removido da blacklist (runtime).",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "Ação inválida. Use add, remove ou list.",
            ephemeral=True,
        )


@_admin_group.command(name="guild-blacklist", description="Manage guild blacklist")
@app_commands.describe(action="add, remove, or list", guild_id="Guild ID (required for add/remove)")
async def guild_blacklist(
    interaction: discord.Interaction,
    action: str,
    guild_id: str | None = None,
) -> None:
    if not interaction.user.guild_permissions.administrator:  # type: ignore[union-attr]
        await interaction.response.send_message(ADMIN_PERMISSION_ERROR, ephemeral=True)
        return

    guard = getattr(interaction.client, "bot_guard", None)
    if guard is None:
        await interaction.response.send_message("Guard system not available.", ephemeral=True)
        return

    if action == "list":
        guilds = list(guard._blacklisted_guilds)
        if guilds:
            msg = "**Servidores bloqueados:**\n" + "\n".join(f"• {g}" for g in guilds)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message("Nenhum servidor bloqueado.", ephemeral=True)
    elif action == "add":
        if not guild_id:
            await interaction.response.send_message("Informe o guild_id.", ephemeral=True)
            return
        guard._blacklisted_guilds.add(guild_id)
        await interaction.response.send_message(
            f"Servidor {guild_id} adicionado à blacklist (runtime).",
            ephemeral=True,
        )
        notifier = getattr(interaction.client, "notifier", None)
        if notifier is not None:
            await notifier.on_guild_blocked(guild_id, "admin_command")
    elif action == "remove":
        if not guild_id:
            await interaction.response.send_message("Informe o guild_id.", ephemeral=True)
            return
        guard._blacklisted_guilds.discard(guild_id)
        await interaction.response.send_message(
            f"Servidor {guild_id} removido da blacklist (runtime).",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "Ação inválida. Use add, remove ou list.",
            ephemeral=True,
        )


@_admin_group.command(name="stats", description="Show bot stats")
async def admin_stats(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.administrator:  # type: ignore[union-attr]
        await interaction.response.send_message(ADMIN_PERMISSION_ERROR, ephemeral=True)
        return

    guard = getattr(interaction.client, "bot_guard", None)
    guild_count = len(interaction.client.guilds)  # type: ignore[union-attr]

    embed = discord.Embed(
        description="📊 **Estatísticas do Bot**",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Servidores", value=str(guild_count), inline=True)
    if guard:
        blocked_users = str(len(guard._blacklisted_users))
        blocked_guilds = str(len(guard._blacklisted_guilds))
        embed.add_field(name="Usuários bloqueados", value=blocked_users, inline=True)
        embed.add_field(name="Servidores bloqueados", value=blocked_guilds, inline=True)

    cache = getattr(interaction.client, "response_cache", None)
    if cache is not None:
        cache_status = "Sim" if cache._max_size > 0 else "Não"
        embed.add_field(name="Cache ativo", value=cache_status, inline=True)
        embed.add_field(name="Tamanho do cache", value=str(cache.size), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@_admin_group.command(name="broadcast", description="Send a message to all guilds")
@app_commands.describe(message="Message to broadcast")
async def broadcast(interaction: discord.Interaction, message: str) -> None:
    if not interaction.user.guild_permissions.administrator:  # type: ignore[union-attr]
        await interaction.response.send_message(ADMIN_PERMISSION_ERROR, ephemeral=True)
        return

    embed = discord.Embed(
        description=message,
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Mensagem administrativa")

    sent = 0
    failed = 0
    for guild in interaction.client.guilds:  # type: ignore[union-attr]
        try:
            system_channel = guild.system_channel
            if system_channel is not None:
                await system_channel.send(embed=embed)
                sent += 1
        except Exception:
            failed += 1

    await interaction.response.send_message(
        f"Mensagem enviada para {sent} servidores ({failed} falhas).",
        ephemeral=True,
    )


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.tree.add_command(_admin_group)
