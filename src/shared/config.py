from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    import duckdb


class Settings(BaseSettings):
    model_config = {"env_prefix": "SOCIALPULSE_"}

    env: str = "development"
    db_path: str = "data/socialpulse.duckdb"
    log_level: str = "INFO"

    twitter_bearer_token: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""

    hf_model_cache_dir: str = ".cache/huggingface"
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    topic_model: str = "all-MiniLM-L6-v2"

    ai_provider: str = "local"  # "local" or "zai"
    zai_api_key: str = ""
    zai_base_url: str = "https://api.z.ai/api/coding/paas/v4"
    zai_model: str = "glm-4.7"

    max_crawl_results: int = 1000
    crawl_timeout_seconds: int = 30
    ai_max_retries: int = 3
    gold_rebuild_batch_size: int = 10000


settings = Settings()

_db_migrated: bool = False


def get_db_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, running migrations once on first call."""
    import duckdb  # noqa: PLC0415

    from src.infrastructure.persistence.migrations import create_all_tables  # noqa: PLC0415

    global _db_migrated  # noqa: PLW0603

    conn = duckdb.connect(str(settings.db_path), read_only=read_only)

    if not _db_migrated and not read_only:
        create_all_tables(conn)
        _db_migrated = True

    return conn
