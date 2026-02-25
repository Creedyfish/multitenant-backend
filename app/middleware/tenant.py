from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.dependencies import get_current_active_user
from app.models.user import User


def get_subdomain_from_host(request: Request) -> str | None:
    host = request.headers.get("host", "").split(":")[0]  # strip port
    parts = host.split(".")
    if len(parts) >= 2 and parts[0] not in ("localhost", "www"):
        return parts[0]
    return None


def get_tenant(request: Request) -> str | None:
    subdomain = get_subdomain_from_host(request)
    if subdomain:
        return subdomain
    return request.headers.get("x-tenant-id")


def get_current_tenant(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UUID:
    return current_user.org_id


OrgID = Annotated[UUID, Depends(get_current_tenant)]
