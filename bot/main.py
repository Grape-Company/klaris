from __future__ import annotations

import structlog
from discord import Activity, ActivityType, Intents, Object
from discord.ext import commands

from bot.cogs.ask import AskCog
from bot.cogs.chat import ChatCog
from bot.cogs.feedback_cog import FeedbackCog
from bot.cogs.help import HelpCog
from bot.cogs.invite import InviteCog
from bot.cogs.stats import StatsCog
from bot.config import bot_settings
from bot.klaris_client import KlarisApiClient
from bot.rate_limit import UserRateLimiter

logger = structlog.get_logger()


class KlarisBot(commands.Bot):
    def __init__(self) -> None:
        intents = Intents.default()
        super().__init__(command_prefix="", intents=intents)
        self.klaris_client = KlarisApiClient(
            api_url=bot_settings.rag_api_url,
            timeout_seconds=bot_settings.bot_request_timeout_seconds,
            bot_api_key=bot_settings.bot_api_key,
        )
        self.user_rate_limiter = UserRateLimiter(
            limit=bot_settings.bot_rate_limit_count,
            window_seconds=bot_settings.bot_rate_limit_window_seconds,
        )

    async def setup_hook(self) -> None:
        await self.add_cog(AskCog(self, self.klaris_client, self.user_rate_limiter))
        await self.add_cog(ChatCog(self, self.klaris_client, rate_limiter=self.user_rate_limiter))
        await self.add_cog(HelpCog(self))
        await self.add_cog(StatsCog(self))
        await self.add_cog(InviteCog(self))
        await self.add_cog(FeedbackCog(self))

    async def on_ready(self) -> None:
        activity_text = bot_settings.bot_activity_text
        activity_type_str = bot_settings.bot_activity_type.lower()

        type_map = {
            "playing": ActivityType.playing,
            "listening": ActivityType.listening,
            "watching": ActivityType.watching,
            "competing": ActivityType.competing,
        }
        activity_type = type_map.get(activity_type_str, ActivityType.listening)

        await self.change_presence(
            activity=Activity(type=activity_type, name=activity_text),
        )

        guild_id = bot_settings.discord_guild_id
        if guild_id is not None:
            guild = Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        logger.info("bot_ready", user=str(self.user), guild_id=guild_id)

    async def close(self) -> None:
        await self.klaris_client.close()
        await super().close()


bot = KlarisBot()


def main() -> None:
    if not bot_settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(bot_settings.discord_bot_token)


if __name__ == "__main__":
    main()
