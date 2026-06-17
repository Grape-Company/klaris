"""Discord bot package for Deepwoken RAG."""

from bot.config import bot_settings
from bot.embeds import (
    build_answer_embed,
    build_error_embed,
    build_help_embed,
    build_not_found_embed,
    build_stats_embed,
)
from bot.guards import BotGuard, GuardResult, WindowRateLimiter
from bot.i18n import DEFAULT_LANG, gettext
from bot.klaris_client import KlarisApiClient
from bot.notifications import BotNotifier

__all__ = [
    "bot_settings",
    "KlarisApiClient",
    "BotGuard",
    "GuardResult",
    "WindowRateLimiter",
    "BotNotifier",
    "build_answer_embed",
    "build_error_embed",
    "build_help_embed",
    "build_stats_embed",
    "build_not_found_embed",
    "gettext",
    "DEFAULT_LANG",
]
