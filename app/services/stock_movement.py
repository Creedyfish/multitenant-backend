import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.db.database import DB
from app.models.enums import StockMovementTypeEnum
from app.models.stock_movement import StockMovement
from app.schemas.audit_log import AuditLogCreate
from app.schemas.stock_movement import (
    StockAdjustmentCreate,
    StockInCreate,
    StockLevelOut,
    StockOutCreate,
    StockTransferCreate,
)
from app.services.audit_log import AuditService


class StockService:
    def __init__(self, db: DB):
        self.db = db
        self.audit = AuditService(db)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _current_stock(
        self, org_id: uuid.UUID, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> int:
        signed_qty = case(
            (
                StockMovement.type.in_(
                    [
                        StockMovementTypeEnum.IN,
                        StockMovementTypeEnum.TRANSFER_IN,
                        StockMovementTypeEnum.ADJUSTMENT,
                    ]
                ),
                StockMovement.quantity,
            ),
            else_=-StockMovement.quantity,
        )
        result = self.db.execute(
            select(func.coalesce(func.sum(signed_qty), 0)).where(
                StockMovement.org_id == org_id,
                StockMovement.product_id == product_id,
                StockMovement.warehouse_id == warehouse_id,
            )
        ).scalar_one()
        return int(result)

    def _create_movement(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        movement_type: StockMovementTypeEnum,
        quantity: int,
        reference: str | None = None,
        notes: str | None = None,
    ) -> StockMovement:
        movement = StockMovement(
            org_id=org_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=user_id,
        )
        self.db.add(movement)
        return movement

    @staticmethod
    def _movement_snapshot(movement: StockMovement) -> dict[str, str | int | None]:
        return {
            "product_id": str(movement.product_id),
            "warehouse_id": str(movement.warehouse_id),
            "type": movement.type.value,
            "quantity": movement.quantity,
            "reference": movement.reference,
            "notes": movement.notes,
        }

    # ── Public methods ────────────────────────────────────────────────────────

    def stock_in(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: StockInCreate,
    ) -> StockMovement:
        movement = self._create_movement(
            org_id=org_id,
            user_id=user_id,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            movement_type=StockMovementTypeEnum.IN,
            quantity=payload.quantity,
            reference=payload.reference,
            notes=payload.notes,
        )
        self.db.flush()
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=user_id,
                action="STOCK_IN",
                entity="StockMovement",
                entity_id=str(movement.id),
                before=None,
                after=self._movement_snapshot(movement),
            ),
        )
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def stock_out(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: StockOutCreate,
    ) -> StockMovement:
        current = self._current_stock(org_id, payload.product_id, payload.warehouse_id)
        if current < payload.quantity:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient stock. Available: {current}, requested: {payload.quantity}.",
            )

        movement = self._create_movement(
            org_id=org_id,
            user_id=user_id,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            movement_type=StockMovementTypeEnum.OUT,
            quantity=payload.quantity,
            reference=payload.reference,
            notes=payload.notes,
        )
        self.db.flush()
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=user_id,
                action="STOCK_OUT",
                entity="StockMovement",
                entity_id=str(movement.id),
                before=None,
                after=self._movement_snapshot(movement),
            ),
        )
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def transfer(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: StockTransferCreate,
    ) -> tuple[StockMovement, StockMovement]:
        if payload.from_warehouse_id == payload.to_warehouse_id:
            raise HTTPException(
                status_code=422,
                detail="Source and destination warehouses must be different.",
            )

        current = self._current_stock(
            org_id, payload.product_id, payload.from_warehouse_id
        )
        if current < payload.quantity:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient stock. Available: {current}, requested: {payload.quantity}.",
            )

        transfer_ref = f"TRANSFER-{uuid.uuid4().hex[:8].upper()}"

        out_movement = self._create_movement(
            org_id=org_id,
            user_id=user_id,
            product_id=payload.product_id,
            warehouse_id=payload.from_warehouse_id,
            movement_type=StockMovementTypeEnum.TRANSFER_OUT,
            quantity=payload.quantity,
            reference=transfer_ref,
            notes=payload.notes,
        )
        in_movement = self._create_movement(
            org_id=org_id,
            user_id=user_id,
            product_id=payload.product_id,
            warehouse_id=payload.to_warehouse_id,
            movement_type=StockMovementTypeEnum.TRANSFER_IN,
            quantity=payload.quantity,
            reference=transfer_ref,
            notes=payload.notes,
        )

        self.db.flush()
        # Log a single audit entry for the transfer as a whole, referencing
        # both movement IDs and the shared transfer_ref so it's easy to query.
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=user_id,
                action="STOCK_TRANSFER",
                entity="StockMovement",
                entity_id=str(out_movement.id),
                before=None,
                after={
                    "transfer_ref": transfer_ref,
                    "product_id": str(payload.product_id),
                    "from_warehouse_id": str(payload.from_warehouse_id),
                    "to_warehouse_id": str(payload.to_warehouse_id),
                    "quantity": payload.quantity,
                    "notes": payload.notes,
                    "in_movement_id": str(in_movement.id),
                },
            ),
        )
        self.db.commit()
        self.db.refresh(out_movement)
        self.db.refresh(in_movement)
        return out_movement, in_movement

    def adjust(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: StockAdjustmentCreate,
    ) -> StockMovement:
        if payload.quantity == 0:
            raise HTTPException(
                status_code=422, detail="Adjustment quantity cannot be zero."
            )

        if payload.quantity < 0:
            current = self._current_stock(
                org_id, payload.product_id, payload.warehouse_id
            )
            if current < abs(payload.quantity):
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient stock to adjust. Available: {current}.",
                )

        movement = self._create_movement(
            org_id=org_id,
            user_id=user_id,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            movement_type=StockMovementTypeEnum.ADJUSTMENT,
            quantity=payload.quantity,
            reference=payload.reference,
            notes=payload.notes,
        )
        self.db.flush()
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=user_id,
                action="STOCK_ADJUSTMENT",
                entity="StockMovement",
                entity_id=str(movement.id),
                before=None,
                after=self._movement_snapshot(movement),
            ),
        )
        self.db.commit()
        self.db.refresh(movement)
        return movement

    # ── Read methods (unchanged) ──────────────────────────────────────────────

    def get_ledger(
        self,
        org_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        movement_type: StockMovementTypeEnum | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[StockMovement]:
        q = select(StockMovement).where(StockMovement.org_id == org_id)

        if product_id:
            q = q.where(StockMovement.product_id == product_id)
        if warehouse_id:
            q = q.where(StockMovement.warehouse_id == warehouse_id)
        if movement_type:
            q = q.where(StockMovement.type == movement_type)
        if start_date:
            q = q.where(StockMovement.created_at >= start_date)
        if end_date:
            q = q.where(StockMovement.created_at <= end_date)

        q = q.order_by(StockMovement.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(q).scalars().all())

    def get_stock_levels(
        self,
        org_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
    ) -> list[StockLevelOut]:
        signed_qty = case(
            (
                StockMovement.type.in_(
                    [
                        StockMovementTypeEnum.IN,
                        StockMovementTypeEnum.TRANSFER_IN,
                        StockMovementTypeEnum.ADJUSTMENT,
                    ]
                ),
                StockMovement.quantity,
            ),
            else_=-StockMovement.quantity,
        )

        q = (
            select(
                StockMovement.product_id,
                StockMovement.warehouse_id,
                func.sum(signed_qty).label("current_stock"),
            )
            .where(StockMovement.org_id == org_id)
            .group_by(StockMovement.product_id, StockMovement.warehouse_id)
        )

        if product_id:
            q = q.where(StockMovement.product_id == product_id)
        if warehouse_id:
            q = q.where(StockMovement.warehouse_id == warehouse_id)

        rows = self.db.execute(q).all()
        return [
            StockLevelOut(
                product_id=row.product_id,
                warehouse_id=row.warehouse_id,
                current_stock=int(row.current_stock),
            )
            for row in rows
        ]
