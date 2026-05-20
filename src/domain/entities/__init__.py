from __future__ import annotations

from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.ai_job import AIJob
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.entities.gold_campaign_summary import GoldCampaignSummary
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.entities.language_result import LanguageResult
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.entities.sentiment_result import SentimentResult
from src.domain.entities.topic_result import TopicResult

__all__ = [
    "AIEnrichment",
    "AIJob",
    "CrawlRun",
    "EnrichedPost",
    "GoldCampaignDaily",
    "GoldCampaignSummary",
    "GoldPostSearch",
    "LanguageResult",
    "RawPost",
    "SearchRequest",
    "SentimentResult",
    "TopicResult",
]
