from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.rbac import require_role
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services.warehouse import WarehouseService

router = APIRouter()


@router.post("/", response_model=WarehouseRead, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return WarehouseService(db).create(current_user.org_id, payload)


@router.get("/", response_model=list[WarehouseRead])
def get_warehouses(
    db: DB, current_user: Annotated[User, Depends(get_current_active_user)]
):
    return WarehouseService(db).get_all(current_user.org_id)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: UUID,
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return WarehouseService(db).get_by_id(current_user.org_id, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return WarehouseService(db).update(current_user.org_id, warehouse_id, payload)


@router.delete("/{warehouse_id}", status_code=204)
def delete_warehouse(
    warehouse_id: UUID,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    WarehouseService(db).delete(current_user.org_id, warehouse_id)
