from __future__ import annotations

import structlog

from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.exceptions import CrawlError
from src.domain.interfaces import Crawler, CrawlRunRepository, PostRepository, SearchRequestRepository
from src.domain.value_objects.crawl_status import CrawlStatus

logger = structlog.get_logger(__name__)


class IngestCrawlRun:
    """Orchestrates the crawl-ingest pipeline: search request → crawl → bronze persistence."""

    def __init__(
        self,
        search_request_repo: SearchRequestRepository,
        crawl_run_repo: CrawlRunRepository,
        post_repo: PostRepository,
    ) -> None:
        self._search_request_repo = search_request_repo
        self._crawl_run_repo = crawl_run_repo
        self._post_repo = post_repo

    async def execute(self, request: SearchRequest, crawler: Crawler) -> CrawlRun:
        saved_request = self._search_request_repo.save(request)

        crawl_run = CrawlRun(
            search_request_id=saved_request.id,
            platform=saved_request.platform,
            status=CrawlStatus.RUNNING,
        )
        saved_run = self._crawl_run_repo.save(crawl_run)

        try:
            raw_posts = await crawler.crawl(
                keyword=saved_request.keyword,
                start_date=saved_request.start_date,
                end_date=saved_request.end_date,
                platform=saved_request.platform,
            )

            posts = [
                post.model_copy(update={
                    "search_request_id": saved_request.id,
                    "crawl_run_id": saved_run.id,
                })
                for post in raw_posts
            ]

            saved_count = self._post_repo.save_posts(posts)

            self._crawl_run_repo.update_status(
                crawl_run_id=str(saved_run.id),
                status=CrawlStatus.COMPLETED,
                posts_fetched=saved_count,
                error_message=None,
            )
            self._search_request_repo.update_status(
                request_id=str(saved_request.id),
                status=CrawlStatus.COMPLETED,
                posts_found=saved_count,
            )

            logger.info(
                "crawl_completed",
                crawl_run_id=str(saved_run.id),
                search_request_id=str(saved_request.id),
                posts_fetched=saved_count,
                platform=saved_request.platform,
                keyword=saved_request.keyword,
            )

            return saved_run.model_copy(update={
                "status": CrawlStatus.COMPLETED,
                "posts_fetched": saved_count,
            })

        except Exception as exc:
            self._crawl_run_repo.update_status(
                crawl_run_id=str(saved_run.id),
                status=CrawlStatus.FAILED,
                posts_fetched=0,
                error_message=str(exc),
            )
            self._search_request_repo.update_status(
                request_id=str(saved_request.id),
                status=CrawlStatus.FAILED,
                posts_found=0,
            )

            logger.error(
                "crawl_failed",
                crawl_run_id=str(saved_run.id),
                search_request_id=str(saved_request.id),
                error=str(exc),
                error_type=type(exc).__name__,
            )

            raise
