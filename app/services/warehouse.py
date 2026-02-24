import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import DB
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


class WarehouseService:
    def __init__(self, db: DB):
        self.db = db

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

    def create(self, org_id: uuid.UUID, payload: WarehouseCreate):
        warehouse = Warehouse(
            org_id=org_id,
            name=payload.name,
            location=payload.location,
            capacity=payload.capacity,
        )
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def update(
        self, org_id: uuid.UUID, warehouse_id: uuid.UUID, payload: WarehouseUpdate
    ):
        warehouse = self.get_by_id(org_id, warehouse_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(warehouse, field, value)

        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def delete(self, org_id: uuid.UUID, warehouse_id: uuid.UUID):
        warehouse = self.get_by_id(org_id, warehouse_id)
        self.db.delete(warehouse)
        self.db.commit()
