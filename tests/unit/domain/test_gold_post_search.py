from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform


def _make_post(**overrides: object) -> GoldPostSearch:
    defaults: dict[str, object] = {
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
    }
    defaults.update(overrides)
    return GoldPostSearch.model_validate(defaults)


@pytest.mark.unit
class TestGoldPostSearchDefaults:
    def test_id_auto_generated(self) -> None:
        post = _make_post()
        assert isinstance(post.id, UUID)

    def test_author_handle_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.author_handle is None

    def test_author_name_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.author_name is None

    def test_post_text_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.post_text is None

    def test_posted_at_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.posted_at is None

    def test_post_url_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.post_url is None

    def test_sentiment_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.sentiment is None

    def test_sentiment_confidence_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.sentiment_confidence is None

    def test_topic_label_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.topic_label is None

    def test_language_defaults_to_none(self) -> None:
        post = _make_post()
        assert post.language is None

    def test_hashtags_defaults_to_empty_list(self) -> None:
        post = _make_post()
        assert post.hashtags == []

    def test_mentions_defaults_to_empty_list(self) -> None:
        post = _make_post()
        assert post.mentions == []

    def test_like_count_defaults_to_zero(self) -> None:
        post = _make_post()
        assert post.like_count == 0

    def test_share_count_defaults_to_zero(self) -> None:
        post = _make_post()
        assert post.share_count == 0

    def test_reply_count_defaults_to_zero(self) -> None:
        post = _make_post()
        assert post.reply_count == 0

    def test_view_count_defaults_to_zero(self) -> None:
        post = _make_post()
        assert post.view_count == 0

    def test_ai_version_defaults_to_one(self) -> None:
        post = _make_post()
        assert post.ai_version == 1

    def test_created_at_auto_populated(self) -> None:
        post = _make_post()
        assert isinstance(post.created_at, datetime)


@pytest.mark.unit
class TestGoldPostSearchExplicitValues:
    def test_explicit_keyword(self) -> None:
        post = _make_post(keyword="data engineering")
        assert post.keyword == "data engineering"

    def test_explicit_platform_twitter(self) -> None:
        post = _make_post(platform=Platform.TWITTER)
        assert post.platform == Platform.TWITTER

    def test_explicit_platform_facebook(self) -> None:
        post = _make_post(platform=Platform.FACEBOOK)
        assert post.platform == Platform.FACEBOOK

    def test_explicit_platform_instagram(self) -> None:
        post = _make_post(platform=Platform.INSTAGRAM)
        assert post.platform == Platform.INSTAGRAM

    def test_explicit_sentiment(self) -> None:
        post = _make_post(sentiment="positive")
        assert post.sentiment == "positive"

    def test_explicit_sentiment_confidence(self) -> None:
        post = _make_post(sentiment_confidence=0.95)
        assert post.sentiment_confidence == 0.95

    def test_explicit_hashtags(self) -> None:
        post = _make_post(hashtags=["python", "data"])
        assert post.hashtags == ["python", "data"]

    def test_explicit_mentions(self) -> None:
        post = _make_post(mentions=["@user1", "@user2"])
        assert post.mentions == ["@user1", "@user2"]

    def test_explicit_engagement_counts(self) -> None:
        post = _make_post(
            like_count=100,
            share_count=50,
            reply_count=25,
            view_count=5000,
        )
        assert post.like_count == 100
        assert post.share_count == 50
        assert post.reply_count == 25
        assert post.view_count == 5000

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        post = _make_post(id=explicit_id)
        assert post.id == explicit_id


@pytest.mark.unit
class TestGoldPostSearchRequiredFields:
    def test_search_request_id_is_required(self) -> None:
        payload: dict[str, object] = {"keyword": "test", "platform": Platform.TWITTER}
        with pytest.raises(PydanticValidationError):
            GoldPostSearch.model_validate(payload)

    def test_keyword_is_required(self) -> None:
        payload: dict[str, object] = {"search_request_id": uuid4(), "platform": Platform.TWITTER}
        with pytest.raises(PydanticValidationError):
            GoldPostSearch.model_validate(payload)

    def test_platform_is_required(self) -> None:
        payload: dict[str, object] = {"search_request_id": uuid4(), "keyword": "test"}
        with pytest.raises(PydanticValidationError):
            GoldPostSearch.model_validate(payload)


@pytest.mark.unit
class TestGoldPostSearchImmutability:
    def test_frozen_model_raises_on_mutation(self) -> None:
        post = _make_post()
        with pytest.raises(PydanticValidationError):
            post.keyword = "changed"
