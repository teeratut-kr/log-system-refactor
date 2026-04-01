from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..api_models import RootResponse, WhoAmIResponse
from ..auth import UserContext, get_user_context
from ..config import RETENTION_CLEANUP_INTERVAL_MINUTES, RETENTION_DAYS, SYSLOG_UDP_HOST, SYSLOG_UDP_PORT
from ..demo_users import DEMO_USERS

router = APIRouter()


@router.get("/", response_model=RootResponse)
async def root(request: Request):
    storage = getattr(request.app.state, "storage", None)
    return {
        "service": "Unified Log Ingestion API",
        "protocols": ["HTTP", "UDP"],
        "http_endpoints": ["/ingest", "/ingest/file", "/logs", "/alerts", "/whoami", "/retention", "/retention/run"],
        "syslog_udp": f"{SYSLOG_UDP_HOST}:{SYSLOG_UDP_PORT}",
        "storage": storage.backend_name if storage else "unknown",
        "auth": {
            "header": "X-User",
            "required_for": ["/logs", "/alerts", "/whoami", "/retention", "/retention/run"],
            "not_required_for": ["/ingest", "/ingest/file"],
            "users": DEMO_USERS,
        },
        "tenant_access_policy": {
            "admin": "can view all logs, including tenant-null logs",
            "viewer": "can only view logs for their own tenant and cannot view tenant-null logs",
        },
        "retention": {
            "mode": "delete",
            "retention_days": RETENTION_DAYS,
            "cleanup_interval_minutes": RETENTION_CLEANUP_INTERVAL_MINUTES,
        },
    }


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user: Annotated[UserContext, Depends(get_user_context)]):
    return {
        "username": user.username,
        "role": user.role,
        "tenant": user.tenant,
    }
