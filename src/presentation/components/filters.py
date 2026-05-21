from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st


def render_sentiment_filter() -> str | None:
    options = ["All", "Positive", "Negative", "Neutral"]
    choice = st.sidebar.selectbox("Sentiment", options, index=0)
    return None if choice == "All" else choice.lower()


def render_platform_filter() -> str | None:
    options = ["All", "Twitter", "Facebook", "Instagram"]
    choice = st.sidebar.selectbox("Platform", options, index=0)
    return None if choice == "All" else choice.lower()


def render_date_range_filter(
    default_start: date | None = None,
    default_end: date | None = None,
) -> tuple[date | None, date | None]:
    col1, col2 = st.sidebar.columns(2)
    start = col1.date_input("Start date", value=default_start or date(2025, 1, 1))
    end = col2.date_input("End date", value=default_end or date.today())
    if start > end:
        st.sidebar.warning("Start date must be before end date.")
        return None, None
    return start, end


def render_keyword_filter() -> str:
    return st.sidebar.text_input("Keyword", placeholder="Search keyword...")


def render_pagination(
    total: int,
    page_size: int = 50,
    key: str = "page",
) -> tuple[int, int]:
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.sidebar.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key=key,
    )
    offset = (page - 1) * page_size
    return offset, page_size


def render_campaign_selector(
    campaigns: list[dict[str, Any]],
    key: str = "campaign",
) -> str | None:
    if not campaigns:
        st.sidebar.info("No campaigns available.")
        return None
    options: dict[str, str] = {f"{c['keyword']} ({c['platform']})": str(c["id"]) for c in campaigns}
    label = st.sidebar.selectbox("Campaign", list(options.keys()), key=key)
    return options.get(label)


def render_multi_campaign_selector(
    campaigns: list[dict[str, Any]],
    key: str = "campaigns",
) -> list[str]:
    if not campaigns:
        st.sidebar.info("No campaigns available.")
        return []
    options: dict[str, str] = {f"{c['keyword']} ({c['platform']})": str(c["id"]) for c in campaigns}
    labels = st.sidebar.multiselect("Campaigns to compare", list(options.keys()), key=key)
    return [options[label] for label in labels]
