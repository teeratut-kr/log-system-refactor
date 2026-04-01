import os


def env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


DASHBOARD_TITLE = env_str("DASHBOARD_TITLE", "Unified Log Dashboard")
DEFAULT_API_BASE = env_str("DASHBOARD_API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:8012"))
REQUEST_TIMEOUT_SECONDS = env_int("DASHBOARD_REQUEST_TIMEOUT_SECONDS", 15)
DEFAULT_FETCH_LIMIT = env_int("DASHBOARD_DEFAULT_FETCH_LIMIT", 1000)
DEFAULT_LOOKBACK_DAYS = env_int("DASHBOARD_DEFAULT_LOOKBACK_DAYS", 7)
SEVERITY_THRESHOLD_HIGH = env_int("DASHBOARD_SEVERITY_THRESHOLD_HIGH", 5)
RAW_PREVIEW_MAX_LEN = env_int("DASHBOARD_RAW_PREVIEW_MAX_LEN", 72)
