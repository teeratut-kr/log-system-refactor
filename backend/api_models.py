from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AuthContextResponse(BaseModel):
    username: str
    role: str
    tenant: Optional[str] = None
    effective_tenant: Optional[str] = None


class WhoAmIResponse(BaseModel):
    username: str
    role: str
    tenant: Optional[str] = None


class IngestSingleResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]
    auth: Optional[Dict[str, Any]] = None


class FileIngestError(BaseModel):
    index: int
    detail: Any
    input: Dict[str, Any]


class FileIngestResponse(BaseModel):
    status: str
    filename: Optional[str] = None
    received: int
    accepted: int
    rejected: int
    items: List[Dict[str, Any]]
    errors: List[FileIngestError]
    auth: Optional[Dict[str, Any]] = None


class LogsResponse(BaseModel):
    count: int
    items: List[Dict[str, Any]]
    auth: AuthContextResponse


class AlertItemResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class AlertsResponse(BaseModel):
    rule: str
    count: int
    items: List[AlertItemResponse]
    auth: AuthContextResponse


class RetentionStatusResponse(BaseModel):
    backend: str
    retention_days: int
    mode: str
    total_logs: int
    oldest_event_time: Optional[str] = None
    newest_event_time: Optional[str] = None
    cleanup_interval_minutes: int
    last_run: Optional[Dict[str, Any]] = None
    auth: AuthContextResponse


class RetentionRunResponse(BaseModel):
    backend: str
    retention_days: int
    mode: Optional[str] = None
    cutoff: str
    deleted: int
    before: int
    remaining: int
    oldest_event_time_before: Optional[str] = None
    newest_event_time_before: Optional[str] = None
    auth: AuthContextResponse


class RootResponse(BaseModel):
    service: str
    protocols: List[str]
    http_endpoints: List[str]
    syslog_udp: str
    storage: str
    auth: Dict[str, Any]
    tenant_access_policy: Dict[str, str]
    retention: Dict[str, Any]
