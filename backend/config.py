import os
from dataclasses import dataclass


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


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


APP_TITLE = env_str("APP_TITLE", "Unified Log Ingestion API")
APP_ENV = env_str("APP_ENV", "development")
LOG_LEVEL = env_str("LOG_LEVEL", "INFO").upper()
LOG_USE_JSON = env_bool("LOG_USE_JSON", False)

SYSLOG_UDP_HOST = env_str("SYSLOG_UDP_HOST", "0.0.0.0")
SYSLOG_UDP_PORT = env_int("SYSLOG_UDP_PORT", 5514)
RETENTION_DAYS = env_int("RETENTION_DAYS", 7)
RETENTION_CLEANUP_INTERVAL_MINUTES = env_int("RETENTION_CLEANUP_INTERVAL_MINUTES", 60)


@dataclass(frozen=True)
class BackendRuntimeConfig:
    app_title: str = APP_TITLE
    app_env: str = APP_ENV
    log_level: str = LOG_LEVEL
    log_use_json: bool = LOG_USE_JSON
    syslog_udp_host: str = SYSLOG_UDP_HOST
    syslog_udp_port: int = SYSLOG_UDP_PORT
    retention_days: int = RETENTION_DAYS
    retention_cleanup_interval_minutes: int = RETENTION_CLEANUP_INTERVAL_MINUTES


def get_runtime_config() -> BackendRuntimeConfig:
    return BackendRuntimeConfig()
