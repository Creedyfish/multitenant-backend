from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.rbac import require_role
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.supplier import SupplierService

router = APIRouter()


@router.post("/", response_model=SupplierRead, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return SupplierService(db).create(current_user.org_id, payload)


@router.get("/", response_model=list[SupplierRead])
def get_suppliers(
    db: DB, current_user: Annotated[User, Depends(get_current_active_user)]
):
    return SupplierService(db).get_all(current_user.org_id)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: UUID,
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return SupplierService(db).get_by_id(current_user.org_id, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return SupplierService(db).update(current_user.org_id, supplier_id, payload)


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: UUID,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    SupplierService(db).delete(current_user.org_id, supplier_id)
