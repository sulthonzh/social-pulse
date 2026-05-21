from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import streamlit as st

from src.domain.exceptions import SocialPulseError
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling import create_crawler
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import DuckDBPostRepository
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)
from src.shared.config import get_db_connection

if TYPE_CHECKING:
    import duckdb

_MAX_KEYWORD_LENGTH = 200
_MAX_DATE_RANGE_DAYS = 365


def _get_conn() -> duckdb.DuckDBPyConnection:
    return get_db_connection()


def _get_recent_requests(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, keyword, platform, start_date, end_date,
               status, posts_found, created_at
        FROM bronze.search_requests
        ORDER BY created_at DESC
        LIMIT 20
        """
    ).fetchall()
    return [
        {
            "id": str(r[0]),
            "keyword": r[1],
            "platform": r[2],
            "start_date": str(r[3]),
            "end_date": str(r[4]),
            "status": r[5],
            "posts_found": r[6],
            "created_at": str(r[7]),
        }
        for r in rows
    ]


def _handle_submission(
    keyword: str,
    platform_choice: str,
    start_date_input: Any,
) -> None:
    if not keyword.strip():
        st.error("Keyword is required.")
        return

    if len(keyword.strip()) > _MAX_KEYWORD_LENGTH:
        st.error(f"Keyword must be {_MAX_KEYWORD_LENGTH} characters or less.")
        return

    try:
        platform = Platform(platform_choice)

        if len(start_date_input) == 0:
            start_date = date(2025, 1, 1)
            end_date = date.today()
        else:
            start_date = start_date_input[0]
            end_date = start_date_input[1] if len(start_date_input) > 1 else date.today()

        if start_date > end_date:
            st.error("Start date must be before end date.")
        elif (end_date - start_date).days > _MAX_DATE_RANGE_DAYS:
            st.error(f"Date range must be {_MAX_DATE_RANGE_DAYS} days or less.")
        else:
            from src.application.use_cases.ingest_crawl import (  # noqa: PLC0415
                IngestCrawlRun,
            )
            from src.application.use_cases.search_posts import (  # noqa: PLC0415
                SearchPosts,
            )

            conn = _get_conn()
            try:
                search_request_repo = DuckDBSearchRequestRepository(conn)
                crawl_run_repo = DuckDBCrawlRunRepository(conn)
                post_repo = DuckDBPostRepository(conn)

                create_use_case = SearchPosts(search_request_repo)
                request = asyncio.run(
                    create_use_case.execute(
                        keyword=keyword.strip(),
                        platform=platform,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

                crawler = create_crawler()
                ingest_use_case = IngestCrawlRun(
                    search_request_repo=search_request_repo,
                    crawl_run_repo=crawl_run_repo,
                    post_repo=post_repo,
                )
                crawl_result = asyncio.run(
                    ingest_use_case.execute(request, crawler)
                )
                st.success(
                    f"Crawled **{request.keyword}** on {request.platform.value} "
                    f"— {crawl_result.posts_fetched} posts found ({request.id})"
                )
            except Exception as crawl_exc:
                st.warning(
                    f"Search created but crawling failed: {crawl_exc}"
                )
            finally:
                conn.close()
    except SocialPulseError as exc:
        st.error(f"Failed to create request: {exc}")


def render() -> None:
    st.header("Search Input")
    st.markdown("Create a new search request to crawl social media posts.")

    with st.form("search_form"):
        keyword = st.text_input("Keyword", placeholder="e.g. data engineering")
        platform_choice = st.selectbox("Platform", ["twitter", "facebook", "instagram"])

        # The date input can return different types depending on how many dates are selected
        start_date_input = st.date_input(
            "Date range",
            value=(date.today() - timedelta(days=90), date.today()),
        )
        submitted = st.form_submit_button("Create Search Request")

        if submitted:
            _handle_submission(keyword, platform_choice, start_date_input)

    st.divider()
    st.subheader("Recent Search Requests")

    try:
        conn = _get_conn()
        requests = _get_recent_requests(conn)
        conn.close()
    except Exception:
        requests = []

    if not requests:
        st.info("No search requests yet. Create one above.")
    else:
        for req in requests:
            status_label = {
                "completed": "Completed",
                "running": "Running",
                "pending": "Pending",
                "failed": "Failed",
            }.get(req["status"], "Unknown")
            st.markdown(
                f"**{req['keyword']}** | {req['platform']} | "
                f"{req['start_date']} to {req['end_date']} | "
                f"{req['posts_found']} posts | {status_label}"
            )
