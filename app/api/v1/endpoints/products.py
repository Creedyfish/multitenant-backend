from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.rbac import require_role
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import ProductService

router = APIRouter()


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return ProductService(db).create(current_user.org_id, payload)


@router.get("/", response_model=list[ProductRead])
def get_products(
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
    search: str | None = None,
    category: str | None = None,
):
    return ProductService(db).get_all(current_user.org_id, search, category)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return ProductService(db).get_by_id(current_user.org_id, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    return ProductService(db).update(current_user.org_id, product_id, payload)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: UUID,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
):
    ProductService(db).delete(current_user.org_id, product_id)
