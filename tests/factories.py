"""Test factory functions for all domain entities.

Provides deterministic defaults with override support for every entity,
centralising construction logic that was previously duplicated across
individual test files.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from src.domain.entities.ai_job import AIJob
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.entities.gold_campaign_summary import GoldCampaignSummary
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.platform import Platform


def make_raw_post(**overrides: Any) -> RawPost:
    defaults: dict[str, Any] = {
        "search_request_id": uuid4(),
        "crawl_run_id": uuid4(),
        "platform": Platform.TWITTER,
    }
    defaults.update(overrides)
    return RawPost(**defaults)


def make_search_request(**overrides: Any) -> SearchRequest:
    defaults: dict[str, Any] = {
        "keyword": "test",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 31),
    }
    defaults.update(overrides)
    return SearchRequest(**defaults)


def make_enriched_post(**overrides: Any) -> EnrichedPost:
    defaults: dict[str, Any] = {
        "bronze_post_id": uuid4(),
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
    }
    defaults.update(overrides)
    return EnrichedPost(**defaults)


def make_crawl_run(**overrides: Any) -> CrawlRun:
    defaults: dict[str, Any] = {
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
    }
    defaults.update(overrides)
    return CrawlRun(**defaults)


def make_ai_job(**overrides: Any) -> AIJob:
    defaults: dict[str, Any] = {
        "silver_post_id": uuid4(),
        "job_type": AIJobType.FULL_ENRICHMENT,
    }
    defaults.update(overrides)
    return AIJob(**defaults)


def make_gold_post_search(**overrides: Any) -> GoldPostSearch:
    defaults: dict[str, Any] = {
        "search_request_id": uuid4(),
        "keyword": "test",
        "platform": Platform.TWITTER,
        "source_crawl_run_id": None,
        "enrichment_job_id": None,
        "lineage_updated_at": None,
    }
    defaults.update(overrides)
    return GoldPostSearch(**defaults)


def make_gold_campaign_daily(**overrides: Any) -> GoldCampaignDaily:
    defaults: dict[str, Any] = {
        "search_request_id": uuid4(),
        "keyword": "test",
        "platform": Platform.TWITTER,
        "date": date(2024, 1, 15),
        "source_crawl_run_id": None,
        "enrichment_job_id": None,
        "lineage_updated_at": None,
    }
    defaults.update(overrides)
    return GoldCampaignDaily(**defaults)


def make_gold_campaign_summary(**overrides: Any) -> GoldCampaignSummary:
    defaults: dict[str, Any] = {
        "search_request_id": uuid4(),
        "keyword": "test",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 31),
        "source_crawl_run_id": None,
        "enrichment_job_id": None,
        "lineage_updated_at": None,
    }
    defaults.update(overrides)
    return GoldCampaignSummary(**defaults)
