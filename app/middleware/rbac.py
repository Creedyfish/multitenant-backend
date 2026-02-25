from typing import Annotated

from fastapi import Depends, HTTPException

from app.core.dependencies import get_current_active_user
from app.models.enums import RoleEnum
from app.models.user import User


def require_role(roles: list[RoleEnum]):
    def dependency(current_user: Annotated[User, Depends(get_current_active_user)]):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency
