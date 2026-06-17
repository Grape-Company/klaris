from __future__ import annotations

import structlog
from discord import Activity, ActivityType, Intents, Object
from discord.ext import commands

from bot.cogs.admin import AdminCog
from bot.cogs.ask import AskCog
from bot.cogs.chat import ChatCog, ConversationStore
from bot.cogs.feedback_cog import FeedbackCog
from bot.cogs.help import HelpCog
from bot.cogs.invite import InviteCog
from bot.cogs.stats import StatsCog
from bot.cogs.utility import UtilityCog
from bot.config import bot_settings
from bot.guards import BotGuard, WindowRateLimiter
from bot.klaris_client import KlarisApiClient
from bot.notifications import BotNotifier

logger = structlog.get_logger()


class KlarisBot(commands.Bot):
    def __init__(self) -> None:
        intents = Intents.default()
        super().__init__(command_prefix="", intents=intents)
        self.klaris_client = KlarisApiClient(
            api_url=bot_settings.rag_api_url,
            timeout_seconds=bot_settings.bot_request_timeout_seconds,
            bot_api_key=bot_settings.bot_api_key,
            admin_api_key=bot_settings.admin_api_key,
        )

        blacklisted_users = _parse_blacklist(bot_settings.bot_blacklisted_users)
        blacklisted_guilds = _parse_blacklist(bot_settings.bot_blacklisted_guilds)

        self.bot_guard = BotGuard(
            user_limiter=WindowRateLimiter(
                limit=bot_settings.bot_rate_limit_count,
                window_seconds=bot_settings.bot_rate_limit_window_seconds,
            ),
            channel_limiter=WindowRateLimiter(
                limit=bot_settings.bot_channel_rate_limit_count,
                window_seconds=bot_settings.bot_channel_rate_limit_window_seconds,
            ),
            global_limiter=WindowRateLimiter(
                limit=bot_settings.bot_global_rate_limit_count,
                window_seconds=bot_settings.bot_global_rate_limit_window_seconds,
            ),
            blacklisted_users=blacklisted_users,
            blacklisted_guilds=blacklisted_guilds,
        )

        self.notifier = BotNotifier(
            bot=self,
            log_channel_id=bot_settings.bot_log_channel_id,
        )

        self.conversation_store = ConversationStore(
            max_turns=bot_settings.bot_context_max_turns,
        )

    async def setup_hook(self) -> None:
        await self.add_cog(AskCog(self, self.klaris_client))
        await self.add_cog(ChatCog(
            self,
            self.klaris_client,
            conversation_store=self.conversation_store,
        ))
        await self.add_cog(HelpCog(self))
        await self.add_cog(StatsCog(self))
        await self.add_cog(InviteCog(self))
        await self.add_cog(FeedbackCog(self))
        await self.add_cog(UtilityCog(self))
        await self.add_cog(AdminCog(self))

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

        await self.notifier.on_bot_started()

    async def close(self) -> None:
        await self.klaris_client.close()
        await super().close()


def _parse_blacklist(raw: str) -> set[str]:
    if not raw or not raw.strip():
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


bot = KlarisBot()


def main() -> None:
    if not bot_settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(bot_settings.discord_bot_token)


if __name__ == "__main__":
    main()
