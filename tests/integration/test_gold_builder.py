from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import duckdb
import pytest
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.gold.builder import GoldBuilder
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.migrations import create_all_tables


def _insert_completed_search_request(
    conn: duckdb.DuckDBPyConnection,
    *,
    keyword: str = "python",
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2025, 1, 31),
) -> str:
    request_id = str(uuid4())
    conn.execute(
        "INSERT INTO bronze.search_requests "
        "(id, keyword, start_date, end_date, platform, status, posts_found) "
        "VALUES (?, ?, ?, ?, 'twitter', 'completed', 3)",
        [request_id, keyword, start_date, end_date],
    )
    return request_id


def _insert_enriched_posts(
    conn: duckdb.DuckDBPyConnection,
    search_request_id: str,
    count: int = 3,
) -> list[EnrichedPost]:
    enriched_repo = DuckDBEnrichedPostRepository(conn)
    posts = [
        EnrichedPost(
            bronze_post_id=uuid4(),
            search_request_id=UUID(search_request_id),
            platform=Platform.TWITTER if i % 2 == 0 else Platform.FACEBOOK,
            platform_id=f"post-{uuid4().hex[:8]}",
            author_handle=f"user_{i}",
            author_name=f"User {i}",
            post_text=f"Post content {i} about python",
            posted_at=datetime(2025, 1, 15 + (i % 3), 10 + i, 0, 0),
            like_count=10 * (i + 1),
            share_count=5 * (i + 1),
            reply_count=2 * (i + 1),
            view_count=100 * (i + 1),
            post_url=f"https://example.com/post/{i}",
        )
        for i in range(count)
    ]
    enriched_repo.save_batch(posts)
    return posts


def _insert_ai_enrichments(
    conn: duckdb.DuckDBPyConnection,
    posts: list[EnrichedPost],
) -> None:
    ai_repo = DuckDBAIEnrichmentRepository(conn)
    sentiments = [SentimentLabel.POSITIVE, SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL]
    for i, post in enumerate(posts):
        ai_repo.save(
            AIEnrichment(
                silver_post_id=post.id,
                hashtags=[f"tag{i}", "python"],
                mentions=["@friend"],
                language="en",
                topic_label="technology" if i % 2 == 0 else "business",
                sentiment=sentiments[i % 3],
                sentiment_confidence=0.85 + (i * 0.02),
            )
        )


@pytest.mark.integration
async def test_builder_initialization(db_with_schema: duckdb.DuckDBPyConnection):
    builder = GoldBuilder(db_with_schema)

    request_id = _insert_completed_search_request(db_with_schema, keyword="init_test")
    posts = _insert_enriched_posts(db_with_schema, request_id, count=1)
    _insert_ai_enrichments(db_with_schema, posts)

    await builder.run()

    row = db_with_schema.execute(
        "SELECT count(*) FROM gold.gold_post_search WHERE search_request_id = ?",
        [request_id],
    ).fetchone()
    assert row is not None
    assert row[0] == 1


@pytest.mark.integration
async def test_builder_happy_path_populates_gold_tables(
    db_with_schema: duckdb.DuckDBPyConnection,
):
    request_id = _insert_completed_search_request(db_with_schema)
    posts = _insert_enriched_posts(db_with_schema, request_id, count=3)
    _insert_ai_enrichments(db_with_schema, posts)

    builder = GoldBuilder(db_with_schema)
    await builder.run()

    search_rows = db_with_schema.execute(
        "SELECT id, keyword, sentiment, topic_label "
        "FROM gold.gold_post_search "
        "WHERE search_request_id = ?",
        [request_id],
    ).fetchall()
    assert len(search_rows) == 3
    sentiments = {row[2] for row in search_rows}
    assert sentiments == {"positive", "negative", "neutral"}
    assert all(row[1] == "python" for row in search_rows)

    daily_rows = db_with_schema.execute(
        "SELECT date, total_posts, positive_count, negative_count, neutral_count "
        "FROM gold.gold_campaign_daily "
        "WHERE search_request_id = ?",
        [request_id],
    ).fetchall()
    assert len(daily_rows) >= 1
    total_posts = sum(row[1] for row in daily_rows)
    assert total_posts == 3

    summary_row = db_with_schema.execute(
        "SELECT keyword, total_posts, positive_pct, negative_pct, neutral_pct, "
        "       total_likes, total_shares, total_replies, total_views, platforms "
        "FROM gold.gold_campaign_summary "
        "WHERE search_request_id = ?",
        [request_id],
    ).fetchone()
    assert summary_row is not None
    assert summary_row[0] == "python"
    assert summary_row[1] == 3
    assert round(summary_row[2], 2) == 33.33
    assert round(summary_row[3], 2) == 33.33
    assert round(summary_row[4], 2) == 33.33
    assert summary_row[5] == 60  # 10+20+30
    assert summary_row[6] == 30  # 5+10+15
    assert summary_row[7] == 12  # 2+4+6
    assert summary_row[8] == 600  # 100+200+300
    assert sorted(summary_row[9]) == ["facebook", "twitter"]


@pytest.mark.integration
async def test_builder_handles_empty_silver_data_gracefully(
    db_with_schema: duckdb.DuckDBPyConnection,
):
    _insert_completed_search_request(db_with_schema, keyword="empty_test")

    builder = GoldBuilder(db_with_schema)
    await builder.run()

    search_rows = db_with_schema.execute(
        "SELECT count(*) FROM gold.gold_post_search",
    ).fetchone()
    assert search_rows is not None
    assert search_rows[0] == 0

    daily_rows = db_with_schema.execute(
        "SELECT count(*) FROM gold.gold_campaign_daily",
    ).fetchone()
    assert daily_rows is not None
    assert daily_rows[0] == 0

    summary_row = db_with_schema.execute(
        "SELECT total_posts FROM gold.gold_campaign_summary",
    ).fetchone()
    assert summary_row is not None
    assert summary_row[0] == 0


@pytest.mark.integration
async def test_builder_gold_post_search_schema(
    db_with_schema: duckdb.DuckDBPyConnection,
):
    request_id = _insert_completed_search_request(db_with_schema)
    posts = _insert_enriched_posts(db_with_schema, request_id, count=1)
    _insert_ai_enrichments(db_with_schema, posts)

    builder = GoldBuilder(db_with_schema)
    await builder.run()

    columns = db_with_schema.execute(
        "SELECT column_name, data_type "
        "FROM information_schema.columns "
        "WHERE table_schema = 'gold' AND table_name = 'gold_post_search' "
        "ORDER BY ordinal_position",
    ).fetchall()
    col_map = {row[0]: row[1] for row in columns}

    assert "id" in col_map
    assert "search_request_id" in col_map
    assert "keyword" in col_map
    assert "platform" in col_map
    assert "sentiment" in col_map
    assert "sentiment_confidence" in col_map
    assert "topic_label" in col_map
    assert "language" in col_map
    assert "hashtags" in col_map
    assert "like_count" in col_map
    assert "share_count" in col_map
    assert "reply_count" in col_map
    assert "view_count" in col_map
    assert "posted_at" in col_map
    assert "post_text" in col_map
    assert "author_handle" in col_map
    assert "author_name" in col_map

    row = db_with_schema.execute(
        "SELECT keyword, platform, sentiment, language, like_count "
        "FROM gold.gold_post_search "
        "WHERE search_request_id = ?",
        [request_id],
    ).fetchone()
    assert row is not None
    assert row[0] == "python"
    assert row[1] == "twitter"
    assert row[2] == "positive"
    assert row[3] == "en"
    assert row[4] == 10


@pytest.mark.integration
async def test_builder_skips_non_completed_requests(
    db_with_schema: duckdb.DuckDBPyConnection,
):
    conn = db_with_schema
    pending_id = str(uuid4())
    conn.execute(
        "INSERT INTO bronze.search_requests "
        "(id, keyword, start_date, end_date, platform, status, posts_found) "
        "VALUES (?, 'pending_kw', '2025-01-01', '2025-01-31', 'twitter', 'pending', 0)",
        [pending_id],
    )

    posts = _insert_enriched_posts(conn, pending_id, count=2)
    _insert_ai_enrichments(conn, posts)

    builder = GoldBuilder(conn)
    await builder.run()

    gold_count = conn.execute(
        "SELECT count(*) FROM gold.gold_post_search WHERE search_request_id = ?",
        [pending_id],
    ).fetchone()
    assert gold_count is not None
    assert gold_count[0] == 0


@pytest.mark.integration
async def test_builder_raises_on_closed_connection(
    db_connection: duckdb.DuckDBPyConnection,
):
    create_all_tables(db_connection)
    db_connection.close()

    builder = GoldBuilder(db_connection)

    with pytest.raises(duckdb.ConnectionException):
        await builder.run()


@pytest.mark.integration
async def test_builder_processes_multiple_campaigns(
    db_with_schema: duckdb.DuckDBPyConnection,
):
    request_id_a = _insert_completed_search_request(db_with_schema, keyword="django")
    posts_a = _insert_enriched_posts(db_with_schema, request_id_a, count=2)
    _insert_ai_enrichments(db_with_schema, posts_a)

    request_id_b = _insert_completed_search_request(db_with_schema, keyword="flask")
    posts_b = _insert_enriched_posts(db_with_schema, request_id_b, count=2)
    _insert_ai_enrichments(db_with_schema, posts_b)

    builder = GoldBuilder(db_with_schema)
    await builder.run()

    gold_posts = db_with_schema.execute(
        "SELECT keyword, count(*) FROM gold.gold_post_search GROUP BY keyword ORDER BY keyword",
    ).fetchall()
    assert len(gold_posts) == 2
    keywords = {row[0]: row[1] for row in gold_posts}
    assert keywords["django"] == 2
    assert keywords["flask"] == 2

    summaries = db_with_schema.execute(
        "SELECT keyword, total_posts FROM gold.gold_campaign_summary ORDER BY keyword",
    ).fetchall()
    assert len(summaries) == 2
    assert summaries[0][0] == "django"
    assert summaries[0][1] == 2
    assert summaries[1][0] == "flask"
    assert summaries[1][1] == 2
