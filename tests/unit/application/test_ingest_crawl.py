from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.ingest_crawl import IngestCrawlRun
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.exceptions import CrawlError
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform


def _make_request(
    keyword: str = "python",
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2025, 1, 31),
    platform: Platform = Platform.TWITTER,
) -> SearchRequest:
    return SearchRequest(
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )


def _make_post(platform: Platform = Platform.TWITTER):
    return RawPost(
        search_request_id=uuid4(),
        crawl_run_id=uuid4(),
        platform=platform,
        platform_id="post-123",
        author_handle="user",
        raw_payload={"text": "hello"},
    )


def _make_crawl_run(
    search_request_id,
    platform: Platform = Platform.TWITTER,
) -> CrawlRun:
    return CrawlRun(
        search_request_id=search_request_id,
        platform=platform,
        status=CrawlStatus.RUNNING,
    )


def _build_use_case():
    search_request_repo = MagicMock(
        spec=["save", "get_by_id", "get_by_keyword", "update_status"],
    )
    crawl_run_repo = MagicMock(
        spec=["save", "get_by_id", "get_by_search_request", "update_status"],
    )
    post_repo = MagicMock(
        spec=[
            "save_posts",
            "get_posts_by_search",
            "get_posts_by_crawl_run",
            "count_posts_by_search",
        ],
    )
    crawler = MagicMock(spec=["crawl", "health_check"])
    crawler.crawl = AsyncMock()
    crawler.health_check = AsyncMock()

    use_case = IngestCrawlRun(
        search_request_repo=search_request_repo,
        crawl_run_repo=crawl_run_repo,
        post_repo=post_repo,
    )
    return use_case, search_request_repo, crawl_run_repo, post_repo, crawler


@pytest.mark.unit
class TestIngestCrawlRun:
    """Tests for the IngestCrawlRun use case orchestration."""

    async def test_happy_path_saves_and_completes(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        request = _make_request()
        saved_request = _make_request()
        req_repo.save.return_value = saved_request

        crawl_run = _make_crawl_run(saved_request.id)
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        posts = [_make_post(), _make_post(), _make_post()]
        crawler.crawl.return_value = posts
        post_repo.save_posts.return_value = 3

        result = await use_case.execute(request, crawler)

        assert result.status == CrawlStatus.COMPLETED
        assert result.posts_fetched == 3

        req_repo.save.assert_called_once_with(request)
        run_repo.save.assert_called_once()
        post_repo.save_posts.assert_called_once()

        saved_posts = post_repo.save_posts.call_args[0][0]
        for post in saved_posts:
            assert post.search_request_id == saved_request.id
            assert post.crawl_run_id == saved_run.id

        run_repo.update_status.assert_called_once_with(
            crawl_run_id=str(saved_run.id),
            status=CrawlStatus.COMPLETED,
            posts_fetched=3,
            error_message=None,
        )
        req_repo.update_status.assert_called_once_with(
            request_id=str(saved_request.id),
            status=CrawlStatus.COMPLETED,
            posts_found=3,
        )

    async def test_crawl_error_sets_failed_and_reraises(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        request = _make_request()
        saved_request = _make_request()
        req_repo.save.return_value = saved_request

        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        crawler.crawl.side_effect = CrawlError("API timeout")

        with pytest.raises(CrawlError, match="API timeout"):
            await use_case.execute(request, crawler)

        run_repo.update_status.assert_called_once_with(
            crawl_run_id=str(saved_run.id),
            status=CrawlStatus.FAILED,
            posts_fetched=0,
            error_message="API timeout",
        )
        req_repo.update_status.assert_called_once_with(
            request_id=str(saved_request.id),
            status=CrawlStatus.FAILED,
            posts_found=0,
        )

    async def test_generic_exception_sets_failed_and_reraises(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request()
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        crawler.crawl.side_effect = ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            await use_case.execute(_make_request(), crawler)

        run_repo.update_status.assert_called_once_with(
            crawl_run_id=str(saved_run.id),
            status=CrawlStatus.FAILED,
            posts_fetched=0,
            error_message="bad input",
        )
        req_repo.update_status.assert_called_once_with(
            request_id=str(saved_request.id),
            status=CrawlStatus.FAILED,
            posts_found=0,
        )

    async def test_runtime_error_sets_failed_and_reraises(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request()
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        crawler.crawl.side_effect = RuntimeError("connection lost")

        with pytest.raises(RuntimeError, match="connection lost"):
            await use_case.execute(_make_request(), crawler)

        run_repo.update_status.assert_called_once_with(
            crawl_run_id=str(saved_run.id),
            status=CrawlStatus.FAILED,
            posts_fetched=0,
            error_message="connection lost",
        )

    async def test_empty_crawl_returns_completed_with_zero_posts(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request()
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        crawler.crawl.return_value = []
        post_repo.save_posts.return_value = 0

        result = await use_case.execute(_make_request(), crawler)

        assert result.status == CrawlStatus.COMPLETED
        assert result.posts_fetched == 0

        run_repo.update_status.assert_called_once_with(
            crawl_run_id=str(saved_run.id),
            status=CrawlStatus.COMPLETED,
            posts_fetched=0,
            error_message=None,
        )

    async def test_facebook_platform_happy_path(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request(platform=Platform.FACEBOOK)
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id, platform=Platform.FACEBOOK)
        run_repo.save.return_value = saved_run

        crawler.crawl.return_value = [_make_post(Platform.FACEBOOK)]
        post_repo.save_posts.return_value = 1

        result = await use_case.execute(
            _make_request(platform=Platform.FACEBOOK),
            crawler,
        )

        assert result.status == CrawlStatus.COMPLETED
        assert result.posts_fetched == 1

        crawl_call_kwargs = crawler.crawl.call_args[1]
        assert crawl_call_kwargs["platform"] == Platform.FACEBOOK

    async def test_instagram_platform_happy_path(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request(platform=Platform.INSTAGRAM)
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id, platform=Platform.INSTAGRAM)
        run_repo.save.return_value = saved_run

        crawler.crawl.return_value = [
            _make_post(Platform.INSTAGRAM),
            _make_post(Platform.INSTAGRAM),
        ]
        post_repo.save_posts.return_value = 2

        result = await use_case.execute(
            _make_request(platform=Platform.INSTAGRAM),
            crawler,
        )

        assert result.status == CrawlStatus.COMPLETED
        assert result.posts_fetched == 2

        crawl_call_kwargs = crawler.crawl.call_args[1]
        assert crawl_call_kwargs["platform"] == Platform.INSTAGRAM

    async def test_post_ids_overwritten_to_saved_ids(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request()
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        original_post = _make_post()
        assert original_post.search_request_id != saved_request.id
        assert original_post.crawl_run_id != saved_run.id

        crawler.crawl.return_value = [original_post]
        post_repo.save_posts.return_value = 1

        await use_case.execute(_make_request(), crawler)

        saved_posts = post_repo.save_posts.call_args[0][0]
        assert saved_posts[0].search_request_id == saved_request.id
        assert saved_posts[0].crawl_run_id == saved_run.id

    async def test_crawl_called_with_correct_parameters(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request(
            keyword="data engineering",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
            platform=Platform.TWITTER,
        )
        req_repo.save.return_value = saved_request
        run_repo.save.return_value = _make_crawl_run(saved_request.id)
        crawler.crawl.return_value = []
        post_repo.save_posts.return_value = 0

        await use_case.execute(_make_request(), crawler)

        crawler.crawl.assert_called_once_with(
            keyword="data engineering",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
            platform=Platform.TWITTER,
        )

    async def test_exception_does_not_swallow_original_error(self):
        use_case, req_repo, run_repo, post_repo, crawler = _build_use_case()

        saved_request = _make_request()
        req_repo.save.return_value = saved_request
        saved_run = _make_crawl_run(saved_request.id)
        run_repo.save.return_value = saved_run

        original_exc = ConnectionError("network down")
        crawler.crawl.side_effect = original_exc

        with pytest.raises(ConnectionError) as exc_info:
            await use_case.execute(_make_request(), crawler)

        assert exc_info.value is original_exc
