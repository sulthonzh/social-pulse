import sys

import streamlit as st

from src.presentation.screens import (
    campaign_analytics,
    cross_campaign,
    post_explorer,
    search_input,
)


def main() -> None:
    """Entry point for the socialpulse console script."""
    from streamlit.web import bootstrap  # noqa: PLC0415

    if len(sys.argv) == 1:
        sys.argv.extend(
            [
                "run",
                __file__,
                "--server.port=8501",
                "--server.address=0.0.0.0",
            ]
        )
    bootstrap.run(__file__, False, [], {})


st.set_page_config(page_title="SocialPulse", layout="wide", page_icon="📊")

page = st.sidebar.selectbox(
    "Navigate",
    ["Search Input", "Post Explorer", "Campaign Analytics", "Cross-Campaign Comparison"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**SocialPulse** — Social Media Analytics")

if page == "Search Input":
    search_input.render()
elif page == "Post Explorer":
    post_explorer.render()
elif page == "Campaign Analytics":
    campaign_analytics.render()
else:
    cross_campaign.render()
