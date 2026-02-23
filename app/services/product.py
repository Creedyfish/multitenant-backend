# services/product.py
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import DB
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: DB):
        self.db = db

    def get_all(
        self, org_id: uuid.UUID, search: str | None = None, category: str | None = None
    ):
        query = select(Product).where(Product.org_id == org_id)

        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        if category:
            query = query.where(Product.category == category)

        return self.db.execute(query).scalars().all()

    def get_by_id(self, org_id: uuid.UUID, product_id: uuid.UUID):
        product = self.db.execute(
            select(Product).where(Product.id == product_id, Product.org_id == org_id)
        ).scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def create(self, org_id: uuid.UUID, payload: ProductCreate):
        existing = self.db.execute(
            select(Product).where(Product.sku == payload.sku, Product.org_id == org_id)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"SKU '{payload.sku}' already exists in this organization",
            )

        product = Product(
            org_id=org_id,
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            min_stock_level=payload.min_stock_level,
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, org_id: uuid.UUID, product_id: uuid.UUID, payload: ProductUpdate):
        product = self.get_by_id(org_id, product_id)

        if payload.sku and payload.sku != product.sku:
            existing = self.db.execute(
                select(Product).where(
                    Product.sku == payload.sku, Product.org_id == org_id
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=409, detail=f"SKU '{payload.sku}' already exists"
                )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, org_id: uuid.UUID, product_id: uuid.UUID):
        product = self.get_by_id(org_id, product_id)
        self.db.delete(product)
        self.db.commit()
