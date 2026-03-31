from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .helpers import clamp_limit, compute_failed_login_alerts, parse_iso_datetime, serialize_raw_for_text_column
from .sql import ALLOW_NULL_TENANT_SQL, CREATE_TABLE_SQL


class PostgresStorage:
    def __init__(self, database_url: str, retention_days: int = 7) -> None:
        self.database_url = database_url
        self.retention_days = max(1, int(retention_days))
        self.pool = AsyncConnectionPool(
            conninfo=database_url,
            open=False,
            min_size=1,
            max_size=10,
            kwargs={"autocommit": False, "row_factory": dict_row},
        )

    @property
    def backend_name(self) -> str:
        return "postgresql"

    async def startup(self) -> None:
        await self.pool.open(wait=True)
        await self._init_schema()

    async def shutdown(self) -> None:
        await self.pool.close()

    async def _init_schema(self) -> None:
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(CREATE_TABLE_SQL)
                await cur.execute(ALLOW_NULL_TENANT_SQL)
            await conn.commit()

    async def save_log(self, item: Dict[str, Any]) -> Dict[str, Any]:
        event_time = parse_iso_datetime(item.get("@timestamp"))
        if event_time is None:
            raise ValueError("missing or invalid @timestamp")

        query = """
        INSERT INTO logs (
            event_time,
            tenant,
            source,
            vendor,
            product,
            event_type,
            event_subtype,
            severity,
            action,
            src_ip,
            src_port,
            dst_ip,
            dst_port,
            protocol,
            user_name,
            host,
            process,
            url,
            http_method,
            status_code,
            status,
            workload,
            rule_name,
            rule_id,
            reason,
            logon_type,
            interface,
            mac_address,
            file_hash_sha256,
            cloud_account_id,
            cloud_region,
            cloud_service,
            raw,
            tags,
            document
        )
        VALUES (
            %(event_time)s,
            %(tenant)s,
            %(source)s,
            %(vendor)s,
            %(product)s,
            %(event_type)s,
            %(event_subtype)s,
            %(severity)s,
            %(action)s,
            %(src_ip)s,
            %(src_port)s,
            %(dst_ip)s,
            %(dst_port)s,
            %(protocol)s,
            %(user_name)s,
            %(host)s,
            %(process)s,
            %(url)s,
            %(http_method)s,
            %(status_code)s,
            %(status)s,
            %(workload)s,
            %(rule_name)s,
            %(rule_id)s,
            %(reason)s,
            %(logon_type)s,
            %(interface)s,
            %(mac_address)s,
            %(file_hash_sha256)s,
            %(cloud_account_id)s,
            %(cloud_region)s,
            %(cloud_service)s,
            %(raw)s,
            %(tags)s,
            %(document)s
        )
        """

        params = {
            "event_time": event_time,
            "tenant": item.get("tenant"),
            "source": item.get("source"),
            "vendor": item.get("vendor"),
            "product": item.get("product"),
            "event_type": item.get("event_type"),
            "event_subtype": item.get("event_subtype"),
            "severity": item.get("severity"),
            "action": item.get("action"),
            "src_ip": item.get("src_ip"),
            "src_port": item.get("src_port"),
            "dst_ip": item.get("dst_ip"),
            "dst_port": item.get("dst_port"),
            "protocol": item.get("protocol"),
            "user_name": item.get("user"),
            "host": item.get("host"),
            "process": item.get("process"),
            "url": item.get("url"),
            "http_method": item.get("http_method"),
            "status_code": item.get("status_code"),
            "status": item.get("status"),
            "workload": item.get("workload"),
            "rule_name": item.get("rule_name"),
            "rule_id": item.get("rule_id"),
            "reason": item.get("reason"),
            "logon_type": item.get("logon_type"),
            "interface": item.get("interface"),
            "mac_address": item.get("mac_address"),
            "file_hash_sha256": item.get("file.hash.sha256"),
            "cloud_account_id": item.get("cloud.account_id"),
            "cloud_region": item.get("cloud.region"),
            "cloud_service": item.get("cloud.service"),
            "raw": serialize_raw_for_text_column(item.get("raw")),
            "tags": item.get("_tags"),
            "document": Jsonb(item),
        }

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
            await conn.commit()

        return item

    def _build_where_clause(
        self,
        *,
        tenant: Optional[str] = None,
        source: Optional[str] = None,
        action: Optional[str] = None,
        min_severity: Optional[int] = None,
        max_severity: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        if tenant:
            clauses.append("tenant = %s")
            params.append(tenant)
        if source:
            clauses.append("source = %s")
            params.append(source)
        if action:
            clauses.append("action = %s")
            params.append(action)
        if min_severity is not None:
            clauses.append("severity >= %s")
            params.append(min_severity)
        if max_severity is not None:
            clauses.append("severity <= %s")
            params.append(max_severity)
        if start:
            clauses.append("event_time >= %s")
            params.append(parse_iso_datetime(start))
        if end:
            clauses.append("event_time <= %s")
            params.append(parse_iso_datetime(end))
        if tag:
            clauses.append("tags @> ARRAY[%s]::text[]")
            params.append(tag)
        if q:
            clauses.append(
                "("
                "COALESCE(tenant, '') ILIKE %s OR "
                "COALESCE(source, '') ILIKE %s OR "
                "COALESCE(vendor, '') ILIKE %s OR "
                "COALESCE(product, '') ILIKE %s OR "
                "COALESCE(event_type, '') ILIKE %s OR "
                "COALESCE(event_subtype, '') ILIKE %s OR "
                "COALESCE(CAST(severity AS TEXT), '') ILIKE %s OR "
                "COALESCE(action, '') ILIKE %s OR "
                "COALESCE(src_ip, '') ILIKE %s OR "
                "COALESCE(dst_ip, '') ILIKE %s OR "
                "COALESCE(protocol, '') ILIKE %s OR "
                "COALESCE(user_name, '') ILIKE %s OR "
                "COALESCE(host, '') ILIKE %s OR "
                "COALESCE(process, '') ILIKE %s OR "
                "COALESCE(url, '') ILIKE %s OR "
                "COALESCE(status, '') ILIKE %s OR "
                "COALESCE(workload, '') ILIKE %s OR "
                "COALESCE(rule_name, '') ILIKE %s OR "
                "COALESCE(rule_id, '') ILIKE %s OR "
                "COALESCE(reason, '') ILIKE %s OR "
                "COALESCE(interface, '') ILIKE %s OR "
                "COALESCE(mac_address, '') ILIKE %s OR "
                "COALESCE(raw, '') ILIKE %s"
                ")"
            )
            like = f"%{q}%"
            params.extend([like] * 23)

        if not clauses:
            return "", params

        return " WHERE " + " AND ".join(clauses), params

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
        where_sql, params = self._build_where_clause(
            tenant=tenant,
            source=source,
            action=action,
            min_severity=min_severity,
            max_severity=max_severity,
            start=start,
            end=end,
            q=q,
            tag=tag,
        )

        count_query = "SELECT COUNT(*) AS total FROM logs" + where_sql
        items_query = (
            "SELECT document FROM logs"
            + where_sql
            + " ORDER BY event_time DESC, id DESC LIMIT %s OFFSET %s"
        )

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(count_query, params)
                count_row = await cur.fetchone()

                await cur.execute(items_query, [*params, limit, offset])
                rows = await cur.fetchall()

        return {
            "count": int(count_row["total"] if count_row else 0),
            "items": [row["document"] for row in rows],
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
        clauses = ["src_ip IS NOT NULL"]
        params: List[Any] = []

        if tenant:
            clauses.append("tenant = %s")
            params.append(tenant)
        if start:
            clauses.append("event_time >= %s")
            params.append(parse_iso_datetime(start))
        if end:
            clauses.append("event_time <= %s")
            params.append(parse_iso_datetime(end))

        where_sql = " WHERE " + " AND ".join(clauses)
        query = (
            "SELECT document FROM logs"
            + where_sql
            + " ORDER BY src_ip ASC, event_time ASC, id ASC LIMIT %s"
        )
        params.append(5000)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()

        items = [row["document"] for row in rows]
        return compute_failed_login_alerts(
            items,
            threshold=threshold,
            window_minutes=window_minutes,
            limit=limit,
        )

    async def run_retention(self, *, retention_days: Optional[int] = None) -> Dict[str, Any]:
        days = max(1, int(retention_days or self.retention_days))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        count_before_query = "SELECT COUNT(*) AS total FROM logs"
        oldest_before_query = "SELECT MIN(event_time) AS oldest_event_time, MAX(event_time) AS newest_event_time FROM logs"
        delete_query = "DELETE FROM logs WHERE event_time < %s"
        count_after_query = "SELECT COUNT(*) AS total FROM logs"

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(count_before_query)
                before_row = await cur.fetchone()

                await cur.execute(oldest_before_query)
                before_times = await cur.fetchone()

                await cur.execute(delete_query, [cutoff])
                deleted = cur.rowcount or 0

                await cur.execute(count_after_query)
                after_row = await cur.fetchone()
            await conn.commit()

        return {
            "backend": self.backend_name,
            "retention_days": days,
            "mode": "delete",
            "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
            "deleted": int(deleted),
            "before": int(before_row["total"] if before_row else 0),
            "remaining": int(after_row["total"] if after_row else 0),
            "oldest_event_time_before": (
                before_times["oldest_event_time"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if before_times and before_times.get("oldest_event_time")
                else None
            ),
            "newest_event_time_before": (
                before_times["newest_event_time"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if before_times and before_times.get("newest_event_time")
                else None
            ),
        }

    async def get_retention_status(self) -> Dict[str, Any]:
        query = "SELECT COUNT(*) AS total, MIN(event_time) AS oldest_event_time, MAX(event_time) AS newest_event_time FROM logs"
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                row = await cur.fetchone()

        return {
            "backend": self.backend_name,
            "retention_days": self.retention_days,
            "mode": "delete",
            "total_logs": int(row["total"] if row else 0),
            "oldest_event_time": (
                row["oldest_event_time"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if row and row.get("oldest_event_time")
                else None
            ),
            "newest_event_time": (
                row["newest_event_time"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if row and row.get("newest_event_time")
                else None
            ),
        }
