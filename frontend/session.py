from datetime import datetime, time, timedelta
from typing import Dict, List

import streamlit as st

try:
    from frontend.config import DEFAULT_LOOKBACK_DAYS
    from frontend.demo_auth import LOGIN_CREDENTIALS
except ModuleNotFoundError:
    from config import DEFAULT_LOOKBACK_DAYS
    from demo_auth import LOGIN_CREDENTIALS


SESSION_DEFAULTS = {
    "logged_in": False,
    "login_name": None,
    "backend_user": None,
    "login_error": None,
    "testing_switch_enabled": False,
    "active_test_user": None,
}


def init_session() -> None:
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)


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


def clear_filter_state(profile: Dict[str, str]) -> None:
    default_end = datetime.now().replace(minute=0, second=0, microsecond=0)
    default_start = default_end - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    st.session_state["selected_tenant"] = profile["tenant"] if profile["role"] == "viewer" else "All"
    st.session_state["selected_source"] = "All"
    st.session_state["min_severity"] = 0
    st.session_state["keyword"] = ""
    st.session_state["start_date"] = default_start.date()
    st.session_state["start_time"] = time(0, 0)
    st.session_state["end_date"] = default_end.date()
    st.session_state["end_time"] = time(default_end.hour, 0)


def ensure_filter_state(profile: Dict[str, str], tenant_options: List[str], source_options: List[str]) -> None:
    default_end = datetime.now().replace(minute=0, second=0, microsecond=0)
    default_start = default_end - timedelta(days=DEFAULT_LOOKBACK_DAYS)

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
