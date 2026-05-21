from __future__ import annotations

from typing import Any

import streamlit as st

from src.domain.exceptions import SocialPulseError
from src.presentation.components.filters import (
    render_date_range_filter,
    render_keyword_filter,
    render_pagination,
    render_platform_filter,
    render_sentiment_filter,
)
from src.shared.config import get_db_connection


_SENTIMENT_COLOR = {
    "positive": "color: #22c55e; font-weight: bold",
    "negative": "color: #ef4444; font-weight: bold",
    "neutral": "color: #f59e0b; font-weight: bold",
}


def render() -> None:
    st.header("Post Explorer")

    with st.sidebar:
        st.subheader("Filters")
        keyword = render_keyword_filter()
        sentiment = render_sentiment_filter()
        platform = render_platform_filter()
        start_date, end_date = render_date_range_filter()

    try:
        conn = get_db_connection()
        offset, limit = render_pagination(total=10000, page_size=50, key="explorer_page")

        from src.application.use_cases.search_gold_posts import SearchGoldPosts  # noqa: PLC0415
        from src.infrastructure.persistence.duckdb_gold_post_search_repository import (  # noqa: PLC0415
            DuckDBGoldPostSearchRepository,
        )

        repo = DuckDBGoldPostSearchRepository(conn)
        use_case = SearchGoldPosts(repo)
        result = use_case.execute(
            keyword=keyword or None,
            sentiment=sentiment,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )
        posts: list[dict[str, Any]] = result.posts
        total: int = result.total
        conn.close()
    except SocialPulseError as exc:
        st.warning(f"Could not load posts: {exc}")
        return

    st.metric("Total Posts", total)
    st.divider()

    if not posts:
        st.info("No posts match your filters.")
        return

    for post in posts:
        color = _SENTIMENT_COLOR.get(post["sentiment"], "")
        st.markdown(
            f"**@{post['author']}** · {post['date']} · "
            f"<span style='{color}'>{post['sentiment'].title()}</span> "
            f"({post['confidence']})",
            unsafe_allow_html=True,
        )
        st.write(post["text"])
        cols = st.columns(4)
        cols[0].metric("Likes", post["likes"])
        cols[1].metric("Shares", post["shares"])
        cols[2].metric("Replies", post["replies"])
        cols[3].metric("Platform", post["platform"])
        st.divider()
