from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.domain.entities.raw_post import RawPost
from src.domain.value_objects.platform import Platform


@pytest.mark.unit
class TestRawPostDefaults:
    def _make_raw_post(self, **overrides: Any) -> RawPost:
        defaults: dict[str, Any] = {
            "search_request_id": uuid4(),
            "crawl_run_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return RawPost(**defaults)

    def test_id_auto_generated(self) -> None:
        post = self._make_raw_post()
        assert post.id is not None
        assert isinstance(post.id, UUID)
        UUID(str(post.id))

    def test_platform_id_defaults_to_none(self) -> None:
        post = self._make_raw_post()
        assert post.platform_id is None

    def test_author_handle_defaults_to_none(self) -> None:
        post = self._make_raw_post()
        assert post.author_handle is None

    def test_raw_payload_defaults_to_none(self) -> None:
        post = self._make_raw_post()
        assert post.raw_payload is None

    def test_fetched_at_auto_populated(self) -> None:
        post = self._make_raw_post()
        assert post.fetched_at is not None
        assert isinstance(post.fetched_at, datetime)


@pytest.mark.unit
class TestRawPostExplicitValues:
    def _make_raw_post(self, **overrides: Any) -> RawPost:
        defaults: dict[str, Any] = {
            "search_request_id": uuid4(),
            "crawl_run_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return RawPost(**defaults)

    def test_explicit_raw_payload_dict(self) -> None:
        payload = {"text": "hello world", "likes": 42}
        post = self._make_raw_post(raw_payload=payload)
        assert post.raw_payload == payload
        assert post.raw_payload["likes"] == 42

    def test_explicit_platform_id(self) -> None:
        post = self._make_raw_post(platform_id="tweet_123")
        assert post.platform_id == "tweet_123"

    def test_explicit_author_handle(self) -> None:
        post = self._make_raw_post(author_handle="@user")
        assert post.author_handle == "@user"

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        post = self._make_raw_post(id=explicit_id)
        assert post.id == explicit_id


@pytest.mark.unit
class TestRawPostAllPlatforms:
    def _make_raw_post(self, platform: Platform) -> RawPost:
        return RawPost(
            search_request_id=uuid4(),
            crawl_run_id=uuid4(),
            platform=platform,
        )

    def test_twitter_platform(self) -> None:
        post = self._make_raw_post(Platform.TWITTER)
        assert post.platform == Platform.TWITTER

    def test_facebook_platform(self) -> None:
        post = self._make_raw_post(Platform.FACEBOOK)
        assert post.platform == Platform.FACEBOOK

    def test_instagram_platform(self) -> None:
        post = self._make_raw_post(Platform.INSTAGRAM)
        assert post.platform == Platform.INSTAGRAM
