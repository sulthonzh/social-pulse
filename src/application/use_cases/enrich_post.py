from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.ai_job import AIJob
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.exceptions import EnrichmentError
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.domain.entities.raw_post import RawPost
    from src.domain.interfaces import (
        AIEnrichmentRepository,
        AIJobRepository,
        EnrichedPostRepository,
        LanguageDetector,
        SentimentAnalyzer,
        TopicExtractor,
    )

logger = structlog.get_logger(__name__)

_HASHTAG_PATTERN = re.compile(r"#(\w+)")
_MENTION_PATTERN = re.compile(r"@(\w+)")


class EnrichPostUseCase:
    """Orchestrates Silver layer enrichment: RawPost -> AI analysis -> EnrichedPost + AIEnrichment + AIJob."""

    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzer,
        topic_extractor: TopicExtractor,
        language_detector: LanguageDetector,
        enriched_post_repo: EnrichedPostRepository,
        ai_enrichment_repo: AIEnrichmentRepository,
        ai_job_repo: AIJobRepository,
        max_retries: int = 3,
    ) -> None:
        self._sentiment_analyzer = sentiment_analyzer
        self._topic_extractor = topic_extractor
        self._language_detector = language_detector
        self._enriched_post_repo = enriched_post_repo
        self._ai_enrichment_repo = ai_enrichment_repo
        self._ai_job_repo = ai_job_repo
        self._max_retries = max_retries

    async def execute(self, raw_post: RawPost) -> EnrichedPost:
        text = self._extract_text(raw_post)
        now = datetime.now(UTC)

        payload = raw_post.raw_payload if raw_post.raw_payload else {}
        metrics = payload.get("public_metrics", {})

        enriched_post = EnrichedPost(
            bronze_post_id=raw_post.id,
            search_request_id=raw_post.search_request_id,
            platform=raw_post.platform,
            platform_id=raw_post.platform_id,
            author_handle=raw_post.author_handle,
            author_name=payload.get("author_name"),
            post_text=text,
            posted_at=self._parse_datetime(
                payload.get("posted_at") or payload.get("created_at")
            ),
            post_url=payload.get("post_url"),
            like_count=metrics.get("like_count", payload.get("like_count", 0)),
            share_count=metrics.get("retweet_count", payload.get("share_count", 0)),
            reply_count=metrics.get("reply_count", payload.get("reply_count", 0)),
            view_count=metrics.get("impression_count", payload.get("view_count", 0)),
            is_retweet=payload.get("is_retweet", False),
        )

        saved_post = self._enriched_post_repo.save(enriched_post)

        current_version = self._ai_enrichment_repo.get_max_version(str(saved_post.id))
        next_version = current_version + 1

        ai_job = AIJob(
            silver_post_id=saved_post.id,
            job_type=AIJobType.FULL_ENRICHMENT,
            status=AIJobStatus.RUNNING,
            ai_version=next_version,
            attempts=1,
            started_at=now,
        )

        try:
            sentiment_result = await self._retry_ai_call(
                lambda: self._sentiment_analyzer.analyze(text),
                "sentiment_analysis",
                job_id=str(ai_job.id),
            )
            topic_result = await self._retry_ai_call(
                lambda: self._topic_extractor.extract(text),
                "topic_extraction",
                job_id=str(ai_job.id),
            )
            language_result = await self._retry_ai_call(
                lambda: self._language_detector.detect(text),
                "language_detection",
                job_id=str(ai_job.id),
            )
        except Exception as exc:
            ai_job = ai_job.model_copy(
                update={
                    "status": AIJobStatus.FAILED,
                    "error_message": str(exc),
                    "completed_at": datetime.now(UTC),
                }
            )
            self._ai_job_repo.save(ai_job)

            logger.error(
                "enrichment_failed",
                raw_post_id=str(raw_post.id),
                error=str(exc),
                error_type=type(exc).__name__,
            )

            raise EnrichmentError(
                f"AI enrichment failed for post {raw_post.id}: {exc}",
            ) from exc

        view_count = metrics.get("impression_count", payload.get("view_count", 0))
        like_count = metrics.get("like_count", payload.get("like_count", 0))
        share_count = metrics.get("retweet_count", payload.get("share_count", 0))
        reply_count = metrics.get("reply_count", payload.get("reply_count", 0))
        total_engagement = like_count + share_count + reply_count
        reach_estimate = view_count if view_count > 0 else total_engagement * 10

        ai_enrichment = AIEnrichment(
            silver_post_id=saved_post.id,
            ai_version=next_version,
            language=language_result.language_code,
            topic_label=topic_result.topic_label,
            topic_confidence=topic_result.confidence,
            sentiment=sentiment_result.label,
            sentiment_confidence=sentiment_result.confidence,
            metadata_model_name=topic_result.model_name,
            metadata_model_version=topic_result.model_version,
            sentiment_model_name=sentiment_result.model_name,
            sentiment_model_version=sentiment_result.model_version,
            hashtags=self._merge_tags(
                raw_post.raw_payload.get("hashtags", []) if raw_post.raw_payload else [],
                self._extract_hashtags_from_text(text),
            ),
            mentions=self._merge_tags(
                raw_post.raw_payload.get("mentions", []) if raw_post.raw_payload else [],
                self._extract_mentions_from_text(text),
            ),
            reach_estimate=reach_estimate,
        )
        self._ai_enrichment_repo.save(ai_enrichment)

        completed_job = ai_job.model_copy(
            update={
                "status": AIJobStatus.COMPLETED,
                "completed_at": datetime.now(UTC),
            }
        )
        self._ai_job_repo.save(completed_job)

        logger.info(
            "enrichment_completed",
            raw_post_id=str(raw_post.id),
            enriched_post_id=str(saved_post.id),
            sentiment=sentiment_result.label,
            language=language_result.language_code,
            topic=topic_result.topic_label,
        )

        return saved_post

    async def _retry_ai_call(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        operation_name: str,
        job_id: str | None = None,
    ) -> Any:
        """Retry an async AI call with exponential backoff."""
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro_factory()
            except Exception as exc:
                last_exc = exc
                if job_id:
                    self._ai_job_repo.update_attempts(job_id, attempt)
                if attempt < self._max_retries:
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "ai_retry",
                        operation=operation_name,
                        attempt=attempt,
                        max_retries=self._max_retries,
                        wait_seconds=wait_time,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait_time)
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _extract_text(raw_post: RawPost) -> str:
        payload: dict[str, Any] | None = raw_post.raw_payload
        if payload is None:
            return ""
        return str(payload.get("text", ""))

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None

    @staticmethod
    def _extract_hashtags_from_text(text: str) -> list[str]:
        return _HASHTAG_PATTERN.findall(text)

    @staticmethod
    def _extract_mentions_from_text(text: str) -> list[str]:
        return [f"@{m}" for m in _MENTION_PATTERN.findall(text)]

    @staticmethod
    def _merge_tags(payload_tags: list[str], regex_tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in payload_tags + regex_tags:
            normalized = tag.lower().lstrip("@").lstrip("#")
            if normalized not in seen:
                seen.add(normalized)
                result.append(tag)
        return result
