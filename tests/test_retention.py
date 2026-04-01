from datetime import datetime, timezone


def test_retention_deletes_old_logs_and_keeps_recent_logs(client):
    old_event = {
        "tenant": "demoA",
        "source": "aws",
        "event_type": "login_failed",
        "user": "old-user",
        "src_ip": "10.0.0.20",
        "reason": "wrong_password",
        "@timestamp": "2020-01-01T00:00:00Z",
    }
    new_event = {
        "tenant": "demoA",
        "source": "aws",
        "event_type": "login_success",
        "user": "new-user",
        "src_ip": "10.0.0.21",
        "@timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }

    assert client.post("/ingest", json=old_event).status_code == 200
    assert client.post("/ingest", json=new_event).status_code == 200

    before = client.get("/logs", headers={"X-User": "admin1"}).json()
    assert before["count"] == 2

    retention = client.post("/retention/run", headers={"X-User": "admin1"})
    assert retention.status_code == 200
    payload = retention.json()
    assert payload["deleted"] >= 1
    assert payload["remaining"] == 1

    after = client.get("/logs", headers={"X-User": "admin1"}).json()
    assert after["count"] == 1
    assert after["items"][0]["user"] == "new-user"
