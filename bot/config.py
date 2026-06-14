from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    discord_bot_token: str = ""
    discord_guild_id: int | None = None
    rag_api_url: str = "http://app:8000"
    bot_request_timeout_seconds: float = 30.0
    bot_rate_limit_count: int = 5
    bot_rate_limit_window_seconds: int = 60
    bot_default_top_k: int = 8

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


bot_settings = BotSettings()
