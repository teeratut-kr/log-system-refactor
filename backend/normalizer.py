import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .schemas import DEFAULT_TENANT, NormalizedLog, SourceEnum


def safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_nested(data: Dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def first_non_empty(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = get_nested(data, key) if "." in key else data.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_timestamp(value: Any) -> str:
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)

    if value in (None, ""):
        return now_utc.isoformat().replace("+00:00", "Z")

    text = str(value).strip()

    if text.endswith("Z"):
        return text

    try:
        dt = datetime.fromisoformat(text.replace(" ", "T"))
        if dt.tzinfo is None:
            return dt.replace(microsecond=0).isoformat() + "Z"
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    try:
        dt = datetime.strptime(f"{now_utc.year} {text}", "%Y %b %d %H:%M:%S")
        return dt.replace(microsecond=0).isoformat() + "Z"
    except ValueError:
        pass

    return now_utc.isoformat().replace("+00:00", "Z")


def normalize_source(value: Any, default: str) -> str:
    text = str(value or default).lower()
    if text in SourceEnum._value2member_map_:
        return text
    return default


def to_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def normalize_tenant(value: Any) -> Optional[str]:
    if value in (None, ""):
        return DEFAULT_TENANT

    text = str(value).strip()
    return text or DEFAULT_TENANT


def normalize_action(value: Any, message: Any = "") -> Optional[str]:
    raw = str(value).lower() if value not in (None, "") else to_text(message).lower()

    mapping = {
        "allow": "allow",
        "accepted": "allow",
        "permit": "allow",
        "deny": "deny",
        "denied": "deny",
        "blocked": "deny",
        "block": "deny",
        "create": "create",
        "created": "create",
        "delete": "delete",
        "deleted": "delete",
        "login": "login",
        "logged in": "login",
        "logout": "logout",
        "logged out": "logout",
        "alert": "alert",
        "quarantine": "alert",
    }

    for key, mapped in mapping.items():
        if key in raw:
            return mapped
    return None


def infer_event_type(message: Any, fallback: Optional[str] = None) -> Optional[str]:
    if fallback:
        return fallback

    msg = to_text(message).lower()

    if "login failed" in msg or "authentication failed" in msg:
        return "login_failed"
    if "login success" in msg or "logged in" in msg:
        return "login_success"
    if "malware" in msg:
        return "malware_detected"
    if "link-down" in msg:
        return "link_down"
    if "deny" in msg or "blocked" in msg:
        return "connection_denied"
    if "allow" in msg or "accepted" in msg:
        return "connection_allowed"
    if msg:
        return "event"

    return None


def infer_severity(value: Any, message: Any = "") -> Optional[int]:
    sev = safe_int(value)
    if sev is not None:
        return max(0, min(10, sev))

    msg = to_text(message).lower()
    if any(x in msg for x in ["critical", "fatal", "emergency"]):
        return 10
    if any(x in msg for x in ["error", "failed", "malware", "deny", "blocked"]):
        return 7
    if "warning" in msg:
        return 5
    if any(x in msg for x in ["info", "notice"]):
        return 3
    return None


def choose_raw_payload(raw_item: Dict[str, Any], original_raw: Any = None) -> Any:
    if raw_item.get("raw") is not None:
        return raw_item.get("raw")
    if original_raw is not None:
        return original_raw
    return raw_item


def normalize_log(
    raw_item: Dict[str, Any],
    default_source: str = "api",
    original_raw: Any = None,
) -> Dict[str, Any]:
    message = to_text(first_non_empty(raw_item, "message", "msg", "event_message", "reason", "raw"))

    explicit_source = first_non_empty(raw_item, "source")
    if explicit_source in (None, ""):
        vendor_text = to_text(first_non_empty(raw_item, "vendor")).lower()
        product_text = to_text(first_non_empty(raw_item, "product")).lower()
        if "crowdstrike" in vendor_text or "crowdstrike" in product_text or "falcon" in product_text:
            source = "crowdstrike"
        else:
            source = normalize_source(None, default_source)
    else:
        source = normalize_source(explicit_source, default_source)

    normalized = {
        "@timestamp": normalize_timestamp(first_non_empty(raw_item, "@timestamp", "timestamp", "time")),
        "tenant": normalize_tenant(first_non_empty(raw_item, "tenant")),
        "source": source,
        "vendor": first_non_empty(raw_item, "vendor"),
        "product": first_non_empty(raw_item, "product"),
        "event_type": infer_event_type(message, first_non_empty(raw_item, "event_type")),
        "event_subtype": first_non_empty(raw_item, "event_subtype"),
        "severity": infer_severity(first_non_empty(raw_item, "severity", "level"), message),
        "action": normalize_action(first_non_empty(raw_item, "action"), message),
        "src_ip": first_non_empty(raw_item, "src_ip", "ip", "source_ip", "client_ip", "src"),
        "src_port": safe_int(first_non_empty(raw_item, "src_port", "source_port", "spt")),
        "dst_ip": first_non_empty(raw_item, "dst_ip", "destination_ip", "server_ip", "dst"),
        "dst_port": safe_int(first_non_empty(raw_item, "dst_port", "destination_port", "server_port", "dpt")),
        "protocol": first_non_empty(raw_item, "protocol", "proto"),
        "user": first_non_empty(raw_item, "user", "username", "principal"),
        "host": first_non_empty(raw_item, "host", "hostname", "device_name"),
        "process": first_non_empty(raw_item, "process", "process_name", "app"),
        "url": first_non_empty(raw_item, "url", "uri", "path"),
        "http_method": first_non_empty(raw_item, "http_method", "method"),
        "status_code": safe_int(first_non_empty(raw_item, "status_code", "http_status", "response_code")),
        "status": first_non_empty(raw_item, "status", "result", "outcome"),
        "workload": first_non_empty(raw_item, "workload"),
        "rule_name": first_non_empty(raw_item, "rule_name", "policy_name", "policy"),
        "rule_id": first_non_empty(raw_item, "rule_id", "policy_id"),
        "reason": first_non_empty(raw_item, "reason"),
        "interface": first_non_empty(raw_item, "interface", "if"),
        "mac_address": first_non_empty(raw_item, "mac", "mac_address"),
        "file.hash.sha256": first_non_empty(raw_item, "file.hash.sha256", "file_hash_sha256", "sha256"),
        "cloud.account_id": first_non_empty(raw_item, "cloud.account_id", "account_id"),
        "cloud.region": first_non_empty(raw_item, "cloud.region", "region"),
        "cloud.service": first_non_empty(raw_item, "cloud.service", "service"),
        "raw": choose_raw_payload(raw_item, original_raw=original_raw),
        "_tags": first_non_empty(raw_item, "_tags", "tags"),
    }

    validated = NormalizedLog(**normalized)
    return validated.model_dump(by_alias=True, exclude_none=False)
