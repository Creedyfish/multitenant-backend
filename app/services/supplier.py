import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import DB
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierService:
    def __init__(self, db: DB):
        self.db = db

    def get_all(self, org_id: uuid.UUID):
        return (
            self.db.execute(select(Supplier).where(Supplier.org_id == org_id))
            .scalars()
            .all()
        )

    def get_by_id(self, org_id: uuid.UUID, supplier_id: uuid.UUID):
        supplier = self.db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id, Supplier.org_id == org_id
            )
        ).scalar_one_or_none()

        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return supplier

    def create(self, org_id: uuid.UUID, payload: SupplierCreate):
        supplier = Supplier(
            org_id=org_id,
            name=payload.name,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            address=payload.address,
        )
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def update(
        self, org_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierUpdate
    ):
        supplier = self.get_by_id(org_id, supplier_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)

        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def delete(self, org_id: uuid.UUID, supplier_id: uuid.UUID):
        supplier = self.get_by_id(org_id, supplier_id)
        self.db.delete(supplier)
        self.db.commit()
