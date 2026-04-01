import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SYSLOG_UDP_PORT", "0")
os.environ.setdefault("RETENTION_CLEANUP_INTERVAL_MINUTES", "60")
os.environ.pop("DATABASE_URL", None)

from backend.main import create_app  # noqa: E402


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
