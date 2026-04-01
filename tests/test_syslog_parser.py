from backend.parsers import parse_syslog_line


def test_parse_syslog_line_extracts_core_fields():
    line = "<190>Aug 20 13:01:02 r1 event_type=login_failed tenant=demoA user=alice src_ip=10.10.10.10 reason=wrong_password"
    item = parse_syslog_line(line, source_hint="network")

    assert item["tenant"] == "demoA"
    assert item["source"] == "network"
    assert item["user"] == "alice"
    assert item["src_ip"] == "10.10.10.10"
    assert item["reason"] == "wrong_password"
