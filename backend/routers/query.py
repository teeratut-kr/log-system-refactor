from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request

from ..api_models import AlertsResponse, LogsResponse
from ..auth import UserContext, authorize_tenant, get_user_context
from ..response_utils import clean_log_items

router = APIRouter()


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    request: Request,
    user: Annotated[UserContext, Depends(get_user_context)],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    tenant: Optional[str] = None,
    source: Optional[str] = None,
    action: Optional[str] = None,
    min_severity: Optional[int] = Query(default=None, ge=0, le=10),
    max_severity: Optional[int] = Query(default=None, ge=0, le=10),
    start: Optional[str] = None,
    end: Optional[str] = None,
    q: Optional[str] = None,
    tag: Optional[str] = None,
):
    effective_tenant = authorize_tenant(user, tenant)
    result = await request.app.state.storage.query_logs(
        limit=limit,
        offset=offset,
        tenant=effective_tenant,
        source=source,
        action=action,
        min_severity=min_severity,
        max_severity=max_severity,
        start=start,
        end=end,
        q=q,
        tag=tag,
    )

    return {
        "count": result["count"],
        "items": clean_log_items(result["items"]),
        "auth": {
            "username": user.username,
            "role": user.role,
            "tenant": user.tenant,
            "effective_tenant": effective_tenant,
        },
    }


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    request: Request,
    user: Annotated[UserContext, Depends(get_user_context)],
    tenant: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    threshold: int = Query(default=3, ge=2, le=20),
    window_minutes: int = Query(default=5, ge=1, le=60),
    limit: int = Query(default=100, ge=1, le=1000),
):
    effective_tenant = authorize_tenant(user, tenant)
    result = await request.app.state.storage.query_alerts(
        tenant=effective_tenant,
        start=start,
        end=end,
        threshold=threshold,
        window_minutes=window_minutes,
        limit=limit,
    )
    return {
        "rule": "repeated_failed_login_same_ip_5m",
        "count": result["count"],
        "items": result["items"],
        "auth": {
            "username": user.username,
            "role": user.role,
            "tenant": user.tenant,
            "effective_tenant": effective_tenant,
        },
    }
