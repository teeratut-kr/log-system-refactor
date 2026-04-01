from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_root_and_whoami_endpoints(client):
    root = client.get("/")
    assert root.status_code == 200
    payload = root.json()
    assert payload["service"] == "Unified Log Ingestion API"
    assert "/ingest" in payload["http_endpoints"]

    whoami = client.get("/whoami", headers={"X-User": "admin1"})
    assert whoami.status_code == 200
    assert whoami.json() == {"username": "admin1", "role": "admin", "tenant": None}


def test_ingest_and_query_round_trip(client):
    body = {
        "tenant": "demoA",
        "source": "aws",
        "event_type": "login_failed",
        "user": "alice",
        "src_ip": "10.0.0.50",
        "severity": 7,
        "reason": "wrong_password",
        "@timestamp": _iso_now(),
        "raw": {"message": "login failed"},
    }

    ingest = client.post("/ingest", json=body)
    assert ingest.status_code == 200
    assert ingest.json()["status"] == "ok"

    logs = client.get("/logs", headers={"X-User": "admin1"})
    assert logs.status_code == 200
    payload = logs.json()
    assert payload["count"] >= 1
    assert any(item.get("user") == "alice" for item in payload["items"])


def test_viewer_cannot_request_other_tenant_logs(client):
    response = client.get("/logs?tenant=demoB", headers={"X-User": "viewerA"})
    assert response.status_code == 403
    assert "can only access tenant" in response.json()["detail"]
