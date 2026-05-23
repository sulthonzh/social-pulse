from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from src.application.validators import RawPostValidator
from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import CrawlError
from src.domain.value_objects.platform import Platform

_UNSET = object()


def _make_post(
    platform_id: str | None = "post-123",
    author_handle: str | None = "user",
    raw_payload: dict[str, object] | None = _UNSET,  # type: ignore[assignment]
    platform: Platform = Platform.REDDIT,
) -> RawPost:
    payload = {"text": "hello"} if raw_payload is _UNSET else raw_payload
    return RawPost(
        search_request_id=uuid4(),
        crawl_run_id=uuid4(),
        platform=platform,
        platform_id=platform_id,
        author_handle=author_handle,
        raw_payload=payload,
    )


@pytest.mark.unit
class TestRawPostValidatorValidate:
    def test_valid_post_passes(self) -> None:
        post = _make_post()
        result = RawPostValidator.validate(post)
        assert result is post

    def test_missing_platform_id_raises(self) -> None:
        post = _make_post(platform_id=None)
        with pytest.raises(CrawlError, match="platform_id is required"):
            RawPostValidator.validate(post)

    def test_empty_platform_id_raises(self) -> None:
        post = _make_post(platform_id="")
        with pytest.raises(CrawlError, match="platform_id is required"):
            RawPostValidator.validate(post)

    def test_empty_raw_payload_raises(self) -> None:
        post = _make_post(raw_payload={})
        with pytest.raises(CrawlError, match="raw_payload must be a non-empty dict"):
            RawPostValidator.validate(post)

    def test_none_raw_payload_raises(self) -> None:
        post = _make_post(raw_payload=None)
        with pytest.raises(CrawlError, match="raw_payload must be a non-empty dict"):
            RawPostValidator.validate(post)

    @patch("src.application.validators.logger")
    def test_missing_author_handle_passes_with_debug_log(self, mock_logger: MagicMock) -> None:
        post = _make_post(author_handle=None)
        result = RawPostValidator.validate(post)
        assert result is post
        mock_logger.debug.assert_called_once_with(
            "raw_post_missing_author",
            platform=post.platform.value,
        )

    def test_multiple_errors_all_reported(self) -> None:
        post = _make_post(platform_id=None, raw_payload=None)
        with pytest.raises(CrawlError) as exc_info:
            RawPostValidator.validate(post)
        message = str(exc_info.value)
        assert "platform_id is required" in message
        assert "raw_payload must be a non-empty dict" in message


@pytest.mark.unit
class TestRawPostValidatorValidateBatch:
    def test_all_valid_returns_all(self) -> None:
        posts = [_make_post(), _make_post(), _make_post()]
        result = RawPostValidator.validate_batch(posts)
        assert result == posts

    def test_all_invalid_returns_empty(self) -> None:
        posts = [
            _make_post(platform_id=None),
            _make_post(raw_payload=None),
        ]
        result = RawPostValidator.validate_batch(posts)
        assert result == []

    def test_mixed_returns_only_valid(self) -> None:
        valid_post = _make_post(platform_id="valid-1")
        invalid_post = _make_post(platform_id=None)
        result = RawPostValidator.validate_batch([valid_post, invalid_post])
        assert result == [valid_post]

    @patch("src.application.validators.logger")
    def test_mixed_logs_batch_summary(self, mock_logger: MagicMock) -> None:
        valid = _make_post(platform_id="v1")
        invalid = _make_post(platform_id=None)
        RawPostValidator.validate_batch([valid, invalid])
        mock_logger.info.assert_called_once_with(
            "raw_post_batch_validation",
            total=2,
            valid=1,
            skipped=1,
        )

    @patch("src.application.validators.logger")
    def test_all_valid_does_not_log_batch_summary(self, mock_logger: MagicMock) -> None:
        posts = [_make_post(), _make_post()]
        RawPostValidator.validate_batch(posts)
        mock_logger.info.assert_not_called()

    def test_empty_batch_returns_empty(self) -> None:
        result = RawPostValidator.validate_batch([])
        assert result == []

    @patch("src.application.validators.logger")
    def test_invalid_posts_log_warning(self, mock_logger: MagicMock) -> None:
        invalid = _make_post(platform_id=None)
        RawPostValidator.validate_batch([invalid])
        mock_logger.warning.assert_called_once_with(
            "raw_post_validation_skipped",
            platform=invalid.platform.value,
            platform_id=invalid.platform_id,
        )
