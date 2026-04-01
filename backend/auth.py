from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException

from .demo_users import DEMO_USERS, available_users


@dataclass
class UserContext:
    username: str
    role: str
    tenant: Optional[str]


def get_user_context(x_user: Annotated[Optional[str], Header(alias="X-User")] = None) -> UserContext:
    if not x_user:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Missing X-User header",
                "available_users": available_users(),
            },
        )

    user_record = DEMO_USERS.get(x_user)
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Unknown user",
                "available_users": available_users(),
            },
        )

    return UserContext(
        username=x_user,
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


def get_admin_user(user: Annotated[UserContext, Depends(get_user_context)]) -> UserContext:
    require_admin(user)
    return user
