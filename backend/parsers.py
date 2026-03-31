import csv
import io
import json
import re
from typing import Any, Dict, List, Optional

from .normalizer import normalize_timestamp
from .schemas import DEFAULT_TENANT

RFC5424_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<version>\d)\s+"
    r"(?P<timestamp>\S+)\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<app>\S+)\s+"
    r"(?P<procid>\S+)\s+"
    r"(?P<msgid>\S+)\s+"
    r"(?P<message>.*)$"
)

RFC3164_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d\d:\d\d:\d\d)\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<tag>[^:]+):?\s*"
    r"(?P<message>.*)$"
)

RFC3164_NO_TAG_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d\d:\d\d:\d\d)\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<message>.*)$"
)


def parse_kv_pairs(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for token in text.split():
        if "=" in token:
            key, value = token.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def parse_syslog_line(line: str, tenant: Optional[str] = None, source_hint: str = "network") -> Dict[str, Any]:
    text = line.strip()
    if not text:
        raise ValueError("empty syslog line")

    m5424 = RFC5424_RE.match(text)
    if m5424:
        g = m5424.groupdict()
        data = parse_kv_pairs(g["message"])
        return {
            "@timestamp": normalize_timestamp(g["timestamp"]),
            "tenant": tenant or DEFAULT_TENANT,
            "source": source_hint,
            "host": None if g["host"] == "-" else g["host"],
            "process": None if g["app"] == "-" else g["app"],
            "message": g["message"],
            "raw": text,
            **data,
        }

    m3164_no_tag = RFC3164_NO_TAG_RE.match(text)
    if m3164_no_tag:
        g = m3164_no_tag.groupdict()
        data = parse_kv_pairs(g["message"])
        return {
            "@timestamp": normalize_timestamp(g["timestamp"]),
            "tenant": tenant or DEFAULT_TENANT,
            "source": source_hint,
            "host": g["host"],
            "process": None,
            "message": g["message"],
            "raw": text,
            **data,
        }

    m3164 = RFC3164_RE.match(text)
    if m3164:
        g = m3164.groupdict()
        data = parse_kv_pairs(g["message"])
        return {
            "@timestamp": normalize_timestamp(g["timestamp"]),
            "tenant": tenant or DEFAULT_TENANT,
            "source": source_hint,
            "host": g["host"],
            "process": g["tag"],
            "message": g["message"],
            "raw": text,
            **data,
        }

    data = parse_kv_pairs(text)
    return {
        "@timestamp": normalize_timestamp(None),
        "tenant": tenant or DEFAULT_TENANT,
        "source": source_hint,
        "message": text,
        "raw": text,
        **data,
    }


def parse_text_lines(content: str, tenant: Optional[str], source_hint: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for line in content.splitlines():
        text = line.strip()
        if not text:
            continue

        if text.startswith("{") and text.endswith("}"):
            item = json.loads(text)
            item.setdefault("tenant", tenant or DEFAULT_TENANT)
            item.setdefault("source", source_hint)
            items.append(item)
        else:
            items.append(parse_syslog_line(text, tenant=tenant, source_hint=source_hint))

    return items


def parse_csv_content(content: str, tenant: Optional[str], source_hint: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    items: List[Dict[str, Any]] = []

    for row in reader:
        item = dict(row)
        item.setdefault("tenant", tenant or DEFAULT_TENANT)
        item.setdefault("source", source_hint)
        items.append(item)

    return items


def parse_uploaded_file(
    filename: str,
    content: bytes,
    tenant: Optional[str],
    source_hint: str,
) -> List[Dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    lower = filename.lower()

    if lower.endswith(".json"):
        payload = json.loads(text)
        if isinstance(payload, list):
            items = [dict(x) for x in payload]
        elif isinstance(payload, dict):
            items = [dict(payload)]
        else:
            raise ValueError("unsupported .json structure")

        for item in items:
            item.setdefault("tenant", tenant or DEFAULT_TENANT)
            item.setdefault("source", source_hint)
        return items

    if lower.endswith(".jsonl"):
        return parse_text_lines(text, tenant, source_hint)

    if lower.endswith(".csv"):
        return parse_csv_content(text, tenant, source_hint)

    if lower.endswith((".log", ".txt")):
        return parse_text_lines(text, tenant, source_hint)

    raise ValueError("unsupported file type; use .json, .jsonl, .csv, .log, or .txt")
