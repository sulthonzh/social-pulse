from __future__ import annotations

import pytest
from src.domain.value_objects.platform import Platform


@pytest.mark.unit
class TestPlatformEnumValues:

    def test_twitter_exists(self) -> None:
        assert Platform.TWITTER is not None

    def test_facebook_exists(self) -> None:
        assert Platform.FACEBOOK is not None

    def test_instagram_exists(self) -> None:
        assert Platform.INSTAGRAM is not None

    def test_twitter_string_value(self) -> None:
        assert Platform.TWITTER.value == "twitter"

    def test_facebook_string_value(self) -> None:
        assert Platform.FACEBOOK.value == "facebook"

    def test_instagram_string_value(self) -> None:
        assert Platform.INSTAGRAM.value == "instagram"


@pytest.mark.unit
class TestPlatformStrEnumBehavior:

    def test_platform_is_string(self) -> None:
        assert isinstance(Platform.TWITTER, str)

    def test_value_lookup_by_string(self) -> None:
        assert Platform("twitter") is Platform.TWITTER

    def test_facebook_value_lookup(self) -> None:
        assert Platform("facebook") is Platform.FACEBOOK

    def test_instagram_value_lookup(self) -> None:
        assert Platform("instagram") is Platform.INSTAGRAM

    def test_iteration(self) -> None:
        members = list(Platform)
        assert len(members) == 3
        assert Platform.TWITTER in members
        assert Platform.FACEBOOK in members
        assert Platform.INSTAGRAM in members

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            Platform("linkedin")
