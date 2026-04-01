from datetime import datetime

import streamlit as st


CSS_BLOCK = """
<style>
    #MainMenu, footer {visibility: hidden;}
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stHeaderActionElements"] {
        display: none;
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
"""


def inject_css() -> None:
    st.markdown(CSS_BLOCK, unsafe_allow_html=True)


def render_app_header(profile: dict[str, str], effective_user: str) -> None:
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <div class="dashboard-title">Unified Log Dashboard</div>
            <div class="dashboard-subtitle">Monitor normalized logs, inspect tenant visibility, review alerts, and demo the platform without changing your backend flow.</div>
            <div class="pill-row">
                <div class="pill">Logged in as: {st.session_state.login_name or '-'}</div>
                <div class="pill">Effective user: {effective_user}</div>
                <div class="pill">Role: {'Administrator' if profile['role'] == 'admin' else 'Viewer'}</div>
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


def render_login_hero() -> None:
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
