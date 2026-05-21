# ruff: noqa: S311
from __future__ import annotations

import logging
import random
import re
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from src.domain.entities.raw_post import RawPost
from src.infrastructure.crawling.base import BaseCrawler

if TYPE_CHECKING:
    from src.domain.value_objects.platform import Platform

logger = logging.getLogger(__name__)

_AUTHORS = [
    {"handle": "@dataengineer_pro", "name": "Data Engineer Pro"},
    {"handle": "@ml_researcher", "name": "ML Research Hub"},
    {"handle": "@pythondaily", "name": "Python Daily"},
    {"handle": "@cloudnative_dev", "name": "Cloud Native Dev"},
    {"handle": "@secops_analyst", "name": "SecOps Analyst"},
    {"handle": "@techlead_sarah", "name": "Sarah Chen"},
    {"handle": "@devops_mike", "name": "Mike Rodriguez"},
    {"handle": "@ai_startup_ceo", "name": "AI Startup CEO"},
    {"handle": "@opensource_fan", "name": "Open Source Fan"},
    {"handle": "@database_nerd", "name": "Database Nerd"},
    {"handle": "@infra_engineer", "name": "Infra Engineer"},
    {"handle": "@ml_ops_pete", "name": "MLOps Pete"},
    {"handle": "@sre_clara", "name": "Clara SRE"},
    {"handle": "@analytics_joe", "name": "Analytics Joe"},
    {"handle": "@platform_eng", "name": "Platform Eng"},
]

_MENTION_POOL = [
    "@tech_influencer",
    "@dev_community",
    "@openai",
    "@googledevs",
    "@awscloud",
    "@github",
    "@vectorhq",
    "@huggingface",
    "@kubernetesio",
    "@python_tip",
    "@rustlang",
    "@datascience",
    "@ml_daily",
    "@cpp_updates",
    "@webdev_hub",
]

_TEXT_TEMPLATES = [
    "Just discovered amazing insights about {keyword}. The future looks bright! #{hashtag}",
    "Working on a project related to {keyword}. Anyone have experience to share? #{hashtag}",
    "Hot take: {keyword} is going to change everything we know about this field. #{hashtag}",
    "Spent the weekend deep-diving into {keyword}. Here are my top 5 takeaways #{hashtag}",
    "{keyword} continues to evolve rapidly. Here's what I've learned in the past month. #{hashtag}",
    "Can we talk about how underrated {keyword} is? Most people don't realize its potential. #{hashtag}",
    "Just completed a certification in {keyword}. The exam was tough but worth it! #{hashtag}",
    "Our team just shipped a major {keyword} feature. 6 months of work, incredible results. #{hashtag}",
    "Reading the latest research paper on {keyword}. The methodology is fascinating. #{hashtag}",
    "Pro tip: If you're getting started with {keyword}, focus on fundamentals first. #{hashtag}",
    "The community around {keyword} is so welcoming. Grateful for all the mentors! #{hashtag}",
    "Benchmark results: {keyword} performance improved 40% after our latest optimization. #{hashtag}",
    "Debunking common myths about {keyword}. Number 3 will surprise you! #{hashtag}",
    "How we scaled our {keyword} infrastructure from 100 to 10M users. Thread below #{hashtag}",
    "Unpopular opinion: {keyword} is overrated. Here's what actually matters... #{hashtag}",
]

_HASHTAG_EXTRAS = [
    "tech",
    "coding",
    "development",
    "programming",
    "engineering",
    "data",
    "ai",
    "machinelearning",
    "opensource",
    "cloud",
    "devops",
    "software",
    "innovation",
    "learning",
    "community",
]


def _extract_hashtag(keyword: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", keyword).lower()


def _random_datetime(start: date, end: date) -> datetime:
    delta = (end - start).days
    offset_days = 0 if delta <= 0 else random.randint(0, delta)
    base = datetime(start.year, start.month, start.day, tzinfo=UTC)
    return base + timedelta(days=offset_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))


class SimulationCrawler(BaseCrawler):
    """Generate realistic social media posts from templates. No API keys needed."""

    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        count = min(max_results, random.randint(10, 25))
        hashtag = _extract_hashtag(keyword)

        posts: list[RawPost] = []
        for _ in range(count):
            author = random.choice(_AUTHORS)
            template = random.choice(_TEXT_TEMPLATES)
            text = template.format(keyword=keyword, hashtag=hashtag)

            extra_hashtags = random.sample(
                _HASHTAG_EXTRAS, k=random.randint(1, 3),
            )
            all_hashtags = list({hashtag, *extra_hashtags})

            mentions = random.sample(
                _MENTION_POOL, k=random.randint(1, 3),
            )

            posted_at = _random_datetime(start_date, end_date)
            post_id = str(uuid4())

            like_count = random.randint(0, 500)
            retweet_count = random.randint(0, 200)
            reply_count = random.randint(0, 100)
            impression_count = random.randint(100, 50_000)

            raw_payload = {
                "id": post_id,
                "text": text,
                "posted_at": posted_at.isoformat(),
                "author_id": author["handle"],
                "author_name": author["name"],
                "public_metrics": {
                    "like_count": like_count,
                    "retweet_count": retweet_count,
                    "reply_count": reply_count,
                    "impression_count": impression_count,
                },
                "lang": "en",
                "hashtags": all_hashtags,
                "mentions": mentions,
            }

            posts.append(
                RawPost(
                    search_request_id=uuid4(),
                    crawl_run_id=uuid4(),
                    platform=platform,
                    platform_id=post_id,
                    author_handle=author["handle"],
                    raw_payload=raw_payload,
                    fetched_at=datetime.now(UTC),
                ),
            )

        logger.info("Simulated %d posts for keyword '%s'", len(posts), keyword)
        return posts

    async def health_check(self) -> bool:
        return True
