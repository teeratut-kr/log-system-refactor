
def test_file_ingest_jsonl_round_trip(client):
    content = b'{"tenant": "demoA", "source": "aws", "event_type": "login_success", "user": "jsonl-user"}\n'
    response = client.post(
        "/ingest/file",
        files={"file": ("events.jsonl", content, "application/json")},
        data={"source_hint": "aws"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] == 1
    assert payload["rejected"] == 0

    logs = client.get("/logs", headers={"X-User": "admin1"}).json()
    assert any(item.get("user") == "jsonl-user" for item in logs["items"])


def test_file_ingest_csv_round_trip(client):
    content = b"tenant,source,event_type,user,src_ip\ndemoA,aws,login_failed,csv-user,10.0.0.99\n"
    response = client.post(
        "/ingest/file",
        files={"file": ("events.csv", content, "text/csv")},
        data={"source_hint": "aws"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] == 1
    assert payload["rejected"] == 0

    logs = client.get("/logs?q=csv-user", headers={"X-User": "admin1"}).json()
    assert logs["count"] >= 1
