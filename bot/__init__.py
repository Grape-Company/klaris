"""Discord bot package for Deepwoken RAG."""

from bot.config import bot_settings
from bot.embeds import (
    build_answer_embed,
    build_error_embed,
    build_help_embed,
    build_not_found_embed,
    build_stats_embed,
)
from bot.i18n import DEFAULT_LANG, gettext
from bot.klaris_client import KlarisApiClient

__all__ = [
    "bot_settings",
    "KlarisApiClient",
    "build_answer_embed",
    "build_error_embed",
    "build_help_embed",
    "build_stats_embed",
    "build_not_found_embed",
    "gettext",
    "DEFAULT_LANG",
]
