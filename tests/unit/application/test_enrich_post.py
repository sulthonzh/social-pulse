from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.application.use_cases.enrich_post import EnrichPostUseCase
from src.domain.entities.language_result import LanguageResult
from src.domain.entities.raw_post import RawPost
from src.domain.entities.sentiment_result import SentimentResult
from src.domain.entities.topic_result import TopicResult
from src.domain.exceptions import EnrichmentError
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel

if TYPE_CHECKING:
    from src.domain.entities.enriched_post import EnrichedPost


def _make_raw_post(
    platform: Platform = Platform.TWITTER,
    text: str = "I love data engineering!",
) -> RawPost:
    return RawPost(
        search_request_id=uuid4(),
        crawl_run_id=uuid4(),
        platform=platform,
        platform_id="post-abc",
        author_handle="data_nerd",
        raw_payload={
            "text": text,
            "author_name": "Data Nerd",
            "posted_at": "2025-01-15T10:30:00Z",
            "post_url": "https://x.com/data_nerd/status/123",
            "like_count": 42,
            "share_count": 5,
            "reply_count": 3,
            "view_count": 1000,
            "is_retweet": False,
            "hashtags": ["data", "engineering"],
            "mentions": ["@friend"],
        },
    )


def _make_sentiment_result(
    label: SentimentLabel = SentimentLabel.POSITIVE,
    confidence: float = 0.95,
) -> SentimentResult:
    return SentimentResult(
        label=label,
        confidence=confidence,
        model_name="sentiment-v1",
        model_version="1.0.0",
    )


def _make_topic_result(topic_label: str = "technology") -> TopicResult:
    return TopicResult(
        topic_label=topic_label,
        model_name="topic-v1",
        model_version="1.0.0",
    )


def _make_language_result(
    language_code: str = "en",
    confidence: float = 0.99,
) -> LanguageResult:
    return LanguageResult(
        language_code=language_code,
        confidence=confidence,
    )


def _build_use_case():
    sentiment_analyzer = MagicMock(spec=["analyze"])
    sentiment_analyzer.analyze = AsyncMock()

    topic_extractor = MagicMock(spec=["extract"])
    topic_extractor.extract = AsyncMock()

    language_detector = MagicMock(spec=["detect"])
    language_detector.detect = AsyncMock()

    enriched_post_repo = MagicMock(
        spec=["save", "save_batch", "get_by_bronze_post_id", "get_by_search", "count_by_search"],
    )
    ai_enrichment_repo = MagicMock(
        spec=["save", "get_by_post", "get_by_search"],
    )
    ai_job_repo = MagicMock(
        spec=["save", "get_pending_jobs", "update_status"],
    )

    use_case = EnrichPostUseCase(
        sentiment_analyzer=sentiment_analyzer,
        topic_extractor=topic_extractor,
        language_detector=language_detector,
        enriched_post_repo=enriched_post_repo,
        ai_enrichment_repo=ai_enrichment_repo,
        ai_job_repo=ai_job_repo,
    )

    return (
        use_case,
        sentiment_analyzer,
        topic_extractor,
        language_detector,
        enriched_post_repo,
        ai_enrichment_repo,
        ai_job_repo,
    )


def _setup_happy_path_mocks(
    sentiment_analyzer,
    topic_extractor,
    language_detector,
    enriched_post_repo,
):
    sentiment_analyzer.analyze.return_value = _make_sentiment_result()
    topic_extractor.extract.return_value = _make_topic_result()
    language_detector.detect.return_value = _make_language_result()

    def _save_post(post: EnrichedPost) -> EnrichedPost:
        return post

    enriched_post_repo.save.side_effect = _save_post


@pytest.mark.unit
class TestEnrichPostUseCase:
    async def test_happy_path_saves_all_entities(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        result = await use_case.execute(raw_post)

        assert result.bronze_post_id == raw_post.id
        assert result.search_request_id == raw_post.search_request_id
        assert result.platform == raw_post.platform
        assert result.author_handle == raw_post.author_handle
        assert result.post_text == "I love data engineering!"

        sentiment_analyzer.analyze.assert_called_once_with("I love data engineering!")
        topic_extractor.extract.assert_called_once_with("I love data engineering!")
        language_detector.detect.assert_called_once_with("I love data engineering!")

        enriched_post_repo.save.assert_called_once()
        ai_enrichment_repo.save.assert_called_once()
        ai_job_repo.save.assert_called_once()

    async def test_happy_path_enriched_post_fields(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        result = await use_case.execute(raw_post)

        assert result.platform_id == "post-abc"
        assert result.author_name == "Data Nerd"
        assert result.like_count == 42
        assert result.share_count == 5
        assert result.reply_count == 3
        assert result.view_count == 1000
        assert result.post_url == "https://x.com/data_nerd/status/123"
        assert result.is_retweet is False

    async def test_happy_path_ai_enrichment_fields(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        await use_case.execute(raw_post)

        saved_enrichment = ai_enrichment_repo.save.call_args[0][0]
        assert saved_enrichment.sentiment == SentimentLabel.POSITIVE
        assert saved_enrichment.sentiment_confidence == 0.95
        assert saved_enrichment.topic_label == "technology"
        assert saved_enrichment.language == "en"
        assert saved_enrichment.sentiment_model_name == "sentiment-v1"
        assert saved_enrichment.sentiment_model_version == "1.0.0"
        assert saved_enrichment.metadata_model_name == "topic-v1"
        assert saved_enrichment.metadata_model_version == "1.0.0"
        assert saved_enrichment.hashtags == ["data", "engineering"]
        assert saved_enrichment.mentions == ["@friend"]

    async def test_happy_path_ai_job_completed(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        await use_case.execute(raw_post)

        saved_job = ai_job_repo.save.call_args[0][0]
        assert saved_job.status == AIJobStatus.COMPLETED
        assert saved_job.job_type == AIJobType.FULL_ENRICHMENT
        assert saved_job.completed_at is not None
        assert saved_job.error_message is None

    async def test_sentiment_failure_saves_failed_job_and_raises(self):
        (
            use_case,
            sentiment_analyzer,
            _topic_extractor,
            _language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.side_effect = RuntimeError("model unavailable")

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post()

        with pytest.raises(EnrichmentError, match="model unavailable"):
            await use_case.execute(raw_post)

        enriched_post_repo.save.assert_called_once()
        ai_enrichment_repo.save.assert_not_called()

        saved_job = ai_job_repo.save.call_args[0][0]
        assert saved_job.status == AIJobStatus.FAILED
        assert "model unavailable" in saved_job.error_message

    async def test_topic_failure_saves_failed_job_and_raises(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            _language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result()
        topic_extractor.extract.side_effect = ConnectionError("API down")

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post()

        with pytest.raises(EnrichmentError, match="API down"):
            await use_case.execute(raw_post)

        enriched_post_repo.save.assert_called_once()
        ai_enrichment_repo.save.assert_not_called()

        saved_job = ai_job_repo.save.call_args[0][0]
        assert saved_job.status == AIJobStatus.FAILED
        assert "API down" in saved_job.error_message

    async def test_language_failure_saves_failed_job_and_raises(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result()
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.side_effect = TimeoutError("request timed out")

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post()

        with pytest.raises(EnrichmentError, match="request timed out"):
            await use_case.execute(raw_post)

        enriched_post_repo.save.assert_called_once()
        ai_enrichment_repo.save.assert_not_called()

        saved_job = ai_job_repo.save.call_args[0][0]
        assert saved_job.status == AIJobStatus.FAILED
        assert "request timed out" in saved_job.error_message

    async def test_raw_post_with_no_payload_uses_empty_text(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result()
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.return_value = _make_language_result()

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = RawPost(
            search_request_id=uuid4(),
            crawl_run_id=uuid4(),
            platform=Platform.TWITTER,
        )

        result = await use_case.execute(raw_post)

        sentiment_analyzer.analyze.assert_called_once_with("")
        assert result.post_text == ""
        assert result.like_count == 0
        assert result.share_count == 0

    async def test_raw_post_with_payload_missing_text_uses_empty_string(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result()
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.return_value = _make_language_result()

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = RawPost(
            search_request_id=uuid4(),
            crawl_run_id=uuid4(),
            platform=Platform.FACEBOOK,
            raw_payload={"like_count": 10},
        )

        result = await use_case.execute(raw_post)

        sentiment_analyzer.analyze.assert_called_once_with("")
        assert result.post_text == ""
        assert result.like_count == 10

    async def test_ai_job_has_correct_type_and_post_id(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        result = await use_case.execute(raw_post)

        saved_job = ai_job_repo.save.call_args[0][0]
        assert saved_job.job_type == AIJobType.FULL_ENRICHMENT
        assert saved_job.silver_post_id == result.id

    async def test_enrichment_error_chained_from_original(self):
        (
            use_case,
            sentiment_analyzer,
            _topic_extractor,
            _language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        original = ValueError("bad model output")
        sentiment_analyzer.analyze.side_effect = original

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post()

        with pytest.raises(EnrichmentError) as exc_info:
            await use_case.execute(raw_post)

        assert exc_info.value.__cause__ is original

    async def test_facebook_platform_enrichment(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post(platform=Platform.FACEBOOK)
        result = await use_case.execute(raw_post)

        assert result.platform == Platform.FACEBOOK

    async def test_instagram_platform_enrichment(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            _ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post(platform=Platform.INSTAGRAM)
        result = await use_case.execute(raw_post)

        assert result.platform == Platform.INSTAGRAM

    async def test_negative_sentiment_result(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result(
            label=SentimentLabel.NEGATIVE,
            confidence=0.88,
        )
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.return_value = _make_language_result()

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post(text="This is terrible")
        await use_case.execute(raw_post)

        saved_enrichment = ai_enrichment_repo.save.call_args[0][0]
        assert saved_enrichment.sentiment == SentimentLabel.NEGATIVE
        assert saved_enrichment.sentiment_confidence == 0.88

    async def test_neutral_sentiment_result(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result(
            label=SentimentLabel.NEUTRAL,
            confidence=0.60,
        )
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.return_value = _make_language_result()

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post(text="Today is Tuesday")
        await use_case.execute(raw_post)

        saved_enrichment = ai_enrichment_repo.save.call_args[0][0]
        assert saved_enrichment.sentiment == SentimentLabel.NEUTRAL

    async def test_non_english_language_result(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        sentiment_analyzer.analyze.return_value = _make_sentiment_result()
        topic_extractor.extract.return_value = _make_topic_result()
        language_detector.detect.return_value = _make_language_result(
            language_code="id",
            confidence=0.92,
        )

        def _save_post(post: EnrichedPost) -> EnrichedPost:
            return post

        enriched_post_repo.save.side_effect = _save_post

        raw_post = _make_raw_post(text="Saya suka pemrograman")
        await use_case.execute(raw_post)

        saved_enrichment = ai_enrichment_repo.save.call_args[0][0]
        assert saved_enrichment.language == "id"

    async def test_ai_enrichment_silver_post_id_matches_enriched_post_id(self):
        (
            use_case,
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
            ai_enrichment_repo,
            _ai_job_repo,
        ) = _build_use_case()

        _setup_happy_path_mocks(
            sentiment_analyzer,
            topic_extractor,
            language_detector,
            enriched_post_repo,
        )

        raw_post = _make_raw_post()
        result = await use_case.execute(raw_post)

        saved_enrichment = ai_enrichment_repo.save.call_args[0][0]
        assert saved_enrichment.silver_post_id == result.id
