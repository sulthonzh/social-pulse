import streamlit as st

from src.presentation.screens import (
    campaign_analytics,
    cross_campaign,
    post_explorer,
    search_input,
)

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
