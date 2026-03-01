from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit_logs,
    auth,
    events,
    items,
    products,
    purchase_requests,
    stock_movements,
    suppliers,
    users,
    warehouses,
)

router = APIRouter()


router.include_router(auth.router, prefix="/auth", tags=["auth"])

router.include_router(users.router, prefix="/users", tags=["users"])

router.include_router(items.router, prefix="/items", tags=["items"])

router.include_router(products.router, prefix="/products", tags=["products"])

router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])

router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])

router.include_router(
    purchase_requests.router, prefix="/purchase_requests", tags=["purchase_requests"]
)

router.include_router(
    stock_movements.router, prefix="/stock_movements", tags=["stock_movements"]
)

router.include_router(audit_logs.router, prefix="/audit_logs", tags=["audit_logs"])

router.include_router(events.router, prefix="/events", tags=["events"])
