from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.cache import (
    get_cached,
    invalidate_org_products,
    make_list_key,
    make_single_key,
    set_cache,
)
from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.rbac import require_role
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from app.services.product import ProductService

router = APIRouter()


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
) -> ProductRead:
    result = ProductService(db).create(current_user.org_id, current_user.id, payload)
    invalidate_org_products(current_user.org_id)
    return result  # type: ignore[return-value]


@router.get("/", response_model=PaginatedProducts)
def get_products(
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
    search: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedProducts:
    key = make_list_key(current_user.org_id, search, category, limit, offset)
    cached = get_cached(key)
    if cached:
        return PaginatedProducts.model_validate(cached)

    result = ProductService(db).get_all(
        current_user.org_id, search, category, limit, offset
    )
    validated = PaginatedProducts.model_validate(result)
    set_cache(key, validated.model_dump(mode="json"))
    return validated


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    db: DB,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProductRead:
    key = make_single_key(current_user.org_id, product_id)
    cached = get_cached(key)
    if cached:
        return ProductRead.model_validate(cached)

    result = ProductService(db).get_by_id(current_user.org_id, product_id)
    validated = ProductRead.model_validate(result)
    set_cache(key, validated.model_dump(mode="json"))
    return validated


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
) -> ProductRead:
    result = ProductService(db).update(
        current_user.org_id, product_id, current_user.id, payload
    )
    invalidate_org_products(current_user.org_id)
    return result  # type: ignore[return-value]


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: UUID,
    db: DB,
    current_user: Annotated[
        User, Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER]))
    ],
) -> None:
    ProductService(db).delete(current_user.org_id, product_id, current_user.id)
    invalidate_org_products(current_user.org_id)
