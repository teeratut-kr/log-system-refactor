import pandas as pd
import streamlit as st

try:
    from frontend.components import (
        build_rank_chart,
        format_logs_table,
        render_export_actions,
        render_severity_chart,
        render_timeline_chart,
        safe_series,
        top_counts,
    )
    from frontend.config import SEVERITY_THRESHOLD_HIGH
except ModuleNotFoundError:
    from components import (
        build_rank_chart,
        format_logs_table,
        render_export_actions,
        render_severity_chart,
        render_timeline_chart,
        safe_series,
        top_counts,
    )
    from config import SEVERITY_THRESHOLD_HIGH


def render_overview(df: pd.DataFrame, total_count: int) -> None:
    high_severity_count = int((safe_series(df, "severity").fillna(-1) >= SEVERITY_THRESHOLD_HIGH).sum())
    unique_users = int(safe_series(df, "user").dropna().astype(str).replace("", pd.NA).dropna().nunique())
    unique_event_types = int(safe_series(df, "event_type").dropna().astype(str).replace("", pd.NA).dropna().nunique())
    unique_tenants = int(safe_series(df, "tenant").dropna().astype(str).replace("", pd.NA).dropna().nunique())
    unique_sources = int(safe_series(df, "source").dropna().astype(str).replace("", pd.NA).dropna().nunique())
    visible_rows = len(df)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total logs", f"{total_count:,}")
    c2.metric("Visible rows", f"{visible_rows:,}")
    c3.metric("High severity", f"{high_severity_count:,}")
    c4.metric("Unique users", f"{unique_users:,}")
    c5.metric("Event types", f"{unique_event_types:,}")

    c6, c7 = st.columns(2)
    with c6:
        st.caption(f"Visible tenants: {unique_tenants:,}")
    with c7:
        st.caption(f"Visible sources: {unique_sources:,}")

    render_export_actions(df)

    left, right = st.columns([1.7, 1.1])
    with left:
        render_timeline_chart(df)
    with right:
        render_severity_chart(df)

    col1, col2 = st.columns(2)
    with col1:
        build_rank_chart(top_counts(df, "src_ip"), "src_ip", "Top source IPs", "No source IP data.")
    with col2:
        build_rank_chart(top_counts(df, "user"), "user", "Top users", "No user data.")

    col3, col4 = st.columns(2)
    with col3:
        build_rank_chart(top_counts(df, "event_type"), "event_type", "Top event types", "No event type data.")
    with col4:
        build_rank_chart(top_counts(df, "tenant"), "tenant", "Top tenants", "No tenant data.")

    with st.expander("Recent logs table", expanded=True):
        logs_table = format_logs_table(df)
        st.dataframe(logs_table, use_container_width=True, height=520)
