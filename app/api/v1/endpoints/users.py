import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_current_active_user
from app.core.limiter import limiter
from app.db.database import DB
from app.middleware.tenant import OrgID
from app.models import RoleEnum, User
from app.schemas.user import (
    RegisterRequest,
    RegisterResponse,
    UserCreate,
    UserRead,
    UserUpdate,
    UserUpdatePassword,
    UserUpdateSelf,
)
from app.services.user import UserService

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_active_user)]


def get_service(db: DB) -> UserService:
    return UserService(db)


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != RoleEnum.ADMIN:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admins only.")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


# ── Registration (public) ─────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
)
@limiter.limit("3/hour")  # type: ignore
def register(
    request: Request,
    payload: RegisterRequest,
    service: UserService = Depends(get_service),
) -> RegisterResponse:
    """Create a new organization and its first admin user in one step."""
    user = service.register(payload)
    return RegisterResponse(
        user=UserRead.model_validate(user),
        org_id=user.org_id,
        subdomain=payload.subdomain,
    )


# ── Current user ──────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserRead,
)
def get_me(current_user: CurrentUser):
    return current_user


@router.patch(
    "/me",
    response_model=UserRead,
)
def update_me(
    payload: UserUpdateSelf,  # role excluded — users cannot promote themselves
    current_user: CurrentUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    # Convert UserUpdateSelf to UserUpdate before passing to service.update
    user_update = UserUpdate(**payload.model_dump())
    return service.update(
        org_id=org_id,
        user_id=current_user.id,
        actor_id=current_user.id,
        payload=user_update,
    )


@router.patch(
    "/me/password",
    response_model=UserRead,
)
def change_my_password(
    payload: UserUpdatePassword,
    current_user: CurrentUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    return service.change_password(
        org_id=org_id,
        user_id=current_user.id,
        payload=payload,
    )


# ── Admin user management ─────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=list[UserRead],
)
def list_users(
    _: AdminUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    return service.get_all(org_id)


@router.get(
    "/{user_id}",
    response_model=UserRead,
)
def get_user(
    user_id: uuid.UUID,
    _: AdminUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    return service.get_by_id(org_id, user_id)


@router.post(
    "/",
    response_model=UserRead,
    status_code=201,
)
def create_user(
    payload: UserCreate,
    current_user: AdminUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    return service.create(
        org_id=org_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.patch(
    "/{user_id}",
    response_model=UserRead,
)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,  # role included — admins can change roles
    current_user: AdminUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    return service.update(
        org_id=org_id,
        user_id=user_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.delete(
    "/{user_id}",
    status_code=204,
)
def delete_user(
    user_id: uuid.UUID,
    current_user: AdminUser,
    org_id: OrgID,
    service: UserService = Depends(get_service),
):
    service.delete(
        org_id=org_id,
        user_id=user_id,
        actor_id=current_user.id,
    )
