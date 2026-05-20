"""Database schema migrations for SocialPulse DuckDB backend.

Creates all tables organized by medallion architecture layers:
bronze (raw ingestion), silver (cleaned/enriched), gold (analytics),
and config (system configuration). All statements are idempotent.

This module is the single source of DDL truth, matching the PRD
authoritative schema definition exactly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

SCHEMA_VERSION: int = 1


def create_all_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all database schemas and tables if they do not exist."""
    _create_bronze_schema(conn)
    _create_silver_schema(conn)
    _create_gold_schema(conn)
    _create_config_schema(conn)


def _create_bronze_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.search_requests (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            keyword         VARCHAR NOT NULL,
            start_date      DATE NOT NULL,
            end_date        DATE NOT NULL,
            platform        VARCHAR DEFAULT 'twitter',
            status          VARCHAR DEFAULT 'pending',
            posts_found     INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT current_timestamp,
            updated_at      TIMESTAMP DEFAULT current_timestamp
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.bronze_crawl_runs (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            search_request_id UUID NOT NULL REFERENCES bronze.search_requests(id),
            platform          VARCHAR NOT NULL,
            status            VARCHAR DEFAULT 'running',
            posts_fetched     INTEGER DEFAULT 0,
            error_message     VARCHAR,
            started_at        TIMESTAMP DEFAULT current_timestamp,
            completed_at      TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.bronze_posts (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            search_request_id UUID NOT NULL REFERENCES bronze.search_requests(id),
            crawl_run_id      UUID NOT NULL REFERENCES bronze.bronze_crawl_runs(id),
            platform          VARCHAR NOT NULL,
            platform_id       VARCHAR,
            author_handle     VARCHAR,
            raw_payload       JSON,
            fetched_at        TIMESTAMP DEFAULT current_timestamp,
            UNIQUE(platform, platform_id)
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_posts_search_req"
        "    ON bronze.bronze_posts(search_request_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_posts_platform"
        "    ON bronze.bronze_posts(platform)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_posts_fetched"
        "    ON bronze.bronze_posts(fetched_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bronze_crawl_runs_search"
        "    ON bronze.bronze_crawl_runs(search_request_id)"
    )


def _create_silver_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS silver")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS silver.silver_posts (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bronze_post_id    UUID NOT NULL,
            search_request_id UUID NOT NULL,
            platform          VARCHAR NOT NULL,
            platform_id       VARCHAR,
            author_handle     VARCHAR,
            author_name       VARCHAR,
            post_text         VARCHAR,
            posted_at         TIMESTAMP,
            like_count        INTEGER DEFAULT 0,
            share_count       INTEGER DEFAULT 0,
            reply_count       INTEGER DEFAULT 0,
            view_count        INTEGER DEFAULT 0,
            post_url          VARCHAR,
            is_retweet        BOOLEAN DEFAULT FALSE,
            created_at        TIMESTAMP DEFAULT current_timestamp
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS silver.silver_ai_enrichment (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            silver_post_id           UUID NOT NULL REFERENCES silver.silver_posts(id),
            ai_version               INTEGER NOT NULL DEFAULT 1,
            hashtags                 VARCHAR[],
            mentions                 VARCHAR[],
            language                 VARCHAR(10),
            topic_label              VARCHAR,
            reach_estimate           BIGINT,
            sentiment                VARCHAR(20),
            sentiment_confidence     FLOAT,
            metadata_model_name      VARCHAR,
            metadata_model_version   VARCHAR,
            sentiment_model_name     VARCHAR,
            sentiment_model_version  VARCHAR,
            created_at               TIMESTAMP DEFAULT current_timestamp,
            UNIQUE(silver_post_id, ai_version)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS silver.ai_jobs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            silver_post_id  UUID NOT NULL REFERENCES silver.silver_posts(id),
            job_type        VARCHAR NOT NULL,
            status          VARCHAR DEFAULT 'pending',
            ai_version      INTEGER NOT NULL DEFAULT 1,
            attempts        INTEGER DEFAULT 0,
            max_attempts    INTEGER DEFAULT 3,
            error_message   VARCHAR,
            started_at      TIMESTAMP,
            completed_at    TIMESTAMP,
            created_at      TIMESTAMP DEFAULT current_timestamp
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_posts_bronze"
        "    ON silver.silver_posts(bronze_post_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_posts_search"
        "    ON silver.silver_posts(search_request_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_posts_platform"
        "    ON silver.silver_posts(platform)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_posts_posted"
        "    ON silver.silver_posts(posted_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_posts_author"
        "    ON silver.silver_posts(author_handle)"
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_enrichment_post"
        "    ON silver.silver_ai_enrichment(silver_post_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_enrichment_version"
        "    ON silver.silver_ai_enrichment(ai_version)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_enrichment_sentiment"
        "    ON silver.silver_ai_enrichment(sentiment)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_enrichment_lang"
        "    ON silver.silver_ai_enrichment(language)"
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_jobs_status"
        "    ON silver.ai_jobs(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_jobs_type_status"
        "    ON silver.ai_jobs(job_type, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_jobs_post"
        "    ON silver.ai_jobs(silver_post_id)"
    )


def _create_gold_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS gold")

    # Post Explorer - flat, filterable, physically ordered by recency
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.gold_post_search (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            search_request_id   UUID NOT NULL,
            keyword             VARCHAR NOT NULL,
            platform            VARCHAR NOT NULL,
            author_handle       VARCHAR,
            author_name         VARCHAR,
            post_text           VARCHAR,
            posted_at           TIMESTAMP,
            post_url            VARCHAR,
            sentiment           VARCHAR(20),
            sentiment_confidence FLOAT,
            topic_label         VARCHAR,
            language            VARCHAR(10),
            hashtags            VARCHAR[],
            mentions            VARCHAR[],
            like_count          INTEGER DEFAULT 0,
            share_count         INTEGER DEFAULT 0,
            reply_count         INTEGER DEFAULT 0,
            view_count          INTEGER DEFAULT 0,
            ai_version          INTEGER NOT NULL DEFAULT 1,
            created_at          TIMESTAMP DEFAULT current_timestamp
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_keyword"
        "    ON gold.gold_post_search(keyword)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_sentiment"
        "    ON gold.gold_post_search(sentiment)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_platform"
        "    ON gold.gold_post_search(platform)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_posted"
        "    ON gold.gold_post_search(posted_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_topic"
        "    ON gold.gold_post_search(topic_label)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_lang"
        "    ON gold.gold_post_search(language)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_post_search_request"
        "    ON gold.gold_post_search(search_request_id)"
    )

    # Campaign Analytics - daily aggregation
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.gold_campaign_daily (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            search_request_id   UUID NOT NULL,
            keyword             VARCHAR NOT NULL,
            platform            VARCHAR NOT NULL,
            date                DATE NOT NULL,
            total_posts         INTEGER NOT NULL DEFAULT 0,
            positive_count      INTEGER NOT NULL DEFAULT 0,
            negative_count      INTEGER NOT NULL DEFAULT 0,
            neutral_count       INTEGER NOT NULL DEFAULT 0,
            avg_confidence      FLOAT,
            top_hashtags        VARCHAR[],
            top_topics          VARCHAR[],
            total_likes         INTEGER DEFAULT 0,
            total_shares        INTEGER DEFAULT 0,
            total_replies       INTEGER DEFAULT 0,
            total_views         BIGINT DEFAULT 0,
            ai_version          INTEGER NOT NULL DEFAULT 1,
            created_at          TIMESTAMP DEFAULT current_timestamp,

            UNIQUE(search_request_id, platform, date)
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_campaign_daily_keyword"
        "    ON gold.gold_campaign_daily(keyword)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_campaign_daily_date"
        "    ON gold.gold_campaign_daily(date DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_campaign_daily_request"
        "    ON gold.gold_campaign_daily(search_request_id)"
    )

    # Cross-Campaign Comparison - per-campaign summary
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gold.gold_campaign_summary (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            search_request_id   UUID NOT NULL UNIQUE,
            keyword             VARCHAR NOT NULL,
            start_date          DATE NOT NULL,
            end_date            DATE NOT NULL,
            total_posts         INTEGER NOT NULL DEFAULT 0,
            positive_pct        FLOAT,
            negative_pct        FLOAT,
            neutral_pct         FLOAT,
            avg_confidence      FLOAT,
            total_engagement    BIGINT DEFAULT 0,
            total_likes         INTEGER DEFAULT 0,
            total_shares        INTEGER DEFAULT 0,
            total_replies       INTEGER DEFAULT 0,
            total_views         BIGINT DEFAULT 0,
            top_hashtags        VARCHAR[],
            top_topics          VARCHAR[],
            platforms           VARCHAR[],
            ai_version          INTEGER NOT NULL DEFAULT 1,
            created_at          TIMESTAMP DEFAULT current_timestamp
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_campaign_summary_keyword"
        "    ON gold.gold_campaign_summary(keyword)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gold_campaign_summary_dates"
        "    ON gold.gold_campaign_summary(start_date, end_date)"
    )


def _create_config_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS config")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config.ai_active_versions (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            model_type          VARCHAR NOT NULL,
            model_name          VARCHAR NOT NULL,
            model_version       VARCHAR NOT NULL,
            ai_version          INTEGER NOT NULL DEFAULT 1,
            is_active           BOOLEAN DEFAULT TRUE,
            activated_at        TIMESTAMP DEFAULT current_timestamp,

            UNIQUE(model_type, ai_version)
        )
        """
    )
