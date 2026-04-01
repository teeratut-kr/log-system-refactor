from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..api_models import RetentionRunResponse, RetentionStatusResponse
from ..auth import UserContext, get_admin_user
from ..config import RETENTION_CLEANUP_INTERVAL_MINUTES

router = APIRouter()


@router.get("/retention", response_model=RetentionStatusResponse)
async def get_retention(request: Request, user: Annotated[UserContext, Depends(get_admin_user)]):
    status = await request.app.state.storage.get_retention_status()
    return {
        **status,
        "cleanup_interval_minutes": RETENTION_CLEANUP_INTERVAL_MINUTES,
        "last_run": getattr(request.app.state, "last_retention_result", None),
        "auth": {"username": user.username, "role": user.role, "tenant": user.tenant},
    }


@router.post("/retention/run", response_model=RetentionRunResponse)
async def run_retention_now(request: Request, user: Annotated[UserContext, Depends(get_admin_user)]):
    result = await request.app.state.storage.run_retention(retention_days=None)
    request.app.state.last_retention_result = result
    return {
        **result,
        "auth": {"username": user.username, "role": user.role, "tenant": user.tenant},
    }
