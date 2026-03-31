from fastapi import APIRouter, Request

from ..auth import get_user_context, require_admin
from ..config import RETENTION_CLEANUP_INTERVAL_MINUTES

router = APIRouter()


@router.get("/retention")
async def get_retention(request: Request):
    user = get_user_context(request)
    require_admin(user)
    status = await request.app.state.storage.get_retention_status()
    return {
        **status,
        "cleanup_interval_minutes": RETENTION_CLEANUP_INTERVAL_MINUTES,
        "last_run": getattr(request.app.state, "last_retention_result", None),
        "auth": {"username": user.username, "role": user.role, "tenant": user.tenant},
    }


@router.post("/retention/run")
async def run_retention_now(request: Request):
    user = get_user_context(request)
    require_admin(user)
    result = await request.app.state.storage.run_retention(retention_days=None)
    request.app.state.last_retention_result = result
    return {
        **result,
        "auth": {"username": user.username, "role": user.role, "tenant": user.tenant},
    }
