from typing import Any, Dict, List

import requests
import streamlit as st

try:
    from frontend.config import DEFAULT_FETCH_LIMIT, REQUEST_TIMEOUT_SECONDS
except ModuleNotFoundError:
    from config import DEFAULT_FETCH_LIMIT, REQUEST_TIMEOUT_SECONDS


@st.cache_data(ttl=5, show_spinner=False)
def auth_headers(selected_user: str) -> Dict[str, str]:
    return {"X-User": selected_user}


@st.cache_data(ttl=5, show_spinner=False)
def fetch_logs(api_base: str, params: Dict[str, Any], selected_user: str) -> Dict[str, Any]:
    response = requests.get(
        f"{api_base.rstrip('/')}/logs",
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=5, show_spinner=False)
def fetch_alerts(api_base: str, params: Dict[str, Any], selected_user: str) -> Dict[str, Any]:
    response = requests.get(
        f"{api_base.rstrip('/')}/alerts",
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=10, show_spinner=False)
def fetch_all_logs_for_options(api_base: str, selected_user: str) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{api_base.rstrip('/')}/logs",
        params={"limit": DEFAULT_FETCH_LIMIT, "offset": 0},
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=auth_headers(selected_user),
    )
    response.raise_for_status()
    return response.json().get("items", [])
