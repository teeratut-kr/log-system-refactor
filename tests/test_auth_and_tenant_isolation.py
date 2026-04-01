def test_whoami_accepts_x_user_header(client):
    response = client.get("/whoami", headers={"X-User": "admin1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "admin1"
    assert payload["role"] == "admin"


def test_tenant_isolation_for_admin_and_viewers(client):
    items = [
        {"tenant": "demoA", "source": "aws", "event_type": "login_failed", "user": "alice", "src_ip": "10.0.0.1", "reason": "wrong_password", "@timestamp": "2026-03-31T10:00:00Z"},
        {"tenant": "demoB", "source": "aws", "event_type": "login_failed", "user": "bob", "src_ip": "10.0.0.2", "reason": "wrong_password", "@timestamp": "2026-03-31T10:05:00Z"},
        {"tenant": None, "source": "aws", "event_type": "login_failed", "user": "charlie", "src_ip": "10.0.0.3", "reason": "wrong_password", "@timestamp": "2026-03-31T10:10:00Z"},
    ]
    for item in items:
        response = client.post("/ingest", json=item)
        assert response.status_code == 200

    admin_logs = client.get("/logs", headers={"X-User": "admin1"}).json()
    viewer_a_logs = client.get("/logs", headers={"X-User": "viewerA"}).json()
    viewer_b_logs = client.get("/logs", headers={"X-User": "viewerB"}).json()

    assert admin_logs["count"] == 3
    assert viewer_a_logs["count"] == 1
    assert viewer_b_logs["count"] == 1
    assert viewer_a_logs["items"][0]["tenant"] == "demoA"
    assert viewer_b_logs["items"][0]["tenant"] == "demoB"

    forbidden = client.get("/logs?tenant=demoB", headers={"X-User": "viewerA"})
    assert forbidden.status_code == 403
