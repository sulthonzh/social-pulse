"""Performance benchmarks for SocialPulse pipeline operations.

Run with: uv run pytest tests/integration/test_benchmarks.py -v -m slow
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
import structlog
from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.application.use_cases.build_post_search import BuildPostSearch
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_daily_repository import (
    DuckDBGoldCampaignDailyRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_summary_repository import (
    DuckDBGoldCampaignSummaryRepository,
)
from src.infrastructure.persistence.duckdb_gold_post_search_repository import (
    DuckDBGoldPostSearchRepository,
)

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger(__name__)

pytestmark = pytest.mark.slow

_SENTIMENTS = [SentimentLabel.POSITIVE, SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL]
_PLATFORMS = [Platform.TWITTER, Platform.FACEBOOK, Platform.REDDIT]
_TOPICS = ["technology", "business", "science", "politics", "health"]


def _seed_search_request(
    conn: duckdb.DuckDBPyConnection,
    keyword: str = "benchmark",
    start_date: date = date(2024, 1, 1),
    end_date: date = date(2024, 12, 31),
) -> str:
    request_id = str(uuid4())
    conn.execute(
        "INSERT INTO bronze.search_requests "
        "(id, keyword, start_date, end_date, platform, status, posts_found) "
        "VALUES (?, ?, ?, ?, 'twitter', 'completed', 0)",
        [request_id, keyword, start_date, end_date],
    )
    return request_id


def _seed_silver_posts(
    conn: duckdb.DuckDBPyConnection,
    count: int,
    search_request_id: str,
) -> list[str]:
    enriched_repo = DuckDBEnrichedPostRepository(conn)
    silver_ids: list[str] = []
    batch_size = 200

    for offset in range(0, count, batch_size):
        batch = min(batch_size, count - offset)
        posts: list[EnrichedPost] = []
        for i in range(batch):
            idx = offset + i
            post = EnrichedPost(
                bronze_post_id=uuid4(),
                search_request_id=UUID(search_request_id),
                platform=_PLATFORMS[idx % len(_PLATFORMS)],
                platform_id=f"pid_{idx}",
                author_handle=f"user_{idx}",
                author_name=f"User {idx}",
                post_text=f"Benchmark post content {idx} about data engineering",
                posted_at=datetime(2024, 1, 1, 10, idx % 60, 0) + timedelta(days=idx % 365),
                like_count=idx % 100,
                share_count=idx % 50,
                reply_count=idx % 20,
                view_count=idx * 10,
                post_url=f"https://example.com/post/{idx}",
            )
            posts.append(post)
            silver_ids.append(str(post.id))
        enriched_repo.save_batch(posts)

    return silver_ids


def _seed_ai_enrichments(
    conn: duckdb.DuckDBPyConnection,
    silver_ids: list[str],
) -> None:
    ai_repo = DuckDBAIEnrichmentRepository(conn)
    batch_size = 200

    for offset in range(0, len(silver_ids), batch_size):
        batch_ids = silver_ids[offset : offset + batch_size]
        for local_i, sid in enumerate(batch_ids):
            idx = offset + local_i
            enrichment = AIEnrichment(
                silver_post_id=UUID(sid),
                hashtags=[f"tag{idx % 10}", "benchmark"],
                mentions=[f"@user_{idx % 5}"],
                language="en",
                topic_label=_TOPICS[idx % len(_TOPICS)],
                sentiment=_SENTIMENTS[idx % len(_SENTIMENTS)],
                sentiment_confidence=0.80 + (idx % 20) * 0.01,
            )
            ai_repo.save(enrichment)


def _seed_gold_posts(
    conn: duckdb.DuckDBPyConnection,
    count: int,
    search_request_id: str,
    keyword: str = "benchmark",
) -> None:
    batch_size = 500
    for offset in range(0, count, batch_size):
        batch = min(batch_size, count - offset)
        values: list[list[object]] = []
        for i in range(batch):
            idx = offset + i
            values.append(
                [
                    str(uuid4()),
                    search_request_id,
                    keyword,
                    _PLATFORMS[idx % len(_PLATFORMS)].value,
                    f"user_{idx}",
                    f"User {idx}",
                    f"Gold post content {idx} about data engineering",
                    datetime(2024, 1, 1, 10, idx % 60, 0) + timedelta(days=idx % 365),
                    f"https://example.com/post/{idx}",
                    _SENTIMENTS[idx % 3].value,
                    0.80 + (idx % 20) * 0.01,
                    _TOPICS[idx % len(_TOPICS)],
                    None,
                    "en",
                    [f"tag{idx % 10}", "benchmark"],
                    [f"@user_{idx % 5}"],
                    idx % 100,
                    idx % 50,
                    idx % 20,
                    idx * 10,
                    1,
                    datetime.now(UTC),
                ]
            )
        conn.executemany(
            "INSERT INTO gold.gold_post_search "
            "(id, search_request_id, keyword, platform, "
            "author_handle, author_name, post_text, posted_at, post_url, "
            "sentiment, sentiment_confidence, topic_label, topic_confidence, language, "
            "hashtags, mentions, "
            "like_count, share_count, reply_count, view_count, "
            "ai_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )


def _build_post_search_use_case(
    conn: duckdb.DuckDBPyConnection,
) -> BuildPostSearch:
    return BuildPostSearch(
        DuckDBEnrichedPostRepository(conn),
        DuckDBAIEnrichmentRepository(conn),
        DuckDBGoldPostSearchRepository(conn),
    )


async def test_enrichment_throughput(db_with_schema: duckdb.DuckDBPyConnection) -> None:
    conn = db_with_schema
    request_id = _seed_search_request(conn)
    count = 500

    start = time.perf_counter()
    silver_ids = _seed_silver_posts(conn, count, request_id)
    _seed_ai_enrichments(conn, silver_ids)
    elapsed = time.perf_counter() - start

    throughput = count / elapsed if elapsed > 0 else 0
    logger.info(
        "enrichment_throughput",
        count=count,
        elapsed_s=round(elapsed, 4),
        posts_per_sec=round(throughput, 2),
    )
    assert throughput > 0
    assert len(silver_ids) == count


async def test_gold_build_performance(db_with_schema: duckdb.DuckDBPyConnection) -> None:
    conn = db_with_schema
    request_id = _seed_search_request(conn, keyword="gold_perf")
    silver_ids = _seed_silver_posts(conn, 500, request_id)
    _seed_ai_enrichments(conn, silver_ids)

    use_case = _build_post_search_use_case(conn)

    start = time.perf_counter()
    inserted = await use_case.execute(request_id, "gold_perf")
    elapsed = time.perf_counter() - start

    throughput = inserted / elapsed if elapsed > 0 else 0
    logger.info(
        "gold_build_performance",
        inserted=inserted,
        elapsed_s=round(elapsed, 4),
        posts_per_sec=round(throughput, 2),
    )
    assert inserted > 0


async def test_gold_build_at_scale(db_with_schema: duckdb.DuckDBPyConnection) -> None:
    conn = db_with_schema
    request_id = _seed_search_request(conn, keyword="scale_test")
    silver_ids = _seed_silver_posts(conn, 5000, request_id)
    _seed_ai_enrichments(conn, silver_ids)

    use_case = _build_post_search_use_case(conn)

    start = time.perf_counter()
    inserted = await use_case.execute(request_id, "scale_test")
    elapsed = time.perf_counter() - start

    throughput = inserted / elapsed if elapsed > 0 else 0
    logger.info(
        "gold_build_at_scale",
        inserted=inserted,
        elapsed_s=round(elapsed, 4),
        posts_per_sec=round(throughput, 2),
    )
    assert inserted == 5000


async def test_dashboard_query_latency(db_with_schema: duckdb.DuckDBPyConnection) -> None:
    conn = db_with_schema
    request_id = _seed_search_request(conn, keyword="dash_test")
    _seed_gold_posts(conn, 10_000, request_id, keyword="dash_test")

    repo = DuckDBGoldPostSearchRepository(conn)
    measurements: list[tuple[str, float]] = []

    start = time.perf_counter()
    result = repo.get_by_keyword("dash_test", limit=50)
    measurements.append(("keyword_filter", time.perf_counter() - start))
    assert len(result) == 50

    start = time.perf_counter()
    breakdown = repo.get_sentiment_breakdown("dash_test")
    measurements.append(("sentiment_breakdown", time.perf_counter() - start))
    assert len(breakdown) > 0

    start = time.perf_counter()
    filtered = repo.get_filtered("dash_test", sentiment="positive")
    measurements.append(("filtered_sentiment", time.perf_counter() - start))
    assert len(filtered) > 0

    start = time.perf_counter()
    by_platform = repo.get_filtered("dash_test", platform="twitter")
    measurements.append(("filtered_platform", time.perf_counter() - start))
    assert len(by_platform) > 0

    start = time.perf_counter()
    posts, total = repo.search_posts("data", None, None, None, None, 0, 50)
    measurements.append(("full_text_search", time.perf_counter() - start))
    assert total > 0
    assert len(posts) > 0

    for name, elapsed in measurements:
        logger.info(
            "dashboard_query_latency",
            query=name,
            elapsed_ms=round(elapsed * 1000, 2),
        )


async def test_incremental_gold_build(db_with_schema: duckdb.DuckDBPyConnection) -> None:
    conn = db_with_schema
    request_id = _seed_search_request(conn, keyword="incremental")
    silver_ids = _seed_silver_posts(conn, 500, request_id)
    _seed_ai_enrichments(conn, silver_ids)

    use_case = _build_post_search_use_case(conn)
    gold_repo = DuckDBGoldPostSearchRepository(conn)
    daily_repo = DuckDBGoldCampaignDailyRepository(conn)
    summary_repo = DuckDBGoldCampaignSummaryRepository(conn)

    build_daily = BuildCampaignDaily(gold_repo, daily_repo)
    build_summary = BuildCampaignSummary(gold_repo, summary_repo)

    start = time.perf_counter()
    first_count = await use_case.execute(request_id, "incremental")
    await build_daily.execute(request_id)
    await build_summary.execute(request_id, date(2024, 1, 1), date(2024, 12, 31))
    first_elapsed = time.perf_counter() - start

    assert first_count > 0

    gold_repo.delete_by_search_request(request_id)

    start = time.perf_counter()
    second_count = await use_case.execute(request_id, "incremental")
    await build_daily.execute(request_id)
    await build_summary.execute(request_id, date(2024, 1, 1), date(2024, 12, 31))
    second_elapsed = time.perf_counter() - start

    assert second_count > 0

    ratio = second_elapsed / first_elapsed if first_elapsed > 0 else 0
    logger.info(
        "incremental_gold_build",
        first_elapsed_s=round(first_elapsed, 4),
        second_elapsed_s=round(second_elapsed, 4),
        ratio=round(ratio, 2),
        first_count=first_count,
        second_count=second_count,
    )
    assert ratio < 5.0
