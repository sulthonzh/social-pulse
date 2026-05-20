from __future__ import annotations

import pytest
from src.domain.exceptions import (
    CrawlError,
    DuplicateError,
    EntityNotFoundError,
    SocialPulseError,
    ValidationError,
)


@pytest.mark.unit
class TestSocialPulseErrorBase:

    def test_is_exception(self) -> None:
        assert issubclass(SocialPulseError, Exception)

    def test_custom_message(self) -> None:
        err = SocialPulseError("something went wrong")
        assert str(err) == "something went wrong"

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(SocialPulseError, match="base error"):
            raise SocialPulseError("base error")


@pytest.mark.unit
class TestSubclassInheritance:

    def test_entity_not_found_is_social_pulse_error(self) -> None:
        assert issubclass(EntityNotFoundError, SocialPulseError)
        assert issubclass(EntityNotFoundError, Exception)

    def test_validation_error_is_social_pulse_error(self) -> None:
        assert issubclass(ValidationError, SocialPulseError)
        assert issubclass(ValidationError, Exception)

    def test_crawl_error_is_social_pulse_error(self) -> None:
        assert issubclass(CrawlError, SocialPulseError)
        assert issubclass(CrawlError, Exception)

    def test_duplicate_error_is_social_pulse_error(self) -> None:
        assert issubclass(DuplicateError, SocialPulseError)
        assert issubclass(DuplicateError, Exception)


@pytest.mark.unit
class TestSubclassRaiseAndCatch:

    def test_entity_not_found_caught_as_base(self) -> None:
        with pytest.raises(SocialPulseError):
            raise EntityNotFoundError("entity xyz not found")

    def test_validation_error_caught_as_base(self) -> None:
        with pytest.raises(SocialPulseError):
            raise ValidationError("invalid field")

    def test_crawl_error_caught_as_base(self) -> None:
        with pytest.raises(SocialPulseError):
            raise CrawlError("crawl timeout")

    def test_duplicate_error_caught_as_base(self) -> None:
        with pytest.raises(SocialPulseError):
            raise DuplicateError("duplicate entry")

    def test_entity_not_found_caught_as_specific(self) -> None:
        with pytest.raises(EntityNotFoundError, match="not found"):
            raise EntityNotFoundError("post not found")

    def test_validation_error_caught_as_specific(self) -> None:
        with pytest.raises(ValidationError, match="bad input"):
            raise ValidationError("bad input")

    def test_crawl_error_caught_as_specific(self) -> None:
        with pytest.raises(CrawlError, match="timeout"):
            raise CrawlError("timeout")

    def test_duplicate_error_caught_as_specific(self) -> None:
        with pytest.raises(DuplicateError, match="already exists"):
            raise DuplicateError("already exists")


@pytest.mark.unit
class TestErrorMessagePropagation:

    def test_entity_not_found_message(self) -> None:
        err = EntityNotFoundError("user 42")
        assert "user 42" in str(err)

    def test_validation_error_message(self) -> None:
        err = ValidationError("email is invalid")
        assert "email is invalid" in str(err)

    def test_crawl_error_message(self) -> None:
        err = CrawlError("rate limit exceeded")
        assert "rate limit exceeded" in str(err)

    def test_duplicate_error_message(self) -> None:
        err = DuplicateError("keyword exists")
        assert "keyword exists" in str(err)
