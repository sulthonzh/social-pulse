from __future__ import annotations


class SocialPulseError(Exception):
    """Base exception for all SocialPulse domain errors."""


class EntityNotFoundError(SocialPulseError):
    """Raised when a requested entity does not exist."""


class ValidationError(SocialPulseError):
    """Raised when domain validation fails."""


class CrawlError(SocialPulseError):
    """Raised when a crawl operation fails."""


class DuplicateError(SocialPulseError):
    """Raised when a duplicate entity is detected."""


class EnrichmentError(SocialPulseError):
    """Raised when AI enrichment fails."""


class AIJobError(SocialPulseError):
    """Raised when an AI job fails."""


class RepositoryError(SocialPulseError):
    """Raised when a repository/persistence operation fails."""


class TransientError(SocialPulseError):
    """Raised when a transient/retryable operation fails."""
