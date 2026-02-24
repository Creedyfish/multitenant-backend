import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.tenant import OrgID
from app.models.enums import RoleEnum, StockMovementTypeEnum
from app.models.user import User
from app.schemas.stock_movement import (
    StockAdjustmentCreate,
    StockInCreate,
    StockLevelOut,
    StockMovementOut,
    StockOutCreate,
    StockTransferCreate,
)
from app.services.stock_movement import StockService

router = APIRouter(prefix="/stock", tags=["Stock"])


def get_service(db: DB) -> StockService:
    return StockService(db)


def require_manager(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role not in (RoleEnum.ADMIN, RoleEnum.MANAGER):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Managers and admins only.")
    return current_user


ManagerUser = Annotated[User, Depends(require_manager)]


# ── Write endpoints (Manager/Admin only) ──────────────────────────────────────


@router.post("/in", response_model=StockMovementOut, status_code=201)
def stock_in(
    payload: StockInCreate,
    current_user: ManagerUser,
    org_id: OrgID,
    service: StockService = Depends(get_service),
):
    return service.stock_in(org_id=org_id, user_id=current_user.id, payload=payload)


@router.post("/out", response_model=StockMovementOut, status_code=201)
def stock_out(
    payload: StockOutCreate,
    current_user: ManagerUser,
    org_id: OrgID,
    service: StockService = Depends(get_service),
):
    return service.stock_out(org_id=org_id, user_id=current_user.id, payload=payload)


@router.post("/transfer", response_model=list[StockMovementOut], status_code=201)
def stock_transfer(
    payload: StockTransferCreate,
    current_user: ManagerUser,
    org_id: OrgID,
    service: StockService = Depends(get_service),
):
    out_mv, in_mv = service.transfer(
        org_id=org_id, user_id=current_user.id, payload=payload
    )
    return [out_mv, in_mv]


@router.post("/adjust", response_model=StockMovementOut, status_code=201)
def stock_adjust(
    payload: StockAdjustmentCreate,
    current_user: ManagerUser,
    org_id: OrgID,
    service: StockService = Depends(get_service),
):
    return service.adjust(org_id=org_id, user_id=current_user.id, payload=payload)


# ── Read endpoints (all roles) ────────────────────────────────────────────────


@router.get("/ledger", response_model=list[StockMovementOut])
def get_ledger(
    _current_user: Annotated[User, Depends(get_current_active_user)],
    org_id: OrgID,
    service: StockService = Depends(get_service),
    product_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    type: StockMovementTypeEnum | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return service.get_ledger(
        org_id=org_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=type,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/levels", response_model=list[StockLevelOut])
def get_stock_levels(
    _: Annotated[User, Depends(get_current_active_user)],
    org_id: OrgID,
    service: StockService = Depends(get_service),
    product_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
):
    return service.get_stock_levels(
        org_id=org_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )
