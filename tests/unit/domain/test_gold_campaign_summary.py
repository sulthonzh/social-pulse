from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.gold_campaign_summary import GoldCampaignSummary


def _make_summary(**overrides: object) -> GoldCampaignSummary:
    defaults: dict[str, object] = {
        "search_request_id": uuid4(),
        "keyword": "python",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 1, 31),
    }
    defaults.update(overrides)
    return GoldCampaignSummary.model_validate(defaults)


@pytest.mark.unit
class TestGoldCampaignSummaryDefaults:
    def test_id_auto_generated(self) -> None:
        summary = _make_summary()
        assert isinstance(summary.id, UUID)

    def test_total_posts_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_posts == 0

    def test_positive_pct_defaults_to_none(self) -> None:
        summary = _make_summary()
        assert summary.positive_pct is None

    def test_negative_pct_defaults_to_none(self) -> None:
        summary = _make_summary()
        assert summary.negative_pct is None

    def test_neutral_pct_defaults_to_none(self) -> None:
        summary = _make_summary()
        assert summary.neutral_pct is None

    def test_avg_confidence_defaults_to_none(self) -> None:
        summary = _make_summary()
        assert summary.avg_confidence is None

    def test_total_engagement_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_engagement == 0

    def test_total_likes_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_likes == 0

    def test_total_shares_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_shares == 0

    def test_total_replies_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_replies == 0

    def test_total_views_defaults_to_zero(self) -> None:
        summary = _make_summary()
        assert summary.total_views == 0

    def test_top_hashtags_defaults_to_empty_list(self) -> None:
        summary = _make_summary()
        assert summary.top_hashtags == []

    def test_top_topics_defaults_to_empty_list(self) -> None:
        summary = _make_summary()
        assert summary.top_topics == []

    def test_platforms_defaults_to_empty_list(self) -> None:
        summary = _make_summary()
        assert summary.platforms == []

    def test_ai_version_defaults_to_one(self) -> None:
        summary = _make_summary()
        assert summary.ai_version == 1

    def test_created_at_auto_populated(self) -> None:
        summary = _make_summary()
        assert isinstance(summary.created_at, datetime)


@pytest.mark.unit
class TestGoldCampaignSummaryExplicitValues:
    def test_explicit_date_range(self) -> None:
        summary = _make_summary(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
        )
        assert summary.start_date == date(2025, 2, 1)
        assert summary.end_date == date(2025, 2, 28)

    def test_explicit_sentiment_percentages(self) -> None:
        summary = _make_summary(
            positive_pct=60.5,
            negative_pct=20.0,
            neutral_pct=19.5,
        )
        assert summary.positive_pct == 60.5
        assert summary.negative_pct == 20.0
        assert summary.neutral_pct == 19.5

    def test_explicit_engagement(self) -> None:
        summary = _make_summary(
            total_engagement=1500,
            total_likes=1000,
            total_shares=300,
            total_replies=200,
            total_views=50000,
        )
        assert summary.total_engagement == 1500
        assert summary.total_likes == 1000
        assert summary.total_shares == 300
        assert summary.total_replies == 200
        assert summary.total_views == 50000

    def test_explicit_top_hashtags_and_topics(self) -> None:
        summary = _make_summary(
            top_hashtags=["python", "data"],
            top_topics=["technology"],
        )
        assert summary.top_hashtags == ["python", "data"]
        assert summary.top_topics == ["technology"]

    def test_explicit_platforms(self) -> None:
        summary = _make_summary(platforms=["twitter", "facebook"])
        assert summary.platforms == ["twitter", "facebook"]


@pytest.mark.unit
class TestGoldCampaignSummaryRequiredFields:
    def test_search_request_id_is_required(self) -> None:
        payload: dict[str, object] = {
            "keyword": "test",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 1, 31),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignSummary.model_validate(payload)

    def test_keyword_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 1, 31),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignSummary.model_validate(payload)

    def test_start_date_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "keyword": "test",
            "end_date": date(2025, 1, 31),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignSummary.model_validate(payload)

    def test_end_date_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "keyword": "test",
            "start_date": date(2025, 1, 1),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignSummary.model_validate(payload)


@pytest.mark.unit
class TestGoldCampaignSummaryImmutability:
    def test_frozen_model_raises_on_mutation(self) -> None:
        summary = _make_summary()
        with pytest.raises(PydanticValidationError):
            summary.keyword = "changed"
