from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st


def render_sentiment_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No sentiment data available.")
        return
    df = pd.DataFrame(data)
    color_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#f59e0b"}
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("sentiment:N", title="Sentiment"),
            y=alt.Y("count:Q", title="Posts"),
            color=alt.Color("sentiment:N", scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values()))),
        )
        .properties(width=400, height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def render_volume_trend(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No volume data available.")
        return
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("count:Q", title="Posts"),
        )
        .properties(width=700, height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def render_hashtag_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No hashtag data available.")
        return
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("hashtag:N", sort="-x", title="Hashtag"),
        )
        .properties(width=400, height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def render_comparison_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No comparison data available.")
        return
    df = pd.DataFrame(data)
    df_melted = df.melt(id_vars=["campaign"], var_name="metric", value_name="value")
    chart = (
        alt.Chart(df_melted)
        .mark_bar()
        .encode(
            x=alt.X("campaign:N", title="Campaign"),
            y=alt.Y("value:Q", title="Percentage"),
            color=alt.Color("metric:N"),
        )
        .properties(width=600, height=350)
    )
    st.altair_chart(chart, use_container_width=True)


def render_volume_comparison_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No volume comparison data available.")
        return
    df = pd.DataFrame(data)
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("count:Q", title="Posts"),
            color=alt.Color("campaign:N"),
        )
        .properties(width=700, height=350)
    )
    st.altair_chart(chart, use_container_width=True)


def render_engagement_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        st.info("No engagement data available.")
        return
    df = pd.DataFrame(data)
    df_melted = df.melt(id_vars=["campaign"], var_name="metric", value_name="value")
    metrics = ["likes", "shares", "replies", "views"]
    df_melted = df_melted[df_melted["metric"].isin(metrics)]
    chart = (
        alt.Chart(df_melted)
        .mark_bar()
        .encode(
            x=alt.X("campaign:N", title="Campaign"),
            y=alt.Y("value:Q", title="Count"),
            color=alt.Color("metric:N"),
        )
        .properties(width=600, height=350)
    )
    st.altair_chart(chart, use_container_width=True)
