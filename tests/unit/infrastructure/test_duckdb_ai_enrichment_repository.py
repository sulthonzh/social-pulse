from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
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


def _make_enriched_post(**overrides) -> EnrichedPost:
    defaults = {
        "id": uuid4(),
        "bronze_post_id": uuid4(),
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
        "platform_id": f"tweet_{uuid4().hex[:8]}",
        "author_handle": "testuser",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return EnrichedPost(**defaults)


def _insert_silver_post(db_with_schema, **overrides) -> EnrichedPost:
    post_repo = DuckDBEnrichedPostRepository(db_with_schema)
    post = _make_enriched_post(**overrides)
    post_repo.save(post)
    return post


def _make_ai_enrichment(silver_post_id, **overrides) -> AIEnrichment:
    defaults = {
        "id": uuid4(),
        "silver_post_id": silver_post_id,
        "ai_version": 1,
        "hashtags": ["python", "data"],
        "mentions": ["@user1", "@user2"],
        "language": "en",
        "topic_label": "technology",
        "reach_estimate": 1000,
        "sentiment": SentimentLabel.POSITIVE,
        "sentiment_confidence": 0.95,
        "metadata_model_name": "bert-base",
        "metadata_model_version": "1.0",
        "sentiment_model_name": "sentiment-v1",
        "sentiment_model_version": "1.0",
        "created_at": datetime(2025, 1, 15, 14, 0, 0),
    }
    defaults.update(overrides)
    return AIEnrichment(**defaults)


@pytest.mark.unit
class TestDuckDBAIEnrichmentRepository:
    def test_save_returns_entity_with_id(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        enrichment = _make_ai_enrichment(post.id)
        result = repo.save(enrichment)
        assert result.id == enrichment.id

    def test_get_by_post_returns_saved_entity(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        enrichment = _make_ai_enrichment(post.id)
        repo.save(enrichment)

        found = repo.get_by_post(str(post.id))
        assert found is not None
        assert found.id == enrichment.id

    def test_get_by_post_returns_none_for_nonexistent(self, db_with_schema):
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        assert repo.get_by_post(str(uuid4())) is None

    def test_get_by_post_with_ai_version(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        e_v1 = _make_ai_enrichment(post.id, ai_version=1)
        e_v2 = _make_ai_enrichment(post.id, ai_version=2)
        repo.save(e_v1)
        repo.save(e_v2)

        found_v1 = repo.get_by_post(str(post.id), ai_version=1)
        found_v2 = repo.get_by_post(str(post.id), ai_version=2)
        assert found_v1 is not None
        assert found_v1.ai_version == 1
        assert found_v2 is not None
        assert found_v2.ai_version == 2

    def test_get_by_search_returns_filtered_results(self, db_with_schema):
        sr_id = uuid4()
        post1 = _insert_silver_post(db_with_schema, search_request_id=sr_id)
        post2 = _insert_silver_post(db_with_schema, search_request_id=sr_id)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        repo.save(_make_ai_enrichment(post1.id))
        repo.save(_make_ai_enrichment(post2.id))

        results = repo.get_by_search(str(sr_id))
        assert len(results) == 2

    def test_get_by_search_returns_empty_for_nonexistent(self, db_with_schema):
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        results = repo.get_by_search(str(uuid4()))
        assert results == []

    def test_save_duplicate_returns_same_count(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        enrichment = _make_ai_enrichment(post.id)
        repo.save(enrichment)
        repo.save(enrichment)

        found = repo.get_by_post(str(post.id))
        assert found is not None
        assert found.id == enrichment.id

    def test_round_trip_all_fields_match(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        enrichment = _make_ai_enrichment(
            post.id,
            hashtags=["python", "ai", "ml"],
            mentions=["@alice", "@bob"],
            language="en",
            topic_label="machine_learning",
            reach_estimate=5000,
            sentiment=SentimentLabel.NEGATIVE,
            sentiment_confidence=0.87,
            metadata_model_name="meta-model",
            metadata_model_version="2.1",
            sentiment_model_name="sent-v2",
            sentiment_model_version="2.0",
            created_at=datetime(2025, 3, 20, 9, 30, 0),
        )
        repo.save(enrichment)

        found = repo.get_by_post(str(post.id))
        assert found is not None
        assert found.id == enrichment.id
        assert found.silver_post_id == enrichment.silver_post_id
        assert found.ai_version == enrichment.ai_version
        assert found.hashtags == enrichment.hashtags
        assert found.mentions == enrichment.mentions
        assert found.language == enrichment.language
        assert found.topic_label == enrichment.topic_label
        assert found.reach_estimate == enrichment.reach_estimate
        assert found.sentiment == enrichment.sentiment
        assert found.sentiment_confidence == pytest.approx(enrichment.sentiment_confidence)
        assert found.metadata_model_name == enrichment.metadata_model_name
        assert found.metadata_model_version == enrichment.metadata_model_version
        assert found.sentiment_model_name == enrichment.sentiment_model_name
        assert found.sentiment_model_version == enrichment.sentiment_model_version
        assert found.created_at == enrichment.created_at

    def test_get_by_search_filters_by_ai_version(self, db_with_schema):
        sr_id = uuid4()
        post = _insert_silver_post(db_with_schema, search_request_id=sr_id)
        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        repo.save(_make_ai_enrichment(post.id, ai_version=1))
        repo.save(_make_ai_enrichment(post.id, ai_version=2))

        results_v1 = repo.get_by_search(str(sr_id), ai_version=1)
        results_v2 = repo.get_by_search(str(sr_id), ai_version=2)
        assert len(results_v1) == 1
        assert len(results_v2) == 1
