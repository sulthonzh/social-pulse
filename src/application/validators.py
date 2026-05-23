"""Validation utilities for pipeline data at use case boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.exceptions import CrawlError

if TYPE_CHECKING:
    from src.domain.entities.raw_post import RawPost

logger = structlog.get_logger(__name__)


class RawPostValidator:
    """Validates RawPost entities before persistence to ensure data quality."""

    @staticmethod
    def validate(post: RawPost) -> RawPost:
        """Validate a RawPost, returning it if valid or raising CrawlError."""
        errors: list[str] = []

        # Platform ID must be present (required for deduplication)
        if not post.platform_id:
            errors.append("platform_id is required")

        if not post.raw_payload:
            errors.append("raw_payload must be a non-empty dict")

        # Author handle should be present for most platforms
        if not post.author_handle:
            logger.debug("raw_post_missing_author", platform=post.platform.value)

        if errors:
            raise CrawlError(f"RawPost validation failed: {'; '.join(errors)}")

        return post

    @staticmethod
    def validate_batch(posts: list[RawPost]) -> list[RawPost]:
        """Validate a batch of RawPosts, filtering out invalid ones with logging."""
        valid: list[RawPost] = []
        for post in posts:
            try:
                valid.append(RawPostValidator.validate(post))
            except CrawlError:
                logger.warning(
                    "raw_post_validation_skipped",
                    platform=post.platform.value,
                    platform_id=post.platform_id,
                )
        if len(valid) < len(posts):
            logger.info(
                "raw_post_batch_validation",
                total=len(posts),
                valid=len(valid),
                skipped=len(posts) - len(valid),
            )
        return valid
