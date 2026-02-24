from fastapi import APIRouter

from app.api.v1.endpoints import auth, items, products, users, warehouses

router = APIRouter()


router.include_router(auth.router, prefix="/auth", tags=["auth"])

router.include_router(users.router, prefix="/users", tags=["users"])

router.include_router(items.router, prefix="/items", tags=["items"])

router.include_router(products.router, prefix="/products", tags=["products"])

router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])
