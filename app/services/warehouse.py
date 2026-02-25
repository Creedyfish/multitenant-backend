import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import DB
from app.models.warehouse import Warehouse
from app.schemas.audit_log import AuditLogCreate
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate
from app.services.audit_log import AuditService


class WarehouseService:
    def __init__(self, db: DB):
        self.db = db
        self.audit = AuditService(db)

    @staticmethod
    def _snapshot(warehouse: Warehouse) -> dict[str, str | int | None]:
        return {
            "name": warehouse.name,
            "location": warehouse.location,
            "capacity": warehouse.capacity,
        }

    def get_all(self, org_id: uuid.UUID):
        return (
            self.db.execute(select(Warehouse).where(Warehouse.org_id == org_id))
            .scalars()
            .all()
        )

    def get_by_id(self, org_id: uuid.UUID, warehouse_id: uuid.UUID):
        warehouse = self.db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id, Warehouse.org_id == org_id
            )
        ).scalar_one_or_none()

        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return warehouse

    def create(self, org_id: uuid.UUID, actor_id: uuid.UUID, payload: WarehouseCreate):
        warehouse = Warehouse(
            org_id=org_id,
            name=payload.name,
            location=payload.location,
            capacity=payload.capacity,
        )
        self.db.add(warehouse)
        self.db.flush()
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="CREATE",
                entity="Warehouse",
                entity_id=str(warehouse.id),
                before=None,
                after=self._snapshot(warehouse),
            ),
        )
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def update(
        self,
        org_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: WarehouseUpdate,
    ):
        warehouse = self.get_by_id(org_id, warehouse_id)
        before = self._snapshot(warehouse)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(warehouse, field, value)

        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="UPDATE",
                entity="Warehouse",
                entity_id=str(warehouse.id),
                before=before,
                after=self._snapshot(warehouse),
            ),
        )
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def delete(self, org_id: uuid.UUID, warehouse_id: uuid.UUID, actor_id: uuid.UUID):
        warehouse = self.get_by_id(org_id, warehouse_id)
        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="DELETE",
                entity="Warehouse",
                entity_id=str(warehouse.id),
                before=self._snapshot(warehouse),
                after={"deleted": True},
            ),
        )
        self.db.delete(warehouse)
        self.db.commit()
