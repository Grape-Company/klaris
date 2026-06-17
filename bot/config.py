from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    discord_bot_token: str = ""
    discord_guild_id: int | None = Field(default=None)
    rag_api_url: str = "http://app:8000"
    bot_request_timeout_seconds: float = 30.0
    bot_rate_limit_count: int = 5
    bot_rate_limit_window_seconds: int = 60
    bot_default_top_k: int = 8

    admin_api_key: str = ""
    bot_api_key: str = ""

    discord_invite_url: str = ""
    bot_default_language: str = "pt-BR"

    bot_activity_type: str = "listening"
    bot_activity_text: str = "/ask"

    bot_context_ttl_seconds: int = 900
    bot_context_max_turns: int = 10

    bot_channel_rate_limit_count: int = 20
    bot_channel_rate_limit_window_seconds: int = 60
    bot_global_rate_limit_count: int = 50
    bot_global_rate_limit_window_seconds: int = 60

    bot_blacklisted_users: str = ""
    bot_blacklisted_guilds: str = ""
    bot_log_channel_id: int | None = Field(default=None)

    bot_response_cache_enabled: bool = True
    bot_response_cache_max_size: int = 128
    bot_response_cache_ttl_seconds: int = 600

    bot_context_backend: str = "in_memory"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )


bot_settings = BotSettings()
