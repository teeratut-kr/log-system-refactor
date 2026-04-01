from datetime import datetime, timezone


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_whoami_requires_header(client):
    response = client.get("/whoami")
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["message"] == "Missing X-User header"


def test_retention_endpoints_are_admin_only(client):
    seed = {
        "tenant": "demoA",
        "source": "aws",
        "event_type": "event",
        "user": "seed-user",
        "@timestamp": _iso_now(),
        "raw": {"message": "seed"},
    }
    assert client.post("/ingest", json=seed).status_code == 200

    viewer_status = client.get("/retention", headers={"X-User": "viewerA"})
    assert viewer_status.status_code == 403

    admin_status = client.get("/retention", headers={"X-User": "admin1"})
    assert admin_status.status_code == 200
    assert admin_status.json()["backend"] in {"memory", "postgresql"}

    admin_run = client.post("/retention/run", headers={"X-User": "admin1"})
    assert admin_run.status_code == 200
    assert "deleted" in admin_run.json()
