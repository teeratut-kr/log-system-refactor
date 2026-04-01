def test_alert_rule_triggers_for_repeated_failed_logins(client):
    events = [
        {"tenant": "demoA", "source": "aws", "event_type": "login_failed", "user": "alice", "src_ip": "10.10.10.10", "reason": "wrong_password", "@timestamp": "2026-03-31T10:00:00Z"},
        {"tenant": "demoA", "source": "aws", "event_type": "login_failed", "user": "alice", "src_ip": "10.10.10.10", "reason": "wrong_password", "@timestamp": "2026-03-31T10:02:00Z"},
        {"tenant": "demoA", "source": "aws", "event_type": "login_failed", "user": "alice", "src_ip": "10.10.10.10", "reason": "wrong_password", "@timestamp": "2026-03-31T10:04:00Z"},
    ]
    for event in events:
        response = client.post("/ingest", json=event)
        assert response.status_code == 200

    alert_response = client.get("/alerts", headers={"X-User": "admin1"})
    assert alert_response.status_code == 200
    payload = alert_response.json()
    assert payload["count"] >= 1
    assert payload["items"][0]["src_ip"] == "10.10.10.10"
    assert payload["items"][0]["match_count"] >= 3
