from __future__ import annotations

import asyncio
from datetime import date

import duckdb
import streamlit as st

from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)
from src.shared.config import get_db_connection


def _get_conn() -> duckdb.DuckDBPyConnection:
    return get_db_connection()


def _get_recent_requests(conn: duckdb.DuckDBPyConnection) -> list[dict]:
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


def render() -> None:
    st.header("Search Input")
    st.markdown("Create a new search request to crawl social media posts.")

    with st.form("search_form"):
        keyword = st.text_input("Keyword", placeholder="e.g. data engineering")
        platform_choice = st.selectbox("Platform", ["twitter", "facebook", "instagram"])
        start, end = st.date_input(
            "Date range",
            value=(date(2025, 1, 1), date.today()),
        )
        submitted = st.form_submit_button("Create Search Request")

        if submitted:
            if not keyword.strip():
                st.error("Keyword is required.")
            else:
                try:
                    platform = Platform(platform_choice)
                    if isinstance(start, tuple):
                        start_date, end_date = start
                    else:
                        start_date = start
                        end_date = end

                    from src.application.use_cases.search_posts import SearchPosts  # noqa: PLC0415

                    conn = _get_conn()
                    repo = DuckDBSearchRequestRepository(conn)
                    use_case = SearchPosts(repo)
                    result = asyncio.get_event_loop().run_until_complete(
                        use_case.execute(
                            keyword=keyword.strip(),
                            platform=platform,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )
                    conn.close()
                    st.success(
                        f"Search request created: **{result.keyword}** "
                        f"on {result.platform.value} ({result.id})"
                    )
                except Exception as exc:
                    st.error(f"Failed to create request: {exc}")

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
            status_emoji = {
                "completed": "✅",
                "running": "⏳",
                "pending": "📝",
                "failed": "❌",
            }.get(req["status"], "❓")
            st.markdown(
                f"{status_emoji} **{req['keyword']}** — {req['platform']} — "
                f"{req['start_date']} to {req['end_date']} — "
                f"{req['posts_found']} posts — _{req['status']}_"
            )
