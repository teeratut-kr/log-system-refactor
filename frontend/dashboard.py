import json
import os
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Unified Log Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8012")
BACKEND_USERS = ["admin1", "viewerA", "viewerB"]
USER_DIRECTORY = {
    "admin1": {"role": "admin", "tenant": "All", "display": "admin"},
    "viewerA": {"role": "viewer", "tenant": "demoA", "display": "viewerA"},
    "viewerB": {"role": "viewer", "tenant": "demoB", "display": "viewerB"},
}
LOGIN_CREDENTIALS = {
    "admin": {"password": "admin", "backend_user": "admin1"},
    "viewerA": {"password": "viewerA", "backend_user": "viewerA"},
    "viewerB": {"password": "viewerB", "backend_user": "viewerB"},
}
SEVERITY_THRESHOLD_HIGH = 5
RAW_PREVIEW_MAX_LEN = 72


def inject_css() -> None:
    st.markdown(
        """
        <style>
            #MainMenu, footer {visibility: hidden;}
            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            [data-testid="stHeaderActionElements"] {
                display: none;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
            section[data-testid="stSidebar"] {
                min-width: 320px !important;
                width: 320px !important;
                transform: none !important;
                visibility: visible !important;
            }
            section[data-testid="stSidebar"][aria-expanded="false"] {
                min-width: 320px !important;
                width: 320px !important;
                margin-left: 0 !important;
                transform: none !important;
            }
            section[data-testid="stSidebar"] > div {
                min-width: 320px !important;
                width: 320px !important;
            }
            .block-container {
                padding-top: 1.0rem;
                padding-bottom: 2rem;
                max-width: 1480px;
            }
            section[data-testid="stSidebar"] .block-container {
                padding-top: 1rem;
            }
            .dashboard-hero {
                padding: 1.15rem 1.25rem;
                border: 1px solid rgba(120, 120, 120, 0.18);
                border-radius: 18px;
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(16, 185, 129, 0.05));
                margin-bottom: 1rem;
            }
            .dashboard-title {
                font-size: 1.85rem;
                font-weight: 700;
                margin: 0;
            }
            .dashboard-subtitle {
                font-size: 0.98rem;
                opacity: 0.85;
                margin-top: 0.35rem;
                margin-bottom: 0.75rem;
            }
            .pill-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 0.25rem;
            }
            .pill {
                border: 1px solid rgba(120, 120, 120, 0.22);
                background: rgba(255, 255, 255, 0.04);
                border-radius: 999px;
                padding: 0.32rem 0.72rem;
                font-size: 0.84rem;
            }
            .section-card {
                border: 1px solid rgba(120, 120, 120, 0.18);
                border-radius: 18px;
                padding: 0.8rem 1rem 0.55rem 1rem;
                background: rgba(255, 255, 255, 0.02);
                margin-bottom: 1rem;
            }
            .small-muted {
                color: rgba(190, 190, 190, 0.95);
                font-size: 0.9rem;
            }
            .sidebar-badge {
                border: 1px solid rgba(120, 120, 120, 0.18);
                background: rgba(255, 255, 255, 0.03);
                border-radius: 14px;
                padding: 0.75rem 0.85rem;
                margin-bottom: 0.9rem;
            }
            .sidebar-badge strong {
                display: block;
                margin-bottom: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session() -> None:
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("login_name", None)
    st.session_state.setdefault("backend_user", None)
    st.session_state.setdefault("login_error", None)
    st.session_state.setdefault("testing_switch_enabled", False)
    st.session_state.setdefault("active_test_user", None)


init_session()
inject_css()


@st.cache_data(ttl=5, show_spinner=False)
def auth_headers(selected_user: str) -> Dict[str, str]:
    return {"X-User": selected_user}


@st.cache_data(ttl=5, show_spinner=False)
def fetch_logs(api_base: str, params: Dict[str, Any], selected_user: str) -> Dict[str, Any]:
    response = requests.get(
        f"{api_base.rstrip('/')}/logs",
        params=params,
        timeout=15,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=5, show_spinner=False)
def fetch_alerts(api_base: str, params: Dict[str, Any], selected_user: str) -> Dict[str, Any]:
    response = requests.get(
        f"{api_base.rstrip('/')}/alerts",
        params=params,
        timeout=15,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=10, show_spinner=False)
def fetch_all_logs_for_options(api_base: str, selected_user: str) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{api_base.rstrip('/')}/logs",
        params={"limit": 1000, "offset": 0},
        timeout=15,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json().get("items", [])


def to_iso_utc(dt_value: Optional[datetime]) -> Optional[str]:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(dtype="object")


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


def format_raw_for_display(value: Any, max_len: int = RAW_PREVIEW_MAX_LEN) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"

    if isinstance(value, dict):
        if "message" in value and value["message"] is not None:
            text = str(value["message"])
        else:
            text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    return text[:max_len] + "..." if len(text) > max_len else text


def format_logs_table(df: pd.DataFrame) -> pd.DataFrame:
    desired_columns = [
        "@timestamp",
        "tenant",
        "source",
        "event_type",
        "severity",
        "src_ip",
        "dst_ip",
        "user",
        "action",
        "raw",
    ]

    table_df = df.copy()
    for col in desired_columns:
        if col not in table_df.columns:
            table_df[col] = None

    table_df = table_df[desired_columns].sort_values(by="@timestamp", ascending=False, na_position="last")
    display_df = table_df.copy()

    if "raw" in display_df.columns:
        display_df["raw"] = table_df["raw"].apply(lambda x: format_raw_for_display(x, max_len=RAW_PREVIEW_MAX_LEN))

    if "@timestamp" in display_df.columns:
        ts = pd.to_datetime(display_df["@timestamp"], errors="coerce", utc=True)
        display_df["@timestamp"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S UTC").fillna("-")

    if "severity" in display_df.columns:
        sev = pd.to_numeric(display_df["severity"], errors="coerce")
        display_df["severity"] = sev.apply(lambda x: "-" if pd.isna(x) else str(int(x)))

    display_df = display_df.fillna("-").reset_index(drop=True)
    display_df.index = display_df.index + 1

    return display_df


def format_alerts_table(alerts: List[Dict[str, Any]]) -> pd.DataFrame:
    if not alerts:
        return pd.DataFrame(
            columns=["last_seen", "src_ip", "match_count", "users", "tenants", "event_types", "description"]
        )

    rows: List[Dict[str, Any]] = []
    for alert in alerts:
        rows.append(
            {
                "last_seen": alert.get("last_seen", "-"),
                "src_ip": alert.get("src_ip", "-"),
                "match_count": alert.get("match_count", 0),
                "users": ", ".join(alert.get("users") or []) or "-",
                "tenants": ", ".join(alert.get("tenants") or []) or "-",
                "event_types": ", ".join(alert.get("event_types") or []) or "-",
                "description": alert.get("description", "-"),
            }
        )
    return pd.DataFrame(rows)


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["severity", "dst_port", "src_port"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def role_label(profile: Dict[str, str]) -> str:
    return "Administrator" if profile["role"] == "admin" else "Viewer"


def render_app_header(profile: Dict[str, str], effective_user: str) -> None:
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <div class="dashboard-title">Unified Log Dashboard</div>
            <div class="dashboard-subtitle">Monitor normalized logs, inspect tenant visibility, review alerts, and demo the platform without changing your backend flow.</div>
            <div class="pill-row">
                <div class="pill">Logged in as: {st.session_state.login_name or '-'}</div>
                <div class="pill">Effective user: {effective_user}</div>
                <div class="pill">Role: {role_label(profile)}</div>
                <div class="pill">Tenant scope: {profile['tenant']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filter_summary(
    selected_tenant: str,
    selected_source: str,
    min_severity: int,
    keyword: str,
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    keyword_value = keyword.strip() or "None"
    st.markdown(
        f"""
        <div class="section-card">
            <strong>Active filters</strong><br>
            <span class="small-muted">
                Tenant: {selected_tenant} &nbsp;•&nbsp; Source: {selected_source} &nbsp;•&nbsp; Min severity: {min_severity} &nbsp;•&nbsp; Keyword: {keyword_value}<br>
                Time range: {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')} UTC-assumed
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_export_actions(df: pd.DataFrame) -> None:
    export_df = format_logs_table(df)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    c1, c2 = st.columns([1, 2.2])
    with c1:
        st.download_button(
            "Download visible rows (CSV)",
            data=csv_bytes,
            file_name="visible_logs.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        st.caption("Export only includes rows currently visible under the active filters.")


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

    timeline_df = build_timeline(df)
    left, right = st.columns([1.7, 1.1])
    with left:
        st.subheader("Log activity over time")
        if timeline_df.empty:
            st.info("No timestamp data available for the current filters.")
        else:
            fig = px.line(timeline_df, x="time_bucket", y="count", markers=True)
            fig.update_traces(mode="lines+markers+text", text=timeline_df["count"], textposition="top center")
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=330, xaxis_title=None, yaxis_title="count")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        sev = safe_series(df, "severity").dropna()
        if sev.empty:
            st.subheader("Severity distribution")
            st.info("No severity data available.")
        else:
            sev_df = sev.astype(int).value_counts().sort_index().reset_index()
            sev_df.columns = ["severity", "count"]
            st.subheader("Severity distribution")
            fig = px.bar(sev_df, x="severity", y="count", text="count")
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=330, xaxis_title=None, yaxis_title="count")
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        build_rank_chart(top_counts(df, "src_ip"), "src_ip", "Top source IPs", "No source IP data.")
    with col4:
        build_rank_chart(top_counts(df, "user"), "user", "Top users", "No user data.")

    col3, col4 = st.columns(2)
    with col3:
        build_rank_chart(top_counts(df, "event_type"), "event_type", "Top event types", "No event type data.")
    with col4:
        build_rank_chart(top_counts(df, "tenant"), "tenant", "Top tenants", "No tenant data.")

    with st.expander("Recent logs table", expanded=True):
        logs_table = format_logs_table(df)
        st.dataframe(logs_table, use_container_width=True, height=520)


def render_alerts(api_base: str, base_params: Dict[str, Any], selected_user: str) -> None:
    alert_params = {
        "threshold": 3,
        "window_minutes": 5,
        "limit": 100,
    }
    if base_params.get("tenant"):
        alert_params["tenant"] = base_params["tenant"]
    if base_params.get("start"):
        alert_params["start"] = base_params["start"]
    if base_params.get("end"):
        alert_params["end"] = base_params["end"]

    try:
        payload = fetch_alerts(api_base, alert_params, selected_user)
        items = payload.get("items", [])
        count = payload.get("count", 0)
    except Exception as exc:
        st.error(f"Failed to load alerts from backend: {exc}")
        return

    st.markdown(
        """
        <div class="section-card">
            <strong>Alert rule</strong><br>
            <span class="small-muted">Repeated failed logins from the same IP within 5 minutes (threshold = 3).</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total alerts", f"{count:,}")
    c2.metric("Affected IPs", f"{len({str(x.get('src_ip')) for x in items if x.get('src_ip')}):,}")
    c3.metric("Sample events", f"{sum(len(x.get('sample_events') or []) for x in items):,}")

    if not items:
        st.success("No alerts were triggered for the current filters.")
        return

    top_col, detail_col = st.columns([1, 1.2])
    with top_col:
        build_rank_chart(top_counts(pd.DataFrame(items), "src_ip"), "src_ip", "Alerted IPs", "No IP data.", height=320)

    with detail_col:
        st.subheader("Alert list")
        st.dataframe(format_alerts_table(items), use_container_width=True, height=320)

    st.subheader("Alert details")
    for idx, alert in enumerate(items, start=1):
        title = f"{idx}. {alert.get('src_ip', '-')} • {alert.get('match_count', 0)} failed logins"
        with st.expander(title):
            st.write(alert.get("description", "-"))
            c1, c2 = st.columns(2)
            c1.write(f"First seen: {alert.get('first_seen', '-')}")
            c2.write(f"Last seen: {alert.get('last_seen', '-')}")
            st.write(f"Users: {', '.join(alert.get('users') or []) or '-'}")
            st.write(f"Tenants: {', '.join(alert.get('tenants') or []) or '-'}")
            sample_df = pd.DataFrame(alert.get("sample_events") or [])
            if not sample_df.empty:
                st.dataframe(sample_df.fillna("-"), use_container_width=True)


def attempt_login(username: str, password: str) -> bool:
    record = LOGIN_CREDENTIALS.get(username)
    if not record or record["password"] != password:
        st.session_state.logged_in = False
        st.session_state.login_name = None
        st.session_state.backend_user = None
        st.session_state.login_error = "Invalid username or password"
        return False

    st.session_state.logged_in = True
    st.session_state.login_name = username
    st.session_state.backend_user = record["backend_user"]
    st.session_state.testing_switch_enabled = False
    st.session_state.active_test_user = record["backend_user"]
    st.session_state.login_error = None
    return True


def clear_filter_state(profile: Dict[str, str]) -> None:
    default_end = datetime.now().replace(minute=0, second=0, microsecond=0)
    default_start = default_end - timedelta(days=7)
    st.session_state["selected_tenant"] = profile["tenant"] if profile["role"] == "viewer" else "All"
    st.session_state["selected_source"] = "All"
    st.session_state["min_severity"] = 0
    st.session_state["keyword"] = ""
    st.session_state["start_date"] = default_start.date()
    st.session_state["start_time"] = time(0, 0)
    st.session_state["end_date"] = default_end.date()
    st.session_state["end_time"] = time(default_end.hour, 0)


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.login_name = None
    st.session_state.backend_user = None
    st.session_state.login_error = None
    st.session_state.testing_switch_enabled = False
    st.session_state.active_test_user = None
    st.cache_data.clear()


def resolve_effective_user() -> str:
    base_user = st.session_state.backend_user or "admin1"
    if st.session_state.get("testing_switch_enabled"):
        return st.session_state.get("active_test_user") or base_user
    return base_user


def ensure_filter_state(profile: Dict[str, str], tenant_options: List[str], source_options: List[str]) -> None:
    default_end = datetime.now().replace(minute=0, second=0, microsecond=0)
    default_start = default_end - timedelta(days=7)

    if profile["role"] == "viewer":
        st.session_state["selected_tenant"] = profile["tenant"]
    else:
        st.session_state.setdefault("selected_tenant", "All")
        if st.session_state["selected_tenant"] not in ["All"] + tenant_options:
            st.session_state["selected_tenant"] = "All"

    st.session_state.setdefault("selected_source", "All")
    if st.session_state["selected_source"] not in ["All"] + source_options:
        st.session_state["selected_source"] = "All"

    st.session_state.setdefault("min_severity", 0)
    st.session_state.setdefault("keyword", "")
    st.session_state.setdefault("start_date", default_start.date())
    st.session_state.setdefault("start_time", time(0, 0))
    st.session_state.setdefault("end_date", default_end.date())
    st.session_state.setdefault("end_time", time(default_end.hour, 0))


def render_login_gate() -> None:
    hero_left, hero_right = st.columns([1.25, 1])
    with hero_left:
        st.markdown(
            """
            <div class="dashboard-hero">
                <div class="dashboard-title">Unified Log Dashboard</div>
                <div class="dashboard-subtitle">Portfolio-ready Streamlit view for your existing FastAPI + PostgreSQL log platform.</div>
                <div class="pill-row">
                    <div class="pill">HTTP JSON ingest</div>
                    <div class="pill">Syslog ingest</div>
                    <div class="pill">Role-based visibility</div>
                    <div class="pill">Alerts + filters</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            if submitted:
                if attempt_login(username.strip(), password):
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
params: Dict[str, Any] = {"limit": 1000, "offset": 0}
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
    render_alerts(api_base, params, selected_user)
