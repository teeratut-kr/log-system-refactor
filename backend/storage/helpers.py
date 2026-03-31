import json
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, List, Optional

FAILED_LOGIN_EVENT_TYPES = {
    "app_login_failed",
    "login_failed",
    "logonfailed",
    "logon_failed",
    "userloginfailed",
}


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if value in (None, ""):
        return None

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 1000:
        return 1000
    return limit


def stringify_for_search(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def serialize_raw_for_text_column(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def event_type_text(item: Dict[str, Any]) -> str:
    return str(item.get("event_type") or "").strip().lower()


def reason_text(item: Dict[str, Any]) -> str:
    return str(item.get("reason") or "").strip().lower()


def status_text(item: Dict[str, Any]) -> str:
    return str(item.get("status") or "").strip().lower()


def is_failed_login(item: Dict[str, Any]) -> bool:
    event_type = event_type_text(item)
    if event_type in FAILED_LOGIN_EVENT_TYPES:
        return True

    event_id = item.get("event_id")
    if event_id == 4625:
        return True

    if event_type in {"login", "logon"} and status_text(item) in {"failed", "failure", "denied"}:
        return True

    if "wrong_password" in reason_text(item):
        return True

    return False


def compute_failed_login_alerts(
    items: List[Dict[str, Any]],
    *,
    threshold: int,
    window_minutes: int,
    limit: int,
) -> Dict[str, Any]:
    threshold = max(1, int(threshold))
    window_minutes = max(1, int(window_minutes))
    limit = clamp_limit(limit)
    window = timedelta(minutes=window_minutes)

    candidates: List[Dict[str, Any]] = []
    for item in items:
        src_ip = item.get("src_ip") or item.get("ip")
        if not src_ip:
            continue
        if not is_failed_login(item):
            continue
        event_dt = parse_iso_datetime(item.get("@timestamp"))
        if event_dt is None:
            continue
        normalized_item = dict(item)
        normalized_item["src_ip"] = src_ip
        normalized_item["_event_dt"] = event_dt
        candidates.append(normalized_item)

    candidates.sort(key=lambda x: (str(x.get("src_ip")), x["_event_dt"]))

    grouped: Dict[str, Deque[Dict[str, Any]]] = {}
    last_emitted_window_end: Dict[str, datetime] = {}
    alerts: List[Dict[str, Any]] = []

    for item in candidates:
        src_ip = str(item["src_ip"])
        current_dt: datetime = item["_event_dt"]
        dq = grouped.setdefault(src_ip, deque())
        dq.append(item)

        while dq and (current_dt - dq[0]["_event_dt"]) > window:
            dq.popleft()

        if len(dq) < threshold:
            continue

        first_dt = dq[0]["_event_dt"]
        prev_end = last_emitted_window_end.get(src_ip)
        if prev_end is not None and first_dt <= prev_end:
            continue

        window_events = list(dq)
        last_emitted_window_end[src_ip] = current_dt

        tenants = sorted({str(x.get("tenant")) for x in window_events if x.get("tenant")})
        users = sorted({str(x.get("user")) for x in window_events if x.get("user")})
        event_types = sorted({str(x.get("event_type")) for x in window_events if x.get("event_type")})
        sources = sorted({str(x.get("source")) for x in window_events if x.get("source")})

        alerts.append(
            {
                "alert_type": "repeated_failed_login_same_ip_5m",
                "title": "Repeated failed logins from same IP",
                "description": f"IP {src_ip} had {len(window_events)} failed login events within {window_minutes} minutes.",
                "src_ip": src_ip,
                "match_count": len(window_events),
                "threshold": threshold,
                "window_minutes": window_minutes,
                "first_seen": first_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "last_seen": current_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "tenant": tenants[0] if len(tenants) == 1 else None,
                "tenants": tenants,
                "users": users,
                "event_types": event_types,
                "sources": sources,
                "sample_events": [
                    {
                        "@timestamp": x.get("@timestamp"),
                        "tenant": x.get("tenant"),
                        "source": x.get("source"),
                        "event_type": x.get("event_type"),
                        "user": x.get("user"),
                        "reason": x.get("reason"),
                    }
                    for x in window_events[-5:]
                ],
            }
        )

    alerts.sort(key=lambda x: x["last_seen"], reverse=True)
    return {"count": len(alerts), "items": alerts[:limit]}
