from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    admin_api_key: str = ""

    database_url: str = "postgresql+asyncpg://deepwoken:deepwoken@localhost:5432/deepwoken"
    database_sync_url: str = "postgresql://deepwoken:deepwoken@localhost:5432/deepwoken"
    database_ssl: bool = False
    database_ssl_verify: bool = True

    mediawiki_api_url: str = "https://deepwoken.fandom.com/api.php"
    crawler_user_agent: str = "DeepwokenRAGBot/0.1"
    crawler_delay_seconds: float = 0.5
    crawler_max_retries: int = 3
    crawler_timeout_seconds: int = 30

    openai_api_key: str = ""
    openai_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    rag_top_k: int = 8
    rag_max_tokens: int = 1024
    rag_request_timeout_seconds: float = 30.0
    rag_max_answer_chars: int = 1800

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    enable_docs: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
