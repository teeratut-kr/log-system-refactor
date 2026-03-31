from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .helpers import clamp_limit, compute_failed_login_alerts, parse_iso_datetime, stringify_for_search


class InMemoryStorage:
    def __init__(self, retention_days: int = 7) -> None:
        self.items: List[Dict[str, Any]] = []
        self.retention_days = max(1, int(retention_days))

    @property
    def backend_name(self) -> str:
        return "memory"

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def save_log(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self.items.append(item)
        return item

    async def query_logs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant: Optional[str] = None,
        source: Optional[str] = None,
        action: Optional[str] = None,
        min_severity: Optional[int] = None,
        max_severity: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = clamp_limit(limit)
        offset = max(0, offset)
        start_dt = parse_iso_datetime(start)
        end_dt = parse_iso_datetime(end)
        q_lower = q.lower() if q else None
        tag_lower = tag.lower() if tag else None

        filtered: List[Dict[str, Any]] = []
        for item in reversed(self.items):
            if tenant and item.get("tenant") != tenant:
                continue
            if source and item.get("source") != source:
                continue
            if action and item.get("action") != action:
                continue

            sev = item.get("severity")
            if min_severity is not None and (sev is None or sev < min_severity):
                continue
            if max_severity is not None and (sev is None or sev > max_severity):
                continue

            item_dt = parse_iso_datetime(item.get("@timestamp"))
            if start_dt and item_dt and item_dt < start_dt:
                continue
            if end_dt and item_dt and item_dt > end_dt:
                continue

            if tag_lower:
                tags = item.get("_tags") or []
                if not any(str(x).lower() == tag_lower for x in tags):
                    continue

            if q_lower:
                haystack = " ".join(
                    stringify_for_search(item.get(key))
                    for key in [
                        "tenant",
                        "source",
                        "vendor",
                        "product",
                        "event_type",
                        "event_subtype",
                        "severity",
                        "action",
                        "src_ip",
                        "dst_ip",
                        "protocol",
                        "user",
                        "host",
                        "process",
                        "url",
                        "status",
                        "workload",
                        "rule_name",
                        "rule_id",
                        "reason",
                        "interface",
                        "mac_address",
                        "raw",
                    ]
                ).lower()
                if q_lower not in haystack:
                    continue

            filtered.append(item)

        return {
            "count": len(filtered),
            "items": filtered[offset : offset + limit],
        }

    async def query_alerts(
        self,
        *,
        tenant: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        threshold: int = 3,
        window_minutes: int = 5,
        limit: int = 100,
    ) -> Dict[str, Any]:
        start_dt = parse_iso_datetime(start)
        end_dt = parse_iso_datetime(end)

        filtered: List[Dict[str, Any]] = []
        for item in self.items:
            if tenant and item.get("tenant") != tenant:
                continue
            item_dt = parse_iso_datetime(item.get("@timestamp"))
            if start_dt and item_dt and item_dt < start_dt:
                continue
            if end_dt and item_dt and item_dt > end_dt:
                continue
            filtered.append(item)

        return compute_failed_login_alerts(
            filtered,
            threshold=threshold,
            window_minutes=window_minutes,
            limit=limit,
        )

    async def run_retention(self, *, retention_days: Optional[int] = None) -> Dict[str, Any]:
        days = max(1, int(retention_days or self.retention_days))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        before = len(self.items)
        kept: List[Dict[str, Any]] = []
        removed = 0
        for item in self.items:
            event_dt = parse_iso_datetime(item.get("@timestamp"))
            if event_dt is not None and event_dt < cutoff:
                removed += 1
                continue
            kept.append(item)
        self.items = kept
        return {
            "backend": self.backend_name,
            "retention_days": days,
            "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
            "deleted": removed,
            "remaining": len(self.items),
            "before": before,
        }

    async def get_retention_status(self) -> Dict[str, Any]:
        event_times = [
            parse_iso_datetime(item.get("@timestamp"))
            for item in self.items
            if parse_iso_datetime(item.get("@timestamp")) is not None
        ]
        oldest = min(event_times).isoformat().replace("+00:00", "Z") if event_times else None
        newest = max(event_times).isoformat().replace("+00:00", "Z") if event_times else None
        return {
            "backend": self.backend_name,
            "retention_days": self.retention_days,
            "mode": "delete",
            "total_logs": len(self.items),
            "oldest_event_time": oldest,
            "newest_event_time": newest,
        }
