from __future__ import annotations

from typing import Any

import duckdb
import streamlit as st

from src.presentation.components.charts import (
    render_hashtag_chart,
    render_sentiment_chart,
    render_volume_trend,
)
from src.presentation.components.filters import render_campaign_selector
from src.shared.config import settings


def _get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(settings.db_path))


def _get_campaigns(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT DISTINCT search_request_id, keyword, platform
        FROM gold.gold_post_search
        ORDER BY keyword
        """
    ).fetchall()
    return [
        {"id": str(r[0]), "keyword": str(r[1]), "platform": str(r[2])}
        for r in rows
    ]


def render() -> None:
    st.header("Campaign Analytics")

    try:
        conn = _get_conn()
        campaigns = _get_campaigns(conn)
    except Exception:
        campaigns = []

    if not campaigns:
        st.info("No campaigns with data available. Run a search first and populate gold tables.")
        return

    selected_id = render_campaign_selector(campaigns, key="campaign_analytics")
    if selected_id is None:
        conn.close() if 'conn' in dir() else None
        return

    from src.application.use_cases.get_campaign_analytics import GetCampaignAnalytics

    try:
        analytics_uc = GetCampaignAnalytics(conn)
        result = analytics_uc.execute(selected_id)
    except Exception as exc:
        st.error(f"Failed to load analytics: {exc}")
        return
    finally:
        conn.close()

    if result is None:
        st.warning("No analytics data found for this campaign.")
        return

    st.subheader(f"Campaign: {result.keyword}")
    st.caption(f"Platform: {result.platform}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Posts", result.total_posts)
    col2.metric("Positive", f"{result.positive_pct}%")
    col3.metric("Negative", f"{result.negative_pct}%")
    col4.metric("Neutral", f"{result.neutral_pct}%")
    col5.metric("Avg Confidence", f"{result.avg_confidence:.2f}")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Sentiment Breakdown")
        render_sentiment_chart(result.sentiment_distribution)

    with chart_col2:
        st.subheader("Volume Trend")
        render_volume_trend(result.daily_volume)

    st.divider()
    col_hash, col_topic = st.columns(2)

    with col_hash:
        st.subheader("Top Hashtags")
        render_hashtag_chart(result.top_hashtags)

    with col_topic:
        st.subheader("Top Topics")
        if result.top_topics:
            for t in result.top_topics:
                st.markdown(f"- **{t['topic']}** ({t['count']})")
        else:
            st.info("No topic data available.")

    st.divider()
    st.subheader("Engagement")
    eng_col1, eng_col2, eng_col3, eng_col4 = st.columns(4)
    eng_col1.metric("Total Likes", result.total_likes)
    eng_col2.metric("Total Shares", result.total_shares)
    eng_col3.metric("Total Replies", result.total_replies)
    eng_col4.metric("Total Views", result.total_views)
