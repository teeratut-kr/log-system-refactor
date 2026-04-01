import importlib
import os
import sys


def reload_module(module_name: str):
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def test_backend_config_reads_log_level_and_retention_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("RETENTION_DAYS", "9")
    config = reload_module("backend.config")
    assert config.LOG_LEVEL == "DEBUG"
    assert config.RETENTION_DAYS == 9


def test_frontend_config_prefers_dashboard_api_base_url(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8011")
    monkeypatch.setenv("DASHBOARD_API_BASE_URL", "http://127.0.0.1:8012")
    config = reload_module("frontend.config")
    assert config.DEFAULT_API_BASE == "http://127.0.0.1:8012"
