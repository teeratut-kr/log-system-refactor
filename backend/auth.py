from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import HTTPException, Request

USERS: Dict[str, Dict[str, Optional[str]]] = {
    "admin1": {"role": "admin", "tenant": None},
    "viewerA": {"role": "viewer", "tenant": "demoA"},
    "viewerB": {"role": "viewer", "tenant": "demoB"},
}


@dataclass
class UserContext:
    username: str
    role: str
    tenant: Optional[str]


def get_user_context(request: Request) -> UserContext:
    username = request.headers.get("X-User")
    if not username:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Missing X-User header",
                "available_users": list(USERS.keys()),
            },
        )

    user_record = USERS.get(username)
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Unknown user",
                "available_users": list(USERS.keys()),
            },
        )

    return UserContext(
        username=username,
        role=str(user_record["role"]),
        tenant=user_record["tenant"],
    )


def authorize_tenant(user: UserContext, requested_tenant: Optional[str]) -> Optional[str]:
    if user.role == "admin":
        return requested_tenant

    if requested_tenant and requested_tenant != user.tenant:
        raise HTTPException(
            status_code=403,
            detail=f"Viewer '{user.username}' can only access tenant '{user.tenant}'",
        )
    return user.tenant


def require_admin(user: UserContext) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
