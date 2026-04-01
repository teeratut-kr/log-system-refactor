from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def safe_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(dtype="object")


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["severity", "dst_port", "src_port"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def top_counts(df: pd.DataFrame, column: str, top_n: int = 10) -> pd.DataFrame:
    series = safe_series(df, column).dropna().astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return pd.DataFrame(columns=[column, "count"])
    counts = series.value_counts().head(top_n).reset_index()
    counts.columns = [column, "count"]
    return counts.sort_values("count", ascending=False).reset_index(drop=True)


def build_timeline(df: pd.DataFrame) -> pd.DataFrame:
    if "@timestamp" not in df.columns:
        return pd.DataFrame(columns=["time_bucket", "count"])
    ts = pd.to_datetime(df["@timestamp"], errors="coerce", utc=True).dropna()
    if ts.empty:
        return pd.DataFrame(columns=["time_bucket", "count"])

    span = ts.max() - ts.min()
    bucket = ts.dt.floor("h") if span <= pd.Timedelta(days=2) else ts.dt.floor("D")
    timeline = bucket.value_counts().sort_index().reset_index()
    timeline.columns = ["time_bucket", "count"]
    return timeline


def build_rank_chart(data: pd.DataFrame, label_col: str, title: str, empty_message: str, height: int = 310) -> None:
    st.subheader(title)
    if data.empty:
        st.info(empty_message)
        return

    chart_df = data.sort_values("count", ascending=False).reset_index(drop=True)
    fig = px.bar(chart_df, x=label_col, y="count", text="count")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        height=height,
        xaxis_title=None,
        yaxis_title="count",
        uniformtext_minsize=8,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(categoryorder="total descending", tickangle=-20)
    st.plotly_chart(fig, use_container_width=True)


def render_timeline_chart(df: pd.DataFrame) -> None:
    timeline_df = build_timeline(df)
    st.subheader("Log activity over time")
    if timeline_df.empty:
        st.info("No timestamp data available for the current filters.")
        return

    fig = px.line(timeline_df, x="time_bucket", y="count", markers=True)
    fig.update_traces(mode="lines+markers+text", text=timeline_df["count"], textposition="top center")
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=330, xaxis_title=None, yaxis_title="count")
    st.plotly_chart(fig, use_container_width=True)


def render_severity_chart(df: pd.DataFrame) -> None:
    sev = safe_series(df, "severity").dropna()
    st.subheader("Severity distribution")
    if sev.empty:
        st.info("No severity data available.")
        return

    sev_df = sev.astype(int).value_counts().sort_index().reset_index()
    sev_df.columns = ["severity", "count"]
    fig = px.bar(sev_df, x="severity", y="count", text="count")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=330, xaxis_title=None, yaxis_title="count")
    st.plotly_chart(fig, use_container_width=True)
