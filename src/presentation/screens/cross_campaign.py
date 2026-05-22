from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.domain.exceptions import SocialPulseError
from src.presentation.components.charts import (
    render_comparison_chart,
    render_engagement_chart,
    render_volume_comparison_chart,
)
from src.presentation.components.filters import render_multi_campaign_selector
from src.shared.config import get_db_connection

_MIN_CAMPAIGNS_FOR_COMPARISON = 2


def render() -> None:
    st.header("Cross-Campaign Comparison")

    conn = None
    try:
        conn = get_db_connection(read_only=True)

        from src.application.use_cases.get_campaigns import GetCampaigns  # noqa: PLC0415
        from src.infrastructure.persistence.duckdb_gold_post_search_repository import (  # noqa: PLC0415
            DuckDBGoldPostSearchRepository,
        )

        repo = DuckDBGoldPostSearchRepository(conn)
        campaigns_uc = GetCampaigns(repo)
        campaigns: list[dict[str, Any]] = campaigns_uc.execute()
    except Exception:
        campaigns = []

    if not campaigns:
        st.info("No campaigns with data available. Run searches first and populate gold tables.")
        return

    selected_ids = render_multi_campaign_selector(campaigns, key="cross_campaign")
    if len(selected_ids) < _MIN_CAMPAIGNS_FOR_COMPARISON:
        st.warning("Select at least 2 campaigns to compare.")
        if conn:
            conn.close()
        return

    from src.application.use_cases.get_cross_campaign import GetCrossCampaign  # noqa: PLC0415

    try:
        use_case = GetCrossCampaign(conn)  # type: ignore[arg-type]
        result = use_case.execute(selected_ids)
    except SocialPulseError as exc:
        st.error(f"Failed to compare campaigns: {exc}")
        return
    finally:
        if conn:
            conn.close()

    if not result.campaigns:
        st.warning("No data found for selected campaigns.")
        return

    st.subheader("Sentiment Comparison")
    render_comparison_chart(result.sentiment_comparison)

    st.divider()
    st.subheader("Volume Comparison")
    render_volume_comparison_chart(result.volume_comparison)

    st.divider()
    st.subheader("Engagement Comparison")
    render_engagement_chart(result.engagement_comparison)

    st.divider()
    st.subheader("Summary Table")
    rows = [
        {
            "Campaign": c.keyword,
            "Platform": c.platform,
            "Total Posts": c.total_posts,
            "Positive %": c.positive_pct,
            "Negative %": c.negative_pct,
            "Neutral %": c.neutral_pct,
            "Avg Confidence": round(c.avg_confidence, 3),
            "Likes": c.total_likes,
            "Shares": c.total_shares,
            "Replies": c.total_replies,
            "Views": c.total_views,
        }
        for c in result.campaigns
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
