from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.tenant import OrgID
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_active_user)]


def get_service(db: DB) -> OrganizationService:
    return OrganizationService(db)


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != RoleEnum.ADMIN:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admins only.")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


@router.post("/", response_model=OrganizationRead, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    service: OrganizationService = Depends(get_service),
):
    """Public endpoint — no auth required to create an org (registration flow)."""
    return service.create(payload)


@router.get("/me", response_model=OrganizationRead)
def get_my_organization(
    current_user: CurrentUser,
    org_id: OrgID,
    service: OrganizationService = Depends(get_service),
):
    return service.get_by_id(org_id)


@router.patch("/me", response_model=OrganizationRead)
def update_my_organization(
    payload: OrganizationUpdate,
    current_user: AdminUser,
    org_id: OrgID,
    service: OrganizationService = Depends(get_service),
):
    """Only admins can update their organization details."""
    return service.update(org_id, payload)
