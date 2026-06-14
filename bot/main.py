import logging

import discord
import httpx
from discord import app_commands

from bot.config import bot_settings
from bot.formatting import format_ask_response
from bot.rag_client import RagApiClient
from bot.rate_limit import UserRateLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
rag_client = RagApiClient(
    api_url=bot_settings.rag_api_url,
    timeout_seconds=bot_settings.bot_request_timeout_seconds,
)
rate_limiter = UserRateLimiter(
    limit=bot_settings.bot_rate_limit_count,
    window_seconds=bot_settings.bot_rate_limit_window_seconds,
)


@client.event  # type: ignore[untyped-decorator]
async def on_ready() -> None:
    if bot_settings.discord_guild_id is not None:
        guild = discord.Object(id=bot_settings.discord_guild_id)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
    else:
        await tree.sync()
    logger.info("discord_bot_ready user=%s", client.user)


@tree.command(name="ask", description="Ask the Deepwoken knowledge base")  # type: ignore[untyped-decorator]
@app_commands.describe(question="Question about Deepwoken")  # type: ignore[untyped-decorator]
async def ask(interaction: discord.Interaction, question: str) -> None:
    if len(question) > 2000:
        await interaction.response.send_message("Question is too long.", ephemeral=True)
        return

    user_key = str(interaction.user.id)
    if not rate_limiter.allow(user_key):
        await interaction.response.send_message(
            "Rate limit reached. Try again soon.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        payload = await rag_client.ask(question, bot_settings.bot_default_top_k)
    except (httpx.HTTPError, ValueError):
        logger.exception("rag_api_request_failed")
        await interaction.followup.send(
            "The knowledge base is unavailable right now. Try again soon.",
            ephemeral=True,
        )
        return

    await interaction.followup.send(format_ask_response(payload))


def main() -> None:
    if not bot_settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    client.run(bot_settings.discord_bot_token)


if __name__ == "__main__":
    main()
