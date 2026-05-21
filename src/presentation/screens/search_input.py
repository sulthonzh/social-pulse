from __future__ import annotations

import os
import subprocess
import time
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import httpx
import streamlit as st

from src.domain.exceptions import SocialPulseError
from src.domain.value_objects.platform import Platform
from src.shared.config import get_db_connection

if TYPE_CHECKING:
    import duckdb

# In Docker, services talk via service names; locally it's localhost
_API_BASE = "http://api:8000" if os.path.exists("/.dockerenv") else "http://localhost:8000"
_MAX_KEYWORD_LENGTH = 200
_MAX_DATE_RANGE_DAYS = 365


def _api_available() -> bool:
    """Check if the pipeline API is reachable."""
    try:
        httpx.get(f"{_API_BASE}/api/health", timeout=2.0)
        return True
    except httpx.ConnectError:
        return False


def _ensure_api_server() -> bool:
    """Check if the pipeline API is reachable.

    NOT cached — API availability changes over time (container restarts, etc).
    Called only on form submission, so the overhead of a health-check GET is negligible.
    """
    if _api_available():
        return True

    # In Docker the api service should be running separately — no auto-start
    if os.path.exists("/.dockerenv"):
        return False

    # Local dev: spawn uvicorn as subprocess
    subprocess.Popen(
        ["uv", "run", "python", "-m", "src.api.app"],  # noqa: S607
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(20):
        if _api_available():
            return True
        time.sleep(0.5)
    return False


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
            if not _ensure_api_server():
                st.error("Pipeline API server failed to start.")
                return

            api_url = f"{_API_BASE}/api/pipeline/start"

            try:
                response = httpx.post(
                    api_url,
                    json={
                        "keyword": keyword.strip(),
                        "platform": platform.value,
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                run_id = response.json()["run_id"]

                from src.presentation.components.pipeline_progress import (  # noqa: PLC0415
                    render_pipeline_progress,
                )

                render_pipeline_progress(run_id)

            except httpx.HTTPStatusError as exc:
                st.error(f"Pipeline API error: {exc.response.status_code}")
            except Exception as exc:
                st.error(f"Failed to start pipeline: {exc}")
    except SocialPulseError as exc:
        st.error(f"Failed to create request: {exc}")


def render() -> None:
    st.header("Search Input")
    st.markdown("Create a new search request to crawl social media posts.")

    with st.form("search_form"):
        keyword = st.text_input("Keyword", placeholder="e.g. data engineering")
        platform_choice = st.selectbox("Platform", ["twitter", "facebook", "instagram", "youtube", "reddit"])

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
