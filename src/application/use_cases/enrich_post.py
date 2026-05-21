from __future__ import annotations

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
    ) -> None:
        self._sentiment_analyzer = sentiment_analyzer
        self._topic_extractor = topic_extractor
        self._language_detector = language_detector
        self._enriched_post_repo = enriched_post_repo
        self._ai_enrichment_repo = ai_enrichment_repo
        self._ai_job_repo = ai_job_repo

    async def execute(self, raw_post: RawPost) -> EnrichedPost:
        text = self._extract_text(raw_post)
        now = datetime.now(UTC)

        # Create and persist the EnrichedPost FIRST so the FK for ai_jobs resolves.
        enriched_post = EnrichedPost(
            bronze_post_id=raw_post.id,
            search_request_id=raw_post.search_request_id,
            platform=raw_post.platform,
            platform_id=raw_post.platform_id,
            author_handle=raw_post.author_handle,
            author_name=raw_post.raw_payload.get("author_name") if raw_post.raw_payload else None,
            post_text=text,
            posted_at=self._parse_datetime(raw_post.raw_payload.get("posted_at"))
            if raw_post.raw_payload
            else None,
            post_url=raw_post.raw_payload.get("post_url") if raw_post.raw_payload else None,
            like_count=raw_post.raw_payload.get("like_count", 0) if raw_post.raw_payload else 0,
            share_count=raw_post.raw_payload.get("share_count", 0) if raw_post.raw_payload else 0,
            reply_count=raw_post.raw_payload.get("reply_count", 0) if raw_post.raw_payload else 0,
            view_count=raw_post.raw_payload.get("view_count", 0) if raw_post.raw_payload else 0,
            is_retweet=raw_post.raw_payload.get("is_retweet", False)
            if raw_post.raw_payload
            else False,
        )

        saved_post = self._enriched_post_repo.save(enriched_post)

        ai_job = AIJob(
            silver_post_id=saved_post.id,
            job_type=AIJobType.FULL_ENRICHMENT,
            status=AIJobStatus.RUNNING,
            attempts=1,
            started_at=now,
        )

        try:
            sentiment_result = await self._sentiment_analyzer.analyze(text)
            topic_result = await self._topic_extractor.extract(text)
            language_result = await self._language_detector.detect(text)
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

        ai_enrichment = AIEnrichment(
            silver_post_id=saved_post.id,
            language=language_result.language_code,
            topic_label=topic_result.topic_label,
            sentiment=sentiment_result.label,
            sentiment_confidence=sentiment_result.confidence,
            metadata_model_name=topic_result.model_name,
            metadata_model_version=topic_result.model_version,
            sentiment_model_name=sentiment_result.model_name,
            sentiment_model_version=sentiment_result.model_version,
            hashtags=raw_post.raw_payload.get("hashtags", []) if raw_post.raw_payload else [],
            mentions=raw_post.raw_payload.get("mentions", []) if raw_post.raw_payload else [],
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

    @staticmethod
    def _extract_text(raw_post: RawPost) -> str:
        payload: dict[str, Any] | None = raw_post.raw_payload
        if payload is None:
            return ""
        return payload.get("text", "")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None
