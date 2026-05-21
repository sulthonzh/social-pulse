from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.application.use_cases.search_gold_posts import SearchGoldPosts, SearchGoldPostsResult
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform


def _make_gold_post(**overrides: object) -> GoldPostSearch:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "author_handle": "testuser",
        "author_name": "Test User",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "post_url": "https://twitter.com/test/status/123",
        "sentiment": "positive",
        "sentiment_confidence": 0.95,
        "topic_label": "technology",
        "language": "en",
        "hashtags": ["python", "data"],
        "mentions": ["@friend"],
        "like_count": 10,
        "share_count": 5,
        "reply_count": 3,
        "view_count": 100,
        "ai_version": 1,
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldPostSearch.model_validate(defaults)


def _build_use_case(posts=None, total=0):
    repo = MagicMock(spec=["search_posts"])
    repo.search_posts.return_value = (posts or [], total)
    return SearchGoldPosts(gold_repo=repo), repo


@pytest.mark.unit
class TestSearchGoldPosts:
    def test_execute_returns_result_with_posts_and_total(self):
        posts = [_make_gold_post()]
        use_case, repo = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert isinstance(result, SearchGoldPostsResult)
        assert result.total == 1
        assert len(result.posts) == 1

    def test_execute_converts_entity_to_presentation_dict(self):
        posts = [_make_gold_post(
            author_handle="johndoe",
            author_name="John Doe",
            post_text="Test post content",
            sentiment="positive",
            sentiment_confidence=0.92,
            posted_at=datetime(2025, 3, 15, 14, 30, 0),
            like_count=42,
            share_count=7,
            reply_count=3,
            platform=Platform.TWITTER,
            topic_label="technology",
            language="en",
        )]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        d = result.posts[0]
        assert d["author"] == "johndoe"
        assert d["text"] == "Test post content"
        assert d["sentiment"] == "positive"
        assert d["confidence"] == 0.92
        assert d["date"] == "2025-03-15"
        assert d["likes"] == 42
        assert d["shares"] == 7
        assert d["replies"] == 3
        assert d["platform"] == "twitter"
        assert d["topic"] == "technology"
        assert d["language"] == "en"

    def test_execute_falls_back_to_author_name_when_handle_missing(self):
        posts = [_make_gold_post(author_handle=None, author_name="Jane Doe")]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["author"] == "Jane Doe"

    def test_execute_falls_back_to_unknown_when_both_authors_missing(self):
        posts = [_make_gold_post(author_handle=None, author_name=None)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["author"] == "Unknown"

    def test_execute_handles_none_sentiment_confidence(self):
        posts = [_make_gold_post(sentiment_confidence=None)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["confidence"] == 0.0

    def test_execute_handles_none_posted_at(self):
        posts = [_make_gold_post(posted_at=None)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["date"] == ""

    def test_execute_passes_all_params_to_repo(self):
        use_case, repo = _build_use_case()

        use_case.execute(
            keyword="python",
            sentiment="positive",
            platform="twitter",
            start_date="2025-01-01",
            end_date="2025-01-31",
            offset=10,
            limit=50,
        )

        repo.search_posts.assert_called_once_with(
            keyword="python",
            sentiment="positive",
            platform="twitter",
            start_date="2025-01-01",
            end_date="2025-01-31",
            offset=10,
            limit=50,
        )

    def test_execute_returns_empty_when_no_posts(self):
        use_case, _ = _build_use_case(posts=[], total=0)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts == []
        assert result.total == 0

    def test_execute_rounds_confidence_to_two_decimals(self):
        posts = [_make_gold_post(sentiment_confidence=0.923456)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["confidence"] == 0.92

    def test_execute_handles_none_post_text(self):
        posts = [_make_gold_post(post_text=None)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["text"] == ""

    def test_execute_handles_none_sentiment(self):
        posts = [_make_gold_post(sentiment=None)]
        use_case, _ = _build_use_case(posts=posts, total=1)

        result = use_case.execute(
            keyword=None, sentiment=None, platform=None,
            start_date=None, end_date=None, offset=0, limit=50,
        )

        assert result.posts[0]["sentiment"] == "unknown"
