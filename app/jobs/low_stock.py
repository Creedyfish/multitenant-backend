import logging
import uuid

from sqlalchemy import or_, select

from app.core.redis import redis_client
from app.db.database import SessionLocal
from app.models.enums import RoleEnum
from app.models.user import User
from app.models.warehouse import Warehouse
from app.services.email import send_low_stock_alert
from app.services.event_publisher import publish_event  # type: ignore
from app.services.product import ProductService
from app.services.stock_movement import StockService
from app.services.warehouse import WarehouseService

logger = logging.getLogger(__name__)


def check_low_stock(org_id: uuid.UUID, product_id: uuid.UUID, warehouse_id: uuid.UUID):
    db = SessionLocal()
    stock_levels = StockService(db).get_stock_levels(org_id, product_id, warehouse_id)

    if not stock_levels:
        logger.info(
            "No stock levels found  product_id=%s  warehouse_id=%s",
            product_id,
            warehouse_id,
        )
        return

    current_stock = stock_levels[0].current_stock

    product = ProductService(db).get_by_id(org_id, product_id)

    if current_stock < product.min_stock_level:
        logger.warning(
            "Low stock detected  product=%s  current=%d  minimum=%d  warehouse_id=%s",
            product.name,
            current_stock,
            product.min_stock_level,
            warehouse_id,
        )

        q = (
            select(User.email)
            .where(User.org_id == org_id)
            .where(or_(User.role == RoleEnum.ADMIN, User.role == RoleEnum.MANAGER))
        )
        recipients = db.execute(q).scalars().all()

        warehouse: Warehouse = WarehouseService(db).get_by_id(
            org_id=org_id, warehouse_id=warehouse_id
        )

        send_low_stock_alert(
            recipients=list(recipients),
            product_name=product.name,
            warehouse_name=warehouse.name,
            current_stock=current_stock,
            minimum_stock=product.min_stock_level,
        )
        publish_event(
            redis_client,
            org_id,
            "low_stock",
            {
                "product_id": str(product_id),
                "product_name": product.name,
                "warehouse_id": str(warehouse_id),
                "warehouse_name": warehouse.name,
                "current_stock": current_stock,
                "minimum_stock": product.min_stock_level,
            },
        )

    else:
        logger.info(
            "Stock OK  product=%s  current=%d  minimum=%d",
            product.name,
            current_stock,
            product.min_stock_level,
        )
