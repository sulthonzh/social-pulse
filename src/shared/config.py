from pydantic_settings import BaseSettings


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

    max_crawl_results: int = 1000
    crawl_timeout_seconds: int = 30
    ai_max_retries: int = 3
    gold_rebuild_batch_size: int = 10000


settings = Settings()
