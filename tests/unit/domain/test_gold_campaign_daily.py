from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.value_objects.platform import Platform


def _make_daily(**overrides: object) -> GoldCampaignDaily:
    defaults: dict[str, object] = {
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "date": date(2025, 1, 15),
    }
    defaults.update(overrides)
    return GoldCampaignDaily.model_validate(defaults)


@pytest.mark.unit
class TestGoldCampaignDailyDefaults:

    def test_id_auto_generated(self) -> None:
        daily = _make_daily()
        assert isinstance(daily.id, UUID)

    def test_total_posts_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.total_posts == 0

    def test_positive_count_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.positive_count == 0

    def test_negative_count_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.negative_count == 0

    def test_neutral_count_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.neutral_count == 0

    def test_avg_confidence_defaults_to_none(self) -> None:
        daily = _make_daily()
        assert daily.avg_confidence is None

    def test_top_hashtags_defaults_to_empty_list(self) -> None:
        daily = _make_daily()
        assert daily.top_hashtags == []

    def test_top_topics_defaults_to_empty_list(self) -> None:
        daily = _make_daily()
        assert daily.top_topics == []

    def test_total_likes_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.total_likes == 0

    def test_total_shares_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.total_shares == 0

    def test_total_replies_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.total_replies == 0

    def test_total_views_defaults_to_zero(self) -> None:
        daily = _make_daily()
        assert daily.total_views == 0

    def test_ai_version_defaults_to_one(self) -> None:
        daily = _make_daily()
        assert daily.ai_version == 1

    def test_created_at_auto_populated(self) -> None:
        daily = _make_daily()
        assert isinstance(daily.created_at, datetime)


@pytest.mark.unit
class TestGoldCampaignDailyExplicitValues:

    def test_explicit_date(self) -> None:
        d = date(2025, 3, 20)
        daily = _make_daily(date=d)
        assert daily.date == d

    def test_explicit_sentiment_counts(self) -> None:
        daily = _make_daily(positive_count=10, negative_count=5, neutral_count=3)
        assert daily.positive_count == 10
        assert daily.negative_count == 5
        assert daily.neutral_count == 3

    def test_explicit_avg_confidence(self) -> None:
        daily = _make_daily(avg_confidence=0.87)
        assert daily.avg_confidence == 0.87

    def test_explicit_top_hashtags(self) -> None:
        daily = _make_daily(top_hashtags=["ai", "ml"])
        assert daily.top_hashtags == ["ai", "ml"]

    def test_explicit_top_topics(self) -> None:
        daily = _make_daily(top_topics=["technology", "science"])
        assert daily.top_topics == ["technology", "science"]

    def test_explicit_engagement_totals(self) -> None:
        daily = _make_daily(
            total_likes=500,
            total_shares=200,
            total_replies=100,
            total_views=10000,
        )
        assert daily.total_likes == 500
        assert daily.total_shares == 200
        assert daily.total_replies == 100
        assert daily.total_views == 10000


@pytest.mark.unit
class TestGoldCampaignDailyRequiredFields:

    def test_search_request_id_is_required(self) -> None:
        payload: dict[str, object] = {
            "keyword": "test",
            "platform": Platform.TWITTER,
            "date": date(2025, 1, 1),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignDaily.model_validate(payload)

    def test_keyword_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "platform": Platform.TWITTER,
            "date": date(2025, 1, 1),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignDaily.model_validate(payload)

    def test_platform_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "keyword": "test",
            "date": date(2025, 1, 1),
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignDaily.model_validate(payload)

    def test_date_is_required(self) -> None:
        payload: dict[str, object] = {
            "search_request_id": uuid4(),
            "keyword": "test",
            "platform": Platform.TWITTER,
        }
        with pytest.raises(PydanticValidationError):
            GoldCampaignDaily.model_validate(payload)


@pytest.mark.unit
class TestGoldCampaignDailyImmutability:

    def test_frozen_model_raises_on_mutation(self) -> None:
        daily = _make_daily()
        with pytest.raises(PydanticValidationError):
            daily.keyword = "changed"
