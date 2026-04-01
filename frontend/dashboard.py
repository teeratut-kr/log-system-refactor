from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

try:
    from frontend.api import fetch_all_logs_for_options, fetch_logs
    from frontend.components import normalize_numeric_columns, safe_series
    from frontend.config import DASHBOARD_TITLE, DEFAULT_API_BASE, DEFAULT_FETCH_LIMIT
    from frontend.demo_auth import BACKEND_USERS, USER_DIRECTORY, role_label
    from frontend.pages import render_alerts_page, render_overview
    from frontend.session import (
        attempt_login,
        clear_filter_state,
        ensure_filter_state,
        init_session,
        logout,
        resolve_effective_user,
    )
    from frontend.styles import inject_css, render_app_header, render_filter_summary, render_login_hero
except ModuleNotFoundError:
    from api import fetch_all_logs_for_options, fetch_logs
    from components import normalize_numeric_columns, safe_series
    from config import DASHBOARD_TITLE, DEFAULT_API_BASE, DEFAULT_FETCH_LIMIT
    from demo_auth import BACKEND_USERS, USER_DIRECTORY, role_label
    from pages import render_alerts_page, render_overview
    from session import attempt_login, clear_filter_state, ensure_filter_state, init_session, logout, resolve_effective_user
    from styles import inject_css, render_app_header, render_filter_summary, render_login_hero

st.set_page_config(page_title=DASHBOARD_TITLE, page_icon="📊", layout="wide")


init_session()
inject_css()


def to_iso_utc(dt_value: Optional[datetime]) -> Optional[str]:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def render_login_gate() -> None:
    hero_left, hero_right = st.columns([1.25, 1])
    with hero_left:
        render_login_hero()
        st.markdown(
            """
            This version keeps the same backend contract and login flow, but presents the system in a cleaner way for demos and portfolio screenshots.
            """
        )

    with hero_right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="admin / viewerA / viewerB")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted and attempt_login(username.strip(), password):
                st.cache_data.clear()
                st.rerun()

        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])

        st.caption("Demo accounts")
        st.code("admin / admin\nviewerA / viewerA\nviewerB / viewerB")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


if not st.session_state.logged_in:
    render_login_gate()

with st.sidebar:
    st.header("Connection")
    api_base = st.text_input("Backend API base URL", value=DEFAULT_API_BASE)

    col_refresh, col_logout = st.columns(2)
    with col_refresh:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_logout:
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    st.divider()
    logged_in_backend_user = st.session_state.backend_user or "admin1"
    logged_in_profile = USER_DIRECTORY[logged_in_backend_user]

    st.markdown(
        f"""
        <div class="sidebar-badge">
            <strong>Session</strong>
            Logged in as: {st.session_state.login_name or '-'}<br>
            Base role: {role_label(logged_in_profile)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.header("Page")
    page = st.radio("Navigate", options=["Overview", "Alerts"], index=0, label_visibility="collapsed")

    if logged_in_profile["role"] == "admin":
        st.divider()
        st.header("Testing user switcher")
        st.checkbox(
            "Enable testing switcher",
            key="testing_switch_enabled",
            help="For dev/demo only. Lets you test admin/viewer behavior without logging out.",
        )
        current_index = BACKEND_USERS.index(st.session_state.get("active_test_user") or logged_in_backend_user)
        selected_test_user = st.selectbox(
            "Active user",
            options=BACKEND_USERS,
            index=current_index,
            disabled=not st.session_state.get("testing_switch_enabled"),
        )
        st.session_state.active_test_user = selected_test_user
    else:
        st.session_state.testing_switch_enabled = False
        st.session_state.active_test_user = logged_in_backend_user

    st.divider()
    st.header("Filters")

    effective_user = resolve_effective_user()
    effective_profile = USER_DIRECTORY[effective_user]

    try:
        option_items = fetch_all_logs_for_options(api_base, effective_user)
    except Exception:
        option_items = []

    option_df = pd.DataFrame(option_items) if option_items else pd.DataFrame()
    tenant_options = sorted([x for x in safe_series(option_df, "tenant").dropna().astype(str).unique().tolist() if x])
    source_options = sorted([x for x in safe_series(option_df, "source").dropna().astype(str).unique().tolist() if x])

    ensure_filter_state(effective_profile, tenant_options, source_options)

    if st.button("Reset filters", use_container_width=True):
        clear_filter_state(effective_profile)
        st.rerun()

    if effective_profile["role"] == "viewer":
        st.selectbox("Tenant", options=[effective_profile["tenant"]], index=0, disabled=True, key="selected_tenant")
    else:
        st.selectbox("Tenant", options=["All"] + tenant_options, key="selected_tenant")

    st.selectbox("Source", options=["All"] + source_options, key="selected_source")
    st.slider("Minimum severity", min_value=0, max_value=10, key="min_severity")
    st.text_input("Keyword search", key="keyword")

    st.subheader("Time range")
    st.date_input("Start date", key="start_date")
    st.time_input("Start time", key="start_time")
    st.date_input("End date", key="end_date")
    st.time_input("End time", key="end_time")

start_dt = datetime.combine(st.session_state["start_date"], st.session_state["start_time"])
end_dt = datetime.combine(st.session_state["end_date"], st.session_state["end_time"])
params: Dict[str, Any] = {"limit": DEFAULT_FETCH_LIMIT, "offset": 0}
if st.session_state["selected_tenant"] != "All":
    params["tenant"] = st.session_state["selected_tenant"]
if st.session_state["selected_source"] != "All":
    params["source"] = st.session_state["selected_source"]
if st.session_state["min_severity"] > 0:
    params["min_severity"] = st.session_state["min_severity"]
if st.session_state["keyword"].strip():
    params["q"] = st.session_state["keyword"].strip()
if end_dt >= start_dt:
    params["start"] = to_iso_utc(start_dt)
    params["end"] = to_iso_utc(end_dt)

selected_user = resolve_effective_user()
effective_profile = USER_DIRECTORY[selected_user]
render_app_header(effective_profile, selected_user)
render_filter_summary(
    st.session_state["selected_tenant"],
    st.session_state["selected_source"],
    st.session_state["min_severity"],
    st.session_state["keyword"],
    start_dt,
    end_dt,
)

try:
    payload = fetch_logs(api_base, params, selected_user)
    items = payload.get("items", [])
    total_count = payload.get("count", 0)
except Exception as exc:
    st.error(f"Failed to load data from backend: {exc}")
    st.stop()

if page == "Overview":
    if not items:
        st.warning("No logs found for the current filters.")
        st.info("Try widening the time range, clearing the keyword, or changing tenant/source filters.")
        st.stop()

    df = pd.DataFrame(items)
    if "@timestamp" in df.columns:
        df["@timestamp"] = pd.to_datetime(df["@timestamp"], errors="coerce", utc=True)
        df = df.sort_values(by="@timestamp", ascending=False, na_position="last")

    df = normalize_numeric_columns(df)
    render_overview(df, total_count)
else:
    render_alerts_page(api_base, params, selected_user)
