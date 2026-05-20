from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform


@pytest.mark.unit
class TestEnrichedPostDefaults:

    def _make_post(self, **overrides: Any) -> EnrichedPost:
        defaults: dict[str, Any] = {
            "bronze_post_id": uuid4(),
            "search_request_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return EnrichedPost(**defaults)

    def test_id_auto_generated(self) -> None:
        post = self._make_post()
        assert post.id is not None
        assert isinstance(post.id, UUID)
        UUID(str(post.id))

    def test_platform_id_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.platform_id is None

    def test_author_handle_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.author_handle is None

    def test_author_name_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.author_name is None

    def test_post_text_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.post_text is None

    def test_posted_at_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.posted_at is None

    def test_like_count_defaults_to_zero(self) -> None:
        post = self._make_post()
        assert post.like_count == 0

    def test_share_count_defaults_to_zero(self) -> None:
        post = self._make_post()
        assert post.share_count == 0

    def test_reply_count_defaults_to_zero(self) -> None:
        post = self._make_post()
        assert post.reply_count == 0

    def test_view_count_defaults_to_zero(self) -> None:
        post = self._make_post()
        assert post.view_count == 0

    def test_post_url_defaults_to_none(self) -> None:
        post = self._make_post()
        assert post.post_url is None

    def test_is_retweet_defaults_to_false(self) -> None:
        post = self._make_post()
        assert post.is_retweet is False

    def test_created_at_auto_populated(self) -> None:
        post = self._make_post()
        assert post.created_at is not None
        assert isinstance(post.created_at, datetime)


@pytest.mark.unit
class TestEnrichedPostExplicitValues:

    def _make_post(self, **overrides: Any) -> EnrichedPost:
        defaults: dict[str, Any] = {
            "bronze_post_id": uuid4(),
            "search_request_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return EnrichedPost(**defaults)

    def test_explicit_platform_id(self) -> None:
        post = self._make_post(platform_id="tweet_999")
        assert post.platform_id == "tweet_999"

    def test_explicit_author_handle(self) -> None:
        post = self._make_post(author_handle="@dev")
        assert post.author_handle == "@dev"

    def test_explicit_author_name(self) -> None:
        post = self._make_post(author_name="Dev User")
        assert post.author_name == "Dev User"

    def test_explicit_post_text(self) -> None:
        post = self._make_post(post_text="Hello world")
        assert post.post_text == "Hello world"

    def test_explicit_engagement_counts(self) -> None:
        post = self._make_post(
            like_count=100,
            share_count=50,
            reply_count=25,
            view_count=5000,
        )
        assert post.like_count == 100
        assert post.share_count == 50
        assert post.reply_count == 25
        assert post.view_count == 5000

    def test_explicit_post_url(self) -> None:
        post = self._make_post(post_url="https://x.com/user/status/123")
        assert post.post_url == "https://x.com/user/status/123"

    def test_explicit_is_retweet(self) -> None:
        post = self._make_post(is_retweet=True)
        assert post.is_retweet is True

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        post = self._make_post(id=explicit_id)
        assert post.id == explicit_id


@pytest.mark.unit
class TestEnrichedPostRequiredFields:

    def test_bronze_post_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            EnrichedPost(  # type: ignore[call-arg]
                search_request_id=uuid4(),
                platform=Platform.TWITTER,
            )

    def test_search_request_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            EnrichedPost(  # type: ignore[call-arg]
                bronze_post_id=uuid4(),
                platform=Platform.TWITTER,
            )

    def test_platform_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            EnrichedPost(  # type: ignore[call-arg]
                bronze_post_id=uuid4(),
                search_request_id=uuid4(),
            )


@pytest.mark.unit
class TestEnrichedPostAllPlatforms:

    def test_twitter_platform(self) -> None:
        post = EnrichedPost(
            bronze_post_id=uuid4(),
            search_request_id=uuid4(),
            platform=Platform.TWITTER,
        )
        assert post.platform == Platform.TWITTER

    def test_facebook_platform(self) -> None:
        post = EnrichedPost(
            bronze_post_id=uuid4(),
            search_request_id=uuid4(),
            platform=Platform.FACEBOOK,
        )
        assert post.platform == Platform.FACEBOOK

    def test_instagram_platform(self) -> None:
        post = EnrichedPost(
            bronze_post_id=uuid4(),
            search_request_id=uuid4(),
            platform=Platform.INSTAGRAM,
        )
        assert post.platform == Platform.INSTAGRAM
