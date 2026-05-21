from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """Supported social media platforms for crawling."""

    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
