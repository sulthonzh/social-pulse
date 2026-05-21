from __future__ import annotations

from typing import Any

import duckdb
import streamlit as st

from src.presentation.components.filters import (
    render_date_range_filter,
    render_keyword_filter,
    render_pagination,
    render_platform_filter,
    render_sentiment_filter,
)
from src.shared.config import get_db_connection


def _get_conn() -> duckdb.DuckDBPyConnection:
    return get_db_connection()


def _query_posts(
    conn: duckdb.DuckDBPyConnection,
    keyword: str | None,
    sentiment: str | None,
    platform: str | None,
    start_date: Any | None,
    end_date: Any | None,
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    conditions: list[str] = []
    params: list[Any] = []

    if keyword:
        conditions.append("post_text ILIKE ?")
        params.append(f"%{keyword}%")
    if sentiment:
        conditions.append("sentiment = ?")
        params.append(sentiment)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if start_date and end_date:
        conditions.append("posted_at BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_row = conn.execute(
        f"SELECT COUNT(*) FROM gold.gold_post_search {where}",
        params,
    ).fetchone()
    total = int(count_row[0]) if count_row else 0

    rows = conn.execute(
        f"""
        SELECT author_handle, author_name, post_text, sentiment,
               sentiment_confidence, posted_at, like_count, share_count,
               reply_count, platform, topic_label, language
        FROM gold.gold_post_search
        {where}
        ORDER BY posted_at DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    posts = [
        {
            "author": r[0] or r[1] or "Unknown",
            "text": r[2] or "",
            "sentiment": r[3] or "unknown",
            "confidence": round(float(r[4] or 0), 2),
            "date": str(r[5])[:10] if r[5] else "",
            "likes": int(r[6] or 0),
            "shares": int(r[7] or 0),
            "replies": int(r[8] or 0),
            "platform": str(r[9] or ""),
            "topic": str(r[10] or ""),
            "language": str(r[11] or ""),
        }
        for r in rows
    ]
    return posts, total


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
        conn = _get_conn()
        offset, limit = render_pagination(total=10000, page_size=50, key="explorer_page")
        posts, total = _query_posts(
            conn, keyword, sentiment, platform, start_date, end_date, offset, limit
        )
        conn.close()
    except Exception as exc:
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
